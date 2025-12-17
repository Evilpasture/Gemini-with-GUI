from typing import TYPE_CHECKING

if TYPE_CHECKING:
    def _(s: str) -> str: ...

import threading
import json
import os # for error handling
from openai import APIError, AuthenticationError


class ChatManager:
    def __init__(self, client, response_callback, settings, safety_settings):
        self.client = client
        self.callback = response_callback
        self.settings = settings
        self.safety = safety_settings
        self.formatted_safety = []
        self.format_safety()
        self.history = None
        self.memory = None

        self.current_model = None
        self.temperature = None

        self.lock = threading.Lock()
        self.is_busy = False

        self.role_map = {}

        self.init_chat()

    def update_settings(self, new_settings, new_safety):
        """Preserve history when settings change by updating the local list."""
        with self.lock:
            current_history = getattr(self, "history", None)
            self.settings = new_settings
            self.safety = new_safety
            self.format_safety()
            self.init_chat(history=current_history)

    def format_safety(self):
        self.formatted_safety = [
            {"category": f"HARM_CATEGORY_{cat}", "threshold": thresh}
            for cat, thresh in self.safety.items()
        ]

    def init_chat(self, history=None):
        try:
            username = self.settings.get('user_name', 'User')
            chatbot_name = self.settings.get('chatbot_name', 'Gemini')
            # MEMORY!!! I should have implemented this a while ago
            # This injects directly into the instructions.
            memory_block = f"\nRELEVANT MEMORY: {self.memory}" if self.memory else ""

            # Explicitly instruct model to use Markdown just in case
            sys_instruct = (
                f"{self.settings.get('instruction', '')}\n"
                f"You are talking to {username}. {memory_block}\n"
                "Format responses in Markdown. "
                "However, you don't have to use formatting often while chatting.\n"
                "System Instructions: Due to the fact that you are called via the OpenAI library from Python, "
                "here are the safety configurations meant to substitute "
                f"the native safety settings of Google-GenAI SDK, injected right inside the system instructions."
                f"\n{str(self.formatted_safety)}\n"
                f"User is using \"{self.settings.get('language', 'en')}\" "
                "in their configurations for added context, but otherwise, "
                "reply with the same language as the prompt just normally."
            )

            new_system_message = {"role": "system", "content": sys_instruct}

            if history:
                # Filter out the OLD system message and keep the actual chat
                clean_history = [msg for msg in history if msg['role'] != 'system']
                self.history = [new_system_message] + clean_history
            else:
                self.history = [new_system_message]

            self.current_model = self.settings.get('model_name', 'gemini-2.5-flash')
            self.temperature = float(self.settings.get('temperature', 0.7))

            self.role_map = {
                'user': username,
                'assistant': chatbot_name
            }
        except Exception as e:
            _error_template = _("System Error: Failed to init model. %s")
            _output = _error_template % e
            self.callback(_output, "error")

    def process_input(self, text):
        """Starts the API call in a separate thread."""
        if not text.strip(): return

        if self.lock.locked():
            self.callback(_("Please wait for the current message to finish."), "warning")
            return

        t = threading.Thread(target=self._run_thread, args=(text,))
        t.daemon = True
        t.start()

    def _run_thread(self, text):
        if not self.lock.acquire(blocking=False):
            return

        self.is_busy = True

        try:
            if not self.chat:
                self.callback(_("Session not initialized."), "error")
                return

            stream = self.chat.send_message_stream(text)

            for chunk in stream:
                if chunk.text:
                    self.callback(chunk.text, "stream")

            self.callback(None, "finished")

        except errors.APIError as e:
            _error_template = _("API Error: %s")
            _output = _error_template % e.message
            self.callback(_output, "error")
        except Exception as e:
            _error_template = _("Connection Error: %s")
            _output = _error_template % e
            self.callback(_output, "error")
        finally:
            self.is_busy = False
            self.lock.release()

    @staticmethod
    def _consolidate_history(raw_history):
        """
        Fixes fragmentation in two steps:
        1. Merges ADJACENT Content objects that have the same role (e.g. Model -> Model).
        2. Merges fragmented text PARTS within those objects (e.g. "He", "llo").
        """
        if not raw_history:
            return []

        # --- Step 1: Merge Adjacent Content Objects ---
        merged_content_list = []

        # Initialize with the first item
        if len(raw_history) > 0:
            current_role = raw_history[0].role
            current_parts = list(raw_history[0].parts)

            for i in range(1, len(raw_history)):
                next_item = raw_history[i]

                if next_item.role == current_role:
                    # Found a split message (Model followed by Model). Merge them.
                    current_parts.extend(next_item.parts)
                else:
                    # Role changed (Model -> User). Save current and start new.
                    merged_content_list.append(types.Content(role=current_role, parts=current_parts))
                    current_role = next_item.role
                    current_parts = list(next_item.parts)

            # Append the final accumulated message
            merged_content_list.append(types.Content(role=current_role, parts=current_parts))

        # --- Step 2: Clean and Merge Text Parts ---
        final_history = []
        for content in merged_content_list:
            clean_parts = []
            text_buffer = []

            for part in content.parts:
                # Check for strictly non-text data (Files, Images, Function Calls)
                # Using getattr to be safe against SDK updates
                is_blob = (
                        getattr(part, 'inline_data', None) or
                        getattr(part, 'function_call', None) or
                        getattr(part, 'function_response', None) or
                        getattr(part, 'file_data', None) or
                        getattr(part, 'executable_code', None) or
                        getattr(part, 'code_execution_result', None)
                )

                if is_blob:
                    # Flush buffer before adding blob
                    if text_buffer:
                        clean_parts.append(types.Part(text="".join(text_buffer)))
                        text_buffer = []
                    clean_parts.append(part)
                else:
                    # It's text (or an empty stream spacer)
                    txt = getattr(part, 'text', '') or ""
                    text_buffer.append(txt)

            # Flush remaining text
            if text_buffer:
                clean_parts.append(types.Part(text="".join(text_buffer)))

            final_history.append(types.Content(role=content.role, parts=clean_parts))

        return final_history

    def save_history(self, filepath):
        if self.lock.locked():
            return _("Cannot save while generating response."), False

        if not self.chat:
            return _("No chat to save."), False

        try:
            raw_history = self.chat.get_history()
            clean_history = self._consolidate_history(raw_history)

            # Convert objects to JSON-serializable dicts
            hist_data = [h.model_dump(mode='json', exclude_none=True) for h in clean_history]

            # CREATE A WRAPPER OBJECT
            save_package = {
                "metadata": {
                    "user_name": self.settings.get('user_name', 'User'),
                    "chatbot_name": self.settings.get('chatbot_name', 'Gemini'),
                    "instruction": self.settings.get('instruction', '')
                },
                "history": hist_data
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_package, f, indent=2, ensure_ascii=False)

            _prefix = _("Saved session to %s")
            _output = _prefix % os.path.basename(filepath)
            return _output, True
        except Exception as e:
            _error_template = _("Save failed: %s")
            _output = _error_template % e
            return _output, False

    def load_history(self, filepath):
        if self.lock.locked():
            return None, _("Cannot load while generating."), False

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                package = json.load(f)

            # Check if it's the new format or the old list-only format
            if isinstance(package, dict) and "history" in package:
                metadata = package.get("metadata", {})
                history_raw = package.get("history", [])

                # Update settings with names from the file
                self.settings['user_name'] = metadata.get('user_name', self.settings.get('user_name'))
                self.settings['chatbot_name'] = metadata.get('chatbot_name', self.settings.get('chatbot_name'))
                self.settings['instruction'] = metadata.get('instruction', self.settings.get('instruction'))
            else:
                # Fallback for old files that are just a list
                history_raw = package

            # Convert dicts back to SDK types
            history = [types.Content(**d) for d in history_raw]

            with self.lock:
                # Re-initialize with the loaded history and updated settings
                self.init_chat(history)

            return history, _("Loaded successfully"), True

        except Exception as e:
            _error_template = _("Load failed: %s")
            _output = _error_template % e
            return None, _output, False

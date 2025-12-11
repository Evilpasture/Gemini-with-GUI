import threading
import json
import os # for error handling
from google.genai import types, errors


class ChatManager:
    def __init__(self, client, response_callback, settings, safety_settings):
        self.client = client
        self.callback = response_callback
        self.settings = settings
        self.safety = safety_settings
        self.chat = None
        self.init_chat()

    def update_settings(self, new_settings, new_safety):
        """Preserve history when settings change so that the bot doesn't treat you like a stranger"""
        history = []
        if self.chat:
            history = self.chat.get_history()

        self.settings = new_settings
        self.safety = new_safety
        self.init_chat(history)

    def init_chat(self, history=None):
        try:
            # Explicitly instruct model to use Markdown, solving the parsing ambiguity
            sys_instruct = (
                f"{self.settings.get('instruction', '')}\n"
                f"You are talking to {self.settings.get('user_name', 'User')}. "
                "Format responses in Markdown."
            )

            config = types.GenerateContentConfig(
                system_instruction=sys_instruct,
                temperature=float(self.settings.get('temperature', 0.7)),
                safety_settings=self.safety
            )

            self.chat = self.client.chats.create(
                model=self.settings.get('model_name', 'gemini-2.0-flash'),
                config=config,
                history=history or []
            )
        except Exception as e:
            self.callback(f"System Error: Failed to init model.\n{e}", "error")

    def process_input(self, text):
        """Starts the API call in a separate thread."""
        if not text.strip(): return
        # Use threading to prevent GUI freeze
        t = threading.Thread(target=self._run_thread, args=(text,))
        t.daemon = True
        t.start()

    def _run_thread(self, text):
        if not self.chat:
            self.callback("Session not initialized.", "error")
            return

        try:
            stream = self.chat.send_message_stream(text)
            for chunk in stream:
                if chunk.text:
                    self.callback(chunk.text, "stream")
            self.callback(None, "finished")

        except errors.APIError as e:
            self.callback(f"API Error: {e.message}", "error")
        except Exception as e:
            self.callback(f"Connection Error: {e}", "error")
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
        if not self.chat: return "No chat to save.", False
        try:
            # Ensure ASCII is false to support Unicode/Emoji
            hist_data = [
                types.Content.model_dump(h, exclude_none=True)
                for h in self.chat.get_history()
            ]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(hist_data, f, indent=2, ensure_ascii=False)
            return f"Saved to {os.path.basename(filepath)}", True
        except Exception as e:
            return f"Save failed: {e}", False

    def load_history(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Reconstruct Google Types
            history = [types.Content(**d) for d in data]
            self.init_chat(history)
            return history, "Loaded successfully", True
        except Exception as e:
            return None, f"Load failed: {e}", False

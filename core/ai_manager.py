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

    def summarize_old_history(self):
        """Compresses oldest messages into long-term memory.

        Hopefully, it will mock you for prompting embarrassing things."""
        if len(self.history) < 30:
            return
        to_summarize = self.history[1:11]
        summary_prompt = (
            "Briefly summarize the key facts from this conversation history into 2-3 sentences. "
            "Focus on user preferences, current tasks. Poke fun if it's strange and be playful."
            "If it's a roleplay, summarize the roleplay for reuse in future conversations with the same characters."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.current_model,
                messages=to_summarize + [{"role": "user", "content": summary_prompt}],
                temperature=0.3  # Low temperature for factual summary
            )

            new_facts = response.choices[0].message.content
            # Update memory and remove the summarized messages
            self.memory = f"{self.memory} {new_facts}".strip()
            self.history = [self.history[0]] + self.history[11:]

            # Re-init to update the system prompt with new memory
            self.init_chat(history=self.history)

        except Exception as e:
            _error_template = _("Memory Compression Failed: %s")
            print(_error_template % e)


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
        full_response_content = ""

        try:
            self.history.append({"role": "user", "content": text})

            stream = self.client.chat.completions.create(
                model=self.current_model,
                messages=self._get_trimmed_history(max_messages=20),
                temperature=self.temperature,
                stream=True,
                # I AM INCREDIBLY UPSET THAT THIS DOESN'T WORK.
                # extra_body={
                #     "google": {
                #         "safetySettings": self.formatted_safety
                #     }
                # } if "gemini" in self.current_model else None,
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response_content += content
                    self.callback(content, "stream")

            self.history.append({"role": "assistant", "content": full_response_content})

            if len(self.history) > 20:
                self.summarize_old_history()

            self.callback(None, "finished")

        except AuthenticationError:
            self.callback(_("Invalid API key. Update in settings."), "error")
        except APIError as e:
            _error_template = _("API Error: %s")
            _output = _error_template % str(e)
            self.callback(_output, "error")
        except Exception as e:
            _error_template = _("Connection Error: %s")
            _output = _error_template % e
            self.callback(_output, "error")
        finally:
            self.is_busy = False
            if self.lock.locked():
                self.lock.release()

    def _get_trimmed_history(self, max_messages=15):
        if len(self.history) <= max_messages:
            return self.history
        system_msg = self.history[0]
        recent_context = self.history[-(max_messages - 1):]

        return [system_msg] + recent_context

    @staticmethod
    def _consolidate_history(raw_history):
        """
        Fixes fragmentation in two steps:
        1. Merges ADJACENT Content objects that have the same role.
        2. Merges fragmented text PARTS within those objects into a single block (e.g. "He", "llo").
        """
        if not raw_history:
            return []

        consolidated = []

        for message in raw_history:
            role = message.get("role")
            content = message.get("content", "")

            # If the last message added has the same role, merge them
            if consolidated and consolidated[-1]["role"] == role:
                # We add a newline to separate the merged thoughts visually
                consolidated[-1]["content"] += f"\n{content}"
            else:
                # New role or first message, add it as a new dictionary
                consolidated.append({"role": role, "content": content})

        return consolidated

    def save_history(self, filepath):
        if self.lock.locked():
            return _("Cannot save while generating response."), False

        # Check the new list instead of the old self.chat object
        if not hasattr(self, 'history') or not self.history:
            return _("No chat to save."), False

        try:
            # 1. Consolidate history (using your new OpenAI-style logic)
            clean_history = self._consolidate_history(self.history)

            # 2. Prepare the wrapper (History is already dicts, so no model_dump needed)
            save_package = {
                "metadata": {
                    "user_name": self.settings.get('user_name', 'User'),
                    "chatbot_name": self.settings.get('chatbot_name', 'Gemini'),
                    "instruction": self.settings.get('instruction', ''),
                    "memory": self.memory
                },
                "history": clean_history
            }

            # 3. Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_package, f, indent=2, ensure_ascii=False)

            return _("Saved session to %s") % os.path.basename(filepath), True
        except Exception as e:
            return _("Save failed: %s") % str(e), False

    def load_history(self, filepath):
        if self.lock.locked():
            return None, _("Cannot load while generating."), False

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                package = json.load(f)

            if isinstance(package, dict) and "history" in package:
                metadata = package.get("metadata", {})
                history = package.get("history", [])

                # Update settings from metadata
                self.settings['user_name'] = metadata.get('user_name', self.settings.get('user_name'))
                self.settings['chatbot_name'] = metadata.get('chatbot_name', self.settings.get('chatbot_name'))
                self.settings['instruction'] = metadata.get('instruction', self.settings.get('instruction'))

                self.memory = metadata.get("memory", "")
            else:
                # Fallback for old files that are just a list
                history = package
                self.memory = ""

            with self.lock:
                self.init_chat(history)

            return history, _("Loaded successfully"), True

        except Exception as e:
            return None, _("Load failed: %s") % str(e), False

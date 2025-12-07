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

    def save_history(self, filepath):
        if not self.chat:
            return "Error: No active chat.", False
        try:
            # Dump history to a list of dicts
            history_list = [
                types.Content.model_dump(h, exclude_none=True)
                for h in self.chat.get_history()
            ]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history_list, f, indent=4, ensure_ascii=False)
            return f"Saved to {filepath}", True
        except Exception as e:
            return f"Save Error: {e}", False

    def load_history(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                history_data = json.load(f)

            # Reconstruct types.Content objects
            loaded_history = [types.Content(**d) for d in history_data]

            # Re-init chat with new history
            self.init_chat(history=loaded_history)
            return loaded_history, f"Loaded from {filepath}", True
        except Exception as e:
            return None, f"Load Error: {e}", False
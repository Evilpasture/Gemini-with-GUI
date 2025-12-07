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

    def update_settings(self, new_settings, new_safety, new_debug):
        """Updates settings and re-initializes the chat session while preserving history."""
        current_history = None
        if self.chat:
            try:
                # Attempt to save current context before reloading
                current_history = self.chat.get_history()
            except Exception as e:
                print(f"History preservation failed during update: {e}")
                current_history = []

        self.settings = new_settings
        self.safety_settings = new_safety
        self.debug_settings = new_debug

        self.init_chat(history=current_history)

    def init_chat(self, history=None):
        try:
            markup_style = self.debug_settings.get('markup_language', 'AsciiDoc')

            if markup_style == "Markdown":
                markup_instruction = ""
            else:
                markup_instruction = (
                    f"\n[SYSTEM: Please use {markup_style} formatting "
                    f"instead of Markdown for code blocks and headers.]"
                )

            persona = f"You are talking to {self.settings.get('user_name', 'User')}."
            full_instruction = f"{self.settings.get('instruction', '')}\n{persona}{markup_instruction}"

            config = types.GenerateContentConfig(
                system_instruction=full_instruction,
                temperature=float(self.settings.get('temperature', 0.7)),
                safety_settings=self.safety_settings
            )

            self.chat = self.client.chats.create(
                model=self.settings.get('model_name', 'gemini-1.5-flash'),
                config=config,
                history=history
            )
        except Exception as e:
            print(f"Chat Initialization Error: {e}")
            # Send error as "error" string, not boolean True
            self.response_callback(f"System Error: Failed to initialize model.\n{e}", "error")

    def process_input(self, user_text):
        """Starts the API call in a separate thread."""
        if not user_text.strip():
            return

        thread = threading.Thread(target=self._run_api_call, args=(user_text,))
        thread.daemon = True
        thread.start()

    def _run_api_call(self, text):
        if not self.chat:
            self.response_callback("Chat session not initialized.", "error")
            return

        try:
            # Send stream request
            response_stream = self.chat.send_message_stream(text)

            for chunk in response_stream:
                if chunk.text:
                    self.response_callback(chunk.text, "stream")

            self.response_callback(None, "finished")

        except errors.APIError as e:
            # Handle API-specific errors (400, 403, etc.)
            self.response_callback(f"API Error {e.code}: {e.message}", "error")
        except Exception as e:
            # Handle connection or unknown errors
            self.response_callback(f"Unexpected Error: {str(e)}", "error")

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
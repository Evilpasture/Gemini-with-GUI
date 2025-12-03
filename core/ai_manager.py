import threading
import json
from google.genai import types, errors

class ChatManager:
    def __init__(self, client, response_callback, settings, safety_settings):
        self.client = client
        self.response_callback = response_callback # Function to call when AI replies
        self.settings = settings
        self.safety_settings = safety_settings
        self.chat = None
        self.init_chat()

    def update_settings(self, new_settings, new_safety):
        current_history = None
        if self.chat:
            try:
                current_history = self.chat.get_history()
            except Exception as e:
                print(f"Chat Init Error: {e}")
                current_history = []

        self.settings = new_settings
        self.safety_settings = new_safety

        # Note: Changing settings will reinitialize chat with current history
        self.init_chat(history=current_history)

    def init_chat(self, history=None):
        try:
            persona = f"At this present, you are talking to {self.settings['user_name']}. "
            config = types.GenerateContentConfig(
                system_instruction=f"{self.settings['instruction']}\n{persona}",
                temperature=self.settings['temperature'],
                safety_settings=self.safety_settings
            )
            self.chat = self.client.chats.create(
                model=self.settings['model_name'],
                config=config,
                history=history
            )
        except Exception as e:
            print(f"Chat Init Error: {e}")
            self.response_callback(f"System Error: Failed to initialize model.", True)

    def process_input(self, user_text):
        """Starts the API call in a separate thread"""
        thread = threading.Thread(target=self._run_api_call, args=(user_text,))
        thread.daemon = True
        thread.start()

    def _run_api_call(self, text):
        if not self.chat:
            self.response_callback("Chat session not initialized.", True)
            return
        # self.handle_safety()
        try:
            response_stream = self.chat.send_message_stream(text)

            for chunk in response_stream:
                if chunk.text:
                    # Send partial chunks to GUI
                    # Note: You need to update your callback to handle "append" vs "finished"
                    self.response_callback(chunk.text, "stream")

            self.response_callback(None, "finished")  # Signal done
        except errors.APIError as e:
            self.response_callback(f"API Error {e.code}: {e.message}", True)
        except Exception as e:
            self.response_callback(f"Error: {str(e)}", True)

    def handle_safety(self, reason, original_prompt):
        # not very urgent right now, you can always relax the filters.
        # the only problem is when you wrote a long prompt, but you didn't receive a response, thus wasting input token.
        print(reason)
        new_prompt = original_prompt
        return new_prompt

    def save_history(self, filepath):
        if not self.chat:
            return "Error: No active chat.", False
        try:
            history_list = [types.Content.model_dump(h, exclude_none=True) for h in self.chat.get_history()]
            with open(filepath, 'w') as f:
                json.dump(history_list, f, indent=4)
            return f"Saved to {filepath}", True
        except Exception as e:
            return f"Save Error: {e}", False

    def load_history(self, filepath):
        try:
            with open(filepath, 'r') as f:
                history_data = json.load(f)
            loaded_history = [types.Content(**d) for d in history_data]
            self.init_chat(history=loaded_history)
            return loaded_history, f"Loaded from {filepath}", True
        except Exception as e:
            return None, f"Load Error: {e}", False

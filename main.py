import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import os
import sys

# --- Third-Party Dependency Check ---
try:
    from dotenv import load_dotenv
    from google import genai
    from google.genai.errors import APIError
    from ttkthemes import ThemedTk
except ImportError as e:
    missing_package = str(e).split(' ')[-1]
    tk.messagebox.showerror(
        "Dependency Error",
        f"Missing critical library: '{missing_package}'. Please install dependencies."
    )
    sys.exit(1)

# --- Internal Module Setup ---
SCRIPT_DIR = Path(getattr(sys, 'frozen', False) and sys.executable or __file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

try:
    from core.config import ConfigManager
    from core.ai_manager import ChatManager
    from ui.main_window import MainWindow
    from ui.settings import PreferencesWindow
    from ui.dialog import Dialog
except ImportError as e:
    tk.messagebox.showerror(
        "Internal Error",
        f"Critical application files are missing or misplaced.\nError: {e}"
    )
    sys.exit(1)

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
OUTPUT_DIR_NAME = "chats"
DEFAULT_FILENAME = "chat.json"


OUTPUT_PATH = SCRIPT_DIR / OUTPUT_DIR_NAME

try:
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    print(f"Output directory established at: {OUTPUT_PATH}")
except OSError as e:
    print(f"Error creating directory {OUTPUT_PATH}: {e}")
    print(f"Falling back to script directory: {SCRIPT_DIR}")


class App:
    def __init__(self, _root):
        self.root = _root

        self.config_manager = ConfigManager()
        self.current_settings = self.config_manager.get_settings()
        self.safety_settings = self.config_manager.get_safety_settings()

        self.api_key = API_KEY

        self.dynamic_models = []

        self.gui = MainWindow(self.root, self, self.current_settings, dynamic_models=self.dynamic_models)

        if not self.api_key:
            key = self.check_api(self.root)
            if key is None:
                sys.exit(0)

            self.api_key = key
            try:
                with open(".env", "w") as f:
                    f.write(f"\nGEMINI_API_KEY=\"{key}\"\n")
            except OSError as e:
                print(f"Failed to write .env file: {e}")

        try:
            self.client = genai.Client(api_key=self.api_key)
            model_list = self.client.models.list()
            for model in model_list:
                if "generateContent" in model.supported_actions and model.name.startswith("models/gemini"):
                    self.dynamic_models.append(model.name.split('/')[-1])
        except ValueError as e:
            messagebox.showerror(
                "Initialization Error",
                f"API Key Initialization Failed. Check Key Format:\n{e}"
            )
            self.root.destroy()
            return
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error during client setup:\n{e}")
            self.root.destroy()
            sys.exit(1)


        self.chat_manager = ChatManager(
            client=self.client,
            response_callback=self.gui.on_response_received,
            settings=self.current_settings,
            safety_settings=self.safety_settings
        )

    @staticmethod
    def check_api(ref_root):
        while True:
            key = Dialog.ask_string(
                parent=ref_root,
                title="Gemini API Key",
                prompt="Enter your API Key:",
                show='*'
            )
            if key is None:
                return None

            try:
                _client = genai.Client(api_key=key)
                # test
                from google.genai.types import ListModelsConfig
                _ = list(_client.models.list(config=ListModelsConfig(page_size=1)))
                return key
            except APIError as e:
                if "API key not valid" in str(e) or "400" in str(e):
                    messagebox.showerror(title="Error", message="Invalid API Key")
                else:
                    messagebox.showerror(title="Error", message=f"API Error: {e}")
            except Exception as e:
                messagebox.showerror(
                    title="Error",
                    message=f"Unexpected error: {e}\nCheck your internet connection.")

    def process_input(self, text):
        self.chat_manager.process_input(text)

    def reload_settings(self):
        self.config_manager.load_config()
        self.current_settings = self.config_manager.get_settings()
        self.safety_settings = self.config_manager.get_safety_settings()
        self.gui.update_settings(self.current_settings)
        self.chat_manager.update_settings(self.current_settings, self.safety_settings)

    def restart_chat(self):
        self.gui.clear_text()
        self.gui.append_text("System: Session reset.\n", "system")
        self.chat_manager.init_chat()

    def save_chat(self, chatbox=None):
        from tkinter import filedialog

        success = False

        filepath = filedialog.asksaveasfilename(
            defaultextension = ".json",
            filetypes = [("JSON", "*.json")],
            initialfile = DEFAULT_FILENAME,
            initialdir = OUTPUT_PATH,
        )
        if filepath:
            msg, success = self.chat_manager.save_history(filepath)
            if chatbox is not None and success and chatbox.edit_modified():
                chatbox.edit_modified(False)
            self.gui.append_text(f"System: {msg}", "system" if success else "error")
        return success

    def load_chat(self):
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            filetypes = [("JSON", "*.json")],
            initialdir = OUTPUT_PATH,
        )
        if filepath:
            hist, msg, success = self.chat_manager.load_history(filepath)
            if success and hist:
                self.gui.clear_text()
                for c in hist:
                    if c.parts and c.parts[0].text:
                        role = "user" if c.role == 'user' else "ai"
                        self.gui.append_text(f"{'You' if role == 'user' else 'Gemini'}: {c.parts[0].text}", role)

    def on_closing(self, chatbox=None):
        if chatbox is not None and chatbox.edit_modified():
            prompt = messagebox.askyesnocancel(title="Closing?", message="Do you want to save chat history before closing?")
            if prompt:
                saved = self.save_chat()
                if saved:
                    self.root.destroy()
                    sys.exit(0)
                else:
                    return
            elif prompt is False:
                self.root.destroy()
                sys.exit(0)
            else:
                return
        else:
            self.root.destroy()
            sys.exit(0)


if __name__ == "__main__":
    # high DPI awareness, just because.
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except AttributeError:
        pass
    except OSError:
        pass

    root = ThemedTk(theme="arc")
    app = App(root)
    root.mainloop()

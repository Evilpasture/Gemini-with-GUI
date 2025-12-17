from typing import TYPE_CHECKING

if TYPE_CHECKING:
    def _(s: str) -> str: ...


import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import os
import sys



# --- Centralized Dependency Check ---
def check_dependencies():
    required = {
        'openai': 'openai',
        'dotenv': 'python-dotenv',
        'ttkthemes': 'ttkthemes'
    }
    missing = []
    for module, pip_name in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pip_name)

    if missing:
        warning_template = _("CRITICAL: Missing libraries: %s")
        missing_list_formatted = ', '.join(missing)
        print(warning_template % missing_list_formatted)

        run_template = _("Run: pip install %s")
        install_command = ' '.join(missing)
        print(run_template % install_command)

        sys.exit(1)


check_dependencies()

# Imports after check
from dotenv import load_dotenv, set_key
from openai import OpenAI, AuthenticationError, APIError
from ttkthemes import ThemedTk

# --- Internal Module Setup ---
SCRIPT_DIR = Path(getattr(sys, 'frozen', False) and sys.executable or __file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

# Consolidated imports to catch structural errors early
try:
    from core.config import ConfigManager

    config_manager = ConfigManager()
    settings = config_manager.get_settings()

    from core.i18n import setup_i18n
    setup_i18n(settings['language'])

    from core.ai_manager import ChatManager
    from ui.main_window import MainWindow
    from ui.dialog import Dialog
except ImportError as e:
    r = tk.Tk()
    r.withdraw()
    _error_template = _("Application files missing. Trace: %s")
    _output = f"{_error_template % e}\n{e}"
    messagebox.showerror(_("Internal Error"), _output)
    sys.exit(1)

load_dotenv()
OUTPUT_PATH = SCRIPT_DIR / "chats"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)


class App:
    def __init__(self, _root):
        self.root = _root
        self.config_manager = ConfigManager()

        # Load settings, just more efficiently because somehow I did call it not efficiently
        self.settings = self.config_manager.get_settings()
        self.safety = self.config_manager.get_safety_settings()

        self.api_key = os.getenv("GEMINI_API_KEY")

        # 1. Setup GUI (Pass empty model list first, populate later)
        self.gui = MainWindow(self.root, self, self.settings)

        # 2. Check API Key - 3. Init Client & Fetch Models
        while True:
            if not self.api_key:
                self.api_key = self.ask_api_key(self.root)
                if not self.api_key:
                    sys.exit(0)
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
                self.client.models.list()

                # Update .env without wiping other variables - just for the future
                set_key(".env", "GEMINI_API_KEY", self.api_key)
                break

            except AuthenticationError:
                print(_("Invalid API Key"))
                self.api_key = None
            except APIError as e:
                print(_("API Service Error: %s") % str(e))
                sys.exit(1)
            except Exception as e:
                _error_template = _("Failed to connect. Check your internet connection: %s")
                _output = _error_template % str(e)
                messagebox.showerror(_("Error"), _output)
                sys.exit(1)

        self.populate_models()

        # 4. Init Chat Manager
        self.chat_manager = ChatManager(
            self.client,
            self.gui.on_response_received,  # Callback
            self.settings,
            self.safety
        )

    def populate_models(self):
        # Fetch models dynamically, but it wouldn't screw up the entire program
        try:
            dynamic_models = []
            for m in self.client.models.list():
                if ("gemini" in m.id) and ("embedding" not in m.id):
                    clean_id = m.id.split('/')[-1]
                    if clean_id not in dynamic_models:
                        dynamic_models.append(clean_id)

            # Pass models to GUI for the settings dropdown
            self.gui.set_available_models(dynamic_models)
        except Exception as e:
            _output = _("Model list warning: %s" % e)
            print(_output)
            # Fallback defaults
            self.gui.set_available_models(["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"])

    @staticmethod
    def ask_api_key(parent):
        return Dialog.ask_string(parent, _("API Key Required"), _("Enter Google GenAI API Key:"), show="*")

    def process_input(self, text):
        self.chat_manager.process_input(text)

    def reload_settings(self):
        self.config_manager.load_config()
        self.settings = self.config_manager.get_settings()
        self.safety = self.config_manager.get_safety_settings()

        # Update GUI Theme/Fonts
        self.gui.update_settings(self.settings)
        # Update AI Logic
        self.chat_manager.update_settings(self.settings, self.safety)

    def restart_chat(self):
        self.gui.reset_ui()
        self.chat_manager.init_chat()

    def save_chat(self):
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir=OUTPUT_PATH
        )
        if filepath:
            msg, success = self.chat_manager.save_history(filepath)
            self.gui.append_system_msg(msg, success)

    def load_chat(self):
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(filetypes=[("JSON", "*.json")], initialdir=OUTPUT_PATH)
        if filepath:
            history, msg, success = self.chat_manager.load_history(filepath)
            if success:
                self.gui.render_history(history)
            else:
                self.gui.append_system_msg(msg, False)

    def on_closing(self):
        if self.gui.is_dirty():
            confirm = messagebox.askyesnocancel(_("Save?"), _("Save chat history before closing?"))
            if confirm:
                self.save_chat()
            elif confirm is None:
                return
        self.root.destroy()
        sys.exit(0)


if __name__ == "__main__":
    # high DPI awareness, just because.
    if sys.platform.startswith("win"):
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except (ImportError, AttributeError): # If you're using non-Windows...
            pass

    root = ThemedTk(theme="arc")
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

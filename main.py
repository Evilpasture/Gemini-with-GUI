import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import os
import sys


# --- Centralized Dependency Check ---
def check_dependencies():
    required = {
        'google.genai': 'google-genai',
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
        # We can't use tk.messagebox easily before root, but simple print/sys.exit is safer here
        print(f"CRITICAL: Missing libraries: {', '.join(missing)}")
        print(f"Run: pip install {' '.join(missing)}")
        sys.exit(1)


check_dependencies()

# Imports after check
from dotenv import load_dotenv
from google import genai
from ttkthemes import ThemedTk

# --- Internal Module Setup ---
SCRIPT_DIR = Path(getattr(sys, 'frozen', False) and sys.executable or __file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

# Consolidated imports to catch structural errors early
try:
    from core.config import ConfigManager
    from core.ai_manager import ChatManager
    from ui.main_window import MainWindow
    from ui.dialog import Dialog
except ImportError as e:
    # Minimal TK root just to show error
    r = tk.Tk()
    r.withdraw()
    messagebox.showerror("Internal Error", f"Application files missing.\nTrace: {e}")
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

        # 2. Check API Key
        if not self.api_key:
            self.api_key = self.ask_api_key(self.root)
            if not self.api_key:
                sys.exit(0)
            # Save to env for next time
            with open(".env", "w") as f:
                f.write(f"\nGEMINI_API_KEY=\"{self.api_key}\"\n")

        # 3. Init Client & Fetch Models
        try:
            self.client = genai.Client(api_key=self.api_key)
            self.populate_models()
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to connect to Gemini. Check your internet connections:\n{e}")
            sys.exit(1)

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
            # Note: Page size config might vary by SDK version, simplified listing:
            for m in self.client.models.list():
                # Filter for Gemini models that support generation
                if "gemini" in m.name and "generateContent" in m.supported_actions:
                    dynamic_models.append(m.name.split('/')[-1])

            # Pass models to GUI for the settings dropdown
            self.gui.set_available_models(dynamic_models)
        except Exception as e:
            print(f"Model list warning: {e}")
            # Fallback defaults
            self.gui.set_available_models(["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"])

    @staticmethod
    def ask_api_key(parent):
        return Dialog.ask_string(parent, "API Key Required", "Enter Google GenAI API Key:", show="*")

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

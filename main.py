import tkinter as tk
from tkinter import messagebox
import os
from dotenv import load_dotenv
from google import genai
from ttkthemes import ThemedTk
from core.config import ConfigManager
from core.ai_manager import ChatManager
from ui.main_window import MainWindow
from ui.settings import PreferencesWindow

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")


class App:
    def __init__(self, root):
        self.root = root

        self.config_manager = ConfigManager()
        self.current_settings = self.config_manager.get_settings()
        self.safety_settings = self.config_manager.get_safety_settings()

        if not API_KEY:
            messagebox.showerror("Error", "GEMINI_API_KEY not found.")
            self.root.destroy()
            return

        try:
            self.client = genai.Client(api_key=API_KEY)
        except Exception as e:
            messagebox.showerror("Error", f"Connection Error:\n{e}")
            self.root.destroy()
            return

        self.gui = MainWindow(self.root, self, self.current_settings)
        self.chat_manager = ChatManager(
            client=self.client,
            response_callback=self.gui.on_response_received,
            settings=self.current_settings,
            safety_settings=self.safety_settings
        )

    def process_input(self, text):
        self.chat_manager.process_input(text)

    def reload_settings(self, reset_default = None):
        if reset_default is not None:
            PreferencesWindow(self.root, self.config_manager.get_parser(), self.reload_settings)
        self.config_manager.load_config()
        self.current_settings = self.config_manager.get_settings()
        self.safety_settings = self.config_manager.get_safety_settings()
        self.gui.update_settings(self.current_settings)  # Theme update happens here
        self.chat_manager.update_settings(self.current_settings, self.safety_settings)

    def restart_chat(self):
        self.gui.clear_text()
        self.gui.append_text("System: Session reset.\n", "system")
        self.chat_manager.init_chat()

    def save_chat(self):
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if filepath:
            msg, success = self.chat_manager.save_history(filepath)
            self.gui.append_text(f"System: {msg}", "system" if success else "error")

    def load_chat(self):
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if filepath:
            hist, msg, success = self.chat_manager.load_history(filepath)
            if success and hist:
                self.gui.clear_text()
                for c in hist:
                    if c.parts and c.parts[0].text:
                        role = "user" if c.role == 'user' else "ai"
                        self.gui.append_text(f"{'You' if role == 'user' else 'Gemini'}: {c.parts[0].text}", role)

    def on_closing(self):
        if messagebox.askokcancel("Exit", "Exit application?"):
            self.root.destroy()


if __name__ == "__main__":
    #MainWindow will load the real theme from config, it's just a safe default
    root = ThemedTk(theme="arc")
    app = App(root)
    root.mainloop()

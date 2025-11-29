import tkinter as tk
from tkinter import messagebox
import os
import sys
from dotenv import load_dotenv
from google import genai

# Import our new modules
from core.config import ConfigManager
from core.ai_manager import ChatManager
from ui.main_window import MainWindow

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")


class App:
    def __init__(self, root):
        self.root = root

        # 1. Initialize Config
        self.config_manager = ConfigManager()
        self.current_settings = self.config_manager.get_settings()
        self.safety_settings = self.config_manager.get_safety_settings()

        # 2. Initialize API Client
        if not API_KEY:
            messagebox.showerror("Error", "GEMINI_API_KEY not found.")
            self.root.destroy()
            return

        try:
            self.client = genai.Client(api_key=API_KEY)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to Gemini:\n{e}")
            self.root.destroy()
            return

        # 3. Initialize GUI
        # We pass 'self' as the controller
        self.gui = MainWindow(self.root, self, self.current_settings)

        # 4. Initialize Logic
        # We pass the GUI's callback method so the Logic can update the UI safely
        self.chat_manager = ChatManager(
            client=self.client,
            response_callback=self.gui.on_response_received,  # Decoupled callback
            settings=self.current_settings,
            safety_settings=self.safety_settings
        )

    def process_input(self, text):
        """Bridge between GUI and Chat Logic"""
        self.chat_manager.process_input(text)

    def reload_settings(self):
        """Called when settings are saved in the UI"""
        # Reload config from file
        self.config_manager.load_config()
        self.current_settings = self.config_manager.get_settings()
        self.safety_settings = self.config_manager.get_safety_settings()

        # Update GUI
        self.gui.update_settings(self.current_settings)
        self.gui.append_text(
            f"System: Settings loaded. Model: {self.current_settings['model_name']}",
            "system"
        )

        # Update Chat Manager
        self.chat_manager.update_settings(self.current_settings, self.safety_settings)

    def restart_chat(self):
        self.gui.clear_text()
        self.gui.append_text("System: Chat history reset.\n", "system")
        self.chat_manager.init_chat()

    def save_chat(self):
        # We handle the file dialog here or in the GUI, then call the manager
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save Chat History"
        )
        if filepath:
            message, success = self.chat_manager.save_history(filepath)
            tag = "system" if success else "error"
            messagebox.showinfo("Save Status", message)
            self.gui.append_text(f"System: {message}", tag)

    def load_chat(self):
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Load Chat History"
        )
        if filepath:
            history, message, success = self.chat_manager.load_history(filepath)
            tag = "system" if success else "error"

            messagebox.showinfo("Load Status", message)
            self.gui.append_text(f"System: {message}", tag)

            if success and history:
                self.gui.clear_text()
                # Re-populate UI
                for content in history:
                    if content.parts and content.parts[0].text:
                        text = content.parts[0].text
                        role = content.role
                        if role == 'user':
                            self.gui.append_text(f"You: {text}", "user")
                        elif role == 'model':
                            self.gui.append_text(f"{self.current_settings['model_name']}:\n{text}", "ai")

    def on_closing(self):
        if messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

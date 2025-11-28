import tkinter as tk
import sys
import os
import threading
import configparser
import json
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
from google import genai
from google.genai.errors import APIError
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configuration Defaults
CONFIG_FILE = "config.ini"
DEFAULT_CONFIG = {
    'SETTINGS': {
        'MODEL_NAME': 'gemini-2.5-flash',
        'INSTRUCTION': 'You are a helpful AI assistant.',
        'STANDARD_FONT_NAME': 'Arial',
        'STANDARD_FONT_SIZE': '10',
        'TEMPERATURE': '0.7'
    }
}


class PreferencesWindow(tk.Toplevel):
    """
    Handles the UI and logic for modifying user settings.
    """

    def __init__(self, parent, config, on_save_callback):
        super().__init__(parent)
        self.config = config
        self.on_save_callback = on_save_callback

        self.title("Preferences")
        self.geometry("500x450")
        self.resizable(False, False)

        # -- UI Variables --
        self.var_model = tk.StringVar(value=self.config.get('SETTINGS', 'MODEL_NAME'))
        self.var_temp = tk.DoubleVar(value=self.config.getfloat('SETTINGS', 'TEMPERATURE'))
        self.var_font_size = tk.IntVar(value=self.config.getint('SETTINGS', 'STANDARD_FONT_SIZE'))
        # Text widget doesn't use StringVar, handled separately

        # -- Layout --
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, expand=True, fill='both')

        self.tab_ai = ttk.Frame(self.notebook, padding="20")
        self.tab_files = ttk.Frame(self.notebook, padding="20")

        self.notebook.add(self.tab_ai, text="AI Behavior")
        self.notebook.add(self.tab_files, text="System & Files")

        self.txt_instruct = None

        self.build_ai_tab()
        self.build_system_tab()

        # -- Action Buttons --
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        ttk.Button(btn_frame, text="Save & Apply", command=self.save_changes).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")

    def build_ai_tab(self):
        # Model Name
        ttk.Label(self.tab_ai, text="Model Name:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(self.tab_ai, textvariable=self.var_model, width=30).grid(row=0, column=1, sticky="w", pady=5)
        ttk.Label(self.tab_ai, text="(e.g., gemini-2.0-flash, gemini-1.5-pro)", font=("Arial", 8, "italic")).grid(row=1,
                                                                                                                  column=1,
                                                                                                                  sticky="w")

        # Temperature
        ttk.Label(self.tab_ai, text="Temperature (Creativity):").grid(row=2, column=0, sticky="w", pady=(20, 5))

        temp_frame = ttk.Frame(self.tab_ai)
        temp_frame.grid(row=2, column=1, sticky="w", pady=(20, 5))

        scale = ttk.Scale(temp_frame, from_=0.0, to=2.0, variable=self.var_temp, orient="horizontal", length=200)
        scale.pack(side="left")
        lbl_val = ttk.Label(temp_frame, text=f"{self.var_temp.get():.1f}")
        lbl_val.pack(side="left", padx=5)

        # Live update label on slide
        scale.configure(command=lambda v: lbl_val.configure(text=f"{float(v):.1f}"))

        # System Instructions
        ttk.Label(self.tab_ai, text="System Instructions:").grid(row=3, column=0, sticky="nw", pady=(20, 5))
        self.txt_instruct = tk.Text(self.tab_ai, height=5, width=30, font=("Arial", 9))
        self.txt_instruct.grid(row=3, column=1, sticky="w", pady=(20, 5))

        # Load current instruction
        current_instr = self.config.get('SETTINGS', 'INSTRUCTION', fallback='')
        self.txt_instruct.insert("1.0", current_instr)

    def build_system_tab(self):
        # Font Size
        ttk.Label(self.tab_files, text="Font Size:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Spinbox(self.tab_files, from_=8, to=24, textvariable=self.var_font_size, width=5).grid(row=0, column=1,
                                                                                                   sticky="w", pady=5)

        ttk.Label(self.tab_files, text="Note: Requires restart to fully apply UI scaling.", font=("Arial", 8, "italic"),
                  foreground="gray").grid(row=1, column=0, columnspan=2, sticky="w")

    def save_changes(self):
        # 1. Update Config Object
        if not self.config.has_section('SETTINGS'):
            self.config.add_section('SETTINGS')

        self.config.set('SETTINGS', 'MODEL_NAME', self.var_model.get().strip())
        self.config.set('SETTINGS', 'TEMPERATURE', f"{self.var_temp.get():.1f}")
        self.config.set('SETTINGS', 'STANDARD_FONT_SIZE', str(self.var_font_size.get()))
        self.config.set('SETTINGS', 'INSTRUCTION', self.txt_instruct.get("1.0", "end-1c").strip())

        # 2. Write to File
        try:
            with open(CONFIG_FILE, 'w') as configfile:
                self.config.write(configfile)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save config.ini: {e}")
            return

        # 3. Trigger App Callback
        self.on_save_callback()
        self.destroy()


class GUI:
    def __init__(self, _root, controller, settings):
        self.root = _root
        self.controller = controller
        self.settings = settings  # Now receives settings dictionary

        self.root.geometry("800x600")
        self.update_title()

        # Styles
        self.font_spec = (self.settings['font_name'], self.settings['font_size'])

        # Menu bar
        self.menubar = tk.Menu(self.root)

        self.chat_menu = tk.Menu(self.menubar, tearoff=0)
        self.chat_menu.add_command(label="Clear Chat", command=self.clear_text)
        self.chat_menu.add_command(label="Reset Session", command=self.controller.restart_chat)
        self.chat_menu.add_separator()

        self.chat_menu.add_command(label="Save Chat...", command=self.controller.save_chat)
        self.chat_menu.add_command(label="Load Chat...", command=self.controller.load_chat)
        self.chat_menu.add_separator()

        self.chat_menu.add_command(label="Exit", command=self.controller.on_closing)

        self.tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.tools_menu.add_command(label="Preferences", command=self.show_options)

        self.menubar.add_cascade(menu=self.chat_menu, label="Chat")
        self.menubar.add_cascade(menu=self.tools_menu, label="Tools")

        self.root.config(menu=self.menubar)

        # Grid layout
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Main Container
        self.frame = ttk.Frame(self.root, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=0)

        # Chat History
        self.text_container = ttk.Frame(self.frame)
        self.text_container.grid(column=0, row=0, sticky="nsew", pady=(0, 10))
        self.text_container.columnconfigure(0, weight=1)
        self.text_container.rowconfigure(0, weight=1)

        self.scrollbar = ttk.Scrollbar(self.text_container)
        self.scrollbar.grid(column=1, row=0, sticky="ns")

        self.textbox = tk.Text(
            self.text_container,
            height=20,
            state="disabled",
            wrap="word",
            yscrollcommand=self.scrollbar.set,
            font=self.font_spec
        )
        self.textbox.tag_config("user", foreground="blue",
                                font=(self.settings['font_name'], self.settings['font_size'], "bold"))
        self.textbox.tag_config("ai", foreground="#006400", font=self.font_spec)
        self.textbox.tag_config("error", foreground="red", font=self.font_spec)
        self.textbox.tag_config("system", foreground="gray",
                                font=(self.settings['font_name'], int(self.settings['font_size']) - 2, "italic"))
        self.textbox.grid(column=0, row=0, sticky="nsew")

        self.scrollbar.config(command=self.textbox.yview)

        # Input Area
        self.input_frame = ttk.Frame(self.frame)
        self.input_frame.grid(column=0, row=1, sticky="ew")
        self.input_frame.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(self.input_frame, font=self.font_spec)
        self.entry.grid(column=0, row=0, sticky="ew", padx=(0, 5))
        self.entry.bind('<Return>', lambda event: self.handle_submit())

        self.button = ttk.Button(self.input_frame, text="Send", command=self.handle_submit)
        self.button.grid(column=1, row=0, sticky="e")

        # Status Label
        self.status_label = ttk.Label(self.frame, text="Ready", font=("Arial", 8))
        self.status_label.grid(row=2, column=0, sticky="w", pady=(5, 0))

        self.root.protocol("WM_DELETE_WINDOW", self.controller.on_closing)

    def update_title(self):
        self.root.title(f"Client: {self.settings['model_name']} (Temp: {self.settings['temperature']})")

    def update_settings(self, new_settings):
        """Called when settings change to update UI elements immediately where possible"""
        self.settings = new_settings
        self.font_spec = (self.settings['font_name'], self.settings['font_size'])
        self.textbox.configure(font=self.font_spec)
        self.entry.configure(font=self.font_spec)
        self.update_title()

    def show_options(self):
        # Open the new PreferencesWindow class
        PreferencesWindow(self.root, self.controller.config_parser, self.controller.reload_settings)

    def handle_submit(self):
        text = self.entry.get()
        if not text.strip():
            return

        self.entry.delete(0, tk.END)
        self.append_text(f"You: {text}\n", "user")

        self.entry.config(state="disabled")
        self.button.config(state="disabled")
        self.status_label.config(text="Thinking...")

        self.controller.process_input(text)

    def clear_text(self):
        self.textbox.configure(state="normal")
        self.textbox.delete('1.0', tk.END)
        self.textbox.configure(state="disabled")

    def append_text(self, text, tag):
        self.textbox.configure(state="normal")
        self.textbox.insert(tk.END, text + "\n", tag)
        self.textbox.configure(state="disabled")
        self.textbox.see(tk.END)

    def on_response_received(self, response_text, is_error=False):
        tag = "error" if is_error else "ai"
        header = "Error: " if is_error else f"{self.settings['model_name']}: "

        self.append_text(f"{header}\n{response_text}\n", tag)

        self.entry.config(state="normal")
        self.button.config(state="normal")
        self.status_label.config(text="Ready")
        self.entry.focus()


class ChatManager:
    def __init__(self, client, gui_ref, settings):
        self.client = client
        self.gui = gui_ref
        self.settings = settings
        self.chat_config = None
        self.chat = None
        self.init_chat()

    def init_chat(self, history=None):
        """Initializes or Re-initializes the chat session with current settings."""
        try:
            self.chat_config = types.GenerateContentConfig(
                system_instruction=self.settings['instruction'],
                temperature=self.settings['temperature']
            )
            self.chat = self.client.chats.create(
                model=self.settings['model_name'],
                config=self.chat_config,
                history=history
            )
        except Exception as e:
            # Don't exit app, just log error to GUI if possible, or console
            print(f"Chat Init Error: {e}")
            self.gui.append_text(
                f"System Error: Failed to initialize model {self.settings['model_name']}. Check API key or Model Name.\n",
                "error")

    def save_history(self, filepath):
        """Saves the current chat history to a JSON file."""
        if not self.chat:
            return "Error: No active chat session to save.", False

        try:
            # The chat history is a list of Content objects
            history_list = [h.to_dict() for h in self.chat.history]

            with open(filepath, 'w') as f:
                json.dump(history_list, f, indent=4)

            return f"Chat history saved to {filepath}", True
        except Exception as e:
            return f"Save Error: {e}", False

    def load_history(self, filepath):
        """Loads chat history from a JSON file and starts a new session."""
        try:
            with open(filepath, 'r') as f:
                history_data = json.load(f)

            # The loaded data is a list of dictionaries (Content objects)
            # We need to convert these back to Content objects
            loaded_history = [types.Content.from_dict(d) for d in history_data]

            # Re-initialize the chat session with the loaded history
            self.init_chat(history=loaded_history)

            # Return history for GUI to display
            return loaded_history, f"Chat history loaded from {filepath}", True

        except FileNotFoundError:
            return None, "Error: File not found.", False
        except json.JSONDecodeError:
            return None, "Error: Invalid chat history file format (JSON decode error).", False
        except Exception as e:
            return None, f"Load Error: {e}", False

    def process_input(self, user_text):
        thread = threading.Thread(target=self._run_api_call, args=(user_text,))
        thread.daemon = True
        thread.start()

    def _run_api_call(self, text):
        if not self.chat:
            self.gui.root.after(0, self.gui.on_response_received, "Chat session not initialized.", True)
            return

        try:
            response = self.chat.send_message(text)
            result_text = response.text
            is_error = False
        except APIError as e:
            result_text = f"API Error {e.code}: {e.message}"
            is_error = True
        except Exception as e:
            result_text = f"Unexpected Error: {str(e)}"
            is_error = True

        self.gui.root.after(0, self.gui.on_response_received, result_text, is_error)


class App:
    def __init__(self, _root):
        self.root = _root
        self.current_settings = None
        self.config_parser = configparser.ConfigParser()
        self.load_config()

        if not API_KEY:
            messagebox.showerror("Error", "GEMINI_API_KEY not found in environment variables.")
            self.root.destroy()
            return

        try:
            self.client = genai.Client(api_key=API_KEY)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to Gemini:\n{e}")
            self.root.destroy()
            return

        # Initialize GUI with current settings
        self.gui = GUI(self.root, self, self.current_settings)

        # Initialize Logic
        self.chat_manager = ChatManager(self.client, self.gui, self.current_settings)

    def load_config(self):
        """Loads config.ini or creates it if missing."""
        if not os.path.exists(CONFIG_FILE):
            for section, options in DEFAULT_CONFIG.items():
                self.config_parser[section] = options
            with open(CONFIG_FILE, 'w') as f:
                self.config_parser.write(f)
        else:
            self.config_parser.read(CONFIG_FILE)

        # Parse into a clean dictionary for easier usage
        self.current_settings = {
            'model_name': self.config_parser.get('SETTINGS', 'MODEL_NAME', fallback='gemini-2.5-flash'),
            'instruction': self.config_parser.get('SETTINGS', 'INSTRUCTION', fallback=''),
            'font_name': self.config_parser.get('SETTINGS', 'STANDARD_FONT_NAME', fallback='Arial'),
            'font_size': self.config_parser.getint('SETTINGS', 'STANDARD_FONT_SIZE', fallback=10),
            'temperature': self.config_parser.getfloat('SETTINGS', 'TEMPERATURE', fallback=0.5),
        }

    def reload_settings(self):
        """Called by PreferencesWindow to apply changes."""
        self.load_config()

        # Update GUI Look
        self.gui.update_settings(self.current_settings)
        self.gui.append_text(
            f"System: Settings loaded. Using {self.current_settings['model_name']} (T={self.current_settings['temperature']})\n",
            "system")

        # Re-init Chat Manager with new model/temp
        self.chat_manager = ChatManager(self.client, self.gui, self.current_settings)

    def process_input(self, text):
        self.chat_manager.process_input(text)

    def restart_chat(self):
        self.gui.clear_text()
        self.gui.append_text("System: Chat history reset.\n", "system")
        self.chat_manager.init_chat()

    def save_chat(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Chat History"
        )
        if filepath:
            message, success = self.chat_manager.save_history(filepath)
            tag = "system" if success else "error"
            messagebox.showinfo("Save Status", message)
            self.gui.append_text(f"System: {message}", tag)

    def load_chat(self):
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
                # Clear the existing display
                self.gui.clear_text()

                # Re-display the loaded history
                for content in history:
                    # Determine if the content part is text and assign role/tag
                    if content.parts and content.parts[0].text:
                        text = content.parts[0].text
                        role = content.role

                        if role == 'user':
                            self.gui.append_text(f"You: {text}", "user")
                        elif role == 'model':
                            self.gui.append_text(f"{self.current_settings['model_name']}:\n{text}", "ai")
                        # Skip system messages or other complex parts for simplicity

                self.gui.append_text(f"System: Chat session re-established with {len(history)} messages.", "system")

    def on_closing(self):
        if tk.messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
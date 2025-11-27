import tkinter as tk
import sys
import os
import threading
from tkinter import ttk
from tkinter import messagebox
from google import genai
from google.genai.errors import APIError
from dotenv import load_dotenv


load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configuration
MODEL_NAME = "gemini-2.5-flash"
STANDARD_FONT = ("Arial", 12)
INSTRUCTION = "Keep responses concise and chat-length."


class GUI:
    def __init__(self, _root, controller):
        self.root = _root
        self.controller = controller

        self.root.geometry("800x600")
        self.root.title(f"Client: {MODEL_NAME}")

        # Menu bar
        self.menubar = tk.Menu(self.root)

        self.chat_menu = tk.Menu(self.menubar, tearoff=0)
        self.chat_menu.add_command(
            label="Close",
            command=self.controller.on_closing
        )
        self.chat_menu.add_separator()
        self.chat_menu.add_command(
            label="Reset",
            command=self.controller.restart_chat
        )

        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.help_menu.add_command(
            label="About",
            command=self.controller.on_about
        )
        self.help_menu.add_separator()
        self.help_menu.add_command(
            label="License",
            command=self.controller.show_license
        )

        self.menubar.add_cascade(menu=self.chat_menu, label="Chat")
        self.menubar.add_cascade(menu=self.help_menu, label="Help")

        self.root.config(menu=self.menubar)

        # Grid layout for root
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Main Container
        self.frame = ttk.Frame(self.root, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)  # Text area expands
        self.frame.rowconfigure(1, weight=0)  # Entry area stays small

        # Chat History (Text Area)
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
            font=STANDARD_FONT
        )
        self.textbox.tag_config("user", foreground="blue", font=("Arial", 12, "bold"))
        self.textbox.tag_config("ai", foreground="#006400", font=STANDARD_FONT)  # Dark Green
        self.textbox.tag_config("error", foreground="red", font=STANDARD_FONT)
        self.textbox.grid(column=0, row=0, sticky="nsew")

        self.scrollbar.config(command=self.textbox.yview)

        # Input Area
        self.input_frame = ttk.Frame(self.frame)
        self.input_frame.grid(column=0, row=1, sticky="ew")
        self.input_frame.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(self.input_frame, font=STANDARD_FONT)
        self.entry.grid(column=0, row=0, sticky="ew", padx=(0, 5))
        # Bind Enter only to the entry box, not the whole window
        self.entry.bind('<Return>', lambda event: self.handle_submit())

        self.button = ttk.Button(self.input_frame, text="Send", command=self.handle_submit)
        self.button.grid(column=1, row=0, sticky="e")

        # Status Label (Loading indicator)
        self.status_label = ttk.Label(self.frame, text="Ready", font=("Arial", 8))
        self.status_label.grid(row=2, column=0, sticky="w", pady=(5, 0))

        self.root.protocol("WM_DELETE_WINDOW", self.controller.on_closing)

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
        header = "Error: " if is_error else f"{MODEL_NAME}: "

        self.append_text(f"{header}\n{response_text}\n", tag)

        # Re-enable UI
        self.entry.config(state="normal")
        self.button.config(state="normal")
        self.status_label.config(text="Ready")
        self.entry.focus()


class ChatManager:
    def __init__(self, client, gui_ref):
        self.client = client
        self.gui = gui_ref
        try:
            self.chat = self.client.chats.create(
                model=MODEL_NAME,
                config={'system_instruction': INSTRUCTION}
            )
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to create chat session: {e}")
            sys.exit(1)

    def process_input(self, user_text):
        thread = threading.Thread(target=self._run_api_call, args=(user_text,))
        thread.daemon = True  # Thread dies if app closes
        thread.start()

    def _run_api_call(self, text):
        try:
            response = self.chat.send_message(text)
            result_text = response.text
            is_error = False
        except APIError as e:
            # ### FIX: Robust error handling for the API call.
            result_text = f"API Error {e.status_code}: {e.message}"
            is_error = True
        except Exception as e:
            result_text = f"Unexpected Error: {str(e)}"
            is_error = True

        self.gui.root.after(0, self.gui.on_response_received, result_text, is_error)


class App:
    def __init__(self, _root):
        self.root = _root

        # 1. Initialize API Client
        if not API_KEY:
            messagebox.showerror("Error", "GEMINI_API_KEY not found in environment variables.")
            root.destroy()
            return

        try:
            self.client = genai.Client(api_key=API_KEY)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to Gemini:\n{e}")
            root.destroy()
            return

        # 2. Setup GUI
        self.gui = GUI(root, self)

        # 3. Setup Logic
        self.chat_manager = ChatManager(self.client, self.gui)

    def process_input(self, text):
        # Bridge between GUI and Logic
        self.chat_manager.process_input(text)

    def restart_chat(self): # stub
        # Clear GUI
        self.gui.clear_text()
        self.gui.append_text("System: Chat history has been reset.\n", "system")

        # Re-initialize Chat Manager (creates new session)
        self.chat_manager = ChatManager(self.client, self.gui)
        self.gui.status_label.config(text="Chat Reset")

    def on_closing(self):
        if tk.messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            self.root.destroy()

    @staticmethod
    def on_about():
        try:
            with open("README.md", "r") as f:
                about = f.read()
            tk.messagebox.showinfo("About", about)
        except FileNotFoundError as e:
            tk.messagebox.showerror("About", f"{e.filename} not found.")

    @staticmethod
    def show_license():
        try:
            with open("LICENSE", "r") as f:
                _license = f.read()
            tk.messagebox.showinfo("License", _license)
        except FileNotFoundError as e:
            tk.messagebox.showerror("License", f"{e.filename} not found.")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

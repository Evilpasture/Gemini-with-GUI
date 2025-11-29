import tkinter as tk
from tkinter import ttk
from .settings import PreferencesWindow


class MainWindow:
    def __init__(self, root, controller, settings):
        self.root = root
        self.controller = controller
        self.settings = settings

        self.root.geometry("800x600")
        self.update_title()
        self.font_spec = (self.settings['font_name'], self.settings['font_size'])

        self._build_menu()
        self._build_layout()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.controller.on_closing)

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        chat_menu = tk.Menu(menubar, tearoff=0)
        chat_menu.add_command(label="Clear Chat", command=self.clear_text)
        chat_menu.add_command(label="Reset Session", command=self.controller.restart_chat)
        chat_menu.add_separator()
        chat_menu.add_command(label="Save Chat...", command=self.controller.save_chat)
        chat_menu.add_command(label="Load Chat...", command=self.controller.load_chat)
        chat_menu.add_separator()
        chat_menu.add_command(label="Exit", command=self.controller.on_closing)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Preferences", command=self.show_options)

        menubar.add_cascade(menu=chat_menu, label="Chat")
        menubar.add_cascade(menu=tools_menu, label="Tools")
        self.root.config(menu=menubar)

    def _build_layout(self):
        # Main Frame
        frame = ttk.Frame(self.root, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        # Text Area
        self.text_container = ttk.Frame(frame)
        self.text_container.grid(column=0, row=0, sticky="nsew", pady=(0, 10))
        self.text_container.columnconfigure(0, weight=1)
        self.text_container.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(self.text_container)
        scrollbar.grid(column=1, row=0, sticky="ns")

        self.textbox = tk.Text(
            self.text_container, height=20, state="disabled", wrap="word",
            yscrollcommand=scrollbar.set, font=self.font_spec
        )
        self.textbox.grid(column=0, row=0, sticky="nsew")
        scrollbar.config(command=self.textbox.yview)

        # Tags
        self.textbox.tag_config("user", foreground="blue",
                                font=(self.settings['font_name'], self.settings['font_size'], "bold"))
        self.textbox.tag_config("ai", foreground="#006400", font=self.font_spec)
        self.textbox.tag_config("error", foreground="red", font=self.font_spec)
        self.textbox.tag_config("system", foreground="gray",
                                font=(self.settings['font_name'], int(self.settings['font_size']) - 2, "italic"))

        # Input Area
        input_frame = ttk.Frame(frame)
        input_frame.grid(column=0, row=1, sticky="ew")
        input_frame.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(input_frame, font=self.font_spec)
        self.entry.grid(column=0, row=0, sticky="ew", padx=(0, 5))
        self.entry.bind('<Return>', lambda event: self.handle_submit())

        self.button = ttk.Button(input_frame, text="Send", command=self.handle_submit)
        self.button.grid(column=1, row=0, sticky="e")

        # Status
        self.status_label = ttk.Label(frame, text="Ready", font=("Arial", 8))
        self.status_label.grid(row=2, column=0, sticky="w", pady=(5, 0))

    def update_title(self):
        self.root.title(f"Client: {self.settings['model_name']} (Temp: {self.settings['temperature']})")

    def update_settings(self, new_settings):
        self.settings = new_settings
        self.font_spec = (self.settings['font_name'], self.settings['font_size'])
        self.textbox.configure(font=self.font_spec)
        self.entry.configure(font=self.font_spec)
        self.update_title()

    def show_options(self):
        # We need the raw parser from the controller's config manager
        parser = self.controller.config_manager.get_parser()
        PreferencesWindow(self.root, parser, self.controller.reload_settings)

    def handle_submit(self):
        text = self.entry.get()
        if not text.strip(): return

        self.entry.delete(0, tk.END)
        self.append_text(f"{self.settings['user_name']}: {text}\n", "user")

        self.entry.config(state="disabled")
        self.button.config(state="disabled")
        self.status_label.config(text="Thinking...")

        self.controller.process_input(text)

    def on_response_received(self, response_text, is_error=False):
        # Thread safety: Ensure this runs on main thread
        self.root.after(0, lambda: self._update_ui_after_response(response_text, is_error))

    def _update_ui_after_response(self, response_text, is_error):
        tag = "error" if is_error else "ai"
        header = "Error: " if is_error else f"{self.settings['chatbot_name']}: "
        self.append_text(f"{header}\n{response_text}\n", tag)

        self.entry.config(state="normal")
        self.button.config(state="normal")
        self.status_label.config(text="Ready")
        self.entry.focus()

    def append_text(self, text, tag):
        self.textbox.configure(state="normal")
        self.textbox.insert(tk.END, text + "\n", tag)
        self.textbox.configure(state="disabled")
        self.textbox.see(tk.END)

    def clear_text(self):
        self.textbox.configure(state="normal")
        self.textbox.delete('1.0', tk.END)
        self.textbox.configure(state="disabled")

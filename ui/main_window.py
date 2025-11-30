import tkinter as tk
from tkinter import ttk
from .settings import PreferencesWindow

# Enhanced palettes... but I won't add dark mode, it's bloody hard.
THEME_ACCENTS = {
    "arc": {
        "highlight": "#5294e2",  # Blue
        "user_text": "#0056b3",
        "hover": "#e6e6e6"
    },
    "yaru": {
        "highlight": "#e95420",  # Orange
        "user_text": "#e95420",
        "hover": "#f7f7f7"
    },
    "breeze": {
        "highlight": "#3daee9",  # Cyan-Blue
        "user_text": "#3daee9",
        "hover": "#dcecfb"
    },
    "radiance": {
        "highlight": "#f69c55",  # Warm Orange
        "user_text": "#f69c55",
        "hover": "#fdf0e3"
    },
    "plastik": {
        "highlight": "#3c81c9",  # Classic Blue
        "user_text": "#3c81c9",
        "hover": "#d9e8f7"
    },
}


class MainWindow:
    def __init__(self, root, controller, settings):
        self.root = root
        self.controller = controller
        self.settings = settings

        self.root.geometry("850x650")

        # 1. Apply Initial Theme
        target_theme = self.settings.get('theme', 'arc')
        try:
            self.root.set_theme(target_theme)
        except Exception as e:
            print(f"Theme '{target_theme}' not found. {e}")
            self.root.set_theme('arc')

        self.update_title()
        self.font_spec = (self.settings['font_name'], self.settings['font_size'])

        self._build_menu()
        self._build_layout()

        # 2. Force apply colors
        self._apply_theme_colors(target_theme)

        self.root.protocol("WM_DELETE_WINDOW", self.controller.on_closing)

    def _build_menu(self):
        self.menubar = tk.Menu(self.root)

        # 1. Save references to sub-menus (self.file_menu) to change colors later
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="New Session", command=self.controller.restart_chat)
        self.file_menu.add_command(label="Clear Output", command=self.clear_text)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save History...", command=self.controller.save_chat)
        self.file_menu.add_command(label="Load History...", command=self.controller.load_chat)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.controller.on_closing)
        self.menubar.add_cascade(label="File", menu=self.file_menu)

        self.tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.tools_menu.add_command(label="Preferences...", command=self.show_options)
        self.menubar.add_cascade(label="Tools", menu=self.tools_menu)

        self.root.config(menu=self.menubar)

    def _build_layout(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill="both", expand=True)

        # Text Area
        self.text_frame = ttk.Frame(main_frame)
        self.text_frame.pack(side="top", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.text_frame)
        scrollbar.pack(side="right", fill="y")

        self.textbox = tk.Text(
            self.text_frame,
            height=20, width=50,
            state="disabled", wrap="word",
            yscrollcommand=scrollbar.set, font=self.font_spec,
            bg="#ffffff", fg="#333333",
            bd=1, relief="solid", padx=15, pady=15,
            highlightthickness=0
        )
        self.textbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.textbox.yview)

        # Input Area
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(side="bottom", fill="x", pady=(15, 0))

        self.entry = ttk.Entry(input_frame, font=self.font_spec)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry.bind('<Return>', lambda event: self.handle_submit())

        self.btn_send = ttk.Button(input_frame, text="Send Message", command=self.handle_submit)
        self.btn_send.pack(side="right")

        self.status_label = ttk.Label(main_frame, text="Ready", font=("Arial", 9), foreground="gray")
        self.status_label.pack(side="bottom", anchor="w", pady=(5, 0))

        self._configure_tags("#0056b3")

    def _configure_tags(self, theme_color):
        self.textbox.tag_config("user", foreground=theme_color, font=(self.font_spec[0], self.font_spec[1], "bold"))
        self.textbox.tag_config("ai", foreground="#28a745", font=self.font_spec)
        self.textbox.tag_config("error", foreground="#dc3545", font=self.font_spec)
        self.textbox.tag_config("system", foreground="#6c757d",
                                font=(self.font_spec[0], int(self.font_spec[1]) - 1, "italic"))

    def _apply_theme_colors(self, theme_name):
        colors = THEME_ACCENTS.get(theme_name, THEME_ACCENTS["arc"])

        # 1. Update Text Selection
        self.textbox.configure(
            selectbackground=colors["highlight"],
            selectforeground="#ffffff"
        )

        # 2. Update User Tag
        self._configure_tags(colors["user_text"])

        # 3. Update Menu Colors (Cascading Menus)
        # Menus are standard Tk widgets, they don't auto-update with TTK themes perfectly.
        # We must explicitly set the active_background (hover color).
        for menu in [self.file_menu, self.tools_menu]:
            menu.configure(
                activebackground=colors["highlight"],
                activeforeground="#ffffff",
                # Neutral background
                bg="#f0f0f0",
                fg="#000000"
            )

        # 4. Update TTK Button Maps
        style = ttk.Style()
        style.map("TButton",
                  background=[("active", colors["hover"])],
                  foreground=[("active", "#000000")]
                  )
        style.map("TEntry",
                  fieldbackground=[("active", "#ffffff"), ("!disabled", "#ffffff")],
                  bordercolor=[("focus", colors["highlight"])]
                  )

    def update_settings(self, new_settings):
        self.settings = new_settings
        self.font_spec = (self.settings['font_name'], self.settings['font_size'])
        self.textbox.configure(font=self.font_spec)
        self.entry.configure(font=self.font_spec)

        new_theme = self.settings.get('theme', 'arc')
        current_theme = ttk.Style().theme_use()

        if new_theme != current_theme:
            try:
                self.root.set_theme(new_theme)
            except Exception as e:
                print(f"Error switching theme: {e}")

        # Re-apply colors (fixes menus, buttons, text)
        self._apply_theme_colors(new_theme)

        self.update_title()

    def update_title(self):
        self.root.title(f"AI Assistant - {self.settings['model_name']}")

    def show_options(self):
        PreferencesWindow(self.root, self.controller.config_manager.get_parser(), self.controller.reload_settings)

    def handle_submit(self):
        text = self.entry.get()
        if not text.strip(): return
        self.entry.delete(0, tk.END)
        self.append_text(f"You: {text}\n", "user")
        self.entry.config(state="disabled")
        self.btn_send.config(state="disabled")
        self.status_label.config(text="Thinking...")
        self.controller.process_input(text)

    def on_response_received(self, response_text, is_error=False):
        self.root.after(0, lambda: self._update_ui_after_response(response_text, is_error))

    def _update_ui_after_response(self, response_text, is_error):
        tag = "error" if is_error else "ai"
        name = self.settings['chatbot_name']
        self.append_text(f"{name}: {response_text}\n", tag)
        self.entry.config(state="normal")
        self.btn_send.config(state="normal")
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

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from core.config import CONFIG_FILE, THRESHOLD_MAP


class PreferencesWindow(tk.Toplevel):
    def __init__(self, parent, config_parser, on_save_callback):
        super().__init__(parent)
        self.config = config_parser
        self.on_save_callback = on_save_callback

        self.title("Preferences")
        self.geometry("500x450")
        self.resizable(False, False)

        # -- UI Variables --
        self.var_model = tk.StringVar(value=self.config.get('SETTINGS', 'MODEL_NAME'))
        self.var_temp = tk.DoubleVar(value=self.config.getfloat('SETTINGS', 'TEMPERATURE'))
        self.var_user_name = tk.StringVar(value=self.config.get('SETTINGS', 'USER_NAME'))
        self.var_chatbot_name = tk.StringVar(value=self.config.get('SETTINGS', 'CHATBOT_NAME'))
        self.var_font_size = tk.IntVar(value=self.config.getint('SETTINGS', 'STANDARD_FONT_SIZE'))

        # -- Layout --
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, expand=True, fill='both')

        self.tab_ai = ttk.Frame(self.notebook, padding="20")
        self.tab_files = ttk.Frame(self.notebook, padding="20")

        self.notebook.add(self.tab_ai, text="AI Behavior")
        self.notebook.add(self.tab_files, text="System & Files")

        self.build_ai_tab()
        self.build_system_tab()

        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        ttk.Button(btn_frame, text="Save & Apply", command=self.save_changes).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")

    def build_ai_tab(self):
        ttk.Label(self.tab_ai, text="Model Name:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(self.tab_ai, textvariable=self.var_model, width=30).grid(row=0, column=1, sticky="w", pady=5)

        ttk.Label(self.tab_ai, text="Temperature:").grid(row=2, column=0, sticky="w", pady=(20, 5))
        scale = ttk.Scale(self.tab_ai, from_=0.0, to=2.0, variable=self.var_temp, orient="horizontal", length=200)
        scale.grid(row=2, column=1, sticky="w", pady=(20, 5))

        ttk.Label(self.tab_ai, text="User Name:").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(self.tab_ai, textvariable=self.var_user_name, width=30).grid(row=3, column=1, sticky="w", pady=5)

        ttk.Label(self.tab_ai, text="Chatbot Name:").grid(row=4, column=0, sticky="w", pady=5)
        ttk.Entry(self.tab_ai, textvariable=self.var_chatbot_name, width=30).grid(row=4, column=1, sticky="w", pady=5)

        ttk.Label(self.tab_ai, text="System Instructions:").grid(row=5, column=0, sticky="nw", pady=(20, 5))
        self.txt_instruct = tk.Text(self.tab_ai, height=5, width=30, font=("Arial", 9))
        self.txt_instruct.grid(row=5, column=1, sticky="w", pady=(20, 5))
        self.txt_instruct.insert("1.0", self.config.get('SETTINGS', 'INSTRUCTION', fallback=''))

        ttk.Button(self.tab_ai, text="Advanced...", command=self.open_advanced).grid(row=6, column=0, sticky="w",
                                                                                     pady=5)

    def build_system_tab(self):
        ttk.Label(self.tab_files, text="Font Size:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Spinbox(self.tab_files, from_=8, to=24, textvariable=self.var_font_size, width=5).grid(row=0, column=1,
                                                                                                   sticky="w", pady=5)

    def open_advanced(self):
        AdvancedSettings(self, self.config)

    def save_changes(self):
        if not self.config.has_section('SETTINGS'): self.config.add_section('SETTINGS')
        self.config.set('SETTINGS', 'MODEL_NAME', self.var_model.get().strip())
        self.config.set('SETTINGS', 'TEMPERATURE', f"{self.var_temp.get():.1f}")
        self.config.set('SETTINGS', 'STANDARD_FONT_SIZE', str(self.var_font_size.get()))
        self.config.set('SETTINGS', 'USER_NAME', self.var_user_name.get().strip())
        self.config.set('SETTINGS', 'CHATBOT_NAME', self.var_chatbot_name.get().strip())
        self.config.set('SETTINGS', 'INSTRUCTION', self.txt_instruct.get("1.0", "end-1c").strip())

        try:
            with open(CONFIG_FILE, 'w') as configfile:
                self.config.write(configfile)
            self.on_save_callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Save Error", str(e))


class AdvancedSettings(tk.Toplevel):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.title('Advanced Settings')
        self.geometry("500x500")

        self.frame = ttk.Frame(self, padding="20")
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(1, weight=1)

        self.choices = list(THRESHOLD_MAP.keys())
        self.vars = {}

        labels = ["HARASSMENT", "HATE_SPEECH", "DANGEROUS_CONTENT", "SEXUALLY_EXPLICIT", "CIVIC_INTEGRITY"]

        for i, lbl in enumerate(labels):
            key = f"{lbl}_THRESHOLD"
            tk.Label(self.frame, text=key).grid(row=i, column=0, sticky="w", pady=10)

            var = tk.StringVar(value=self.config.get('SAFETY_SETTINGS', key, fallback="BLOCK_MEDIUM_AND_ABOVE"))
            self.vars[key] = var

            ttk.OptionMenu(self.frame, var, var.get(), *self.choices).grid(row=i, column=1, sticky="e", pady=10)
        tk.Label(self.frame, text="This changes the filters.", font=("Arial", 8, "italic")).grid(row=i+1, column=0, sticky="w", pady=10)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        ttk.Button(btn_frame, text="Apply changes...", command=self.apply).pack(side="right")

    def apply(self):
        if not self.config.has_section('SAFETY_SETTINGS'): self.config.add_section('SAFETY_SETTINGS')
        for key, var in self.vars.items():
            self.config.set('SAFETY_SETTINGS', key, var.get())

        # Note: We rely on the parent window to write the file, or we can write it here.
        # For safety, let's write it here too or just let the main save button handle it.
        # In this implementation, we update the config object in memory.
        self.destroy()

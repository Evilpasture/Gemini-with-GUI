import tkinter as tk
from tkinter import ttk, messagebox
import os
from core.config import CONFIG_FILE, LIGHT_THEMES, THRESHOLD_MAP, ALL_MODELS, DEFAULT_CONFIG


class PreferencesWindow(tk.Toplevel):
    def __init__(self, parent, config_parser, on_save_callback, dynamic_models=None):
        super().__init__(parent)
        self.config = config_parser
        self.on_save_callback = on_save_callback
        # Rename for clarity and handle None
        self.dynamic_models = dynamic_models if dynamic_models else ALL_MODELS

        self.title("Preferences")
        self.geometry("450x620")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self.txt_instruct = None

        # Initialize Variables
        self.init_variables()

        # Layout
        self.create_layout()

    def init_variables(self):
        """Loads values from config into Tk variables."""
        self.var_model = tk.StringVar(value=self.config.get('SETTINGS', 'MODEL_NAME', fallback='gemini-2.5-flash'))
        self.var_temp = tk.DoubleVar(value=self.config.getfloat('SETTINGS', 'TEMPERATURE', fallback=0.7))
        self.var_user = tk.StringVar(value=self.config.get('SETTINGS', 'USER_NAME', fallback='User'))
        self.var_bot = tk.StringVar(value=self.config.get('SETTINGS', 'CHATBOT_NAME', fallback='Gemini'))
        self.var_font = tk.IntVar(value=self.config.getint('SETTINGS', 'STANDARD_FONT_SIZE', fallback=11))
        self.var_theme = tk.StringVar(value=self.config.get('SETTINGS', 'THEME', fallback='arc'))

    def create_layout(self):
        notebook = ttk.Notebook(self)
        notebook.pack(pady=10, padx=10, expand=True, fill='both')

        self.tab_ai = ttk.Frame(notebook, padding=15)
        self.tab_sys = ttk.Frame(notebook, padding=15)

        notebook.add(self.tab_ai, text="AI Settings")
        notebook.add(self.tab_sys, text="Appearance")

        self.build_ai_tab()
        self.build_sys_tab()

        # Action Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", fill="x", padx=15, pady=15)

        self.btn_reset = ttk.Button(btn_frame, text="Reset to Defaults", command=self.reset_default)
        self.btn_reset.pack(side="left")

        ttk.Button(btn_frame, text="Save & Apply", command=self.save).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")

    def build_ai_tab(self):
        # Grid helper
        def grid_row(idx, label, widget):
            ttk.Label(self.tab_ai, text=label).grid(row=idx, column=0, sticky="w", pady=8)
            widget.grid(row=idx, column=1, sticky="w", pady=8)

        # Model Selection
        cb_model = ttk.Combobox(self.tab_ai, textvariable=self.var_model, values=self.dynamic_models)
        grid_row(0, "Model Name:", cb_model)

        # Temperature
        scale = ttk.Scale(self.tab_ai, from_=0.0, to=2.0, variable=self.var_temp)
        grid_row(1, "Temperature:", scale)

        # Names
        grid_row(2, "User Name:", ttk.Entry(self.tab_ai, textvariable=self.var_user))
        grid_row(3, "Bot Name:", ttk.Entry(self.tab_ai, textvariable=self.var_bot))

        # Instructions
        ttk.Label(self.tab_ai, text="System Instructions:").grid(row=4, column=0, sticky="nw", pady=8)
        self.txt_instruct = tk.Text(self.tab_ai, height=5, width=25, font=("Arial", 9))
        self.txt_instruct.grid(row=4, column=1, sticky="ew", pady=8)

        # Load instruction text safely
        current_instruct = self.config.get('SETTINGS', 'INSTRUCTION', fallback='')
        self.txt_instruct.insert("1.0", current_instruct)

        # Advanced Button
        ttk.Button(self.tab_ai, text="Safety & Debug...", command=self.open_advanced).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(15, 5)
        )
        self.tab_ai.columnconfigure(1, weight=1)

    def build_sys_tab(self):
        ttk.Label(self.tab_sys, text="Font Size:").grid(row=0, column=0, sticky="w", pady=10)
        ttk.Spinbox(self.tab_sys, from_=8, to=24, textvariable=self.var_font, width=10).grid(row=0, column=1,
                                                                                             sticky="w", pady=10)

        ttk.Label(self.tab_sys, text="Visual Theme:").grid(row=1, column=0, sticky="w", pady=10)
        ttk.Combobox(self.tab_sys, textvariable=self.var_theme, values=LIGHT_THEMES, state="readonly").grid(row=1,
                                                                                                            column=1,
                                                                                                            sticky="w",
                                                                                                            pady=10)

    def open_advanced(self):
        AdvancedSettings(self, self.config)

    def reset_default(self):
        if not messagebox.askokcancel("Reset", "Reset all settings to default values?"):
            return

        try:
            # 1. Delete file
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)

            # 2. Reset In-Memory Config Object
            self.config.read_dict(DEFAULT_CONFIG)

            # 3. Update UI Variables to reflect defaults immediately
            self.var_model.set(DEFAULT_CONFIG['SETTINGS']['MODEL_NAME'])
            self.var_temp.set(float(DEFAULT_CONFIG['SETTINGS']['TEMPERATURE']))
            self.var_user.set(DEFAULT_CONFIG['SETTINGS']['USER_NAME'])
            self.var_bot.set(DEFAULT_CONFIG['SETTINGS']['CHATBOT_NAME'])
            self.var_font.set(int(DEFAULT_CONFIG['SETTINGS']['STANDARD_FONT_SIZE']))
            self.var_theme.set(DEFAULT_CONFIG['SETTINGS']['THEME'])

            self.txt_instruct.delete("1.0", tk.END)
            self.txt_instruct.insert("1.0", DEFAULT_CONFIG['SETTINGS']['INSTRUCTION'])

            messagebox.showinfo("Reset", "Defaults restored. Click 'Save' to apply.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset: {e}")

    def save(self):
        if not self.config.has_section('SETTINGS'): self.config.add_section('SETTINGS')

        self.config.set('SETTINGS', 'MODEL_NAME', self.var_model.get().strip())
        self.config.set('SETTINGS', 'TEMPERATURE', f"{self.var_temp.get():.1f}")
        self.config.set('SETTINGS', 'USER_NAME', self.var_user.get().strip())
        self.config.set('SETTINGS', 'CHATBOT_NAME', self.var_bot.get().strip())
        self.config.set('SETTINGS', 'STANDARD_FONT_SIZE', str(self.var_font.get()))
        self.config.set('SETTINGS', 'THEME', self.var_theme.get())
        self.config.set('SETTINGS', 'INSTRUCTION', self.txt_instruct.get("1.0", "end-1c").strip())

        with open(CONFIG_FILE, 'w') as f:
            self.config.write(f)

        self.on_save_callback()
        self.destroy()


# AdvancedSettings class remains mostly the same, just ensure it uses self.config correctly
class AdvancedSettings(tk.Toplevel):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.title('Safety & Debug')
        self.geometry("450x600")
        self.transient(parent)
        self.grab_set()

        notebook = ttk.Notebook(self)
        notebook.pack(pady=10, padx=10, expand=True, fill='both')

        self.filter_tab = ttk.Frame(notebook, padding="20")
        self.debug_tab = ttk.Frame(notebook, padding="20")

        notebook.add(self.filter_tab, text="Safety Filters")
        notebook.add(self.debug_tab, text="Debug / Advanced")

        self.filter_vars = {}
        self.build_filter_tab()

        self.var_markup = tk.StringVar(value=self.config.get('DEBUG_SETTINGS', 'MARKUP_LANGUAGE', fallback='AsciiDoc'))
        self.build_debug_tab()

        ttk.Button(self, text="Close (Staging)", command=self.apply).pack(side="bottom", pady=10)

    def build_filter_tab(self):
        labels = ["HARASSMENT", "HATE_SPEECH", "DANGEROUS_CONTENT", "SEXUALLY_EXPLICIT", "CIVIC_INTEGRITY"]
        choices = list(THRESHOLD_MAP.keys())

        for i, lbl in enumerate(labels):
            key = f"{lbl}_THRESHOLD"
            display = lbl.replace("_", " ").title()

            ttk.Label(self.filter_tab, text=display).grid(row=i, column=0, sticky="w", pady=5)

            val = self.config.get('SAFETY_SETTINGS', key, fallback="BLOCK_MEDIUM_AND_ABOVE")
            var = tk.StringVar(value=val)
            self.filter_vars[key] = var

            ttk.Combobox(self.filter_tab, textvariable=var, values=choices, state="readonly").grid(row=i, column=1,
                                                                                                   sticky="e", pady=5)

    def build_debug_tab(self):
        ttk.Label(self.debug_tab, text="Markup Parser:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            self.debug_tab,
            textvariable=self.var_markup,
            values=["AsciiDoc", "Markdown", "reStructuredText"]
        ).grid(row=0,column=1,sticky="e")

    def apply(self):
        if not self.config.has_section('SAFETY_SETTINGS'): self.config.add_section('SAFETY_SETTINGS')
        for key, var in self.filter_vars.items():
            self.config.set('SAFETY_SETTINGS', key, var.get())

        if not self.config.has_section('DEBUG_SETTINGS'): self.config.add_section('DEBUG_SETTINGS')
        self.config.set('DEBUG_SETTINGS', 'MARKUP_LANGUAGE', self.var_markup.get())

        self.destroy()
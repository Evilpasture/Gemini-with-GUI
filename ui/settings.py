import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import os
from core.config import CONFIG_FILE, LIGHT_THEMES, THRESHOLD_MAP


class PreferencesWindow(tk.Toplevel):
    def __init__(self, parent, config_parser, on_save_callback):
        super().__init__(parent)
        self.config = config_parser
        self.on_save_callback = on_save_callback

        self.title("Preferences")
        self.geometry("450x600")
        self.resizable(False, False)

        # Variables
        self.var_model = tk.StringVar(value=self.config.get('SETTINGS', 'MODEL_NAME'))
        self.var_temp = tk.DoubleVar(value=self.config.getfloat('SETTINGS', 'TEMPERATURE'))
        self.var_user = tk.StringVar(value=self.config.get('SETTINGS', 'USER_NAME'))
        self.var_bot = tk.StringVar(value=self.config.get('SETTINGS', 'CHATBOT_NAME'))
        self.var_font = tk.IntVar(value=self.config.getint('SETTINGS', 'STANDARD_FONT_SIZE'))
        self.var_theme = tk.StringVar(value=self.config.get('SETTINGS', 'THEME', fallback='arc'))

        # Layout
        self.txt_instruct = None

        notebook = ttk.Notebook(self)
        notebook.pack(pady=10, padx=10, expand=True, fill='both')

        self.tab_ai = ttk.Frame(notebook, padding=15)
        self.tab_sys = ttk.Frame(notebook, padding=15)

        notebook.add(self.tab_ai, text="AI Settings")
        notebook.add(self.tab_sys, text="Appearance")

        self.build_ai_tab()
        self.build_sys_tab()

        # Main Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", fill="x", padx=15, pady=15)
        ttk.Button(btn_frame, text="Reset to Default", command=self.reset_default).pack(side="left")
        ttk.Button(btn_frame, text="Save & Apply", command=self.save).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")

    def build_ai_tab(self):
        def row(idx, label, var=None):
            ttk.Label(self.tab_ai, text=label).grid(row=idx, column=0, sticky="w", pady=8)
            if var:
                ttk.Entry(self.tab_ai, textvariable=var, width=25).grid(row=idx, column=1, sticky="w", pady=8)

        row(0, "Model Name:", self.var_model)

        ttk.Label(self.tab_ai, text="Temperature:").grid(row=1, column=0, sticky="w", pady=8)
        ttk.Scale(self.tab_ai, from_=0.0, to=2.0, variable=self.var_temp).grid(row=1, column=1, sticky="ew", pady=8)

        row(2, "User Name:", self.var_user)
        row(3, "Bot Name:", self.var_bot)

        ttk.Label(self.tab_ai, text="System Instructions:").grid(row=4, column=0, sticky="nw", pady=8)
        self.txt_instruct = tk.Text(self.tab_ai, height=5, width=25, font=("Arial", 9))
        self.txt_instruct.grid(row=4, column=1, sticky="w", pady=8)
        self.txt_instruct.insert("1.0", self.config.get('SETTINGS', 'INSTRUCTION', fallback=''))

        ttk.Button(self.tab_ai, text="Advanced Safety Filters...", command=self.open_advanced).grid(row=5, column=0,
                                                                                                    columnspan=2,
                                                                                                    sticky="ew",
                                                                                                    pady=(15, 5))

    def build_sys_tab(self):
        ttk.Label(self.tab_sys, text="Font Size:").grid(row=0, column=0, sticky="w", pady=10)
        ttk.Spinbox(self.tab_sys, from_=8, to=24, textvariable=self.var_font, width=10).grid(row=0, column=1,
                                                                                             sticky="w", pady=10)

        ttk.Label(self.tab_sys, text="Visual Theme:").grid(row=1, column=0, sticky="w", pady=10)
        theme_cb = ttk.Combobox(self.tab_sys, textvariable=self.var_theme, values=LIGHT_THEMES, state="readonly",
                                width=15)
        theme_cb.grid(row=1, column=1, sticky="w", pady=10)

        ttk.Label(self.tab_sys, text="(Changes apply immediately on save)", font=("Arial", 8, "italic"),
                  foreground="gray").grid(row=2, column=0, columnspan=2, sticky="w")

    def open_advanced(self):
        AdvancedSettings(self, self.config)

    def reset_default(self):
        try:
            # stub
            pass
        except FileNotFoundError:
            pass
        except PermissionError:
            tk.messagebox.showerror("Error", "Permission denied. Please grant yourself administrative permissions if you have to.")
        except Exception as e:
            tk.messagebox.showerror("Error", f"Unknown error. {e}")

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


class AdvancedSettings(tk.Toplevel):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.title('Safety Filters')
        self.geometry("450x450")
        self.resizable(False, False)

        self.frame = ttk.Frame(self, padding="20")
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(1, weight=1)

        self.choices = list(THRESHOLD_MAP.keys())
        self.vars = {}

        labels = [
            "HARASSMENT",
            "HATE_SPEECH",
            "DANGEROUS_CONTENT",
            "SEXUALLY_EXPLICIT",
            "CIVIC_INTEGRITY"
        ]

        ttk.Label(
            self.frame,
            text="Adjust Content Blocking Thresholds",
            font=("Arial", 10, "bold")
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            pady=(0, 20)
        )

        for i, lbl in enumerate(labels):
            key = f"{lbl}_THRESHOLD"
            # Format label to look nicer (e.g., "HATE SPEECH")
            display_text = lbl.replace("_", " ")

            ttk.Label(self.frame, text=display_text).grid(row=i + 1, column=0, sticky="w", pady=10)

            # Load current value
            current_val = self.config.get('SAFETY_SETTINGS', key, fallback="BLOCK_MEDIUM_AND_ABOVE")
            var = tk.StringVar(value=current_val)
            self.vars[key] = var

            # Dropdown
            cb = ttk.Combobox(self.frame, textvariable=var, values=self.choices, state="readonly", width=22)
            cb.grid(row=i + 1, column=1, sticky="e", pady=10)

        # Info Label
        ttk.Label(self.frame,
                  text="Settings are staged immediately.\nClick 'Save & Apply' on the main window to write to file.",
                  font=("Arial", 8, "italic"), foreground="gray", justify="center").grid(row=10, column=0, columnspan=2,
                                                                                         pady=20)

        # Close Button
        ttk.Button(self.frame, text="Done", command=self.apply).grid(row=11, column=0, columnspan=2, sticky="ew")

    def apply(self):
        # Update the config parser object in memory
        if not self.config.has_section('SAFETY_SETTINGS'): self.config.add_section('SAFETY_SETTINGS')
        for key, var in self.vars.items():
            self.config.set('SAFETY_SETTINGS', key, var.get())

        self.destroy()

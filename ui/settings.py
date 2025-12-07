import tkinter as tk
from tkinter import ttk

# Options available in Google GenAI
SAFETY_OPTIONS = [
    "BLOCK_NONE",
    "BLOCK_ONLY_HIGH",
    "BLOCK_MEDIUM_AND_ABOVE",
    "BLOCK_LOW_AND_ABOVE"
]


class PreferencesWindow(tk.Toplevel):
    def __init__(self, parent, config_manager, save_callback, models):
        super().__init__(parent)
        self.config = config_manager.get_parser()
        self.save_callback = save_callback
        self.models = models

        self.title("Settings")
        self.geometry("450x550")  # Slightly taller for extra tab
        self.transient(parent)
        self.grab_set()

        self.safety_vars = {}  # Store safety string variables here

        self._init_vars()
        self._build_ui()

    def _init_vars(self):
        # General Settings
        s = self.config['SETTINGS']
        self.v_model = tk.StringVar(value=s.get('MODEL_NAME'))
        self.v_temp = tk.DoubleVar(value=s.getfloat('TEMPERATURE'))
        self.v_user = tk.StringVar(value=s.get('USER_NAME'))
        self.v_bot = tk.StringVar(value=s.get('CHATBOT_NAME'))
        self.v_font = tk.IntVar(value=s.getint('FONT_SIZE'))
        self.v_theme = tk.StringVar(value=s.get('THEME'))

        # Safety Settings
        # We loop through the keys defined in config.py
        safe_sect = self.config['SAFETY']
        for key in ['HARASSMENT', 'HATE_SPEECH', 'DANGEROUS', 'SEXUAL', 'CIVIC']:
            # Default to BLOCK_MEDIUM if key missing
            val = safe_sect.get(key, "BLOCK_MEDIUM_AND_ABOVE")
            self.safety_vars[key] = tk.StringVar(value=val)

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        f_gen = ttk.Frame(nb, padding=15)
        f_safe = ttk.Frame(nb, padding=15)  # New Safety Tab
        f_app = ttk.Frame(nb, padding=15)

        nb.add(f_gen, text="AI Parameters")
        nb.add(f_safe, text="Safety Filters")
        nb.add(f_app, text="Appearance")

        # --- 1. General Tab ---
        self._grid_opt(f_gen, 0, "Model:", ttk.Combobox(f_gen, textvariable=self.v_model, values=self.models))

        ttk.Label(f_gen, text="Creativity (Temp):").grid(row=1, column=0, sticky="w", pady=5)
        sc = ttk.Scale(f_gen, from_=0.0, to=1.0, variable=self.v_temp)
        sc.grid(row=1, column=1, sticky="ew")

        self._grid_opt(f_gen, 2, "Your Name:", ttk.Entry(f_gen, textvariable=self.v_user))
        self._grid_opt(f_gen, 3, "Bot Name:", ttk.Entry(f_gen, textvariable=self.v_bot))

        ttk.Label(f_gen, text="Instructions:").grid(row=4, column=0, sticky="nw", pady=5)
        self.txt_instr = tk.Text(f_gen, height=5, width=20, font=("Segoe UI", 9))
        self.txt_instr.grid(row=4, column=1, sticky="ew")
        self.txt_instr.insert("1.0", self.config['SETTINGS'].get('INSTRUCTION', ''))

        # --- 2. Safety Tab ---
        # Generate dropdowns dynamically
        row_idx = 0
        for key, var in self.safety_vars.items():
            label_text = key.replace("_", " ").title() + ":"
            cb = ttk.Combobox(f_safe, textvariable=var, values=SAFETY_OPTIONS, state="readonly")
            self._grid_opt(f_safe, row_idx, label_text, cb)
            row_idx += 1

        ttk.Label(f_safe, text=
"""Note: 'Block None' may result in 
unfiltered or unstable content. 
But I know you're responsible... right?""",
                  foreground="gray").grid(row=row_idx, column=0, columnspan=2)

        # --- 3. App Tab ---
        self._grid_opt(f_app, 0, "Font Size:", ttk.Spinbox(f_app, from_=8, to=24, textvariable=self.v_font))
        themes = ["arc", "yaru", "radiance", "breeze", "equilux"]
        self._grid_opt(f_app, 1, "Theme:", ttk.Combobox(f_app, textvariable=self.v_theme, values=themes))

        # --- Bottom Buttons ---
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=10)
        ttk.Button(btns, text="Save & Apply", command=self.save).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=5)

    @staticmethod
    def _grid_opt(parent, row, label, widget):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=8)
        widget.grid(row=row, column=1, sticky="ew", pady=8, padx=(10, 0))
        parent.columnconfigure(1, weight=1)

    def save(self):
        # Save General
        s = self.config['SETTINGS']
        s['MODEL_NAME'] = self.v_model.get()
        s['TEMPERATURE'] = f"{self.v_temp.get():.1f}"
        s['USER_NAME'] = self.v_user.get()
        s['CHATBOT_NAME'] = self.v_bot.get()
        s['FONT_SIZE'] = str(self.v_font.get())
        s['THEME'] = self.v_theme.get()
        s['INSTRUCTION'] = self.txt_instr.get("1.0", "end-1c").strip()

        # Save Safety
        safe_sect = self.config['SAFETY']
        for key, var in self.safety_vars.items():
            safe_sect[key] = var.get()

        # Write to file
        with open("config.ini", "w") as f:
            self.config.write(f)

        self.save_callback()
        self.destroy()

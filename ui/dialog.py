import tkinter as tk
from tkinter import ttk, messagebox


class Dialog(tk.Toplevel):
    def __init__(self, parent, title, prompt, value_type=str, initial_value="", show=None):
        super().__init__(parent)
        self.title(title)
        self.prompt = prompt
        self.value_type = value_type
        self.show_char = show  # Store the mask character (e.g., "*")
        self.output = None

        self.minsize(300, 150)
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._setup_ui(initial_value)
        self._center_window(parent)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_ui(self, initial_value):
        self.frame = ttk.Frame(self, padding=20)
        self.frame.pack(fill='both', expand=True)

        self.var = tk.StringVar(value=str(initial_value))

        self.label = ttk.Label(self.frame, text=self.prompt, font=("Arial", 11))
        self.label.pack(fill='x', pady=(0, 10))

        self.entry = ttk.Entry(self.frame, textvariable=self.var, font=("Arial", 11))
        self.entry.pack(fill='x', pady=(0, 10))

        # If a show character was provided (e.g. '*'), apply it to the entry
        if self.show_char:
            self.entry.configure(show=self.show_char)

        self.entry.focus_set()
        self.bind('<Return>', lambda event: self.handle_submit())

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill='x')

        self.btn = ttk.Button(btn_frame, text="OK", command=self.handle_submit)
        self.btn.pack(side='right')

    def _center_window(self, parent):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

    def on_close(self):
        self.output = None
        self.destroy()

    def handle_submit(self):
        raw_input = self.var.get().strip()

        if raw_input == "":
            messagebox.showwarning("Warning", "Please enter a value", parent=self)
            self.entry.focus_set()
            return
        try:
            if self.value_type == int:
                self.output = int(raw_input)
            elif self.value_type == float:
                self.output = float(raw_input)
            else:
                self.output = raw_input

            self.destroy()

        except ValueError:
            type_name = "an integer" if self.value_type == int else "a number"
            messagebox.showerror("Invalid Input", f"Please enter valid {type_name}.", parent=self)
            self.entry.focus_set()
            self.entry.selection_range(0, tk.END)

    def show_dialog(self):
        self.wait_window(self)
        return self.output

    @staticmethod
    def ask_string(parent, title, prompt, show=None):
        return Dialog(parent, title, prompt, value_type=str, show=show).show_dialog()

    @staticmethod
    def ask_integer(parent, title, prompt, show=None):
        return Dialog(parent, title, prompt, value_type=int, show=show).show_dialog()

    @staticmethod
    def ask_float(parent, title, prompt):
        return Dialog(parent, title, prompt, value_type=float).show_dialog()

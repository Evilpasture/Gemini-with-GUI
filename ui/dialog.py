from typing import TYPE_CHECKING

if TYPE_CHECKING:
    def _(s: str) -> str: ...
else:
    import builtins
    _ = getattr(builtins, "_", lambda s: s)


import tkinter as tk
from tkinter import ttk, messagebox


class Dialog(tk.Toplevel):
    def __init__(self, parent, title, prompt, show=None):
        super().__init__(parent)
        self.title(title)
        self.result = None

        self.geometry("300x150")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._center(parent)

        ttk.Label(self, text=prompt).pack(pady=10)
        self.var = tk.StringVar()
        entry = ttk.Entry(self, textvariable=self.var, show=show)
        entry.pack(pady=5, padx=20, fill="x")
        entry.focus()
        entry.bind("<Return>", lambda e: self.submit())

        ttk.Button(self, text=_("OK"), command=self.submit).pack(pady=10)

    def _center(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 150
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 75
        self.geometry(f"+{x}+{y}")

    def submit(self):
        if self.var.get().strip():
            self.result = self.var.get().strip()
            self.destroy()
        else:
            messagebox.showwarning(_("Required"), _("Input cannot be empty."))

    @staticmethod
    def ask_string(parent, title, prompt, show=None):
        d = Dialog(parent, title, prompt, show)
        parent.wait_window(d)
        return d.result

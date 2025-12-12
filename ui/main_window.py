import tkinter as tk
from tkinter import ttk
import time
try:
    from util.chat_text import ChatTextWidget
    HasCustomWidget = True
except ImportError:
    print("Missing chat_text.py. Falling back to standard tk.Text with adapter.")
    HasCustomWidget = False


class StandardTextAdapter(tk.Text):
    """
    A wrapper around tk.Text to provide compatibility methods
    if ChatTextWidget is missing. Prevents AttributeErrors.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(font=("Segoe UI", 10))  # Default font

    def set_font_size(self, size):
        current_font = self.cget("font")
        # specific implementation depends on how you defined font originally,
        # this is a basic safe fallback
        self.configure(font=(current_font, size))

    def append_message(self, role, name, text):
        self.configure(state="normal")
        self.insert("end", f"\n[{name}]: {text}\n")
        self.configure(state="disabled")
        self.see("end")

    def append_chunk(self, text):
        self.configure(state="normal")
        self.insert("end", text)
        self.configure(state="disabled")
        self.see("end")

    def finalize_formatting(self):
        # No specific formatting in plain text mode
        pass


from .settings import PreferencesWindow


class MainWindow:
    def __init__(self, root, controller, settings):
        self.root = root
        self.controller = controller
        self.settings = settings
        self.available_models = []

        # Stop watch state
        self.start_time = 0
        self.timer_running = False

        self.root.geometry("800x650")
        self.update_title()

        try:
            self.root.set_theme(settings['theme'])
        except Exception as e:
            print(f"Failed to load theme: {e}")

        self._build_menu()
        self._build_layout()
        self.is_text_dirty = False

    def set_available_models(self, models):
        self.available_models = models

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Chat", command=self.controller.restart_chat)
        file_menu.add_command(label="Save Chat...", command=self._on_save)
        file_menu.add_command(label="Load Chat...", command=self._on_load)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.controller.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Settings", command=self.show_settings)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        self.root.config(menu=menubar)

    def _build_layout(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Chat Area
        chat_frame = ttk.Frame(main_frame)
        chat_frame.pack(side="top", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(chat_frame)
        scrollbar.pack(side="right", fill="y")

        # Use the unified widget, or fallback to default tk.Text
        if HasCustomWidget:
            self.chat_display = ChatTextWidget(chat_frame, yscrollcommand=scrollbar.set, wrap="word", relief="flat")
        else:
            # Use the adapter instead of raw tk.Text
            self.chat_display = StandardTextAdapter(chat_frame, yscrollcommand=scrollbar.set, wrap="word",
                                                    relief="flat")

        self.chat_display.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.chat_display.yview)

        self.chat_display.set_font_size(self.settings['font_size'])
        self.chat_display.bind("<<Modified>>", self._on_text_modified)

        # Input Area
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(side="bottom", fill="x", pady=(10, 0))

        self.input_entry = ttk.Entry(input_frame, font=("Segoe UI", 11))
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.input_entry.bind('<Return>', lambda e: self.send_message())

        self.send_btn = ttk.Button(input_frame, text="Send", command=self.send_message)
        self.send_btn.pack(side="right")

        # --- STATUS BAR ---
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(side="bottom", fill="x", pady=(5, 0))

        self.status_lbl = ttk.Label(status_frame, text="Ready", foreground="gray")
        self.status_lbl.pack(side="left")

        self.time_lbl = ttk.Label(status_frame, text="", foreground="#0056b3")  # Blue timer
        self.time_lbl.pack(side="right")

    def _on_save(self):
        self.controller.save_chat()
        self._mark_clean()

    def _on_load(self):
        self.controller.load_chat()
        self._mark_clean()

    def _on_text_modified(self, event=None):
        """Called automatically by Tkinter when text changes."""
        # Only mark dirty if the widget explicitly says it's modified.
        # This prevents the loop where resetting the flag triggers this event again.
        if self.chat_display.edit_modified():
            if not self.is_text_dirty:
                self.is_text_dirty = True

        # Optional: Update window title to show asterisk (*)
        # Probably will add, some time later
        # self.root.title(self.root.title() + " *")

    def _mark_clean(self):
        """Helper to reset the dirty state."""
        self.is_text_dirty = False
        self.chat_display.edit_modified(False)

    def is_dirty(self):
        return self.is_text_dirty

    def update_settings(self, settings):
        self.settings = settings
        self.update_title()
        self.chat_display.set_font_size(settings['font_size'])
        try:
            if ttk.Style().theme_use() != settings['theme']:
                self.root.set_theme(settings['theme'])
        except Exception as e:
            print(f"Something bad happened when updating themes in settings. {e}")

    def update_title(self):
        self.root.title(f"Gemini Chat - {self.settings['model_name']}")

    def show_settings(self):
        PreferencesWindow(self.root, self.controller.config_manager, self.controller.reload_settings,
                          self.available_models)

    def send_message(self):
        text = self.input_entry.get().strip()
        if not text: return

        self.input_entry.delete(0, tk.END)
        self.input_entry.config(state="disabled")
        self.send_btn.config(state="disabled")
        self.status_lbl.config(text="Thinking...")

        # Display User Message
        self.chat_display.append_message("user", self.settings['user_name'], text)

        # Prepare AI visual block
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", "\n\n")
        self.chat_display.insert("end", f"{self.settings['chatbot_name']}: ", "ai_msg")
        self.chat_display.configure(state="disabled")

        # start timer
        self._start_stopwatch()

        self.controller.process_input(text)

    def on_response_received(self, text, status):
        # Schedule GUI update on main thread
        self.root.after_idle(lambda: self._handle_stream(text, status))

    def _handle_stream(self, text, status):
        if status == "stream":
            self.chat_display.append_chunk(text)
        elif status == "finished":
            # stop timer
            self._stop_stopwatch()

            self.chat_display.finalize_formatting()
            self.chat_display.insert("end", "\n")  # Spacing for next turn
            self.input_entry.config(state="normal")
            self.send_btn.config(state="normal")
            self.input_entry.focus()
            self.status_lbl.config(text="Ready")
        elif status == "error":
            self._stop_stopwatch()
            self.chat_display.configure(state="normal")
            self.chat_display.insert("end", f"\n[Error: {text}]\n", "error")
            self.chat_display.configure(state="disabled")
            self.input_entry.config(state="normal")
            self.send_btn.config(state="normal")
            self.status_lbl.config(text="Error")

    # --- STOPWATCH LOGIC ---
    def _start_stopwatch(self):
        self.start_time = time.time()
        self.timer_running = True
        self.time_lbl.config(text="0.0s")
        self._update_timer()

    def _update_timer(self):
        if self.timer_running:
            elapsed = time.time() - self.start_time
            self.time_lbl.config(text=f"{elapsed:.1f}s")
            self.root.after(100, self._update_timer)

    def _stop_stopwatch(self):
        if self.timer_running:
            self.timer_running = False
            elapsed = time.time() - self.start_time
            self.time_lbl.config(text=f"{elapsed:.2f}s")

    def reset_ui(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.configure(state="disabled")

        # Resetting UI counts as a modification, but usually, a "New Chat" is considered "Clean".
        self._mark_clean()

        self.append_system_msg("Session Reset.", True)

    def append_system_msg(self, text, success=True):
        tag = "system" if success else "error"
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"\n[System: {text}]\n", tag)
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def render_history(self, history):
        self.reset_ui()
        for item in history:
            role = "user" if item.role == "user" else "ai"
            name = self.settings['user_name'] if role == "user" else self.settings['chatbot_name']
            # Safety check if parts exist
            txt = item.parts[0].text if item.parts else ""
            self.chat_display.append_message(role, name, txt)

import tkinter as tk


class ChatTextWidget(tk.Text):
    """
    A robust, simplified Markdown widget for Chat.
    Instead of 'hiding' characters (which crashes Tkinter indices),
    this widget styles them (dimming them) and emphasizes the content.
    Handles Code Blocks, Bold, Italic, and Headers.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.base_font_size = 11
        self._configure_styles()

    def set_font_size(self, size):
        self.base_font_size = size
        self.configure(font=("Segoe UI", size))  # Modern default font
        self._configure_styles()

    def _configure_styles(self):
        s = self.base_font_size
        family = "Segoe UI"
        mono = "Consolas"

        # Define Fonts
        self.tag_config("user_msg", foreground="#0056b3", font=(family, s, "bold"))
        self.tag_config("ai_msg", foreground="#2da44e", font=(family, s, "bold"))
        self.tag_config("error", foreground="red")
        self.tag_config("system", foreground="gray", font=(family, s - 1, "italic"))

        # Markdown Styles
        self.tag_config("h1", font=(family, int(s * 1.5), "bold"), spacing3=5)
        self.tag_config("h2", font=(family, int(s * 1.3), "bold"), spacing3=5)
        self.tag_config("bold", font=(family, s, "bold"))
        self.tag_config("italic", font=(family, s, "italic"))

        # Code Blocks (Light background, monospaced)
        self.tag_config("code", font=(mono, s - 1), background="#f6f8fa", foreground="#d63384")
        self.tag_config("codeblock", font=(mono, s - 1), background="#f0f0f0", lmargin1=20)

        # FIX: Don't hide chars, just dim them. Hiding breaks selection/copy-paste index math.
        self.tag_config("syntax", foreground="#cccccc")

    def append_message(self, role, name, text):
        self.configure(state="normal")

        # Add Name Header
        tag = "user_msg" if role == "user" else "ai_msg"
        if self.index("end-1c") != "1.0":
            self.insert("end", "\n\n")

        self.insert("end", f"{name}: ", tag)

        # Insert Content with Markdown parsing
        self._insert_markdown(text)

        self.configure(state="disabled")
        self.see("end")

    def append_chunk(self, text):
        """Used for streaming AI responses"""
        self.configure(state="normal")

        # Simple insertion for chunks to keep performance high during stream
        # Full reparsing happens only if strictly necessary, but here we just append.
        # A more complex implementation would buffer lines.
        self.insert("end", text)

        # Apply simplified highlighting on the newly inserted range
        # (For a real production app, you'd track the start index of the chunk)

        self.configure(state="disabled")
        self.see("end")

    def finalize_formatting(self):
        """Call this after streaming ends to apply full Markdown syntax highlights."""
        self.configure(state="normal")
        # For simplicity in this refactor, we reparse the whole text
        # In a very long chat, you'd only parse the last message.
        text_content = self.get("1.0", "end")

        # Clear specific styling tags (preserve headers/roles)
        for tag in ["bold", "italic", "code", "codeblock", "h1", "h2", "syntax"]:
            self.tag_remove(tag, "1.0", "end")

        self._apply_markdown_regex("1.0", "end")
        self.configure(state="disabled")

    def _insert_markdown(self, text):
        start = self.index("end-1c")
        self.insert("end", text)
        end = self.index("end-1c")
        self._apply_markdown_regex(start, end)

    def _apply_markdown_regex(self, start_pos, end_pos):
        count = tk.IntVar()

        # 1. Code Blocks (```...```) - Highest Priority
        # We find these first to avoid styling inside them
        code_ranges = []
        curr = start_pos
        while True:
            # Find start ```
            pos_start = self.search(r"```", curr, stopindex=end_pos, count=count, regexp=True)
            if not pos_start: break

            # Find end ```
            search_from = f"{pos_start}+3c"
            pos_end = self.search(r"```", search_from, stopindex=end_pos, count=count, regexp=True)

            if not pos_end:
                # Open code block at end of text
                block_end = end_pos
                next_search = end_pos
            else:
                block_end = f"{pos_end}+3c"
                next_search = block_end

            self.tag_add("codeblock", pos_start, block_end)
            code_ranges.append((str(self.index(pos_start)), str(self.index(block_end))))
            curr = next_search

        # Helper to check if a position is inside a code block
        def is_in_code(idx):
            idx_float = float(str(self.index(idx)))
            for s, e in code_ranges:
                if float(s) <= idx_float < float(e):
                    return True
            return False

        # 2. Inline Code (`...`)
        self._regex_style(r"`[^`\n]+`", "code", start_pos, end_pos, is_in_code)

        # 3. Bold (**...**)
        self._regex_style(r"\*\*[^\*\n]+\*\*", "bold", start_pos, end_pos, is_in_code)

        # 4. Italic (*...*)
        self._regex_style(r"\*[^\*\n]+\*", "italic", start_pos, end_pos, is_in_code)

        # 5. Headers (# )
        self._regex_style(r"^# .+$", "h1", start_pos, end_pos, is_in_code)
        self._regex_style(r"^## .+$", "h2", start_pos, end_pos, is_in_code)

    def _regex_style(self, pattern, tag, start, end, exclusion_check):
        count = tk.IntVar()
        curr = start
        while True:
            pos = self.search(pattern, curr, stopindex=end, count=count, regexp=True)
            if not pos: break

            match_len = count.get()
            end_match = f"{pos}+{match_len}c"

            if not exclusion_check(pos):
                self.tag_add(tag, pos, end_match)

                # Optional: Dim syntax chars (e.g. the **)
                # This requires more complex regex groups, kept simple here.

            curr = end_match

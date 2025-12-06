import tkinter as tk
import tkinter.font as tkfont
import re


class ReSTText(tk.Text):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.font_info = self._get_font_info()
        self._configure_styles()

    def _get_font_info(self):
        """Safely extracts font family/size/weight from the current widget."""
        current_font = self.cget("font")
        temp_font = tkfont.Font(font=current_font)
        return {
            "family": temp_font.cget("family"),
            "size": temp_font.cget("size"),
            "weight": temp_font.cget("weight")
        }

    def _configure_styles(self):
        """Defines the fonts and colors for reStructuredText elements."""
        info = self.font_info
        base_family = info["family"]
        base_size = info["size"]
        s = abs(base_size)

        # --- Fonts ---
        h1_font = tkfont.Font(family=base_family, size=int(s * 1.6), weight="bold")
        h2_font = tkfont.Font(family=base_family, size=int(s * 1.4), weight="bold")
        h3_font = tkfont.Font(family=base_family, size=int(s * 1.2), weight="bold")

        bold_font = tkfont.Font(family=base_family, size=s, weight="bold")
        italic_font = tkfont.Font(family=base_family, size=s, slant="italic")
        mono_font = tkfont.Font(family="Consolas", size=s)

        # --- Tag Configs ---
        self.tag_config("h1", font=h1_font, spacing3=10, foreground="#222222")
        self.tag_config("h2", font=h2_font, spacing3=8, foreground="#333333")
        self.tag_config("h3", font=h3_font, spacing3=5, foreground="#444444")

        self.tag_config("strong", font=bold_font)  # **bold**
        self.tag_config("emphasis", font=italic_font)  # *italic*

        # Inline literals: ``text``
        self.tag_config("literal", font=mono_font, background="#f4f4f4", foreground="#d63384")

        # Code Blocks (:: or .. code::)
        self.tag_config("literal_block", font=mono_font, background="#f0f0f0", foreground="#333333", lmargin1=20)

        # Directives/Admonitions (.. note::)
        self.tag_config("directive", font=bold_font, foreground="#2c3e50", background="#e8f4f8")

        # Field lists (:Field:)
        self.tag_config("field_name", font=bold_font, foreground="#0056b3")

        self.tag_config("bullet", lmargin1=20, lmargin2=30)
        self.tag_config("hidden", elide=True)

    def _raise_tags(self):
        """Ensures formatting sits on top of text."""
        # 'hidden' top priority to hide syntax.
        # 'literal_block' protects code from inline regex.
        priorities = ["hidden", "literal", "literal_block", "strong", "emphasis",
                      "h1", "h2", "h3", "directive", "field_name", "bullet"]
        for tag in priorities:
            self.tag_raise(tag)

    def load_markup(self, doc_text, tags=None):
        """
        Parses reStructuredText string and inserts it.
        """
        self.configure(state="normal")

        if tags is None:
            extra_tags = ()
        elif isinstance(tags, str):
            extra_tags = (tags,)
        else:
            extra_tags = tuple(tags)

        start_index = self.index("end-1c")
        lines = doc_text.split("\n")

        # State Machine Flags
        in_literal_block = False
        literal_indent_level = 0

        # Helper to detect header underlines
        def is_underline(line_text, char):
            return line_text.strip().startswith(char * 3) and len(line_text.strip()) == line_text.count(char)

        for i, line in enumerate(lines):
            stripped = line.strip()
            current_tags = list(extra_tags)

            # 1. Handle Literal Blocks (Indentation based)
            # ReST blocks often start after '::'
            if in_literal_block:
                # Check indentation (simple heuristic: if line is empty or starts with space)
                # If line is not empty and has NO indentation, block ends.
                if stripped and not (line.startswith(" ") or line.startswith("\t")):
                    in_literal_block = False
                else:
                    self.insert("end", line + "\n", ("literal_block",) + extra_tags)
                    continue

            # Check entry to literal block via '::' at end of previous line (handled loosely)
            if line.endswith("::") or line.strip() == "::":
                # We don't hide the :: usually in chat, but we flag next lines
                in_literal_block = True

            # Check explicit code directive
            if stripped.startswith(".. code") or stripped.startswith(".. sourcecode"):
                in_literal_block = True
                self.insert("end", line + "\n", ("directive",) + extra_tags)
                continue

            # 2. Section Headers (Underline detection)
            # If this line is '====', apply H1 to the PREVIOUS line
            is_header_underline = False
            header_tag = None

            if is_underline(stripped, "="):
                header_tag = "h1"
                is_header_underline = True
            elif is_underline(stripped, "-"):
                header_tag = "h2"
                is_header_underline = True
            elif is_underline(stripped, "~"):
                header_tag = "h3"
                is_header_underline = True

            if is_header_underline:
                # Go back one line in the widget and apply tag
                # Note: We must check if there IS a previous line in this batch or widget
                # 'end-2c' is the end of the line just inserted
                prev_line_start = self.index("end-2l linestart")
                prev_line_end = self.index("end-2l lineend")

                # Apply tag to previous line
                self.tag_add(header_tag, prev_line_start, prev_line_end)

                # Do NOT insert the underline line (hide it)
                # But to keep line sync, we can insert it as hidden
                self.insert("end", line + "\n", ("hidden",) + extra_tags)
                continue

            # 3. Admonitions / Directives (.. note::)
            if stripped.startswith(".. ") and "::" in stripped:
                self.insert("end", line + "\n", ("directive",) + extra_tags)
                continue

            # 4. Bullet Lists (*, -, +)
            if re.match(r"^(\*|\-|\+)\s+", stripped):
                current_tags.append("bullet")
                # Clean up the bullet char for visual niceness
                content = "\u2022 " + stripped[1:].lstrip()
                self.insert("end", content + "\n", tuple(current_tags))
                continue

            # 5. Field Lists (:Name: Value)
            field_match = re.match(r"^:([a-zA-Z0-9 _-]+):(.*)", stripped)
            if field_match:
                # Insert Name
                self.insert("end", f":{field_match.group(1)}:", ("field_name",) + extra_tags)
                # Insert Value
                self.insert("end", f"{field_match.group(2)}\n", extra_tags)
                continue

            # Standard Insert
            self.insert("end", line + "\n", tuple(current_tags))

        end_index = self.index("end-1c")

        # --- INLINE REGEX STYLING ---

        # 1. Inline Literal ``text`` (Double backticks in ReST)
        self._apply_regex(r"``(.*?)``", "literal", start_index, end_index, d_len=2)

        # 2. Strong (Bold) **text**
        self._apply_regex(r"\*\*(.*?)\*\*", "strong", start_index, end_index, d_len=2)

        # 3. Emphasis (Italic) *text*
        # ReST is strict about spaces around single asterisks, but we'll be loose for chat
        self._apply_regex(r"\*(.*?)\*", "emphasis", start_index, end_index, d_len=1)

        self._raise_tags()
        self.configure(state="disabled")

    def _apply_regex(self, pattern, tag, start_index, limit_index, d_len=1):
        """Applies tags to regex matches, hiding delimiters."""
        count = tk.IntVar()
        current_index = start_index

        while True:
            pos = self.search(pattern, current_index, stopindex=limit_index, count=count, regexp=True)
            if not pos: break

            match_len = count.get()
            end_match = f"{pos}+{match_len}c"

            # Check if we are inside a Literal Block (don't style code blocks!)
            current_tags = self.tag_names(pos)
            if "literal_block" in current_tags:
                current_index = end_match
                continue

            inner_start = f"{pos}+{d_len}c"
            inner_end = f"{end_match}-{d_len}c"

            self.tag_add(tag, inner_start, inner_end)
            self.tag_add("hidden", pos, inner_start)
            self.tag_add("hidden", inner_end, end_match)

            current_index = end_match

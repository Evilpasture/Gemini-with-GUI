import tkinter as tk
import tkinter.font as tkfont


class MarkdownText(tk.Text):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.font_info = self._get_font_info()
        self._configure_tags()

    def _get_font_info(self):
        """Safely extracts font family/size/weight from the current widget."""
        current_font = self.cget("font")
        temp_font = tkfont.Font(font=current_font)
        return {
            "family": temp_font.cget("family"),
            "size": temp_font.cget("size"),
            "weight": temp_font.cget("weight")
        }

    def _configure_tags(self):
        """Defines the fonts and colors for markdown elements."""
        info = self.font_info
        base_family = info["family"]
        base_size = info["size"]
        s = abs(base_size)

        # --- Font Definitions ---
        # We need a specific font for Bold+Italic combined
        bold_italic_font = tkfont.Font(family=base_family, size=s, weight="bold", slant="italic")
        bold_font = tkfont.Font(family=base_family, size=s, weight="bold")
        italic_font = tkfont.Font(family=base_family, size=s, slant="italic")

        # Code block font (usually slightly smaller or different family)
        code_font = tkfont.Font(family="Consolas", size=s)

        # Header fonts
        h1_font = tkfont.Font(family=base_family, size=int(s * 1.6), weight="bold")
        h2_font = tkfont.Font(family=base_family, size=int(s * 1.4), weight="bold")
        h3_font = tkfont.Font(family=base_family, size=int(s * 1.2), weight="bold")

        # --- Tag Configurations ---
        self.tag_config("h1", font=h1_font, spacing3=10)
        self.tag_config("h2", font=h2_font, spacing3=5)
        self.tag_config("h3", font=h3_font, spacing3=2)

        self.tag_config("bold_italic", font=bold_italic_font)
        self.tag_config("bold", font=bold_font)
        self.tag_config("italic", font=italic_font)

        # Inline code (`text`)
        self.tag_config("code", font=code_font, background="#e6e6e6", foreground="#d63384")

        # Multi-line code block (```)
        # We add 'spacing1' and 'spacing3' to give the block some breathing room
        self.tag_config("codeblock", font=code_font, background="#f0f0f0", foreground="#333333")

        self.tag_config("bullet", lmargin1=20, lmargin2=30)
        self.tag_config("hidden", elide=True)

    def _raise_markdown_tags(self):
        # The order matters here!
        # "hidden" must be on top to hide delimiters.
        # "codeblock" protects text from having bold/italic applied inside it.
        priorities = ["hidden", "code", "codeblock", "bold_italic", "bold", "italic", "h1", "h2", "bullet"]
        for tag in priorities:
            self.tag_raise(tag)

    def load_markdown(self, md_text, tags=None):
        """
        Parses markdown and appends it to the widget.
        """
        self.configure(state="normal")

        if tags is None:
            extra_tags = ()
        elif isinstance(tags, str):
            extra_tags = (tags,)
        else:
            extra_tags = tuple(tags)

        start_index = self.index("end-1c")

        lines = md_text.split("\n")

        # --- PHASE 1: LINE PARSING (State Machine) ---
        in_code_block = False

        for line in lines:
            # Handle Code Block Toggles (```)
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                # We insert the fence, but we will hide it later if you prefer,
                # or just leave it to show boundaries. Let's tag it hidden.
                self.insert("end", line + "\n", ("hidden",) + extra_tags)
                continue

            # If inside a code block, insert literally and skip markdown checks
            if in_code_block:
                self.insert("end", line + "\n", ("codeblock",) + extra_tags)
                continue

            # --- Normal Markdown Parsing ---
            md_tag = None
            content = line

            if line.startswith("# "):
                md_tag = "h1"
                content = line[2:]
            elif line.startswith("## "):
                md_tag = "h2"
                content = line[3:]
            elif line.startswith("### "):
                md_tag = "h3"
                content = line[4:]
            elif line.strip().startswith("- "):
                md_tag = "bullet"
                content = "\u2022 " + line.strip()[2:]

            combined = (md_tag,) + extra_tags if md_tag else extra_tags
            self.insert("end", content + "\n", combined)

        end_index = self.index("end-1c")

        # --- PHASE 2: INLINE REGEX ---
        # We apply this ONLY to text that is NOT a code block.
        # However, tk regex search is global.
        # The trick: The "codeblock" tag is raised above bold/italic in _raise_markdown_tags.
        # Even if we accidentally tag inside the codeblock, the codeblock font will win visually.

        # 1. Inline Code `text`
        self._apply_regex_styling(r"`(.*?)`", "code", start_index, end_index)

        # 2. Bold+Italic ***text*** (Must be before Bold or Italic)
        self._apply_regex_styling(r"\*\*\*(.*?)\*\*\*", "bold_italic", start_index, end_index)

        # 3. Bold **text**
        self._apply_regex_styling(r"\*\*(.*?)\*\*", "bold", start_index, end_index)

        # 4. Italic *text*
        self._apply_regex_styling(r"\*(.*?)\*", "italic", start_index, end_index)

        self._raise_markdown_tags()
        self.configure(state="disabled")

    def _apply_regex_styling(self, pattern, tag, start_index, limit_index):
        """Applies tags to regex matches within a specific range."""
        count = tk.IntVar()
        current_index = start_index

        while True:
            pos = self.search(pattern, current_index, stopindex=limit_index, count=count, regexp=True)
            if not pos: break

            match_len = count.get()
            end_match = f"{pos}+{match_len}c"

            # Determine delimiter length
            if tag == "bold_italic":
                d_len = 3
            elif tag == "bold":
                d_len = 2
            elif tag == "italic":
                d_len = 1
            elif tag == "code":
                d_len = 1
            else:
                d_len = 0

            # Tag the inner content
            inner_start = f"{pos}+{d_len}c"
            inner_end = f"{end_match}-{d_len}c"

            # CHECK: Don't apply formatting if we are inside a code block!
            # We look at the tags present at the start of the match.
            current_tags = self.tag_names(pos)
            if "codeblock" not in current_tags:
                self.tag_add(tag, inner_start, inner_end)

                # Hide delimiters
                if d_len > 0:
                    self.tag_add("hidden", pos, inner_start)
                    self.tag_add("hidden", inner_end, end_match)

            current_index = end_match

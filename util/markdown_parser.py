import tkinter as tk
import tkinter.font as tkfont
import re


class MarkdownText(tk.Text):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        # self.config(wrap="word")
        self.font = self.cget("font")

        font_object_reference = tkfont.nametofont(self.font)

        self.font_family = font_object_reference.cget("family")
        self.font_size = font_object_reference.cget("size")
        self.font_weight = font_object_reference.cget("weight")

        self._configure_tags()

    def _configure_tags(self):
        """Defines the fonts and colors for markdown elements."""
        # Base fonts
        normal_font = tkfont.Font(family=self.font_family, size=self.font_size)
        bold_font = normal_font.copy(); bold_font.configure(weight="bold")
        italic_font = normal_font.copy(); italic_font.configure(slant="italic")
        h1_font = tkfont.Font(family=self.font_family, size=self.font_size + int(self.font_size*0.6), weight="bold")
        h2_font = tkfont.Font(family=self.font_family, size=self.font_size + int(self.font_size*0.4), weight="bold")
        h3_font = tkfont.Font(family=self.font_family, size=self.font_size + int(self.font_size*0.2), weight="bold")
        code_font = tkfont.Font(family="Courier New", size=self.font_size)

        # Tag configurations
        tag_configurations = {
            "normal": {"font": normal_font},
            "bold": {"font": bold_font},
            "italic": {"font": italic_font},
            "h1": {"font": h1_font, "spacing3": 10},
            "h2": {"font": h2_font, "spacing3": 5},
            "h3": {"font": h3_font, "spacing3": 2},
            "code": {"font": code_font, "background": "#f0f0f0", "foreground": "#d63384"},
            "bullet": {"font": normal_font, "lmargin1": 20, "lmargin2": 30},
        }

        for tag_name, config_options in tag_configurations.items():
            self.tag_config(tag_name, **config_options)

    def _raise_markdown_tags(self):
        """Ensures Markdown formatting sits 'on top' of user formatting"""
        self.tag_raise("bold")
        self.tag_raise("italic")
        self.tag_raise("h1")
        self.tag_raise("h2")
        self.tag_raise("h3")
        self.tag_raise("code")
        self.tag_raise("bullet")

    def load_markdown(self, md_text, tags=None):
        """Parses simple markdown and inserts it into the widget."""
        self.configure(state="normal")
        # self.delete("1.0", "end")

        if tags is None:
            extra_tags = ()
        elif isinstance(tags, str):
            extra_tags = (tags,)
        else:
            extra_tags = tuple(tags)

        lines = md_text.split("\n")

        for line in lines:
            # Default markdown tag
            md_tag = "normal"
            content = line

            # 1. Handle Block elements
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


            combined_tags = (md_tag,) + extra_tags

            # Insert the clean text with the block tag
            self._raise_markdown_tags()
            self.insert("end", content + "\n", combined_tags)

        # 2. Handle Inline elements (Bold, Italic, Code) via Regex
        # We process the text we just inserted to apply inline styles
        self._apply_regex_styling(r'\*\*(.*?)\*\*', "bold")  # **bold**
        self._apply_regex_styling(r'\*(.*?)\*', "italic")  # *italic*
        self._apply_regex_styling(r'`(.*?)`', "code")  # `code`

        self.configure(state="disabled")

    def _apply_regex_styling(self, pattern, tag):
        """Finds regex matches and applies tags, hiding the syntax symbols."""
        count = tk.IntVar()
        start_index = "1.0"

        while True:
            # Search for the regex pattern
            pos = self.search(pattern, start_index, stopindex="end", count=count, regexp=True)
            if not pos:
                break

            # Calculate positions
            # pos is "line.char" start of the match
            match_len = count.get()
            end_index = f"{pos}+{match_len}c"

            # Get the full matched text (e.g., **bold**)
            full_text = self.get(pos, end_index)

            # Determine length of delimiters based on the tag
            if tag == "bold":
                delimiter_len = 2  # **
            elif tag == "italic":
                delimiter_len = 1  # *
            elif tag == "code":
                delimiter_len = 1  # `
            else:
                delimiter_len = 0

            # Apply the style tag to the inner text only
            # inner_start = pos + delimiter chars
            inner_start = f"{pos}+{delimiter_len}c"
            # inner_end = end_index - delimiter chars
            inner_end = f"{end_index}-{delimiter_len}c"

            self.tag_add(tag, inner_start, inner_end)

            # "Hide" the delimiters (Markdown syntax) by making them elided
            # Note: This keeps indices correct but makes text invisible
            self.tag_add("hidden", pos, inner_start)
            self.tag_add("hidden", inner_end, end_index)
            self.tag_config("hidden", elide=True)

            # Update start_index to search after this match
            start_index = end_index

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
        s = abs(base_size)  # Absolute size

        # Markdown Fonts
        h1_font = tkfont.Font(family=base_family, size=int(s * 1.6), weight="bold")
        h2_font = tkfont.Font(family=base_family, size=int(s * 1.4), weight="bold")
        h3_font = tkfont.Font(family=base_family, size=int(s * 1.2), weight="bold")
        bold_font = tkfont.Font(family=base_family, size=s, weight="bold")
        italic_font = tkfont.Font(family=base_family, size=s, slant="italic")
        code_font = tkfont.Font(family="Courier New", size=s)

        # Standard Markdown configurations
        self.tag_config("h1", font=h1_font, spacing3=10)
        self.tag_config("h2", font=h2_font, spacing3=5)
        self.tag_config("h3", font=h3_font, spacing3=2)
        self.tag_config("bold", font=bold_font)
        self.tag_config("italic", font=italic_font)
        self.tag_config("code", font=code_font, background="#e0e0e0", foreground="#d63384")
        self.tag_config("bullet", lmargin1=20, lmargin2=30)
        self.tag_config("hidden", elide=True)

    def _raise_markdown_tags(self):
        """
        Crucial: Raises Markdown tags above external tags (like 'user', 'system').
        This ensures bold/colors show up on top of message bubble colors.
        """
        priority_tags = ["hidden", "code", "bold", "italic", "h1", "h2", "h3", "bullet"]
        for tag in priority_tags:
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

        # Record start position of THIS append operation
        start_index = self.index("end-1c")

        lines = md_text.split("\n")

        for line in lines:
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

            if md_tag:
                combined_tags = (md_tag,) + extra_tags
            else:
                combined_tags = extra_tags

            self.insert("end", content + "\n", combined_tags)

        end_index = self.index("end-1c")

        # --- FIXED REGEX SECTION ---
        # We rely on Order of Operations.
        # Tcl's search skips "hidden" text. So if we hide Code and Bold syntax first,
        # the Italic search won't see the bold '**' markers.

        # 1. Code: `text`
        self._apply_regex_styling(r"`(.*?)`", "code", start_index, end_index)

        # 2. Bold: **text**
        # We process this BEFORE italic. The ** markers get hidden here.
        self._apply_regex_styling(r"\*\*(.*?)\*\*", "bold", start_index, end_index)

        # 3. Italic: *text*
        # Because ** was hidden in step 2, this simple regex is now safe.
        # It won't accidentally match the halves of a bold tag.
        self._apply_regex_styling(r"\*(.*?)\*", "italic", start_index, end_index)

        self._raise_markdown_tags()
        self.configure(state="disabled")

    def _apply_regex_styling(self, pattern, tag, start_index, limit_index):
        """Applies tags to regex matches within a specific range."""
        count = tk.IntVar()
        current_index = start_index

        while True:
            # Search strictly within the new text block
            pos = self.search(pattern, current_index, stopindex=limit_index, count=count, regexp=True)
            if not pos:
                break

            match_len = count.get()
            # Calculate the end of the match based on count
            end_match = f"{pos}+{match_len}c"

            # Determine delimiter length
            if tag == "bold":
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
            self.tag_add(tag, inner_start, inner_end)

            # Hide delimiters (make them invisible)
            if d_len > 0:
                self.tag_add("hidden", pos, inner_start)
                self.tag_add("hidden", inner_end, end_match)

            # Move search forward to the end of this match
            current_index = end_match
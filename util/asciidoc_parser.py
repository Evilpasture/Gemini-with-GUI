import tkinter as tk
import tkinter.font as tkfont
import re


class AsciiDocText(tk.Text):
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
        """Defines the fonts and colors for AsciiDoc elements."""
        info = self.font_info
        base_family = info["family"]
        base_size = info["size"]
        s = abs(base_size)

        # --- Fonts ---
        # AsciiDoc uses standard bold/italic, but also Monospace for literals
        # and different sizes for headers (=, ==, ===).

        # Headers (AsciiDoc uses = for Level 0, == for Level 1, etc.)
        h0_font = tkfont.Font(family=base_family, size=int(s * 1.8), weight="bold")
        h1_font = tkfont.Font(family=base_family, size=int(s * 1.5), weight="bold")
        h2_font = tkfont.Font(family=base_family, size=int(s * 1.3), weight="bold")
        h3_font = tkfont.Font(family=base_family, size=int(s * 1.1), weight="bold")

        bold_font = tkfont.Font(family=base_family, size=s, weight="bold")
        italic_font = tkfont.Font(family=base_family, size=s, slant="italic")

        # Monospace (for `literal` or +literal+ or ---- blocks)
        mono_font = tkfont.Font(family="Consolas", size=s)

        # --- Tag Configs ---
        self.tag_config("h0", font=h0_font, spacing3=15, foreground="#222222")
        self.tag_config("h1", font=h1_font, spacing3=10, foreground="#333333")
        self.tag_config("h2", font=h2_font, spacing3=8, foreground="#444444")
        self.tag_config("h3", font=h3_font, spacing3=5, foreground="#555555")

        self.tag_config("strong", font=bold_font)  # *bold*
        self.tag_config("emphasis", font=italic_font)  # _italic_

        # Inline Monospace: `text` or +text+
        self.tag_config("monospace", font=mono_font, background="#f4f4f4", foreground="#d63384")

        # Listing Blocks: ----
        self.tag_config("listing", font=mono_font, background="#f0f0f0", foreground="#333333", lmargin1=10)

        # Admonitions (NOTE, TIP) - Simple coloring
        self.tag_config("admonition", font=bold_font, foreground="#2c3e50", background="#e8f4f8")

        self.tag_config("bullet", lmargin1=20, lmargin2=30)
        self.tag_config("hidden", elide=True)

    def _raise_tags(self):
        """Ensures formatting sits on top of text."""
        # 'hidden' must be top to hide syntax chars.
        # 'listing' protects code blocks from inline parsing.
        priorities = ["hidden", "monospace", "listing", "strong", "emphasis", "h0", "h1", "h2", "h3", "admonition",
                      "bullet"]
        for tag in priorities:
            self.tag_raise(tag)

    def load_asciidoc(self, doc_text, tags=None):
        """
        Parses AsciiDoc string and inserts it.
        :param doc_text: The AsciiDoc string.
        :param tags: Optional external tags (e.g. 'user', 'system').
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
        in_listing_block = False  # for ----

        for line in lines:
            # 1. Handle Listing Block Delimiters (----)
            if line.strip() == "----":
                in_listing_block = not in_listing_block
                # Insert the fence line, but hide it
                self.insert("end", line + "\n", ("hidden",) + extra_tags)
                continue

            # 2. If inside a listing block, insert as Literal
            if in_listing_block:
                self.insert("end", line + "\n", ("listing",) + extra_tags)
                continue

            # 3. Normal AsciiDoc Line Parsing
            adoc_tag = None
            content = line

            # Headers (= Title, == Section)
            if line.startswith("= "):
                adoc_tag = "h0"
                content = line[2:]
            elif line.startswith("== "):
                adoc_tag = "h1"
                content = line[3:]
            elif line.startswith("=== "):
                adoc_tag = "h2"
                content = line[4:]
            elif line.startswith("==== "):
                adoc_tag = "h3"
                content = line[5:]

            # Lists (* item, - item, . item)
            elif line.strip().startswith("* ") or line.strip().startswith("- "):
                adoc_tag = "bullet"
                # Convert * or - to a nice Unicode bullet
                content = "\u2022 " + line.strip()[2:]

            # Admonitions (NOTE: Text)
            elif re.match(r"^(NOTE|TIP|IMPORTANT|WARNING|CAUTION):", line):
                # We tag the whole line, or split it? Let's tag the label.
                # Actually, simpler to tag the whole line for now.
                adoc_tag = "admonition"

            combined = (adoc_tag,) + extra_tags if adoc_tag else extra_tags
            self.insert("end", content + "\n", combined)

        end_index = self.index("end-1c")

        # --- INLINE REGEX STYLING ---
        # AsciiDoc inline syntax is processed here.

        # 1. Monospace: `text` or +text+
        # We process this first.
        self._apply_regex(r"`(.*?)`", "monospace", start_index, end_index)
        self._apply_regex(r"\+(.*?)\+", "monospace", start_index, end_index)

        # 2. Strong (Bold): *text*
        # AsciiDoc uses single asterisks for bold.
        # Note: We stripped bullet points (* ) in the line loop,
        # so this regex won't match list items, only inline *bold*.
        self._apply_regex(r"\*(.*?)\*", "strong", start_index, end_index)

        # 3. Emphasis (Italic): _text_
        self._apply_regex(r"_(.*?)_", "emphasis", start_index, end_index)

        self._raise_tags()
        self.configure(state="disabled")

    def _apply_regex(self, pattern, tag, start_index, limit_index):
        """Applies tags to regex matches, hiding delimiters."""
        count = tk.IntVar()
        current_index = start_index

        while True:
            # Search strictly within range
            pos = self.search(pattern, current_index, stopindex=limit_index, count=count, regexp=True)
            if not pos: break

            match_len = count.get()
            end_match = f"{pos}+{match_len}c"

            # Check if we are inside a Listing Block (don't style code blocks!)
            current_tags = self.tag_names(pos)
            if "listing" in current_tags:
                current_index = end_match
                continue

            # Determine delimiter length for hiding
            # For AsciiDoc, most delimiters are 1 char (*, _, `, +)
            d_len = 1

            inner_start = f"{pos}+{d_len}c"
            inner_end = f"{end_match}-{d_len}c"

            self.tag_add(tag, inner_start, inner_end)
            self.tag_add("hidden", pos, inner_start)
            self.tag_add("hidden", inner_end, end_match)

            current_index = end_match
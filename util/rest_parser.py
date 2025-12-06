import tkinter as tk
import tkinter.font as tkfont
from docutils.core import publish_string
from docutils.writers import Writer
from docutils.nodes import NodeVisitor, SkipNode


class TkVisitor(NodeVisitor):
    def __init__(self, document, text_widget, base_tags=()):
        super().__init__(document)
        self.widget = text_widget

        # Handle single tag string vs tuple of tags
        if base_tags is None:
            self.base_tags = ()
        elif isinstance(base_tags, str):
            self.base_tags = (base_tags,)
        else:
            self.base_tags = tuple(base_tags)

        self.section_level = 0
        self.current_tags = []

        # STATE TRACKING (Crucial for wrapping fix)
        self.in_literal_block = False

    # --- Helpers ---
    def _insert(self, text, extra_tags=()):
        """Central insertion method to combine formatting + base tags."""
        # Order: Base Tags (bottom) -> Current Structure (middle) -> Specific Extra (top)
        # Note: Visual priority is handled by _raise_tags(), not tuple order.
        combined_tags = tuple(self.current_tags) + extra_tags + self.base_tags
        self.widget.insert("end", text, combined_tags)

    # --- Core Text ---
    def visit_Text(self, node):
        text = node.astext()

        # If we are NOT in a code block, replace source-code newlines with spaces.
        # This allows Tkinter to calculate line wrapping dynamically based on width.
        if not self.in_literal_block:
            text = text.replace("\n", " ")

        self._insert(text)

    def depart_Text(self, node):
        pass

    # --- Structure (Paragraphs) ---
    def visit_paragraph(self, node):
        pass

    def depart_paragraph(self, node):
        # Only double-space if we are NOT inside a tight container (like a list or field)
        # But for chat, double-spacing usually looks cleaner.
        self._insert("\n\n")

    def visit_section(self, node):
        self.section_level += 1

    def depart_section(self, node):
        self.section_level -= 1

    # --- Headers (Titles) ---
    def visit_title(self, node):
        # We handle headers, but we don't make them MASSIVE.
        # Just bold and distinct.
        if self.section_level == 1:
            self.current_tags.append("h1")
        elif self.section_level == 2:
            self.current_tags.append("h2")
        else:
            self.current_tags.append("h3")

    def depart_title(self, node):
        self.current_tags.pop()
        self._insert("\n")

    # --- Inline Formatting ---
    def visit_strong(self, node):
        self.current_tags.append("strong")

    def depart_strong(self, node):
        self.current_tags.pop()

    def visit_emphasis(self, node):
        self.current_tags.append("emphasis")

    def depart_emphasis(self, node):
        self.current_tags.pop()

    def visit_literal(self, node):
        self.current_tags.append("literal")

    def depart_literal(self, node):
        self.current_tags.pop()

    def visit_reference(self, node):
        self.current_tags.append("link")

    def depart_reference(self, node):
        self.current_tags.pop()

    # --- Code Blocks ---
    def visit_literal_block(self, node):
        self.in_literal_block = True
        self.current_tags.append("literal_block")
        # Ensure distinct line start
        if not self.widget.get("end-2c") == "\n":
            self._insert("\n")

    def depart_literal_block(self, node):
        self.in_literal_block = False
        self.current_tags.pop()
        self._insert("\n")

    # --- Lists ---
    def visit_bullet_list(self, node):
        pass

    def depart_bullet_list(self, node):
        pass

    def visit_enumerated_list(self, node):
        pass

    def depart_enumerated_list(self, node):
        pass

    def visit_list_item(self, node):
        self._insert("\u2022 ", ("bullet",))

    def depart_list_item(self, node):
        pass

    # --- SPECIAL HANDLING: Field Lists (The "User: Hello" Bug) ---
    # Docutils treats "User: Hello" as a metadata field.
    # We strip the "metadata" formatting and print it as normal text.
    def visit_field_list(self, node):
        pass

    def depart_field_list(self, node):
        pass

    def visit_field(self, node):
        pass

    def depart_field(self, node):
        self._insert("\n")

    def visit_field_name(self, node):
        # Print "Name:" in bold, but inline
        self.current_tags.append("strong")
        self._insert(node.astext())
        self.current_tags.pop()
        self._insert(": ")
        raise SkipNode  # Skip standard children processing to avoid double print

    def visit_field_body(self, node):
        # Just visit children (the text) normally
        pass

    def depart_field_body(self, node):
        pass

    # --- Admonitions (Notes, etc) ---
    def visit_admonition(self, node, name=""):
        self.current_tags.append("directive")
        title = name.upper() if name else "NOTE"
        self._insert(f"\n{title}: \n", ("strong",))

    def depart_admonition(self, node):
        self.current_tags.pop()
        self._insert("\n")

    def visit_note(self, node):
        self.visit_admonition(node, "Note")

    def depart_note(self, node):
        self.depart_admonition(node)

    def visit_warning(self, node):
        self.visit_admonition(node, "Warning")

    def depart_warning(self, node):
        self.depart_admonition(node)

    # --- System Messages (Errors) ---
    def visit_system_message(self, node):
        # HIDE errors from the user view.
        # "Normal literature" shouldn't scream XML errors.
        raise SkipNode

    def depart_system_message(self, node):
        pass

    # --- Catch All ---
    def unknown_visit(self, node):
        # Pass through unknown nodes so we see their text content
        pass

    def unknown_departure(self, node):
        pass


class TkWriter(Writer):
    def __init__(self, text_widget, base_tags=()):
        super().__init__()
        self.widget = text_widget
        self.base_tags = base_tags

    def translate(self):
        visitor = TkVisitor(self.document, self.widget, self.base_tags)
        self.document.walkabout(visitor)


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
        # Fonts
        info = self.font_info
        family = info.get("family") if info.get("family") in tkfont.families() else "Helvetica"
        _s = info.get("size")
        size = abs(_s)

        # Headers (Scaled down to fit chat)
        self.tag_config("h1", font=(family, int(size * 1.3), "bold"), spacing3=5)
        self.tag_config("h2", font=(family, int(size * 1.15), "bold"), spacing3=5)
        self.tag_config("h3", font=(family, size, "bold"), spacing3=2)

        # Inline
        self.tag_config("strong", font=(family, size, "bold"))
        self.tag_config("emphasis", font=(family, size, "italic"))
        self.tag_config("link", foreground="blue", underline=True)

        # Code
        self.tag_config("literal", font=("Consolas", size), background="#E0E0E0")
        self.tag_config("literal_block", font=("Consolas", size), background="#F5F5F5", lmargin1=15)

        # Structure
        self.tag_config("directive", background="#E1F5FE", lmargin1=10)
        self.tag_config("bullet", lmargin1=20, lmargin2=30)

    def _raise_tags(self):
        """
        Layering Strategy:
        Bottom: Base Tags (User/System Colors)
        Middle: Block Styles (Code backgrounds)
        Top:    Inline Styles (Bold/Links)
        """
        # 1. Base Structure
        self.tag_raise("bullet")
        self.tag_raise("directive")

        # 2. Blocks
        self.tag_raise("literal_block")

        # 3. Headers
        self.tag_raise("h3")
        self.tag_raise("h2")
        self.tag_raise("h1")

        # 4. Inline (Highest Priority)
        self.tag_raise("strong")
        self.tag_raise("emphasis")
        self.tag_raise("literal")
        self.tag_raise("link")

        # 5. Selection
        self.tag_raise("sel")

    def load_markup(self, source_text, tags=None):
        self.configure(state="normal")

        # Optional: Add double newlines to make "chat" text behave like paragraphs
        # This fixes "Hi\nThere" becoming "Hi There"
        # formatted_text = source_text.replace("\n", "\n\n")

        writer = TkWriter(self, base_tags=tags)

        try:
            # report_level=5 suppresses console warnings
            publish_string(
                source=source_text,
                writer=writer,
                settings_overrides={'report_level': 5}
            )
        except Exception:
            # Absolute fallback: If docutils crashes, just insert text
            err_tags = (tags,) if isinstance(tags, str) and tags else tags
            self.insert("end", source_text + "\n", err_tags)

        self._raise_tags()
        self.configure(state="disabled")

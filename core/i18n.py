import gettext
import sys
from pathlib import Path

def setup_i18n(language_code="en"):
    """
    Installs the _() function globally.
    """
    # Determine the path to the 'locales' folder
    # This logic handles running as a script vs running as a PyInstaller .exe
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).resolve().parent.parent

    locale_path = base_path / "locales"

    try:
        # Tries to load: locales/{language_code}/LC_MESSAGES/base.mo
        # If language is 'en', and no file exists, it falls back to the strings in code.
        lang = gettext.translation('base', localedir=locale_path, languages=[language_code])
        lang.install() # Injects '_' into builtins
    except FileNotFoundError:
        # Fallback: Just return the string as-is if translation missing
        gettext.install('base', localedir=locale_path)
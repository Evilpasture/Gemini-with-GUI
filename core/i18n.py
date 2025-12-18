import gettext
import sys
from pathlib import Path

def get_locale_path():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as .exe - sys._MEIPASS is created by PyInstaller
        base_path = Path(sys._MEIPASS)
    else:
        # Running as script - Go up from core/ to project root
        base_path = Path(__file__).resolve().parent.parent

    return base_path / "locales"

def setup_i18n(language_code="en"):
    """
    Installs the _() function globally.
    """
    locale_path = get_locale_path()

    try:
        lang = gettext.translation('base', localedir=str(locale_path), languages=[language_code])
        lang.install()
    except (FileNotFoundError, OSError):
        print(f"Locale not found in {locale_path}, falling back to default.")
        gettext.install('base', localedir=str(locale_path))

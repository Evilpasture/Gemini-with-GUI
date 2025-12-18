import gettext
import sys
from pathlib import Path

def setup_i18n(language_code="en"):
    """
    Installs the _() function globally.
    """
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).resolve().parent.parent

    locale_path = base_path / "locales"

    try:
        lang = gettext.translation('base', localedir=locale_path, languages=[language_code])
        lang.install() # Injects '_' into builtins
    except FileNotFoundError:
        gettext.install('base', localedir=locale_path)
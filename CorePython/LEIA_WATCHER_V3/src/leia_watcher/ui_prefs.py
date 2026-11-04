"""Private, non-sensitive desktop-only preferences; never changes core config."""
import json
from .config import home,write_atomic
VALID_MODES={'auto','reduced','off'}

def load_mode(default='auto'):
    try:
        value=json.loads((home()/'ui_prefs.json').read_text(encoding='utf8')).get('motion_mode')
        return value if value in VALID_MODES else default
    except (ValueError,OSError,TypeError):return default

def set_mode(mode):
    if mode not in VALID_MODES:raise ValueError('Invalid motion mode')
    write_atomic(home()/'ui_prefs.json',{'motion_mode':mode})

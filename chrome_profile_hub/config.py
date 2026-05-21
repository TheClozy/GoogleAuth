from __future__ import annotations
import os
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CHROME_UA_VERSION = os.environ.get('CHROME_UA_VERSION', '148')
FIXED_USER_AGENT = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CHROME_UA_VERSION}.0.0.0 Safari/537.36'
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
CHROME_STABLE_ARGS = ['--no-first-run', '--no-default-browser-check', '--disable-blink-features=AutomationControlled', '--start-maximized', '--disable-extensions', '--disable-popup-blocking', '--disable-dev-shm-usage', '--lang=tr-TR']
ACCOUNTS_LOGIN_URL = 'https://accounts.google.com/login'
GMAIL_URL = 'https://mail.google.com/mail/u/0/'
DEFAULT_PROFILES_DIRNAME = 'selenium_profiles'

def get_profiles_root() -> Path:
    env = os.environ.get('SELENIUM_PROFILES_DIR')
    if env:
        root = Path(env).expanduser().resolve()
    else:
        project = (PROJECT_ROOT / DEFAULT_PROFILES_DIRNAME).resolve()
        legacy = Path('C:\\selenium_profiles')
        project_meta = project / 'profiles_registry.json'
        legacy_meta = legacy / 'profiles_registry.json'
        use_legacy = legacy_meta.is_file() and (not project_meta.is_file() or project_meta.stat().st_size <= 2)
        root = legacy if use_legacy else project
    root.mkdir(parents=True, exist_ok=True)
    return root

def get_metadata_path(root: Path | None=None) -> Path:
    root = root or get_profiles_root()
    return root / 'profiles_registry.json'

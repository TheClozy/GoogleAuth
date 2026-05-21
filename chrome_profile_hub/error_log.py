from __future__ import annotations
import logging
import traceback
from datetime import datetime
from pathlib import Path
from .config import get_profiles_root
_LOG: logging.Logger | None = None

def get_error_log_path() -> Path:
    return get_profiles_root() / 'errors.log'

def setup_error_file_logging() -> Path:
    global _LOG
    path = get_error_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('chrome_profile_hub.errors')
    if not logger.handlers:
        handler = logging.FileHandler(path, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    _LOG = logger
    return path

def log_error(message: str, exc: BaseException | None=None) -> Path:
    path = setup_error_file_logging()
    logger = _LOG or logging.getLogger('chrome_profile_hub.errors')
    text = message
    if exc:
        text = f'{message}\n{type(exc).__name__}: {exc}\n{traceback.format_exc()}'
    logger.error(text)
    with path.open('a', encoding='utf-8') as f:
        f.write(f'\n--- {datetime.now().isoformat()} ---\n{text}\n')
    return path

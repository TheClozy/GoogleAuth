from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from selenium.common.exceptions import WebDriverException
from .session_guard import is_closed_browser_error
if TYPE_CHECKING:
    import undetected_chromedriver as uc
logger = logging.getLogger(__name__)
COOKIE_FILE = '.session_cookies.json'
_SEED_URLS = ('https://mail.google.com/mail/u/0/', 'https://accounts.google.com/')

def cookie_path(profile_dir: Path) -> Path:
    return profile_dir.resolve() / COOKIE_FILE

def save_session_cookies(driver: 'uc.Chrome', profile_dir: Path) -> int:
    try:
        cookies = driver.get_cookies()
    except WebDriverException as exc:
        if is_closed_browser_error(exc):
            return 0
        raise
    google = [c for c in cookies if any((d in (c.get('domain') or '') for d in ('.google.com', 'google.com', '.google.com.tr', 'mail.google.com')))]
    if not google:
        logger.warning('Google çerezi bulunamadı: %s', profile_dir)
        return 0
    path = cookie_path(profile_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(google, f, indent=0)
    logger.info('%d çerez kaydedildi → %s', len(google), path)
    return len(google)

def load_session_cookies(driver: 'uc.Chrome', profile_dir: Path) -> int:
    path = cookie_path(profile_dir)
    if not path.is_file():
        return 0
    try:
        with path.open(encoding='utf-8') as f:
            cookies: list[dict[str, Any]] = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning('Çerez dosyası okunamadı: %s', exc)
        return 0
    if not cookies:
        return 0
    loaded = 0
    for url in _SEED_URLS:
        try:
            driver.get(url)
            break
        except WebDriverException:
            continue
    for raw in cookies:
        try:
            payload = _to_cdp_cookie(raw)
            driver.execute_cdp_cmd('Network.setCookie', payload)
            loaded += 1
        except WebDriverException as exc:
            if is_closed_browser_error(exc):
                return loaded
            continue
        except Exception:
            continue
    logger.info('%d çerez yüklendi ← %s', loaded, path)
    return loaded

def _to_cdp_cookie(raw: dict[str, Any]) -> dict[str, Any]:
    domain = raw.get('domain') or '.google.com'
    payload: dict[str, Any] = {'name': raw['name'], 'value': raw['value'], 'domain': domain, 'path': raw.get('path', '/'), 'secure': bool(raw.get('secure', True)), 'httpOnly': bool(raw.get('httpOnly', False))}
    if raw.get('sameSite'):
        payload['sameSite'] = raw['sameSite']
    exp = raw.get('expiry') or raw.get('expires')
    if exp is not None:
        try:
            payload['expires'] = float(exp)
        except (TypeError, ValueError):
            pass
    return payload

def profile_has_cookie_backup(profile_dir: Path) -> bool:
    path = cookie_path(profile_dir)
    return path.is_file() and path.stat().st_size > 10

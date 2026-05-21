from __future__ import annotations
import logging
import os
import re
import subprocess
from pathlib import Path
logger = logging.getLogger(__name__)
_CHROME_PATHS = (Path('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'), Path('C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'), Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'Application' / 'chrome.exe')

def _parse_major(version_text: str) -> int | None:
    match = re.search('(\\d+)\\.', version_text)
    if match:
        return int(match.group(1))
    return None

def _from_registry() -> int | None:
    if os.name != 'nt':
        return None
    try:
        import winreg
        for hive, path in ((winreg.HKEY_CURRENT_USER, 'Software\\Google\\Chrome\\BLBeacon'), (winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Google\\Chrome\\BLBeacon'), (winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Wow6432Node\\Google\\Chrome\\BLBeacon')):
            try:
                with winreg.OpenKey(hive, path) as key:
                    version, _ = winreg.QueryValueEx(key, 'version')
                    major = _parse_major(str(version))
                    if major:
                        return major
            except OSError:
                continue
    except Exception as exc:
        logger.debug('Registry Chrome sürümü okunamadı: %s', exc)
    return None

def _from_executable() -> int | None:
    for path in _CHROME_PATHS:
        if not path.is_file():
            continue
        try:
            result = subprocess.run([str(path), '--version'], capture_output=True, text=True, timeout=15, check=False)
            output = (result.stdout or result.stderr or '').strip()
            major = _parse_major(output)
            if major:
                logger.debug('Chrome sürümü %s üzerinden: %s', path, major)
                return major
        except Exception as exc:
            logger.debug('Chrome --version başarısız (%s): %s', path, exc)
    return None

def get_chrome_major_version() -> int | None:
    env = os.environ.get('CHROME_VERSION_MAIN')
    if env:
        try:
            forced = int(env.strip())
            logger.info('Chrome sürümü (ortam değişkeni): %s', forced)
            return forced
        except ValueError:
            logger.warning('CHROME_VERSION_MAIN geçersiz: %s', env)
    major = _from_registry() or _from_executable()
    if major:
        logger.info('Algılanan Chrome sürümü: %s', major)
    else:
        logger.warning('Chrome sürümü algılanamadı; CHROME_VERSION_MAIN ortam değişkenini kullanın.')
    return major

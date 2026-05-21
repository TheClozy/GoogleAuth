from __future__ import annotations
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any
import undetected_chromedriver as uc
from selenium.common.exceptions import WebDriverException
from .chrome_detect import get_chrome_major_version
from .config import ACCOUNTS_LOGIN_URL, CHROME_STABLE_ARGS, FIXED_USER_AGENT, GMAIL_URL
from .cookie_store import load_session_cookies, save_session_cookies
from .session_guard import is_closed_browser_error
logger = logging.getLogger(__name__)
QUIT_FLUSH_SEC = 8
START_SETTLE_SEC = 2

def _kill_chromedriver() -> None:
    if os.name != 'nt':
        return
    subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)

def _kill_stale_chrome(profile_path: Path) -> None:
    if os.name != 'nt':
        return
    marker = str(profile_path.resolve()).lower()
    marker_slash = marker if marker.endswith('\\') else marker + '\\'
    try:
        out = subprocess.check_output(['wmic', 'process', 'where', "name='chrome.exe'", 'get', 'ProcessId,CommandLine'], stderr=subprocess.DEVNULL, text=True, encoding='utf-8', errors='ignore')
        for line in out.splitlines():
            low = line.lower()
            if marker not in low and marker_slash not in low:
                continue
            parts = line.strip().split()
            if parts and parts[-1].isdigit():
                subprocess.run(['taskkill', '/F', '/PID', parts[-1]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        logger.debug('Chrome temizleme atlandı: %s', exc)
    time.sleep(1)

def _wait_unlock(profile_path: Path, sec: int=25) -> None:
    locks = (profile_path / 'SingletonLock', profile_path / 'lockfile', profile_path / 'Default' / 'SingletonLock')
    for _ in range(sec * 2):
        if not any((p.exists() for p in locks)):
            return
        time.sleep(0.5)

def prepare_profile_launch(profile_path: Path) -> None:
    profile_path = profile_path.resolve()
    _kill_chromedriver()
    _kill_stale_chrome(profile_path)
    _wait_unlock(profile_path)

class BrowserSession:

    def __init__(self, profile_path: Path, fingerprint: dict[str, Any] | None=None) -> None:
        self.profile_path = profile_path.resolve()
        self.fingerprint = fingerprint or {}
        self.driver: uc.Chrome | None = None

    def start(self, *, restore_cookies: bool=True) -> uc.Chrome:
        if self.driver:
            return self.driver
        self.profile_path.mkdir(parents=True, exist_ok=True)
        prepare_profile_launch(self.profile_path)
        options = uc.ChromeOptions()
        for arg in CHROME_STABLE_ARGS:
            options.add_argument(arg)
        path_str = str(self.profile_path)
        options.add_argument(f'--user-data-dir={path_str}')
        options.add_argument('--profile-directory=Default')
        ua = self.fingerprint.get('user_agent', FIXED_USER_AGENT)
        options.add_argument(f'--user-agent={ua}')
        version_main = get_chrome_major_version()
        logger.info('user_data_dir=%s', path_str)
        kwargs: dict[str, Any] = {'options': options, 'user_data_dir': path_str, 'use_subprocess': True, 'suppress_welcome': True}
        if version_main:
            kwargs['version_main'] = version_main
        self.driver = uc.Chrome(**kwargs)
        time.sleep(START_SETTLE_SEC)
        if restore_cookies:
            n = load_session_cookies(self.driver, self.profile_path)
            if n:
                logger.info('Çerez yedeği yüklendi (%d)', n)
                time.sleep(1)
        return self.driver

    def go_login(self) -> None:
        assert self.driver
        try:
            self.driver.get(ACCOUNTS_LOGIN_URL)
        except WebDriverException as exc:
            if not is_closed_browser_error(exc):
                raise

    def go_gmail(self) -> None:
        assert self.driver
        try:
            self.driver.get(GMAIL_URL)
        except WebDriverException as exc:
            if not is_closed_browser_error(exc):
                raise

    def persist_session(self) -> int:
        if not self.driver:
            return 0
        return save_session_cookies(self.driver, self.profile_path)

    def quit(self) -> None:
        if not self.driver:
            return
        try:
            save_session_cookies(self.driver, self.profile_path)
        except Exception as exc:
            logger.debug('Çerez kaydı atlandı: %s', exc)
        try:
            self.driver.quit()
        except WebDriverException as exc:
            if not is_closed_browser_error(exc):
                logger.warning('quit: %s', exc)
        except Exception as exc:
            logger.warning('quit: %s', exc)
        self.driver = None
        _kill_chromedriver()
        _wait_unlock(self.profile_path, 30)
        time.sleep(QUIT_FLUSH_SEC)

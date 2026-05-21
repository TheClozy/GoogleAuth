from __future__ import annotations
import logging
import re
import time
from typing import TYPE_CHECKING
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from .config import ACCOUNTS_LOGIN_URL, GMAIL_URL
from .session_guard import is_browser_alive, is_closed_browser_error
if TYPE_CHECKING:
    import undetected_chromedriver as uc
logger = logging.getLogger(__name__)
LOGIN_WAIT_SEC = 300
SESSION_CHECK_SEC = 35
EMAIL_RE = re.compile('[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}')
_SIGNIN_URL_PARTS = ('accounts.google.com/v3/signin', 'accounts.google.com/signin', 'accounts.google.com/login', 'accounts.google.com/servicelogin', 'accounts.google.com/o/oauth2')
_GMAIL_URL_PARTS = ('mail.google.com', 'google.com/mail')
_LOGGED_IN_URL_PARTS = ('myaccount.google.com', 'mail.google.com', 'google.com/mail', 'drive.google.com', 'docs.google.com', 'accounts.google.com/accountchooser', 'accounts.google.com/multilogin')

class LoginError(Exception):
    pass

class LoginTabClosedError(LoginError):
    pass

def _safe_current_url(driver: 'uc.Chrome') -> str:
    try:
        return driver.current_url or ''
    except WebDriverException as exc:
        if is_closed_browser_error(exc):
            return ''
        raise

def _url_lower(driver: 'uc.Chrome') -> str:
    return _safe_current_url(driver).lower()

def _is_signin_url(url: str) -> bool:
    u = url.lower()
    return any((part in u for part in _SIGNIN_URL_PARTS))

def _is_gmail_url(url: str) -> bool:
    u = url.lower()
    return any((part in u for part in _GMAIL_URL_PARTS))

def _is_logged_in_url(url: str) -> bool:
    u = url.lower()
    if _is_signin_url(u):
        return False
    return any((part in u for part in _LOGGED_IN_URL_PARTS))

def _has_login_form(driver: 'uc.Chrome') -> bool:
    url = _url_lower(driver)
    if _is_gmail_url(url) or not _is_signin_url(url):
        return False
    try:
        for sel in ('input[type="email"]', 'input[type="password"]', '#identifierId'):
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed():
                    return True
    except WebDriverException as exc:
        if is_closed_browser_error(exc):
            return False
    except Exception:
        pass
    return False

def _is_challenge_page(driver: 'uc.Chrome') -> bool:
    url = _url_lower(driver)
    return any((x in url for x in ('challenge', 'totp', 'verify', 'ipp', 'captcha')))

def _email_on_current_tab(driver: 'uc.Chrome') -> str | None:
    try:
        for el in driver.find_elements(By.CSS_SELECTOR, '[data-email]'):
            val = (el.get_attribute('data-email') or '').strip().lower()
            if val and EMAIL_RE.fullmatch(val):
                return val
        body = driver.find_element(By.TAG_NAME, 'body').text
        for addr in EMAIL_RE.findall(body):
            low = addr.lower()
            if low.endswith('@gmail.com') or low.endswith('@googlemail.com'):
                return low
    except WebDriverException as exc:
        if is_closed_browser_error(exc):
            return None
    except Exception:
        pass
    return None

def read_email(driver: 'uc.Chrome') -> str | None:
    try:
        handles = list(driver.window_handles)
    except WebDriverException as exc:
        if is_closed_browser_error(exc):
            return None
        raise
    for handle in handles:
        try:
            driver.switch_to.window(handle)
            found = _email_on_current_tab(driver)
            if found:
                return found
        except WebDriverException as exc:
            if is_closed_browser_error(exc):
                continue
            continue
    return None

def gmail_is_open(driver: 'uc.Chrome') -> bool:
    url = _url_lower(driver)
    if not _is_gmail_url(url):
        return False
    if _is_signin_url(url):
        return False
    if _has_login_form(driver):
        return False
    return True

def is_google_session_active(driver: 'uc.Chrome', expected_email: str | None=None) -> bool:
    try:
        handles = list(driver.window_handles)
    except WebDriverException as exc:
        if is_closed_browser_error(exc):
            return False
        raise
    expected = expected_email.strip().lower() if expected_email else None
    found_any_email: str | None = None
    for handle in handles:
        try:
            driver.switch_to.window(handle)
            url = _url_lower(driver)
            if gmail_is_open(driver):
                return True
            if _is_challenge_page(driver):
                return True
            if _is_logged_in_url(url) and (not _has_login_form(driver)):
                return True
            email = _email_on_current_tab(driver)
            if email:
                found_any_email = email
                if expected and email == expected:
                    return True
        except WebDriverException as exc:
            if is_closed_browser_error(exc):
                continue
            continue
    if found_any_email:
        return not expected or found_any_email == expected
    return False

def wait_for_session_ready(driver: 'uc.Chrome', *, expected_email: str | None=None, timeout: int=SESSION_CHECK_SEC) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not is_browser_alive(driver):
            return False
        if is_google_session_active(driver, expected_email):
            return True
        time.sleep(1.2)
    return is_google_session_active(driver, expected_email)

def _scan_tabs(driver: 'uc.Chrome') -> tuple[bool, bool, bool]:
    gmail_ok = False
    has_form = False
    challenge = False
    try:
        handles = list(driver.window_handles)
    except WebDriverException as exc:
        if is_closed_browser_error(exc):
            return (False, False, False)
        raise
    for handle in handles:
        try:
            driver.switch_to.window(handle)
            if gmail_is_open(driver):
                gmail_ok = True
            if _has_login_form(driver):
                has_form = True
            if _is_challenge_page(driver):
                challenge = True
        except WebDriverException as exc:
            if is_closed_browser_error(exc):
                continue
            continue
    return (gmail_ok, has_form, challenge)

def _finish_login(driver: 'uc.Chrome') -> str:
    email = read_email(driver)
    if not email:
        try:
            driver.get(GMAIL_URL)
            time.sleep(3)
            email = read_email(driver)
        except WebDriverException as exc:
            if is_closed_browser_error(exc):
                raise LoginTabClosedError('Tarayıcı kapatıldı.') from exc
            raise
    if not email:
        raise LoginError('E-posta okunamadı.')
    print(f'  Giriş tamam: {email}')
    time.sleep(3)
    return email

def wait_for_manual_login(driver: 'uc.Chrome', *, total_timeout: int=LOGIN_WAIT_SEC) -> str:
    if not is_browser_alive(driver):
        raise LoginTabClosedError('Tarayıcı kapalı.')
    print('  Google hesabınıza giriş yapın.')
    print('  Gmail açılınca otomatik kaydedilip tarayıcı kapanacak.')
    print('  (2FA varsa tarayıcıda tamamlayın, program bekler.)')
    deadline = time.time() + total_timeout
    last_hint = 0.0
    last_gmail_try = 0.0
    while time.time() < deadline:
        if not is_browser_alive(driver):
            raise LoginTabClosedError('Tarayıcı kapatıldı.')
        if is_google_session_active(driver):
            gmail_ok, has_form, challenge = _scan_tabs(driver)
            if gmail_ok or (not has_form and read_email(driver)):
                return _finish_login(driver)
        gmail_ok, has_form, challenge = _scan_tabs(driver)
        if gmail_ok:
            return _finish_login(driver)
        now = time.time()
        if challenge and now - last_hint > 20:
            print('  Doğrulama ekranı algılandı — tarayıcıda tamamlayın...')
            last_hint = now
        if not challenge and (not has_form) and (not gmail_ok) and (now - last_gmail_try > 8):
            last_gmail_try = now
            try:
                driver.get(GMAIL_URL)
                time.sleep(4)
                if gmail_is_open(driver) or is_google_session_active(driver):
                    return _finish_login(driver)
            except WebDriverException as exc:
                if is_closed_browser_error(exc):
                    raise LoginTabClosedError('Tarayıcı kapatıldı.') from exc
        time.sleep(1.5)
    raise LoginError('Giriş zaman aşımı. Gmail açılmadı.')

def confirm_gmail_session(driver: 'uc.Chrome', timeout: int=SESSION_CHECK_SEC, expected_email: str | None=None) -> bool:
    try:
        driver.get(GMAIL_URL)
    except WebDriverException as exc:
        if is_closed_browser_error(exc):
            return False
        raise
    return wait_for_session_ready(driver, expected_email=expected_email, timeout=timeout)

def wait_until_browser_closed(driver: 'uc.Chrome') -> None:
    print('  Kapatmak için tarayıcı penceresini kapatın.')
    while True:
        try:
            if not is_browser_alive(driver):
                return
        except WebDriverException as exc:
            if is_closed_browser_error(exc):
                return
            raise
        time.sleep(0.5)

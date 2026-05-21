from __future__ import annotations
import logging
import sys
import time
from datetime import datetime
from selenium.common.exceptions import WebDriverException
from .arrow_menu import arrow_select
from .browser import BrowserSession
from .cookie_store import load_session_cookies, profile_has_cookie_backup
from .error_log import get_error_log_path, log_error, setup_error_file_logging
from .google_login import LoginError, LoginTabClosedError, confirm_gmail_session, wait_for_manual_login, wait_for_session_ready, wait_until_browser_closed
from .session_guard import is_browser_alive, is_closed_browser_error
from .profile_manager import ProfileError, ProfileManager
from .ui import BOLD, CYAN, DIM, GREEN, RED, RESET, WHITE, YELLOW, clear_screen, print_error, print_header, print_info, print_success
logger = logging.getLogger(__name__)
MAIN_MENU_ITEMS = [('add', 'Yeni hesap ekle', 'Giriş yap · otomatik kayıt'), ('manage', 'Hesapları yönet', 'Aç / sil'), ('exit', 'Çıkış', '')]
CHROME_QUIT_WAIT = 10
POST_LOGIN_SAVE_SEC = 5

def _prompt(text: str) -> str:
    try:
        return input(text).strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)

def _pause(msg: str='\n  Enter...') -> None:
    try:
        input(msg)
    except (EOFError, KeyboardInterrupt):
        pass

class MenuApp:

    def __init__(self, pm: ProfileManager) -> None:
        self.pm = pm
        self._status: str | None = None
        setup_error_file_logging()

    def redraw(self, body: list[str] | None=None) -> None:
        clear_screen()
        print_header(self.pm.root)
        lines: list[str] = []
        if self._status:
            lines += [f'  {GREEN}✔{RESET} {self._status}', '']
            self._status = None
        if body:
            lines.extend(body)
        if lines:
            print('\n'.join(lines))

    def _error(self, title: str, msg: str, exc: BaseException | None=None) -> None:
        log_error(f'{title}: {msg}', exc)
        self.redraw(['', f'{RED}✖ {title}{RESET}', f'  {msg}', '', f'{DIM}Log: {get_error_log_path()}{RESET}'])
        _pause()

    def add_account(self) -> None:
        self.redraw(['', f'{CYAN}  Yeni hesap ekleniyor...{RESET}', ''])
        folder = self.pm.create_profile_folder(None)
        session = BrowserSession(folder)
        try:
            session.start()
            session.go_login()
            email = wait_for_manual_login(session.driver)
            if session.driver:
                confirm_gmail_session(session.driver, expected_email=email, timeout=40)
                session.go_gmail()
                time.sleep(POST_LOGIN_SAVE_SEC)
                n = session.persist_session()
                if n < 3:
                    print_info('Çerez yedeği az — Gmail tam açılana kadar bekleyin.')
        except (LoginTabClosedError, LoginError) as exc:
            session.quit()
            time.sleep(2)
            self.pm.delete_folder(folder)
            self._error('Giriş başarısız', str(exc), exc)
            return
        except WebDriverException as exc:
            session.quit()
            time.sleep(2)
            self.pm.delete_folder(folder)
            if is_closed_browser_error(exc):
                self._error('Giriş başarısız', 'Tarayıcı kapatıldı.', None)
            else:
                self._error('Hata', str(exc), exc)
            return
        except Exception as exc:
            session.quit()
            time.sleep(2)
            self.pm.delete_folder(folder)
            if is_closed_browser_error(exc):
                self._error('Giriş başarısız', 'Tarayıcı kapatıldı.', None)
            else:
                self._error('Hata', str(exc), exc)
            return
        session.quit()
        time.sleep(CHROME_QUIT_WAIT)
        try:
            name, path = self.pm.save_after_login(folder, email, None)
        except ProfileError as exc:
            self.pm.delete_folder(folder)
            self._error('Kayıt hatası', str(exc), exc)
            return
        self._status = f'Hesap eklendi: {name} ({email})'
        self.redraw(['', f'{GREEN}  Tamamlandı{RESET}', f'  Profil: {BOLD}{name}{RESET}', f'  Gmail:  {email}', f'  Klasör: {DIM}{path}{RESET}', ''])
        time.sleep(2)

    def open_browser(self, name: str) -> None:
        meta = self.pm.get_profile(name)
        path = self.pm.get_profile_path(name)
        expected_email = meta.get('email') or None
        session = BrowserSession(path, self.pm.get_fingerprint(name))
        self.redraw(['', f"{CYAN}›{RESET} {BOLD}{name}{RESET} · {expected_email or ''}", f'{DIM}{path}{RESET}', '', f'{DIM}  Gmail yükleniyor...{RESET}'])
        user_closed = False
        try:
            session.start()
            self.pm.touch_last_opened(name)
            try:
                session.go_gmail()
                ready = False
                if session.driver:
                    ready = wait_for_session_ready(session.driver, expected_email=expected_email)
                    if not ready and profile_has_cookie_backup(path):
                        load_session_cookies(session.driver, path)
                        session.go_gmail()
                        ready = wait_for_session_ready(session.driver, expected_email=expected_email, timeout=20)
                    if ready:
                        session.persist_session()
                if ready:
                    self.redraw(['', f"{CYAN}›{RESET} {BOLD}{name}{RESET} · {expected_email or ''}", f'{GREEN}  Oturum hazır — tarayıcıyı kullanın.{RESET}', ''])
                elif session.driver and is_browser_alive(session.driver):
                    self.redraw(['', f'{CYAN}›{RESET} {BOLD}{name}{RESET}', f'{YELLOW}  Gmail yükleniyor; gerekirse tarayıcıda hesabı seçin.{RESET}', ''])
            except WebDriverException as exc:
                if is_closed_browser_error(exc):
                    user_closed = True
                else:
                    raise
            if not user_closed and session.driver:
                wait_until_browser_closed(session.driver)
                user_closed = True
        except (LoginError, LoginTabClosedError) as exc:
            self._error('Tarayıcı', str(exc), exc)
            return
        except WebDriverException as exc:
            if is_closed_browser_error(exc):
                user_closed = True
            else:
                self._error('Tarayıcı', str(exc), exc)
                return
        except Exception as exc:
            if is_closed_browser_error(exc):
                user_closed = True
            else:
                logger.exception('Tarayıcı oturumu')
                self._error('Tarayıcı', str(exc), exc)
                return
        finally:
            try:
                session.quit()
            except Exception:
                pass
        if user_closed:
            self._status = 'Tarayıcı kapatıldı.'

    def _fmt_dt(self, iso: str | None) -> str:
        if not iso or iso == '?':
            return '-'
        try:
            return datetime.fromisoformat(iso.replace('Z', '+00:00')).strftime('%d.%m.%Y %H:%M')
        except ValueError:
            return iso[:16]

    def _row_account(self, p: dict, _sel: bool) -> list[str]:
        return [f"{p['name']}", f"Gmail: {p.get('email', '-')}", f"Son: {self._fmt_dt(p.get('last_opened'))}"]

    def _row_main(self, item: tuple, _sel: bool) -> list[str]:
        return [item[1], item[2]]

    def pick_main(self) -> str | None:
        i = arrow_select(MAIN_MENU_ITEMS, redraw=lambda e: self.redraw(e), title='Ana Menü', render_item=self._row_main, hint='↑↓ Enter · Esc çıkış')
        return None if i is None else MAIN_MENU_ITEMS[i][0]

    def manage_accounts(self) -> None:
        while True:
            profiles = self.pm.list_profiles()
            if not profiles:
                self.redraw()
                print_info('Hesap yok.')
                _pause()
                return
            i = arrow_select(profiles, redraw=lambda e: self.redraw(e), title=f'Hesaplar ({len(profiles)})', render_item=self._row_account, hint='↑↓ Enter · Esc geri')
            if i is None:
                return
            self._account_menu(profiles[i])

    def _account_menu(self, profile: dict) -> None:
        name = profile['name']
        email = profile.get('email', '-')
        actions = ['Tarayıcıyı aç', 'Profili sil', 'Geri']
        while True:
            hdr = ['', f'  {BOLD}{name}{RESET} · {email}', '']
            i = arrow_select(actions, redraw=lambda e: self.redraw(hdr + e), title='İşlem', render_item=lambda a, _s: [a], hint='↑↓ Enter · Esc geri')
            if i is None or i == 2:
                return
            if i == 0:
                self.open_browser(name)
                return
            if i == 1:
                self.redraw(hdr + ['', '  Silmek için: e'])
                if _prompt('  > ').lower() in ('e', 'evet', 'y', 'yes'):
                    try:
                        self.pm.delete_profile(name)
                        self._status = f'{name} silindi.'
                    except ProfileError as exc:
                        self._error('Silme', str(exc))
                return

def run_menu() -> None:
    app = MenuApp(ProfileManager())
    while True:
        act = app.pick_main()
        if act is None or act == 'exit':
            app.redraw()
            print_success('Çıkıldı.')
            break
        if act == 'add':
            app.add_account()
        elif act == 'manage':
            app.manage_accounts()

from __future__ import annotations
from selenium.common.exceptions import WebDriverException
_CLOSED_MARKERS = ('no such window', 'target window already closed', 'web view not found', 'invalid session id', 'disconnected', 'chrome not reachable', 'unable to connect to renderer', 'not connected to devtools', 'session deleted', 'browser has closed')

def is_closed_browser_error(exc: BaseException) -> bool:
    msg = f'{type(exc).__name__}: {exc}'.lower()
    return any((marker in msg for marker in _CLOSED_MARKERS))

def is_browser_alive(driver) -> bool:
    try:
        handles = driver.window_handles
        return bool(handles)
    except WebDriverException as exc:
        if is_closed_browser_error(exc):
            return False
        return False
    except Exception:
        return False

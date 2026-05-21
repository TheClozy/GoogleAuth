from __future__ import annotations
import os
import sys
from collections.abc import Callable
from typing import TypeVar
from .ui import BOLD, CYAN, DIM, GREEN, RESET, YELLOW, enable_ansi
T = TypeVar('T')
_KEY_UP = 'UP'
_KEY_DOWN = 'DOWN'
_KEY_ENTER = 'ENTER'
_KEY_ESC = 'ESC'

def _read_key_windows() -> str | None:
    import msvcrt
    ch = msvcrt.getch()
    if ch in (b'\x00', b'\xe0'):
        ch2 = msvcrt.getch()
        if ch2 == b'H':
            return _KEY_UP
        if ch2 == b'P':
            return _KEY_DOWN
        return None
    if ch in (b'\r', b'\n'):
        return _KEY_ENTER
    if ch == b'\x1b':
        return _KEY_ESC
    return None

def _read_key_posix() -> str | None:
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1) if ch2 == '[' else ''
            if ch2 == '[' and ch3 == 'A':
                return _KEY_UP
            if ch2 == '[' and ch3 == 'B':
                return _KEY_DOWN
            return _KEY_ESC
        if ch in ('\r', '\n'):
            return _KEY_ENTER
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return None

def read_menu_key() -> str | None:
    if os.name == 'nt':
        return _read_key_windows()
    if sys.stdin.isatty():
        try:
            return _read_key_posix()
        except Exception:
            pass
    return None

def arrow_select(items: list[T], *, redraw: Callable[[list[str]], None], title: str, render_item: Callable[[T, bool], list[str]], hint: str='↑↓ seç · Enter onayla · Esc geri', start_index: int=0) -> int | None:
    if not items:
        return None
    enable_ansi()
    index = max(0, min(start_index, len(items) - 1))
    while True:
        lines: list[str] = ['', f'{CYAN}{title}{RESET}', f'{DIM}  {hint}{RESET}', '']
        for i, item in enumerate(items):
            selected = i == index
            for j, row in enumerate(render_item(item, selected)):
                if j == 0:
                    mark = f'{GREEN}▸{RESET}' if selected else ' '
                    style = f'{BOLD}{YELLOW}' if selected else ''
                    lines.append(f'  {mark} {style}{row}{RESET}')
                else:
                    lines.append(f'     {DIM}{row}{RESET}')
            lines.append('')
        redraw(lines)
        key = read_menu_key()
        if key == _KEY_UP:
            index = (index - 1) % len(items)
        elif key == _KEY_DOWN:
            index = (index + 1) % len(items)
        elif key == _KEY_ENTER:
            return index
        elif key == _KEY_ESC:
            return None
        elif key is None:
            redraw(lines + ['', f'{DIM}  Numara (1-{len(items)}, 0=iptal): {RESET}'])
            try:
                raw = input('  > ').strip()
            except (EOFError, KeyboardInterrupt):
                return None
            if raw in ('0', ''):
                return None
            try:
                num = int(raw) - 1
                if 0 <= num < len(items):
                    return num
            except ValueError:
                pass

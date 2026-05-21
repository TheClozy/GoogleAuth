from __future__ import annotations

import os
import sys
from pathlib import Path

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
WHITE = "\033[97m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"

GITHUB_USER = "Clozy"
GITHUB_URL = "https://github.com/TheClozy/GoogleAuth"

_NAME_COLORS = ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[94m", "\033[95m"]

BANNER_LINES = (
    "   _____  ____   ____   _____ _      ______           _    _ _______ _    _ ",
    "  / ____|/ __ \\ / __ \\ / ____| |    |  ____|     /\\  | |  | |__   __| |  | |",
    " | |  __| |  | | |  | | |  __| |    | |__       /  \\ | |  | |  | |  | |__| |",
    " | | |_ | |  | | |  | | | |_ | |    |  __|     / /\\ \\| |  | |  | |  |  __  |",
    " | |__| | |__| | |__| | |__| | |____| |____   / ____ \\ |__| |  | |  | |  | |",
    "  \\_____|\\____/ \\____/ \\_____|______|______| /_/    \\_\\____/   |_|  |_|  |_|",
)


def enable_ansi() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            mode.value |= 4
            kernel32.SetConsoleMode(handle, mode)
    except Exception:
        pass


def _hyperlink(text: str, url: str) -> str:
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def _styled_signature() -> str:
    name = "".join(
        f"{_NAME_COLORS[i % len(_NAME_COLORS)]}{ch}{RESET}" for i, ch in enumerate(GITHUB_USER)
    )
    link = _hyperlink(name, GITHUB_URL)
    return f"{DIM}      {RESET}{BOLD}{WHITE}by @{RESET}{link}{RESET}"


def print_header(profiles_root: Path | None = None) -> None:
    enable_ansi()
    for line in BANNER_LINES:
        print(f"{CYAN}{line}{RESET}")
    print(_styled_signature())
    print()
    if profiles_root:
        print(f"{DIM}  Profil dizini:{RESET} {profiles_root}")
        print()


def print_success(msg: str) -> None:
    print(f"{GREEN}✔{RESET} {msg}")


def print_info(msg: str) -> None:
    print(f"{CYAN}›{RESET} {msg}")


def print_error(msg: str) -> None:
    print(f"\033[91m✖{RESET} {msg}", file=sys.stderr)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")

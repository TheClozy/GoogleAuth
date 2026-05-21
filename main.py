#!/usr/bin/env python3
from __future__ import annotations
import argparse
import logging
import sys
from chrome_profile_hub.cli import run_menu
from chrome_profile_hub.config import get_profiles_root
from chrome_profile_hub.error_log import setup_error_file_logging

def setup_logging(verbose: bool=False) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    log_path = setup_error_file_logging()
    logging.getLogger(__name__).info('Hata günlüğü: %s', log_path)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog='google-auth', description='GoogleAuth — izole Google hesap profilleri')
    parser.add_argument('-v', '--verbose', action='store_true', help='Ayrıntılı log')
    parser.add_argument('--profiles-dir', type=str, default=None, help='Profil kök dizini')
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)
    if args.profiles_dir:
        import os
        os.environ['SELENIUM_PROFILES_DIR'] = args.profiles_dir
    logging.info('Profil kökü: %s', get_profiles_root())
    try:
        run_menu()
    except KeyboardInterrupt:
        print('\nProgram sonlandırıldı.')
        return 130
    return 0
if __name__ == '__main__':
    sys.exit(main())

from __future__ import annotations
import json
import logging
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .config import FIXED_USER_AGENT, WINDOW_HEIGHT, WINDOW_WIDTH, get_metadata_path, get_profiles_root
logger = logging.getLogger(__name__)
SAFE_NAME_PATTERN = re.compile('^[a-zA-Z0-9_\\-\\u00C0-\\u024F\\u0400-\\u04FF]+$')
EMAIL_PATTERN = re.compile('^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$')

class ProfileError(Exception):
    pass

class ProfileManager:

    def __init__(self, root: Path | None=None) -> None:
        self.root = (root or get_profiles_root()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.metadata_path = get_metadata_path(self.root)
        self._registry: dict[str, Any] = self._load_registry()

    def _load_registry(self) -> dict[str, Any]:
        if not self.metadata_path.exists():
            return {'profiles': {}}
        try:
            with self.metadata_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
            reg = data if 'profiles' in data else {'profiles': {}}
            self._warn_duplicate_profile_dirs(reg)
            return reg
        except (json.JSONDecodeError, OSError):
            return {'profiles': {}}

    @staticmethod
    def _warn_duplicate_profile_dirs(registry: dict[str, Any]) -> None:
        seen: dict[str, str] = {}
        for name, meta in registry.get('profiles', {}).items():
            p = str(meta.get('user_data_dir', '')).lower()
            if not p:
                continue
            if p in seen:
                logger.error('Aynı profil klasörü iki hesapta: %s ve %s → %s', seen[p], name, p)
            seen[p] = name

    def _save_registry(self) -> None:
        with self.metadata_path.open('w', encoding='utf-8') as f:
            json.dump(self._registry, f, indent=2, ensure_ascii=False)

    @staticmethod
    def normalize_email(email: str) -> str:
        email = email.strip().lower()
        if not EMAIL_PATTERN.match(email):
            raise ProfileError('Geçerli bir e-posta girin.')
        return email

    @staticmethod
    def validate_name(name: str) -> str:
        name = name.strip()
        if not name or len(name) > 64:
            raise ProfileError('Profil adı 1–64 karakter olmalıdır.')
        if not SAFE_NAME_PATTERN.match(name):
            raise ProfileError('Profil adı yalnızca harf, rakam, tire, alt çizgi içerebilir.')
        return name

    @staticmethod
    def name_from_email(email: str) -> str:
        local = email.split('@', 1)[0].strip().lower()
        name = re.sub('[^a-zA-Z0-9_\\-]', '_', local)
        name = re.sub('_+', '_', name).strip('_')
        if not name:
            raise ProfileError('E-postadan profil adı üretilemedi.')
        return name[:64]

    def resolve_profile_name(self, email: str, requested_name: str | None=None) -> str:
        if requested_name and requested_name.strip():
            base = self.validate_name(requested_name)
        else:
            base = self.name_from_email(email)
        if base not in self._registry['profiles']:
            return base
        n = 2
        while f'{base}_{n}' in self._registry['profiles']:
            n += 1
        return f'{base}_{n}'

    def find_by_email(self, email: str) -> str | None:
        normalized = self.normalize_email(email)
        for name, meta in self._registry['profiles'].items():
            if meta.get('email', '').lower() == normalized:
                return name
        return None

    def get_profile_path(self, name: str) -> Path:
        name = self.validate_name(name)
        if name not in self._registry['profiles']:
            raise ProfileError(f"'{name}' kayıtlı değil.")
        meta = self._registry['profiles'][name]
        path = Path(meta.get('user_data_dir', self.root / name))
        return path.resolve()

    def create_profile_folder(self, requested_name: str | None=None) -> Path:
        if requested_name and requested_name.strip():
            folder = (self.root / self.validate_name(requested_name)).resolve()
        else:
            folder = (self.root / f'_p_{uuid.uuid4().hex[:10]}').resolve()
        folder.mkdir(parents=True, exist_ok=True)
        fp = {'user_agent': FIXED_USER_AGENT, 'window_width': WINDOW_WIDTH, 'window_height': WINDOW_HEIGHT}
        with (folder / '.fingerprint.json').open('w', encoding='utf-8') as f:
            json.dump(fp, f, indent=2)
        return folder

    def save_after_login(self, folder: Path, email: str, requested_name: str | None=None) -> tuple[str, Path]:
        folder = folder.resolve()
        email = self.normalize_email(email)
        if self.find_by_email(email):
            shutil.rmtree(folder, ignore_errors=True)
            raise ProfileError(f'Bu e-posta zaten kayıtlı: {email}')
        name = self.resolve_profile_name(email, requested_name)
        if name in self._registry['profiles']:
            shutil.rmtree(folder, ignore_errors=True)
            raise ProfileError(f"'{name}' adı zaten kullanılıyor.")
        now = datetime.now(timezone.utc).isoformat()
        fingerprint = {'user_agent': FIXED_USER_AGENT, 'window_width': WINDOW_WIDTH, 'window_height': WINDOW_HEIGHT}
        self._registry['profiles'][name] = {'created_at': now, 'last_opened': now, 'login_completed': True, 'email': email, 'user_data_dir': str(folder), 'fingerprint': fingerprint}
        self._save_registry()
        logger.info('Kayıt: %s | %s | %s', name, email, folder)
        return (name, folder)

    def delete_folder(self, folder: Path) -> None:
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)

    def get_profile(self, name: str) -> dict[str, Any]:
        name = self.validate_name(name)
        if name not in self._registry['profiles']:
            raise ProfileError(f"'{name}' kayıtlı değil.")
        meta = dict(self._registry['profiles'][name])
        path = self.get_profile_path(name)
        meta['name'] = name
        meta['path'] = str(path)
        meta['exists_on_disk'] = path.is_dir()
        return meta

    def list_profiles(self) -> list[dict[str, Any]]:
        items = []
        for name, meta in sorted(self._registry['profiles'].items()):
            path = Path(meta.get('user_data_dir', self.root / name))
            items.append({'name': name, 'email': meta.get('email', '-'), 'path': str(path.resolve()), 'created_at': meta.get('created_at', '?'), 'last_opened': meta.get('last_opened'), 'login_completed': meta.get('login_completed', False), 'exists_on_disk': path.is_dir()})
        return items

    def touch_last_opened(self, name: str) -> None:
        name = self.validate_name(name)
        self._registry['profiles'][name]['last_opened'] = datetime.now(timezone.utc).isoformat()
        self._save_registry()

    def get_fingerprint(self, name: str) -> dict[str, Any]:
        name = self.validate_name(name)
        meta = self._registry['profiles'][name]
        if meta.get('fingerprint'):
            return meta['fingerprint']
        path = self.get_profile_path(name) / '.fingerprint.json'
        if path.exists():
            with path.open(encoding='utf-8') as f:
                return json.load(f)
        return {'user_agent': FIXED_USER_AGENT, 'window_width': WINDOW_WIDTH, 'window_height': WINDOW_HEIGHT}

    def delete_profile(self, name: str) -> None:
        name = self.validate_name(name)
        if name not in self._registry['profiles']:
            raise ProfileError(f"'{name}' kayıtlı değil.")
        path = self.get_profile_path(name)
        if path.is_dir():
            shutil.rmtree(path)
        self._registry['profiles'].pop(name, None)
        self._save_registry()

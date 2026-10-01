from __future__ import annotations

from typing import Any, Optional

from core.json_db import JsonDb


class Settings:
    _cache: dict = {}
    _loaded: bool = False

    @classmethod
    def _load(cls) -> None:
        if cls._loaded:
            return
        cls._cache = JsonDb.settings_all()
        cls._loaded = True

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        cls._load()
        return cls._cache.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        cls._load()
        JsonDb.settings_set(key, str(value))
        cls._cache[key] = str(value)

    @classmethod
    def all(cls) -> dict:
        cls._load()
        return cls._cache

    @classmethod
    def reload(cls) -> None:
        cls._loaded = False
        cls._load()

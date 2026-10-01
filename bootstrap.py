"""
Botni ishga tushirishdan oldin bir marta chaqiriladi: bazani (JSON fayllar)
yaratadi, standart sozlamalarni seed qiladi va SUPER_ADMIN_IDS ro'yxatidagi
foydalanuvchilarni admins jadvaliga qo'shadi.
"""
from __future__ import annotations

import datetime

import config
from core.json_db import JsonDb


def bootstrap() -> None:
    JsonDb.init()
    JsonDb.settings_seed(config.DEFAULT_SETTINGS)
    for super_id in config.SUPER_ADMIN_IDS:
        if not JsonDb.first("admins", lambda a: int(a.get("tg_id", 0)) == int(super_id)):
            JsonDb.insert("admins", {
                "tg_id": int(super_id),
                "username": "super",
                "added_at": datetime.datetime.now(config.TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            })

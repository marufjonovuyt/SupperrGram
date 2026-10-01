from __future__ import annotations

import datetime
import re
import secrets
from typing import Optional

import config
from core.json_db import JsonDb


def _now() -> str:
    return datetime.datetime.now(config.TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")


class Helpers:
    @staticmethod
    def money(amount: int) -> str:
        return f"{amount:,.0f}".replace(",", " ") + " so'm"

    @staticmethod
    def is_admin(tg_id: int) -> bool:
        if tg_id in config.SUPER_ADMIN_IDS:
            return True
        return JsonDb.first("admins", lambda a: int(a.get("tg_id", 0)) == tg_id) is not None

    @staticmethod
    def get_or_create_user(from_user: dict) -> dict:
        tg_id = int(from_user["id"])
        user = JsonDb.first("users", lambda u: int(u.get("tg_id", 0)) == tg_id)

        if not user:
            user = JsonDb.insert("users", {
                "tg_id": tg_id,
                "username": from_user.get("username"),
                "first_name": from_user.get("first_name"),
                "balance": 0,
                "stars_pool": 0,
                "banned": 0,
                "state": None,
                "created_at": _now(),
                "last_seen_at": None,
            })
        else:
            user = JsonDb.update("users", int(user["id"]), {
                "username": from_user.get("username"),
                "first_name": from_user.get("first_name"),
                "last_seen_at": _now(),
            })
        return user

    @staticmethod
    def set_state(tg_id: int, state: Optional[dict]) -> None:
        JsonDb.update_where(
            "users",
            lambda u: int(u.get("tg_id", 0)) == tg_id,
            {"state": state},
        )

    @staticmethod
    def get_state(tg_id: int) -> Optional[dict]:
        u = JsonDb.first("users", lambda u: int(u.get("tg_id", 0)) == tg_id)
        return (u or {}).get("state")

    @staticmethod
    def change_balance(user_id: int, delta: int) -> None:
        JsonDb.increment("users", user_id, "balance", delta)

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[dict]:
        return JsonDb.find("users", user_id)

    @staticmethod
    def log_tx(user_id: int, tx_type: str, amount: int, status: str, meta: Optional[dict] = None) -> None:
        JsonDb.insert("transactions", {
            "user_id": user_id,
            "type": tx_type,
            "amount": amount,
            "status": status,
            "meta": meta or {},
            "created_at": _now(),
        })

    @staticmethod
    def parse_int(text: str) -> Optional[int]:
        """So'rov matnidan raqamlarni tozalab olish, masalan "10 000" -> 10000"""
        clean = re.sub(r"[^\d]", "", text or "")
        if clean == "":
            return None
        return int(clean)

    @staticmethod
    def random_id(length: int = 12) -> str:
        return secrets.token_hex((length + 1) // 2)[:length]

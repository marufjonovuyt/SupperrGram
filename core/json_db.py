"""
JsonDb - SQL/PDO o'rnini bosuvchi oddiy fayl (JSON) asosidagi baza.

Hech qanday SQL yoki tashqi DB-server talab qilinmaydi - faqat Python'ning
o'zidagi fayl funksiyalari ishlatiladi.

Har bir "jadval" DB_DIR papkasidagi alohida .json faylda saqlanadi:
    { "next_id": 5, "rows": [ {"id": 1, ...}, {"id": 2, ...} ] }

"settings" jadvali esa oddiy kalit->qiymat obyekti sifatida saqlanadi.

Yozish paytida fcntl.flock() orqali fayl qulflanadi, shuning uchun bir
vaqtning o'zida bir nechta so'rov kelsa ham (masalan webhook) ma'lumot
buzilmaydi.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Callable, Optional

import config

try:
    import fcntl

    HAS_FCNTL = True
except ImportError:  # Windows'da fcntl yo'q - jarayon ichi lock bilan cheklanamiz
    HAS_FCNTL = False

# Bitta jarayon ichida bir nechta asyncio vazifasi bir vaqtda yozmasligi uchun
_process_lock = threading.RLock()


def _dir() -> Path:
    d = config.DB_DIR
    d.mkdir(parents=True, exist_ok=True)
    if not os.access(d, os.W_OK):
        raise RuntimeError(
            f"Baza papkasiga yozish huquqi yo'q: {d}. "
            "Papka ruxsatini (chmod 755/775) tekshiring."
        )
    return d


def _path(table: str) -> Path:
    return _dir() / f"{table}.json"


def _empty_state(table: str) -> dict:
    return {} if table == "settings" else {"next_id": 1, "rows": []}


def _lock(handle, exclusive: bool) -> None:
    if not HAS_FCNTL:
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)


def _unlock(handle) -> None:
    if not HAS_FCNTL:
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class JsonDb:
    """PHP'dagi JsonDb klassining Python porti (barcha metodlar statik)."""

    # ---------------- transact / read (past darajadagi) ----------------

    @staticmethod
    def transact(table: str, fn: Callable[[dict], Any]) -> Any:
        file = _path(table)
        with _process_lock:
            file.touch(exist_ok=True)
            with open(file, "r+", encoding="utf-8") as handle:
                _lock(handle, exclusive=True)
                try:
                    raw = handle.read()
                    try:
                        data = json.loads(raw) if raw.strip() else None
                    except json.JSONDecodeError:
                        data = None
                    if not isinstance(data, dict):
                        data = _empty_state(table)

                    result = fn(data)

                    handle.seek(0)
                    handle.truncate()
                    handle.write(json.dumps(data, ensure_ascii=False, indent=2))
                    handle.flush()
                    os.fsync(handle.fileno())
                finally:
                    _unlock(handle)
        return result

    @staticmethod
    def read(table: str) -> dict:
        file = _path(table)
        if not file.exists():
            return _empty_state(table)
        with open(file, "r", encoding="utf-8") as handle:
            _lock(handle, exclusive=False)
            try:
                raw = handle.read()
            finally:
                _unlock(handle)
        try:
            data = json.loads(raw) if raw.strip() else None
        except json.JSONDecodeError:
            data = None
        if not isinstance(data, dict):
            data = _empty_state(table)
        return data

    # ---------------- "rows" turidagi jadvallar (id bilan) ----------------

    @staticmethod
    def all(table: str) -> list[dict]:
        return JsonDb.read(table).get("rows", [])

    @staticmethod
    def find(table: str, row_id: int) -> Optional[dict]:
        for row in JsonDb.all(table):
            if int(row.get("id", 0)) == int(row_id):
                return row
        return None

    @staticmethod
    def first(table: str, where: Callable[[dict], bool]) -> Optional[dict]:
        for row in JsonDb.all(table):
            if where(row):
                return row
        return None

    @staticmethod
    def where(table: str, where_fn: Callable[[dict], bool]) -> list[dict]:
        return [row for row in JsonDb.all(table) if where_fn(row)]

    @staticmethod
    def insert(table: str, fields: dict) -> dict:
        def _fn(data: dict):
            row_id = data.get("next_id", 1)
            data["next_id"] = row_id + 1
            row = {"id": row_id, **fields}
            data.setdefault("rows", []).append(row)
            return row

        return JsonDb.transact(table, _fn)

    @staticmethod
    def update(table: str, row_id: int, fields: dict) -> Optional[dict]:
        def _fn(data: dict):
            for row in data.get("rows", []):
                if int(row.get("id", 0)) == int(row_id):
                    row.update(fields)
                    return row
            return None

        return JsonDb.transact(table, _fn)

    @staticmethod
    def update_where(table: str, match: Callable[[dict], bool], fields: dict) -> int:
        def _fn(data: dict):
            count = 0
            for row in data.get("rows", []):
                if match(row):
                    row.update(fields)
                    count += 1
            return count

        return JsonDb.transact(table, _fn)

    @staticmethod
    def increment(table: str, row_id: int, field: str, delta: int) -> Optional[dict]:
        def _fn(data: dict):
            for row in data.get("rows", []):
                if int(row.get("id", 0)) == int(row_id):
                    row[field] = int(row.get(field, 0)) + delta
                    return row
            return None

        return JsonDb.transact(table, _fn)

    @staticmethod
    def delete(table: str, row_id: int) -> None:
        def _fn(data: dict):
            data["rows"] = [r for r in data.get("rows", []) if int(r.get("id", 0)) != int(row_id)]
            return None

        JsonDb.transact(table, _fn)

    @staticmethod
    def upsert(table: str, unique_field: str, unique_value: Any, fields: dict) -> dict:
        def _fn(data: dict):
            for row in data.get("rows", []):
                if row.get(unique_field) == unique_value:
                    row.update(fields)
                    return row
            row_id = data.get("next_id", 1)
            data["next_id"] = row_id + 1
            row = {"id": row_id, unique_field: unique_value, **fields}
            data.setdefault("rows", []).append(row)
            return row

        return JsonDb.transact(table, _fn)

    @staticmethod
    def count(table: str, where_fn: Optional[Callable[[dict], bool]] = None) -> int:
        rows = JsonDb.all(table)
        return len([r for r in rows if where_fn(r)]) if where_fn else len(rows)

    @staticmethod
    def sum(table: str, field: str, where_fn: Optional[Callable[[dict], bool]] = None) -> float:
        rows = JsonDb.all(table)
        if where_fn:
            rows = [r for r in rows if where_fn(r)]
        return sum(float(r.get(field, 0) or 0) for r in rows)

    @staticmethod
    def sort_by(rows: list[dict], field: str, direction: str = "ASC") -> list[dict]:
        return sorted(
            rows,
            key=lambda r: (r.get(field) is None, r.get(field)),
            reverse=(direction.upper() == "DESC"),
        )

    @staticmethod
    def paginate(rows: list[dict], limit: int, offset: int = 0) -> list[dict]:
        return rows[offset: offset + limit]

    # ---------------- "settings" jadvali (kalit -> qiymat) ----------------

    @staticmethod
    def settings_all() -> dict:
        return JsonDb.read("settings")

    @staticmethod
    def settings_set(key: str, value: str) -> None:
        def _fn(data: dict):
            data[key] = value
            return None

        JsonDb.transact("settings", _fn)

    @staticmethod
    def settings_seed(defaults: dict) -> None:
        def _fn(data: dict):
            for k, v in defaults.items():
                if k not in data:
                    data[k] = str(v)
            return None

        JsonDb.transact("settings", _fn)

    # ---------------- boshlang'ich sozlash ----------------

    @staticmethod
    def init() -> None:
        _dir()  # papka mavjudligini/yozish huquqini tekshiradi
        tables = [
            "users", "topups", "transactions", "gifts_catalog",
            "pubg_products", "pubg_orders", "sms_countries", "sms_orders", "admins",
        ]
        for t in tables:
            file = _path(t)
            if not file.exists():
                file.write_text(
                    json.dumps(_empty_state(t), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        settings_file = _path("settings")
        if not settings_file.exists():
            settings_file.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")

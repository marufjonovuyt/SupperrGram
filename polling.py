#!/usr/bin/env python3
"""
Webhook o'rniga long-polling orqali botni ishga tushirish (masalan VPS'da):
    python3 polling.py
Doimiy ishlashi uchun screen/tmux yoki systemd/supervisor orqali ishga tushiring.
DIQQAT: bir vaqtning o'zida faqat bittasi ishlashi kerak - webhook.py YOKI
polling.py, ikkalasi emas.
"""
from __future__ import annotations

import asyncio

import config
from bootstrap import bootstrap
from core.telegram import Telegram, close_client
from handlers.router import Router

logger = config.logger

OFFSET_FILE = config.BASE_DIR / "logs" / "offset.txt"


async def main() -> None:
    bootstrap()
    await Telegram.delete_webhook()

    print("SuperGram polling rejimida ishga tushdi...")

    offset = 0
    if OFFSET_FILE.exists():
        try:
            offset = int(OFFSET_FILE.read_text().strip() or 0)
        except ValueError:
            offset = 0

    try:
        while True:
            updates = await Telegram.get_updates(offset, 25)
            if updates.get("ok") and updates.get("result"):
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    OFFSET_FILE.write_text(str(offset))
                    # Har bir update alohida vazifa sifatida ishga tushiriladi -
                    # shu orqali bitta sekin so'rov qolganlarini bloklamaydi.
                    asyncio.create_task(_safe_handle(update))
            await asyncio.sleep(0.3)
    finally:
        await close_client()


async def _safe_handle(update: dict) -> None:
    try:
        await Router.handle_update(update)
    except Exception:  # noqa: BLE001
        logger.exception("Polling: update qayta ishlashda xatolik")
    

if __name__ == "__main__":
    asyncio.run(main())

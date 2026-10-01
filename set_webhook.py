#!/usr/bin/env python3
"""
Webhookni o'rnatish uchun ishga tushiring:
    python3 set_webhook.py https://domeningiz.uz/webhook

Eslatma: domeningiz HTTPS bo'lishi shart (Telegram HTTP webhookni qabul qilmaydi).
"""
from __future__ import annotations

import asyncio
import sys

import config
from core.telegram import Telegram, close_client


async def main() -> None:
    if len(sys.argv) < 2:
        print("Foydalanish: python3 set_webhook.py https://domeningiz.uz/webhook")
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith("https://"):
        print("❌ Webhook manzili https:// bilan boshlanishi kerak.")
        sys.exit(1)

    try:
        result = await Telegram.set_webhook(url)
        if result.get("ok"):
            print(f"✅ Webhook muvaffaqiyatli o'rnatildi: {url}")
            print(f"🔐 Maxfiy token (secret_token): {config.WEBHOOK_SECRET}")
            print("   (bu qiymat webhook.py ichida avtomatik tekshiriladi, qo'lda hech narsa qilish shart emas)")
        else:
            print(f"❌ Xatolik: {result.get('description')}")
    finally:
        await close_client()


if __name__ == "__main__":
    asyncio.run(main())

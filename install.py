#!/usr/bin/env python3
"""
Botni birinchi marta o'rnatish uchun ishga tushiring:
    python3 install.py
"""
from __future__ import annotations

import sys
import traceback

import config
from bootstrap import bootstrap


def main() -> None:
    try:
        bootstrap()
        print(f"✅ Baza muvaffaqiyatli yaratildi: {config.DB_DIR} (oddiy .json fayllar, SQL/SQLite ishlatilmaydi)")
        print("✅ Sozlamalar seed qilindi.")
        print("\nKeyingi qadamlar:")
        print("1. config.py faylida BOT_TOKEN va SUPER_ADMIN_IDS ni to'ldiring (agar hali qilmagan bo'lsangiz)")
        print("   yoki BOT_TOKEN muhit o'zgaruvchisi (environment variable) sifatida bering.")
        print("2. Webhook o'rnatish uchun ishga tushiring: python3 set_webhook.py https://domeningiz.uz/webhook")
        print("   (yoki webhook imkoni bo'lmasa: python3 polling.py)")
        print("3. Botga /start yuboring, so'ng /admin orqali admin panelga kiring.")
        print("4. Admin panelda Checkout / Fragment / Coindrop / Cheap-SMM API kalitlarini kiriting.")
    except Exception as e:  # noqa: BLE001
        print("❌ O'RNATISHDA XATOLIK YUZ BERDI:\n")
        print(str(e))
        print()
        traceback.print_exc()
        print("\nEng ko'p uchraydigan sabablar:")
        print("- 'database' papkasiga (yoki logs/ papkasiga) yozish huquqi yo'q (chmod 755/775)")
        print("- Python versiyasi juda eski (3.11+ tavsiya etiladi)")
        sys.exit(1)


if __name__ == "__main__":
    main()

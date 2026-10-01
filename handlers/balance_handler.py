from __future__ import annotations

import datetime

from core.helpers import Helpers
from core.json_db import JsonDb
from core.keyboards import Keyboards
from core.telegram import Telegram
import config


class BalanceHandler:
    @staticmethod
    async def start(chat_id: int, user: dict) -> None:
        Helpers.set_state(int(user["tg_id"]), {"step": "topup_amount"})
        await Telegram.send_message(
            chat_id,
            "👛 <b>Hisobni to'ldirish</b>\n\nTo'ldirmoqchi bo'lgan summani kiriting (so'mda).\n"
            "Masalan: <code>50000</code>\n\nMinimal: 1 000 so'm, maksimal: 10 000 000 so'm.",
            reply_markup=Keyboards.cancel_inline(),
        )

    @staticmethod
    async def handle_state(chat_id: int, user: dict, state: dict, text: str) -> None:
        if state.get("step") != "topup_amount":
            return

        amount = Helpers.parse_int(text)
        if not amount or amount < 1000 or amount > 10_000_000:
            await Telegram.send_message(chat_id, "❗️ Noto'g'ri summa. 1 000 dan 10 000 000 so'm oralig'ida kiriting.")
            return

        # Yangi to'lov yozuvini bazaga saqlaymiz (status: pending)
        topup = JsonDb.insert("topups", {
            "user_id": user["id"],
            "amount": amount,
            "status": "pending",
            "created_at": datetime.datetime.now(config.TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "paid_at": None,
        })
        topup_id = topup["id"]

        Helpers.set_state(int(user["tg_id"]), None)

        # O'zingizning karta raqamingizni shu yerga yozasiz (yoki config dan olasiz)
        CARD_NUMBER = "9860 1201 1857 8885" # <-- O'z kartangizni yozib qo'ying
        CARD_HOLDER = "Marufjonov A."         # <-- Karta egasining ismi (ixtiyoriy)

        await Telegram.send_message(
            chat_id,
            f"💳 <b>{Helpers.money(amount)}</b> miqdorida to'lov qilish uchun:\n\n"
            f"Quyidagi kartaga aniq summani o'tkazing:\n"
            f"Card: <code>{CARD_NUMBER}</code>\n"
            f"Egasi: {CARD_HOLDER}\n\n"
            f" Pulni o'tkazganingizdan so'ng 1-2 daqiqa ichida balansingiz avtomatik ravishda to'ldiriladi!",
            reply_markup=Keyboards.inline([
                [Keyboards.ibtn("❌ Bekor qilish", f"topup:cancel:{topup_id}", "danger")],
            ]),
        )

    @staticmethod
    async def callback(cq: dict, chat_id: int, message_id: int, user: dict, action: str, param: str) -> None:
        topup_id = int(param) if param else 0
        topup = JsonDb.first(
            "topups",
            lambda t: int(t["id"]) == topup_id and int(t["user_id"]) == int(user["id"]),
        )

        if not topup:
            await Telegram.answer_callback_query(cq["id"], "Topilmadi", True)
            return

        if action == "cancel":
            JsonDb.update("topups", topup_id, {"status": "cancelled"})
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.edit_message_text(chat_id, message_id, "❌ To'lov bekor qilindi.")
            return
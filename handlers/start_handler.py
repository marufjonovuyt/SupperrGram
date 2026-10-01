from __future__ import annotations

import config
from core.keyboards import Keyboards
from core.telegram import Telegram


class StartHandler:
    @staticmethod
    async def start(chat_id: int, user: dict, is_admin: bool) -> None:
        # Agar admin panelning pastki menyusi ochiq qolgan bo'lsa, uni tozalab tashlaymiz
        # (asosiy menyu endi tepada inline tugmalar sifatida chiqadi).
        await Telegram.clear_reply_keyboard(chat_id)

        name = user.get("first_name") or "foydalanuvchi"
        text = (
            f"💯 <b>@{config.BOT_USERNAME}</b> orqali buyurtmalarni kuzatishingiz mumkin\n"
            "😎 Biz bilan ishonchlik va tezkor savdo qiling!\n\n"
            f"Salom, <b>{name}</b>! Kerakli tugmani 👇 tanlang."
        )

        await Telegram.send_message(chat_id, text, reply_markup=Keyboards.main_menu())

        if is_admin:
            await Telegram.send_message(
                chat_id, "🛡 Siz administratorsiz. Boshqaruv paneliga kirish uchun /admin buyrug'ini yuboring."
            )

from __future__ import annotations

from core.helpers import Helpers
from core.keyboards import Keyboards
from core.telegram import Telegram


class PremiumHandler:
    @staticmethod
    async def start(chat_id: int, user: dict) -> None:
        """Telegram Premium sotib olish menyusi"""
        rows = [
            [Keyboards.ibtn("🌟 3 oylik Premium", "premium:pick:3", "success")],
            [Keyboards.ibtn("🌟 6 oylik Premium", "premium:pick:6", "success")],
            [Keyboards.ibtn("🌟 12 oylik Premium", "premium:pick:12", "success")],
            [Keyboards.ibtn("❌ Bekor qilish", "cancel", "danger")]
        ]

        await Telegram.send_message(
            chat_id,
            "💎 <b>Telegram Premium xizmati</b>\n\nObuna muddatini tanlang:",
            reply_markup=Keyboards.inline(rows)
        )

    @staticmethod
    async def callback(cq: dict, chat_id: int, message_id: int, user: dict, action: str, param: str) -> None:
        await Telegram.answer_callback_query(cq["id"])

        if action == "pick":
            months = int(param)
            Helpers.set_state(int(user["tg_id"]), {"step": "premium_username", "months": months})
            
            await Telegram.edit_message_text(
                chat_id, message_id,
                f"🌟 <b>{months} oylik</b> Telegram Premium tanlandi.\n\n"
                "Kimga sovg'a qilmoqchisiz? Telegram username kiriting (masalan: <code>@username</code>):"
            )
            return

    @staticmethod
    async def handle_state(chat_id: int, user: dict, state: dict, text: str) -> None:
        step = state.get("step")
        
        if step == "premium_username":
            username = text.strip().lstrip("@")
            months = state.get("months", 3)
            
            Helpers.set_state(int(user["tg_id"]), None)
            
            await Telegram.send_message(
                chat_id,
                f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
                f"🎁 Xizmat: Telegram Premium ({months} oy)\n"
                f"👤 Qabul qiluvchi: @{username}\n\n"
                f"Buyurtma navbatga qo'shildi.",
                reply_markup=Keyboards.main_menu()
            )
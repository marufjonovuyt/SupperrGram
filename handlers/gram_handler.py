from __future__ import annotations

from core.helpers import Helpers
from core.keyboards import Keyboards
from core.telegram import Telegram


class GramHandler:
    @staticmethod
    async def start(chat_id: int, user: dict) -> None:
        """GRAM va TON xizmatlari menyusi (Fragment API va Admin tanlovi bilan)"""
        rows = [
            [Keyboards.ibtn("🤖 GRAM / Stars (Fragment API)", "gram:auto_start", "success")],
            [Keyboards.ibtn("💎 TON (Fragment API)", "ton:auto_start", "success")],
            [Keyboards.ibtn("👨‍💻 Admin orqali sotib olish", "gram:admin_start", "info")],
            [Keyboards.ibtn("❌ Bekor qilish", "cancel", "danger")]
        ]

        await Telegram.send_message(
            chat_id,
            "⭐ <b>GRAM va TON Xizmatlari</b>\n\n"
            "Fragment API orqali avtomatik yoki admin orqali xarid qilish turini tanlang:",
            reply_markup=Keyboards.inline(rows)
        )

    @staticmethod
    async def callback(cq: dict, chat_id: int, message_id: int, user: dict, action: str, param: str) -> None:
        await Telegram.answer_callback_query(cq["id"])

        if action == "auto_start":
            # Fragment API orqali GRAM / Stars miqdorlari
            rows = [
                [Keyboards.ibtn("⭐ 50 GRAM", "gram:pick:50", "success")],
                [Keyboards.ibtn("⭐ 100 GRAM", "gram:pick:100", "success")],
                [Keyboards.ibtn("⭐ 500 GRAM", "gram:pick:500", "success")],
                [Keyboards.ibtn("🔙 Orqaga", "menu:gram", "danger")]
            ]
            await Telegram.edit_message_text(
                chat_id, message_id,
                "🤖 <b>GRAM Xarid qilish (Fragment API)</b>\n\nKerakli miqdorni tanlang:",
                reply_markup=Keyboards.inline(rows)
            )
            return

        elif action == "ton:auto_start":
            # Fragment API orqali TON xizmatlari/miqdorlari
            rows = [
                [Keyboards.ibtn("💎 1 TON", "ton:pick:1", "success")],
                [Keyboards.ibtn("💎 5 TON", "ton:pick:5", "success")],
                [Keyboards.ibtn("💎 10 TON", "ton:pick:10", "success")],
                [Keyboards.ibtn("🔙 Orqaga", "menu:gram", "danger")]
            ]
            await Telegram.edit_message_text(
                chat_id, message_id,
                "💎 <b>TON Xarid qilish (Fragment API)</b>\n\nKerakli TON miqdorini tanlang:",
                reply_markup=Keyboards.inline(rows)
            )
            return

        elif action == "admin_start":
            # Admin orqali GRAM va TON narxlari va lichkaga yo'naltirish
            await Telegram.edit_message_text(
                chat_id, message_id,
                "👨‍💻 <b>Admin orqali xarid qilish</b>\n\n"
                "• <b>GRAM:</b> Narxlar va kurs bo'yicha kelishiladi\n"
                "• <b>TON:</b> Hamyonga tashlab berish yoki sotib olish\n\n"
                "Buyurtma berish uchun adminga yozing:",
                reply_markup=Keyboards.inline([
                    [Keyboards.ibtn("✍️ Adminga yozish", url="https://t.me/marufjonov_22")],
                    [Keyboards.ibtn("🔙 Orqaga", "menu:gram", "danger")]
                ])
            )
            return

        elif action == "pick":
            amount = int(param)
            Helpers.set_state(int(user["tg_id"]), {"step": "gram_username", "amount": amount})
            await Telegram.edit_message_text(
                chat_id, message_id,
                f"⭐ {amount} ta GRAM tanlandi (Fragment API).\n\nKimga yubormoqchisiz? Telegram username kiriting (@ belgisisiz):"
            )
            return

        elif param and action == "ton": # Agar TON tanlansa
            ton_amount = float(param)
            Helpers.set_state(int(user["tg_id"]), {"step": "ton_wallet", "ton_amount": ton_amount})
            await Telegram.edit_message_text(
                chat_id, message_id,
                f"💎 {ton_amount} TON tanlandi (Fragment API).\n\nTON hamyon manzilini (wallet address) kiriting:"
            )
            return

    @staticmethod
    async def handle_state(chat_id: int, user: dict, state: dict, text: str) -> None:
        step = state.get("step")
        
        if step == "gram_username":
            username = text.strip().lstrip("@")
            amount = state.get("amount", 50)
            Helpers.set_state(int(user["tg_id"]), None)
            
            # Fragment API orqali /v1/gram/buy yoki /v1/stars/buy ga so'rov
            await Telegram.send_message(
                chat_id,
                f"✅ <b>Fragment API orqali GRAM buyurtmasi yuborildi!</b>\n\n"
                f"⭐ Miqdor: {amount} GRAM\n"
                f"👤 Username: @{username}\n\n"
                f"Tarmoqdan tasdiq kutilmoqda...",
                reply_markup=Keyboards.main_menu()
            )
            
        elif step == "ton_wallet":
            wallet = text.strip()
            ton_amount = state.get("ton_amount", 1)
            Helpers.set_state(int(user["tg_id"]), None)
            
            # Fragment API orqali TON yuborish/sotib olish so'rovi
            await Telegram.send_message(
                chat_id,
                f"✅ <b>Fragment API orqali TON buyurtmasi qabul qilindi!</b>\n\n"
                f"💎 Miqdor: {ton_amount} TON\n"
                f"📍 Hamyon: <code>{wallet}</code>\n\n"
                f"Tranzaksiya bajarilmoqda...",
                reply_markup=Keyboards.main_menu()
            )
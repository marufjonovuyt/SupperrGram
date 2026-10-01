from __future__ import annotations

from core.keyboards import Keyboards
from core.settings import Settings
from core.telegram import Telegram


class GramHandler:
    @staticmethod
    async def buy(chat_id: int, user: dict) -> None:
        await GramHandler.route_to_admin(chat_id, "gram_buy_admin", "💎 Gram olish")

    @staticmethod
    async def sell(chat_id: int, user: dict) -> None:
        await GramHandler.route_to_admin(chat_id, "gram_sell_admin", "💎 Gram sotish")

    @staticmethod
    async def route_to_admin(chat_id: int, setting_key: str, service_title: str) -> None:
        """
        Foydalanuvchini admin panelda belgilangan admin kontaktiga yo'naltirish
        (Gram olish/sotish, NFT sotish, Kanal sotish shu orqali ishlaydi)
        """
        admin = str(Settings.get(setting_key, "") or "").strip()
        if admin == "":
            await Telegram.send_message(
                chat_id,
                f"⚠️ <b>{service_title}</b> xizmati hozircha sozlanmagan. Iltimos, birozdan so'ng qayta urinib ko'ring.",
            )
            return
        username = admin.lstrip("@")
        await Telegram.send_message(
            chat_id,
            f"🤝 <b>{service_title}</b>\n\nUshbu xizmat bo'yicha savdo mas'ul menejerimiz orqali amalga oshiriladi.\n"
            "Quyidagi tugma orqali menejer bilan bog'laning va shartlarni kelishib oling.",
            reply_markup=Keyboards.inline([
                [Keyboards.url_btn("👨‍💼 Menejer bilan bog'lanish", f"https://t.me/{username}", "primary")],
            ]),
        )

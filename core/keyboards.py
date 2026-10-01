"""
Barcha klaviaturalar shu yerda yig'ilgan.
Bot API 9.4 (09.02.2026) dan boshlab KeyboardButton/InlineKeyboardButton
`style` maydonini qo'llab-quvvatlaydi: "primary" (ko'k), "danger" (qizil),
"success" (yashil).
"""
from __future__ import annotations

from typing import Optional


class Keyboards:
    @staticmethod
    def _btn(text: str, style: Optional[str] = None) -> dict:
        b: dict = {"text": text}
        if style:
            b["style"] = style
        return b

    @staticmethod
    def main_menu() -> dict:
        """Asosiy foydalanuvchi menyusi - rangli inline tugmalar."""
        return Keyboards.inline([
            [Keyboards.ibtn("👛 Xisob to'ldirish", "menu:topup", "danger")],
            [Keyboards.ibtn("💎 Gram olish", "menu:gram_buy", "primary"),
             Keyboards.ibtn("💎 Gram sotish", "menu:gram_sell", "primary")],
            [Keyboards.ibtn("⭐ Stars olish", "menu:stars_buy", "success"),
             Keyboards.ibtn("⭐ Stars sotish", "menu:stars_sell", "success")],
            [Keyboards.ibtn("🧸 Gift olish", "menu:gift", "success"),
             Keyboards.ibtn("🎭 NFT sotish", "menu:nft_sell", "success")],
            [Keyboards.ibtn("⭐️ Premium olish", "menu:premium", "success"),
             Keyboards.ibtn("📡 Kanal sotish", "menu:channel_sell", "success")],
            [Keyboards.ibtn("🎮 Pubg UC olish", "menu:pubg", "danger"),
             Keyboards.ibtn("📱 Nomer olish", "menu:number", "danger")],
            [Keyboards.ibtn("👛 Xisobim", "menu:account"), Keyboards.ibtn("🆘 Yordam", "menu:help")],
        ])

    @staticmethod
    def admin_menu() -> dict:
        """Admin panel pastki menyusi (faqat admin uchun)."""
        keyboard = [
            [Keyboards._btn("📊 1. Statistika"), Keyboards._btn("💳 2. To'lovlar holati")],
            [Keyboards._btn("🧾 3. Checkout API"), Keyboards._btn("🌐 4. Fragment API")],
            [Keyboards._btn("🎮 5. Coindrop API"), Keyboards._btn("🎁 6. Gift import")],
            [Keyboards._btn("⭐ 7. Bot hisobini to'ldirish"), Keyboards._btn("🔌 8. Bot ON/OFF")],
            [Keyboards._btn("📱 9. Cheap-SMS API"), Keyboards._btn("👥 Foydalanuvchilar")],
            [Keyboards._btn("⚙️ Menejerlar"), Keyboards._btn("🚪 10. Chiqish")],
        ]
        return {"keyboard": keyboard, "resize_keyboard": True, "is_persistent": True}

    @staticmethod
    def remove() -> dict:
        return {"remove_keyboard": True}

    @staticmethod
    def inline(rows: list) -> dict:
        return {"inline_keyboard": rows}

    @staticmethod
    def ibtn(text: str, callback: str, style: Optional[str] = None) -> dict:
        b: dict = {"text": text, "callback_data": callback}
        if style:
            b["style"] = style
        return b

    @staticmethod
    def url_btn(text: str, url: str, style: Optional[str] = None) -> dict:
        b: dict = {"text": text, "url": url}
        if style:
            b["style"] = style
        return b

    @staticmethod
    def webapp_btn(text: str, url: str, style: Optional[str] = None) -> dict:
        b: dict = {"text": text, "web_app": {"url": url}}
        if style:
            b["style"] = style
        return b

    @staticmethod
    def cancel_inline() -> dict:
        return Keyboards.inline([[Keyboards.ibtn("❌ Bekor qilish", "cancel", "danger")]])

    @staticmethod
    def back_inline(to: str) -> dict:
        return Keyboards.inline([[Keyboards.ibtn("◀️ Orqaga", to)]])

from __future__ import annotations

from core.helpers import Helpers
from core.json_db import JsonDb
from core.keyboards import Keyboards
from core.telegram import Telegram

LABELS = {
    "topup": "👛 Hisob to'ldirish",
    "stars_buy": "⭐ Stars olish",
    "premium_buy": "⭐️ Premium olish",
    "gift_buy": "🧸 Gift olish",
    "pubg_uc": "🎮 Pubg UC",
    "number_buy": "📱 Nomer olish",
}


class AccountHandler:
    @staticmethod
    async def show(chat_id: int, user: dict) -> None:
        fresh = Helpers.get_user_by_id(user["id"])
        txs = JsonDb.where("transactions", lambda t: int(t["user_id"]) == int(user["id"]))
        txs = JsonDb.sort_by(txs, "id", "DESC")
        txs = JsonDb.paginate(txs, 10)

        text = (
            "👛 <b>Mening hisobim</b>\n\n"
            f"🆔 ID: <code>{fresh['tg_id']}</code>\n"
            f"👤 Username: {'@' + fresh['username'] if fresh.get('username') else '—'}\n"
            f"💰 Balans: <b>{Helpers.money(int(fresh['balance']))}</b>\n"
            f"📅 Ro'yxatdan o'tgan: {fresh['created_at']}\n\n"
            "🧾 <b>So'nggi amaliyotlar:</b>\n"
        )

        if not txs:
            text += "— hozircha amaliyotlar yo'q —"
        else:
            for t in txs:
                label = LABELS.get(t["type"], t["type"])
                sign = "+" if t["amount"] >= 0 else ""
                status_icon = "✅" if t["status"] == "success" else ("❌" if t["status"] == "failed" else "⏳")
                text += f"\n{status_icon} {label}: {sign}{Helpers.money(int(t['amount']))} <i>({t['created_at']})</i>"

        await Telegram.send_message(chat_id, text, reply_markup=Keyboards.main_menu())

    @staticmethod
    async def help(chat_id: int) -> None:
        await Telegram.send_message(
            chat_id,
            "🆘 <b>Yordam</b>\n\nSavollaringiz bo'lsa, admin bilan bog'laning yoki botdagi bo'limlar orqali "
            "xizmatlardan foydalaning.\n\n"
            "💡 Har bir xarid hisobingizdagi balansdan amalga oshiriladi. Avval \"👛 Xisob to'ldirish\" orqali "
            "hisobingizni to'ldiring.",
        )

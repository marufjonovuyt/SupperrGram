from __future__ import annotations

import re

from api.fragment_api import FragmentApi
from core.helpers import Helpers
from core.keyboards import Keyboards
from core.telegram import Telegram
from handlers.gram_handler import GramHandler

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")


class StarsHandler:
    @staticmethod
    async def buy_start(chat_id: int, user: dict) -> None:
        Helpers.set_state(int(user["tg_id"]), {"step": "stars_amount"})
        await Telegram.send_message(
            chat_id,
            "⭐ <b>Stars olish</b>\n\nNecha dona Stars sotib olmoqchisiz? Miqdorni kiriting.\nMasalan: <code>100</code>",
            reply_markup=Keyboards.cancel_inline(),
        )

    @staticmethod
    async def sell(chat_id: int, user: dict) -> None:
        await GramHandler.route_to_admin(chat_id, "stars_sell_admin", "⭐ Stars sotish")

    @staticmethod
    async def handle_state(chat_id: int, user: dict, state: dict, text: str) -> None:
        tg_id = int(user["tg_id"])

        if state.get("step") == "stars_amount":
            amount = Helpers.parse_int(text)
            if not amount or amount < 1:
                await Telegram.send_message(chat_id, "❗️ Iltimos, to'g'ri miqdor kiriting. Masalan: 100")
                return

            pricing = await FragmentApi.stars_pricing(amount)
            if not pricing.get("ok"):
                err_msg = pricing.get("message") or "noma'lum xato"
                await Telegram.send_message(chat_id, f"⚠️ Narxni olishda xatolik: {err_msg}")
                Helpers.set_state(tg_id, None)
                return

            result = pricing["result"]
            real_amount = int(result["amount"])
            usd = float((result.get("price") or {}).get("usd", 0))
            price_uzs = FragmentApi.usd_to_uzs_with_markup(usd)

            Helpers.set_state(tg_id, {"step": "stars_username", "amount": real_amount, "price_uzs": price_uzs})
            await Telegram.send_message(
                chat_id,
                f"⭐ <b>{real_amount} Stars</b> narxi: <b>{Helpers.money(price_uzs)}</b>\n\n"
                "Kimga yubormoqchisiz? Telegram username kiriting (@ belgisisiz).\nMasalan: <code>durov</code>",
                reply_markup=Keyboards.cancel_inline(),
            )
            return

        if state.get("step") == "stars_username":
            username = text.strip().lstrip("@")
            if username == "" or not USERNAME_RE.match(username):
                await Telegram.send_message(chat_id, "❗️ Username noto'g'ri. Faqat lotin harflar, raqam va _ bo'lishi mumkin.")
                return

            info = await FragmentApi.get_info(username)
            if not info.get("ok"):
                await Telegram.send_message(chat_id, f"⚠️ Bunday foydalanuvchi topilmadi yoki Fragment xizmatida xato: {info.get('message', '')}")
                return

            amount = state["amount"]
            price_uzs = state["price_uzs"]
            name = (info.get("result") or {}).get("name", username)

            Helpers.set_state(int(user["tg_id"]), None)
            await Telegram.send_message(
                chat_id,
                f"✅ Foydalanuvchi topildi: <b>{name}</b> (@{username})\n"
                f"⭐ Miqdor: <b>{amount}</b>\n"
                f"💵 Narx: <b>{Helpers.money(price_uzs)}</b>\n\nTasdiqlaysizmi?",
                reply_markup=Keyboards.inline([
                    [Keyboards.ibtn("✅ Tasdiqlash", f"stars:confirm:{amount}|{price_uzs}|{username}", "success")],
                    [Keyboards.ibtn("❌ Bekor qilish", "cancel", "danger")],
                ]),
            )

    @staticmethod
    async def callback(cq: dict, chat_id: int, message_id: int, user: dict, action: str, param: str) -> None:
        if action != "confirm":
            await Telegram.answer_callback_query(cq["id"])
            return

        amount_s, price_s, username = param.split("|", 2)
        amount = int(amount_s)
        price_uzs = int(price_s)

        fresh = Helpers.get_user_by_id(user["id"])
        if fresh["balance"] < price_uzs:
            await Telegram.answer_callback_query(cq["id"], "Balansingiz yetarli emas!", True)
            await Telegram.edit_message_text(
                chat_id, message_id,
                f"❌ Balansingiz yetarli emas. Avval hisobingizni to'ldiring.\n"
                f"Kerak: {Helpers.money(price_uzs)}\nMavjud: {Helpers.money(fresh['balance'])}",
            )
            return

        await Telegram.answer_callback_query(cq["id"], "⏳ Yuborilmoqda...")
        await Telegram.edit_message_text(chat_id, message_id, "⏳ Stars yuborilmoqda, biroz kuting...")

        result = await FragmentApi.buy_stars(amount, username)
        if result.get("ok"):
            Helpers.change_balance(user["id"], -price_uzs)
            Helpers.log_tx(user["id"], "stars_buy", -price_uzs, "success", {"amount": amount, "to": username})
            await Telegram.edit_message_text(
                chat_id, message_id,
                f"✅ <b>{amount} Stars</b> muvaffaqiyatli @{username} ga yuborildi!\n💵 Yechildi: {Helpers.money(price_uzs)}",
            )
        else:
            Helpers.log_tx(user["id"], "stars_buy", 0, "failed", {"amount": amount, "to": username, "error": result.get("message", "")})
            err_msg = result.get("message") or "noma'lum xato"
            await Telegram.edit_message_text(
                chat_id, message_id,
                f"❌ Xatolik: {err_msg}\nBalansingizdan hech narsa yechilmadi.",
            )

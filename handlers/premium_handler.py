from __future__ import annotations

import re

from api.fragment_api import FragmentApi
from core.helpers import Helpers
from core.keyboards import Keyboards
from core.telegram import Telegram

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")


class PremiumHandler:
    @staticmethod
    async def start(chat_id: int, user: dict) -> None:
        pricing = await FragmentApi.premium_pricing()
        if not pricing.get("ok"):
            await Telegram.send_message(chat_id, "⚠️ Premium narxlarini olishda xatolik. Birozdan so'ng urinib ko'ring.")
            return
        packages = (pricing.get("result") or {}).get("packages") or []
        if not packages:
            await Telegram.send_message(chat_id, "⚠️ Hozircha Premium paketlari mavjud emas.")
            return

        rows = []
        for pkg in packages:
            months = int(pkg["months"])
            usd = float(pkg["usd"])
            price_uzs = FragmentApi.usd_to_uzs_with_markup(usd)
            rows.append([Keyboards.ibtn(
                f"⭐️ {months} oy — {Helpers.money(price_uzs)}",
                f"premium:pick:{months}|{price_uzs}",
                "success",
            )])
        rows.append([Keyboards.ibtn("❌ Bekor qilish", "cancel", "danger")])

        await Telegram.send_message(chat_id, "⭐️ <b>Telegram Premium olish</b>\n\nKerakli muddatni tanlang:", reply_markup=Keyboards.inline(rows))

    @staticmethod
    async def callback(cq: dict, chat_id: int, message_id: int, user: dict, action: str, param: str) -> None:
        if action == "pick":
            months_s, price_s = param.split("|", 1)
            months, price_uzs = int(months_s), int(price_s)
            Helpers.set_state(int(user["tg_id"]), {"step": "premium_username", "months": months, "price_uzs": price_uzs})
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.edit_message_text(
                chat_id, message_id,
                f"⭐️ {months} oylik Premium — {Helpers.money(price_uzs)}\n\n"
                "Kimga yubormoqchisiz? Telegram username kiriting (@ belgisisiz).",
            )
            return

        if action == "confirm":
            months_s, price_s, username = param.split("|", 2)
            months, price_uzs = int(months_s), int(price_s)

            fresh = Helpers.get_user_by_id(user["id"])
            if fresh["balance"] < price_uzs:
                await Telegram.answer_callback_query(cq["id"], "Balansingiz yetarli emas!", True)
                await Telegram.edit_message_text(
                    chat_id, message_id,
                    f"❌ Balansingiz yetarli emas.\nKerak: {Helpers.money(price_uzs)}\nMavjud: {Helpers.money(fresh['balance'])}",
                )
                return

            await Telegram.answer_callback_query(cq["id"], "⏳ Yuborilmoqda...")
            await Telegram.edit_message_text(chat_id, message_id, "⏳ Premium buyurtma qilinmoqda...")

            result = await FragmentApi.buy_premium(months, username)
            if result.get("ok"):
                Helpers.change_balance(user["id"], -price_uzs)
                Helpers.log_tx(user["id"], "premium_buy", -price_uzs, "success", {"months": months, "to": username})
                await Telegram.edit_message_text(
                    chat_id, message_id,
                    f"✅ <b>{months} oylik Telegram Premium</b> @{username} ga muvaffaqiyatli yuborildi!\n💵 Yechildi: {Helpers.money(price_uzs)}",
                )
            else:
                err_msg = result.get("message") or "noma'lum xato"
                Helpers.log_tx(user["id"], "premium_buy", 0, "failed", {"months": months, "to": username, "error": result.get("message", "")})
                await Telegram.edit_message_text(chat_id, message_id, f"❌ Xatolik: {err_msg}")

    @staticmethod
    async def handle_state(chat_id: int, user: dict, state: dict, text: str) -> None:
        if state.get("step") != "premium_username":
            return

        username = text.strip().lstrip("@")
        if username == "" or not USERNAME_RE.match(username):
            await Telegram.send_message(chat_id, "❗️ Username noto'g'ri. Qaytadan kiriting.")
            return

        info = await FragmentApi.get_info(username)
        if not info.get("ok"):
            err_msg = info.get("message") or ""
            await Telegram.send_message(chat_id, f"⚠️ Bunday foydalanuvchi topilmadi: {err_msg}")
            return

        name = (info.get("result") or {}).get("name", username)
        months, price_uzs = state["months"], state["price_uzs"]
        Helpers.set_state(int(user["tg_id"]), None)

        await Telegram.send_message(
            chat_id,
            f"✅ Foydalanuvchi: <b>{name}</b> (@{username})\n⭐️ Muddat: {months} oy\n"
            f"💵 Narx: {Helpers.money(price_uzs)}\n\nTasdiqlaysizmi?",
            reply_markup=Keyboards.inline([
                [Keyboards.ibtn("✅ Tasdiqlash", f"premium:confirm:{months}|{price_uzs}|{username}", "success")],
                [Keyboards.ibtn("❌ Bekor qilish", "cancel", "danger")],
            ]),
        )

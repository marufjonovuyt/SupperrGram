from __future__ import annotations

import datetime
import re
import time

from api.playpay_api import CoindropApi
from core.helpers import Helpers
from core.json_db import JsonDb
from core.keyboards import Keyboards
from core.settings import Settings
from core.telegram import Telegram
import config

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")


class GiftHandler:
    PER_PAGE = 6

    @staticmethod
    async def start(chat_id: int, user: dict, page: int = 0) -> None:
        all_active = JsonDb.where("gifts_catalog", lambda g: int(g.get("active", 0)) == 1)
        all_active = JsonDb.sort_by(all_active, "sell_price_uzs", "ASC")
        gifts = JsonDb.paginate(all_active, GiftHandler.PER_PAGE, page * GiftHandler.PER_PAGE)

        if not gifts:
            await Telegram.send_message(chat_id, "🧸 Hozircha sovg'alar ro'yxati mavjud emas. Iltimos, birozdan so'ng qayta urinib ko'ring.")
            return

        rows = []
        for g in gifts:
            rows.append([Keyboards.ibtn(
                f"{g['emoji']} {g['stars']}⭐ — {Helpers.money(g['sell_price_uzs'])}",
                f"gift:pick:{g['id']}",
                "success",
            )])

        nav = []
        if page > 0:
            nav.append(Keyboards.ibtn("◀️ Oldingi", f"gift:page:{page - 1}"))
        total = len(all_active)
        if (page + 1) * GiftHandler.PER_PAGE < total:
            nav.append(Keyboards.ibtn("Keyingisi ▶️", f"gift:page:{page + 1}"))
        if nav:
            rows.append(nav)
        rows.append([Keyboards.ibtn("❌ Bekor qilish", "cancel", "danger")])

        await Telegram.send_message(chat_id, "🧸 <b>Gift olish</b>\n\nKerakli sovg'ani tanlang:", reply_markup=Keyboards.inline(rows))

    @staticmethod
    async def callback(cq: dict, chat_id: int, message_id: int, user: dict, action: str, param: str) -> None:
        if action == "page":
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.delete_message(chat_id, message_id)
            await GiftHandler.start(chat_id, user, int(param))
            return

        if action == "pick":
            gift = JsonDb.find("gifts_catalog", int(param))
            if not gift:
                await Telegram.answer_callback_query(cq["id"], "Topilmadi", True)
                return

            Helpers.set_state(int(user["tg_id"]), {"step": "gift_username", "gift_id": gift["id"]})
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.edit_message_text(
                chat_id, message_id,
                f"{gift['emoji']} <b>{gift['stars']} ⭐ sovg'a</b> — {Helpers.money(gift['sell_price_uzs'])}\n\n"
                "Kimga yubormoqchisiz? Telegram username kiriting (@ belgisisiz).",
            )
            return

        if action == "confirm":
            gift_id_s, username = param.split("|", 1)
            gift = JsonDb.find("gifts_catalog", int(gift_id_s))
            if not gift:
                await Telegram.answer_callback_query(cq["id"], "Topilmadi", True)
                return

            fresh = Helpers.get_user_by_id(user["id"])
            if fresh["balance"] < gift["sell_price_uzs"]:
                await Telegram.answer_callback_query(cq["id"], "Balansingiz yetarli emas!", True)
                await Telegram.edit_message_text(chat_id, message_id, f"❌ Balansingiz yetarli emas.\nKerak: {Helpers.money(gift['sell_price_uzs'])}")
                return

            await Telegram.answer_callback_query(cq["id"], "⏳ Yuborilmoqda...")
            await Telegram.edit_message_text(chat_id, message_id, "⏳ Sovg'a yuborilmoqda...")

            result = await CoindropApi.send_gift({
                "gift_id": gift["gift_id"],
                "player_id": username,
                "external_ref": f"user_{user['tg_id']}_{int(time.time())}",
            })

            if result.get("success"):
                Helpers.change_balance(user["id"], -gift["sell_price_uzs"])
                Helpers.log_tx(user["id"], "gift_buy", -gift["sell_price_uzs"], "success",
                                {"gift": gift["emoji"], "to": username, "order_id": result.get("order_id")})
                await Telegram.edit_message_text(
                    chat_id, message_id,
                    f"✅ {gift['emoji']} sovg'a @{username} ga muvaffaqiyatli yuborildi!\n💵 Yechildi: {Helpers.money(gift['sell_price_uzs'])}",
                )
            else:
                Helpers.log_tx(user["id"], "gift_buy", 0, "failed", {"gift": gift["emoji"], "to": username, "error": result.get("detail", "")})
                err_msg = result.get("detail") or "noma'lum xato"
                await Telegram.edit_message_text(chat_id, message_id, f"❌ Xatolik: {err_msg}")

    @staticmethod
    async def handle_state(chat_id: int, user: dict, state: dict, text: str) -> None:
        if state.get("step") != "gift_username":
            return

        username = text.strip().lstrip("@")
        if username == "" or not USERNAME_RE.match(username):
            await Telegram.send_message(chat_id, "❗️ Username noto'g'ri. Qaytadan kiriting.")
            return

        gift_id = state["gift_id"]
        Helpers.set_state(int(user["tg_id"]), None)
        gift = JsonDb.find("gifts_catalog", int(gift_id))
        if not gift:
            await Telegram.send_message(chat_id, "⚠️ Sovg'a topilmadi.")
            return

        await Telegram.send_message(
            chat_id,
            f"{gift['emoji']} Sovg'a: <b>{gift['stars']} ⭐</b>\n👤 Qabul qiluvchi: @{username}\n"
            f"💵 Narx: {Helpers.money(gift['sell_price_uzs'])}\n\nTasdiqlaysizmi?",
            reply_markup=Keyboards.inline([
                [Keyboards.ibtn("✅ Tasdiqlash", f"gift:confirm:{gift_id}|{username}", "success")],
                [Keyboards.ibtn("❌ Bekor qilish", "cancel", "danger")],
            ]),
        )

    @staticmethod
    async def import_catalog() -> dict:
        """Admin panel: coindrop.uz dan sovg'alar katalogini avtomatik import qilish"""
        resp = await CoindropApi.gifts()
        if not resp.get("success"):
            return {"ok": False, "message": resp.get("detail") or "gift ro'yxatini olib bo'lmadi"}
        markup = int(Settings.get("gift_markup_uzs", 1000))
        count = 0
        for g in resp["gifts"]:
            price_uzs = round(g.get("price_uzs", 0) or 0)
            sell = price_uzs + markup
            JsonDb.upsert("gifts_catalog", "gift_id", str(g["gift_id"]), {
                "emoji": g.get("emoji", "🎁"),
                "stars": int(g["stars"]),
                "price_usd": float(g["price_usd"]),
                "price_uzs": price_uzs,
                "sell_price_uzs": sell,
                "min_purchase_stars": int(g.get("min_purchase_stars", 50)),
                "active": 1,
                "updated_at": datetime.datetime.now(config.TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            })
            count += 1
        return {"ok": True, "count": count}

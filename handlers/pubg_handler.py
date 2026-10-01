from __future__ import annotations

import datetime
import json
import re
import time

from api.coindrop_api import CoindropApi
from core.helpers import Helpers
from core.json_db import JsonDb
from core.keyboards import Keyboards
from core.settings import Settings
from core.telegram import Telegram
import config

PLAYER_ID_RE = re.compile(r"^\d{6,15}$")


class PubgHandler:
    GAME_KEY = "pubg-mobile"

    @staticmethod
    async def start(chat_id: int, user: dict) -> None:
        webapp_url = str(Settings.get("webapp_url", "") or "").strip()

        if webapp_url != "":
            url = webapp_url.rstrip("/") + f"/?uid={user['tg_id']}"
            await Telegram.send_message(
                chat_id,
                "🎮 <b>Pubg UC olish</b>\n\nQuyidagi tugma orqali mini-ilovani oching, ID raqamingizni kiriting, "
                "tekshiring va kerakli paketni tanlang.",
                reply_markup=Keyboards.inline([
                    [Keyboards.webapp_btn("🎮 UC sotib olish", url, "danger")],
                    [Keyboards.ibtn("✍️ Chatda davom etish", "pubg:chat:0")],
                ]),
            )
            return

        await PubgHandler.ask_id(chat_id, user)

    @staticmethod
    async def ask_id(chat_id: int, user: dict) -> None:
        Helpers.set_state(int(user["tg_id"]), {"step": "pubg_player_id"})
        await Telegram.send_message(
            chat_id,
            "🎮 <b>Pubg UC olish</b>\n\nAPI orqali ID kiriting, biz avtomatik tekshiramiz.\n"
            "PUBG Mobile Player ID raqamingizni yuboring:",
            reply_markup=Keyboards.cancel_inline(),
        )

    @staticmethod
    async def handle_state(chat_id: int, user: dict, state: dict, text: str) -> None:
        if state.get("step") != "pubg_player_id":
            return

        player_id = text.strip()
        if not PLAYER_ID_RE.match(player_id):
            await Telegram.send_message(chat_id, "❗️ ID faqat raqamlardan iborat bo'lishi kerak (6-15 xona). Qaytadan kiriting.")
            return

        await Telegram.send_chat_action(chat_id, "typing")
        check = await CoindropApi.validate(PubgHandler.GAME_KEY, player_id)

        if not check.get("success") or not check.get("valid"):
            err_msg = check.get("message") or ""
            await Telegram.send_message(
                chat_id,
                f"❌ ID topilmadi yoki noto'g'ri: {err_msg}\nQaytadan kiriting yoki bekor qiling.",
                reply_markup=Keyboards.cancel_inline(),
            )
            return

        player_name = check.get("username", player_id)
        Helpers.set_state(int(user["tg_id"]), {"step": "pubg_product", "player_id": player_id, "player_name": player_name})

        products = PubgHandler.list_products()
        if not products:
            await Telegram.send_message(chat_id, "⚠️ Hozircha UC paketlari mavjud emas. Admin bilan bog'laning.")
            return

        rows = []
        for p in products:
            rows.append([Keyboards.ibtn(f"{p['name']} — {Helpers.money(p['sell_price_uzs'])}", f"pubg:pick:{p['product_id']}", "success")])
        rows.append([Keyboards.ibtn("❌ Bekor qilish", "cancel", "danger")])

        await Telegram.send_message(
            chat_id, f"✅ ID tekshirildi: <b>{player_name}</b>\n\nKerakli UC paketini tanlang:",
            reply_markup=Keyboards.inline(rows),
        )

    @staticmethod
    async def callback(cq: dict, chat_id: int, message_id: int, user: dict, action: str, param: str) -> None:
        if action == "chat":
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.delete_message(chat_id, message_id)
            await PubgHandler.ask_id(chat_id, user)
            return

        if action == "pick":
            state = Helpers.get_state(int(user["tg_id"]))
            if not state or state.get("step") != "pubg_product":
                await Telegram.answer_callback_query(cq["id"], "Sessiya tugagan, qaytadan boshlang.", True)
                return
            product = JsonDb.first("pubg_products", lambda p: p["product_id"] == param)
            if not product:
                await Telegram.answer_callback_query(cq["id"], "Topilmadi", True)
                return

            Helpers.set_state(int(user["tg_id"]), None)
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.edit_message_text(
                chat_id, message_id,
                f"🎮 ID: <b>{state['player_name']}</b> ({state['player_id']})\n"
                f"📦 Paket: <b>{product['name']}</b>\n💵 Narx: {Helpers.money(product['sell_price_uzs'])}\n\nTasdiqlaysizmi?",
                reply_markup=Keyboards.inline([
                    [Keyboards.ibtn("✅ Tasdiqlash", f"pubg:confirm:{product['product_id']}|{state['player_id']}|{state['player_name']}", "success")],
                    [Keyboards.ibtn("❌ Bekor qilish", "cancel", "danger")],
                ]),
            )
            return

        if action == "confirm":
            product_id, player_id, player_name = param.split("|", 2)
            await PubgHandler.place_order(cq, chat_id, message_id, user, product_id, player_id, player_name)

    @staticmethod
    async def place_order(cq: dict, chat_id: int, message_id: int, user: dict, product_id: str, player_id: str, player_name: str) -> None:
        product = JsonDb.first("pubg_products", lambda p: p["product_id"] == product_id)
        if not product:
            await Telegram.answer_callback_query(cq["id"], "Mahsulot topilmadi", True)
            return

        fresh = Helpers.get_user_by_id(user["id"])
        if fresh["balance"] < product["sell_price_uzs"]:
            await Telegram.answer_callback_query(cq["id"], "Balansingiz yetarli emas!", True)
            await Telegram.edit_message_text(chat_id, message_id, f"❌ Balansingiz yetarli emas.\nKerak: {Helpers.money(product['sell_price_uzs'])}")
            return

        await Telegram.answer_callback_query(cq["id"], "⏳ Buyurtma yuborilmoqda...")
        await Telegram.edit_message_text(chat_id, message_id, "⏳ Buyurtma amalga oshirilmoqda...")

        result = await CoindropApi.create_order({
            "game_key": PubgHandler.GAME_KEY,
            "product_id": product_id,
            "player_id": player_id,
            "player_name": player_name,
            "external_ref": f"user_{user['tg_id']}_{int(time.time())}",
        })

        order_fields = {
            "user_id": user["id"],
            "player_id": player_id,
            "player_name": player_name,
            "product_id": product_id,
            "product_name": product["name"],
            "price_uzs": product["sell_price_uzs"],
            "coindrop_order_id": result.get("order_id"),
            "created_at": datetime.datetime.now(config.TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        }

        if result.get("success") and result.get("status") == "delivered":
            Helpers.change_balance(user["id"], -product["sell_price_uzs"])
            Helpers.log_tx(user["id"], "pubg_uc", -product["sell_price_uzs"], "success", {"player_id": player_id, "product": product["name"]})
            JsonDb.insert("pubg_orders", {**order_fields, "status": "delivered"})
            await Telegram.edit_message_text(
                chat_id, message_id,
                f"✅ <b>{product['name']}</b> ID: {player_id} ({player_name}) ga muvaffaqiyatli yuklandi!\n"
                f"💵 Yechildi: {Helpers.money(product['sell_price_uzs'])}",
            )
        else:
            JsonDb.insert("pubg_orders", {**order_fields, "status": "failed"})
            Helpers.log_tx(user["id"], "pubg_uc", 0, "failed", {"player_id": player_id, "error": result.get("detail", "")})
            err_msg = result.get("detail") or "noma'lum xato"
            await Telegram.edit_message_text(chat_id, message_id, f"❌ Xatolik: {err_msg}\nBalansingizdan hech narsa yechilmadi.")

    @staticmethod
    async def handle_webapp_data(chat_id: int, user: dict, raw_json: str) -> None:
        """Mini-app'dan kelgan ma'lumotni qayta ishlash (Telegram.WebApp.sendData)"""
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            data = None
        if not isinstance(data, dict) or not data.get("product_id") or not data.get("player_id"):
            await Telegram.send_message(chat_id, "⚠️ Mini-ilovadan noto'g'ri ma'lumot keldi.")
            return
        fake_cq = {"id": "0"}
        msg = await Telegram.send_message(chat_id, "⏳ Buyurtmangiz qabul qilindi, tekshirilmoqda...")
        message_id = (msg.get("result") or {}).get("message_id", 0)
        await PubgHandler.place_order(
            fake_cq, chat_id, message_id or 0, user,
            data["product_id"], data["player_id"], data.get("player_name", data["player_id"]),
        )

    @staticmethod
    def list_products() -> list:
        active = JsonDb.where("pubg_products", lambda p: int(p.get("active", 0)) == 1)
        return JsonDb.sort_by(active, "sell_price_uzs", "ASC")

    @staticmethod
    async def import_products() -> dict:
        """Admin panel: coindrop.uz dan PUBG mahsulotlarini 100% avtomatik import qilish"""
        resp = await CoindropApi.products(PubgHandler.GAME_KEY)
        if not resp.get("success"):
            return {"ok": False, "message": resp.get("detail") or "mahsulotlarni olib bo'lmadi"}
        count = 0
        for p in resp["products"]:
            price = round(p["price_uzs"])
            sell = round(p.get("retail_uzs", p["price_uzs"]))  # coindrop tavsiya etgan chakana narx
            JsonDb.upsert("pubg_products", "product_id", str(p["id"]), {
                "name": p["name"],
                "price_uzs": price,
                "sell_price_uzs": sell,
                "active": 1,
                "updated_at": datetime.datetime.now(config.TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            })
            count += 1
        return {"ok": True, "count": count}

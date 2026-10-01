from __future__ import annotations

import datetime

from api.cheapsmm_api import CheapSmmApi
from core.helpers import Helpers
from core.json_db import JsonDb
from core.keyboards import Keyboards
from core.telegram import Telegram
import config


class NumberHandler:
    PER_PAGE = 8

    @staticmethod
    async def start(chat_id: int, user: dict, page: int = 0) -> None:
        all_active = JsonDb.where("sms_countries", lambda c: int(c.get("active", 0)) == 1)
        all_active = JsonDb.sort_by(all_active, "sell_price", "ASC")
        countries = JsonDb.paginate(all_active, NumberHandler.PER_PAGE, page * NumberHandler.PER_PAGE)

        if not countries:
            await Telegram.send_message(chat_id, "⚠️ Hozircha davlatlar ro'yxati mavjud emas. Admin bilan bog'laning.")
            return

        rows = []
        for c in countries:
            rows.append([Keyboards.ibtn(f"{c['name']} — {Helpers.money(c['sell_price'])}", f"number:pick:{c['code']}", "danger")])

        nav = []
        if page > 0:
            nav.append(Keyboards.ibtn("◀️ Oldingi", f"number:page:{page - 1}"))
        total = len(all_active)
        if (page + 1) * NumberHandler.PER_PAGE < total:
            nav.append(Keyboards.ibtn("Keyingisi ▶️ (eng arzon)", f"number:page:{page + 1}"))
        if nav:
            rows.append(nav)
        rows.append([Keyboards.ibtn("❌ Bekor qilish", "cancel", "danger")])

        await Telegram.send_message(
            chat_id, "📱 <b>Nomer olish</b>\n\nEng arzon davlatlar ro'yxati (narxlar eng arzonidan boshlab):",
            reply_markup=Keyboards.inline(rows),
        )

    @staticmethod
    async def callback(cq: dict, chat_id: int, message_id: int, user: dict, action: str, param: str) -> None:
        if action == "page":
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.delete_message(chat_id, message_id)
            await NumberHandler.start(chat_id, user, int(param))
            return

        if action == "pick":
            country = JsonDb.first("sms_countries", lambda c: c["code"] == param)
            if not country:
                await Telegram.answer_callback_query(cq["id"], "Topilmadi", True)
                return

            fresh = Helpers.get_user_by_id(user["id"])
            if fresh["balance"] < country["sell_price"]:
                await Telegram.answer_callback_query(cq["id"], "Balansingiz yetarli emas!", True)
                await Telegram.edit_message_text(chat_id, message_id, f"❌ Balansingiz yetarli emas.\nKerak: {Helpers.money(country['sell_price'])}")
                return

            await Telegram.answer_callback_query(cq["id"], "⏳ Raqam olinmoqda...")
            await Telegram.edit_message_text(chat_id, message_id, "⏳ Raqam olinmoqda...")

            resp = await CheapSmmApi.buy_number(country["code"])
            if not resp.get("status"):
                err_msg = resp.get("message") or "raqam topilmadi yoki davlat raqamlari tugagan"
                await Telegram.edit_message_text(chat_id, message_id, f"❌ Xatolik: {err_msg}")
                return

            result_obj = resp.get("result") or {}
            hash_code = resp.get("hash_code") or result_obj.get("hash_code")
            phone = resp.get("phone") or result_obj.get("phone") or resp.get("number")

            if not hash_code:
                await Telegram.edit_message_text(chat_id, message_id, "❌ Raqam olinmadi. Qaytadan urinib ko'ring.")
                return

            Helpers.change_balance(user["id"], -country["sell_price"])
            Helpers.log_tx(user["id"], "number_buy", -country["sell_price"], "success", {"country": country["code"], "phone": phone})
            order = JsonDb.insert("sms_orders", {
                "user_id": user["id"],
                "hash_code": hash_code,
                "country": country["code"],
                "phone": phone,
                "price_uzs": country["sell_price"],
                "status": "pending",
                "code": None,
                "created_at": datetime.datetime.now(config.TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            })
            order_id = order["id"]

            await Telegram.edit_message_text(
                chat_id, message_id,
                f"✅ Raqam olindi!\n📞 Nomer: <code>{phone}</code>\n🌍 Davlat: {country['name']}\n"
                f"💵 Narx: {Helpers.money(country['sell_price'])}\n\n"
                "SMS kod kelishini kuting va \"Kodni tekshirish\" tugmasini bosing.",
                reply_markup=Keyboards.inline([
                    [Keyboards.ibtn("🔎 Kodni tekshirish", f"number:code:{order_id}", "success")],
                ]),
            )
            return

        if action == "code":
            order_id = int(param)
            order = JsonDb.first("sms_orders", lambda o: int(o["id"]) == order_id and int(o["user_id"]) == int(user["id"]))
            if not order:
                await Telegram.answer_callback_query(cq["id"], "Topilmadi", True)
                return

            resp = await CheapSmmApi.get_code(order["hash_code"])
            code = resp.get("code") or (resp.get("result") or {}).get("code")

            if code:
                JsonDb.update("sms_orders", int(order["id"]), {"status": "code_received", "code": code})
                await Telegram.answer_callback_query(cq["id"], "✅ Kod keldi!")
                await Telegram.edit_message_text(
                    chat_id, message_id,
                    f"✅ SMS kod qabul qilindi!\n📞 Nomer: <code>{order['phone']}</code>\n🔑 Kod: <code>{code}</code>",
                )
            else:
                await Telegram.answer_callback_query(cq["id"], "⏳ Hali kod kelmadi, kuting...", True)

    @staticmethod
    async def handle_state(chat_id: int, user: dict, state: dict, text: str) -> None:
        # Hozircha matnli bosqich talab qilinmaydi (hammasi inline tugmalar orqali)
        pass

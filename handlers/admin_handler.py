from __future__ import annotations

import datetime
import re
import tempfile
from pathlib import Path

from api.checkout_api import CheckoutApi
from api.cheapsmm_api import CheapSmmApi
from api.playpay_api import CoindropApi
from api.fragment_api import FragmentApi
from core.helpers import Helpers
from core.json_db import JsonDb
from core.keyboards import Keyboards
from core.settings import Settings
from core.telegram import Telegram
import config

STATUS_LABELS = {
    "paid": "✅ MUVAFFAQIYATLI",
    "pending": "⏳ KUTILMOQDA",
    "cancelled": "❌ BEKOR QILINGAN"
}

TX_LABELS = {
    "stars_buy": "⭐ Stars sotildi",
    "premium_buy": "💎 Premium sotildi",
    "gift_buy": "🎁 Gift sotildi",
    "pubg_uc": "🎮 Pubg UC sotildi",
    "number_buy": "📱 Nomerlar sotildi",
    "topup": "💳 Hisob to'ldirishlar",
}

def _now() -> str:
    return datetime.datetime.now(config.TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")


class AdminHandler:
    @staticmethod
    async def open_panel(chat_id: int) -> None:
        await Telegram.send_message(
            chat_id,
            "🛡 <b>Admin panel</b>\n\nQuyidagi bo'limlardan birini tanlang:",
            reply_markup=Keyboards.admin_menu()
        )

    @staticmethod
    async def exit_panel(chat_id: int, user: dict) -> None:
        Helpers.set_state(int(user["tg_id"]), None)
        await Telegram.clear_reply_keyboard(chat_id)
        await Telegram.send_message(
            chat_id,
            "🚪 Admin paneldan chiqdingiz.",
            reply_markup=Keyboards.main_menu()
        )

    # ================= 1. STATISTIKA =================
    @staticmethod
    async def statistics(chat_id: int) -> None:
        total_users = JsonDb.count("users")
        total_balance = int(JsonDb.sum("users", "balance"))

        txs = JsonDb.where("transactions", lambda t: t.get("status") == "success" and float(t.get("amount", 0)) < 0)
        grouped: dict = {}
        for t in txs:
            tx_type = t.get("type", "unknown")
            g = grouped.setdefault(tx_type, {"cnt": 0, "spent": 0})
            g["cnt"] += 1
            g["spent"] += -float(t.get("amount", 0))

        lines = [
            "=== SupperGramBot STATISTIKA ===",
            f"Sana: {_now()}",
            f"Jami foydalanuvchilar: {total_users} ta",
            f"Foydalanuvchilar balansi jami: {Helpers.money(total_balance)}",
            "",
            "--- Xizmatlar bo'yicha ---",
        ]
        if not grouped:
            lines.append("Hozircha savdo qayd etilmagan.")
        for tx_type, g in grouped.items():
            label = TX_LABELS.get(tx_type, tx_type)
            lines.append(f"{label}: {g['cnt']} ta buyurtma, {Helpers.money(int(g['spent']))}")

        topups_paid = int(JsonDb.sum("topups", "amount", lambda t: t.get("status") == "paid"))
        lines.append("")
        lines.append(f"Jami to'langan hisob to'ldirishlar: {Helpers.money(topups_paid)}")

        file = Path(tempfile.gettempdir()) / f"statistika_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            file.write_text("\n".join(lines), encoding="utf-8")
            await Telegram.send_document(chat_id, str(file), "📊 To'liq statistika")
        finally:
            if file.exists():
                file.unlink(missing_ok=True)

    # ================= 2. TO'LOVLAR HOLATI =================
    @staticmethod
    async def payments_report(chat_id: int) -> None:
        topups = JsonDb.sort_by(JsonDb.all("topups"), "id", "DESC")
        topups = JsonDb.paginate(topups, 500)

        lines = ["=== TO'LOVLAR HOLATI (oxirgi 500 ta) ===", f"Sana: {_now()}", ""]
        if not topups:
            lines.append("Hozircha to'lovlar mavjud emas.")
        for r in topups:
            u = Helpers.get_user_by_id(int(r.get("user_id", 0))) or {}
            tg_id = u.get("tg_id", "—")
            uname = f"@{u['username']}" if u.get("username") else "usernamesiz"
            status_text = STATUS_LABELS.get(r.get("status"), str(r.get("status")).upper())
            sender_card = f" | Karta: *{r['sender_card']}" if r.get("sender_card") else ""
            lines.append(
                f"#{r['id']} | ID:{tg_id} ({uname}) | {Helpers.money(int(r.get('amount', 0)))} | {status_text}{sender_card} | "
                f"yaratildi: {r.get('created_at')} | to'landi: {r.get('paid_at') or '—'}"
            )

        file = Path(tempfile.gettempdir()) / f"tolovlar_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            file.write_text("\n".join(lines), encoding="utf-8")
            await Telegram.send_document(chat_id, str(file), "💳 To'lovlar holati hisoboti")
        finally:
            if file.exists():
                file.unlink(missing_ok=True)

    # ================= 3. CHECKOUT API =================
    @staticmethod
    async def checkout_api_menu(chat_id: int) -> None:
        key = Settings.get("checkout_api_key", "")
        status = f"✅ Kalit kiritilgan ({key[:6]}...)" if key else "❌ Kalit kiritilmagan"
        await Telegram.send_message(
            chat_id,
            f"🧾 <b>Checkout.uz to'lov API</b>\n\nHolat: {status}\n\n"
            "Kassa sozlamalaridan (checkout.uz shaxsiy kabinet) API kalitni oling va shu yerga yuboring.",
            reply_markup=Keyboards.inline([
                [Keyboards.ibtn("🔑 API kalit kiritish", "admin:setkey:checkout", "primary")],
                [Keyboards.ibtn("💰 Balansni tekshirish", "admin:testkey:checkout", "success")],
            ]),
        )

    # ================= 4. FRAGMENT API =================
    @staticmethod
    async def fragment_api_menu(chat_id: int) -> None:
        key = Settings.get("fragment_api_key", "")
        status = "✅ Kalit kiritilgan" if key else "❌ Kalit kiritilmagan"
        await Telegram.send_message(
            chat_id,
            f"🌐 <b>Fragment API (Stars/Premium)</b>\n\nHolat: {status}\n"
            f"Joriy foyda ustamasi: {Helpers.money(int(float(Settings.get('fragment_markup_uzs', 350))))}",
            reply_markup=Keyboards.inline([
                [Keyboards.ibtn("🔑 API kalit kiritish", "admin:setkey:fragment", "primary")],
                [Keyboards.ibtn("💰 Hisob balansini ko'rish", "admin:testkey:fragment", "success")],
                [Keyboards.ibtn("❌ Kalitni o'chirish", "admin:delkey:fragment", "danger")],
            ]),
        )

    # ================= 5. COINDROP API =================
    @staticmethod
    async def coindrop_api_menu(chat_id: int) -> None:
        key = Settings.get("coindrop_api_key", "")
        status = "✅ Kalit kiritilgan" if key else "❌ Kalit kiritilmagan"
        count = JsonDb.count("pubg_products", lambda p: int(p.get("active", 0)) == 1)
        await Telegram.send_message(
            chat_id,
            f"🎮 <b>Coindrop API (Pubg UC)</b>\n\nHolat: {status}\nImport qilingan paketlar: {count} ta",
            reply_markup=Keyboards.inline([
                [Keyboards.ibtn("🔑 API kalit kiritish", "admin:setkey:coindrop", "primary")],
                [Keyboards.ibtn("💰 Balansni ko'rish", "admin:testkey:coindrop", "success")],
                [Keyboards.ibtn("📥 Xizmatlarni import qilish", "admin:import:pubg", "success")],
                [Keyboards.ibtn("❌ Kalitni o'chirish", "admin:delkey:coindrop", "danger")],
            ]),
        )

    # ================= 6. GIFT IMPORT =================
    @staticmethod
    async def gift_import_menu(chat_id: int) -> None:
        count = JsonDb.count("gifts_catalog", lambda g: int(g.get("active", 0)) == 1)
        await Telegram.send_message(
            chat_id,
            f"🎁 <b>Telegram Gift import</b>\n\nHozirda katalogda: {count} ta sovg'a\n"
            "Import coindrop.uz API kaliti orqali amalga oshiriladi (5-bo'limda kalit kiritilgan bo'lishi kerak).",
            reply_markup=Keyboards.inline([
                [Keyboards.ibtn("📥 Avto import qilish", "admin:import:gift", "success")],
                [Keyboards.ibtn("➕ Gift ID orqali qo'lda qo'shish", "admin:addgift:0", "primary")],
            ]),
        )

    # ================= 7. BOT STARS TOPUP =================
    @staticmethod
    async def stars_topup_menu(chat_id: int) -> None:
        Helpers.set_state(chat_id, {"step": "admin_stars_amount"})
        await Telegram.send_message(
            chat_id,
            "⭐ <b>Bot hisobini Stars bilan to'ldirish</b>\n\nQancha Stars yubormoqchisiz? Miqdorni kiriting (masalan: 100).",
            reply_markup=Keyboards.cancel_inline(),
        )

    @staticmethod
    async def handle_stars_payment_success(chat_id: int, payment: dict) -> None:
        amount = int(payment.get("total_amount", 0))
        current = int(float(Settings.get("bot_stars_balance", 0)))
        Settings.set("bot_stars_balance", current + amount)
        await Telegram.send_message(
            chat_id,
            f"✅ {amount} ⭐ Stars bot hisobiga muvaffaqiyatli qo'shildi!\nJami: {current + amount} ⭐"
        )

    # ================= 8. BOT ON/OFF =================
    @staticmethod
    async def toggle_bot_status(chat_id: int) -> None:
        current = Settings.get("bot_status", "on")
        new = "off" if current == "on" else "on"
        Settings.set("bot_status", new)
        text = (
            "✅ Bot yoqildi. Foydalanuvchilar botdan foydalanishi mumkin."
            if new == "on" else
            "⛔️ Bot o'chirildi. Foydalanuvchilarga texnik ishlar xabari ko'rsatiladi."
        )
        await Telegram.send_message(chat_id, text)

    # ================= 9. CHEAP-SMM API =================
    @staticmethod
    async def cheapsmm_api_menu(chat_id: int) -> None:
        key = Settings.get("cheapsmm_api_key", "")
        status = "✅ Kalit kiritilgan" if key else "❌ Kalit kiritilmagan"
        count = JsonDb.count("sms_countries", lambda c: int(c.get("active", 0)) == 1)
        await Telegram.send_message(
            chat_id,
            f"📱 <b>Cheap-SMM SMS API (Nomer olish)</b>\n\nHolat: {status}\nImport qilingan davlatlar: {count} ta\n"
            f"Ustama: {Helpers.money(int(float(Settings.get('number_markup_uzs', 500))))}",
            reply_markup=Keyboards.inline([
                [Keyboards.ibtn("🔑 API kalit kiritish", "admin:setkey:cheapsmm", "primary")],
                [Keyboards.ibtn("💰 Balansni ko'rish", "admin:testkey:cheapsmm", "success")],
                [Keyboards.ibtn("📥 Davlatlarni import qilish", "admin:import:countries", "success")],
            ]),
        )

    # ================= MENEJERLAR =================
    @staticmethod
    async def managers_menu(chat_id: int) -> None:
        rows = [
            ("gram_buy_admin", "💎 Gram olish menejeri"),
            ("gram_sell_admin", "💎 Gram sotish menejeri"),
            ("stars_sell_admin", "⭐ Stars sotish menejeri"),
            ("channel_sell_admin", "📡 Kanal sotish menejeri"),
            ("nft_sell_admin", "🎭 NFT sotish menejeri"),
        ]
        text = "⚙️ <b>Xizmat menejerlari</b>\n\nUshbu xizmatlarda foydalanuvchi to'g'ridan-to'g'ri belgilangan menejerga yo'naltiriladi.\n\n"
        buttons = []
        for key, label in rows:
            val = Settings.get(key, "")
            text += ("✅ " if val else "❌ ") + f"{label}: {val or '—'}\n"
            buttons.append([Keyboards.ibtn(f"✏️ {label}", f"admin:setmgr:{key}", "primary")])
        await Telegram.send_message(chat_id, text, reply_markup=Keyboards.inline(buttons))

    # ================= FOYDALANUVCHILAR =================
    @staticmethod
    async def users_menu(chat_id: int) -> None:
        total = JsonDb.count("users")
        await Telegram.send_message(
            chat_id,
            f"👥 <b>Foydalanuvchilar</b>\n\nJami: {total} ta\n\nFoydalanuvchini qidirish uchun ID yoki username kiriting:",
            reply_markup=Keyboards.inline([[Keyboards.ibtn("🔍 Qidirish", "admin:finduser:0", "primary")]]),
        )

    # ================= CALLBACKS =================
    @staticmethod
    async def callback(cq: dict, chat_id: int, message_id: int, user: dict, is_admin: bool, action: str, param: str) -> None:
        if not is_admin:
            await Telegram.answer_callback_query(cq["id"], "⛔️ Ruxsat yo'q", True)
            return
        admin_tg_id = int(user["tg_id"])

        if action == "setkey":
            Helpers.set_state(admin_tg_id, {"step": "admin_setkey", "provider": param})
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.send_message(chat_id, f"🔑 <b>{param}</b> uchun API kalitni yuboring:", reply_markup=Keyboards.cancel_inline())

        elif action == "delkey":
            Settings.set(f"{param}_api_key", "")
            await Telegram.answer_callback_query(cq["id"], "O'chirildi ✅")
            await Telegram.edit_message_text(chat_id, message_id, f"❌ {param} API kaliti o'chirildi.")

        elif action == "testkey":
            await Telegram.answer_callback_query(cq["id"], "Tekshirilmoqda...")
            await AdminHandler._test_key(chat_id, param)

        elif action == "import":
            await Telegram.answer_callback_query(cq["id"], "Import qilinmoqda...")
            await AdminHandler._run_import(chat_id, param)

        elif action == "setmgr":
            Helpers.set_state(admin_tg_id, {"step": "admin_setmgr", "key": param})
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.send_message(chat_id, "✏️ Menejer usernameni kiriting (@ belgisisiz):", reply_markup=Keyboards.cancel_inline())

        elif action == "addgift":
            Helpers.set_state(admin_tg_id, {"step": "admin_addgift_id"})
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.send_message(chat_id, "🎁 Gift ID raqamini kiriting:", reply_markup=Keyboards.cancel_inline())

        elif action == "finduser":
            Helpers.set_state(admin_tg_id, {"step": "admin_finduser"})
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.send_message(chat_id, "🔍 Foydalanuvchi Telegram ID yoki username kiriting:", reply_markup=Keyboards.cancel_inline())

        elif action == "uball":
            await AdminHandler._user_balance_action(cq, chat_id, message_id, param, "add")
        elif action == "usub":
            await AdminHandler._user_balance_action(cq, chat_id, message_id, param, "sub")
        elif action == "uban":
            await AdminHandler._user_toggle_ban(cq, chat_id, message_id, param)
        else:
            await Telegram.answer_callback_query(cq["id"])

    @staticmethod
    async def _test_key(chat_id: int, provider: str) -> None:
        if provider == "checkout":
            r = await CheckoutApi.get_balance()
            if r.get("status") == "success":
                b = r["balance"]
                await Telegram.send_message(
                    chat_id,
                    f"💰 Checkout.uz balans:\nUZS: {b.get('uzs', 0):,}\nUSD: {b.get('usd', 0)}\nTON: {b.get('ton', 0)}".replace(",", " "),
                )
            else:
                await Telegram.send_message(chat_id, "❌ Ulanib bo'lmadi. Kalitni tekshiring.")

        elif provider == "fragment":
            r = await FragmentApi.wallet_balance()
            if r.get("ok"):
                res = r["result"]
                await Telegram.send_message(
                    chat_id,
                    f"💰 Fragment hamyon balansi:\nTON: {res['balance_ton']}\nUSDT: {res['balance_usdt']}\nManzil: <code>{res['address']}</code>",
                )
            else:
                err_msg = r.get("message") or ""
                await Telegram.send_message(chat_id, f"❌ Xatolik: {err_msg}")

        elif provider == "coindrop":
            r = await CoindropApi.account()
            if r.get("success"):
                a = r["account"]
                api_status = "yoqilgan ✅" if a.get("api_enabled") else "o'chirilgan ❌"
                await Telegram.send_message(
                    chat_id,
                    f"💰 Coindrop balans:\nUSD: {a['balance_usd']}\nUZS: {a['balance_uzs']}\nAPI holati: {api_status}",
                )
            else:
                err_msg = r.get("detail") or ""
                await Telegram.send_message(chat_id, f"❌ Xatolik: {err_msg}")

        elif provider == "cheapsmm":
            r = await CheapSmmApi.get_balance()
            if r.get("status"):
                await Telegram.send_message(chat_id, f"💰 Cheap-SMM balans: {r.get('balance', 0)} {r.get('currency', 'UZS')}")
            else:
                err_msg = r.get("message") or ""
                await Telegram.send_message(chat_id, f"❌ Xatolik: {err_msg}")

    @staticmethod
    async def _run_import(chat_id: int, import_type: str) -> None:
        from handlers.pubg_handler import PubgHandler
        from handlers.gift_handler import GiftHandler

        if import_type == "pubg":
            r = await PubgHandler.import_products()
            await Telegram.send_message(chat_id, f"✅ {r['count']} ta Pubg UC paketi import qilindi." if r.get("ok") else f"❌ Xatolik: {r['message']}")
        elif import_type == "gift":
            r = await GiftHandler.import_catalog()
            await Telegram.send_message(chat_id, f"✅ {r['count']} ta sovg'a import qilindi." if r.get("ok") else f"❌ Xatolik: {r['message']}")
        elif import_type == "countries":
            r = await AdminHandler.import_countries()
            await Telegram.send_message(chat_id, f"✅ {r['count']} ta davlat import qilindi." if r.get("ok") else f"❌ Xatolik: {r['message']}")

    @staticmethod
    async def import_countries() -> dict:
        resp = await CheapSmmApi.get_countries()
        if not resp.get("status"):
            return {"ok": False, "message": resp.get("message") or "davlatlar ro'yxatini olib bo'lmadi"}
        countries = (resp.get("result") or {}).get("countries") or {}
        markup = int(float(Settings.get("number_markup_uzs", 500)))
        names = AdminHandler._country_names()
        count = 0
        for code, price in countries.items():
            base = int(price)
            sell = base + markup
            name = names.get(code, code)
            JsonDb.upsert("sms_countries", "code", code, {
                "name": name, "base_price": base, "sell_price": sell, "active": 1, "updated_at": _now(),
            })
            count += 1
        return {"ok": True, "count": count}

    @staticmethod
    def _country_names() -> dict:
        return {
            "UZ": "🇺🇿 O'zbekiston", "RU": "🇷🇺 Rossiya", "US": "🇺🇸 AQSH", "KZ": "🇰🇿 Qozog'iston",
            "UA": "🇺🇦 Ukraina", "ID": "🇮🇩 Indoneziya", "IN": "🇮🇳 Hindiston", "PH": "🇵🇭 Filippin",
            "KG": "🇰🇬 Qirg'iziston", "TJ": "🇹🇯 Tojikiston", "GB": "🇬🇧 Angliya", "DE": "🇩🇪 Germaniya",
            "FR": "🇫🇷 Fransiya", "BR": "🇧🇷 Braziliya", "VN": "🇻🇳 Vetnam", "MY": "🇲🇾 Malayziya",
        }

    @staticmethod
    async def _user_balance_action(cq: dict, chat_id: int, message_id: int, param: str, mode: str) -> None:
        user_id_s, amount_s = param.split("|", 1)
        user_id, amount = int(user_id_s), int(amount_s)
        delta = (1 if mode == "add" else -1) * amount
        
        Helpers.change_balance(user_id, delta)
        Helpers.log_tx(user_id, "admin_adjust", delta, "success", {"by_admin": True})
        
        u = Helpers.get_user_by_id(user_id)
        
        await Telegram.answer_callback_query(cq["id"], "Bajarildi ✅")
        await Telegram.edit_message_text(chat_id, message_id, AdminHandler.user_card(u), reply_markup=AdminHandler.user_card_keyboard(u))

    @staticmethod
    async def _user_toggle_ban(cq: dict, chat_id: int, message_id: int, user_id_s: str) -> None:
        user_id = int(user_id_s)
        u = Helpers.get_user_by_id(user_id)
        new_status = 0 if u.get("banned") else 1
        
        JsonDb.update("users", user_id, {"banned": new_status})
        u["banned"] = new_status
        
        await Telegram.answer_callback_query(cq["id"], "Bloklandi 🚫" if new_status else "Blok olindi ✅")
        await Telegram.edit_message_text(chat_id, message_id, AdminHandler.user_card(u), reply_markup=AdminHandler.user_card_keyboard(u))

    @staticmethod
    def user_card(u: dict) -> str:
        return (
            "👤 <b>Foydalanuvchi ma'lumotlari</b>\n\n"
            f"🆔 ID: <code>{u.get('tg_id')}</code>\n"
            f"👤 Username: {'@' + u['username'] if u.get('username') else '—'}\n"
            f"📝 Ism: {u.get('first_name') or '—'}\n"
            f"💰 Balans: <b>{Helpers.money(int(u.get('balance', 0)))}</b>\n"
            f"📌 Holat: {'🚫 Bloklangan' if u.get('banned') else '✅ Faol'}\n"
            f"📅 Ro'yxatdan o'tgan: {u.get('created_at', '—')}"
        )

    @staticmethod
    def user_card_keyboard(u: dict) -> dict:
        # Eslatma: Bazangizda asosiy identifikator 'tg_id' yoki 'id' ekanligiga e'tibor bering. 
        # Odatda telegram botlarda tg_id ishlatiladi.
        uid = u.get('tg_id') or u.get('id')
        return Keyboards.inline([
            [
                Keyboards.ibtn("➕ 50 000", f"admin:uball:{uid}|50000", "success"),
                Keyboards.ibtn("➖ 50 000", f"admin:usub:{uid}|50000", "danger")
            ],
            [
                Keyboards.ibtn("✅ Blokdan chiqarish" if u.get("banned") else "🚫 Bloklash", f"admin:uban:{uid}", "danger")
            ],
        ])

    # ================= FSM STATE HANDLING =================
    @staticmethod
    async def handle_state(chat_id: int, user: dict, state: dict, text: str) -> None:
        tg_id = int(user["tg_id"])
        step = state.get("step")

        if step == "admin_setkey":
            provider = state.get("provider")
            key_map = {
                "checkout": "checkout_api_key", 
                "fragment": "fragment_api_key",
                "coindrop": "coindrop_api_key", 
                "cheapsmm": "cheapsmm_api_key"
            }
            target_setting = key_map.get(provider)
            if target_setting:
                Settings.set(target_setting, text.strip())
                Helpers.set_state(tg_id, None)
                await Telegram.send_message(chat_id, f"✅ <b>{provider}</b> API kaliti saqlandi.")
                await AdminHandler._test_key(chat_id, provider)
                if provider == "coindrop":
                    await AdminHandler._run_import(chat_id, "pubg")
                if provider == "cheapsmm":
                    await AdminHandler._run_import(chat_id, "countries")
            return

        if step == "admin_setmgr":
            key = state.get("key")
            value = text.strip().lstrip("@")
            Settings.set(key, value)
            Helpers.set_state(tg_id, None)
            await Telegram.send_message(chat_id, f"✅ Menejer saqlandi: @{value}")
            return

        if step == "admin_stars_amount":
            amount = Helpers.parse_int(text)
            if not amount or amount < 1:
                await Telegram.send_message(chat_id, "❗ To'g'ri miqdor kiriting.")
                return
            Helpers.set_state(tg_id, None)
            await Telegram.send_invoice_stars(
                chat_id, 
                "Bot hisobini to'ldirish", 
                f"{amount} ⭐ Stars bilan bot hisobini to'ldirish",
                f"bot_topup_{int(datetime.datetime.now().timestamp())}", 
                amount,
            )
            return

        if step == "admin_addgift_id":
            Helpers.set_state(tg_id, {"step": "admin_addgift_details", "gift_id": text.strip()})
            await Telegram.send_message(
                chat_id, 
                "Endi ma'lumotlarni shu tartibda yuboring:\n<code>emoji stars narx_som</code>\n\nMasalan: <code>🧸 15 3000</code>"
            )
            return

        if step == "admin_addgift_details":
            parts = re.split(r"\s+", text.strip())
            if len(parts) < 3:
                await Telegram.send_message(chat_id, "❗ Format noto'g'ri. Misol: <code>🧸 15 3000</code>")
                return
            emoji, stars, price = parts[0], parts[1], parts[2]
            JsonDb.upsert("gifts_catalog", "gift_id", state.get("gift_id"), {
                "emoji": emoji, 
                "stars": int(stars), 
                "price_usd": 0, 
                "price_uzs": int(price),
                "sell_price_uzs": int(price), 
                "active": 1, 
                "updated_at": _now(),
            })
            Helpers.set_state(tg_id, None)
            await Telegram.send_message(chat_id, "✅ Gift muvaffaqiyatli qo'shildi/yangilandi.")
            return

        if step == "admin_finduser":
            q = text.strip()
            if q.isdigit():
                u = JsonDb.first("users", lambda u: str(u.get("tg_id")) == q)
            else:
                q_username = q.lstrip("@")
                u = JsonDb.first("users", lambda u: str(u.get("username", "")).lower() == q_username.lower())
                
            Helpers.set_state(tg_id, None)
            if not u:
                await Telegram.send_message(chat_id, "❌ Foydalanuvchi topilmadi.")
                return
            await Telegram.send_message(chat_id, AdminHandler.user_card(u), reply_markup=AdminHandler.user_card_keyboard(u))
            return
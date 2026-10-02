from __future__ import annotations

import config
from core.helpers import Helpers
from core.keyboards import Keyboards
from core.settings import Settings
from core.telegram import Telegram

from handlers.start_handler import StartHandler
from handlers.account_handler import AccountHandler
from handlers.gram_handler import GramHandler
from handlers.balance_handler import BalanceHandler
from handlers.stars_handler import StarsHandler
from handlers.premium_handler import PremiumHandler
from handlers.gift_handler import GiftHandler
from handlers.pubg_handler import PubgHandler
from handlers.number_handler import NumberHandler
from handlers.admin_handler import AdminHandler

logger = config.logger

ADMIN_MENU_BUTTONS = {
    "📊 1. Statistika", "💳 2. To'lovlar holati", "🧾 3. Checkout API", "🌐 4. Fragment API",
    "🎮 5. Coindrop API", "🎁 6. Gift import", "⭐ 7. Bot hisobini to'ldirish", "🔌 8. Bot ON/OFF",
    "📱 9. Cheap-SMS API", "👥 Foydalanuvchilar", "⚙️ Menejerlar", "🚪 10. Chiqish",
}


class Router:
    @staticmethod
    async def handle_update(update: dict) -> None:
        try:
            if "message" in update:
                await Router._handle_message(update["message"])
            elif "callback_query" in update:
                await Router._handle_callback(update["callback_query"])
            elif "pre_checkout_query" in update:
                await Telegram.answer_pre_checkout_query(update["pre_checkout_query"]["id"], True)
        except Exception as e:
            logger.exception("Router xatosi: %s", e)

    @staticmethod
    async def _handle_message(msg: dict) -> None:
        from_user = msg.get("from")
        if not from_user or from_user.get("is_bot"):
            return

        chat_id = msg["chat"]["id"]
        user = Helpers.get_or_create_user(from_user)
        is_admin = Helpers.is_admin(from_user["id"])

        if Settings.get("bot_status", "on") != "on" and not is_admin:
            await Telegram.send_message(chat_id, Settings.get("maintenance_text"))
            return

        if user.get("banned"):
            await Telegram.send_message(chat_id, "🚫 Siz botdan foydalanishdan bloklangansiz.")
            return

        if "successful_payment" in msg:
            await AdminHandler.handle_stars_payment_success(chat_id, msg["successful_payment"])
            return

        if "web_app_data" in msg:
            await PubgHandler.handle_webapp_data(chat_id, user, msg["web_app_data"]["data"])
            return

        text = (msg.get("text") or "").strip()

        if text == "/start":
            Helpers.set_state(from_user["id"], None)
            await StartHandler.start(chat_id, user, is_admin)
            return

        if text == "/admin":
            if not is_admin:
                await Telegram.send_message(chat_id, "⛔️ Sizga ruxsat yo'q.")
                return
            Helpers.set_state(from_user["id"], None)
            await AdminHandler.open_panel(chat_id)
            return

        state = Helpers.get_state(from_user["id"])
        if state and not Router._is_menu_button(text):
            await Router._route_state(chat_id, user, is_admin, state, text)
            return

        if is_admin and await Router._route_admin_menu(chat_id, user, text):
            return

        await Router._route_main_menu(chat_id, user, text)

    @staticmethod
    def _is_menu_button(text: str) -> bool:
        return text in ADMIN_MENU_BUTTONS

    @staticmethod
    async def _route_state(chat_id: int, user: dict, is_admin: bool, state: dict, text: str) -> None:
        step = state.get("step", "")
        if text in ("/cancel", "❌ Bekor qilish"):
            Helpers.set_state(int(user["tg_id"]), None)
            await Telegram.send_message(chat_id, "Bekor qilindi.", reply_markup=Keyboards.main_menu())
            return

        if step.startswith("topup_"):
            await BalanceHandler.handle_state(chat_id, user, state, text)
        elif step.startswith("gram_"):
            await GramHandler.handle_state(chat_id, user, state, text)
        elif step.startswith("stars_"):
            await StarsHandler.handle_state(chat_id, user, state, text)
        elif step.startswith("premium_"):
            await PremiumHandler.handle_state(chat_id, user, state, text)
        elif step.startswith("gift_"):
            await GiftHandler.handle_state(chat_id, user, state, text)
        elif step.startswith("pubg_"):
            await PubgHandler.handle_state(chat_id, user, state, text)
        elif step.startswith("number_"):
            await NumberHandler.handle_state(chat_id, user, state, text)
        elif step.startswith("admin_"):
            await AdminHandler.handle_state(chat_id, user, state, text)
        else:
            Helpers.set_state(int(user["tg_id"]), None)

    @staticmethod
    async def _route_main_menu(chat_id: int, user: dict, text: str) -> None:
        await Telegram.send_message(chat_id, "Quyidagi menyudan kerakli bo'limni tanlang 👇", reply_markup=Keyboards.main_menu())

    @staticmethod
    async def _route_admin_menu(chat_id: int, user: dict, text: str) -> bool:
        mapping = {
            "📊 1. Statistika": AdminHandler.statistics,
            "💳 2. To'lovlar holati": AdminHandler.payments_report,
            "🧾 3. Checkout API": AdminHandler.checkout_api_menu,
            "🌐 4. Fragment API": AdminHandler.fragment_api_menu,
            "🎮 5. PlayPay": AdminHandler.coindrop_api_menu,
            "🎁 6. Gift import": AdminHandler.gift_import_menu,
            "⭐ 7. Bot hisobini to'ldirish": AdminHandler.stars_topup_menu,
            "🔌 8. Bot ON/OFF": AdminHandler.toggle_bot_status,
            "📱 9. Cheap-SMS API": AdminHandler.cheapsmm_api_menu,
            "👥 Foydalanuvchilar": AdminHandler.users_menu,
            "⚙️ Menejerlar": AdminHandler.managers_menu,
        }
        if text == "🚪 10. Chiqish":
            await AdminHandler.exit_panel(chat_id, user)
            return True
        fn = mapping.get(text)
        if fn:
            await fn(chat_id)
            return True
        return False

    @staticmethod
    async def _handle_callback(cq: dict) -> None:
        from_user = cq["from"]
        chat_id = cq["message"]["chat"]["id"]
        message_id = cq["message"]["message_id"]
        data = cq["data"]
        user = Helpers.get_or_create_user(from_user)
        is_admin = Helpers.is_admin(from_user["id"])

        if Settings.get("bot_status", "on") != "on" and not is_admin:
            await Telegram.answer_callback_query(cq["id"], "Bot texnik ishlarda", True)
            return

        if data == "cancel":
            Helpers.set_state(from_user["id"], None)
            await Telegram.answer_callback_query(cq["id"])
            await Telegram.edit_message_text(chat_id, message_id, "❌ Bekor qilindi.")
            return

        parts = (data.split(":", 2) + [None, None, None])[:3]
        scope, action, param = parts

        if scope == "menu":
            await Router._route_menu_callback(chat_id, user, action)
            await Telegram.answer_callback_query(cq["id"])
        elif scope == "topup":
            await BalanceHandler.callback(cq, chat_id, message_id, user, action, param)
        elif scope == "gram":
            await GramHandler.callback(cq, chat_id, message_id, user, action, param)
        elif scope == "stars":
            await StarsHandler.callback(cq, chat_id, message_id, user, action, param)
        elif scope == "premium":
            await PremiumHandler.callback(cq, chat_id, message_id, user, action, param)
        elif scope == "gift":
            await GiftHandler.callback(cq, chat_id, message_id, user, action, param)
        elif scope == "pubg":
            await PubgHandler.callback(cq, chat_id, message_id, user, action, param)
        elif scope == "number":
            await NumberHandler.callback(cq, chat_id, message_id, user, action, param)
        elif scope == "admin":
            await AdminHandler.callback(cq, chat_id, message_id, user, is_admin, action, param)
        elif scope == "nav":
            await Telegram.answer_callback_query(cq["id"])
            if action == "main":
                await StartHandler.start(chat_id, user, is_admin)
        else:
            await Telegram.answer_callback_query(cq["id"])

    @staticmethod
    async def _route_menu_callback(chat_id: int, user: dict, action: str | None) -> None:
        if action == "topup":
            await BalanceHandler.start(chat_id, user)
        elif action == "gram_buy":
            await GramHandler.start(chat_id, user)
        elif action == "gram_sell":
            await GramHandler.start(chat_id, user)
        elif action == "stars_buy":
            await StarsHandler.buy_start(chat_id, user)
        elif action == "stars_sell":
            await StarsHandler.sell(chat_id, user)
        elif action == "gift":
            await GiftHandler.start(chat_id, user)
        elif action == "nft_sell":
            await GramHandler.route_to_admin(chat_id, "nft_sell_admin", "🎭 NFT sotish")
        elif action == "premium":
            await PremiumHandler.start(chat_id, user)
        elif action == "channel_sell":
            await GramHandler.route_to_admin(chat_id, "channel_sell_admin", "📡 Kanal sotish")
        elif action == "pubg":
            await PubgHandler.start(chat_id, user)
        elif action == "number":
            await NumberHandler.start(chat_id, user)
        elif action == "account":
            await AccountHandler.show(chat_id, user)
        elif action == "help":
            await AccountHandler.help(chat_id)
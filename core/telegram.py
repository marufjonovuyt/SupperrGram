"""
Yupqa Telegram Bot API wrapper - httpx (async) asosida, aiogram kabi og'ir
freymvorklarsiz, PHP versiyasidagi Telegram.php bilan bir xil metodlar.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

import config
from core.keyboards import Keyboards

logger = config.logger

API_BASE = "https://api.telegram.org/bot{token}/{method}"

# Butun dastur davomida qayta ishlatiladigan bitta async HTTP klient
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=25)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()


class Telegram:
    @staticmethod
    async def _call(method: str, params: Optional[dict] = None) -> dict:
        url = API_BASE.format(token=config.BOT_TOKEN, method=method)
        client = _get_client()
        try:
            resp = await client.post(url, json=params or {})
        except httpx.HTTPError as e:
            logger.error("Telegram API cURL xato (%s): %s", method, e)
            return {"ok": False, "description": str(e)}

        try:
            data = resp.json()
        except ValueError:
            logger.error("Telegram API noto'g'ri javob (%s): %s", method, resp.text[:500])
            return {"ok": False, "description": "invalid_json"}

        if not isinstance(data, dict):
            return {"ok": False, "description": "invalid_json"}
        if not data.get("ok"):
            logger.error("Telegram API xato (%s): %s", method, data)
        return data

    @staticmethod
    async def send_message(chat_id: int, text: str, **extra: Any) -> dict:
        params = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            **extra,
        }
        return await Telegram._call("sendMessage", params)

    @staticmethod
    async def edit_message_text(chat_id: int, message_id: int, text: str, **extra: Any) -> dict:
        params = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            **extra,
        }
        return await Telegram._call("editMessageText", params)

    @staticmethod
    async def delete_message(chat_id: int, message_id: int) -> dict:
        return await Telegram._call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    @staticmethod
    async def clear_reply_keyboard(chat_id: int) -> None:
        """
        Pastki (reply) klaviaturani "iz qoldirmasdan" olib tashlaydi: kichik
        xabar remove_keyboard bilan yuboriladi, so'ng shu zahoti o'chiriladi.
        """
        res = await Telegram._call(
            "sendMessage",
            {"chat_id": chat_id, "text": ".", "reply_markup": Keyboards.remove()},
        )
        if res.get("ok") and res.get("result", {}).get("message_id"):
            await Telegram.delete_message(chat_id, int(res["result"]["message_id"]))

    @staticmethod
    async def answer_callback_query(callback_id: str, text: str = "", alert: bool = False) -> dict:
        return await Telegram._call(
            "answerCallbackQuery",
            {"callback_query_id": callback_id, "text": text, "show_alert": alert},
        )

    @staticmethod
    async def send_chat_action(chat_id: int, action: str = "typing") -> dict:
        return await Telegram._call("sendChatAction", {"chat_id": chat_id, "action": action})

    @staticmethod
    async def send_invoice_stars(chat_id: int, title: str, desc: str, payload: str, stars_amount: int) -> dict:
        # Telegram Stars orqali botning o'z hisobini to'ldirish (XTR valyuta)
        return await Telegram._call(
            "sendInvoice",
            {
                "chat_id": chat_id,
                "title": title,
                "description": desc,
                "payload": payload,
                "currency": "XTR",
                "prices": [{"label": title, "amount": stars_amount}],
            },
        )

    @staticmethod
    async def answer_pre_checkout_query(query_id: str, ok: bool, error_message: str = "") -> dict:
        params: dict = {"pre_checkout_query_id": query_id, "ok": ok}
        if not ok:
            params["error_message"] = error_message
        return await Telegram._call("answerPreCheckoutQuery", params)

    @staticmethod
    async def set_webhook(url: str) -> dict:
        return await Telegram._call(
            "setWebhook",
            {
                "url": url,
                "secret_token": config.WEBHOOK_SECRET,
                "allowed_updates": ["message", "callback_query", "pre_checkout_query", "web_app_data"],
            },
        )

    @staticmethod
    async def delete_webhook() -> dict:
        return await Telegram._call("deleteWebhook")

    @staticmethod
    async def get_updates(offset: int = 0, timeout: int = 25) -> dict:
        return await Telegram._call("getUpdates", {"offset": offset, "timeout": timeout})

    @staticmethod
    async def send_document(chat_id: int, file_path: str, caption: str = "") -> dict:
        url = API_BASE.format(token=config.BOT_TOKEN, method="sendDocument")
        client = _get_client()
        with open(file_path, "rb") as f:
            files = {"document": (file_path.split("/")[-1], f)}
            data = {"chat_id": str(chat_id), "caption": caption}
            try:
                resp = await client.post(url, data=data, files=files, timeout=30)
            except httpx.HTTPError as e:
                logger.error("sendDocument xato: %s", e)
                return {"ok": False, "description": str(e)}
        try:
            return resp.json()
        except ValueError:
            return {"ok": False, "description": "invalid_json"}

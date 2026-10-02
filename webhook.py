#!/usr/bin/env python3
"""
Webhook rejimida ishga tushirish (production uchun tavsiya etiladi):
    python3 webhook.py
    (ichki portda ishlaydi, oldida Nginx/Caddy orqali HTTPS bilan proxy qilinadi)

Yo'nalishlar (routes):
    POST /webhook                    - Telegram bot yangilanishlari shu yerga keladi
    GET  /webapp/pubg/                - Pubg UC mini-ilova sahifasi
    GET  /webapp/pubg/api             - mini-ilova uchun JSON API (validate/products)

DIQQAT: webhook.py YOKI polling.py - ikkalasini bir vaqtda ishlatmang.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from aiohttp import web

import config
from bootstrap import bootstrap
from core.json_db import JsonDb
from core.telegram import close_client
from handlers.router import Router
from api.playpay_api import CoindropApi
from handlers.pubg_handler import PubgHandler

logger = config.logger

PLAYER_ID_RE = re.compile(r"^\d{6,15}$")
WEBAPP_DIR = config.BASE_DIR / "webapp" / "pubg"

routes = web.RouteTableDef()


@routes.post("/webhook")
async def telegram_webhook(request: web.Request) -> web.Response:
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != config.WEBHOOK_SECRET:
        return web.Response(status=403, text="forbidden")

    try:
        update = await request.json()
    except (json.JSONDecodeError, ValueError):
        return web.Response(status=400, text="bad request")

    # Telegramni tezda "200 OK" bilan javob berish uchun update fon vazifasida
    # qayta ishlanadi (Telegram sekin javobda qayta-qayta yuborishga urinadi).
    async def _run():
        try:
            await Router.handle_update(update)
        except Exception:  # noqa: BLE001
            logger.exception("Webhook: update qayta ishlashda xatolik")

    request.app["tasks"].add(request.app.loop.create_task(_run()))
    return web.Response(text="ok")


@routes.get("/webapp/pubg/")
@routes.get("/webapp/pubg/index.html")
async def pubg_index(request: web.Request) -> web.Response:
    index_file = WEBAPP_DIR / "index.html"
    if not index_file.exists():
        return web.Response(status=404, text="not found")
    return web.Response(text=index_file.read_text(encoding="utf-8"), content_type="text/html")


@routes.get("/webapp/pubg/api.php")  # index.html ichidagi fetch("api.php?...") manzili bilan mos
async def pubg_api(request: web.Request) -> web.Response:
    action = request.query.get("action", "")
    headers = {"Access-Control-Allow-Origin": "*"}

    try:
        if action == "products":
            products = PubgHandler.list_products()
            return web.json_response({"ok": True, "products": products}, headers=headers)

        if action == "validate":
            player_id = (request.query.get("player_id") or "").strip()
            if not PLAYER_ID_RE.match(player_id):
                return web.json_response({"ok": False, "message": "ID noto'g'ri formatda"}, headers=headers)

            check = await CoindropApi.validate("pubg-mobile", player_id)
            if check.get("success") and check.get("valid"):
                return web.json_response(
                    {"ok": True, "player_name": check.get("username", player_id)}, headers=headers
                )
            return web.json_response(
                {"ok": False, "message": check.get("message") or "ID topilmadi"}, headers=headers
            )

        return web.json_response({"ok": False, "message": "unknown_action"}, headers=headers)
    except Exception:  # noqa: BLE001
        logger.exception("Mini-app api xatosi")
        return web.json_response({"ok": False, "message": "server_error"}, headers=headers, status=500)


@routes.get("/check_server")
async def check_server(request: web.Request) -> web.Response:
    """PHP versiyasidagi check_server.php o'rniga - server sog'ligini tekshirish"""
    checks = {}
    try:
        JsonDb.settings_all()
        checks["database"] = "ok"
    except Exception as e:  # noqa: BLE001
        checks["database"] = f"error: {e}"

    checks["python"] = "ok"
    checks["bot_token_configured"] = bool(config.BOT_TOKEN and config.BOT_TOKEN != "YOUR_BOT_TOKEN_HERE")
    return web.json_response({"status": "running", "checks": checks})


async def on_startup(app: web.Application) -> None:
    bootstrap()
    app["tasks"] = set()
    logger.info("HamyonUzRoBot webhook server ishga tushdi.")


async def on_cleanup(app: web.Application) -> None:
    for t in list(app["tasks"]):
        if not t.done():
            t.cancel()
    await close_client()


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes(routes)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=8080)

import asyncio
import datetime
import logging
import os
import re
import sqlite3
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from telethon import TelegramClient, events
from telethon.errors import AuthKeyUnregisteredError, FloodWaitError

import config

# === LOGLASH SOZLAMASI ===
logging.basicConfig(
    filename="checkout_system.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("CheckoutApi")

# === TELEGRAM USERBOT SOZLAMALARI ===
API_ID = getattr(config, "API_ID", 33186178)
API_HASH = getattr(config, "API_HASH", "42ca80e3a6ee41cb0cb5f5d0267da416")
SESSION_NAME = getattr(config, "SESSION_NAME", "userbot")
WEBHOOK_URL = getattr(config, "WEBHOOK_URL", "https://c578.coresuz.ru")

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


# ==========================================
# 1. MA'LUMOTLAR BAZASI (SQLite Setup)
# ==========================================
def get_db_connection():
    db_path = getattr(config, "DB_DIR", None)
    if db_path:
        db_file = str(db_path / "payments.db")
    else:
        db_file = "payments.db"
    return sqlite3.connect(db_file)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Kutilayotgan va bajarilgan buyurtmalar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            amount REAL NOT NULL,
            card_last4 TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Mos kelmagan / noma'lum to'lovlar (kechikkan yoki xato summa)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unmatched_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            card_last4 TEXT NOT NULL,
            source TEXT NOT NULL,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ==========================================
# 2. TO'LOV MANTIQI (PAYMENT ENGINE)
# ==========================================
class PaymentEngine:

    @staticmethod
    def cleanup_expired_orders():
        """5 daqiqadan o'tib ketgan buyurtmalarni EXPIRED ga o'tkazish"""
        conn = get_db_connection()
        cursor = conn.cursor()
        five_mins_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)

        cursor.execute(
            "UPDATE orders SET status = 'EXPIRED' WHERE status = 'PENDING' AND created_at < ?",
            (five_mins_ago,),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def create_order(user_id: str, base_amount: float, card_last4: str):
        """
        1 so'mdan oshirib noyob (unique) summa shakllantiradi va buyurtma yaratadi
        """
        PaymentEngine.cleanup_expired_orders()
        conn = get_db_connection()
        cursor = conn.cursor()

        target_amount = float(base_amount)
        while True:
            cursor.execute(
                "SELECT id FROM orders WHERE card_last4 = ? AND amount = ? AND status = 'PENDING'",
                (card_last4, target_amount),
            )
            if cursor.fetchone() is None:
                break
            target_amount += 1.0  # 1 so'm qo'shib noyob qilamiz

        cursor.execute(
            "INSERT INTO orders (user_id, amount, card_last4) VALUES (?, ?, ?)",
            (str(user_id), target_amount, str(card_last4)),
        )
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(
            f"🛒 Yangi buyurtma #{order_id}: User={user_id}, Summa={target_amount} UZS, Karta=***{card_last4}"
        )
        return {
            "order_id": order_id,
            "exact_amount": target_amount,
            "card": card_last4,
            "expires_in_minutes": 5,
        }

    @staticmethod
    def process_incoming_payment(amount: float, card_last4: str, source: str):
        """
        SMS kelganda to'lovni 1 so'mgacha aniqlikda tekshiradi
        """
        PaymentEngine.cleanup_expired_orders()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, user_id FROM orders 
            WHERE card_last4 = ? AND amount = ? AND status = 'PENDING'
            ORDER BY id ASC LIMIT 1
        """,
            (str(card_last4), float(amount)),
        )

        order = cursor.fetchone()

        if order:
            order_id, user_id = order
            cursor.execute(
                "UPDATE orders SET status = 'PAID' WHERE id = ?", (order_id,)
            )
            conn.commit()
            conn.close()

            logger.info(
                f"✅ TO'LOV TASDIQLANDI! Order #{order_id} | User: {user_id} | Summa: {amount} UZS | Manba: {source}"
            )
            return True
        else:
            cursor.execute(
                "INSERT INTO unmatched_payments (amount, card_last4, source) VALUES (?, ?, ?)",
                (float(amount), str(card_last4), str(source)),
            )
            conn.commit()
            conn.close()

            logger.warning(
                f"⚠️ BEGONA / KECHIKKAN TO'LOV! Summa: {amount} UZS | Karta: ***{card_last4} | Manba: {source}"
            )
            return False


# ==========================================
# 3. CHECKOUT API KLASI (Bot va Handlerlar uchun)
# ==========================================
class CheckoutApi:
    """
    admin_handler.py, router.py va bot import qiladigan asosiy API klasi
    """

    def __init__(self, webhook_url: str = WEBHOOK_URL, api_key: str = None):
        self.webhook_url = webhook_url
        self.api_key = api_key or getattr(config, "DEFAULT_SETTINGS", {}).get(
            "checkout_api_key", ""
        )
        self.base_url = getattr(
            config, "CHECKOUT_API_URL", "http://127.0.0.1:8000/api"
        ).rstrip("/")

    async def mark_paid(self, amount: str, card: str, source: str = "Telegram"):
        """Serverga Webhook POST so'rovini yuboradi"""
        payload = {
            "method": "markPaid",
            "amount": str(amount),
            "card": str(card),
            "source": str(source),
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url, data=payload, timeout=15
                ) as resp:
                    result = await resp.text()
                    logger.info(
                        f"✅ Webhook yuborildi [{source}]: {payload} | Status: {resp.status} | Javob: {result}"
                    )
                    return result
        except Exception as e:
            logger.error(
                f"❌ Webhook yuborishda xatolik [{source}]: {e}", exc_info=True
            )
            return None

    async def create_order(
        self, user_id: str, amount: float, card_last4: str = None
    ):
        """Buyurtma yaratish"""
        card = card_last4 or getattr(config, "DEFAULT_SETTINGS", {}).get(
            "card_last4", "1234"
        )
        return PaymentEngine.create_order(user_id, amount, card)

    async def check_order(self, order_id: int):
        """Buyurtma holatini tekshirish"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {"order_id": order_id, "status": row[0]}
        return None

    async def get_balance(self) -> float:
        """Admin panel uchun hisob balansi"""
        return 0.0


# Instansiya yaratamiz
checkout_api_instance = CheckoutApi()


# ==========================================
# 4. TELEGRAM USERBOT HANDLERLARI
# ==========================================
@client.on(events.NewMessage(from_users="@CardXabarBot"))
async def cardxabar_handler(event):
    try:
        text = event.raw_text
        logger.info(f"🟢 CardXabarBot xabari: {text}")

        if "🟢 Kartaga o'tkazma" in text:
            summa_match = re.search(r"➕\s*([\d\s]+,\d+|[\d\s]+\.\d+|\d+)", text)
            karta_match = re.search(r"\*{3}(\d{4})", text)

            if summa_match and karta_match:
                raw_sum = (
                    summa_match.group(1).replace(" ", "").replace(",", ".")
                )
                summa = float(raw_sum)
                karta = karta_match.group(1)

                PaymentEngine.process_incoming_payment(
                    summa, karta, source="CardXabarBot"
                )
                await checkout_api_instance.mark_paid(
                    amount=str(summa), card=karta, source="CardXabarBot"
                )
            else:
                logger.warning("❌ CardXabarBot: Summa yoki karta mos kelmadi.")
    except Exception as e:
        logger.error(f"CardXabarBot xatosi: {e}", exc_info=True)


@client.on(events.NewMessage(from_users="@HUMOcardbot"))
async def humo_handler(event):
    try:
        text = event.raw_text
        logger.info(f"🎉 HUMOcardbot xabari: {text}")

        if "🎉 To'ldirish" in text:
            summa_match = re.search(r"➕\s*([\d\s.,]+)", text)
            karta_match = re.search(r"\*?(\d{4})", text)

            if summa_match and karta_match:
                raw_sum = (
                    summa_match.group(1)
                    .replace(" ", "")
                    .replace(".", "")
                    .replace(",", ".")
                )
                summa = float(raw_sum)
                karta = karta_match.group(1)

                PaymentEngine.process_incoming_payment(
                    summa, karta, source="HUMOcardbot"
                )
                await checkout_api_instance.mark_paid(
                    amount=str(summa), card=karta, source="HUMOcardbot"
                )
            else:
                logger.warning("❌ HUMOcardbot: Summa yoki karta mos kelmadi.")
    except Exception as e:
        logger.error(f"HUMOcardbot xatosi: {e}", exc_info=True)


# ==========================================
# 5. FASTAPI SERVER VA LIFESPAN RUNNER
# ==========================================
async def start_telethon():
    while True:
        try:
            logger.info("🚀 Userbot ulanmoqda...")
            await client.start()
            logger.info("✅ Telegram Userbot muvaffaqiyatli ishga tushdi!")
            await client.run_until_disconnected()
        except FloodWaitError as e:
            logger.error(f"FloodWait: {e.seconds} soniya kutilmoqda...")
            await asyncio.sleep(e.seconds + 5)
        except AuthKeyUnregisteredError:
            logger.critical("Session bekor qilindi.")
            break
        except Exception as e:
            logger.error(f"Userbot qayta ulanmoqda: {e}")
            await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    telethon_task = asyncio.create_task(start_telethon())
    yield
    await client.disconnect()
    telethon_task.cancel()


app = FastAPI(title="P2P Auto Payment System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === PUBG API ENDPOINTLARI ===
@app.get("/api/pubg/validate")
async def validate_pubg_id(player_id: str):
    if not player_id.isdigit() or not (6 <= len(player_id) <= 15):
        return {"ok": False, "message": "ID noto'g'ri kiritildi"}
    return {
        "ok": True,
        "player_id": player_id,
        "player_name": f"PUBG_PLAYER_{player_id[-4:]}",
    }


@app.get("/api/pubg/products")
async def get_pubg_products():
    products = [
        {"product_id": 1, "name": "60 UC", "sell_price_uzs": 13000},
        {"product_id": 2, "name": "325 UC", "sell_price_uzs": 72000},
        {"product_id": 3, "name": "660 UC", "sell_price_uzs": 140000},
        {"product_id": 4, "name": "1800 UC", "sell_price_uzs": 380000},
    ]
    return {"ok": True, "products": products}


# === TO'LOV ENDPOINTLARI ===
class CreateOrderRequest(BaseModel):
    user_id: str
    amount: float
    card_last4: str


@app.post("/api/create-order")
async def api_create_order(req: CreateOrderRequest):
    res = PaymentEngine.create_order(req.user_id, req.amount, req.card_last4)
    return {"status": "success", "data": res}


@app.get("/api/check-order/{order_id}")
async def api_check_order(order_id: int):
    res = await checkout_api_instance.check_order(order_id)
    if not res:
        raise HTTPException(status_code=404, detail="Order topilmadi")
    return res


# ==========================================
# 6. IMPORT ALIASE'LARI (Barcha import xatolarini to'liq yopadi)
# ==========================================
CheckoutApi = CheckoutApi
CheckoutAPI = CheckoutApi
checkout_api = checkout_api_instance

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("checkout_api:app", host="0.0.0.0", port=8000, reload=False)
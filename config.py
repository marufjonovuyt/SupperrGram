"""
HamyonUzRoBot - Asosiy sozlamalar fayli (O'zimizning FastAPI Checkout ga moslangan)
"""

import hashlib
import logging
import os
from pathlib import Path

# ==== 1. ASOSIY PAPKALAR VA YO'LLAR ====
BASE_DIR = Path(__file__).resolve().parent

DB_DIR = BASE_DIR / "database"
LOG_DIR = BASE_DIR / "logs"

DB_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ==== 2. BOT VA MAXFIY SOZLAMALAR ====
BOT_TOKEN = os.environ.get(
    "BOT_TOKEN", "8404752815:AAGiVYNM0CyIsh0CLQzK4AAforVJNRrC2_I"
)
BOT_USERNAME = (
    os.environ.get("BOT_USERNAME", "SuperGram_Bot").replace("@", "").strip()
)

_default_secret = hashlib.md5(BOT_TOKEN.encode()).hexdigest()[:12]
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", f"secret_{_default_secret}")


# ==== 3. SUPER ADMINLAR ====
_env_admins = os.environ.get("SUPER_ADMIN_IDS", "")
if _env_admins:
    SUPER_ADMIN_IDS = [
        int(x.strip()) for x in _env_admins.split(",") if x.strip().isdigit()
    ]
else:
    SUPER_ADMIN_IDS = [
        8754614153,
    ]


# ==== 4. LOCAL / EXTERNAL API BASE URLS ====
# Tashqi checkout.uz o'rniga o'zimizning FastAPI serverimiz
CHECKOUT_API_URL = os.environ.get("CHECKOUT_API_URL", "http://127.0.0.1:8000/api")
FRAGMENT_API_URL = os.environ.get("FRAGMENT_API_URL", "https://fragment-api.uz/api/v1")
COINDROP_API_URL = os.environ.get("COINDROP_API_URL", "https://coindrop.uz/api/v1")
CHEAPSMM_API_URL = os.environ.get("CHEAPSMM_API_URL", "https://cheap-smm.uz/sms")


# ==== 5. BOT SOZLAMALARI (DEFAULT SETTINGS) ====
DEFAULT_SETTINGS = {
    "bot_status": "on",
    "card_last4": "1234",  # To'lov qabul qiluvchi kartangizning oxirgi 4 raqami
    "fragment_api_key": "",
    "coindrop_api_key": "",
    "cheapsmm_api_key": "",
    "fragment_markup_uzs": "350",
    "number_markup_uzs": "500",
    "gift_markup_uzs": "1000",
    "usd_to_uzs": "12700",
    "gram_buy_admin": "",
    "gram_sell_admin": "",
    "stars_sell_admin": "",
    "channel_sell_admin": "",
    "nft_sell_admin": "",
    "webapp_url": os.environ.get(
        "WEBAPP_URL", "https://c578.coresuz.ru/webapp/pubg/index.html"
    ),
    "bot_stars_balance": "0",
    "maintenance_text": (
        "🛠 Botda vaqtincha texnik ishlar olib borilmoqda.\n"
        "Iltimos, birozdan so'ng qayta urinib ko'ring."
    ),
}


# ==== 6. TIMEZONE ====
try:
    from zoneinfo import ZoneInfo
    TASHKENT_TZ = ZoneInfo("Asia/Tashkent")
except Exception:
    import datetime
    TASHKENT_TZ = datetime.timezone(datetime.timedelta(hours=5))


# ==== 7. LOGLASH ====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "error.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("HamyonUzRoBot")
"""
config.py - HamyonUzRoBot Asosiy sozlamalar fayli
"""

import hashlib
import logging
import os
from pathlib import Path

# ==== 1. ASOSIY PAPKALAR ====
BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"
LOG_DIR = BASE_DIR / "logs"

DB_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ==== 2. BOT VA MAXFIY SOZLAMALAR ====
BOT_TOKEN = os.environ.get(
    "BOT_TOKEN", "8404752815:AAGiVYNM0CyIsh0CLQzK4AAforVJNRrC2_I"
)
BOT_USERNAME = (
    os.environ.get("BOT_USERNAME", "SuperGram_Bot").replace("@", "").strip()
)

_default_secret = hashlib.md5(BOT_TOKEN.encode()).hexdigest()[:12]
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", f"secret_{_default_secret}")


# ==== 3. SUPER ADMINLAR ====
_env_admins = os.environ.get("SUPER_ADMIN_IDS", "")
if _env_admins:
    SUPER_ADMIN_IDS = [
        int(x.strip()) for x in _env_admins.split(",") if x.strip().isdigit()
    ]
else:
    SUPER_ADMIN_IDS = [8754614153]


# ==== 4. API BASE URLS ====
CHECKOUT_API_URL = os.environ.get(
    "CHECKOUT_API_URL", "http://127.0.0.1:8000/api"
)
FRAGMENT_API_URL = os.environ.get(
    "FRAGMENT_API_URL", "https://fragment-api.uz/api/v1"
)
COINDROP_API_URL = os.environ.get(
    "COINDROP_API_URL", "https://coindrop.uz/api/v1"
)
CHEAPSMM_API_URL = os.environ.get(
    "CHEAPSMM_API_URL", "https://cheap-smm.uz/sms"
)


# ==== 5. BOT SOZLAMALARI ====
DEFAULT_SETTINGS = {
    "bot_status": "on",
    "card_last4": "1234",
    "coindrop_api_key": os.environ.get("COINDROP_API_KEY", ""),
    "fragment_api_key": "",
    "cheapsmm_api_key": "",
    "fragment_markup_uzs": "350",
    "number_markup_uzs": "500",
    "gift_markup_uzs": "1000",
    "usd_to_uzs": "12700",
    "webapp_url": os.environ.get(
        "WEBAPP_URL", "https://c578.coresuz.ru/webapp/pubg/index.html"
    ),
    "bot_stars_balance": "0",
    "maintenance_text": (
        "🛠 Botda vaqtincha texnik ishlar olib borilmoqda.\n"
        "Iltimos, birozdan so'ng qayta urinib ko'ring."
    ),
}


# ==== 6. TIMEZONE ====
try:
    from zoneinfo import ZoneInfo

    TASHKENT_TZ = ZoneInfo("Asia/Tashkent")
except Exception:
    import datetime

    TASHKENT_TZ = datetime.timezone(datetime.timedelta(hours=5))


# ==== 7. LOGGING ====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "error.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("HamyonUzRoBot")
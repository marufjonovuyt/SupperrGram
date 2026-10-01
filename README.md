# HamyonUzRoBot — Python versiyasi (HaytonPython)

Bu bot asl PHP loyihasining **to'liq Python (3.12+) porti**. Hech qanday PHP
kod qolmagan — barcha mantiq `asyncio` + `httpx` (Telegram/tashqi API'lar
uchun) va `aiohttp` (webhook server uchun) yordamida qayta yozilgan.

Ma'lumotlar bazasi ham avvalgidek — SQL emas, oddiy `.json` fayllar
(`database/` papkasida), fayl qulflash (`fcntl.flock`) bilan xavfsiz yozish.

## Imkoniyatlar (asl botdagi barcha funksiyalar saqlangan)

- 👛 Hisobni to'ldirish — Checkout.uz orqali (Click/Payme va h.k.)
- 💎 Gram olish/sotish — menejerga yo'naltirish
- ⭐ Stars olish (Fragment API) / sotish — menejerga yo'naltirish
- ⭐️ Telegram Premium olish (Fragment API)
- 🧸 Telegram Gift yuborish (Coindrop API)
- 🎭 NFT sotish, 📡 Kanal sotish — menejerga yo'naltirish
- 🎮 PUBG Mobile UC sotib olish — Telegram Mini App (WebApp) yoki chat orqali
- 📱 Virtual raqam olish (Cheap-SMM API), SMS kodni tekshirish
- 🛡 To'liq admin panel: statistika, to'lovlar hisobot fayli, API kalitlar,
  gift/mahsulot import, bot Stars balansi, bot ON/OFF, foydalanuvchilarni
  boshqarish (balans qo'shish/ayirish, bloklash), menejerlarni sozlash

## Talablar

- **Python 3.12 yoki undan yangi** (2026-yil avgust holatiga eng so'nggi barqaror versiya)
- `pip install -r requirements.txt` (httpx, aiohttp)

## O'rnatish

```bash
cd HaytonPython
pip install -r requirements.txt --break-system-packages   # kerak bo'lsa
```

`config.py` faylini oching va quyidagilarni to'ldiring:

- `BOT_TOKEN` — @BotFather'dan olingan token
- `BOT_USERNAME` — bot username (@ belgisisiz)
- `SUPER_ADMIN_IDS` — o'zingizning Telegram ID raqamingiz (ro'yxat, bir nechta bo'lishi mumkin)

Muhit o'zgaruvchilari orqali ham berish mumkin (tavsiya etiladi, ayniqsa production'da):

```bash
export BOT_TOKEN="123456:AA...."
export BOT_USERNAME="HamyonUzRoBot"
```

So'ng bazani yaratish uchun:

```bash
python3 install.py
```

## Ishga tushirish

**1-usul — Webhook (production uchun tavsiya etiladi, HTTPS domen kerak):**

```bash
python3 webhook.py            # 0.0.0.0:8080 da ishga tushadi
```

Nginx/Caddy orqali `https://domeningiz.uz/webhook` manzilini shu portga
proxy qiling, so'ng:

```bash
python3 set_webhook.py https://domeningiz.uz/webhook
```

**2-usul — Long polling (domen/HTTPS shart emas, oddiy VPS uchun qulay):**

```bash
python3 polling.py
```

> ⚠️ Webhook va polling'ni bir vaqtning o'zida ishlatmang — faqat bittasini tanlang.

Doimiy ishlab turishi uchun `systemd`, `supervisor` yoki `tmux`/`screen`
ishlatishni tavsiya qilamiz. Masalan systemd uchun oddiy unit fayl namunasi:

```ini
[Unit]
Description=HamyonUzRoBot
After=network.target

[Service]
WorkingDirectory=/path/to/HaytonPython
ExecStart=/usr/bin/python3 polling.py
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

## Birinchi qadamlar botda

1. Botga `/start` yuboring.
2. O'zingiz (super admin) bo'lsangiz, `/admin` yuboring — boshqaruv paneli ochiladi.
3. Admin panelda tartib bilan:
   - **3. Checkout API** — to'lov qabul qilish kaliti
   - **4. Fragment API** — Stars/Premium kaliti (kiritilgach avtomatik tekshiriladi)
   - **5. Coindrop API** — PUBG UC va Gift kaliti (kiritilgach mahsulotlar avtomatik import qilinadi)
   - **9. Cheap-SMS API** — virtual raqamlar kaliti (kiritilgach davlatlar avtomatik import qilinadi)
   - **⚙️ Menejerlar** — Gram/Stars sotish, Kanal/NFT sotish uchun @username'larni kiriting

## Loyiha tuzilishi

```
HaytonPython/
├── config.py              # sozlamalar
├── bootstrap.py           # baza/sozlamalarni ishga tushirish
├── install.py             # birinchi o'rnatish
├── set_webhook.py         # webhook o'rnatish
├── webhook.py             # aiohttp webhook server + mini-app
├── polling.py             # long-polling rejimi
├── core/
│   ├── json_db.py         # JSON fayl-baza (fcntl bilan xavfsiz)
│   ├── settings.py        # sozlamalar keshi
│   ├── telegram.py        # Telegram Bot API wrapper (httpx)
│   ├── keyboards.py       # klaviaturalar
│   └── helpers.py         # umumiy yordamchi funksiyalar
├── api/
│   ├── checkout_api.py
│   ├── fragment_api.py
│   ├── coindrop_api.py
│   └── cheapsmm_api.py
├── handlers/
│   ├── router.py          # barcha update'larni yo'naltiruvchi asosiy modul
│   ├── start_handler.py
│   ├── account_handler.py
│   ├── gram_handler.py
│   ├── balance_handler.py
│   ├── stars_handler.py
│   ├── premium_handler.py
│   ├── gift_handler.py
│   ├── pubg_handler.py
│   ├── number_handler.py
│   └── admin_handler.py
├── webapp/pubg/index.html # PUBG UC mini-ilova (o'zgarishsiz)
├── database/               # .json fayllar shu yerda saqlanadi (avtomatik yaratiladi)
└── logs/                   # xatolik loglari
```

## Eslatmalar

- Asl PHP loyihada bo'lgani kabi, baza hali ham oddiy `.json` fayllar —
  agar foydalanuvchilar soni juda ko'payib ketsa (o'nlab minglab), kelajakda
  PostgreSQL/SQLite'ga o'tish tavsiya etiladi, lekin hozirgi ko'lam uchun bu
  yechim yetarli va PHP versiyasi bilan bir xil formatga ega.
- `core/keyboards.py` tugmalarida `style` maydoni ishlatiladi (Bot API 9.4,
  2026-yil fevral) — rangli tugmalar (`primary`/`danger`/`success`) uchun.

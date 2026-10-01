"""
api/coindrop_api.py - CoinDrop API v1 Rasmiy Integratsiyasi
"""

import logging
import aiohttp
import config

logger = logging.getLogger(__name__)


class CoindropApi:

    def __init__(self, api_key: str = None):
        self.api_key = (
            api_key
            or config.DEFAULT_SETTINGS.get("coindrop_api_key")
            or ""
        )
        self.base_url = "https://coindrop.uz/api/v1"

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Key": self.api_key,
        }

    async def get_services(self):
        """CoinDrop v1 API orqali xizmatlarni olish"""
        url = f"{self.base_url}/services"
        headers = self._get_headers()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict):
                            return (
                                data.get("services")
                                or data.get("data")
                                or data.get("products")
                                or data.get("result")
                                or []
                            )
                    else:
                        text = await resp.text()
                        logger.error(f"❌ CoinDrop API xatoligi [{resp.status}]: {text}")
        except Exception as e:
            logger.error(f"❌ CoinDrop API ga ulanishda xato: {e}")
        return []

    async def import_pubg_packages(self):
        """PUBG Mobile paketlarini filtrlab olish"""
        all_services = await self.get_services()
        pubg_list = []

        for item in all_services:
            name = str(
                item.get("name")
                or item.get("service_name")
                or item.get("title")
                or ""
            ).lower()
            category = str(
                item.get("category") or item.get("category_name") or ""
            ).lower()
            game_key = str(
                item.get("game_key") or item.get("game") or ""
            ).lower()

            if "pubg" in name or "pubg" in category or "pubg" in game_key or "uc" in name:
                pkg = {
                    "game_key": item.get("game_key") or "pubg-mobile",
                    "product_id": str(
                        item.get("id")
                        or item.get("product_id")
                        or item.get("service_id")
                        or item.get("service")
                    ),
                    "name": item.get("name")
                    or item.get("service_name")
                    or item.get("title"),
                    "price_uzs": float(
                        item.get("price_uzs")
                        or item.get("rate")
                        or item.get("price")
                        or 0
                    ),
                    "category": item.get("category") or "PUBG Mobile",
                }
                pubg_list.append(pkg)

        logger.info(f"🎯 Jami {len(pubg_list)} ta PUBG paketi topildi.")
        return pubg_list

    # --- ATRIBUT XATOSINI 100% YO'Q QILUVCHI METOD ---
    @classmethod
    async def products(cls, game_key: str = "pubg-mobile"):
        """PubgHandler to'g'ridan-to'g'ri chaqiradigan classmethod"""
        instance = cls()
        return await instance.import_pubg_packages()

    async def create_order(
        self,
        game_key: str,
        product_id: str,
        player_id: str,
        server_id: str = None,
        amount: float = None,
        external_ref: str = None,
        notification_url: str = None,
    ):
        """Rasmiy POST /api/v1/orders orqali buyurtma berish"""
        url = f"{self.base_url}/orders"
        headers = self._get_headers()

        payload = {
            "game_key": game_key,
            "player_id": str(player_id),
        }

        if product_id:
            payload["product_id"] = str(product_id)
        if amount is not None:
            payload["amount"] = float(amount)
        if server_id:
            payload["server_id"] = str(server_id)
        if external_ref:
            payload["external_ref"] = str(external_ref)
        if notification_url:
            payload["notification_url"] = str(notification_url)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, headers=headers, timeout=20
                ) as resp:
                    res_data = await resp.json()
                    if resp.status == 200 and res_data.get("success"):
                        return res_data
                    else:
                        return {"success": False, "error": res_data}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Aliaslar
CheckoutApi = CoindropApi
checkout_api = CoindropApi()
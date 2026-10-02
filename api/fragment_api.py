"""
fragment_api.uz (https://fragment-api.uz/api) - Telegram Stars va Premium
"""
from __future__ import annotations

from typing import Optional

import time
import json
from pathlib import Path
import httpx

import config
from core.settings import Settings

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=25)
    return _client


class FragmentApi:
    @staticmethod
    async def _request(endpoint: str, body: Optional[dict] = None) -> dict:
        key = Settings.get("fragment_api_key", "")
        client = _get_client()
        # Endpoint oldidagi slashlarni to'g'rilab olamiz
        url = config.FRAGMENT_API_URL.rstrip("/") + "/" + endpoint.lstrip("/")
        try:
            resp = await client.post(
                url,
                json=body or {},
                headers={"Content-Type": "application/json", "X-API-Key": key},
            )
        except httpx.HTTPError:
            return {"ok": False, "message": "connection_error", "code": "CONNECTION_ERROR"}
        try:
            data = resp.json()
        except ValueError:
            return {"ok": False, "message": "invalid_response", "code": "INVALID_RESPONSE"}
        return data if isinstance(data, dict) else {"ok": False, "message": "invalid_response", "code": "INVALID_RESPONSE"}

    @staticmethod
    async def get_info(username: str) -> dict:
        return await FragmentApi._request("/getInfo", {"username": username.lstrip("@")})

    @staticmethod
    async def stars_pricing(amount: int) -> dict:
        return await FragmentApi._request("/stars/pricing", {"amount": amount})

    @staticmethod
    async def premium_pricing() -> dict:
        return await FragmentApi._request("/premium/pricing", {})

    @staticmethod
    async def buy_stars(amount: int, username: str) -> dict:
        return await FragmentApi._request("/stars/buy", {"amount": amount, "username": username.lstrip("@")})

    @staticmethod
    async def buy_premium(duration: int, username: str) -> dict:
        return await FragmentApi._request("/premium/buy", {"duration": duration, "username": username.lstrip("@")})

    @staticmethod
    async def wallet_balance() -> dict:
        return await FragmentApi._request("/wallet/balance", {})

    @staticmethod
    async def wallet_calculate() -> dict:
        """Joriy balansga qancha Stars va qaysi Premium paketlari yetishini tekshiradi"""
        return await FragmentApi._request("/wallet/calculate", {})

    @staticmethod
    def usd_to_uzs_with_markup(usd: float) -> int:
        """USD narxni so'mga aylantirib, ustiga sozlamalardagi foyda summasini qo'shadi"""
        rate = float(Settings.get("usd_to_uzs", 12700))
        markup = int(float(Settings.get("fragment_markup_uzs", 350)))
        return round(usd * rate) + markup



# FragmentApi klassi ichiga yoki tashqarisiga qo'shish mumkin:
    @staticmethod
    async def get_ton_price() -> float | None:
        """TON narxini CoinGecko orqali kesh bilan olish"""
        cache_file = Path(__file__).resolve().parent / 'ton_price_cache.json'
        cache_time = 300  # 5 daqiqa kesh
        
        if cache_file.exists() and (time.time() - cache_file.stat().st_mtime < cache_time):
            try:
                data = json.loads(cache_file.read_text(encoding='utf-8'))
                return data.get('usd')
            except Exception:
                pass
        
        try:
            client = _get_client()
            resp = await client.get("https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd")
            if resp.status_code == 200:
                price = resp.json().get('the-open-network', {}).get('usd')
                if price:
                    cache_file.write_text(json.dumps({'usd': price}), encoding='utf-8')
                    return price
        except Exception:
            pass
        
        # Agar API ishlamasa eski keshni o'qish
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding='utf-8'))
                return data.get('usd')
            except Exception:
                pass
        return None
"""cheap-smm.uz SMS API (https://cheap-smm.uz/sms-doc) - virtual raqamlar"""
from __future__ import annotations

from typing import Optional

import httpx

import config
from core.settings import Settings

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=20)
    return _client


class CheapSmmApi:
    @staticmethod
    async def _request(params: dict) -> dict:
        key = Settings.get("cheapsmm_api_key", "")
        params = {**params, "apiKey": key}
        client = _get_client()
        try:
            resp = await client.get(config.CHEAPSMM_API_URL, params=params)
        except httpx.HTTPError:
            return {"status": False, "message": "connection_error"}
        try:
            data = resp.json()
        except ValueError:
            return {"status": False, "message": "invalid_response"}
        return data if isinstance(data, dict) else {"status": False, "message": "invalid_response"}

    @staticmethod
    async def get_balance() -> dict:
        return await CheapSmmApi._request({"action": "getBalance"})

    @staticmethod
    async def get_countries() -> dict:
        return await CheapSmmApi._request({"action": "getCountries"})

    @staticmethod
    async def buy_number(country: str) -> dict:
        return await CheapSmmApi._request({"action": "buyNumber", "country": country})

    @staticmethod
    async def get_code(hash_code: str) -> dict:
        return await CheapSmmApi._request({"action": "getCode", "hash_code": hash_code})

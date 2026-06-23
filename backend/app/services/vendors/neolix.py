import hashlib
import random
import string
import time
from typing import Any

import httpx

from app.models.entities import VendorAccount
from app.services.vendors.base import VendorAdapter


class NeolixAdapter(VendorAdapter):
    def __init__(self, account: VendorAccount) -> None:
        super().__init__(account)
        self.base_url = (account.base_url or "").rstrip("/")
        self.config = account.config or {}
        self.secret_config = account.secret_config or {}

    def _signature(self, timestamp: str, nonce: str) -> str:
        """生成 SHA-1 签名，输出大写 hex（与官方 Java SDK SignUtil.getSignature 一致）。"""
        app_secret = self.secret_config.get("client_secret") or self.config.get("client_secret") or ""
        content = "".join(sorted([app_secret, timestamp, nonce]))
        return hashlib.sha1(content.encode("utf-8")).hexdigest().upper()

    def _headers(self) -> dict[str, str]:
        return {
            "X-From": self.config.get("x_from", "88e01d37NvKINh0LRm0NSivW"),
            "X-Version": self.config.get("x_version", "0.1.0"),
        }

    def get_access_token(self) -> str:
        client_id = self.config.get("client_id") or self.secret_config.get("client_id")
        client_secret = self.secret_config.get("client_secret") or self.config.get("client_secret")
        if not self.base_url or not client_id or not client_secret:
            raise ValueError("neolix base_url/client_id/client_secret are required")
        with httpx.Client(timeout=10) as client:
            response = client.post(
                f"{self.base_url}/auth/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            # 兼容两种响应格式：{access_token:...} 或 {data:{access_token:...}}
            if "data" in data and isinstance(data["data"], dict):
                return data["data"]["access_token"]
            return data["access_token"]

    def _signed_params(self, access_token: str) -> dict[str, Any]:
        timestamp = str(int(time.time()))
        # 与官方 Java SDK 一致：2位数字，只含 1-9（不含 0）
        nonce = "".join(random.choices("123456789", k=2))
        return {
            "signature": self._signature(timestamp, nonce),
            "timeStamp": timestamp,
            "nonce": nonce,
            "access_token": access_token,
        }

    def test_connection(self) -> dict[str, Any]:
        try:
            token = self.get_access_token()
            return {"status": "ok", "message": "token acquired", "token_preview": token[:6] + "***"}
        except Exception as exc:
            return {"status": "failed", "message": str(exc)}

    def fetch_vehicle_list(self) -> list[dict[str, Any]]:
        token = self.get_access_token()
        params = self._signed_params(token)
        user_id = self.config.get("user_id")
        if user_id:
            params["userId"] = user_id
        with httpx.Client(timeout=15) as client:
            response = client.get(
                f"{self.base_url}/openapi-server/slvapi/getVehicleList",
                params=params,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data") or []

    def batch_get_realtime(self, vins: list[str]) -> list[dict[str, Any]]:
        token = self.get_access_token()
        with httpx.Client(timeout=15) as client:
            response = client.post(
                f"{self.base_url}/openapi-server/slvapi/batchGetVehicleList",
                params=self._signed_params(token),
                json={"vin": vins},
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data") or []


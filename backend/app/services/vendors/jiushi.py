"""九识适配器 — 同时支持 MQTT 推送（模式 B）和 HTTP 开放 API"""

import socket
from typing import Any

import httpx

from app.models.entities import VendorAccount
from app.services.vendors.base import VendorAdapter


# 九识开放 API 默认地址
JIUSHI_API_BASE_URLS = {
    "test": "https://gateway-uat.zelostech.com.cn/business-proxy/open-apis",
    "production": "https://gateway.zelostech.com.cn/business-proxy/open-apis",
}

JIUSHI_AUTH_BASE_URLS = {
    "test": "https://auth-uat.zelostech.com.cn/app",
    "production": "https://auth.zelostech.com.cn/app",
}


class JiushiAdapter(VendorAdapter):
    def __init__(self, account: VendorAccount) -> None:
        super().__init__(account)
        self.config = account.config or {}
        self.secret_config = account.secret_config or {}
        self.environment = account.environment or "test"

    # ------------------------------------------------------------------
    # 开放 API（HTTP REST）
    # ------------------------------------------------------------------

    @property
    def api_base_url(self) -> str:
        """获取开放 API 的 base_url"""
        return self.config.get("api_base_url") or JIUSHI_API_BASE_URLS.get(self.environment, JIUSHI_API_BASE_URLS["test"])

    @property
    def auth_base_url(self) -> str:
        return JIUSHI_AUTH_BASE_URLS.get(self.environment, JIUSHI_AUTH_BASE_URLS["test"])

    def _get_access_token(self) -> str:
        """通过 appId + appKey 换取 token"""
        app_id = self.secret_config.get("app_id") or self.config.get("app_id")
        app_key = self.secret_config.get("app_key") or self.config.get("app_key")
        if not app_id or not app_key:
            raise ValueError("九识开放API需要配置 appId 和 appKey")

        with httpx.Client(timeout=10) as client:
            response = client.post(
                f"{self.auth_base_url}/accessToken",
                json={"appId": app_id, "appKey": app_key},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            success = data.get("success") if "success" in data else data.get("data", {}).get("token") is not None
            if not success:
                raise ValueError(f"获取Token失败: {data.get('message') or data.get('errorCode') or '未知错误'}")
            token = data.get("data", {}).get("token") or data.get("token")
            if not token:
                raise ValueError(f"获取Token失败: 响应中无token字段, raw={data}")
            return token

    def _api_headers(self) -> dict[str, str]:
        """获取带 token 的 API 请求头"""
        token = self._get_access_token()
        return {"token": token, "Content-Type": "application/json"}

    def fetch_vehicle_list(self) -> list[dict[str, Any]]:
        """通过开放 API 分页拉取所有车辆"""
        app_id = self.secret_config.get("app_id") or self.config.get("app_id")
        if not app_id:
            # 没有开放 API 凭据，回退到空列表（仅 MQTT 模式）
            return []

        headers = self._api_headers()
        all_vehicles = []
        page_number = 1
        page_size = 100

        with httpx.Client(timeout=30) as client:
            while True:
                resp = client.get(
                    f"{self.api_base_url}/vehicles",
                    params={"pageNumber": page_number, "pageSize": page_size},
                    headers=headers,
                )
                resp.raise_for_status()
                body = resp.json()
                data = body.get("data", {})
                vehicles = data.get("list", [])
                all_vehicles.extend(vehicles)

                total = data.get("total", 0)
                if len(all_vehicles) >= total or len(vehicles) == 0:
                    break
                page_number += 1

        return all_vehicles

    # ------------------------------------------------------------------
    # 连接测试（MQTT + 开放 API 双重检测）
    # ------------------------------------------------------------------

    def test_connection(self) -> dict[str, Any]:
        """测试连接：MQTT Broker TCP 可达 + 开放 API Token 获取"""
        org_code = self.config.get("organization_code")
        mqtt_host = self.config.get("mqtt_host")
        mqtt_port = int(self.config.get("mqtt_port", 1883))

        results = []

        # 1. MQTT Broker 可达性
        if mqtt_host:
            try:
                sock = socket.create_connection((mqtt_host, mqtt_port), timeout=5)
                sock.close()
                results.append(f"MQTT Broker {mqtt_host}:{mqtt_port} 端口可达")
            except Exception as e:
                results.append(f"MQTT Broker 不可达: {e}")

        # 2. 开放 API Token 获取
        app_id = self.secret_config.get("app_id") or self.config.get("app_id")
        if app_id:
            try:
                token = self._get_access_token()
                results.append(f"API Token 获取成功 (preview: {token[:6]}***)")
            except Exception as e:
                results.append(f"API Token 获取失败: {e}")

        if not results:
            return {"status": "failed", "message": "无可用配置"}

        all_ok = all("失败" not in r for r in results)
        return {
            "status": "ok" if all_ok else "failed",
            "message": "; ".join(results),
            "org_code": org_code,
        }

    # ------------------------------------------------------------------
    # MQTT 推送（模式 B）
    # ------------------------------------------------------------------

    def topics(self) -> list[str]:
        """返回九识 MQTT 推送数据的 topic 列表"""
        organization_code = self.config.get("organization_code")
        if not organization_code:
            return []
        return [
            f"{organization_code}/vehicle/+/realtime/push",
            f"{organization_code}/vehicle/+/business/push",
        ]

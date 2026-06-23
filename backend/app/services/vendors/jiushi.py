"""九识 MQTT 适配器 — 模式 B：企业提供 Broker，九识推送数据"""

import socket
from typing import Any

from app.models.entities import VendorAccount
from app.services.vendors.base import VendorAdapter


class JiushiAdapter(VendorAdapter):
    def __init__(self, account: VendorAccount) -> None:
        super().__init__(account)
        self.config = account.config or {}
        self.secret_config = account.secret_config or {}

    def test_connection(self) -> dict[str, Any]:
        """测试连接：检查配置完整性 + TCP 端口可达性"""
        required = ["mqtt_host", "organization_code"]
        missing = [key for key in required if not self.config.get(key)]
        if missing:
            return {"status": "failed", "message": f"缺少配置: {', '.join(missing)}"}

        host = self.config["mqtt_host"]
        port = int(self.config.get("mqtt_port", 1883))

        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            return {
                "status": "ok",
                "message": f"Broker {host}:{port} 端口可达, org={self.config['organization_code']}",
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"无法连接 Broker {host}:{port}: {e}。请确认 MQTT Broker 已启动。",
            }

    def fetch_vehicle_list(self) -> list[dict[str, Any]]:
        """九识通过 MQTT 推送，不支持主动拉取车辆列表"""
        return []

    def topics(self) -> list[str]:
        """返回九识推送数据的 topic 列表"""
        organization_code = self.config["organization_code"]
        return [
            f"{organization_code}/vehicle/+/realtime/push",
            f"{organization_code}/vehicle/+/business/push",
        ]

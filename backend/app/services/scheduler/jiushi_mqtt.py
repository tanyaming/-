"""
九识 MQTT 客户端：连接企业自有 MQTT Broker，订阅九识推送的实时数据和业务状态

架构说明:
  模式 B — 企业提供 MQTT Broker，九识将数据推送到企业 Broker
  企业 → 搭建 MQTT Broker (Mosquitto/EMQX)
  企业 → 将 host/port/username/password 提供给九识
  九识 → 提供 organizationCode，作为发布者向企业 Broker 推送数据
  中台 → 作为 MQTT 客户端连接自有 Broker，订阅九识推送的 topic
"""

import json
import logging
import ssl
import time
from threading import Thread
from typing import Any, Callable

import paho.mqtt.client as mqtt

from app.services.normalizers.jiushi import normalize_jiushi_realtime
from app.services.normalizers.models import StandardVehicleState

logger = logging.getLogger(__name__)

# 全局回调：收到归一化状态后调用
_on_state_callback: Callable[[str, dict[str, Any], StandardVehicleState], None] | None = None


def set_on_state_callback(cb: Callable[[str, dict[str, Any], StandardVehicleState], None]) -> None:
    """设置收到九识数据后的回调函数"""
    global _on_state_callback
    _on_state_callback = cb


class JiushiMQTTClient:
    """
    九识 MQTT 客户端

    连接企业自有 MQTT Broker，订阅九识车辆数据推送。
    配置参数说明：
    - mqtt_host/port:    企业搭建的 MQTT Broker 地址（提供给九识的同一份信息）
    - mqtt_username/pw:  MQTT 认证凭据
    - organization_code: 九识分配的企业编码，用于构造订阅 topic
    """

    def __init__(self, account_id: int, config: dict[str, Any]) -> None:
        self.account_id = account_id
        self.host = config.get("mqtt_host", "")
        self.port = int(config.get("mqtt_port", 1883))
        self.username = config.get("mqtt_username", "")
        self.password = config.get("mqtt_password", "")
        self.organization_code = config.get("organization_code", "")
        self._client: mqtt.Client | None = None
        self._thread: Thread | None = None
        self._running = False

    def start(self) -> None:
        """启动 MQTT 连接"""
        if self._running:
            return
        # 校验必要参数
        if not self.organization_code:
            logger.error(f"九识 MQTT 缺少 organization_code, account_id={self.account_id}")
            return
        if not self.host:
            logger.error(f"九识 MQTT 缺少 mqtt_host, 请先部署 MQTT Broker 并配置, account_id={self.account_id}")
            return

        self._running = True
        self._thread = Thread(
            target=self._connect_loop,
            daemon=True,
            name=f"jiushi-mqtt-{self.account_id}",
        )
        self._thread.start()
        logger.info(
            f"九识 MQTT 客户端启动 account_id={self.account_id} "
            f"broker={self.host}:{self.port} "
            f"org={self.organization_code}"
        )

    def stop(self) -> None:
        """停止 MQTT 连接"""
        self._running = False
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
        self._client = None
        logger.info(f"九识 MQTT 客户端停止 account_id={self.account_id}")

    def _connect_loop(self) -> None:
        """带重连的连接循环"""
        while self._running:
            try:
                self._connect_and_subscribe()
            except Exception as exc:
                logger.error(f"九识 MQTT 连接异常 account_id={self.account_id}: {exc}")
            if self._running:
                time.sleep(5)

    def _connect_and_subscribe(self) -> None:
        client = mqtt.Client(
            client_id=f"vehicle-hub-jiushi-{self.account_id}",
            protocol=mqtt.MQTTv311,
        )

        # 认证
        if self.username:
            client.username_pw_set(self.username, self.password)

        # TLS 可选（生产环境建议启用）
        use_tls = self.port in (8883, 443, 8443)
        if use_tls:
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)

        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect

        logger.info(f"九识 MQTT 连接企业 Broker: {self.host}:{self.port}")
        client.connect(self.host, self.port, keepalive=60)
        self._client = client

        while self._running:
            client.loop(timeout=1.0)

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: dict, rc: int) -> None:
        if rc == 0:
            logger.info(f"九识 MQTT Broker 连接成功 account_id={self.account_id}")
            # 订阅九识推送的 topic
            topics = [
                (f"{self.organization_code}/vehicle/+/realtime/push", 1),
                (f"{self.organization_code}/vehicle/+/business/push", 1),
            ]
            result, mid = client.subscribe(topics)
            logger.info(
                f"九识 MQTT 订阅完成 account_id={self.account_id} "
                f"result={result} topics={[t[0] for t in topics]}"
            )
        else:
            logger.error(
                f"九识 MQTT 连接 Broker 失败 account_id={self.account_id} rc={rc}. "
                f"请检查 host/port/username/password 是否正确, Broker 是否在运行"
            )

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            topic = msg.topic
            logger.info(f"九识 MQTT 收到推送 topic={topic}")

            state = normalize_jiushi_realtime(payload)

            if _on_state_callback:
                _on_state_callback("jiushi", payload, state)
        except json.JSONDecodeError as e:
            logger.error(f"九识 MQTT JSON 解析失败 topic={msg.topic}: {e}")
        except Exception as e:
            logger.error(f"九识 MQTT 消息处理异常 topic={msg.topic}: {e}")

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        if rc != 0:
            logger.warning(
                f"九识 MQTT 与 Broker 断开 account_id={self.account_id} rc={rc}, "
                f"将自动重连"
            )
        self._client = None

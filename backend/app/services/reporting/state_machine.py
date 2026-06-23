"""
TCP/TLS 上报状态机：握手 → 0x34 → 等待 0x35 → 周期上报
支持自动重连和指数退避
"""

import asyncio
import logging
import socket
import ssl
import struct
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.services.normalizers.models import StandardVehicleState
from app.services.protocols.chengdu_decoder import DecodedStaticAck, decode_static_ack
from app.services.protocols.chengdu_encoder import (
    MSG_STATIC_ACK,
    ChengduStaticParams,
    encode_fault_state,
    encode_runtime_state,
    encode_static_params,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 常量
# ------------------------------------------------------------------

HEADER_SIZE = 16
MAX_RECONNECT_DELAY = 60.0  # 最大重连间隔(秒)
INITIAL_RECONNECT_DELAY = 2.0  # 初始重连间隔(秒)
RECONNECT_BACKOFF = 2.0  # 退避倍数
STATIC_ACK_TIMEOUT = 10.0  # 等 0x35 确认超时(秒)
HEARTBEAT_INTERVAL = 240.0  # 心跳间隔(秒)，平台5分钟无消息会断开


# ------------------------------------------------------------------
# 数据类
# ------------------------------------------------------------------

class ConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    WAITING_ACK = "waiting_ack"  # 已发 0x34，等待 0x35
    ACTIVE = "active"  # 握手完成，正常上报
    ERROR = "error"


@dataclass
class ChengduConnectionConfig:
    host: str
    port: int
    vehicle_no: str
    cert_file: Path
    key_file: Path | None = None
    ca_file: Path | None = None
    timeout: float = 10.0


# ------------------------------------------------------------------
# 上报状态机
# ------------------------------------------------------------------

class ChengduReportingStateMachine:
    """成都市监管平台上报表态机"""

    def __init__(self, config: ChengduConnectionConfig) -> None:
        self.config = config
        self._state = ConnectionState.DISCONNECTED
        self._socket: ssl.SSLSocket | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._message_no: int = 0
        self._reconnect_attempts: int = 0
        self._last_send_at: float = 0.0
        self._last_error: str | None = None
        self._ack_status: int | None = None

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_active(self) -> bool:
        return self._state == ConnectionState.ACTIVE

    @property
    def message_no(self) -> int:
        return self._message_no

    @property
    def reconnect_attempts(self) -> int:
        return self._reconnect_attempts

    @property
    def ack_status(self) -> int | None:
        return self._ack_status

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def _next_message_no(self) -> int:
        """递增消息编号, 溢出后从 1 开始"""
        self._message_no = self._message_no + 1 if self._message_no < 9_223_372_036_854_775_806 else 1
        return self._message_no

    def _reconnect_delay(self) -> float:
        """指数退避重连间隔"""
        delay = INITIAL_RECONNECT_DELAY * (RECONNECT_BACKOFF ** min(self._reconnect_attempts, 10))
        return min(delay, MAX_RECONNECT_DELAY)

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """
        TLS 握手 + 发送 0x34 + 等待 0x35 确认
        Returns: True = 握手成功进入 ACTIVE
        """
        self._state = ConnectionState.CONNECTING
        self._last_error = None

        try:
            # Step 1: TCP + TLS 连接
            await self._do_handshake()
            logger.info(f"车辆 {self.config.vehicle_no} TLS 握手成功")

            # Step 2: 发送准静态参数(0x34)
            await self._send_static_params()
            logger.info(f"车辆 {self.config.vehicle_no} 已发送 0x34 准静态参数")

            # Step 3: 等待 0x35 确认
            self._state = ConnectionState.WAITING_ACK
            ack = await self._wait_for_ack()
            if ack is None:
                raise ConnectionError("等待 0x35 响应超时")
            self._ack_status = ack.status

            if ack.status == 0:
                self._state = ConnectionState.ACTIVE
                self._reconnect_attempts = 0
                self._last_send_at = time.time()
                logger.info(f"车辆 {self.config.vehicle_no} 上报状态机进入 ACTIVE, ack_status=0")
                return True
            else:
                self._last_error = f"0x35 返回非确认状态: {ack.status}"
                self._state = ConnectionState.ERROR
                logger.warning(f"车辆 {self.config.vehicle_no} 0x35 确认失败 status={ack.status}")
                await self._disconnect()
                return False

        except Exception as exc:
            self._last_error = str(exc)
            self._state = ConnectionState.ERROR
            logger.error(f"车辆 {self.config.vehicle_no} 连接失败: {exc}")
            await self._disconnect()
            return False

    async def reconnect(self) -> bool:
        """带退避的重连"""
        self._reconnect_attempts += 1
        delay = self._reconnect_delay()
        logger.info(f"车辆 {self.config.vehicle_no} 第 {self._reconnect_attempts} 次重连, 等待 {delay:.1f}s")
        await asyncio.sleep(delay)
        return await self.connect()

    async def disconnect(self) -> None:
        """主动断开"""
        self._state = ConnectionState.DISCONNECTED
        await self._disconnect()

    async def _disconnect(self) -> None:
        """内部断开资源"""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._writer = None
        self._reader = None
        self._socket = None

    async def _do_handshake(self) -> None:
        """异步 TCP + TLS 握手"""
        loop = asyncio.get_event_loop()

        # TCP connect
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw.setblocking(False)
        await loop.sock_connect(raw, (self.config.host, self.config.port))

        # TLS wrap
        context = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH,
            cafile=str(self.config.ca_file) if self.config.ca_file else None,
        )
        context.load_cert_chain(
            certfile=str(self.config.cert_file),
            keyfile=str(self.config.key_file) if self.config.key_file else None,
        )
        # 允许自签名证书(测试环境)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        ssl_sock = context.wrap_socket(raw, server_hostname=self.config.host, do_handshake_on_connect=False)

        # 异步握手
        await loop.sock_connect(ssl_sock, (self.config.host, self.config.port))
        await asyncio.to_thread(ssl_sock.do_handshake)
        # Wait for handshake to complete
        await loop.sock_connect(ssl_sock, (self.config.host, self.config.port))
        ssl_sock.setblocking(False)

        self._socket = ssl_sock

    async def _send_static_params(self) -> None:
        """发送 0x34 准静态参数"""
        payload = encode_static_params(
            ChengduStaticParams(vehicle_no=self.config.vehicle_no)
        )
        await self._raw_send(payload)

    # ------------------------------------------------------------------
    # 等待 0x35 确认
    # ------------------------------------------------------------------

    async def _wait_for_ack(self) -> DecodedStaticAck | None:
        """等待 0x35 确认响应, 超时返回 None"""
        loop = asyncio.get_event_loop()
        deadline = loop.time() + STATIC_ACK_TIMEOUT
        buffer = b""

        while loop.time() < deadline:
            try:
                chunk = await asyncio.to_thread(self._socket.recv, 4096)
                if not chunk:
                    return None
                buffer += chunk

                # 尝试解析
                if len(buffer) >= HEADER_SIZE:
                    mark, payload_len, msg_type, version, ts, reserved = struct.unpack(
                        ">BIBBQB", buffer[:HEADER_SIZE]
                    )
                    total_len = HEADER_SIZE + payload_len
                    if len(buffer) >= total_len:
                        ack = decode_static_ack(buffer[:total_len])
                        if ack:
                            return ack
                        # 不是 0x35, 继续读
                        buffer = buffer[total_len:]
                    # 数据不够, 继续读
            except (ssl.SSLWantReadError, BlockingIOError):
                remain = deadline - loop.time()
                if remain <= 0:
                    return None
                await asyncio.sleep(0.1)
            except Exception as exc:
                logger.error(f"车辆 {self.config.vehicle_no} 读取 0x35 异常: {exc}")
                return None

        return None

    # ------------------------------------------------------------------
    # 数据发送
    # ------------------------------------------------------------------

    async def send_runtime_state(self, state: StandardVehicleState) -> int:
        """发送运行状态消息 0x15"""
        self._next_message_no()
        payload = encode_runtime_state(self.config.vehicle_no, self._message_no, state)
        await self._raw_send(payload)
        self._last_send_at = time.time()
        return self._message_no

    async def send_fault_state(self, state: StandardVehicleState) -> int:
        """发送故障消息 0x5C"""
        self._next_message_no()
        payload = encode_fault_state(self.config.vehicle_no, self._message_no, state)
        await self._raw_send(payload)
        self._last_send_at = time.time()
        return self._message_no

    async def check_idle(self) -> bool:
        """检查是否需要发送心跳(距离上次发送超过 240 秒)"""
        if time.time() - self._last_send_at >= HEARTBEAT_INTERVAL:
            return True
        return False

    async def _raw_send(self, data: bytes) -> None:
        """底层发送, 检测断开"""
        if self._socket is None:
            raise ConnectionError("socket 未连接")

        loop = asyncio.get_event_loop()
        try:
            await asyncio.to_thread(self._socket.sendall, data)
        except (BrokenPipeError, ConnectionResetError, ssl.SSLError, OSError) as exc:
            self._last_error = str(exc)
            self._state = ConnectionState.ERROR
            await self._disconnect()
            raise ConnectionError(f"发送失败: {exc}") from exc

"""
TCP/TLS 上报状态机：握手 → 0x34 → 等待 0x35 → 周期上报
支持自动重连和指数退避
"""

import asyncio
import logging
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
MAX_RECONNECT_DELAY = 60.0
INITIAL_RECONNECT_DELAY = 2.0
RECONNECT_BACKOFF = 2.0
STATIC_ACK_TIMEOUT = 10.0
HEARTBEAT_INTERVAL = 240.0


# ------------------------------------------------------------------
# 数据类
# ------------------------------------------------------------------

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    WAITING_ACK = "waiting_ack"
    ACTIVE = "active"
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
        self._message_no = self._message_no + 1 if self._message_no < 9_223_372_036_854_775_806 else 1
        return self._message_no

    def _reconnect_delay(self) -> float:
        delay = INITIAL_RECONNECT_DELAY * (RECONNECT_BACKOFF ** min(self._reconnect_attempts, 10))
        return min(delay, MAX_RECONNECT_DELAY)

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        self._state = ConnectionState.CONNECTING
        self._last_error = None

        try:
            await self._do_handshake()
            logger.info(f"车辆 {self.config.vehicle_no} TLS 握手成功")

            static_payload = encode_static_params(
                ChengduStaticParams(vehicle_no=self.config.vehicle_no)
            )
            logger.info(f"车辆 {self.config.vehicle_no} 发送 0x34, len={len(static_payload)}B hex={static_payload.hex()}")
            await self._raw_send(static_payload)
            logger.info(f"车辆 {self.config.vehicle_no} 已发送 0x34")

            self._state = ConnectionState.WAITING_ACK
            ack = await self._wait_for_ack()
            if ack is None:
                raise ConnectionError("等待 0x35 响应超时")
            self._ack_status = ack.status

            if ack.status == 0:
                self._state = ConnectionState.ACTIVE
                self._reconnect_attempts = 0
                self._last_send_at = time.time()
                logger.info(f"车辆 {self.config.vehicle_no} ACTIVE, ack_status=0")
                return True
            else:
                self._last_error = f"0x35 非确认 status={ack.status}"
                self._state = ConnectionState.ERROR
                logger.warning(f"车辆 {self.config.vehicle_no} 0x35 失败 status={ack.status}")
                await self._disconnect()
                return False

        except Exception as exc:
            self._last_error = str(exc)
            self._state = ConnectionState.ERROR
            logger.error(f"车辆 {self.config.vehicle_no} 连接失败: {exc}")
            await self._disconnect()
            return False

    async def reconnect(self) -> bool:
        self._reconnect_attempts += 1
        delay = self._reconnect_delay()
        logger.info(f"车辆 {self.config.vehicle_no} 第 {self._reconnect_attempts} 次重连, 等待 {delay:.1f}s")
        await asyncio.sleep(delay)
        return await self.connect()

    async def disconnect(self) -> None:
        self._state = ConnectionState.DISCONNECTED
        await self._disconnect()

    async def _disconnect(self) -> None:
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
        context = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH,
            cafile=str(self.config.ca_file) if self.config.ca_file else None,
        )
        context.load_cert_chain(
            certfile=str(self.config.cert_file),
            keyfile=str(self.config.key_file) if self.config.key_file else None,
        )
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        reader, writer = await asyncio.open_connection(
            host=self.config.host,
            port=self.config.port,
            ssl=context,
            server_hostname=self.config.host,
        )
        self._reader = reader
        self._writer = writer
        transport = writer.transport
        sock = transport.get_extra_info('socket')
        self._socket = sock

    # ------------------------------------------------------------------
    # 等待 0x35 确认
    # ------------------------------------------------------------------

    async def _wait_for_ack(self) -> DecodedStaticAck | None:
        if self._reader is None:
            return None
        logger.info(f"车辆 {self.config.vehicle_no} 等待 0x35 (timeout={STATIC_ACK_TIMEOUT}s)...")
        try:
            header = await asyncio.wait_for(self._reader.readexactly(HEADER_SIZE), timeout=STATIC_ACK_TIMEOUT)
            logger.info(f"车辆 {self.config.vehicle_no} 收到头: {header.hex()}")
            mark, payload_len, msg_type, version, ts, reserved = struct.unpack(
                ">BIBBQB", header
            )
            logger.info(f"  解析: mark=0x{mark:02X} len={payload_len} type=0x{msg_type:02X} ver=0x{version:02X}")
            total_len = HEADER_SIZE + payload_len
            payload = await asyncio.wait_for(self._reader.readexactly(payload_len), timeout=5.0)
            full_msg = header + payload
            ack = decode_static_ack(full_msg)
            if ack:
                logger.info(f"  0x35 ack: status={ack.status} no={ack.vehicle_no}")
                return ack
            logger.warning(f"  非 0x35, type=0x{msg_type:02X}")
        except asyncio.TimeoutError:
            logger.warning(f"车辆 {self.config.vehicle_no} 0x35 超时")
        except Exception as exc:
            logger.error(f"车辆 {self.config.vehicle_no} 0x35 异常: {exc}")
        return None

    # ------------------------------------------------------------------
    # 数据发送
    # ------------------------------------------------------------------

    async def send_runtime_state(self, state: StandardVehicleState) -> int:
        self._next_message_no()
        payload = encode_runtime_state(self.config.vehicle_no, self._message_no, state)
        await self._raw_send(payload)
        self._last_send_at = time.time()
        return self._message_no

    async def send_fault_state(self, state: StandardVehicleState) -> int:
        self._next_message_no()
        payload = encode_fault_state(self.config.vehicle_no, self._message_no, state)
        await self._raw_send(payload)
        self._last_send_at = time.time()
        return self._message_no

    async def check_idle(self) -> bool:
        if time.time() - self._last_send_at >= HEARTBEAT_INTERVAL:
            return True
        return False

    async def _raw_send(self, data: bytes) -> None:
        if self._writer is None:
            raise ConnectionError("socket 未连接")
        try:
            self._writer.write(data)
            await self._writer.drain()
        except (BrokenPipeError, ConnectionResetError, ssl.SSLError, OSError) as exc:
            self._last_error = str(exc)
            self._state = ConnectionState.ERROR
            await self._disconnect()
            raise ConnectionError(f"发送失败: {exc}") from exc

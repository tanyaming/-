"""
成都市协议二进制报文解码
"""

import struct
from dataclasses import dataclass

HEADER_MARK = 0xF2
HEADER_SIZE = 16
MSG_STATIC_ACK = 0x35


@dataclass
class DecodedStaticAck:
    """解析后的 0x35 准静态参数响应"""
    vehicle_no: str
    status: int  # 0=成功
    raw: bytes


def decode_static_ack(data: bytes) -> DecodedStaticAck | None:
    """解析 0x35 准静态参数响应报文"""
    if len(data) < HEADER_SIZE:
        return None

    mark, payload_len, msg_type, version, timestamp_ms, reserved = struct.unpack(
        ">BIBBQB", data[:HEADER_SIZE]
    )
    if mark != HEADER_MARK or msg_type != MSG_STATIC_ACK:
        return None

    body = data[HEADER_SIZE:]
    if len(body) < 9:
        return None

    vehicle_no = body[:8].decode("utf-8", errors="replace").rstrip("\x00")
    status = body[8]
    return DecodedStaticAck(vehicle_no=vehicle_no, status=status, raw=data)

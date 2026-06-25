import struct
import time
from dataclasses import dataclass

from app.services.normalizers.coordinate import gcj02_to_wgs84
from app.services.normalizers.models import StandardVehicleState
from app.services.normalizers.units import clamp


HEADER_MARK = 0xF2
MSG_STATIC = 0x34
MSG_STATIC_ACK = 0x35
MSG_RUNTIME = 0x15
MSG_FAULT = 0x5C


GEAR_VALUE = {
    "drive": 31,
    "reverse": 32,
    "parking": 33,
    "neutral": 34,
}

DRIVE_MODE_VALUE = {
    "manual": 1,
    "auto": 2,
    "remote": 7,
    "remote_assist": 7,
    "takeover": 6,
    "unknown": 8,
}


@dataclass
class ChengduStaticParams:
    vehicle_no: str
    vehicle_software_version: str = "v1.0.0"
    ad_hardware_version: str = "H1.0"
    ad_software_version: str = "A1.0"
    wireless_type: int = 1
    location_accuracy: int = 255
    time_sync_type: int = 2
    coordinate_system: int = 1


def _now_ms() -> int:
    return int(time.time() * 1000)


def _header(message_type: int, version: int, payload: bytes, timestamp_ms: int | None = None) -> bytes:
    return struct.pack(
        ">BIBBQB",
        HEADER_MARK,
        len(payload),
        message_type,
        version,
        timestamp_ms or _now_ms(),
        0,
    )


def _fixed_string(value: str, length: int) -> bytes:
    data = value.encode("utf-8")
    if len(data) != length:
        raise ValueError(f"value {value!r} must be {length} bytes")
    return data


def _var_string(value: str) -> bytes:
    data = value.encode("utf-8")
    if len(data) > 254:
        raise ValueError("string field length must be <= 254")
    return struct.pack(">B", len(data)) + data


def encode_static_params(params: ChengduStaticParams) -> bytes:
    payload = b"".join(
        [
            _fixed_string(params.vehicle_no, 8),
            _var_string(params.vehicle_software_version),
            _var_string(params.ad_hardware_version),
            _var_string(params.ad_software_version),
            struct.pack(
                ">BBBB",
                params.wireless_type,
                params.location_accuracy,
                params.time_sync_type,
                params.coordinate_system,
            ),
        ]
    )
    return _header(MSG_STATIC, 0x01, payload) + payload


def _coord_for_chengdu(state: StandardVehicleState) -> tuple[float | None, float | None]:
    if state.coordinate_system.upper() in {"GCJ02", "GCJ-02"}:
        return gcj02_to_wgs84(state.longitude, state.latitude)
    return state.longitude, state.latitude


def _encoded_lon(lon: float | None) -> int:
    if lon is None:
        return 0xFFFFFFFFFFFFFFFF
    return clamp(round((lon + 180.0) * 10_000_000), 0, 3_600_000_000)


def _encoded_lat(lat: float | None) -> int:
    if lat is None:
        return 0xFFFFFFFF
    return clamp(round((lat + 90.0) * 10_000_000), 0, 1_800_000_000)


def _encoded_speed(speed_mps: float | None) -> int:
    if speed_mps is None:
        return 0xFFFF
    return clamp(round(speed_mps * 100), 0, 20_000)


def _encoded_heading(heading_deg: float | None) -> int:
    if heading_deg is None:
        return 0xFFFFFFFF
    return clamp(round((heading_deg % 360.0) * 10_000), 0, 3_600_000)


def _encoded_acceleration(value: float | None) -> int:
    if value is None:
        return 0xFFFF
    return clamp(round((value + 100.0) * 100), 0, 20_000)


def _encoded_percent(value: float | None, missing: int = 0xFFFF) -> int:
    if value is None:
        return missing
    return clamp(round(value * 10), 0, 1000)


def _light_bits(lights: dict) -> int:
    if not lights:
        return 0x8000
    bits = 0
    bits |= int(bool(lights.get("front_low"))) << 0
    bits |= int(bool(lights.get("front_high"))) << 1
    bits |= int(bool(lights.get("left"))) << 2
    bits |= int(bool(lights.get("right"))) << 3
    bits |= int(bool(lights.get("hazard"))) << 4
    bits |= int(bool(lights.get("reverse"))) << 11
    bits |= int(bool(lights.get("brake"))) << 12
    return bits


def encode_runtime_state(vehicle_no: str, message_no: int, state: StandardVehicleState) -> bytes:
    lon, lat = _coord_for_chengdu(state)
    source_ms = int(state.source_timestamp.timestamp() * 1000) if state.source_timestamp else _now_ms()
    wheel_count = min(len(state.tires), 12)
    wheel_speeds = [0xFFFF] * wheel_count
    tire_pressures = [clamp(int((item.get("pressure") or 0)), 0, 400) for item in state.tires[:wheel_count]]
    payload = b"".join(
        [
            _fixed_string(vehicle_no, 8),
            struct.pack(">Q", message_no),
            struct.pack(">Q", source_ms),
            struct.pack(">H", _encoded_speed(state.speed_mps)),
            struct.pack(">Q", _encoded_lon(lon)),
            struct.pack(">I", _encoded_lat(lat)),
            struct.pack(">I", 0xFFFFFFFF if state.altitude is None else clamp(round(state.altitude * 10 + 5000), 0, 70000)),
            struct.pack(">I", _encoded_heading(state.heading_deg)),
            struct.pack(">B", GEAR_VALUE.get(state.gear or "", 0xFF)),
            struct.pack(">I", 0xFFFFFFFF if state.steering_angle_deg is None else clamp(round((state.steering_angle_deg + 1000) * 10000), 0, 20_000_000)),
            struct.pack(">H", _encoded_speed(state.speed_mps)),
            struct.pack(">H", _encoded_acceleration(state.longitudinal_acceleration)),
            struct.pack(">H", _encoded_acceleration(state.lateral_acceleration)),
            struct.pack(">H", _encoded_acceleration(state.vertical_acceleration)),
            struct.pack(">H", 0xFFFF),
            struct.pack(">H", _encoded_percent(state.throttle_percent)),
            struct.pack(">H", 0xFFFF),
            struct.pack(">I", 0xFFFFFFFF),
            struct.pack(">B", 1 if state.brake_percent and state.brake_percent > 0 else 0),
            struct.pack(">H", _encoded_percent(state.brake_percent)),
            struct.pack(">H", 0xFFFF),
            struct.pack(">H", 0xFFFF),
            struct.pack(">B", DRIVE_MODE_VALUE.get(state.drive_mode or "", 8)),
            struct.pack(">BBBBBBBBB", 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF),
            struct.pack(">I", 0xFFFFFFFF if state.odometer_km is None else clamp(round(state.odometer_km * 10), 0, 10_000_000)),
            struct.pack(">H", 0xFFFF),
            struct.pack(">H", 0xFFFF if state.battery_soc is None else clamp(round(state.battery_soc * 100), 0, 10_000)),
            struct.pack(">B", 0xFF if state.battery_temperature is None else clamp(round(state.battery_temperature + 100), 0, 200)),
            struct.pack(">I", 0xFFFFFFFF if state.range_km is None else clamp(round(state.range_km), 0, 500_000)),
            struct.pack(">H", 0xFFFF),
            struct.pack(">I", 0xFFFFFFFF),
            struct.pack(">B", 0xFF),
            struct.pack(">B", 3 if state.charge_status == "charging" else 1),
            struct.pack(">H", 0xFFFF),
            struct.pack(">H", 0xFFFF),
            struct.pack(">B", 0xFF),
            struct.pack(">B", wheel_count),
            struct.pack(f">{wheel_count}H", *wheel_speeds) if wheel_count else b"",
            struct.pack(f">{wheel_count}H", *tire_pressures) if wheel_count else b"",
            struct.pack(">H", _light_bits(state.lights)),
            struct.pack(">H", 0xC000),
        ]
    )
    return _header(MSG_RUNTIME, 0x02, payload, source_ms) + payload


def encode_fault_state(vehicle_no: str, message_no: int, state: StandardVehicleState) -> bytes:
    lon, lat = _coord_for_chengdu(state)
    source_ms = int(state.source_timestamp.timestamp() * 1000) if state.source_timestamp else _now_ms()
    vehicle_fault_bits = 0
    hardware_fault_bits = 0
    software_fault_bits = 0
    if state.fault_level == "fault":
        vehicle_fault_bits |= 1 << 14
    payload = b"".join(
        [
            _fixed_string(vehicle_no, 8),
            struct.pack(">Q", message_no),
            struct.pack(">Q", source_ms),
            struct.pack(">Q", _encoded_lon(lon)),
            struct.pack(">I", _encoded_lat(lat)),
            struct.pack(">I", 0xFFFFFFFF if state.altitude is None else clamp(round(state.altitude * 10 + 5000), 0, 70000)),
            struct.pack(">III", vehicle_fault_bits, hardware_fault_bits, software_fault_bits),
        ]
    )
    return _header(MSG_FAULT, 0x01, payload, source_ms) + payload


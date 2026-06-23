from datetime import datetime, timezone
from typing import Any

from app.services.normalizers.models import StandardVehicleState
from app.services.normalizers.units import kmh_to_mps


GEAR_MAP = {"D": "drive", "R": "reverse", "P": "parking", "N": "neutral"}
DRIVE_MODE_MAP = {
    0: "unknown",
    1: "auto",
    2: "remote_assist",
    3: "nearby_remote",
}


def normalize_neolix_vehicle_info(payload: dict[str, Any]) -> StandardVehicleState:
    data = payload.get("data") or payload
    position = data.get("position") or {}
    ts = data.get("occurTimestamp")
    source_ts = datetime.fromtimestamp(ts / 1000, tz=timezone.utc) if ts else None
    fault_status = data.get("faultStatus")
    return StandardVehicleState(
        vendor_code="neolix",
        vendor_vehicle_id=data.get("vinId") or data.get("vin"),
        vin=data.get("vin"),
        vehicle_name=data.get("vinCode") or data.get("vinId"),
        source_timestamp=source_ts,
        longitude=position.get("lon"),
        latitude=position.get("lat"),
        coordinate_system="GCJ02",
        speed_mps=kmh_to_mps(data.get("speed")),
        heading_deg=data.get("gnssHead"),
        longitudinal_acceleration=data.get("acceleration_V"),
        lateral_acceleration=data.get("acceleration_H"),
        gear=GEAR_MAP.get(data.get("gear"), data.get("gear")),
        drive_mode=DRIVE_MODE_MAP.get(data.get("driveMode"), "unknown"),
        battery_soc=data.get("realBattery") or data.get("electricity"),
        range_km=data.get("mile"),
        charge_status="charging" if data.get("chargingStatus") == 1 else "discharging",
        vehicle_state="online" if data.get("powerState") else "offline",
        fault_level="fault" if fault_status == 1 else "normal",
        tires=[
            {"position": "front_left", "pressure": data.get("lfPressure")},
            {"position": "front_right", "pressure": data.get("rfPressure")},
            {"position": "rear_left", "pressure": data.get("lrPressure")},
            {"position": "rear_right", "pressure": data.get("rrPressure")},
        ],
        raw=data,
        quality={"source": "neolix_http"},
    )


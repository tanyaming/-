from datetime import datetime, timezone
from typing import Any

from app.services.normalizers.models import StandardVehicleState
from app.services.normalizers.units import rad_east_ccw_to_deg_north_cw, rad_to_deg


GEAR_MAP = {
    "GEAR_DRIVE": "drive",
    "GEAR_REVERSE": "reverse",
    "GEAR_PARKING": "parking",
    "GEAR_NEUTRAL": "neutral",
}

DRIVE_MODE_MAP = {
    "DRIVEMODE_ENGAGED_AUTO_CTRL": "auto",
    "DRIVEMODE_TAKEOVER_REMOTE_CTRL": "remote",
    "DRIVEMODE_TAKEOVER_REMOTE_SUPER_CTRL": "remote",
    "DRIVEMODE_TAKEOVER_CHASSIS_CTRL": "manual",
    "DRIVEMODE_TAKEOVER_EMERGENCY_STOP": "takeover",
    "DRIVEMODE_ENGAGED_CHASSIS_FAULT": "fault",
}


def normalize_jiushi_realtime(payload: dict[str, Any]) -> StandardVehicleState:
    ts = payload.get("timestamp")
    source_ts = datetime.fromtimestamp(ts / 1000, tz=timezone.utc) if ts else None
    vehicle_state = payload.get("vehicleState")
    return StandardVehicleState(
        vendor_code="jiushi",
        vendor_vehicle_id=payload.get("vehicleVin") or payload.get("vehicleName"),
        vin=payload.get("vehicleVin"),
        vehicle_name=payload.get("vehicleName"),
        source_timestamp=source_ts,
        longitude=payload.get("gcj02Lon"),
        latitude=payload.get("gcj02Lat"),
        coordinate_system="GCJ02",
        speed_mps=payload.get("speed"),
        heading_deg=rad_east_ccw_to_deg_north_cw(payload.get("heading")),
        steering_angle_deg=rad_to_deg(payload.get("frontWheelAngle")),
        throttle_percent=payload.get("throttle"),
        brake_percent=payload.get("brake"),
        gear=GEAR_MAP.get(payload.get("gear"), payload.get("gear")),
        drive_mode=DRIVE_MODE_MAP.get(payload.get("chassisState"), payload.get("chassisState")),
        battery_soc=payload.get("power"),
        battery_temperature=payload.get("temperature"),
        odometer_km=(payload.get("odometer") / 1000.0) if payload.get("odometer") is not None else None,
        charge_status=payload.get("chargeStatus"),
        vehicle_state=vehicle_state,
        business_status=payload.get("vehicleBusinessStatus"),
        fault_level="fault" if vehicle_state == "MALFUNCTION" else "normal",
        lights={
            "front_low": payload.get("frontLowLight"),
            "front_high": payload.get("frontHightLight"),
            "brake": payload.get("brakeLight"),
            "reverse": payload.get("backLight"),
            "left": payload.get("leftLight"),
            "right": payload.get("rightLight"),
            "hazard": payload.get("hazardLight"),
        },
        doors={"doorStatus": payload.get("doorStatus"), "doors": payload.get("doors")},
        tires=payload.get("wheelStatus") or [],
        raw=payload,
        quality={"source": "jiushi_mqtt"},
    )


from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import VehicleLatestState, VehicleNormalizedMessage, VehicleRawMessage
from app.services.normalizers.jiushi import normalize_jiushi_realtime
from app.services.normalizers.models import StandardVehicleState
from app.services.normalizers.neolix import normalize_neolix_vehicle_info


def normalize_by_vendor(vendor_code: str, payload: dict[str, Any]) -> StandardVehicleState:
    if vendor_code == "neolix":
        return normalize_neolix_vehicle_info(payload)
    if vendor_code == "jiushi":
        return normalize_jiushi_realtime(payload)
    raise ValueError(f"unsupported vendor code: {vendor_code}")


def persist_standard_state(
    db: Session,
    *,
    vehicle_id: int,
    vendor_id: int | None,
    vendor_code: str,
    payload: dict[str, Any],
    source_topic: str | None = None,
) -> VehicleLatestState:
    state = normalize_by_vendor(vendor_code, payload)
    raw = VehicleRawMessage(
        vendor_id=vendor_id,
        vehicle_id=vehicle_id,
        message_type=f"{vendor_code}_realtime",
        source_topic=source_topic,
        source_timestamp=state.source_timestamp,
        payload=payload,
    )
    db.add(raw)
    db.flush()
    normalized = VehicleNormalizedMessage(
        raw_message_id=raw.id,
        vehicle_id=vehicle_id,
        message_type="vehicle_state",
        payload=state.to_payload(),
        quality=state.quality,
    )
    db.add(normalized)

    latest = db.query(VehicleLatestState).filter(VehicleLatestState.vehicle_id == vehicle_id).one_or_none()
    if latest is None:
        latest = VehicleLatestState(vehicle_id=vehicle_id)
        db.add(latest)

    latest.source_vendor_id = vendor_id
    latest.source_timestamp = state.source_timestamp
    latest.received_at = datetime.now(timezone.utc)
    latest.longitude = state.longitude
    latest.latitude = state.latitude
    latest.altitude = state.altitude
    latest.coordinate_system = state.coordinate_system
    latest.speed_mps = state.speed_mps
    latest.heading_deg = state.heading_deg
    latest.battery_soc = state.battery_soc
    latest.drive_mode = state.drive_mode
    latest.gear = state.gear
    latest.fault_level = state.fault_level
    latest.quality = state.quality
    latest.payload = state.to_payload()
    db.commit()
    db.refresh(latest)
    return latest


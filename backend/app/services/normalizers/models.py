from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class StandardVehicleState:
    vendor_code: str
    vendor_vehicle_id: str | None = None
    vin: str | None = None
    vehicle_name: str | None = None
    source_timestamp: datetime | None = None
    longitude: float | None = None
    latitude: float | None = None
    altitude: float | None = None
    coordinate_system: str = "GCJ02"
    speed_mps: float | None = None
    heading_deg: float | None = None
    longitudinal_acceleration: float | None = None
    lateral_acceleration: float | None = None
    vertical_acceleration: float | None = None
    steering_angle_deg: float | None = None
    throttle_percent: float | None = None
    brake_percent: float | None = None
    gear: str | None = None
    drive_mode: str | None = None
    battery_soc: float | None = None
    battery_temperature: float | None = None
    odometer_km: float | None = None
    range_km: float | None = None
    charge_status: str | None = None
    vehicle_state: str | None = None
    business_status: str | None = None
    fault_level: str | None = None
    lights: dict[str, Any] = field(default_factory=dict)
    doors: dict[str, Any] = field(default_factory=dict)
    tires: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "vendor_code": self.vendor_code,
            "vendor_vehicle_id": self.vendor_vehicle_id,
            "vin": self.vin,
            "vehicle_name": self.vehicle_name,
            "source_timestamp": self.source_timestamp.isoformat() if self.source_timestamp else None,
            "location": {
                "longitude": self.longitude,
                "latitude": self.latitude,
                "altitude": self.altitude,
                "coordinate_system": self.coordinate_system,
            },
            "motion": {
                "speed_mps": self.speed_mps,
                "heading_deg": self.heading_deg,
                "longitudinal_acceleration": self.longitudinal_acceleration,
                "lateral_acceleration": self.lateral_acceleration,
                "vertical_acceleration": self.vertical_acceleration,
            },
            "control": {
                "steering_angle_deg": self.steering_angle_deg,
                "throttle_percent": self.throttle_percent,
                "brake_percent": self.brake_percent,
                "gear": self.gear,
                "drive_mode": self.drive_mode,
            },
            "energy": {
                "battery_soc": self.battery_soc,
                "battery_temperature": self.battery_temperature,
                "odometer_km": self.odometer_km,
                "range_km": self.range_km,
                "charge_status": self.charge_status,
            },
            "body": {"lights": self.lights, "doors": self.doors, "tires": self.tires},
            "status": {
                "vehicle_state": self.vehicle_state,
                "business_status": self.business_status,
                "fault_level": self.fault_level,
            },
            "quality": self.quality,
        }


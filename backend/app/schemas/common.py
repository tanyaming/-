from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class VendorAccountCreate(BaseModel):
    name: str
    vendor_type: str
    environment: str = "test"
    base_url: str | None = None
    config: dict[str, Any] = {}
    secret_config: dict[str, Any] = {}
    is_enabled: bool = True


class VendorAccountRead(ORMModel, VendorAccountCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class RegulatoryPlatformCreate(BaseModel):
    name: str
    city_code: str
    platform_type: str = "chengdu"
    host: str
    port: int
    coordinate_system: str = "WGS84"
    report_frequency_hz: int = 10
    fault_frequency_hz: int = 1
    config: dict[str, Any] = {}
    is_enabled: bool = True


class RegulatoryPlatformRead(ORMModel, RegulatoryPlatformCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class VehicleCreate(BaseModel):
    name: str
    vin: str | None = None
    plate_no: str | None = None
    model: str | None = None
    brand: str | None = None
    vehicle_category: str | None = None
    power_type: str | None = None
    project_code: str | None = None
    status: str = "active"


class VehicleRead(ORMModel, VehicleCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class VehicleVendorBindingRead(ORMModel):
    id: int
    vehicle_id: int
    vendor_id: int
    vendor_vehicle_id: str
    vendor_vehicle_name: str | None = None
    vendor_vin: str | None = None
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class VehicleRegulatoryBindingRead(ORMModel):
    id: int
    vehicle_id: int
    platform_id: int
    regulatory_vehicle_no: str
    certificate_id: int | None = None
    is_enabled: bool
    reporting_strategy: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class VehicleDetailRead(VehicleRead):
    vendor_bindings: list[VehicleVendorBindingRead] = []
    regulatory_bindings: list[VehicleRegulatoryBindingRead] = []


class VehicleVendorBindingCreate(BaseModel):
    vendor_id: int
    vendor_vehicle_id: str
    vendor_vehicle_name: str | None = None
    vendor_vin: str | None = None
    is_primary: bool = True


class VehicleRegulatoryBindingCreate(BaseModel):
    platform_id: int
    regulatory_vehicle_no: str
    certificate_id: int | None = None
    is_enabled: bool = True
    reporting_strategy: str = "strict"
    config: dict[str, Any] = {}


class VehicleStateRead(ORMModel):
    id: int
    vehicle_id: int
    source_vendor_id: int | None = None
    source_timestamp: datetime | None = None
    received_at: datetime
    longitude: float | None = None
    latitude: float | None = None
    altitude: float | None = None
    coordinate_system: str
    speed_mps: float | None = None
    heading_deg: float | None = None
    battery_soc: float | None = None
    drive_mode: str | None = None
    gear: str | None = None
    fault_level: str | None = None
    quality: dict[str, Any]
    payload: dict[str, Any]


class CertificateRead(ORMModel):
    id: int
    name: str
    vehicle_id: int | None = None
    certificate_path: str
    private_key_path: str | None = None
    ca_certificate_path: str | None = None
    expires_at: datetime | None = None
    fingerprint: str | None = None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class MappingRuleCreate(BaseModel):
    source_type: str
    target_type: str
    source_field: str
    target_field: str
    transform: str | None = None
    default_value: str | None = None
    is_required: bool = False
    is_enabled: bool = True


class EnumMappingRuleCreate(BaseModel):
    source_type: str
    target_type: str
    field_name: str
    source_value: str
    target_value: str
    description: str | None = None
    is_enabled: bool = True


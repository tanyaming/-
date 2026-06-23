from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class VendorType(StrEnum):
    NEOLIX = "neolix"
    JIUSHI = "jiushi"
    OTHER = "other"


class PlatformType(StrEnum):
    CHENGDU = "chengdu"
    OTHER = "other"


class VehicleStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ConnectionKind(StrEnum):
    VENDOR = "vendor"
    REGULATORY = "regulatory"
    VEHICLE_REPORTER = "vehicle_reporter"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(64))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="admin", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class VendorAccount(Base, TimestampMixin):
    __tablename__ = "vendor_accounts"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor_type: Mapped[VendorType] = mapped_column(
        Enum(VendorType, values_callable=lambda values: [item.value for item in values]), nullable=False
    )
    environment: Mapped[str] = mapped_column(String(32), default="test", nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(255))
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    secret_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    vehicle_bindings: Mapped[list["VehicleVendorBinding"]] = relationship(back_populates="vendor")


class RegulatoryPlatform(Base, TimestampMixin):
    __tablename__ = "regulatory_platforms"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    city_code: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_type: Mapped[PlatformType] = mapped_column(
        Enum(PlatformType, values_callable=lambda values: [item.value for item in values]), nullable=False
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    coordinate_system: Mapped[str] = mapped_column(String(16), default="WGS84", nullable=False)
    report_frequency_hz: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    fault_frequency_hz: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    vehicle_bindings: Mapped[list["VehicleRegulatoryBinding"]] = relationship(back_populates="platform")


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    vin: Mapped[str | None] = mapped_column(String(64), unique=True)
    plate_no: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(64))
    brand: Mapped[str | None] = mapped_column(String(64))
    vehicle_category: Mapped[str | None] = mapped_column(String(32))
    power_type: Mapped[str | None] = mapped_column(String(32))
    project_code: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[VehicleStatus] = mapped_column(
        Enum(VehicleStatus, values_callable=lambda values: [item.value for item in values]),
        default=VehicleStatus.ACTIVE,
        nullable=False,
    )

    vendor_bindings: Mapped[list["VehicleVendorBinding"]] = relationship(back_populates="vehicle")
    regulatory_bindings: Mapped[list["VehicleRegulatoryBinding"]] = relationship(back_populates="vehicle")
    latest_state: Mapped["VehicleLatestState | None"] = relationship(back_populates="vehicle")


class VehicleVendorBinding(Base, TimestampMixin):
    __tablename__ = "vehicle_vendor_bindings"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor_accounts.id"), nullable=False)
    vendor_vehicle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor_vehicle_name: Mapped[str | None] = mapped_column(String(128))
    vendor_vin: Mapped[str | None] = mapped_column(String(64))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    vehicle: Mapped[Vehicle] = relationship(back_populates="vendor_bindings")
    vendor: Mapped[VendorAccount] = relationship(back_populates="vehicle_bindings")


class VehicleCertificate(Base, TimestampMixin):
    __tablename__ = "vehicle_certificates"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"))
    certificate_path: Mapped[str] = mapped_column(String(512), nullable=False)
    private_key_path: Mapped[str | None] = mapped_column(String(512))
    ca_certificate_path: Mapped[str | None] = mapped_column(String(512))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fingerprint: Mapped[str | None] = mapped_column(String(128))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class VehicleRegulatoryBinding(Base, TimestampMixin):
    __tablename__ = "vehicle_regulatory_bindings"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    platform_id: Mapped[int] = mapped_column(ForeignKey("regulatory_platforms.id"), nullable=False)
    regulatory_vehicle_no: Mapped[str] = mapped_column(String(8), nullable=False)
    certificate_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_certificates.id"))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reporting_strategy: Mapped[str] = mapped_column(String(32), default="strict", nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    vehicle: Mapped[Vehicle] = relationship(back_populates="regulatory_bindings")
    platform: Mapped[RegulatoryPlatform] = relationship(back_populates="vehicle_bindings")


class VehicleLatestState(Base, TimestampMixin):
    __tablename__ = "vehicle_latest_states"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), unique=True, nullable=False)
    source_vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendor_accounts.id"))
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    longitude: Mapped[float | None] = mapped_column()
    latitude: Mapped[float | None] = mapped_column()
    altitude: Mapped[float | None] = mapped_column()
    coordinate_system: Mapped[str] = mapped_column(String(16), default="GCJ02", nullable=False)
    speed_mps: Mapped[float | None] = mapped_column()
    heading_deg: Mapped[float | None] = mapped_column()
    battery_soc: Mapped[float | None] = mapped_column()
    drive_mode: Mapped[str | None] = mapped_column(String(64))
    gear: Mapped[str | None] = mapped_column(String(32))
    fault_level: Mapped[str | None] = mapped_column(String(32))
    quality: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    vehicle: Mapped[Vehicle] = relationship(back_populates="latest_state")


class VehicleRawMessage(Base, TimestampMixin):
    __tablename__ = "vehicle_raw_messages"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendor_accounts.id"))
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"))
    message_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_topic: Mapped[str | None] = mapped_column(String(255))
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class VehicleNormalizedMessage(Base, TimestampMixin):
    __tablename__ = "vehicle_normalized_messages"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    raw_message_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_raw_messages.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    message_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    quality: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class RegulatoryReportLog(Base, TimestampMixin):
    __tablename__ = "regulatory_report_logs"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("regulatory_platforms.id"), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    binding_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_regulatory_bindings.id"))
    message_type: Mapped[str] = mapped_column(String(32), nullable=False)
    message_no: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    payload_hex: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConnectionStatus(Base, TimestampMixin):
    __tablename__ = "connection_status"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    kind: Mapped[ConnectionKind] = mapped_column(
        Enum(ConnectionKind, values_callable=lambda values: [item.value for item in values]), nullable=False
    )
    ref_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class FieldMappingRule(Base, TimestampMixin):
    __tablename__ = "field_mapping_rules"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_field: Mapped[str] = mapped_column(String(128), nullable=False)
    target_field: Mapped[str] = mapped_column(String(128), nullable=False)
    transform: Mapped[str | None] = mapped_column(String(128))
    default_value: Mapped[str | None] = mapped_column(String(255))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EnumMappingRule(Base, TimestampMixin):
    __tablename__ = "enum_mapping_rules"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_value: Mapped[str] = mapped_column(String(128), nullable=False)
    target_value: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AlertEvent(Base, TimestampMixin):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    ref_id: Mapped[int | None] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OperationLog(Base, TimestampMixin):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    actor: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

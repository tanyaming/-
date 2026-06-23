"""
告警检测器：在调度引擎各个节点检测异常并触发告警
"""

import logging
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.entities import (
    AlertEvent,
    ConnectionKind,
    VehicleCertificate,
    VehicleVendorBinding,
    VendorAccount,
    ConnectionStatus,
)
from app.services.alerts import AlertManager

logger = logging.getLogger(__name__)

# 告警阈值配置
CERT_EXPIRY_DAYS_WARN = 30  # 证书到期前 30 天告警
DATA_STALE_SECONDS = 15  # 源数据超过 15 秒未更新告警
RECONNECT_THRESHOLD = 10  # 重连超过 10 次告警


class AlertDetector:
    """告警检测器：在各异常点调用"""

    # ------------------------------------------------------------------
    # 连接异常
    # ------------------------------------------------------------------

    @staticmethod
    def on_vendor_connection_error(vendor_id: int, vendor_name: str, error: str) -> None:
        AlertManager.create(
            severity="critical",
            source=f"vendor:{vendor_id}",
            title=f"厂商连接异常: {vendor_name}",
            message=f"厂商 {vendor_name} (id={vendor_id}) 连接失败: {error}",
            ref_id=vendor_id,
        )

    @staticmethod
    def on_vendor_connection_recovered(vendor_id: int, vendor_name: str) -> None:
        AlertManager.resolve(
            source=f"vendor:{vendor_id}",
            title=f"厂商连接异常: {vendor_name}",
        )

    @staticmethod
    def on_reporting_error(
        vehicle_id: int, vehicle_name: str, error: str, attempts: int = 0
    ) -> None:
        severity = "warning" if attempts < RECONNECT_THRESHOLD else "critical"
        AlertManager.create(
            severity=severity,
            source=f"reporting:{vehicle_id}",
            title=f"监管上报异常: 车辆{vehicle_id}",
            message=(
                f"车辆 {vehicle_name} (id={vehicle_id}) 上报失败, "
                f"重连 {attempts} 次。错误: {error}"
            ),
            ref_id=vehicle_id,
        )

    @staticmethod
    def on_reporting_recovered(vehicle_id: int, vehicle_name: str) -> None:
        AlertManager.resolve(
            source=f"reporting:{vehicle_id}",
            title=f"监管上报异常: 车辆{vehicle_id}",
        )

    @staticmethod
    def on_handshake_failed(
        vehicle_id: int, vehicle_name: str, ack_status: int, error: str
    ) -> None:
        AlertManager.create(
            severity="critical",
            source=f"reporting:{vehicle_id}",
            title=f"监管握手失败: 车辆{vehicle_id}",
            message=(
                f"车辆 {vehicle_name} (id={vehicle_id}) TLS 握手失败, "
                f"0x35 确认状态={ack_status}, 错误: {error}"
            ),
            ref_id=vehicle_id,
        )

    # ------------------------------------------------------------------
    # 数据异常
    # ------------------------------------------------------------------

    @staticmethod
    def on_data_stale(
        vehicle_id: int,
        vehicle_name: str,
        vendor_name: str,
        seconds_since_last: float,
    ) -> None:
        AlertManager.create(
            severity="warning",
            source=f"data:{vehicle_id}",
            title=f"源数据超时: 车辆{vehicle_id}",
            message=(
                f"车辆 {vehicle_name} (id={vehicle_id}) 超过 {seconds_since_last:.0f} 秒未收到 "
                f"{vendor_name} 数据更新"
            ),
            ref_id=vehicle_id,
        )

    @staticmethod
    def on_data_recovered(vehicle_id: int) -> None:
        AlertManager.resolve(
            source=f"data:{vehicle_id}",
            title=f"源数据超时: 车辆{vehicle_id}",
        )

    @staticmethod
    def on_normalization_failed(
        vehicle_id: int, vendor_code: str, error: str
    ) -> None:
        AlertManager.create(
            severity="warning",
            source=f"data:{vehicle_id}",
            title=f"数据标准化失败: 车辆{vehicle_id}",
            message=f"车辆 {vehicle_id} 的 {vendor_code} 数据标准化失败: {error}",
            ref_id=vehicle_id,
        )

    # ------------------------------------------------------------------
    # 证书异常
    # ------------------------------------------------------------------

    @staticmethod
    def on_cert_missing(vehicle_id: int, cert_path: str) -> None:
        AlertManager.create(
            severity="critical",
            source=f"cert:{vehicle_id}",
            title=f"证书文件缺失: 车辆{vehicle_id}",
            message=f"车辆 {vehicle_id} 证书文件不存在: {cert_path}",
            ref_id=vehicle_id,
        )

    @staticmethod
    def on_cert_expiring(cert_id: int, vehicle_id: int, name: str, expiry: str) -> None:
        AlertManager.create(
            severity="warning",
            source=f"cert:{vehicle_id}",
            title=f"证书即将过期: {name}",
            message=f"证书 {name} (id={cert_id}) 即将在 {expiry} 过期",
            ref_id=vehicle_id,
        )

    # ------------------------------------------------------------------
    # 批量检测
    # ------------------------------------------------------------------

    @staticmethod
    def check_certs() -> list[AlertEvent]:
        """检测即将过期的证书"""
        db = SessionLocal()
        results = []
        try:
            now = datetime.now(timezone.utc)
            certs = db.query(VehicleCertificate).filter(
                VehicleCertificate.is_enabled == True,
                VehicleCertificate.expires_at.isnot(None),
            ).all()
            for cert in certs:
                if cert.expires_at is None:
                    continue
                days_left = (cert.expires_at - now).days
                if days_left <= CERT_EXPIRY_DAYS_WARN:
                    alert = AlertDetector.on_cert_expiring(
                        cert.id,
                        cert.vehicle_id or 0,
                        cert.name,
                        cert.expires_at.strftime("%Y-%m-%d"),
                    )
                    if alert:
                        results.append(alert)
            return results
        finally:
            db.close()

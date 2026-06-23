"""
调度引擎 v2：管理「拉取→标准化→编码→上报」完整链路
- 使用 ChengduReportingStateMachine 管理 TLS 握手/0x34/0x35/重连
- 使用 FrequencyAdapter 处理频率补齐
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.db.session import SessionLocal
from app.models.entities import (
    PlatformType,
    RegulatoryPlatform,
    RegulatoryReportLog,
    Vehicle,
    VehicleRegulatoryBinding,
    VendorAccount,
    VendorType,
    VehicleVendorBinding,
    ConnectionStatus,
    ConnectionKind,
)
from app.services.normalizers.frequency_adapter import FillStrategy, FrequencyAdapter
from app.services.normalizers.models import StandardVehicleState
from app.services.reporting.state_machine import (
    ChengduConnectionConfig,
    ChengduReportingStateMachine,
    ConnectionState,
)
from app.services.alerts.detector import AlertDetector
from app.services.state_store import normalize_by_vendor, persist_standard_state
from app.services.scheduler.jiushi_mqtt import JiushiMQTTClient, set_on_state_callback
from app.services.vendors.neolix import NeolixAdapter

logger = logging.getLogger(__name__)

# 频率适配器 {vehicle_id: FrequencyAdapter}
_frequency_adapters: dict[int, FrequencyAdapter] = {}

# 上报状态机 {vehicle_id: ChengduReportingStateMachine}
_state_machines: dict[int, ChengduReportingStateMachine] = {}

# 九识 MQTT 客户端 {account_id: JiushiMQTTClient}
_jiushi_clients: dict[int, JiushiMQTTClient] = {}


class SchedulerEngine:
    """调度引擎：管理厂商数据拉取和监管上报"""

    def __init__(self) -> None:
        self._running = False
        self._tasks: list[asyncio.Task] = []

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """启动调度引擎"""
        if self._running:
            return
        self._running = True
        logger.info("调度引擎 v2 启动")

        # 注册九识 MQTT 回调
        set_on_state_callback(self._on_jiushi_state)

        db = SessionLocal()
        try:
            # 上报任务
            chengdu_platforms = db.query(RegulatoryPlatform).filter(
                RegulatoryPlatform.platform_type == PlatformType.CHENGDU,
                RegulatoryPlatform.is_enabled == True,
            ).all()
            for platform in chengdu_platforms:
                bindings = (
                    db.query(VehicleRegulatoryBinding)
                    .filter(
                        VehicleRegulatoryBinding.platform_id == platform.id,
                        VehicleRegulatoryBinding.is_enabled == True,
                    )
                    .all()
                )
                for binding in bindings:
                    self._tasks.append(
                        asyncio.create_task(
                            self._reporting_loop(platform, binding),
                            name=f"report-{binding.vehicle_id}",
                        )
                    )
            # 新石器拉取任务
            neolix_accounts = db.query(VendorAccount).filter(
                VendorAccount.vendor_type == VendorType.NEOLIX,
                VendorAccount.is_enabled == True,
            ).all()
            for account in neolix_accounts:
                self._tasks.append(
                    asyncio.create_task(
                        self._neolix_poll_loop(account),
                        name=f"poll-neolix-{account.id}",
                    )
                )
            # 九识 MQTT 订阅
            jiushi_accounts = db.query(VendorAccount).filter(
                VendorAccount.vendor_type == VendorType.JIUSHI,
                VendorAccount.is_enabled == True,
            ).all()
            for account in jiushi_accounts:
                self._start_jiushi_client(account)
        finally:
            db.close()

        # 启动周期性检测任务
        self._tasks.append(
            asyncio.create_task(self._periodic_health_check(), name="health-check")
        )

        logger.info(
            f"调度引擎已启动: {len(self._tasks)} 个任务, "
            f"{len(_jiushi_clients)} 个 MQTT 客户端"
        )

    async def stop(self) -> None:
        """停止调度引擎"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

        # 断开所有上报连接
        for sm in _state_machines.values():
            await sm.disconnect()
        _state_machines.clear()
        _frequency_adapters.clear()

        # 停止九识 MQTT 客户端
        for jc in _jiushi_clients.values():
            jc.stop()
        _jiushi_clients.clear()

        logger.info("调度引擎已停止")

    # ------------------------------------------------------------------
    # 新石器 HTTP 定时拉取
    # ------------------------------------------------------------------

    async def _neolix_poll_loop(self, account: VendorAccount) -> None:
        adapter = NeolixAdapter(account)
        interval = account.config.get("poll_interval_seconds", 0.2)
        consecutive_errors = 0
        while self._running:
            try:
                ok = await self._poll_neolix(adapter, account)
                if ok:
                    if consecutive_errors > 0:
                        AlertDetector.on_vendor_connection_recovered(account.id, account.name)
                    consecutive_errors = 0
            except asyncio.CancelledError:
                break
            except Exception as exc:
                consecutive_errors += 1
                logger.error(f"新石器拉取异常 account={account.id}: {exc}")
                self._update_connection_status(ConnectionKind.VENDOR, account.id, "error", str(exc))
                if consecutive_errors >= 3:
                    AlertDetector.on_vendor_connection_error(account.id, account.name, str(exc))
            await asyncio.sleep(interval)

    async def _poll_neolix(self, adapter: NeolixAdapter, account: VendorAccount) -> bool:
        db = SessionLocal()
        try:
            bindings = (
                db.query(VehicleVendorBinding)
                .filter(VehicleVendorBinding.vendor_id == account.id)
                .all()
            )
            if not bindings:
                return False

            vins = [b.vendor_vehicle_id for b in bindings]
            vehicle_map = {b.vendor_vehicle_id: b.vehicle_id for b in bindings}

            raw_list = adapter.batch_get_realtime(vins)
            if raw_list:
                self._update_connection_status(ConnectionKind.VENDOR, account.id, "ok")

            for item in raw_list:
                vin = item.get("vinId") or item.get("vin")
                vehicle_id = vehicle_map.get(vin)
                if not vehicle_id:
                    continue
                try:
                    persist_standard_state(
                        db,
                        vehicle_id=vehicle_id,
                        vendor_id=account.id,
                        vendor_code="neolix",
                        payload=item,
                    )
                    # 喂入频率适配器
                    state = normalize_by_vendor("neolix", item)
                    self._get_frequency_adapter(vehicle_id, bindings, db).feed(state)
                except Exception as e:
                    logger.error(f"新石器标准化失败 vehicle_id={vehicle_id}: {e}")
                    AlertDetector.on_normalization_failed(vehicle_id, "neolix", str(e))

            db.commit()
            return len(raw_list) > 0
        finally:
            db.close()

    # ------------------------------------------------------------------
    # 九识 MQTT 管理
    # ------------------------------------------------------------------

    def _start_jiushi_client(self, account: VendorAccount) -> None:
        config = {**account.config, **account.secret_config}
        client = JiushiMQTTClient(account.id, config)
        client.start()
        _jiushi_clients[account.id] = client
        logger.info(f"九识 MQTT 客户端已启动 account_id={account.id}")

    def _on_jiushi_state(
        self, vendor_code: str, raw_payload: dict[str, Any], state: StandardVehicleState
    ) -> None:
        """九识 MQTT 消息回调"""
        db = SessionLocal()
        try:
            vin = state.vin or state.vendor_vehicle_id
            binding = (
                db.query(VehicleVendorBinding)
                .filter(VehicleVendorBinding.vendor_vin == vin)
                .first()
            )
            if not binding:
                logger.warning(f"九识消息未匹配车辆 vin={vin}")
                return

            persist_standard_state(
                db,
                vehicle_id=binding.vehicle_id,
                vendor_id=binding.vendor_id,
                vendor_code=vendor_code,
                payload=raw_payload,
            )
            # 喂入频率适配器
            self._get_frequency_adapter(binding.vehicle_id, [binding], db).feed(state)
        except Exception as e:
            logger.error(f"九识状态持久化失败: {e}")
            db.rollback()
        finally:
            db.close()

    # ------------------------------------------------------------------
    # 监管上报循环 v2（使用状态机 + 频率适配器）
    # ------------------------------------------------------------------

    async def _reporting_loop(
        self, platform: RegulatoryPlatform, binding: VehicleRegulatoryBinding
    ) -> None:
        vehicle_id = binding.vehicle_id

        db = SessionLocal()
        try:
            vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if not vehicle:
                logger.error(f"上报任务: 车辆 {vehicle_id} 不存在")
                return
            # 确保频率适配器已初始化
            self._get_frequency_adapter(vehicle_id, [binding], db)
        finally:
            db.close()

        target_interval = 1.0 / max(platform.report_frequency_hz, 1)
        fault_frequency = platform.fault_frequency_hz
        last_fault_sent_at = 0.0

        while self._running:
            loop_start = asyncio.get_event_loop().time()

            try:
                # Step 1: 确保连接
                sm = await self._ensure_state_machine(platform, binding)
                if sm is None or not sm.is_active:
                    await asyncio.sleep(1)
                    continue

                # Step 2: 从频率适配器获取下一个状态
                fa = _frequency_adapters.get(vehicle_id)
                if fa is None:
                    await asyncio.sleep(target_interval)
                    continue

                # 数据超时检测
                if fa.is_stale:
                    db = SessionLocal()
                    try:
                        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
                        if v:
                            AlertDetector.on_data_stale(
                                vehicle_id, v.name, "未知厂商", 15
                            )
                    finally:
                        db.close()
                    await asyncio.sleep(target_interval)
                    continue

                state = fa.get_state()
                if state is None:
                    # 严格模式且数据已消耗
                    await asyncio.sleep(0.01)
                    continue

                # Step 3: 发送运行状态
                msg_no = await sm.send_runtime_state(state)
                self._log_report(binding, platform.id, vehicle_id, "runtime", msg_no, "ok", sm.state.value)

                # Step 4: 发送故障消息
                now = asyncio.get_event_loop().time()
                fault_interval = 1.0 / max(fault_frequency, 1)
                if state.fault_level == "fault":
                    if now - last_fault_sent_at >= fault_interval:
                        fault_msg_no = await sm.send_fault_state(state)
                        self._log_report(binding, platform.id, vehicle_id, "fault", fault_msg_no, "ok", sm.state.value)
                        last_fault_sent_at = now
                elif now - last_fault_sent_at >= 60:
                    fault_msg_no = await sm.send_fault_state(state)
                    self._log_report(binding, platform.id, vehicle_id, "fault", fault_msg_no, "ok", sm.state.value)
                    last_fault_sent_at = now

                self._update_connection_status(ConnectionKind.REGULATORY, vehicle_id, sm.state.value)

            except asyncio.CancelledError:
                break
            except ConnectionError as exc:
                logger.warning(f"车辆 {vehicle_id} 连接异常: {exc}")
                self._update_connection_status(ConnectionKind.REGULATORY, vehicle_id, "error", str(exc))
                db = SessionLocal()
                try:
                    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
                    if v:
                        sm = _state_machines.get(vehicle_id)
                        attempts = sm.reconnect_attempts if sm else 0
                        AlertDetector.on_reporting_error(vehicle_id, v.name, str(exc), attempts)
                finally:
                    db.close()
                await asyncio.sleep(2)
                continue
            except Exception as exc:
                logger.error(f"车辆 {vehicle_id} 上报异常: {exc}")
                self._update_connection_status(ConnectionKind.REGULATORY, vehicle_id, "error", str(exc))
                await asyncio.sleep(5)
                continue

            # 精确定时
            elapsed = asyncio.get_event_loop().time() - loop_start
            await asyncio.sleep(max(0, target_interval - elapsed))

    async def _ensure_state_machine(
        self,
        platform: RegulatoryPlatform,
        binding: VehicleRegulatoryBinding,
    ) -> ChengduReportingStateMachine | None:
        """确保连接状态机处于 ACTIVE 状态"""
        vehicle_id = binding.vehicle_id

        sm = _state_machines.get(vehicle_id)
        if sm is None:
            sm = await self._create_state_machine(platform, binding)
            if sm is None:
                return None
            _state_machines[vehicle_id] = sm

        if sm.is_active:
            return sm

        if sm.state in (ConnectionState.DISCONNECTED, ConnectionState.ERROR):
            # 需要重连
            ok = await sm.reconnect()
            if ok:
                self._update_connection_status(ConnectionKind.REGULATORY, vehicle_id, "ok")
            else:
                self._update_connection_status(
                    ConnectionKind.REGULATORY, vehicle_id, "error",
                    f"重连失败: {sm.last_error}, 已尝试 {sm.reconnect_attempts} 次",
                )
            return sm

        return sm

    async def _create_state_machine(
        self,
        platform: RegulatoryPlatform,
        binding: VehicleRegulatoryBinding,
    ) -> ChengduReportingStateMachine | None:
        """创建新的状态机并完成 TLS 握手"""
        vehicle_id = binding.vehicle_id
        cert_path = Path("./storage/certificates")
        cert_file = cert_path / f"{binding.regulatory_vehicle_no}.pem"
        key_file = cert_path / f"{binding.regulatory_vehicle_no}.key"
        ca_file = cert_path / "ca.pem"

        # 证书缺失检测
        if not cert_file.exists():
            AlertDetector.on_cert_missing(vehicle_id, str(cert_file))
            return None

        config = ChengduConnectionConfig(
            host=platform.host,
            port=platform.port,
            vehicle_no=binding.regulatory_vehicle_no,
            cert_file=cert_file,
            key_file=key_file if key_file.exists() else None,
            ca_file=ca_file if ca_file.exists() else None,
            timeout=10.0,
        )

        sm = ChengduReportingStateMachine(config)
        ok = await sm.connect()
        if ok:
            logger.info(f"车辆 {vehicle_id} 上报状态机 ACTIVE")
            self._update_connection_status(ConnectionKind.REGULATORY, vehicle_id, "ok")
            AlertDetector.on_reporting_recovered(vehicle_id, f"车辆{vehicle_id}")
        else:
            logger.warning(f"车辆 {vehicle_id} 上报状态机握手失败: {sm.last_error}")
            self._update_connection_status(ConnectionKind.REGULATORY, vehicle_id, "error", sm.last_error)
            AlertDetector.on_handshake_failed(
                vehicle_id, f"车辆{vehicle_id}",
                sm.ack_status or -1,
                sm.last_error or "未知错误",
            )
        return sm

    # ------------------------------------------------------------------
    # 周期性健康检测
    # ------------------------------------------------------------------

    async def _periodic_health_check(self) -> None:
        """每 60 秒检查一次证书过期、连接状态等"""
        while self._running:
            try:
                # 检查证书过期
                AlertDetector.check_certs()

                # 检查状态机重连次数
                for vehicle_id, sm in _state_machines.items():
                    if sm.reconnect_attempts >= 10:
                        db = SessionLocal()
                        try:
                            v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
                            if v:
                                AlertDetector.on_reporting_error(
                                    vehicle_id, v.name,
                                    f"持续重连失败, 已尝试 {sm.reconnect_attempts} 次",
                                    sm.reconnect_attempts,
                                )
                        finally:
                            db.close()

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"健康检测异常: {exc}")

            await asyncio.sleep(60)

    # ------------------------------------------------------------------
    # 频率适配器
    # ------------------------------------------------------------------

    def _get_frequency_adapter(
        self,
        vehicle_id: int,
        bindings: list,
        db,
    ) -> FrequencyAdapter:
        """获取或创建频率适配器"""
        if vehicle_id not in _frequency_adapters:
            # 根据车辆绑定的监管平台配置确定策略
            # 简化：默认 repeat 策略，新石器 5Hz 源, 九识 1Hz 源
            strategy = FillStrategy.REPEAT
            source_hz = 5.0  # 默认

            # 查找监管绑定以获取平台频率
            reg_bindings = (
                db.query(VehicleRegulatoryBinding)
                .filter(
                    VehicleRegulatoryBinding.vehicle_id == vehicle_id,
                    VehicleRegulatoryBinding.is_enabled == True,
                )
                .all()
            )

            target_hz = 10.0
            if reg_bindings:
                # 取第一个监管平台的目标频率
                for rb in reg_bindings:
                    platform = db.query(RegulatoryPlatform).filter(
                        RegulatoryPlatform.id == rb.platform_id
                    ).first()
                    if platform:
                        target_hz = float(platform.report_frequency_hz)
                        # 从 binding config 读取策略
                        strat_str = rb.reporting_strategy or "repeat"
                        strategy = FillStrategy(strat_str)
                        break

            # 从厂商绑定推测源频率
            vendor_bindings = (
                db.query(VehicleVendorBinding)
                .filter(VehicleVendorBinding.vehicle_id == vehicle_id)
                .all()
            )
            for vb in vendor_bindings:
                vendor = db.query(VendorAccount).filter(VendorAccount.id == vb.vendor_id).first()
                if vendor and vendor.vendor_type == VendorType.JIUSHI:
                    source_hz = 1.0
                    break

            _frequency_adapters[vehicle_id] = FrequencyAdapter(
                target_hz=target_hz,
                source_hz=source_hz,
                strategy=strategy,
            )
            logger.info(
                f"频率适配器已创建 vehicle_id={vehicle_id} "
                f"target={target_hz}Hz source={source_hz}Hz strategy={strategy.value}"
            )

        return _frequency_adapters[vehicle_id]

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _update_connection_status(
        self, kind: ConnectionKind, ref_id: int, status: str, error: str | None = None
    ) -> None:
        db = SessionLocal()
        try:
            conn = (
                db.query(ConnectionStatus)
                .filter(ConnectionStatus.kind == kind, ConnectionStatus.ref_id == ref_id)
                .one_or_none()
            )
            if conn is None:
                conn = ConnectionStatus(kind=kind, ref_id=ref_id, status=status, metrics={})
                db.add(conn)
            conn.status = status
            conn.last_seen_at = datetime.now(timezone.utc)
            conn.last_error = error
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def _log_report(
        self,
        binding: VehicleRegulatoryBinding,
        platform_id: int,
        vehicle_id: int,
        message_type: str,
        message_no: int,
        status: str,
        detail: str = "",
    ) -> None:
        """记录上报日志（采样写入以降低 DB 压力）"""
        # 运行状态高频（10Hz），采样写入：每 100 条写一次
        if message_type == "runtime" and message_no % 100 != 0:
            return

        db = SessionLocal()
        try:
            log = RegulatoryReportLog(
                platform_id=platform_id,
                vehicle_id=vehicle_id,
                binding_id=binding.id,
                message_type=message_type,
                message_no=message_no,
                status=status,
                error_message=detail if detail else None,
                sent_at=datetime.now(timezone.utc),
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


# 全局引擎实例
_scheduler: SchedulerEngine | None = None


def get_scheduler() -> SchedulerEngine:
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerEngine()
    return _scheduler

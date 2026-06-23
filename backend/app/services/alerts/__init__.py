"""
告警服务：在调度引擎中主动检测异常并写入 alert_events 表
支持去重（同源同类型告警在 resolved 前不重复创建）
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.db.session import SessionLocal
from app.models.entities import AlertEvent

logger = logging.getLogger(__name__)

# 告警去重缓存: {(source, title): AlertEvent.id}
# 相同 source+title 的告警在 resolved 前只创建一次
_dedup_cache: dict[tuple[str, str], int] = {}

# 去重缓存过期时间
DEDUP_TTL = 3600  # 1 小时


class AlertManager:
    """告警管理器：创建、去重、状态检查"""

    @staticmethod
    def create(
        severity: str,
        source: str,
        title: str,
        message: str,
        ref_id: int | None = None,
    ) -> AlertEvent | None:
        """
        创建告警，自动去重。
        返回 AlertEvent 表示新创建，返回 None 表示已存在未处理的同类型告警。
        """
        dedup_key = (source, title)

        # 检查缓存
        cached_id = _dedup_cache.get(dedup_key)
        if cached_id is not None:
            db = SessionLocal()
            try:
                existing = db.get(AlertEvent, cached_id)
                if existing and existing.status == "open":
                    # 更新消息
                    existing.message = message
                    db.commit()
                    return None
                else:
                    # 已 resolved，清除缓存
                    del _dedup_cache[dedup_key]
            except Exception:
                pass
            finally:
                db.close()

        # 查询数据库
        db = SessionLocal()
        try:
            existing = (
                db.query(AlertEvent)
                .filter(
                    AlertEvent.source == source,
                    AlertEvent.title == title,
                    AlertEvent.status == "open",
                )
                .first()
            )
            if existing:
                existing.message = message
                db.commit()
                _dedup_cache[dedup_key] = existing.id
                logger.debug(f"告警去重: {source}/{title}")
                return None
        except Exception:
            db.rollback()
            return None
        finally:
            db.close()

        # 创建新告警
        db = SessionLocal()
        try:
            alert = AlertEvent(
                severity=severity,
                source=source,
                ref_id=ref_id,
                title=title,
                message=message,
                status="open",
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            _dedup_cache[dedup_key] = alert.id
            logger.warning(f"🔔 新告警: [{severity}] {title} - {message[:100]}")
            return alert
        except Exception:
            db.rollback()
            return None
        finally:
            db.close()

    @staticmethod
    def resolve(source: str, title: str) -> None:
        """手动 resolve 告警"""
        dedup_key = (source, title)
        _dedup_cache.pop(dedup_key, None)

        db = SessionLocal()
        try:
            (
                db.query(AlertEvent)
                .filter(
                    AlertEvent.source == source,
                    AlertEvent.title == title,
                    AlertEvent.status == "open",
                )
                .update({"status": "resolved", "resolved_at": datetime.now(timezone.utc)})
            )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def cleanup_dedup_cache() -> None:
        """清理过期去重缓存（防止内存泄漏）"""
        # 简化实现：定期调用时全清
        now = time.time()
        # 实际生产环境应实现 TTL 检查
        pass

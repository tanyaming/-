import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.monotonic()
        response = await call_next(request)
        elapsed = (time.monotonic() - t0) * 1000
        logger.warning("⏱ %s %s → %d %.0fms", request.method, request.url.path, response.status_code, elapsed)
        return response

from app.api.routes import alerts, auth, certificates, health, mappings, platforms, reports, scheduler_ctrl, states, vendors, vehicles
from app.core.auth_middleware import AuthMiddleware
from app.core.config import get_settings
from app.db.init_db import init_db
from app.services.scheduler.engine import get_scheduler


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    if settings.app_env == "local":
        init_db()

    # 启动调度引擎
    if settings.reporting_enabled:
        scheduler = get_scheduler()
        await scheduler.start()
    yield
    # 关闭时停止调度引擎
    scheduler = get_scheduler()
    await scheduler.stop()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段全开
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Timing 中间件（调试用，问题定位后移除）
app.add_middleware(TimingMiddleware)

# 认证中间件
app.add_middleware(AuthMiddleware)

# Auth routes (must be before other routes)
app.include_router(auth.router, prefix="/api", tags=["auth"])

# 其他路由
app.include_router(health.router, prefix="/api")
app.include_router(vendors.router, prefix="/api/vendors", tags=["vendors"])
app.include_router(platforms.router, prefix="/api/regulatory-platforms", tags=["regulatory-platforms"])
app.include_router(vehicles.router, prefix="/api/vehicles", tags=["vehicles"])
app.include_router(certificates.router, prefix="/api/certificates", tags=["certificates"])
app.include_router(states.router, prefix="/api/states", tags=["states"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(mappings.router, prefix="/api/mappings", tags=["mappings"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(scheduler_ctrl.router, prefix="/api", tags=["scheduler"])

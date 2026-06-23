"""
认证中间件：对所有 /api/* 请求进行 token 校验（跳过 /api/auth/* 和 /api/health）
"""

import re

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.auth import verify_token

SKIP_PATHS = {"/api/auth/login", "/api/auth/logout", "/api/health", "/api/scheduler/status", "/docs", "/openapi.json", "/redoc"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")

        # 跳过不需要鉴权的路径
        if path in SKIP_PATHS or path.startswith("/api/auth/"):
            return await call_next(request)

        # 检查 token
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Missing authorization token"})

        username = verify_token(token)
        if username is None:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        request.state.username = username
        return await call_next(request)

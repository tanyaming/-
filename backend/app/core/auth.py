"""
认证模块：JWT token 签发与验证
首期简化版：单用户 admin 模式，通过环境变量密码认证
"""

import hashlib
import hmac
import time
from typing import Any

from app.core.config import get_settings


def _sign(payload: str) -> str:
    """HMAC-SHA256 签名"""
    settings = get_settings()
    key = settings.secret_key.encode("utf-8")
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_token(username: str) -> str:
    """创建简易 token: username:timestamp:signature"""
    timestamp = str(int(time.time()))
    payload = f"{username}:{timestamp}"
    sig = _sign(payload)
    return f"{payload}:{sig}"


def verify_token(token: str) -> str | None:
    """验证 token，返回 username 或 None"""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        username, timestamp, sig = parts

        # 检查过期（24小时）
        created = int(timestamp)
        if time.time() - created > 86400:
            return None

        # 验证签名
        expected = _sign(f"{username}:{timestamp}")
        if not hmac.compare_digest(sig, expected):
            return None

        return username
    except Exception:
        return None

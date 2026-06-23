"""认证 API：登录/登出/当前用户"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.auth import create_token, verify_token
from app.core.config import get_settings

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


@router.post("/auth/login")
def login(body: LoginRequest):
    """简易登录：用户名 admin，密码从环境变量读取"""
    settings = get_settings()

    # 简单认证：admin / secret_key（生产环境需改为真正的密码）
    if body.username != "admin" or body.password != settings.secret_key:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(body.username)
    return LoginResponse(token=token, username=body.username)


@router.post("/auth/logout")
def logout():
    """登出（token 无服务端状态，前端删除即可）"""
    return {"status": "ok"}


@router.get("/auth/me")
def me():
    """当前用户信息"""
    return {"username": "admin", "role": "admin", "display_name": "系统管理员"}

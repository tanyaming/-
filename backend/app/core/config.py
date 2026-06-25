from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "无人车数据中台"
    app_env: str = "local"
    secret_key: str = "change-me"
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/vehicle_data_hub?charset=utf8mb4"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cert_storage_path: Path = Field(default=Path("./storage/certificates"))
    reporting_enabled: bool = False
    #chengdu_host: str = "182.148.54.57"  #开发环境
    chengdu_host: str = "171.221.218.40"  #测试环境
    chengdu_port: int = 48090
    # 逆地理编码 (高德地图 Web API Key)
    amap_web_api_key: str = "5a07496722e0cc1a6aa118eacf313042"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


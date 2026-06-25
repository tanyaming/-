"""
逆地理编码服务：经纬度 -> 省/市/区/街道/详细地址

支持：
- 高德地图 Web API（推荐，国内精度高）
- 本地 LRU 缓存避免重复请求
"""

import logging
import time
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 内存缓存：key=(lat, lng, provider), value=(result, expire_ts)
_cache: dict[tuple[float, float, str], tuple[dict[str, str], float]] = {}
_CACHE_TTL = 3600  # 1 小时


def _cache_key(lat: float, lng: float) -> tuple[float, float, str]:
    # 把经纬度四舍五入到小数点后 5 位作为缓存 key（约 1m 精度）
    return (round(lat, 5), round(lng, 5), "amap")


def reverse_geocode(lat: float, lng: float) -> dict[str, str] | None:
    """逆地理编码，返回地址字典"""
    if lat is None or lng is None:
        return None

    key = _cache_key(lat, lng)
    now = time.time()

    # 命中缓存
    if key in _cache:
        result, expire = _cache[key]
        if now < expire:
            return result

    settings = get_settings()
    api_key = settings.amap_web_api_key
    if not api_key:
        logger.debug("高德 API Key 未配置，跳过逆地理编码")
        return None

    try:
        # 高德逆地理编码 API
        # https://lbs.amap.com/api/webservice/guide/api/georegeo
        url = "https://restapi.amap.com/v3/geocode/regeo"
        params = {
            "key": api_key,
            "location": f"{lng},{lat}",
            "extensions": "base",
            "output": "JSON",
        }
        resp = httpx.get(url, params=params, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "1" or data.get("info") != "OK":
            logger.warning(f"逆地理编码失败: {data.get('info', 'unknown')}")
            return None

        regeo = data.get("regeocode", {})
        addr_comp = regeo.get("addressComponent", {})

        # 特殊处理：直辖市的 city 为空时用 province
        province = addr_comp.get("province", "") or ""
        city = addr_comp.get("city", "") or province  # 直辖市 city 可能为空
        district = addr_comp.get("district", "") or ""
        township = addr_comp.get("township", "") or ""
        street = addr_comp.get("streetNumber", {}).get("street", "") or ""
        street_num = addr_comp.get("streetNumber", {}).get("number", "") or ""
        formatted = regeo.get("formatted_address", "") or ""

        result = {
            "province": province,
            "city": city,
            "district": district,
            "township": township,
            "street": street,
            "street_number": street_num,
            "formatted_address": formatted,
            "address": (f"{province}{city}{district}{township}{street}{street_num}"
                        if not formatted else formatted),
        }

        _cache[key] = (result, now + _CACHE_TTL)
        return result

    except Exception as e:
        logger.error(f"逆地理编码异常: {e}")
        return None

"""
逆地理编码服务：经纬度 -> 省/市/区/街道/详细地址

设计要点（性能关键）：
- 接口主链路**绝不**做阻塞的外网请求。`get_address_fast()` 只读内存缓存，
  命中即返回地址，未命中返回 None 并把坐标投递到后台队列。
- 后台守护线程池异步调用高德 API，复用同一个 httpx.Client（连接池）。
- 内存缓存按经纬度网格 + TTL，避免重复请求；带容量上限防止内存膨胀。

这样 `/states/latest` 从「N 次串行 5s 外网请求」变为「零网络 I/O」，
响应从 10s+ 降到毫秒级；地址在后台几秒内补齐，响应结构保持不变。
"""

import logging
import queue
import threading
import time
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_CACHE_TTL = 1800          # 地址缓存 30 分钟
_CACHE_MAX = 20000         # 缓存条目上限，超出按最旧清理
_QUEUE_MAX = 5000          # 后台任务队列上限
_WORKERS = 4               # 后台地理编码并发线程数
_HTTP_TIMEOUT = 5.0

# 内存缓存：key=(lat5, lng5) -> (result, expire_ts)
_cache: dict[tuple[float, float], tuple[dict[str, str], float]] = {}
_cache_lock = threading.Lock()

# 待编码队列与去重集合（避免同一坐标重复入队）
_task_queue: "queue.Queue[tuple[float, float]]" = queue.Queue(maxsize=_QUEUE_MAX)
_inflight: set[tuple[float, float]] = set()
_inflight_lock = threading.Lock()

_client: httpx.Client | None = None
_client_lock = threading.Lock()
_workers_started = False
_start_lock = threading.Lock()


def _cache_key(lat: float, lng: float) -> tuple[float, float]:
    # 经纬度四舍五入到小数点后 5 位（约 1m 精度）作为缓存 key
    return (round(lat, 5), round(lng, 5))


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = httpx.Client(
                    timeout=_HTTP_TIMEOUT,
                    limits=httpx.Limits(max_keepalive_connections=_WORKERS, max_connections=_WORKERS * 2),
                )
    return _client


def _cache_get(key: tuple[float, float]) -> dict[str, str] | None:
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now < hit[1]:
            return hit[0]
    return None


def _cache_put(key: tuple[float, float], result: dict[str, str]) -> None:
    with _cache_lock:
        if len(_cache) >= _CACHE_MAX:
            # 简单清理：删掉最早过期/最旧的一批
            for k in sorted(_cache, key=lambda k: _cache[k][1])[: _CACHE_MAX // 10]:
                _cache.pop(k, None)
        _cache[key] = (result, time.time() + _CACHE_TTL)


def _do_request(lat: float, lng: float) -> dict[str, str] | None:
    """实际调用高德逆地理编码 API（在后台线程中执行）。"""
    settings = get_settings()
    api_key = settings.amap_web_api_key
    if not api_key:
        return None

    try:
        resp = _get_client().get(
            "https://restapi.amap.com/v3/geocode/regeo",
            params={
                "key": api_key,
                "location": f"{lng},{lat}",
                "extensions": "base",
                "output": "JSON",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "1" or data.get("info") != "OK":
            logger.warning("逆地理编码失败: %s", data.get("info", "unknown"))
            return None

        regeo = data.get("regeocode", {})
        addr_comp = regeo.get("addressComponent", {})

        province = addr_comp.get("province", "") or ""
        city = addr_comp.get("city", "") or province  # 直辖市 city 可能为空
        district = addr_comp.get("district", "") or ""
        township = addr_comp.get("township", "") or ""
        street_obj = addr_comp.get("streetNumber", {}) or {}
        street = street_obj.get("street", "") or ""
        street_num = street_obj.get("number", "") or ""
        formatted = regeo.get("formatted_address", "") or ""

        return {
            "province": province,
            "city": city,
            "district": district,
            "township": township,
            "street": street,
            "street_number": street_num,
            "formatted_address": formatted,
            "address": formatted or f"{province}{city}{district}{township}{street}{street_num}",
        }
    except Exception as e:  # noqa: BLE001 - 后台任务不可抛出
        logger.error("逆地理编码异常: %s", e)
        return None


def _worker() -> None:
    while True:
        key = _task_queue.get()
        try:
            lat, lng = key
            result = _do_request(lat, lng)
            if result is not None:
                _cache_put(key, result)
        finally:
            with _inflight_lock:
                _inflight.discard(key)
            _task_queue.task_done()


def _ensure_workers() -> None:
    global _workers_started
    if _workers_started:
        return
    with _start_lock:
        if _workers_started:
            return
        for i in range(_WORKERS):
            t = threading.Thread(target=_worker, name=f"geocode-worker-{i}", daemon=True)
            t.start()
        _workers_started = True


def _enqueue(key: tuple[float, float]) -> None:
    """把坐标投递到后台队列（去重、非阻塞）。"""
    with _inflight_lock:
        if key in _inflight:
            return
        _inflight.add(key)
    _ensure_workers()
    try:
        _task_queue.put_nowait(key)
    except queue.Full:
        with _inflight_lock:
            _inflight.discard(key)


def get_address_fast(lat: float | None, lng: float | None) -> dict[str, str] | None:
    """
    接口主链路调用：命中缓存立即返回地址；未命中返回 None 并触发后台编码，
    下次刷新（前端 10s 轮询）时即可拿到地址。**不做任何阻塞外网请求。**
    """
    if lat is None or lng is None:
        return None
    key = _cache_key(lat, lng)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    _enqueue(key)
    return None


def reverse_geocode(lat: float | None, lng: float | None) -> dict[str, str] | None:
    """
    同步逆地理编码（向后兼容）：命中缓存返回缓存，否则同步请求一次并写缓存。
    注意：会阻塞，**不要**在批量循环/请求主链路里使用，请改用 get_address_fast。
    """
    if lat is None or lng is None:
        return None
    key = _cache_key(lat, lng)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = _do_request(lat, lng)
    if result is not None:
        _cache_put(key, result)
    return result

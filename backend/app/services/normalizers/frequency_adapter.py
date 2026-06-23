"""
频率补齐策略：源数据低频时，按配置策略补齐到监管要求频率。

策略说明:
- strict:   低于目标频率则告警，按真实频率上报（不补齐）
- repeat:   最近值复用，将最近一次有效数据重复发送，数据标记 reused
- linear:   对位置、速度做线性插值，其他字段复用最近值，数据标记 interpolated
"""

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.services.normalizers.models import StandardVehicleState

logger = logging.getLogger(__name__)


class FillStrategy(StrEnum):
    STRICT = "strict"
    REPEAT = "repeat"
    LINEAR = "linear"


@dataclass
class StateWindow:
    """最近两次状态的窗口，用于插值计算"""
    prev: StandardVehicleState | None = None
    prev_time: float = 0.0  # 本地接收时间
    current: StandardVehicleState | None = None
    current_time: float = 0.0
    hit_count: int = 0  # 当前窗口复用次数
    quality_flags: list[str] = field(default_factory=list)


class FrequencyAdapter:
    """频率适配器：将低频源数据适配到目标频率"""

    def __init__(
        self,
        target_hz: float = 10.0,
        source_hz: float = 1.0,
        strategy: FillStrategy = FillStrategy.REPEAT,
    ) -> None:
        self.target_hz = target_hz
        self.source_hz = source_hz
        self.strategy = strategy
        self.target_interval = 1.0 / target_hz if target_hz > 0 else 0.1
        self._window = StateWindow()
        self._last_source_time: float = 0.0
        self._source_interval: float = 1.0 / source_hz if source_hz > 0 else 1.0

    def feed(self, state: StandardVehicleState) -> None:
        """喂入新的真实源数据"""
        now = time.time()

        # 滑动窗口
        if self._window.current is not None:
            self._window.prev = self._window.current
            self._window.prev_time = self._window.current_time

        self._window.current = state
        self._window.current_time = now
        self._window.hit_count = 0
        self._window.quality_flags = []

        # 更新实际源间隔
        if self._last_source_time > 0:
            actual_interval = now - self._last_source_time
            self._source_interval = actual_interval
        self._last_source_time = now

    def get_state(self) -> StandardVehicleState | None:
        """
        获取下一个要上报的状态。
        如果策略允许且窗口内数据有效，可能返回复用/插值状态。
        Returns None 表示严格模式下无数据可上报。
        """
        if self._window.current is None:
            return None

        if self.strategy == FillStrategy.STRICT:
            return self._strict_get()
        elif self.strategy == FillStrategy.REPEAT:
            return self._repeat_get()
        elif self.strategy == FillStrategy.LINEAR:
            return self._linear_get()
        else:
            return self._window.current

    # ------------------------------------------------------------------
    # 策略实现
    # ------------------------------------------------------------------

    def _strict_get(self) -> StandardVehicleState | None:
        """严格模式：只有新数据到达并消耗后才返回，消耗后设为 None"""
        if self._window.hit_count > 0:
            # 已消耗过，等待新数据
            return None
        self._window.hit_count += 1
        self._window.quality_flags.append("strict_mode")
        state = self._window.current
        if state:
            state.quality["fill_strategy"] = "none"
            state.quality["source_hz"] = self.source_hz
        return state

    def _repeat_get(self) -> StandardVehicleState | None:
        """复用模式：每次请求都返回最近有效数据，标记 reused"""
        if self._window.current is None:
            return None

        self._window.hit_count += 1
        state = self._window.current

        if self._window.hit_count == 1:
            # 首次使用 -> 真实数据
            state.quality["fill_strategy"] = "none"
        else:
            # 复用
            state.quality["fill_strategy"] = "reused"
            state.quality["reuse_count"] = self._window.hit_count

        state.quality["source_hz"] = round(1.0 / self._source_interval, 2) if self._source_interval > 0 else 0
        state.quality["target_hz"] = self.target_hz
        return state

    def _linear_get(self) -> StandardVehicleState | None:
        """
        线性插值模式：
        - 位置(lon/lat)：在 prev→current 之间线性插值
        - 速度：取最近值
        - 角度：取最近值
        - 其他字段：取 current
        """
        if self._window.current is None:
            return None

        self._window.hit_count += 1

        if self._window.hit_count == 1:
            state = self._window.current
            state.quality["fill_strategy"] = "none"
            state.quality["source_hz"] = round(1.0 / self._source_interval, 2) if self._source_interval > 0 else 0
            state.quality["target_hz"] = self.target_hz
            return state

        # 插值
        prev = self._window.prev
        curr = self._window.current
        if prev is None or prev.longitude is None or prev.latitude is None:
            # 无历史数据，退化为复用
            state = curr
            state.quality["fill_strategy"] = "reused"
            state.quality["reuse_count"] = self._window.hit_count
            return state

        # 计算插值比例
        # 假设源间隔内需要产生 n 条目标频率数据
        expected_per_source = max(1, int(self.target_hz / max(self.source_hz, 0.5)))
        # hit_count 从 1 开始, 第 2 次调用相当于第 1 次插值
        t = self._window.hit_count - 1
        fraction = min(1.0, t / max(expected_per_source, 1))

        # 创建插值后的状态
        import copy
        interpolated = copy.deepcopy(curr)

        # 线性插值位置
        if curr.longitude is not None and curr.latitude is not None:
            interpolated.longitude = prev.longitude + (curr.longitude - prev.longitude) * fraction  # type: ignore
            interpolated.latitude = prev.latitude + (curr.latitude - prev.latitude) * fraction  # type: ignore

        # 速度线性插值
        if prev.speed_mps is not None and curr.speed_mps is not None:
            interpolated.speed_mps = prev.speed_mps + (curr.speed_mps - prev.speed_mps) * fraction  # type: ignore

        interpolated.quality["fill_strategy"] = "interpolated"
        interpolated.quality["interpolation_fraction"] = round(fraction, 3)
        interpolated.quality["reuse_count"] = self._window.hit_count
        interpolated.quality["source_hz"] = round(1.0 / self._source_interval, 2) if self._source_interval > 0 else 0
        interpolated.quality["target_hz"] = self.target_hz
        return interpolated

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    @property
    def is_stale(self) -> bool:
        """源数据是否已过期（超过源间隔 3 倍）"""
        if self._last_source_time == 0:
            return True
        return time.time() - self._last_source_time > self._source_interval * 3

    @property
    def actual_source_hz(self) -> float:
        """实际源频率"""
        if self._source_interval <= 0:
            return 0.0
        return 1.0 / self._source_interval

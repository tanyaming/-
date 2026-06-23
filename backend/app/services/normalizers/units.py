import math


def kmh_to_mps(value: float | int | None) -> float | None:
    return None if value is None else float(value) / 3.6


def rad_east_ccw_to_deg_north_cw(value: float | int | None) -> float | None:
    if value is None:
        return None
    deg_from_east_ccw = math.degrees(float(value))
    return (90.0 - deg_from_east_ccw) % 360.0


def rad_to_deg(value: float | int | None) -> float | None:
    return None if value is None else math.degrees(float(value))


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


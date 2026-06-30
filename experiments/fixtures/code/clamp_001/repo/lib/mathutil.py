def clamp(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    return value

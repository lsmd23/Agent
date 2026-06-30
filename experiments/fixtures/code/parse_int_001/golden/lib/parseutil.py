def safe_int(value: str) -> int:
    if not value.strip():
        return 0
    return int(value)

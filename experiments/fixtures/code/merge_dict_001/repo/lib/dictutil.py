def deep_merge(a: dict, b: dict) -> dict:
    result = dict(a)
    result.update(b)
    return result

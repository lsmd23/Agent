def get_path(data: dict, key: str):
    current = data
    for part in key.split('.'):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current

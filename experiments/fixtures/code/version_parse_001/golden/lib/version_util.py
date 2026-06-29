def parse_version(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def is_compatible(required: str, installed: str) -> bool:
    return parse_version(installed) >= parse_version(required)

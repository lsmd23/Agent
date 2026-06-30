import re

_TAG_RE = re.compile(r'<[^>]+>')


def strip_tags(text: str) -> str:
    return _TAG_RE.sub('', text)

def trim_lines(text: str) -> str:
    """Strip whitespace from each line."""
    return '\n'.join(line.strip() for line in text.splitlines())

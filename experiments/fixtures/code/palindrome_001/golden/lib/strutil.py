def is_palindrome(text: str) -> bool:
    normalized = text.lower().replace(' ', '')
    return normalized == normalized[::-1]

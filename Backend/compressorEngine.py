import re


def compressor(text: str) -> str:
    """Compact whitespace while retaining all story text."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return re.sub(r"\s+", " ", text).strip()

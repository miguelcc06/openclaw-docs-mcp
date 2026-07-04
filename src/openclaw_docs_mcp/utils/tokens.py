import tiktoken

_ENCODING: tiktoken.Encoding | None = None


def get_encoding() -> tiktoken.Encoding:
    global _ENCODING
    if _ENCODING is None:
        _ENCODING = tiktoken.get_encoding("cl100k_base")
    return _ENCODING


def count_tokens(text: str) -> int:
    return len(get_encoding().encode(text))

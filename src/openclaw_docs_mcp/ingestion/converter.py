from markitdown import MarkItDown

_md = MarkItDown(enable_plugins=False)


def convert_url(url: str) -> str:
    result = _md.convert(url)
    return result.text_content

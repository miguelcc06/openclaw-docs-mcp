import re
import xml.etree.ElementTree as ET

import httpx

from openclaw_docs_mcp.config import get_settings

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
LOCALE_CODES = {
    "ar", "de", "es", "fr", "ja-JP", "ko", "pt-BR", "ru", "uk", "zh-CN", "zh-TW",
    "hi", "id", "it", "nl", "pl", "tr", "vi", "fa", "th",
}
LOCALE_PATTERN = re.compile(
    r"^https://docs\.openclaw\.ai/(" + "|".join(re.escape(c) for c in LOCALE_CODES) + r")(?:/|$)"
)
REDIRECT_MARKERS = ("redirect to",)


async def fetch_sitemap_urls(client: httpx.AsyncClient) -> list[str]:
    settings = get_settings()
    response = await client.get(f"{settings.docs_base_url}/sitemap.xml")
    response.raise_for_status()
    root = ET.fromstring(response.text)
    urls: list[str] = []
    for loc in root.findall(".//sm:loc", SITEMAP_NS):
        if loc.text:
            urls.append(loc.text.strip())
    return urls


def filter_english_urls(urls: list[str]) -> list[str]:
    settings = get_settings()
    locale_prefixes = settings.locale_prefixes
    filtered: list[str] = []
    for url in urls:
        if LOCALE_PATTERN.match(url):
            continue
        for prefix in locale_prefixes:
            if f"/{prefix}/" in url:
                break
        else:
            path = url.replace(settings.docs_base_url, "").rstrip("/")
            if not path or path.endswith((".md", ".json", ".xml", ".txt")):
                continue
            segment = path.lstrip("/").split("/")[0]
            if segment in LOCALE_CODES:
                continue
            filtered.append(url)
    return sorted(set(filtered))


def url_to_path(url: str) -> str:
    settings = get_settings()
    path = url.replace(settings.docs_base_url, "").split("?")[0].rstrip("/")
    return path or "/"


def is_redirect_page(content: str) -> bool:
    lower = content.lower()
    if lower.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            check = (parts[1] + parts[2][:200]).lower()
            return any(marker in check for marker in REDIRECT_MARKERS)
    return any(marker in lower[:300] for marker in REDIRECT_MARKERS)


def extract_title(content: str) -> str | None:
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if line.strip().lower().startswith("title:"):
                    return line.split(":", 1)[1].strip().strip('"').strip("'")
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None

import httpx

from openclaw_docs_mcp.config import get_settings
from openclaw_docs_mcp.ingestion.sitemap import url_to_path


async def fetch_markdown(client: httpx.AsyncClient, url: str) -> str:
    settings = get_settings()
    path = url_to_path(url)
    md_url = f"{settings.docs_base_url}{path}.md"
    response = await client.get(
        md_url,
        headers={"Accept": "text/markdown"},
        follow_redirects=True,
    )
    response.raise_for_status()
    return response.text

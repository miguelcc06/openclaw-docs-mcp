import uuid

from fastmcp import FastMCP

from openclaw_docs_mcp.db.pool import get_pool
from openclaw_docs_mcp.db import queries


def register_discovery_tools(mcp: FastMCP) -> None:
    @mcp.tool
    async def list_pages(
        prefix: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List indexed OpenClaw documentation pages with path, title, and chunk count. Paginated."""
        pool = await get_pool()
        return await queries.list_pages(pool, prefix, min(limit, 200), max(offset, 0))

    @mcp.tool
    async def get_page_outline(page_id: str) -> dict:
        """Return heading hierarchy and chunk IDs for a page without full content bodies."""
        pool = await get_pool()
        return await queries.get_page_outline(pool, uuid.UUID(page_id))

    @mcp.tool
    async def get_stats() -> dict:
        """Index statistics: document count, chunk count, last sync, and embedding model."""
        pool = await get_pool()
        return await queries.get_stats(pool)

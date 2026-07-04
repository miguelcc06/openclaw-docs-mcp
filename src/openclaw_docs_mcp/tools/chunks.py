import uuid

from fastmcp import FastMCP

from openclaw_docs_mcp.db.pool import get_pool
from openclaw_docs_mcp.db import queries


def register_chunk_tools(mcp: FastMCP) -> None:
    @mcp.tool
    async def get_chunk(chunk_id: str) -> dict:
        """Retrieve full chunk content by UUID, including metadata and prev/next IDs."""
        pool = await get_pool()
        return await queries.get_chunk(pool, uuid.UUID(chunk_id))

    @mcp.tool
    async def get_chunks(chunk_ids: list[str]) -> list[dict]:
        """Batch retrieve 1–20 chunks by ID."""
        pool = await get_pool()
        ids = [uuid.UUID(cid) for cid in chunk_ids[:20]]
        return await queries.get_chunks(pool, ids)

    @mcp.tool
    async def get_chunk_next(chunk_id: str, count: int = 5) -> dict:
        """Get the next N chunks in document order (default 5, max 100)."""
        pool = await get_pool()
        return await queries.get_adjacent_chunks(pool, uuid.UUID(chunk_id), "next", count)

    @mcp.tool
    async def get_chunk_prev(chunk_id: str, count: int = 5) -> dict:
        """Get the previous N chunks in document order (default 5, max 100)."""
        pool = await get_pool()
        return await queries.get_adjacent_chunks(pool, uuid.UUID(chunk_id), "prev", count)

    @mcp.tool
    async def get_chunk_neighbors(chunk_id: str, count: int = 2) -> dict:
        """Get previous, current, and next chunks in one call."""
        pool = await get_pool()
        return await queries.get_neighbors(pool, uuid.UUID(chunk_id), count)

    @mcp.tool
    async def get_context_window(chunk_id: str, before: int = 2, after: int = 2) -> dict:
        """Symmetric context window around a chunk (configurable before/after count)."""
        pool = await get_pool()
        return await queries.get_context_window(pool, uuid.UUID(chunk_id), before, after)

    @mcp.tool
    async def get_document_chunks(page_id: str, from_index: int = 0, limit: int = 20) -> dict:
        """Paginate chunks within a document by chunk_index."""
        pool = await get_pool()
        return await queries.get_document_chunks(
            pool, uuid.UUID(page_id), max(from_index, 0), min(limit, 100)
        )

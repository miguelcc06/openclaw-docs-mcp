import uuid

from fastmcp import FastMCP

from openclaw_docs_mcp.config import get_settings
from openclaw_docs_mcp.db.pool import get_pool
from openclaw_docs_mcp.db import queries
from openclaw_docs_mcp.ingestion.embedder import OpenAIEmbedder

def register_search_tools(mcp: FastMCP) -> None:
    @mcp.tool
    async def search(
        query: str,
        limit: int | None = None,
        min_score: float | None = None,
    ) -> list[dict]:
        """Hybrid semantic + full-text search across OpenClaw docs. For best results, write search queries in English (documentation is indexed in English only). Returns snippets, scores, and chunk IDs."""
        settings = get_settings()
        pool = await get_pool()
        embedder = OpenAIEmbedder()
        embedding = await embedder.embed_query(query)
        return await queries.hybrid_search(
            pool,
            query,
            embedding,
            limit=limit or settings.search_default_limit,
            min_score=min_score if min_score is not None else settings.search_min_score,
        )

    @mcp.tool
    async def search_in_page(
        query: str,
        page_id: str,
        limit: int = 5,
    ) -> list[dict]:
        """Hybrid search scoped to a single document. For best results, write search queries in English (documentation is indexed in English only)."""
        pool = await get_pool()
        embedder = OpenAIEmbedder()
        embedding = await embedder.embed_query(query)
        settings = get_settings()
        return await queries.hybrid_search(
            pool,
            query,
            embedding,
            limit=min(limit, 20),
            min_score=settings.search_min_score,
            document_id=uuid.UUID(page_id),
        )

    @mcp.tool
    async def lexical_search(
        query: str,
        limit: int = 10,
        page_id: str | None = None,
    ) -> list[dict]:
        """Full-text search only (tsvector). Useful for exact CLI command names. For best results, write search queries in English (documentation is indexed in English only)."""
        pool = await get_pool()
        doc_id = uuid.UUID(page_id) if page_id else None
        return await queries.lexical_search(pool, query, min(limit, 50), doc_id)

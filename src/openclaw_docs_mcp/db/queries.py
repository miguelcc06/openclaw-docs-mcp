import json
import uuid
from typing import Any

import asyncpg

from openclaw_docs_mcp.config import get_settings
from openclaw_docs_mcp.utils.errors import ChunkNotFoundError, PageNotFoundError


def _snippet(content: str, max_len: int = 200) -> str:
    text = content.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _row_to_chunk(row: asyncpg.Record, include_content: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {
        "chunk_id": str(row["id"]),
        "page_id": str(row["document_id"]),
        "page_path": row["page_path"],
        "heading_path": list(row["heading_path"] or []),
        "chunk_index": row["chunk_index"],
        "token_count": row["token_count"],
        "prev_id": str(row["prev_id"]) if row.get("prev_id") else None,
        "next_id": str(row["next_id"]) if row.get("next_id") else None,
    }
    if include_content:
        result["content"] = row["content"]
    if "similarity" in row and row["similarity"] is not None:
        result["score"] = float(row["similarity"])
        result["snippet"] = _snippet(row["content"])
    return result


async def hybrid_search(
    pool: asyncpg.Pool,
    query_text: str,
    query_embedding: list[float],
    limit: int = 8,
    min_score: float = 0.0,
    document_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    settings = get_settings()
    async with pool.acquire() as conn:
        if settings.hybrid_search:
            rows = await conn.fetch(
                """
                SELECT * FROM hybrid_search($1, $2::vector, $3, $4, $5)
                """,
                query_text,
                _vector_literal(query_embedding),
                limit,
                min_score,
                document_id,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM search_chunks($1::vector, $2, $3, $4)
                """,
                _vector_literal(query_embedding),
                limit,
                document_id,
                min_score,
            )
    return [_row_to_chunk(r, include_content=False) for r in rows]


async def lexical_search(
    pool: asyncpg.Pool,
    query_text: str,
    limit: int = 10,
    document_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                c.id,
                c.document_id,
                c.content,
                c.heading_path,
                c.chunk_index,
                c.token_count,
                c.prev_id,
                c.next_id,
                d.path AS page_path,
                ts_rank(c.content_tsv, plainto_tsquery('english', $1)) AS similarity
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.content_tsv @@ plainto_tsquery('english', $1)
              AND ($2::uuid IS NULL OR c.document_id = $2)
            ORDER BY similarity DESC
            LIMIT $3
            """,
            query_text,
            document_id,
            limit,
        )
    return [_row_to_chunk(r, include_content=False) for r in rows]


async def get_chunk(pool: asyncpg.Pool, chunk_id: uuid.UUID) -> dict[str, Any]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT c.*, d.path AS page_path
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.id = $1
            """,
            chunk_id,
        )
    if not row:
        raise ChunkNotFoundError(f"Chunk not found: {chunk_id}")
    return _row_to_chunk(row)


async def get_chunks(pool: asyncpg.Pool, chunk_ids: list[uuid.UUID]) -> list[dict[str, Any]]:
    if not chunk_ids:
        return []
    if len(chunk_ids) > 20:
        chunk_ids = chunk_ids[:20]
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.*, d.path AS page_path
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.id = ANY($1::uuid[])
            ORDER BY c.chunk_index
            """,
            chunk_ids,
        )
    return [_row_to_chunk(r) for r in rows]


async def get_adjacent_chunks(
    pool: asyncpg.Pool,
    chunk_id: uuid.UUID,
    direction: str,
    count: int,
) -> dict[str, Any]:
    count = min(max(count, 1), 100)
    async with pool.acquire() as conn:
        current = await conn.fetchrow(
            "SELECT id, document_id, chunk_index FROM chunks WHERE id = $1",
            chunk_id,
        )
        if not current:
            raise ChunkNotFoundError(f"Chunk not found: {chunk_id}")

        if direction == "next":
            rows = await conn.fetch(
                """
                SELECT c.*, d.path AS page_path
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.document_id = $1 AND c.chunk_index > $2
                ORDER BY c.chunk_index ASC
                LIMIT $3
                """,
                current["document_id"],
                current["chunk_index"],
                count,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT c.*, d.path AS page_path
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.document_id = $1 AND c.chunk_index < $2
                ORDER BY c.chunk_index DESC
                LIMIT $3
                """,
                current["document_id"],
                current["chunk_index"],
                count,
            )
            rows = list(reversed(rows))

    return {
        "reference_chunk_id": str(chunk_id),
        "direction": direction,
        "chunks": [_row_to_chunk(r) for r in rows],
    }


async def get_neighbors(
    pool: asyncpg.Pool,
    chunk_id: uuid.UUID,
    count: int = 2,
) -> dict[str, Any]:
    async with pool.acquire() as conn:
        current = await conn.fetchrow(
            """
            SELECT c.*, d.path AS page_path
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.id = $1
            """,
            chunk_id,
        )
        if not current:
            raise ChunkNotFoundError(f"Chunk not found: {chunk_id}")

        prev_rows = await conn.fetch(
            """
            SELECT c.*, d.path AS page_path
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.document_id = $1 AND c.chunk_index < $2
            ORDER BY c.chunk_index DESC
            LIMIT $3
            """,
            current["document_id"],
            current["chunk_index"],
            count,
        )
        next_rows = await conn.fetch(
            """
            SELECT c.*, d.path AS page_path
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.document_id = $1 AND c.chunk_index > $2
            ORDER BY c.chunk_index ASC
            LIMIT $3
            """,
            current["document_id"],
            current["chunk_index"],
            count,
        )

    return {
        "chunk_id": str(chunk_id),
        "previous": [_row_to_chunk(r) for r in reversed(prev_rows)],
        "current": _row_to_chunk(current),
        "next": [_row_to_chunk(r) for r in next_rows],
    }


async def get_context_window(
    pool: asyncpg.Pool,
    chunk_id: uuid.UUID,
    before: int = 2,
    after: int = 2,
) -> dict[str, Any]:
    neighbors = await get_neighbors(pool, chunk_id, count=max(before, after))
    return {
        "chunk_id": str(chunk_id),
        "before": neighbors["previous"][-before:] if before else [],
        "current": neighbors["current"],
        "after": neighbors["next"][:after] if after else [],
    }


async def list_pages(
    pool: asyncpg.Pool,
    prefix: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    async with pool.acquire() as conn:
        if prefix:
            rows = await conn.fetch(
                """
                SELECT id, path, title, chunk_count, token_count, indexed_at
                FROM documents
                WHERE path LIKE $1
                ORDER BY path
                LIMIT $2 OFFSET $3
                """,
                f"{prefix}%",
                limit,
                offset,
            )
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM documents WHERE path LIKE $1",
                f"{prefix}%",
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, path, title, chunk_count, token_count, indexed_at
                FROM documents
                ORDER BY path
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
            total = await conn.fetchval("SELECT COUNT(*) FROM documents")

    pages = [
        {
            "page_id": str(r["id"]),
            "path": r["path"],
            "title": r["title"],
            "chunk_count": r["chunk_count"],
            "token_count": r["token_count"],
            "indexed_at": r["indexed_at"].isoformat() if r["indexed_at"] else None,
        }
        for r in rows
    ]
    return {"pages": pages, "total": total, "limit": limit, "offset": offset}


async def get_page_outline(pool: asyncpg.Pool, page_id: uuid.UUID) -> dict[str, Any]:
    async with pool.acquire() as conn:
        doc = await conn.fetchrow(
            "SELECT id, path, title, chunk_count FROM documents WHERE id = $1",
            page_id,
        )
        if not doc:
            raise PageNotFoundError(f"Page not found: {page_id}")
        rows = await conn.fetch(
            """
            SELECT id, chunk_index, heading_path, token_count
            FROM chunks
            WHERE document_id = $1
            ORDER BY chunk_index
            """,
            page_id,
        )

    sections = [
        {
            "chunk_id": str(r["id"]),
            "chunk_index": r["chunk_index"],
            "heading_path": list(r["heading_path"] or []),
            "token_count": r["token_count"],
        }
        for r in rows
    ]
    return {
        "page_id": str(doc["id"]),
        "path": doc["path"],
        "title": doc["title"],
        "chunk_count": doc["chunk_count"],
        "sections": sections,
    }


async def get_document_chunks(
    pool: asyncpg.Pool,
    page_id: uuid.UUID,
    from_index: int,
    limit: int,
) -> dict[str, Any]:
    async with pool.acquire() as conn:
        doc = await conn.fetchrow("SELECT id, path, title FROM documents WHERE id = $1", page_id)
        if not doc:
            raise PageNotFoundError(f"Page not found: {page_id}")
        rows = await conn.fetch(
            """
            SELECT c.*, d.path AS page_path
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.document_id = $1 AND c.chunk_index >= $2
            ORDER BY c.chunk_index
            LIMIT $3
            """,
            page_id,
            from_index,
            limit,
        )
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM chunks WHERE document_id = $1",
            page_id,
        )

    return {
        "page_id": str(page_id),
        "path": doc["path"],
        "from_index": from_index,
        "limit": limit,
        "total_chunks": total,
        "chunks": [_row_to_chunk(r) for r in rows],
    }


async def get_stats(pool: asyncpg.Pool) -> dict[str, Any]:
    settings = get_settings()
    async with pool.acquire() as conn:
        doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        chunk_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        last_sync = await conn.fetchrow(
            """
            SELECT finished_at, pages_processed, pages_updated, status
            FROM ingest_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        )
        stored_model = await conn.fetchval(
            "SELECT embedding_model FROM chunks WHERE embedding_model IS NOT NULL LIMIT 1"
        )

    stats: dict[str, Any] = {
        "document_count": doc_count,
        "chunk_count": chunk_count,
        "embedding_model": stored_model or settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
        "hybrid_search": settings.hybrid_search,
    }
    if last_sync:
        stats["last_sync"] = {
            "finished_at": last_sync["finished_at"].isoformat() if last_sync["finished_at"] else None,
            "pages_processed": last_sync["pages_processed"],
            "pages_updated": last_sync["pages_updated"],
            "status": last_sync["status"],
        }
    if stored_model and stored_model != settings.embedding_model:
        stats["warning"] = "embedding_model_mismatch"
    return stats


async def resolve_page_id(pool: asyncpg.Pool, page_path: str) -> uuid.UUID:
    path = page_path if page_path.startswith("/") else f"/{page_path}"
    async with pool.acquire() as conn:
        page_id = await conn.fetchval("SELECT id FROM documents WHERE path = $1", path)
    if not page_id:
        raise PageNotFoundError(f"Page not found: {path}")
    return page_id


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(v) for v in values) + "]"

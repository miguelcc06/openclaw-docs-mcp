import asyncio
import hashlib
import uuid
from datetime import datetime, timezone

import asyncpg
import httpx

from openclaw_docs_mcp.config import get_settings
from openclaw_docs_mcp.db.pool import get_pool
from openclaw_docs_mcp.ingestion.chunker import chunk_markdown
from openclaw_docs_mcp.ingestion.converter import convert_url
from openclaw_docs_mcp.ingestion.embedder import OpenAIEmbedder
from openclaw_docs_mcp.ingestion.fetcher import fetch_markdown
from openclaw_docs_mcp.ingestion.sitemap import (
    extract_title,
    fetch_sitemap_urls,
    filter_english_urls,
    is_redirect_page,
    url_to_path,
)


async def run_ingest(full: bool = False) -> dict:
    settings = get_settings()
    pool = await get_pool()
    embedder = OpenAIEmbedder()
    run_id = uuid.uuid4()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO ingest_runs (id, started_at, status, full_run)
            VALUES ($1, $2, 'running', $3)
            """,
            run_id,
            datetime.now(timezone.utc),
            full,
        )

    processed = 0
    updated = 0
    errors: list[str] = []

    limits = httpx.Limits(max_connections=settings.ingest_concurrency)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        urls = filter_english_urls(await fetch_sitemap_urls(client))
        sem = asyncio.Semaphore(settings.ingest_concurrency)

        async def process_url(url: str) -> None:
            nonlocal processed, updated
            async with sem:
                try:
                    changed = await _process_page(pool, client, embedder, url, full)
                    processed += 1
                    if changed:
                        updated += 1
                except Exception as exc:
                    errors.append(f"{url}: {exc}")
                await asyncio.sleep(settings.ingest_rate_limit_ms / 1000)

        await asyncio.gather(*[process_url(url) for url in urls])

    status = "completed" if not errors else "completed_with_errors"
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE ingest_runs
            SET finished_at = $2, pages_processed = $3, pages_updated = $4,
                status = $5, error_log = $6
            WHERE id = $1
            """,
            run_id,
            datetime.now(timezone.utc),
            processed,
            updated,
            status,
            "\n".join(errors[:100]) if errors else None,
        )

    return {
        "run_id": str(run_id),
        "pages_processed": processed,
        "pages_updated": updated,
        "errors": len(errors),
        "status": status,
    }


async def _process_page(
    pool: asyncpg.Pool,
    client: httpx.AsyncClient,
    embedder: OpenAIEmbedder,
    url: str,
    full: bool,
) -> bool:
    settings = get_settings()
    path = url_to_path(url)

    try:
        content = await fetch_markdown(client, url)
    except Exception:
        content = convert_url(url)

    if is_redirect_page(content):
        return False

    content_hash = hashlib.sha256(content.encode()).hexdigest()
    title = extract_title(content) or path.strip("/").split("/")[-1]

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id, content_hash FROM documents WHERE path = $1",
            path,
        )
        if existing and existing["content_hash"] == content_hash and not full:
            return False

        if existing:
            doc_id = existing["id"]
            await conn.execute("DELETE FROM chunks WHERE document_id = $1", doc_id)
            await conn.execute(
                """
                UPDATE documents
                SET title = $2, source_url = $3, content_hash = $4,
                    token_count = $5, indexed_at = $6, updated_at = $6
                WHERE id = $1
                """,
                doc_id,
                title,
                url,
                content_hash,
                0,
                datetime.now(timezone.utc),
            )
        else:
            doc_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO documents (id, path, title, source_url, content_hash, indexed_at, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $6, $6)
                """,
                doc_id,
                path,
                title,
                url,
                content_hash,
                datetime.now(timezone.utc),
            )

    chunks = chunk_markdown(content)
    if not chunks:
        return True

    embeddings = await embedder.embed_texts([c.content for c in chunks])
    total_tokens = sum(c.token_count for c in chunks)

    async with pool.acquire() as conn:
        chunk_ids: list[uuid.UUID] = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            chunk_id = uuid.uuid4()
            chunk_ids.append(chunk_id)
            await conn.execute(
                """
                INSERT INTO chunks (
                    id, document_id, chunk_index, content, token_count,
                    heading_path, embedding, embedding_model, start_line, end_line
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8, $9, $10)
                """,
                chunk_id,
                doc_id,
                idx,
                chunk.content,
                chunk.token_count,
                chunk.heading_path,
                _vector_literal(embedding),
                settings.embedding_model,
                chunk.start_line,
                chunk.end_line,
            )

        for i in range(len(chunk_ids)):
            prev_id = chunk_ids[i - 1] if i > 0 else None
            next_id = chunk_ids[i + 1] if i < len(chunk_ids) - 1 else None
            await conn.execute(
                "UPDATE chunks SET prev_id = $2, next_id = $3 WHERE id = $1",
                chunk_ids[i],
                prev_id,
                next_id,
            )

        await conn.execute(
            """
            UPDATE documents
            SET chunk_count = $2, token_count = $3, indexed_at = $4, updated_at = $4
            WHERE id = $1
            """,
            doc_id,
            len(chunks),
            total_tokens,
            datetime.now(timezone.utc),
        )

    return True


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(v) for v in values) + "]"

import asyncio
import json

import typer

from openclaw_docs_mcp.db.pool import close_pool, get_pool
from openclaw_docs_mcp.db import queries
from openclaw_docs_mcp.ingestion.sync import run_ingest
from openclaw_docs_mcp.main import run_server

app = typer.Typer(no_args_is_help=True, help="OpenClaw Docs MCP — RAG server for docs.openclaw.ai")


@app.command()
def serve() -> None:
    """Start the MCP HTTP server."""
    run_server()


@app.command()
def ingest(full: bool = typer.Option(False, "--full", help="Re-index all pages regardless of content hash")) -> None:
    """Crawl docs.openclaw.ai sitemap and index English documentation."""
    result = asyncio.run(run_ingest(full=full))
    typer.echo(json.dumps(result, indent=2))


@app.command()
def sync() -> None:
    """Incremental sync: only re-index pages whose content hash changed."""
    result = asyncio.run(run_ingest(full=False))
    typer.echo(json.dumps(result, indent=2))


@app.command()
def stats() -> None:
    """Print index statistics."""

    async def _stats() -> dict:
        pool = await get_pool()
        try:
            return await queries.get_stats(pool)
        finally:
            await close_pool()

    typer.echo(json.dumps(asyncio.run(_stats()), indent=2))


if __name__ == "__main__":
    app()

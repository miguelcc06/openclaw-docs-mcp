from contextlib import asynccontextmanager

from fastmcp import FastMCP

from openclaw_docs_mcp.auth import ApiKeyMiddleware
from openclaw_docs_mcp.db.pool import close_pool, get_pool
from openclaw_docs_mcp.config import get_settings
from openclaw_docs_mcp.tools import register_all_tools


@asynccontextmanager
async def lifespan(server: FastMCP):
    await get_pool()
    yield
    await close_pool()


def create_mcp() -> FastMCP:
    mcp = FastMCP(
        "openclaw-docs-mcp",
        instructions=(
            "OpenClaw documentation RAG server. Use search tools to find relevant chunks, "
            "then get_chunk or get_chunk_neighbors to read full content. "
            "Write search queries in English for best results."
        ),
        lifespan=lifespan,
    )
    mcp.add_middleware(ApiKeyMiddleware())
    register_all_tools(mcp)
    return mcp


def run_server() -> None:
    settings = get_settings()
    mcp = create_mcp()
    mcp.run(
        transport="http",
        host=settings.mcp_host,
        port=settings.mcp_port,
        path=settings.mcp_path,
    )

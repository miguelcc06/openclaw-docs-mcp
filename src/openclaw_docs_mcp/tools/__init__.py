from fastmcp import FastMCP

from openclaw_docs_mcp.tools.chunks import register_chunk_tools
from openclaw_docs_mcp.tools.discovery import register_discovery_tools
from openclaw_docs_mcp.tools.search import register_search_tools


def register_all_tools(mcp: FastMCP) -> None:
    register_discovery_tools(mcp)
    register_search_tools(mcp)
    register_chunk_tools(mcp)

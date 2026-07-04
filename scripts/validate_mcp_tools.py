#!/usr/bin/env python3
"""Validate all openclaw-docs MCP tools via HTTP transport."""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / "config.env")

API_KEY = os.environ.get("API_KEY", "")
URL = "http://127.0.0.1:8000/mcp"


async def main() -> int:
    if not API_KEY:
        print("ERROR: API_KEY not set in config.env")
        return 1

    transport = StreamableHttpTransport(
        URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
    )

    results: list[dict] = []
    page_id: str | None = None
    chunk_id: str | None = None

    async with Client(transport) as client:
        tools = await client.list_tools()
        tool_names = {t.name for t in tools}
        print(f"Connected. Tools listed: {len(tools)}")
        print(f"Names: {sorted(tool_names)}\n")

        async def run(name: str, args: dict) -> None:
            try:
                result = await client.call_tool(name, args)
                text = result.content[0].text if result.content else str(result)
                preview = text[:200] + "..." if len(text) > 200 else text
                results.append({"tool": name, "status": "ok", "preview": preview})
                print(f"  OK  {name}")
            except Exception as exc:
                results.append({"tool": name, "status": "error", "error": str(exc)})
                print(f"  FAIL {name}: {exc}")

        await run("get_stats", {})
        list_result = await client.call_tool("list_pages", {"limit": 3, "offset": 0})
        list_text = list_result.content[0].text
        list_data = json.loads(list_text)
        page_id = list_data["pages"][0]["page_id"] if list_data.get("pages") else None
        results.append({"tool": "list_pages", "status": "ok", "pages": len(list_data.get("pages", []))})
        print(f"  OK  list_pages ({len(list_data.get('pages', []))} pages)")

        search_result = await client.call_tool("search", {"query": "gateway configuration", "limit": 3})
        search_data = json.loads(search_result.content[0].text)
        if isinstance(search_data, list) and search_data:
            chunk_id = search_data[0].get("chunk_id")
        results.append({"tool": "search", "status": "ok", "hits": len(search_data) if isinstance(search_data, list) else 0})
        print(f"  OK  search ({len(search_data) if isinstance(search_data, list) else 0} hits)")

        await run("lexical_search", {"query": "openclaw gateway", "limit": 3})

        if page_id:
            await run("get_page_outline", {"page_id": page_id})
            await run("search_in_page", {"query": "configuration", "page_id": page_id, "limit": 3})
            await run("get_document_chunks", {"page_id": page_id, "from_index": 0, "limit": 3})
        else:
            results.append({"tool": "get_page_outline", "status": "skipped", "reason": "no page_id"})
            print("  SKIP get_page_outline (no page_id)")

        if chunk_id:
            await run("get_chunk", {"chunk_id": chunk_id})
            await run("get_chunks", {"chunk_ids": [chunk_id]})
            await run("get_chunk_next", {"chunk_id": chunk_id, "count": 2})
            await run("get_chunk_prev", {"chunk_id": chunk_id, "count": 2})
            await run("get_chunk_neighbors", {"chunk_id": chunk_id, "count": 1})
            await run("get_context_window", {"chunk_id": chunk_id, "before": 1, "after": 1})
        else:
            for t in ("get_chunk", "get_chunks", "get_chunk_next", "get_chunk_prev",
                      "get_chunk_neighbors", "get_context_window"):
                results.append({"tool": t, "status": "skipped", "reason": "no chunk_id"})
                print(f"  SKIP {t} (no chunk_id)")

    ok = sum(1 for r in results if r["status"] == "ok")
    fail = sum(1 for r in results if r["status"] == "error")
    skip = sum(1 for r in results if r["status"] == "skipped")
    print(f"\nSummary: {ok} ok, {fail} failed, {skip} skipped")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

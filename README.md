# OpenClaw Docs MCP

MCP RAG server for [OpenClaw documentation](https://docs.openclaw.ai). Indexes English docs into PostgreSQL with pgvector and exposes hybrid search tools over HTTP via [FastMCP](https://gofastmcp.com).

## Features

- Hybrid search (pgvector + full-text) across ~721 English documentation pages
- 13 MCP tools: search, get_chunk, next/prev navigation, page outline, stats
- HTTP transport with API key authentication
- Incremental sync via content hash
- systemd service + optional daily sync timer

## Requirements

- Python 3.11+
- PostgreSQL 15+ with [pgvector](https://github.com/pgvector/pgvector) extension
- OpenAI API key (for `text-embedding-3-small`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp config.env.example config.env
# Edit config.env: DATABASE_URL, OPENAI_API_KEY, API_KEY

# Create empty database, then run migrations
alembic upgrade head

# Index documentation (crawl sitemap, ~5-15 min)
openclaw-docs-mcp ingest --full

# Start MCP server
openclaw-docs-mcp serve
```

Server runs at `http://0.0.0.0:8000/mcp` (configurable via `MCP_PORT` in config.env).

## MCP Tools

All search tools note: **write queries in English for best results** (docs indexed in English only).

| Tool | Description |
|------|-------------|
| `search` | Hybrid semantic + full-text search |
| `search_in_page` | Search within a single document |
| `lexical_search` | Full-text search only |
| `get_chunk` | Full chunk by ID |
| `get_chunks` | Batch retrieve chunks |
| `get_chunk_next` / `get_chunk_prev` | Navigate document order |
| `get_chunk_neighbors` | Previous + current + next |
| `get_context_window` | Symmetric context around a chunk |
| `get_document_chunks` | Paginate chunks in a document |
| `list_pages` | List indexed pages |
| `get_page_outline` | Headings + chunk IDs |
| `get_stats` | Index statistics |

## Cursor Configuration

**Localhost (same machine):**

```json
{
  "mcpServers": {
    "openclaw-docs": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

**Remote (Cloudflare tunnel):**

```json
{
  "mcpServers": {
    "openclaw-docs": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote@latest",
        "https://your-tunnel.example.com/mcp",
        "--header", "Authorization: Bearer ${OPENCLAW_DOCS_API_KEY}"
      ],
      "env": {
        "OPENCLAW_DOCS_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

## systemd Deployment

```bash
sudo cp deploy/openclaw-docs-mcp.service /etc/systemd/system/
sudo cp deploy/openclaw-docs-mcp-sync.service deploy/openclaw-docs-mcp-sync.timer /etc/systemd/system/
sudo cp deploy/sync-wrapper.sh /home/miguelcc06/openclaw-docs-mcp/deploy/
chmod +x deploy/sync-wrapper.sh

sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-docs-mcp
sudo systemctl enable --now openclaw-docs-mcp-sync.timer
```

Set `SYNC_ENABLED=true` and `SYNC_SCHEDULE=daily` in `config.env`.

## CLI Commands

```bash
openclaw-docs-mcp serve          # Start HTTP MCP server
openclaw-docs-mcp ingest --full  # Full re-index
openclaw-docs-mcp sync           # Incremental sync
openclaw-docs-mcp stats          # Index statistics
alembic upgrade head             # Apply DB migrations
```

## License

MIT

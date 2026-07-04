<div align="center">
  <img src="./assets/architecture_banner.png" width="100%" alt="OpenClaw Docs MCP Architecture Banner" style="border-radius: 10px;" />

  <br />
  <br />

  # 📖 OpenClaw Docs MCP

  **An MCP RAG server providing powerful hybrid search over OpenClaw documentation**

  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
    <img src="https://img.shields.io/badge/pgvector-Enabled-8B0000?style=for-the-badge" alt="pgvector" />
    <img src="https://img.shields.io/badge/FastMCP-Supported-00E5FF?style=for-the-badge&logo=fastapi&logoColor=black" alt="FastMCP" />
  </p>
</div>

---

> **OpenClaw Docs MCP** indexes the [OpenClaw documentation](https://docs.openclaw.ai) into PostgreSQL using **pgvector** and exposes powerful hybrid search tools via **HTTP** using [FastMCP](https://gofastmcp.com).

## ✨ Key Features

*   🧠 **Hybrid Search:** Combines semantic (pgvector) and full-text search across ~721 English documentation pages.
*   🛠️ **13 MCP Tools:** Fully equipped with search, `get_chunk`, navigation (next/prev), page outlines, and index statistics.
*   ⚡ **HTTP Transport:** Exposed securely over HTTP with API key authentication.
*   🔄 **Incremental Sync:** Smart content-hash syncing to avoid redundant updates.
*   ⚙️ **Production Ready:** Includes `systemd` service files and an optional daily sync timer.

## 📋 Requirements

*   **Python:** `3.11+`
*   **Database:** `PostgreSQL 15+` with the [pgvector](https://github.com/pgvector/pgvector) extension.
*   **AI:** OpenAI API key (for embedding generation using `text-embedding-3-small`).

---

## 🚀 Setup & Installation

### 1. Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configuration
```bash
cp config.env.example config.env
# Edit config.env with: DATABASE_URL, OPENAI_API_KEY, API_KEY
```

### 3. Database & Ingestion
```bash
# Run migrations (ensure your database exists)
alembic upgrade head

# Crawl sitemap and index content (~5-15 min)
openclaw-docs-mcp ingest --full
```

### 4. Run the Server
```bash
openclaw-docs-mcp serve
```
> 📍 Server runs at `http://0.0.0.0:8000/mcp` (configurable via `MCP_PORT`).

---

## 🧰 MCP Tools Available

> ⚠️ **Note:** Write all queries in **English** for the best results (docs are indexed in English only).

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

---

## 🔌 Cursor Configuration

### 🏠 Localhost (same machine)
```json
{
  "mcpServers": {
    "openclaw-docs": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "***"
      }
    }
  }
}
```

### 🌍 Remote (e.g., Cloudflare tunnel)
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

---

## ⚙️ systemd Deployment

For automated management and background syncing:

```bash
sudo cp deploy/openclaw-docs-mcp.service /etc/systemd/system/
sudo cp deploy/openclaw-docs-mcp-sync.service deploy/openclaw-docs-mcp-sync.timer /etc/systemd/system/
sudo cp deploy/sync-wrapper.sh /home/miguelcc06/openclaw-docs-mcp/deploy/
chmod +x deploy/sync-wrapper.sh

sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-docs-mcp
sudo systemctl enable --now openclaw-docs-mcp-sync.timer
```
> 💡 **Tip:** Set `SYNC_ENABLED=true` and `SYNC_SCHEDULE=daily` in `config.env`.

---

## 💻 CLI Commands Quick Reference

```bash
openclaw-docs-mcp serve          # Start HTTP MCP server
openclaw-docs-mcp ingest --full  # Full re-index
openclaw-docs-mcp sync           # Incremental sync
openclaw-docs-mcp stats          # Index statistics
alembic upgrade head             # Apply DB migrations
```

---
<div align="center">
  <i>Built to make AI smarter about its own documentation.</i><br>
  <b>License: MIT</b>
</div>
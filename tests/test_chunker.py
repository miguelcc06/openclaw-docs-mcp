import pytest

from openclaw_docs_mcp.ingestion.chunker import chunk_markdown


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from openclaw_docs_mcp.config import get_settings

    get_settings.cache_clear()


SAMPLE_MD = """---
title: Gateway Configuration
---

# Gateway Configuration

Configure the OpenClaw gateway.

## Authentication

Use API keys for auth.

## Tokens

Token settings go here.
"""


def test_chunk_markdown_splits_by_headers():
    chunks = chunk_markdown(SAMPLE_MD)
    assert len(chunks) >= 2
    assert any("Authentication" in " > ".join(c.heading_path) for c in chunks)


def test_chunk_markdown_assigns_tokens():
    chunks = chunk_markdown(SAMPLE_MD)
    assert all(c.token_count > 0 for c in chunks)

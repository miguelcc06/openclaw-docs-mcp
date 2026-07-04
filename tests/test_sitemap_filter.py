import pytest

from openclaw_docs_mcp.ingestion.sitemap import filter_english_urls, is_redirect_page, url_to_path


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from openclaw_docs_mcp.config import get_settings

    get_settings.cache_clear()


def test_filter_english_urls_excludes_locales():
    urls = [
        "https://docs.openclaw.ai/gateway/configuration",
        "https://docs.openclaw.ai/es/gateway/configuration",
        "https://docs.openclaw.ai/zh-CN/start/getting-started",
        "https://docs.openclaw.ai/start/getting-started.md",
    ]
    filtered = filter_english_urls(urls)
    assert "https://docs.openclaw.ai/gateway/configuration" in filtered
    assert "https://docs.openclaw.ai/es/gateway/configuration" not in filtered
    assert "https://docs.openclaw.ai/zh-CN/start/getting-started" not in filtered
    assert "https://docs.openclaw.ai/start/getting-started.md" not in filtered


def test_url_to_path():
    assert url_to_path("https://docs.openclaw.ai/gateway/configuration") == "/gateway/configuration"


def test_is_redirect_page():
    assert is_redirect_page("Redirect to /gateway/configuration")
    assert not is_redirect_page("# Real Page\n\nContent here.")

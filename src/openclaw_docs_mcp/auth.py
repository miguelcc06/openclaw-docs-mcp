from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext

from openclaw_docs_mcp.config import get_settings


class ApiKeyMiddleware(Middleware):
    """Validate API key on every HTTP request (X-API-Key or Bearer token)."""

    async def on_request(self, context: MiddlewareContext, call_next):
        settings = get_settings()
        headers = get_http_headers() or {}
        token = self._extract_token(headers)
        if not token or token != settings.api_key:
            raise ToolError("Unauthorized: invalid or missing API key")
        return await call_next(context)

    @staticmethod
    def _extract_token(headers: dict[str, str]) -> str | None:
        if key := headers.get("x-api-key"):
            return key
        auth = headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return None

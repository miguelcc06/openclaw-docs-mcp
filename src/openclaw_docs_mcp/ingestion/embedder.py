import asyncio

from openai import AsyncOpenAI

from openclaw_docs_mcp.config import get_settings

BATCH_SIZE = 64
MAX_RETRIES = 3


class OpenAIEmbedder:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            embeddings = await self._embed_batch(batch)
            results.extend(embeddings)
        return results

    async def embed_query(self, query: str) -> list[float]:
        result = await self.embed_texts([query])
        return result[0]

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.embeddings.create(
                    model=self.model,
                    input=texts,
                    dimensions=settings.embedding_dimensions,
                )
                return [item.embedding for item in response.data]
            except Exception:
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2**attempt)
        return []

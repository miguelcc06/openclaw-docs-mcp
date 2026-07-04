from fastmcp.exceptions import ToolError


class DocsMCPError(ToolError):
    kind: str = "error"

    def __init__(self, message: str, kind: str | None = None):
        self.kind = kind or self.kind
        super().__init__(message)


class ChunkNotFoundError(DocsMCPError):
    kind = "chunk_not_found"


class PageNotFoundError(DocsMCPError):
    kind = "page_not_found"


class EmbeddingModelMismatchError(DocsMCPError):
    kind = "embedding_model_mismatch"

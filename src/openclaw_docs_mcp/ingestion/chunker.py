import re
from dataclasses import dataclass, field

from openclaw_docs_mcp.config import get_settings
from openclaw_docs_mcp.utils.tokens import count_tokens

HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
CODE_FENCE_RE = re.compile(r"^```", re.MULTILINE)


@dataclass
class ChunkData:
    content: str
    heading_path: list[str] = field(default_factory=list)
    token_count: int = 0
    start_line: int = 1
    end_line: int = 1


def chunk_markdown(content: str) -> list[ChunkData]:
    settings = get_settings()
    sections = _split_by_headers(content)
    chunks: list[ChunkData] = []
    for section in sections:
        chunks.extend(_split_section(section, settings.chunk_size, settings.chunk_overlap, settings.chunk_min_size))
    for idx, chunk in enumerate(chunks):
        chunk.token_count = count_tokens(chunk.content)
        if chunk.token_count < settings.chunk_min_size and idx > 0:
            prev = chunks[idx - 1]
            prev.content = prev.content.rstrip() + "\n\n" + chunk.content
            prev.token_count = count_tokens(prev.content)
            chunk.content = ""
    return [c for c in chunks if c.content.strip()]


def _split_by_headers(content: str) -> list[ChunkData]:
    lines = content.splitlines()
    sections: list[ChunkData] = []
    current_lines: list[str] = []
    heading_path: list[str] = []
    start_line = 1

    for i, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match and current_lines:
            sections.append(
                ChunkData(
                    content="\n".join(current_lines).strip(),
                    heading_path=heading_path.copy(),
                    start_line=start_line,
                    end_line=i - 1,
                )
            )
            current_lines = []
            start_line = i

        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_path = heading_path[: level - 1] + [title]

        current_lines.append(line)

    if current_lines:
        sections.append(
            ChunkData(
                content="\n".join(current_lines).strip(),
                heading_path=heading_path.copy(),
                start_line=start_line,
                end_line=len(lines),
            )
        )

    return [s for s in sections if s.content.strip()]


def _split_section(section: ChunkData, chunk_size: int, overlap: int, min_size: int) -> list[ChunkData]:
    if count_tokens(section.content) <= chunk_size:
        return [section]

    paragraphs = _preserve_code_blocks(section.content)
    chunks: list[ChunkData] = []
    current = ""
    current_tokens = 0

    for para in paragraphs:
        para_tokens = count_tokens(para)
        if para_tokens > chunk_size:
            if current.strip():
                chunks.append(_clone_section(section, current))
                current = ""
                current_tokens = 0
            chunks.extend(_split_large_paragraph(section, para, chunk_size, overlap))
            continue

        if current_tokens + para_tokens > chunk_size and current.strip():
            chunks.append(_clone_section(section, current))
            overlap_text = _tail_overlap(current, overlap)
            current = overlap_text + ("\n\n" if overlap_text else "") + para
            current_tokens = count_tokens(current)
        else:
            current = (current + "\n\n" + para).strip() if current else para
            current_tokens = count_tokens(current)

    if current.strip():
        chunks.append(_clone_section(section, current))

    return chunks or [section]


def _preserve_code_blocks(content: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    in_fence = False
    for line in content.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        current.append(line)
        if not in_fence and not line.strip():
            parts.append("\n".join(current).strip())
            current = []
    if current:
        parts.append("\n".join(current).strip())
    return [p for p in parts if p]


def _split_large_paragraph(section: ChunkData, text: str, chunk_size: int, overlap: int) -> list[ChunkData]:
    words = text.split()
    chunks: list[ChunkData] = []
    current: list[str] = []
    current_tokens = 0
    for word in words:
        word_tokens = count_tokens(word + " ")
        if current_tokens + word_tokens > chunk_size and current:
            chunk_text = " ".join(current)
            chunks.append(_clone_section(section, chunk_text))
            overlap_words = chunk_text.split()[-max(overlap // 4, 1) :]
            current = overlap_words + [word]
            current_tokens = count_tokens(" ".join(current))
        else:
            current.append(word)
            current_tokens += word_tokens
    if current:
        chunks.append(_clone_section(section, " ".join(current)))
    return chunks


def _tail_overlap(text: str, overlap_tokens: int) -> str:
    words = text.split()
    tail = words[-max(overlap_tokens // 4, 1) :]
    return " ".join(tail)


def _clone_section(section: ChunkData, content: str) -> ChunkData:
    return ChunkData(
        content=content.strip(),
        heading_path=section.heading_path.copy(),
        start_line=section.start_line,
        end_line=section.end_line,
    )

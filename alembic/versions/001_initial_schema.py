"""Initial schema with pgvector and hybrid search functions.

Revision ID: 001
Revises:
Create Date: 2026-07-04
"""

from typing import Sequence, Union

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE documents (
            id UUID PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            title TEXT,
            source_url TEXT,
            content_hash TEXT NOT NULL,
            token_count INT DEFAULT 0,
            chunk_count INT DEFAULT 0,
            metadata JSONB DEFAULT '{}',
            indexed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE ingest_runs (
            id UUID PRIMARY KEY,
            started_at TIMESTAMPTZ NOT NULL,
            finished_at TIMESTAMPTZ,
            pages_processed INT DEFAULT 0,
            pages_updated INT DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'running',
            full_run BOOLEAN DEFAULT false,
            error_log TEXT
        )
        """
    )

    op.execute(
        """
        CREATE TABLE chunks (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INT NOT NULL,
            content TEXT NOT NULL,
            token_count INT NOT NULL,
            heading_path TEXT[] DEFAULT '{}',
            embedding vector(1536),
            embedding_model TEXT,
            content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
            start_line INT,
            end_line INT,
            prev_id UUID REFERENCES chunks(id) ON DELETE SET NULL,
            next_id UUID REFERENCES chunks(id) ON DELETE SET NULL,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (document_id, chunk_index)
        )
        """
    )

    op.execute("CREATE INDEX chunks_document_idx ON chunks(document_id, chunk_index)")
    op.execute(
        """
        CREATE INDEX chunks_embedding_hnsw ON chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )
    op.execute("CREATE INDEX chunks_content_fts ON chunks USING GIN (content_tsv)")
    op.execute("CREATE INDEX documents_path_idx ON documents(path)")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION search_chunks(
            query_embedding vector(1536),
            match_count int DEFAULT 8,
            filter_document_id uuid DEFAULT NULL,
            min_similarity float DEFAULT 0.0
        )
        RETURNS TABLE (
            id uuid,
            document_id uuid,
            content text,
            heading_path text[],
            chunk_index int,
            token_count int,
            prev_id uuid,
            next_id uuid,
            page_path text,
            similarity float
        ) AS $$
            SELECT
                c.id,
                c.document_id,
                c.content,
                c.heading_path,
                c.chunk_index,
                c.token_count,
                c.prev_id,
                c.next_id,
                d.path,
                1 - (c.embedding <=> query_embedding) AS similarity
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.embedding IS NOT NULL
              AND (filter_document_id IS NULL OR c.document_id = filter_document_id)
              AND (1 - (c.embedding <=> query_embedding)) >= min_similarity
            ORDER BY c.embedding <=> query_embedding
            LIMIT match_count;
        $$ LANGUAGE sql STABLE;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION hybrid_search(
            query_text text,
            query_embedding vector(1536),
            match_count int DEFAULT 8,
            min_similarity float DEFAULT 0.0,
            filter_document_id uuid DEFAULT NULL
        )
        RETURNS TABLE (
            id uuid,
            document_id uuid,
            content text,
            heading_path text[],
            chunk_index int,
            token_count int,
            prev_id uuid,
            next_id uuid,
            page_path text,
            similarity float
        ) AS $$
            WITH vector_results AS (
                SELECT c.id, 1 - (c.embedding <=> query_embedding) AS score,
                       ROW_NUMBER() OVER (ORDER BY c.embedding <=> query_embedding) AS rank
                FROM chunks c
                WHERE c.embedding IS NOT NULL
                  AND (filter_document_id IS NULL OR c.document_id = filter_document_id)
            ),
            text_results AS (
                SELECT c.id, ts_rank(c.content_tsv, plainto_tsquery('english', query_text)) AS score,
                       ROW_NUMBER() OVER (
                           ORDER BY ts_rank(c.content_tsv, plainto_tsquery('english', query_text)) DESC
                       ) AS rank
                FROM chunks c
                WHERE c.content_tsv @@ plainto_tsquery('english', query_text)
                  AND (filter_document_id IS NULL OR c.document_id = filter_document_id)
            ),
            combined AS (
                SELECT
                    COALESCE(v.id, t.id) AS id,
                    COALESCE(1.0 / (60 + v.rank), 0) + COALESCE(1.0 / (60 + t.rank), 0) AS rrf_score
                FROM vector_results v
                FULL OUTER JOIN text_results t ON v.id = t.id
            )
            SELECT
                c.id,
                c.document_id,
                c.content,
                c.heading_path,
                c.chunk_index,
                c.token_count,
                c.prev_id,
                c.next_id,
                d.path,
                cb.rrf_score AS similarity
            FROM combined cb
            JOIN chunks c ON c.id = cb.id
            JOIN documents d ON d.id = c.document_id
            WHERE cb.rrf_score >= min_similarity
            ORDER BY cb.rrf_score DESC
            LIMIT match_count;
        $$ LANGUAGE sql STABLE;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS hybrid_search(text, vector, int, float, uuid)")
    op.execute("DROP FUNCTION IF EXISTS search_chunks(vector, int, uuid, float)")
    op.execute("DROP TABLE IF EXISTS chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS ingest_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS documents CASCADE")
    op.execute("DROP EXTENSION IF EXISTS vector")

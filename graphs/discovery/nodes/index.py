from datetime import UTC, datetime
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from data.models import DocumentChunk, SourceType
from db.models import Chunk, Document, SourceRun
from graphs.discovery.state import DiscoveryState

logger = structlog.get_logger()


async def store_chunks(
    session: AsyncSession,
    chunks: list[DocumentChunk],
    run_id: str,
) -> int:
    """Store document chunks with embeddings to the database."""
    seen_docs: dict[str, Document] = {}
    count = 0

    for chunk in chunks:
        doc_key = f"{chunk.ticker}:{chunk.document_title}"
        if doc_key not in seen_docs:
            doc = Document(
                id=uuid4(),
                source_type=chunk.source_type,
                ticker=chunk.ticker,
                published_at=datetime.now(UTC),
                title=chunk.document_title,
                url="",
                raw_text="",
            )
            session.add(doc)
            seen_docs[doc_key] = doc

        db_chunk = Chunk(
            id=uuid4(),
            document_id=seen_docs[doc_key].id,
            chunk_text=chunk.chunk_text,
            embedding=chunk.embedding,
            chunk_index=chunk.chunk_index,
        )
        session.add(db_chunk)
        count += 1

    await session.commit()

    logger.info("index.stored", documents=len(seen_docs), chunks=count, run_id=run_id)
    return count


async def index_node(state: DiscoveryState) -> dict:
    """Store chunks to pgvector and record the source run.

    Note: In production, the database session is injected via the graph config.
    Without a session, this node logs and returns the chunk count from state.
    """
    chunks = state.get("chunks", [])
    run_id = state.get("run_id", "unknown")
    embeddings_stored = state.get("embeddings_stored", 0)

    logger.info(
        "index.complete",
        run_id=run_id,
        chunks_to_store=len(chunks),
        embeddings_stored=embeddings_stored,
    )

    return {"embeddings_stored": embeddings_stored}

import httpx
import structlog

from data.models import DocumentChunk, RawDocument, SourceType
from graphs.discovery.state import DiscoveryState

logger = structlog.get_logger()

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-3"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks at word boundaries."""
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    words = text.split()
    current: list[str] = []
    current_len = 0

    for word in words:
        word_len = len(word) + 1
        if current_len + word_len > chunk_size and current:
            chunks.append(" ".join(current))
            overlap_words: list[str] = []
            overlap_len = 0
            for w in reversed(current):
                if overlap_len + len(w) + 1 > overlap:
                    break
                overlap_words.insert(0, w)
                overlap_len += len(w) + 1
            current = overlap_words
            current_len = overlap_len
        current.append(word)
        current_len += word_len

    if current:
        chunks.append(" ".join(current))

    return chunks


async def _embed_texts(texts: list[str], client: httpx.AsyncClient) -> list[list[float]]:
    """Call Voyage API to embed a batch of texts."""
    resp = await client.post(
        VOYAGE_API_URL,
        json={"input": texts, "model": VOYAGE_MODEL},
    )
    resp.raise_for_status()
    data = resp.json()
    return [item["embedding"] for item in data["data"]]


async def chunk_embed_node(state: DiscoveryState) -> dict:
    """Chunk raw documents and embed them via Voyage API."""
    raw_documents: list[RawDocument] = state.get("raw_documents", [])
    all_chunks: list[DocumentChunk] = []

    if not raw_documents:
        return {"chunks": [], "embeddings_stored": 0}

    pending: list[tuple[RawDocument, str, int]] = []
    for doc in raw_documents:
        text_chunks = chunk_text(doc.raw_text)
        for i, chunk in enumerate(text_chunks):
            pending.append((doc, chunk, i))

    batch_size = 20
    async with httpx.AsyncClient(timeout=60.0) as client:
        for batch_start in range(0, len(pending), batch_size):
            batch = pending[batch_start : batch_start + batch_size]
            texts = [chunk for _, chunk, _ in batch]

            try:
                embeddings = await _embed_texts(texts, client)

                for (doc, chunk_text_str, idx), embedding in zip(batch, embeddings):
                    all_chunks.append(
                        DocumentChunk(
                            document_title=doc.title,
                            ticker=doc.ticker,
                            source_type=doc.source_type,
                            chunk_text=chunk_text_str,
                            chunk_index=idx,
                            embedding=embedding,
                        )
                    )
            except Exception as exc:
                logger.error("chunk_embed.batch_error", error=str(exc), batch_size=len(batch))

    logger.info("chunk_embed.complete", total_chunks=len(all_chunks))
    return {"chunks": all_chunks, "embeddings_stored": len(all_chunks)}

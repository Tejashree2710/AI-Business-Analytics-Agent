
from backend.database import SessionLocal
from backend.models import DocumentChunk
from backend.services.embedding_service import generate_embedding


def search_similar_chunks(
    query: str,
    session_id: int,
    top_k: int = 5
):
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    if not session_id:
        raise ValueError("Session ID is required")

    db = SessionLocal()

    try:
        query_embedding = generate_embedding(query)

        results = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.session_id == session_id)
            .order_by(
                DocumentChunk.embedding.cosine_distance(query_embedding)
            )
            .limit(top_k)
            .all()
        )

        return [
            {
                "filename": result.filename,
                "content": result.content,
                "chunk_index": result.chunk_index
            }
            for result in results
        ]

    finally:
        db.close()

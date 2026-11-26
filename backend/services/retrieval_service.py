
from backend.database import SessionLocal
from backend.models import DocumentChunk
from backend.services.embedding_service import generate_embedding


def search_similar_chunks(query: str, top_k: int = 5):
    db = SessionLocal()

    try:
        query_embedding = generate_embedding(query)

        results = (
            db.query(DocumentChunk)
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

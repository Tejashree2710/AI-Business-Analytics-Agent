
from backend.database import SessionLocal
from backend.models import DocumentChunk
from backend.services.embedding_service import generate_embedding


def store_document_chunks(chunks: list[dict]):
    db = SessionLocal()

    try:
        saved_count = 0

        for chunk in chunks:
            embedding = generate_embedding(chunk["content"])

            document_chunk = DocumentChunk(
                filename=chunk["filename"],
                file_type=chunk["file_type"],
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                embedding=embedding
            )

            db.add(document_chunk)
            saved_count += 1

        db.commit()

        return {
            "message": "Document chunks stored successfully",
            "saved_chunks": saved_count
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

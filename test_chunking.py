
from backend.services.chunking_service import create_chunks

sample_data = {
    "file_type": "document",
    "text": """
    Business Analytics helps organizations make better decisions.

    Data visualization helps identify trends and patterns.

    Machine learning can help predict future business outcomes.
    """
}

chunks = create_chunks(sample_data, "sample_document.txt")

print("Total chunks:", len(chunks))

for chunk in chunks:
    print("\nChunk:", chunk["chunk_index"])
    print(chunk["content"])

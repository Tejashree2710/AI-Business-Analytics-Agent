
from backend.services.retrieval_service import search_similar_chunks

query = "How does machine learning help businesses?"

results = search_similar_chunks(query)

print("Retrieved chunks:", len(results))

for result in results:
    print("\nFilename:", result["filename"])
    print("Content:", result["content"])

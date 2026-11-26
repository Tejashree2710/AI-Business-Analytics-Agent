
from backend.services.embedding_service import generate_embedding

sample_text = """
Business Analytics helps organizations make better decisions.
Data visualization helps identify trends and patterns.
Machine learning can help predict future business outcomes.
"""

embedding = generate_embedding(sample_text)

print("SUCCESS!")
print("Embedding dimensions:", len(embedding))
print("First 5 values:", embedding[:5])

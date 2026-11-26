
from backend.services.retrieval_service import search_similar_chunks
from backend.services.gemini_service import generate_ai_response


def answer_question(question: str):
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    retrieved_chunks = search_similar_chunks(question, top_k=5)

    if not retrieved_chunks:
        return {
            "question": question,
            "answer": "I could not find relevant information in the uploaded documents.",
            "sources": []
        }

    context = "\n\n".join(
        chunk["content"] for chunk in retrieved_chunks
    )

    prompt = f"""
You are an AI Business Analytics Assistant.

Answer the user's question using only the context provided below.

If the answer is not available in the context, clearly say that
the uploaded documents do not contain enough information.

Do not invent facts or figures.

Context:
{context}

User Question:
{question}

Provide a clear and useful answer.
"""

    answer = generate_ai_response(prompt)

    return {
        "question": question,
        "answer": answer,
        "sources": [
            {
                "filename": chunk["filename"],
                "chunk_index": chunk["chunk_index"]
            }
            for chunk in retrieved_chunks
        ]
    }


import json
import re

from backend.services.retrieval_service import search_similar_chunks
from backend.services.dataset_query_service import answer_dataset_question
from backend.services.gemini_service import generate_ai_response


def has_usable_dataset_results(dataset_result):
    if not isinstance(dataset_result, dict):
        return False

    results = dataset_result.get("results")

    if results is None:
        return False

    if isinstance(results, (list, dict, str)):
        return len(results) > 0

    return True


def clean_json_response(response):
    response = response.strip()

    response = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        response,
        flags=re.IGNORECASE
    )

    return response.strip()


def build_document_source(chunk):
    source = {
        "filename": chunk.get("filename"),
        "chunk_index": chunk.get("chunk_index"),
        "type": "document"
    }

    if chunk.get("page_number") is not None:
        source["page_number"] = chunk["page_number"]

    if chunk.get("table_number") is not None:
        source["table_number"] = chunk["table_number"]

    return source


def build_dataset_source(dataset_result):
    source_metadata = dataset_result.get("source") or {}

    source = {
        "filename": dataset_result.get("filename"),
        "type": "dataset"
    }

    if source_metadata.get("source_type"):
        source["source_type"] = source_metadata["source_type"]

    if source_metadata.get("page_number") is not None:
        source["page_number"] = source_metadata["page_number"]

    if source_metadata.get("table_number") is not None:
        source["table_number"] = source_metadata["table_number"]

    return source


def answer_question(question: str, session_id: int):

    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    if not session_id:
        raise ValueError("Session ID is required")

    # Retrieve relevant document information
    retrieved_chunks = search_similar_chunks(
        question,
        session_id=session_id,
        top_k=5
    )

    if not isinstance(retrieved_chunks, list):
        retrieved_chunks = []

    # Prepare document evidence with unique reference IDs
    document_evidence = []

    for index, chunk in enumerate(retrieved_chunks):
        content = chunk.get("content", "")

        if not content or not content.strip():
            continue

        document_evidence.append({
            "evidence_id": f"D{index}",
            "filename": chunk.get("filename"),
            "chunk_index": chunk.get("chunk_index"),
            "page_number": chunk.get("page_number"),
            "table_number": chunk.get("table_number"),
            "content": content
        })

    # Execute dataset analysis
    # Dataset analysis should not prevent document-only questions
    try:
        dataset_result = answer_dataset_question(
            question=question,
            session_id=session_id
        )
    except (ValueError, KeyError, TypeError):
        dataset_result = None

    # Ignore empty or unusable dataset results
    if not has_usable_dataset_results(dataset_result):
        dataset_result = None

    document_context = json.dumps(
        document_evidence,
        indent=2,
        ensure_ascii=False,
        default=str
    ) if document_evidence else "No document evidence retrieved."

    dataset_context = json.dumps(
        dataset_result,
        indent=2,
        ensure_ascii=False,
        default=str
    ) if dataset_result else "No usable dataset results available."

    # Check whether evidence is available
    if not document_evidence and not dataset_result:
        return {
            "question": question,
            "answer": (
                "I could not find relevant information in the files "
                "uploaded to this chat session."
            ),
            "sources": []
        }

    prompt = f"""
You are an AI Business Analytics and Decision Support Assistant.

Answer the user's question using only the supplied evidence.

DOCUMENT EVIDENCE:
{document_context}

CALCULATED DATASET RESULTS:
{dataset_context}

IMPORTANT ANSWERING RULES:

1. Use calculated dataset results for numerical calculations.
2. Do not invent, estimate, or recalculate numerical results.
3. Use document evidence for explanations, definitions, facts and values
   stated in documents.
4. Combine document and dataset evidence when both are needed.
5. Do not assume that every supplied document chunk is relevant.
6. Do not assume that dataset results are relevant to every question.
7. If the evidence does not answer the question, clearly explain what
   information is missing.
8. Select only evidence that directly supports the answer.
9. Do not cite evidence that was merely retrieved but not used.
10. Preserve the supplied numerical values and units.
11. Do not invent page numbers, filenames or evidence IDs.

SOURCE SELECTION RULES:

1. Document evidence IDs are the IDs beginning with D.
2. Select only document evidence IDs that actually support your answer.
3. Set dataset_evidence_used to true only when the calculated dataset
   results actually contribute to the answer.
4. If dataset results are unavailable or empty, set it to false.
5. If the answer uses only document evidence, select no dataset evidence.
6. If the answer uses only dataset evidence, select no document evidence.
7. Do not select sources simply because they are available.

Return ONLY valid JSON in this exact structure:

{{
    "answer": "Your complete answer here",
    "document_evidence_ids": ["D0"],
    "dataset_evidence_used": false
}}

USER QUESTION:
{question}
"""

    response = generate_ai_response(prompt)

    # Parse Gemini's structured response
    try:
        parsed_response = json.loads(
            clean_json_response(response)
        )

        if not isinstance(parsed_response, dict):
            raise ValueError("Invalid response structure")

        answer = parsed_response.get("answer")

        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Missing answer")

        selected_document_ids = parsed_response.get(
            "document_evidence_ids",
            []
        )

        if not isinstance(selected_document_ids, list):
            selected_document_ids = []

        dataset_evidence_used = (
            parsed_response.get("dataset_evidence_used") is True
        )

    except (json.JSONDecodeError, ValueError, TypeError):
        # Do not claim sources when structured source selection fails
        answer = response.strip()
        selected_document_ids = []
        dataset_evidence_used = False

    # Validate selected document evidence IDs
    available_evidence = {
        item["evidence_id"]: item
        for item in document_evidence
    }

    valid_document_ids = set(selected_document_ids)

    sources = []

    for evidence_id in valid_document_ids:
        evidence = available_evidence.get(evidence_id)

        if evidence:
            source = build_document_source(evidence)

            if source["filename"] and source not in sources:
                sources.append(source)

    # Include dataset source only if Gemini used it
    # and usable calculated results actually exist
    if dataset_evidence_used and dataset_result:
        dataset_source = build_dataset_source(dataset_result)

        if dataset_source["filename"] and dataset_source not in sources:
            sources.append(dataset_source)

    return {
        "question": question,
        "answer": answer,
        "sources": sources
    }

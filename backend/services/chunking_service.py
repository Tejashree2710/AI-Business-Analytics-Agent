
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)


def create_chunks(extracted_data: dict, filename: str):
    file_type = extracted_data.get("file_type")

    if file_type == "document":
        content = extracted_data.get("text", "")

    elif file_type == "tabular":
        content = json.dumps(
            extracted_data.get("data", []),
            ensure_ascii=False,
            indent=2
        )

    else:
        raise ValueError("Unsupported extracted data type")

    if not content.strip():
        raise ValueError("No content available for chunking")

    chunks = text_splitter.split_text(content)

    return [
        {
            "filename": filename,
            "file_type": file_type,
            "chunk_index": index,
            "content": chunk
        }
        for index, chunk in enumerate(chunks)
    ]

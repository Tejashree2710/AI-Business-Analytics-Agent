
from langchain_text_splitters import RecursiveCharacterTextSplitter


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)


def create_chunks(extracted_data: dict, filename: str):
    file_type = extracted_data.get("file_type")

    if file_type != "document":
        return []

    content = extracted_data.get("text", "")

    if not content or not content.strip():
        raise ValueError("No text content available for chunking")

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

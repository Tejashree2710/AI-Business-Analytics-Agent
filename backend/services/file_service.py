
from pathlib import Path

import pandas as pd
from pypdf import PdfReader
from docx import Document

UPLOAD_DIR = Path("uploads")

ALLOWED_EXTENSIONS = {
    ".csv",
    ".xlsx",
    ".xls",
    ".pdf",
    ".docx",
    ".txt"
}


def extract_file_content(file_path: Path):
    extension = file_path.suffix.lower()

    if extension == ".csv":
        df = pd.read_csv(file_path)

        clean_df = df.head(100).astype(object)
        clean_df = clean_df.where(pd.notna(clean_df), None)

        return {
            "file_type": "tabular",
            "columns": df.columns.tolist(),
            "row_count": len(df),
            "data": clean_df.to_dict(orient="records")
        }

    if extension in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)

        clean_df = df.head(100).astype(object)
        clean_df = clean_df.where(pd.notna(clean_df), None)

        return {
            "file_type": "tabular",
            "columns": df.columns.tolist(),
            "row_count": len(df),
            "data": clean_df.to_dict(orient="records")
        }

    if extension == ".pdf":
        reader = PdfReader(str(file_path))

        text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

        return {
            "file_type": "document",
            "page_count": len(reader.pages),
            "text": text
        }

    if extension == ".docx":
        document = Document(file_path)

        text = "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

        return {
            "file_type": "document",
            "text": text
        }

    if extension == ".txt":
        text = file_path.read_text(encoding="utf-8")

        return {
            "file_type": "document",
            "text": text
        }

    raise ValueError("Unsupported file format")

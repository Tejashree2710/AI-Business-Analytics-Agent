
from pathlib import Path

import pandas as pd
import pdfplumber
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


def clean_dataframe(df):
    clean_df = df.astype(object)
    clean_df = clean_df.where(pd.notna(clean_df), None)
    return clean_df


def extract_pdf_content(file_path: Path):
    reader = PdfReader(str(file_path))

    pages = []
    page_texts = []

    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""

            pages.append({
                "page_number": page_number,
                "text": text
            })

            if text.strip():
                page_texts.append(
                    f"[Page {page_number}]\n{text}"
                )

        tables = []

        for page_number, page in enumerate(pdf.pages, start=1):
            extracted_tables = page.extract_tables() or []

            for table_index, table in enumerate(
                extracted_tables,
                start=1
            ):
                if not table or len(table) < 2:
                    continue

                headers = table[0]

                columns = []
                for column_index, header in enumerate(headers):
                    column_name = (
                        str(header).strip()
                        if header is not None and str(header).strip()
                        else f"Column {column_index + 1}"
                    )
                    columns.append(column_name)

                rows = []

                for row in table[1:]:
                    if not row:
                        continue

                    cleaned_row = list(row[:len(columns)])

                    while len(cleaned_row) < len(columns):
                        cleaned_row.append(None)

                    cleaned_row = [
                        str(value).strip() if value is not None else None
                        for value in cleaned_row
                    ]

                    if any(value is not None for value in cleaned_row):
                        rows.append(cleaned_row)

                if rows:
                    df = pd.DataFrame(rows, columns=columns)
                    df = clean_dataframe(df)

                    tables.append({
                        "page_number": page_number,
                        "table_index": table_index,
                        "columns": columns,
                        "row_count": len(df),
                        "data": df.to_dict(orient="records")
                    })

    return {
        "file_type": "document",
        "page_count": len(reader.pages),
        "text": "\n\n".join(page_texts),
        "pages": pages,
        "tables": tables
    }


def extract_file_content(file_path: Path):
    extension = file_path.suffix.lower()

    if extension == ".csv":
        df = pd.read_csv(file_path)
        clean_df = clean_dataframe(df.head(100))

        return {
            "file_type": "tabular",
            "columns": df.columns.tolist(),
            "row_count": len(df),
            "data": clean_df.to_dict(orient="records")
        }

    if extension in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)
        clean_df = clean_dataframe(df.head(100))

        return {
            "file_type": "tabular",
            "columns": df.columns.tolist(),
            "row_count": len(df),
            "data": clean_df.to_dict(orient="records")
        }

    if extension == ".pdf":
        return extract_pdf_content(file_path)

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

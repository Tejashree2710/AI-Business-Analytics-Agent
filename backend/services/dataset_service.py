
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import UploadedFile
from backend.services.analytics_service import generate_analytics
from backend.services.file_service import extract_file_content


UPLOAD_DIR = Path("uploads")

TABULAR_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def load_dataset(file_path: Path) -> pd.DataFrame:
    extension = file_path.suffix.lower()

    if extension == ".csv":
        try:
            return pd.read_csv(file_path)
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding="latin1")

    if extension in [".xlsx", ".xls"]:
        return pd.read_excel(file_path)

    raise ValueError(f"Unsupported dataset format: {extension}")


def get_column_metadata(df: pd.DataFrame) -> dict:
    metadata = {}

    for column in df.columns:
        series = df[column]

        metadata[str(column)] = {
            "data_type": str(series.dtype),
            "missing_values": int(series.isna().sum()),
            "unique_values": int(series.nunique()),
        }

        if pd.api.types.is_numeric_dtype(series):
            metadata[str(column)]["type_category"] = "numeric"

        elif pd.api.types.is_datetime64_any_dtype(series):
            metadata[str(column)]["type_category"] = "datetime"

        else:
            metadata[str(column)]["type_category"] = "categorical"

    return metadata


def get_column_statistics(df: pd.DataFrame) -> dict:
    statistics = {}

    for column in df.columns:
        series = df[column]
        column_stats = {}

        if pd.api.types.is_numeric_dtype(series):
            valid = series.dropna()

            if not valid.empty:
                column_stats = {
                    "count": int(valid.count()),
                    "mean": float(valid.mean()),
                    "median": float(valid.median()),
                    "minimum": float(valid.min()),
                    "maximum": float(valid.max()),
                    "standard_deviation": (
                        float(valid.std()) if len(valid) > 1 else 0
                    ),
                }

                min_index = valid.idxmin()
                max_index = valid.idxmax()

                column_stats["minimum_record"] = (
                    df.loc[min_index].to_dict()
                )

                column_stats["maximum_record"] = (
                    df.loc[max_index].to_dict()
                )

        else:
            column_stats = {
                "unique_values": int(series.nunique()),
                "most_frequent_values": (
                    series.value_counts()
                    .head(10)
                    .to_dict()
                )
            }

        statistics[str(column)] = column_stats

    return statistics


def analyze_dataframe(
    df: pd.DataFrame,
    filename: str,
    source_type: str,
    page_number: int = None,
    table_number: int = None
) -> dict:

    return {
        "source": {
            "filename": filename,
            "source_type": source_type,
            "page_number": page_number,
            "table_number": table_number
        },
        "overview": {
            "filename": filename,
            "total_rows": int(len(df)),
            "total_columns": int(len(df.columns)),
            "columns": df.columns.astype(str).tolist(),
            "data_types": {
                str(column): str(dtype)
                for column, dtype in df.dtypes.items()
            }
        },
        "column_metadata": get_column_metadata(df),
        "column_statistics": get_column_statistics(df),
        "analytics": generate_analytics(df)
    }


def get_dataset_analysis(file_path: Path) -> dict:
    df = load_dataset(file_path)

    return analyze_dataframe(
        df=df,
        filename=file_path.name,
        source_type="tabular_file"
    )


def get_session_datasets(session_id: int) -> list:
    if not session_id:
        raise ValueError("Session ID is required")

    db: Session = SessionLocal()

    try:
        uploaded_files = (
            db.query(UploadedFile)
            .filter(UploadedFile.session_id == session_id)
            .all()
        )

        datasets = []

        for uploaded_file in uploaded_files:
            file_path = UPLOAD_DIR / uploaded_file.stored_filename

            if not file_path.exists():
                continue

            if uploaded_file.extension in TABULAR_EXTENSIONS:
                df = load_dataset(file_path)

                if not df.empty:
                    datasets.append({
                        **analyze_dataframe(
                            df=df,
                            filename=uploaded_file.filename,
                            source_type="tabular_file"
                        ),
                        "dataframe": df
                    })

            elif uploaded_file.extension == ".pdf":
                extracted_data = extract_file_content(file_path)

                for table in extracted_data.get("tables", []):
                    df = pd.DataFrame(
                        table["data"],
                        columns=table["columns"]
                    )

                    if df.empty:
                        continue

                    datasets.append({
                        **analyze_dataframe(
                            df=df,
                            filename=uploaded_file.filename,
                            source_type="pdf_table",
                            page_number=table["page_number"],
                            table_number=table["table_index"]
                        ),
                        "dataframe": df
                    })

        return datasets

    finally:
        db.close()


def get_session_dataset_context(
    question: str,
    session_id: int
) -> str:

    datasets = get_session_datasets(session_id)

    dataset_contexts = []

    for dataset in datasets:
        df = dataset["dataframe"]

        dataset_information = {
            "source": dataset["source"],
            "overview": dataset["overview"],
            "column_metadata": dataset["column_metadata"],
            "column_statistics": dataset["column_statistics"],
            "sample_records": df.head(10).to_dict(orient="records")
        }

        dataset_contexts.append(
            f"DATASET INFORMATION:\n{dataset_information}"
        )

    return "\n\n".join(dataset_contexts)

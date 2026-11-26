
import pandas as pd


def generate_analytics(df: pd.DataFrame):
    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    categorical_columns = df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    analytics = {
        "overview": {
            "total_rows": int(df.shape[0]),
            "total_columns": int(df.shape[1]),
            "numeric_columns": len(numeric_columns),
            "categorical_columns": len(categorical_columns),
            "missing_values": int(df.isnull().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum())
        },
        "numeric_analysis": {},
        "categorical_analysis": {},
        "charts": {}
    }

    for column in numeric_columns:
        series = df[column].dropna()

        if series.empty:
            continue

        analytics["numeric_analysis"][column] = {
            "mean": float(series.mean()),
            "median": float(series.median()),
            "minimum": float(series.min()),
            "maximum": float(series.max()),
            "standard_deviation": float(series.std()) if len(series) > 1 else 0
        }

        analytics["charts"][column] = {
            "type": "histogram",
            "labels": series.round(2).tolist()[:500]
        }

    for column in categorical_columns:
        counts = df[column].fillna("Missing").astype(str).value_counts().head(10)

        analytics["categorical_analysis"][column] = {
            "unique_values": int(df[column].nunique()),
            "top_values": counts.to_dict()
        }

        analytics["charts"][column] = {
            "type": "bar",
            "labels": counts.index.tolist(),
            "values": counts.astype(int).tolist()
        }

    return analytics


import json
import re

import pandas as pd

from backend.services.dataset_service import (
    get_session_datasets as load_session_datasets
)
from backend.services.gemini_service import generate_ai_response


ALLOWED_OPERATIONS = {
    "lookup",
    "filter",
    "rank",
    "aggregate",
    "describe",
    "change"
}

ALLOWED_FILTERS = {
    "eq", "ne", "gt", "gte", "lt", "lte",
    "contains", "in", "between"
}

ALLOWED_METRICS = {
    "count", "sum", "mean", "min", "max", "median", "nunique"
}


def get_session_datasets(session_id: int):
    if not session_id:
        raise ValueError("Session ID is required")

    session_datasets = load_session_datasets(session_id)

    datasets = []

    for dataset in session_datasets:
        df = dataset["dataframe"]

        if df.empty:
            continue

        source = dataset["source"]

        datasets.append({
            "filename": source["filename"],
            "source": source,
            "dataframe": df,
            "schema": {
                "columns": [
                    {
                        "name": str(column),
                        "dtype": str(df[column].dtype),
                        "examples": (
                            df[column]
                            .dropna()
                            .head(3)
                            .astype(str)
                            .tolist()
                        )
                    }
                    for column in df.columns
                ],
                "row_count": len(df)
            }
        })

    return datasets


def create_query_plan(question: str, datasets: list) -> dict:
    schemas = [
        {
            "dataset_index": index,
            "filename": dataset["filename"],
            "source": dataset["source"],
            **dataset["schema"]
        }
        for index, dataset in enumerate(datasets)
    ]

    prompt = f"""
You are a general-purpose data analysis query planner.

Convert the user's question into one JSON query plan.

Available datasets and their schemas:
{json.dumps(schemas, default=str)}

User question:
{question}

Return ONLY valid JSON using this structure:

{{
    "dataset_index": 0,
    "operation": "lookup",
    "filters": [],
    "columns": [],
    "rank_column": null,
    "direction": "desc",
    "metric": null,
    "group_by": [],
    "column": null,
    "time_column": null,
    "value_column": null,
    "limit": 20
}}

Available operations:

1. lookup: Retrieve matching records.
2. filter: Retrieve records matching conditions.
3. rank: Sort individual records by a column.
4. aggregate: Calculate count, sum, mean, min, max, median or nunique.
5. describe: Return descriptive statistics.
6. change: Calculate the difference between the earliest and latest observations.

IMPORTANT RULES FOR CHANGE:

1. Use change when the user asks about improvement, growth, decline, increase, decrease, change over time, or difference between the first and latest observations.
2. Do NOT use rank for questions about change over time.
3. Identify the entity or category using group_by.
4. Identify the time-related column using time_column.
5. Identify the numeric measurement using value_column.
6. Calculate the earliest and latest observations separately for every group.
7. Use direction desc for greatest improvement and direction asc for greatest decline.
8. The change is latest value minus earliest value.
9. Never calculate change using only the highest and lowest individual records.
10. The executor will calculate the actual results.

General rules:

1. Select the dataset that best answers the question.
2. Consider both ordinary tabular files and tables extracted from PDF documents.
3. Use only columns present in the selected dataset.
4. Use actual column names exactly as provided.
5. Never invent columns or filter values.
6. Filters must use eq, ne, gt, gte, lt, lte, contains, in or between.
7. Use rank for highest, lowest, top and bottom individual records.
8. Use aggregate for averages, totals and grouped calculations.
9. Use lookup for questions about particular records.
10. Return a reasonable limit between 1 and 100.
11. Do not generate Python, SQL, code or explanations.
"""

    response = generate_ai_response(prompt).strip()

    response = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        response,
        flags=re.IGNORECASE
    )

    try:
        plan = json.loads(response)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Unable to understand the data question. Please rephrase it."
        ) from error

    if not isinstance(plan, dict):
        raise ValueError("Invalid query plan")

    return plan


def apply_filters(df: pd.DataFrame, filters: list) -> pd.DataFrame:
    if not isinstance(filters, list):
        raise ValueError("Invalid filter configuration")

    for condition in filters:
        if not isinstance(condition, dict):
            raise ValueError("Invalid filter condition")

        column = condition.get("column")
        operator = condition.get("operator")
        value = condition.get("value")

        if column not in df.columns:
            raise ValueError(f"Unknown dataset column: {column}")

        if operator not in ALLOWED_FILTERS:
            raise ValueError("Unsupported filter operation")

        series = df[column]

        if operator == "eq":
            if pd.isna(value):
                mask = series.isna()
            else:
                mask = series.astype(str) == str(value)

        elif operator == "ne":
            if pd.isna(value):
                mask = series.notna()
            else:
                mask = series.astype(str) != str(value)

        elif operator in {"gt", "gte", "lt", "lte"}:
            numeric_series = pd.to_numeric(series, errors="coerce")

            numeric_value = pd.to_numeric(
                pd.Series([value]),
                errors="coerce"
            ).iloc[0]

            if pd.isna(numeric_value):
                raise ValueError("Invalid numeric filter value")

            if operator == "gt":
                mask = numeric_series > numeric_value
            elif operator == "gte":
                mask = numeric_series >= numeric_value
            elif operator == "lt":
                mask = numeric_series < numeric_value
            else:
                mask = numeric_series <= numeric_value

        elif operator == "contains":
            mask = series.astype(str).str.contains(
                str(value),
                case=False,
                na=False,
                regex=False
            )

        elif operator == "in":
            if not isinstance(value, list):
                raise ValueError("The 'in' filter requires a list")

            mask = series.astype(str).isin(
                [str(item) for item in value]
            )

        else:
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError(
                    "The 'between' filter requires two values"
                )

            try:
                lower = float(value[0])
                upper = float(value[1])
            except (TypeError, ValueError):
                raise ValueError("Invalid range values")

            if lower > upper:
                raise ValueError("Invalid range boundaries")

            numeric_series = pd.to_numeric(series, errors="coerce")
            mask = numeric_series.between(lower, upper)

        df = df.loc[mask]

    return df


def calculate_group_changes(
    df: pd.DataFrame,
    group_by: list,
    time_column: str,
    value_column: str,
    direction: str,
    limit: int
):
    if not isinstance(group_by, list):
        raise ValueError("Invalid grouping configuration")

    if not time_column or time_column not in df.columns:
        raise ValueError("Invalid time column")

    if not value_column or value_column not in df.columns:
        raise ValueError("Invalid value column")

    if time_column == value_column:
        raise ValueError("Time and value columns must be different")

    if not all(column in df.columns for column in group_by):
        raise ValueError("Invalid grouping column")

    if direction not in {"asc", "desc"}:
        raise ValueError("Invalid change ranking direction")

    working_df = df.copy()

    working_df["_analysis_time"] = pd.to_numeric(
        working_df[time_column],
        errors="coerce"
    )

    if working_df["_analysis_time"].notna().sum() == 0:
        parsed_dates = pd.to_datetime(
            working_df[time_column],
            errors="coerce",
            format="mixed"
        )

        working_df["_analysis_time"] = parsed_dates

    working_df["_analysis_value"] = pd.to_numeric(
        working_df[value_column],
        errors="coerce"
    )

    working_df = working_df.dropna(
        subset=["_analysis_time", "_analysis_value"]
    )

    if working_df.empty:
        raise ValueError(
            "No valid time and numeric value observations were found."
        )

    if group_by:
        grouping = group_by[0] if len(group_by) == 1 else group_by

        groups = working_df.groupby(
            grouping,
            dropna=False,
            sort=False
        )
    else:
        groups = [(None, working_df)]

    results = []

    for group_key, group_df in groups:
        group_df = group_df.sort_values(
            by="_analysis_time",
            ascending=True,
            kind="stable"
        )

        earliest = group_df.iloc[0]
        latest = group_df.iloc[-1]

        start_value = float(earliest["_analysis_value"])
        end_value = float(latest["_analysis_value"])

        change = end_value - start_value

        percent_change = (
            (change / abs(start_value)) * 100
            if start_value != 0
            else None
        )

        record = {}

        if group_by:
            group_values = (
                group_key
                if isinstance(group_key, tuple)
                else (group_key,)
            )

            for column, value in zip(group_by, group_values):
                record[column] = (
                    None if pd.isna(value) else value
                )

        record.update({
            "start_period": str(earliest[time_column]),
            "end_period": str(latest[time_column]),
            "start_value": start_value,
            "end_value": end_value,
            "change": change,
            "percent_change": percent_change
        })

        results.append(record)

    results.sort(
        key=lambda item: item["change"],
        reverse=(direction == "desc")
    )

    return results[:limit]


def execute_query_plan(df: pd.DataFrame, plan: dict):
    operation = plan.get("operation")

    if operation not in ALLOWED_OPERATIONS:
        raise ValueError("Unsupported dataset operation")

    limit = plan.get("limit", 20)

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= 100
    ):
        limit = 20

    result_df = apply_filters(
        df.copy(),
        plan.get("filters", [])
    )

    if operation in {"lookup", "filter"}:
        columns = plan.get("columns") or result_df.columns.tolist()

        if not isinstance(columns, list):
            raise ValueError("Invalid column selection")

        if not all(column in result_df.columns for column in columns):
            raise ValueError("Invalid column requested")

        return result_df[columns].head(limit).to_dict(
            orient="records"
        )

    if operation == "rank":
        column = plan.get("rank_column")

        if column not in result_df.columns:
            raise ValueError("Invalid ranking column")

        direction = plan.get("direction", "desc")

        if direction not in {"asc", "desc"}:
            raise ValueError("Invalid ranking direction")

        result_df[column] = pd.to_numeric(
            result_df[column],
            errors="coerce"
        )

        result_df = result_df.dropna(subset=[column])

        result_df = result_df.sort_values(
            by=column,
            ascending=(direction == "asc")
        )

        return result_df.head(limit).to_dict(orient="records")

    if operation == "change":
        return calculate_group_changes(
            df=result_df,
            group_by=plan.get("group_by") or [],
            time_column=plan.get("time_column"),
            value_column=plan.get("value_column"),
            direction=plan.get("direction", "desc"),
            limit=limit
        )

    if operation == "aggregate":
        metric = plan.get("metric")
        column = plan.get("column")
        group_by = plan.get("group_by") or []

        if metric not in ALLOWED_METRICS:
            raise ValueError("Unsupported aggregation")

        if metric != "count" and column not in result_df.columns:
            raise ValueError("Invalid aggregation column")

        if not isinstance(group_by, list):
            raise ValueError("Invalid grouping configuration")

        if not all(item in result_df.columns for item in group_by):
            raise ValueError("Invalid grouping column")

        if column and metric in {
            "sum", "mean", "min", "max", "median"
        }:
            result_df[column] = pd.to_numeric(
                result_df[column],
                errors="coerce"
            )

        if group_by:
            grouped = result_df.groupby(
                group_by,
                dropna=False
            )

            if metric == "count":
                result = grouped.size().reset_index(name="result")
            else:
                result = grouped[column].agg(metric).reset_index(
                    name="result"
                )

            return result.head(limit).to_dict(orient="records")

        if metric == "count":
            return {"result": int(len(result_df))}

        series = result_df[column]

        if metric == "nunique":
            value = int(series.nunique())
        else:
            value = getattr(series, metric)()

        return {
            "column": column,
            "metric": metric,
            "result": (
                value.item()
                if hasattr(value, "item")
                else value
            )
        }

    if operation == "describe":
        return result_df.describe(
            include="all"
        ).fillna("").to_dict()

    raise ValueError("Unable to execute dataset query")


def answer_dataset_question(question: str, session_id: int):
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    if not session_id:
        raise ValueError("Session ID is required")

    datasets = get_session_datasets(session_id)

    if not datasets:
        return None

    plan = create_query_plan(question, datasets)

    dataset_index = plan.get("dataset_index")

    if (
        isinstance(dataset_index, bool)
        or not isinstance(dataset_index, int)
        or not 0 <= dataset_index < len(datasets)
    ):
        raise ValueError("Invalid dataset selection")

    selected_dataset = datasets[dataset_index]

    results = execute_query_plan(
        selected_dataset["dataframe"],
        plan
    )

    return {
        "filename": selected_dataset["filename"],
        "source": selected_dataset["source"],
        "operation": plan["operation"],
        "results": results
    }

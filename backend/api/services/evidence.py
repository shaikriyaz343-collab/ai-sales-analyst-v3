from __future__ import annotations

import pandas as pd

from schema_profiler_v2 import normalize_column_name


SOURCE_RECORD_ALIASES = (
    "order_id",
    "opportunity_id",
    "customer_id",
    "subscription_id",
    "client_id",
    "employee_id",
    "record_id",
    "id",
)


def resolve_source_record_column(
    data: pd.DataFrame,
    *extra_aliases: str,
) -> str | None:
    """Resolve a stable source-record identifier from semantic or normalized aliases."""
    aliases = (*extra_aliases, *SOURCE_RECORD_ALIASES)
    columns = [str(column) for column in data.columns]
    exact = {column for column in columns}
    for alias in aliases:
        if alias in exact:
            return alias
    wanted = {normalize_column_name(alias) for alias in aliases}
    return next(
        (column for column in columns if normalize_column_name(column) in wanted),
        next((column for column in columns if column.endswith("_id")), None),
    )


def format_source_records(
    values: pd.Series,
    column: str,
    *,
    limit: int = 12,
) -> list[str]:
    """Return deterministic, human-readable source-record references."""
    records = (
        values.dropna()
        .astype(str)
        .str.strip()
        .loc[lambda series: series.ne("") & series.str.lower().ne("nan")]
        .drop_duplicates()
        .tolist()
    )
    return [f"{column}={value}" for value in records[: max(0, int(limit))]]

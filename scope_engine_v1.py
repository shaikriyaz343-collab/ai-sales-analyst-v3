from __future__ import annotations

import pandas as pd


SCOPE_DIMENSIONS = {
    "transactional_sales": [
        ("product", "Product"),
        ("customer", "Customer"),
        ("region", "Region"),
    ],
    "sales_pipeline": [
        ("salesperson", "Salesperson"),
        ("stage", "Pipeline stage"),
        ("customer", "Account"),
    ],
    "subscription": [
        ("customer", "Customer"),
        ("plan", "Plan"),
        ("churn_status", "Churn status"),
    ],
    "services": [
        ("client", "Client"),
        ("service", "Service"),
        ("employee", "Employee"),
    ],
}


def available_scope_dimensions(
    full_df: pd.DataFrame,
    primary_type: str | None = None,
    max_dimensions: int = 2,
) -> list[tuple[str, str]]:
    """Return useful categorical dimensions actually present in this dataset."""
    preferred = SCOPE_DIMENSIONS.get(
        primary_type,
        [],
    )

    available: list[tuple[str, str]] = []
    for column, label in preferred:
        if column in full_df.columns:
            values = full_df[column].dropna()
            if not values.empty and values.astype(str).nunique() > 1:
                available.append((column, label))

    # Fall back to other useful canonical dimensions if an archetype-specific
    # dimension is absent. Never expose identifiers or numeric measures.
    if len(available) < max_dimensions:
        excluded = {
            "date", "order_id", "opportunity_id", "subscription_id",
            "project_id", "product", "customer", "salesperson", "stage",
            "client", "service", "employee", "region", "plan",
            "churn_status", "return_status", "payment_method",
        }
        for column in full_df.columns:
            if column in excluded:
                continue
            if column in {name for name, _ in available}:
                continue
            if not (
                pd.api.types.is_object_dtype(full_df[column])
                or pd.api.types.is_string_dtype(full_df[column])
                or pd.api.types.is_categorical_dtype(full_df[column])
            ):
                continue
            values = full_df[column].dropna()
            if 1 < values.astype(str).nunique() <= 50:
                available.append((column, column.replace("_", " ").title()))
            if len(available) >= max_dimensions:
                break

    return available[:max_dimensions]


def apply_scope_filters(
    full_df: pd.DataFrame,
    date_range=None,
    product: str = "All",
    customer: str = "All",
    dimension_filters: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Apply the exact dashboard-scope intersection used by the UI."""
    scoped = full_df.copy()

    if (
        date_range
        and isinstance(date_range, tuple)
        and len(date_range) == 2
        and "date" in scoped.columns
    ):
        start_date, end_date = date_range
        scoped_dates = pd.to_datetime(
            scoped["date"],
            errors="coerce",
        )
        scoped = scoped.loc[
            scoped_dates.between(
                pd.Timestamp(start_date),
                pd.Timestamp(end_date)
                + pd.Timedelta("1D")
                - pd.Timedelta("1s"),
            )
        ].copy()

    filters = dict(dimension_filters or {})

    # Backward-compatible legacy filters.
    if product != "All":
        filters["product"] = product
    if customer != "All":
        filters["customer"] = customer

    for column, selected in filters.items():
        if (
            selected
            and selected != "All"
            and column in scoped.columns
        ):
            scoped = scoped.loc[
                scoped[column].astype(str) == str(selected)
            ].copy()

    return scoped

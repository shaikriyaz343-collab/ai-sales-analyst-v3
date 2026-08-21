
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import io
import re
from typing import Any

import pandas as pd


@dataclass
class FieldProfile:
    original_name: str
    normalized_name: str
    role: str
    semantic_type: str
    confidence: str
    sample_values: list[str]
    unique_values: int
    nullable_pct: float
    recognized_as: str | None = None


COLUMN_ALIASES = {
    "date": [
        "date", "order date", "orderdate", "sale date",
        "sales date", "transaction date", "transactiondate",
        "invoice date", "invoicedate"
    ],
    "order_id": [
        "order id", "orderid", "order number", "ordernumber",
        "order no", "invoice", "invoice number", "invoicenumber",
        "invoice no", "transaction id", "transactionid"
    ],
    "customer": [
        "customer", "customer name", "customername",
        "client", "client name", "buyer", "account", "account name"
    ],
    "product": [
        "product", "product name", "productname", "item",
        "item name", "service", "service name"
    ],
    "category": [
        "category", "product category", "productcategory",
        "item category", "type", "product type"
    ],
    "quantity": [
        "quantity", "qty", "units", "units sold",
        "quantity sold", "items sold"
    ],
    "price": [
        "price", "unit price", "unitprice",
        "selling price", "sale price", "item price"
    ],
    "revenue": [
        "revenue", "sales", "sales amount", "total amount",
        "totalamount", "amount", "order total",
        "order total amount", "net sales", "sales revenue"
    ],
    "sku": [
        "sku", "sku code", "product sku", "productsku",
        "item sku", "stock keeping unit"
    ],
    "discount_pct": [
        "discount", "discount %", "discount pct",
        "discount percentage", "discountpercent"
    ],
    "discount_amount": [
        "discount amount", "discount value", "discount total"
    ],
    "return_status": [
        "return status", "returnstatus", "returned", "return flag",
        "refund status", "refundstatus"
    ],
    "return_amount": [
        "return amount", "returned amount", "refund amount",
        "refund value", "refund total"
    ],
    "region": [
        "region", "territory", "area", "market"
    ],
    "salesperson": [
        "salesperson", "sales person", "sales rep",
        "sales representative", "rep", "account manager"
    ],
    "channel": [
        "channel", "sales channel", "saleschannel",
        "order channel", "source"
    ],
    "payment_method": [
        "payment method", "paymentmethod", "payment type",
        "paymenttype", "tender"
    ],
    "order_status": [
        "order status", "orderstatus", "status"
    ],
    "opportunity_id": [
        "opportunity id", "opportunityid", "opportunity number",
        "deal id", "dealid", "lead id", "leadid"
    ],
    "stage": [
        "stage", "opportunity stage", "deal stage"
    ],
    "amount": [
        "amount", "deal amount", "opportunity amount",
        "pipeline amount"
    ],
    "probability": [
        "probability", "win probability", "close probability"
    ],
    "expected_close": [
        "expected close", "expected close date", "close date",
        "expectedclosedate"
    ],
    "created_date": [
        "created date", "createddate", "creation date",
        "lead created date", "opportunity created date"
    ],
    "start_date": [
        "start date", "startdate", "subscription start date"
    ],
    "subscription_id": [
        "subscription id", "subscriptionid"
    ],
    "plan": [
        "plan", "subscription plan", "package", "tier"
    ],
    "mrr": [
        "mrr", "monthly recurring revenue", "monthly recurring"
    ],
    "arr": [
        "arr", "annual recurring revenue"
    ],
    "churn_status": [
        "churn status", "churnstatus", "churn"
    ],
    "renewal_status": [
        "renewal status", "renewalstatus", "renewal"
    ],
    "project_id": [
        "project id", "projectid"
    ],
    "client": [
        "client", "client name"
    ],
    "service": [
        "service", "service name"
    ],
    "hours": [
        "hours", "billable hours", "hours billed", "hours worked"
    ],
    "billings": [
        "billings", "billing", "billed amount"
    ],
    "hourly_rate": [
        "hourly rate", "hourlyrate", "rate per hour"
    ],
    "employee": [
        "employee", "employee name", "consultant", "staff"
    ],
    "tax_amount": [
        "tax", "tax amount", "taxamount", "vat", "gst"
    ],
    "shipping_amount": [
        "shipping", "shipping amount", "shippingamount",
        "freight", "delivery charge"
    ],
    "cost": [
        "cost", "unit cost", "unitcost", "cogs", "cost of goods"
    ],
    "currency": [
        "currency", "currency code", "currencycode"
    ],
}


CORE_FIELDS = {
    "date",
    "order_id",
    "customer",
    "product",
    "quantity",
}

VALUE_FIELDS = {
    "price",
    "revenue",
}

OPTIONAL_ANALYTICS = {
    "sku": "SKU analysis",
    "discount_pct": "Discount analysis",
    "discount_amount": "Discount amount analysis",
    "return_status": "Return analysis",
    "return_amount": "Return value analysis",
    "region": "Regional analysis",
    "salesperson": "Sales team analysis",
    "channel": "Channel analysis",
    "payment_method": "Payment method analysis",
    "order_status": "Order status analysis",
    "tax_amount": "Tax analysis",
    "shipping_amount": "Shipping analysis",
    "cost": "Cost and margin analysis",
}


def normalize_column_name(column: str) -> str:
    text = str(column).strip()

    text = re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])",
        " ",
        text,
    )

    text = re.sub(
        r"(?<=[A-Z])(?=[A-Z][a-z])",
        " ",
        text,
    )

    return (
        text.lower()
        .replace("_", " ")
        .replace("-", " ")
        .strip()
    )


def _alias_lookup() -> dict[str, str]:
    lookup = {}

    for semantic_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            lookup[
                normalize_column_name(alias)
            ] = semantic_name

    return lookup


def _try_parse_wrapped_csv(df: pd.DataFrame, file_path: str | None):
    if df.shape[1] != 1:
        return df

    values = df.iloc[:, 0].astype(str)
    raw_column = str(df.columns[0]).strip()

    comma_ratio = values.str.contains(
        ",",
        regex=False,
    ).mean()

    looks_wrapped = (
        comma_ratio >= 0.8
        and (
            raw_column.lower()
            in {
                "fld1",
                "column1",
                "unnamed: 0",
            }
            or values.iloc[0].count(",") >= 3
        )
    )

    if not looks_wrapped:
        return df

    if file_path is None:
        return df

    raw_lines = Path(file_path).read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines()

    if (
        raw_lines
        and raw_lines[0].strip().lower()
        == raw_column.lower()
    ):
        raw_lines = raw_lines[1:]

    inner_lines = []

    for line in raw_lines:

        stripped = line.strip()

        if (
            len(stripped) >= 2
            and stripped.startswith('"')
            and stripped.endswith('"')
        ):
            stripped = stripped[1:-1].replace(
                '""',
                '"',
            )

        inner_lines.append(
            stripped
        )

    return pd.read_csv(
        io.StringIO(
            "\n".join(inner_lines)
        )
    )


def load_dataframe(
    source: str | Path | pd.DataFrame
) -> pd.DataFrame:

    if isinstance(source, pd.DataFrame):
        return source.copy()

    path = Path(source)

    if path.suffix.lower() == ".csv":

        df = pd.read_csv(path)

        return _try_parse_wrapped_csv(
            df,
            str(path),
        )

    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)

    raise ValueError(
        "Supported files: CSV, XLSX, XLS."
    )


def _infer_semantic_type(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    numeric_ratio = numeric.notna().mean()

    if numeric_ratio >= 0.9:
        return "numeric"

    try:
        parsed_dates = pd.to_datetime(
            series,
            errors="coerce",
            format="mixed",
        )
    except (TypeError, ValueError):
        # Older pandas versions do not support format="mixed".
        parsed_dates = pd.to_datetime(
            series,
            errors="coerce",
        )

    if parsed_dates.notna().mean() >= 0.9:
        return "date"

    return "text"


def _infer_confidence(
    column: str,
    recognized_as: str | None,
    semantic_type: str,
) -> str:

    if recognized_as is not None:

        if normalize_column_name(column) == normalize_column_name(
            recognized_as
        ):
            return "high"

        return "high"

    if semantic_type == "date":
        return "medium"

    return "low"


def profile_dataframe(
    source: str | Path | pd.DataFrame
) -> dict[str, Any]:

    data = load_dataframe(source)

    alias_lookup = _alias_lookup()

    fields: list[FieldProfile] = []
    recognized: dict[str, list[str]] = {}

    for column in data.columns:

        semantic_type = _infer_semantic_type(
            data[column]
        )

        normalized = normalize_column_name(
            column
        )

        recognized_as = alias_lookup.get(
            normalized
        )

        if recognized_as in CORE_FIELDS:
            role = "core"
        elif recognized_as in VALUE_FIELDS:
            role = "value"
        elif recognized_as in OPTIONAL_ANALYTICS:
            role = "optional"
        elif recognized_as:
            role = "optional"
        else:
            role = "additional"

        non_null = data[column].dropna()

        samples = [
            str(value)
            for value in non_null.head(3).tolist()
        ]

        field = FieldProfile(
            original_name=str(column),
            normalized_name=normalized,
            role=role,
            semantic_type=semantic_type,
            confidence=_infer_confidence(
                str(column),
                recognized_as,
                semantic_type,
            ),
            sample_values=samples,
            unique_values=int(
                data[column].nunique(
                    dropna=True
                )
            ),
            nullable_pct=round(
                float(
                    data[column].isna().mean()
                    * 100
                ),
                2,
            ),
            recognized_as=recognized_as,
        )

        fields.append(field)

        if recognized_as:
            recognized.setdefault(
                recognized_as,
                [],
            ).append(
                str(column)
            )

    recognized_keys = set(
        recognized.keys()
    )

    core_available = sorted(
        recognized_keys.intersection(
            CORE_FIELDS
        )
    )

    value_available = sorted(
        recognized_keys.intersection(
            VALUE_FIELDS
        )
    )

    optional_available = sorted(
        recognized_keys.intersection(
            OPTIONAL_ANALYTICS
        )
    )

    missing_core = sorted(
        CORE_FIELDS.difference(
            recognized_keys
        )
    )

    has_value = bool(
        recognized_keys.intersection(
            VALUE_FIELDS
        )
    )

    if not missing_core and has_value:
        readiness = "ready"
        readiness_message = (
            "Your file is ready for sales analysis."
        )
    else:
        readiness = "needs_review"
        readiness_message = (
            "We found some fields, but a few important sales fields "
            "still need to be identified."
        )

    available_analysis = [
        "Core sales performance",
        "Product performance",
        "Customer performance",
        "Monthly performance",
        "Ask Your Business Analyst",
        "Executive report",
    ]

    available_analysis.extend(
        OPTIONAL_ANALYTICS[field]
        for field in optional_available
    )

    return {
        "row_count": int(len(data)),
        "column_count": int(len(data.columns)),
        "fields": [
            asdict(field)
            for field in fields
        ],
        "recognized": recognized,
        "core_available": core_available,
        "value_available": value_available,
        "optional_available": optional_available,
        "unmapped_fields": [
            item.original_name
            for item in fields
            if item.role == "additional"
        ],
        "missing_core": missing_core,
        "readiness": readiness,
        "readiness_message": readiness_message,
        "available_analysis": available_analysis,
    }


def profile_for_ui(
    source: str | Path | pd.DataFrame
) -> dict[str, Any]:

    profile = profile_dataframe(
        source
    )

    return {
        "rows": profile["row_count"],
        "columns": profile["column_count"],
        "status": profile["readiness"],
        "message": profile["readiness_message"],
        "core_fields": [
            item["recognized_as"]
            for item in profile["fields"]
            if item["role"] == "core"
            and item["recognized_as"]
        ],
        "value_fields": [
            item["recognized_as"]
            for item in profile["fields"]
            if item["role"] == "value"
            and item["recognized_as"]
        ],
        "additional_fields": [
            {
                "file_field": item["original_name"],
                "analysis": OPTIONAL_ANALYTICS.get(
                    item["recognized_as"],
                    "Additional analysis",
                ),
            }
            for item in profile["fields"]
            if item["role"] == "optional"
        ],
        "unmapped_fields": [
            item["original_name"]
            for item in profile["fields"]
            if item["role"] == "additional"
        ],
    }

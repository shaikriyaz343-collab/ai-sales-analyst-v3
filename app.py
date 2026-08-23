
from __future__ import annotations

import scope_engine_v1 as _scope_engine

_apply_scope_filters = _scope_engine.apply_scope_filters
available_scope_dimensions = getattr(
    _scope_engine,
    "available_scope_dimensions",
    lambda full_df, primary_type=None, max_dimensions=2: [],
)

import hashlib
import os
import re
import tempfile
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from schema_profiler_v2 import profile_dataframe
from semantic_business_model_v2 import build_semantic_model
from data_quality_engine_v1 import run_data_quality_checks, quality_summary
from business_type_detector_v1 import detect_business_type
from adaptive_analysis_engine_v1 import analyze_modules
from business_analysis_packs_v1 import run_business_type_packs
from adaptive_dashboard_engine_v1 import build_dashboard_plan
from report_generator import (
    calculate_kpis,
    analyze_products,
    analyze_customers,
    analyze_monthly_sales,
)
from sales_query_engine_v1 import answer_sales_question_structured, plan_sales_question
from business_intelligence import build_business_findings
from adaptive_pdf_generator_v1 import generate_adaptive_pdf
from business_analyst_agent_v1 import answer_with_agent


def _load_analyst_intelligence():
    """
    Lazily import the analyst-intelligence module.

    Streamlit Cloud may rerun/reload modules during a code update. A transient
    partially-initialized module can otherwise surface as a KeyError during
    import and blank the entire app. Retry once after invalidating import
    caches, then surface a controlled fallback to the UI.
    """
    import importlib

    last_error = None
    for attempt in range(2):
        try:
            importlib.invalidate_caches()
            module = importlib.import_module(
                "analyst_intelligence_v2"
            )
            return module
        except KeyError as exc:
            last_error = exc
            sys.modules.pop(
                "analyst_intelligence_v2",
                None,
            )
        except Exception as exc:
            last_error = exc
            break

    raise RuntimeError(
        "Analyst intelligence module could not be loaded."
    ) from last_error


def _safe_build_business_brief(
    *,
    data,
    profile,
    semantic_model,
    business_type,
    adaptive_analysis,
    packs,
    data_quality,
    fallback_findings=None,
):
    try:
        module = _load_analyst_intelligence()
        return module.build_business_brief(
            data=data,
            profile=profile,
            semantic_model=semantic_model,
            business_type=business_type,
            adaptive_analysis=adaptive_analysis,
            packs=packs,
            data_quality=data_quality,
        )
    except Exception as exc:
        return {
            "signals": fallback_findings or [],
            "summary": (
                "The core business analysis is available, but the optional "
                "analyst-intelligence layer is temporarily unavailable."
            ),
            "limitations": [str(exc)],
            "recommended_actions": [],
        }


def _safe_build_query_evidence(
    data,
    question,
    plan,
):
    try:
        module = _load_analyst_intelligence()
        return module.build_query_evidence(
            data,
            question,
            plan,
        )
    except Exception as exc:
        return {
            "question": question,
            "scope": "Full uploaded dataset",
            "rows_in_file": int(len(data)),
            "source_fields": list(data.columns),
            "calculation": "Verified deterministic query",
            "limitations": [
                "Detailed evidence builder unavailable; answer still came "
                "from the deterministic query engine."
            ],
            "error": str(exc),
        }



st.set_page_config(
    page_title="AI Business Analyst",
    page_icon="📊",
    layout="wide",
)

# ------------------------------------------------------------------
# Session state
# ------------------------------------------------------------------
defaults = {
    "source_df": None,
    "normalized_df": None,
    "profile": None,
    "semantic_model": None,
    "quality": None,
    "business_type": None,
    "adaptive_analysis": None,
    "business_packs": None,
    "dashboard_plan": None,
    "business_name": "My Business",
    "ask_answer": None,
    "ask_agent_result": None,
    "ask_question": "",
    "ask_answered_question": "",
    "ask_history": [],
    "report": None,
    "full_report": None,
    "view_report": None,
    "scope_active": False,
    "scope_product": "All",
    "scope_customer": "All",
    "scope_dates": None,
    "scope_filters": {},
    "ask_use_view_scope": False,
    "pdf_file": None,
    "uploaded_file_key": None,
    "analysis_pending": False,
    "active_dashboard_section": "overview",
    "review_section_nav": "overview",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def _normalize_uploaded_data(
    data: pd.DataFrame,
    profile: dict,
) -> pd.DataFrame:
    """Convert profiled source fields to the application's canonical names."""
    df = data.copy()

    rename_map = {}
    for semantic_name, columns in profile.get("recognized", {}).items():
        for column in columns:
            if column in df.columns:
                # Do not overwrite if a canonical name is already present.
                if semantic_name not in df.columns:
                    rename_map[column] = semantic_name

    df = df.rename(columns=rename_map)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

    if "quantity" in df.columns:
        df["quantity"] = pd.to_numeric(
            df["quantity"],
            errors="coerce",
        )

    if "price" in df.columns:
        df["price"] = pd.to_numeric(
            df["price"],
            errors="coerce",
        )

    if "revenue" in df.columns:
        df["revenue"] = pd.to_numeric(
            df["revenue"],
            errors="coerce",
        )

    # Derive revenue or unit price where possible.
    if "revenue" not in df.columns and {
        "quantity",
        "price",
    }.issubset(df.columns):
        df["revenue"] = (
            df["quantity"] * df["price"]
        )

    if "price" not in df.columns and {
        "revenue",
        "quantity",
    }.issubset(df.columns):
        safe_q = df["quantity"].replace(0, pd.NA)
        df["price"] = (
            df["revenue"] / safe_q
        )

    if "category" not in df.columns:
        df["category"] = "Uncategorized"

    return df


def _build_report_context(
    df: pd.DataFrame,
    business_type: dict,
    profile: dict,
    semantic_model: dict,
    adaptive_analysis: dict,
    packs: dict,
    data_quality: dict | None,
    scope_filters: dict | None = None,
    scope_dates=None,
) -> dict:
    """Build the single analysis context used by every dashboard surface."""
    primary = business_type.get("primary_type")

    report = {
        "data": df,
        "kpis": {},
        "products": [],
        "customers": [],
        "monthly": [],
        "reporting_period": {
            "start": df["date"].min() if "date" in df.columns else None,
            "end": df["date"].max() if "date" in df.columns else None,
        },
        "business_findings": {
            "findings": [],
            "priority_findings": [],
            "positive_findings": [],
        },
    }

    if primary == "transactional_sales":
        report["kpis"] = calculate_kpis(df)
        report["products"] = analyze_products(df)
        report["customers"] = analyze_customers(df)
        report["monthly"] = analyze_monthly_sales(df)

        try:
            report["business_findings"] = build_business_findings(report)
        except Exception:
            pass

    report["business_brief"] = _safe_build_business_brief(
        data=df,
        profile=profile,
        semantic_model=semantic_model,
        business_type=business_type,
        adaptive_analysis=adaptive_analysis,
        packs=packs,
        data_quality=data_quality,
    )

    # Convert the shared brief into the legacy finding contract so older UI
    # components and the Executive Report can consume the same ranked facts.
    brief_signals = report["business_brief"].get("signals", [])

    # A filtered dimension cannot be used as evidence of concentration risk.
    # Example: after filtering to Client A, saying "Client A is 100% of billings"
    # is tautological rather than a business finding.
    filters = dict(scope_filters or {})
    concentration_types = {
        "product": "product_concentration",
        "customer": "customer_concentration",
        "client": "client_concentration",
        "salesperson": "salesperson_concentration",
        "region": "region_concentration",
        "plan": "plan_concentration",
    }
    filtered_dimension_types = {
        concentration_types[column]
        for column, value in filters.items()
        if value != "All" and column in concentration_types
    }
    if filtered_dimension_types:
        brief_signals = [
            signal
            for signal in brief_signals
            if signal.get("type") not in filtered_dimension_types
        ]
        report["business_brief"]["signals"] = brief_signals

    if brief_signals:
        report["business_findings"]["priority_findings"] = brief_signals
        report["business_findings"]["findings"] = brief_signals

    report["scope"] = {
        "active": bool(filters or scope_dates),
        "filters": filters,
        "dates": scope_dates,
    }

    return report



def _dataset_is_usable(
    profile: dict,
    business_type: dict,
) -> bool:
    primary = business_type.get(
        "primary_type"
    )

    available = set(
        profile.get(
            "recognized",
            {}
        ).keys()
    )

    if primary == "transactional_sales":
        return (
            {"date", "order_id", "customer", "product", "quantity"}
            .issubset(available)
            and bool(
                {"revenue", "price"} & available
            )
        )

    if primary == "sales_pipeline":
        return (
            (
                "opportunity_id" in available
                or "order_id" in available
            )
            and "stage" in available
            and "amount" in available
        )

    if primary == "subscription":
        return (
            "mrr" in available
            and (
                "customer" in available
                or "subscription_id" in available
            )
        )

    if primary == "services":
        return (
            "hours" in available
            and (
                "billings" in available
                or "revenue" in available
                or "amount" in available
            )
        )

    return False


def _process_upload(uploaded_file):
    suffix = Path(
        uploaded_file.name
    ).suffix.lower()

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as temp:
        temp.write(
            uploaded_file.getvalue()
        )
        temp_path = temp.name

    try:
        profile = profile_dataframe(
            temp_path
        )

        if suffix == ".csv":
            from schema_profiler_v2 import load_dataframe
        else:
            from schema_profiler_v2 import load_dataframe

        raw_df = load_dataframe(
            temp_path
        )

        normalized = _normalize_uploaded_data(
            raw_df,
            profile,
        )

        semantic = build_semantic_model(
            profile,
            normalized,
        )

        quality = run_data_quality_checks(
            normalized,
            semantic,
        )

        business_type = detect_business_type(
            semantic,
            profile,
        )

        adaptive = analyze_modules(
            normalized,
            semantic,
            quality,
        )

        packs = run_business_type_packs(
            normalized,
            business_type,
        )

        dashboard = build_dashboard_plan(
            semantic,
            business_type,
            adaptive,
            quality,
        )

        return (
            raw_df,
            normalized,
            profile,
            semantic,
            quality,
            business_type,
            adaptive,
            packs,
            dashboard,
        )

    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def _format_currency(value):
    if value is None or pd.isna(value):
        return "—"
    return f"${float(value):,.2f}"



def _answer_business_pack_question(
    primary: str,
    packs: dict,
    question: str,
) -> dict | None:
    """Deterministic Q&A for non-transactional business models."""
    q = (question or "").strip().lower()
    pack_map = packs.get(
        "packs",
        {},
    )

    if primary == "sales_pipeline":
        module = pack_map.get("sales_pipeline")
        forecast = pack_map.get("forecast")

        if not module or not module.get("available"):
            return None

        metrics = module.get("metrics", {})
        rows = module.get("salesperson_breakdown", [])

        if (
            ("pipeline" in q and any(
                phrase in q
                for phrase in (
                    "how much",
                    "value",
                    "total",
                    "worth",
                )
            ))
            or "pipeline value" in q
        ):
            return {
                "mode": "deterministic",
                "answer": (
                    f"Pipeline value is "
                    f"{_format_currency(metrics.get('pipeline_value'))} "
                    f"across {metrics.get('opportunities', 0):,} opportunities."
                ),
                "steps": [],
                "recommendations": [],
                "limitations": [],
                "confidence": "high",
            }

        if "win rate" in q:
            value = metrics.get("win_rate_pct")
            return {
                "mode": "deterministic",
                "answer": (
                    "Closed-opportunity win rate is "
                    + (
                        f"{value:.1f}%."
                        if value is not None
                        else "not available because closed outcomes are missing."
                    )
                ),
                "steps": [],
                "recommendations": [],
                "limitations": [],
                "confidence": "high",
            }

        if any(
            phrase in q
            for phrase in (
                "top sales rep",
                "best sales rep",
                "top salesperson",
                "best salesperson",
                "highest seller",
            )
        ):
            if not rows:
                return None
            top = rows[0]
            return {
                "mode": "deterministic",
                "answer": (
                    f"{top.get('salesperson')} has the highest pipeline value "
                    f"in the uploaded data at "
                    f"{_format_currency(top.get('amount'))}. "
                    "This is pipeline value, not a measure of sales performance or quota attainment."
                ),
                "steps": [],
                "recommendations": [],
                "limitations": [],
                "confidence": "high",
            }

        if "forecast" in q:
            if forecast and forecast.get("available"):
                fmetrics = forecast.get("metrics", {})
                return {
                    "mode": "deterministic",
                    "answer": (
                        f"Expected pipeline is "
                        f"{_format_currency(fmetrics.get('pipeline_value'))}; "
                        f"probability-weighted forecast is "
                        f"{_format_currency(fmetrics.get('weighted_forecast'))}."
                    ),
                    "steps": [],
                    "recommendations": [],
                    "limitations": forecast.get("notes", []),
                    "confidence": "high",
                }
            return None

    elif primary == "subscription":
        module = pack_map.get("subscription")
        if not module or not module.get("available"):
            return None

        metrics = module.get("metrics", {})
        rows = module.get("customer_breakdown", [])

        # Entity-specific questions take precedence over metric-only questions.
        if any(
            phrase in q
            for phrase in (
                "top customer",
                "best customer",
                "highest mrr customer",
                "highest mrr",
                "largest customer",
            )
        ):
            if not rows:
                return None
            top = rows[0]
            return {
                "mode": "deterministic",
                "answer": (
                    f"{top.get('customer')} has the highest MRR in the uploaded "
                    f"data at {_format_currency(top.get('mrr'))}."
                ),
                "steps": [],
                "recommendations": [],
                "limitations": [],
                "confidence": "high",
            }

        if "mrr" in q or "monthly recurring revenue" in q:
            return {
                "mode": "deterministic",
                "answer": (
                    f"Current MRR in the uploaded data is "
                    f"{_format_currency(metrics.get('mrr'))}."
                ),
                "steps": [],
                "recommendations": [],
                "limitations": [],
                "confidence": "high",
            }

        if (
            "arr" in q
            or "annualized revenue" in q
            or "annual recurring revenue" in q
        ):
            return {
                "mode": "deterministic",
                "answer": (
                    f"Annualized recurring revenue is "
                    f"{_format_currency(metrics.get('annualized_revenue'))} "
                    "based on the current MRR snapshot."
                ),
                "steps": [],
                "recommendations": [],
                "limitations": [],
                "confidence": "high",
            }

        if "churn" in q:
            value = metrics.get("churn_rate_pct")
            return {
                "mode": "deterministic",
                "answer": (
                    "Churn rate is "
                    + (
                        f"{value:.1f}%."
                        if value is not None
                        else "not available because a churn-status field was not found."
                    )
                ),
                "steps": [],
                "recommendations": [],
                "limitations": [],
                "confidence": "high",
            }

    elif primary == "services":
        module = pack_map.get("services")
        if not module or not module.get("available"):
            return None

        metrics = module.get("metrics", {})
        clients = module.get("client_breakdown", [])
        employees = module.get("employee_breakdown", [])

        if "billings" in q or "billing" in q:
            return {
                "mode": "deterministic",
                "answer": (
                    f"Total billings in the uploaded data are "
                    f"{_format_currency(metrics.get('billings'))}."
                ),
                "steps": [],
                "recommendations": [],
                "limitations": [],
                "confidence": "high",
            }

        if "revenue per hour" in q or "billing rate" in q:
            return {
                "mode": "deterministic",
                "answer": (
                    f"Average recorded revenue per hour is "
                    f"{_format_currency(metrics.get('revenue_per_hour'))}."
                ),
                "steps": [],
                "recommendations": [],
                "limitations": [],
                "confidence": "high",
            }

        if "hours" in q or "most hours" in q:
            if not employees:
                return None
            top = employees[0]
            return {
                "mode": "deterministic",
                "answer": (
                    f"{top.get('employee')} has the most recorded hours at "
                    f"{float(top.get('hours', 0)):.1f} hours. "
                    "This is recorded utilization, not a measure of employee quality."
                ),
                "steps": [],
                "recommendations": [],
                "limitations": [],
                "confidence": "high",
            }

        if any(
            phrase in q
            for phrase in (
                "top client",
                "best client",
                "largest client",
                "top customer",
            )
        ):
            if not clients:
                return None
            top = clients[0]
            return {
                "mode": "deterministic",
                "answer": (
                    f"{top.get('client')} has the highest recorded billings at "
                    f"{_format_currency(top.get('revenue', top.get('billings')))}. "
                    "This ranks clients by billings, not profitability."
                ),
                "steps": [],
                "recommendations": [],
                "limitations": [],
                "confidence": "high",
            }

    return None


def _answer_business_question(report, question: str) -> dict:
    """Route questions by business model, preferring verified calculations."""
    q = (question or "").strip().lower()
    primary = (
        st.session_state.get("business_type", {})
        .get("primary_type")
    )

    investigation_terms = (
        "why ",
        "what caused",
        "reason",
        "decline",
        "drop",
        "fell",
        "weak",
        "weaker",
        "change",
        "changed",
    )

    # The transaction-specific investigation agent is only safe when the
    # underlying data actually contains transaction revenue/order history.
    if primary == "transactional_sales" and any(
        term in q for term in investigation_terms
    ):
        result = answer_with_agent(
            report["data"],
            question,
        )
        if result.get("intent") == "investigate_change":
            return {
                "mode": "agent",
                "answer": result["executive_answer"],
                "steps": result.get("steps", []),
                "recommendations": result.get("recommendations", []),
                "limitations": result.get("limitations", []),
                "confidence": result.get("confidence", "medium"),
                "evidence": {
                    "question": question,
                    "scope": "Full uploaded dataset",
                    "rows_in_file": int(len(report.get("data", pd.DataFrame()))),
                    "calculation": "Deterministic period, product, customer, and optional return/discount checks",
                    "source_fields": list(report.get("data", pd.DataFrame()).columns),
                    "limitations": result.get("limitations", []),
                },
            }

    if primary != "transactional_sales":
        active_packs = (
            st.session_state.get("scope_business_packs")
            if st.session_state.get("ask_use_view_scope")
            and st.session_state.get("scope_business_packs") is not None
            else st.session_state.get("business_packs", {})
        )

        business_pack_answer = _answer_business_pack_question(
            primary,
            active_packs,
            question,
        )

        if business_pack_answer is not None:
            business_pack_answer["evidence"] = {
                "question": question,
                "scope": "Current dashboard scope" if st.session_state.get("ask_use_view_scope") else "Full uploaded dataset",
                "rows_in_file": int(len(report.get("data", pd.DataFrame()))),
                "calculation": "Verified business-specific metric from the detected semantic model",
                "source_fields": list(report.get("data", pd.DataFrame()).columns),
                "limitations": business_pack_answer.get("limitations", []),
            }
            return business_pack_answer

        # A senior analyst should prefer a transparent limitation over a
        # plausible but unsupported explanation.
        if any(term in q for term in investigation_terms):
            limitation = {
                "subscription": "The file does not include cancellation reasons or longitudinal retention history, so the cause of churn cannot be established from this data alone.",
                "sales_pipeline": "The file supports pipeline and stage analysis, but it does not include enough historical context to establish why performance changed.",
                "services": "The file supports billing, hours, and utilization analysis, but it does not contain enough context to establish the operational cause of a change.",
            }.get(primary, "The available data does not support a reliable causal explanation.")
        else:
            limitation = "The requested metric is not mapped to a verified calculation for this business type."

        return {
            "mode": "business_pack",
            "answer": "I can't verify that conclusion from the available fields without guessing.",
            "steps": [],
            "recommendations": [],
            "limitations": [limitation],
            "confidence": "low",
            "evidence": {
                "question": question,
                "scope": "Current dashboard scope" if st.session_state.get("ask_use_view_scope") else "Full uploaded dataset",
                "rows_in_file": int(len(report.get("data", pd.DataFrame()))),
                "source_fields": list(report.get("data", pd.DataFrame()).columns),
                "limitations": [limitation],
            },
        }

    # Ambiguous performance wording must not silently map to revenue.
    # A business analyst should ask which measurable outcome the user means.
    q_lower = (question or "").strip().lower()
    if (
        re.search(
            r"\b(performed well|performing well|did well|best performance|"
            r"good performance)\b",
            q_lower,
        )
        and not any(
            phrase in q_lower
            for phrase in (
                "revenue",
                "sales",
                "units",
                "quantity",
                "orders",
                "aov",
                "average order",
            )
        )
    ):
        return {
            "mode": "clarification",
            "answer": (
                "“Performed well” can mean different things. "
                "Do you mean highest revenue, most units sold, most orders, "
                "or highest average order value?"
            ),
            "steps": [],
            "recommendations": [],
            "limitations": [
                "No KPI was assumed because the question did not define performance."
            ],
            "confidence": "low",
            "evidence": {
                "question": question,
                "scope": (
                    "Current dashboard scope"
                    if st.session_state.get("ask_use_view_scope")
                    else "Full uploaded dataset"
                ),
                "rows_in_file": int(len(report.get("data", pd.DataFrame()))),
                "calculation": "No calculation performed; clarification required.",
                "source_fields": list(
                    report.get("data", pd.DataFrame()).columns
                ),
            },
        }

    structured = answer_sales_question_structured(
        report,
        question,
    )
    evidence = _safe_build_query_evidence(
        report.get("data", pd.DataFrame()),
        question,
        structured.get("plan", {}),
    )

    return {
        "mode": "deterministic",
        "answer": structured["answer"],
        "steps": [],
        "recommendations": [],
        "limitations": [],
        "confidence": "high",
        "evidence": evidence,
    }



def _render_profile(profile, quality, business_type):
    st.success(
        f"{profile['row_count']:,} rows and "
        f"{profile['column_count']} fields detected."
    )

    c1, c2, c3 = st.columns(3)

    primary_type = business_type.get(
        "primary_type"
    )

    available = set(
        profile.get(
            "recognized",
            {}
        ).keys()
    )

    if primary_type == "transactional_sales":
        type_ready = (
            {"date", "order_id", "customer", "product", "quantity"}
            .issubset(available)
            and bool(
                {"revenue", "price"} & available
            )
        )
    elif primary_type == "sales_pipeline":
        type_ready = (
            (
                "opportunity_id" in available
                or "order_id" in available
            )
            and "stage" in available
            and "amount" in available
        )
    elif primary_type == "subscription":
        type_ready = (
            "mrr" in available
            and (
                "customer" in available
                or "subscription_id" in available
            )
        )
    elif primary_type == "services":
        type_ready = (
            "hours" in available
            and (
                "billings" in available
                or "revenue" in available
                or "amount" in available
            )
        )
    else:
        type_ready = profile["readiness"] == "ready"

    row_count = int(profile.get("row_count", 0))
    column_count = int(profile.get("column_count", 0))
    useful_dimensions = len(profile.get("recognized", {}))
    analysis_areas = len([
        section
        for section in st.session_state.dashboard_plan.get("sections", [])
        if section["id"] not in {"overview", "attention", "performance", "ask", "report", "data_quality"}
    ])
    coverage_label = (
        "Limited" if row_count < 20
        else "Moderate" if row_count < 100
        else "Good"
    )

    c1.metric("Analysis readiness", "Ready" if type_ready else "Review")
    c2.metric("Business type", business_type["primary_label"])
    c3.metric(
        "Schema match",
        "Strong" if business_type["confidence"] >= 0.8
        else "Moderate" if business_type["confidence"] >= 0.6
        else "Needs review",
    )

    st.markdown(
        f"**Data coverage:** {coverage_label} — "
        f"{row_count:,} rows × {column_count:,} fields."
    )

    if row_count < 20:
        st.warning(
            "The dataset is small. Analysis is ready, but findings should be "
            "treated as directional until more records are available."
        )

    st.caption(
        f"I found {useful_dimensions} recognizable business dimensions and "
        f"{analysis_areas} analysis areas supported by this file."
    )

    if type_ready:
        st.markdown(
            f"**Your {business_type['primary_label'].lower()} data is ready for analysis.**"
        )
    else:
        st.markdown(
            f"**We need a little more information to analyze this "
            f"{business_type['primary_label'].lower()} dataset safely.**"
        )

    st.caption(
        quality_summary(
            quality
        )
    )

    with st.expander(
        "🔎 See what we found in your file"
    ):
        mapped_rows = []

        for concept, source_columns in profile[
            "recognized"
        ].items():
            for source_column in source_columns:
                mapped_rows.append(
                    {
                        "Your field": source_column,
                        "We understand it as": concept.replace(
                            "_",
                            " ",
                        ).title(),
                    }
                )

        if mapped_rows:
            st.dataframe(
                pd.DataFrame(
                    mapped_rows
                ),
                width="stretch",
                hide_index=True,
            )

        if profile["missing_core"]:
            st.warning(
                "Still need: "
                + ", ".join(
                    profile["missing_core"]
                )
            )

        if profile["unmapped_fields"]:
            st.info(
                "Additional fields found: "
                + ", ".join(
                    profile["unmapped_fields"]
                )
            )

    if quality["issue_count"]:
        with st.expander(
            "⚠️ Data quality checks"
        ):
            for issue in quality["issues"]:
                icon = {
                    "critical": "🔴",
                    "warning": "🟠",
                    "info": "🔵",
                }.get(
                    issue["severity"],
                    "ℹ️",
                )
                st.write(
                    f"{icon} **{issue['message']}**"
                )
                if issue["recommendation"]:
                    st.caption(
                        issue["recommendation"]
                    )


def _render_overview(
    report,
    analysis,
    business_type,
):
    brief = report.get("business_brief", {})
    st.subheader("🏠 Business Brief")

    coverage = brief.get("coverage", {})
    capability = brief.get("capabilities", {})
    st.caption(
        f"{business_type['primary_label']} • {coverage.get('period', 'uploaded dataset')} • "
        f"{coverage.get('rows', 0):,} rows • {capability.get('count', 0)} analysis capabilities"
    )

    snapshots = brief.get("snapshot", [])
    if snapshots:
        cols = st.columns(min(len(snapshots), 4))
        for idx, item in enumerate(snapshots[:4]):
            cols[idx].metric(
                item.get("label", "Metric"),
                item.get("value", "—"),
            )
        if len(snapshots) > 4:
            with st.expander("More business metrics"):
                more_cols = st.columns(min(len(snapshots[4:]), 4))
                for idx, item in enumerate(snapshots[4:8]):
                    more_cols[idx].metric(
                        item.get("label", "Metric"),
                        item.get("value", "—"),
                    )

    st.markdown("### What matters most")
    signals = brief.get("signals", [])[:3]
    only_no_signal = (
        bool(signals)
        and all(
            signal.get("type") == "no_material_signal"
            for signal in signals
        )
    )

    if only_no_signal:
        st.info(
            "No priority risk was detected from the available fields. "
            "That does not prove the business is healthy; use the opportunities "
            "and business-specific analysis below to decide what to investigate."
        )
    else:
        for index, signal in enumerate(signals):
            risk = signal.get("priority", 0) >= 60
            _render_finding_card(
                signal,
                index,
                risk=risk,
            )

    if brief.get("opportunities"):
        st.markdown("### Opportunities to explore")
        for item in brief["opportunities"][:3]:
            st.info(
                f"**{item.get('title', 'Opportunity')}** — {item.get('message', '')}"
            )

    st.markdown("### What this file supports")
    dim_labels = capability.get("dimensions", [])
    metric_labels = capability.get("metrics", [])
    if dim_labels:
        st.caption("Dimensions: " + ", ".join(dim_labels[:12]))
    if metric_labels:
        st.caption("Metrics: " + ", ".join(metric_labels[:12]))

    assumptions = brief.get("assumptions", [])
    limitations = brief.get("limitations", [])
    with st.expander("🔎 Analysis basis & limitations"):
        st.write(
            f"Schema match: **{coverage.get('schema_match', 'Unknown')}**. "
            f"Data coverage: **{coverage.get('coverage_label', 'Unknown')}**."
        )
        if assumptions:
            st.markdown("**Assumptions**")
            for item in assumptions:
                st.write(f"• {item}")
        if limitations:
            st.markdown("**Limitations**")
            for item in limitations:
                st.write(f"• {item}")

    st.caption(
        "The brief is evidence-first: it only surfaces metrics and signals that "
        "can be calculated from the fields detected in your file."
    )



def _ensure_business_action_plan(
    finding: dict,
    primary: str | None,
) -> dict:
    finding = dict(finding)
    if finding.get("recommended_action"):
        return finding

    message = finding.get("message", "")

    if primary == "subscription":
        if "churn" in message.lower():
            finding["what_happened"] = message
            finding["why_it_matters"] = (
                "Churn reduces recurring revenue and may create future renewal pressure "
                "if affected accounts are not addressed."
            )
            finding["recommended_action"] = (
                "Review churned customers, cancellation timing, plan mix, and stated loss "
                "reasons before the next renewal cycle."
            )
            finding["decision_question"] = (
                "Which customers churned, and what recurring revenue did they represent?"
            )
        elif "represents" in message.lower() and "mrr" in message.lower():
            finding["what_happened"] = message
            finding["why_it_matters"] = (
                "A large share of recurring revenue depends on one customer."
            )
            finding["recommended_action"] = (
                "Review that customer's renewal status and identify opportunities to "
                "diversify recurring revenue across other accounts."
            )
            finding["decision_question"] = (
                "Which plans and periods contribute most to this customer's MRR?"
            )

    elif primary == "sales_pipeline":
        finding["what_happened"] = message
        if "lost opportunities" in message.lower():
            finding["why_it_matters"] = (
                "More value is being lost than won in the current pipeline view."
            )
            finding["recommended_action"] = (
                "Break lost opportunities down by stage, owner, segment, and loss reason "
                "to identify where conversion is failing."
            )
            finding["decision_question"] = (
                "Which sales stage and owner account for the most lost value?"
            )
        elif "forecast" in message.lower():
            finding["why_it_matters"] = (
                "The weighted forecast represents only a limited portion of the expected "
                "pipeline, so the near-term outlook carries uncertainty."
            )
            finding["recommended_action"] = (
                "Review low-probability opportunities and focus sales effort on deals "
                "with credible close dates and stronger conversion signals."
            )
            finding["decision_question"] = (
                "Which opportunities make up the largest share of the weighted forecast?"
            )

    elif primary == "services":
        finding["what_happened"] = message
        if "client" in message.lower() and "billings" in message.lower():
            finding["why_it_matters"] = (
                "A large share of billings depends on one client."
            )
            finding["recommended_action"] = (
                "Review that client's billing trend and pipeline while identifying "
                "other accounts that can increase their share of billings."
            )
            finding["decision_question"] = (
                "Which services and periods generate the most billing from this client?"
            )

    return finding


def _render_finding_card(
    finding: dict,
    index: int,
    risk: bool = True,
):
    title = finding.get(
        "title",
        finding.get("message", "Review this finding."),
    )
    prefix = "🔴" if risk else "🟢"

    with st.container(border=True):
        st.markdown(
            f"### {prefix} {title}"
        )

        if finding.get("what_happened"):
            st.markdown(
                f"**What happened**  \n{finding['what_happened']}"
            )
        if finding.get("why_it_matters"):
            st.markdown(
                f"**Why it matters**  \n{finding['why_it_matters']}"
            )
        if finding.get("recommended_action"):
            st.markdown(
                f"**Recommended action**  \n{finding['recommended_action']}"
            )
        if finding.get("investigate_next"):
            st.markdown(
                f"**Investigate next**  \n{finding['investigate_next']}"
            )

        question = finding.get("decision_question")
        if question:
            if st.button(
                "💬 Investigate this",
                key=f"finding_followup_{index}_{'risk' if risk else 'positive'}",
            ):
                try:
                    result = _answer_business_question(
                        st.session_state.view_report or st.session_state.report,
                        question,
                    )
                    st.session_state.ask_question = question
                    st.session_state.ask_answer = result["answer"]
                    st.session_state.ask_answered_question = question
                    st.session_state.ask_agent_result = result
                    st.session_state.ask_use_view_scope = True
                except Exception:
                    st.session_state.ask_question = question
                    st.session_state.ask_answer = (
                        "I couldn't answer that investigation question "
                        "from the available data."
                    )
                    st.session_state.ask_answered_question = question
                    st.session_state.ask_agent_result = {
                        "mode": "error",
                        "answer": st.session_state.ask_answer,
                        "steps": [],
                        "recommendations": [],
                        "limitations": [
                            "The suggested investigation could not be "
                            "calculated from the available fields."
                        ],
                        "confidence": "low",
                    }

                st.session_state.active_dashboard_section = "ask"
                st.session_state.pending_review_section = "ask"
                st.rerun()


def _render_attention(report):
    st.subheader("🚦 What needs your attention")

    brief = report.get("business_brief", {})
    signals = brief.get("signals", [])

    if not signals:
        st.success(
            "No material exception was detected by the current evidence checks."
        )
        return

    st.caption(
        "These are ranked signals, not diagnoses. Each finding is based on "
        "the fields available in the uploaded file."
    )

    for index, signal in enumerate(signals[:5]):
        risk = signal.get("priority", 0) >= 60 and signal.get("type") != "trend_growth"
        _render_finding_card(
            signal,
            index,
            risk=risk,
        )



def _render_products(analysis):
    module = analysis["modules"].get("products")
    if not module or not module.get("available"):
        return

    st.subheader("📦 Products")

    table = pd.DataFrame(
        module["top_products"]
    )

    if not table.empty:
        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
        )

    concentration = module.get(
        "concentration"
    )
    if concentration:
        st.caption(
            f"{concentration['top_product']} contributes "
            f"{concentration['top_product_revenue_share_pct']:.1f}% "
            "of revenue."
        )


def _render_customers(analysis):
    module = analysis["modules"].get("customers")
    if not module or not module.get("available"):
        return

    st.subheader("👥 Customers")

    table = pd.DataFrame(
        module["top_customers"]
    )

    if not table.empty:
        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
        )

    concentration = module.get(
        "concentration"
    )
    if concentration:
        st.caption(
            f"{concentration['top_customer']} contributes "
            f"{concentration['top_customer_revenue_share_pct']:.1f}% "
            "of revenue."
        )


def _render_dimension(
    analysis,
    key,
    title,
):
    module = analysis["modules"].get(key)

    if not module or not module.get("available"):
        return

    st.subheader(title)

    table = pd.DataFrame(
        module.get(
            "ranked_values",
            [],
        )
    )

    if not table.empty:
        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
        )


def _render_discounts(analysis):
    module = analysis["modules"].get("discounts")
    if not module or not module.get("available"):
        return

    st.subheader("🏷️ Discounts")

    metrics = module.get(
        "metrics",
        {}
    )

    cols = st.columns(2)

    cols[0].metric(
        "Average discount",
        (
            f"{metrics['average_discount_pct']:.1f}%"
            if metrics.get("average_discount_pct") is not None
            else "—"
        ),
    )

    discount_amount = metrics.get("discount_amount")
    cols[1].metric(
        "Discount amount",
        (
            _format_currency(discount_amount)
            if discount_amount is not None
            else "Not available"
        ),
    )

    if discount_amount is None:
        st.caption(
            "Your file contains a discount percentage, but not the original "
            "pre-discount amount, so the actual discount value cannot be "
            "calculated reliably."
        )


def _render_returns(analysis):
    module = analysis["modules"].get("returns")
    if not module or not module.get("available"):
        return

    st.subheader("↩️ Returns")

    metrics = module.get(
        "metrics",
        {}
    )

    cols = st.columns(3)

    cols[0].metric(
        "Return rate",
        (
            f"{metrics['return_rate_pct']:.1f}%"
            if metrics.get("return_rate_pct") is not None
            else "—"
        ),
    )
    cols[1].metric(
        "Returned orders rate",
        (
            f"{metrics['returned_order_rate_pct']:.1f}%"
            if metrics.get("returned_order_rate_pct") is not None
            else "Not available"
        ),
    )

    return_amount = metrics.get("return_amount")
    cols[2].metric(
        "Returned value",
        (
            _format_currency(return_amount)
            if return_amount is not None
            else "Not available"
        ),
    )

    if metrics.get("return_amount_is_estimated"):
        st.caption(
            "Returned value is estimated from revenue on rows marked returned "
            "because the file does not contain a separate return-amount field."
        )
    elif (
        metrics.get("returned_order_rate_pct") is None
        or return_amount is None
    ):
        st.caption(
            "Some return metrics cannot be calculated because the file does "
            "not contain the required order or return-value fields."
        )


def _render_pipeline(packs):
    module = packs.get("packs", {}).get("sales_pipeline")
    if not module or not module.get("available"):
        st.info("Sales pipeline analysis is not available from the detected fields.")
        return

    st.subheader("📊 Sales pipeline")
    metrics = module.get("metrics", {})
    cols = st.columns(4)
    cols[0].metric("Open pipeline", _format_currency(metrics.get("open_pipeline_value", metrics.get("pipeline_value"))))
    cols[1].metric("Open opportunities", f"{metrics.get('open_opportunities', metrics.get('opportunities', 0)):,}")
    cols[2].metric("Won value", _format_currency(metrics.get("won_value")))
    cols[3].metric(
        "Value win rate",
        f"{metrics['value_win_rate_pct']:.1f}%" if metrics.get("value_win_rate_pct") is not None else "Not available",
    )

    st.caption(
        "Open pipeline excludes stages classified as won or lost. Win rate is value-based: won value ÷ (won + lost value)."
    )

    stage = pd.DataFrame(module.get("stage_breakdown", []))
    if not stage.empty:
        st.markdown("### Open pipeline by stage")
        st.dataframe(stage, width="stretch", hide_index=True)

    reps = pd.DataFrame(module.get("salesperson_breakdown", []))
    if not reps.empty:
        st.markdown("### Open pipeline by salesperson")
        reps = reps.rename(columns={"amount": "Open pipeline value"})
        st.dataframe(reps, width="stretch", hide_index=True)



def _render_subscription(packs, view="recurring_revenue"):
    module = packs.get("packs", {}).get("subscription")
    if not module or not module.get("available"):
        st.info("Recurring-revenue analysis is not available from the detected fields.")
        return

    metrics = module.get("metrics", {})

    if view == "recurring_revenue":
        st.subheader("🔁 Recurring revenue")
        cols = st.columns(3)
        cols[0].metric("MRR", _format_currency(metrics.get("mrr")))
        cols[1].metric("Annualized recurring revenue", _format_currency(metrics.get("annualized_revenue")))
        churn = metrics.get("churned_customer_rate_pct", metrics.get("churn_rate_pct"))
        cols[2].metric("Customer churn rate" if metrics.get("churned_customer_rate_pct") is not None else "Record churn rate", f"{churn:.1f}%" if churn is not None else "Not available")
        if metrics.get("snapshot_label"):
            st.caption(f"MRR snapshot used: {metrics['snapshot_label']}")

    elif view == "retention":
        st.subheader("🧲 Retention")
        if metrics.get("churned_customer_rate_pct") is not None:
            retained = 100 - metrics["churned_customer_rate_pct"]
            st.metric("Observed customer retention", f"{retained:.1f}%")
            st.caption("Retention here is the complement of the observed churn-status rate in the analyzed snapshot; it is not a cohort-retention curve.")
        else:
            st.info("A customer-level retention rate requires customer and churn-status fields. Historical cohort retention requires repeated period snapshots.")

    elif view == "churn":
        st.subheader("📉 Churn")
        cols = st.columns(2)
        churn = metrics.get("churned_customer_rate_pct")
        cols[0].metric("Customer churn rate", f"{churn:.1f}%" if churn is not None else "Not available")
        cols[1].metric("Churned customers", f"{metrics.get('churned_customers', 0):,}" if metrics.get("churned_customers") is not None else "Not available")
        if churn is None and metrics.get("churn_rate_pct") is not None:
            st.caption("Customer-level churn could not be calculated; the displayed churn metric is record-level.")



def _render_services(packs, view="services"):
    module = packs.get("packs", {}).get("services")
    if not module or not module.get("available"):
        st.info("Services analysis is not available from the detected fields.")
        return

    metrics = module.get("metrics", {})

    if view == "services":
        st.subheader("🧰 Services")
        cols = st.columns(3)
        cols[0].metric("Billings", _format_currency(metrics.get("billings")))
        cols[1].metric("Hours", f"{metrics.get('hours', 0):,.1f}")
        cols[2].metric("Revenue / hour", _format_currency(metrics.get("revenue_per_hour")))

    elif view == "billings":
        st.subheader("🧾 Billings by client")
        rows = module.get("client_breakdown", [])
        table = pd.DataFrame(rows)
        if not table.empty:
            table = table.rename(columns={"revenue": "Billings"})
            st.dataframe(table, width="stretch", hide_index=True)
        else:
            st.info("Client-level billings require a client/customer field.")

    elif view == "utilization":
        st.subheader("⏱️ Utilization by employee")
        rows = module.get("employee_breakdown", [])
        table = pd.DataFrame(rows)
        if not table.empty:
            table = table.rename(columns={"hours": "Hours"})
            st.dataframe(table, width="stretch", hide_index=True)
        else:
            st.info("Employee utilization requires an employee/consultant field.")




# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
st.title("📊 AI Business Analyst")
st.caption(
    "Upload the business data you already have. "
    "We'll understand the structure, find what matters, "
    "and show the analysis your data supports."
)

with st.expander(
    "📘 New here? See how it works",
    expanded=False,
):
    st.markdown(
        """
**1. Upload your file**  
CSV or Excel is fine.

**2. Let the app understand your data**  
We'll identify the fields, check data quality, and determine what analysis is available.

**3. Start with the business overview**  
You don't need to choose filters before seeing the main picture.

**4. Explore only what your data supports**  
Products, customers, regions, discounts, returns, pipeline, recurring revenue, services, and more appear only when the relevant fields exist.

**5. Ask your analyst**  
Ask questions in plain English.

**6. Download the executive report**  
Use the report for meetings and follow-up.
"""
    )

# ------------------------------------------------------------------
# Upload / profile
# ------------------------------------------------------------------
st.subheader("1️⃣ Upload your business file")

business_name = st.text_input(
    "Business name (optional)",
    value=st.session_state.business_name,
)
st.session_state.business_name = (
    business_name.strip()
    or "My Business"
)

uploaded = st.file_uploader(
    "CSV or Excel file",
    type=["csv", "xlsx", "xls"],
)

if uploaded is not None:
    # A newly selected file must never inherit the previous file's
    # business type, tabs, findings, or answers.
    uploaded_bytes = uploaded.getvalue()
    uploaded_key = hashlib.sha256(uploaded_bytes).hexdigest()

    if uploaded_key != st.session_state.uploaded_file_key:
        for key in [
            "source_df",
            "normalized_df",
            "profile",
            "semantic_model",
            "quality",
            "business_type",
            "adaptive_analysis",
            "business_packs",
            "dashboard_plan",
            "ask_answer",
            "ask_agent_result",
            "ask_answered_question",
            "ask_history",
            "report",
            "full_report",
            "view_report",
            "scope_active",
            "scope_product",
            "scope_customer",
            "scope_dates",
            "scope_filters",
            "scope_quality",
            "scope_adaptive_analysis",
            "scope_business_packs",
            "ask_use_view_scope",
            "pdf_file",
        ]:
            st.session_state[key] = None

        st.session_state.active_dashboard_section = "overview"
        st.session_state.review_section_nav = "overview"
        st.session_state.pending_review_section = None
        st.session_state.analysis_pending = True

    st.session_state.uploaded_file_key = uploaded_key

    if st.session_state.analysis_pending:
        st.info(
            f"New file selected: **{uploaded.name}**. "
            "Click **Understand my data** to analyze this file."
        )

        if st.button(
            "🔎 Understand my data",
            type="primary",
        ):

            with st.spinner(
                "Understanding your file..."
            ):
                (
                    raw_df,
                    normalized,
                    profile,
                    semantic,
                    quality,
                    business_type,
                    adaptive,
                    packs,
                    dashboard,
                ) = _process_upload(
                    uploaded
                )

            st.session_state.source_df = raw_df
            st.session_state.normalized_df = normalized
            st.session_state.profile = profile
            st.session_state.semantic_model = semantic
            st.session_state.quality = quality
            st.session_state.business_type = business_type
            st.session_state.adaptive_analysis = adaptive
            st.session_state.business_packs = packs
            st.session_state.dashboard_plan = dashboard
            st.session_state.report = None
            st.session_state.ask_answer = None
            st.session_state.ask_answered_question = ""
            st.session_state.ask_history = []
            st.session_state.pdf_file = None
            st.session_state.active_dashboard_section = "overview"
            st.session_state.review_section_nav = "overview"
            st.session_state.pending_review_section = None
            st.session_state.analysis_pending = False
            st.rerun()

if st.session_state.profile is not None and not st.session_state.analysis_pending:

    _render_profile(
        st.session_state.profile,
        st.session_state.quality,
        st.session_state.business_type,
    )

    available_sections = [
        section["title"]
        for section in st.session_state.dashboard_plan["sections"]
        if section["id"] not in {"overview", "attention", "performance", "ask", "report"}
    ]

    if available_sections:
        st.info(
            "Your file unlocks: "
            + ", ".join(available_sections)
        )

    dataset_usable = _dataset_is_usable(
        st.session_state.profile,
        st.session_state.business_type,
    )

    if dataset_usable:

        if st.session_state.report is None:
            if st.button(
                "🚀 Analyze my business",
                type="primary",
            ):

                with st.spinner(
                    "Analyzing your business..."
                ):

                    normalized = st.session_state.normalized_df
                    report = _build_report_context(
                        normalized,
                        st.session_state.business_type,
                        st.session_state.profile,
                        st.session_state.semantic_model,
                        st.session_state.adaptive_analysis,
                        st.session_state.business_packs,
                        st.session_state.quality,
                    )
                    st.session_state.report = report
                    st.session_state.full_report = report
                    st.session_state.view_report = report
                    st.session_state.scope_active = False
                    st.session_state.scope_product = "All"
                    st.session_state.scope_customer = "All"
                    st.session_state.scope_dates = None
                    st.session_state.scope_filters = {}
                    st.session_state.ask_use_view_scope = False

                st.success(
                    st.session_state.dashboard_plan[
                        "onboarding_message"
                    ]
                )
                st.rerun()

    else:
        st.error(
            "We couldn't safely build an analysis from this file yet. "
            "The file needs a recognizable set of fields for its detected "
            "business type. Check the field mapping above and try another file."
        )

# ------------------------------------------------------------------
# Analysis scope
# ------------------------------------------------------------------
if st.session_state.view_report is not None:
    full_df = st.session_state.normalized_df
    if isinstance(full_df, pd.DataFrame) and not full_df.empty:
        with st.expander(
            "🔎 Explore a subset of the business",
            expanded=False,
        ):
            st.caption(
                "Use this area to create a temporary dashboard view. "
                "The default is the full uploaded file."
            )

            primary_type = (
                st.session_state.get("business_type", {})
                .get("primary_type")
            )
            dimension_specs = available_scope_dimensions(
                full_df,
                primary_type,
                max_dimensions=2,
            )

            control_specs = []
            if "date" in full_df.columns:
                control_specs.append(("date", "Date range"))
            control_specs.extend(dimension_specs)

            readable_dimensions = [
                label for column, label in dimension_specs
            ]
            if readable_dimensions:
                st.caption(
                    "This view is available for every supported business type. "
                    "It only exposes dimensions found in the uploaded file: "
                    + ", ".join(readable_dimensions)
                    + ". It changes the dashboard view, not the source data."
                )
            elif "date" not in full_df.columns:
                st.info(
                    "No filterable date or categorical business dimensions were "
                    "found in this file, so there is no meaningful subset to create."
                )

            scope_cols = st.columns(max(1, min(3, len(control_specs))))
            date_range = None
            selected_dimensions: dict[str, str] = {}

            for idx, (column, label) in enumerate(control_specs):
                col = scope_cols[idx % len(scope_cols)]

                if column == "date":
                    dates = pd.to_datetime(
                        full_df["date"],
                        errors="coerce",
                    ).dropna()
                    if not dates.empty:
                        date_range = col.date_input(
                            "Date range",
                            value=(
                                dates.min().date(),
                                dates.max().date(),
                            ),
                            key="scope_date_input",
                        )
                    continue

                options = ["All"] + sorted(
                    full_df[column]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )
                selected = col.selectbox(
                    label,
                    options,
                    index=(
                        options.index(
                            st.session_state.get(
                                "scope_filters",
                                {},
                            ).get(column, "All")
                        )
                        if st.session_state.get(
                            "scope_filters",
                            {},
                        ).get(column, "All") in options
                        else 0
                    ),
                    key=f"scope_dimension_{column}",
                )
                selected_dimensions[column] = selected


            # A date range is valid only when both endpoints are selected.
            valid_date_range = (
                date_range is None
                or (
                    isinstance(date_range, tuple)
                    and len(date_range) == 2
                    and date_range[0] is not None
                    and date_range[1] is not None
                )
            )

            effective_date_range = (
                date_range
                if valid_date_range
                else None
            )

            # Preview the exact intersection before the user applies it.
            scope_preview = _apply_scope_filters(
                full_df,
                effective_date_range,
                dimension_filters=selected_dimensions,
            )

            # A full-source date range is not an active restriction.
            date_is_restrictive = False
            if (
                valid_date_range
                and date_range
                and "date" in full_df.columns
            ):
                all_dates = pd.to_datetime(
                    full_df["date"],
                    errors="coerce",
                ).dropna()
                if not all_dates.empty:
                    date_is_restrictive = (
                        date_range[0] != all_dates.min().date()
                        or date_range[1] != all_dates.max().date()
                    )

            active_filter_count = (
                int(date_is_restrictive)
                + sum(
                    value != "All"
                    for value in selected_dimensions.values()
                )
            )

            preview_cols = st.columns(3)
            preview_cols[0].metric(
                "Matching rows",
                f"{len(scope_preview):,}",
            )

            if (
                date_range is not None
                and not valid_date_range
            ):
                st.warning(
                    "Select both a start and end date before applying the view."
                )

            if not scope_preview.empty:
                if "revenue" in scope_preview.columns:
                    revenue_preview = pd.to_numeric(
                        scope_preview["revenue"],
                        errors="coerce",
                    ).sum()
                    preview_cols[1].metric(
                        "Revenue in view",
                        _format_currency(
                            revenue_preview
                        ),
                    )
                else:
                    preview_cols[1].metric(
                        "View status",
                        "Ready",
                    )

                preview_cols[2].metric(
                    "Active filters",
                    active_filter_count,
                )

                st.success(
                    f"{len(scope_preview):,} rows match the selected view."
                )
            else:
                # Explain why the combination cannot work instead of making
                # Apply appear to do nothing.
                coverage_parts = []
                for column, selected in selected_dimensions.items():
                    if selected == "All" or column not in full_df.columns:
                        continue
                    matches = full_df.loc[
                        full_df[column].astype(str) == str(selected)
                    ]
                    if not matches.empty and "date" in full_df.columns:
                        dim_dates = pd.to_datetime(
                            matches["date"],
                            errors="coerce",
                        ).dropna()
                        if not dim_dates.empty:
                            coverage_parts.append(
                                f"{selected} has data from "
                                f"{dim_dates.min().strftime('%d %b %Y')} "
                                f"to {dim_dates.max().strftime('%d %b %Y')}"
                            )

                st.warning(
                    "This filter combination matches 0 rows."
                    + (
                        " " + " ".join(coverage_parts) + "."
                        if coverage_parts
                        else ""
                    )
                    + " Broaden the date range or remove a dimension filter."
                )


            apply_col, reset_col = st.columns(
                [1, 1]
            )

            with apply_col:
                apply_scope = st.button(
                    "Apply view",
                    type="primary",
                    disabled=(
                        scope_preview.empty
                        or not valid_date_range
                    ),
                )

            with reset_col:
                reset_scope = st.button(
                    "Show full business"
                )

            if apply_scope:
                st.session_state.scope_filters = dict(
                    selected_dimensions
                )
                st.session_state.scope_product = selected_dimensions.get(
                    "product",
                    "All",
                )
                st.session_state.scope_customer = selected_dimensions.get(
                    "customer",
                    "All",
                )
                st.session_state.scope_dates = effective_date_range
                st.session_state.scope_active = True

                scope_df = scope_preview.copy()

                # Recompute every downstream analytical layer from the scoped
                # dataframe. Otherwise Retail appeared filtered while
                # Pipeline/Subscription/Services still showed full-file metrics.
                scope_quality = run_data_quality_checks(
                    scope_df,
                    st.session_state.semantic_model,
                )
                scope_adaptive = analyze_modules(
                    scope_df,
                    st.session_state.semantic_model,
                    scope_quality,
                )
                scope_packs = run_business_type_packs(
                    scope_df,
                    st.session_state.business_type,
                )

                scope_profile = dict(
                    st.session_state.profile
                )
                scope_profile["row_count"] = len(scope_df)
                scope_profile["column_count"] = len(scope_df.columns)

                scope_report = _build_report_context(
                    scope_df,
                    st.session_state.business_type,
                    scope_profile,
                    st.session_state.semantic_model,
                    scope_adaptive,
                    scope_packs,
                    scope_quality,
                    scope_filters=selected_dimensions,
                    scope_dates=date_range,
                )

                st.session_state.scope_quality = scope_quality
                st.session_state.scope_adaptive_analysis = scope_adaptive
                st.session_state.scope_business_packs = scope_packs
                st.session_state.view_report = scope_report
                st.session_state.report = scope_report
                st.rerun()

            if reset_scope:
                st.session_state.scope_active = False
                st.session_state.scope_product = "All"
                st.session_state.scope_customer = "All"
                st.session_state.scope_dates = None
                st.session_state.scope_filters = {}
                st.session_state.scope_quality = None
                st.session_state.scope_adaptive_analysis = None
                st.session_state.scope_business_packs = None
                st.session_state.view_report = None
                st.session_state.report = st.session_state.full_report
                st.rerun()

        if st.session_state.scope_active:
            st.info(
                "Dashboard scope: "
                + ", ".join(
                    part
                    for part in [
                        *[
                            f"{key}={value}"
                            for key, value in st.session_state.get(
                                "scope_filters",
                                {},
                            ).items()
                            if value != "All"
                        ],
                        (
                            "custom date range"
                            if st.session_state.scope_dates
                            else None
                        ),
                    ]
                    if part
                )
                or "filtered view",
            )


# ------------------------------------------------------------------
# Adaptive dashboard
# ------------------------------------------------------------------
if (
    st.session_state.report is not None
    and st.session_state.dashboard_plan is not None
):

    plan = st.session_state.dashboard_plan
    report = st.session_state.view_report or st.session_state.report
    analysis = (
        st.session_state.scope_adaptive_analysis
        if st.session_state.get("scope_active")
        and st.session_state.get("scope_adaptive_analysis") is not None
        else st.session_state.adaptive_analysis
    )
    packs = (
        st.session_state.scope_business_packs
        if st.session_state.get("scope_active")
        and st.session_state.get("scope_business_packs") is not None
        else st.session_state.business_packs
    )

    st.divider()

    st.subheader(
        f"2️⃣ {plan['primary_cta']}"
    )

    section_options = {
        section["id"]: f"{section['icon']} {section['title']}"
        for section in plan["sections"]
    }
    section_ids = list(section_options.keys())
    current_section = st.session_state.get(
        "active_dashboard_section",
        "overview",
    )
    if current_section not in section_ids:
        current_section = section_ids[0]
        st.session_state.active_dashboard_section = current_section

    # Single source of truth: the selected widget return value is the section
    # rendered in this run. Programmatic navigation is selected before the
    # widget is created, without a second persistent navigation widget.
    pending_section = st.session_state.get(
        "pending_review_section"
    )
    if pending_section in section_ids:
        current_section = pending_section
        st.session_state.pending_review_section = None
    else:
        current_section = st.session_state.get(
            "active_dashboard_section",
            "overview",
        )

    if current_section not in section_ids:
        current_section = section_ids[0]

    if len(section_ids) <= 8:
        selected_section = st.segmented_control(
            "Review section",
            options=section_ids,
            selection_mode="single",
            format_func=lambda sid: section_options[sid],
            label_visibility="collapsed",
            width="stretch",
            index=section_ids.index(current_section),
        )
    else:
        selected_section = st.selectbox(
            "Review section",
            options=section_ids,
            index=section_ids.index(current_section),
            format_func=lambda sid: section_options[sid],
            label_visibility="collapsed",
        )

    selected_section = selected_section or current_section
    st.session_state.active_dashboard_section = selected_section
    sid = selected_section


    if sid == "overview":
        _render_overview(
            report,
            analysis,
            st.session_state.business_type,
        )

    elif sid == "attention":
        _render_attention(
            report
        )

    elif sid == "performance":
        module = analysis["modules"].get(
            "sales_performance"
        )

        if module and module.get("monthly"):
            st.subheader(
                "📈 Monthly performance"
            )
            monthly = pd.DataFrame(
                module["monthly"]
            )
            if not monthly.empty:
                monthly_display = monthly.rename(
                    columns={
                        "_month": "Month",
                        "revenue": "Revenue",
                        "orders": "Orders",
                        "quantity": "Units",
                        "aov": "AOV",
                    }
                )
                st.line_chart(
                    monthly_display.set_index(
                        "Month"
                    )[["Revenue"]]
                )
                st.dataframe(
                    monthly_display,
                    width="stretch",
                    hide_index=True,
                )
        else:
            primary = st.session_state.business_type.get(
                "primary_type"
            )

            if primary == "sales_pipeline":
                pipeline = packs.get("packs", {}).get("sales_pipeline")
                if pipeline and pipeline.get("available"):
                    metrics = pipeline.get("metrics", {})
                    st.subheader("📈 Pipeline performance")
                    cols = st.columns(4)
                    cols[0].metric("Pipeline", _format_currency(metrics.get("pipeline_value")))
                    cols[1].metric("Opportunities", f"{metrics.get('opportunities', 0):,}")
                    cols[2].metric("Won", _format_currency(metrics.get("won_value")))
                    cols[3].metric(
                        "Value win rate",
                        (
                            f"{metrics['win_rate_pct']:.1f}%"
                            if metrics.get("win_rate_pct") is not None
                            else "—"
                        ),
                    )

            elif primary == "subscription":
                subscription = packs.get("packs", {}).get("subscription")
                if subscription and subscription.get("available"):
                    metrics = subscription.get("metrics", {})
                    st.subheader("📈 Recurring revenue performance")
                    cols = st.columns(3)
                    cols[0].metric("MRR", _format_currency(metrics.get("mrr")))
                    cols[1].metric(
                        "Annualized revenue",
                        _format_currency(metrics.get("annualized_revenue")),
                    )
                    cols[2].metric(
                        "Churn",
                        (
                            f"{metrics['churn_rate_pct']:.1f}%"
                            if metrics.get("churn_rate_pct") is not None
                            else "—"
                        ),
                    )

            elif primary == "services":
                services = packs.get("packs", {}).get("services")
                if services and services.get("available"):
                    metrics = services.get("metrics", {})
                    st.subheader("📈 Services performance")
                    cols = st.columns(3)
                    cols[0].metric("Billings", _format_currency(metrics.get("billings")))
                    cols[1].metric(
                        "Hours",
                        (
                            f"{metrics.get('hours', 0):,.1f}"
                            if metrics.get("hours") is not None
                            else "—"
                        ),
                    )
                    cols[2].metric(
                        "Revenue / hour",
                        _format_currency(metrics.get("revenue_per_hour")),
                    )

    elif sid == "products":
        _render_products(
            analysis
        )

    elif sid == "customers":
        _render_customers(
            analysis
        )

    elif sid == "regions":
        _render_dimension(
            analysis,
            "region",
            "🌎 Regions",
        )

    elif sid == "sales_team":
        _render_dimension(
            analysis,
            "salesperson",
            "🎯 Sales Team",
        )

    elif sid == "channels":
        _render_dimension(
            analysis,
            "channel",
            "🛒 Channels",
        )

    elif sid == "payments":
        _render_dimension(
            analysis,
            "payment_method",
            "💳 Payments",
        )

    elif sid == "order_status":
        _render_dimension(
            analysis,
            "order_status",
            "📋 Order Status",
        )

    elif sid == "discounts":
        _render_discounts(
            analysis
        )

    elif sid == "returns":
        _render_returns(
            analysis
        )

    elif sid == "profitability":
        module = analysis["modules"].get(
            "profitability"
        )
        if module and module.get("available"):
            st.subheader(
                "💰 Costs & Margin"
            )
            metrics = module["metrics"]
            cols = st.columns(4)
            cols[0].metric(
                "Revenue",
                _format_currency(
                    metrics.get("revenue")
                ),
            )
            cols[1].metric(
                "Cost",
                _format_currency(
                    metrics.get("cost")
                ),
            )
            cols[2].metric(
                "Gross margin",
                _format_currency(
                    metrics.get("gross_margin")
                ),
            )
            cols[3].metric(
                "Margin %",
                (
                    f"{metrics['gross_margin_pct']:.1f}%"
                    if metrics.get("gross_margin_pct") is not None
                    else "—"
                ),
            )

    elif sid == "pipeline":
        _render_pipeline(
            packs
        )

    elif sid == "forecast":
        forecast = packs.get(
            "packs",
            {}
        ).get(
            "forecast"
        )

        if forecast and forecast.get("available"):
            st.subheader("🔮 Sales Forecast")

            metrics = forecast.get(
                "metrics",
                {}
            )

            cols = st.columns(3)
            cols[0].metric(
                "Open pipeline",
                _format_currency(
                    metrics.get("open_pipeline_value", metrics.get("pipeline_value"))
                ),
            )
            cols[1].metric(
                "Weighted forecast",
                _format_currency(
                    metrics.get("weighted_forecast")
                ),
            )
            cols[2].metric(
                "Opportunities",
                f"{metrics.get('opportunities', 0):,}",
            )

            monthly = pd.DataFrame(
                forecast.get(
                    "monthly_forecast",
                    [],
                )
            )

            if not monthly.empty:
                display = monthly.rename(
                    columns={
                        "month": "Expected close",
                        "expected_value": "Expected value",
                        "weighted_forecast": "Weighted forecast",
                        "opportunities": "Opportunities",
                    }
                )
                st.dataframe(
                    display,
                    width="stretch",
                    hide_index=True,
                )

            for note in forecast.get(
                "notes",
                [],
            ):
                st.info(note)
        else:
            st.info(
                "Forecast is unavailable because the file does not "
                "contain enough information to estimate expected sales. "
                "Add an expected close date and opportunity amount."
            )

    elif sid == "recurring_revenue":
        _render_subscription(
            packs,
            "recurring_revenue",
        )

    elif sid == "retention":
        _render_subscription(
            packs,
            "retention",
        )

    elif sid == "churn":
        _render_subscription(
            packs,
            "churn",
        )

    elif sid == "services":
        _render_services(
            packs,
            "services",
        )

    elif sid == "billings":
        _render_services(
            packs,
            "billings",
        )

    elif sid == "utilization":
        _render_services(
            packs,
            "utilization",
        )

    elif sid == "ask":
        st.subheader(
            "💬 Ask Your Business Analyst"
        )
        st.caption(
            "Ask a question in plain English. "
            "Answers are calculated from the uploaded dataset."
        )

        history = st.session_state.get("ask_history", [])
        if history:
            with st.expander("🕘 Recent questions", expanded=False):
                for item in reversed(history[-5:]):
                    st.caption(item["question"])

        use_view_scope = st.checkbox(
            "Use the current dashboard scope for this question",
            value=st.session_state.get("ask_use_view_scope", False),
            disabled=not st.session_state.get("scope_active", False),
            help="By default questions use the full uploaded file. Turn this on to ask about the filtered dashboard view.",
        )
        st.session_state.ask_use_view_scope = use_view_scope
        qna_report = (
            st.session_state.view_report
            if use_view_scope and st.session_state.get("view_report") is not None
            else st.session_state.full_report
        )

        question = st.text_input(
            "What would you like to know about your business?",
            placeholder=(
                "e.g. Which product made the most revenue in August?"
            ),
            value=st.session_state.ask_question,
        )

        # Do not keep showing an answer to an older question after the user
        # edits the input. This was the main source of "wrong answers" in the
        # recorded walkthrough.
        current_question = question.strip()
        answered_question = st.session_state.get(
            "ask_answered_question",
            "",
        )

        if (
            current_question
            and answered_question
            and current_question != answered_question
        ):
            st.info(
                "New question detected. Click Get Business Answer to calculate "
                "the new answer."
            )

        col_answer, col_clear = st.columns(
            [1, 1]
        )

        with col_answer:
            if st.button(
                "💬 Get Business Answer",
                type="primary",
            ):
                if current_question:
                    try:
                        result = _answer_business_question(
                            qna_report,
                            current_question,
                        )
                        st.session_state.ask_answer = result["answer"]
                        st.session_state.ask_agent_result = result
                        st.session_state.ask_question = current_question
                        st.session_state.ask_answered_question = current_question
                        history = st.session_state.get("ask_history", [])
                        history.append({"question": current_question, "answer": result["answer"]})
                        st.session_state.ask_history = history[-5:]
                    except Exception as exc:
                        st.session_state.ask_answer = (
                            "I couldn't answer that question from the "
                            "available data."
                        )
                        st.session_state.ask_agent_result = {
                            "mode": "error",
                            "answer": st.session_state.ask_answer,
                            "steps": [],
                            "recommendations": [],
                            "limitations": [],
                            "confidence": "low",
                        }
                        st.exception(exc)
                else:
                    st.warning(
                        "Enter a question first."
                    )

        with col_clear:
            if st.button(
                "🧹 Clear",
            ):
                st.session_state.ask_question = ""
                st.session_state.ask_answer = None
                st.session_state.ask_answered_question = ""
                st.session_state.ask_agent_result = None
                st.session_state.ask_history = []
                st.session_state.ask_use_view_scope = False
                st.rerun()

        # Only display an answer when it belongs to the currently entered
        # question.
        if (
            st.session_state.ask_answer
            and current_question == answered_question
        ):
            st.markdown("#### Answer")

            st.success(
                st.session_state.ask_answer
            )

            result_evidence = (
                st.session_state.get("ask_agent_result", {})
                .get("evidence")
            )
            if result_evidence:
                with st.expander("🔎 How this answer was calculated"):
                    st.write(f"**Scope:** {result_evidence.get('scope', 'Not specified')}")
                    st.write(f"**Calculation:** {result_evidence.get('calculation', result_evidence.get('operation', 'Verified business metric'))}")
                    st.write(f"**Rows available:** {result_evidence.get('rows_in_file', len(report.get('data', []))):,}")
                    fields = result_evidence.get("source_fields", [])
                    if fields:
                        st.write("**Source fields:** " + ", ".join(fields))
                    filters = result_evidence.get("filters", {})
                    if filters:
                        st.write("**Filters:** " + ", ".join(f"{k}={v}" for k,v in filters.items()))

            agent_result = st.session_state.get(
                "ask_agent_result"
            )

            if (
                agent_result
                and agent_result.get("mode") == "agent"
            ):
                with st.expander(
                    "🔎 How the analyst investigated this"
                ):
                    for step in agent_result.get("steps", []):
                        st.write(
                            f"• {step.get('finding', '')}"
                        )

                    recommendations = agent_result.get(
                        "recommendations", []
                    )
                    if recommendations:
                        st.markdown(
                            "**What to look at next**"
                        )
                        for item in recommendations:
                            st.write(
                                f"• {item}"
                            )

                    limitations = agent_result.get(
                        "limitations", []
                    )
                    if limitations:
                        st.caption(
                            "Note: " + " ".join(limitations)
                        )


    elif sid == "report":
        st.subheader(
            "📄 Executive Report"
        )
        st.caption(
            "Review the key story first, then download the same "
            "summary as a shareable PDF."
        )

        report_kpis = report.get(
            "kpis",
            {}
        )
        primary = st.session_state.business_type.get(
            "primary_type"
        )

        st.markdown("### Executive summary")

        if primary == "transactional_sales":
            cols = st.columns(4)
            cols[0].metric(
                "Revenue",
                _format_currency(
                    report_kpis.get("total_revenue")
                ),
            )
            cols[1].metric(
                "Orders",
                f"{report_kpis.get('total_orders', 0):,}",
            )
            cols[2].metric(
                "Units",
                (
                    f"{report_kpis.get('total_quantity', 0):,.0f}"
                    if report_kpis.get("total_quantity") is not None
                    else "—"
                ),
            )
            cols[3].metric(
                "AOV",
                _format_currency(
                    report_kpis.get("average_order_value")
                ),
            )

        elif primary == "sales_pipeline":
            module = packs.get("packs", {}).get("sales_pipeline")
            if module and module.get("available"):
                metrics = module.get("metrics", {})
                cols = st.columns(4)
                cols[0].metric(
                    "Pipeline",
                    _format_currency(metrics.get("pipeline_value")),
                )
                cols[1].metric(
                    "Opportunities",
                    f"{metrics.get('opportunities', 0):,}",
                )
                cols[2].metric(
                    "Won",
                    _format_currency(metrics.get("won_value")),
                )
                cols[3].metric(
                    "Value win rate",
                    (
                        f"{metrics['win_rate_pct']:.1f}%"
                        if metrics.get("win_rate_pct") is not None
                        else "—"
                    ),
                )

        elif primary == "subscription":
            module = packs.get("packs", {}).get("subscription")
            if module and module.get("available"):
                metrics = module.get("metrics", {})
                cols = st.columns(3)
                cols[0].metric(
                    "MRR",
                    _format_currency(metrics.get("mrr")),
                )
                cols[1].metric(
                    "Annualized revenue",
                    _format_currency(metrics.get("annualized_revenue")),
                )
                cols[2].metric(
                    "Churn",
                    (
                        f"{metrics['churn_rate_pct']:.1f}%"
                        if metrics.get("churn_rate_pct") is not None
                        else "—"
                    ),
                )

        elif primary == "services":
            module = packs.get("packs", {}).get("services")
            if module and module.get("available"):
                metrics = module.get("metrics", {})
                cols = st.columns(3)
                cols[0].metric(
                    "Billings",
                    _format_currency(metrics.get("billings")),
                )
                cols[1].metric(
                    "Hours",
                    f"{metrics.get('hours', 0):,.1f}",
                )
                cols[2].metric(
                    "Revenue / hour",
                    _format_currency(metrics.get("revenue_per_hour")),
                )

        brief = report.get("business_brief", {})
        signals = brief.get("signals", [])[:3]
        if signals:
            st.markdown("### Key findings")
            for finding in signals:
                title = finding.get("title", finding.get("message", "Review this finding."))
                st.markdown(f"**• {title}**")
                if finding.get("why_it_matters"):
                    st.caption(f"Why it matters: {finding['why_it_matters']}")
                if finding.get("recommended_action"):
                    st.write(f"**Recommended action:** {finding['recommended_action']}")

        st.markdown("### Recommended next steps")
        if signals:
            for finding in signals:
                action = finding.get("recommended_action")
                if action:
                    st.write(f"• {action}")
        else:
            st.write("• Review the business-specific sections and investigate the metric that matters most to you.")
        st.write(
            "• Use Ask Your Business Analyst for a verified follow-up question; the answer will show its calculation basis."
        )

        if st.button(
            "📄 Create Executive PDF",
        ):
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".pdf",
            ) as tmp:
                pdf_path = tmp.name

            try:
                generate_adaptive_pdf(
                    pdf_path,
                    st.session_state.business_name,
                    st.session_state.business_type,
                    st.session_state.profile,
                    analysis,
                    st.session_state.quality,
                    packs,
                    report.get("business_brief"),
                )

                with open(
                    pdf_path,
                    "rb",
                ) as handle:
                    st.session_state.pdf_file = handle.read()

            finally:
                try:
                    os.unlink(pdf_path)
                except OSError:
                    pass

        if st.session_state.pdf_file:
            st.download_button(
                "⬇️ Download Executive PDF",
                data=st.session_state.pdf_file,
                file_name=(
                    f"{st.session_state.business_name}"
                    "_business_report.pdf"
                ),
                mime="application/pdf",
            )

    elif sid == "data_quality":
        st.subheader(
            "✅ Data Quality"
        )
        st.write(
            quality_summary(
                st.session_state.quality
            )
        )

        for issue in st.session_state.quality[
            "issues"
        ]:
            st.write(
                f"• {issue['message']}"
            )

# ------------------------------------------------------------------
# Runtime self-test
# ------------------------------------------------------------------
# Use ?diagnostics=1 in the Streamlit URL, or set ENABLE_DIAGNOSTICS=1,
# to expose the diagnostic panel. The tests run inside the actual live
# Streamlit process and call the same application helpers used by users.
diagnostics_requested = (
    os.getenv("ENABLE_DIAGNOSTICS", "").strip() == "1"
    or str(
        st.query_params.get(
            "diagnostics",
            "",
        )
    ).lower()
    in {
        "1",
        "true",
        "yes",
    }
)

if diagnostics_requested:
    from runtime_diagnostics import run_runtime_diagnostics

    st.divider()
    st.subheader("🧪 Runtime diagnostics")
    st.caption(
        "Developer validation mode. These checks run inside the live "
        "Streamlit process against the bundled representative business files."
    )

    if st.button(
        "▶️ Run full runtime self-test",
        type="primary",
    ):
        with st.spinner(
            "Running the live application self-test..."
        ):
            diagnostic_results = run_runtime_diagnostics(
                sys.modules[__name__],
                Path(__file__).resolve().parent / "samples",
            )

        passed = sum(
            result["status"] == "PASS"
            for result in diagnostic_results
        )
        failed = len(diagnostic_results) - passed

        for result in diagnostic_results:
            icon = (
                "✅"
                if result["status"] == "PASS"
                else "❌"
            )
            with st.container(border=True):
                st.markdown(
                    f"**{icon} {result['test']}**"
                )
                st.caption(
                    result["details"]
                )

        from runtime_diagnostics import run_release_contract_diagnostics

        contract_results = run_release_contract_diagnostics(
            sys.modules[__name__],
            Path(__file__).resolve().parent,
        )
        contract_failed = [
            result for result in contract_results
            if result["status"] != "PASS"
        ]

        total_checks = len(diagnostic_results) + len(contract_results)
        total_passed = passed + (
            len(contract_results) - len(contract_failed)
        )
        total_failed = failed + len(contract_failed)

        d1, d2, d3 = st.columns(3)
        d1.metric("Checks", total_checks)
        d2.metric("Passed", total_passed)
        d3.metric("Failed", total_failed)

        st.markdown("### Runtime checks")
        for result in contract_results:
            icon = (
                "✅" if result["status"] == "PASS"
                else "❌"
            )
            with st.container(border=True):
                st.markdown(
                    f"**{icon} {result['test']}**"
                )
                st.caption(
                    result["details"]
                )

        if total_failed == 0:
            st.success(
                "All runtime diagnostics and release gates passed."
            )
        else:
            st.error(
                f"{total_failed} release check(s) failed. "
                "Review the failed items above before deployment."
            )

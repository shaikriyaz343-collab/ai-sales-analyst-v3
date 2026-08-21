
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any
import re

import pandas as pd


class DiagnosticUpload:
    """Small UploadedFile-compatible object for runtime self-tests."""

    def __init__(self, path: Path):
        self.name = path.name
        self._bytes = path.read_bytes()

    def getvalue(self) -> bytes:
        return self._bytes


def _case_result(name: str, passed: bool, details: str) -> dict[str, Any]:
    return {
        "test": name,
        "status": "PASS" if passed else "FAIL",
        "details": details,
    }


def run_runtime_diagnostics(
    app_module,
    sample_dir: Path,
) -> list[dict[str, Any]]:
    """
    Execute the application's real runtime helpers inside the Streamlit
    process that is currently serving the app.

    This deliberately calls the same helpers used by the live UI instead of
    reimplementing their logic in a separate test harness.
    """
    results: list[dict[str, Any]] = []

    sample_names = [
        "retail.csv",
        "pipeline.csv",
        "subscription.csv",
        "services.csv",
    ]

    originals = {
        key: app_module.st.session_state.get(key)
        for key in (
            "source_df",
            "normalized_df",
            "profile",
            "semantic_model",
            "quality",
            "business_type",
            "adaptive_analysis",
            "business_packs",
            "dashboard_plan",
            "report",
            "full_report",
            "view_report",
            "business_name",
            "ask_question",
            "ask_answer",
            "ask_answered_question",
            "ask_agent_result",
            "ask_history",
            "scope_active",
            "scope_product",
            "scope_customer",
            "scope_dates",
            "scope_filters",
            "ask_use_view_scope",
            "active_dashboard_section",
            "pdf_file",
        )
    }

    try:
        for sample_name in sample_names:
            path = sample_dir / sample_name

            if not path.exists():
                results.append(
                    _case_result(
                        sample_name,
                        False,
                        "Sample dataset is missing from the package.",
                    )
                )
                continue

            upload = DiagnosticUpload(path)

            try:
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
                ) = app_module._process_upload(upload)

                assert len(raw_df) > 0
                assert profile["row_count"] == len(raw_df)
                assert profile["column_count"] == len(raw_df.columns)
                assert business_type["primary_label"]

                section_ids = [
                    section["id"]
                    for section in dashboard["sections"]
                ]

                assert "overview" in section_ids
                assert "attention" in section_ids
                assert "ask" in section_ids
                assert "report" in section_ids

                results.append(
                    _case_result(
                        f"{sample_name} — upload/profile",
                        True,
                        (
                            f"{business_type['primary_label']}; "
                            f"{profile['row_count']} rows × "
                            f"{profile['column_count']} fields; "
                            f"{len(section_ids)} review sections."
                        ),
                    )
                )

                # Exercise the same session-state objects used by the UI.
                st = app_module.st
                assignments = {
                    "source_df": raw_df,
                    "normalized_df": normalized,
                    "profile": profile,
                    "semantic_model": semantic,
                    "quality": quality,
                    "business_type": business_type,
                    "adaptive_analysis": adaptive,
                    "business_packs": packs,
                    "dashboard_plan": dashboard,
                    "business_name": "Runtime Diagnostic Business",
                    "active_dashboard_section": "overview",
                }
                for key, value in assignments.items():
                    st.session_state[key] = value

                report = app_module._build_report_context(
                    normalized,
                    business_type,
                    profile,
                    semantic,
                    adaptive,
                    packs,
                    quality,
                )
                assert report["data"] is not None
                assert report["data"].shape[0] == normalized.shape[0]

                st.session_state.report = report

                results.append(
                    _case_result(
                        f"{sample_name} — analysis/report",
                        True,
                        "Report context built from the same live runtime path.",
                    )
                )

                # Build the PDF through the same generator called by the UI.
                with tempfile.NamedTemporaryFile(
                    suffix=".pdf",
                    delete=False,
                ) as handle:
                    pdf_path = Path(handle.name)

                try:
                    app_module.generate_adaptive_pdf(
                        str(pdf_path),
                        "Runtime Diagnostic Business",
                        business_type,
                        profile,
                        adaptive,
                        quality,
                        packs,
                    )
                    assert pdf_path.exists()
                    assert pdf_path.stat().st_size > 1000
                    results.append(
                        _case_result(
                            f"{sample_name} — executive PDF",
                            True,
                            f"Generated {pdf_path.stat().st_size:,} bytes.",
                        )
                    )
                finally:
                    pdf_path.unlink(missing_ok=True)

                # Business-specific feature gates: verify the modules users
                # actually see are available from the same live processing path.
                primary = business_type.get("primary_type")
                if primary == "transactional_sales":
                    module = adaptive.get("modules", {}).get("sales_performance", {})
                    required_modules = [
                        "products",
                        "customers",
                        "region",
                        "discounts",
                        "returns",
                        "payment_method",
                    ]
                    passed_feature = bool(
                        module.get("available")
                        and all(
                            adaptive.get("modules", {}).get(
                                key,
                                {},
                            ).get("available")
                            for key in required_modules
                        )
                    )
                    feature_details = (
                        "Sales performance plus product/customer/region/discount/return/payment "
                        "analysis modules are available."
                    )

                elif primary == "sales_pipeline":
                    pipe = packs.get("packs", {}).get("sales_pipeline", {})
                    fc = packs.get("packs", {}).get("forecast", {})
                    passed_feature = bool(
                        pipe.get("available")
                        and pipe.get("metrics", {}).get("open_pipeline_value") is not None
                        and fc.get("available")
                    )
                    feature_details = (
                        "Open pipeline metrics and forecast are available."
                    )

                elif primary == "subscription":
                    sub = packs.get("packs", {}).get("subscription", {})
                    passed_feature = bool(
                        sub.get("available")
                        and sub.get("metrics", {}).get("mrr") is not None
                    )
                    feature_details = (
                        "Recurring revenue metrics are available."
                    )

                elif primary == "services":
                    svc = packs.get("packs", {}).get("services", {})
                    passed_feature = bool(
                        svc.get("available")
                        and svc.get("metrics", {}).get("billings") is not None
                        and svc.get("metrics", {}).get("hours") is not None
                    )
                    feature_details = (
                        "Services billings and utilization metrics are available."
                    )
                else:
                    passed_feature = False
                    feature_details = "No business-specific feature contract exists."

                results.append(
                    _case_result(
                        f"{sample_name} — business-specific features",
                        passed_feature,
                        feature_details,
                    )
                )

                scope_primary = business_type.get("primary_type")
                scope_dimensions = app_module.available_scope_dimensions(
                    normalized,
                    scope_primary,
                    max_dimensions=2,
                )
                expected_scope = {
                    "transactional_sales": {"product", "customer"},
                    "sales_pipeline": {"salesperson", "stage"},
                    "subscription": {"customer", "plan"},
                    "services": {"client", "service"},
                }.get(scope_primary, set())
                actual_scope = {name for name, _ in scope_dimensions}
                scope_ok = expected_scope.issubset(actual_scope)
                results.append(
                    _case_result(
                        f"{sample_name} — adaptive scope dimensions",
                        scope_ok,
                        "Exposes business-relevant filters: "
                        + ", ".join(label for _, label in scope_dimensions),
                    )
                )

            except Exception as exc:
                results.append(
                    _case_result(
                        f"{sample_name} — runtime path",
                        False,
                        f"{type(exc).__name__}: {exc}",
                    )
                )

        # Retail Q&A: run through the live router, not the test module.
        retail = sample_dir / "retail.csv"
        if retail.exists():
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
            ) = app_module._process_upload(
                DiagnosticUpload(retail)
            )
            app_module.st.session_state.business_type = business_type
            app_module.st.session_state.business_packs = packs
            report = app_module._build_report_context(
                normalized,
                business_type,
                profile,
                semantic,
                adaptive,
                packs,
                quality,
            )
            app_module.st.session_state.report = report

            qna_cases = [
                (
                    "Which product made the most revenue?",
                    "product",
                ),
                (
                    "Which product sold the most units?",
                    "units",
                ),
                (
                    "Who was the best customer?",
                    "customer",
                ),
            ]

            for question, expected_word in qna_cases:
                result = app_module._answer_business_question(
                    report,
                    question,
                )
                answer = result.get("answer", "")
                passed = bool(answer) and expected_word.lower() in answer.lower()
                results.append(
                    _case_result(
                        f"Retail Q&A — {question}",
                        passed,
                        answer[:500],
                    )
                )

        # Scope behavior is a runtime gate, not only a source-code contract.
        retail_scope = sample_dir / "retail.csv"
        if retail_scope.exists():
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
            ) = app_module._process_upload(
                DiagnosticUpload(retail_scope)
            )
            if "date" in normalized.columns and "customer" in normalized.columns:
                dates = pd.to_datetime(
                    normalized["date"],
                    errors="coerce",
                ).dropna()

                if not dates.empty:
                    matching = app_module._apply_scope_filters(
                        normalized,
                        (
                            dates.min().date(),
                            dates.max().date(),
                        ),
                        "All",
                        "B",
                    )
                    scope_ok = len(matching) >= 1
                    results.append(
                        _case_result(
                            "Retail scope filter — valid intersection",
                            scope_ok,
                            f"Customer B matched {len(matching):,} row(s) in the full date range.",
                        )
                    )

                    empty_matching = app_module._apply_scope_filters(
                        normalized,
                        (
                            pd.Timestamp("2026-02-28").date(),
                            pd.Timestamp("2026-03-31").date(),
                        ),
                        "All",
                        "B",
                    )
                    empty_ok = empty_matching.empty
                    results.append(
                        _case_result(
                            "Retail scope filter — zero-row intersection",
                            empty_ok,
                            "A zero-row filter combination is detected before Apply view.",
                        )
                    )

        # Factual Q&A for every non-retail business archetype.
        qna_non_retail = [
            ("pipeline.csv", "What is our pipeline value?"),
            ("subscription.csv", "What is our MRR?"),
            ("services.csv", "Who is the top client?"),
        ]

        for sample_name, question in qna_non_retail:
            path = sample_dir / sample_name
            if not path.exists():
                continue

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
            ) = app_module._process_upload(
                DiagnosticUpload(path)
            )
            app_module.st.session_state.business_type = business_type
            app_module.st.session_state.business_packs = packs
            report = app_module._build_report_context(
                normalized,
                business_type,
                profile,
                semantic,
                adaptive,
                packs,
                quality,
            )
            app_module.st.session_state.report = report

            result = app_module._answer_business_question(
                report,
                question,
            )
            answer = result.get("answer", "")
            passed_qna = bool(answer) and result.get("confidence") in {
                "high",
                "medium",
            }
            results.append(
                _case_result(
                    f"{sample_name} — factual Q&A",
                    passed_qna,
                    answer[:500],
                )
            )

        # Retail Q&A guardrail: subject and metric must follow the wording,
        # not an LLM's ambiguous interpretation.
        retail_qna_path = sample_dir / "retail.csv"
        if retail_qna_path.exists():
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
            ) = app_module._process_upload(
                DiagnosticUpload(retail_qna_path)
            )
            app_module.st.session_state.business_type = business_type
            plan = app_module.plan_sales_question(
                {
                    "data": normalized,
                    "profile": profile,
                    "semantic_model": semantic,
                },
                "Which customer bought the most products?",
            )
            qna_guard_ok = (
                plan.get("entity") == "customer"
                and plan.get("metric") == "quantity"
                and plan.get("operation") == "rank"
            )
            results.append(
                _case_result(
                    "retail.csv — Q&A subject/metric guardrail",
                    qna_guard_ok,
                    (
                        "customer + quantity ranking"
                        if qna_guard_ok
                        else str(plan)
                    ),
                )
            )

        # Source-level contract checks for the two historically fragile flows.
        source = Path(app_module.__file__).read_text(
            encoding="utf-8"
        )

        checks = [
            (
                "Ask — Clear control",
                '🧹 Clear' in source,
                "Clear action is present in the live application source.",
            ),
            (
                "Ask — stale-answer guard",
                "ask_answered_question" in source
                and "current_question == answered_question" in source,
                "Previous answers are tied to the question that produced them.",
            ),
            (
                "Investigate — executes",
                "st.session_state.ask_answer = result[\"answer\"]" in source
                and 'st.session_state.active_dashboard_section = "ask"' in source,
                "Investigate action executes a question and navigates to Ask.",
            ),
            (
                "Navigation — no conflicting widget key",
                'key="dashboard_section_selector"' not in source,
                "Review navigation is driven by session state.",
            ),
            (
                "Review navigation — segmented control",
                "st.segmented_control(" in source
                and "st.radio(" not in source,
                "Review navigation uses the segmented control on the pinned Streamlit version.",
            ),
            (
                "Streamlit API — no deprecated container width",
                "use_container_width" not in source,
                "All app dataframe calls use width=\"stretch\".",
            ),
        ]

        for test_name, passed, details in checks:
            results.append(
                _case_result(
                    test_name,
                    passed,
                    details,
                )
            )

    finally:
        for key, value in originals.items():
            app_module.st.session_state[key] = value

    return results


def run_release_contract_diagnostics(
    app_module,
    root_dir: Path,
) -> list[dict[str, Any]]:
    """Checks that should block release even when feature smoke tests pass."""
    source = Path(app_module.__file__).read_text(
        encoding="utf-8"
    )
    query_source = (
        root_dir / "sales_query_engine_v1.py"
    ).read_text(
        encoding="utf-8"
    )

    results = []

    def add(name, passed, details):
        results.append(
            _case_result(
                name,
                passed,
                details,
            )
        )

    add(
        "Review navigation — no default/key conflict",
        "default=st.session_state.review_section_nav" not in source,
        "Segmented control is keyed and initialized through Session State before rendering.",
    )
    add(
        "Review navigation — no post-render widget mutation",
        "st.session_state.review_section_nav = \"ask\"" not in source
        and "st.session_state.review_section_nav = selected_section" not in source,
        "Programmatic navigation uses pending_review_section instead of mutating the widget after render.",
    )
    add(
        "Q&A schema — no invalid union type arrays",
        '\"type\": [\"integer\", \"null\"]' not in query_source
        and '\"type\": [\"string\", \"null\"]' not in query_source,
        "Nullable fields use supported anyOf JSON Schema.",
    )
    add(
        "Deprecated Streamlit API — clean",
        "use_container_width" not in source
        and all(
            (
                p.name == "runtime_diagnostics.py"
                or "tests_v2" in p.parts
                or "use_container_width" not in p.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            )
            for p in root_dir.rglob("*.py")
        ),
        "No deprecated use_container_width calls remain in the production application code.",
    )

    # Every planned review section must have an explicit renderer branch.
    known_branches = {
        sid
        for sid in re.findall(
            r'elif sid == "([^"]+)"',
            source,
        )
    } | set(
        re.findall(
            r'if sid == "([^"]+)"',
            source,
        )
    )
    add(
        "Review navigation — renderer coverage",
        {"overview", "attention", "performance", "ask", "report"}.issubset(
            known_branches
        ),
        f"Found render branches for {len(known_branches)} section ids.",
    )

    # Required optional modules must exist beside the app.
    required_files = [
        "analyst_intelligence_v2.py",
        "runtime_diagnostics.py",
        "adaptive_dashboard_engine_v1.py",
        "adaptive_pdf_generator_v1.py",
        "sales_query_engine_v1.py",
    ]
    missing = [
        name
        for name in required_files
        if not (root_dir / name).exists()
    ]
    add(
        "Package integrity — required modules",
        not missing,
        "All required application modules are present."
        if not missing
        else f"Missing: {', '.join(missing)}",
    )

    # Import the analyst intelligence module in the live process.
    try:
        app_module._load_analyst_intelligence()
        import_ok = True
        detail = "analyst_intelligence_v2 imported successfully."
    except Exception as exc:
        import_ok = False
        detail = f"{type(exc).__name__}: {exc}"

    add(
        "Startup dependency — analyst intelligence",
        import_ok,
        detail,
    )

    return results

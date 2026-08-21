
from __future__ import annotations

from pathlib import Path
import importlib.util
import sys
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name,
        ROOT / filename,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ProductHardeningTests(unittest.TestCase):

    def test_scope_intersection_is_exact(self):
        scope = load(
            "hardening_scope",
            "scope_engine_v1.py",
        )

        data = pd.read_csv(
            SAMPLES / "retail.csv",
        )
        data["date"] = pd.to_datetime(
            data["OrderDate"]
        )
        data = data.rename(
            columns={
                "ProductName": "product",
                "CustomerName": "customer",
            }
        )

        empty = scope.apply_scope_filters(
            data,
            (
                pd.Timestamp("2026-02-28").date(),
                pd.Timestamp("2026-03-31").date(),
            ),
            "All",
            "B",
        )
        self.assertTrue(empty.empty)

        valid = scope.apply_scope_filters(
            data,
            (
                pd.Timestamp("2026-01-01").date(),
                pd.Timestamp("2026-01-03").date(),
            ),
            "All",
            "B",
        )
        self.assertEqual(
            len(valid),
            1,
        )

    def test_business_brief_capability_count_uses_live_modules(self):
        ai = load(
            "hardening_ai",
            "analyst_intelligence_v2.py",
        )

        data = pd.DataFrame({
            "client": ["A", "B"],
            "hours": [10, 20],
            "billings": [1000, 2000],
        })

        brief = ai.build_business_brief(
            data,
            {
                "recognized": {},
                "capabilities": {},
                "dimensions": [],
                "metrics": [],
            },
            {
                "capabilities": {},
                "dimensions": [],
                "metrics": [],
            },
            {
                "primary_type": "services",
                "confidence": 1.0,
            },
            {
                "enabled_modules": [
                    "services",
                    "billings",
                    "utilization",
                ],
            },
            {
                "packs": {
                    "services": {
                        "available": True,
                    },
                },
            },
            {},
        )

        self.assertGreaterEqual(
            brief["capabilities"]["count"],
            3,
        )

    def test_entity_names_are_explicit(self):
        ai = load(
            "hardening_entity_ai",
            "analyst_intelligence_v2.py",
        )

        data = pd.DataFrame({
            "product": ["Phone", "Shift"],
            "customer": ["A", "B"],
            "revenue": [900, 100],
            "order_id": ["1", "2"],
        })

        brief = ai.build_business_brief(
            data,
            {
                "recognized": {},
                "capabilities": {},
                "dimensions": [],
                "metrics": [],
            },
            {
                "capabilities": {},
                "dimensions": [],
                "metrics": [],
            },
            {
                "primary_type": "transactional_sales",
                "confidence": 1.0,
            },
            {},
            {"packs": {}},
            {},
        )

        titles = [
            signal.get("title", "")
            for signal in brief["signals"]
        ]

        self.assertTrue(
            any("Product Phone" in title for title in titles)
            or any("Customer A" in title for title in titles)
        )

    def test_no_material_signal_is_not_rendered_as_an_investigation_target(self):
        source = (
            ROOT / "app.py"
        ).read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "only_no_signal",
            source,
        )
        self.assertIn(
            "No priority risk was detected",
            source,
        )

    def test_navigation_has_single_source_of_truth(self):
        source = (
            ROOT / "app.py"
        ).read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "selected_section = st.segmented_control(",
            source,
        )
        self.assertIn(
            "selected_section = st.selectbox(",
            source,
        )
        self.assertNotIn(
            'key="review_primary_nav"',
            source,
        )
        self.assertNotIn(
            'key="review_more_nav"',
            source,
        )
        self.assertIn(
            "st.session_state.active_dashboard_section = selected_section",
            source,
        )


    def test_scope_engine_supports_business_specific_dimensions(self):
        scope = load(
            "hardening_scope_dimensions",
            "scope_engine_v1.py",
        )

        cases = [
            (
                "transactional_sales",
                pd.DataFrame({
                    "product": ["P1", "P2"],
                    "customer": ["C1", "C2"],
                    "region": ["North", "South"],
                }),
                {"product", "customer", "region"},
            ),
            (
                "sales_pipeline",
                pd.DataFrame({
                    "salesperson": ["R1", "R2"],
                    "stage": ["Proposal", "Won"],
                    "customer": ["A", "B"],
                }),
                {"salesperson", "stage", "customer"},
            ),
            (
                "subscription",
                pd.DataFrame({
                    "customer": ["A", "B"],
                    "plan": ["Basic", "Pro"],
                    "churn_status": ["active", "churned"],
                }),
                {"customer", "plan", "churn_status"},
            ),
            (
                "services",
                pd.DataFrame({
                    "client": ["A", "B"],
                    "service": ["Consulting", "Audit"],
                    "employee": ["E1", "E2"],
                }),
                {"client", "service", "employee"},
            ),
        ]

        for primary, data, expected in cases:
            available = {
                name
                for name, _ in scope.available_scope_dimensions(
                    data,
                    primary,
                    max_dimensions=3,
                )
            }
            self.assertTrue(
                expected.issubset(available),
                f"{primary} missing {sorted(expected - available)}",
            )

    def test_scope_rebuilds_business_packs(self):
        packs_mod = load(
            "hardening_packs_scope",
            "business_analysis_packs_v1.py",
        )

        sub = pd.read_csv(
            SAMPLES / "subscription.csv",
        ).rename(
            columns={
                "SubscriptionID": "subscription_id",
                "CustomerName": "customer",
                "Plan": "plan",
                "StartDate": "date",
                "MRR": "mrr",
                "ChurnStatus": "churn_status",
            }
        )
        scoped = sub.loc[
            sub["plan"].astype(str) == "Basic"
        ].copy()

        result = packs_mod.run_business_type_packs(
            scoped,
            {"primary_type": "subscription"},
        )
        metrics = result["packs"]["subscription"]["metrics"]

        self.assertEqual(
            metrics["mrr"],
            50.0,
        )
        self.assertEqual(
            metrics["annualized_revenue"],
            600.0,
        )

        services = pd.read_csv(
            SAMPLES / "services.csv",
        ).rename(
            columns={
                "Client": "client",
                "Service": "service",
                "Hours": "hours",
                "Billings": "billings",
                "Employee": "employee",
                "ProjectID": "project_id",
            }
        )
        svc = services.loc[
            (services["client"].astype(str) == "A")
            & (services["service"].astype(str) == "Consulting")
        ].copy()
        result = packs_mod.run_business_type_packs(
            svc,
            {"primary_type": "services"},
        )
        metrics = result["packs"]["services"]["metrics"]

        self.assertEqual(
            metrics["billings"],
            1000.0,
        )
        self.assertEqual(
            metrics["hours"],
            10.0,
        )
        self.assertEqual(
            metrics["revenue_per_hour"],
            100.0,
        )

    def test_qna_scope_uses_scope_packs_only_when_enabled(self):
        # Source-level contract: Q&A must choose scope packs only when the
        # explicit "Use the current dashboard scope" flag is enabled.
        source = (
            ROOT / "app.py"
        ).read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "active_packs = (",
            source,
        )
        self.assertIn(
            "st.session_state.get(\"ask_use_view_scope\")",
            source,
        )
        self.assertIn(
            "st.session_state.get(\"scope_business_packs\")",
            source,
        )

    def test_single_dimension_scope_does_not_create_self_concentration(self):
        ai = load(
            "hardening_ai_scope_concentration",
            "analyst_intelligence_v2.py",
        )
        source = ROOT / "app.py"
        text_source = source.read_text(encoding="utf-8")

        self.assertIn(
            "filtered_dimension_types",
            text_source,
        )
        self.assertIn(
            "product_concentration",
            text_source,
        )
        self.assertIn(
            "customer_concentration",
            text_source,
        )

    def test_pipeline_uses_value_win_rate_label(self):
        source = (
            ROOT / "app.py"
        ).read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '"Value win rate"',
            source,
        )

    def test_scope_dimensions_are_business_specific(self):
        scope = load(
            "hardening_scope_dimensions",
            "scope_engine_v1.py",
        )
        cases = {
            "retail": (
                pd.DataFrame({
                    "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                    "product": ["P1", "P2"],
                    "customer": ["A", "B"],
                    "region": ["N", "S"],
                }),
                "transactional_sales",
                {"product", "customer"},
            ),
            "pipeline": (
                pd.DataFrame({
                    "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                    "salesperson": ["R1", "R2"],
                    "stage": ["Proposal", "Closed Won"],
                }),
                "sales_pipeline",
                {"salesperson", "stage"},
            ),
            "subscription": (
                pd.DataFrame({
                    "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                    "customer": ["A", "B"],
                    "plan": ["Pro", "Basic"],
                }),
                "subscription",
                {"customer", "plan"},
            ),
            "services": (
                pd.DataFrame({
                    "client": ["A", "B"],
                    "service": ["Consulting", "Support"],
                    "employee": ["E1", "E2"],
                }),
                "services",
                {"client", "service"},
            ),
        }

        for _, (frame, primary, expected) in cases.items():
            names = {
                name
                for name, _ in scope.available_scope_dimensions(
                    frame,
                    primary,
                    max_dimensions=2,
                )
            }
            self.assertEqual(names, expected)

    def test_scope_filters_generic_dimensions(self):
        scope = load(
            "hardening_scope_generic",
            "scope_engine_v1.py",
        )
        frame = pd.DataFrame({
            "date": pd.to_datetime(
                ["2026-01-01", "2026-01-02", "2026-01-03"]
            ),
            "salesperson": ["R1", "R1", "R2"],
            "stage": ["Proposal", "Closed Won", "Proposal"],
            "amount": [10, 20, 30],
        })
        result = scope.apply_scope_filters(
            frame,
            (
                pd.Timestamp("2026-01-01").date(),
                pd.Timestamp("2026-01-03").date(),
            ),
            dimension_filters={
                "salesperson": "R1",
                "stage": "Closed Won",
            },
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["amount"], 20)

    def test_qna_customer_bought_most_products_is_customer_quantity(self):
        qna = load(
            "hardening_qna_intent",
            "sales_query_engine_v1.py",
        )
        report = {
            "data": pd.DataFrame({
                "date": pd.to_datetime(
                    ["2026-01-01", "2026-01-02", "2026-01-03"]
                ),
                "customer": ["A", "A", "B"],
                "product": ["Phone", "Shirt", "Phone"],
                "quantity": [2, 2, 1],
                "revenue": [100, 50, 50],
                "order_id": [1, 2, 3],
            })
        }
        plan = qna.plan_sales_question(
            report,
            "Which customer bought the most products?",
        )
        self.assertEqual(plan["entity"], "customer")
        self.assertEqual(plan["metric"], "quantity")
        self.assertEqual(plan["operation"], "rank")

    def test_qna_vague_performance_requires_clarification(self):
        qna = load(
            "hardening_qna_vague",
            "sales_query_engine_v1.py",
        )
        report = {
            "data": pd.DataFrame({
                "date": pd.to_datetime(["2026-01-01"]),
                "customer": ["A"],
                "product": ["Phone"],
                "quantity": [1],
                "revenue": [100],
                "order_id": [1],
            })
        }
        plan = qna.plan_sales_question(
            report,
            "Which product performed well?",
        )
        self.assertTrue(plan.get("_needs_clarification"))



if __name__ == "__main__":
    unittest.main()

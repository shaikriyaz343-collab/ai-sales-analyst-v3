
from __future__ import annotations

from pathlib import Path
import importlib.util
import sys
import unittest

import pandas as pd


BASE = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name,
        BASE / filename,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


profiler = load("profiler", "schema_profiler_v2.py")
semantic = load("semantic", "semantic_business_model_v2.py")
quality = load("quality", "data_quality_engine_v1.py")
business_type = load("business_type", "business_type_detector_v1.py")
adaptive = load("adaptive", "adaptive_analysis_engine_v1.py")
packs = load("packs", "business_analysis_packs_v1.py")
dashboard = load("dashboard", "adaptive_dashboard_engine_v1.py")
agent = load("agent", "business_analyst_agent_v1.py")


def normalize(data, profile):
    rename = {}

    for semantic_name, columns in profile["recognized"].items():
        for column in columns:
            if (
                column in data.columns
                and semantic_name not in data.columns
            ):
                rename[column] = semantic_name

    result = data.rename(columns=rename).copy()

    for column in [
        "date",
        "expected_close",
    ]:
        if column in result.columns:
            result[column] = pd.to_datetime(
                result[column],
                errors="coerce",
            )

    for column in [
        "quantity",
        "price",
        "revenue",
        "amount",
        "mrr",
        "hours",
        "billings",
        "discount_pct",
        "probability",
    ]:
        if column in result.columns:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

    return result


class V2ArchitectureTests(unittest.TestCase):

    def run_stack(self, data):
        profile = profiler.profile_dataframe(data)
        normalized = normalize(
            data,
            profile,
        )
        model = semantic.build_semantic_model(
            profile,
            normalized,
        )
        dq = quality.run_data_quality_checks(
            normalized,
            model,
        )
        detected = business_type.detect_business_type(
            model,
            profile,
        )
        analysis = adaptive.analyze_modules(
            normalized,
            model,
            dq,
        )
        pack_result = packs.run_business_type_packs(
            normalized,
            detected,
        )
        plan = dashboard.build_dashboard_plan(
            model,
            detected,
            analysis,
            dq,
        )
        return (
            profile,
            normalized,
            model,
            dq,
            detected,
            analysis,
            pack_result,
            plan,
        )

    def test_retail(self):
        data = pd.DataFrame({
            "OrderID": ["1", "2"],
            "OrderDate": ["2026-01-01", "2026-02-01"],
            "CustomerName": ["A", "B"],
            "ProductName": ["Phone", "Shirt"],
            "Quantity": [1, 2],
            "UnitPrice": [700, 50],
            "TotalAmount": [700, 100],
            "Region": ["North", "South"],
            "Discount %": [0, 10],
            "Return Status": ["No", "Returned"],
        })

        *_, detected, _, _, plan = self.run_stack(
            data
        )

        self.assertEqual(
            detected["primary_type"],
            "transactional_sales",
        )
        self.assertIn(
            "discounts",
            plan["section_ids"],
        )
        self.assertIn(
            "returns",
            plan["section_ids"],
        )

    def test_pipeline(self):
        data = pd.DataFrame({
            "OpportunityID": ["O1", "O2"],
            "CreatedDate": ["2026-01-01", "2026-01-01"],
            "AccountName": ["A", "B"],
            "Salesperson": ["Rep1", "Rep2"],
            "Stage": ["Closed Won", "Proposal"],
            "Amount": [50000, 30000],
            "Probability": [1.0, 0.6],
            "ExpectedClose": ["2026-02-01", "2026-02-01"],
        })

        *_, detected, _, pack_result, plan = self.run_stack(
            data
        )

        self.assertEqual(
            detected["primary_type"],
            "sales_pipeline",
        )
        self.assertTrue(
            pack_result["packs"]["sales_pipeline"]["available"]
        )
        self.assertIn(
            "pipeline",
            plan["section_ids"],
        )

    def test_subscription(self):
        data = pd.DataFrame({
            "SubscriptionID": ["S1", "S2"],
            "CustomerName": ["A", "B"],
            "Plan": ["Pro", "Basic"],
            "StartDate": ["2026-01-01", "2026-01-01"],
            "MRR": [100, 50],
            "ChurnStatus": ["Active", "Churned"],
        })

        *_, detected, _, pack_result, plan = self.run_stack(
            data
        )

        self.assertEqual(
            detected["primary_type"],
            "subscription",
        )
        self.assertTrue(
            pack_result["packs"]["subscription"]["available"]
        )
        self.assertIn(
            "recurring_revenue",
            plan["section_ids"],
        )

    def test_services(self):
        data = pd.DataFrame({
            "ProjectID": ["P1", "P2"],
            "Client": ["A", "B"],
            "Service": ["Consulting", "Support"],
            "Hours": [10, 20],
            "Billings": [1000, 1500],
            "Employee": ["E1", "E2"],
        })

        *_, detected, _, pack_result, plan = self.run_stack(
            data
        )

        self.assertEqual(
            detected["primary_type"],
            "services",
        )
        self.assertTrue(
            pack_result["packs"]["services"]["available"]
        )
        self.assertIn(
            "services",
            plan["section_ids"],
        )

    def test_business_analyst_investigation(self):
        data = pd.DataFrame({
            "date": pd.to_datetime([
                "2026-07-01",
                "2026-07-02",
                "2026-08-01",
                "2026-08-02",
            ]),
            "order_id": ["J1", "J2", "A1", "A2"],
            "customer": ["A", "B", "A", "B"],
            "product": [
                "P1",
                "P2",
                "P1",
                "P2",
            ],
            "quantity": [5, 4, 2, 2],
            "revenue": [100, 80, 40, 40],
        })

        result = agent.answer_with_agent(
            data,
            "Why was August weak?",
        )

        self.assertEqual(
            result["intent"],
            "investigate_change",
        )
        self.assertGreaterEqual(
            len(result["steps"]),
            3,
        )
        self.assertTrue(
            result["recommendations"]
        )


if __name__ == "__main__":
    unittest.main()

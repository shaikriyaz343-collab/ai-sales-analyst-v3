
from __future__ import annotations

from pathlib import Path
import importlib.util
import sys
import unittest

import pandas as pd


BASE = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


packs = load(
    "business_analysis_packs_test",
    BASE / "business_analysis_packs_v1.py",
)


class BusinessAnalysisPackTests(unittest.TestCase):

    def test_pipeline_pack(self):
        data = pd.DataFrame(
            {
                "opportunity_id": ["O1", "O2", "O3"],
                "stage": [
                    "Closed Won",
                    "Proposal",
                    "Closed Lost",
                ],
                "amount": [50000, 30000, 20000],
                "salesperson": [
                    "Rep 1",
                    "Rep 2",
                    "Rep 1",
                ],
            }
        )

        result = packs.analyze_sales_pipeline(data)

        self.assertTrue(result["available"])
        self.assertEqual(
            result["metrics"]["pipeline_value"],
            100000.0,
        )
        self.assertEqual(
            result["metrics"]["won_value"],
            50000.0,
        )
        self.assertEqual(
            result["metrics"]["lost_value"],
            20000.0,
        )

    def test_subscription_pack(self):
        data = pd.DataFrame(
            {
                "customer": ["A", "B", "C"],
                "mrr": [100, 50, 150],
                "churn_status": [
                    "Active",
                    "Churned",
                    "Active",
                ],
            }
        )

        result = packs.analyze_subscription_business(data)

        self.assertTrue(result["available"])
        self.assertEqual(
            result["metrics"]["mrr"],
            300.0,
        )
        self.assertEqual(
            result["metrics"]["annualized_revenue"],
            3600.0,
        )
        self.assertAlmostEqual(
            result["metrics"]["churn_rate_pct"],
            33.33333333333333,
            places=4,
        )

    def test_services_pack(self):
        data = pd.DataFrame(
            {
                "client": ["A", "B", "C"],
                "hours": [10, 20, 15],
                "billings": [1000, 1200, 900],
                "employee": ["E1", "E2", "E1"],
            }
        )

        result = packs.analyze_services_business(data)

        self.assertTrue(result["available"])
        self.assertEqual(
            result["metrics"]["hours"],
            45.0,
        )
        self.assertEqual(
            result["metrics"]["billings"],
            3100.0,
        )
        self.assertAlmostEqual(
            result["metrics"]["revenue_per_hour"],
            68.8888888889,
            places=6,
        )

    def test_missing_fields_do_not_claim_availability(self):
        data = pd.DataFrame(
            {
                "customer": ["A", "B"],
                "revenue": [100, 200],
            }
        )

        pipeline = packs.analyze_sales_pipeline(data)
        subscription = packs.analyze_subscription_business(data)
        services = packs.analyze_services_business(data)

        self.assertFalse(pipeline["available"])
        self.assertFalse(subscription["available"])
        self.assertFalse(services["available"])


if __name__ == "__main__":
    unittest.main()

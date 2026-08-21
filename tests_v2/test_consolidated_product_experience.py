
from __future__ import annotations

from pathlib import Path
import importlib.util
import sys
import unittest

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
SAMPLES = Path("/mnt/data/v2_validation_workspace/samples")


def load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name,
        BASE / filename,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


profiler = load("consolidated_profiler", "schema_profiler_v2.py")
packs = load("consolidated_packs", "business_analysis_packs_v1.py")


class ConsolidatedProductTests(unittest.TestCase):

    def test_small_dataset_reports_coverage(self):
        data = pd.read_csv(
            SAMPLES / "services.csv"
        )
        profile = profiler.profile_dataframe(data)

        self.assertEqual(
            profile["row_count"],
            4,
        )
        self.assertEqual(
            profile["column_count"],
            6,
        )
        self.assertIn(
            "client",
            profile["recognized"],
        )

    def test_pipeline_forecast_is_available_only_with_required_fields(self):
        data = pd.read_csv(
            SAMPLES / "pipeline.csv"
        )
        profile = profiler.profile_dataframe(data)

        rename = {}
        for concept, columns in profile["recognized"].items():
            for column in columns:
                if (
                    column in data.columns
                    and concept not in data.columns
                ):
                    rename[column] = concept

        normalized = data.rename(
            columns=rename
        )

        result = packs.analyze_sales_forecast(
            normalized
        )

        self.assertTrue(
            result["available"]
        )
        self.assertEqual(
            result["metrics"]["pipeline_value"],
            155000.0,
        )
        self.assertEqual(
            result["metrics"]["open_pipeline_value"],
            85000.0,
        )
        self.assertEqual(
            result["metrics"]["weighted_forecast"],
            50500.0,
        )

    def test_retail_findings_use_action_plans(self):
        data = pd.DataFrame({
            "date": pd.to_datetime([
                "2026-01-01",
                "2026-02-01",
                "2026-02-02",
            ]),
            "order_id": ["1", "2", "3"],
            "product": ["Phone", "Phone", "Shift"],
            "customer": ["A", "B", "C"],
            "quantity": [1, 1, 10],
            "revenue": [1000, 500, 100],
        })

        bi = load(
            "consolidated_bi",
            "business_intelligence.py",
        )

        products = data.groupby(
            "product"
        ).agg(
            revenue=("revenue", "sum"),
            quantity_sold=("quantity", "sum"),
        )
        customers = data.groupby(
            "customer"
        ).agg(
            revenue=("revenue", "sum")
        )
        monthly = data.groupby(
            data["date"].dt.to_period("M").astype(str)
        ).agg(
            revenue=("revenue", "sum")
        )

        result = bi.build_business_findings({
            "data": data,
            "products": products,
            "customers": customers,
            "monthly": monthly,
        })

        self.assertTrue(
            result["priority_findings"]
        )

        for finding in result["priority_findings"]:
            self.assertTrue(
                finding.get("recommended_action")
            )

            self.assertTrue(
                finding.get("decision_question")
            )


if __name__ == "__main__":
    unittest.main()

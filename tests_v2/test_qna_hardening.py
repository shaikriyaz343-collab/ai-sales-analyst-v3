
from __future__ import annotations

from pathlib import Path
import importlib.util
import sys
import unittest

import pandas as pd


BASE = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location(
        "qna_hardening_engine",
        BASE / "sales_query_engine_v1.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


query = load()


class QNAHardeningTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = pd.DataFrame({
            "date": pd.to_datetime([
                "2026-01-01",
                "2026-01-02",
                "2026-02-01",
                "2026-02-02",
                "2026-03-01",
            ]),
            "order_id": ["1", "2", "3", "4", "5"],
            "product": [
                "Phone",
                "Shift",
                "Phone",
                "Mug",
                "Shift",
            ],
            "customer": [
                "A",
                "B",
                "A",
                "C",
                "B",
            ],
            "quantity": [2, 20, 1, 3, 25],
            "revenue": [2000, 100, 800, 60, 125],
        })

        cls.report = {
            "data": cls.data,
            "kpis": {
                "total_revenue": cls.data["revenue"].sum(),
                "total_orders": cls.data["order_id"].nunique(),
                "average_order_value": (
                    cls.data["revenue"].sum()
                    / cls.data["order_id"].nunique()
                ),
            },
        }

    def test_best_product_means_revenue_rank(self):
        answer = query.answer_sales_question(
            self.report,
            "what was the best product?",
        )
        self.assertIn("Phone", answer)
        self.assertIn("$2,800.00", answer)

    def test_most_units_uses_quantity(self):
        answer = query.answer_sales_question(
            self.report,
            "which product sold the most units?",
        )
        self.assertIn("Shift", answer)
        self.assertIn("45", answer)

    def test_customer_rank_is_not_product_rank(self):
        answer = query.answer_sales_question(
            self.report,
            "who was the best customer?",
        )
        self.assertIn("A", answer)
        self.assertNotIn("Phone", answer)

    def test_month_is_respected(self):
        answer = query.answer_sales_question(
            self.report,
            "which product made the most revenue in February?",
        )
        self.assertIn("February 2026", answer)
        self.assertIn("Phone", answer)
        self.assertIn("$800.00", answer)

    def test_missing_month_is_explicit(self):
        answer = query.answer_sales_question(
            self.report,
            "which product made the most revenue in August?",
        )
        self.assertIn(
            "no data for that month",
            answer.lower(),
        )

    def test_unsupported_question_does_not_guess(self):
        answer = query.answer_sales_question(
            self.report,
            "tell me something interesting",
        )
        self.assertTrue(
            "verified query" in answer.lower()
            or "try asking" in answer.lower()
        )


if __name__ == "__main__":
    unittest.main()


from __future__ import annotations

from pathlib import Path
import importlib.util
import sys
import unittest

import pandas as pd


BASE = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location(
        "sales_query_engine_month_test",
        BASE / "sales_query_engine_v1.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


query = load()


class MonthAwareQueryTests(unittest.TestCase):

    def build_report(self, data):
        orders = data["order_id"].nunique()
        revenue = data["revenue"].sum()
        return {
            "data": data,
            "kpis": {
                "total_revenue": revenue,
                "total_orders": orders,
                "average_order_value": revenue / orders,
            },
        }

    def test_missing_month_is_explained(self):
        data = pd.DataFrame({
            "order_id": ["1", "2", "3"],
            "date": pd.to_datetime([
                "2026-01-01",
                "2026-02-01",
                "2026-03-01",
            ]),
            "customer": ["A", "B", "C"],
            "product": ["P1", "P2", "P3"],
            "quantity": [1, 1, 1],
            "price": [100, 200, 300],
            "revenue": [100, 200, 300],
        })

        answer = query.answer_sales_question(
            self.build_report(data),
            "Which product made the most revenue in August?",
        )

        self.assertIn(
            "no data for that month",
            answer.lower(),
        )
        self.assertIn(
            "january 2026",
            answer.lower(),
        )

    def test_named_month_is_ranked_when_present(self):
        data = pd.DataFrame({
            "order_id": ["1", "2", "3", "4"],
            "date": pd.to_datetime([
                "2026-08-01",
                "2026-08-02",
                "2026-08-03",
                "2026-08-04",
            ]),
            "customer": ["A", "B", "C", "D"],
            "product": ["Phone", "Shirt", "Phone", "Mug"],
            "quantity": [1, 10, 2, 1],
            "price": [700, 50, 700, 20],
            "revenue": [700, 500, 1400, 20],
        })

        answer = query.answer_sales_question(
            self.build_report(data),
            "Which product made the most revenue in August?",
        )

        self.assertIn(
            "phone",
            answer.lower(),
        )
        self.assertIn(
            "$2,100.00",
            answer,
        )


if __name__ == "__main__":
    unittest.main()

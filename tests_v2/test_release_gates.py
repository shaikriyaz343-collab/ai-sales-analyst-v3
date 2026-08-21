
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

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


class ReleaseGateTests(unittest.TestCase):

    def test_all_business_archetypes_run_pack_analysis(self):
        packs = load(
            "release_packs",
            "business_analysis_packs_v1.py",
        )

        expected = {
            "retail.csv": "transactional_sales",
            "pipeline.csv": "sales_pipeline",
            "subscription.csv": "subscription",
            "services.csv": "services",
        }

        for filename, primary_type in expected.items():
            data = pd.read_csv(
                SAMPLES / filename
            )
            result = packs.run_business_type_packs(
                data,
                {
                    "primary_type": primary_type,
                },
            )
            self.assertIn("packs", result)
            self.assertIsInstance(
                result["packs"],
                dict,
            )

    def test_dashboard_renderer_contract_covers_declared_sections(self):
        dashboard = load(
            "release_dashboard",
            "adaptive_dashboard_engine_v1.py",
        )
        source = (ROOT / "app.py").read_text(encoding="utf-8")

        branch_ids = set(
            re.findall(
                r'(?:if|elif) sid == "([^"]+)"',
                source,
            )
        )

        all_ids = set(dashboard.MODULE_DEFINITIONS)
        self.assertTrue(
            {"overview", "attention", "performance", "ask", "report", "data_quality"}.issubset(
                branch_ids
            )
        )
        self.assertTrue(
            all_ids.issubset(branch_ids),
            f"Missing render branches for: {sorted(all_ids - branch_ids)}",
        )

        # Build representative capability-driven plans and verify required
        # business-model sections are exposed.
        cases = [
            (
                "transactional_sales",
                {
                    "product_analysis": True,
                    "customer_analysis": True,
                    "regional_analysis": True,
                    "discount_analysis": True,
                    "return_analysis": True,
                    "payment_analysis": True,
                },
                {"overview", "attention", "performance", "products", "customers", "regions", "discounts", "returns", "payments", "ask", "report", "data_quality"},
            ),
            (
                "sales_pipeline",
                {},
                {"overview", "attention", "performance", "pipeline", "forecast", "ask", "report", "data_quality"},
            ),
            (
                "subscription",
                {},
                {"overview", "attention", "performance", "recurring_revenue", "retention", "churn", "ask", "report", "data_quality"},
            ),
            (
                "services",
                {},
                {"overview", "attention", "performance", "services", "billings", "utilization", "ask", "report", "data_quality"},
            ),
        ]

        for primary_type, capabilities, expected in cases:
            available_concepts = (
                ["expected_close", "amount"]
                if primary_type == "sales_pipeline"
                else []
            )
            plan = dashboard.build_dashboard_plan(
                {"capabilities": capabilities, "available_concepts": available_concepts},
                {"primary_type": primary_type},
                {"module_count": 0},
                {},
            )
            ids = set(plan["section_ids"])
            self.assertTrue(
                expected.issubset(ids),
                f"{primary_type} missing: {sorted(expected - ids)}",
            )

    def test_no_deprecated_streamlit_calls_in_application(self):
        for path in ROOT.rglob("*.py"):
            if path.name == "runtime_diagnostics.py" or "tests_v2" in path.parts:
                continue
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
            self.assertNotIn(
                "use_container_width",
                text,
                str(path),
            )

    def test_no_widget_state_mutation_after_render_pattern(self):
        source = (
            ROOT / "app.py"
        ).read_text(
            encoding="utf-8"
        )
        self.assertNotIn(
            'st.session_state.review_section_nav = "ask"',
            source,
        )
        self.assertNotIn(
            "st.session_state.review_section_nav = selected_section",
            source,
        )
        self.assertIn(
            "pending_review_section",
            source,
        )

    def test_query_schema_uses_anyof_for_nullable_fields(self):
        source = (
            ROOT / "sales_query_engine_v1.py"
        ).read_text(
            encoding="utf-8"
        )
        self.assertNotIn(
            '"type": ["integer", "null"]',
            source,
        )
        self.assertNotIn(
            '"type": ["string", "null"]',
            source,
        )
        self.assertIn(
            '"anyOf":',
            source,
        )

    def test_required_runtime_modules_exist(self):
        required = [
            "app.py",
            "analyst_intelligence_v2.py",
            "business_analysis_packs_v1.py",
            "adaptive_dashboard_engine_v1.py",
            "adaptive_pdf_generator_v1.py",
            "sales_query_engine_v1.py",
            "runtime_diagnostics.py",
            "requirements.txt",
        ]
        for filename in required:
            self.assertTrue(
                (ROOT / filename).exists(),
                filename,
            )


if __name__ == "__main__":
    unittest.main()

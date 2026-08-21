from __future__ import annotations

from pathlib import Path
import importlib.util
import sys
import unittest
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
SAMPLES = Path('/mnt/data/v2_validation_workspace/samples')


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


profiler = load('senior_profiler', 'schema_profiler_v2.py')
packs = load('senior_packs', 'business_analysis_packs_v1.py')
intel = load('senior_intel', 'analyst_intelligence_v2.py')
query = load('senior_query', 'sales_query_engine_v1.py')


class SeniorAnalystQualityTests(unittest.TestCase):
    def test_pipeline_uses_open_pipeline_for_forecast(self):
        data = pd.read_csv(SAMPLES / 'pipeline.csv')
        profile = profiler.profile_dataframe(data)
        rename = {}
        for concept, cols in profile['recognized'].items():
            for col in cols:
                if col in data.columns and concept not in data.columns:
                    rename[col] = concept
        normalized = data.rename(columns=rename)
        result = packs.analyze_sales_pipeline(normalized)
        self.assertEqual(result['metrics']['pipeline_value'], 155000.0)
        self.assertEqual(result['metrics']['open_pipeline_value'], 85000.0)
        self.assertEqual(result['metrics']['won_value'], 50000.0)
        self.assertEqual(result['metrics']['lost_value'], 20000.0)
        self.assertEqual(result['metrics']['open_opportunities'], 3)

        forecast = packs.analyze_sales_forecast(normalized)
        self.assertTrue(forecast['available'])
        self.assertEqual(forecast['metrics']['open_pipeline_value'], 85000.0)
        self.assertEqual(forecast['metrics']['weighted_forecast'], 50500.0)

    def test_subscription_uses_customer_level_churn(self):
        data = pd.read_csv(SAMPLES / 'subscription.csv')
        profile = profiler.profile_dataframe(data)
        rename = {}
        for concept, cols in profile['recognized'].items():
            for col in cols:
                if col in data.columns and concept not in data.columns:
                    rename[col] = concept
        normalized = data.rename(columns=rename)
        result = packs.analyze_subscription_business(normalized)
        self.assertEqual(result['metrics']['mrr'], 800.0)
        self.assertEqual(result['metrics']['churned_customer_rate_pct'], 25.0)
        self.assertEqual(result['metrics']['churned_customers'], 1)

    def test_services_billing_concentration_is_not_lost(self):
        data = pd.read_csv(SAMPLES / 'services.csv')
        profile = profiler.profile_dataframe(data)
        rename = {}
        for concept, cols in profile['recognized'].items():
            for col in cols:
                if col in data.columns and concept not in data.columns:
                    rename[col] = concept
        normalized = data.rename(columns=rename)
        self.assertIn('billings', normalized.columns)
        result = intel.build_business_brief(
            data=normalized,
            profile=profile,
            semantic_model={'capabilities': {}, 'dimensions': [], 'metrics': []},
            business_type={'primary_type': 'services', 'confidence': 1.0},
            adaptive_analysis={},
            packs={'packs': {'services': packs.analyze_services_business(normalized)}},
            data_quality={'issue_count': 0},
        )
        self.assertEqual(result['snapshot'][0]['label'], 'Billings')
        # No false concentration signal with four evenly sized clients.
        self.assertFalse(any(s['type'] == 'client_concentration' for s in result['signals']))

    def test_query_engine_does_not_guess_vague_questions(self):
        data = pd.DataFrame({
            'date': pd.to_datetime(['2026-01-01', '2026-02-01']),
            'order_id': ['1', '2'],
            'product': ['A', 'B'],
            'customer': ['C1', 'C2'],
            'quantity': [1, 2],
            'revenue': [100, 200],
        })
        report = {'data': data, 'kpis': {'total_revenue': 300, 'total_orders': 2, 'average_order_value': 150}}
        answer = query.answer_sales_question(report, 'Tell me something interesting')
        self.assertIn('verified query', answer.lower())

    def test_source_uses_canonical_query_engine(self):
        text = (BASE / 'app.py').read_text(encoding='utf-8')
        self.assertIn('from sales_query_engine_v1 import answer_sales_question_structured', text)
        self.assertNotIn('answer_sales_question,\n)', text)

    def test_clear_and_scope_controls_exist(self):
        text = (BASE / 'app.py').read_text(encoding='utf-8')
        self.assertIn('"🧹 Clear"', text)
        self.assertIn('Use the current dashboard scope for this question', text)
        self.assertIn('Show full business', text)


if __name__ == '__main__':
    unittest.main()


from pathlib import Path
import unittest

APP = Path(__file__).resolve().parents[1] / "app.py"


class InvestigateButtonContractTests(unittest.TestCase):
    def test_investigate_navigates_and_executes(self):
        text = APP.read_text(encoding="utf-8")
        block_start = text.index('question = finding.get("decision_question")')
        block_end = text.index(
            'def _render_attention',
            block_start,
        )
        block = text[block_start:block_end]

        self.assertIn(
            "st.session_state.ask_question = question",
            block,
        )
        self.assertIn(
            "st.session_state.ask_answer = result[\"answer\"]",
            block,
        )
        self.assertIn(
            'st.session_state.active_dashboard_section = "ask"',
            block,
        )
        self.assertIn(
            "st.rerun()",
            block,
        )

    def test_radio_does_not_use_conflicting_persistent_widget_key(self):
        text = APP.read_text(encoding="utf-8")
        self.assertNotIn(
            'key="dashboard_section_selector"',
            text,
        )


if __name__ == "__main__":
    unittest.main()

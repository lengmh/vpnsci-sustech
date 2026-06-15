import unittest

from vpnsci_sustech.sources.search_mode import (
    classify_search_mode,
    is_doi_query,
    is_precise_single_paper_query,
    is_strong_pro_trigger,
    is_url_query,
    should_show_upgrade_suggestion,
)
from vpnsci_sustech.sources.search_models import SearchError, SearchHit


class SearchModeTests(unittest.TestCase):
    def test_strong_pro_trigger_whitelist(self):
        self.assertTrue(is_strong_pro_trigger("请生成钙钛矿太阳能电池文献综述"))
        self.assertTrue(is_strong_pro_trigger("make a systematic review about RAG"))
        self.assertTrue(is_strong_pro_trigger("PRISMA search for sepsis biomarkers"))

    def test_high_intent_words_do_not_directly_trigger_pro(self):
        decision = classify_search_mode("帮我找最新高引论文，尽量全面", {})
        self.assertEqual(decision.mode, "standard")
        self.assertIn("no_strong_trigger", decision.reasons)

    def test_explicit_report_arg_triggers_pro(self):
        decision = classify_search_mode("graph neural network", {"mode": "pro"})
        self.assertEqual(decision.mode, "pro")
        self.assertIn("explicit_mode_pro", decision.reasons)

    def test_doi_and_url_detection(self):
        self.assertTrue(is_doi_query("10.1109/ICNC57223.2023.10074111"))
        self.assertTrue(is_doi_query("https://doi.org/10.1000/example"))
        self.assertTrue(is_url_query("https://ieeexplore.ieee.org/document/10074111/"))
        self.assertFalse(is_url_query("graph neural network"))

    def test_precise_single_paper_title_detection(self):
        self.assertTrue(is_precise_single_paper_query("Network Anomaly Detection Using a Graph Neural Network"))
        self.assertFalse(is_precise_single_paper_query("graph neural network anomaly detection"))
        self.assertFalse(is_precise_single_paper_query("钙钛矿太阳能电池 稳定性"))

    def test_upgrade_suggestion_requires_quality_results(self):
        hits = [
            SearchHit(title=f"Paper {i}", doi=f"10.1000/{i}") for i in range(5)
        ]
        decision = should_show_upgrade_suggestion("graph neural network anomaly detection", hits, [])
        self.assertTrue(decision.show)
        self.assertIn("result_count>=5", decision.reasons)

    def test_upgrade_suggestion_suppressed_for_doi_url_precise_title_and_errors(self):
        hits = [SearchHit(title=f"Paper {i}", doi=f"10.1000/{i}") for i in range(5)]
        self.assertFalse(should_show_upgrade_suggestion("10.1000/a", hits, []).show)
        self.assertFalse(should_show_upgrade_suggestion("https://example.org/paper", hits, []).show)
        self.assertFalse(
            should_show_upgrade_suggestion(
                "Network Anomaly Detection Using a Graph Neural Network",
                hits,
                [],
            ).show
        )
        self.assertFalse(
            should_show_upgrade_suggestion(
                "graph neural network",
                hits,
                [SearchError(source="openalex", code="rate_limited", message="429")],
            ).show
        )


if __name__ == "__main__":
    unittest.main()

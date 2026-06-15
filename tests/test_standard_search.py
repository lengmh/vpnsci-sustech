import tempfile
import unittest
import json
from pathlib import Path
from unittest import mock

from vpnsci_sustech.config import Config
from vpnsci_sustech.sources import standard_search
from vpnsci_sustech.sources.search_models import SearchHit


class StandardSearchTests(unittest.TestCase):
    def test_standard_search_uses_query_variants_openalex_and_saves_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(cache_dir=tmp, openalex_api_key="oa-key", semantic_scholar_api_key="s2-key")
            openalex_hits = [
                SearchHit(title="Perovskite Stability", doi="10.1000/a", source="openalex", backend="openalex"),
                SearchHit(title="Perovskite Solar Cells", doi="10.1000/b", source="openalex", backend="openalex"),
                SearchHit(title="Perovskite Photovoltaics", doi="10.1000/c", source="openalex", backend="openalex"),
                SearchHit(title="Paper 4", doi="10.1000/d", source="openalex", backend="openalex"),
                SearchHit(title="Paper 5", doi="10.1000/e", source="openalex", backend="openalex"),
            ]
            with mock.patch.object(standard_search.openalex, "search", return_value=openalex_hits) as oa_mock, \
                 mock.patch.object(standard_search.semantic_scholar, "search", return_value=[]) as s2_mock:
                session = standard_search.search("钙钛矿太阳能电池 稳定性", limit=5, config=cfg)

            self.assertTrue(session.session_id.startswith("search-"))
            self.assertEqual(len(session.hits), 5)
            self.assertGreaterEqual(oa_mock.call_count, 1)
            self.assertFalse(s2_mock.called)
            self.assertEqual(session.source_summary["openalex"], 5)
            self.assertTrue(session.upgrade_suggested)
            self.assertTrue((Path(tmp) / "search" / "sessions" / f"{session.session_id}.json").exists())

    def test_standard_search_suppresses_s2_when_openalex_satisfies_limit_even_with_s2_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(cache_dir=tmp, openalex_api_key="oa-key", semantic_scholar_api_key="s2-key")
            openalex_hits = [
                SearchHit(title=f"Paper {i}", doi=f"10.1000/{i}", source="openalex", backend="openalex")
                for i in range(3)
            ]
            with mock.patch.object(standard_search.openalex, "search", return_value=openalex_hits), \
                 mock.patch.object(standard_search.semantic_scholar, "search", return_value=[]) as s2_mock:
                standard_search.search("graph neural network", limit=3, config=cfg)

            s2_mock.assert_not_called()

    def test_standard_search_falls_back_to_s2_when_openalex_rate_limited(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(cache_dir=tmp, semantic_scholar_api_key="s2-key")
            s2_result = standard_search.semantic_scholar.SearchResult(
                title="Fallback Paper",
                doi="10.1000/fallback",
                citation_count=3,
            )
            with mock.patch.object(standard_search.openalex, "search", side_effect=standard_search.openalex.OpenAlexRateLimitError("429")), \
                 mock.patch.object(standard_search.semantic_scholar, "search", return_value=[s2_result]):
                session = standard_search.search("graph neural network", limit=5, config=cfg)

            self.assertEqual(session.hits[0].title, "Fallback Paper")
            self.assertEqual(session.errors[0].source, "openalex")
            self.assertEqual(session.errors[0].code, "rate_limited")
            self.assertFalse(session.upgrade_suggested)

    def test_standard_search_merges_openalex_and_s2_by_doi(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(cache_dir=tmp, semantic_scholar_api_key="s2-key")
            oa_hit = SearchHit(title="Paper", doi="10.1000/merge", source="openalex", backend="openalex")
            s2_result = standard_search.semantic_scholar.SearchResult(
                title="Paper",
                doi="10.1000/merge",
                abstract="Longer abstract from S2",
                citation_count=99,
            )
            with mock.patch.object(standard_search.openalex, "search", return_value=[oa_hit]), \
                 mock.patch.object(standard_search.semantic_scholar, "search", return_value=[s2_result]):
                session = standard_search.search("graph neural network", limit=5, config=cfg, enrich_with_s2=True)

            self.assertEqual(len(session.hits), 1)
            self.assertEqual(session.hits[0].citation_count, 99)
            self.assertIn("openalex", session.hits[0].sources)
            self.assertIn("semantic_scholar", session.hits[0].sources)

    def test_standard_search_persists_v2_origin_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(cache_dir=tmp, openalex_api_key="oa-key")
            openalex_hits = [SearchHit(title="Paper", doi="10.1000/a", source="openalex", backend="openalex")]
            with mock.patch.object(standard_search.openalex, "search", return_value=openalex_hits), \
                 mock.patch.object(standard_search.semantic_scholar, "search", return_value=[]):
                session = standard_search.search("graph neural network", limit=1, config=cfg)

            data = json.loads((Path(tmp) / "search" / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
            self.assertEqual(data["origin"]["kind"], "source_execution")
            self.assertIn("route_reason", data["origin"])


if __name__ == "__main__":
    unittest.main()

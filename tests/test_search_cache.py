import tempfile
import unittest
from pathlib import Path

from vpnsci_sustech.sources.search_cache import (
    SearchSession,
    cache_key,
    load_cached_hits,
    load_session,
    save_cached_hits,
    save_session,
)
from vpnsci_sustech.sources.search_models import SearchError, SearchHit


class SearchCacheTests(unittest.TestCase):
    def test_cache_key_is_stable_and_includes_filters(self):
        a = cache_key("OpenAlex", "query", {"year": "2020-", "limit": 5})
        b = cache_key("OpenAlex", "query", {"limit": 5, "year": "2020-"})
        c = cache_key("OpenAlex", "query", {"limit": 10, "year": "2020-"})
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_save_and_load_session_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-test",
                query="graph neural networks",
                display_query="Graph neural networks",
                filters={"year_range": "2020-"},
                hits=[SearchHit(title="Paper", doi="10.1000/a", hit_key="doi:10.1000/a", source="openalex")],
                source_summary={"openalex": 1},
                errors=[SearchError(source="semantic_scholar", code="rate_limited", message="HTTP 429")],
                upgrade_suggested=True,
                decision_reasons=["result_count>=5"],
                origin={"engine": "openalex", "kind": "source_execution"},
                derivation={"root_session_id": "search-root"},
                recovered_label="Recovered graph neural networks",
            )

            path = save_session(session, Path(tmp))
            loaded = load_session("search-test", Path(tmp))

            self.assertTrue(path.exists())
            self.assertEqual(loaded.session_id, "search-test")
            self.assertEqual(loaded.hits[0].doi, "10.1000/a")
            self.assertEqual(loaded.hits[0].hit_key, "doi:10.1000/a")
            self.assertEqual(loaded.errors[0].code, "rate_limited")
            self.assertTrue(loaded.upgrade_suggested)
            self.assertEqual(loaded.schema_version, 2)
            self.assertEqual(loaded.display_query, "Graph neural networks")
            self.assertEqual(loaded.origin["engine"], "openalex")
            self.assertEqual(loaded.derivation["root_session_id"], "search-root")
            self.assertEqual(loaded.recovered_label, "Recovered graph neural networks")

    def test_save_and_load_cached_hits_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            hits = [SearchHit(title="Paper", doi="10.1000/a")]
            save_cached_hits("openalex", "query", {"limit": 5}, hits, Path(tmp))

            loaded = load_cached_hits("openalex", "query", {"limit": 5}, Path(tmp))

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded[0].doi, "10.1000/a")
            self.assertEqual(loaded[0].hit_key, "doi:10.1000/a")

    def test_load_session_coerces_legacy_v1_schema_into_v2_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            session_path = Path(tmp) / "search" / "sessions" / "search-legacy.json"
            session_path.parent.mkdir(parents=True, exist_ok=True)
            session_path.write_text(
                """
                {
                  "session_id": "search-legacy",
                  "query": "legacy query",
                  "filters": {},
                  "hits": [
                    {
                      "title": "知网论文",
                      "cnki_id": "ABC123",
                      "unknown_field": "ignored"
                    }
                  ],
                  "source_summary": {"cnki": 1}
                }
                """,
                encoding="utf-8",
            )

            loaded = load_session("search-legacy", Path(tmp))

            self.assertEqual(loaded.schema_version, 2)
            self.assertEqual(loaded.display_query, "legacy query")
            self.assertEqual(loaded.recovered_label, "")
            self.assertEqual(loaded.origin, {})
            self.assertEqual(loaded.derivation, {})
            self.assertEqual(loaded.hits[0].hit_key, "cnki:ABC123")

    def test_load_cached_hits_uses_search_hit_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "search" / "entries" / f"{cache_key('cnki', 'query', {})}.json"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                """
                {
                  "source": "cnki",
                  "query": "query",
                  "filters": {},
                  "created_at_epoch": 4102444800,
                  "hits": [
                    {
                      "title": "知网论文",
                      "cnki_id": "ABC123",
                      "unknown_field": "ignored"
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )

            loaded = load_cached_hits("cnki", "query", {}, Path(tmp))

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded[0].hit_key, "cnki:ABC123")


if __name__ == "__main__":
    unittest.main()

import unittest
from types import SimpleNamespace
from unittest import mock

from vpnsci_sustech.sources import semantic_scholar


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class SemanticScholarTests(unittest.TestCase):
    def test_search_falls_back_to_api_key_after_anonymous_429(self):
        anon = _Response(429)
        key = _Response(
            200,
            {
                "data": [
                    {
                        "title": "Keyed Search Result",
                        "authors": [{"name": "A"}],
                        "year": 2024,
                        "abstract": "a",
                        "externalIds": {"DOI": "10.1234/key"},
                        "journal": {"name": "J"},
                        "citationCount": 1,
                        "url": "https://example.com",
                    }
                ]
            },
        )

        calls = []

        def fake_get(url, params=None, timeout=None, headers=None):
            calls.append({"url": url, "params": params, "headers": headers or {}})
            return anon if len(calls) == 1 else key

        with mock.patch.object(semantic_scholar, "MAX_RETRIES", 1), mock.patch.object(
            semantic_scholar.requests, "get", side_effect=fake_get
        ):
            results = semantic_scholar.search("test query", limit=1, api_key="S2-KEY")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Keyed Search Result")
        self.assertEqual(calls[0]["headers"], {})
        self.assertEqual(calls[1]["headers"].get("x-api-key"), "S2-KEY")

    def test_api_key_requests_are_throttled_to_one_per_second(self):
        with mock.patch.object(semantic_scholar, "_last_api_key_request_at", 0.0), mock.patch.object(
            semantic_scholar.time, "monotonic", side_effect=[10.0, 10.2, 11.0]
        ), mock.patch.object(semantic_scholar.time, "sleep") as sleep_mock:
            semantic_scholar._throttle_api_key_requests()
            semantic_scholar._throttle_api_key_requests()

        sleep_mock.assert_called_once()
        self.assertAlmostEqual(sleep_mock.call_args.args[0], 0.8, places=6)

    def test_to_search_hit_preserves_semantic_scholar_fields(self):
        result = semantic_scholar.SearchResult(
            title="Example",
            authors=["Alice"],
            year=2024,
            abstract="Abstract",
            doi="10.1000/example",
            arxiv_id="2401.12345",
            journal="Journal",
            citation_count=7,
            s2_url="https://semanticscholar.org/paper/id",
            paper_id="S2ID",
        )

        hit = semantic_scholar.to_search_hit(
            result,
            query_variant="graph neural networks",
            query_variant_type="translated_keywords",
        )

        self.assertEqual(hit.title, "Example")
        self.assertEqual(hit.doi, "10.1000/example")
        self.assertEqual(hit.arxiv_id, "2401.12345")
        self.assertEqual(hit.url, "https://semanticscholar.org/paper/id")
        self.assertEqual(hit.s2_paper_id, "S2ID")
        self.assertEqual(hit.source, "semantic_scholar")
        self.assertEqual(hit.query_variant_type, "translated_keywords")

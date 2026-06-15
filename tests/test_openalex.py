import unittest
from unittest import mock

from vpnsci_sustech.sources import openalex


class _Resp:
    def __init__(self, status_code=200, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class OpenAlexTests(unittest.TestCase):
    def test_reconstructs_abstract_from_inverted_index(self):
        abstract = openalex.abstract_from_inverted_index(
            {"Graph": [0], "neural": [1], "networks": [2], "work": [3]}
        )
        self.assertEqual(abstract, "Graph neural networks work")

    def test_parse_work_to_search_hit(self):
        work = {
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.1000/example",
            "display_name": "Example Paper",
            "publication_year": 2024,
            "cited_by_count": 12,
            "abstract_inverted_index": {"Example": [0], "abstract": [1]},
            "authorships": [
                {"author": {"display_name": "Alice"}},
                {"author": {"display_name": "Bob"}},
            ],
            "primary_location": {
                "source": {"display_name": "Example Journal"},
                "landing_page_url": "https://journal.example/paper",
                "pdf_url": "https://journal.example/paper.pdf",
            },
            "ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/123", "pmcid": "PMC123"},
        }

        hit = openalex.work_to_search_hit(
            work,
            query_variant="钙钛矿",
            query_variant_type="original",
        )

        self.assertEqual(hit.title, "Example Paper")
        self.assertEqual(hit.doi, "10.1000/example")
        self.assertEqual(hit.year, 2024)
        self.assertEqual(hit.citation_count, 12)
        self.assertEqual(hit.abstract, "Example abstract")
        self.assertEqual(hit.authors, ["Alice", "Bob"])
        self.assertEqual(hit.journal, "Example Journal")
        self.assertEqual(hit.url, "https://journal.example/paper")
        self.assertEqual(hit.pdf_url, "https://journal.example/paper.pdf")
        self.assertEqual(hit.openalex_id, "https://openalex.org/W123")
        self.assertEqual(hit.pmid, "123")
        self.assertEqual(hit.pmcid, "PMC123")
        self.assertEqual(hit.source, "openalex")
        self.assertEqual(hit.query_variant_type, "original")

    def test_search_sends_api_key_select_and_year_filter(self):
        payload = {"results": [{"display_name": "A", "doi": "https://doi.org/10.1/a"}]}
        with mock.patch.object(openalex.requests, "get", return_value=_Resp(payload=payload)) as get_mock:
            hits = openalex.search("graph neural networks", limit=5, year_range="2020-2024", api_key="key")

        self.assertEqual(len(hits), 1)
        params = get_mock.call_args.kwargs["params"]
        self.assertEqual(params["search"], "graph neural networks")
        self.assertEqual(params["per_page"], 5)
        self.assertIn("api_key", params)
        self.assertIn("from_publication_date:2020-01-01", params["filter"])
        self.assertIn("to_publication_date:2024-12-31", params["filter"])
        self.assertIn("select", params)

    def test_search_can_read_api_key_from_environment(self):
        payload = {"results": []}
        with mock.patch.dict(openalex.os.environ, {"OPENALEX_API_KEY": "env-key"}), \
             mock.patch.object(openalex.requests, "get", return_value=_Resp(payload=payload)) as get_mock:
            openalex.search("graph neural networks", limit=5)

        self.assertEqual(get_mock.call_args.kwargs["params"]["api_key"], "env-key")

    def test_search_raises_rate_limit_error_on_429(self):
        with mock.patch.object(openalex.requests, "get", return_value=_Resp(status_code=429, text="too many")):
            with self.assertRaises(openalex.OpenAlexRateLimitError):
                openalex.search("query", limit=5)


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import unittest

from tests.test_paper_search_pro_adapter import WritableTemporaryDirectory
from vpnsci_sustech.paper_search_pro_adapter import _write_materialized_data
from vpnsci_sustech.sources.search_cache import SearchSession
from vpnsci_sustech.sources.search_models import SearchHit


class PaperSearchCnkiFieldsTests(unittest.TestCase):
    def test_seed_report_preserves_cnki_metadata_fields(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-cnki",
                query="钙钛矿 中国知网",
                filters={"backend": "cnki"},
                hits=[
                    SearchHit(
                        hit_key="cnki:ABC123",
                        title="钙钛矿太阳能电池稳定性研究",
                        authors=["张三"],
                        year=2024,
                        doi="10.1234/example",
                        citation_count=12,
                        cnki_id="ABC123",
                        dbcode="CJFD",
                        dbname="中国学术期刊网络出版总库",
                        source_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                        download_format="caj",
                        local_file="F:/AI playground/TempFiles/钙钛矿太阳能电池稳定性研究 - 张三.caj",
                        result_type="journal",
                        keywords=["钙钛矿", "太阳能电池"],
                        affiliations=["南方科技大学"],
                        source="cnki",
                        backend="cnki",
                        sources=["cnki"],
                    )
                ],
                source_summary={"cnki": 1},
            )

            materialized = _write_materialized_data(session, Path(tmp), display_query="钙钛矿 中国知网")
            papers = json.loads((materialized / "paper_list.json").read_text(encoding="utf-8"))
            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))

            self.assertEqual(papers[0]["cnki_id"], "ABC123")
            self.assertEqual(papers[0]["source_url"], "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123")
            self.assertEqual(papers[0]["download_format"], "caj")
            self.assertEqual(papers[0]["local_file"], "F:/AI playground/TempFiles/钙钛矿太阳能电池稳定性研究 - 张三.caj")
            self.assertEqual(papers[0]["result_type"], "journal")
            self.assertEqual(papers[0]["id"], "cnki:ABC123")
            self.assertEqual(papers[0]["doi"], "10.1234/example")
            self.assertEqual(papers[0]["citation_count"], 12)
            self.assertEqual(papers[0]["dbcode"], "CJFD")
            self.assertEqual(papers[0]["dbname"], "中国学术期刊网络出版总库")
            self.assertEqual(papers[0]["keywords"], ["钙钛矿", "太阳能电池"])
            self.assertEqual(papers[0]["affiliations"], ["南方科技大学"])
            self.assertEqual(metadata["seed_source"], "cnki")
            self.assertTrue(metadata["cnki_fields"]["present"])
            self.assertEqual(metadata["cnki_fields"]["hit_count"], 1)
            self.assertEqual(metadata["cnki_fields"]["preserved_counts"]["cnki_id"], 1)
            self.assertIn("local_file", metadata["cnki_fields"]["fields"])

    def test_seed_report_marks_mixed_source_when_cnki_is_not_only_source(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-mixed",
                query="钙钛矿",
                filters={},
                hits=[
                    SearchHit(
                        title="CNKI paper",
                        cnki_id="ABC123",
                        source="cnki",
                        backend="cnki",
                        sources=["cnki"],
                    ),
                    SearchHit(
                        title="OpenAlex paper",
                        doi="10.1234/example",
                        source="openalex",
                        backend="openalex",
                        sources=["openalex"],
                    ),
                ],
                source_summary={"cnki": 1, "openalex": 1},
            )

            materialized = _write_materialized_data(session, Path(tmp), display_query="钙钛矿")
            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))

            self.assertEqual(metadata["seed_source"], "mixed")
            self.assertTrue(metadata["cnki_fields"]["present"])
            self.assertEqual(metadata["cnki_fields"]["hit_count"], 1)

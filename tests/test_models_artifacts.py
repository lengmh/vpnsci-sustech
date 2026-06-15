import json
import unittest

from vpnsci_sustech.models import Artifact, Paper


class PaperArtifactModelTests(unittest.TestCase):
    def test_paper_json_roundtrip_preserves_artifacts(self):
        paper = Paper(
            title="CNKI Paper",
            artifacts=[
                Artifact(
                    path="F:/AI playground/TempFiles/CNKI Paper.caj",
                    format="caj",
                    kind="source_file",
                    source_url="https://kns.cnki.net/kcms2/article/abstract?v=x",
                    text_extracted=False,
                    note="原文已保存但未解析全文",
                )
            ],
        )

        loaded = Paper.from_json(paper.to_json())

        self.assertEqual(len(loaded.artifacts), 1)
        self.assertIsInstance(loaded.artifacts[0], Artifact)
        self.assertEqual(loaded.artifacts[0].format, "caj")
        self.assertFalse(loaded.artifacts[0].text_extracted)

    def test_from_json_accepts_old_cache_without_artifacts(self):
        loaded = Paper.from_json('{"title": "Old", "pdf_path": "old.pdf"}')

        self.assertEqual(loaded.title, "Old")
        self.assertEqual(loaded.pdf_path, "old.pdf")
        self.assertEqual(loaded.artifacts, [])

    def test_from_json_accepts_artifacts_as_list_of_dicts(self):
        loaded = Paper.from_json(
            {
                "title": "CNKI",
                "artifacts": [
                    {
                        "path": "paper.pdf",
                        "format": "pdf",
                        "kind": "fulltext",
                        "source_url": "https://example.test/paper",
                        "text_extracted": True,
                        "note": "",
                    }
                ],
            }
        )

        self.assertIsInstance(loaded.artifacts[0], Artifact)
        self.assertEqual(loaded.artifacts[0].path, "paper.pdf")

    def test_markdown_lists_artifacts_even_without_full_text(self):
        paper = Paper(
            title="CNKI CAJ",
            artifacts=[
                Artifact(
                    path="paper.caj",
                    format="caj",
                    kind="source_file",
                    text_extracted=False,
                    note="原文已保存但未解析全文",
                )
            ],
        )

        markdown = paper.to_markdown(include_pdf_path=True)

        self.assertIn("## Artifacts", markdown)
        self.assertIn("paper.caj", markdown)
        self.assertIn("text_extracted=false", markdown)
        self.assertIn("原文已保存但未解析全文", markdown)

    def test_to_json_contains_artifacts(self):
        paper = Paper(artifacts=[Artifact(path="paper.pdf", format="pdf")])

        data = json.loads(paper.to_json())

        self.assertEqual(data["artifacts"][0]["path"], "paper.pdf")

    def test_paper_json_roundtrip_preserves_cnki_rich_metadata_fields(self):
        paper = Paper(
            title="CNKI Paper",
            doi="10.1234/example",
            citation_count=12,
            cnki_id="ABC123",
            dbcode="CJFD",
            dbname="中国学术期刊网络出版总库",
            result_type="journal",
            download_format="caj",
            keywords=["钙钛矿", "太阳能电池"],
            affiliations=["南方科技大学"],
            fund="国家自然科学基金",
            classification="TM914.4",
            publication_info="2024年第3期 12-20页",
            online_first=True,
            citation_network={"inbound": 5, "outbound": 12},
        )

        loaded = Paper.from_json(paper.to_json())

        self.assertEqual(loaded.doi, "10.1234/example")
        self.assertEqual(loaded.citation_count, 12)
        self.assertEqual(loaded.cnki_id, "ABC123")
        self.assertEqual(loaded.dbcode, "CJFD")
        self.assertEqual(loaded.dbname, "中国学术期刊网络出版总库")
        self.assertEqual(loaded.result_type, "journal")
        self.assertEqual(loaded.download_format, "caj")
        self.assertEqual(loaded.keywords, ["钙钛矿", "太阳能电池"])
        self.assertEqual(loaded.affiliations, ["南方科技大学"])
        self.assertEqual(loaded.fund, "国家自然科学基金")
        self.assertEqual(loaded.classification, "TM914.4")
        self.assertEqual(loaded.publication_info, "2024年第3期 12-20页")
        self.assertTrue(loaded.online_first)
        self.assertEqual(loaded.citation_network, {"inbound": 5, "outbound": 12})


if __name__ == "__main__":
    unittest.main()

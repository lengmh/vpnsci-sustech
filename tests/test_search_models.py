import unittest

from vpnsci_sustech.sources.search_models import (
    SearchHit,
    build_hit_key,
    canonical_key,
    coerce_search_hit,
    merge_hit,
    merge_search_hits,
    normalize_doi,
    normalize_title,
)


class SearchModelsTests(unittest.TestCase):
    def test_normalize_doi_strips_url_prefix_and_lowercases(self):
        self.assertEqual(
            normalize_doi("https://doi.org/10.1109/ICNC57223.2023.10074111"),
            "10.1109/icnc57223.2023.10074111",
        )

    def test_normalize_title_collapses_punctuation_and_space(self):
        self.assertEqual(
            normalize_title("  Network: Anomaly   Detection! "),
            "network anomaly detection",
        )

    def test_canonical_key_prefers_doi(self):
        hit = SearchHit(title="Different Title", doi="DOI:10.1000/ABC", year=2024)
        self.assertEqual(canonical_key(hit), "doi:10.1000/abc")

    def test_canonical_key_uses_arxiv_when_no_doi(self):
        hit = SearchHit(title="Title", arxiv_id="2401.12345")
        self.assertEqual(canonical_key(hit), "arxiv:2401.12345")

    def test_build_hit_key_uses_cnki_id_when_no_doi(self):
        hit = SearchHit(title="知网论文", cnki_id="ABC123")
        self.assertEqual(build_hit_key(hit), "cnki:ABC123")

    def test_canonical_key_uses_cnki_id_before_title_year(self):
        hit = SearchHit(title="知网论文", year=2024, cnki_id="ABC123")
        self.assertEqual(canonical_key(hit), "cnki:ABC123")

    def test_canonical_key_uses_title_year_last(self):
        hit = SearchHit(title="Graph Neural Networks for Anomaly Detection", year=2023)
        self.assertEqual(canonical_key(hit), "title:graph neural networks for anomaly detection:2023")

    def test_coerce_search_hit_backfills_hit_key_and_ignores_unknown_fields(self):
        hit = coerce_search_hit(
            {
                "title": "知网论文",
                "cnki_id": "ABC123",
                "unknown": "ignored",
            }
        )

        self.assertEqual(hit.title, "知网论文")
        self.assertEqual(hit.hit_key, "cnki:ABC123")

    def test_merge_hit_preserves_richer_fields_and_provenance(self):
        base = SearchHit(
            title="Graph Neural Networks for Anomaly Detection",
            doi="10.1109/example",
            hit_key="doi:10.1109/example",
            source="openalex",
            backend="openalex",
            query_variant="图神经网络 异常检测",
            query_variant_type="original",
            sources=["openalex"],
            query_variants=["original:图神经网络 异常检测"],
        )
        extra = SearchHit(
            title="Graph Neural Networks for Anomaly Detection",
            doi="10.1109/example",
            url="https://example.org/paper",
            abstract="Detailed abstract",
            citation_count=42,
            source="semantic_scholar",
            backend="semantic_scholar",
            query_variant="graph neural networks anomaly detection",
            query_variant_type="translated_keywords",
            sources=["semantic_scholar"],
            query_variants=["translated_keywords:graph neural networks anomaly detection"],
        )

        merged = merge_hit(base, extra)

        self.assertEqual(merged.url, "https://example.org/paper")
        self.assertEqual(merged.abstract, "Detailed abstract")
        self.assertEqual(merged.citation_count, 42)
        self.assertEqual(merged.sources, ["openalex", "semantic_scholar"])
        self.assertEqual(
            merged.query_variants,
            [
                "original:图神经网络 异常检测",
                "translated_keywords:graph neural networks anomaly detection",
            ],
        )
        self.assertEqual(merged.hit_key, "doi:10.1109/example")

    def test_merge_hit_preserves_cnki_and_recovery_fields(self):
        base = SearchHit(
            title="知网论文",
            cnki_id="ABC123",
            hit_key="cnki:ABC123",
            source="cnki",
        )
        extra = SearchHit(
            title="知网论文",
            cnki_id="ABC123",
            hit_key="cnki:ABC123",
            source_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
            download_format="caj",
            local_file="F:/AI playground/TempFiles/source.caj",
            result_type="journal",
            dbcode="CJFD",
            dbname="中国学术期刊网络出版总库",
            keywords=["钙钛矿"],
            affiliations=["南方科技大学"],
        )

        merged = merge_hit(base, extra)

        self.assertEqual(merged.hit_key, "cnki:ABC123")
        self.assertEqual(merged.source_url, "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123")
        self.assertEqual(merged.download_format, "caj")
        self.assertEqual(merged.local_file, "F:/AI playground/TempFiles/source.caj")
        self.assertEqual(merged.result_type, "journal")
        self.assertEqual(merged.dbcode, "CJFD")
        self.assertEqual(merged.dbname, "中国学术期刊网络出版总库")
        self.assertEqual(merged.keywords, ["钙钛矿"])
        self.assertEqual(merged.affiliations, ["南方科技大学"])

    def test_merge_search_hits_does_not_merge_different_dois_by_title(self):
        hits = [
            SearchHit(title="Same Title", doi="10.1000/a", year=2023),
            SearchHit(title="Same Title", doi="10.1000/b", year=2023),
        ]

        merged = merge_search_hits(hits)

        self.assertEqual(len(merged), 2)

    def test_search_hit_has_cnki_artifact_fields(self):
        hit = SearchHit(
            title="知网论文",
            cnki_id="ABC123",
            source_url="https://kns.cnki.net/kcms2/article/abstract?v=x",
            download_format="caj",
            local_file="F:/AI playground/TempFiles/知网论文.caj",
            result_type="学位论文",
        )

        self.assertEqual(hit.cnki_id, "ABC123")
        self.assertEqual(hit.download_format, "caj")
        self.assertEqual(hit.result_type, "学位论文")


if __name__ == "__main__":
    unittest.main()

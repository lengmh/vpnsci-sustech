import json
import tempfile
import unittest
from pathlib import Path

from vpnsci_sustech.report_recovery import (
    classify_report_recovery,
    recover_session_from_download_sidecar,
    infer_quality_profile,
    resolve_report_recovery_session,
    split_missing_and_insufficient_fields,
)


class ReportRecoveryTests(unittest.TestCase):
    def test_classify_report_recovery_prefers_sidecar_over_weak_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sidecar = base / "download-workflows" / "download-123.json"
            sidecar.parent.mkdir(parents=True, exist_ok=True)
            sidecar.write_text(
                json.dumps(
                    {
                        "workflow_id": "download-123",
                        "display_query": "展示标题",
                        "items": [{"hit_key": "cnki:ABC123"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            recovery = classify_report_recovery(sidecar=sidecar, local_files=[base / "paper.caj"])

            self.assertEqual(recovery.recovery_kind, "A")
            self.assertEqual(recovery.capability, "standard")
            self.assertEqual(recovery.reason, "sidecar_available")

    def test_classify_report_recovery_falls_back_to_weak_recovery_without_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            local_file = base / "paper.caj"
            local_file.write_bytes(b"content")

            recovery = classify_report_recovery(local_files=[local_file])

            self.assertEqual(recovery.recovery_kind, "C")
            self.assertEqual(recovery.capability, "degraded")
            self.assertEqual(recovery.reason, "weak_local_files_only")

    def test_classify_report_recovery_keeps_legacy_json_as_compatible_b(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report_json = base / "materialized" / "report_data.json"
            report_json.parent.mkdir(parents=True, exist_ok=True)
            report_json.write_text("{}", encoding="utf-8")

            recovery = classify_report_recovery(report_json=report_json)

            self.assertEqual(recovery.recovery_kind, "B")
            self.assertEqual(recovery.capability, "compatible")
            self.assertEqual(recovery.reason, "legacy_report_json_available")

    def test_split_missing_and_insufficient_fields_distinguishes_semantics(self):
        missing, insufficient = split_missing_and_insufficient_fields(
            total_hits=6,
            field_presence={"actual_queries": 0, "year": 6, "citation_count": 2},
        )

        self.assertIn("actual_queries", missing)
        self.assertIn("citation_count", insufficient)
        self.assertNotIn("year", missing)

    def test_infer_quality_profile_for_html_import_uses_limited_modes(self):
        profile = infer_quality_profile(
            origin_kind="html_import",
            actual_queries=[{"source": "CNKI", "queries": ["滤波耦合器"]}],
            total_hits=6,
            field_presence={"year": 6, "citation_count": 2, "abstract_or_keywords": 2},
            original_query="",
            display_query="滤波耦合器",
            recovered_label="",
        )

        self.assertEqual(profile["query_trace_level"], "imported")
        self.assertEqual(profile["audit_level"], "limited")
        self.assertEqual(profile["title_mode"], "summary")
        self.assertEqual(profile["query_strip_mode"], "imported_queries")
        self.assertEqual(profile["discovery_curve_mode"], "disabled")
        self.assertEqual(profile["citation_analysis_mode"], "disabled")
        self.assertEqual(profile["topic_analysis_mode"], "limited")

    def test_infer_quality_profile_for_recovered_label_uses_recovered_summary(self):
        profile = infer_quality_profile(
            origin_kind="weak_recovery",
            actual_queries=[],
            total_hits=1,
            field_presence={},
            original_query="",
            display_query="",
            recovered_label="CNKI 下载结果集合",
        )

        self.assertEqual(profile["query_trace_level"], "recovered")
        self.assertEqual(profile["audit_level"], "minimal")
        self.assertEqual(profile["title_mode"], "recovered_summary")
        self.assertEqual(profile["query_strip_mode"], "hidden")

    def test_recover_session_from_download_sidecar_returns_search_session(self):
        sidecar = {
            "workflow_id": "download-123",
            "root_session_id": "search-root",
            "source_session_id": "search-source",
            "derived_session_id": "search-derived",
            "original_query": "",
            "display_query": "CNKI 下载结果集合",
            "recovered_label": "CNKI 下载结果集合",
            "actual_queries": [],
            "items": [
                {
                    "hit_key": "cnki:ABC123",
                    "title": "知网论文",
                    "authors": ["张三"],
                    "source": "cnki",
                    "source_url": "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                    "local_file": "F:/AI playground/TempFiles/知网论文.caj",
                    "download_format": "caj",
                    "result_type": "downloaded_caj",
                }
            ],
        }

        session = recover_session_from_download_sidecar(sidecar)

        self.assertEqual(session.origin["kind"], "download_sidecar")
        self.assertEqual(session.display_query, "CNKI 下载结果集合")
        self.assertEqual(session.recovered_label, "CNKI 下载结果集合")
        self.assertEqual(session.derivation["source_session_id"], "search-source")
        self.assertEqual(session.derivation["root_session_id"], "search-root")
        self.assertEqual(session.hits[0].hit_key, "cnki:ABC123")

    def test_resolve_report_recovery_session_can_use_explicit_legacy_report_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            materialized = base / "materialized"
            materialized.mkdir(parents=True, exist_ok=True)
            report_json = materialized / "report_data.json"
            report_json.write_text(
                json.dumps(
                    {
                        "metadata": {
                            "query": "恢复后的展示标题",
                            "original_query": "原始检索词",
                            "display_query": "恢复后的展示标题",
                            "recovered_label": "",
                            "generated_at": "2026-06-04T04:00:00+00:00",
                            "source_summary": {"cnki": 1},
                            "seed_session_id": "search-report",
                            "seed_source": "cnki",
                            "quality_profile": {
                                "query_trace_level": "imported",
                            },
                        },
                        "paper_list": [
                            {
                                "paper_id": "cnki:ABC123",
                                "title": "知网论文",
                                "authors": ["张三"],
                                "year": 2024,
                                "source": "cnki",
                                "source_url": "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                                "cnki_id": "ABC123",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            resolved = resolve_report_recovery_session(report_json=report_json, prefer="B")

            self.assertEqual(resolved.decision.recovery_kind, "B")
            self.assertEqual(resolved.session.origin["kind"], "html_import")
            self.assertEqual(resolved.session.query, "原始检索词")
            self.assertEqual(resolved.session.display_query, "恢复后的展示标题")
            self.assertEqual(resolved.session.hits[0].hit_key, "cnki:ABC123")

    def test_resolve_report_recovery_session_prefers_sidecar_but_compares_legacy_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sidecar = base / "download-workflows" / "download-123.json"
            sidecar.parent.mkdir(parents=True, exist_ok=True)
            sidecar.write_text(
                json.dumps(
                    {
                        "workflow_id": "download-123",
                        "created_at": "2026-06-04T05:00:00+00:00",
                        "display_query": "CNKI 下载结果集合",
                        "recovered_label": "CNKI 下载结果集合",
                        "items": [
                            {
                                "hit_key": "cnki:ABC123",
                                "title": "知网论文",
                                "source": "cnki",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            materialized = base / "materialized"
            materialized.mkdir(parents=True, exist_ok=True)
            report_json = materialized / "report_data.json"
            report_json.write_text(
                json.dumps(
                    {
                        "metadata": {
                            "query": "CNKI 下载结果集合",
                            "display_query": "CNKI 下载结果集合",
                            "generated_at": "2026-06-04T04:00:00+00:00",
                            "source_summary": {"cnki": 1},
                            "seed_session_id": "search-report",
                            "seed_source": "cnki",
                        },
                        "paper_list": [
                            {
                                "paper_id": "cnki:ABC123",
                                "title": "知网论文",
                                "authors": ["张三"],
                                "source": "cnki",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            resolved = resolve_report_recovery_session(sidecar=sidecar, report_json=report_json)

            self.assertEqual(resolved.decision.recovery_kind, "A")
            self.assertTrue(resolved.decision.details["identity_match"])
            self.assertEqual(resolved.decision.details["freshness_winner"], "sidecar")
            self.assertEqual(resolved.decision.capability, "standard")

    def test_resolve_report_recovery_session_falls_back_to_weak_local_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            local_file = Path(tmp) / "paper.caj"
            local_file.write_bytes(b"content")

            resolved = resolve_report_recovery_session(
                local_files=[local_file],
                display_query="Recovered local files",
            )

            self.assertEqual(resolved.decision.recovery_kind, "C")
            self.assertEqual(resolved.session.origin["kind"], "weak_recovery")
            self.assertEqual(resolved.session.display_query, "Recovered local files")
            self.assertEqual(resolved.session.hits[0].local_file, str(local_file))

    def test_resolve_report_recovery_session_downgrades_incomplete_sidecar_to_degraded_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sidecar = base / "download-workflows" / "download-123.json"
            sidecar.parent.mkdir(parents=True, exist_ok=True)
            sidecar.write_text(
                json.dumps(
                    {
                        "workflow_id": "download-123",
                        "display_query": "",
                        "recovered_label": "CNKI 下载结果集合",
                        "items": [{"hit_key": "cnki:ABC123", "title": "知网论文", "source": "cnki"}],
                        "report_recovery_capability": "standard",
                        "missing_fields": ["root_session_id", "source_session_id", "actual_queries"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            resolved = resolve_report_recovery_session(sidecar=sidecar)

            self.assertEqual(resolved.decision.recovery_kind, "A")
            self.assertEqual(resolved.decision.capability, "degraded")
            self.assertEqual(resolved.session.origin["report_recovery_capability"], "degraded")

    def test_infer_quality_profile_for_download_sidecar_can_preserve_formal_audit(self):
        profile = infer_quality_profile(
            origin_kind="download_sidecar",
            actual_queries=[{"source": "CNKI", "queries": ["滤波耦合器"]}],
            total_hits=10,
            field_presence={"year": 10, "citation_count": 6, "abstract_or_keywords": 7},
            original_query="滤波耦合器",
            display_query="滤波耦合器结果集合",
            recovered_label="",
        )

        self.assertEqual(profile["query_trace_level"], "recovered")
        self.assertEqual(profile["audit_level"], "full")
        self.assertEqual(profile["title_mode"], "search")
        self.assertEqual(profile["query_strip_mode"], "actual_queries")
        self.assertEqual(profile["discovery_curve_mode"], "enabled")


if __name__ == "__main__":
    unittest.main()

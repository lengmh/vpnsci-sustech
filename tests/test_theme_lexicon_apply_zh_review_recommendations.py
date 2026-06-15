from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "apply_zh_review_recommendations.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_module():
    spec = importlib.util.spec_from_file_location("apply_zh_review_recommendations", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class ApplyZhReviewRecommendationsTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_applies_explicit_recommendations_and_leaves_unlisted_zh_needs_review(self) -> None:
        review = self.root / "review_decisions.jsonl"
        recs = self.root / "recommendations.json"
        write_jsonl(
            review,
            [
                {"concept_id": "c1", "alias": "信道估计", "lang": "zh", "decision": "needs_review", "review_tier": "needs_review"},
                {"concept_id": "c2", "alias": "错误别名", "lang": "zh", "decision": "needs_review", "review_tier": "needs_review"},
                {"concept_id": "c3", "alias": "歧义别名", "lang": "zh", "decision": "needs_review", "review_tier": "needs_review"},
                {"concept_id": "c4", "alias": "english", "lang": "en", "decision": "accept", "review_tier": "auto_accept"},
            ],
        )
        recs.write_text(
            json.dumps(
                {
                    "recommendations": [
                        {"concept_id": "c2", "alias": "错误别名", "recommendation": "reject", "reason": "wrong", "merge_duplicate_concepts": False},
                        {"concept_id": "c3", "alias": "歧义别名", "recommendation": "blocked", "reason": "ambiguous", "merge_duplicate_concepts": False},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        module = load_module()
        summary = module.apply_zh_review_recommendations(review_decisions_path=review, recommendations_path=recs)

        rows = {(row["concept_id"], row["alias"]): row for row in read_jsonl(review)}
        self.assertEqual(rows[("c1", "信道估计")]["decision"], "needs_review")
        self.assertEqual(rows[("c2", "错误别名")]["decision"], "reject")
        self.assertEqual(rows[("c3", "歧义别名")]["decision"], "blocked")
        self.assertEqual(rows[("c4", "english")]["decision"], "accept")
        self.assertEqual(summary["accept"], 0)
        self.assertEqual(summary["reject"], 1)
        self.assertEqual(summary["blocked"], 1)
        self.assertEqual(summary["accept_missing"], False)

    def test_accept_missing_legacy_mode_accepts_unlisted_zh_needs_review(self) -> None:
        review = self.root / "review_decisions.jsonl"
        recs = self.root / "recommendations.json"
        write_jsonl(
            review,
            [
                {"concept_id": "c1", "alias": "信道估计", "lang": "zh", "decision": "needs_review", "review_tier": "needs_review"},
            ],
        )
        recs.write_text(json.dumps({"recommendations": []}, ensure_ascii=False), encoding="utf-8")

        module = load_module()
        summary = module.apply_zh_review_recommendations(
            review_decisions_path=review,
            recommendations_path=recs,
            accept_missing=True,
        )

        rows = {(row["concept_id"], row["alias"]): row for row in read_jsonl(review)}
        self.assertEqual(rows[("c1", "信道估计")]["decision"], "accept")
        self.assertEqual(summary["accept"], 1)
        self.assertEqual(summary["accept_missing"], True)

    def test_can_apply_explicit_english_recommendations_when_lang_is_en(self) -> None:
        review = self.root / "review_decisions.jsonl"
        recs = self.root / "recommendations.json"
        write_jsonl(
            review,
            [
                {"concept_id": "c1", "alias": "ATP", "lang": "en", "decision": "needs_review", "review_tier": "needs_review"},
                {"concept_id": "c2", "alias": "AMP", "lang": "en", "decision": "needs_review", "review_tier": "needs_review"},
                {"concept_id": "c3", "alias": "信道估计", "lang": "zh", "decision": "needs_review", "review_tier": "needs_review"},
            ],
        )
        recs.write_text(
            json.dumps(
                {
                    "recommendations": [
                        {"concept_id": "c1", "alias": "ATP", "recommendation": "blocked", "reason": "ambiguous acronym", "merge_duplicate_concepts": False},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        module = load_module()
        summary = module.apply_zh_review_recommendations(
            review_decisions_path=review,
            recommendations_path=recs,
            lang="en",
        )

        rows = {(row["concept_id"], row["alias"], row["lang"]): row for row in read_jsonl(review)}
        self.assertEqual(rows[("c1", "ATP", "en")]["decision"], "blocked")
        self.assertEqual(rows[("c2", "AMP", "en")]["decision"], "needs_review")
        self.assertEqual(rows[("c3", "信道估计", "zh")]["decision"], "needs_review")
        self.assertEqual(summary["blocked"], 1)
        self.assertEqual(summary["lang"], "en")
        self.assertEqual(summary["schema_version"], "theme_en_review_apply.v1")
        self.assertEqual(Path(summary["manifest"]).name, "en_review_apply_manifest.json")
        self.assertTrue((review.parent / "en_review_apply_manifest.json").exists())
        self.assertFalse((review.parent / "zh_review_apply_manifest.json").exists())

    def test_explicit_recommendation_lang_prevents_cross_language_key_collision(self) -> None:
        review = self.root / "review_decisions.jsonl"
        recs = self.root / "recommendations.json"
        write_jsonl(
            review,
            [
                {"concept_id": "c1", "alias": "ATP", "lang": "en", "decision": "needs_review", "review_tier": "needs_review"},
                {"concept_id": "c1", "alias": "ATP", "lang": "zh", "decision": "needs_review", "review_tier": "needs_review"},
            ],
        )
        recs.write_text(
            json.dumps(
                {
                    "recommendations": [
                        {"concept_id": "c1", "alias": "ATP", "lang": "zh", "recommendation": "blocked", "reason": "zh only", "merge_duplicate_concepts": False},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        module = load_module()
        summary = module.apply_zh_review_recommendations(
            review_decisions_path=review,
            recommendations_path=recs,
            lang="en",
        )

        rows = {(row["concept_id"], row["alias"], row["lang"]): row for row in read_jsonl(review)}
        self.assertEqual(rows[("c1", "ATP", "en")]["decision"], "needs_review")
        self.assertEqual(rows[("c1", "ATP", "zh")]["decision"], "needs_review")
        self.assertEqual(summary["blocked"], 0)

    def test_accept_missing_is_rejected_for_english_review(self) -> None:
        review = self.root / "review_decisions.jsonl"
        recs = self.root / "recommendations.json"
        write_jsonl(
            review,
            [
                {"concept_id": "c1", "alias": "ATP", "lang": "en", "decision": "needs_review", "review_tier": "needs_review"},
            ],
        )
        recs.write_text(json.dumps({"recommendations": []}, ensure_ascii=False), encoding="utf-8")

        module = load_module()
        with self.assertRaisesRegex(ValueError, "accept_missing is only supported for zh review"):
            module.apply_zh_review_recommendations(
                review_decisions_path=review,
                recommendations_path=recs,
                accept_missing=True,
                lang="en",
            )

        rows = {(row["concept_id"], row["alias"], row["lang"]): row for row in read_jsonl(review)}
        self.assertEqual(rows[("c1", "ATP", "en")]["decision"], "needs_review")


if __name__ == "__main__":
    unittest.main()

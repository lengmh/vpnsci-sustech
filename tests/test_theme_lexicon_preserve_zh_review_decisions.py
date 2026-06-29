from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "preserve_zh_review_decisions.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_module():
    spec = importlib.util.spec_from_file_location("preserve_zh_review_decisions", SCRIPT_PATH)
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


class PreserveZhReviewDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_preserves_prior_zh_accept_reject_blocked_and_leaves_new_needs_review(self) -> None:
        prior = self.root / "prior.jsonl"
        current = self.root / "current.jsonl"
        write_jsonl(
            prior,
            [
                {"concept_id": "c1", "alias": "信道估计", "lang": "zh", "decision": "accept", "review_tier": "review_accept", "reviewer": "subagent-recommended+main-agent-accepted", "reason": "ok"},
                {"concept_id": "c2", "alias": "错误", "lang": "zh", "decision": "reject", "review_tier": "review_reject", "reviewer": "subagent-recommended+main-agent-accepted", "reason": "bad"},
                {"concept_id": "c3", "alias": "歧义", "lang": "zh", "decision": "blocked", "review_tier": "review_blocked", "reviewer": "subagent-recommended+main-agent-accepted", "reason": "ambiguous"},
                {"concept_id": "e1", "alias": "english", "lang": "en", "decision": "accept", "review_tier": "auto_accept"},
            ],
        )
        write_jsonl(
            current,
            [
                {"concept_id": "c1", "alias": "信道估计", "lang": "zh", "decision": "needs_review", "review_tier": "needs_review", "reviewer": "validator"},
                {"concept_id": "c2", "alias": "错误", "lang": "zh", "decision": "needs_review", "review_tier": "needs_review", "reviewer": "validator"},
                {"concept_id": "c3", "alias": "歧义", "lang": "zh", "decision": "needs_review", "review_tier": "needs_review", "reviewer": "validator"},
                {"concept_id": "c4", "alias": "新词", "lang": "zh", "decision": "needs_review", "review_tier": "needs_review", "reviewer": "validator"},
                {"concept_id": "e1", "alias": "english", "lang": "en", "decision": "accept", "review_tier": "auto_accept"},
            ],
        )

        module = load_module()
        summary = module.preserve_zh_review_decisions(prior_path=prior, current_path=current)

        rows = {(row["concept_id"], row["alias"]): row for row in read_jsonl(current)}
        self.assertEqual(rows[("c1", "信道估计")]["decision"], "accept")
        self.assertEqual(rows[("c2", "错误")]["decision"], "reject")
        self.assertEqual(rows[("c3", "歧义")]["decision"], "blocked")
        self.assertEqual(rows[("c4", "新词")]["decision"], "needs_review")
        self.assertEqual(summary["preserved"], 3)

    def test_preserves_prior_reviewed_target_when_validator_regenerates_collision_block(self) -> None:
        prior = self.root / "prior.jsonl"
        current = self.root / "current.jsonl"
        write_jsonl(
            prior,
            [
                {
                    "concept_id": "c1",
                    "alias": "人工神经网络",
                    "lang": "zh",
                    "decision": "accept",
                    "review_tier": "review_accept",
                    "reviewer": "subagent-recommended+main-agent-accepted",
                    "reason": "explicit target selected",
                }
            ],
        )
        write_jsonl(
            current,
            [
                {
                    "concept_id": "c1",
                    "alias": "人工神经网络",
                    "lang": "zh",
                    "decision": "blocked",
                    "review_tier": "review_blocked",
                    "reviewer": "validator",
                    "reason": "alias collision blocked until duplicate concept merge or explicit runtime target is resolved",
                },
                {
                    "concept_id": "c2",
                    "alias": "人工神经网络",
                    "lang": "zh",
                    "decision": "blocked",
                    "review_tier": "review_blocked",
                    "reviewer": "validator",
                    "reason": "alias collision blocked until duplicate concept merge or explicit runtime target is resolved",
                },
            ],
        )

        module = load_module()
        summary = module.preserve_zh_review_decisions(prior_path=prior, current_path=current)

        rows = {(row["concept_id"], row["alias"]): row for row in read_jsonl(current)}
        self.assertEqual(rows[("c1", "人工神经网络")]["decision"], "accept")
        self.assertEqual(rows[("c2", "人工神经网络")]["decision"], "blocked")
        self.assertEqual(summary["preserved"], 1)

    def test_does_not_preserve_prior_accept_over_hard_reject(self) -> None:
        prior = self.root / "prior.jsonl"
        current = self.root / "current.jsonl"
        write_jsonl(
            prior,
            [
                {
                    "concept_id": "c1",
                    "alias": "坏形态",
                    "lang": "zh",
                    "decision": "accept",
                    "review_tier": "review_accept",
                }
            ],
        )
        write_jsonl(
            current,
            [
                {
                    "concept_id": "c1",
                    "alias": "坏形态",
                    "lang": "zh",
                    "decision": "reject",
                    "review_tier": "shape_reject",
                    "reason": "alias shape rejected",
                }
            ],
        )

        module = load_module()
        summary = module.preserve_zh_review_decisions(prior_path=prior, current_path=current)

        rows = {(row["concept_id"], row["alias"]): row for row in read_jsonl(current)}
        self.assertEqual(rows[("c1", "坏形态")]["decision"], "reject")
        self.assertEqual(summary["preserved"], 0)


if __name__ == "__main__":
    unittest.main()

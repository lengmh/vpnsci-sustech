from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "block_accepted_alias_conflicts.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_module():
    spec = importlib.util.spec_from_file_location("block_accepted_alias_conflicts", SCRIPT_PATH)
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


class BlockAcceptedAliasConflictsTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_blocks_accepted_aliases_that_map_to_multiple_concepts(self) -> None:
        review = self.root / "review_decisions.jsonl"
        write_jsonl(
            review,
            [
                {"concept_id": "c1", "alias": "无线通信", "lang": "zh", "decision": "accept", "review_tier": "review_accept"},
                {"concept_id": "c2", "alias": "无线通信", "lang": "zh", "decision": "accept", "review_tier": "review_accept"},
                {"concept_id": "c1", "alias": "wireless communication", "lang": "en", "decision": "accept", "review_tier": "auto_accept"},
                {"concept_id": "c3", "alias": "信道估计", "lang": "zh", "decision": "accept", "review_tier": "review_accept"},
                {"concept_id": "c4", "alias": "待审", "lang": "zh", "decision": "needs_review", "review_tier": "needs_review"},
            ],
        )

        module = load_module()
        summary = module.block_accepted_alias_conflicts(review_decisions_path=review)

        rows = {(row["concept_id"], row["alias"], row["lang"]): row for row in read_jsonl(review)}
        self.assertEqual(rows[("c1", "无线通信", "zh")]["decision"], "blocked")
        self.assertEqual(rows[("c2", "无线通信", "zh")]["decision"], "blocked")
        self.assertEqual(rows[("c1", "无线通信", "zh")]["review_tier"], "review_blocked")
        self.assertEqual(rows[("c3", "信道估计", "zh")]["decision"], "accept")
        self.assertEqual(rows[("c4", "待审", "zh")]["decision"], "needs_review")
        self.assertEqual(summary["accepted_conflict_groups"], 1)
        self.assertEqual(summary["blocked"], 2)


if __name__ == "__main__":
    unittest.main()

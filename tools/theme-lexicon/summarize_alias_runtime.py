"""Summarize compact theme concept alias runtime artifacts.

Default path is manifest-first so host Agents can inspect current status
without opening the large legacy full overlay.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "vpnsci_sustech" / "data" / "theme_concept_alias_manifest.json"
DEFAULT_INDEX_PATH = REPO_ROOT / "vpnsci_sustech" / "data" / "theme_concept_alias_index.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def summarize_alias_runtime(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    index_path: Path = DEFAULT_INDEX_PATH,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    index_path = Path(index_path)
    if manifest_path.exists():
        payload = _load_json(manifest_path)
        payload = dict(payload)
        payload["source"] = "manifest"
        payload["manifest_path"] = str(manifest_path)
        return payload

    payload = _load_json(index_path)
    concepts = payload.get("concepts") or {}
    aliases = payload.get("aliases") or {}
    alias_counts = {"en": 0, "zh": 0}
    concepts_with_zh: set[str] = set()
    for alias_key, concept_id in aliases.items():
        if str(alias_key).startswith("en:"):
            alias_counts["en"] += 1
        elif str(alias_key).startswith("zh:"):
            alias_counts["zh"] += 1
            concepts_with_zh.add(str(concept_id))
    concept_count = len(concepts)
    return {
        "source": "index",
        "index_path": str(index_path),
        "schema_version": "theme_concept_alias_manifest_from_index.v1",
        "build_status": payload.get("build_status"),
        "concepts": concept_count,
        "concepts_with_zh_alias": len(concepts_with_zh),
        "concepts_with_zh_alias_percent": round(
            (len(concepts_with_zh) / concept_count * 100) if concept_count else 0.0,
            2,
        ),
        "aliases": alias_counts,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = summarize_alias_runtime(
        manifest_path=args.manifest_path,
        index_path=args.index_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

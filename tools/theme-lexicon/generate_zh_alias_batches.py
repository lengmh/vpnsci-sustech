"""Prepare full-coverage Chinese alias candidate batches for host-Agent review.

This script does not translate or activate aliases. It materializes one pending
candidate-generation row per English concept so a host Agent/SubAgent workflow
can fill ``zh_alias_candidates`` later without runtime side effects.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from math import ceil
from pathlib import Path
from typing import Any, Iterable


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def _candidate_record(concept: dict[str, Any], *, max_candidates: int) -> dict[str, Any]:
    aliases = concept.get("aliases") or {}
    canonical = concept.get("canonical") or {}
    return {
        "concept_id": str(concept.get("concept_id") or ""),
        "canonical_en": str(canonical.get("en") or ""),
        "aliases_en": [str(alias) for alias in (aliases.get("en") or []) if str(alias or "")],
        "domains": [str(domain) for domain in (concept.get("domains") or []) if str(domain or "")],
        "source_refs": [dict(ref) for ref in (concept.get("source_refs") or []) if isinstance(ref, dict)],
        "max_zh_alias_candidates": max_candidates,
        "candidate_generation_status": "pending_host_agent",
        "zh_alias_candidates": [],
    }


def generate_zh_alias_batches(
    concept_path: Path,
    output_dir: Path,
    *,
    batch_size: int = 200,
    max_candidates: int = 3,
) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if max_candidates < 0:
        raise ValueError("max_candidates must not be negative")
    concepts = sorted(
        _read_jsonl(Path(concept_path)),
        key=lambda concept: (str(concept.get("concept_id") or ""), str((concept.get("canonical") or {}).get("en") or "")),
    )
    rows = [_candidate_record(concept, max_candidates=max_candidates) for concept in concepts]
    output_dir = Path(output_dir)
    outputs = []
    total_batches = ceil(len(rows) / batch_size) if rows else 0
    for batch_index in range(total_batches):
        start = batch_index * batch_size
        chunk = rows[start:start + batch_size]
        path = output_dir / f"zh_alias_candidates.batch-{batch_index + 1:03d}.jsonl"
        outputs.append({"output": str(path), "records": _write_jsonl(path, chunk)})
    manifest = {
        "schema_version": "theme_zh_alias_candidates.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "concept_input": str(Path(concept_path).resolve()),
        "output_dir": str(output_dir.resolve()),
        "concepts": len(rows),
        "batch_size": batch_size,
        "max_zh_alias_candidates": max_candidates,
        "candidate_generation_status": "pending_host_agent",
        "batches": outputs,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "zh_alias_candidate_manifest.json"
    manifest["manifest"] = str(manifest_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("concept_path", nargs="?", type=Path, default=Path("lexicons/builds/merged_en_concept_candidates.jsonl"))
    parser.add_argument("output_dir", nargs="?", type=Path, default=Path("lexicons/candidates"))
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--max-candidates", type=int, default=3)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = generate_zh_alias_batches(
        args.concept_path,
        args.output_dir,
        batch_size=args.batch_size,
        max_candidates=args.max_candidates,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

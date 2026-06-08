"""Normalize local theme lexicon source dumps into one JSONL schema.

This script is an offline maintenance tool. It reads gitignored source dumps
under ``lexicons/sources`` and writes gitignored normalized JSONL outputs under
``lexicons/normalized``. Runtime report generation must not import this module
or read its intermediate outputs.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import zipfile


DEFAULT_SOURCES = (
    "arxiv",
    "openalex_topics",
    "ieee_taxonomy",
    "physh",
    "cso",
    "mesh",
)

OUTPUT_FILENAMES = {
    "arxiv": "arxiv_terms.jsonl",
    "openalex_topics": "openalex_topics_terms.jsonl",
    "ieee_taxonomy": "ieee_taxonomy_terms.jsonl",
    "physh": "physh_terms.jsonl",
    "cso": "cso_terms.jsonl",
    "mesh": "mesh_terms.jsonl",
}

ARXIV_DOMAINS = {
    "astro-ph": "physics_astronomy",
    "cond-mat": "physics_condensed_matter",
    "cs": "computer_science",
    "econ": "economics",
    "eess": "electrical_engineering",
    "gr-qc": "physics_general_relativity",
    "hep-ex": "physics_high_energy",
    "hep-lat": "physics_high_energy",
    "hep-ph": "physics_high_energy",
    "hep-th": "physics_high_energy",
    "math": "mathematics",
    "math-ph": "mathematical_physics",
    "nlin": "nonlinear_sciences",
    "nucl-ex": "nuclear_physics",
    "nucl-th": "nuclear_physics",
    "physics": "physics",
    "q-bio": "quantitative_biology",
    "q-fin": "quantitative_finance",
    "quant-ph": "quantum_physics",
    "stat": "statistics",
}

MESH_ROOTS = {
    "A": "Anatomy",
    "B": "Organisms",
    "C": "Diseases",
    "D": "Chemicals and Drugs",
    "E": "Analytical, Diagnostic and Therapeutic Techniques and Equipment",
    "F": "Psychiatry and Psychology",
    "G": "Phenomena and Processes",
    "H": "Disciplines and Occupations",
    "I": "Anthropology, Education, Sociology and Social Phenomena",
    "J": "Technology, Industry, and Agriculture",
    "K": "Humanities",
    "L": "Information Science",
    "M": "Named Groups",
    "N": "Health Care",
    "V": "Publication Characteristics",
    "Y": "Qualifiers",
    "Z": "Geographicals",
}


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _slug(value: str) -> str:
    value = unquote(_clean_text(value)).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "unknown"


def _uri_tail(uri: str) -> str:
    text = _clean_text(uri).strip("<>")
    tail = text.rstrip("/").rsplit("/", 1)[-1]
    return unquote(tail)


def _label_from_uri(uri: str) -> str:
    tail = _uri_tail(uri)
    return _clean_text(tail.replace("_", " ").replace("-", " "))


def _unique_text(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _source_id(source: str, raw_id: str) -> str:
    raw_id = _clean_text(raw_id)
    return f"{source}:{raw_id}" if raw_id else f"{source}:unknown"


def _record(
    *,
    source: str,
    source_id: str,
    label: str,
    aliases: Iterable[Any] = (),
    path: Iterable[Any] = (),
    parent: str | None = None,
    root: str | None = None,
    domains: Iterable[Any] = (),
    source_confidence: str = "medium",
    license_note: str = "local gitignored source cache",
) -> dict[str, Any] | None:
    label = _clean_text(label)
    if not label:
        return None
    clean_path = _unique_text(path)
    if not clean_path:
        clean_path = [label]
    clean_aliases = [
        alias
        for alias in _unique_text(aliases)
        if alias.casefold() != label.casefold()
    ]
    clean_domains = [_slug(domain) for domain in _unique_text(domains)]
    return {
        "source": source,
        "source_id": source_id,
        "label": label,
        "lang": "en",
        "aliases": clean_aliases,
        "path": clean_path,
        "parent": _clean_text(parent) or None,
        "root": _clean_text(root) or clean_path[0],
        "domains": clean_domains,
        "source_confidence": source_confidence,
        "license_note": license_note,
    }


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_arxiv(source_root: Path) -> Iterator[dict[str, Any]]:
    source = "arxiv"
    for item in _load_json(source_root / source / "categories.json"):
        code = _clean_text(item.get("code"))
        label = _clean_text(item.get("label"))
        prefix = code.split(".", 1)[0] if "." in code else code
        domain = ARXIV_DOMAINS.get(prefix, prefix)
        rec = _record(
            source=source,
            source_id=_source_id(source, code),
            label=label,
            aliases=[code],
            path=[domain, label],
            parent=domain,
            root=domain,
            domains=[domain],
            source_confidence="medium",
        )
        if rec:
            yield rec


def normalize_openalex_topics(source_root: Path) -> Iterator[dict[str, Any]]:
    source = "openalex_topics"
    for item in _load_json(source_root / source / "topics.json"):
        label = _clean_text(item.get("display_name"))
        topic_id = _uri_tail(item.get("id", "")) or _slug(label)
        domain = _clean_text((item.get("domain") or {}).get("display_name"))
        field = _clean_text((item.get("field") or {}).get("display_name"))
        subfield = _clean_text((item.get("subfield") or {}).get("display_name"))
        path = [value for value in (domain, field, subfield, label) if value]
        aliases = item.get("keywords") or []
        rec = _record(
            source=source,
            source_id=_source_id(source, topic_id),
            label=label,
            aliases=aliases,
            path=path,
            parent=subfield or field or domain or None,
            root=domain or field or label,
            domains=[domain, field],
            source_confidence="high",
        )
        if rec:
            yield rec


def normalize_ieee_taxonomy(source_root: Path) -> Iterator[dict[str, Any]]:
    source = "ieee_taxonomy"
    path = source_root / source / "taxonomy_terms.jsonl"
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            label = _clean_text(item.get("term"))
            term_path = item.get("path") or [label]
            root = _clean_text(item.get("root")) or (term_path[0] if term_path else label)
            rec = _record(
                source=source,
                source_id=_source_id(source, _slug(" / ".join(term_path))),
                label=label,
                aliases=[],
                path=term_path,
                parent=item.get("parent"),
                root=root,
                domains=[root],
                source_confidence="high",
            )
            if rec:
                yield rec


def normalize_physh(source_root: Path) -> Iterator[dict[str, Any]]:
    source = "physh"
    for item in _load_json(source_root / source / "concepts.json"):
        if item.get("exclude_from_indexing") is True:
            continue
        label = _clean_text(item.get("label"))
        raw_id = _clean_text(item.get("id")) or _uri_tail(item.get("@id", "")) or _slug(label)
        rec = _record(
            source=source,
            source_id=_source_id(source, raw_id),
            label=label,
            aliases=item.get("altLabel") or [],
            path=["Physics", label],
            parent="Physics",
            root="Physics",
            domains=["physics"],
            source_confidence="high",
        )
        if rec:
            yield rec


def _read_cso_edges(zip_path: Path) -> tuple[set[str], dict[str, set[str]], dict[str, set[str]]]:
    topics: set[str] = set()
    parents: dict[str, set[str]] = {}
    aliases: dict[str, set[str]] = {}
    with zipfile.ZipFile(zip_path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise FileNotFoundError(f"No CSV file found inside {zip_path}")
        with archive.open(csv_names[0]) as raw:
            text = (line.decode("utf-8", errors="replace") for line in raw)
            reader = csv.reader(text)
            for row in reader:
                if len(row) < 3:
                    continue
                subj, pred, obj = (_clean_text(part).strip("<>") for part in row[:3])
                pred_tail = pred.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
                if not subj or not obj:
                    continue
                topics.add(subj)
                topics.add(obj)
                if pred_tail == "superTopicOf":
                    parents.setdefault(obj, set()).add(subj)
                elif pred_tail in {"relatedEquivalent", "preferentialEquivalent"}:
                    aliases.setdefault(subj, set()).add(obj)
                    aliases.setdefault(obj, set()).add(subj)
    return topics, parents, aliases


def _cso_path(uri: str, parents: dict[str, set[str]]) -> list[str]:
    path = [_label_from_uri(uri)]
    seen = {uri}
    current = uri
    for _ in range(12):
        candidates = sorted(parents.get(current, set()))
        parent = next((candidate for candidate in candidates if candidate not in seen), "")
        if not parent:
            break
        path.insert(0, _label_from_uri(parent))
        seen.add(parent)
        current = parent
    return path


def normalize_cso(source_root: Path) -> Iterator[dict[str, Any]]:
    source = "cso"
    topics, parents, aliases = _read_cso_edges(source_root / source / "CSO.3.5.csv.zip")
    for uri in sorted(topics):
        label = _label_from_uri(uri)
        term_path = _cso_path(uri, parents)
        parent_uri = sorted(parents.get(uri, set()))[0] if parents.get(uri) else ""
        rec = _record(
            source=source,
            source_id=_source_id(source, _slug(_uri_tail(uri))),
            label=label,
            aliases=[_label_from_uri(alias) for alias in sorted(aliases.get(uri, set()))],
            path=term_path,
            parent=_label_from_uri(parent_uri) if parent_uri else None,
            root=term_path[0] if term_path else "Computer Science",
            domains=["computer_science"],
            source_confidence="high",
        )
        if rec:
            yield rec


def _mesh_root_from_tree_numbers(tree_numbers: list[str], fallback: str) -> str:
    if not tree_numbers:
        return fallback
    key = tree_numbers[0][:1]
    return MESH_ROOTS.get(key, fallback)


def _mesh_terms(record: ET.Element) -> list[str]:
    return [
        node.text or ""
        for node in record.findall(".//TermList/Term/String")
    ]


def _mesh_record(
    *,
    source_id_prefix: str,
    record: ET.Element,
    ui_tag: str,
    name_path: str,
    fallback_root: str,
) -> dict[str, Any] | None:
    ui = _clean_text(record.findtext(ui_tag))
    label = _clean_text(record.findtext(name_path))
    tree_numbers = [
        _clean_text(node.text)
        for node in record.findall("./TreeNumberList/TreeNumber")
        if _clean_text(node.text)
    ]
    root = _mesh_root_from_tree_numbers(tree_numbers, fallback_root)
    return _record(
        source="mesh",
        source_id=_source_id("mesh", f"{source_id_prefix}:{ui or _slug(label)}"),
        label=label,
        aliases=_mesh_terms(record),
        path=[root, label],
        parent=root,
        root=root,
        domains=["biomedical", root],
        source_confidence="high",
    )


def normalize_mesh(source_root: Path) -> Iterator[dict[str, Any]]:
    source_dir = source_root / "mesh"

    for _event, elem in ET.iterparse(source_dir / "desc2026.xml", events=("end",)):
        if elem.tag != "DescriptorRecord":
            continue
        rec = _mesh_record(
            source_id_prefix="descriptor",
            record=elem,
            ui_tag="./DescriptorUI",
            name_path="./DescriptorName/String",
            fallback_root="MeSH Descriptor",
        )
        if rec:
            yield rec
        elem.clear()

    for _event, elem in ET.iterparse(source_dir / "qual2026.xml", events=("end",)):
        if elem.tag != "QualifierRecord":
            continue
        rec = _mesh_record(
            source_id_prefix="qualifier",
            record=elem,
            ui_tag="./QualifierUI",
            name_path="./QualifierName/String",
            fallback_root="Qualifiers",
        )
        if rec:
            yield rec
        elem.clear()


NORMALIZERS = {
    "arxiv": normalize_arxiv,
    "openalex_topics": normalize_openalex_topics,
    "ieee_taxonomy": normalize_ieee_taxonomy,
    "physh": normalize_physh,
    "cso": normalize_cso,
    "mesh": normalize_mesh,
}


def write_jsonl(records: Iterable[dict[str, Any]], output_path: Path, *, limit: int | None = None) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
            if limit is not None and count >= limit:
                break
    return count


def normalize_sources(
    *,
    source_root: Path,
    output_dir: Path,
    sources: Iterable[str] = DEFAULT_SOURCES,
    limit_per_source: int | None = None,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    output_dir = output_dir.resolve()
    summary: dict[str, Any] = {
        "schema_version": "theme_source_normalization.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root),
        "output_dir": str(output_dir),
        "sources": {},
    }
    for source in sources:
        if source not in NORMALIZERS:
            raise ValueError(f"Unsupported source: {source}")
        output_path = output_dir / OUTPUT_FILENAMES[source]
        count = write_jsonl(
            NORMALIZERS[source](source_root),
            output_path,
            limit=limit_per_source,
        )
        summary["sources"][source] = {
            "output": str(output_path),
            "records": count,
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "source_parse_manifest.json"
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["manifest"] = str(manifest_path)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("lexicons/sources"))
    parser.add_argument("--output-dir", type=Path, default=Path("lexicons/normalized"))
    parser.add_argument("--sources", nargs="+", choices=DEFAULT_SOURCES, default=list(DEFAULT_SOURCES))
    parser.add_argument(
        "--limit-per-source",
        type=int,
        default=None,
        help="Optional smoke/debug cap. Omit for full deterministic normalization.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = normalize_sources(
        source_root=args.source_root,
        output_dir=args.output_dir,
        sources=args.sources,
        limit_per_source=args.limit_per_source,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

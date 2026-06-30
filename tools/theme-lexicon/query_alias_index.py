"""Query the compact theme concept alias runtime index.

This is a small host-Agent working-view helper.  It avoids opening the full
legacy alias overlay when checking one alias or one concept.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX_PATH = REPO_ROOT / "vpnsci_sustech" / "data" / "theme_concept_alias_index.json"


def _singular_alias_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith(("ches", "shes", "sses", "xes", "zes")):
        return token[:-2]
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def normalize_alias(value: str) -> str:
    text = (value or "").strip().casefold()
    if any("一" <= ch <= "鿿" for ch in text):
        text = re.sub(r"(?<=[一-鿿])(?=[A-Za-z0-9+#%,])", " ", text)
        text = re.sub(r"(?<=[A-Za-z0-9+#%,])(?=[一-鿿])", " ", text)
        text = text.replace("∞", " infinity ")
        text = text.replace("&", " and ")
        text = re.sub(r"[\-_/]+", " ", text)
        text = re.sub(r"[^\w\s一-鿿+#%,]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()
    text = text.replace("∞", " infinity ")
    text = text.replace("&", " and ")
    text = re.sub(r"[\-_/]+", " ", text)
    text = re.sub(r"[^a-z0-9+#\s]+", " ", text)
    return " ".join(_singular_alias_token(token) for token in text.split() if token)


def _is_chinese_text(value: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in value or "")


def _load_index(index_path: Path) -> dict[str, Any]:
    return json.loads(Path(index_path).read_text(encoding="utf-8"))


def _aliases_for_concept(payload: dict[str, Any], concept_id: str) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {"en": [], "zh": []}
    for alias_key, target_id in (payload.get("aliases") or {}).items():
        if str(target_id) != concept_id or ":" not in str(alias_key):
            continue
        lang, normalized = str(alias_key).split(":", 1)
        if lang in grouped:
            grouped[lang].append(normalized)
    return {lang: sorted(values) for lang, values in grouped.items() if values}


def query_alias_index(
    *,
    index_path: Path = DEFAULT_INDEX_PATH,
    alias: str | None = None,
    concept_id: str | None = None,
    lang: str | None = None,
) -> dict[str, Any]:
    payload = _load_index(Path(index_path))
    concepts = payload.get("concepts") or {}
    aliases = payload.get("aliases") or {}
    curation = payload.get("curation") or {}
    redirects = curation.get("redirects") or {}
    alias_redirect_sources = curation.get("alias_redirect_sources") or {}

    if alias:
        query_lang = (lang or ("zh" if _is_chinese_text(alias) else "en")).strip().lower()
        if query_lang not in {"en", "zh"}:
            raise ValueError("lang must be 'en' or 'zh'")
        alias_key = f"{query_lang}:{normalize_alias(alias)}"
        target_id = aliases.get(alias_key)
        concept = concepts.get(str(target_id)) if target_id else None
        return {
            "matched": bool(concept),
            "mode": "alias",
            "index_path": str(Path(index_path)),
            "alias": alias,
            "lang": query_lang,
            "alias_key": alias_key,
            "concept_id": target_id,
            "concept": concept,
            "redirect": alias_redirect_sources.get(alias_key),
        }

    if concept_id:
        concept = concepts.get(concept_id)
        redirected_to = redirects.get(concept_id)
        target_concept = concepts.get(str(redirected_to)) if redirected_to else None
        return {
            "matched": isinstance(concept, dict),
            "mode": "concept_id",
            "index_path": str(Path(index_path)),
            "concept_id": concept_id,
            "concept": concept,
            "redirected_to": redirected_to,
            "target_concept": target_concept,
            "aliases": _aliases_for_concept(payload, concept_id),
        }

    raise ValueError("Either alias or concept_id is required")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--alias", default=None)
    parser.add_argument("--concept-id", default=None)
    parser.add_argument("--lang", choices=("en", "zh"), default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = query_alias_index(
        index_path=args.index_path,
        alias=args.alias,
        concept_id=args.concept_id,
        lang=args.lang,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

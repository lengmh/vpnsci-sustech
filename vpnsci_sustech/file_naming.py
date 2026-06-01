"""Filename policy helpers for downloaded paper artifacts."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any

DEFAULT_POLICY = "identifier"
DEFAULT_TEMPLATE = "{title} - {first_author}"
DEFAULT_MAX_LENGTH = 180
DEFAULT_COLLISION = "hash"
POLICIES = {"identifier", "title_author", "title_year_author", "custom"}

_WINDOWS_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

_ARXIV_URL_PATTERN = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+/\d{7}(?:v\d+)?)",
    flags=re.I,
)


def sanitize_filename_component(text: Any, *, fallback: str = "unknown") -> str:
    """Return a cross-platform-safe filename component.

    Keeps Unicode text such as Chinese titles/authors, while removing Windows
    invalid characters and reserved basenames.
    """

    value = unicodedata.normalize("NFKC", str(text or "")).strip()
    value = _WINDOWS_INVALID_CHARS.sub("_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    if not value:
        value = fallback
    stem = value.split(".", 1)[0].upper()
    if stem in _RESERVED_NAMES:
        value = f"_{value}"
    return value


def identifier_stem(*, doi: str = "", url: str = "", title: str = "", cnki_id: str = "") -> str:
    """Build the legacy-compatible identifier stem."""

    if cnki_id:
        return sanitize_filename_component(cnki_id)

    if doi:
        return re.sub(r"[^\w\-.]", "_", doi)

    if url:
        arxiv_match = _ARXIV_URL_PATTERN.search(url)
        if arxiv_match:
            return f"arxiv_{arxiv_match.group(1).replace('/', '_')}"
        ieee_match = re.search(r"/document/(\d+)", url)
        if ieee_match:
            return f"ieee_{ieee_match.group(1)}"
        pii_match = re.search(r"/pii/([A-Z0-9]+)", url, flags=re.I)
        if pii_match:
            return f"pii_{pii_match.group(1)}"
        springer_match = re.search(r"/article/(10\.\d{4,9}/[^\s/?#]+)", url, flags=re.I)
        if springer_match:
            return re.sub(r"[^\w\-.]", "_", springer_match.group(1))

    if title:
        slug = re.sub(r"[^\w\-.]+", "_", title.strip()).strip("_")
        if slug:
            return slug[:120]

    return "unknown"


def has_strong_identifier(*, doi: str = "", url: str = "", cnki_id: str = "") -> bool:
    """Return whether identifier policy has a stable external identifier."""

    if doi or cnki_id:
        return True
    if not url:
        return False
    return any(
        pattern.search(url)
        for pattern in [
            _ARXIV_URL_PATTERN,
            re.compile(r"/document/\d+", flags=re.I),
            re.compile(r"/pii/[A-Z0-9]+", flags=re.I),
            re.compile(r"/article/10\.\d{4,9}/[^\s/?#]+", flags=re.I),
        ]
    )


def _short_hash(value: str) -> str:
    return hashlib.sha1((value or "unknown").encode("utf-8")).hexdigest()[:8]


def _truncate_with_hash(stem: str, max_length: int, hash_key: str) -> str:
    if max_length <= 0 or len(stem) <= max_length:
        return stem
    suffix = "_" + _short_hash(hash_key or stem)
    head_len = max(1, max_length - len(suffix))
    return stem[:head_len].rstrip(" ._") + suffix


def _has_filename_signal(value: str) -> bool:
    return bool(re.search(r"[^\W_]", value or "", flags=re.UNICODE))


def _metadata(paper: Any) -> dict[str, str]:
    authors = list(getattr(paper, "authors", None) or [])
    first_author = authors[0] if authors else ""
    authors_short = first_author
    if len(authors) > 1:
        authors_short = f"{first_author} et al."
    year = getattr(paper, "year", "") or ""
    doi = getattr(paper, "doi", "") or ""
    url = getattr(paper, "url", "") or ""
    title = getattr(paper, "title", "") or ""
    cnki_id = getattr(paper, "cnki_id", "") or ""
    identifier = identifier_stem(doi=doi, url=url, title=title, cnki_id=cnki_id)
    return {
        "title": str(title),
        "first_author": str(first_author),
        "authors_short": str(authors_short),
        "year": str(year),
        "journal": str(getattr(paper, "journal", "") or ""),
        "doi": str(doi),
        "source": str(getattr(paper, "source", "") or ""),
        "cnki_id": str(cnki_id),
        "identifier": str(identifier),
    }


def build_artifact_stem(
    paper: Any,
    *,
    policy: str = DEFAULT_POLICY,
    template: str = "",
    max_length: int = DEFAULT_MAX_LENGTH,
) -> str:
    """Build a filename stem from paper metadata and naming policy."""

    policy = (policy or DEFAULT_POLICY).strip().lower()
    if policy not in POLICIES:
        policy = DEFAULT_POLICY

    meta = _metadata(paper)
    if policy == "identifier":
        stem = meta["identifier"]
    else:
        if policy == "title_author":
            fmt = "{title} - {first_author}"
        elif policy == "title_year_author":
            fmt = "{title} ({year}) - {first_author}"
        else:
            fmt = template or DEFAULT_TEMPLATE
        try:
            stem = fmt.format_map(meta)
        except (KeyError, ValueError):
            stem = DEFAULT_TEMPLATE.format_map(meta)
        if not _has_filename_signal(stem):
            stem = meta["identifier"] or "unknown"
        stem = stem.replace("() -", "-")

    stem = sanitize_filename_component(stem, fallback=meta["identifier"] or "unknown")
    return _truncate_with_hash(stem, max_length, "|".join(meta.values()))


def reserve_unique_path(
    output_dir: str | Path,
    *,
    stem: str,
    ext: str,
    collision_key: str = "",
    collision: str = DEFAULT_COLLISION,
    overwrite: bool = False,
) -> Path:
    """Return an available artifact path without overwriting existing files."""

    output = Path(output_dir)
    clean_ext = (ext or "").lstrip(".") or "bin"
    clean_stem = sanitize_filename_component(stem)
    candidate = output / f"{clean_stem}.{clean_ext}"
    if overwrite:
        return candidate
    if not candidate.exists():
        return candidate

    if collision == "increment":
        index = 2
        while True:
            candidate = output / f"{clean_stem}__{index}.{clean_ext}"
            if not candidate.exists():
                return candidate
            index += 1

    suffix = _short_hash(collision_key or clean_stem)
    candidate = output / f"{clean_stem}_{suffix}.{clean_ext}"
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = output / f"{clean_stem}_{suffix}__{index}.{clean_ext}"
        if not candidate.exists():
            return candidate
        index += 1

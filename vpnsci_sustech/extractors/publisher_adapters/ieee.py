"""HTML extractor for IEEE Xplore article pages."""

import json
import re

from bs4 import BeautifulSoup


def can_handle(url: str) -> bool:
    return "ieeexplore.ieee.org" in url.lower()


def extract(html: str, url: str = "") -> dict:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    metadata = _extract_metadata_blob(html)
    return {
        "title": _extract_title(soup, metadata),
        "authors": _extract_authors(metadata),
        "abstract": _extract_abstract(soup, metadata),
        "full_text": _extract_body(soup, metadata),
        "figures": [],
        "references": [],
    }


def _extract_metadata_blob(html: str) -> dict:
    patterns = [
        r"xplGlobal\.document\.metadata\s*=\s*(\{.*?\})\s*(?:;|</script>)",
        r'"metadata":(\{.*?"abstract":"(?:[^"\\]|\\.)*".*?\})\s*,\s*"showGetAccess',
    ]
    for pat in patterns:
        m = re.search(pat, html, flags=re.S)
        if not m:
            continue
        raw = m.group(1)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            continue
    return {}


def _extract_title(soup: BeautifulSoup, metadata: dict) -> str:
    title = metadata.get("title", "").strip()
    if title:
        return title

    for selector in [
        "h1.document-title",
        "h1",
        "title",
    ]:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            if text:
                return text
    return ""


def _extract_authors(metadata: dict) -> list[str]:
    authors = []
    for item in metadata.get("authors", []) or []:
        name = (item or {}).get("name", "").strip()
        if name:
            authors.append(name)
    return authors


def _extract_abstract(soup: BeautifulSoup, metadata: dict) -> str:
    abstract = metadata.get("abstract", "").strip()
    if abstract:
        return _clean(abstract)

    text = soup.get_text("\n", strip=True)
    m = re.search(r"Abstract\s*:?\s*(.+?)(?:\n(?:Published in|DOI:|Date of Publication|Authors|Keywords)\b)", text, flags=re.S | re.I)
    if m:
        return _clean(m.group(1))
    return ""


def _extract_body(soup: BeautifulSoup, metadata: dict) -> str:
    # IEEE HTML often exposes abstract + metadata but not full article body.
    abstract = _extract_abstract(soup, metadata)
    if abstract:
        return abstract
    return ""


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

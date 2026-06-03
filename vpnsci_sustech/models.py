"""Data models for vpnsci."""

import json
from dataclasses import asdict, dataclass, field


@dataclass
class Artifact:
    """Represents a downloaded or generated paper artifact."""

    path: str = ""
    format: str = ""          # pdf/caj/cajx/nh/kdh
    kind: str = "fulltext"    # fulltext/generated_pdf/source_file
    source_url: str = ""
    text_extracted: bool = False
    note: str = ""


@dataclass
class Paper:
    """Represents a fetched academic paper."""

    doi: str = ""
    citation_count: int | None = None
    title: str = ""
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    year: int | None = None
    abstract: str = ""
    full_text: str = ""
    figures: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    source: str = ""  # "webvpn" | "open_access" | "arxiv"
    pdf_path: str = ""
    url: str = ""
    keywords: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    fund: str = ""
    classification: str = ""
    publication_info: str = ""
    online_first: bool | None = None
    citation_network: dict = field(default_factory=dict)
    cnki_id: str = ""
    dbcode: str = ""
    dbname: str = ""
    result_type: str = ""
    download_format: str = ""
    artifacts: list[Artifact] = field(default_factory=list)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self), indent=indent, ensure_ascii=False)

    def to_markdown(self, include_pdf_path: bool = False) -> str:
        """Render as Markdown for Claude consumption."""
        lines = []
        lines.append(f"# {self.title or 'Untitled'}")
        lines.append("")
        if self.authors:
            lines.append(f"**Authors:** {', '.join(self.authors)}")
        if self.journal:
            lines.append(f"**Journal:** {self.journal}")
        if self.year:
            lines.append(f"**Year:** {self.year}")
        if self.doi:
            lines.append(f"**DOI:** {self.doi}")
        if self.source:
            lines.append(f"**Source:** {self.source}")
        if include_pdf_path and self.pdf_path:
            lines.append(f"**PDF saved to:** {self.pdf_path}")
        lines.append("")

        if self.artifacts:
            lines.append("## Artifacts")
            lines.append("")
            for artifact in self.artifacts:
                label = artifact.format or "artifact"
                status = f"text_extracted={str(artifact.text_extracted).lower()}"
                line = f"- **{label}:** {artifact.path} ({status})"
                if artifact.kind:
                    line += f", kind={artifact.kind}"
                if artifact.source_url:
                    line += f", source={artifact.source_url}"
                if artifact.note:
                    line += f" — {artifact.note}"
                lines.append(line)
            lines.append("")

        if self.abstract:
            lines.append("## Abstract")
            lines.append("")
            lines.append(self.abstract)
            lines.append("")

        if self.full_text:
            lines.append("## Full Text")
            lines.append("")
            lines.append(self.full_text)
            lines.append("")

        if self.figures:
            lines.append("## Figures")
            lines.append("")
            for i, fig in enumerate(self.figures, 1):
                lines.append(f"**Figure {i}:** {fig}")
            lines.append("")

        if self.references:
            lines.append("## References")
            lines.append("")
            for ref in self.references:
                lines.append(f"- {ref}")
            lines.append("")

        return "\n".join(lines)

    def to_text(self) -> str:
        """Plain text output (minimal tokens for Claude)."""
        parts = []
        if self.title:
            parts.append(self.title)
            parts.append("")
        if self.abstract:
            parts.append(self.abstract)
            parts.append("")
        if self.full_text:
            parts.append(self.full_text)
        return "\n".join(parts)

    @classmethod
    def from_json(cls, data: str | dict) -> "Paper":
        """Deserialize from JSON string or dict."""
        if isinstance(data, str):
            data = json.loads(data)
        values = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        raw_artifacts = values.get("artifacts") or []
        artifacts: list[Artifact] = []
        for item in raw_artifacts:
            if isinstance(item, Artifact):
                artifacts.append(item)
            elif isinstance(item, dict):
                artifacts.append(Artifact(**{k: v for k, v in item.items() if k in Artifact.__dataclass_fields__}))
        values["artifacts"] = artifacts
        return cls(**values)

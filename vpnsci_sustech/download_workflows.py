"""Download workflow sidecar persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from .config import Config


@dataclass
class DownloadWorkflowItem:
    """Minimal downloadable item for report recovery."""

    hit_key: str
    title: str = ""
    authors: list[str] = field(default_factory=list)
    source: str = ""
    source_url: str = ""
    local_file: str = ""
    download_format: str = ""
    result_type: str = ""
    cnki_id: str = ""
    dbcode: str = ""
    dbname: str = ""


@dataclass
class DownloadWorkflowSidecar:
    """Sidecar saved after a download workflow completes."""

    workflow_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    runner: str = "agent"
    root_session_id: str = ""
    source_session_id: str = ""
    derived_session_id: str = ""
    original_query: str = ""
    display_query: str = ""
    recovered_label: str = ""
    actual_queries: list[dict] = field(default_factory=list)
    items: list[DownloadWorkflowItem] = field(default_factory=list)
    report_recovery_capability: str = "standard"
    missing_fields: list[str] = field(default_factory=list)
    insufficient_analysis_fields: list[str] = field(default_factory=list)


def _coerce_workflow_item(item: DownloadWorkflowItem | dict) -> DownloadWorkflowItem:
    if isinstance(item, DownloadWorkflowItem):
        return item
    values = {
        key: value
        for key, value in (item or {}).items()
        if key in DownloadWorkflowItem.__dataclass_fields__
    }
    return DownloadWorkflowItem(**values)


def _coerce_workflow_sidecar(data: DownloadWorkflowSidecar | dict) -> DownloadWorkflowSidecar:
    if isinstance(data, DownloadWorkflowSidecar):
        return DownloadWorkflowSidecar(
            workflow_id=data.workflow_id,
            created_at=data.created_at,
            runner=data.runner,
            root_session_id=data.root_session_id,
            source_session_id=data.source_session_id,
            derived_session_id=data.derived_session_id,
            original_query=data.original_query,
            display_query=data.display_query,
            recovered_label=data.recovered_label,
            actual_queries=list(data.actual_queries or []),
            items=[_coerce_workflow_item(item) for item in data.items],
            report_recovery_capability=data.report_recovery_capability,
            missing_fields=list(data.missing_fields or []),
            insufficient_analysis_fields=list(data.insufficient_analysis_fields or []),
        )
    values = {
        key: value
        for key, value in (data or {}).items()
        if key in DownloadWorkflowSidecar.__dataclass_fields__
    }
    values["items"] = [_coerce_workflow_item(item) for item in values.get("items", [])]
    return DownloadWorkflowSidecar(**values)


def new_workflow_id() -> str:
    return f"download-{uuid4().hex[:12]}"


def sidecar_directory(config: Config) -> Path:
    return Path(config.cache_dir) / "download-workflows"


def write_download_workflow_sidecar(sidecar: DownloadWorkflowSidecar, config: Config) -> Path:
    directory = sidecar_directory(config)
    directory.mkdir(parents=True, exist_ok=True)
    workflow_id = sidecar.workflow_id or new_workflow_id()
    payload = _coerce_workflow_sidecar(sidecar)
    payload.workflow_id = workflow_id
    path = directory / f"{workflow_id}.json"
    path.write_text(json.dumps(asdict(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_download_workflow_sidecar(path: str | Path) -> DownloadWorkflowSidecar:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return _coerce_workflow_sidecar(data)


def find_download_workflow_sidecars(
    config: Config,
    *,
    workflow_id: str = "",
    display_query: str = "",
) -> list[DownloadWorkflowSidecar]:
    directory = sidecar_directory(config)
    if not directory.exists():
        return []
    found: list[DownloadWorkflowSidecar] = []
    for path in sorted(directory.glob("*.json"), key=lambda p: p.name):
        sidecar = load_download_workflow_sidecar(path)
        if workflow_id and sidecar.workflow_id != workflow_id:
            continue
        if display_query and sidecar.display_query != display_query:
            continue
        found.append(sidecar)
    return found

"""Optional bridge to external paper-search-pro report workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import shlex
import subprocess

from .config import Config
from . import report_tools
from .sources.search_cache import load_session


class ReportBridgeError(RuntimeError):
    """Base report bridge error."""


class ReportBridgeConfigError(ReportBridgeError):
    """The bridge is not configured."""


class ReportBridgeExecutionError(ReportBridgeError):
    """The external report workflow failed."""


@dataclass
class ReportResult:
    report_path: str
    seed_session_id: str
    summary: str = ""
    expanded_sources: list[str] = field(default_factory=list)
    deduped_paper_count: int = 0
    failures: list[str] = field(default_factory=list)


def _output_dir(config: Config) -> Path:
    if config.paper_search_pro_output_dir:
        return Path(config.paper_search_pro_output_dir)
    return Path(config.cache_dir) / "search" / "reports"


def _validate_config(config: Config) -> tuple[Path, str, Path]:
    if not config.paper_search_pro_root:
        raise ReportBridgeConfigError("paper_search_pro_root is not configured")
    if not config.paper_search_pro_command:
        raise ReportBridgeConfigError("paper_search_pro_command is not configured")
    root = Path(config.paper_search_pro_root)
    if not root.exists():
        raise ReportBridgeConfigError(f"paper_search_pro_root does not exist: {root}")
    out_dir = _output_dir(config)
    out_dir.mkdir(parents=True, exist_ok=True)
    return root, config.paper_search_pro_command, out_dir


def _write_seed_package(session, out_dir: Path) -> Path:
    seed_path = out_dir / f"{session.session_id}-seed.json"
    seed_path.write_text(json.dumps(asdict(session), ensure_ascii=False, indent=2), encoding="utf-8")
    return seed_path


def _strip_outer_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _render_command(
    template: str,
    *,
    seed_json: Path,
    output_dir: Path,
    session_id: str,
    mode: str = "standard",
) -> list[str]:
    """Render a command template without hardcoding the upstream entrypoint.

    Placeholders are replaced after tokenization so paths containing spaces work
    whether the template author quoted placeholders or not.
    """

    replacements = {
        "__VPNSCI_SEED_JSON__": str(seed_json),
        "__VPNSCI_OUTPUT_DIR__": str(output_dir),
        "__VPNSCI_SESSION_ID__": session_id,
        "__VPNSCI_MODE__": mode,
    }
    rendered = (
        template.replace("{seed_json}", "__VPNSCI_SEED_JSON__")
        .replace("{output_dir}", "__VPNSCI_OUTPUT_DIR__")
        .replace("{session_id}", "__VPNSCI_SESSION_ID__")
        .replace("{mode}", "__VPNSCI_MODE__")
    )
    tokens = shlex.split(rendered, posix=False)
    command: list[str] = []
    for token in tokens:
        value = _strip_outer_quotes(token)
        for sentinel, replacement in replacements.items():
            value = value.replace(sentinel, replacement)
        command.append(value)
    return command


def generate_report_from_session(
    search_session_id: str,
    *,
    config: Config | None = None,
    mode: str = "standard",
) -> ReportResult:
    """Generate a report from a saved search session via configured command."""

    persist_autoconfig = config is None
    config = config or Config.load()
    if not config.paper_search_pro_root or not config.paper_search_pro_command:
        config = report_tools.ensure_report_tool_configured(config, force=False, persist=persist_autoconfig)
    root, command_template, out_dir = _validate_config(config)
    session = load_session(search_session_id, Path(config.cache_dir))
    seed_path = _write_seed_package(session, out_dir)
    command = _render_command(
        command_template,
        seed_json=seed_path,
        output_dir=out_dir,
        session_id=session.session_id,
        mode=mode,
    )

    completed = subprocess.run(
        command,
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if completed.returncode != 0:
        raise ReportBridgeExecutionError(
            f"paper-search-pro failed with code {completed.returncode}: {completed.stderr or completed.stdout}"
        )

    report_path = out_dir / "report.html"
    if not report_path.exists():
        raise ReportBridgeExecutionError(f"paper-search-pro did not produce expected report: {report_path}")

    return ReportResult(
        report_path=str(report_path),
        seed_session_id=session.session_id,
        summary=(completed.stdout or "").strip(),
        expanded_sources=list(session.source_summary.keys()),
        deduped_paper_count=len(session.hits),
        failures=[],
    )

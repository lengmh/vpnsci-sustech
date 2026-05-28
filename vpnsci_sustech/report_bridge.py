"""Optional bridge to external paper-search-pro report workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import shlex
import subprocess
import sys
from urllib.parse import quote

from .config import Config
from . import report_tools
from .sources.search_cache import load_session


class ReportBridgeError(RuntimeError):
    """Base report bridge error."""


class ReportBridgeConfigError(ReportBridgeError):
    """The bridge is not configured."""


class ReportBridgeExecutionError(ReportBridgeError):
    """The external report workflow failed."""


FULL_MODE_ALIASES = {"full", "pro", "professional", "paper-search-pro", "paper_search_pro"}
SEED_PREVIEW_ALIASES = {"seed", "seed_preview", "seed-preview", "preview", "standard", ""}


@dataclass
class ReportResult:
    report_path: str
    seed_session_id: str
    file_url: str = ""
    summary: str = ""
    expanded_sources: list[str] = field(default_factory=list)
    deduped_paper_count: int = 0
    failures: list[str] = field(default_factory=list)
    report_mode: str = "seed_preview"
    handoff_path: str = ""


@dataclass
class ReportJob:
    report_path: str
    seed_session_id: str
    status: str
    file_url: str = ""
    pid: int | None = None
    log_path: str = ""
    expanded_sources: list[str] = field(default_factory=list)
    deduped_paper_count: int = 0
    failures: list[str] = field(default_factory=list)
    report_mode: str = "seed_preview"
    handoff_path: str = ""


def normalize_report_mode(mode: str) -> str:
    normalized = (mode or "").strip().lower().replace(" ", "_")
    if normalized in FULL_MODE_ALIASES:
        return "full"
    if normalized in SEED_PREVIEW_ALIASES:
        return "seed_preview"
    raise ReportBridgeConfigError(f"Unsupported report mode: {mode}")


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


def create_full_workflow_handoff(
    session,
    output_dir: Path,
    *,
    mode: str,
    display_query: str = "",
    tool_root: Path | None = None,
) -> Path:
    """Create a handoff package for the upstream Agent/Skill workflow."""

    handoff_dir = output_dir / "full-workflow-handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    seed_path = handoff_dir / "seed.json"
    seed_path.write_text(json.dumps(asdict(session), ensure_ascii=False, indent=2), encoding="utf-8")
    query_context = {
        "report_mode": "full",
        "requested_mode": mode,
        "session_id": session.session_id,
        "user_query": display_query or session.query,
        "seed_session_query": session.query,
        "seed_count": len(session.hits),
        "source_summary": session.source_summary,
        "tool_root": str(tool_root) if tool_root else "",
        "required_workflow": [
            "OpenAlex / Semantic Scholar / CrossRef / PubMed / arXiv expansion",
            "query planning / source routing / synonym expansion",
            "LLM SubAgent relevance grading",
            "RCS / PRISMA / exports",
        ],
        "automation": {
            "runner": "codex-session",
            "requires_multi_agent": True,
            "subagent_tool": "multi_agent_v1.spawn_agent",
            "subagent_wait_tool": "multi_agent_v1.wait_agent",
            "subagent_failure_policy": "ask_user_before_degraded_execution",
            "fallback_allowed": "explicit_user_choice_only",
            "fallback_options": [
                {
                    "id": "seed_preview",
                    "label": "Run seed_preview HTML report",
                    "tradeoff": "Fast; no full source expansion or full PRISMA-S audit.",
                },
                {
                    "id": "main_agent_serial",
                    "label": "Continue full workflow with main Agent serial classification",
                    "tradeoff": "Closer to full workflow but slower and more context-intensive; disclose that SubAgents were not used.",
                },
                {
                    "id": "stop",
                    "label": "Stop and retry when SubAgents are available",
                    "tradeoff": "Preserves upstream parallel workflow semantics.",
                },
            ],
            "fallback_prompt_required": True,
            "handoff_status": "ready_for_codex_full_workflow",
        },
        "failure_reporting": {
            "report_channel": "current_conversation",
            "failure_codes": [
                "subagent_spawn_failed",
                "subagent_timeout",
                "subagent_result_invalid",
                "full_workflow_step_failed",
            ],
        },
    }
    (handoff_dir / "query_plan_context.json").write_text(
        json.dumps(query_context, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    instructions = "\n".join(
        [
            "# Full paper-search-pro workflow handoff",
            "",
            "This is not a completed HTML report.",
            "The configured bridge currently points at the seed-only renderer, so full mode did not silently downgrade.",
            "",
            f"- Search Session: `{session.session_id}`",
            f"- User Query: {display_query or session.query}",
            f"- Seed Session Query: {session.query}",
            f"- Seed Count: {len(session.hits)}",
            f"- Requested Mode: {mode}",
            f"- Local paper-search-pro root: {tool_root or ''}",
            f"- Seed JSON: `{seed_path}`",
            f"- Query Context: `{handoff_dir / 'query_plan_context.json'}`",
            "",
            "## Codex automation contract",
            "",
            "- Runner: Codex session, not the MCP Python process.",
            "- Required tool: `multi_agent_v1.spawn_agent` for parallel classifier SubAgents.",
            "- Wait tool: `multi_agent_v1.wait_agent`.",
            "- If SubAgents cannot start, time out, or return invalid output, report in the current conversation.",
            "- Failure codes: `subagent_spawn_failed`, `subagent_timeout`, `subagent_result_invalid`, `full_workflow_step_failed`.",
            "- Fallback: do not silently run seed_preview or serial classification.",
            "- If SubAgents are unavailable, ask the user to choose one option:",
            "  1. run `seed_preview` HTML report (fast, not full workflow);",
            "  2. continue with main-Agent serial classification (slower; disclose no SubAgents were used);",
            "  3. stop and retry when SubAgents are available.",
            "",
            "Run the upstream paper-search-pro Skill workflow with this seed package to perform full professional research.",
            "Required upstream capabilities: five-source expansion, query planning, source routing, SubAgent relevance grading, RCS/PRISMA/export generation.",
            "",
        ]
    )
    instructions_path = handoff_dir / "instructions.md"
    instructions_path.write_text(instructions, encoding="utf-8")
    return instructions_path


def _session_output_dir(base_out_dir: Path, session_id: str) -> Path:
    return base_out_dir / session_id


def path_to_file_url(path: str | Path) -> str:
    """Return a browser-friendly file:// URL for a local report path."""

    path_str = str(Path(path).absolute()).replace("\\", "/")
    if not path_str.startswith("/"):
        path_str = "/" + path_str
    return "file://" + quote(path_str, safe="/:")


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


def _normalize_background_command(command: list[str]) -> list[str]:
    if command and command[0].lower() in {"python", "python.exe"}:
        return [sys.executable, *command[1:]]
    return command


def _is_builtin_adapter_command(command: list[str]) -> bool:
    return any(
        part == "vpnsci_sustech.paper_search_pro_adapter"
        or part.replace("\\", "/").endswith("vpnsci_sustech/paper_search_pro_adapter.py")
        for part in command
    )


def _append_adapter_options(
    command: list[str],
    *,
    display_query: str = "",
    language: str = "",
    open_report: bool = False,
) -> list[str]:
    """Append options only understood by the bundled vpnsci adapter."""

    if not _is_builtin_adapter_command(command):
        return command
    extended = list(command)
    if display_query:
        extended.extend(["--display-query", display_query])
    if language:
        extended.extend(["--language", language])
    if open_report:
        extended.append("--open-report")
    return extended


def generate_report_from_session(
    search_session_id: str,
    *,
    config: Config | None = None,
    mode: str = "standard",
) -> ReportResult:
    """Generate a report from a saved search session via configured command."""

    normalized_mode = normalize_report_mode(mode)
    persist_autoconfig = config is None
    config = config or Config.load()
    if not config.paper_search_pro_root or not config.paper_search_pro_command:
        config = report_tools.ensure_report_tool_configured(config, force=False, persist=persist_autoconfig)
    root, command_template, out_dir = _validate_config(config)
    session = load_session(search_session_id, Path(config.cache_dir))
    session_out_dir = _session_output_dir(out_dir, session.session_id)
    session_out_dir.mkdir(parents=True, exist_ok=True)
    seed_path = _write_seed_package(session, session_out_dir)
    command = _render_command(
        command_template,
        seed_json=seed_path,
        output_dir=session_out_dir,
        session_id=session.session_id,
        mode=normalized_mode,
    )
    if normalized_mode == "full" and _is_builtin_adapter_command(command):
        handoff_path = create_full_workflow_handoff(
            session,
            session_out_dir,
            mode=normalized_mode,
            tool_root=root,
        )
        return ReportResult(
            report_path="",
            file_url="",
            seed_session_id=session.session_id,
            summary="Full paper-search-pro workflow requires upstream Skill/SubAgent execution; handoff package created.",
            expanded_sources=list(session.source_summary.keys()),
            deduped_paper_count=len(session.hits),
            failures=["full_workflow_handoff_required"],
            report_mode="full",
            handoff_path=str(handoff_path),
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

    report_path = session_out_dir / "report.html"
    if not report_path.exists():
        raise ReportBridgeExecutionError(f"paper-search-pro did not produce expected report: {report_path}")

    return ReportResult(
        report_path=str(report_path),
        file_url=path_to_file_url(report_path),
        seed_session_id=session.session_id,
        summary=(completed.stdout or "").strip(),
        expanded_sources=list(session.source_summary.keys()),
        deduped_paper_count=len(session.hits),
        failures=[],
        report_mode=normalized_mode,
    )


def start_report_from_session(
    search_session_id: str,
    *,
    config: Config | None = None,
    mode: str = "standard",
    display_query: str = "",
    language: str = "",
    open_report: bool = False,
) -> ReportJob:
    """Start report generation in the background and return expected paths."""

    normalized_mode = normalize_report_mode(mode)
    persist_autoconfig = config is None
    config = config or Config.load()
    if not config.paper_search_pro_root or not config.paper_search_pro_command:
        config = report_tools.ensure_report_tool_configured(config, force=False, persist=persist_autoconfig)
    root, command_template, out_dir = _validate_config(config)
    session = load_session(search_session_id, Path(config.cache_dir))
    session_out_dir = _session_output_dir(out_dir, session.session_id)
    session_out_dir.mkdir(parents=True, exist_ok=True)
    seed_path = _write_seed_package(session, session_out_dir)
    command = _render_command(
        command_template,
        seed_json=seed_path,
        output_dir=session_out_dir,
        session_id=session.session_id,
        mode=normalized_mode,
    )
    if normalized_mode == "full" and _is_builtin_adapter_command(command):
        handoff_path = create_full_workflow_handoff(
            session,
            session_out_dir,
            mode=normalized_mode,
            display_query=display_query,
            tool_root=root,
        )
        return ReportJob(
            report_path="",
            file_url="",
            seed_session_id=session.session_id,
            status="handoff_required",
            log_path="",
            expanded_sources=list(session.source_summary.keys()),
            deduped_paper_count=len(session.hits),
            failures=["full_workflow_handoff_required"],
            report_mode="full",
            handoff_path=str(handoff_path),
        )
    command = _append_adapter_options(
        command,
        display_query=display_query,
        language=language,
        open_report=open_report,
    )
    command = _normalize_background_command(command)

    log_path = session_out_dir / "report.log"
    report_path = session_out_dir / "report.html"
    log_file = log_path.open("w", encoding="utf-8")
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        process = subprocess.Popen(
            command,
            cwd=str(root),
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            close_fds=True,
            creationflags=creationflags,
        )
    finally:
        log_file.close()

    return ReportJob(
        report_path=str(report_path),
        file_url=path_to_file_url(report_path),
        seed_session_id=session.session_id,
        status="started",
        pid=process.pid,
        log_path=str(log_path),
        expanded_sources=list(session.source_summary.keys()),
        deduped_paper_count=len(session.hits),
        failures=[],
        report_mode=normalized_mode,
    )

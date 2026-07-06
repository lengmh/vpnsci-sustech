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
from .light_report_bridge import prepare_report
from .theme_candidate_resolution import (
    THEME_CANDIDATE_RESOLUTION_REQUEST_FILENAME,
    THEME_CANDIDATE_RESOLUTION_RESULT_FILENAME,
    apply_theme_candidate_resolution_result,
    build_theme_candidate_resolution_request,
)
from .theme_postprocess import (
    THEME_POSTPROCESS_REQUEST_FILENAME,
    THEME_POSTPROCESS_RESULT_FILENAME,
    apply_theme_postprocess_result,
    build_theme_postprocess_request,
)
from .sources.search_cache import load_session


class ReportBridgeError(RuntimeError):
    """Base report bridge error."""


class ReportBridgeConfigError(ReportBridgeError):
    """The bridge is not configured."""


class ReportBridgeExecutionError(ReportBridgeError):
    """The external report workflow failed."""


FULL_MODE_ALIASES = {"full", "pro", "professional", "paper-search-pro", "paper_search_pro"}
SEED_PREVIEW_ALIASES = {"seed", "seed_preview", "seed-preview", "preview", "standard", ""}
SEED_CLASSIFIED_ALIASES = {"seed_classified", "seed-classified", "classified_seed", "seed_rcs"}
RCS_EXECUTION_MODES = {"subagent_parallel", "main_agent_serial"}


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
    status: str = "completed"
    materialized_dir: str = ""
    theme_candidate_resolution_request_path: str = ""
    theme_candidate_resolution_result_path: str = ""
    theme_postprocess_request_path: str = ""
    theme_postprocess_result_path: str = ""
    rcs_classification_request_path: str = ""
    rcs_classification_result_path: str = ""
    user_query: str = ""
    language: str = ""


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
    materialized_dir: str = ""
    theme_candidate_resolution_request_path: str = ""
    theme_candidate_resolution_result_path: str = ""
    theme_postprocess_request_path: str = ""
    theme_postprocess_result_path: str = ""
    rcs_classification_request_path: str = ""
    rcs_classification_result_path: str = ""
    user_query: str = ""
    language: str = ""


def normalize_report_mode(mode: str) -> str:
    normalized = (mode or "").strip().lower().replace(" ", "_")
    if normalized in FULL_MODE_ALIASES:
        return "full"
    if normalized in SEED_PREVIEW_ALIASES:
        return "seed_preview"
    if normalized in SEED_CLASSIFIED_ALIASES:
        return "seed_classified"
    raise ReportBridgeConfigError(f"Unsupported report mode: {mode}")


def _output_dir(config: Config) -> Path:
    if config.paper_search_pro_output_dir:
        return Path(config.paper_search_pro_output_dir)
    return Path(config.cache_dir) / "search" / "reports"


def _validate_config(config: Config) -> tuple[Path, str, Path]:
    if not config.paper_search_pro_root:
        raise ReportBridgeConfigError("paper_search_pro_root is not configured")
    root = Path(config.paper_search_pro_root)
    if not root.exists():
        raise ReportBridgeConfigError(f"paper_search_pro_root does not exist: {root}")
    out_dir = _output_dir(config)
    out_dir.mkdir(parents=True, exist_ok=True)
    command_template = config.paper_search_pro_command or report_tools.default_report_command()
    return root, command_template, out_dir


def _write_seed_package(session, out_dir: Path) -> Path:
    seed_path = out_dir / f"{session.session_id}-seed.json"
    seed_path.write_text(json.dumps(asdict(session), ensure_ascii=False, indent=2), encoding="utf-8")
    return seed_path


CNKI_SEED_FIELDS = ["cnki_id", "source_url", "download_format", "local_file", "result_type"]


def _seed_source_label(session) -> str:
    summary = getattr(session, "source_summary", {}) or {}
    active = [source for source, count in summary.items() if count]
    if active == ["cnki"]:
        return "cnki"
    if active:
        return "mixed" if len(active) > 1 else active[0]
    hit_sources = {
        source
        for hit in getattr(session, "hits", [])
        for source in (getattr(hit, "sources", []) or [getattr(hit, "source", "") or getattr(hit, "backend", "")])
        if source
    }
    if hit_sources == {"cnki"}:
        return "cnki"
    if hit_sources:
        return "mixed" if len(hit_sources) > 1 else next(iter(hit_sources))
    return "seed"


def _cnki_field_status(session) -> dict:
    hits = getattr(session, "hits", []) or []
    cnki_hits = [
        hit for hit in hits
        if getattr(hit, "cnki_id", "")
        or getattr(hit, "source_url", "")
        or getattr(hit, "download_format", "")
        or getattr(hit, "local_file", "")
        or getattr(hit, "result_type", "")
        or "cnki" in (getattr(hit, "sources", []) or [])
        or getattr(hit, "source", "") == "cnki"
        or getattr(hit, "backend", "") == "cnki"
    ]
    return {
        "present": bool(cnki_hits),
        "hit_count": len(cnki_hits),
        "fields": CNKI_SEED_FIELDS,
        "preserved_counts": {
            field: sum(1 for hit in cnki_hits if getattr(hit, field, ""))
            for field in CNKI_SEED_FIELDS
        },
    }


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
        "seed_source": _seed_source_label(session),
        "cnki_fields": _cnki_field_status(session),
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
                    "tradeoff": "Fast; no full source expansion, formal RCS, or full PRISMA-S audit.",
                },
                {
                    "id": "seed_classified",
                    "label": "Run seed-only RCS classification report",
                    "tradeoff": "Classifies only the saved SearchSession seed set; no full source expansion or full PRISMA-S audit.",
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
            "- Fallback: do not silently run seed_preview, seed_classified, or serial classification.",
            "- If SubAgents are unavailable, ask the user to choose one option:",
            "  1. run `seed_preview` HTML report (fast, not full workflow, no formal RCS);",
            "  2. run `seed_classified` seed-only RCS report (not full workflow);",
            "  3. continue with main-Agent serial classification (same full scope, slower; disclose no SubAgents were used);",
            "  4. stop and retry when SubAgents are available.",
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
        or part == "vpnsci_sustech.light_report_bridge"
        or part.replace("\\", "/").endswith("vpnsci_sustech/paper_search_pro_adapter.py")
        or part.replace("\\", "/").endswith("vpnsci_sustech/light_report_bridge.py")
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


def _prepare_builtin_adapter_report(
    *,
    seed_path: Path,
    session_out_dir: Path,
    display_query: str = "",
    language: str = "",
    report_mode: str = "seed_preview",
    rcs_classification_result: object | None = None,
    rcs_execution_mode: str = "none",
) -> dict:
    if report_mode == "seed_classified" and rcs_classification_result is None:
        materialized_dir = session_out_dir / "materialized"
        result_path = materialized_dir / "rcs_classification_result.json"
        metadata = _read_json_if_exists(materialized_dir / "metadata.json")
        if result_path.exists() and isinstance(metadata, dict):
            existing_mode = str(metadata.get("rcs_execution_mode") or "")
            if existing_mode in RCS_EXECUTION_MODES:
                rcs_classification_result = _read_json_if_exists(result_path)
                rcs_execution_mode = existing_mode
    return prepare_report(
        seed_path,
        session_out_dir,
        display_query=display_query,
        language=language,
        report_mode=report_mode,
        rcs_classification_result=rcs_classification_result,
        rcs_execution_mode=rcs_execution_mode,
    )


def render_html_webartifacts(
    *,
    materialized_data_dir: Path,
    output_path: Path,
    user_query: str = "",
    language: str = "",
    tool_root: Path | None = None,
) -> Path:
    if tool_root:
        candidates = [tool_root]
        nested = tool_root / "tools" / "paper-search-pro"
        if nested.exists():
            candidates.append(nested)
        for candidate in candidates:
            if (candidate / "scripts").exists():
                sys.path.insert(0, str(candidate))
    from scripts.html_renderer_webartifacts import render_html_webartifacts as renderer

    return renderer(
        materialized_data_dir=materialized_data_dir,
        output_path=output_path,
        user_query=user_query,
        language=language or None,
    )


def _read_json_if_exists(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _detect_language_from_text(text: str) -> str:
    return "zh" if any("\u4e00" <= ch <= "\u9fff" for ch in text or "") else "en"


def _prepare_existing_full_materialized_theme_postprocess(
    *,
    session_out_dir: Path,
    display_query: str = "",
    language: str = "",
) -> dict | None:
    materialized_dir = session_out_dir / "materialized"
    chart_path = materialized_dir / "chart_data.json"
    paper_path = materialized_dir / "paper_list.json"
    metadata_path = materialized_dir / "metadata.json"
    report_data_path = materialized_dir / "report_data.json"
    if not chart_path.exists() or not paper_path.exists():
        return None

    chart_data = _read_json_if_exists(chart_path)
    papers = _read_json_if_exists(paper_path)
    metadata = _read_json_if_exists(metadata_path) or {}
    if not isinstance(chart_data, dict) or not isinstance(papers, list):
        return None

    raw_theme_treemap = chart_data.get("raw_theme_treemap") or chart_data.get("theme_treemap")
    request_payload, trace = build_theme_postprocess_request(
        raw_theme_treemap,
        papers,
        report_mode="full",
    )
    if not request_payload:
        return None

    request_path = materialized_dir / THEME_POSTPROCESS_REQUEST_FILENAME
    result_path = materialized_dir / THEME_POSTPROCESS_RESULT_FILENAME
    _write_json(request_path, request_payload)

    chart_data["theme_postprocess_request"] = request_payload
    chart_data["theme_postprocess"] = trace
    _write_json(chart_path, chart_data)

    report_data = _read_json_if_exists(report_data_path)
    if isinstance(report_data, dict):
        report_data["chart_data"] = chart_data
        _write_json(report_data_path, report_data)

    resolved_query = (
        display_query
        or str(metadata.get("display_query") or metadata.get("query") or "")
    )
    resolved_language = language or str(metadata.get("language") or "") or _detect_language_from_text(resolved_query)
    return {
        "report_path": str(session_out_dir / "report.html"),
        "materialized_dir": str(materialized_dir),
        "theme_postprocess_request_path": str(request_path),
        "theme_postprocess_result_path": str(result_path),
        "theme_postprocess_pending": not result_path.exists(),
        "user_query": resolved_query,
        "language": resolved_language,
    }


def _prepare_existing_full_materialized_theme_candidate_resolution(
    *,
    session_out_dir: Path,
    display_query: str = "",
    language: str = "",
) -> dict | None:
    materialized_dir = session_out_dir / "materialized"
    chart_path = materialized_dir / "chart_data.json"
    paper_path = materialized_dir / "paper_list.json"
    metadata_path = materialized_dir / "metadata.json"
    report_data_path = materialized_dir / "report_data.json"
    if not chart_path.exists() or not paper_path.exists():
        return None

    chart_data = _read_json_if_exists(chart_path)
    papers = _read_json_if_exists(paper_path)
    metadata = _read_json_if_exists(metadata_path) or {}
    if not isinstance(chart_data, dict) or not isinstance(papers, list):
        return None

    resolved_query = display_query or str(metadata.get("display_query") or metadata.get("query") or "")
    resolved_language = language or str(metadata.get("language") or "") or _detect_language_from_text(resolved_query)
    raw_theme_treemap = chart_data.get("raw_theme_treemap") or chart_data.get("theme_treemap")
    request_payload, trace = build_theme_candidate_resolution_request(
        raw_theme_treemap,
        papers,
        display_query=resolved_query,
        language=resolved_language,
    )
    if not request_payload:
        return None

    request_path = materialized_dir / THEME_CANDIDATE_RESOLUTION_REQUEST_FILENAME
    result_path = materialized_dir / THEME_CANDIDATE_RESOLUTION_RESULT_FILENAME
    _write_json(request_path, request_payload)

    chart_data["theme_candidate_resolution_request"] = request_payload
    if result_path.exists():
        result_payload = _read_json_if_exists(result_path)
        if isinstance(result_payload, dict):
            refined, trace = apply_theme_candidate_resolution_result(
                raw_theme_treemap,
                request_payload,
                result_payload,
                model_label="host-agent",
            )
            chart_data["theme_treemap"] = refined
    chart_data["theme_candidate_resolution"] = trace
    _write_json(chart_path, chart_data)

    report_data = _read_json_if_exists(report_data_path)
    if isinstance(report_data, dict):
        report_data["chart_data"] = chart_data
        _write_json(report_data_path, report_data)

    return {
        "report_path": str(session_out_dir / "report.html"),
        "materialized_dir": str(materialized_dir),
        "theme_candidate_resolution_request_path": str(request_path),
        "theme_candidate_resolution_result_path": str(result_path),
        "theme_candidate_resolution_pending": not result_path.exists(),
        "user_query": resolved_query,
        "language": resolved_language,
    }


def _apply_theme_candidate_resolution_to_existing_materialized(
    *,
    session_out_dir: Path,
    result_payload: dict,
    display_query: str = "",
    language: str = "",
    tool_root: Path,
    open_report: bool = False,
) -> dict:
    prepared = _prepare_existing_full_materialized_theme_candidate_resolution(
        session_out_dir=session_out_dir,
        display_query=display_query,
        language=language,
    )
    if not prepared:
        raise ReportBridgeConfigError("Theme candidate resolution apply requires an existing materialized report with candidate request.")

    materialized_dir = Path(prepared["materialized_dir"])
    chart_path = materialized_dir / "chart_data.json"
    report_data_path = materialized_dir / "report_data.json"
    chart_data = _read_json_if_exists(chart_path)
    report_data = _read_json_if_exists(report_data_path)
    if not isinstance(chart_data, dict):
        raise ReportBridgeExecutionError("chart_data.json is missing or invalid.")

    raw_theme_treemap = chart_data.get("raw_theme_treemap") or chart_data.get("theme_treemap")
    request_payload = chart_data.get("theme_candidate_resolution_request")
    refined, trace = apply_theme_candidate_resolution_result(
        raw_theme_treemap,
        request_payload,
        result_payload,
        model_label="host-agent",
    )
    result_path = Path(prepared["theme_candidate_resolution_result_path"])
    _write_json(result_path, result_payload)

    chart_data["theme_treemap"] = refined
    chart_data["theme_candidate_resolution"] = trace
    _write_json(chart_path, chart_data)

    if isinstance(report_data, dict):
        report_data["chart_data"] = chart_data
        _write_json(report_data_path, report_data)

    report_path = Path(prepared["report_path"])
    render_html_webartifacts(
        materialized_data_dir=materialized_dir,
        output_path=report_path,
        user_query=str(prepared["user_query"]),
        language=str(prepared["language"]),
        tool_root=tool_root,
    )
    if open_report:
        import webbrowser
        webbrowser.open(report_path.resolve().as_uri())

    prepared["status"] = "completed"
    return prepared


def _apply_theme_postprocess_to_existing_materialized(
    *,
    session_out_dir: Path,
    result_payload: dict,
    display_query: str = "",
    language: str = "",
    tool_root: Path,
    open_report: bool = False,
) -> dict:
    prepared = _prepare_existing_full_materialized_theme_postprocess(
        session_out_dir=session_out_dir,
        display_query=display_query,
        language=language,
    )
    if not prepared:
        raise ReportBridgeConfigError("Full theme postprocess apply requires an existing materialized full report.")

    materialized_dir = Path(prepared["materialized_dir"])
    chart_path = materialized_dir / "chart_data.json"
    report_data_path = materialized_dir / "report_data.json"
    chart_data = _read_json_if_exists(chart_path)
    report_data = _read_json_if_exists(report_data_path)
    if not isinstance(chart_data, dict):
        raise ReportBridgeExecutionError("chart_data.json is missing or invalid.")

    raw_theme_treemap = chart_data.get("raw_theme_treemap") or chart_data.get("theme_treemap")
    refined, trace = apply_theme_postprocess_result(
        raw_theme_treemap,
        result_payload,
        model_label="host-agent",
    )
    result_path = Path(prepared["theme_postprocess_result_path"])
    _write_json(result_path, result_payload)

    chart_data["theme_treemap"] = refined
    chart_data["theme_postprocess"] = trace
    _write_json(chart_path, chart_data)

    if isinstance(report_data, dict):
        report_data["chart_data"] = chart_data
        _write_json(report_data_path, report_data)

    report_path = Path(prepared["report_path"])
    render_html_webartifacts(
        materialized_data_dir=materialized_dir,
        output_path=report_path,
        user_query=str(prepared["user_query"]),
        language=str(prepared["language"]),
        tool_root=tool_root,
    )
    if open_report:
        import webbrowser
        webbrowser.open(report_path.resolve().as_uri())

    prepared["status"] = "completed"
    return prepared


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
    if not config.paper_search_pro_root:
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
    if normalized_mode == "seed_classified" and _is_builtin_adapter_command(command):
        prepared = _prepare_builtin_adapter_report(
            seed_path=seed_path,
            session_out_dir=session_out_dir,
            report_mode=normalized_mode,
        )
        if prepared.get("rcs_classification_pending"):
            return ReportResult(
                report_path=str(Path(prepared["report_path"])),
                file_url=path_to_file_url(prepared["report_path"]),
                seed_session_id=session.session_id,
                expanded_sources=list(session.source_summary.keys()),
                deduped_paper_count=len(session.hits),
                failures=["rcs_classification_pending"],
                report_mode=normalized_mode,
                status="rcs_classification_required",
                materialized_dir=str(prepared["materialized_dir"]),
                theme_postprocess_request_path=str(prepared["theme_postprocess_request_path"]),
                theme_postprocess_result_path=str(prepared["theme_postprocess_result_path"]),
                rcs_classification_request_path=str(prepared["rcs_classification_request_path"]),
                rcs_classification_result_path=str(prepared["rcs_classification_result_path"]),
                user_query=str(prepared["user_query"]),
                language=str(prepared["language"]),
            )
        if prepared.get("theme_candidate_resolution_pending"):
            return ReportResult(
                report_path=str(Path(prepared["report_path"])),
                file_url=path_to_file_url(prepared["report_path"]),
                seed_session_id=session.session_id,
                expanded_sources=list(session.source_summary.keys()),
                deduped_paper_count=len(session.hits),
                failures=["theme_candidate_resolution_pending"],
                report_mode=normalized_mode,
                status="theme_candidate_resolution_required",
                materialized_dir=str(prepared["materialized_dir"]),
                theme_candidate_resolution_request_path=str(prepared["theme_candidate_resolution_request_path"]),
                theme_candidate_resolution_result_path=str(prepared["theme_candidate_resolution_result_path"]),
                theme_postprocess_request_path=str(prepared["theme_postprocess_request_path"]),
                theme_postprocess_result_path=str(prepared["theme_postprocess_result_path"]),
                rcs_classification_request_path=str(prepared["rcs_classification_request_path"]),
                rcs_classification_result_path=str(prepared["rcs_classification_result_path"]),
                user_query=str(prepared["user_query"]),
                language=str(prepared["language"]),
            )
        if prepared.get("theme_postprocess_pending"):
            return ReportResult(
                report_path=str(Path(prepared["report_path"])),
                file_url=path_to_file_url(prepared["report_path"]),
                seed_session_id=session.session_id,
                expanded_sources=list(session.source_summary.keys()),
                deduped_paper_count=len(session.hits),
                failures=["theme_postprocess_pending"],
                report_mode=normalized_mode,
                status="theme_postprocess_required",
                materialized_dir=str(prepared["materialized_dir"]),
                theme_candidate_resolution_request_path=str(prepared.get("theme_candidate_resolution_request_path", "")),
                theme_candidate_resolution_result_path=str(prepared.get("theme_candidate_resolution_result_path", "")),
                theme_postprocess_request_path=str(prepared["theme_postprocess_request_path"]),
                theme_postprocess_result_path=str(prepared["theme_postprocess_result_path"]),
                rcs_classification_request_path=str(prepared["rcs_classification_request_path"]),
                rcs_classification_result_path=str(prepared["rcs_classification_result_path"]),
                user_query=str(prepared["user_query"]),
                language=str(prepared["language"]),
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
    if not config.paper_search_pro_root:
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
        prepared_candidate = _prepare_existing_full_materialized_theme_candidate_resolution(
            session_out_dir=session_out_dir,
            display_query=display_query,
            language=language,
        )
        if prepared_candidate and prepared_candidate.get("theme_candidate_resolution_pending"):
            return ReportJob(
                report_path=str(Path(prepared_candidate["report_path"])),
                file_url=path_to_file_url(prepared_candidate["report_path"]),
                seed_session_id=session.session_id,
                status="theme_candidate_resolution_required",
                log_path="",
                expanded_sources=list(session.source_summary.keys()),
                deduped_paper_count=len(session.hits),
                failures=["theme_candidate_resolution_pending"],
                report_mode="full",
                materialized_dir=str(prepared_candidate["materialized_dir"]),
                theme_candidate_resolution_request_path=str(prepared_candidate["theme_candidate_resolution_request_path"]),
                theme_candidate_resolution_result_path=str(prepared_candidate["theme_candidate_resolution_result_path"]),
                user_query=str(prepared_candidate["user_query"]),
                language=str(prepared_candidate["language"]),
            )
        prepared_full = _prepare_existing_full_materialized_theme_postprocess(
            session_out_dir=session_out_dir,
            display_query=display_query,
            language=language,
        )
        if prepared_full and prepared_full.get("theme_postprocess_pending"):
            return ReportJob(
                report_path=str(Path(prepared_full["report_path"])),
                file_url=path_to_file_url(prepared_full["report_path"]),
                seed_session_id=session.session_id,
                status="theme_postprocess_required",
                log_path="",
                expanded_sources=list(session.source_summary.keys()),
                deduped_paper_count=len(session.hits),
                failures=["theme_postprocess_pending"],
                report_mode="full",
                materialized_dir=str(prepared_full["materialized_dir"]),
                theme_candidate_resolution_request_path=str(prepared_candidate.get("theme_candidate_resolution_request_path", "") if prepared_candidate else ""),
                theme_candidate_resolution_result_path=str(prepared_candidate.get("theme_candidate_resolution_result_path", "") if prepared_candidate else ""),
                theme_postprocess_request_path=str(prepared_full["theme_postprocess_request_path"]),
                theme_postprocess_result_path=str(prepared_full["theme_postprocess_result_path"]),
                user_query=str(prepared_full["user_query"]),
                language=str(prepared_full["language"]),
            )
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
    if normalized_mode in {"seed_preview", "seed_classified"} and _is_builtin_adapter_command(command):
        prepared = _prepare_builtin_adapter_report(
            seed_path=seed_path,
            session_out_dir=session_out_dir,
            display_query=display_query,
            language=language,
            report_mode=normalized_mode,
        )
        if normalized_mode == "seed_classified" and prepared.get("rcs_classification_pending"):
            return ReportJob(
                report_path=str(Path(prepared["report_path"])),
                file_url=path_to_file_url(prepared["report_path"]),
                seed_session_id=session.session_id,
                status="rcs_classification_required",
                log_path="",
                expanded_sources=list(session.source_summary.keys()),
                deduped_paper_count=len(session.hits),
                failures=["rcs_classification_pending"],
                report_mode=normalized_mode,
                materialized_dir=str(prepared["materialized_dir"]),
                theme_postprocess_request_path=str(prepared["theme_postprocess_request_path"]),
                theme_postprocess_result_path=str(prepared["theme_postprocess_result_path"]),
                rcs_classification_request_path=str(prepared["rcs_classification_request_path"]),
                rcs_classification_result_path=str(prepared["rcs_classification_result_path"]),
                user_query=str(prepared["user_query"]),
                language=str(prepared["language"]),
            )
        if prepared.get("theme_candidate_resolution_pending"):
            return ReportJob(
                report_path=str(Path(prepared["report_path"])),
                file_url=path_to_file_url(prepared["report_path"]),
                seed_session_id=session.session_id,
                status="theme_candidate_resolution_required",
                log_path="",
                expanded_sources=list(session.source_summary.keys()),
                deduped_paper_count=len(session.hits),
                failures=["theme_candidate_resolution_pending"],
                report_mode=normalized_mode,
                materialized_dir=str(prepared["materialized_dir"]),
                theme_candidate_resolution_request_path=str(prepared["theme_candidate_resolution_request_path"]),
                theme_candidate_resolution_result_path=str(prepared["theme_candidate_resolution_result_path"]),
                theme_postprocess_request_path=str(prepared.get("theme_postprocess_request_path", "")),
                theme_postprocess_result_path=str(prepared.get("theme_postprocess_result_path", "")),
                rcs_classification_request_path=str(prepared.get("rcs_classification_request_path", "")),
                rcs_classification_result_path=str(prepared.get("rcs_classification_result_path", "")),
                user_query=str(prepared["user_query"]),
                language=str(prepared["language"]),
            )
        if prepared.get("theme_postprocess_pending"):
            return ReportJob(
                report_path=str(Path(prepared["report_path"])),
                file_url=path_to_file_url(prepared["report_path"]),
                seed_session_id=session.session_id,
                status="theme_postprocess_required",
                log_path="",
                expanded_sources=list(session.source_summary.keys()),
                deduped_paper_count=len(session.hits),
                failures=["theme_postprocess_pending"],
                report_mode=normalized_mode,
                materialized_dir=str(prepared["materialized_dir"]),
                theme_candidate_resolution_request_path=str(prepared.get("theme_candidate_resolution_request_path", "")),
                theme_candidate_resolution_result_path=str(prepared.get("theme_candidate_resolution_result_path", "")),
                theme_postprocess_request_path=str(prepared["theme_postprocess_request_path"]),
                theme_postprocess_result_path=str(prepared["theme_postprocess_result_path"]),
                rcs_classification_request_path=str(prepared.get("rcs_classification_request_path", "")),
                rcs_classification_result_path=str(prepared.get("rcs_classification_result_path", "")),
                user_query=str(prepared["user_query"]),
                language=str(prepared["language"]),
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


def apply_rcs_classification_and_render(
    search_session_id: str,
    *,
    result_payload: object,
    rcs_execution_mode: str,
    config: Config | None = None,
    display_query: str = "",
    language: str = "",
    open_report: bool = False,
) -> ReportResult:
    """Persist one host-Agent RCS classification result and render seed_classified HTML."""

    if rcs_execution_mode not in {"subagent_parallel", "main_agent_serial"}:
        raise ReportBridgeConfigError("rcs_execution_mode must be subagent_parallel or main_agent_serial.")

    persist_autoconfig = config is None
    config = config or Config.load()
    if not config.paper_search_pro_root:
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
        mode="seed_classified",
    )
    if not _is_builtin_adapter_command(command):
        raise ReportBridgeConfigError("RCS classification apply requires the built-in vpnsci adapter command.")

    prepared = _prepare_builtin_adapter_report(
        seed_path=seed_path,
        session_out_dir=session_out_dir,
        display_query=display_query,
        language=language,
        report_mode="seed_classified",
        rcs_classification_result=result_payload,
        rcs_execution_mode=rcs_execution_mode,
    )
    result_path = Path(prepared["rcs_classification_result_path"])
    _write_json(result_path, result_payload)

    report_path = Path(prepared["report_path"])
    render_html_webartifacts(
        materialized_data_dir=Path(prepared["materialized_dir"]),
        output_path=report_path,
        user_query=str(prepared["user_query"]),
        language=str(prepared["language"]),
        tool_root=root,
    )
    if open_report:
        import webbrowser
        webbrowser.open(report_path.resolve().as_uri())

    return ReportResult(
        report_path=str(report_path),
        file_url=path_to_file_url(report_path),
        seed_session_id=session.session_id,
        summary="",
        expanded_sources=list(session.source_summary.keys()),
        deduped_paper_count=len(session.hits),
        failures=[],
        report_mode="seed_classified",
        status="completed",
        materialized_dir=str(prepared["materialized_dir"]),
        theme_postprocess_request_path=str(prepared["theme_postprocess_request_path"]),
        theme_postprocess_result_path=str(prepared["theme_postprocess_result_path"]),
        rcs_classification_request_path=str(prepared["rcs_classification_request_path"]),
        rcs_classification_result_path=str(result_path),
        user_query=str(prepared["user_query"]),
        language=str(prepared["language"]),
    )


def apply_theme_postprocess_and_render(
    search_session_id: str,
    *,
    result_payload: dict,
    config: Config | None = None,
    mode: str = "seed_preview",
    display_query: str = "",
    language: str = "",
    open_report: bool = False,
) -> ReportResult:
    """Persist one host-Agent result payload and render the final report."""

    normalized_mode = normalize_report_mode(mode)

    persist_autoconfig = config is None
    config = config or Config.load()
    if not config.paper_search_pro_root:
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
    if not _is_builtin_adapter_command(command):
        raise ReportBridgeConfigError("Theme postprocess apply requires the built-in vpnsci adapter command.")

    if normalized_mode == "full":
        prepared = _apply_theme_postprocess_to_existing_materialized(
            session_out_dir=session_out_dir,
            result_payload=result_payload,
            display_query=display_query,
            language=language,
            tool_root=root,
            open_report=open_report,
        )
        report_path = Path(prepared["report_path"])
        return ReportResult(
            report_path=str(report_path),
            file_url=path_to_file_url(report_path),
            seed_session_id=session.session_id,
            summary="",
            expanded_sources=list(session.source_summary.keys()),
            deduped_paper_count=len(session.hits),
            failures=[],
            report_mode=normalized_mode,
            status="completed",
            materialized_dir=str(prepared["materialized_dir"]),
            theme_postprocess_request_path=str(prepared["theme_postprocess_request_path"]),
            theme_postprocess_result_path=str(prepared["theme_postprocess_result_path"]),
            user_query=str(prepared["user_query"]),
            language=str(prepared["language"]),
        )

    prepared = _prepare_builtin_adapter_report(
        seed_path=seed_path,
        session_out_dir=session_out_dir,
        display_query=display_query,
        language=language,
        report_mode=normalized_mode,
    )
    result_path = Path(prepared["theme_postprocess_result_path"])
    result_path.write_text(
        json.dumps(result_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    command = _append_adapter_options(
        command,
        display_query=display_query,
        language=language,
        open_report=open_report,
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
        status="completed",
        materialized_dir=str(prepared["materialized_dir"]),
        theme_postprocess_request_path=str(prepared["theme_postprocess_request_path"]),
        theme_postprocess_result_path=str(prepared["theme_postprocess_result_path"]),
        user_query=str(prepared["user_query"]),
        language=str(prepared["language"]),
    )


def apply_theme_candidate_resolution_and_render(
    search_session_id: str,
    *,
    result_payload: dict,
    config: Config | None = None,
    mode: str = "seed_preview",
    display_query: str = "",
    language: str = "",
    open_report: bool = False,
) -> ReportResult:
    """Persist one host-Agent ambiguous-candidate result and render the final report."""

    normalized_mode = normalize_report_mode(mode)
    persist_autoconfig = config is None
    config = config or Config.load()
    if not config.paper_search_pro_root:
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
    if not _is_builtin_adapter_command(command):
        raise ReportBridgeConfigError("Theme candidate resolution apply requires the built-in vpnsci adapter command.")

    if normalized_mode == "full":
        prepared = _apply_theme_candidate_resolution_to_existing_materialized(
            session_out_dir=session_out_dir,
            result_payload=result_payload,
            display_query=display_query,
            language=language,
            tool_root=root,
            open_report=open_report,
        )
        report_path = Path(prepared["report_path"])
    else:
        prepared = _prepare_builtin_adapter_report(
            seed_path=seed_path,
            session_out_dir=session_out_dir,
            display_query=display_query,
            language=language,
            report_mode=normalized_mode,
        )
        result_path = Path(prepared["theme_candidate_resolution_result_path"])
        _write_json(result_path, result_payload)
        prepared = _prepare_builtin_adapter_report(
            seed_path=seed_path,
            session_out_dir=session_out_dir,
            display_query=display_query,
            language=language,
            report_mode=normalized_mode,
        )
        report_path = Path(prepared["report_path"])
        render_html_webartifacts(
            materialized_data_dir=Path(prepared["materialized_dir"]),
            output_path=report_path,
            user_query=str(prepared["user_query"]),
            language=str(prepared["language"]),
            tool_root=root,
        )
        if open_report:
            import webbrowser
            webbrowser.open(report_path.resolve().as_uri())

    return ReportResult(
        report_path=str(report_path),
        file_url=path_to_file_url(report_path),
        seed_session_id=session.session_id,
        summary="",
        expanded_sources=list(session.source_summary.keys()),
        deduped_paper_count=len(session.hits),
        failures=[],
        report_mode=normalized_mode,
        status="completed",
        materialized_dir=str(prepared["materialized_dir"]),
        theme_candidate_resolution_request_path=str(prepared["theme_candidate_resolution_request_path"]),
        theme_candidate_resolution_result_path=str(prepared["theme_candidate_resolution_result_path"]),
        theme_postprocess_request_path=str(prepared.get("theme_postprocess_request_path", "")),
        theme_postprocess_result_path=str(prepared.get("theme_postprocess_result_path", "")),
        user_query=str(prepared["user_query"]),
        language=str(prepared["language"]),
    )

# Requirements — vpnsci-sustech and paper-search-pro handoff

This document separates the dependencies required by `vpnsci-sustech` itself from the optional dependencies required when an Agent continues the full upstream `paper-search-pro` workflow.

## Core `vpnsci-sustech`

The installable package dependencies are declared in `pyproject.toml`.

Core features covered there include:

- MCP server and CLI;
- OpenAlex / Semantic Scholar standard metadata search through `vpnsci_sustech` adapters;
- paper fetching and PDF processing;
- seed-preview HTML rendering through the bundled adapter when assets are present.

## Full `paper-search-pro` workflow

Full report mode is Agent/Codex-orchestrated. The MCP server creates a handoff package and does not install or run the entire upstream Skill workflow itself.

When an Agent continues the full workflow and invokes upstream helper scripts from `tools/paper-search-pro`, the upstream runtime may require these Python packages:

```text
pyalex>=0.21
semanticscholar>=0.10
biopython>=1.85
arxiv>=2.1
requests>=2.32
PyYAML>=6.0
Jinja2>=3.1
```

These are listed by the bundled upstream file:

```text
tools/paper-search-pro/scripts/requirements.txt
```

They are not automatically added to `vpnsci-sustech` core dependencies because full workflow execution belongs to the Agent/Codex layer and can be run in a separate environment.

## Recommended Agent check

Before running a full handoff, a capable Agent should verify:

```powershell
@'
import importlib.util
mods = ["pyalex", "semanticscholar", "Bio", "arxiv", "requests", "yaml", "jinja2"]
for m in mods:
    print(m, "OK" if importlib.util.find_spec(m) else "MISSING")
'@ | python -
```

Use an ASCII-only script body or a UTF-8 script file when running through shells with uncertain codepages.

## Missing dependency policy

If full-workflow dependencies are missing:

1. report the missing package list and failed step;
2. do not present `seed_preview` as a full report;
3. continue only if the requested tier can still be honestly satisfied through available adapters;
4. otherwise report `full_workflow_runner_unavailable`.

## Encoding requirement

All generated JSON, Markdown, and HTML artifacts must be UTF-8 without BOM.

For CJK queries, do not rely on shell command encoding. Load the query from UTF-8 JSON handoff files or pass it through a UTF-8 argument file.

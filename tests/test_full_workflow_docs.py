from pathlib import Path


def test_full_workflow_doc_describes_serial_fallback_as_full_workflow_execution():
    doc = Path("docs/agent-workflows/paper-search-pro-full-workflow.md").read_text(encoding="utf-8")

    assert "main-Agent serial classification" not in doc
    assert "main-Agent serial full-workflow execution" in doc
    assert "serial source expansion / retrieval" in doc

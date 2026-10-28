import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "theme-lexicon"


def load_audit():
    spec = importlib.util.spec_from_file_location(
        "curation_audit_paths", TOOLS / "audit_remaining_concepts_for_curation.py"
    )
    module = importlib.util.module_from_spec(spec)
    with mock.patch.object(sys, "path", [str(TOOLS), *sys.path]):
        spec.loader.exec_module(module)
    return module


def test_default_audit_output_uses_system_temp_and_preserves_explicit_override():
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch("tempfile.gettempdir", return_value=tmp):
            module = load_audit()
        assert module.parse_args([]).output_dir == Path(tmp) / "vpnsci-sustech" / "curation-audit"
        explicit = Path(tmp) / "审计 workspace"
        assert module.parse_args(["--output-dir", str(explicit)]).output_dir == explicit


def test_explicit_audit_output_keeps_filenames_schema_and_read_only_inputs():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        index = root / "index.json"
        index.write_text(json.dumps({
            "build_status": "review_complete",
            "concepts": {"concept:example": {
                "canonical": {"en": "Example", "zh": ""},
                "domains": [], "parents": [],
            }},
            "aliases": {},
        }), encoding="utf-8")
        review = root / "review.jsonl"
        review.write_text("", encoding="utf-8")
        inputs = (index.read_bytes(), review.read_bytes())
        output = root / "审计 workspace"
        module = load_audit()
        result = module.audit_remaining_concepts_for_curation(
            index_path=index, review_decisions_path=review, output_dir=output, stamp="fixture"
        )
        assert len(result["outputs"]) == 6
        for path in result["outputs"].values():
            path = Path(path)
            assert path.parent == output
            assert path.name.startswith("theme_alias_remaining_concept_curation_")
            assert path.name.endswith("_fixture.json")
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert payload["summary"]["schema_version"] == "theme_remaining_concept_curation_audit.v1"
        assert (index.read_bytes(), review.read_bytes()) == inputs

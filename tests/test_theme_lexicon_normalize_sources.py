from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "normalize_sources.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_module():
    spec = importlib.util.spec_from_file_location("normalize_sources", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class ThemeLexiconNormalizeSourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)
        self.sources = self.root / "sources"
        self.output = self.root / "normalized"
        self._write_fixture_sources()
        self.module = load_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_fixture_sources(self) -> None:
        write_json(
            self.sources / "arxiv" / "categories.json",
            [{"code": "cs.AI", "label": "Artificial Intelligence"}],
        )
        write_json(
            self.sources / "openalex_topics" / "topics.json",
            [
                {
                    "id": "https://openalex.org/T1",
                    "display_name": "Channel Estimation",
                    "keywords": ["CSI estimation", "wireless channels"],
                    "domain": {"display_name": "Physical Sciences"},
                    "field": {"display_name": "Engineering"},
                    "subfield": {"display_name": "Electrical Engineering"},
                }
            ],
        )
        ieee_dir = self.sources / "ieee_taxonomy"
        ieee_dir.mkdir(parents=True, exist_ok=True)
        (ieee_dir / "taxonomy_terms.jsonl").write_text(
            json.dumps(
                {
                    "term": "Wireless communication",
                    "path": ["Communications technology", "Wireless communication"],
                    "parent": "Communications technology",
                    "root": "Communications technology",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        write_json(
            self.sources / "physh" / "concepts.json",
            [
                {
                    "id": "phy-1",
                    "label": "Quantum information",
                    "altLabel": ["Quantum information science"],
                    "exclude_from_indexing": False,
                }
            ],
        )
        cso_dir = self.sources / "cso"
        cso_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(cso_dir / "CSO.3.5.csv.zip", "w") as archive:
            archive.writestr(
                "CSO.3.5.csv",
                "\n".join(
                    [
                        '"<https://cso.kmi.open.ac.uk/topics/computer_science>","<http://cso.kmi.open.ac.uk/schema/cso#superTopicOf>","<https://cso.kmi.open.ac.uk/topics/artificial_intelligence>"',
                        '"<https://cso.kmi.open.ac.uk/topics/artificial_intelligence>","<http://cso.kmi.open.ac.uk/schema/cso#relatedEquivalent>","<https://cso.kmi.open.ac.uk/topics/ai>"',
                        '"<https://cso.kmi.open.ac.uk/topics/artificial_intelligence>","<http://www.w3.org/2000/01/rdf-schema#label>","artificial intelligence@en ."',
                        '"<https://cso.kmi.open.ac.uk/topics/artificial_intelligence>","<http://www.w3.org/2002/07/owl#sameAs>","<http://rdf.freebase.com/ns/m.02y_3vt>"',
                        '"<https://cso.kmi.open.ac.uk/topics/force_sensing>","<http://schema.org/relatedLink>","<https://academic.microsoft.com/#/detail/101833716>"',
                    ]
                ),
            )
        mesh_dir = self.sources / "mesh"
        mesh_dir.mkdir(parents=True, exist_ok=True)
        (mesh_dir / "desc2026.xml").write_text(
            """<?xml version="1.0"?>
<DescriptorRecordSet>
  <DescriptorRecord>
    <DescriptorUI>D000001</DescriptorUI>
    <DescriptorName><String>Calcimycin</String></DescriptorName>
    <TreeNumberList><TreeNumber>D03.633</TreeNumber></TreeNumberList>
    <ConceptList><Concept><TermList><Term><String>A-23187</String></Term></TermList></Concept></ConceptList>
  </DescriptorRecord>
</DescriptorRecordSet>
""",
            encoding="utf-8",
        )
        (mesh_dir / "qual2026.xml").write_text(
            """<?xml version="1.0"?>
<QualifierRecordSet>
  <QualifierRecord>
    <QualifierUI>Q000001</QualifierUI>
    <QualifierName><String>adverse effects</String></QualifierName>
    <TreeNumberList><TreeNumber>Y02.010</TreeNumber></TreeNumberList>
    <ConceptList><Concept><TermList><Term><String>side effects</String></Term></TermList></Concept></ConceptList>
  </QualifierRecord>
</QualifierRecordSet>
""",
            encoding="utf-8",
        )

    def test_normalize_sources_writes_common_schema_for_each_source(self) -> None:
        summary = self.module.normalize_sources(
            source_root=self.sources,
            output_dir=self.output,
            sources=["arxiv", "openalex_topics", "ieee_taxonomy", "physh", "cso", "mesh"],
        )

        self.assertEqual(summary["sources"]["arxiv"]["records"], 1)
        self.assertEqual(summary["sources"]["mesh"]["records"], 2)
        self.assertTrue((self.output / "source_parse_manifest.json").exists())

        required = {
            "source",
            "source_id",
            "label",
            "lang",
            "aliases",
            "path",
            "parent",
            "root",
            "domains",
            "source_confidence",
            "license_note",
        }
        for output in self.output.glob("*_terms.jsonl"):
            for record in read_jsonl(output):
                self.assertEqual(set(record), required)
                self.assertEqual(record["lang"], "en")
                self.assertTrue(record["label"])
                self.assertTrue(record["source_id"].startswith(record["source"] + ":"))
                self.assertIsInstance(record["aliases"], list)
                self.assertIsInstance(record["path"], list)
                self.assertIsInstance(record["domains"], list)

    def test_source_specific_aliases_and_paths_are_preserved(self) -> None:
        self.module.normalize_sources(
            source_root=self.sources,
            output_dir=self.output,
            sources=["openalex_topics", "cso", "mesh"],
        )

        openalex = read_jsonl(self.output / "openalex_topics_terms.jsonl")[0]
        self.assertEqual(openalex["label"], "Channel Estimation")
        self.assertNotIn("CSI estimation", openalex["aliases"])
        self.assertEqual(
            openalex["path"],
            [
                "Physical Sciences",
                "Engineering",
                "Electrical Engineering",
                "Channel Estimation",
            ],
        )

        cso = {
            record["label"]: record
            for record in read_jsonl(self.output / "cso_terms.jsonl")
        }
        self.assertIn("ai", cso["artificial intelligence"]["aliases"])
        self.assertNotIn("m.02y 3vt", cso)
        self.assertNotIn("101833716", cso)
        self.assertNotIn("artificial intelligence@en .", cso)
        self.assertEqual(
            cso["artificial intelligence"]["path"],
            ["computer science", "artificial intelligence"],
        )

        mesh = {
            record["label"]: record
            for record in read_jsonl(self.output / "mesh_terms.jsonl")
        }
        self.assertIn("A-23187", mesh["Calcimycin"]["aliases"])
        self.assertIn("side effects", mesh["adverse effects"]["aliases"])


if __name__ == "__main__":
    unittest.main()

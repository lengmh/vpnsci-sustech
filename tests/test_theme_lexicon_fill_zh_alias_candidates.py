from __future__ import annotations

from functools import cache
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent, usable_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "fill_zh_alias_candidates.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


@cache
def load_module():
    spec = importlib.util.spec_from_file_location("fill_zh_alias_candidates", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_usable_temp_parent_rejects_existing_file_path() -> None:
    assert usable_temp_parent(Path(__file__)) is None


def test_select_temp_parent_falls_back_to_repo_tests_dir_when_primary_unusable() -> None:
    assert select_temp_parent(Path(__file__), REPO_ROOT / "tests") == REPO_ROOT / "tests"


class FillZhAliasCandidatesTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)
        self.candidates = self.root / "candidates"
        self.batch = self.candidates / "zh_alias_candidates.batch-001.jsonl"
        (self.candidates / "zh_alias_candidate_manifest.json").parent.mkdir(parents=True, exist_ok=True)
        (self.candidates / "zh_alias_candidate_manifest.json").write_text(
            json.dumps({"batches": [{"output": str(self.batch)}]}, ensure_ascii=False),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_fills_high_confidence_source_priority_aliases_without_overwriting_existing(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:channel_estimation",
                    "canonical_en": "Channel Estimation",
                    "aliases_en": ["channel estimation"],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "channel estimation"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:vehicle_routing_problem",
                    "canonical_en": "Vehicle Routing Problem",
                    "aliases_en": ["vehicle routing problem"],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Vehicle routing problem"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:existing",
                    "canonical_en": "Image Segmentation",
                    "aliases_en": ["image segmentation"],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "openalex_topics", "label": "Image Segmentation"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [{"alias": "既有别名", "source": "manual"}],
                },
                {
                    "concept_id": "concept:adaptive_routing",
                    "canonical_en": "Adaptive Routing",
                    "aliases_en": ["adaptive routing"],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "adaptive routing"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:mesh_only",
                    "canonical_en": "Vehicle Emissions",
                    "aliases_en": ["Vehicle Emissions"],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Vehicle Emissions"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:generic",
                    "canonical_en": "System",
                    "aliases_en": ["system"],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "system"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        summary = module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:channel_estimation"]["zh_alias_candidates"][0]["alias"], "信道估计")
        self.assertEqual(rows["concept:vehicle_routing_problem"]["zh_alias_candidates"][0]["alias"], "车辆路径问题")
        self.assertEqual(rows["concept:adaptive_routing"]["zh_alias_candidates"][0]["alias"], "自适应路由")
        self.assertEqual(rows["concept:existing"]["zh_alias_candidates"], [{"alias": "既有别名", "source": "manual"}])
        self.assertEqual(rows["concept:mesh_only"]["zh_alias_candidates"], [])
        self.assertEqual(rows["concept:generic"]["zh_alias_candidates"], [])
        self.assertEqual(summary["records_filled"], 3)

    def test_fills_conservative_non_priority_source_aliases_for_review(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:dna_repair",
                    "canonical_en": "DNA Repair",
                    "aliases_en": ["DNA Repair"],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "DNA Repair"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:adrenergic_beta_receptors",
                    "canonical_en": "Receptors, Adrenergic, beta",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Receptors, Adrenergic, beta"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:accelerator_physics",
                    "canonical_en": "Accelerator Physics",
                    "aliases_en": [],
                    "domains": ["physics"],
                    "source_refs": [{"source": "physh", "label": "Accelerator Physics"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:protein",
                    "canonical_en": "Protein",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Protein"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:adrenergic_fiber",
                    "canonical_en": "Adrenergic Fibers",
                    "aliases_en": ["Fiber, Adrenergic"],
                    "domains": ["biomedical", "anatomy"],
                    "source_refs": [{"source": "mesh", "label": "Adrenergic Fibers"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        summary = module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:dna_repair"]["zh_alias_candidates"][0]["alias"], "DNA修复")
        self.assertEqual(rows["concept:adrenergic_beta_receptors"]["zh_alias_candidates"][0]["alias"], "肾上腺素能β受体")
        self.assertEqual(rows["concept:accelerator_physics"]["zh_alias_candidates"][0]["alias"], "加速器物理")
# protein now has exact glossary entry 蛋白质
        protein_candidates = rows["concept:protein"]["zh_alias_candidates"]
        self.assertEqual(len(protein_candidates), 1)
        self.assertEqual(protein_candidates[0]["alias"], "蛋白质")
        self.assertEqual(protein_candidates[0]["source"], "agent_exact_glossary")
        self.assertEqual(rows["concept:adrenergic_fiber"]["zh_alias_candidates"], [])
# exact glossary added 1 extra record
        self.assertEqual(summary["records_filled"], 4)

    def test_can_replace_only_agent_generated_candidates(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:dna_repair",
                    "canonical_en": "DNA Repair",
                    "aliases_en": ["DNA Repair"],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "DNA Repair"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "conservative_generated",
                    "zh_alias_candidates": [{"alias": "旧生成值", "source": "agent_compositional_glossary"}],
                },
                {
                    "concept_id": "concept:manual",
                    "canonical_en": "DNA Repair",
                    "aliases_en": ["DNA Repair"],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "DNA Repair"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "manual",
                    "zh_alias_candidates": [{"alias": "人工值", "source": "manual"}],
                },
                {
                    "concept_id": "concept:still_pending",
                    "canonical_en": "Unmapped Term",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Unmapped Term"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:cleared",
                    "canonical_en": "Adrenergic Fibers",
                    "aliases_en": ["Fiber, Adrenergic"],
                    "domains": ["biomedical", "anatomy"],
                    "source_refs": [{"source": "mesh", "label": "Adrenergic Fibers"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "conservative_generated",
                    "zh_alias_candidates": [{"alias": "肾上腺素能光纤", "source": "agent_compositional_glossary"}],
                },
                {
                    "concept_id": "concept:empty_generated_status",
                    "canonical_en": "Adrenergic Fibers",
                    "aliases_en": [],
                    "domains": ["biomedical", "anatomy"],
                    "source_refs": [{"source": "mesh", "label": "Adrenergic Fibers"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "conservative_generated",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        summary = module.fill_zh_alias_candidates(candidate_dir=self.candidates, replace_generated=True)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:dna_repair"]["zh_alias_candidates"][0]["alias"], "DNA修复")
        self.assertEqual(rows["concept:manual"]["zh_alias_candidates"], [{"alias": "人工值", "source": "manual"}])
        self.assertEqual(rows["concept:still_pending"]["candidate_generation_status"], "pending_host_agent")
        self.assertEqual(rows["concept:cleared"]["zh_alias_candidates"], [])
        self.assertEqual(rows["concept:cleared"]["candidate_generation_status"], "pending_host_agent")
        self.assertEqual(rows["concept:empty_generated_status"]["candidate_generation_status"], "pending_host_agent")
        self.assertEqual(summary["records_replaced"], 3)

    def test_non_priority_sources_use_canonical_label_and_avoid_entry_term_word_salad(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:education_medical",
                    "canonical_en": "Education, Medical",
                    "aliases_en": ["Medical Education"],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Education, Medical"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:diagnosis_differential",
                    "canonical_en": "Diagnosis, Differential",
                    "aliases_en": ["Differential Diagnosis"],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Diagnosis, Differential"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:dysarthria",
                    "canonical_en": "Dysarthria",
                    "aliases_en": ["Scanning Speech", "Speechs, Scanning"],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Dysarthria"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:education_medical"]["zh_alias_candidates"][0]["alias"], "医学教育")
        self.assertNotIn("教育医学", json.dumps(rows["concept:education_medical"], ensure_ascii=False))
        self.assertEqual(rows["concept:diagnosis_differential"]["zh_alias_candidates"][0]["alias"], "鉴别诊断")
        self.assertEqual(rows["concept:dysarthria"]["zh_alias_candidates"], [])

    def test_priority_sources_can_use_single_component_and_relation_phrases_as_candidates(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:accelerometers",
                    "canonical_en": "Accelerometers",
                    "aliases_en": [],
                    "domains": ["instrumentation_and_measurement"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Accelerometers"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:power_system_control",
                    "canonical_en": "Control Of Power Systems",
                    "aliases_en": [],
                    "domains": ["power_engineering_and_energy"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Control Of Power Systems"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:protein",
                    "canonical_en": "Protein",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Protein"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:acoustic_sensors",
                    "canonical_en": "Acoustic Sensors",
                    "aliases_en": [],
                    "domains": ["sensors"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Acoustic Sensors"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:adaptive_beamforming",
                    "canonical_en": "Adaptive Beamforming",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Adaptive Beamforming"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:education",
                    "canonical_en": "Education",
                    "aliases_en": [],
                    "domains": ["education"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Education"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:synthetic_aperture_radar",
                    "canonical_en": "Synthetic Aperture Radar",
                    "aliases_en": [],
                    "domains": ["signal_processing"],
                    "source_refs": [{"source": "cso", "label": "Synthetic Aperture Radar"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:light_emitting_diode",
                    "canonical_en": "Light Emitting Diode",
                    "aliases_en": [],
                    "domains": ["components_packaging_and_manufacturing_technology"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Light Emitting Diode"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:remote_sensing",
                    "canonical_en": "Remote Sensing",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Remote Sensing"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:x_ray",
                    "canonical_en": "X Ray",
                    "aliases_en": [],
                    "domains": ["science_general"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "X Ray"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:mean_square_error",
                    "canonical_en": "Mean Square Error",
                    "aliases_en": [],
                    "domains": ["signal_processing"],
                    "source_refs": [{"source": "cso", "label": "Mean Square Error"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:ac_motor",
                    "canonical_en": "AC Motors",
                    "aliases_en": [],
                    "domains": ["industry_applications"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "AC Motors"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:action_potential",
                    "canonical_en": "Action Potentials",
                    "aliases_en": [],
                    "domains": ["engineering_in_medicine_and_biology"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Action Potentials"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:active_pixel_sensor",
                    "canonical_en": "Active Pixel Sensor",
                    "aliases_en": [],
                    "domains": ["imaging"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Active Pixel Sensor"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        summary = module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:accelerometers"]["zh_alias_candidates"][0]["alias"], "加速度计")
        self.assertEqual(rows["concept:power_system_control"]["zh_alias_candidates"][0]["alias"], "电力系统的控制")
# protein now has exact glossary entry 蛋白质
        protein_candidates = rows["concept:protein"]["zh_alias_candidates"]
        self.assertEqual(len(protein_candidates), 1)
        self.assertEqual(protein_candidates[0]["alias"], "蛋白质")
        self.assertEqual(protein_candidates[0]["source"], "agent_exact_glossary")
        self.assertEqual(rows["concept:acoustic_sensors"]["zh_alias_candidates"][0]["alias"], "声学传感器")
        self.assertEqual(rows["concept:adaptive_beamforming"]["zh_alias_candidates"][0]["alias"], "自适应波束成形")
        self.assertEqual(rows["concept:education"]["zh_alias_candidates"], [])
        self.assertEqual(rows["concept:synthetic_aperture_radar"]["zh_alias_candidates"][0]["alias"], "合成孔径雷达")
        self.assertEqual(rows["concept:light_emitting_diode"]["zh_alias_candidates"][0]["alias"], "发光二极管")
        self.assertEqual(rows["concept:remote_sensing"]["zh_alias_candidates"][0]["alias"], "遥感")
        self.assertEqual(rows["concept:x_ray"]["zh_alias_candidates"][0]["alias"], "X射线")
        self.assertEqual(rows["concept:mean_square_error"]["zh_alias_candidates"][0]["alias"], "均方误差")
        self.assertEqual(rows["concept:ac_motor"]["zh_alias_candidates"][0]["alias"], "AC电机")
        self.assertEqual(rows["concept:action_potential"]["zh_alias_candidates"][0]["alias"], "动作电位")
        self.assertEqual(rows["concept:active_pixel_sensor"]["zh_alias_candidates"][0]["alias"], "有源像素传感器")
        self.assertEqual(summary["records_filled"], 13)

    def test_priority_only_broad_components_and_relations_do_not_pollute_mesh(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:agent_based_framework",
                    "canonical_en": "Agent-based Framework",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Agent-based Framework"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:mesh_agent_based_framework",
                    "canonical_en": "Agent-based Framework",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Agent-based Framework"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:brca_gene_mutation",
                    "canonical_en": "BRCA Gene Mutation",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "openalex_topics", "label": "BRCA Gene Mutation"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:mimo_radar",
                    "canonical_en": "Multiple Input Multiple Output MIMO Radar",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Multiple Input Multiple Output MIMO Radar"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:shape_memory_alloy_actuator",
                    "canonical_en": "Shape Memory Alloy Actuator",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Shape Memory Alloy Actuator"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:attribute_based_encryption",
                    "canonical_en": "Attribute-based Encryption",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Attribute-based Encryption"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:applications_for_wireless_networks",
                    "canonical_en": "Applications For Wireless Networks",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Applications For Wireless Networks"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:intelligent_agent",
                    "canonical_en": "Intelligent Agent",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Intelligent Agent"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:application_mapping",
                    "canonical_en": "Application Mapping",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Application Mapping"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:internet_of_things",
                    "canonical_en": "Internet Of Things",
                    "aliases_en": ["internet of thing (iot)", "internet of things (iot)", "iot"],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Internet Of Things"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:adaboost_algorithm",
                    "canonical_en": "Adaboost Algorithm",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Adaboost Algorithm"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:mesh_adaboost_algorithm",
                    "canonical_en": "Adaboost Algorithm",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Adaboost Algorithm"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:agent_based_framework"]["zh_alias_candidates"][0]["alias"], "基于智能体的框架")
        self.assertEqual(rows["concept:mesh_agent_based_framework"]["zh_alias_candidates"], [])
        self.assertEqual(rows["concept:brca_gene_mutation"]["zh_alias_candidates"][0]["alias"], "BRCA基因突变")
        self.assertEqual(rows["concept:mimo_radar"]["zh_alias_candidates"][0]["alias"], "多输入多输出雷达")
        self.assertEqual(rows["concept:shape_memory_alloy_actuator"]["zh_alias_candidates"][0]["alias"], "形状记忆合金执行器")
        self.assertEqual(rows["concept:attribute_based_encryption"]["zh_alias_candidates"][0]["alias"], "基于属性的加密")
        self.assertEqual(rows["concept:applications_for_wireless_networks"]["zh_alias_candidates"][0]["alias"], "用于无线网络的应用")
        self.assertEqual(rows["concept:intelligent_agent"]["zh_alias_candidates"][0]["alias"], "智能体")
        self.assertEqual(rows["concept:application_mapping"]["zh_alias_candidates"][0]["alias"], "应用映射")
        self.assertEqual(rows["concept:internet_of_things"]["zh_alias_candidates"], [
            {
                "alias": "物联网",
                "confidence": "high",
                "evidence_en": "Internet Of Things",
                "reason": "source-prioritized exact bilingual glossary",
                "source": "agent_exact_glossary",
                "status": "candidate",
            }
        ])
        self.assertEqual(rows["concept:adaboost_algorithm"]["zh_alias_candidates"][0]["alias"], "AdaBoost算法")
        self.assertEqual(rows["concept:mesh_adaboost_algorithm"]["zh_alias_candidates"][0]["alias"], "AdaBoost算法")

    def test_rejects_redundant_compositional_aliases_without_literal_pattern_blocks(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:repeated_component_translation",
                    "canonical_en": "Recognition Recognition",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Recognition Recognition"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:overlapping_component_translation",
                    "canonical_en": "Smart Intelligent Agent",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Smart Intelligent Agent"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:exact_phrase_still_allowed",
                    "canonical_en": "Intelligent Agent",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Intelligent Agent"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:normal_mixed_alias_still_allowed",
                    "canonical_en": "Adaboost Algorithm",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Adaboost Algorithm"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:repeated_component_translation"]["zh_alias_candidates"], [])
        self.assertEqual(rows["concept:overlapping_component_translation"]["zh_alias_candidates"], [])
        self.assertEqual(rows["concept:exact_phrase_still_allowed"]["zh_alias_candidates"][0]["alias"], "智能体")
        self.assertEqual(rows["concept:normal_mixed_alias_still_allowed"]["zh_alias_candidates"][0]["alias"], "AdaBoost算法")

    def test_mixed_class_suffix_candidates_use_canonical_terms_for_non_priority_sources(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:adamts13_protein",
                    "canonical_en": "Adamts13 Protein",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Adamts13 Protein"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:acute_aortic_syndrome",
                    "canonical_en": "Acute Aortic Syndrome",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Acute Aortic Syndrome"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:acetylcholine_release_inhibitor",
                    "canonical_en": "Acetylcholine Release Inhibitors",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Acetylcholine Release Inhibitors"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:advanced_practice_nursing",
                    "canonical_en": "Advanced Practice Nursing",
                    "aliases_en": [],
                    "domains": ["biomedical", "disciplines_and_occupations"],
                    "source_refs": [{"source": "mesh", "label": "Advanced Practice Nursing"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:home_care_services",
                    "canonical_en": "Home Care Services",
                    "aliases_en": [],
                    "domains": ["health_sciences", "medicine"],
                    "source_refs": [{"source": "mesh", "label": "Home Care Services"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:colored_petri_net",
                    "canonical_en": "Colored Petri Net",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Colored Petri Net"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:mesh_alias_not_promoted",
                    "canonical_en": "Acatalasia",
                    "aliases_en": ["Takahara Disease"],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Acatalasia"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:adamts13_protein"]["zh_alias_candidates"][0]["alias"], "ADAMTS13蛋白")
        self.assertEqual(rows["concept:acute_aortic_syndrome"]["zh_alias_candidates"][0]["alias"], "急性主动脉综合征")
        self.assertEqual(
            rows["concept:acetylcholine_release_inhibitor"]["zh_alias_candidates"][0]["alias"],
            "乙酰胆碱释放抑制剂",
        )
        self.assertEqual(rows["concept:advanced_practice_nursing"]["zh_alias_candidates"][0]["alias"], "先进实践护理")
        self.assertEqual(rows["concept:home_care_services"]["zh_alias_candidates"][0]["alias"], "家庭护理服务")
        self.assertEqual(rows["concept:colored_petri_net"]["zh_alias_candidates"][0]["alias"], "有色Petri网")
        self.assertEqual(rows["concept:mesh_alias_not_promoted"]["zh_alias_candidates"], [])

    def test_source_priority_compositional_fallback_is_shape_limited_before_label_fallback(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:single_unknown_segment",
                    "canonical_en": "Academic Integrity And Plagiarism",
                    "aliases_en": [],
                    "domains": ["social_sciences"],
                    "source_refs": [{"source": "openalex_topics", "label": "Academic Integrity And Plagiarism"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:too_many_unknown_segments",
                    "canonical_en": "Foo And Bar Signaling",
                    "aliases_en": [],
                    "domains": ["life_sciences"],
                    "source_refs": [{"source": "openalex_topics", "label": "Foo And Bar Signaling"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:single_unknown_segment"]["zh_alias_candidates"][0]["alias"], "学术诚信与剽窃")
        self.assertEqual(rows["concept:too_many_unknown_segments"]["zh_alias_candidates"], [])

    def test_cross_domain_common_terms_are_translated_before_unknown_fallback(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:acute_ischemic_stroke_management",
                    "canonical_en": "Acute Ischemic Stroke Management",
                    "aliases_en": [],
                    "domains": ["health_sciences", "medicine"],
                    "source_refs": [{"source": "openalex_topics", "label": "Acute Ischemic Stroke Management"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:acute_myocardial_infarction_research",
                    "canonical_en": "Acute Myocardial Infarction Research",
                    "aliases_en": [],
                    "domains": ["health_sciences", "medicine"],
                    "source_refs": [{"source": "openalex_topics", "label": "Acute Myocardial Infarction Research"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:acute_respiratory_distress_syndrome",
                    "canonical_en": "Acute Respiratory Distress Syndrome",
                    "aliases_en": [],
                    "domains": ["engineering_in_medicine_and_biology"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Acute Respiratory Distress Syndrome"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:acid_sensing_ion_channel",
                    "canonical_en": "Acid Sensing Ion Channels",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Acid Sensing Ion Channels"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:active_disturbance_rejection_control",
                    "canonical_en": "Active Disturbance Rejection Controls",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Active Disturbance Rejection Controls"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:central_nervous_system",
                    "canonical_en": "Central Nervous System",
                    "aliases_en": [],
                    "domains": ["biomedical", "anatomy"],
                    "source_refs": [{"source": "mesh", "label": "Central Nervous System"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:load_balancing_algorithm",
                    "canonical_en": "Load Balancing Algorithms",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Load Balancing Algorithms"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:unknown_proper_phrase_keeps_readable_spacing",
                    "canonical_en": "Foo Bar System",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Foo Bar System"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:acute_ischemic_stroke_management"]["zh_alias_candidates"][0]["alias"], "急性缺血性卒中管理")
        self.assertEqual(rows["concept:acute_myocardial_infarction_research"]["zh_alias_candidates"][0]["alias"], "急性心肌梗死研究")
        self.assertEqual(rows["concept:acute_respiratory_distress_syndrome"]["zh_alias_candidates"][0]["alias"], "急性呼吸窘迫综合征")
        self.assertEqual(rows["concept:acid_sensing_ion_channel"]["zh_alias_candidates"][0]["alias"], "酸敏感离子通道")
        self.assertEqual(rows["concept:active_disturbance_rejection_control"]["zh_alias_candidates"][0]["alias"], "主动扰动抑制控制")
        self.assertEqual(rows["concept:central_nervous_system"]["zh_alias_candidates"][0]["alias"], "中枢神经系统")
        self.assertEqual(rows["concept:load_balancing_algorithm"]["zh_alias_candidates"][0]["alias"], "负载均衡算法")
        self.assertEqual(rows["concept:unknown_proper_phrase_keeps_readable_spacing"]["zh_alias_candidates"], [])

    def test_agent_translation_is_domain_aware(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:adrenergic_agent",
                    "canonical_en": "Adrenergic Agents",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Adrenergic Agents"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:antimicrobial_agent_and_application",
                    "canonical_en": "Antimicrobial Agents And Applications",
                    "aliases_en": [],
                    "domains": ["chemistry", "physical_sciences"],
                    "source_refs": [{"source": "openalex_topics", "label": "Antimicrobial Agents And Applications"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:agent_based_modeling",
                    "canonical_en": "Agent-based Modeling",
                    "aliases_en": [],
                    "domains": ["systems_engineering_and_theory"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Agent-based Modeling"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:adrenergic_agent"]["zh_alias_candidates"][0]["alias"], "肾上腺素能药剂")
        self.assertEqual(rows["concept:antimicrobial_agent_and_application"]["zh_alias_candidates"][0]["alias"], "抗微生物药剂与应用")
        self.assertEqual(rows["concept:agent_based_modeling"]["zh_alias_candidates"][0]["alias"], "基于智能体的建模")

    def test_polysemous_terms_use_domain_sensitive_translations(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:public_administration_and_governance",
                    "canonical_en": "Public Administration And Governance",
                    "aliases_en": [],
                    "domains": ["social_sciences"],
                    "source_refs": [{"source": "openalex_topics", "label": "Public Administration And Governance"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:oral_administration",
                    "canonical_en": "Administration, Oral",
                    "aliases_en": [],
                    "domains": ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Administration, Oral"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:oral_communication",
                    "canonical_en": "Oral Communication",
                    "aliases_en": [],
                    "domains": ["professional_communication"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Oral Communication"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:oral_history_memory_narrative_analysis",
                    "canonical_en": "Oral History, Memory, Narrative Analysis",
                    "aliases_en": [],
                    "domains": ["arts_and_humanities", "social_sciences"],
                    "source_refs": [{"source": "openalex_topics", "label": "Oral History, Memory, Narrative Analysis"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:schur_complement",
                    "canonical_en": "Schur Complement",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Schur Complement"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:complement_activation",
                    "canonical_en": "Complement Activation",
                    "aliases_en": [],
                    "domains": ["biomedical", "phenomena_and_processes"],
                    "source_refs": [{"source": "mesh", "label": "Complement Activation"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:viral_marketing",
                    "canonical_en": "Viral Marketing",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Viral Marketing"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:clinical_trials",
                    "canonical_en": "Clinical Trials",
                    "aliases_en": [],
                    "domains": ["engineering_in_medicine_and_biology"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Clinical Trials"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:bacterial_typing_techniques",
                    "canonical_en": "Bacterial Typing Techniques",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Bacterial Typing Techniques"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:patient_rehabilitation",
                    "canonical_en": "Patient Rehabilitation",
                    "aliases_en": [],
                    "domains": ["engineering_in_medicine_and_biology"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Patient Rehabilitation"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:public_administration_and_governance"]["zh_alias_candidates"][0]["alias"], "公共行政与治理")
        self.assertEqual(rows["concept:oral_administration"]["zh_alias_candidates"][0]["alias"], "口服给药")
        self.assertEqual(rows["concept:oral_communication"]["zh_alias_candidates"][0]["alias"], "口头交流")
        self.assertEqual(
            rows["concept:oral_history_memory_narrative_analysis"]["zh_alias_candidates"][0]["alias"],
            "口述史记忆叙事分析",
        )
        self.assertEqual(rows["concept:schur_complement"]["zh_alias_candidates"][0]["alias"], "Schur补")
        self.assertEqual(rows["concept:complement_activation"]["zh_alias_candidates"][0]["alias"], "补体活化")
        self.assertEqual(rows["concept:viral_marketing"]["zh_alias_candidates"][0]["alias"], "病毒式营销")
        self.assertEqual(rows["concept:clinical_trials"]["zh_alias_candidates"][0]["alias"], "临床试验")
        self.assertEqual(rows["concept:bacterial_typing_techniques"]["zh_alias_candidates"][0]["alias"], "细菌分型技术")
        self.assertEqual(rows["concept:patient_rehabilitation"]["zh_alias_candidates"][0]["alias"], "患者康复")

    def test_high_confidence_terms_reduce_mixed_english_pollution(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:analytical_hierarchy_process",
                    "canonical_en": "Analytical Hierarchy Process",
                    "aliases_en": [],
                    "domains": ["systems_engineering_and_theory"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Analytical Hierarchy Process"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:border_gateway_protocol",
                    "canonical_en": "Border Gateway Protocol",
                    "aliases_en": [],
                    "domains": ["communications_technology"],
                    "source_refs": [{"source": "cso", "label": "Border Gateway Protocol"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:chosen_ciphertext_attack",
                    "canonical_en": "Chosen Ciphertext Attack",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Chosen Ciphertext Attack"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:auto_encoders",
                    "canonical_en": "Auto Encoders",
                    "aliases_en": [],
                    "domains": ["computational_and_artificial_intelligence"],
                    "source_refs": [{"source": "openalex_topics", "label": "Auto Encoders"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:adrenal_gland_diseases",
                    "canonical_en": "Adrenal Gland Diseases",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Adrenal Gland Diseases"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:bile_duct_diseases",
                    "canonical_en": "Bile Duct Diseases",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Bile Duct Diseases"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:common_bile_duct_diseases",
                    "canonical_en": "Common Bile Duct Diseases",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Common Bile Duct Diseases"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:carotid_artery_diseases",
                    "canonical_en": "Carotid Artery Diseases",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Carotid Artery Diseases"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:carotid_artery_injuries",
                    "canonical_en": "Carotid Artery Injuries",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Carotid Artery Injuries"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:cell_death",
                    "canonical_en": "Cell Death",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Cell Death"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:retinal_diseases",
                    "canonical_en": "Retinal Diseases",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Retinal Diseases"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:kidney_diseases",
                    "canonical_en": "Kidney Diseases",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Kidney Diseases"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:liver_diseases",
                    "canonical_en": "Liver Diseases",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Liver Diseases"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:analytical_hierarchy_process"]["zh_alias_candidates"][0]["alias"], "层次分析法")
        self.assertEqual(rows["concept:border_gateway_protocol"]["zh_alias_candidates"][0]["alias"], "边界网关协议")
        self.assertEqual(rows["concept:chosen_ciphertext_attack"]["zh_alias_candidates"][0]["alias"], "选择密文攻击")
        self.assertEqual(rows["concept:auto_encoders"]["zh_alias_candidates"][0]["alias"], "自编码器")
        self.assertEqual(rows["concept:adrenal_gland_diseases"]["zh_alias_candidates"][0]["alias"], "肾上腺疾病")
        self.assertEqual(rows["concept:bile_duct_diseases"]["zh_alias_candidates"][0]["alias"], "胆管疾病")
        self.assertEqual(rows["concept:common_bile_duct_diseases"]["zh_alias_candidates"][0]["alias"], "胆总管疾病")
        self.assertEqual(rows["concept:carotid_artery_diseases"]["zh_alias_candidates"][0]["alias"], "颈动脉疾病")
        self.assertEqual(rows["concept:carotid_artery_injuries"]["zh_alias_candidates"][0]["alias"], "颈动脉损伤")
        self.assertEqual(rows["concept:cell_death"]["zh_alias_candidates"][0]["alias"], "细胞死亡")
        self.assertEqual(rows["concept:retinal_diseases"]["zh_alias_candidates"][0]["alias"], "视网膜疾病")
        self.assertEqual(rows["concept:kidney_diseases"]["zh_alias_candidates"][0]["alias"], "肾脏疾病")
        self.assertEqual(rows["concept:liver_diseases"]["zh_alias_candidates"][0]["alias"], "肝脏疾病")

    def test_residual_mixed_english_terms_use_domain_exact_glosses(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:ad_hoc_routing_protocol",
                    "canonical_en": "Ad Hoc Routing Protocol",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Ad Hoc Routing Protocol"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:gtp_binding_alpha",
                    "canonical_en": "Gtp-binding Protein Alpha Subunits",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Gtp-binding Protein Alpha Subunits"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:cdc42_gtp_binding",
                    "canonical_en": "Cdc42 Gtp-binding Protein",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Cdc42 Gtp-binding Protein"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:cytochrome_p450_inhibitors",
                    "canonical_en": "Cytochrome P-450 Cyp1a2 Inhibitors",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Cytochrome P-450 Cyp1a2 Inhibitors"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:cytochrome_p450_cyp2b6_inhibitors",
                    "canonical_en": "Cytochrome P-450 Cyp2b6 Inhibitors",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Cytochrome P-450 Cyp2b6 Inhibitors"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:erbium_doped_fiber_amplifier",
                    "canonical_en": "Erbium Doped Fiber Amplifiers",
                    "aliases_en": [],
                    "domains": ["photonics", "signal_processing"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Erbium Doped Fiber Amplifiers"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:delta_sigma_modulation",
                    "canonical_en": "Delta-sigma Modulation",
                    "aliases_en": [],
                    "domains": ["circuits_and_systems", "signal_processing"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Delta-sigma Modulation"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:k_nearest_neighbor",
                    "canonical_en": "K Nearest Neighbor",
                    "aliases_en": ["K-nn Algorithm"],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "K Nearest Neighbor"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:delay_locked_loops",
                    "canonical_en": "Delay-locked Loops",
                    "aliases_en": [],
                    "domains": ["circuits_and_systems"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Delay-locked Loops"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:core_binding_factor_alpha",
                    "canonical_en": "Core Binding Factor Alpha Subunits",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Core Binding Factor Alpha Subunits"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:core_binding_factor_alpha_1",
                    "canonical_en": "Core Binding Factor Alpha 1 Subunit",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Core Binding Factor Alpha 1 Subunit"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:african_continental_ancestry",
                    "canonical_en": "African Continental Ancestry Group",
                    "aliases_en": [],
                    "domains": ["biomedical", "named_groups"],
                    "source_refs": [{"source": "mesh", "label": "African Continental Ancestry Group"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:mitochondrial_trifunctional_alpha",
                    "canonical_en": "Mitochondrial Trifunctional Protein, Alpha Subunit",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Mitochondrial Trifunctional Protein, Alpha Subunit"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:carotid_ultrasonography",
                    "canonical_en": "Ultrasonography, Carotid Arteries",
                    "aliases_en": [],
                    "domains": ["biomedical", "diagnostic_techniques"],
                    "source_refs": [{"source": "mesh", "label": "Ultrasonography, Carotid Arteries"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:erbium_doped",
                    "canonical_en": "Erbium Doped",
                    "aliases_en": [],
                    "domains": ["photonics", "signal_processing"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Erbium Doped"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:vehicular_ad_hoc_networks_vanets",
                    "canonical_en": "Vehicular Ad Hoc Networks (vanets)",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Vehicular Ad Hoc Networks (vanets)"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:ad_hoc_routing_protocol"]["zh_alias_candidates"][0]["alias"], "自组织路由协议")
        self.assertEqual(rows["concept:gtp_binding_alpha"]["zh_alias_candidates"][0]["alias"], "GTP结合蛋白α亚基")
        self.assertEqual(rows["concept:cdc42_gtp_binding"]["zh_alias_candidates"][0]["alias"], "CDC42 GTP结合蛋白")
        self.assertEqual(rows["concept:cytochrome_p450_inhibitors"]["zh_alias_candidates"][0]["alias"], "细胞色素P450 CYP1A2抑制剂")
        self.assertEqual(rows["concept:cytochrome_p450_cyp2b6_inhibitors"]["zh_alias_candidates"][0]["alias"], "细胞色素P450 CYP2B6抑制剂")
        self.assertEqual(rows["concept:erbium_doped_fiber_amplifier"]["zh_alias_candidates"][0]["alias"], "掺铒光纤放大器")
        self.assertEqual(rows["concept:delta_sigma_modulation"]["zh_alias_candidates"][0]["alias"], "Δ-Σ调制")
        k_nearest_aliases = [item["alias"] for item in rows["concept:k_nearest_neighbor"]["zh_alias_candidates"]]
        self.assertEqual(k_nearest_aliases[:2], ["K近邻", "K近邻算法"])
        self.assertNotIn("K Nn算法", k_nearest_aliases)
        self.assertEqual(rows["concept:delay_locked_loops"]["zh_alias_candidates"][0]["alias"], "延迟锁定环")
        self.assertEqual(rows["concept:core_binding_factor_alpha"]["zh_alias_candidates"][0]["alias"], "核心结合因子α亚基")
        self.assertEqual(rows["concept:core_binding_factor_alpha_1"]["zh_alias_candidates"][0]["alias"], "核心结合因子α1亚基")
        self.assertEqual(rows["concept:african_continental_ancestry"]["zh_alias_candidates"][0]["alias"], "非洲大陆祖源群体")
        self.assertEqual(rows["concept:mitochondrial_trifunctional_alpha"]["zh_alias_candidates"][0]["alias"], "线粒体三功能蛋白α亚基")
        self.assertEqual(rows["concept:carotid_ultrasonography"]["zh_alias_candidates"][0]["alias"], "颈动脉超声检查")
        self.assertEqual(rows["concept:erbium_doped"]["zh_alias_candidates"][0]["alias"], "掺铒")
        self.assertEqual(rows["concept:vehicular_ad_hoc_networks_vanets"]["zh_alias_candidates"][0]["alias"], "车载自组织网络")

    def test_exact_domain_aware_expansion_avoids_reopening_mixed_fallback(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:charge_pumps",
                    "canonical_en": "Charge Pumps",
                    "aliases_en": [],
                    "domains": ["circuits_and_systems"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Charge Pumps"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:case_base",
                    "canonical_en": "Case Base",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Case Base"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:case_control_studies",
                    "canonical_en": "Case-control Studies",
                    "aliases_en": [],
                    "domains": ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Case-control Studies"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:closed_loop_control",
                    "canonical_en": "Closed Loop Control",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Closed Loop Control"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:cable_tv",
                    "canonical_en": "Cable TV",
                    "aliases_en": [],
                    "domains": ["communications_technology"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Cable TV"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:collaborative_tools",
                    "canonical_en": "Collaborative Tools",
                    "aliases_en": [],
                    "domains": ["professional_communication"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Collaborative Tools"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:cell_free_system",
                    "canonical_en": "Cell-free System",
                    "aliases_en": [],
                    "domains": ["anatomy", "biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Cell-free System"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:charge_pumps"]["zh_alias_candidates"][0]["alias"], "电荷泵")
        self.assertEqual(rows["concept:case_base"]["zh_alias_candidates"][0]["alias"], "案例库")
        self.assertEqual(rows["concept:case_control_studies"]["zh_alias_candidates"][0]["alias"], "病例对照研究")
        self.assertEqual(rows["concept:closed_loop_control"]["zh_alias_candidates"][0]["alias"], "闭环控制")
        self.assertEqual(rows["concept:cable_tv"]["zh_alias_candidates"][0]["alias"], "有线电视")
        self.assertEqual(rows["concept:collaborative_tools"]["zh_alias_candidates"][0]["alias"], "协同工具")
        self.assertEqual(rows["concept:cell_free_system"]["zh_alias_candidates"], [])

    def test_additional_exact_domain_terms_expand_without_acronym_noise(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:achievable_rate",
                    "canonical_en": "Achievable Rate",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Achievable Rate"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:ac_dc_power_converters",
                    "canonical_en": "Ac-dc Power Converters",
                    "aliases_en": [],
                    "domains": ["power_electronics"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Ac-dc Power Converters"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:active_inductors",
                    "canonical_en": "Active Inductors",
                    "aliases_en": [],
                    "domains": ["circuits_and_systems"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Active Inductors"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:adaptive_cruise_control",
                    "canonical_en": "Adaptive Cruise Control",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Adaptive Cruise Control"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:additive_white_gaussian_noise_channel",
                    "canonical_en": "Additive White Gaussian Noise Channel",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Additive White Gaussian Noise Channel"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:admission_control_algorithms",
                    "canonical_en": "Admission Control Algorithms",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Admission Control Algorithms"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:aac",
                    "canonical_en": "Aac",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Aac"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:achievable_rate"]["zh_alias_candidates"][0]["alias"], "可达速率")
        self.assertEqual(rows["concept:ac_dc_power_converters"]["zh_alias_candidates"][0]["alias"], "AC-DC电源转换器")
        self.assertEqual(rows["concept:active_inductors"]["zh_alias_candidates"][0]["alias"], "有源电感")
        self.assertEqual(rows["concept:adaptive_cruise_control"]["zh_alias_candidates"][0]["alias"], "自适应巡航控制")
        self.assertEqual(
            rows["concept:additive_white_gaussian_noise_channel"]["zh_alias_candidates"][0]["alias"],
            "加性白高斯噪声信道",
        )
        self.assertEqual(rows["concept:admission_control_algorithms"]["zh_alias_candidates"][0]["alias"], "接入控制算法")
        self.assertEqual(rows["concept:aac"]["zh_alias_candidates"], [])

    def test_domain_overrides_do_not_overgeneralize_polysemous_tokens(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:access_charges",
                    "canonical_en": "Access Charges",
                    "aliases_en": [],
                    "domains": ["communications_technology"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Access Charges"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:charge_pumps",
                    "canonical_en": "Charge Pumps",
                    "aliases_en": [],
                    "domains": ["circuits_and_systems"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Charge Pumps"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:active_noise_reduction",
                    "canonical_en": "Active Noise Reduction",
                    "aliases_en": [],
                    "domains": ["signal_processing"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Active Noise Reduction"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertNotEqual(rows["concept:access_charges"]["zh_alias_candidates"][0]["alias"], "访问电荷")
        self.assertEqual(rows["concept:access_charges"]["zh_alias_candidates"][0]["alias"], "接入费用")
        self.assertEqual(rows["concept:charge_pumps"]["zh_alias_candidates"][0]["alias"], "电荷泵")
        self.assertEqual(rows["concept:active_noise_reduction"]["zh_alias_candidates"][0]["alias"], "主动降噪")

    def test_compositional_expansion_keeps_standard_technical_terms_precise(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:virtual_environment",
                    "canonical_en": "3-d Virtual Environment",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "3-d Virtual Environment"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:abstract_state_machine",
                    "canonical_en": "Abstract State Machines",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Abstract State Machines"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:access_rights",
                    "canonical_en": "Access Rights",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Access Rights"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:acoustic_streaming",
                    "canonical_en": "Acoustic Streaming",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Acoustic Streaming"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:virtual_environment"]["zh_alias_candidates"][0]["alias"], "三维虚拟环境")
        self.assertEqual(rows["concept:abstract_state_machine"]["zh_alias_candidates"][0]["alias"], "抽象状态机")
        self.assertEqual(rows["concept:access_rights"]["zh_alias_candidates"][0]["alias"], "访问权限")
        self.assertEqual(rows["concept:acoustic_streaming"]["zh_alias_candidates"][0]["alias"], "声流")

    def test_reviewed_technical_collocations_replace_literal_word_senses(self) -> None:
        cases = [
            ("additive_gaussian_noise", "Additive Gaussian Noise", ["computer_science"], "加性高斯噪声"),
            ("african_american", "African American", ["social_sciences"], "非裔美国人"),
            ("air_navigation", "Air Navigation", ["aerospace_and_electronic_systems"], "空中导航"),
            ("air_to_ground_communication", "Air To Ground Communication", ["communications_technology"], "空地通信"),
            ("algebraic_geometry_number_theory", "Algebraic Geometry And Number Theory", ["mathematics"], "代数几何与数论"),
            ("analytical_expression", "Analytical Expressions", ["mathematics"], "解析表达式"),
            ("approximation_error", "Approximation Error", ["computer_science"], "近似误差"),
            ("antenna_diversity", "Antenna Diversity", ["antennas_and_propagation"], "天线分集"),
            ("antenna_pattern", "Antenna Pattern", ["antennas_and_propagation"], "天线方向图"),
            ("active_circuit", "Active Circuits", ["circuits_and_systems"], "有源电路"),
            ("advanced_power_amplifier_design", "Advanced Power Amplifier Design", ["computer_science"], "先进功率放大器设计"),
            ("ai_planning", "Ai Planning", ["computer_science"], "AI规划"),
            ("adaptive_sliding_mode_control", "Adaptive Sliding Mode Control", ["control_systems"], "自适应滑模控制"),
            ("architectural_pattern", "Architectural Pattern", ["computer_science"], "架构模式"),
            ("advanced_mathematical_identities", "Advanced Mathematical Identities", ["mathematics"], "高等数学恒等式"),
            ("architectural_knowledge", "Architectural Knowledge", ["computer_science"], "架构知识"),
            ("architectural_knowledge_management", "Architectural Knowledge Management", ["computer_science"], "架构知识管理"),
            ("architectural_knowledge_modeling", "Architectural Knowledge Modeling", ["computer_science"], "架构知识建模"),
            ("architectural_knowledge_sharing", "Architectural Knowledge Sharing", ["computer_science"], "架构知识共享"),
            ("architectural_language", "Architectural Language", ["computer_science"], "架构描述语言"),
            ("number_theory", "Number Theory", ["mathematics"], "数论"),
            ("power_amplifier", "Power Amplifiers", ["signal_processing"], "功率放大器"),
            ("high_power_amplifier", "High Power Amplifiers", ["signal_processing"], "高功率放大器"),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "cso", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_noncanonical_aliases_do_not_generate_compositional_scope_drift(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:ai_planning",
                    "canonical_en": "Ai Planning",
                    "aliases_en": ["planning algorithms"],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Ai Planning"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:3d_virtual_environment",
                    "canonical_en": "3-d Virtual Environment",
                    "aliases_en": ["virtual reality technology"],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "3-d Virtual Environment"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(
            [item["alias"] for item in rows["concept:ai_planning"]["zh_alias_candidates"]],
            ["AI规划"],
        )
        self.assertEqual(
            [item["alias"] for item in rows["concept:3d_virtual_environment"]["zh_alias_candidates"]],
            ["三维虚拟环境"],
        )


    def test_domain_sensitive_review_fixes_common_compositional_mistranslations(self) -> None:
        cases = [
            (
                "base_stations",
                "Base Stations",
                ["communications_technology", "computer_science"],
                "基站",
            ),
            (
                "color_tv",
                "Color TV",
                ["communications_technology"],
                "彩色电视",
            ),
            (
                "digital_tv",
                "Digital TV",
                ["communications_technology"],
                "数字电视",
            ),
            (
                "battery_storage_plants",
                "Battery Storage Plants",
                ["power_engineering_and_energy"],
                "电池储能电站",
            ),
            (
                "electric_power_systems_control",
                "Electric Power Systems And Control",
                ["power_engineering_and_energy"],
                "电力系统与控制",
            ),
            (
                "estimation_error",
                "Estimation Error",
                ["mathematics"],
                "估计误差",
            ),
            (
                "base_station_antennas",
                "Base Station Antennas",
                ["communications_technology"],
                "基站天线",
            ),
            (
                "mobile_base_station",
                "Mobile Base Station",
                ["communications_technology"],
                "移动基站",
            ),
            (
                "difference_equations",
                "Difference Equations",
                ["mathematics"],
                "差分方程",
            ),
            (
                "load_flow",
                "Load Flow",
                ["power_engineering_and_energy"],
                "潮流",
            ),
            (
                "load_flow_control",
                "Load Flow Control",
                ["power_engineering_and_energy"],
                "潮流控制",
            ),
            (
                "current_transformers",
                "Current Transformers",
                ["power_engineering_and_energy"],
                "电流互感器",
            ),
            (
                "electric_power_consumption",
                "Electric Power Consumption",
                ["power_engineering_and_energy"],
                "电力消耗",
            ),
            (
                "electric_power_industries",
                "Electric Power Industries",
                ["power_engineering_and_energy"],
                "电力行业",
            ),
            (
                "electric_power_system_optimization",
                "Electric Power System Optimization",
                ["power_engineering_and_energy"],
                "电力系统优化",
            ),
            (
                "high_speed_networks",
                "High-speed Networks",
                ["communications_technology"],
                "高速网络",
            ),
            (
                "instrument_transformers",
                "Instrument Transformers",
                ["power_engineering_and_energy"],
                "互感器",
            ),
            (
                "power_distribution",
                "Power Distribution",
                ["power_engineering_and_energy"],
                "配电",
            ),
            (
                "wave_energy_conversion",
                "Wave Energy Conversion",
                ["power_engineering_and_energy"],
                "波浪能转换",
            ),
            (
                "heart_failure",
                "Heart Failure",
                ["biomedical", "diseases"],
                "心力衰竭",
            ),
            (
                "acute_phase_proteins",
                "Acute-phase Proteins",
                ["biomedical", "chemicals_and_drugs"],
                "急性期蛋白",
            ),
            (
                "fiber_to_the_home",
                "Fiber To The Home",
                ["communications_technology"],
                "光纤到户",
            ),
            (
                "product_families",
                "Product Families",
                ["computer_science"],
                "产品族",
            ),
            (
                "product_family_design",
                "Product Family Design",
                ["computer_science"],
                "产品族设计",
            ),
            (
                "power_distribution_control",
                "Power Distribution Control",
                ["power_engineering_and_energy"],
                "配电控制",
            ),
            (
                "power_distribution_lines",
                "Power Distribution Lines",
                ["power_engineering_and_energy"],
                "配电线路",
            ),
            (
                "electrical_power_distribution",
                "Electrical Power Distribution",
                ["power_engineering_and_energy"],
                "配电",
            ),
            (
                "high_speed_integrated_circuits",
                "High-speed Integrated Circuits",
                ["communications_technology"],
                "高速集成电路",
            ),
            (
                "high_speed_machining",
                "High Speed Machining",
                ["manufacturing_engineering"],
                "高速加工",
            ),
            (
                "nuclear_power_plants",
                "Nuclear Power Plants",
                ["power_engineering_and_energy"],
                "核电站",
            ),
            (
                "multiple_antenna",
                "Multiple Antenna",
                ["communications_technology"],
                "多天线",
            ),
            (
                "multiple_attribute_decision_making",
                "Multiple Attribute Decision Making",
                ["computer_science"],
                "多属性决策",
            ),
            (
                "multiple_classifier_system",
                "Multiple Classifier System",
                ["computer_science"],
                "多分类器系统",
            ),
            (
                "multiple_beam",
                "Multiple Beam",
                ["communications_technology"],
                "多波束",
            ),
            (
                "multiple_input_single_outputs",
                "Multiple Input Single Outputs",
                ["computer_science"],
                "多输入单输出",
            ),
            (
                "multiple_kernels",
                "Multiple Kernels",
                ["computer_science"],
                "多核",
            ),
            (
                "multiple_linear_regression",
                "Multiple Linear Regression",
                ["mathematics"],
                "多元线性回归",
            ),
            (
                "multiple_organ_failure",
                "Multiple Organ Failure",
                ["biomedical", "diseases"],
                "多器官衰竭",
            ),
            (
                "heat_transfer",
                "Heat Transfer",
                ["engineering", "physical_sciences"],
                "传热",
            ),
            (
                "heat_transfer_and_optimization",
                "Heat Transfer And Optimization",
                ["engineering", "physical_sciences"],
                "传热与优化",
            ),
            (
                "fluid_dynamics_and_heat_transfer",
                "Fluid Dynamics And Heat Transfer",
                ["engineering", "physical_sciences"],
                "流体动力学与传热",
            ),
            (
                "active_matrix_oled",
                "Active Matrix Organic Light Emitting Diodes",
                ["electron_devices"],
                "有源矩阵有机发光二极管",
            ),
            (
                "accidents_home",
                "Accidents, Home",
                ["biomedical", "health_care"],
                "家庭事故",
            ),
            (
                "multiple_path",
                "Multiple-path",
                ["communications_technology"],
                "多径",
            ),
            (
                "information_transfer_rate",
                "Information Transfer Rate",
                ["computer_science"],
                "信息传输速率",
            ),
            (
                "load_transfer",
                "Load Transfer",
                ["engineering"],
                "载荷传递",
            ),
            (
                "gene_transfer_techniques",
                "Gene Transfer Techniques",
                ["biomedical"],
                "基因转移技术",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "ieee_taxonomy", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_biomedical_numbered_and_topic_patterns_expand_review_gated_candidates(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:fourteen_three_three_protein",
                    "canonical_en": "14-3-3 Proteins",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "14-3-3 Proteins"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:activating_transcription_factor_1",
                    "canonical_en": "Activating Transcription Factor 1",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Activating Transcription Factor 1"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:hydroxysteroid_dehydrogenase_type_1",
                    "canonical_en": "11-beta-hydroxysteroid Dehydrogenase Type 1",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "11-beta-hydroxysteroid Dehydrogenase Type 1"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:abbreviations_as_topic",
                    "canonical_en": "Abbreviations As Topic",
                    "aliases_en": [],
                    "domains": ["biomedical", "publication_characteristics"],
                    "source_refs": [{"source": "mesh", "label": "Abbreviations As Topic"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:clinical_trial_phase_i_as_topic",
                    "canonical_en": "Clinical Trial Phase I As Topic",
                    "aliases_en": [],
                    "domains": ["biomedical", "publication_characteristics"],
                    "source_refs": [{"source": "mesh", "label": "Clinical Trial Phase I As Topic"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:abortifacient_agents",
                    "canonical_en": "Abortifacient Agents",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Abortifacient Agents"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:barium_radioisotopes",
                    "canonical_en": "Barium Radioisotopes",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Barium Radioisotopes"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:adenylosuccinate_lyase",
                    "canonical_en": "Adenylosuccinate Lyase",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Adenylosuccinate Lyase"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:african_people",
                    "canonical_en": "African People",
                    "aliases_en": [],
                    "domains": ["biomedical", "named_groups"],
                    "source_refs": [{"source": "mesh", "label": "African People"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:fourteen_three_three_protein"]["zh_alias_candidates"][0]["alias"], "14-3-3蛋白")
        self.assertEqual(rows["concept:activating_transcription_factor_1"]["zh_alias_candidates"][0]["alias"], "活化转录因子1")
        self.assertEqual(
            rows["concept:hydroxysteroid_dehydrogenase_type_1"]["zh_alias_candidates"][0]["alias"],
            "11β-羟类固醇脱氢酶1型",
        )
        self.assertEqual(rows["concept:abbreviations_as_topic"]["zh_alias_candidates"][0]["alias"], "缩写主题")
        self.assertEqual(rows["concept:clinical_trial_phase_i_as_topic"]["zh_alias_candidates"][0]["alias"], "I期临床试验主题")
        self.assertEqual(rows["concept:abortifacient_agents"]["zh_alias_candidates"][0]["alias"], "堕胎药")
        self.assertEqual(rows["concept:barium_radioisotopes"]["zh_alias_candidates"][0]["alias"], "钡放射性同位素")
        self.assertEqual(rows["concept:adenylosuccinate_lyase"]["zh_alias_candidates"][0]["alias"], "腺苷酸琥珀酸裂解酶")
        self.assertEqual(rows["concept:african_people"]["zh_alias_candidates"][0]["alias"], "非洲人群")

    def test_long_biomedical_class_suffixes_are_review_gated_unless_exact(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:autoimmune_neurological_treatments",
                    "canonical_en": "Autoimmune Neurological Disorders And Treatments",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Autoimmune Neurological Disorders And Treatments"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:amino_acids_peptides_proteins",
                    "canonical_en": "Amino Acids, Peptides, And Proteins",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Amino Acids, Peptides, And Proteins"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:bronchiolitis_viral",
                    "canonical_en": "Bronchiolitis, Viral",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Bronchiolitis, Viral"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(
            rows["concept:autoimmune_neurological_treatments"]["zh_alias_candidates"][0]["alias"],
            "自身免疫神经障碍与治疗",
        )
        self.assertEqual(
            rows["concept:amino_acids_peptides_proteins"]["zh_alias_candidates"][0]["alias"],
            "氨基酸、肽和蛋白质",
        )
        self.assertEqual(
            rows["concept:amino_acids_peptides_proteins"]["zh_alias_candidates"][0]["source"],
            "agent_exact_glossary",
        )
        self.assertEqual(rows["concept:bronchiolitis_viral"]["zh_alias_candidates"][0]["alias"], "病毒性细支气管炎")
        self.assertEqual(
            rows["concept:bronchiolitis_viral"]["zh_alias_candidates"][0]["status"],
            "candidate",
        )

    def test_high_frequency_biomedical_components_expand_named_entity_coverage(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:adenine_nucleotide_translocator_1",
                    "canonical_en": "Adenine Nucleotide Translocator 1",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Adenine Nucleotide Translocator 1"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:cationic_amino_acid_transporter_1",
                    "canonical_en": "Cationic Amino Acid Transporter 1",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Cationic Amino Acid Transporter 1"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:chromosome_human_pair_10",
                    "canonical_en": "Chromosomes, Human, Pair 10",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Chromosomes, Human, Pair 10"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:influenza_a_virus",
                    "canonical_en": "Influenza A Virus",
                    "aliases_en": [],
                    "domains": ["biomedical", "organisms"],
                    "source_refs": [{"source": "mesh", "label": "Influenza A Virus"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:proto_oncogene_protein_c_fos",
                    "canonical_en": "Proto-oncogene Protein C-fos",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Proto-oncogene Protein C-fos"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:matrix_metalloproteinase_1",
                    "canonical_en": "Matrix Metalloproteinase 1",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Matrix Metalloproteinase 1"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:adenine_nucleotide_translocator_1"]["zh_alias_candidates"][0]["alias"], "腺嘌呤核苷酸转位酶1")
        self.assertEqual(rows["concept:cationic_amino_acid_transporter_1"]["zh_alias_candidates"][0]["alias"], "阳离子氨基酸转运蛋白1")
        self.assertEqual(rows["concept:chromosome_human_pair_10"]["zh_alias_candidates"][0]["alias"], "人类10号染色体")
        self.assertEqual(rows["concept:influenza_a_virus"]["zh_alias_candidates"][0]["alias"], "甲型流感病毒")
        self.assertEqual(rows["concept:proto_oncogene_protein_c_fos"]["zh_alias_candidates"][0]["alias"], "原癌基因蛋白C-FOS")
        self.assertEqual(rows["concept:matrix_metalloproteinase_1"]["zh_alias_candidates"][0]["alias"], "基质金属蛋白酶1")

    def test_source_priority_label_fallback_is_review_gated_and_skips_short_acronyms(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:unknown_openalex_topic",
                    "canonical_en": "Foo Bar Baz",
                    "aliases_en": [],
                    "domains": ["social_sciences"],
                    "source_refs": [{"source": "openalex_topics", "label": "Foo Bar Baz"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:short_acronym",
                    "canonical_en": "Aac",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "aac"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:mesh_not_fallback",
                    "canonical_en": "Acatalasia",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Acatalasia"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:unknown_openalex_topic"]["zh_alias_candidates"], [])
        self.assertEqual(rows["concept:short_acronym"]["zh_alias_candidates"], [])
        self.assertEqual(rows["concept:mesh_not_fallback"]["zh_alias_candidates"], [])

    def test_non_priority_review_fallback_is_low_confidence_and_shape_guarded(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:abdominal_abscess",
                    "canonical_en": "Abdominal Abscess",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Abdominal Abscess"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:unmapped_injury_scale",
                    "canonical_en": "Unmapped Injury Scale",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Unmapped Injury Scale"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:repeated_token",
                    "canonical_en": "Recognition Recognition Scale",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Recognition Recognition Scale"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:single_unknown",
                    "canonical_en": "Acatalasia",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Acatalasia"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:abdominal_abscess"]["zh_alias_candidates"][0]["alias"], "腹部脓肿")
        self.assertEqual(rows["concept:unmapped_injury_scale"]["zh_alias_candidates"], [])
        self.assertEqual(rows["concept:repeated_token"]["zh_alias_candidates"], [])
        self.assertEqual(rows["concept:single_unknown"]["zh_alias_candidates"], [])

    def test_biomedical_vascular_terms_avoid_artery_duplication(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:aortic_aneurysm",
                    "canonical_en": "Aortic Aneurysm",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Aortic Aneurysm"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:coronary_artery_disease",
                    "canonical_en": "Coronary Artery Disease",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Coronary Artery Disease"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:anomalous_left_coronary_artery",
                    "canonical_en": "Anomalous Left Coronary Artery",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Anomalous Left Coronary Artery"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:aortic_aneurysm"]["zh_alias_candidates"][0]["alias"], "主动脉瘤")
        self.assertEqual(rows["concept:coronary_artery_disease"]["zh_alias_candidates"][0]["alias"], "冠状动脉疾病")
        self.assertNotIn(
            "动脉动脉",
            rows["concept:anomalous_left_coronary_artery"]["zh_alias_candidates"][0]["alias"],
        )

    def test_review_feedback_corrects_polysemous_standard_terms(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:cell_division",
                    "canonical_en": "Cell Division",
                    "aliases_en": [],
                    "domains": ["biomedical", "phenomena_and_processes"],
                    "source_refs": [{"source": "mesh", "label": "Cell Division"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:fractures_closed",
                    "canonical_en": "Fractures, Closed",
                    "aliases_en": [],
                    "domains": ["biomedical", "diseases"],
                    "source_refs": [{"source": "mesh", "label": "Fractures, Closed"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:clinical_trial_phase_ii",
                    "canonical_en": "Clinical Trial Phase II",
                    "aliases_en": [],
                    "domains": ["biomedical", "health_care"],
                    "source_refs": [{"source": "mesh", "label": "Clinical Trial Phase II"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:optimal_solution",
                    "canonical_en": "Optimal Solution",
                    "aliases_en": [],
                    "domains": ["computer_science", "mathematics"],
                    "source_refs": [{"source": "cso", "label": "Optimal Solution"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:surgery_plastic",
                    "canonical_en": "Surgery, Plastic",
                    "aliases_en": [],
                    "domains": ["biomedical", "analytical_diagnostic_and_therapeutic_techniques_and_equipment"],
                    "source_refs": [{"source": "mesh", "label": "Surgery, Plastic"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:cell_division"]["zh_alias_candidates"][0]["alias"], "细胞分裂")
        self.assertEqual(rows["concept:fractures_closed"]["zh_alias_candidates"][0]["alias"], "闭合性骨折")
        self.assertEqual(rows["concept:clinical_trial_phase_ii"]["zh_alias_candidates"][0]["alias"], "II期临床试验")
        self.assertEqual(rows["concept:optimal_solution"]["zh_alias_candidates"][0]["alias"], "最优解")
        self.assertEqual(rows["concept:surgery_plastic"]["zh_alias_candidates"][0]["alias"], "整形外科")

    def test_review_feedback_adds_common_standard_term_exact_aliases(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:zero_knowledge_proof",
                    "canonical_en": "Zero Knowledge Proof",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Zero Knowledge Proof"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:quadratic_programming",
                    "canonical_en": "Quadratic Programming",
                    "aliases_en": [],
                    "domains": ["mathematics"],
                    "source_refs": [{"source": "cso", "label": "Quadratic Programming"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:brownian_motion",
                    "canonical_en": "Brownian Motion",
                    "aliases_en": [],
                    "domains": ["physics"],
                    "source_refs": [{"source": "physh", "label": "Brownian Motion"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:lattice_boltzmann_method",
                    "canonical_en": "Lattice Boltzmann Method",
                    "aliases_en": [],
                    "domains": ["physics", "mathematics"],
                    "source_refs": [{"source": "cso", "label": "Lattice Boltzmann Method"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:cyclic_redundancy_check",
                    "canonical_en": "Cyclic Redundancy Check",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Cyclic Redundancy Check"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:zero_knowledge_proof"]["zh_alias_candidates"][0]["alias"], "零知识证明")
        self.assertEqual(rows["concept:quadratic_programming"]["zh_alias_candidates"][0]["alias"], "二次规划")
        self.assertEqual(rows["concept:brownian_motion"]["zh_alias_candidates"][0]["alias"], "布朗运动")
        self.assertEqual(rows["concept:lattice_boltzmann_method"]["zh_alias_candidates"][0]["alias"], "格子玻尔兹曼方法")
        self.assertEqual(rows["concept:cyclic_redundancy_check"]["zh_alias_candidates"][0]["alias"], "循环冗余校验")

    def test_review_feedback_adds_common_biomedical_exact_aliases(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:receptor_interleukin_7",
                    "canonical_en": "Receptor, Interleukin-7",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "mesh", "label": "Receptor, Interleukin-7"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:tooth_extraction",
                    "canonical_en": "Tooth Extraction",
                    "aliases_en": [],
                    "domains": ["biomedical", "analytical_diagnostic_and_therapeutic_techniques_and_equipment"],
                    "source_refs": [{"source": "mesh", "label": "Tooth Extraction"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:body_temperature",
                    "canonical_en": "Body Temperature",
                    "aliases_en": [],
                    "domains": ["biomedical", "phenomena_and_processes"],
                    "source_refs": [{"source": "mesh", "label": "Body Temperature"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:stroke_volume",
                    "canonical_en": "Stroke Volume",
                    "aliases_en": [],
                    "domains": ["biomedical", "phenomena_and_processes"],
                    "source_refs": [{"source": "mesh", "label": "Stroke Volume"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:airway_management",
                    "canonical_en": "Airway Management",
                    "aliases_en": [],
                    "domains": ["biomedical", "analytical_diagnostic_and_therapeutic_techniques_and_equipment"],
                    "source_refs": [{"source": "mesh", "label": "Airway Management"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:receptor_interleukin_7"]["zh_alias_candidates"][0]["alias"], "白细胞介素7受体")
        self.assertEqual(rows["concept:tooth_extraction"]["zh_alias_candidates"][0]["alias"], "拔牙")
        self.assertEqual(rows["concept:body_temperature"]["zh_alias_candidates"][0]["alias"], "体温")
        self.assertEqual(rows["concept:stroke_volume"]["zh_alias_candidates"][0]["alias"], "每搏量")
        self.assertEqual(rows["concept:airway_management"]["zh_alias_candidates"][0]["alias"], "气道管理")

    def test_review_feedback_corrects_domain_polysemy_and_mechanical_order(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:traffic_accident",
                    "canonical_en": "Accidents, Traffic",
                    "aliases_en": [],
                    "domains": ["biomedical", "health_care"],
                    "source_refs": [{"source": "mesh", "label": "Accidents, Traffic"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:air_traffic_control",
                    "canonical_en": "Air Traffic Control",
                    "aliases_en": [],
                    "domains": ["aerospace_and_electronic_systems"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Air Traffic Control"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:chromosome_human_13_15",
                    "canonical_en": "Chromosomes, Human, 13-15",
                    "aliases_en": [],
                    "domains": ["anatomy", "biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Chromosomes, Human, 13-15"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:computational_grid",
                    "canonical_en": "Computational Grid",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Computational Grid"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:grid_cell",
                    "canonical_en": "Grid Cells",
                    "aliases_en": [],
                    "domains": ["anatomy", "biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Grid Cells"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:cognitive_function_and_memory",
                    "canonical_en": "Cognitive Functions And Memory",
                    "aliases_en": [],
                    "domains": ["psychology", "social_sciences"],
                    "source_refs": [{"source": "openalex_topics", "label": "Cognitive Functions And Memory"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:traffic_accident"]["zh_alias_candidates"][0]["alias"], "交通事故")
        self.assertEqual(rows["concept:air_traffic_control"]["zh_alias_candidates"][0]["alias"], "空中交通管制")
        self.assertEqual(rows["concept:chromosome_human_13_15"]["zh_alias_candidates"][0]["alias"], "人类13-15号染色体")
        self.assertEqual(rows["concept:computational_grid"]["zh_alias_candidates"][0]["alias"], "计算网格")
        self.assertEqual(rows["concept:grid_cell"]["zh_alias_candidates"][0]["alias"], "网格细胞")
        self.assertEqual(rows["concept:cognitive_function_and_memory"]["zh_alias_candidates"][0]["alias"], "认知功能与记忆")


    def test_rule_level_cs_communications_polysemy_and_phrase_order(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:agent_oriented",
                    "canonical_en": "Agent-oriented",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Agent-oriented"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:aspect_oriented_programming",
                    "canonical_en": "Aspect Oriented Programming",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Aspect Oriented Programming"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:artificial_potential_field",
                    "canonical_en": "Artificial Potential Field",
                    "aliases_en": [],
                    "domains": ["computer_science", "robotics_and_automation"],
                    "source_refs": [{"source": "cso", "label": "Artificial Potential Field"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:attribute_weight",
                    "canonical_en": "Attribute Weight",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Attribute Weight"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:acoustic_surface_wave_filter",
                    "canonical_en": "Acoustic Surface Wave Filters",
                    "aliases_en": [],
                    "domains": ["computer_science", "signal_processing"],
                    "source_refs": [{"source": "cso", "label": "Acoustic Surface Wave Filters"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:audio_streaming",
                    "canonical_en": "Audio Streaming",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Audio Streaming"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:agent_oriented"]["zh_alias_candidates"][0]["alias"], "面向智能体的")
        self.assertEqual(rows["concept:aspect_oriented_programming"]["zh_alias_candidates"][0]["alias"], "面向方面的编程")
        self.assertEqual(rows["concept:artificial_potential_field"]["zh_alias_candidates"][0]["alias"], "人工势场")
        self.assertEqual(rows["concept:attribute_weight"]["zh_alias_candidates"][0]["alias"], "属性权重")
        self.assertEqual(rows["concept:acoustic_surface_wave_filter"]["zh_alias_candidates"][0]["alias"], "声表面波滤波器")
        self.assertEqual(rows["concept:audio_streaming"]["zh_alias_candidates"][0]["alias"], "音频流")


    def test_rule_level_optical_and_linear_standard_terms(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:optical_flow_algorithm",
                    "canonical_en": "Optical Flow Algorithm",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Optical Flow Algorithm"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:optical_cable",
                    "canonical_en": "Optical Cables",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Optical Cables"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:optical_communication_equipment",
                    "canonical_en": "Optical Communication Equipment",
                    "aliases_en": [],
                    "domains": ["communications_technology"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Optical Communication Equipment"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:optical_losses",
                    "canonical_en": "Optical Losses",
                    "aliases_en": [],
                    "domains": ["lasers_and_electrooptics"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Optical Losses"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:optical_harmonic_generation",
                    "canonical_en": "Optical Harmonic Generation",
                    "aliases_en": [],
                    "domains": ["lasers_and_electrooptics"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Optical Harmonic Generation"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:linear_system_of_equations",
                    "canonical_en": "Linear System Of Equations",
                    "aliases_en": [],
                    "domains": ["computer_science", "mathematics"],
                    "source_refs": [{"source": "cso", "label": "Linear System Of Equations"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:linear_time_delay_system",
                    "canonical_en": "Linear Time-delay System",
                    "aliases_en": [],
                    "domains": ["computer_science", "control_systems"],
                    "source_refs": [{"source": "cso", "label": "Linear Time-delay System"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:optical_flow_algorithm"]["zh_alias_candidates"][0]["alias"], "光流算法")
        self.assertEqual(rows["concept:optical_cable"]["zh_alias_candidates"][0]["alias"], "光缆")
        self.assertEqual(rows["concept:optical_communication_equipment"]["zh_alias_candidates"][0]["alias"], "光通信设备")
        self.assertEqual(rows["concept:optical_losses"]["zh_alias_candidates"][0]["alias"], "光损耗")
        self.assertEqual(rows["concept:optical_harmonic_generation"]["zh_alias_candidates"][0]["alias"], "光学谐波产生")
        self.assertEqual(rows["concept:linear_system_of_equations"]["zh_alias_candidates"][0]["alias"], "线性方程组")
        self.assertEqual(rows["concept:linear_time_delay_system"]["zh_alias_candidates"][0]["alias"], "线性时滞系统")

    def test_rule_level_network_and_system_standard_terms(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:network_induced_delay",
                    "canonical_en": "Network-induced Delay",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Network-induced Delay"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:network_on_chip_architectur",
                    "canonical_en": "Network-on-chip Architectures",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Network-on-chip Architectures"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:system_level_modeling",
                    "canonical_en": "System-level Modeling",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "System-level Modeling"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:system_on_a_chip",
                    "canonical_en": "System-on-a-chip",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "System-on-a-chip"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:network_induced_delay"]["zh_alias_candidates"][0]["alias"], "网络诱导时延")
        self.assertEqual(rows["concept:network_on_chip_architectur"]["zh_alias_candidates"][0]["alias"], "片上网络架构")
        self.assertEqual(rows["concept:system_level_modeling"]["zh_alias_candidates"][0]["alias"], "系统级建模")
        self.assertEqual(rows["concept:system_on_a_chip"]["zh_alias_candidates"][0]["alias"], "片上系统")

    def test_rule_level_video_parallel_and_automatic_polysemy_terms(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:video_on_demand",
                    "canonical_en": "Video On Demand",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Video On Demand"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:video_surveillance_application",
                    "canonical_en": "Video-surveillance Applications",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Video-surveillance Applications"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:distributed_parallel_and_cluster_computing",
                    "canonical_en": "Distributed, Parallel, And Cluster Computing",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Distributed, Parallel, And Cluster Computing"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:parallel_text",
                    "canonical_en": "Parallel Text",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Parallel Text"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:automatic_facial_expression_recognition",
                    "canonical_en": "Automatic Facial Expression Recognition",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Automatic Facial Expression Recognition"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:automatic_service_composition",
                    "canonical_en": "Automatic Service Composition",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Automatic Service Composition"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:video_streaming_servic",
                    "canonical_en": "Video Streaming Services",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Video Streaming Services"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:wireless_video_streaming",
                    "canonical_en": "Wireless Video Streaming",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Wireless Video Streaming"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:automatic_vehicle_identification",
                    "canonical_en": "Automatic Vehicle Identification",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Automatic Vehicle Identification"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:microscopy_video",
                    "canonical_en": "Microscopy, Video",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Microscopy, Video"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:automatic_transcription",
                    "canonical_en": "Automatic Transcription",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Automatic Transcription"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:video_on_demand"]["zh_alias_candidates"][0]["alias"], "视频点播")
        self.assertEqual(rows["concept:video_surveillance_application"]["zh_alias_candidates"][0]["alias"], "视频监控应用")
        self.assertEqual(
            rows["concept:distributed_parallel_and_cluster_computing"]["zh_alias_candidates"][0]["alias"],
            "分布式并行与集群计算",
        )
        self.assertEqual(rows["concept:parallel_text"]["zh_alias_candidates"][0]["alias"], "平行文本")
        self.assertEqual(
            rows["concept:automatic_facial_expression_recognition"]["zh_alias_candidates"][0]["alias"],
            "自动面部表情识别",
        )
        self.assertEqual(rows["concept:automatic_service_composition"]["zh_alias_candidates"][0]["alias"], "自动服务组合")
        self.assertEqual(rows["concept:video_streaming_servic"]["zh_alias_candidates"][0]["alias"], "视频流媒体服务")
        self.assertEqual(rows["concept:wireless_video_streaming"]["zh_alias_candidates"][0]["alias"], "无线视频流传输")
        self.assertEqual(rows["concept:automatic_vehicle_identification"]["zh_alias_candidates"][0]["alias"], "车辆自动识别")
        self.assertEqual(rows["concept:microscopy_video"]["zh_alias_candidates"][0]["alias"], "视频显微术")
        self.assertEqual(rows["concept:automatic_transcription"]["zh_alias_candidates"][0]["alias"], "自动转写")

    def test_rule_level_human_domain_polysemy_terms(self) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": "concept:human_body",
                    "canonical_en": "Human Body",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Human Body"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:human_action_recognition",
                    "canonical_en": "Human Action Recognition",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Human Action Recognition"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:human_facial_expression",
                    "canonical_en": "Human Facial Expressions",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Human Facial Expressions"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:human_genome_project",
                    "canonical_en": "Human Genome Project",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "source_refs": [{"source": "mesh", "label": "Human Genome Project"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:human_motion_tracking",
                    "canonical_en": "Human Motion Tracking",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Human Motion Tracking"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:human_resource_development_and_performance_evaluation",
                    "canonical_en": "Human Resource Development And Performance Evaluation",
                    "aliases_en": [],
                    "domains": ["social_sciences"],
                    "source_refs": [{"source": "openalex_topics", "label": "Human Resource Development And Performance Evaluation"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:human_resource_management",
                    "canonical_en": "Human Resource Management",
                    "aliases_en": [],
                    "domains": ["engineering_management"],
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Human Resource Management"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        self.assertEqual(rows["concept:human_body"]["zh_alias_candidates"][0]["alias"], "人体")
        self.assertEqual(rows["concept:human_action_recognition"]["zh_alias_candidates"][0]["alias"], "人体动作识别")
        self.assertEqual(rows["concept:human_facial_expression"]["zh_alias_candidates"][0]["alias"], "人类面部表情")
        self.assertEqual(rows["concept:human_genome_project"]["zh_alias_candidates"][0]["alias"], "人类基因组计划")
        self.assertEqual(rows["concept:human_motion_tracking"]["zh_alias_candidates"][0]["alias"], "人体运动跟踪")
        self.assertEqual(
            rows["concept:human_resource_development_and_performance_evaluation"]["zh_alias_candidates"][0]["alias"],
            "人力资源开发与绩效评估",
        )
        self.assertEqual(rows["concept:human_resource_management"]["zh_alias_candidates"][0]["alias"], "人力资源管理")

    def test_rule_level_dynamic_polysemy_terms(self) -> None:
        cases = [
            (
                "dynamic_background",
                "Dynamic Background",
                ["computer_science"],
                "动态背景",
            ),
            (
                "dynamic_bandwidth_allocation",
                "Dynamic Bandwidth Allocation",
                ["computer_science"],
                "动态带宽分配",
            ),
            (
                "dynamic_binary_translation",
                "Dynamic Binary Translation",
                ["computer_science"],
                "动态二进制翻译",
            ),
            (
                "dynamic_channel_assignment",
                "Dynamic Channel Assignment",
                ["computer_science"],
                "动态信道分配",
            ),
            (
                "dynamic_composition",
                "Dynamic Composition",
                ["computer_science"],
                "动态组合",
            ),
            (
                "dynamic_environment",
                "Dynamic Environment",
                ["computer_science"],
                "动态环境",
            ),
            (
                "dynamic_group",
                "Dynamic Groups",
                ["computer_science"],
                "动态群组",
            ),
            (
                "dynamic_load_balancing",
                "Dynamic Load Balancing",
                ["computer_science"],
                "动态负载均衡",
            ),
            (
                "dynamic_service_composition",
                "Dynamic Service Composition",
                ["computer_science"],
                "动态服务组合",
            ),
            (
                "dynamic_source_routing_protocol",
                "Dynamic Source Routing Protocol",
                ["computer_science"],
                "动态源路由协议",
            ),
            (
                "dynamic_spectrum_allocation",
                "Dynamic Spectrum Allocation",
                ["computer_science"],
                "动态频谱分配",
            ),
            (
                "dynamic_spectrum_sharing",
                "Dynamic Spectrum Sharing",
                ["computer_science"],
                "动态频谱共享",
            ),
            (
                "dynamic_program_analysis",
                "Dynamic Program Analysis",
                ["computer_science"],
                "动态程序分析",
            ),
            (
                "dynamic_software_architecture",
                "Dynamic Software Architecture",
                ["computer_science"],
                "动态软件架构",
            ),
            (
                "dynamic_output_feedback_controller",
                "Dynamic Output Feedback Controller",
                ["computer_science"],
                "动态输出反馈控制器",
            ),
            (
                "dynamic_optimization_problem",
                "Dynamic Optimization Problems",
                ["computer_science"],
                "动态优化问题",
            ),
            (
                "dynamic_logic",
                "Dynamic Logic",
                ["computer_science"],
                "动态逻辑",
            ),
            (
                "dynamic_language",
                "Dynamic Languages",
                ["computer_science"],
                "动态语言",
            ),
            (
                "dynamic_range",
                "Dynamic Range",
                ["instrumentation_and_measurement"],
                "动态范围",
            ),
            (
                "high_dynamic_range",
                "High Dynamic Range",
                ["instrumentation_and_measurement"],
                "高动态范围",
            ),
            (
                "dynamic_light_scattering",
                "Dynamic Light Scattering",
                ["biomedical", "analytical_diagnostic_and_therapeutic_techniques_and_equipment"],
                "动态光散射",
            ),
            (
                "dynamic_mechanical_analysis",
                "Dynamic Mechanical Analysis",
                ["engineering", "physical_sciences"],
                "动态力学分析",
            ),
            (
                "dynamic_response",
                "Dynamic Response",
                ["engineering_general"],
                "动态响应",
            ),
            (
                "dynamic_scheduling",
                "Dynamic Scheduling",
                ["engineering_management"],
                "动态调度",
            ),
            (
                "dynamic_traffic",
                "Dynamic Traffic",
                ["computer_science"],
                "动态流量",
            ),
            (
                "dynamic_walking",
                "Dynamic Walking",
                ["robotics_and_automation"],
                "动态行走",
            ),
            (
                "passive_dynamic_walking",
                "Passive Dynamic Walking",
                ["robotics_and_automation"],
                "被动动态行走",
            ),
            (
                "static_and_dynamic_analysis",
                "Static And Dynamic Analysis",
                ["computer_science"],
                "静态与动态分析",
            ),
            (
                "beam_dynamics",
                "Beam Dynamics",
                ["physics"],
                "波束动力学",
            ),
            (
                "complex_system_and_dynamic",
                "Complex Systems And Dynamics",
                ["physical_sciences", "physics_and_astronomy"],
                "复杂系统与动力学",
            ),
            (
                "chaotic_dynamics",
                "Chaotic Dynamics",
                ["nonlinear_sciences"],
                "混沌动力学",
            ),
            (
                "control_and_dynamic_of_mobile_robot",
                "Control And Dynamics Of Mobile Robots",
                ["engineering", "physical_sciences"],
                "移动机器人控制与动力学",
            ),
            (
                "dynamic_and_control_of_mechanical_system",
                "Dynamics And Control Of Mechanical Systems",
                ["engineering", "physical_sciences"],
                "机械系统动力学与控制",
            ),
            (
                "dynamic_of_network",
                "Dynamics Of Networks",
                ["physics"],
                "网络动力学",
            ),
            (
                "robotic_mechanism_and_dynamic",
                "Robotic Mechanisms And Dynamics",
                ["engineering", "physical_sciences"],
                "机器人机构与动力学",
            ),
            (
                "solar_and_space_plasma_dynamic",
                "Solar And Space Plasma Dynamics",
                ["physical_sciences", "physics_and_astronomy"],
                "太阳与空间等离子体动力学",
            ),
            (
                "structural_response_to_dynamic_load",
                "Structural Response To Dynamic Loads",
                ["engineering", "physical_sciences"],
                "结构对动力荷载的响应",
            ),
            (
                "thermodynamic_and_structural_property_of_metal_and_alloy",
                "Thermodynamic And Structural Properties Of Metals And Alloys",
                ["engineering", "physical_sciences"],
                "金属与合金的热力学和结构性质",
            ),
            (
                "vibration_and_dynamic_analysis",
                "Vibration And Dynamic Analysis",
                ["engineering", "physical_sciences"],
                "振动与动力分析",
            ),
            (
                "american_political_and_social_dynamic",
                "American Political And Social Dynamics",
                ["social_sciences"],
                "美国政治与社会动态",
            ),
            (
                "consumer_behavior_and_market_dynamic",
                "Consumer Behavior And Market Dynamics",
                ["social_sciences"],
                "消费者行为与市场动态",
            ),
            (
                "cultural_and_social_dynamic",
                "Cultural And Social Dynamics",
                ["social_sciences"],
                "文化与社会动态",
            ),
            (
                "food_security_and_socioeconomic_dynamic",
                "Food Security And Socioeconomic Dynamics",
                ["agricultural_and_biological_sciences", "life_sciences"],
                "粮食安全与社会经济动态",
            ),
            (
                "gender_labor_and_family_dynamic",
                "Gender, Labor, And Family Dynamics",
                ["social_sciences"],
                "性别、劳动与家庭动态",
            ),
            (
                "global_socioeconomic_and_political_dynamic",
                "Global Socioeconomic And Political Dynamics",
                ["economics_econometrics_and_finance", "social_sciences"],
                "全球社会经济与政治动态",
            ),
            (
                "global_political_and_social_dynamic",
                "Global Political And Social Dynamics",
                ["social_sciences"],
                "全球政治与社会动态",
            ),
            (
                "global_socioeconomic_and_cultural_dynamic",
                "Global Socioeconomic And Cultural Dynamics",
                ["social_sciences"],
                "全球社会经济与文化动态",
            ),
            (
                "global_urban_network_and_dynamic",
                "Global Urban Networks And Dynamics",
                ["social_sciences"],
                "全球城市网络与动态",
            ),
            (
                "group_dynamic",
                "Group Dynamics",
                ["biomedical", "psychiatry_and_psychology"],
                "群体动力学",
            ),
            (
                "migration_and_labor_dynamic",
                "Migration And Labor Dynamics",
                ["social_sciences"],
                "迁移与劳动动态",
            ),
            (
                "migration_education_indigenou_social_dynamic",
                "Migration, Education, Indigenous Social Dynamics",
                ["social_sciences"],
                "迁移、教育与原住民社会动态",
            ),
            (
                "plant_water_relation_and_carbon_dynamic",
                "Plant Water Relations And Carbon Dynamics",
                ["environmental_science", "physical_sciences"],
                "植物水分关系与碳动态",
            ),
            (
                "political_dynamic_in_latin_america",
                "Political Dynamics In Latin America",
                ["social_sciences"],
                "拉丁美洲政治动态",
            ),
            (
                "social_and_cultural_dynamic",
                "Social And Cultural Dynamics",
                ["social_sciences"],
                "社会与文化动态",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "cso", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_rule_level_source_specific_and_biomedical_word_order_terms(self) -> None:
        cases = [
            (
                "chemical_and_physical_property_of_material",
                "Chemical And Physical Properties Of Materials",
                ["materials_science", "physical_sciences"],
                "材料的化学与物理性质",
            ),
            (
                "electrical_and_thermal_property_of_material",
                "Electrical And Thermal Properties Of Materials",
                ["engineering", "physical_sciences"],
                "材料的电学与热学性质",
            ),
            (
                "electronic_and_structural_property_of_oxid",
                "Electronic And Structural Properties Of Oxides",
                ["materials_science", "physical_sciences"],
                "氧化物的电子与结构性质",
            ),
            (
                "synthesi_and_property_of_polymer",
                "Synthesis And Properties Of Polymers",
                ["materials_science", "physical_sciences"],
                "聚合物的合成与性质",
            ),
            (
                "cultural_and_social_study_in_latin_america",
                "Cultural And Social Studies In Latin America",
                ["arts_and_humanities", "social_sciences"],
                "拉丁美洲文化与社会研究",
            ),
            (
                "international_relation_in_latin_america",
                "International Relations In Latin America",
                ["social_sciences"],
                "拉丁美洲国际关系",
            ),
            (
                "social_issu_and_policy_in_latin_america",
                "Social Issues And Policies In Latin America",
                ["social_sciences"],
                "拉丁美洲社会问题与政策",
            ),
            (
                "joint_source_channel_coding",
                "Joint Source Channel Coding",
                ["computer_science"],
                "联合信源信道编码",
            ),
            (
                "abdominal_cavity",
                "Abdominal Cavity",
                ["anatomy", "biomedical"],
                "腹腔",
            ),
            (
                "abo_blood_group_system",
                "ABO Blood-group System",
                ["biomedical", "chemicals_and_drugs"],
                "ABO血型系统",
            ),
            (
                "chromosom_artificial",
                "Chromosomes, Artificial",
                ["anatomy", "biomedical"],
                "人工染色体",
            ),
            (
                "genome_fungal",
                "Genome, Fungal",
                ["biomedical", "phenomena_and_processes"],
                "真菌基因组",
            ),
            (
                "herpesviru_1_bovine",
                "Herpesvirus 1, Bovine",
                ["biomedical", "organisms"],
                "牛疱疹病毒1型",
            ),
            (
                "carcinoma_non_small_cell_lung",
                "Carcinoma, Non-small-cell Lung",
                ["biomedical", "diseases"],
                "非小细胞肺癌",
            ),
            (
                "cell_culture_techniqu",
                "Cell Culture Techniques",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "细胞培养技术",
            ),
            (
                "cardiovascular_condition_and_treatment",
                "Cardiovascular Conditions And Treatments",
                ["health_sciences", "medicine"],
                "心血管疾病与治疗",
            ),
            (
                "diagnostic_techniqu_cardiovascular",
                "Diagnostic Techniques, Cardiovascular",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "心血管诊断技术",
            ),
            (
                "heart_rate_and_cardiovascular_health",
                "Heart Rate And Cardiovascular Health",
                ["health_sciences", "medicine"],
                "心率与心血管健康",
            ),
            (
                "enzyme_structure_and_function",
                "Enzyme Structure And Function",
                ["materials_science", "physical_sciences"],
                "酶结构与功能",
            ),
            (
                "chemokine_receptor_and_signaling",
                "Chemokine Receptors And Signaling",
                ["health_sciences", "medicine"],
                "趋化因子受体与信号传导",
            ),
            (
                "acid_phosphatase",
                "Acid Phosphatase",
                ["biomedical", "chemicals_and_drugs"],
                "酸性磷酸酶",
            ),
            (
                "activated_protein_c_resistance",
                "Activated Protein C Resistance",
                ["biomedical", "diseases"],
                "活化蛋白C抵抗",
            ),
            (
                "acute_phase_reaction",
                "Acute-phase Reaction",
                ["biomedical", "diseases"],
                "急性期反应",
            ),
            (
                "b7_1_antigen",
                "B7-1 Antigen",
                ["biomedical", "chemicals_and_drugs"],
                "B7-1抗原",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_001_standard_biomedical_and_engineering_terms(self) -> None:
        cases = [
            (
                "blood_alcohol_content",
                "Blood Alcohol Content",
                ["biomedical", "chemicals_and_drugs"],
                "血液酒精浓度",
            ),
            (
                "blood_culture",
                "Blood Culture",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "血培养",
            ),
            (
                "blood_glucose",
                "Blood Glucose",
                ["biomedical", "chemicals_and_drugs"],
                "血糖",
            ),
            (
                "blood_group_antigen",
                "Blood Group Antigens",
                ["biomedical", "chemicals_and_drugs"],
                "血型抗原",
            ),
            (
                "blood_pressure",
                "Blood Pressure",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "血压",
            ),
            (
                "body_fluid",
                "Body Fluids",
                ["anatomy", "biomedical"],
                "体液",
            ),
            (
                "body_surface_area",
                "Body Surface Area",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "体表面积",
            ),
            (
                "body_water",
                "Body Water",
                ["anatomy", "biomedical"],
                "体水分",
            ),
            (
                "body_weight",
                "Body Weight",
                ["biomedical", "diseases"],
                "体重",
            ),
            (
                "bone_development",
                "Bone Development",
                ["biomedical", "phenomena_and_processes"],
                "骨发育",
            ),
            (
                "bone_diseases_infectious",
                "Bone Diseases, Infectious",
                ["biomedical", "diseases"],
                "感染性骨病",
            ),
            (
                "bone_diseases_metabolic",
                "Bone Diseases, Metabolic",
                ["biomedical", "diseases"],
                "代谢性骨病",
            ),
            (
                "cell_line",
                "Cell Line",
                ["anatomy", "biomedical"],
                "细胞系",
            ),
            (
                "cell_line_tumor",
                "Cell Line, Tumor",
                ["anatomy", "biomedical"],
                "肿瘤细胞系",
            ),
            (
                "cell_culture_techniques_three_dimensional",
                "Cell Culture Techniques, Three Dimensional",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "三维细胞培养技术",
            ),
            (
                "calcium_channel",
                "Calcium Channels",
                ["biomedical", "chemicals_and_drugs"],
                "钙通道",
            ),
            (
                "potassium_channel",
                "Potassium Channels",
                ["biomedical", "chemicals_and_drugs"],
                "钾通道",
            ),
            (
                "potassium_channels_calcium_activated",
                "Potassium Channels, Calcium-activated",
                ["biomedical", "chemicals_and_drugs"],
                "钙激活钾通道",
            ),
            (
                "potassium_channels_sodium_activated",
                "Potassium Channels, Sodium-activated",
                ["biomedical", "chemicals_and_drugs"],
                "钠激活钾通道",
            ),
            (
                "liver_function_tests",
                "Liver Function Tests",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "肝功能检查",
            ),
            (
                "respiratory_function_tests",
                "Respiratory Function Tests",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "呼吸功能检查",
            ),
            (
                "acoustic_material",
                "Acoustic Materials",
                ["materials_elements_and_compounds"],
                "声学材料",
            ),
            (
                "acoustic_propagation",
                "Acoustic Propagation",
                ["science_general"],
                "声传播",
            ),
            (
                "acoustical_engineering",
                "Acoustical Engineering",
                ["engineering_general"],
                "声学工程",
            ),
            (
                "aerospace_electronic",
                "Aerospace Electronics",
                ["aerospace_and_electronic_systems"],
                "航空航天电子学",
            ),
            (
                "aerospace_medicine",
                "Aerospace Medicine",
                ["biomedical", "disciplines_and_occupations"],
                "航空航天医学",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_006_continues_high_confidence_standard_terms(self) -> None:
        cases = [
            (
                "saccades",
                "Saccades",
                ["biomedical", "phenomena_and_processes"],
                "扫视",
            ),
            (
                "saliency_detection",
                "Saliency Detection",
                ["computers_and_information_processing"],
                "显著性检测",
            ),
            (
                "zero_shot_learning",
                "Zero-shot Learning",
                ["computer_science"],
                "零样本学习",
            ),
            (
                "zika_virus",
                "Zika Virus",
                ["biomedical", "organisms"],
                "寨卡病毒",
            ),
            (
                "high_energy_shock_waves",
                "High-energy Shock Waves",
                ["biomedical", "phenomena_and_processes"],
                "高能冲击波",
            ),
            (
                "mass_vaccination",
                "Mass Vaccination",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "大规模疫苗接种",
            ),
            (
                "receptors_serotonin",
                "Receptors, Serotonin",
                ["biomedical", "chemicals_and_drugs"],
                "5-羟色胺受体",
            ),
            (
                "shock_waves",
                "Shock Waves",
                ["science_general"],
                "冲击波",
            ),
            (
                "sodium_salicylate",
                "Sodium Salicylate",
                ["biomedical", "chemicals_and_drugs"],
                "水杨酸钠",
            ),
            (
                "traumatic_subarachnoid_hemorrhage",
                "Subarachnoid Hemorrhage, Traumatic",
                ["biomedical", "diseases"],
                "创伤性蛛网膜下腔出血",
            ),
            (
                "sinus_tachycardia",
                "Tachycardia, Sinus",
                ["biomedical", "diseases"],
                "窦性心动过速",
            ),
            (
                "ventricular_tachycardia",
                "Tachycardia, Ventricular",
                ["biomedical", "diseases"],
                "室性心动过速",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_007_continues_domain_aware_biomedical_terms(self) -> None:
        cases = [
            (
                "angina_stable",
                "Angina, Stable",
                ["biomedical", "diseases"],
                "稳定型心绞痛",
            ),
            (
                "aortic_valve_stenosis",
                "Aortic Valve Stenosis",
                ["biomedical", "diseases"],
                "主动脉瓣狭窄",
            ),
            (
                "coronary_artery_bypass",
                "Coronary Artery Bypass",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "冠状动脉旁路移植术",
            ),
            (
                "dna_mitochondrial",
                "DNA, Mitochondrial",
                ["biomedical", "chemicals_and_drugs"],
                "线粒体DNA",
            ),
            (
                "mitochondrial_disease",
                "Mitochondrial Diseases",
                ["biomedical", "diseases"],
                "线粒体疾病",
            ),
            (
                "chemokine_ccl2",
                "Chemokine CCL2",
                ["biomedical", "chemicals_and_drugs"],
                "趋化因子CCL2",
            ),
            (
                "meningioma",
                "Meningioma",
                ["biomedical", "diseases"],
                "脑膜瘤",
            ),
            (
                "mart_1_antigen",
                "MART-1 Antigen",
                ["biomedical", "chemicals_and_drugs"],
                "MART-1抗原",
            ),
            (
                "axon_guidance",
                "Axon Guidance",
                ["biomedical", "phenomena_and_processes"],
                "轴突导向",
            ),
            (
                "cell_adhesion_molecules_neuronal",
                "Cell Adhesion Molecules, Neuronal",
                ["biomedical", "chemicals_and_drugs"],
                "神经元细胞黏附分子",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_008_continues_biomedical_a_terms(self) -> None:
        cases = [
            (
                "abducens_nerve",
                "Abducens Nerve",
                ["anatomy", "biomedical"],
                "外展神经",
            ),
            (
                "acetyl_coenzyme_a",
                "Acetyl Coenzyme A",
                ["biomedical", "chemicals_and_drugs"],
                "乙酰辅酶A",
            ),
            (
                "acquired_immunodeficiency_syndrome",
                "Acquired Immunodeficiency Syndrome",
                ["biomedical", "diseases"],
                "获得性免疫缺陷综合征",
            ),
            (
                "adenocarcinoma",
                "Adenocarcinoma",
                ["biomedical", "diseases"],
                "腺癌",
            ),
            (
                "adrenocorticotropic_hormone",
                "Adrenocorticotropic Hormone",
                ["biomedical", "chemicals_and_drugs"],
                "促肾上腺皮质激素",
            ),
            (
                "amyotrophic_lateral_sclerosis",
                "Amyotrophic Lateral Sclerosis",
                ["biomedical", "diseases"],
                "肌萎缩侧索硬化",
            ),
            (
                "angiotensin_converting_enzyme_2",
                "Angiotensin-Converting Enzyme 2",
                ["biomedical", "chemicals_and_drugs"],
                "血管紧张素转换酶2",
            ),
            (
                "antigen_presentation",
                "Antigen Presentation",
                ["biomedical", "phenomena_and_processes"],
                "抗原呈递",
            ),
            (
                "anti_n_methyl_d_aspartate_receptor_encephalitis",
                "Anti-N-Methyl-D-Aspartate Receptor Encephalitis",
                ["biomedical", "diseases"],
                "抗N-甲基-D-天冬氨酸受体脑炎",
            ),
            (
                "angelman_syndrome",
                "Angelman Syndrome",
                ["biomedical", "diseases"],
                "Angelman综合征",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_009_continues_cs_and_signal_terms(self) -> None:
        cases = [
            (
                "adaptive_neuro_fuzzy_inference_system",
                "Adaptive Neuro-Fuzzy Inference System",
                ["computer_science"],
                "自适应神经模糊推理系统",
            ),
            (
                "admission_control",
                "Admission Control",
                ["communications_technology", "computer_science"],
                "准入控制",
            ),
            (
                "admittance_control",
                "Admittance Control",
                ["control_systems"],
                "导纳控制",
            ),
            (
                "aes_encryption",
                "AES Encryption",
                ["computer_science"],
                "AES加密",
            ),
            (
                "affine_projection_algorithm",
                "Affine Projection Algorithm",
                ["computer_science"],
                "仿射投影算法",
            ),
            (
                "all_optical_signal_processing",
                "All-Optical Signal Processing",
                ["computer_science"],
                "全光信号处理",
            ),
            (
                "answer_set_semantics",
                "Answer Set Semantics",
                ["computer_science"],
                "答案集语义",
            ),
            (
                "anycast_routing",
                "Anycast Routing",
                ["computer_science"],
                "任播路由",
            ),
            (
                "cache_coherence_protocol",
                "Cache Coherence Protocol",
                ["computer_science"],
                "缓存一致性协议",
            ),
            (
                "canny_edge_detection",
                "Canny Edge Detection",
                ["computer_science"],
                "Canny边缘检测",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_010_continues_remaining_biomedical_terms(self) -> None:
        cases = [
            (
                "antiphospholipid_syndrome",
                "Antiphospholipid Syndrome",
                ["biomedical", "diseases"],
                "抗磷脂综合征",
            ),
            (
                "antithrombin_iii_deficiency",
                "Antithrombin III Deficiency",
                ["biomedical", "diseases"],
                "抗凝血酶III缺乏症",
            ),
            (
                "atypical_hemolytic_uremic_syndrome",
                "Atypical Hemolytic Uremic Syndrome",
                ["biomedical", "diseases"],
                "非典型溶血尿毒综合征",
            ),
            (
                "autoimmune_inner_ear_disease",
                "Autoimmune Inner Ear Disease",
                ["biomedical", "diseases"],
                "自身免疫性内耳病",
            ),
            (
                "autoimmune_lymphoproliferative_syndrome",
                "Autoimmune Lymphoproliferative Syndrome",
                ["biomedical", "diseases"],
                "自身免疫性淋巴增殖综合征",
            ),
            (
                "axl_receptor_tyrosine_kinase",
                "Axl Receptor Tyrosine Kinase",
                ["biomedical", "chemicals_and_drugs"],
                "Axl受体酪氨酸激酶",
            ),
            (
                "aurora_kinase_a",
                "Aurora Kinase A",
                ["biomedical", "chemicals_and_drugs"],
                "Aurora激酶A",
            ),
            (
                "aurora_kinase_b",
                "Aurora Kinase B",
                ["biomedical", "chemicals_and_drugs"],
                "Aurora激酶B",
            ),
            (
                "aurora_kinase_c",
                "Aurora Kinase C",
                ["biomedical", "chemicals_and_drugs"],
                "Aurora激酶C",
            ),
            (
                "b_cell_maturation_antigen",
                "B-Cell Maturation Antigen",
                ["biomedical", "chemicals_and_drugs"],
                "B细胞成熟抗原",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_011_adds_bacterial_and_basal_terms(self) -> None:
        cases = [
            (
                "bacterial_adhesion",
                "Bacterial Adhesion",
                ["biomedical", "phenomena_and_processes"],
                "细菌黏附",
            ),
            (
                "bacterial_outer_membrane",
                "Bacterial Outer Membrane",
                ["anatomy", "biomedical"],
                "细菌外膜",
            ),
            (
                "bacterial_translocation",
                "Bacterial Translocation",
                ["biomedical", "phenomena_and_processes"],
                "细菌易位",
            ),
            (
                "bartonella_infections",
                "Bartonella Infections",
                ["biomedical", "diseases"],
                "巴尔通体感染",
            ),
            (
                "basal_cell_carcinoma",
                "Basal Cell Carcinoma",
                ["biomedical", "diseases"],
                "基底细胞癌",
            ),
            (
                "basal_forebrain",
                "Basal Forebrain",
                ["anatomy", "biomedical"],
                "基底前脑",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_012_adds_b_syndrome_protein_and_tumor_terms(self) -> None:
        cases = [
            (
                "behcet_syndrome",
                "Behcet Syndrome",
                ["biomedical", "diseases"],
                "白塞综合征",
            ),
            (
                "bence_jones_protein",
                "Bence Jones Protein",
                ["biomedical", "chemicals_and_drugs"],
                "本周蛋白",
            ),
            (
                "beta_glucosidase",
                "beta-Glucosidase",
                ["biomedical", "chemicals_and_drugs"],
                "β-葡萄糖苷酶",
            ),
            (
                "bile_duct_neoplasms",
                "Bile Duct Neoplasms",
                ["biomedical", "diseases"],
                "胆管肿瘤",
            ),
            (
                "biotinidase_deficiency",
                "Biotinidase Deficiency",
                ["biomedical", "diseases"],
                "生物素酶缺乏症",
            ),
            (
                "blood_brain_barrier",
                "Blood-Brain Barrier",
                ["anatomy", "biomedical"],
                "血脑屏障",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_013_adds_blood_and_bone_terms(self) -> None:
        cases = [
            (
                "blood_cell_count",
                "Blood Cell Count",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "血细胞计数",
            ),
            (
                "blood_coagulation_disorders_inherited",
                "Blood Coagulation Disorders, Inherited",
                ["biomedical", "diseases"],
                "遗传性凝血障碍",
            ),
            (
                "blood_retinal_barrier",
                "Blood-Retinal Barrier",
                ["anatomy", "biomedical"],
                "血视网膜屏障",
            ),
            (
                "blood_urea_nitrogen",
                "Blood Urea Nitrogen",
                ["biomedical", "chemicals_and_drugs"],
                "血尿素氮",
            ),
            (
                "bone_marrow_transplantation",
                "Bone Marrow Transplantation",
                ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                "骨髓移植",
            ),
            (
                "bone_resorption",
                "Bone Resorption",
                ["biomedical", "phenomena_and_processes"],
                "骨吸收",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_014_adds_cardio_celiac_and_cell_terms(self) -> None:
        cases = [
            (
                "cardio_renal_syndrome",
                "Cardio-Renal Syndrome",
                ["biomedical", "diseases"],
                "心肾综合征",
            ),
            (
                "cardiovascular_diseases",
                "Cardiovascular Diseases",
                ["biomedical", "diseases"],
                "心血管疾病",
            ),
            (
                "carpal_tunnel_syndrome",
                "Carpal Tunnel Syndrome",
                ["biomedical", "diseases"],
                "腕管综合征",
            ),
            (
                "cat_scratch_disease",
                "Cat-Scratch Disease",
                ["biomedical", "diseases"],
                "猫抓病",
            ),
            (
                "celiac_disease",
                "Celiac Disease",
                ["biomedical", "diseases"],
                "乳糜泻",
            ),
            (
                "cellular_senescence",
                "Cellular Senescence",
                ["biomedical", "phenomena_and_processes"],
                "细胞衰老",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_015_adds_cns_cerebral_and_infection_terms(self) -> None:
        cases = [
            (
                "central_cord_syndrome",
                "Central Cord Syndrome",
                ["biomedical", "diseases"],
                "中央脊髓综合征",
            ),
            (
                "cerebral_small_vessel_diseases",
                "Cerebral Small Vessel Diseases",
                ["biomedical", "diseases"],
                "脑小血管病",
            ),
            (
                "chagas_disease",
                "Chagas Disease",
                ["biomedical", "diseases"],
                "恰加斯病",
            ),
            (
                "charcot_marie_tooth_disease",
                "Charcot-Marie-Tooth Disease",
                ["biomedical", "diseases"],
                "腓骨肌萎缩症",
            ),
            (
                "chemokine_receptor_d6",
                "Chemokine Receptor D6",
                ["biomedical", "chemicals_and_drugs"],
                "趋化因子受体D6",
            ),
            (
                "chlamydia_infections",
                "Chlamydia Infections",
                ["biomedical", "diseases"],
                "衣原体感染",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_016_adds_blood_brain_and_bone_terms(self) -> None:
        cases = [
            (
                "blood_air_barrier",
                "Blood-Air Barrier",
                ["anatomy", "biomedical"],
                "血气屏障",
            ),
            (
                "blood_nerve_barrier",
                "Blood-Nerve Barrier",
                ["anatomy", "biomedical"],
                "血神经屏障",
            ),
            (
                "brain_abscess",
                "Brain Abscess",
                ["biomedical", "diseases"],
                "脑脓肿",
            ),
            (
                "brain_derived_neurotrophic_factor",
                "Brain-Derived Neurotrophic Factor",
                ["biomedical", "chemicals_and_drugs"],
                "脑源性神经营养因子",
            ),
            (
                "brain_edema",
                "Brain Edema",
                ["biomedical", "diseases"],
                "脑水肿",
            ),
            (
                "bone_morphogenetic_protein_2",
                "Bone Morphogenetic Protein 2",
                ["biomedical", "chemicals_and_drugs"],
                "骨形态发生蛋白2",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_017_adds_b_disease_infection_and_virus_terms(self) -> None:
        cases = [
            (
                "bovine_virus_diarrhea_mucosal_disease",
                "Bovine Virus Diarrhea-Mucosal Disease",
                ["biomedical", "diseases"],
                "牛病毒性腹泻-黏膜病",
            ),
            (
                "breast_neoplasms",
                "Breast Neoplasms",
                ["biomedical", "diseases"],
                "乳腺肿瘤",
            ),
            (
                "brucellosis",
                "Brucellosis",
                ["biomedical", "diseases"],
                "布鲁氏菌病",
            ),
            (
                "brugada_syndrome",
                "Brugada Syndrome",
                ["biomedical", "diseases"],
                "Brugada综合征",
            ),
            (
                "budd_chiari_syndrome",
                "Budd-Chiari Syndrome",
                ["biomedical", "diseases"],
                "Budd-Chiari综合征",
            ),
            (
                "burkitt_lymphoma",
                "Burkitt Lymphoma",
                ["biomedical", "diseases"],
                "伯基特淋巴瘤",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_018_adds_c_antigen_protein_and_kinase_terms(self) -> None:
        cases = [
            (
                "c_reactive_protein",
                "C-Reactive Protein",
                ["biomedical", "chemicals_and_drugs"],
                "C反应蛋白",
            ),
            (
                "ca_125_antigen",
                "CA-125 Antigen",
                ["biomedical", "chemicals_and_drugs"],
                "CA-125抗原",
            ),
            (
                "ca_19_9_antigen",
                "CA-19-9 Antigen",
                ["biomedical", "chemicals_and_drugs"],
                "CA-19-9抗原",
            ),
            (
                "calcium_binding_proteins",
                "Calcium-Binding Proteins",
                ["biomedical", "chemicals_and_drugs"],
                "钙结合蛋白",
            ),
            (
                "calcium_calmodulin_dependent_protein_kinases",
                "Calcium-Calmodulin-Dependent Protein Kinases",
                ["biomedical", "chemicals_and_drugs"],
                "钙调蛋白依赖性蛋白激酶",
            ),
            (
                "cancer_vaccines",
                "Cancer Vaccines",
                ["biomedical", "chemicals_and_drugs"],
                "癌症疫苗",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_019_adds_carcinoma_and_cardiac_terms(self) -> None:
        cases = [
            (
                "carcinoembryonic_antigen",
                "Carcinoembryonic Antigen",
                ["biomedical", "chemicals_and_drugs"],
                "癌胚抗原",
            ),
            (
                "carcinoma_adenoid_cystic",
                "Carcinoma, Adenoid Cystic",
                ["biomedical", "diseases"],
                "腺样囊性癌",
            ),
            (
                "carcinoma_in_situ",
                "Carcinoma in Situ",
                ["biomedical", "diseases"],
                "原位癌",
            ),
            (
                "carcinoma_small_cell",
                "Carcinoma, Small Cell",
                ["biomedical", "diseases"],
                "小细胞癌",
            ),
            (
                "carcinoma_squamous_cell",
                "Carcinoma, Squamous Cell",
                ["biomedical", "diseases"],
                "鳞状细胞癌",
            ),
            (
                "cardiac_tamponade",
                "Cardiac Tamponade",
                ["biomedical", "diseases"],
                "心脏压塞",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_020_adds_cell_cholesterol_and_chronic_disease_terms(self) -> None:
        cases = [
            (
                "cartilage_oligomeric_matrix_protein",
                "Cartilage Oligomeric Matrix Protein",
                ["biomedical", "chemicals_and_drugs"],
                "软骨寡聚基质蛋白",
            ),
            (
                "casein_kinase_ii",
                "Casein Kinase II",
                ["biomedical", "chemicals_and_drugs"],
                "酪蛋白激酶II",
            ),
            (
                "ccaat_enhancer_binding_proteins",
                "CCAAT-Enhancer-Binding Proteins",
                ["biomedical", "chemicals_and_drugs"],
                "CCAAT/增强子结合蛋白",
            ),
            (
                "chitinase_3_like_protein_1",
                "Chitinase-3-Like Protein 1",
                ["biomedical", "chemicals_and_drugs"],
                "几丁质酶3样蛋白1",
            ),
            (
                "cholesterol_ester_transfer_proteins",
                "Cholesterol Ester Transfer Proteins",
                ["biomedical", "chemicals_and_drugs"],
                "胆固醇酯转运蛋白",
            ),
            (
                "chronic_kidney_disease_mineral_and_bone_disorder",
                "Chronic Kidney Disease-Mineral and Bone Disorder",
                ["biomedical", "diseases"],
                "慢性肾脏病-矿物质和骨异常",
            ),
        ]
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def assert_exact_alias_cases(self, cases: list[tuple[str, str, list[str], str]]) -> None:
        write_jsonl(
            self.batch,
            [
                {
                    "concept_id": f"concept:{concept_id}",
                    "canonical_en": canonical_en,
                    "aliases_en": [],
                    "domains": domains,
                    "source_refs": [{"source": "openalex_topics", "label": canonical_en}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                }
                for concept_id, canonical_en, domains, _alias in cases
            ],
        )

        module = load_module()
        module.fill_zh_alias_candidates(candidate_dir=self.candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(self.batch)}
        for concept_id, _canonical_en, _domains, alias in cases:
            self.assertEqual(rows[f"concept:{concept_id}"]["zh_alias_candidates"][0]["alias"], alias)

    def test_exact_expansion_batch_021_adds_complement_colonic_and_community_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "complement_c1_inactivator_protein",
                    "Complement C1 Inactivator Proteins",
                    ["biomedical", "chemicals_and_drugs"],
                    "补体C1抑制蛋白",
                ),
                (
                    "complement_factor_h",
                    "Complement Factor H",
                    ["biomedical", "chemicals_and_drugs"],
                    "补体因子H",
                ),
                (
                    "complement_system_proteins",
                    "Complement System Proteins",
                    ["biomedical", "chemicals_and_drugs"],
                    "补体系统蛋白",
                ),
                (
                    "colonic_neoplasms",
                    "Colonic Neoplasms",
                    ["biomedical", "diseases"],
                    "结肠肿瘤",
                ),
                (
                    "colorectal_neoplasms",
                    "Colorectal Neoplasms",
                    ["biomedical", "diseases"],
                    "结直肠肿瘤",
                ),
                (
                    "community_acquired_infections",
                    "Community-Acquired Infections",
                    ["biomedical", "diseases"],
                    "社区获得性感染",
                ),
            ]
        )

    def test_exact_expansion_batch_022_adds_connective_corneal_and_cord_blood_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "connective_tissue_diseases",
                    "Connective Tissue Diseases",
                    ["biomedical", "diseases"],
                    "结缔组织病",
                ),
                (
                    "connective_tissue_growth_factor",
                    "Connective Tissue Growth Factor",
                    ["biomedical", "chemicals_and_drugs"],
                    "结缔组织生长因子",
                ),
                (
                    "corneal_diseases",
                    "Corneal Diseases",
                    ["biomedical", "diseases"],
                    "角膜疾病",
                ),
                (
                    "corneal_endothelial_cell_loss",
                    "Corneal Endothelial Cell Loss",
                    ["biomedical", "diseases"],
                    "角膜内皮细胞丢失",
                ),
                (
                    "cord_blood_stem_cell_transplantation",
                    "Cord Blood Stem Cell Transplantation",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "脐血干细胞移植",
                ),
                (
                    "copper_transport_proteins",
                    "Copper Transport Proteins",
                    ["biomedical", "chemicals_and_drugs"],
                    "铜转运蛋白",
                ),
                (
                    "coronavirus_229e_human",
                    "Coronavirus 229E, Human",
                    ["biomedical", "organisms"],
                    "人冠状病毒229E",
                ),
                (
                    "coronavirus_bovine",
                    "Coronavirus, Bovine",
                    ["biomedical", "organisms"],
                    "牛冠状病毒",
                ),
                (
                    "receptor_coronavirus",
                    "Receptors, Coronavirus",
                    ["biomedical", "chemicals_and_drugs"],
                    "冠状病毒受体",
                ),
            ]
        )

    def test_exact_expansion_batch_023_adds_cyclic_nucleotide_and_cdk_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "cyclic_amp_dependent_protein_kinase_type_i",
                    "Cyclic AMP-Dependent Protein Kinase Type I",
                    ["biomedical", "chemicals_and_drugs"],
                    "I型cAMP依赖性蛋白激酶",
                ),
                (
                    "cyclic_amp_response_element_binding_protein",
                    "Cyclic AMP Response Element-Binding Protein",
                    ["biomedical", "chemicals_and_drugs"],
                    "cAMP反应元件结合蛋白",
                ),
                (
                    "cyclic_gmp_dependent_protein_kinases",
                    "Cyclic GMP-Dependent Protein Kinases",
                    ["biomedical", "chemicals_and_drugs"],
                    "cGMP依赖性蛋白激酶",
                ),
                (
                    "cyclin_dependent_kinases",
                    "Cyclin-Dependent Kinases",
                    ["biomedical", "chemicals_and_drugs"],
                    "细胞周期蛋白依赖性激酶",
                ),
                (
                    "cyclin_dependent_kinase_2",
                    "Cyclin-Dependent Kinase 2",
                    ["biomedical", "chemicals_and_drugs"],
                    "细胞周期蛋白依赖性激酶2",
                ),
                (
                    "cyclin_dependent_kinase_activating_kinase",
                    "Cyclin-Dependent Kinase-Activating Kinase",
                    ["biomedical", "chemicals_and_drugs"],
                    "细胞周期蛋白依赖性激酶激活激酶",
                ),
            ]
        )

    def test_exact_expansion_batch_024_adds_cdk_inhibitor_and_cystadenocarcinoma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "cyclin_dependent_kinase_inhibitor_p16",
                    "Cyclin-Dependent Kinase Inhibitor p16",
                    ["biomedical", "chemicals_and_drugs"],
                    "细胞周期蛋白依赖性激酶抑制剂p16",
                ),
                (
                    "cyclin_dependent_kinase_inhibitor_p21",
                    "Cyclin-Dependent Kinase Inhibitor p21",
                    ["biomedical", "chemicals_and_drugs"],
                    "细胞周期蛋白依赖性激酶抑制剂p21",
                ),
                (
                    "cystadenocarcinoma",
                    "Cystadenocarcinoma",
                    ["biomedical", "diseases"],
                    "囊腺癌",
                ),
                (
                    "cystadenocarcinoma_mucinous",
                    "Cystadenocarcinoma, Mucinous",
                    ["biomedical", "diseases"],
                    "黏液性囊腺癌",
                ),
                (
                    "cystadenocarcinoma_papillary",
                    "Cystadenocarcinoma, Papillary",
                    ["biomedical", "diseases"],
                    "乳头状囊腺癌",
                ),
                (
                    "cystadenocarcinoma_serous",
                    "Cystadenocarcinoma, Serous",
                    ["biomedical", "diseases"],
                    "浆液性囊腺癌",
                ),
            ]
        )

    def test_exact_expansion_batch_025_adds_cytochrome_cytokine_and_cmv_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "cytochrome_p_450_enzyme_inhibitors",
                    "Cytochrome P-450 Enzyme Inhibitors",
                    ["biomedical", "chemicals_and_drugs"],
                    "细胞色素P450酶抑制剂",
                ),
                (
                    "cytokine_induced_killer_cells",
                    "Cytokine-Induced Killer Cells",
                    ["anatomy", "biomedical"],
                    "细胞因子诱导的杀伤细胞",
                ),
                (
                    "cytokine_release_syndrome",
                    "Cytokine Release Syndrome",
                    ["biomedical", "diseases"],
                    "细胞因子释放综合征",
                ),
                (
                    "cytomegalovirus",
                    "Cytomegalovirus",
                    ["biomedical", "organisms"],
                    "巨细胞病毒",
                ),
                (
                    "cytomegalovirus_infections",
                    "Cytomegalovirus Infections",
                    ["biomedical", "diseases"],
                    "巨细胞病毒感染",
                ),
                (
                    "cytoskeletal_proteins",
                    "Cytoskeletal Proteins",
                    ["biomedical", "chemicals_and_drugs"],
                    "细胞骨架蛋白",
                ),
            ]
        )

    def test_exact_expansion_batch_026_adds_early_d_syndrome_and_death_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "dandy_walker_syndrome",
                    "Dandy-Walker Syndrome",
                    ["biomedical", "diseases"],
                    "Dandy-Walker综合征",
                ),
                (
                    "darier_disease",
                    "Darier Disease",
                    ["biomedical", "diseases"],
                    "Darier病",
                ),
                (
                    "dax_1_orphan_nuclear_receptor",
                    "DAX-1 Orphan Nuclear Receptor",
                    ["biomedical", "chemicals_and_drugs"],
                    "DAX-1孤儿核受体",
                ),
                (
                    "de_lange_syndrome",
                    "De Lange Syndrome",
                    ["biomedical", "diseases"],
                    "De Lange综合征",
                ),
                (
                    "de_quervain_disease",
                    "De Quervain Disease",
                    ["biomedical", "diseases"],
                    "De Quervain病",
                ),
                (
                    "death_associated_protein_kinases",
                    "Death-Associated Protein Kinases",
                    ["biomedical", "chemicals_and_drugs"],
                    "死亡相关蛋白激酶",
                ),
            ]
        )

    def test_exact_expansion_batch_027_adds_delta_dendritic_and_dengue_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "deltaretrovirus_infections",
                    "Deltaretrovirus Infections",
                    ["biomedical", "diseases"],
                    "δ逆转录病毒感染",
                ),
                (
                    "demyelinating_autoimmune_diseases_cns",
                    "Demyelinating Autoimmune Diseases, CNS",
                    ["biomedical", "diseases"],
                    "中枢神经系统脱髓鞘性自身免疫病",
                ),
                (
                    "dendritic_cells",
                    "Dendritic Cells",
                    ["anatomy", "biomedical"],
                    "树突状细胞",
                ),
                (
                    "dendritic_cells_follicular",
                    "Dendritic Cells, Follicular",
                    ["anatomy", "biomedical"],
                    "滤泡树突状细胞",
                ),
                (
                    "dengue_vaccines",
                    "Dengue Vaccines",
                    ["biomedical", "chemicals_and_drugs"],
                    "登革热疫苗",
                ),
                (
                    "dengue_virus",
                    "Dengue Virus",
                    ["biomedical", "organisms"],
                    "登革病毒",
                ),
            ]
        )

    def test_exact_expansion_batch_028_adds_diabetes_digestive_and_diphtheria_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "diabetes_insipidus",
                    "Diabetes Insipidus",
                    ["biomedical", "diseases"],
                    "尿崩症",
                ),
                (
                    "diabetes_insipidus_nephrogenic",
                    "Diabetes Insipidus, Nephrogenic",
                    ["biomedical", "diseases"],
                    "肾性尿崩症",
                ),
                (
                    "digeorge_syndrome",
                    "DiGeorge Syndrome",
                    ["biomedical", "diseases"],
                    "DiGeorge综合征",
                ),
                (
                    "digestive_system_diseases",
                    "Digestive System Diseases",
                    ["biomedical", "diseases"],
                    "消化系统疾病",
                ),
                (
                    "digestive_system_neoplasms",
                    "Digestive System Neoplasms",
                    ["biomedical", "diseases"],
                    "消化系统肿瘤",
                ),
                (
                    "diphtheria_tetanus_pertussis_vaccine",
                    "Diphtheria-Tetanus-Pertussis Vaccine",
                    ["biomedical", "chemicals_and_drugs"],
                    "白喉-破伤风-百日咳疫苗",
                ),
            ]
        )

    def test_exact_expansion_batch_029_adds_dna_dopamine_and_doublecortin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "dna_activated_protein_kinase",
                    "DNA-Activated Protein Kinase",
                    ["biomedical", "chemicals_and_drugs"],
                    "DNA活化蛋白激酶",
                ),
                (
                    "dna_bacterial",
                    "DNA, Bacterial",
                    ["biomedical", "chemicals_and_drugs"],
                    "细菌DNA",
                ),
                (
                    "dna_binding_proteins",
                    "DNA-Binding Proteins",
                    ["biomedical", "chemicals_and_drugs"],
                    "DNA结合蛋白",
                ),
                (
                    "dna_repair_deficiency_disorders",
                    "DNA Repair-Deficiency Disorders",
                    ["biomedical", "diseases"],
                    "DNA修复缺陷病",
                ),
                (
                    "dna_tumor_viruses",
                    "DNA Tumor Viruses",
                    ["biomedical", "organisms"],
                    "DNA肿瘤病毒",
                ),
                (
                    "dopamine_d2_receptor_antagonists",
                    "Dopamine D2 Receptor Antagonists",
                    ["biomedical", "chemicals_and_drugs"],
                    "多巴胺D2受体拮抗剂",
                ),
            ]
        )

    def test_exact_expansion_batch_030_adds_down_drug_resistance_and_duodenal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "down_syndrome",
                    "Down Syndrome",
                    ["biomedical", "diseases"],
                    "唐氏综合征",
                ),
                (
                    "dried_blood_spot_testing",
                    "Dried Blood Spot Testing",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "干血斑检测",
                ),
                (
                    "drug_resistance_bacterial",
                    "Drug Resistance, Bacterial",
                    ["biomedical", "phenomena_and_processes"],
                    "细菌耐药性",
                ),
                (
                    "drug_resistance_multiple_bacterial",
                    "Drug Resistance, Multiple, Bacterial",
                    ["biomedical", "phenomena_and_processes"],
                    "多重细菌耐药性",
                ),
                (
                    "dumping_syndrome",
                    "Dumping Syndrome",
                    ["biomedical", "diseases"],
                    "倾倒综合征",
                ),
                (
                    "duodenal_neoplasms",
                    "Duodenal Neoplasms",
                    ["biomedical", "diseases"],
                    "十二指肠肿瘤",
                ),
            ]
        )

    def test_exact_expansion_batch_031_adds_diagnosis_and_diagnostic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "delayed_diagnosis",
                    "Delayed Diagnosis",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "延迟诊断",
                ),
                (
                    "diagnosis_computer_assisted",
                    "Diagnosis, Computer-Assisted",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "计算机辅助诊断",
                ),
                (
                    "diagnosis_differential",
                    "Diagnosis, Differential",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "鉴别诊断",
                ),
                (
                    "diagnostic_techniques_neurological",
                    "Diagnostic Techniques, Neurological",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "神经系统诊断技术",
                ),
                (
                    "diagnostic_techniques_ophthalmological",
                    "Diagnostic Techniques, Ophthalmological",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "眼科诊断技术",
                ),
                (
                    "diagnostic_tests_routine",
                    "Diagnostic Tests, Routine",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "常规诊断试验",
                ),
            ]
        )

    def test_exact_expansion_batch_032_adds_dna_damage_and_repair_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "dna_adducts",
                    "DNA Adducts",
                    ["biomedical", "chemicals_and_drugs"],
                    "DNA加合物",
                ),
                (
                    "dna_breaks",
                    "DNA Breaks",
                    ["biomedical", "phenomena_and_processes"],
                    "DNA断裂",
                ),
                (
                    "dna_breaks_double_stranded",
                    "DNA Breaks, Double-Stranded",
                    ["biomedical", "phenomena_and_processes"],
                    "DNA双链断裂",
                ),
                (
                    "dna_fingerprinting",
                    "DNA Fingerprinting",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "DNA指纹分析",
                ),
                (
                    "dna_methylation",
                    "DNA Methylation",
                    ["biomedical", "phenomena_and_processes"],
                    "DNA甲基化",
                ),
                (
                    "dna_mismatch_repair",
                    "DNA Mismatch Repair",
                    ["biomedical", "phenomena_and_processes"],
                    "DNA错配修复",
                ),
            ]
        )

    def test_exact_expansion_batch_033_adds_dna_enzyme_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "dna_glycosylases",
                    "DNA Glycosylases",
                    ["biomedical", "chemicals_and_drugs"],
                    "DNA糖基化酶",
                ),
                (
                    "dna_gyrase",
                    "DNA Gyrase",
                    ["biomedical", "chemicals_and_drugs"],
                    "DNA旋转酶",
                ),
                (
                    "dna_helicases",
                    "DNA Helicases",
                    ["biomedical", "chemicals_and_drugs"],
                    "DNA解旋酶",
                ),
                (
                    "dna_ligase_atp",
                    "DNA Ligase ATP",
                    ["biomedical", "chemicals_and_drugs"],
                    "ATP依赖性DNA连接酶",
                ),
                (
                    "dna_polymerase_beta",
                    "DNA Polymerase Beta",
                    ["biomedical", "chemicals_and_drugs"],
                    "DNA聚合酶β",
                ),
                (
                    "dna_topoisomerases_type_i",
                    "DNA Topoisomerases, Type I",
                    ["biomedical", "chemicals_and_drugs"],
                    "I型DNA拓扑异构酶",
                ),
            ]
        )

    def test_exact_expansion_batch_034_adds_drug_development_and_adverse_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "drug_carriers",
                    "Drug Carriers",
                    ["biomedical", "chemicals_and_drugs"],
                    "药物载体",
                ),
                (
                    "drug_combinations",
                    "Drug Combinations",
                    ["biomedical", "chemicals_and_drugs"],
                    "药物组合",
                ),
                (
                    "drug_development",
                    "Drug Development",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "药物开发",
                ),
                (
                    "drug_discovery",
                    "Drug Discovery",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "药物发现",
                ),
                (
                    "drug_eruptions",
                    "Drug Eruptions",
                    ["biomedical", "diseases"],
                    "药疹",
                ),
                (
                    "drug_overdose",
                    "Drug Overdose",
                    ["biomedical", "diseases"],
                    "药物过量",
                ),
            ]
        )

    def test_exact_expansion_batch_035_adds_drug_resistance_and_therapy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "drug_resistance_multiple",
                    "Drug Resistance, Multiple",
                    ["biomedical", "phenomena_and_processes"],
                    "多重耐药性",
                ),
                (
                    "drug_resistance_viral",
                    "Drug Resistance, Viral",
                    ["biomedical", "phenomena_and_processes"],
                    "病毒耐药性",
                ),
                (
                    "drug_resistant_epilepsy",
                    "Drug Resistant Epilepsy",
                    ["biomedical", "diseases"],
                    "耐药性癫痫",
                ),
                (
                    "drug_therapy_combination",
                    "Drug Therapy, Combination",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "联合药物治疗",
                ),
                (
                    "drug_therapy_computer_assisted",
                    "Drug Therapy, Computer-Assisted",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "计算机辅助药物治疗",
                ),
                (
                    "drug_tolerance",
                    "Drug Tolerance",
                    ["biomedical", "phenomena_and_processes"],
                    "药物耐受性",
                ),
            ]
        )

    def test_exact_expansion_batch_036_adds_early_ear_and_ebolavirus_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "ear_diseases",
                    "Ear Diseases",
                    ["biomedical", "diseases"],
                    "耳疾病",
                ),
                (
                    "ear_neoplasms",
                    "Ear Neoplasms",
                    ["biomedical", "diseases"],
                    "耳肿瘤",
                ),
                (
                    "early_diagnosis",
                    "Early Diagnosis",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "早期诊断",
                ),
                (
                    "ebola_vaccines",
                    "Ebola Vaccines",
                    ["biomedical", "chemicals_and_drugs"],
                    "埃博拉疫苗",
                ),
                (
                    "ebolavirus",
                    "Ebolavirus",
                    ["biomedical", "organisms"],
                    "埃博拉病毒属",
                ),
                (
                    "ehlers_danlos_syndrome",
                    "Ehlers-Danlos Syndrome",
                    ["biomedical", "diseases"],
                    "Ehlers-Danlos综合征",
                ),
            ]
        )

    def test_exact_expansion_batch_037_adds_encephalitis_and_enterovirus_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "encephalitis_arbovirus",
                    "Encephalitis, Arbovirus",
                    ["biomedical", "diseases"],
                    "虫媒病毒性脑炎",
                ),
                (
                    "encephalitis_varicella_zoster",
                    "Encephalitis, Varicella Zoster",
                    ["biomedical", "diseases"],
                    "水痘-带状疱疹脑炎",
                ),
                (
                    "encephalitis_virus_japanese",
                    "Encephalitis Virus, Japanese",
                    ["biomedical", "organisms"],
                    "日本脑炎病毒",
                ),
                (
                    "encephalitis_viruses_tick_borne",
                    "Encephalitis Viruses, Tick-Borne",
                    ["biomedical", "organisms"],
                    "蜱传脑炎病毒",
                ),
                (
                    "enterovirus",
                    "Enterovirus",
                    ["biomedical", "organisms"],
                    "肠道病毒",
                ),
                (
                    "enterovirus_infections",
                    "Enterovirus Infections",
                    ["biomedical", "diseases"],
                    "肠道病毒感染",
                ),
            ]
        )

    def test_exact_expansion_batch_038_adds_enzyme_and_endothelial_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "enzyme_assays",
                    "Enzyme Assays",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "酶测定",
                ),
                (
                    "enzyme_inhibitors",
                    "Enzyme Inhibitors",
                    ["biomedical", "chemicals_and_drugs"],
                    "酶抑制剂",
                ),
                (
                    "enzyme_replacement_therapy",
                    "Enzyme Replacement Therapy",
                    ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"],
                    "酶替代疗法",
                ),
                (
                    "endothelial_cells",
                    "Endothelial Cells",
                    ["anatomy", "biomedical"],
                    "内皮细胞",
                ),
                (
                    "endothelial_growth_factors",
                    "Endothelial Growth Factors",
                    ["biomedical", "chemicals_and_drugs"],
                    "内皮生长因子",
                ),
                (
                    "endothelin_receptor_antagonists",
                    "Endothelin Receptor Antagonists",
                    ["biomedical", "chemicals_and_drugs"],
                    "内皮素受体拮抗剂",
                ),
            ]
        )

    def test_exact_expansion_batch_039_adds_extracellular_and_eye_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "extracellular_matrix",
                    "Extracellular Matrix",
                    ["anatomy", "biomedical"],
                    "细胞外基质",
                ),
                (
                    "extracellular_matrix_proteins",
                    "Extracellular Matrix Proteins",
                    ["biomedical", "chemicals_and_drugs"],
                    "细胞外基质蛋白",
                ),
                (
                    "extracellular_vesicles",
                    "Extracellular Vesicles",
                    ["anatomy", "biomedical"],
                    "细胞外囊泡",
                ),
                (
                    "eye_diseases",
                    "Eye Diseases",
                    ["biomedical", "diseases"],
                    "眼病",
                ),
                (
                    "eye_infections",
                    "Eye Infections",
                    ["biomedical", "diseases"],
                    "眼部感染",
                ),
                (
                    "eye_neoplasms",
                    "Eye Neoplasms",
                    ["biomedical", "diseases"],
                    "眼肿瘤",
                ),
            ]
        )

    def test_exact_expansion_batch_040_adds_factor_fanconi_and_fibroblast_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                (
                    "fabry_disease",
                    "Fabry Disease",
                    ["biomedical", "diseases"],
                    "Fabry病",
                ),
                (
                    "factor_v_deficiency",
                    "Factor V Deficiency",
                    ["biomedical", "diseases"],
                    "V因子缺乏症",
                ),
                (
                    "factor_xa_inhibitors",
                    "Factor Xa Inhibitors",
                    ["biomedical", "chemicals_and_drugs"],
                    "Xa因子抑制剂",
                ),
                (
                    "fanconi_syndrome",
                    "Fanconi Syndrome",
                    ["biomedical", "diseases"],
                    "Fanconi综合征",
                ),
                (
                    "factitious_disorders",
                    "Factitious Disorders",
                    ["biomedical", "psychiatry_and_psychology"],
                    "做作性障碍",
                ),
                (
                    "fas_receptor",
                    "Fas Receptor",
                    ["biomedical", "chemicals_and_drugs"],
                    "Fas受体",
                ),
                (
                    "fibroblast_growth_factors",
                    "Fibroblast Growth Factors",
                    ["biomedical", "chemicals_and_drugs"],
                    "成纤维细胞生长因子",
                ),
                (
                    "receptors_fibroblast_growth_factor",
                    "Receptors, Fibroblast Growth Factor",
                    ["biomedical", "chemicals_and_drugs"],
                    "成纤维细胞生长因子受体",
                ),
            ]
        )

    def test_exact_expansion_batch_041_adds_fibroma_and_fibromatosis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("fibroadenoma", "Fibroadenoma", ["biomedical", "diseases"], "纤维腺瘤"),
                ("fibroblast__3", "Fibroblasts", ["anatomy", "biomedical"], "成纤维细胞"),
                ("fibroma_desmoplastic", "Fibroma, Desmoplastic", ["biomedical", "diseases"], "硬纤维瘤"),
                ("fibroma_ossifying", "Fibroma, Ossifying", ["biomedical", "diseases"], "骨化性纤维瘤"),
                ("fibromatosi_plantar", "Fibromatosis, Plantar", ["biomedical", "diseases"], "跖纤维瘤病"),
            ]
        )

    def test_exact_expansion_batch_042_adds_fibrosis_and_fibula_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("fibromuscular_dysplasia", "Fibromuscular Dysplasia", ["biomedical", "diseases"], "纤维肌性发育不良"),
                ("fibromyalgia", "Fibromyalgia", ["biomedical", "diseases"], "纤维肌痛"),
                ("fibrosarcoma", "Fibrosarcoma", ["biomedical", "diseases"], "纤维肉瘤"),
                ("fibrosi", "Fibrosis", ["biomedical", "diseases"], "纤维化"),
                ("fibula_fractur", "Fibula Fractures", ["biomedical", "diseases"], "腓骨骨折"),
            ]
        )

    def test_exact_expansion_batch_043_adds_ficolin_and_filaria_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ficolin", "Ficolins", ["biomedical", "chemicals_and_drugs"], "纤维胶凝蛋白"),
                ("fiducial_marker__2", "Fiducial Markers", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "基准标记物"),
                ("figlu_test", "FIGLU Test", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "FIGLU试验"),
                ("filaggrin_protein", "Filaggrin Proteins", ["biomedical", "chemicals_and_drugs"], "丝聚蛋白"),
                ("filariasi", "Filariasis", ["biomedical", "diseases"], "丝虫病"),
            ]
        )

    def test_exact_expansion_batch_044_adds_filovirus_and_finger_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("filoviridae", "Filoviridae", ["biomedical", "organisms"], "丝状病毒科"),
                ("filoviridae_infection", "Filoviridae Infections", ["biomedical", "diseases"], "丝状病毒科感染"),
                ("fimbriae_bacterial", "Fimbriae, Bacterial", ["anatomy", "biomedical"], "细菌菌毛"),
                ("finger_injury", "Finger Injuries", ["biomedical", "diseases"], "手指损伤"),
                ("finger_joint", "Finger Joint", ["anatomy", "biomedical"], "手指关节"),
            ]
        )

    def test_exact_expansion_batch_045_adds_fish_and_flagella_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("fish_disease", "Fish Diseases", ["biomedical", "diseases"], "鱼类疾病"),
                ("fish_oils", "Fish Oils", ["biomedical", "chemicals_and_drugs"], "鱼油"),
                ("fissure_in_ano", "Fissure in Ano", ["biomedical", "diseases"], "肛裂"),
                ("flagella", "Flagella", ["anatomy", "biomedical"], "鞭毛"),
                ("flail_chest", "Flail Chest", ["biomedical", "diseases"], "连枷胸"),
            ]
        )

    def test_exact_expansion_batch_046_adds_flavivirus_and_flavonoid_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("flavin_mononucleotide", "Flavin Mononucleotide", ["biomedical", "chemicals_and_drugs"], "黄素单核苷酸"),
                ("flaviviridae", "Flaviviridae", ["biomedical", "organisms"], "黄病毒科"),
                ("flaviviridae_infection", "Flaviviridae Infections", ["biomedical", "diseases"], "黄病毒科感染"),
                ("flaviviru", "Flavivirus", ["biomedical", "organisms"], "黄病毒属"),
                ("flavonoid", "Flavonoids", ["biomedical", "chemicals_and_drugs"], "黄酮类化合物"),
            ]
        )

    def test_exact_expansion_batch_047_adds_fluorescence_technique_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("flow_cytometry__2", "Flow Cytometry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "流式细胞术"),
                ("fluorescein_angiography", "Fluorescein Angiography", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "荧光素血管造影"),
                ("fluorescence_polarization", "Fluorescence Polarization", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "荧光偏振"),
                ("fluorescence_resonance_energy_transfer", "Fluorescence Resonance Energy Transfer", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "荧光共振能量转移"),
                ("fluorescent_antibody_technique", "Fluorescent Antibody Technique", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "荧光抗体技术"),
            ]
        )

    def test_exact_expansion_batch_048_adds_fluoride_and_fluorine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("fluoridation", "Fluoridation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "氟化处理"),
                ("fluoride_poisoning", "Fluoride Poisoning", ["biomedical", "diseases"], "氟化物中毒"),
                ("fluorid_topical", "Fluorides, Topical", ["biomedical", "chemicals_and_drugs"], "局部用氟化物"),
                ("fluorine_radioisotop", "Fluorine Radioisotopes", ["biomedical", "chemicals_and_drugs"], "氟放射性同位素"),
                ("fluorine_19_magnetic_resonance_imaging", "Fluorine-19 Magnetic Resonance Imaging", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "氟-19磁共振成像"),
            ]
        )

    def test_exact_expansion_batch_049_adds_fluoro_drug_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("fluconazole", "Fluconazole", ["biomedical", "chemicals_and_drugs"], "氟康唑"),
                ("fluorodeoxyglucose_f18", "Fluorodeoxyglucose F18", ["biomedical", "chemicals_and_drugs"], "氟代脱氧葡萄糖F18"),
                ("fluoroquinolon", "Fluoroquinolones", ["biomedical", "chemicals_and_drugs"], "氟喹诺酮类"),
                ("fluorouracil", "Fluorouracil", ["biomedical", "chemicals_and_drugs"], "氟尿嘧啶"),
                ("fluoxetine", "Fluoxetine", ["biomedical", "chemicals_and_drugs"], "氟西汀"),
            ]
        )

    def test_exact_expansion_batch_050_adds_more_fluoro_drug_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("fluphenazine", "Fluphenazine", ["biomedical", "chemicals_and_drugs"], "氟奋乃静"),
                ("flurbiprofen", "Flurbiprofen", ["biomedical", "chemicals_and_drugs"], "氟比洛芬"),
                ("flutamide", "Flutamide", ["biomedical", "chemicals_and_drugs"], "氟他胺"),
                ("fluticasone", "Fluticasone", ["biomedical", "chemicals_and_drugs"], "氟替卡松"),
                ("fluvoxamine", "Fluvoxamine", ["biomedical", "chemicals_and_drugs"], "氟伏沙明"),
            ]
        )

    def test_exact_expansion_batch_051_adds_focal_and_folate_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("focal_adhesion", "Focal Adhesions", ["anatomy", "biomedical"], "黏着斑"),
                ("focal_cortical_dysplasia", "Focal Cortical Dysplasia", ["biomedical", "diseases"], "局灶性皮质发育不良"),
                ("focal_infection", "Focal Infection", ["biomedical", "diseases"], "局灶感染"),
                ("focused_assessment_with_sonography_for_trauma", "Focused Assessment with Sonography for Trauma", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "创伤重点超声评估"),
                ("folate_receptor_1", "Folate Receptor 1", ["biomedical", "chemicals_and_drugs"], "叶酸受体1"),
            ]
        )

    def test_exact_expansion_batch_052_adds_folic_and_follicle_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("folic_acid", "Folic Acid", ["biomedical", "chemicals_and_drugs"], "叶酸"),
                ("folic_acid_antagonist", "Folic Acid Antagonists", ["biomedical", "chemicals_and_drugs"], "叶酸拮抗剂"),
                ("folic_acid_deficiency", "Folic Acid Deficiency", ["biomedical", "diseases"], "叶酸缺乏"),
                ("follicle_stimulating_hormone", "Follicle Stimulating Hormone", ["biomedical", "chemicals_and_drugs"], "促卵泡激素"),
                ("follicular_phase", "Follicular Phase", ["biomedical", "phenomena_and_processes"], "卵泡期"),
            ]
        )

    def test_exact_expansion_batch_053_adds_food_and_foodborne_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("food_addiction", "Food Addiction", ["biomedical", "psychiatry_and_psychology"], "食物成瘾"),
                ("food_additiv", "Food Additives", ["biomedical", "chemicals_and_drugs"], "食品添加剂"),
                ("food_analysi", "Food Analysis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "食品分析"),
                ("food_drug_interaction", "Food-Drug Interactions", ["biomedical", "phenomena_and_processes"], "食物-药物相互作用"),
                ("foodborne_disease", "Foodborne Diseases", ["biomedical", "diseases"], "食源性疾病"),
            ]
        )

    def test_exact_expansion_batch_054_adds_foot_and_foramen_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("foot_deformity", "Foot Deformities", ["biomedical", "diseases"], "足畸形"),
                ("foot_disease", "Foot Diseases", ["biomedical", "diseases"], "足疾病"),
                ("foot_ulcer", "Foot Ulcer", ["biomedical", "diseases"], "足溃疡"),
                ("foot_and_mouth_disease", "Foot-and-Mouth Disease", ["biomedical", "diseases"], "口蹄疫"),
                ("foramen_ovale_patent", "Foramen Ovale, Patent", ["biomedical", "diseases"], "卵圆孔未闭"),
            ]
        )

    def test_exact_expansion_batch_055_adds_forearm_and_foreign_body_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("forearm", "Forearm", ["anatomy", "biomedical"], "前臂"),
                ("forearm_injury", "Forearm Injuries", ["biomedical", "diseases"], "前臂损伤"),
                ("foreign_body", "Foreign Bodies", ["biomedical", "diseases"], "异物"),
                ("foreign_body_reaction", "Foreign-Body Reaction", ["biomedical", "diseases"], "异物反应"),
                ("forensic_imaging", "Forensic Imaging", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "法医影像学"),
            ]
        )

    def test_exact_expansion_batch_056_adds_formate_and_fosfomycin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("formaldehyde__2", "Formaldehyde", ["biomedical", "chemicals_and_drugs"], "甲醛"),
                ("formate_dehydrogenase", "Formate Dehydrogenases", ["biomedical", "chemicals_and_drugs"], "甲酸脱氢酶"),
                ("formic_acid_ester", "Formic Acid Esters", ["biomedical", "chemicals_and_drugs"], "甲酸酯"),
                ("foscarnet", "Foscarnet", ["biomedical", "chemicals_and_drugs"], "膦甲酸钠"),
                ("fosfomycin", "Fosfomycin", ["biomedical", "chemicals_and_drugs"], "磷霉素"),
            ]
        )

    def test_exact_expansion_batch_057_adds_fracture_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("fractional_exhaled_nitric_oxide_testing", "Fractional Exhaled Nitric Oxide Testing", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "呼出气一氧化氮分数检测"),
                ("fracture_fixation", "Fracture Fixation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "骨折固定"),
                ("fracture_fixation_internal", "Fracture Fixation, Internal", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "内固定"),
                ("fractur_open", "Fractures, Open", ["biomedical", "diseases"], "开放性骨折"),
                ("fractur_stress", "Fractures, Stress", ["biomedical", "diseases"], "应力性骨折"),
            ]
        )

    def test_exact_expansion_batch_058_adds_fragile_and_frontotemporal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("fragile_x_syndrome", "Fragile X Syndrome", ["biomedical", "diseases"], "脆性X综合征"),
                ("frameshift_mutation", "Frameshift Mutation", ["biomedical", "phenomena_and_processes"], "移码突变"),
                ("friedreich_ataxia", "Friedreich Ataxia", ["biomedical", "diseases"], "Friedreich共济失调"),
                ("frontal_lobe", "Frontal Lobe", ["anatomy", "biomedical"], "额叶"),
                ("frontotemporal_dementia", "Frontotemporal Dementia", ["biomedical", "diseases"], "额颞叶痴呆"),
            ]
        )

    def test_exact_expansion_batch_059_adds_fructose_and_fungal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("fructose", "Fructose", ["biomedical", "chemicals_and_drugs"], "果糖"),
                ("fructose_intolerance", "Fructose Intolerance", ["biomedical", "diseases"], "果糖不耐受"),
                ("fungal_protein", "Fungal Proteins", ["biomedical", "chemicals_and_drugs"], "真菌蛋白"),
                ("fungal_vaccin", "Fungal Vaccines", ["biomedical", "chemicals_and_drugs"], "真菌疫苗"),
                ("fungemia", "Fungemia", ["biomedical", "diseases"], "真菌血症"),
            ]
        )

    def test_exact_expansion_batch_060_adds_fusobacterium_and_gaba_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("furosemide", "Furosemide", ["biomedical", "chemicals_and_drugs"], "呋塞米"),
                ("fusariosi", "Fusariosis", ["biomedical", "diseases"], "镰刀菌病"),
                ("fusobacterium_infection", "Fusobacterium Infections", ["biomedical", "diseases"], "梭杆菌感染"),
                ("gaba_agent", "GABA Agents", ["biomedical", "chemicals_and_drugs"], "GABA能药物"),
                ("gabaergic_neuron", "GABAergic Neurons", ["anatomy", "biomedical"], "GABA能神经元"),
            ]
        )

    def test_exact_expansion_batch_061_adds_gaba_receptor_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gaba_a_receptor_agonist", "GABA-A Receptor Agonists", ["biomedical", "chemicals_and_drugs"], "GABA-A受体激动剂"),
                ("gaba_a_receptor_antagonist", "GABA-A Receptor Antagonists", ["biomedical", "chemicals_and_drugs"], "GABA-A受体拮抗剂"),
                ("gaba_b_receptor_agonist", "GABA-B Receptor Agonists", ["biomedical", "chemicals_and_drugs"], "GABA-B受体激动剂"),
                ("gaba_b_receptor_antagonist", "GABA-B Receptor Antagonists", ["biomedical", "chemicals_and_drugs"], "GABA-B受体拮抗剂"),
                ("gabapentin", "Gabapentin", ["biomedical", "chemicals_and_drugs"], "加巴喷丁"),
            ]
        )

    def test_exact_expansion_batch_062_adds_gadolinium_and_gait_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gadolinium_dtpa", "Gadolinium DTPA", ["biomedical", "chemicals_and_drugs"], "钆喷酸葡胺"),
                ("gadolinium_oxide", "Gadolinium Oxide", ["materials_elements_and_compounds"], "氧化钆"),
                ("gain_of_function_mutation", "Gain Of Function Mutation", ["biomedical", "phenomena_and_processes"], "功能获得性突变"),
                ("gait_analysi", "Gait Analysis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "步态分析"),
                ("gait_disorder_neurologic", "Gait Disorders, Neurologic", ["biomedical", "diseases"], "神经性步态障碍"),
            ]
        )

    def test_exact_expansion_batch_063_adds_galactose_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("galactitol", "Galactitol", ["biomedical", "chemicals_and_drugs"], "半乳糖醇"),
                ("galactokinase", "Galactokinase", ["biomedical", "chemicals_and_drugs"], "半乳糖激酶"),
                ("galactose", "Galactose", ["biomedical", "chemicals_and_drugs"], "半乳糖"),
                ("galactose_oxidase", "Galactose Oxidase", ["biomedical", "chemicals_and_drugs"], "半乳糖氧化酶"),
                ("galactosemia", "Galactosemias", ["biomedical", "diseases"], "半乳糖血症"),
            ]
        )

    def test_exact_expansion_batch_064_adds_galactosidase_and_galanin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("galactosidase", "Galactosidases", ["biomedical", "chemicals_and_drugs"], "半乳糖苷酶"),
                ("galactosylceramidase", "Galactosylceramidase", ["biomedical", "chemicals_and_drugs"], "半乳糖神经酰胺酶"),
                ("galanin", "Galanin", ["biomedical", "chemicals_and_drugs"], "甘丙肽"),
                ("galanin_like_peptide", "Galanin-like Peptide", ["biomedical", "chemicals_and_drugs"], "甘丙肽样肽"),
                ("galantamine", "Galantamine", ["biomedical", "chemicals_and_drugs"], "加兰他敏"),
            ]
        )

    def test_exact_expansion_batch_065_adds_galectin_and_gallbladder_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("galectin", "Galectins", ["biomedical", "chemicals_and_drugs"], "半乳糖凝集素"),
                ("galectin_3", "Galectin 3", ["biomedical", "chemicals_and_drugs"], "半乳糖凝集素3"),
                ("gallbladder", "Gallbladder", ["anatomy", "biomedical"], "胆囊"),
                ("gallbladder_disease", "Gallbladder Diseases", ["biomedical", "diseases"], "胆囊疾病"),
                ("gallbladder_neoplasm", "Gallbladder Neoplasms", ["biomedical", "diseases"], "胆囊肿瘤"),
            ]
        )

    def test_exact_expansion_batch_066_adds_gallium_and_gallstone_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gallic_acid", "Gallic Acid", ["biomedical", "chemicals_and_drugs"], "没食子酸"),
                ("gallium_arsenide", "Gallium Arsenide", ["materials_elements_and_compounds"], "砷化镓"),
                ("gallium_nitride", "Gallium Nitride", ["materials_elements_and_compounds"], "氮化镓"),
                ("gallium_radioisotop", "Gallium Radioisotopes", ["biomedical", "chemicals_and_drugs"], "镓放射性同位素"),
                ("gallston", "Gallstones", ["biomedical", "diseases"], "胆结石"),
            ]
        )

    def test_exact_expansion_batch_067_adds_gambling_and_gamete_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("galvanic_skin_response", "Galvanic Skin Response", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "皮肤电反应"),
                ("gambling", "Gambling", ["biomedical", "psychiatry_and_psychology"], "赌博"),
                ("gamete_intrafallopian_transfer", "Gamete Intrafallopian Transfer", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "配子输卵管内移植"),
                ("gametogenesi", "Gametogenesis", ["biomedical", "phenomena_and_processes"], "配子发生"),
                ("gamification", "Gamification", ["computer_science"], "游戏化"),
            ]
        )

    def test_exact_expansion_batch_068_adds_gamma_biomedical_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gamma_aminobutyric_acid", "Gamma-aminobutyric Acid", ["biomedical", "chemicals_and_drugs"], "γ-氨基丁酸"),
                ("gamma_camera", "Gamma Cameras", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "伽马照相机"),
                ("gamma_globulin", "Gamma-globulins", ["biomedical", "chemicals_and_drugs"], "γ-球蛋白"),
                ("gamma_linolenic_acid", "Gamma-linolenic Acid", ["biomedical", "chemicals_and_drugs"], "γ-亚麻酸"),
                ("gamma_tocopherol", "Gamma-tocopherol", ["biomedical", "chemicals_and_drugs"], "γ-生育酚"),
            ]
        )

    def test_exact_expansion_batch_069_adds_gamma_ray_and_virus_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gamma_distribution", "Gamma Distribution", ["mathematics"], "伽马分布"),
                ("gamma_ray_burst", "Gamma-ray Bursts", ["nuclear_and_plasma_sciences"], "伽马射线暴"),
                ("gamma_ray_detector", "Gamma-ray Detectors", ["sensors"], "伽马射线探测器"),
                ("gamma_rays", "Gamma-rays", ["nuclear_and_plasma_sciences"], "伽马射线"),
                ("gammaretroviru", "Gammaretrovirus", ["biomedical", "organisms"], "γ逆转录病毒"),
            ]
        )

    def test_exact_expansion_batch_070_adds_ganglia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ganglia", "Ganglia", ["anatomy", "biomedical"], "神经节"),
                ("ganglia_autonomic", "Ganglia, Autonomic", ["anatomy", "biomedical"], "自主神经节"),
                ("ganglia_parasympathetic", "Ganglia, Parasympathetic", ["anatomy", "biomedical"], "副交感神经节"),
                ("ganglia_sensory", "Ganglia, Sensory", ["anatomy", "biomedical"], "感觉神经节"),
                ("ganglia_spinal", "Ganglia, Spinal", ["anatomy", "biomedical"], "脊神经节"),
            ]
        )

    def test_exact_expansion_batch_071_adds_ganglion_and_ganglioside_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ganglioglioma", "Ganglioglioma", ["biomedical", "diseases"], "神经节胶质瘤"),
                ("ganglion_cyst", "Ganglion Cysts", ["biomedical", "diseases"], "腱鞘囊肿"),
                ("ganglioneuroblastoma", "Ganglioneuroblastoma", ["biomedical", "diseases"], "神经节神经母细胞瘤"),
                ("ganglioneuroma", "Ganglioneuroma", ["biomedical", "diseases"], "神经节神经瘤"),
                ("gangliosid", "Gangliosides", ["biomedical", "chemicals_and_drugs"], "神经节苷脂"),
            ]
        )

    def test_exact_expansion_batch_072_adds_gap_junction_and_gardnerella_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gangrene", "Gangrene", ["biomedical", "diseases"], "坏疽"),
                ("gap_junction", "Gap Junctions", ["anatomy", "biomedical"], "缝隙连接"),
                ("gardner_syndrome", "Gardner Syndrome", ["biomedical", "diseases"], "Gardner综合征"),
                ("gardnerella", "Gardnerella", ["biomedical", "organisms"], "加德纳菌属"),
                ("gardnerella_vaginali", "Gardnerella Vaginalis", ["biomedical", "organisms"], "阴道加德纳菌"),
            ]
        )

    def test_exact_expansion_batch_073_adds_gas_chromatography_and_gangrene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("garlic", "Garlic", ["biomedical", "organisms"], "大蒜"),
                ("gas_chromatography", "Gas Chromatography", ["instrumentation_and_measurement"], "气相色谱法"),
                ("gas_chromatography_mass_spectrometry", "Gas Chromatography-mass Spectrometry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "气相色谱-质谱法"),
                ("gas_gangrene", "Gas Gangrene", ["biomedical", "diseases"], "气性坏疽"),
                ("gas_poisoning", "Gas Poisoning", ["biomedical", "diseases"], "气体中毒"),
            ]
        )

    def test_exact_expansion_batch_074_adds_gaseous_and_gastrectomy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gasdermin", "Gasdermins", ["biomedical", "chemicals_and_drugs"], "Gasdermin蛋白"),
                ("gasoline", "Gasoline", ["biomedical", "chemicals_and_drugs"], "汽油"),
                ("gasotransmitter", "Gasotransmitters", ["biomedical", "chemicals_and_drugs"], "气体递质"),
                ("gastrectomy", "Gastrectomy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "胃切除术"),
                ("gastric_absorption", "Gastric Absorption", ["biomedical", "phenomena_and_processes"], "胃吸收"),
            ]
        )

    def test_exact_expansion_batch_075_adds_gastric_anatomy_and_procedure_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gastric_acid", "Gastric Acid", ["anatomy", "biomedical"], "胃酸"),
                ("gastric_artery", "Gastric Artery", ["anatomy", "biomedical"], "胃动脉"),
                ("gastric_balloon", "Gastric Balloon", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "胃球囊"),
                ("gastric_bypass", "Gastric Bypass", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "胃旁路术"),
                ("gastric_emptying", "Gastric Emptying", ["biomedical", "phenomena_and_processes"], "胃排空"),
            ]
        )

    def test_exact_expansion_batch_076_adds_gastric_disease_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gastric_antral_vascular_ectasia", "Gastric Antral Vascular Ectasia", ["biomedical", "diseases"], "胃窦血管扩张症"),
                ("gastric_dilatation", "Gastric Dilatation", ["biomedical", "diseases"], "胃扩张"),
                ("gastric_fistula", "Gastric Fistula", ["biomedical", "diseases"], "胃瘘"),
                ("gastric_lavage", "Gastric Lavage", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "洗胃"),
                ("gastric_outlet_obstruction", "Gastric Outlet Obstruction", ["biomedical", "diseases"], "胃出口梗阻"),
            ]
        )

    def test_exact_expansion_batch_077_adds_gastrin_and_gastritis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gastrin", "Gastrins", ["biomedical", "chemicals_and_drugs"], "胃泌素"),
                ("gastrin_releasing_peptide", "Gastrin-releasing Peptide", ["biomedical", "chemicals_and_drugs"], "胃泌素释放肽"),
                ("gastrinoma", "Gastrinoma", ["biomedical", "diseases"], "胃泌素瘤"),
                ("gastriti__2", "Gastritis", ["biomedical", "diseases"], "胃炎"),
                ("gastriti_atrophic", "Gastritis, Atrophic", ["biomedical", "diseases"], "萎缩性胃炎"),
            ]
        )

    def test_exact_expansion_batch_078_adds_gastroenteritis_and_reflux_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gastroenteriti", "Gastroenteritis", ["biomedical", "diseases"], "胃肠炎"),
                ("gastroenterology__2", "Gastroenterology", ["biomedical", "disciplines_and_occupations"], "胃肠病学"),
                ("gastroenterostomy", "Gastroenterostomy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "胃肠吻合术"),
                ("gastroepiploic_artery", "Gastroepiploic Artery", ["anatomy", "biomedical"], "胃网膜动脉"),
                ("gastroesophageal_reflux", "Gastroesophageal Reflux", ["biomedical", "diseases"], "胃食管反流"),
            ]
        )

    def test_exact_expansion_batch_079_adds_gastrointestinal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gastrointestinal_absorption", "Gastrointestinal Absorption", ["biomedical", "phenomena_and_processes"], "胃肠吸收"),
                ("gastrointestinal_content", "Gastrointestinal Contents", ["anatomy", "biomedical"], "胃肠内容物"),
                ("gastrointestinal_disease", "Gastrointestinal Diseases", ["biomedical", "diseases"], "胃肠疾病"),
                ("gastrointestinal_hemorrhage", "Gastrointestinal Hemorrhage", ["biomedical", "diseases"], "胃肠出血"),
                ("gastrointestinal_hormon", "Gastrointestinal Hormones", ["biomedical", "chemicals_and_drugs"], "胃肠激素"),
            ]
        )

    def test_exact_expansion_batch_080_adds_gastrointestinal_stromal_and_gata_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gastrointestinal_neoplasm", "Gastrointestinal Neoplasms", ["biomedical", "diseases"], "胃肠肿瘤"),
                ("gastrointestinal_stromal_tumor", "Gastrointestinal Stromal Tumors", ["biomedical", "diseases"], "胃肠间质瘤"),
                ("gastroparesi", "Gastroparesis", ["biomedical", "diseases"], "胃轻瘫"),
                ("gastroscopy", "Gastroscopy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "胃镜检查"),
                ("gated_blood_pool_imaging", "Gated Blood-pool Imaging", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "门控血池显像"),
            ]
        )

    def test_exact_expansion_batch_061_to_080_fixes_review_side_effect_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("alpha_galactosidase", "Alpha-Galactosidase", ["biomedical", "chemicals_and_drugs"], "α-半乳糖苷酶"),
                ("beta_galactosidase", "Beta-Galactosidase", ["biomedical", "chemicals_and_drugs"], "β-半乳糖苷酶"),
                ("g_m1_ganglioside", "G(M1) Ganglioside", ["biomedical", "chemicals_and_drugs"], "GM1神经节苷脂"),
                ("g_m2_ganglioside", "G(M2) Ganglioside", ["biomedical", "chemicals_and_drugs"], "GM2神经节苷脂"),
                ("receptor_galanin_type_1", "Receptors, Galanin, Type 1", ["biomedical", "chemicals_and_drugs"], "1型甘丙肽受体"),
                ("receptor_gastrointestinal_hormone", "Receptors, Gastrointestinal Hormone", ["biomedical", "chemicals_and_drugs"], "胃肠激素受体"),
            ]
        )

    def test_exact_expansion_batch_081_adds_gaussian_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gaussian_beam", "Gaussian Beam", ["computer_science"], "高斯光束"),
                ("gaussian_channel", "Gaussian Channels", ["information_theory"], "高斯信道"),
                ("gaussian_distribution", "Gaussian Distribution", ["computer_science", "mathematics"], "高斯分布"),
                ("gaussian_filter", "Gaussian Filter", ["computer_science"], "高斯滤波器"),
                ("gaussian_mixture_model", "Gaussian Mixture Model", ["computer_science", "mathematics"], "高斯混合模型"),
            ]
        )

    def test_exact_expansion_batch_082_adds_gelatin_and_gemcitabine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gb_viru_c", "GB Virus C", ["biomedical", "organisms"], "GB病毒C"),
                ("gelatin", "Gelatin", ["biomedical", "chemicals_and_drugs"], "明胶"),
                ("gelatin_sponge_absorbable", "Gelatin Sponge, Absorbable", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "可吸收明胶海绵"),
                ("gemcitabine", "Gemcitabine", ["biomedical", "chemicals_and_drugs"], "吉西他滨"),
                ("gemfibrozil", "Gemfibrozil", ["biomedical", "chemicals_and_drugs"], "吉非罗齐"),
            ]
        )

    def test_exact_expansion_batch_083_adds_basic_gene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gen", "Genes", ["biomedical", "phenomena_and_processes"], "基因"),
                ("gen_abl", "Genes, Abl", ["biomedical", "phenomena_and_processes"], "Abl基因"),
                ("gen_apc", "Genes, APC", ["biomedical", "phenomena_and_processes"], "APC基因"),
                ("gen_archaeal", "Genes, Archaeal", ["biomedical", "phenomena_and_processes"], "古菌基因"),
                ("gen_bacterial", "Genes, Bacterial", ["biomedical", "phenomena_and_processes"], "细菌基因"),
            ]
        )

    def test_exact_expansion_batch_084_adds_brca_and_bcl_gene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gen_bcl_1", "Genes, Bcl-1", ["biomedical", "phenomena_and_processes"], "Bcl-1基因"),
                ("gen_bcl_2", "Genes, Bcl-2", ["biomedical", "phenomena_and_processes"], "Bcl-2基因"),
                ("gen_brca1", "Genes, Brca1", ["biomedical", "phenomena_and_processes"], "BRCA1基因"),
                ("gen_brca2", "Genes, Brca2", ["biomedical", "phenomena_and_processes"], "BRCA2基因"),
                ("gen_chloroplast", "Genes, Chloroplast", ["biomedical", "phenomena_and_processes"], "叶绿体基因"),
            ]
        )

    def test_exact_expansion_batch_085_adds_developmental_and_env_gene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gen_dcc", "Genes, DCC", ["biomedical", "phenomena_and_processes"], "DCC基因"),
                ("gen_developmental", "Genes, Developmental", ["biomedical", "phenomena_and_processes"], "发育基因"),
                ("gen_dominant", "Genes, Dominant", ["biomedical", "phenomena_and_processes"], "显性基因"),
                ("gen_duplicate", "Genes, Duplicate", ["biomedical", "phenomena_and_processes"], "重复基因"),
                ("gen_env", "Genes, Env", ["biomedical", "phenomena_and_processes"], "Env基因"),
            ]
        )

    def test_exact_expansion_batch_086_adds_erbb_and_fungal_gene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gen_erbb_1", "Genes, Erbb-1", ["biomedical", "phenomena_and_processes"], "ERBB1基因"),
                ("gen_erbb_2", "Genes, Erbb-2", ["biomedical", "phenomena_and_processes"], "ERBB2基因"),
                ("gen_fms", "Genes, Fms", ["biomedical", "phenomena_and_processes"], "Fms基因"),
                ("gen_fungal", "Genes, Fungal", ["biomedical", "phenomena_and_processes"], "真菌基因"),
                ("gen_gag", "Genes, Gag", ["biomedical", "phenomena_and_processes"], "Gag基因"),
            ]
        )

    def test_exact_expansion_batch_087_adds_homeobox_and_immunoglobulin_gene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gen_homeobox", "Genes, Homeobox", ["biomedical", "phenomena_and_processes"], "同源盒基因"),
                ("gen_immediate_early", "Genes, Immediate-early", ["biomedical", "phenomena_and_processes"], "即刻早期基因"),
                ("gen_immunoglobulin", "Genes, Immunoglobulin", ["biomedical", "phenomena_and_processes"], "免疫球蛋白基因"),
                ("gen_immunoglobulin_heavy_chain", "Genes, Immunoglobulin Heavy Chain", ["biomedical", "phenomena_and_processes"], "免疫球蛋白重链基因"),
                ("gen_immunoglobulin_light_chain", "Genes, Immunoglobulin Light Chain", ["biomedical", "phenomena_and_processes"], "免疫球蛋白轻链基因"),
            ]
        )

    def test_exact_expansion_batch_088_adds_mhc_and_mitochondrial_gene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gen_mhc_class_i", "Genes, MHC Class I", ["biomedical", "phenomena_and_processes"], "MHC I类基因"),
                ("gen_mhc_class_ii", "Genes, MHC Class II", ["biomedical", "phenomena_and_processes"], "MHC II类基因"),
                ("gen_mitochondrial__2", "Genes, Mitochondrial", ["biomedical", "phenomena_and_processes"], "线粒体基因"),
                ("gen_modifier", "Genes, Modifier", ["biomedical", "phenomena_and_processes"], "修饰基因"),
                ("gen_myc", "Genes, Myc", ["biomedical", "phenomena_and_processes"], "Myc基因"),
            ]
        )

    def test_exact_expansion_batch_089_adds_p53_and_ras_gene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gen_p16", "Genes, P16", ["biomedical", "phenomena_and_processes"], "P16基因"),
                ("gen_p53", "Genes, P53", ["biomedical", "phenomena_and_processes"], "P53基因"),
                ("gen_plant", "Genes, Plant", ["biomedical", "phenomena_and_processes"], "植物基因"),
                ("gen_rag_1", "Genes, Rag-1", ["biomedical", "phenomena_and_processes"], "RAG-1基因"),
                ("gen_ras", "Genes, Ras", ["biomedical", "phenomena_and_processes"], "Ras基因"),
            ]
        )

    def test_exact_expansion_batch_090_adds_t_cell_receptor_gene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gen_t_cell_receptor", "Genes, T-cell Receptor", ["biomedical", "phenomena_and_processes"], "T细胞受体基因"),
                ("gen_t_cell_receptor_alpha", "Genes, T-cell Receptor Alpha", ["biomedical", "phenomena_and_processes"], "T细胞受体α基因"),
                ("gen_t_cell_receptor_beta", "Genes, T-cell Receptor Beta", ["biomedical", "phenomena_and_processes"], "T细胞受体β基因"),
                ("gen_t_cell_receptor_delta", "Genes, T-cell Receptor Delta", ["biomedical", "phenomena_and_processes"], "T细胞受体δ基因"),
                ("gen_t_cell_receptor_gamma", "Genes, T-cell Receptor Gamma", ["biomedical", "phenomena_and_processes"], "T细胞受体γ基因"),
            ]
        )

    def test_exact_expansion_batch_091_adds_gene_therapy_and_transfer_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gene_amplification", "Gene Amplification", ["biomedical", "phenomena_and_processes"], "基因扩增"),
                ("gene_conversion", "Gene Conversion", ["biomedical", "phenomena_and_processes"], "基因转换"),
                ("gene_deletion", "Gene Deletion", ["biomedical", "phenomena_and_processes"], "基因缺失"),
                ("gene_editing", "Gene Editing", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "基因编辑"),
                ("gene_therapy_agent", "Gene Therapy Agents", ["biomedical", "chemicals_and_drugs"], "基因治疗剂"),
            ]
        )

    def test_exact_expansion_batch_092_adds_gene_expression_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gene_expression", "Gene Expression", ["biomedical", "phenomena_and_processes"], "基因表达"),
                ("gene_expression_profiling__2", "Gene Expression Profiling", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "基因表达谱分析"),
                ("gene_expression_regulation", "Gene Expression Regulation", ["biomedical", "phenomena_and_processes"], "基因表达调控"),
                ("gene_expression_regulation_bacterial", "Gene Expression Regulation, Bacterial", ["biomedical", "phenomena_and_processes"], "细菌基因表达调控"),
                ("gene_expression_regulation_viral", "Gene Expression Regulation, Viral", ["biomedical", "phenomena_and_processes"], "病毒基因表达调控"),
            ]
        )

    def test_exact_expansion_batch_093_adds_gene_product_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gene_product_env", "Gene Products, Env", ["biomedical", "chemicals_and_drugs"], "Env基因产物"),
                ("gene_product_gag", "Gene Products, Gag", ["biomedical", "chemicals_and_drugs"], "Gag基因产物"),
                ("gene_product_pol", "Gene Products, Pol", ["biomedical", "chemicals_and_drugs"], "Pol基因产物"),
                ("gene_product_tat", "Gene Products, Tat", ["biomedical", "chemicals_and_drugs"], "Tat基因产物"),
                ("gene_product_vif", "Gene Products, Vif", ["biomedical", "chemicals_and_drugs"], "Vif基因产物"),
            ]
        )

    def test_exact_expansion_batch_094_adds_gene_rearrangement_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gene_rearrangement", "Gene Rearrangement", ["biomedical", "phenomena_and_processes"], "基因重排"),
                ("gene_rearrangement_b_lymphocyte", "Gene Rearrangement, B-lymphocyte", ["biomedical", "phenomena_and_processes"], "B淋巴细胞基因重排"),
                ("gene_rearrangement_t_lymphocyte", "Gene Rearrangement, T-lymphocyte", ["biomedical", "phenomena_and_processes"], "T淋巴细胞基因重排"),
                ("gene_regulatory_network", "Gene Regulatory Networks", ["biomedical", "phenomena_and_processes"], "基因调控网络"),
                ("gene_silencing", "Gene Silencing", ["biomedical", "phenomena_and_processes"], "基因沉默"),
            ]
        )

    def test_exact_expansion_batch_095_adds_gene_targeting_and_transfer_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gene_targeting", "Gene Targeting", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "基因打靶"),
                ("gene_transfer_horizontal", "Gene Transfer, Horizontal", ["biomedical", "phenomena_and_processes"], "水平基因转移"),
                ("gene_transfer_techniqu", "Gene Transfer Techniques", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "基因转移技术"),
                ("general_practice", "General Practice", ["biomedical", "disciplines_and_occupations"], "全科医学"),
                ("general_surgery", "General Surgery", ["biomedical", "disciplines_and_occupations"], "普通外科"),
            ]
        )

    def test_exact_expansion_batch_096_adds_gender_and_anxiety_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gender_affirming_care", "Gender-affirming Care", ["biomedical", "health_care"], "性别肯定护理"),
                ("gender_dysphoria", "Gender Dysphoria", ["biomedical", "psychiatry_and_psychology"], "性别焦虑"),
                ("gender_identity", "Gender Identity", ["biomedical", "psychiatry_and_psychology"], "性别认同"),
                ("gender_role", "Gender Role", ["biomedical", "psychiatry_and_psychology"], "性别角色"),
                ("generalized_anxiety_disorder", "Generalized Anxiety Disorder", ["biomedical", "psychiatry_and_psychology"], "广泛性焦虑障碍"),
            ]
        )

    def test_exact_expansion_batch_097_adds_generative_ai_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("generative_adversarial_network", "Generative Adversarial Networks", ["computer_science", "mathematics"], "生成对抗网络"),
                ("generative_ai", "Generative AI", ["computational_and_artificial_intelligence"], "生成式AI"),
                ("generative_artificial_intelligence", "Generative Artificial Intelligence", ["biomedical", "information_science"], "生成式人工智能"),
                ("generative_model", "Generative Model", ["computer_science"], "生成模型"),
                ("generative_pre_trained_transformer", "Generative Pre-trained Transformer", ["computational_and_artificial_intelligence"], "生成式预训练Transformer"),
            ]
        )

    def test_exact_expansion_batch_098_adds_genetic_algorithm_and_association_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("genetic_algorithm", "Genetic Algorithms", ["computational_and_artificial_intelligence"], "遗传算法"),
                ("genetic_association_study__2", "Genetic Association Studies", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "遗传关联研究"),
                ("genetic_background", "Genetic Background", ["biomedical", "phenomena_and_processes"], "遗传背景"),
                ("genetic_carrier_screening", "Genetic Carrier Screening", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "遗传携带者筛查"),
                ("genetic_code", "Genetic Code", ["biomedical", "phenomena_and_processes"], "遗传密码"),
            ]
        )

    def test_exact_expansion_batch_099_adds_genetic_counseling_and_disease_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("genetic_counseling", "Genetic Counseling", ["biomedical", "disciplines_and_occupations"], "遗传咨询"),
                ("genetic_determinism", "Genetic Determinism", ["biomedical", "psychiatry_and_psychology"], "遗传决定论"),
                ("genetic_disease_inborn", "Genetic Diseases, Inborn", ["biomedical", "diseases"], "先天性遗传病"),
                ("genetic_disease_x_linked", "Genetic Diseases, X-linked", ["biomedical", "diseases"], "X连锁遗传病"),
                ("genetic_engineering__2", "Genetic Engineering", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "遗传工程"),
            ]
        )

    def test_exact_expansion_batch_100_adds_genetic_marker_and_phenomena_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("genetic_enhancement", "Genetic Enhancement", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "遗传增强"),
                ("genetic_heterogeneity", "Genetic Heterogeneity", ["biomedical", "phenomena_and_processes"], "遗传异质性"),
                ("genetic_marker", "Genetic Markers", ["biomedical", "chemicals_and_drugs"], "遗传标记"),
                ("genetic_phenomena", "Genetic Phenomena", ["biomedical", "phenomena_and_processes"], "遗传现象"),
                ("genetic_polymorphism", "Genetic Polymorphism", ["computer_science"], "遗传多态性"),
            ]
        )

    def test_exact_expansion_batch_101_adds_genetic_profile_and_risk_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("genetic_profile", "Genetic Profile", ["biomedical", "phenomena_and_processes"], "遗传谱"),
                ("genetic_programming", "Genetic Programming", ["computer_science"], "遗传编程"),
                ("genetic_risk_score", "Genetic Risk Score", ["biomedical", "diseases"], "遗传风险评分"),
                ("genetic_services", "Genetic Services", ["biomedical", "health_care"], "遗传服务"),
                ("genetic_techniques", "Genetic Techniques", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "遗传技术"),
            ]
        )

    def test_exact_expansion_batch_102_adds_genome_taxon_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("genome_archaeal", "Genome, Archaeal", ["biomedical", "phenomena_and_processes"], "古菌基因组"),
                ("genome_bacterial", "Genome, Bacterial", ["biomedical", "phenomena_and_processes"], "细菌基因组"),
                ("genome_chloroplast", "Genome, Chloroplast", ["biomedical", "phenomena_and_processes"], "叶绿体基因组"),
                ("genome_helminth", "Genome, Helminth", ["biomedical", "phenomena_and_processes"], "蠕虫基因组"),
                ("genome_mitochondrial", "Genome, Mitochondrial", ["biomedical", "phenomena_and_processes"], "线粒体基因组"),
            ]
        )

    def test_exact_expansion_batch_103_adds_genomic_medicine_and_variation_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("genomic_imprinting", "Genomic Imprinting", ["biomedical", "phenomena_and_processes"], "基因组印记"),
                ("genomic_instability", "Genomic Instability", ["biomedical", "diseases"], "基因组不稳定性"),
                ("genomic_islands", "Genomic Islands", ["biomedical", "phenomena_and_processes"], "基因组岛"),
                ("genomic_library", "Genomic Library", ["biomedical", "phenomena_and_processes"], "基因组文库"),
                ("genomic_medicine", "Genomic Medicine", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "基因组医学"),
            ]
        )

    def test_exact_expansion_batch_104_adds_geniculate_and_genital_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("geniculate_bodies", "Geniculate Bodies", ["anatomy", "biomedical"], "膝状体"),
                ("geniculate_ganglion", "Geniculate Ganglion", ["anatomy", "biomedical"], "膝状神经节"),
                ("genioplasty", "Genioplasty", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "颏成形术"),
                ("genital_diseases", "Genital Diseases", ["biomedical", "diseases"], "生殖器疾病"),
                ("genitalia_female", "Genitalia, Female", ["anatomy", "biomedical"], "女性生殖器"),
            ]
        )

    def test_exact_expansion_batch_105_adds_geographic_and_genu_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gentamicins", "Gentamicins", ["biomedical", "chemicals_and_drugs"], "庆大霉素类"),
                ("gentian_violet", "Gentian Violet", ["biomedical", "chemicals_and_drugs"], "龙胆紫"),
                ("genu_valgum", "Genu Valgum", ["biomedical", "diseases"], "膝外翻"),
                ("geographic_atrophy", "Geographic Atrophy", ["biomedical", "diseases"], "地图样萎缩"),
                ("geographic_routing", "Geographic Routing", ["computer_science"], "地理路由"),
            ]
        )

    def test_exact_expansion_batch_106_adds_geology_and_geomagnetic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("geo_spatial_data", "Geo-spatial Data", ["computer_science"], "地理空间数据"),
                ("geologic_sediments", "Geologic Sediments", ["biomedical", "phenomena_and_processes"], "地质沉积物"),
                ("geological_phenomena", "Geological Phenomena", ["biomedical", "phenomena_and_processes"], "地质现象"),
                ("geomagnetic_storms", "Geomagnetic Storms", ["magnetics"], "地磁暴"),
                ("geodesic_active_contour", "Geodesic Active Contour", ["computer_science"], "测地线主动轮廓"),
            ]
        )

    def test_exact_expansion_batch_107_adds_geometric_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("geometric_active_contours", "Geometric Active Contours", ["computer_science"], "几何主动轮廓"),
                ("geometric_continuity", "Geometric Continuity", ["computer_science"], "几何连续性"),
                ("geometric_distortion", "Geometric Distortion", ["computer_science"], "几何失真"),
                ("geometric_transformation", "Geometric Transformation", ["computer_science"], "几何变换"),
                ("geometrical_optics", "Geometrical Optics", ["lasers_and_electrooptics"], "几何光学"),
            ]
        )

    def test_exact_expansion_batch_108_adds_geophysical_and_geospatial_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("geophysical_measurements", "Geophysical Measurements", ["instrumentation_and_measurement"], "地球物理测量"),
                ("geophysical_signal_processing", "Geophysical Signal Processing", ["signal_processing"], "地球物理信号处理"),
                ("geoprocessing", "Geoprocessing", ["computer_science"], "地理处理"),
                ("geostationary_satellite", "Geostationary Satellite", ["computer_science"], "地球静止卫星"),
                ("geostrophic_flow", "Geostrophic Flow", ["computer_science"], "地转流"),
            ]
        )

    def test_exact_expansion_batch_109_adds_geotechnical_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("geotechnical_engineering", "Geotechnical Engineering", ["engineering_general"], "岩土工程"),
                ("geotechnical_structures", "Geotechnical Structures", ["engineering_general"], "岩土结构"),
                ("geotechnical_engineering_and_soil_mechanics", "Geotechnical Engineering And Soil Mechanics", ["engineering", "physical_sciences"], "岩土工程与土力学"),
                ("geotechnical_engineering_and_underground_structures", "Geotechnical Engineering And Underground Structures", ["engineering", "physical_sciences"], "岩土工程与地下结构"),
                ("geothermal_energy", "Geothermal Energy", ["power_engineering_and_energy"], "地热能"),
            ]
        )

    def test_exact_expansion_batch_110_adds_geriatric_and_germ_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("geriatric_dentistry", "Geriatric Dentistry", ["biomedical", "disciplines_and_occupations"], "老年牙科学"),
                ("geriatric_psychiatry", "Geriatric Psychiatry", ["biomedical", "disciplines_and_occupations"], "老年精神病学"),
                ("germ_layers", "Germ Layers", ["anatomy", "biomedical"], "胚层"),
                ("germ_line_mutation", "Germ-line Mutation", ["biomedical", "phenomena_and_processes"], "生殖系突变"),
                ("germinoma", "Germinoma", ["biomedical", "diseases"], "生殖细胞瘤"),
            ]
        )

    def test_exact_expansion_batch_111_adds_giant_cell_and_giardia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("giant_axonal_neuropathy", "Giant Axonal Neuropathy", ["biomedical", "diseases"], "巨轴索神经病"),
                ("giant_cell_arteritis", "Giant Cell Arteritis", ["biomedical", "diseases"], "巨细胞动脉炎"),
                ("giant_cell_tumor_of_bone", "Giant Cell Tumor Of Bone", ["biomedical", "diseases"], "骨巨细胞瘤"),
                ("giant_magnetoresistance", "Giant Magnetoresistance", ["magnetics"], "巨磁阻"),
                ("giardiasis", "Giardiasis", ["biomedical", "diseases"], "贾第虫病"),
            ]
        )

    def test_exact_expansion_batch_112_adds_gibbs_and_gingipain_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gibbs_distribution", "Gibbs Distribution", ["computer_science"], "吉布斯分布"),
                ("gibbs_sampler", "Gibbs Sampler", ["computer_science"], "吉布斯采样器"),
                ("gibbs_sampling", "Gibbs Sampling", ["computer_science"], "吉布斯采样"),
                ("gigabit_ethernet", "Gigabit Ethernet", ["computer_science"], "千兆以太网"),
                ("gingipain_cysteine_endopeptidases", "Gingipain Cysteine Endopeptidases", ["biomedical", "chemicals_and_drugs"], "牙龈蛋白酶半胱氨酸内肽酶"),
            ]
        )

    def test_exact_expansion_batch_113_adds_gingival_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gingival_crevicular_fluid", "Gingival Crevicular Fluid", ["anatomy", "biomedical"], "龈沟液"),
                ("gingival_diseases", "Gingival Diseases", ["biomedical", "diseases"], "牙龈疾病"),
                ("gingival_hyperplasia", "Gingival Hyperplasia", ["biomedical", "diseases"], "牙龈增生"),
                ("gingival_retraction_techniques", "Gingival Retraction Techniques", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "排龈技术"),
                ("gingivitis_necrotizing_ulcerative", "Gingivitis, Necrotizing Ulcerative", ["biomedical", "diseases"], "坏死性溃疡性牙龈炎"),
            ]
        )

    def test_exact_expansion_batch_114_adds_ginkgo_and_glasgow_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ginkgo_biloba", "Ginkgo Biloba", ["biomedical", "organisms"], "银杏"),
                ("ginkgolides", "Ginkgolides", ["biomedical", "chemicals_and_drugs"], "银杏内酯"),
                ("gitelman_syndrome", "Gitelman Syndrome", ["biomedical", "diseases"], "吉特尔曼综合征"),
                ("glasgow_coma_scale", "Glasgow Coma Scale", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "格拉斯哥昏迷量表"),
                ("glasgow_outcome_scale", "Glasgow Outcome Scale", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "格拉斯哥预后量表"),
            ]
        )

    def test_exact_expansion_batch_115_adds_glaucoma_and_glial_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glaucoma_angle_closure", "Glaucoma, Angle-closure", ["biomedical", "diseases"], "闭角型青光眼"),
                ("glaucoma_neovascular", "Glaucoma, Neovascular", ["biomedical", "diseases"], "新生血管性青光眼"),
                ("glenoid_cavity", "Glenoid Cavity", ["anatomy", "biomedical"], "关节盂"),
                ("glial_fibrillary_acidic_protein", "Glial Fibrillary Acidic Protein", ["biomedical", "chemicals_and_drugs"], "胶质纤维酸性蛋白"),
                ("glipizide", "Glipizide", ["biomedical", "chemicals_and_drugs"], "格列吡嗪"),
            ]
        )

    def test_exact_expansion_batch_116_adds_global_technical_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("global_asymptotic_stability", "Global Asymptotic Stability", ["computer_science"], "全局渐近稳定性"),
                ("global_burden_of_disease", "Global Burden Of Disease", ["biomedical", "health_care"], "全球疾病负担"),
                ("global_illumination", "Global Illumination", ["computer_science"], "全局照明"),
                ("global_longitudinal_strain", "Global Longitudinal Strain", ["biomedical", "phenomena_and_processes"], "整体纵向应变"),
                ("global_optimization_problems", "Global Optimization Problems", ["computer_science"], "全局优化问题"),
            ]
        )

    def test_exact_expansion_batch_117_adds_globus_and_glomerular_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("globus_pallidus", "Globus Pallidus", ["anatomy", "biomedical"], "苍白球"),
                ("glomerular_basement_membrane", "Glomerular Basement Membrane", ["anatomy", "biomedical"], "肾小球基底膜"),
                ("glomerular_filtration_rate", "Glomerular Filtration Rate", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "肾小球滤过率"),
                ("glomerulonephritis_membranous", "Glomerulonephritis, Membranous", ["biomedical", "diseases"], "膜性肾小球肾炎"),
                ("glomerulosclerosis_focal_segmental", "Glomerulosclerosis, Focal Segmental", ["biomedical", "diseases"], "局灶节段性肾小球硬化"),
            ]
        )

    def test_exact_expansion_batch_118_adds_glomus_and_glossopharyngeal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glomus_jugulare_tumor", "Glomus Jugulare Tumor", ["biomedical", "diseases"], "颈静脉球瘤"),
                ("glomus_tympanicum_tumor", "Glomus Tympanicum Tumor", ["biomedical", "diseases"], "鼓室球瘤"),
                ("glossitis_benign_migratory", "Glossitis, Benign Migratory", ["biomedical", "diseases"], "良性游走性舌炎"),
                ("glossopharyngeal_nerve", "Glossopharyngeal Nerve", ["anatomy", "biomedical"], "舌咽神经"),
                ("glossoptosis", "Glossoptosis", ["biomedical", "diseases"], "舌后坠"),
            ]
        )

    def test_exact_expansion_batch_119_adds_glow_and_glucagon_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glow_discharges", "Glow Discharges", ["dielectrics_and_electrical_insulation"], "辉光放电"),
                ("glucagon_like_peptides", "Glucagon-like Peptides", ["biomedical", "chemicals_and_drugs"], "胰高血糖素样肽"),
                ("glucagon_like_peptide_1", "Glucagon-like Peptide 1", ["biomedical", "chemicals_and_drugs"], "胰高血糖素样肽-1"),
                ("glucagon_like_peptide_1_receptor_agonists", "Glucagon-like Peptide-1 Receptor Agonists", ["biomedical", "chemicals_and_drugs"], "胰高血糖素样肽-1受体激动剂"),
                ("glucagonoma", "Glucagonoma", ["biomedical", "diseases"], "胰高血糖素瘤"),
            ]
        )

    def test_exact_expansion_batch_120_adds_glucose_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glucocorticoids", "Glucocorticoids", ["biomedical", "chemicals_and_drugs"], "糖皮质激素"),
                ("gluconeogenesis", "Gluconeogenesis", ["biomedical", "phenomena_and_processes"], "糖异生"),
                ("glucose_6_phosphate", "Glucose-6-phosphate", ["biomedical", "chemicals_and_drugs"], "葡萄糖-6-磷酸"),
                ("glucose_clamp_technique", "Glucose Clamp Technique", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "葡萄糖钳夹技术"),
                ("glucose_solution_hypertonic", "Glucose Solution, Hypertonic", ["biomedical", "chemicals_and_drugs"], "高渗葡萄糖溶液"),
            ]
        )

    def test_exact_expansion_batch_101_to_120_fixes_review_side_effect_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("alpha_globin", "Alpha-globins", ["biomedical", "chemicals_and_drugs"], "α珠蛋白"),
                ("beta_glucan", "Beta-glucans", ["biomedical", "chemicals_and_drugs"], "β-葡聚糖"),
                ("calcium_gluconate", "Calcium Gluconate", ["biomedical", "chemicals_and_drugs"], "葡萄糖酸钙"),
                ("germinal_center_kinase", "Germinal Center Kinases", ["biomedical", "chemicals_and_drugs"], "生发中心激酶"),
                ("receptor_ghrelin", "Receptors, Ghrelin", ["biomedical", "chemicals_and_drugs"], "胃饥饿素受体"),
                ("receptor_glucocorticoid", "Receptors, Glucocorticoid", ["biomedical", "chemicals_and_drugs"], "糖皮质激素受体"),
            ]
        )

    def test_exact_expansion_batch_121_adds_glucose_transport_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glucose_1_phosphate_adenylyltransferase", "Glucose-1-phosphate Adenylyltransferase", ["biomedical", "chemicals_and_drugs"], "葡萄糖-1-磷酸腺苷酰转移酶"),
                ("glucose_transport_proteins_facilitative", "Glucose Transport Proteins, Facilitative", ["biomedical", "chemicals_and_drugs"], "促进性葡萄糖转运蛋白"),
                ("glucose_transporter_type_1", "Glucose Transporter Type 1", ["biomedical", "chemicals_and_drugs"], "葡萄糖转运蛋白1型"),
                ("glucose_transporter_type_4", "Glucose Transporter Type 4", ["biomedical", "chemicals_and_drugs"], "葡萄糖转运蛋白4型"),
                ("glucosephosphate_dehydrogenase_deficiency", "Glucosephosphate Dehydrogenase Deficiency", ["biomedical", "diseases"], "葡萄糖-6-磷酸脱氢酶缺乏症"),
            ]
        )

    def test_exact_expansion_batch_122_adds_glucoside_and_glucuronide_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glucosides", "Glucosides", ["biomedical", "chemicals_and_drugs"], "葡萄糖苷类"),
                ("glucosinolates", "Glucosinolates", ["biomedical", "chemicals_and_drugs"], "硫代葡萄糖苷类"),
                ("glucosylceramidase", "Glucosylceramidase", ["biomedical", "chemicals_and_drugs"], "葡糖神经酰胺酶"),
                ("glucuronides", "Glucuronides", ["biomedical", "chemicals_and_drugs"], "葡萄糖醛酸苷类"),
                ("glucuronosyltransferase", "Glucuronosyltransferase", ["biomedical", "chemicals_and_drugs"], "葡萄糖醛酸转移酶"),
            ]
        )

    def test_exact_expansion_batch_123_adds_glutamate_enzyme_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gluk2_kainate_receptor", "Gluk2 Kainate Receptor", ["biomedical", "chemicals_and_drugs"], "GluK2海人酸受体"),
                ("glutamate_5_semialdehyde_dehydrogenase", "Glutamate-5-semialdehyde Dehydrogenase", ["biomedical", "chemicals_and_drugs"], "谷氨酸-5-半醛脱氢酶"),
                ("glutamate_carboxypeptidase_ii", "Glutamate Carboxypeptidase II", ["biomedical", "chemicals_and_drugs"], "谷氨酸羧肽酶II"),
                ("glutamate_decarboxylase", "Glutamate Decarboxylase", ["biomedical", "chemicals_and_drugs"], "谷氨酸脱羧酶"),
                ("glutamate_trna_ligase", "Glutamate-trna Ligase", ["biomedical", "chemicals_and_drugs"], "谷氨酸-tRNA连接酶"),
            ]
        )

    def test_exact_expansion_batch_124_adds_glutathione_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glutaminase", "Glutaminase", ["biomedical", "chemicals_and_drugs"], "谷氨酰胺酶"),
                ("glutamine", "Glutamine", ["biomedical", "chemicals_and_drugs"], "谷氨酰胺"),
                ("glutaral", "Glutaral", ["biomedical", "chemicals_and_drugs"], "戊二醛"),
                ("glutathione_disulfide", "Glutathione Disulfide", ["biomedical", "chemicals_and_drugs"], "氧化型谷胱甘肽"),
                ("glutathione_peroxidase", "Glutathione Peroxidase", ["biomedical", "chemicals_and_drugs"], "谷胱甘肽过氧化物酶"),
            ]
        )

    def test_exact_expansion_batch_125_adds_glycemic_and_glyceraldehyde_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glyburide", "Glyburide", ["biomedical", "chemicals_and_drugs"], "格列本脲"),
                ("glycated_serum_albumin", "Glycated Serum Albumin", ["biomedical", "chemicals_and_drugs"], "糖化血清白蛋白"),
                ("glycation_end_products_advanced", "Glycation End Products, Advanced", ["biomedical", "chemicals_and_drugs"], "晚期糖基化终产物"),
                ("glycemic_index", "Glycemic Index", ["biomedical", "phenomena_and_processes"], "血糖指数"),
                ("glyceraldehyde_3_phosphate_dehydrogenases", "Glyceraldehyde-3-phosphate Dehydrogenases", ["biomedical", "chemicals_and_drugs"], "甘油醛-3-磷酸脱氢酶"),
            ]
        )

    def test_exact_expansion_batch_126_adds_glycerol_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glyceric_acids", "Glyceric Acids", ["biomedical", "chemicals_and_drugs"], "甘油酸类"),
                ("glycerol", "Glycerol", ["biomedical", "chemicals_and_drugs"], "甘油"),
                ("glycerol_kinase", "Glycerol Kinase", ["biomedical", "chemicals_and_drugs"], "甘油激酶"),
                ("glycerophospholipids", "Glycerophospholipids", ["biomedical", "chemicals_and_drugs"], "甘油磷脂类"),
                ("glycerylphosphorylcholine", "Glycerylphosphorylcholine", ["biomedical", "chemicals_and_drugs"], "甘油磷酰胆碱"),
            ]
        )

    def test_exact_expansion_batch_127_adds_glycine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glycine", "Glycine", ["biomedical", "chemicals_and_drugs"], "甘氨酸"),
                ("glycine_decarboxylase_complex", "Glycine Decarboxylase Complex", ["biomedical", "chemicals_and_drugs"], "甘氨酸脱羧酶复合物"),
                ("glycine_hydroxymethyltransferase", "Glycine Hydroxymethyltransferase", ["biomedical", "chemicals_and_drugs"], "甘氨酸羟甲基转移酶"),
                ("glycine_max", "Glycine Max", ["biomedical", "organisms"], "大豆"),
                ("glycine_plasma_membrane_transport_proteins", "Glycine Plasma Membrane Transport Proteins", ["biomedical", "chemicals_and_drugs"], "甘氨酸质膜转运蛋白"),
            ]
        )

    def test_exact_expansion_batch_128_adds_glycobiology_and_glycogen_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glycobiology", "Glycobiology", ["biomedical", "disciplines_and_occupations"], "糖生物学"),
                ("glycocalyx", "Glycocalyx", ["anatomy", "biomedical"], "糖萼"),
                ("glycocholic_acid", "Glycocholic Acid", ["biomedical", "chemicals_and_drugs"], "甘胆酸"),
                ("glycogen", "Glycogen", ["biomedical", "chemicals_and_drugs"], "糖原"),
                ("glycogen_phosphorylase", "Glycogen Phosphorylase", ["biomedical", "chemicals_and_drugs"], "糖原磷酸化酶"),
            ]
        )

    def test_exact_expansion_batch_129_adds_glycogen_storage_disease_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glycogen_storage_disease", "Glycogen Storage Disease", ["biomedical", "diseases"], "糖原贮积病"),
                ("glycogen_storage_disease_type_i", "Glycogen Storage Disease Type I", ["biomedical", "diseases"], "糖原贮积病I型"),
                ("glycogen_storage_disease_type_ii", "Glycogen Storage Disease Type II", ["biomedical", "diseases"], "糖原贮积病II型"),
                ("glycogen_storage_disease_type_v", "Glycogen Storage Disease Type V", ["biomedical", "diseases"], "糖原贮积病V型"),
                ("glycogen_storage_disease_type_viii", "Glycogen Storage Disease Type VIII", ["biomedical", "diseases"], "糖原贮积病VIII型"),
            ]
        )

    def test_exact_expansion_batch_130_adds_glycolysis_and_glycomics_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glycogen_synthase_kinase_3_beta", "Glycogen Synthase Kinase 3 Beta", ["biomedical", "chemicals_and_drugs"], "糖原合酶激酶3β"),
                ("glycogenolysis", "Glycogenolysis", ["biomedical", "phenomena_and_processes"], "糖原分解"),
                ("glycolipids", "Glycolipids", ["biomedical", "chemicals_and_drugs"], "糖脂类"),
                ("glycolysis", "Glycolysis", ["biomedical", "phenomena_and_processes"], "糖酵解"),
                ("glycomics", "Glycomics", ["biomedical", "disciplines_and_occupations"], "糖组学"),
            ]
        )

    def test_exact_expansion_batch_131_adds_glycoside_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glycopeptides", "Glycopeptides", ["biomedical", "chemicals_and_drugs"], "糖肽类"),
                ("glycoprotein_hormones_alpha_subunit", "Glycoprotein Hormones, Alpha Subunit", ["biomedical", "chemicals_and_drugs"], "糖蛋白激素α亚基"),
                ("glycopyrrolate", "Glycopyrrolate", ["biomedical", "chemicals_and_drugs"], "格隆溴铵"),
                ("glycosaminoglycans", "Glycosaminoglycans", ["biomedical", "chemicals_and_drugs"], "糖胺聚糖类"),
                ("glycoside_hydrolase_inhibitors", "Glycoside Hydrolase Inhibitors", ["biomedical", "chemicals_and_drugs"], "糖苷水解酶抑制剂"),
            ]
        )

    def test_exact_expansion_batch_132_adds_glycyrrhiza_and_glymphatic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("glycosyltransferases", "Glycosyltransferases", ["biomedical", "chemicals_and_drugs"], "糖基转移酶类"),
                ("glycyrrhetinic_acid", "Glycyrrhetinic Acid", ["biomedical", "chemicals_and_drugs"], "甘草次酸"),
                ("glycyrrhizic_acid", "Glycyrrhizic Acid", ["biomedical", "chemicals_and_drugs"], "甘草酸"),
                ("glymphatic_system", "Glymphatic System", ["anatomy", "biomedical"], "类淋巴系统"),
                ("glyphosate", "Glyphosate", ["biomedical", "chemicals_and_drugs"], "草甘膦"),
            ]
        )

    def test_exact_expansion_batch_133_adds_gps_gpu_and_graft_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gps_positioning", "Gps Positioning", ["computer_science"], "GPS定位"),
                ("gpu_programming", "Gpu Programming", ["computer_science"], "GPU编程"),
                ("gradient_methods", "Gradient Methods", ["computer_science", "mathematics"], "梯度方法"),
                ("graft_survival", "Graft Survival", ["biomedical", "phenomena_and_processes"], "移植物存活"),
                ("graft_vs_host_reaction", "Graft Vs Host Reaction", ["biomedical", "phenomena_and_processes"], "移植物抗宿主反应"),
            ]
        )

    def test_exact_expansion_batch_134_adds_grain_and_gram_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("grain_boundaries", "Grain Boundaries", ["materials_elements_and_compounds"], "晶界"),
                ("gram_negative_aerobic_bacteria", "Gram-negative Aerobic Bacteria", ["biomedical", "organisms"], "革兰阴性需氧菌"),
                ("gram_negative_bacterial_infections", "Gram-negative Bacterial Infections", ["biomedical", "diseases"], "革兰阴性菌感染"),
                ("gram_positive_cocci", "Gram-positive Cocci", ["biomedical", "organisms"], "革兰阳性球菌"),
                ("gramicidin", "Gramicidin", ["biomedical", "chemicals_and_drugs"], "短杆菌肽"),
            ]
        )

    def test_exact_expansion_batch_135_adds_grammar_and_granular_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("grammar_induction", "Grammar Induction", ["computer_science"], "语法归纳"),
                ("granger_causality_test", "Granger Causality Test", ["computer_science"], "格兰杰因果检验"),
                ("granisetron", "Granisetron", ["biomedical", "chemicals_and_drugs"], "格拉司琼"),
                ("granular_computing", "Granular Computing", ["computers_and_information_processing"], "粒计算"),
                ("granulation_tissue", "Granulation Tissue", ["anatomy", "biomedical"], "肉芽组织"),
            ]
        )

    def test_exact_expansion_batch_136_adds_granulocyte_and_granuloma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("granulocyte_colony_stimulating_factor", "Granulocyte Colony-stimulating Factor", ["biomedical", "chemicals_and_drugs"], "粒细胞集落刺激因子"),
                ("granulocyte_macrophage_colony_stimulating_factor", "Granulocyte-macrophage Colony-stimulating Factor", ["biomedical", "chemicals_and_drugs"], "粒细胞-巨噬细胞集落刺激因子"),
                ("granulocyte_precursor_cells", "Granulocyte Precursor Cells", ["anatomy", "biomedical"], "粒细胞前体细胞"),
                ("granuloma", "Granuloma", ["biomedical", "diseases"], "肉芽肿"),
                ("granuloma_foreign_body", "Granuloma, Foreign-body", ["biomedical", "diseases"], "异物性肉芽肿"),
            ]
        )

    def test_exact_expansion_batch_137_adds_granulomatosis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("granuloma_pyogenic", "Granuloma, Pyogenic", ["biomedical", "diseases"], "化脓性肉芽肿"),
                ("granulomatosis_orofacial", "Granulomatosis, Orofacial", ["biomedical", "diseases"], "口面部肉芽肿病"),
                ("granulomatosis_with_polyangiitis", "Granulomatosis With Polyangiitis", ["biomedical", "diseases"], "多血管炎性肉芽肿病"),
                ("granulomatous_disease_chronic", "Granulomatous Disease, Chronic", ["biomedical", "diseases"], "慢性肉芽肿病"),
                ("granulomatous_mastitis", "Granulomatous Mastitis", ["biomedical", "diseases"], "肉芽肿性乳腺炎"),
            ]
        )

    def test_exact_expansion_batch_138_adds_granulosa_and_graph_base_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("granulosa_cells", "Granulosa Cells", ["anatomy", "biomedical"], "颗粒膜细胞"),
                ("granulosa_cell_tumor", "Granulosa Cell Tumor", ["biomedical", "diseases"], "颗粒膜细胞瘤"),
                ("grape_seed_extract", "Grape Seed Extract", ["biomedical", "chemicals_and_drugs"], "葡萄籽提取物"),
                ("graph_anomaly_detection", "Graph Anomaly Detection", ["computer_science"], "图异常检测"),
                ("graph_based_representations", "Graph-based Representations", ["computer_science"], "基于图的表示"),
            ]
        )

    def test_exact_expansion_batch_139_adds_graph_algorithm_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("graph_coloring", "Graph Coloring", ["computer_science"], "图着色"),
                ("graph_coloring_problem", "Graph Coloring Problem", ["computer_science"], "图着色问题"),
                ("graph_cuts", "Graph Cuts", ["computer_science"], "图割"),
                ("graph_drawing", "Graph Drawing", ["computer_science"], "图绘制"),
                ("graph_matching_algorithms", "Graph-matching Algorithms", ["computer_science"], "图匹配算法"),
            ]
        )

    def test_exact_expansion_batch_140_adds_graph_transformation_and_graphene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("graph_rewriting", "Graph Rewriting", ["computer_science"], "图重写"),
                ("graph_transformation", "Graph Transformation", ["computer_science"], "图变换"),
                ("graph_transformation_system", "Graph Transformation System", ["computer_science"], "图变换系统"),
                ("graphene", "Graphene", ["materials_elements_and_compounds"], "石墨烯"),
                ("graphics_hardware", "Graphics Hardware", ["computer_science"], "图形硬件"),
            ]
        )

    def test_exact_expansion_batch_121_to_140_fixes_review_side_effect_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("alpha_glucosidase", "Alpha-glucosidases", ["biomedical", "chemicals_and_drugs"], "α-葡萄糖苷酶"),
                ("formal_grammar", "Formal Grammar", ["computer_science"], "形式文法"),
                ("glucan_1_4_alpha_glucosidase", "Glucan 1,4-alpha-glucosidase", ["biomedical", "chemicals_and_drugs"], "葡聚糖1,4-α-葡萄糖苷酶"),
                ("plasma_cell_granuloma_pulmonary", "Plasma Cell Granuloma, Pulmonary", ["biomedical", "diseases"], "肺浆细胞肉芽肿"),
                ("receptor_glycine", "Receptors, Glycine", ["biomedical", "chemicals_and_drugs"], "甘氨酸受体"),
                ("receptor_granulocyte_colony_stimulating_factor", "Receptors, Granulocyte Colony-Stimulating Factor", ["biomedical", "chemicals_and_drugs"], "粒细胞集落刺激因子受体"),
            ]
        )

    def test_exact_expansion_batch_141_adds_graphics_grasp_and_graves_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("graphic_processor", "Graphics Processor", ["computer_science"], "图形处理器"),
                ("graphite", "Graphite", ["materials_elements_and_compounds"], "石墨"),
                ("grasp_planning", "Grasp Planning", ["computer_science"], "抓取规划"),
                ("grating", "Gratings", ["materials_elements_and_compounds"], "光栅"),
                ("grav_disease", "Graves Disease", ["biomedical", "diseases"], "格雷夫斯病"),
            ]
        )

    def test_exact_expansion_batch_142_adds_gravity_gray_and_greedy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gravitational_wav", "Gravitational Waves", ["science_general"], "引力波"),
                ("gray_matter", "Gray Matter", ["anatomy", "biomedical"], "灰质"),
                ("gray_platelet_syndrome", "Gray Platelet Syndrome", ["biomedical", "diseases"], "灰色血小板综合征"),
                ("greedy_algorithm", "Greedy Algorithms", ["computational_and_artificial_intelligence"], "贪心算法"),
                ("greedy_routing", "Greedy Routing", ["computer_science"], "贪婪路由"),
            ]
        )

    def test_exact_expansion_batch_143_adds_green_and_greenhouse_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("green_chemistry_technology", "Green Chemistry Technology", ["biomedical", "technology_industry_and_agriculture"], "绿色化学技术"),
                ("green_computing", "Green Computing", ["computers_and_information_processing"], "绿色计算"),
                ("green_fluorescent_protein", "Green Fluorescent Proteins", ["biomedical", "chemicals_and_drugs"], "绿色荧光蛋白"),
                ("green_hydrogen", "Green Hydrogen", ["materials_elements_and_compounds"], "绿氢"),
                ("greenhouse_gase", "Greenhouse Gases", ["biomedical", "chemicals_and_drugs"], "温室气体"),
            ]
        )

    def test_exact_expansion_batch_144_adds_grey_and_grid_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("grey_relational_analysi", "Grey Relational Analysis", ["computer_science"], "灰色关联分析"),
                ("grey_system_theory", "Grey System Theory", ["computer_science"], "灰色系统理论"),
                ("grid_cell", "Grid Cells", ["anatomy", "biomedical"], "网格细胞"),
                ("grid_computing", "Grid Computing", ["computers_and_information_processing"], "网格计算"),
                ("grid_scheduling", "Grid Scheduling", ["computer_science"], "网格调度"),
            ]
        )

    def test_exact_expansion_batch_145_adds_ground_and_group_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ground_moving_target_indication", "Ground Moving Target Indication", ["computer_science"], "地面运动目标指示"),
                ("ground_penetrating_radar", "Ground Penetrating Radar", ["electromagnetic_compatibility_and_interference"], "探地雷达"),
                ("ground_station", "Ground Stations", ["computer_science"], "地面站"),
                ("grounded_theory", "Grounded Theory", ["biomedical", "disciplines_and_occupations"], "扎根理论"),
                ("group_decision", "Group Decision", ["computer_science"], "群决策"),
            ]
        )

    def test_exact_expansion_batch_146_adds_group_key_and_group_theory_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("group_i_chaperonin", "Group I Chaperonins", ["biomedical", "chemicals_and_drugs"], "I组伴侣蛋白"),
                ("group_key_agreement", "Group Key Agreement", ["computer_science"], "群组密钥协商"),
                ("group_signature", "Group Signature", ["computer_science"], "群签名"),
                ("group_support_system", "Group Support Systems", ["computer_science"], "群体支持系统"),
                ("group_theory", "Group Theory", ["mathematics"], "群论"),
            ]
        )

    def test_exact_expansion_batch_147_adds_growth_factor_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("growth_arrest_specific_protein_6", "Growth Arrest-specific Protein 6", ["biomedical", "chemicals_and_drugs"], "生长停滞特异性蛋白6"),
                ("growth_con", "Growth Cones", ["anatomy", "biomedical"], "生长锥"),
                ("growth_differentiation_factor_15", "Growth Differentiation Factor 15", ["biomedical", "chemicals_and_drugs"], "生长分化因子15"),
                ("growth_disorder", "Growth Disorders", ["biomedical", "diseases"], "生长障碍"),
                ("growth_hormone_releasing_hormone", "Growth Hormone-releasing Hormone", ["biomedical", "chemicals_and_drugs"], "生长激素释放激素"),
            ]
        )

    def test_exact_expansion_batch_148_adds_gtp_and_guanidine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gtp_binding_protein", "Gtp-binding Proteins", ["biomedical", "chemicals_and_drugs"], "GTP结合蛋白"),
                ("gtp_cyclohydrolase", "GTP Cyclohydrolase", ["biomedical", "chemicals_and_drugs"], "GTP环化水解酶"),
                ("gtpase_activating_protein", "Gtpase-activating Proteins", ["biomedical", "chemicals_and_drugs"], "GTP酶激活蛋白"),
                ("guanidinoacetate_n_methyltransferase", "Guanidinoacetate N-methyltransferase", ["biomedical", "chemicals_and_drugs"], "胍基乙酸N-甲基转移酶"),
                ("guanine", "Guanine", ["biomedical", "chemicals_and_drugs"], "鸟嘌呤"),
            ]
        )

    def test_exact_expansion_batch_149_adds_guanine_and_guanosine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("guanine_nucleotide_exchange_factor", "Guanine Nucleotide Exchange Factors", ["biomedical", "chemicals_and_drugs"], "鸟嘌呤核苷酸交换因子"),
                ("guanosine_diphosphate_fucose", "Guanosine Diphosphate Fucose", ["biomedical", "chemicals_and_drugs"], "鸟苷二磷酸岩藻糖"),
                ("guanosine_monophosphate", "Guanosine Monophosphate", ["biomedical", "chemicals_and_drugs"], "鸟苷一磷酸"),
                ("guanosine_triphosphate", "Guanosine Triphosphate", ["biomedical", "chemicals_and_drugs"], "鸟苷三磷酸"),
                ("guanylate_cyclase", "Guanylate Cyclase", ["biomedical", "chemicals_and_drugs"], "鸟苷酸环化酶"),
            ]
        )

    def test_exact_expansion_batch_150_adds_guidance_guideline_and_gun_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gui_testing", "Gui Testing", ["computer_science"], "GUI测试"),
                ("guidance_and_control_system", "Guidance And Control Systems", ["engineering", "physical_sciences"], "制导与控制系统"),
                ("guided_tissue_regeneration_periodontal", "Guided Tissue Regeneration, Periodontal", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "牙周引导组织再生"),
                ("guideline_adherence", "Guideline Adherence", ["biomedical", "health_care"], "指南依从性"),
                ("gunshot_detection_system", "Gunshot Detection Systems", ["aerospace_and_electronic_systems"], "枪声检测系统"),
            ]
        )

    def test_exact_expansion_batch_151_adds_gwas_gynecology_and_gyro_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("gwas", "Gwas", ["computer_science"], "全基因组关联研究"),
                ("gynecologic_surgical_procedur", "Gynecologic Surgical Procedures", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "妇科外科手术"),
                ("gynecology", "Gynecology", ["engineering_in_medicine_and_biology"], "妇科学"),
                ("gyroscopes", "Gyroscopes", ["control_systems"], "陀螺仪"),
                ("gyrotron", "Gyrotrons", ["microwave_theory_and_techniques"], "回旋管"),
            ]
        )

    def test_exact_expansion_batch_152_adds_h264_haar_and_habitat_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("h_264_avc_encoder", "H.264/avc Encoder", ["computer_science"], "H.264/AVC编码器"),
                ("h_infinity_control", "H Infinity Control", ["mathematics"], "H∞控制"),
                ("haar_like_featur", "Haar-like Features", ["computer_science"], "Haar样特征"),
                ("habenula", "Habenula", ["anatomy", "biomedical"], "缰核"),
                ("habitat_loss", "Habitat Loss", ["environmental_degradation"], "栖息地丧失"),
            ]
        )

    def test_exact_expansion_batch_153_adds_haemophilus_hafnium_and_hair_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("haemophilu_influenzae", "Haemophilus Influenzae", ["biomedical", "organisms"], "流感嗜血杆菌"),
                ("haemophilu_influenzae_type_b", "Haemophilus Influenzae Type B", ["biomedical", "organisms"], "b型流感嗜血杆菌"),
                ("hafnium_compound", "Hafnium Compounds", ["materials_elements_and_compounds"], "铪化合物"),
                ("hair_cell_auditory_inner", "Hair Cells, Auditory, Inner", ["anatomy", "biomedical"], "内毛细胞"),
                ("hair_follicle", "Hair Follicle", ["anatomy", "biomedical"], "毛囊"),
            ]
        )

    def test_exact_expansion_batch_154_adds_hair_half_duplex_and_hallux_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hair_removal", "Hair Removal", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "脱毛"),
                ("half_duplex_relay", "Half-duplex Relay", ["computer_science"], "半双工中继"),
                ("half_life", "Half-life", ["biomedical", "phenomena_and_processes"], "半衰期"),
                ("hall_effect_devic", "Hall Effect Devices", ["electron_devices"], "霍尔效应器件"),
                ("hallux_valgu", "Hallux Valgus", ["biomedical", "diseases"], "拇外翻"),
            ]
        )

    def test_exact_expansion_batch_155_adds_halogen_haloperidol_and_hamartoma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("halogen", "Halogens", ["biomedical", "chemicals_and_drugs"], "卤素"),
                ("halogenated_diphenyl_ether", "Halogenated Diphenyl Ethers", ["biomedical", "chemicals_and_drugs"], "卤代二苯醚"),
                ("haloperidol", "Haloperidol", ["biomedical", "chemicals_and_drugs"], "氟哌啶醇"),
                ("ham_radio", "Ham Radios", ["communications_technology"], "业余无线电"),
                ("hamartoma_syndrome_multiple", "Hamartoma Syndrome, Multiple", ["biomedical", "diseases"], "多发性错构瘤综合征"),
            ]
        )

    def test_exact_expansion_batch_156_adds_hamming_and_hand_disease_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hamiltonian_system", "Hamiltonian Systems", ["physics"], "哈密顿系统"),
                ("hamming_distance", "Hamming Distance", ["computer_science"], "汉明距离"),
                ("hand_arm_vibration_syndrome", "Hand-arm Vibration Syndrome", ["biomedical", "diseases"], "手臂振动综合征"),
                ("hand_dermatose", "Hand Dermatoses", ["biomedical", "diseases"], "手部皮肤病"),
                ("hand_foot_and_mouth_disease", "Hand, Foot And Mouth Disease", ["biomedical", "diseases"], "手足口病"),
            ]
        )

    def test_exact_expansion_batch_157_adds_hand_gesture_and_device_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hand_gesture_recognition", "Hand Gesture Recognition", ["computer_science"], "手势识别"),
                ("hand_held_device", "Hand Held Device", ["computer_science"], "手持设备"),
                ("hand_posture_recognition", "Hand Posture Recognition", ["computer_science"], "手部姿态识别"),
                ("hand_tracking", "Hand Tracking", ["computer_science"], "手部跟踪"),
                ("hand_written_character_recognition", "Hand Written Character Recognition", ["computer_science"], "手写字符识别"),
            ]
        )

    def test_exact_expansion_batch_158_adds_handwriting_hantavirus_and_haptic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("handwriting_recognition", "Handwriting Recognition", ["computers_and_information_processing"], "手写识别"),
                ("handwritten_chinese_character", "Handwritten Chinese Character", ["computer_science"], "手写汉字"),
                ("hantavirus_pulmonary_syndrome", "Hantavirus Pulmonary Syndrome", ["biomedical", "diseases"], "汉坦病毒肺综合征"),
                ("haploinsufficiency", "Haploinsufficiency", ["biomedical", "phenomena_and_processes"], "单倍剂量不足"),
                ("haptic_feedback", "Haptic Feedback", ["computer_science"], "触觉反馈"),
            ]
        )

    def test_exact_expansion_batch_159_adds_haptic_and_hardware_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("haptic_rendering", "Haptic Rendering", ["computer_science"], "触觉渲染"),
                ("hardware_acceleration", "Hardware Acceleration", ["computers_and_information_processing"], "硬件加速"),
                ("hardware_description_languag", "Hardware Description Languages", ["computer_science"], "硬件描述语言"),
                ("hardware_in_the_loop_simulation", "Hardware-in-the-loop Simulation", ["systems_engineering_and_theory"], "硬件在环仿真"),
                ("hardware_software_partitioning", "Hardware/software Partitioning", ["computer_science"], "软硬件划分"),
            ]
        )

    def test_exact_expansion_batch_160_adds_harmonic_hash_and_hashimoto_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("harmful_algal_bloom", "Harmful Algal Bloom", ["biomedical", "phenomena_and_processes"], "有害藻华"),
                ("harmonic_distortion", "Harmonic Distortion", ["signal_processing"], "谐波失真"),
                ("harri_corner_detection", "Harris Corner Detection", ["computer_science"], "Harris角点检测"),
                ("hash_function", "Hash Functions", ["computer_science", "mathematics"], "哈希函数"),
                ("hashimoto_disease", "Hashimoto Disease", ["biomedical", "diseases"], "桥本病"),
            ]
        )

    def test_exact_expansion_batch_161_adds_hazard_head_and_display_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hazard_ratio", "Hazard Ratio", ["computer_science"], "风险比"),
                ("hcv_ns3_4a_protease_inhibitor", "HCV Ns3-4a Protease Inhibitors", ["biomedical", "chemicals_and_drugs"], "HCV NS3/4A蛋白酶抑制剂"),
                ("head_impulse_test", "Head Impulse Test", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "头脉冲试验"),
                ("head_mounted_display", "Head-mounted Displays", ["systems_man_and_cybernetics"], "头戴式显示器"),
                ("head_pose_estimation", "Head Pose Estimation", ["computer_science"], "头部姿态估计"),
            ]
        )

    def test_exact_expansion_batch_162_adds_health_care_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("health_belief_model", "Health Belief Model", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "健康信念模型"),
                ("health_care_cost", "Health Care Costs", ["biomedical", "health_care"], "医疗保健费用"),
                ("health_care_evaluation_mechanism", "Health Care Evaluation Mechanisms", ["biomedical", "health_care"], "医疗保健评价机制"),
                ("health_care_reform", "Health Care Reform", ["anthropology_education_sociology_and_social_phenomena", "biomedical"], "医疗保健改革"),
                ("health_equity", "Health Equity", ["biomedical", "health_care"], "健康公平"),
            ]
        )

    def test_exact_expansion_batch_163_adds_health_facility_and_service_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("health_facility_administration", "Health Facility Administration", ["biomedical", "health_care"], "卫生设施管理"),
                ("health_impact_assessment", "Health Impact Assessment", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "健康影响评估"),
                ("health_information_exchange", "Health Information Exchange", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "健康信息交换"),
                ("health_record_personal", "Health Records, Personal", ["computer_science"], "个人健康记录"),
                ("health_statu_indicator", "Health Status Indicators", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "健康状况指标"),
            ]
        )

    def test_exact_expansion_batch_164_adds_healthcare_hearing_and_healthy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("healthcare_associated_pneumonia", "Healthcare-associated Pneumonia", ["biomedical", "diseases"], "医疗相关性肺炎"),
                ("healthcare_failure_mode_and_effect_analysi", "Healthcare Failure Mode And Effect Analysis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "医疗保健失效模式与影响分析"),
                ("healthy_life_expectancy", "Healthy Life Expectancy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "健康预期寿命"),
                ("hearing_loss_sensorineural", "Hearing Loss, Sensorineural", ["biomedical", "diseases"], "感音神经性听力损失"),
                ("hearing_test", "Hearing Tests", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "听力测试"),
            ]
        )

    def test_exact_expansion_batch_165_adds_heart_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("heart_assist_devic", "Heart-assist Devices", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "心脏辅助装置"),
                ("heart_conduction_system", "Heart Conduction System", ["anatomy", "biomedical"], "心脏传导系统"),
                ("heart_failure_systolic", "Heart Failure, Systolic", ["biomedical", "diseases"], "收缩性心力衰竭"),
                ("heart_lung_transplantation", "Heart-lung Transplantation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "心肺移植"),
                ("heart_valve_prosthesi_implantation", "Heart Valve Prosthesis Implantation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "心脏瓣膜假体植入"),
            ]
        )

    def test_exact_expansion_batch_166_adds_heat_heavy_and_hedgehog_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("heat_assisted_magnetic_recording", "Heat-assisted Magnetic Recording", ["signal_processing"], "热辅助磁记录"),
                ("heat_shock_protein", "Heat-shock Proteins", ["biomedical", "chemicals_and_drugs"], "热休克蛋白"),
                ("heat_stroke", "Heat Stroke", ["biomedical", "diseases"], "热射病"),
                ("heavy_ion_radiotherapy", "Heavy Ion Radiotherapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "重离子放射治疗"),
                ("hedgehog_protein", "Hedgehog Proteins", ["biomedical", "chemicals_and_drugs"], "Hedgehog蛋白"),
            ]
        )

    def test_exact_expansion_batch_167_adds_heel_helicobacter_and_helium_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("heimlich_maneuver", "Heimlich Maneuver", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "海姆立克急救法"),
                ("helical_antenna", "Helical Antennas", ["antennas_and_propagation"], "螺旋天线"),
                ("helicobacter_infection", "Helicobacter Infections", ["biomedical", "diseases"], "螺杆菌感染"),
                ("helicobacter_hepaticu", "Helicobacter Hepaticus", ["biomedical", "organisms"], "肝螺杆菌"),
                ("helioseismology", "Helioseismology", ["nuclear_and_plasma_sciences"], "日震学"),
            ]
        )

    def test_exact_expansion_batch_168_adds_helix_helminth_and_hemagglutination_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("helix_loop_helix_motif", "Helix-loop-helix Motifs", ["biomedical", "phenomena_and_processes"], "螺旋-环-螺旋基序"),
                ("hellp_syndrome", "Hellp Syndrome", ["biomedical", "diseases"], "HELLP综合征"),
                ("helmholtz_equation", "Helmholtz Equation", ["computer_science"], "亥姆霍兹方程"),
                ("helminthiasi", "Helminthiasis", ["biomedical", "diseases"], "蠕虫病"),
                ("hemagglutination_inhibition_test", "Hemagglutination Inhibition Tests", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "血凝抑制试验"),
            ]
        )

    def test_exact_expansion_batch_169_adds_hemagglutinin_and_hemangioma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hemagglutinin", "Hemagglutinins", ["biomedical", "chemicals_and_drugs"], "血凝素"),
                ("hemagglutinin_glycoprotein_influenza_viru", "Hemagglutinin Glycoproteins, Influenza Virus", ["biomedical", "chemicals_and_drugs"], "流感病毒血凝素糖蛋白"),
                ("hemangioblastoma", "Hemangioblastoma", ["biomedical", "diseases"], "血管母细胞瘤"),
                ("hemangioma_cavernou", "Hemangioma, Cavernous", ["biomedical", "diseases"], "海绵状血管瘤"),
                ("hematocrit", "Hematocrit", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "血细胞比容"),
            ]
        )

    def test_exact_expansion_batch_170_adds_hematologic_and_hematoma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hematologic_disease", "Hematologic Diseases", ["biomedical", "diseases"], "血液病"),
                ("hematologic_neoplasm", "Hematologic Neoplasms", ["biomedical", "diseases"], "血液系统肿瘤"),
                ("hematoma_epidural_cranial", "Hematoma, Epidural, Cranial", ["biomedical", "diseases"], "颅内硬膜外血肿"),
                ("hematoma_subdural_chronic", "Hematoma, Subdural, Chronic", ["biomedical", "diseases"], "慢性硬膜下血肿"),
                ("hematopoietic_stem_cell_transplantation", "Hematopoietic Stem Cell Transplantation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "造血干细胞移植"),
            ]
        )

    def test_exact_expansion_batch_171_adds_heme_and_hemi_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hematoxylin", "Hematoxylin", ["biomedical", "chemicals_and_drugs"], "苏木精"),
                ("heme_binding_protein", "Heme-binding Proteins", ["biomedical", "chemicals_and_drugs"], "血红素结合蛋白"),
                ("heme_oxygenase_1", "Heme Oxygenase-1", ["biomedical", "chemicals_and_drugs"], "血红素加氧酶-1"),
                ("hemianopsia", "Hemianopsia", ["biomedical", "diseases"], "偏盲"),
                ("hemifacial_spasm", "Hemifacial Spasm", ["biomedical", "diseases"], "面肌痉挛"),
            ]
        )

    def test_exact_expansion_batch_172_adds_hemodynamic_and_hemoglobin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hemochromatosi", "Hemochromatosis", ["biomedical", "diseases"], "血色病"),
                ("hemodiafiltration", "Hemodiafiltration", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "血液透析滤过"),
                ("hemodynamic", "Hemodynamics", ["biomedical", "phenomena_and_processes"], "血流动力学"),
                ("hemoglobin_sickle", "Hemoglobin, Sickle", ["biomedical", "chemicals_and_drugs"], "镰状血红蛋白"),
                ("hemoglobinometry", "Hemoglobinometry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "血红蛋白测定"),
            ]
        )

    def test_exact_expansion_batch_173_adds_hemolysis_and_hemorrhagic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hemoglobinopathy", "Hemoglobinopathies", ["biomedical", "diseases"], "血红蛋白病"),
                ("hemolysi", "Hemolysis", ["biomedical", "diseases"], "溶血"),
                ("hemolytic_uremic_syndrome", "Hemolytic-uremic Syndrome", ["biomedical", "diseases"], "溶血性尿毒综合征"),
                ("hemoperfusion", "Hemoperfusion", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "血液灌流"),
                ("hemorrhagic_fever_with_renal_syndrome", "Hemorrhagic Fever With Renal Syndrome", ["biomedical", "diseases"], "肾综合征出血热"),
            ]
        )

    def test_exact_expansion_batch_174_adds_hemostasis_and_hemt_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hemorrhagic_stroke", "Hemorrhagic Stroke", ["biomedical", "diseases"], "出血性卒中"),
                ("hemosiderosi_pulmonary", "Hemosiderosis, Pulmonary", ["biomedical", "diseases"], "肺含铁血黄素沉着症"),
                ("hemostatic_techniqu", "Hemostatic Techniques", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "止血技术"),
                ("hemothorax", "Hemothorax", ["biomedical", "diseases"], "血胸"),
                ("hemt", "Hemts", ["solid_state_circuits"], "高电子迁移率晶体管"),
            ]
        )

    def test_exact_expansion_batch_175_adds_heparan_heparin_and_hepatic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("heparan_sulfate", "Heparan Sulfate", ["biomedical", "chemicals_and_drugs"], "硫酸乙酰肝素"),
                ("heparin", "Heparin", ["biomedical", "chemicals_and_drugs"], "肝素"),
                ("heparin_binding_egf_like_growth_factor", "Heparin-binding Egf-like Growth Factor", ["biomedical", "chemicals_and_drugs"], "肝素结合EGF样生长因子"),
                ("hepatectomy", "Hepatectomy", ["engineering_in_medicine_and_biology"], "肝切除术"),
                ("hepatic_encephalopathy", "Hepatic Encephalopathy", ["biomedical", "diseases"], "肝性脑病"),
            ]
        )

    def test_exact_expansion_batch_176_adds_hepatitis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hepatiti_alcoholic", "Hepatitis, Alcoholic", ["biomedical", "diseases"], "酒精性肝炎"),
                ("hepatiti_autoimmune", "Hepatitis, Autoimmune", ["biomedical", "diseases"], "自身免疫性肝炎"),
                ("hepatiti_b_e_antigen", "Hepatitis B E Antigens", ["biomedical", "chemicals_and_drugs"], "乙型肝炎e抗原"),
                ("hepatiti_d_chronic", "Hepatitis D, Chronic", ["biomedical", "diseases"], "慢性丁型肝炎"),
                ("hepatiti_viral_human", "Hepatitis, Viral, Human", ["biomedical", "diseases"], "人病毒性肝炎"),
            ]
        )

    def test_exact_expansion_batch_177_adds_hepatocyte_and_heptose_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hepatoblastoma", "Hepatoblastoma", ["biomedical", "diseases"], "肝母细胞瘤"),
                ("hepatocyte_nuclear_factor_4", "Hepatocyte Nuclear Factor 4", ["biomedical", "chemicals_and_drugs"], "肝细胞核因子4"),
                ("hepatolenticular_degeneration", "Hepatolenticular Degeneration", ["biomedical", "diseases"], "肝豆状核变性"),
                ("hepatopulmonary_syndrome", "Hepatopulmonary Syndrome", ["biomedical", "diseases"], "肝肺综合征"),
                ("heptavalent_pneumococcal_conjugate_vaccine", "Heptavalent Pneumococcal Conjugate Vaccine", ["biomedical", "chemicals_and_drugs"], "七价肺炎球菌结合疫苗"),
            ]
        )

    def test_exact_expansion_batch_178_adds_herbal_hereditary_and_herpes_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("herb_drug_interaction", "Herb-drug Interactions", ["biomedical", "phenomena_and_processes"], "草药-药物相互作用"),
                ("herbal_medicine", "Herbal Medicine", ["biomedical", "disciplines_and_occupations"], "草药医学"),
                ("herbicide_resistance", "Herbicide Resistance", ["biomedical", "phenomena_and_processes"], "除草剂抗性"),
                ("hereditary_angioedema_type_iii", "Hereditary Angioedema Type III", ["biomedical", "diseases"], "III型遗传性血管性水肿"),
                ("herpes_simplex", "Herpes Simplex", ["biomedical", "diseases"], "单纯疱疹"),
            ]
        )

    def test_exact_expansion_batch_179_adds_hernia_hexokinase_and_hidden_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hernia_hiatal", "Hernia, Hiatal", ["biomedical", "diseases"], "食管裂孔疝"),
                ("herpes_zoster_vaccine", "Herpes Zoster Vaccine", ["biomedical", "chemicals_and_drugs"], "带状疱疹疫苗"),
                ("hexachlorophene", "Hexachlorophene", ["biomedical", "chemicals_and_drugs"], "六氯酚"),
                ("hexokinase", "Hexokinase", ["biomedical", "chemicals_and_drugs"], "己糖激酶"),
                ("hidden_markov_model", "Hidden Markov Models", ["systems_engineering_and_theory"], "隐马尔可夫模型"),
            ]
        )

    def test_exact_expansion_batch_180_adds_hierarchical_and_high_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hierarchical_cluster_analysi", "Hierarchical Cluster Analysis", ["computer_science"], "层次聚类分析"),
                ("hierarchical_reinforcement_learning", "Hierarchical Reinforcement Learning", ["computer_science"], "层次强化学习"),
                ("high_dimensional_data", "High Dimensional Data", ["computational_and_artificial_intelligence"], "高维数据"),
                ("high_intensity_focused_ultrasound_ablation", "High-intensity Focused Ultrasound Ablation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "高强度聚焦超声消融"),
                ("high_performance_computing", "High Performance Computing", ["computers_and_information_processing"], "高性能计算"),
            ]
        )

    def test_exact_expansion_batch_181_adds_high_power_and_signal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("high_electron_mobility_transistor", "High Electron Mobility Transistors", ["computer_science"], "高电子迁移率晶体管"),
                ("high_energy_laser", "High Energy Lasers", ["computer_science"], "高能激光器"),
                ("high_power_fiber_laser", "High Power Fiber Lasers", ["computer_science"], "高功率光纤激光器"),
                ("high_power_microwave_generation", "High Power Microwave Generation", ["microwave_theory_and_techniques"], "高功率微波产生"),
                ("high_signal_to_noise_ratio", "High Signal-to-noise Ratio", ["computer_science"], "高信噪比"),
            ]
        )

    def test_exact_expansion_batch_182_adds_high_video_and_physics_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("high_definition_television", "High Definition Television", ["computer_science"], "高清电视"),
                ("high_definition_video", "High Definition Video", ["signal_processing"], "高清视频"),
                ("high_dimensionality", "High Dimensionality", ["computer_science"], "高维性"),
                ("high_energy_physic_experiment", "High Energy Physics - Experiment", ["physics_high_energy"], "高能物理实验"),
                ("high_energy_physic_lattice", "High Energy Physics - Lattice", ["physics_high_energy"], "格点高能物理"),
            ]
        )

    def test_exact_expansion_batch_183_adds_high_frequency_and_language_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("high_frequency_jet_ventilation", "High-frequency Jet Ventilation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "高频喷射通气"),
                ("high_intensity_interval_training", "High-intensity Interval Training", ["biomedical", "phenomena_and_processes"], "高强度间歇训练"),
                ("high_k_dielectric_material", "High-k Dielectric Materials", ["materials_elements_and_compounds"], "高k介电材料"),
                ("high_level_languag", "High Level Languages", ["computer_science"], "高级语言"),
                ("high_level_petri_nets", "High-level Petri Nets", ["computer_science"], "高级Petri网"),
            ]
        )

    def test_exact_expansion_batch_184_adds_high_order_and_resolution_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("high_order_accuracy", "High-order Accuracy", ["computer_science"], "高阶精度"),
                ("high_order_method", "High-order Methods", ["computer_science"], "高阶方法"),
                ("high_quality_solution", "High-quality Solutions", ["computer_science"], "高质量解"),
                ("high_resolution_imaging", "High-resolution Imaging", ["computers_and_information_processing"], "高分辨率成像"),
                ("high_speed_electronic", "High-speed Electronics", ["communications_technology"], "高速电子学"),
            ]
        )

    def test_exact_expansion_batch_185_adds_higher_and_hilbert_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("higher_order_logic", "Higher Order Logic", ["computer_science"], "高阶逻辑"),
                ("higher_order_statistic", "Higher Order Statistics", ["mathematics"], "高阶统计量"),
                ("hilbert_space", "Hilbert Space", ["mathematics"], "希尔伯特空间"),
                ("hilbert_transform", "Hilbert Transform", ["computer_science"], "希尔伯特变换"),
                ("hilbert_huang_transform", "Hilbert-huang Transform", ["computer_science"], "希尔伯特-黄变换"),
            ]
        )

    def test_exact_expansion_batch_186_adds_hip_and_hippo_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hip_contracture", "Hip Contracture", ["biomedical", "diseases"], "髋关节挛缩"),
                ("hip_dislocation", "Hip Dislocation", ["biomedical", "diseases"], "髋关节脱位"),
                ("hip_joint", "Hip Joint", ["anatomy", "biomedical"], "髋关节"),
                ("hip_prosthesi", "Hip Prosthesis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "髋关节假体"),
                ("hippo_signaling_pathway", "Hippo Signaling Pathway", ["biomedical", "phenomena_and_processes"], "Hippo信号通路"),
                ("hippo_pathway_signaling_and_yap_taz", "Hippo Pathway Signaling And Yap/taz", ["biochemistry_genetics_and_molecular_biology", "life_sciences"], "Hippo-YAP/TAZ信号通路"),
            ]
        )

    def test_exact_expansion_batch_187_adds_histamine_and_histidine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("histamine_antagonist", "Histamine Antagonists", ["biomedical", "chemicals_and_drugs"], "组胺拮抗剂"),
                ("histamine_h1_antagonist", "Histamine H1 Antagonists", ["biomedical", "chemicals_and_drugs"], "组胺H1拮抗剂"),
                ("histidine", "Histidine", ["biomedical", "chemicals_and_drugs"], "组氨酸"),
                ("histidine_kinase", "Histidine Kinase", ["biomedical", "chemicals_and_drugs"], "组氨酸激酶"),
                ("histidine_rich_glycoprotein", "Histidine-rich Glycoprotein", ["biomedical", "chemicals_and_drugs"], "富组氨酸糖蛋白"),
            ]
        )

    def test_exact_expansion_batch_188_adds_histocompatibility_and_histone_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("histocompatibility_antigen", "Histocompatibility Antigens", ["biomedical", "chemicals_and_drugs"], "组织相容性抗原"),
                ("histocompatibility_antigen_class_i", "Histocompatibility Antigens Class I", ["biomedical", "chemicals_and_drugs"], "I类组织相容性抗原"),
                ("histology", "Histology", ["biomedical", "disciplines_and_occupations"], "组织学"),
                ("histone_deacetylase_inhibitor", "Histone Deacetylase Inhibitors", ["biomedical", "chemicals_and_drugs"], "组蛋白去乙酰化酶抑制剂"),
                ("histone_methyltransferase", "Histone Methyltransferases", ["biomedical", "chemicals_and_drugs"], "组蛋白甲基转移酶"),
            ]
        )

    def test_exact_expansion_batch_189_adds_hiv_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hiv_antibody", "HIV Antibodies", ["biomedical", "chemicals_and_drugs"], "HIV抗体"),
                ("hiv_core_protein_p24", "HIV Core Protein P24", ["biomedical", "chemicals_and_drugs"], "HIV核心蛋白p24"),
                ("hiv_envelope_protein_gp120", "HIV Envelope Protein Gp120", ["biomedical", "chemicals_and_drugs"], "HIV包膜蛋白gp120"),
                ("hiv_integrase_inhibitor", "HIV Integrase Inhibitors", ["biomedical", "chemicals_and_drugs"], "HIV整合酶抑制剂"),
                ("hiv_reverse_transcriptase", "HIV Reverse Transcriptase", ["biomedical", "chemicals_and_drugs"], "HIV逆转录酶"),
            ]
        )

    def test_exact_expansion_batch_190_adds_hla_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hla_antigen", "HLA Antigens", ["biomedical", "chemicals_and_drugs"], "HLA抗原"),
                ("hla_a2_antigen", "Hla-a2 Antigen", ["biomedical", "chemicals_and_drugs"], "HLA-A2抗原"),
                ("hla_b27_antigen", "Hla-b27 Antigen", ["biomedical", "chemicals_and_drugs"], "HLA-B27抗原"),
                ("hla_drb1_chain", "Hla-drb1 Chains", ["biomedical", "chemicals_and_drugs"], "HLA-DRB1链"),
                ("hla_g_antigen", "Hla-g Antigens", ["biomedical", "chemicals_and_drugs"], "HLA-G抗原"),
            ]
        )

    def test_exact_expansion_batch_191_adds_hmg_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hmg_box_domain", "Hmg-box Domains", ["biomedical", "phenomena_and_processes"], "HMG盒结构域"),
                ("hmga_protein", "HMGA Proteins", ["biomedical", "chemicals_and_drugs"], "HMGA蛋白"),
                ("hmga2_protein", "Hmga2 Protein", ["biomedical", "chemicals_and_drugs"], "HMGA2蛋白"),
                ("hmgb1_protein", "Hmgb1 Protein", ["biomedical", "chemicals_and_drugs"], "HMGB1蛋白"),
                ("hmgn1_protein", "Hmgn1 Protein", ["biomedical", "chemicals_and_drugs"], "HMGN1蛋白"),
            ]
        )

    def test_exact_expansion_batch_192_adds_hoarding_hodgkin_and_holography_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hoarding_disorder", "Hoarding Disorder", ["biomedical", "psychiatry_and_psychology"], "囤积障碍"),
                ("hoare_logic", "Hoare Logic", ["computer_science"], "Hoare逻辑"),
                ("hodgkin_disease", "Hodgkin Disease", ["biomedical", "diseases"], "霍奇金病"),
                ("holmium_laser", "Holmium Laser", ["computer_science"], "钬激光"),
                ("holographic_display", "Holographic Displays", ["computer_science"], "全息显示器"),
            ]
        )

    def test_exact_expansion_batch_193_adds_home_care_and_gateway_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("home_applianc", "Home Appliances", ["computer_science"], "家用电器"),
                ("home_automation", "Home Automation", ["consumer_electronics"], "家庭自动化"),
                ("home_care_agency", "Home Care Agencies", ["biomedical", "health_care"], "家庭护理机构"),
                ("home_care_servic", "Home Care Services", ["biomedical", "health_care", "qualifiers"], "家庭护理服务"),
                ("home_gateway", "Home Gateway", ["computer_science"], "家庭网关"),
            ]
        )

    def test_exact_expansion_batch_194_adds_home_health_and_network_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("home_health_aid", "Home Health Aides", ["biomedical", "named_groups"], "居家健康助理"),
                ("home_health_nursing", "Home Health Nursing", ["biomedical", "disciplines_and_occupations"], "居家健康护理"),
                ("home_infusion_therapy", "Home Infusion Therapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "居家输液治疗"),
                ("home_network", "Home Network", ["computer_science"], "家庭网络"),
                ("home_nursing", "Home Nursing", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical", "health_care"], "居家护理"),
            ]
        )

    def test_exact_expansion_batch_195_adds_homeobox_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("homeobox_a1_protein", "Homeobox A1 Protein", ["biomedical", "chemicals_and_drugs"], "同源盒A1蛋白"),
                ("homeobox_a10_protein", "Homeobox A10 Proteins", ["biomedical", "chemicals_and_drugs"], "同源盒A10蛋白"),
                ("homeobox_protein_nkx_2_5", "Homeobox Protein Nkx-2.5", ["biomedical", "chemicals_and_drugs"], "同源盒蛋白Nkx-2.5"),
                ("homeodomain_protein", "Homeodomain Proteins", ["biomedical", "chemicals_and_drugs"], "同源结构域蛋白"),
                ("homeopathy", "Homeopathy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "顺势疗法"),
            ]
        )

    def test_exact_expansion_batch_196_adds_homologous_and_homocysteine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("homologou_recombination", "Homologous Recombination", ["biomedical", "phenomena_and_processes"], "同源重组"),
                ("homocysteine_s_methyltransferase", "Homocysteine S-methyltransferase", ["biomedical", "chemicals_and_drugs"], "同型半胱氨酸S-甲基转移酶"),
                ("homocystinuria", "Homocystinuria", ["biomedical", "diseases"], "同型胱氨酸尿症"),
                ("homogeneou_network", "Homogeneous Network", ["computer_science", "physics"], "同构网络"),
                ("homophobia", "Homophobia", ["biomedical", "psychiatry_and_psychology"], "恐同"),
            ]
        )

    def test_exact_expansion_batch_197_adds_hormone_and_hospital_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hormone_antagonist", "Hormone Antagonists", ["biomedical", "chemicals_and_drugs"], "激素拮抗剂"),
                ("hormone_replacement_therapy", "Hormone Replacement Therapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "激素替代疗法"),
                ("hormon", "Hormones", ["biomedical", "chemicals_and_drugs"], "激素"),
                ("hospital_administration", "Hospital Administration", ["biomedical", "disciplines_and_occupations"], "医院管理"),
                ("hospital_bed_capacity", "Hospital Bed Capacity", ["biomedical", "health_care"], "医院床位容量"),
            ]
        )

    def test_exact_expansion_batch_198_adds_hospital_information_and_record_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hospital_charg", "Hospital Charges", ["biomedical", "health_care"], "医院收费"),
                ("hospital_cost", "Hospital Costs", ["biomedical", "health_care"], "医院费用"),
                ("hospital_information_system", "Hospital Information System", ["computer_science"], "医院信息系统"),
                ("hospital_record", "Hospital Records", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "医院病历"),
                ("hospitalist", "Hospitalists", ["biomedical", "named_groups"], "住院医师"),
            ]
        )

    def test_exact_expansion_batch_199_adds_host_hot_and_huffman_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("host_cell_factor_c1", "Host Cell Factor C1", ["biomedical", "chemicals_and_drugs"], "宿主细胞因子C1"),
                ("host_parasite_interaction", "Host-parasite Interactions", ["biomedical", "phenomena_and_processes"], "宿主-寄生虫相互作用"),
                ("hot_flash", "Hot Flashes", ["biomedical", "diseases"], "潮热"),
                ("hough_transform", "Hough Transform", ["computer_science"], "霍夫变换"),
                ("huffman_coding", "Huffman Coding", ["computers_and_information_processing"], "哈夫曼编码"),
            ]
        )

    def test_exact_expansion_batch_200_adds_human_activity_and_biomedical_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("human_activity_recognition", "Human Activity Recognition", ["aerospace_and_electronic_systems"], "人体活动识别"),
                ("human_computer_interaction", "Human Computer Interaction", ["systems_man_and_cybernetics"], "人机交互"),
                ("human_embryonic_stem_cell", "Human Embryonic Stem Cells", ["anatomy", "biomedical"], "人胚胎干细胞"),
                ("human_growth_hormone", "Human Growth Hormone", ["biomedical", "chemicals_and_drugs"], "人生长激素"),
                ("human_papillomaviru_16", "Human Papillomavirus 16", ["biomedical", "organisms"], "16型人乳头瘤病毒"),
            ]
        )

    def test_exact_expansion_batch_201_adds_human_general_and_genome_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("human_action_recognition", "Human Action Recognition", ["computer_science"], "人体动作识别"),
                ("human_ai_collaboration", "Human-ai Collaboration", ["computer_science"], "人-AI协作"),
                ("human_challenge_trial", "Human Challenge Trials", ["biomedical", "publication_characteristics"], "人体挑战试验"),
                ("human_factor", "Human Factors", ["systems_man_and_cybernetics"], "人因"),
                ("human_genome_project", "Human Genome Project", ["biomedical", "phenomena_and_processes"], "人类基因组计划"),
            ]
        )

    def test_exact_expansion_batch_202_adds_human_vision_and_motion_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("human_face_detection", "Human Face Detection", ["computer_science"], "人脸检测"),
                ("human_face_recognition", "Human Face Recognition", ["computer_science"], "人脸识别"),
                ("human_in_the_loop", "Human In The Loop", ["systems_engineering_and_theory"], "人在环路"),
                ("human_motion_capture", "Human Motion Capture", ["computer_science"], "人体动作捕捉"),
                ("human_pose_estimation", "Human Pose Estimations", ["computer_science"], "人体姿态估计"),
            ]
        )

    def test_exact_expansion_batch_203_adds_human_papillomavirus_and_robot_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("human_papillomaviru_18", "Human Papillomavirus 18", ["biomedical", "organisms"], "18型人乳头瘤病毒"),
                ("human_papillomaviru_dna_test", "Human Papillomavirus DNA Tests", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "人乳头瘤病毒DNA检测"),
                ("human_robot_interaction", "Human-robot Interaction", ["systems_man_and_cybernetics"], "人与机器人交互"),
                ("human_t_lymphotropic_viru_1", "Human T-lymphotropic Virus 1", ["biomedical", "organisms"], "人T淋巴细胞病毒1型"),
                ("human_umbilical_vein_endothelial_cell", "Human Umbilical Vein Endothelial Cells", ["anatomy", "biomedical"], "人脐静脉内皮细胞"),
            ]
        )

    def test_exact_expansion_batch_204_adds_humanoid_humerus_and_hyaluronic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("humanoid_robot", "Humanoid Robots", ["robotics_and_automation"], "类人机器人"),
                ("humeral_fractur", "Humeral Fractures", ["biomedical", "diseases"], "肱骨骨折"),
                ("humidity_measurement", "Humidity Measurement", ["instrumentation_and_measurement"], "湿度测量"),
                ("hyaluronic_acid", "Hyaluronic Acid", ["biomedical", "chemicals_and_drugs"], "透明质酸"),
                ("hybrid_electric_vehicl", "Hybrid Electric Vehicles", ["vehicular_and_wireless_technologies"], "混合动力电动汽车"),
            ]
        )

    def test_exact_expansion_batch_205_adds_hybrid_hygiene_and_hypnosis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hybrid_metaheuristic", "Hybrid Metaheuristics", ["computer_science"], "混合元启发式"),
                ("hybrid_renal_replacement_therapy", "Hybrid Renal Replacement Therapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "混合肾脏替代治疗"),
                ("hybridoma", "Hybridomas", ["anatomy", "biomedical"], "杂交瘤"),
                ("hygiene_hypothesi", "Hygiene Hypothesis", ["biomedical", "humanities"], "卫生假说"),
                ("hypnosi_dental", "Hypnosis, Dental", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "牙科催眠"),
            ]
        )

    def test_exact_expansion_batch_206_adds_hydatidiform_and_hydraulic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hydantoin", "Hydantoins", ["biomedical", "chemicals_and_drugs"], "乙内酰脲类"),
                ("hydatidiform_mole", "Hydatidiform Mole", ["biomedical", "diseases"], "葡萄胎"),
                ("hydraulic_diameter", "Hydraulic Diameter", ["science_general"], "水力直径"),
                ("hydraulic_fracking", "Hydraulic Fracking", ["biomedical", "technology_industry_and_agriculture"], "水力压裂"),
                ("hydrazon", "Hydrazones", ["biomedical", "chemicals_and_drugs"], "腙类"),
            ]
        )

    def test_exact_expansion_batch_207_adds_hydrocarbon_and_hydrocephalus_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hydrobromic_acid", "Hydrobromic Acid", ["biomedical", "chemicals_and_drugs"], "氢溴酸"),
                ("hydrocarbon_aromatic", "Hydrocarbons, Aromatic", ["biomedical", "chemicals_and_drugs"], "芳香烃"),
                ("hydrocephalu_normal_pressure", "Hydrocephalus, Normal Pressure", ["biomedical", "diseases"], "正常压力脑积水"),
                ("hydrochlorothiazide", "Hydrochlorothiazide", ["biomedical", "chemicals_and_drugs"], "氢氯噻嗪"),
                ("hydrocortisone", "Hydrocortisone", ["biomedical", "chemicals_and_drugs"], "氢化可的松"),
            ]
        )

    def test_exact_expansion_batch_208_adds_hydrogen_and_hydrogel_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hydroelectric_power_generation", "Hydroelectric Power Generation", ["power_engineering_and_energy"], "水力发电"),
                ("hydrofluoric_acid", "Hydrofluoric Acid", ["biomedical", "chemicals_and_drugs"], "氢氟酸"),
                ("hydrogen_deuterium_exchange_mass_spectrometry", "Hydrogen Deuterium Exchange-mass Spectrometry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "氢氘交换质谱"),
                ("hydrogen_storage", "Hydrogen Storage", ["power_engineering_and_energy"], "储氢"),
                ("hydrogen_sulfide", "Hydrogen Sulfide", ["biomedical", "chemicals_and_drugs"], "硫化氢"),
            ]
        )

    def test_exact_expansion_batch_209_adds_hydrology_and_hydrophobic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hydrological_forecasting_using_ai", "Hydrological Forecasting Using AI", ["environmental_science", "physical_sciences"], "基于AI的水文预报"),
                ("hydrology_and_drought_analysi", "Hydrology And Drought Analysis", ["environmental_science", "physical_sciences"], "水文学与干旱分析"),
                ("hydromorphone", "Hydromorphone", ["biomedical", "chemicals_and_drugs"], "氢吗啡酮"),
                ("hydrophobic_and_hydrophilic_interaction", "Hydrophobic And Hydrophilic Interactions", ["biomedical", "phenomena_and_processes"], "疏水与亲水相互作用"),
                ("hydropneumothorax", "Hydropneumothorax", ["biomedical", "diseases"], "液气胸"),
            ]
        )

    def test_exact_expansion_batch_210_adds_hydroxy_chemical_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hydroquinon", "Hydroquinones", ["biomedical", "chemicals_and_drugs"], "对苯二酚类"),
                ("hydrothermal_vent", "Hydrothermal Vents", ["biomedical", "phenomena_and_processes"], "热液喷口"),
                ("hydroxyapatit", "Hydroxyapatites", ["biomedical", "chemicals_and_drugs"], "羟基磷灰石"),
                ("hydroxybutyrate_dehydrogenase", "Hydroxybutyrate Dehydrogenase", ["biomedical", "chemicals_and_drugs"], "羟基丁酸脱氢酶"),
                ("hydroxychloroquine", "Hydroxychloroquine", ["biomedical", "chemicals_and_drugs"], "羟氯喹"),
            ]
        )

    def test_exact_expansion_batch_211_adds_hydroxyl_and_hmg_coa_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hydroxyindoleacetic_acid", "Hydroxyindoleacetic Acid", ["biomedical", "chemicals_and_drugs"], "羟吲哚乙酸"),
                ("hydroxyl_radical", "Hydroxyl Radical", ["biomedical", "chemicals_and_drugs"], "羟自由基"),
                ("hydroxymethylglutaryl_coa_reductase_inhibitor", "Hydroxymethylglutaryl-coa Reductase Inhibitors", ["biomedical", "chemicals_and_drugs"], "HMG-CoA还原酶抑制剂"),
                ("hydroxyproline", "Hydroxyproline", ["biomedical", "chemicals_and_drugs"], "羟脯氨酸"),
                ("hydroxyurea", "Hydroxyurea", ["biomedical", "chemicals_and_drugs"], "羟基脲"),
            ]
        )

    def test_exact_expansion_batch_212_adds_early_hyper_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hyper_igm_immunodeficiency_syndrome", "Hyper-igm Immunodeficiency Syndrome", ["biomedical", "diseases"], "高IgM免疫缺陷综合征"),
                ("hyper_spectral_imag", "Hyper-spectral Images", ["computer_science"], "高光谱图像"),
                ("hyperacusi", "Hyperacusis", ["biomedical", "diseases"], "听觉过敏"),
                ("hyperbilirubinemia_neonatal", "Hyperbilirubinemia, Neonatal", ["biomedical", "diseases"], "新生儿高胆红素血症"),
                ("hypercementosi", "Hypercementosis", ["biomedical", "diseases"], "牙骨质增生症"),
            ]
        )

    def test_exact_expansion_batch_213_adds_hypermetabolic_and_electrolyte_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hyperemesi_gravidarum", "Hyperemesis Gravidarum", ["biomedical", "diseases"], "妊娠剧吐"),
                ("hypereosinophilic_syndrome", "Hypereosinophilic Syndrome", ["biomedical", "diseases"], "嗜酸性粒细胞增多综合征"),
                ("hyperglycemic_hyperosmolar_nonketotic_coma", "Hyperglycemic Hyperosmolar Nonketotic Coma", ["biomedical", "diseases"], "高渗性非酮症高血糖昏迷"),
                ("hyperhomocysteinemia", "Hyperhomocysteinemia", ["biomedical", "diseases"], "高同型半胱氨酸血症"),
                ("hyperkalemia", "Hyperkalemia", ["biomedical", "diseases"], "高钾血症"),
            ]
        )

    def test_exact_expansion_batch_214_adds_hyperlipoproteinemia_and_hyperostosis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hyperledger", "Hyperledger", ["computer_science"], "超级账本"),
                ("hyperlipoproteinemia_type_i", "Hyperlipoproteinemia Type I", ["biomedical", "diseases"], "I型高脂蛋白血症"),
                ("hypernatremia", "Hypernatremia", ["biomedical", "diseases"], "高钠血症"),
                ("hyperopia", "Hyperopia", ["biomedical", "diseases"], "远视"),
                ("hyperostosi_diffuse_idiopathic_skeletal", "Hyperostosis, Diffuse Idiopathic Skeletal", ["biomedical", "diseases"], "弥漫性特发性骨肥厚"),
            ]
        )

    def test_exact_expansion_batch_215_adds_parathyroid_and_hypersensitivity_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hyperparameter_optimization", "Hyperparameter Optimization", ["computational_and_artificial_intelligence"], "超参数优化"),
                ("hyperparathyroidism_primary", "Hyperparathyroidism, Primary", ["biomedical", "diseases"], "原发性甲状旁腺功能亢进症"),
                ("hyperpolarization_activated_cyclic_nucleotide_gated_channel", "Hyperpolarization-activated Cyclic Nucleotide-gated Channels", ["biomedical", "chemicals_and_drugs"], "超极化激活环核苷酸门控通道"),
                ("hypersensitivity_delayed", "Hypersensitivity, Delayed", ["biomedical", "diseases"], "迟发型超敏反应"),
                ("hypersensitivity_immediate", "Hypersensitivity, Immediate", ["biomedical", "diseases"], "速发型超敏反应"),
            ]
        )

    def test_exact_expansion_batch_216_adds_hyperspectral_and_hypertension_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hyperspectral_image_classification", "Hyperspectral Image Classification", ["computer_science"], "高光谱图像分类"),
                ("hyperspectral_unmixing", "Hyperspectral Unmixing", ["computer_science"], "高光谱解混"),
                ("hypertension_pregnancy_induced", "Hypertension, Pregnancy-induced", ["biomedical", "diseases"], "妊娠期高血压"),
                ("hypertension_pulmonary", "Hypertension, Pulmonary", ["biomedical", "diseases"], "肺动脉高压"),
                ("hypertensive_retinopathy", "Hypertensive Retinopathy", ["biomedical", "diseases"], "高血压视网膜病变"),
            ]
        )

    def test_exact_expansion_batch_217_adds_hyperthermia_and_early_hypo_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hyperthermic_intraperitoneal_chemotherapy", "Hyperthermic Intraperitoneal Chemotherapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "腹腔热灌注化疗"),
                ("hypertrophy_left_ventricular", "Hypertrophy, Left Ventricular", ["biomedical", "diseases"], "左心室肥厚"),
                ("hypervisor", "Hypervisor", ["computer_science"], "虚拟机监控器"),
                ("hypoalbuminemia", "Hypoalbuminemia", ["biomedical", "diseases"], "低白蛋白血症"),
                ("hypobetalipoproteinemia", "Hypobetalipoproteinemias", ["biomedical", "diseases"], "低β脂蛋白血症"),
            ]
        )

    def test_exact_expansion_batch_218_adds_hypocalcemia_and_hypoglossal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hypocalcemia", "Hypocalcemia", ["biomedical", "diseases"], "低钙血症"),
                ("hypochlorou_acid", "Hypochlorous Acid", ["biomedical", "chemicals_and_drugs"], "次氯酸"),
                ("hypoglossal_nerve", "Hypoglossal Nerve", ["anatomy", "biomedical"], "舌下神经"),
                ("hypoglycemic_agent", "Hypoglycemic Agents", ["biomedical", "chemicals_and_drugs"], "降血糖药"),
                ("hypokalemic_periodic_paralysi", "Hypokalemic Periodic Paralysis", ["biomedical", "diseases"], "低钾性周期性麻痹"),
            ]
        )

    def test_exact_expansion_batch_219_adds_hypopharynx_and_pituitary_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hypolipidemic_agent", "Hypolipidemic Agents", ["biomedical", "chemicals_and_drugs"], "降脂药"),
                ("hypoparathyroidism", "Hypoparathyroidism", ["biomedical", "diseases"], "甲状旁腺功能减退症"),
                ("hypopharyngeal_neoplasm", "Hypopharyngeal Neoplasms", ["biomedical", "diseases"], "下咽肿瘤"),
                ("hypophysectomy", "Hypophysectomy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "垂体切除术"),
                ("hypoplastic_left_heart_syndrome", "Hypoplastic Left Heart Syndrome", ["biomedical", "diseases"], "左心发育不良综合征"),
            ]
        )

    def test_exact_expansion_batch_220_adds_hypothalamus_and_hypoxia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hypothalamic_pituitary_gonadal_axis", "Hypothalamic-pituitary-gonadal Axis", ["anatomy", "biomedical"], "下丘脑-垂体-性腺轴"),
                ("hypothalamus_anterior", "Hypothalamus, Anterior", ["anatomy", "biomedical"], "前下丘脑"),
                ("hypotonic_solution", "Hypotonic Solutions", ["biomedical", "chemicals_and_drugs"], "低渗溶液"),
                ("hypoxanthine_phosphoribosyltransferase", "Hypoxanthine Phosphoribosyltransferase", ["biomedical", "chemicals_and_drugs"], "次黄嘌呤磷酸核糖转移酶"),
                ("hypoxia_inducible_factor_1_alpha_subunit", "Hypoxia-inducible Factor 1, Alpha Subunit", ["biomedical", "chemicals_and_drugs"], "缺氧诱导因子1α亚基"),
            ]
        )

    def test_exact_expansion_batch_221_adds_image_acquisition_and_compression_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("image_acquisition", "Image Acquisition", ["computer_science"], "图像采集"),
                ("image_and_object_detection_techniqu", "Image And Object Detection Techniques", ["computer_science", "physical_sciences"], "图像与目标检测技术"),
                ("image_annotation", "Image Annotation", ["computer_science"], "图像标注"),
                ("image_binarization", "Image Binarization", ["computer_science"], "图像二值化"),
                ("image_compression_algorithm", "Image Compression Algorithms", ["computer_science"], "图像压缩算法"),
            ]
        )

    def test_exact_expansion_batch_222_adds_image_denoising_and_enhancement_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("image_deblurring", "Image Deblurring", ["computer_science"], "图像去模糊"),
                ("image_dehazing", "Image Dehazing", ["computers_and_information_processing"], "图像去雾"),
                ("image_denoising_algorithm", "Image Denoising Algorithm", ["computer_science"], "图像去噪算法"),
                ("image_edge_detection", "Image Edge Detection", ["computers_and_information_processing"], "图像边缘检测"),
                ("image_fusion", "Image Fusion", ["computers_and_information_processing"], "图像融合"),
            ]
        )

    def test_exact_expansion_batch_223_adds_guided_matching_and_processing_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("image_guided_biopsy", "Image-guided Biopsy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "图像引导活检"),
                ("image_guided_radiation_therapy", "Image-guided Radiation Therapy", ["computer_science"], "图像引导放射治疗"),
                ("image_hashing", "Image Hashing", ["computer_science"], "图像哈希"),
                ("image_interpretation_computer_assisted", "Image Interpretation, Computer-assisted", ["computer_science"], "计算机辅助图像解释"),
                ("image_processing_and_3d_reconstruction", "Image Processing And 3D Reconstruction", ["computer_science", "physical_sciences"], "图像处理与三维重建"),
            ]
        )

    def test_exact_expansion_batch_224_adds_image_quality_registration_and_retrieval_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("image_quality_assessment", "Image Quality Assessment", ["computer_science"], "图像质量评估"),
                ("image_reconstruction_algorithm", "Image Reconstruction Algorithm", ["computer_science"], "图像重建算法"),
                ("image_registration_techniqu", "Image Registration Techniques", ["computer_science"], "图像配准技术"),
                ("image_retrieval_system", "Image Retrieval Systems", ["computer_science"], "图像检索系统"),
                ("image_segmentation_algorithm", "Image Segmentation Algorithm", ["computer_science"], "图像分割算法"),
            ]
        )

    def test_exact_expansion_batch_225_adds_image_sequence_and_watermarking_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("image_sensor", "Image Sensors", ["imaging"], "图像传感器"),
                ("image_sequence_analysi", "Image Sequence Analysis", ["computers_and_information_processing"], "图像序列分析"),
                ("image_steganography", "Image Steganography", ["computer_science"], "图像隐写"),
                ("image_super_resolution", "Image Super-resolution", ["computer_science"], "图像超分辨率"),
                ("image_watermarking_algorithm", "Image Watermarking Algorithm", ["computer_science"], "图像水印算法"),
            ]
        )

    def test_exact_expansion_batch_226_adds_imaging_and_immune_checkpoint_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("imaging_three_dimensional", "Imaging, Three-dimensional", ["computer_science"], "三维成像"),
                ("immune_adherence_reaction", "Immune Adherence Reaction", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "免疫黏附反应"),
                ("immune_checkpoint_inhibitor", "Immune Checkpoint Inhibitors", ["biomedical", "chemicals_and_drugs"], "免疫检查点抑制剂"),
                ("immune_evasion", "Immune Evasion", ["biomedical", "phenomena_and_processes"], "免疫逃逸"),
                ("immune_reconstitution_inflammatory_syndrome", "Immune Reconstitution Inflammatory Syndrome", ["biomedical", "diseases"], "免疫重建炎症综合征"),
            ]
        )

    def test_exact_expansion_batch_227_adds_immunity_and_immunization_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("immunity_cellular", "Immunity, Cellular", ["biomedical", "phenomena_and_processes"], "细胞免疫"),
                ("immunity_herd", "Immunity, Herd", ["biomedical", "phenomena_and_processes"], "群体免疫"),
                ("immunity_testing", "Immunity Testing", ["electromagnetic_compatibility_and_interference"], "抗扰度测试"),
                ("immunization_passive", "Immunization, Passive", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "被动免疫"),
                ("immunoblotting", "Immunoblotting", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "免疫印迹"),
            ]
        )

    def test_exact_expansion_batch_228_adds_immunodiffusion_and_immunofluorescence_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("immunodeficiency_viru_bovine", "Immunodeficiency Virus, Bovine", ["biomedical", "organisms"], "牛免疫缺陷病毒"),
                ("immunodiffusion", "Immunodiffusion", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "免疫扩散"),
                ("immunodominant_epitop", "Immunodominant Epitopes", ["biomedical", "chemicals_and_drugs"], "免疫优势表位"),
                ("immunoelectrophoresi_two_dimensional", "Immunoelectrophoresis, Two-dimensional", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "二维免疫电泳"),
                ("immunogenicity_vaccine", "Immunogenicity, Vaccine", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "疫苗免疫原性"),
            ]
        )

    def test_exact_expansion_batch_229_adds_immunoglobulin_core_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("immunoglobulin_a_secretory", "Immunoglobulin A, Secretory", ["biomedical", "chemicals_and_drugs"], "分泌型免疫球蛋白A"),
                ("immunoglobulin_class_switching", "Immunoglobulin Class Switching", ["biomedical", "phenomena_and_processes"], "免疫球蛋白类别转换"),
                ("immunoglobulin_fab_fragment", "Immunoglobulin Fab Fragments", ["biomedical", "chemicals_and_drugs"], "免疫球蛋白Fab片段"),
                ("immunoglobulin_g4_related_disease", "Immunoglobulin G4-related Disease", ["biomedical", "diseases"], "IgG4相关疾病"),
                ("immunoglobulin_heavy_chain", "Immunoglobulin Heavy Chains", ["biomedical", "chemicals_and_drugs"], "免疫球蛋白重链"),
            ]
        )

    def test_exact_expansion_batch_230_adds_immunoglobulin_chain_and_histochemistry_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("immunoglobulin_kappa_chain", "Immunoglobulin Kappa-chains", ["biomedical", "chemicals_and_drugs"], "免疫球蛋白κ链"),
                ("immunoglobulin_light_chain_amyloidosi", "Immunoglobulin Light-chain Amyloidosis", ["biomedical", "diseases"], "免疫球蛋白轻链淀粉样变性"),
                ("immunoglobulin_m", "Immunoglobulin M", ["biomedical", "chemicals_and_drugs"], "免疫球蛋白M"),
                ("immunoglobulin_variable_region", "Immunoglobulin Variable Region", ["biomedical", "chemicals_and_drugs"], "免疫球蛋白可变区"),
                ("immunohistochemistry", "Immunohistochemistry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "免疫组织化学"),
            ]
        )

    def test_exact_expansion_batch_231_adds_immunologic_and_immunomodulation_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("immunologic_deficiency_syndrom", "Immunologic Deficiency Syndromes", ["biomedical", "diseases"], "免疫缺陷综合征"),
                ("immunologic_memory", "Immunologic Memory", ["biomedical", "phenomena_and_processes"], "免疫记忆"),
                ("immunological_synapse", "Immunological Synapses", ["anatomy", "biomedical"], "免疫突触"),
                ("immunomagnetic_separation", "Immunomagnetic Separation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "免疫磁分离"),
                ("immunophenotyping", "Immunophenotyping", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "免疫表型分析"),
            ]
        )

    def test_exact_expansion_batch_232_adds_immunosuppression_and_implant_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("immunosenescence", "Immunosenescence", ["biomedical", "phenomena_and_processes"], "免疫衰老"),
                ("immunosorbent_techniqu", "Immunosorbent Techniques", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "免疫吸附技术"),
                ("immunotherapy_adoptive", "Immunotherapy, Adoptive", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "过继免疫治疗"),
                ("implant_capsular_contracture", "Implant Capsular Contracture", ["biomedical", "diseases"], "植入物包膜挛缩"),
                ("implantable_neurostimulator", "Implantable Neurostimulators", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "植入式神经刺激器"),
            ]
        )

    def test_exact_expansion_batch_233_adds_infection_control_and_infectious_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("infection_control_dental", "Infection Control, Dental", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "牙科感染控制"),
                ("infectiou_anemia_viru_equine", "Infectious Anemia Virus, Equine", ["biomedical", "organisms"], "马传染性贫血病毒"),
                ("infectiou_bovine_rhinotracheiti", "Infectious Bovine Rhinotracheitis", ["biomedical", "diseases"], "牛传染性鼻气管炎"),
                ("infectiou_disease_incubation_period", "Infectious Disease Incubation Period", ["biomedical", "health_care"], "传染病潜伏期"),
                ("infectiou_disease_transmission_vertical", "Infectious Disease Transmission, Vertical", ["biomedical", "health_care"], "传染病垂直传播"),
            ]
        )

    def test_exact_expansion_batch_234_adds_inflammation_and_influenza_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("inflammation_mediator", "Inflammation Mediators", ["biomedical", "chemicals_and_drugs"], "炎症介质"),
                ("inflammatory_breast_neoplasm", "Inflammatory Breast Neoplasms", ["biomedical", "diseases"], "炎性乳腺肿瘤"),
                ("influenza_a_viru_h1n1_subtype", "Influenza A Virus, H1N1 Subtype", ["biomedical", "organisms"], "H1N1亚型甲型流感病毒"),
                ("influenza_human", "Influenza, Human", ["biomedical", "diseases"], "人流感"),
                ("influenza_pandemic_1918_1919", "Influenza Pandemic, 1918-1919", ["biomedical", "humanities"], "1918-1919年流感大流行"),
            ]
        )

    def test_exact_expansion_batch_235_adds_infrared_and_infrastructure_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("infrared_imagery", "Infrared Imagery", ["computer_science"], "红外影像"),
                ("infrared_rays", "Infrared Rays", ["biomedical", "phenomena_and_processes"], "红外线"),
                ("infrared_thermography", "Infrared Thermography", ["computer_science"], "红外热成像"),
                ("infrastructure_as_a_service_iaas", "Infrastructure As A Service (iaas)", ["computer_science"], "基础设施即服务"),
                ("infratentorial_neoplasm", "Infratentorial Neoplasms", ["biomedical", "diseases"], "幕下肿瘤"),
            ]
        )

    def test_exact_expansion_batch_236_adds_inhibitor_injury_and_insulin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("inhibin_beta_subunit", "Inhibin-beta Subunits", ["biomedical", "chemicals_and_drugs"], "抑制素β亚基"),
                ("inhibitory_concentration_50", "Inhibitory Concentration 50", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "半数抑制浓度"),
                ("injury_severity_score", "Injury Severity Score", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "损伤严重度评分"),
                ("insulin_aspart", "Insulin Aspart", ["biomedical", "chemicals_and_drugs"], "门冬胰岛素"),
                ("insulin_glargine", "Insulin Glargine", ["biomedical", "chemicals_and_drugs"], "甘精胰岛素"),
            ]
        )

    def test_exact_expansion_batch_237_adds_insulin_like_factor_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("insulin_infusion_system", "Insulin Infusion Systems", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "胰岛素输注系统"),
                ("insulin_like_growth_factor_binding_protein_3", "Insulin-like Growth Factor Binding Protein 3", ["biomedical", "chemicals_and_drugs"], "胰岛素样生长因子结合蛋白3"),
                ("insulin_like_growth_factor_i", "Insulin-like Growth Factor I", ["biomedical", "chemicals_and_drugs"], "胰岛素样生长因子I"),
                ("insulin_receptor_substrate_protein", "Insulin Receptor Substrate Proteins", ["biomedical", "chemicals_and_drugs"], "胰岛素受体底物蛋白"),
                ("insulinoma", "Insulinoma", ["biomedical", "diseases"], "胰岛素瘤"),
            ]
        )

    def test_exact_expansion_batch_238_adds_internet_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("internet_addiction_disorder", "Internet Addiction Disorder", ["biomedical", "psychiatry_and_psychology"], "互联网成瘾障碍"),
                ("internet_of_medical_thing", "Internet Of Medical Things", ["engineering_in_medicine_and_biology"], "医疗物联网"),
                ("internet_protocol_version_6", "Internet Protocol Version 6", ["computer_science"], "互联网协议第6版"),
                ("internet_service_provider", "Internet Service Providers", ["computer_science"], "互联网服务提供商"),
                ("internet_worm", "Internet Worm", ["computer_science"], "互联网蠕虫"),
            ]
        )

    def test_exact_expansion_batch_239_adds_intracellular_and_intracranial_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("intracellular_fluid", "Intracellular Fluid", ["anatomy", "biomedical"], "细胞内液"),
                ("intracranial_arteriovenou_malformation", "Intracranial Arteriovenous Malformations", ["biomedical", "diseases"], "颅内动静脉畸形"),
                ("intracranial_hemorrhage_hypertensive", "Intracranial Hemorrhage, Hypertensive", ["biomedical", "diseases"], "高血压性颅内出血"),
                ("intracranial_hypertension", "Intracranial Hypertension", ["biomedical", "diseases"], "颅内高压"),
                ("intractable_pain", "Intractable Pain", ["biomedical", "diseases"], "顽固性疼痛"),
            ]
        )

    def test_exact_expansion_batch_240_adds_ionic_and_isotope_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ionic_liquid", "Ionic Liquids", ["biomedical", "chemicals_and_drugs"], "离子液体"),
                ("isotachophoresi", "Isotachophoresis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "等速电泳"),
                ("isotonic_solution", "Isotonic Solutions", ["biomedical", "chemicals_and_drugs"], "等渗溶液"),
                ("isotope_labeling", "Isotope Labeling", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "同位素标记"),
                ("isotretinoin", "Isotretinoin", ["biomedical", "chemicals_and_drugs"], "异维A酸"),
            ]
        )

    def test_exact_expansion_batch_241_adds_isotropic_and_it_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("isotropic_material", "Isotropic Materials", ["computer_science"], "各向同性材料"),
                ("isovaleryl_coa_dehydrogenase", "Isovaleryl-coa Dehydrogenase", ["biomedical", "chemicals_and_drugs"], "异戊酰辅酶A脱氢酶"),
                ("isradipine", "Isradipine", ["biomedical", "chemicals_and_drugs"], "伊拉地平"),
                ("it_infrastructure", "It Infrastructure", ["computer_science"], "IT基础设施"),
                ("it_service_management", "It Service Management", ["computer_science"], "IT服务管理"),
            ]
        )

    def test_exact_expansion_batch_242_adds_iterative_algorithm_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("iterated_local_search", "Iterated Local Search", ["computer_science"], "迭代局部搜索"),
                ("iterative_algorithm", "Iterative Algorithms", ["mathematics"], "迭代算法"),
                ("iterative_closest_point_algorithm", "Iterative Closest Point Algorithm", ["mathematics"], "迭代最近点算法"),
                ("iterative_decoding", "Iterative Decoding", ["information_theory"], "迭代译码"),
                ("iterative_learning_control", "Iterative Learning Control", ["computer_science", "mathematics"], "迭代学习控制"),
            ]
        )

    def test_exact_expansion_batch_243_adds_iterative_method_and_jagged_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("iterative_method", "Iterative Methods", ["mathematics"], "迭代法"),
                ("iterative_solver", "Iterative Solvers", ["computer_science"], "迭代求解器"),
                ("itraconazole", "Itraconazole", ["biomedical", "chemicals_and_drugs"], "伊曲康唑"),
                ("jagged_1_protein", "Jagged-1 Protein", ["biomedical", "chemicals_and_drugs"], "Jagged-1蛋白"),
                ("janu_kinase_inhibitor", "Janus Kinase Inhibitors", ["biomedical", "chemicals_and_drugs"], "Janus激酶抑制剂"),
            ]
        )

    def test_exact_expansion_batch_244_adds_janus_jaundice_and_java_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("janu_kinase_1", "Janus Kinase 1", ["biomedical", "chemicals_and_drugs"], "Janus激酶1"),
                ("japanese_encephaliti_vaccin", "Japanese Encephalitis Vaccines", ["biomedical", "chemicals_and_drugs"], "日本脑炎疫苗"),
                ("jaundice_neonatal", "Jaundice, Neonatal", ["biomedical", "diseases"], "新生儿黄疸"),
                ("java_language", "Java Language", ["computer_science"], "Java语言"),
                ("java_virtual_machine", "Java Virtual Machine", ["computer_science"], "Java虚拟机"),
            ]
        )

    def test_exact_expansion_batch_245_adds_jaw_and_jejunal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("jaw_cyst", "Jaw Cysts", ["biomedical", "diseases"], "颌囊肿"),
                ("jaw_fixation_techniqu", "Jaw Fixation Techniques", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "颌固定技术"),
                ("jejunal_disease", "Jejunal Diseases", ["biomedical", "diseases"], "空肠疾病"),
                ("jejunal_neoplasm", "Jejunal Neoplasms", ["biomedical", "diseases"], "空肠肿瘤"),
                ("jejunostomy", "Jejunostomy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "空肠造口术"),
            ]
        )

    def test_exact_expansion_batch_246_adds_jet_jnk_and_job_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("jet_engin", "Jet Engines", ["industry_applications"], "喷气发动机"),
                ("jet_lag_syndrome", "Jet Lag Syndrome", ["biomedical", "diseases"], "时差综合征"),
                ("jnk_mitogen_activated_protein_kinase", "JNK Mitogen-activated Protein Kinases", ["biomedical", "chemicals_and_drugs"], "JNK丝裂原活化蛋白激酶"),
                ("job_satisfaction", "Job Satisfaction", ["biomedical", "psychiatry_and_psychology"], "工作满意度"),
                ("job_scheduling", "Job Scheduling", ["computer_science"], "作业调度"),
            ]
        )

    def test_exact_expansion_batch_247_adds_joint_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("joint_capsule", "Joint Capsule", ["anatomy", "biomedical"], "关节囊"),
                ("joint_deformity_acquired", "Joint Deformities, Acquired", ["biomedical", "diseases"], "获得性关节畸形"),
                ("joint_disease", "Joint Diseases", ["biomedical", "diseases"], "关节疾病"),
                ("joint_dislocation", "Joint Dislocations", ["biomedical", "diseases"], "关节脱位"),
                ("joint_instability", "Joint Instability", ["biomedical", "diseases"], "关节不稳"),
            ]
        )

    def test_exact_expansion_batch_248_adds_josephson_journal_and_jpeg_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("josephson_effect", "Josephson Effect", ["electron_devices"], "约瑟夫森效应"),
                ("josephson_junction", "Josephson Junctions", ["superconductivity"], "约瑟夫森结"),
                ("journal_impact_factor", "Journal Impact Factor", ["biomedical", "information_science"], "期刊影响因子"),
                ("jpeg_compression", "Jpeg Compression", ["computer_science"], "JPEG压缩"),
                ("judgment_matrix", "Judgment Matrix", ["computer_science"], "判断矩阵"),
            ]
        )

    def test_exact_expansion_batch_249_adds_junction_and_juvenile_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("junctional_adhesion_molecule_a", "Junctional Adhesion Molecule A", ["biomedical", "chemicals_and_drugs"], "连接黏附分子A"),
                ("junctional_adhesion_molecule_b", "Junctional Adhesion Molecule B", ["biomedical", "chemicals_and_drugs"], "连接黏附分子B"),
                ("junctionless_nanowire_transistor", "Junctionless Nanowire Transistors", ["nanotechnology"], "无结纳米线晶体管"),
                ("juvenile_hormon", "Juvenile Hormones", ["biomedical", "chemicals_and_drugs"], "保幼激素"),
                ("juxtaglomerular_apparatu", "Juxtaglomerular Apparatus", ["anatomy", "biomedical"], "肾小球旁器"),
            ]
        )

    def test_exact_expansion_batch_250_adds_k_neighbor_and_anonymity_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("k_cl_cotransporter", "K Cl- Cotransporters", ["biomedical", "chemicals_and_drugs"], "K-Cl协同转运蛋白"),
                ("k_nearest_neighbor", "K Nearest Neighbor", ["computer_science"], "K近邻"),
                ("k_nearest_neighbor_algorithm", "K Nearest Neighbor Algorithm", ["computer_science"], "K近邻算法"),
                ("k_anonymity", "K-anonymity", ["computer_science"], "K匿名"),
                ("k_band", "K-band", ["microwave_theory_and_techniques"], "K波段"),
            ]
        )

    def test_exact_expansion_batch_251_adds_kmeans_and_ka_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("k_mean_clustering_algorithm", "K-means Clustering Algorithm", ["computer_science"], "K均值聚类算法"),
                ("k_mean_clustering_method", "K-means Clustering Method", ["computer_science"], "K均值聚类方法"),
                ("k_mean_method", "K-means Method", ["computer_science"], "K均值法"),
                ("ka_band", "Ka-band", ["microwave_theory_and_techniques"], "Ka波段"),
                ("kaempferol", "Kaempferols", ["biomedical", "chemicals_and_drugs"], "山柰酚类"),
            ]
        )

    def test_exact_expansion_batch_252_adds_kainic_and_kallikrein_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("kainic_acid", "Kainic Acid", ["biomedical", "chemicals_and_drugs"], "海人酸"),
                ("kainic_acid_receptor", "Kainic Acid Receptors", ["biomedical", "chemicals_and_drugs"], "海人酸受体"),
                ("kallikrein_kinin_system", "Kallikrein-kinin System", ["biomedical", "phenomena_and_processes"], "激肽释放酶-激肽系统"),
                ("kallikrein", "Kallikreins", ["biomedical", "chemicals_and_drugs"], "激肽释放酶类"),
                ("kallmann_syndrome", "Kallmann Syndrome", ["biomedical", "diseases"], "Kallmann综合征"),
            ]
        )

    def test_exact_expansion_batch_253_adds_kalman_and_kanamycin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("kalman_filter_algorithm", "Kalman Filter Algorithms", ["computer_science"], "卡尔曼滤波算法"),
                ("kalman_filtering_algorithm", "Kalman Filtering Algorithms", ["computer_science"], "卡尔曼滤波算法"),
                ("kanamycin", "Kanamycin", ["biomedical", "chemicals_and_drugs"], "卡那霉素"),
                ("kanamycin_kinase", "Kanamycin Kinase", ["biomedical", "chemicals_and_drugs"], "卡那霉素激酶"),
                ("kanamycin_resistance", "Kanamycin Resistance", ["biomedical", "phenomena_and_processes"], "卡那霉素耐药性"),
            ]
        )

    def test_exact_expansion_batch_254_adds_kaplan_kaposi_and_karyotype_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("kangaroo_mother_care_method", "Kangaroo-mother Care Method", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "袋鼠式护理法"),
                ("kaplan_meier_method", "Kaplan Meier Method", ["computer_science"], "Kaplan-Meier法"),
                ("kaposi_varicelliform_eruption", "Kaposi Varicelliform Eruption", ["biomedical", "diseases"], "卡波西水痘样疹"),
                ("karnofsky_performance_statu", "Karnofsky Performance Status", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "Karnofsky体能状态评分"),
                ("karyotyping", "Karyotyping", ["computer_science"], "核型分析"),
            ]
        )

    def test_exact_expansion_batch_255_adds_keratin_and_keratitis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("keratan_sulfate", "Keratan Sulfate", ["biomedical", "chemicals_and_drugs"], "硫酸角质素"),
                ("keratin_14", "Keratin-14", ["biomedical", "chemicals_and_drugs"], "角蛋白14"),
                ("keratinocyt", "Keratinocytes", ["anatomy", "biomedical"], "角质形成细胞"),
                ("keratiti_herpetic", "Keratitis, Herpetic", ["biomedical", "diseases"], "疱疹性角膜炎"),
                ("keratoconu", "Keratoconus", ["biomedical", "diseases"], "圆锥角膜"),
            ]
        )

    def test_exact_expansion_batch_256_adds_kernel_and_ketone_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("kernel_function", "Kernel Function", ["computer_science"], "核函数"),
                ("kernel_method", "Kernel Method", ["computer_science"], "核方法"),
                ("ketamine", "Ketamine", ["biomedical", "chemicals_and_drugs"], "氯胺酮"),
                ("ketoconazole", "Ketoconazole", ["biomedical", "chemicals_and_drugs"], "酮康唑"),
                ("ketone_body", "Ketone Bodies", ["biomedical", "chemicals_and_drugs"], "酮体"),
            ]
        )

    def test_exact_expansion_batch_257_adds_key_and_keyword_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("key_agreement", "Key Agreement", ["computer_science"], "密钥协商"),
                ("key_distribution", "Key Distribution", ["computer_science"], "密钥分发"),
                ("key_management", "Key Management", ["computer_science"], "密钥管理"),
                ("keystroke_dynamic", "Keystroke Dynamics", ["systems_man_and_cybernetics"], "击键动力学"),
                ("keyword_search", "Keyword Search", ["professional_communication"], "关键词搜索"),
            ]
        )

    def test_exact_expansion_batch_258_adds_kidney_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("kidney", "Kidney", ["anatomy", "biomedical"], "肾脏"),
                ("kidney_calculi", "Kidney Calculi", ["biomedical", "diseases"], "肾结石"),
                ("kidney_cortex", "Kidney Cortex", ["anatomy", "biomedical"], "肾皮质"),
                ("kidney_glomerulu", "Kidney Glomerulus", ["anatomy", "biomedical"], "肾小球"),
                ("kidney_tubul_proximal", "Kidney Tubules, Proximal", ["anatomy", "biomedical"], "近端肾小管"),
            ]
        )

    def test_exact_expansion_batch_259_adds_killer_kinase_and_klebsiella_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("killer_cell_lymphokine_activated", "Killer Cells, Lymphokine-activated", ["anatomy", "biomedical"], "淋巴因子激活杀伤细胞"),
                ("kinematic_chain", "Kinematic Chain", ["computer_science"], "运动链"),
                ("kinetic_energy", "Kinetic Energy", ["science_general"], "动能"),
                ("klatskin_tumor", "Klatskin Tumor", ["biomedical", "diseases"], "Klatskin肿瘤"),
                ("klebsiella_pneumoniae", "Klebsiella Pneumoniae", ["biomedical", "organisms"], "肺炎克雷伯菌"),
            ]
        )

    def test_exact_expansion_batch_260_adds_knowledge_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("knowledge_acquisition", "Knowledge Acquisition", ["computational_and_artificial_intelligence"], "知识获取"),
                ("knowledge_base", "Knowledge Base", ["computer_science"], "知识库"),
                ("knowledge_discovery_in_database", "Knowledge Discovery In Database", ["computer_science"], "数据库知识发现"),
                ("knowledge_graph_embedding", "Knowledge Graph Embedding", ["computer_science"], "知识图谱嵌入"),
                ("knowledge_representation_and_reasoning", "Knowledge Representation And Reasoning", ["computer_science"], "知识表示与推理"),
            ]
        )

    def test_exact_expansion_batch_261_adds_knowledge_and_kohonen_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("knowledge_transfer", "Knowledge Transfer", ["computers_and_information_processing"], "知识转移"),
                ("knowledge_visualization", "Knowledge Visualization", ["computer_science"], "知识可视化"),
                ("kohonen_self_organizing_maps", "Kohonen Self-organizing Maps", ["computer_science"], "Kohonen自组织映射"),
                ("krill_herd_algorithm", "Krill Herd Algorithm", ["mathematics"], "磷虾群算法"),
                ("krylov_subspace_method", "Krylov Subspace Method", ["computer_science"], "Krylov子空间法"),
            ]
        )

    def test_exact_expansion_batch_262_adds_kr_kruppel_and_ku_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("korsakoff_syndrome", "Korsakoff Syndrome", ["biomedical", "diseases"], "Korsakoff综合征"),
                ("krukenberg_tumor", "Krukenberg Tumor", ["biomedical", "diseases"], "Krukenberg肿瘤"),
                ("kruppel_like_factor_4", "Kruppel-like Factor 4", ["biomedical", "chemicals_and_drugs"], "Kruppel样因子4"),
                ("ku_band", "Ku-band", ["microwave_theory_and_techniques"], "Ku波段"),
                ("kupffer_cell", "Kupffer Cells", ["anatomy", "biomedical"], "Kupffer细胞"),
            ]
        )

    def test_exact_expansion_batch_263_adds_kv_channel_and_kynurenine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("kv1_1_potassium_channel", "Kv1.1 Potassium Channel", ["biomedical", "chemicals_and_drugs"], "Kv1.1钾通道"),
                ("kv1_2_potassium_channel", "Kv1.2 Potassium Channel", ["biomedical", "chemicals_and_drugs"], "Kv1.2钾通道"),
                ("kv1_3_potassium_channel", "Kv1.3 Potassium Channel", ["biomedical", "chemicals_and_drugs"], "Kv1.3钾通道"),
                ("kynurenic_acid", "Kynurenic Acid", ["biomedical", "chemicals_and_drugs"], "犬尿喹啉酸"),
                ("kynurenine_3_monooxygenase", "Kynurenine 3-monooxygenase", ["biomedical", "chemicals_and_drugs"], "犬尿氨酸3-单加氧酶"),
            ]
        )

    def test_exact_expansion_batch_264_adds_l_enzyme_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("l_amino_acid_oxidase", "L-amino Acid Oxidase", ["biomedical", "chemicals_and_drugs"], "L-氨基酸氧化酶"),
                ("l_aminoadipate_semialdehyde_dehydrogenase", "L-aminoadipate-semialdehyde Dehydrogenase", ["biomedical", "chemicals_and_drugs"], "L-氨基己二酸半醛脱氢酶"),
                ("l_gulonolactone_oxidase", "L-gulonolactone Oxidase", ["biomedical", "chemicals_and_drugs"], "L-古洛糖酸内酯氧化酶"),
                ("l_lactate_dehydrogenase", "L-lactate Dehydrogenase", ["biomedical", "chemicals_and_drugs"], "L-乳酸脱氢酶"),
                ("l_selectin", "L-selectin", ["biomedical", "chemicals_and_drugs"], "L-选择素"),
            ]
        )

    def test_exact_expansion_batch_265_adds_lband_lab_chip_and_label_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("l2_cache", "L2 Cache", ["computer_science"], "L2缓存"),
                ("la_crosse_viru", "La Crosse Virus", ["biomedical", "organisms"], "拉克罗斯病毒"),
                ("lab_on_a_chip_devic", "Lab-on-a-chip Devices", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "芯片实验室装置"),
                ("label_propagation", "Label Propagation", ["computer_science"], "标签传播"),
                ("label_switched_path", "Label Switched Paths", ["computer_science"], "标签交换路径"),
                ("food_labeling", "Food Labeling", ["biomedical", "technology_industry_and_agriculture"], "食品标识"),
                ("product_labeling", "Product Labeling", ["biomedical", "technology_industry_and_agriculture"], "产品标识"),
                ("sequence_labeling", "Sequence Labeling", ["computer_science"], "序列标注"),
            ]
        )

    def test_exact_expansion_batch_266_adds_laboratory_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("labetalol", "Labetalol", ["biomedical", "chemicals_and_drugs"], "拉贝洛尔"),
                ("labial_frenum", "Labial Frenum", ["anatomy", "biomedical"], "唇系带"),
                ("laboratory_clinical", "Laboratories, Clinical", ["biomedical", "health_care"], "临床实验室"),
                ("laboratory_critical_valu", "Laboratory Critical Values", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "实验室危急值"),
                ("laboratory_proficiency_testing", "Laboratory Proficiency Testing", ["biomedical", "technology_industry_and_agriculture"], "实验室能力验证"),
            ]
        )

    def test_exact_expansion_batch_267_adds_lac_and_lactase_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("beta_lactam", "Beta-lactams", ["biomedical", "chemicals_and_drugs"], "β-内酰胺类"),
                ("beta_lactam_resistance", "Beta-lactam Resistance", ["biomedical", "phenomena_and_processes"], "β-内酰胺耐药性"),
                ("lac_operon", "Lac Operon", ["biomedical", "phenomena_and_processes"], "Lac操纵子"),
                ("lac_repressor", "Lac Repressors", ["biomedical", "chemicals_and_drugs"], "Lac阻遏蛋白"),
                ("laccase", "Laccase", ["biomedical", "chemicals_and_drugs"], "漆酶"),
                ("lacosamide", "Lacosamide", ["biomedical", "chemicals_and_drugs"], "拉考沙胺"),
                ("lactase_phlorizin_hydrolase", "Lactase-phlorizin Hydrolase", ["biomedical", "chemicals_and_drugs"], "乳糖酶-根皮苷水解酶"),
            ]
        )

    def test_exact_expansion_batch_268_adds_lactic_lactobacillus_and_lactose_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lactat", "Lactates", ["biomedical", "chemicals_and_drugs"], "乳酸盐"),
                ("lactic_acid", "Lactic Acid", ["biomedical", "chemicals_and_drugs"], "乳酸"),
                ("lactobacillu", "Lactobacillus", ["biomedical", "organisms"], "乳杆菌属"),
                ("lactobacillu_acidophilu", "Lactobacillus Acidophilus", ["biomedical", "organisms"], "嗜酸乳杆菌"),
                ("lactose_intolerance", "Lactose Intolerance", ["biomedical", "diseases"], "乳糖不耐受"),
            ]
        )

    def test_exact_expansion_batch_269_adds_lactoferrin_and_lactone_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lactoferrin", "Lactoferrin", ["biomedical", "chemicals_and_drugs"], "乳铁蛋白"),
                ("lactoglobulin", "Lactoglobulins", ["biomedical", "chemicals_and_drugs"], "乳球蛋白"),
                ("lacton", "Lactones", ["biomedical", "chemicals_and_drugs"], "内酯类"),
                ("lactoperoxidase", "Lactoperoxidase", ["biomedical", "chemicals_and_drugs"], "乳过氧化物酶"),
                ("lactulose", "Lactulose", ["biomedical", "chemicals_and_drugs"], "乳果糖"),
                ("sodium_lactate", "Sodium Lactate", ["biomedical", "chemicals_and_drugs"], "乳酸钠"),
            ]
        )

    def test_exact_expansion_batch_270_adds_lambda_and_lamin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lambda_calculu", "Lambda Calculus", ["computer_science"], "Lambda演算"),
                ("lambert_eaton_myasthenic_syndrome", "Lambert-eaton Myasthenic Syndrome", ["biomedical", "diseases"], "Lambert-Eaton肌无力综合征"),
                ("laminar_flow", "Laminar Flows", ["physics"], "层流"),
                ("lamin_b_receptor", "Lamin B Receptor", ["biomedical", "chemicals_and_drugs"], "Lamin B受体"),
                ("lamivudine", "Lamivudine", ["biomedical", "chemicals_and_drugs"], "拉米夫定"),
            ]
        )

    def test_exact_expansion_batch_271_adds_land_and_lane_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ieee_802_11_wireless_lan", "Ieee 802.11 Wireless Lan", ["computer_science"], "IEEE 802.11无线局域网"),
                ("land_mobile_radio_cellular_system", "Land Mobile Radio Cellular Systems", ["computer_science"], "陆地移动无线蜂窝系统"),
                ("land_mobile_radio_equipment", "Land Mobile Radio Equipment", ["communications_technology"], "陆地移动无线设备"),
                ("land_surface_temperature", "Land Surface Temperature", ["change"], "地表温度"),
                ("land_vehicl", "Land Vehicles", ["intelligent_transportation_systems"], "陆地车辆"),
                ("lane_detection", "Lane Detection", ["industry_applications"], "车道检测"),
            ]
        )

    def test_exact_expansion_batch_272_adds_language_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("language_acquisition", "Language Acquisition", ["computer_science"], "语言习得"),
                ("language_development", "Language Development", ["biomedical", "psychiatry_and_psychology"], "语言发展"),
                ("language_disorder", "Language Disorders", ["biomedical", "diseases"], "语言障碍"),
                ("language_model", "Language Model", ["computer_science"], "语言模型"),
                ("language_therapy", "Language Therapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "语言治疗"),
            ]
        )

    def test_exact_expansion_batch_273_adds_laplace_and_large_language_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("concept_lattice", "Concept Lattice", ["computer_science"], "概念格"),
                ("laplace_equation", "Laplace Equations", ["mathematics"], "拉普拉斯方程"),
                ("laplacian_eigenmap", "Laplacian Eigenmaps", ["computer_science"], "拉普拉斯特征映射"),
                ("laplacian_pyramid", "Laplacian Pyramid", ["computer_science"], "拉普拉斯金字塔"),
                ("large_language_model", "Large Language Models", ["computational_and_artificial_intelligence"], "大语言模型"),
                ("large_scale_wireless_sensor_network", "Large-scale Wireless Sensor Networks", ["computer_science"], "大规模无线传感器网络"),
            ]
        )

    def test_exact_expansion_batch_274_adds_large_scale_and_channel_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("large_vocabulary_continuou_speech_recognition", "Large Vocabulary Continuous Speech Recognition", ["computer_science"], "大词汇量连续语音识别"),
                ("large_conductance_calcium_activated_potassium_channel", "Large-conductance Calcium-activated Potassium Channels", ["biomedical", "chemicals_and_drugs"], "大电导钙激活钾通道"),
                ("large_conductance_calcium_activated_potassium_channel_alpha_subunit", "Large-conductance Calcium-activated Potassium Channel Alpha Subunits", ["biomedical", "chemicals_and_drugs"], "大电导钙激活钾通道α亚基"),
                ("large_conductance_calcium_activated_potassium_channel_beta_subunit", "Large-conductance Calcium-activated Potassium Channel Beta Subunits", ["biomedical", "chemicals_and_drugs"], "大电导钙激活钾通道β亚基"),
                ("large_eddy_simulation", "Large Eddy Simulations", ["physics"], "大涡模拟"),
            ]
        )

    def test_exact_expansion_batch_275_adds_laryngeal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("larynx_artificial", "Larynx, Artificial", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "人工喉"),
                ("laryngeal_cartilag", "Laryngeal Cartilages", ["anatomy", "biomedical"], "喉软骨"),
                ("laryngeal_disease", "Laryngeal Diseases", ["biomedical", "diseases"], "喉疾病"),
                ("laryngeal_neoplasm", "Laryngeal Neoplasms", ["biomedical", "diseases"], "喉肿瘤"),
                ("laryngoscopy", "Laryngoscopy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "喉镜检查"),
                ("larynx", "Larynx", ["anatomy", "biomedical"], "喉部"),
            ]
        )

    def test_exact_expansion_batch_276_adds_laser_basic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("laser_ablation", "Laser Ablation", ["lasers_and_electrooptics"], "激光烧蚀"),
                ("laser_beam_cutting", "Laser Beam Cutting", ["lasers_and_electrooptics"], "激光束切割"),
                ("laser_capture_microdissection", "Laser Capture Microdissection", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "激光捕获显微切割"),
                ("laser_coagulation", "Laser Coagulation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "激光凝固"),
                ("laser_communication", "Laser Communication", ["computer_science"], "激光通信"),
                ("laser_material_processing_techniqu", "Laser Material Processing Techniques", ["engineering", "physical_sciences"], "激光材料加工技术"),
                ("measurement_by_laser_beam", "Measurement By Laser Beam", ["instrumentation_and_measurement"], "激光束测量"),
            ]
        )

    def test_exact_expansion_batch_277_adds_laser_system_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("laser_doppler_vibrometry", "Laser Doppler Vibrometry", ["computer_science"], "激光多普勒测振"),
                ("laser_guide_star", "Laser Guide Star", ["computer_science"], "激光导星"),
                ("laser_induced_damage_threshold", "Laser Induced Damage Thresholds", ["computer_science"], "激光损伤阈值"),
                ("laser_printer", "Laser Printers", ["computers_and_information_processing"], "激光打印机"),
                ("laser_scanning_cytometry", "Laser Scanning Cytometry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "激光扫描细胞术"),
            ]
        )

    def test_exact_expansion_batch_278_adds_laser_imaging_and_laser_type_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("laser_speckle_contrast_imaging", "Laser Speckle Contrast Imaging", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "激光散斑对比成像"),
                ("laser_doppler_flowmetry", "Laser-doppler Flowmetry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "激光多普勒血流测定"),
                ("laser_evoked_potential", "Laser-evoked Potentials", ["biomedical", "phenomena_and_processes"], "激光诱发电位"),
                ("laser_excimer", "Lasers, Excimer", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "准分子激光器"),
                ("laser_semiconductor", "Lasers, Semiconductor", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "半导体激光器"),
                ("optic_and_laser", "Optics & Lasers", ["physics"], "光学与激光"),
            ]
        )

    def test_exact_expansion_batch_279_adds_latent_lateral_and_latex_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("latent_autoimmune_diabet_in_adult", "Latent Autoimmune Diabetes In Adults", ["biomedical", "diseases"], "成人隐匿性自身免疫性糖尿病"),
                ("latent_class_analysi", "Latent Class Analysis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "潜类别分析"),
                ("latent_variable", "Latent Variable", ["computer_science"], "潜变量"),
                ("lateral_ventricl", "Lateral Ventricles", ["anatomy", "biomedical"], "侧脑室"),
                ("latex_hypersensitivity", "Latex Hypersensitivity", ["biomedical", "diseases"], "乳胶超敏反应"),
            ]
        )

    def test_exact_expansion_batch_280_adds_lead_learning_and_least_square_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("non_binary_ldpc_cod", "Non-binary Ldpc Codes", ["computer_science"], "非二进制LDPC码"),
                ("lead_acid_battery", "Lead Acid Batteries", ["industry_applications"], "铅酸电池"),
                ("lead_poisoning", "Lead Poisoning", ["biomedical", "diseases"], "铅中毒"),
                ("learning_automata", "Learning Automata", ["computational_and_artificial_intelligence"], "学习自动机"),
                ("learning_management_system", "Learning Management Systems", ["computational_and_artificial_intelligence"], "学习管理系统"),
                ("least_mean_squar_method", "Least Mean Squares Methods", ["mathematics"], "最小二乘法"),
                ("medical_laboratory_personnel", "Medical Laboratory Personnel", ["biomedical", "named_groups"], "医学实验室人员"),
                ("receptor_laminin", "Receptors, Laminin", ["biomedical", "chemicals_and_drugs"], "层粘连蛋白受体"),
            ]
        )

    def test_exact_expansion_batch_281_adds_least_lectin_and_left_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("least_significant_bit", "Least Significant Bits", ["computer_science"], "最低有效位"),
                ("least_square_support_vector_machine", "Least Square Support Vector Machine", ["computer_science"], "最小二乘支持向量机"),
                ("least_squar_approximation", "Least Squares Approximations", ["computer_science", "mathematics"], "最小二乘近似"),
                ("leave_one_out", "Leave-one-out", ["computer_science"], "留一法"),
                ("lecithin", "Lecithins", ["biomedical", "chemicals_and_drugs"], "卵磷脂类"),
                ("lectin_c_type", "Lectins, C-type", ["biomedical", "chemicals_and_drugs"], "C型凝集素"),
                ("left_atrial_appendage_closure", "Left Atrial Appendage Closure", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "左心耳封堵术"),
            ]
        )

    def test_exact_expansion_batch_282_adds_leg_legacy_and_leiomyoma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("leg_injury", "Leg Injuries", ["biomedical", "diseases"], "腿损伤"),
                ("leg_length_inequality", "Leg Length Inequality", ["biomedical", "diseases"], "下肢长度不等"),
                ("legacy_code", "Legacy Code", ["computer_science"], "遗留代码"),
                ("legacy_system", "Legacy System", ["computer_science"], "遗留系统"),
                ("leigh_disease", "Leigh Disease", ["biomedical", "diseases"], "Leigh病"),
                ("leiomyoma", "Leiomyoma", ["biomedical", "diseases"], "平滑肌瘤"),
                ("leiomyosarcoma", "Leiomyosarcoma", ["biomedical", "diseases"], "平滑肌肉瘤"),
            ]
        )

    def test_exact_expansion_batch_283_adds_leishmania_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("leishmania", "Leishmania", ["biomedical", "organisms"], "利什曼原虫属"),
                ("leishmania_donovani", "Leishmania Donovani", ["biomedical", "organisms"], "杜氏利什曼原虫"),
                ("leishmania_major", "Leishmania Major", ["biomedical", "organisms"], "硕大利什曼原虫"),
                ("leishmaniasi", "Leishmaniasis", ["biomedical", "diseases"], "利什曼病"),
                ("leishmaniasi_cutaneou", "Leishmaniasis, Cutaneous", ["biomedical", "diseases"], "皮肤利什曼病"),
                ("leishmaniasi_mucocutaneou", "Leishmaniasis, Mucocutaneous", ["biomedical", "diseases"], "黏膜皮肤利什曼病"),
                ("leishmaniasi_visceral", "Leishmaniasis, Visceral", ["biomedical", "diseases"], "内脏利什曼病"),
            ]
        )

    def test_exact_expansion_batch_284_adds_lens_and_lentivirus_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lemierre_syndrome", "Lemierre Syndrome", ["biomedical", "diseases"], "Lemierre综合征"),
                ("lenalidomide", "Lenalidomide", ["biomedical", "chemicals_and_drugs"], "来那度胺"),
                ("length_of_stay", "Length Of Stay", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "住院时间"),
                ("lennox_gastaut_syndrome", "Lennox Gastaut Syndrome", ["biomedical", "diseases"], "Lennox-Gastaut综合征"),
                ("lens_crystalline", "Lens, Crystalline", ["anatomy", "biomedical"], "晶状体"),
                ("lens_implantation_intraocular", "Lens Implantation, Intraocular", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "人工晶状体植入术"),
                ("lentiviru", "Lentivirus", ["biomedical", "organisms"], "慢病毒属"),
            ]
        )

    def test_exact_expansion_batch_285_adds_leprosy_leptin_and_leptospira_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("leo_satellite_network", "Leo Satellite Networks", ["computer_science"], "低轨卫星网络"),
                ("leprosy", "Leprosy", ["biomedical", "diseases"], "麻风"),
                ("leprosy_lepromatou", "Leprosy, Lepromatous", ["biomedical", "diseases"], "瘤型麻风"),
                ("leptin", "Leptin", ["biomedical", "chemicals_and_drugs"], "瘦素"),
                ("lepton", "Leptons", ["physics"], "轻子"),
                ("leptospira_interrogan", "Leptospira Interrogans", ["biomedical", "organisms"], "问号钩端螺旋体"),
                ("leptospirosi", "Leptospirosis", ["biomedical", "diseases"], "钩端螺旋体病"),
            ]
        )

    def test_exact_expansion_batch_286_adds_leucine_and_lesch_nyhan_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("leriche_syndrome", "Leriche Syndrome", ["biomedical", "diseases"], "Leriche综合征"),
                ("lesch_nyhan_syndrome", "Lesch-nyhan Syndrome", ["biomedical", "diseases"], "Lesch-Nyhan综合征"),
                ("lethal_dose_50", "Lethal Dose 50", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "半数致死量"),
                ("leucine", "Leucine", ["biomedical", "chemicals_and_drugs"], "亮氨酸"),
                ("leucine_zipper", "Leucine Zippers", ["biomedical", "phenomena_and_processes"], "亮氨酸拉链"),
                ("leucine_rich_repeat_protein", "Leucine-rich Repeat Proteins", ["biomedical", "chemicals_and_drugs"], "富亮氨酸重复蛋白"),
                ("leucyl_aminopeptidase", "Leucyl Aminopeptidase", ["biomedical", "chemicals_and_drugs"], "亮氨酰氨肽酶"),
            ]
        )

    def test_exact_expansion_batch_287_adds_leukemia_factor_and_virus_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("leukapheresi", "Leukapheresis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "白细胞单采术"),
                ("leukemia_inhibitory_factor", "Leukemia Inhibitory Factor", ["biomedical", "chemicals_and_drugs"], "白血病抑制因子"),
                ("leukemia_l1210", "Leukemia L1210", ["biomedical", "diseases"], "L1210白血病"),
                ("leukemia_viru_bovine", "Leukemia Virus, Bovine", ["biomedical", "organisms"], "牛白血病病毒"),
                ("leukemia_viru_feline", "Leukemia Virus, Feline", ["biomedical", "organisms"], "猫白血病病毒"),
                ("leukemia_basophilic_acute", "Leukemia, Basophilic, Acute", ["biomedical", "diseases"], "急性嗜碱性白血病"),
                ("leukemia_erythroblastic_acute", "Leukemia, Erythroblastic, Acute", ["biomedical", "diseases"], "急性红白血病"),
            ]
        )

    def test_exact_expansion_batch_288_adds_leukemia_subtype_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("leukemia_hairy_cell", "Leukemia, Hairy Cell", ["biomedical", "diseases"], "毛细胞白血病"),
                ("leukemia_large_granular_lymphocytic", "Leukemia, Large Granular Lymphocytic", ["biomedical", "diseases"], "大颗粒淋巴细胞白血病"),
                ("leukemia_lymphocytic_chronic_b_cell", "Leukemia, Lymphocytic, Chronic, B-cell", ["biomedical", "diseases"], "B细胞慢性淋巴细胞白血病"),
                ("leukemia_megakaryoblastic_acute", "Leukemia, Megakaryoblastic, Acute", ["biomedical", "diseases"], "急性巨核细胞白血病"),
                ("leukemia_myeloid_acute", "Leukemia, Myeloid, Acute", ["biomedical", "diseases"], "急性髓系白血病"),
                ("leukemia_promyelocytic_acute", "Leukemia, Promyelocytic, Acute", ["biomedical", "diseases"], "急性早幼粒细胞白血病"),
                ("leukemia_lymphoma_adult_t_cell", "Leukemia-lymphoma, Adult T-cell", ["biomedical", "diseases"], "成人T细胞白血病淋巴瘤"),
            ]
        )

    def test_exact_expansion_batch_289_adds_leukocyte_and_leukoplakia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("leukemoid_reaction", "Leukemoid Reaction", ["biomedical", "diseases"], "类白血病反应"),
                ("leukoaraiosi", "Leukoaraiosis", ["biomedical", "diseases"], "脑白质疏松"),
                ("leukocyte_elastase", "Leukocyte Elastase", ["biomedical", "chemicals_and_drugs"], "白细胞弹性蛋白酶"),
                ("leukocyte_rolling", "Leukocyte Rolling", ["biomedical", "phenomena_and_processes"], "白细胞滚动"),
                ("leukocyte_adhesion_deficiency_syndrome", "Leukocyte-adhesion Deficiency Syndrome", ["biomedical", "diseases"], "白细胞黏附缺陷综合征"),
                ("leukodystrophy_metachromatic", "Leukodystrophy, Metachromatic", ["biomedical", "diseases"], "异染性脑白质营养不良"),
                ("leukoplakia_oral", "Leukoplakia, Oral", ["biomedical", "diseases"], "口腔白斑"),
            ]
        )

    def test_exact_expansion_batch_290_adds_leukotriene_and_levodopa_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("leukopoiesi", "Leukopoiesis", ["biomedical", "phenomena_and_processes"], "白细胞生成"),
                ("leukotriene_a4", "Leukotriene A4", ["biomedical", "chemicals_and_drugs"], "白三烯A4"),
                ("leukotriene_antagonist", "Leukotriene Antagonists", ["biomedical", "chemicals_and_drugs"], "白三烯拮抗剂"),
                ("leukotrien", "Leukotrienes", ["biomedical", "chemicals_and_drugs"], "白三烯类"),
                ("leuprolide", "Leuprolide", ["biomedical", "chemicals_and_drugs"], "亮丙瑞林"),
                ("levodopa", "Levodopa", ["biomedical", "chemicals_and_drugs"], "左旋多巴"),
                ("levofloxacin", "Levofloxacin", ["biomedical", "chemicals_and_drugs"], "左氧氟沙星"),
            ]
        )

    def test_exact_expansion_batch_291_adds_lewis_lexical_and_leydig_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lewi_acid", "Lewis Acids", ["biomedical", "chemicals_and_drugs"], "路易斯酸"),
                ("lewi_base", "Lewis Bases", ["biomedical", "chemicals_and_drugs"], "路易斯碱"),
                ("lewy_body_disease", "Lewy Body Disease", ["biomedical", "diseases"], "路易体病"),
                ("lexical_database", "Lexical Database", ["computer_science"], "词汇数据库"),
                ("lexical_semantic", "Lexical Semantics", ["computer_science"], "词汇语义学"),
                ("leydig_cell_tumor", "Leydig Cell Tumor", ["biomedical", "diseases"], "Leydig细胞瘤"),
                ("li_fraumeni_syndrome", "Li-fraumeni Syndrome", ["biomedical", "diseases"], "Li-Fraumeni综合征"),
            ]
        )

    def test_exact_expansion_batch_292_adds_library_license_lidar_and_lichen_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("library_digital", "Libraries, Digital", ["biomedical", "technology_industry_and_agriculture"], "数字图书馆"),
                ("library_medical", "Libraries, Medical", ["biomedical", "technology_industry_and_agriculture"], "医学图书馆"),
                ("library_automation", "Library Automation", ["biomedical", "information_science"], "图书馆自动化"),
                ("license_plate_recognition", "License Plate Recognition", ["computers_and_information_processing"], "车牌识别"),
                ("lichen_planu", "Lichen Planus", ["biomedical", "diseases"], "扁平苔藓"),
                ("lidar_system", "Lidar Systems", ["computer_science"], "激光雷达系统"),
                ("lidocaine", "Lidocaine", ["biomedical", "chemicals_and_drugs"], "利多卡因"),
            ]
        )

    def test_exact_expansion_batch_293_adds_life_ligament_and_ligase_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lie_group", "Lie Groups", ["mathematics"], "李群"),
                ("life_cycle_assessment", "Life Cycle Assessment", ["engineering_management"], "生命周期评价"),
                ("life_expectancy", "Life Expectancy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "预期寿命"),
                ("life_support_system", "Life Support Systems", ["biomedical", "health_care"], "生命支持系统"),
                ("ligament_articular", "Ligaments, Articular", ["anatomy", "biomedical"], "关节韧带"),
                ("ligand_gated_ion_channel", "Ligand-gated Ion Channels", ["biomedical", "chemicals_and_drugs"], "配体门控离子通道"),
                ("ligase_chain_reaction", "Ligase Chain Reaction", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "连接酶链反应"),
            ]
        )

    def test_exact_expansion_batch_294_adds_light_and_lighting_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("light_amplifier", "Light Amplifiers", ["computer_science"], "光放大器"),
                ("light_detection_and_ranging", "Light Detection And Ranging", ["computer_science"], "激光雷达"),
                ("light_emitting_diod", "Light Emitting Diodes", ["components_packaging_and_manufacturing_technology"], "发光二极管"),
                ("light_field", "Light Fields", ["lasers_and_electrooptics"], "光场"),
                ("light_modulation", "Light Modulation", ["computer_science"], "光调制"),
                ("light_sourc", "Light Sources", ["lasers_and_electrooptics"], "光源"),
                ("light_harvesting_protein_complexe", "Light-harvesting Protein Complexes", ["biomedical", "chemicals_and_drugs"], "捕光蛋白复合物"),
            ]
        )

    def test_exact_expansion_batch_295_adds_limb_limit_and_lincosamide_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("likelihood_function", "Likelihood Functions", ["computer_science"], "似然函数"),
                ("limb_buds", "Limb Buds", ["anatomy", "biomedical"], "肢芽"),
                ("limbal_stem_cell_deficiency", "Limbal Stem Cell Deficiency", ["biomedical", "diseases"], "角膜缘干细胞缺乏"),
                ("limbic_system", "Limbic System", ["anatomy", "biomedical"], "边缘系统"),
                ("limit_of_detection", "Limit Of Detection", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "检出限"),
                ("lincomycin", "Lincomycin", ["biomedical", "chemicals_and_drugs"], "林可霉素"),
                ("lindblad_equation", "Lindblad Equation", ["physics"], "Lindblad方程"),
            ]
        )

    def test_exact_expansion_batch_296_adds_linear_system_and_coding_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("line_of_sight_propagation", "Line-of-sight Propagation", ["electromagnetic_compatibility_and_interference"], "视距传播"),
                ("linear_accelerator", "Linear Accelerators", ["nuclear_and_plasma_sciences"], "直线加速器"),
                ("linear_antenna_array", "Linear Antenna Arrays", ["antennas_and_propagation"], "线性天线阵列"),
                ("linear_canonical_transform", "Linear Canonical Transform", ["computer_science"], "线性正则变换"),
                ("linear_cryptanalysi", "Linear Cryptanalysis", ["computer_science"], "线性密码分析"),
                ("linear_discriminant_analysi", "Linear Discriminant Analysis", ["computer_science", "mathematics"], "线性判别分析"),
                ("linear_feedback_control_system", "Linear Feedback Control Systems", ["control_systems"], "线性反馈控制系统"),
            ]
        )

    def test_exact_expansion_batch_297_adds_linear_programming_and_lingual_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("linear_minimum_mean_squared_error", "Linear Minimum Mean-squared Errors", ["computer_science"], "线性最小均方误差"),
                ("linear_predictive_coding", "Linear Predictive Coding", ["computational_and_artificial_intelligence"], "线性预测编码"),
                ("linear_programming", "Linear Programming", ["mathematics"], "线性规划"),
                ("linear_spectral_unmixing", "Linear Spectral Unmixing", ["computer_science"], "线性光谱解混"),
                ("linear_time_invariant_system", "Linear Time-invariant System", ["computer_science"], "线性时不变系统"),
                ("linezolid", "Linezolid", ["biomedical", "chemicals_and_drugs"], "利奈唑胺"),
                ("lingual_nerve", "Lingual Nerve", ["anatomy", "biomedical"], "舌神经"),
            ]
        )

    def test_exact_expansion_batch_298_adds_link_linoleic_and_lip_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("link_prediction", "Link Prediction", ["computer_science"], "链接预测"),
                ("linkage_disequilibrium", "Linkage Disequilibrium", ["biomedical", "phenomena_and_processes"], "连锁不平衡"),
                ("linked_open_data", "Linked Open Data", ["computer_science"], "开放关联数据"),
                ("linoleic_acid", "Linoleic Acids", ["biomedical", "chemicals_and_drugs"], "亚油酸"),
                ("linolenic_acid", "Linolenic Acids", ["biomedical", "chemicals_and_drugs"], "亚麻酸"),
                ("lip_disease", "Lip Diseases", ["biomedical", "diseases"], "唇疾病"),
                ("lipase", "Lipase", ["biomedical", "chemicals_and_drugs"], "脂肪酶"),
            ]
        )

    def test_exact_expansion_batch_299_adds_lipid_and_lipodystrophy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lipedema", "Lipedema", ["biomedical", "diseases"], "脂肪水肿"),
                ("lipid_bilayer", "Lipid Bilayers", ["biomedical", "chemicals_and_drugs"], "脂质双层"),
                ("lipid_droplet", "Lipid Droplets", ["anatomy", "biomedical"], "脂滴"),
                ("lipid_peroxidation", "Lipid Peroxidation", ["biomedical", "phenomena_and_processes"], "脂质过氧化"),
                ("lipidomic", "Lipidomics", ["biomedical", "disciplines_and_occupations"], "脂质组学"),
                ("lipoblastoma", "Lipoblastoma", ["biomedical", "diseases"], "脂肪母细胞瘤"),
                ("lipodystrophy", "Lipodystrophy", ["biomedical", "diseases"], "脂肪营养不良"),
            ]
        )

    def test_exact_expansion_batch_300_adds_lipoprotein_liquid_and_liposarcoma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lipopolysaccharide_binding_protein", "Lipopolysaccharide-binding Protein", ["biomedical", "chemicals_and_drugs"], "脂多糖结合蛋白"),
                ("lipopolysaccharid", "Lipopolysaccharides", ["biomedical", "chemicals_and_drugs"], "脂多糖"),
                ("lipoprotein_lipase", "Lipoprotein Lipase", ["biomedical", "chemicals_and_drugs"], "脂蛋白脂肪酶"),
                ("liposarcoma", "Liposarcoma", ["biomedical", "diseases"], "脂肪肉瘤"),
                ("liposom", "Liposomes", ["biomedical", "chemicals_and_drugs"], "脂质体"),
                ("liquid_biopsy", "Liquid Biopsy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "液体活检"),
                ("liquid_chromatography_mass_spectrometry", "Liquid Chromatography-mass Spectrometry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "液相色谱-质谱法"),
            ]
        )

    def test_exact_expansion_batch_301_adds_liquid_listeria_and_liraglutide_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("liquid_crystal_spatial_light_modulator", "Liquid Crystal Spatial Light Modulators", ["computer_science"], "液晶空间光调制器"),
                ("liquid_liquid_extraction", "Liquid-liquid Extraction", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "液-液萃取"),
                ("liraglutide", "Liraglutide", ["biomedical", "chemicals_and_drugs"], "利拉鲁肽"),
                ("lisinopril", "Lisinopril", ["biomedical", "chemicals_and_drugs"], "赖诺普利"),
                ("lissencephaly", "Lissencephaly", ["biomedical", "diseases"], "无脑回畸形"),
                ("listeria_monocytogen", "Listeria Monocytogenes", ["biomedical", "organisms"], "单核细胞增生李斯特菌"),
                ("listeriosi", "Listeriosis", ["biomedical", "diseases"], "李斯特菌病"),
            ]
        )

    def test_exact_expansion_batch_302_adds_lithium_lithotripsy_and_live_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lithiasi", "Lithiasis", ["biomedical", "diseases"], "结石病"),
                ("lithium_ion_battery", "Lithium-ion Batteries", ["industry_applications"], "锂离子电池"),
                ("lithium_carbonate", "Lithium Carbonate", ["biomedical", "chemicals_and_drugs"], "碳酸锂"),
                ("lithocholic_acid", "Lithocholic Acid", ["biomedical", "chemicals_and_drugs"], "石胆酸"),
                ("lithotripsy", "Lithotripsy", ["engineering_in_medicine_and_biology"], "碎石术"),
                ("litter_size", "Litter Size", ["biomedical", "phenomena_and_processes"], "窝产仔数"),
                ("livedo_reticulari", "Livedo Reticularis", ["biomedical", "diseases"], "网状青斑"),
            ]
        )

    def test_exact_expansion_batch_303_adds_liver_livestock_and_lizard_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("liver", "Liver", ["anatomy", "biomedical"], "肝脏"),
                ("liver_abscess_amebic", "Liver Abscess, Amebic", ["biomedical", "diseases"], "阿米巴性肝脓肿"),
                ("liver_cirrhosi_alcoholic", "Liver Cirrhosis, Alcoholic", ["biomedical", "diseases"], "酒精性肝硬化"),
                ("liver_disease_parasitic", "Liver Diseases, Parasitic", ["biomedical", "diseases"], "寄生虫性肝病"),
                ("liver_specific_organic_anion_transporter_1", "Liver-specific Organic Anion Transporter 1", ["biomedical", "chemicals_and_drugs"], "肝特异性有机阴离子转运蛋白1"),
                ("livestock", "Livestock", ["biomedical", "organisms"], "家畜"),
                ("living_donor", "Living Donors", ["biomedical", "named_groups"], "活体供者"),
            ]
        )

    def test_exact_expansion_batch_304_adds_load_and_local_area_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("load_balancing_algorithm", "Load Balancing Algorithms", ["computer_science"], "负载均衡算法"),
                ("load_frequency_control", "Load Frequency Control", ["computer_science"], "负荷频率控制"),
                ("load_imbalance", "Load Imbalance", ["computer_science"], "负载不均衡"),
                ("load_management", "Load Management", ["power_engineering_and_energy"], "负荷管理"),
                ("loaded_antenna", "Loaded Antennas", ["antennas_and_propagation"], "加载天线"),
                ("lobeline", "Lobeline", ["biomedical", "chemicals_and_drugs"], "洛贝林"),
                ("local_binary_pattern", "Local Binary Pattern", ["computer_science"], "局部二值模式"),
            ]
        )

    def test_exact_expansion_batch_305_adds_local_feature_and_projection_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("local_descriptor", "Local Descriptors", ["computer_science"], "局部描述符"),
                ("local_field_potential", "Local Field Potentials", ["signal_processing"], "局部场电位"),
                ("local_image_descriptor", "Local Image Descriptors", ["computer_science"], "局部图像描述符"),
                ("local_lymph_node_assay", "Local Lymph Node Assay", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "局部淋巴结试验"),
                ("local_search_operator", "Local Search Operators", ["computer_science"], "局部搜索算子"),
                ("locality_preserving_projection", "Locality Preserving Projection", ["computer_science"], "局部保持投影"),
                ("locally_linear_embedding", "Locally Linear Embedding", ["computer_science"], "局部线性嵌入"),
            ]
        )

    def test_exact_expansion_batch_306_adds_localization_and_location_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("localization_accuracy", "Localization Accuracy", ["computer_science"], "定位精度"),
                ("localization_schem", "Localization Schemes", ["computer_science"], "定位方案"),
                ("location_awareness", "Location Awareness", ["communications_technology"], "位置感知"),
                ("location_based_service", "Location Based Service", ["computer_science"], "基于位置的服务"),
                ("location_fingerprinting", "Location Fingerprinting", ["computer_science"], "位置指纹"),
                ("location_privacy", "Location Privacy", ["computer_science"], "位置隐私"),
                ("location_based_social_network", "Location-based Social Networks", ["computer_science"], "基于位置的社交网络"),
            ]
        )

    def test_exact_expansion_batch_307_adds_locus_log_and_logic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("locked_in_syndrome", "Locked-in Syndrome", ["biomedical", "diseases"], "闭锁综合征"),
                ("locu_coeruleu", "Locus Coeruleus", ["anatomy", "biomedical"], "蓝斑"),
                ("lod_score", "Lod Score", ["computer_science"], "LOD评分"),
                ("loey_dietz_syndrome", "Loeys-dietz Syndrome", ["biomedical", "diseases"], "Loeys-Dietz综合征"),
                ("log_analysi", "Log Analysis", ["computer_science"], "日志分析"),
                ("log_normal_distribution", "Log-normal Distribution", ["mathematics"], "对数正态分布"),
                ("logic_circuit", "Logic Circuits", ["circuits_and_systems"], "逻辑电路"),
            ]
        )

    def test_exact_expansion_batch_308_adds_logic_and_logistic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("logic_gate", "Logic Gate", ["computer_science"], "逻辑门"),
                ("logic_programming", "Logic Programming", ["computers_and_information_processing"], "逻辑编程"),
                ("logic_synthesi", "Logic Synthesis", ["computer_science"], "逻辑综合"),
                ("logical_observation_identifier_nam_and_cod", "Logical Observation Identifiers Names And Codes", ["biomedical", "information_science"], "逻辑观测标识符名称和代码"),
                ("logistic_map", "Logistic Map", ["computer_science"], "Logistic映射"),
                ("logistic_regression", "Logistic Regression", ["computer_science"], "Logistic回归"),
                ("logistic_service_provider", "Logistics Service Provider", ["computer_science"], "物流服务提供商"),
            ]
        )

    def test_exact_expansion_batch_309_adds_long_term_and_lstm_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("long_interspersed_nucleotide_element", "Long Interspersed Nucleotide Elements", ["biomedical", "phenomena_and_processes"], "长散在核苷酸元件"),
                ("long_period_fiber_grating", "Long Period Fiber Grating", ["computer_science"], "长周期光纤光栅"),
                ("long_qt_syndrome", "Long QT Syndrome", ["biomedical", "diseases"], "长QT综合征"),
                ("long_short_term_memory", "Long Short Term Memory", ["computational_and_artificial_intelligence"], "长短期记忆"),
                ("long_term_adverse_effect", "Long Term Adverse Effects", ["biomedical", "diseases"], "长期不良反应"),
                ("long_chain_3_hydroxyacyl_coa_dehydrogenase", "Long-chain-3-hydroxyacyl-coa Dehydrogenase", ["biomedical", "chemicals_and_drugs"], "长链3-羟酰辅酶A脱氢酶"),
                ("long_term_potentiation", "Long-term Potentiation", ["biomedical", "phenomena_and_processes"], "长时程增强"),
            ]
        )

    def test_exact_expansion_batch_310_adds_longitudinal_loop_and_losartan_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("longevity", "Longevity", ["biomedical", "phenomena_and_processes"], "长寿"),
                ("longitudinal_control", "Longitudinal Control", ["computer_science"], "纵向控制"),
                ("longitudinal_ligament", "Longitudinal Ligaments", ["anatomy", "biomedical"], "纵韧带"),
                ("loop_antenna", "Loop Antennas", ["antennas_and_propagation"], "环形天线"),
                ("loop_of_henle", "Loop Of Henle", ["anatomy", "biomedical"], "Henle袢"),
                ("loopy_belief_propagation", "Loopy Belief Propagation", ["computer_science"], "有环置信传播"),
                ("losartan", "Losartan", ["biomedical", "chemicals_and_drugs"], "氯沙坦"),
            ]
        )

    def test_exact_expansion_batch_311_adds_lossless_and_lovastatin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("loss_of_function_mutation", "Loss Of Function Mutation", ["biomedical", "phenomena_and_processes"], "功能缺失突变"),
                ("loss_of_heterozygosity", "Loss Of Heterozygosity", ["computer_science"], "杂合性缺失"),
                ("lossless_coding", "Lossless Coding", ["computer_science"], "无损编码"),
                ("lossless_data_compression", "Lossless Data Compression", ["computer_science"], "无损数据压缩"),
                ("lossless_data_hiding", "Lossless Data Hiding", ["computer_science"], "无损数据隐藏"),
                ("lossy_compression", "Lossy Compression", ["computer_science"], "有损压缩"),
                ("lovastatin", "Lovastatin", ["biomedical", "chemicals_and_drugs"], "洛伐他汀"),
            ]
        )

    def test_exact_expansion_batch_312_adds_low_power_and_ldpc_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("low_back_pain", "Low Back Pain", ["biomedical", "diseases"], "下背痛"),
                ("low_bit_rate", "Low Bit Rate", ["computer_science"], "低比特率"),
                ("low_carbon_economy", "Low Carbon Economy", ["power_engineering_and_energy"], "低碳经济"),
                ("low_density_parity_check_cod", "Low Density Parity Check Codes", ["computer_science"], "低密度奇偶校验码"),
                ("low_earth_orbit_satellit", "Low Earth Orbit Satellites", ["aerospace_and_electronic_systems"], "低地球轨道卫星"),
                ("low_latency_communication", "Low Latency Communication", ["communications_technology"], "低时延通信"),
                ("low_power", "Low Power", ["computer_science"], "低功耗"),
            ]
        )

    def test_exact_expansion_batch_313_adds_low_resolution_and_low_level_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("low_power_design", "Low Power Design", ["computer_science"], "低功耗设计"),
                ("low_resolution", "Low Resolution", ["computer_science"], "低分辨率"),
                ("low_resolution_imag", "Low Resolution Images", ["computer_science"], "低分辨率图像"),
                ("low_signal_to_noise_ratio", "Low Signal-to-noise Ratio", ["computer_science"], "低信噪比"),
                ("low_tension_glaucoma", "Low Tension Glaucoma", ["biomedical", "diseases"], "低眼压性青光眼"),
                ("low_dimensional_manifold", "Low-dimensional Manifolds", ["computer_science"], "低维流形"),
                ("low_level_light_therapy", "Low-level Light Therapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "低强度光疗"),
            ]
        )

    def test_exact_expansion_batch_314_adds_low_pass_lower_and_low_rank_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("low_noise_amplifier", "Low-noise Amplifiers", ["signal_processing"], "低噪声放大器"),
                ("low_pass_filter", "Low-pass Filters", ["circuits_and_systems"], "低通滤波器"),
                ("low_power_wide_area_network", "Low-power Wide Area Networks", ["communications_technology"], "低功耗广域网"),
                ("low_rank_adaptation", "Low-rank Adaptation", ["computer_science"], "低秩适配"),
                ("low_temperature_plasma", "Low-temperature Plasmas", ["nuclear_and_plasma_sciences"], "低温等离子体"),
                ("lower_bound", "Lower Bound", ["mathematics"], "下界"),
                ("lower_urinary_tract_symptom", "Lower Urinary Tract Symptoms", ["biomedical", "diseases"], "下尿路症状"),
            ]
        )

    def test_exact_expansion_batch_315_adds_lte_ltl_lu_and_lubricant_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lown_ganong_levine_syndrome", "Lown-ganong-levine Syndrome", ["biomedical", "diseases"], "Lown-Ganong-Levine综合征"),
                ("lte_uplink", "Lte Uplink", ["computer_science"], "LTE上行链路"),
                ("lti_system", "Lti Systems", ["computer_science"], "LTI系统"),
                ("ltl_model_checking", "Ltl Model-checking", ["computer_science"], "LTL模型检测"),
                ("lu_factorization", "Lu Factorization", ["computer_science"], "LU分解"),
                ("lubiprostone", "Lubiprostone", ["biomedical", "chemicals_and_drugs"], "鲁比前列酮"),
                ("lubricating_oils", "Lubricating Oils", ["materials_elements_and_compounds"], "润滑油"),
            ]
        )

    def test_exact_expansion_batch_316_adds_luciferase_lumbar_and_lung_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("luciferase", "Luciferases", ["biomedical", "chemicals_and_drugs"], "荧光素酶"),
                ("luciferase_firefly", "Luciferases, Firefly", ["biomedical", "chemicals_and_drugs"], "萤火虫荧光素酶"),
                ("ludwig_s_angina", "Ludwig's Angina", ["biomedical", "diseases"], "路德维希咽峡炎"),
                ("lumbar_vertebrae", "Lumbar Vertebrae", ["anatomy", "biomedical"], "腰椎"),
                ("lumbosacral_plexu", "Lumbosacral Plexus", ["anatomy", "biomedical"], "腰骶丛"),
                ("luminol", "Luminol", ["biomedical", "chemicals_and_drugs"], "鲁米诺"),
                ("lung", "Lung", ["anatomy", "biomedical"], "肺脏"),
            ]
        )

    def test_exact_expansion_batch_317_adds_lung_disease_and_lupus_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lung_abscess", "Lung Abscess", ["biomedical", "diseases"], "肺脓肿"),
                ("lung_compliance", "Lung Compliance", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "肺顺应性"),
                ("lung_disease_interstitial", "Lung Diseases, Interstitial", ["biomedical", "diseases"], "间质性肺疾病"),
                ("lung_neoplasm", "Lung Neoplasms", ["biomedical", "diseases"], "肺肿瘤"),
                ("lung_transplantation", "Lung Transplantation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "肺移植"),
                ("lupu_erythematosu_systemic", "Lupus Erythematosus, Systemic", ["biomedical", "diseases"], "系统性红斑狼疮"),
                ("lupu_nephriti", "Lupus Nephritis", ["biomedical", "diseases"], "狼疮性肾炎"),
            ]
        )

    def test_exact_expansion_batch_318_adds_lutein_lutetium_and_lyapunov_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lurasidone_hydrochloride", "Lurasidone Hydrochloride", ["biomedical", "chemicals_and_drugs"], "盐酸鲁拉西酮"),
                ("luteal_phase", "Luteal Phase", ["biomedical", "phenomena_and_processes"], "黄体期"),
                ("luteinizing_hormone", "Luteinizing Hormone", ["biomedical", "chemicals_and_drugs"], "黄体生成素"),
                ("luteolytic_agent", "Luteolytic Agents", ["biomedical", "chemicals_and_drugs"], "溶黄体剂"),
                ("lutetium", "Lutetium", ["materials_elements_and_compounds"], "镥元素"),
                ("lyapunov_equation", "Lyapunov Equation", ["computer_science"], "Lyapunov方程"),
                ("lyapunov_krasovskii_functional", "Lyapunov-krasovskii Functional", ["computer_science"], "Lyapunov-Krasovskii泛函"),
            ]
        )

    def test_exact_expansion_batch_319_adds_lyme_and_lymphatic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lyase", "Lyases", ["biomedical", "chemicals_and_drugs"], "裂解酶类"),
                ("lycopene", "Lycopene", ["biomedical", "chemicals_and_drugs"], "番茄红素"),
                ("lyme_disease", "Lyme Disease", ["biomedical", "diseases"], "莱姆病"),
                ("lyme_neuroborreliosi", "Lyme Neuroborreliosis", ["biomedical", "diseases"], "莱姆神经疏螺旋体病"),
                ("lymphadeniti", "Lymphadenitis", ["biomedical", "diseases"], "淋巴结炎"),
                ("lymphangioma_cystic", "Lymphangioma, Cystic", ["biomedical", "diseases"], "囊性淋巴管瘤"),
                ("lymphedema", "Lymphedema", ["biomedical", "diseases"], "淋巴水肿"),
            ]
        )

    def test_exact_expansion_batch_320_adds_lymphocyte_and_lymphoma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lymphocyte_activation", "Lymphocyte Activation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "淋巴细胞活化"),
                ("lymphocyte_count", "Lymphocyte Count", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "淋巴细胞计数"),
                ("lymphocyte_function_associated_antigen_1", "Lymphocyte Function-associated Antigen-1", ["biomedical", "chemicals_and_drugs"], "淋巴细胞功能相关抗原1"),
                ("lymphocyte_subset", "Lymphocyte Subsets", ["anatomy", "biomedical"], "淋巴细胞亚群"),
                ("lymphocytic_choriomeningiti", "Lymphocytic Choriomeningitis", ["biomedical", "diseases"], "淋巴细胞性脉络丛脑膜炎"),
                ("lymphogranuloma_venereum", "Lymphogranuloma Venereum", ["biomedical", "diseases"], "性病性淋巴肉芽肿"),
                ("lymphoma_non_hodgkin", "Lymphoma, Non-hodgkin", ["biomedical", "diseases"], "非霍奇金淋巴瘤"),
            ]
        )

    def test_exact_expansion_batch_321_adds_lymphoma_diagnosis_and_large_cell_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lymphadenopathy_diagnosi_and_analysi", "Lymphadenopathy Diagnosis And Analysis", ["health_sciences", "medicine"], "淋巴结病诊断与分析"),
                ("lymphatic_disorder_and_treatment", "Lymphatic Disorders And Treatments", ["health_sciences", "medicine"], "淋巴系统疾病与治疗"),
                ("lymphatic_system_and_disease", "Lymphatic System And Diseases", ["health_sciences", "medicine"], "淋巴系统与疾病"),
                ("lymphoma_diagnosi_and_treatment", "Lymphoma Diagnosis And Treatment", ["health_sciences", "medicine"], "淋巴瘤诊断与治疗"),
                ("lymphoma_large_cell_immunoblastic", "Lymphoma, Large-cell, Immunoblastic", ["biomedical", "diseases"], "免疫母细胞性大细胞淋巴瘤"),
                ("lymphoma_primary_effusion", "Lymphoma, Primary Effusion", ["biomedical", "diseases"], "原发性渗出性淋巴瘤"),
                ("lymphomatoid_granulomatosi", "Lymphomatoid Granulomatosis", ["biomedical", "diseases"], "淋巴瘤样肉芽肿病"),
            ]
        )

    def test_exact_expansion_batch_322_adds_cutaneous_lymphoma_and_lymphopenia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lymphoma_primary_cutaneou_anaplastic_large_cell", "Lymphoma, Primary Cutaneous Anaplastic Large Cell", ["biomedical", "diseases"], "原发性皮肤间变性大细胞淋巴瘤"),
                ("lymphoma_t_cell_cutaneou", "Lymphoma, T-cell, Cutaneous", ["biomedical", "diseases"], "皮肤T细胞淋巴瘤"),
                ("lymphoma_t_cell_peripheral", "Lymphoma, T-cell, Peripheral", ["biomedical", "diseases"], "外周T细胞淋巴瘤"),
                ("lymphomatoid_papulosi", "Lymphomatoid Papulosis", ["biomedical", "diseases"], "淋巴瘤样丘疹病"),
                ("lymphopenia", "Lymphopenia", ["biomedical", "diseases"], "淋巴细胞减少症"),
                ("lymphopoiesi", "Lymphopoiesis", ["biomedical", "phenomena_and_processes"], "淋巴细胞生成"),
                ("lymphoproliferative_disorder", "Lymphoproliferative Disorders", ["biomedical", "diseases"], "淋巴增殖性疾病"),
            ]
        )

    def test_exact_expansion_batch_323_adds_lymphoscintigraphy_lymphotoxin_and_lynch_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lymphoscintigraphy", "Lymphoscintigraphy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "淋巴显像"),
                ("lymphotoxin_alpha1_beta2_heterotrimer", "Lymphotoxin Alpha1, Beta2 Heterotrimer", ["biomedical", "chemicals_and_drugs"], "淋巴毒素α1β2异源三聚体"),
                ("lymphotoxin_beta_receptor", "Lymphotoxin Beta Receptor", ["biomedical", "chemicals_and_drugs"], "淋巴毒素β受体"),
                ("lymphotoxin_alpha", "Lymphotoxin-alpha", ["biomedical", "chemicals_and_drugs"], "淋巴毒素α"),
                ("lymphotoxin_beta", "Lymphotoxin-beta", ["biomedical", "chemicals_and_drugs"], "淋巴毒素β"),
                ("lynch_syndrome_ii", "Lynch Syndrome II", ["biomedical", "diseases"], "Lynch综合征II"),
                ("lynestrenol", "Lynestrenol", ["biomedical", "chemicals_and_drugs"], "利奈孕醇"),
            ]
        )

    def test_exact_expansion_batch_324_adds_lyngbya_lysergic_and_lysholm_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lyngbya", "Lyngbya", ["biomedical", "organisms"], "鞘丝藻属"),
                ("lyngbya_toxin", "Lyngbya Toxins", ["biomedical", "chemicals_and_drugs"], "鞘丝藻毒素"),
                ("lynx", "Lynx", ["biomedical", "organisms"], "猞猁属"),
                ("lypressin", "Lypressin", ["biomedical", "chemicals_and_drugs"], "赖氨加压素"),
                ("lysergic_acid", "Lysergic Acid", ["biomedical", "chemicals_and_drugs"], "麦角酸"),
                ("lysergic_acid_diethylamide", "Lysergic Acid Diethylamide", ["biomedical", "chemicals_and_drugs"], "麦角酸二乙胺"),
                ("lysholm_knee_score", "Lysholm Knee Score", ["biomedical", "health_care"], "Lysholm膝关节评分"),
            ]
        )

    def test_exact_expansion_batch_325_adds_lysine_and_lysine_enzyme_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lysimachia", "Lysimachia", ["biomedical", "organisms"], "珍珠菜属"),
                ("lysine", "Lysine", ["biomedical", "chemicals_and_drugs"], "赖氨酸"),
                ("lysine_acetyltransferase_5", "Lysine Acetyltransferase 5", ["biomedical", "chemicals_and_drugs"], "赖氨酸乙酰转移酶5"),
                ("lysine_acetyltransferase", "Lysine Acetyltransferases", ["biomedical", "chemicals_and_drugs"], "赖氨酸乙酰转移酶"),
                ("lysine_carboxypeptidase", "Lysine Carboxypeptidase", ["biomedical", "chemicals_and_drugs"], "赖氨酸羧肽酶"),
                ("lysine_trna_ligase", "Lysine-trna Ligase", ["biomedical", "chemicals_and_drugs"], "赖氨酰tRNA连接酶"),
                ("lysinoalanine", "Lysinoalanine", ["biomedical", "chemicals_and_drugs"], "赖氨酰丙氨酸"),
            ]
        )

    def test_exact_expansion_batch_326_adds_lysogeny_and_lysophospholipid_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lysobacter", "Lysobacter", ["biomedical", "organisms"], "溶杆菌属"),
                ("lysogeny", "Lysogeny", ["biomedical", "phenomena_and_processes"], "溶原性"),
                ("lysophosphatidylcholin", "Lysophosphatidylcholines", ["biomedical", "chemicals_and_drugs"], "溶血磷脂酰胆碱"),
                ("lysophospholipase", "Lysophospholipase", ["biomedical", "chemicals_and_drugs"], "溶血磷脂酶"),
                ("lysophospholipase_d", "Lysophospholipase D", ["biomedical", "chemicals_and_drugs"], "溶血磷脂酶D"),
                ("lysophospholipid", "Lysophospholipids", ["biomedical", "chemicals_and_drugs"], "溶血磷脂"),
                ("lysosomal_membrane_protein", "Lysosomal Membrane Proteins", ["biomedical", "chemicals_and_drugs"], "溶酶体膜蛋白"),
            ]
        )

    def test_exact_expansion_batch_327_adds_lysosomal_storage_and_lamp_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lysosomal_storage_disease", "Lysosomal Storage Diseases", ["biomedical", "diseases"], "溶酶体贮积病"),
                ("lysosomal_storage_disease_nervou_system", "Lysosomal Storage Diseases, Nervous System", ["biomedical", "diseases"], "神经系统溶酶体贮积病"),
                ("lysosomal_storage_disorder_research", "Lysosomal Storage Disorders Research", ["health_sciences", "medicine"], "溶酶体贮积症研究"),
                ("lysosomal_associated_membrane_protein_1", "Lysosomal-associated Membrane Protein 1", ["biomedical", "chemicals_and_drugs"], "溶酶体相关膜蛋白1"),
                ("lysosomal_associated_membrane_protein_2", "Lysosomal-associated Membrane Protein 2", ["biomedical", "chemicals_and_drugs"], "溶酶体相关膜蛋白2"),
                ("lysosomal_associated_membrane_protein_3", "Lysosomal-associated Membrane Protein 3", ["biomedical", "chemicals_and_drugs"], "溶酶体相关膜蛋白3"),
                ("lysosom", "Lysosomes", ["anatomy", "biomedical"], "溶酶体"),
            ]
        )

    def test_exact_expansion_batch_328_adds_lysostaphin_m_phase_and_m_sequence_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("lysostaphin", "Lysostaphin", ["biomedical", "chemicals_and_drugs"], "溶葡萄球菌酶"),
                ("lyssaviru", "Lyssavirus", ["biomedical", "organisms"], "丽沙病毒属"),
                ("lythraceae", "Lythraceae", ["biomedical", "organisms"], "千屈菜科"),
                ("lythrum", "Lythrum", ["biomedical", "organisms"], "千屈菜属"),
                ("m_phase_cell_cycle_checkpoint", "M Phase Cell Cycle Checkpoints", ["biomedical", "phenomena_and_processes"], "M期细胞周期检查点"),
                ("m_sequence", "M Sequence", ["computer_science"], "M序列"),
                ("m_commerce", "M-commerce", ["computer_science"], "移动商务"),
            ]
        )

    def test_exact_expansion_batch_329_adds_m_learning_mac_address_and_mac_layer_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("m_learning", "M-learning", ["computer_science"], "移动学习"),
                ("m_matrix", "M-matrix", ["computer_science"], "M矩阵"),
                ("m2m", "M2m", ["computer_science"], "M2M通信"),
                ("maackia", "Maackia", ["biomedical", "organisms"], "马鞍树属"),
                ("mac_address", "Mac Address", ["computer_science"], "MAC地址"),
                ("mac_layer", "Mac Layer", ["computer_science"], "MAC层"),
                ("macadamia", "Macadamia", ["biomedical", "organisms"], "澳洲坚果属"),
            ]
        )

    def test_exact_expansion_batch_330_adds_macaca_species_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("macaca", "Macaca", ["biomedical", "organisms"], "猕猴属"),
                ("macaca_arctoid", "Macaca Arctoides", ["biomedical", "organisms"], "熊猴"),
                ("macaca_fasciculari", "Macaca Fascicularis", ["biomedical", "organisms"], "食蟹猴"),
                ("macaca_fuscata", "Macaca Fuscata", ["biomedical", "organisms"], "日本猕猴"),
                ("macaca_mulatta", "Macaca Mulatta", ["biomedical", "organisms"], "恒河猴"),
                ("macaca_nemestrina", "Macaca Nemestrina", ["biomedical", "organisms"], "豚尾猴"),
                ("macaca_radiata", "Macaca Radiata", ["biomedical", "organisms"], "冠毛猕猴"),
            ]
        )

    def test_exact_expansion_batch_331_adds_mach_and_machinability_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("macau", "Macau", ["biomedical", "geographicals"], "澳门"),
                ("mach_zehnder_modulator", "Mach Zehnder Modulator", ["computer_science"], "Mach-Zehnder调制器"),
                ("mach_zehnder", "Mach-zehnder", ["computer_science"], "Mach-Zehnder结构"),
                ("machado_joseph_disease", "Machado-joseph Disease", ["biomedical", "diseases"], "Machado-Joseph病"),
                ("machiavellianism", "Machiavellianism", ["biomedical", "psychiatry_and_psychology"], "马基雅维利主义"),
                ("machinability", "Machinability", ["computer_science"], "可加工性"),
                ("machine_component", "Machine Components", ["industry_applications"], "机器部件"),
            ]
        )

    def test_exact_expansion_batch_332_adds_machine_design_and_machine_learning_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("machine_design", "Machine Design", ["computer_science"], "机械设计"),
                ("machine_ethic", "Machine Ethics", ["change"], "机器伦理"),
                ("machine_intelligence", "Machine Intelligence", ["computational_and_artificial_intelligence"], "机器智能"),
                ("machine_learning", "Machine Learning", ["computational_and_artificial_intelligence"], "机器学习"),
                ("machine_learning_algorithm__2", "Machine Learning Algorithms", ["biomedical", "phenomena_and_processes"], "机器学习算法"),
                ("machine_learning_and_elm", "Machine Learning And ELM", ["computer_science", "physical_sciences"], "机器学习与极限学习机"),
                ("machine_listening", "Machine Listening", ["computational_and_artificial_intelligence"], "机器听觉"),
            ]
        )

    def test_exact_expansion_batch_333_adds_machine_learning_application_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("machine_learning_in_bioinformatic", "Machine Learning In Bioinformatics", ["biochemistry_genetics_and_molecular_biology", "life_sciences"], "生物信息学中的机器学习"),
                ("machine_learning_in_healthcare", "Machine Learning In Healthcare", ["computer_science", "physical_sciences"], "医疗保健中的机器学习"),
                ("machine_learning_in_material_science", "Machine Learning In Materials Science", ["materials_science", "physical_sciences"], "材料科学中的机器学习"),
                ("machine_perception", "Machine Perception", ["computer_science"], "机器感知"),
                ("machine_shop", "Machine Shops", ["industry_applications"], "机械加工车间"),
                ("machine_storytelling", "Machine Storytelling", ["computer_science"], "机器叙事"),
                ("machine_tool", "Machine Tools", ["industry_applications"], "机床"),
            ]
        )

    def test_exact_expansion_batch_334_adds_machine_translation_and_machining_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("machine_translation", "Machine Translation", ["systems_man_and_cybernetics"], "机器翻译"),
                ("machine_vector_control", "Machine Vector Control", ["industrial_electronics"], "电机矢量控制"),
                ("machine_vision", "Machine Vision", ["computers_and_information_processing"], "机器视觉"),
                ("machine_winding", "Machine Windings", ["dielectrics_and_electrical_insulation"], "电机绕组"),
                ("machine_to_machine_m2m", "Machine-to-machine (m2m)", ["computer_science"], "机器到机器通信"),
                ("machine_to_machine_communication", "Machine-to-machine Communications", ["communications_technology"], "机器到机器通信"),
                ("machined_surface", "Machined Surface", ["computer_science"], "加工表面"),
            ]
        )

    def test_exact_expansion_batch_335_adds_machinery_and_machining_operation_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("machinery", "Machinery", ["industry_applications"], "机械"),
                ("machinery_production_industry", "Machinery Production Industries", ["industry_applications"], "机械制造业"),
                ("machining", "Machining", ["industry_applications"], "机械加工"),
                ("machining_center", "Machining Centers", ["computer_science"], "加工中心"),
                ("machining_efficiency", "Machining Efficiency", ["computer_science"], "加工效率"),
                ("machining_operation", "Machining Operations", ["computer_science"], "机械加工操作"),
                ("machining_parameter", "Machining Parameters", ["computer_science"], "加工参数"),
            ]
        )

    def test_exact_expansion_batch_336_adds_macro_and_macromolecule_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("machining_time", "Machining Time", ["computer_science"], "加工时间"),
                ("maclura", "Maclura", ["biomedical", "organisms"], "柘属"),
                ("macro_block", "Macro Block", ["computer_science"], "宏块"),
                ("macroautophagy", "Macroautophagy", ["biomedical", "phenomena_and_processes"], "巨自噬"),
                ("macrocyclic_compound", "Macrocyclic Compounds", ["biomedical", "chemicals_and_drugs"], "大环化合物"),
                ("macroeconomic_factor", "Macroeconomic Factors", ["computer_science"], "宏观经济因素"),
                ("macrolid", "Macrolides", ["biomedical", "chemicals_and_drugs"], "大环内酯类"),
            ]
        )

    def test_exact_expansion_batch_337_adds_macroglobulin_and_macrophage_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("macroglobulin", "Macroglobulins", ["biomedical", "chemicals_and_drugs"], "巨球蛋白"),
                ("macroglossia", "Macroglossia", ["biomedical", "diseases"], "巨舌症"),
                ("macromolecular_substanc", "Macromolecular Substances", ["biomedical", "chemicals_and_drugs"], "大分子物质"),
                ("macromolecul", "Macromolecules", ["physics"], "大分子"),
                ("macronucleu", "Macronucleus", ["anatomy", "biomedical"], "大核"),
                ("macrophage_colony_stimulating_factor", "Macrophage Colony-stimulating Factor", ["biomedical", "chemicals_and_drugs"], "巨噬细胞集落刺激因子"),
                ("macrophage_inflammatory_protein", "Macrophage Inflammatory Proteins", ["biomedical", "chemicals_and_drugs"], "巨噬细胞炎性蛋白"),
            ]
        )

    def test_exact_expansion_batch_338_adds_macrophage_and_macular_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("macrophage_migration_inhibitory_factor", "Macrophage Migration Inhibitory Factor", ["biomedical", "chemicals_and_drugs", "immunology_and_microbiology", "life_sciences"], "巨噬细胞迁移抑制因子"),
                ("macrophag_alveolar", "Macrophages, Alveolar", ["anatomy", "biomedical"], "肺泡巨噬细胞"),
                ("macrophag_peritoneal", "Macrophages, Peritoneal", ["anatomy", "biomedical"], "腹腔巨噬细胞"),
                ("macrostomia", "Macrostomia", ["biomedical", "diseases"], "巨口症"),
                ("macula_lutea", "Macula Lutea", ["anatomy", "biomedical"], "黄斑"),
                ("macular_degeneration", "Macular Degeneration", ["biomedical", "diseases"], "黄斑变性"),
                ("macular_edema", "Macular Edema", ["biomedical", "diseases"], "黄斑水肿"),
            ]
        )

    def test_exact_expansion_batch_339_adds_macular_madagascar_and_magnesium_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("macular_pigment", "Macular Pigment", ["biomedical", "chemicals_and_drugs"], "黄斑色素"),
                ("madagascar", "Madagascar", ["biomedical", "geographicals"], "马达加斯加"),
                ("madin_darby_canine_kidney_cell", "Madin Darby Canine Kidney Cells", ["anatomy", "biomedical"], "Madin-Darby犬肾细胞"),
                ("maf_transcription_factor", "Maf Transcription Factors", ["biomedical", "chemicals_and_drugs"], "Maf转录因子"),
                ("mafenide", "Mafenide", ["biomedical", "chemicals_and_drugs"], "磺胺米隆"),
                ("magnesium", "Magnesium", ["materials_elements_and_compounds"], "镁元素"),
                ("magnesium_chloride", "Magnesium Chloride", ["biomedical", "chemicals_and_drugs"], "氯化镁"),
            ]
        )

    def test_exact_expansion_batch_340_adds_magnesium_and_magnetic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("magnesium_deficiency", "Magnesium Deficiency", ["biomedical", "diseases"], "镁缺乏"),
                ("magnesium_hydroxide", "Magnesium Hydroxide", ["biomedical", "chemicals_and_drugs"], "氢氧化镁"),
                ("magnesium_oxide", "Magnesium Oxide", ["biomedical", "chemicals_and_drugs"], "氧化镁"),
                ("magnesium_sulfate", "Magnesium Sulfate", ["biomedical", "chemicals_and_drugs"], "硫酸镁"),
                ("magnetic_anisotropy", "Magnetic Anisotropy", ["magnetics"], "磁各向异性"),
                ("magnetic_circuit", "Magnetic Circuits", ["circuits_and_systems"], "磁路"),
                ("magnetic_disk_storage", "Magnetic Disk Storage", ["computer_science"], "磁盘存储"),
            ]
        )

    def test_exact_expansion_batch_341_adds_magneto_effect_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("magneto_electrical_resistivity_imaging_technique", "Magneto Electrical Resistivity Imaging Technique", ["imaging"], "磁电阻率成像技术"),
                ("magneto_optical_property_and_application", "Magneto-optical Properties And Applications", ["engineering", "physical_sciences"], "磁光性质与应用"),
                ("magneto_rheological_damper", "Magneto-rheological Dampers", ["computer_science"], "磁流变阻尼器"),
                ("magnetoacoustic_effect", "Magnetoacoustic Effects", ["magnetics"], "磁声效应"),
                ("magnetocardiography", "Magnetocardiography", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "心磁图"),
                ("magnetoelasticity", "Magnetoelasticity", ["magnetics"], "磁弹性"),
                ("magnetoelectric_effect", "Magnetoelectric Effects", ["magnetics"], "磁电效应"),
            ]
        )

    def test_exact_expansion_batch_342_adds_magnetohydrodynamic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("magnetoelectronic", "Magnetoelectronics", ["magnetics"], "磁电子学"),
                ("magnetoencephalography", "Magnetoencephalography", ["magnetics"], "脑磁图"),
                ("magnetohydrodynamic_power_generation", "Magnetohydrodynamic Power Generation", ["power_engineering_and_energy"], "磁流体发电"),
                ("magnetohydrodynamic_techniqu", "Magnetohydrodynamic Techniques", ["physics"], "磁流体动力学技术"),
                ("magnetohydrodynamic", "Magnetohydrodynamics", ["science_general"], "磁流体动力学"),
                ("magnetomechanical_effect", "Magnetomechanical Effects", ["magnetics"], "磁机械效应"),
                ("magnetometer", "Magnetometers", ["instrumentation_and_measurement"], "磁强计"),
            ]
        )

    def test_exact_expansion_batch_343_adds_magnetooptic_and_magnetoresistance_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("magnetometry", "Magnetometry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "磁测量"),
                ("magnetooptic_devic", "Magnetooptic Devices", ["magnetics"], "磁光器件"),
                ("magnetooptic_effect", "Magnetooptic Effects", ["magnetics"], "磁光效应"),
                ("magnetooptic_recording", "Magnetooptic Recording", ["lasers_and_electrooptics"], "磁光记录"),
                ("magnetoresistance", "Magnetoresistance", ["magnetics"], "磁阻"),
                ("magnetoresistive_devic", "Magnetoresistive Devices", ["magnetics"], "磁阻器件"),
                ("magnetosom", "Magnetosomes", ["anatomy", "biomedical"], "磁小体"),
            ]
        )

    def test_exact_expansion_batch_344_adds_magnetostatic_and_magnolia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("magnetosphere", "Magnetosphere", ["change"], "磁层"),
                ("magnetospirillum", "Magnetospirillum", ["biomedical", "organisms"], "趋磁螺菌属"),
                ("magnetostatic_wav", "Magnetostatic Waves", ["science_general"], "静磁波"),
                ("magnetostriction", "Magnetostriction", ["magnetics"], "磁致伸缩"),
                ("magnetostrictive_devic", "Magnetostrictive Devices", ["magnetics"], "磁致伸缩器件"),
                ("magnetron", "Magnetrons", ["electron_devices"], "磁控管"),
                ("magnolia", "Magnolia", ["biomedical", "organisms"], "木兰属"),
            ]
        )

    def test_exact_expansion_batch_345_adds_magnolia_maintenance_and_major_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("magnoliaceae", "Magnoliaceae", ["biomedical", "organisms"], "木兰科"),
                ("magnonic", "Magnonics", ["magnetics"], "磁振子学"),
                ("maillard_reaction", "Maillard Reaction", ["biomedical", "phenomena_and_processes"], "美拉德反应"),
                ("computer_mainframe", "Computers, Mainframe", ["biomedical", "information_science"], "大型计算机"),
                ("maintenance_chemotherapy", "Maintenance Chemotherapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "维持化疗"),
                ("maize_streak_viru", "Maize Streak Virus", ["biomedical", "organisms"], "玉米条纹病毒"),
                ("major_depressive_disorder", "Major Depressive Disorder", ["biomedical", "psychiatry_and_psychology"], "重性抑郁障碍"),
                ("major_histocompatibility_complex", "Major Histocompatibility Complex", ["biomedical", "phenomena_and_processes"], "主要组织相容性复合体"),
            ]
        )

    def test_exact_expansion_batch_346_adds_malaria_and_malate_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("major_vault_protein", "Major Vault Protein", ["biomedical", "chemicals_and_drugs"], "主要穹窿蛋白"),
                ("malacoplakia", "Malacoplakia", ["biomedical", "diseases"], "软斑病"),
                ("malaria_research_and_control", "Malaria Research And Control", ["health_sciences", "medicine"], "疟疾研究与控制"),
                ("malaria_avian", "Malaria, Avian", ["biomedical", "diseases"], "鸟疟疾"),
                ("malaria_falciparum", "Malaria, Falciparum", ["biomedical", "diseases"], "恶性疟"),
                ("malaria_vivax", "Malaria, Vivax", ["biomedical", "diseases"], "间日疟"),
                ("malate_dehydrogenase", "Malate Dehydrogenase", ["biomedical", "chemicals_and_drugs"], "苹果酸脱氢酶"),
            ]
        )

    def test_exact_expansion_batch_347_adds_maleic_and_cortical_malformation_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("malate_synthase", "Malate Synthase", ["biomedical", "chemicals_and_drugs"], "苹果酸合酶"),
                ("malathion", "Malathion", ["biomedical", "chemicals_and_drugs"], "马拉硫磷"),
                ("male_urogenital_disease", "Male Urogenital Diseases", ["biomedical", "diseases"], "男性泌尿生殖系统疾病"),
                ("breast_neoplasm_male", "Breast Neoplasms, Male", ["biomedical", "diseases"], "男性乳腺肿瘤"),
                ("infertility_male", "Infertility, Male", ["biomedical", "diseases"], "男性不育"),
                ("nurse_male", "Nurses, Male", ["biomedical", "named_groups"], "男护士"),
                ("maleat", "Maleates", ["biomedical", "chemicals_and_drugs"], "马来酸盐"),
                ("maleic_anhydrid", "Maleic Anhydrides", ["biomedical", "chemicals_and_drugs"], "马来酸酐类"),
                ("maleimid", "Maleimides", ["biomedical", "chemicals_and_drugs"], "马来酰亚胺类"),
                ("malformation_of_cortical_development", "Malformations Of Cortical Development", ["biomedical", "diseases"], "皮质发育畸形"),
            ]
        )

    def test_exact_expansion_batch_348_adds_malicious_malignant_and_malocclusion_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("maliciou_attack", "Malicious Attack", ["computer_science"], "恶意攻击"),
                ("maliciou_code", "Malicious Code", ["computer_science"], "恶意代码"),
                ("malignant_atrophic_papulosi", "Malignant Atrophic Papulosis", ["biomedical", "diseases"], "恶性萎缩性丘疹病"),
                ("malignant_carcinoid_syndrome", "Malignant Carcinoid Syndrome", ["biomedical", "diseases"], "恶性类癌综合征"),
                ("malignant_hyperthermia", "Malignant Hyperthermia", ["biomedical", "diseases"], "恶性高热"),
                ("malocclusion", "Malocclusion", ["biomedical", "diseases"], "错颌"),
                ("malocclusion_angle_class_ii", "Malocclusion, Angle Class II", ["biomedical", "diseases"], "安氏II类错颌"),
            ]
        )

    def test_exact_expansion_batch_349_adds_malonate_malware_and_mammaglobin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("malondialdehyde", "Malondialdehyde", ["biomedical", "chemicals_and_drugs"], "丙二醛"),
                ("malonyl_coenzyme_a", "Malonyl Coenzyme A", ["biomedical", "chemicals_and_drugs"], "丙二酰辅酶A"),
                ("maltose", "Maltose", ["biomedical", "chemicals_and_drugs"], "麦芽糖"),
                ("maltose_binding_protein", "Maltose-binding Proteins", ["biomedical", "chemicals_and_drugs"], "麦芽糖结合蛋白"),
                ("anti_malware", "Anti-malware", ["computer_science"], "反恶意软件"),
                ("malware_analysi", "Malware Analysis", ["computer_science"], "恶意软件分析"),
                ("mammaglobin_a", "Mammaglobin A", ["biomedical", "chemicals_and_drugs"], "乳腺珠蛋白A"),
                ("mammaglobin_b", "Mammaglobin B", ["biomedical", "chemicals_and_drugs"], "乳腺珠蛋白B"),
            ]
        )

    def test_exact_expansion_batch_350_adds_mammary_and_mammography_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mammalian_orthoreoviru_3", "Mammalian Orthoreovirus 3", ["biomedical", "organisms"], "哺乳动物正呼肠孤病毒3型"),
                ("mammaplasty", "Mammaplasty", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "乳房成形术"),
                ("mammary_analogue_secretory_carcinoma", "Mammary Analogue Secretory Carcinoma", ["biomedical", "diseases"], "乳腺样分泌性癌"),
                ("mammary_gland_animal", "Mammary Glands, Animal", ["anatomy", "biomedical"], "动物乳腺"),
                ("mammary_neoplasm_experimental", "Mammary Neoplasms, Experimental", ["biomedical", "diseases"], "实验性乳腺肿瘤"),
                ("mammary_tumor_viru_mouse", "Mammary Tumor Virus, Mouse", ["biomedical", "organisms"], "小鼠乳腺肿瘤病毒"),
                ("mammillary_body", "Mammillary Bodies", ["anatomy", "biomedical"], "乳头体"),
                ("digital_mammogram", "Digital Mammograms", ["computer_science"], "数字乳腺X线片"),
            ]
        )

    def test_exact_expansion_batch_351_adds_managed_care_and_management_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("man_in_the_middle_attack", "Man-in-the-middle Attack", ["computer_science"], "中间人攻击"),
                ("managed_care_program", "Managed Care Programs", ["biomedical", "health_care"], "管理式医疗项目"),
                ("managed_competition", "Managed Competition", ["biomedical", "health_care"], "管理式竞争"),
                ("management_and_marketing_education", "Management And Marketing Education", ["business_management_and_accounting", "social_sciences"], "管理与营销教育"),
                ("management_audit", "Management Audit", ["biomedical", "health_care"], "管理审计"),
                ("management_information_base", "Management Information Base", ["computers_and_information_processing"], "管理信息库"),
                ("management_of_metastatic_bone_disease", "Management Of Metastatic Bone Disease", ["health_sciences", "medicine"], "转移性骨病管理"),
            ]
        )

    def test_exact_expansion_batch_352_adds_mandatory_and_mandibular_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mandatory_reporting", "Mandatory Reporting", ["anthropology_education_sociology_and_social_phenomena", "biomedical"], "强制报告"),
                ("mandatory_testing", "Mandatory Testing", ["anthropology_education_sociology_and_social_phenomena", "biomedical"], "强制检测"),
                ("mandatory_vaccination", "Mandatory Vaccination", ["anthropology_education_sociology_and_social_phenomena", "biomedical"], "强制接种"),
                ("mandelic_acid", "Mandelic Acids", ["biomedical", "chemicals_and_drugs"], "扁桃酸类"),
                ("mandibular_canal", "Mandibular Canal", ["anatomy", "biomedical"], "下颌管"),
                ("mandibular_fractur", "Mandibular Fractures", ["biomedical", "diseases"], "下颌骨骨折"),
                ("mandibular_nerve", "Mandibular Nerve", ["anatomy", "biomedical"], "下颌神经"),
            ]
        )

    def test_exact_expansion_batch_353_adds_manet_manganese_and_manifold_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("manet", "Manet", ["computer_science"], "移动自组织网络"),
                ("manet_routing", "Manet Routing", ["computer_science"], "移动自组织网络路由"),
                ("maneuvering_target_tracking", "Maneuvering Target Tracking", ["computer_science"], "机动目标跟踪"),
                ("manganese_alloy", "Manganese Alloys", ["materials_elements_and_compounds"], "锰合金"),
                ("manganese_compound", "Manganese Compounds", ["biomedical", "chemicals_and_drugs"], "锰化合物"),
                ("manganese_poisoning", "Manganese Poisoning", ["biomedical", "diseases"], "锰中毒"),
                ("manifold_learning", "Manifold Learning", ["computer_science", "mathematics"], "流形学习"),
            ]
        )

    def test_exact_expansion_batch_354_adds_manipulation_and_mannose_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("manipulation_chiropractic", "Manipulation, Chiropractic", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "脊椎按摩手法"),
                ("manipulation_orthopedic", "Manipulation, Orthopedic", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "骨科手法"),
                ("manipulation_spinal", "Manipulation, Spinal", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "脊柱手法"),
                ("manipulator_system", "Manipulator Systems", ["computer_science"], "机械臂系统"),
                ("mannitol", "Mannitol", ["biomedical", "chemicals_and_drugs"], "甘露醇"),
                ("mannitol_dehydrogenase", "Mannitol Dehydrogenases", ["biomedical", "chemicals_and_drugs"], "甘露醇脱氢酶"),
                ("alpha_mannosidase", "Alpha-mannosidase", ["biomedical", "chemicals_and_drugs"], "α-甘露糖苷酶"),
                ("beta_mannosidase", "Beta-mannosidase", ["biomedical", "chemicals_and_drugs"], "β-甘露糖苷酶"),
                ("mannose_receptor", "Mannose Receptor", ["biomedical", "chemicals_and_drugs"], "甘露糖受体"),
            ]
        )

    def test_exact_expansion_batch_355_adds_mannose_manual_and_manufacturing_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mannose_6_phosphate_isomerase", "Mannose-6-phosphate Isomerase", ["biomedical", "chemicals_and_drugs"], "甘露糖-6-磷酸异构酶"),
                ("mannose_binding_lectin", "Mannose-binding Lectins", ["biomedical", "chemicals_and_drugs"], "甘露糖结合凝集素"),
                ("mannosidase_deficiency_disease", "Mannosidase Deficiency Diseases", ["biomedical", "diseases"], "甘露糖苷酶缺乏病"),
                ("manual_lymphatic_drainage", "Manual Lymphatic Drainage", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "手法淋巴引流"),
                ("manual_segmentation", "Manual Segmentation", ["computer_science"], "手动分割"),
                ("manufacturing_automation", "Manufacturing Automation", ["industrial_electronics"], "制造自动化"),
                ("manufacturing_resource_planning", "Manufacturing Resource Planning", ["computer_science"], "制造资源计划"),
            ]
        )

    def test_exact_expansion_batch_356_adds_many_core_and_map_kinase_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("many_body_techniqu", "Many-body Techniques", ["physics"], "多体技术"),
                ("many_core_architecture", "Many-core Architecture", ["computer_science"], "众核架构"),
                ("many_core_processor", "Many-core Processors", ["computer_science"], "众核处理器"),
                ("many_valued_logic", "Many-valued Logic", ["computer_science"], "多值逻辑"),
                ("map_kinase_kinase_1", "MAP Kinase Kinase 1", ["biomedical", "chemicals_and_drugs"], "MAP激酶激酶1"),
                ("map_kinase_kinase_kinase_1", "MAP Kinase Kinase Kinase 1", ["biomedical", "chemicals_and_drugs"], "MAP激酶激酶激酶1"),
                ("map_kinase_signaling_system", "MAP Kinase Signaling System", ["biomedical", "phenomena_and_processes"], "MAP激酶信号系统"),
            ]
        )

    def test_exact_expansion_batch_357_adds_mapreduce_and_marine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("map_matching", "Map Matching", ["computer_science"], "地图匹配"),
                ("map_matching_algorithm", "Map-matching Algorithm", ["computer_science"], "地图匹配算法"),
                ("map_reduce", "Map-reduce", ["computer_science"], "映射归约"),
                ("maple_syrup_urine_disease", "Maple Syrup Urine Disease", ["biomedical", "diseases"], "枫糖尿病"),
                ("maraviroc", "Maraviroc", ["biomedical", "chemicals_and_drugs"], "马拉韦罗"),
                ("marburg_viru_disease", "Marburg Virus Disease", ["biomedical", "diseases"], "马尔堡病毒病"),
                ("marek_disease", "Marek Disease", ["biomedical", "diseases"], "马立克病"),
            ]
        )

    def test_exact_expansion_batch_358_adds_marine_and_maritime_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("marfan_syndrome", "Marfan Syndrome", ["biomedical", "diseases"], "马凡综合征"),
                ("marijuana_abuse", "Marijuana Abuse", ["biomedical", "diseases"], "大麻滥用"),
                ("marine_biology", "Marine Biology", ["biomedical", "disciplines_and_occupations"], "海洋生物学"),
                ("marine_engineering", "Marine Engineering", ["engineering_general"], "海洋工程"),
                ("marine_navigation", "Marine Navigation", ["intelligent_transportation_systems"], "海上导航"),
                ("marine_pollution", "Marine Pollution", ["oceanic_engineering_and_marine_technology"], "海洋污染"),
                ("maritime_communication", "Maritime Communications", ["communications_technology"], "海事通信"),
            ]
        )

    def test_exact_expansion_batch_359_adds_market_and_markov_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("market_dynamic_and_volatility", "Market Dynamics And Volatility", ["economics_econometrics_and_finance", "social_sciences"], "市场动态与波动性"),
                ("market_research", "Market Research", ["engineering_management"], "市场研究"),
                ("marketing_management", "Marketing Management", ["engineering_management"], "营销管理"),
                ("consumer_behavior_and_marketing_influence", "Consumer Behavior And Marketing Influence", ["business_management_and_accounting", "social_sciences"], "消费者行为与营销影响"),
                ("digital_marketing_and_social_media", "Digital Marketing And Social Media", ["social_sciences"], "数字营销与社交媒体"),
                ("social_marketing", "Social Marketing", ["biomedical", "technology_industry_and_agriculture"], "社会营销"),
                ("markov_chain", "Markov Chain", ["computer_science"], "马尔可夫链"),
                ("markov_chain_monte_carlo", "Markov Chain Monte Carlo", ["computer_science"], "马尔可夫链蒙特卡罗"),
                ("markov_logic_network", "Markov Logic Networks", ["computer_science"], "马尔可夫逻辑网络"),
                ("markov_random_field", "Markov Random Fields", ["computer_science", "mathematics"], "马尔可夫随机场"),
            ]
        )

    def test_exact_expansion_batch_360_adds_mass_and_mast_cell_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("masked_hypertension", "Masked Hypertension", ["biomedical", "diseases"], "隐匿性高血压"),
                ("masked_language_modeling", "Masked Language Modeling", ["computer_science"], "掩码语言建模"),
                ("mass_casualty_incident", "Mass Casualty Incidents", ["anthropology_education_sociology_and_social_phenomena", "biomedical"], "大规模伤亡事件"),
                ("mass_drug_administration", "Mass Drug Administration", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "群体给药"),
                ("mass_spectrometry", "Mass Spectrometry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "质谱法"),
                ("mass_spectrometry_techniqu_and_application", "Mass Spectrometry Techniques And Applications", ["chemistry", "physical_sciences"], "质谱技术与应用"),
                ("mast_cell_activation_syndrome", "Mast Cell Activation Syndrome", ["biomedical", "diseases"], "肥大细胞活化综合征"),
                ("mast_cell_stabilizer", "Mast Cell Stabilizers", ["biomedical", "chemicals_and_drugs"], "肥大细胞稳定剂"),
            ]
        )

    def test_exact_expansion_batch_361_adds_mast_cell_and_mastectomy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mast_cell", "Mast Cells", ["anatomy", "biomedical"], "肥大细胞"),
                ("mast_cell_activation_disorder", "Mast Cell Activation Disorders", ["biomedical", "diseases"], "肥大细胞活化障碍"),
                ("mast_cell_sarcoma", "Mast-cell Sarcoma", ["biomedical", "diseases"], "肥大细胞肉瘤"),
                ("mastectomy_modified_radical", "Mastectomy, Modified Radical", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "改良根治性乳房切除术"),
                ("mastectomy_segmental", "Mastectomy, Segmental", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "节段性乳房切除术"),
                ("mastication", "Mastication", ["biomedical", "phenomena_and_processes"], "咀嚼"),
                ("masticatory_muscl", "Masticatory Muscles", ["anatomy", "biomedical"], "咀嚼肌"),
                ("mastocytosi_systemic", "Mastocytosis, Systemic", ["biomedical", "diseases"], "系统性肥大细胞增多症"),
                ("mastoiditi", "Mastoiditis", ["biomedical", "diseases"], "乳突炎"),
            ]
        )

    def test_exact_expansion_batch_362_adds_matching_and_material_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("master_slave_system", "Master-slave Systems", ["computer_science"], "主从系统"),
                ("match_score", "Match Score", ["computer_science"], "匹配分数"),
                ("matched_filter", "Matched Filters", ["signal_processing"], "匹配滤波器"),
                ("matched_pair_analysi", "Matched-pair Analysis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "配对分析"),
                ("matching_algorithm", "Matching Algorithm", ["computer_science"], "匹配算法"),
                ("matching_pursuit_algorithm", "Matching Pursuit Algorithms", ["computer_science", "mathematics"], "匹配追踪算法"),
                ("material_property", "Material Properties", ["materials_elements_and_compounds"], "材料性能"),
                ("material_removal_rate", "Material Removal Rate", ["computer_science"], "材料去除率"),
                ("material_safety_data_sheet", "Material Safety Data Sheets", ["biomedical", "health_care"], "化学品安全技术说明书"),
                ("materialized_view", "Materialized View", ["computer_science"], "物化视图"),
            ]
        )

    def test_exact_expansion_batch_363_adds_materials_management_and_testing_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("material_handling", "Materials Handling", ["materials_elements_and_compounds"], "物料搬运"),
                ("material_handling_equipment", "Materials Handling Equipment", ["materials_elements_and_compounds"], "物料搬运设备"),
                ("material_management_hospital", "Materials Management, Hospital", ["biomedical", "health_care"], "医院物资管理"),
                ("material_preparation", "Materials Preparation", ["materials_elements_and_compounds"], "材料制备"),
                ("material_processing", "Materials Processing", ["industry_applications"], "材料加工"),
                ("material_reliability", "Materials Reliability", ["reliability"], "材料可靠性"),
                ("material_requirement_planning", "Materials Requirements Planning", ["engineering_general"], "物料需求计划"),
                ("material_science", "Materials Science", ["physics_condensed_matter"], "材料科学"),
                ("material_science_and_technology", "Materials Science And Technology", ["materials_elements_and_compounds"], "材料科学与技术"),
                ("material_testing", "Materials Testing", ["materials_elements_and_compounds"], "材料测试"),
            ]
        )

    def test_exact_expansion_batch_364_adds_maternal_health_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("maternal_age", "Maternal Age", ["biomedical", "phenomena_and_processes"], "母亲年龄"),
                ("maternal_behavior", "Maternal Behavior", ["biomedical", "psychiatry_and_psychology"], "母性行为"),
                ("maternal_death", "Maternal Death", ["biomedical", "diseases"], "孕产妇死亡"),
                ("maternal_health", "Maternal Health", ["biomedical", "health_care"], "孕产妇健康"),
                ("maternal_health_servic", "Maternal Health Services", ["biomedical", "health_care"], "孕产妇保健服务"),
                ("maternal_inheritance", "Maternal Inheritance", ["biomedical", "phenomena_and_processes"], "母系遗传"),
                ("maternal_mortality", "Maternal Mortality", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "孕产妇死亡率"),
                ("maternal_child_health_servic", "Maternal-child Health Services", ["biomedical", "health_care"], "妇幼保健服务"),
                ("maternal_fetal_exchange", "Maternal-fetal Exchange", ["biomedical", "phenomena_and_processes"], "母胎交换"),
            ]
        )

    def test_exact_expansion_batch_365_adds_mathematical_analysis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mathematical_analysi", "Mathematical Analysis", ["mathematics"], "数学分析"),
                ("mathematical_and_computational_method", "Mathematical And Computational Methods", ["mathematics", "physical_sciences"], "数学与计算方法"),
                ("mathematical_control_system_and_analysi", "Mathematical Control Systems And Analysis", ["computer_science", "physical_sciences"], "数学控制系统与分析"),
                ("mathematical_finance", "Mathematical Finance", ["quantitative_finance"], "金融数学"),
                ("mathematical_inequality_and_application", "Mathematical Inequalities And Applications", ["mathematics", "physical_sciences"], "数学不等式与应用"),
                ("mathematical_model", "Mathematical Models", ["systems_engineering_and_theory"], "数学模型"),
                ("mathematical_physic", "Mathematical Physics", ["mathematical_physics"], "数学物理"),
                ("mathematical_programming", "Mathematical Programming", ["mathematics"], "数学规划"),
                ("mathematic_education_and_teaching_techniqu", "Mathematics Education And Teaching Techniques", ["social_sciences"], "数学教育与教学技术"),
            ]
        )

    def test_exact_expansion_batch_366_adds_matlab_and_matrix_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("matlab", "MATLAB", ["computers_and_information_processing"], "MATLAB软件"),
                ("matlab_environment", "Matlab Environment", ["computer_science"], "MATLAB环境"),
                ("matlab_simulation", "Matlab Simulation", ["computer_science"], "MATLAB仿真"),
                ("matlab_simulink", "Matlab-simulink", ["computer_science"], "MATLAB/Simulink软件"),
                ("matrix_algebra", "Matrix Algebra", ["computer_science"], "矩阵代数"),
                ("matrix_attachment_region", "Matrix Attachment Regions", ["biomedical", "phenomena_and_processes"], "基质附着区"),
                ("matrix_converter", "Matrix Converters", ["power_electronics"], "矩阵变换器"),
                ("matrix_factorization", "Matrix Factorization", ["computer_science"], "矩阵分解"),
                ("matrix_gla_protein", "Matrix Gla Protein", ["biomedical", "chemicals_and_drugs"], "基质Gla蛋白"),
                ("matrix_theory", "Matrix Theory", ["computer_science"], "矩阵理论"),
            ]
        )

    def test_exact_expansion_batch_367_adds_matrix_metalloproteinase_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("matrix_metalloproteinase_1", "Matrix Metalloproteinase 1", ["biomedical", "chemicals_and_drugs"], "基质金属蛋白酶1"),
                ("matrix_metalloproteinase_2", "Matrix Metalloproteinase 2", ["biomedical", "chemicals_and_drugs"], "基质金属蛋白酶2"),
                ("matrix_metalloproteinase_3", "Matrix Metalloproteinase 3", ["biomedical", "chemicals_and_drugs"], "基质金属蛋白酶3"),
                ("matrix_metalloproteinase_9", "Matrix Metalloproteinase 9", ["biomedical", "chemicals_and_drugs"], "基质金属蛋白酶9"),
                ("matrix_metalloproteinase_13", "Matrix Metalloproteinase 13", ["biomedical", "chemicals_and_drugs"], "基质金属蛋白酶13"),
                ("matrix_metalloproteinase_inhibitor", "Matrix Metalloproteinase Inhibitors", ["biomedical", "chemicals_and_drugs"], "基质金属蛋白酶抑制剂"),
                ("matrix_metalloproteinase_membrane_associated", "Matrix Metalloproteinases, Membrane-associated", ["biomedical", "chemicals_and_drugs"], "膜相关基质金属蛋白酶"),
                ("matrix_metalloproteinase_secreted", "Matrix Metalloproteinases, Secreted", ["biomedical", "chemicals_and_drugs"], "分泌型基质金属蛋白酶"),
            ]
        )

    def test_exact_expansion_batch_368_adds_maxillary_and_maximal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("maxillary_artery", "Maxillary Artery", ["anatomy", "biomedical"], "上颌动脉"),
                ("maxillary_fractur", "Maxillary Fractures", ["biomedical", "diseases"], "上颌骨骨折"),
                ("maxillary_nerve", "Maxillary Nerve", ["anatomy", "biomedical"], "上颌神经"),
                ("maxillary_sinu", "Maxillary Sinus", ["anatomy", "biomedical"], "上颌窦"),
                ("maxillary_sinusiti", "Maxillary Sinusitis", ["biomedical", "diseases"], "上颌窦炎"),
                ("maxillofacial_injury", "Maxillofacial Injuries", ["biomedical", "diseases"], "颌面损伤"),
                ("maxillofacial_prosthesi", "Maxillofacial Prosthesis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "颌面假体"),
                ("maximal_frequent_itemset", "Maximal Frequent Itemsets", ["computer_science"], "最大频繁项集"),
                ("maximal_ratio_combining", "Maximal Ratio Combining", ["computer_science"], "最大比合并"),
                ("maximal_voluntary_ventilation", "Maximal Voluntary Ventilation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "最大自主通气量"),
            ]
        )

    def test_exact_expansion_batch_369_adds_maximum_likelihood_and_power_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("maximum_a_posteriori_estimation", "Maximum A Posteriori Estimation", ["mathematics"], "最大后验估计"),
                ("maximum_entropy_model", "Maximum Entropy Model", ["computer_science"], "最大熵模型"),
                ("maximum_likelihood_decoding", "Maximum Likelihood Decoding", ["information_theory"], "最大似然译码"),
                ("maximum_likelihood_detection", "Maximum Likelihood Detection", ["computer_science", "mathematics"], "最大似然检测"),
                ("maximum_likelihood_estimation", "Maximum Likelihood Estimation", ["computer_science", "mathematics"], "最大似然估计"),
                ("maximum_likelihood_method", "Maximum Likelihood Method", ["computer_science"], "最大似然法"),
                ("maximum_power_point_tracking", "Maximum Power Point Tracking", ["computer_science"], "最大功率点跟踪"),
                ("maximum_tolerated_dose", "Maximum Tolerated Dose", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "最大耐受剂量"),
                ("maxwell_equation", "Maxwell Equations", ["computer_science", "mathematics"], "麦克斯韦方程"),
                ("maxwell_boltzmann_distribution", "Maxwell-boltzmann Distribution", ["mathematics"], "麦克斯韦-玻尔兹曼分布"),
            ]
        )

    def test_exact_expansion_batch_370_adds_mean_and_measurement_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mean_absolute_error", "Mean Absolute Error", ["computer_science"], "平均绝对误差"),
                ("mean_diffusivity", "Mean Diffusivity", ["computer_science"], "平均弥散率"),
                ("mean_field_theory", "Mean Field Theory", ["mathematics"], "平均场理论"),
                ("mean_filter", "Mean Filter", ["computer_science"], "均值滤波器"),
                ("mean_opinion_score", "Mean Opinion Score", ["computer_science"], "平均意见得分"),
                ("mean_platelet_volume", "Mean Platelet Volume", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "平均血小板体积"),
                ("mean_shift_tracking", "Mean Shift Tracking", ["computer_science"], "均值漂移跟踪"),
                ("mean_shift_segmentation", "Mean-shift Segmentation", ["computer_science"], "均值漂移分割"),
                ("measl_mump_rubella_vaccine", "Measles-mumps-rubella Vaccine", ["biomedical", "chemicals_and_drugs"], "麻疹-腮腺炎-风疹疫苗"),
                ("measurement_uncertainty", "Measurement Uncertainty", ["instrumentation_and_measurement"], "测量不确定度"),
            ]
        )

    def test_exact_expansion_batch_371_adds_mechanical_engineering_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mechanical_behavior_of_composit", "Mechanical Behavior Of Composites", ["engineering", "physical_sciences"], "复合材料力学行为"),
                ("mechanical_circulatory_support_devic", "Mechanical Circulatory Support Devices", ["engineering", "physical_sciences"], "机械循环辅助装置"),
                ("mechanical_design", "Mechanical Design", ["computer_science"], "机械设计"),
                ("mechanical_energy", "Mechanical Energy", ["engineering_general"], "机械能"),
                ("mechanical_engineering", "Mechanical Engineering", ["engineering_general"], "机械工程"),
                ("mechanical_failure_analysi_and_simulation", "Mechanical Failure Analysis And Simulation", ["engineering", "physical_sciences"], "机械失效分析与仿真"),
                ("mechanical_power_transmission", "Mechanical Power Transmission", ["engineering_general"], "机械传动"),
                ("mechanical_sensor", "Mechanical Sensors", ["sensors"], "机械传感器"),
                ("mechanical_stress_and_fatigue_analysi", "Mechanical Stress And Fatigue Analysis", ["engineering", "physical_sciences"], "机械应力与疲劳分析"),
                ("mechanical_vibration", "Mechanical Vibrations", ["computer_science"], "机械振动"),
            ]
        )

    def test_exact_expansion_batch_372_adds_mechanics_mechatronics_and_media_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mechanic_and_biomechanic_study", "Mechanics And Biomechanics Studies", ["engineering", "physical_sciences"], "力学与生物力学研究"),
                ("mechanism_design", "Mechanism Design", ["computer_science"], "机制设计"),
                ("mechanistic_target_of_rapamycin_complex_1", "Mechanistic Target Of Rapamycin Complex 1", ["biomedical", "chemicals_and_drugs"], "雷帕霉素机制靶蛋白复合物1"),
                ("mechanistic_target_of_rapamycin_complex_2", "Mechanistic Target Of Rapamycin Complex 2", ["biomedical", "chemicals_and_drugs"], "雷帕霉素机制靶蛋白复合物2"),
                ("mechanobiology", "Mechanobiology", ["engineering_in_medicine_and_biology"], "机械生物学"),
                ("mechanoreceptor", "Mechanoreceptors", ["anatomy", "biomedical"], "机械感受器"),
                ("mechanotransduction_cellular", "Mechanotransduction, Cellular", ["biomedical", "phenomena_and_processes"], "细胞机械转导"),
                ("mechatronic_system", "Mechatronic Systems", ["computer_science"], "机电一体化系统"),
                ("media_access_control", "Media Access Control", ["computer_science"], "媒体访问控制"),
                ("media_independent_handover", "Media Independent Handover", ["computer_science"], "媒体无关切换"),
            ]
        )

    def test_exact_expansion_batch_373_adds_medial_median_and_mediastinal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("medial_axis", "Medial Axis", ["computer_science"], "中轴"),
                ("medial_collateral_ligament_knee", "Medial Collateral Ligament, Knee", ["anatomy", "biomedical"], "膝内侧副韧带"),
                ("medial_forebrain_bundle", "Medial Forebrain Bundle", ["anatomy", "biomedical"], "内侧前脑束"),
                ("median_arcuate_ligament_syndrome", "Median Arcuate Ligament Syndrome", ["biomedical", "diseases"], "中弓韧带综合征"),
                ("median_filter", "Median Filter", ["computer_science"], "中值滤波器"),
                ("median_nerve", "Median Nerve", ["anatomy", "biomedical"], "正中神经"),
                ("mediastinal_emphysema", "Mediastinal Emphysema", ["biomedical", "diseases"], "纵隔气肿"),
                ("mediastinal_neoplasm", "Mediastinal Neoplasms", ["biomedical", "diseases"], "纵隔肿瘤"),
                ("mediation_analysi", "Mediation Analysis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "中介分析"),
                ("mediator_complex_subunit_1", "Mediator Complex Subunit 1", ["biomedical", "chemicals_and_drugs"], "中介复合体亚基1"),
            ]
        )

    def test_exact_expansion_batch_374_adds_medical_device_and_database_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("medicaid", "Medicaid", ["biomedical", "health_care"], "医疗补助"),
                ("medical_and_biological_scienc", "Medical And Biological Sciences", ["health_sciences", "medicine"], "医学与生物科学"),
                ("medical_assistance", "Medical Assistance", ["biomedical", "health_care"], "医疗援助"),
                ("medical_audit", "Medical Audit", ["biomedical", "health_care"], "医疗审计"),
                ("medical_control_system", "Medical Control Systems", ["control_systems"], "医疗控制系统"),
                ("medical_countermeasur", "Medical Countermeasures", ["biomedical", "health_care"], "医疗对策"),
                ("medical_database", "Medical Database", ["computer_science"], "医疗数据库"),
                ("medical_device_sterilization_and_disinfection", "Medical Device Sterilization And Disinfection", ["immunology_and_microbiology", "life_sciences"], "医疗器械灭菌与消毒"),
                ("medical_diagnostic_imaging", "Medical Diagnostic Imaging", ["imaging"], "医学诊断成像"),
                ("medical_expert_system", "Medical Expert Systems", ["engineering_in_medicine_and_biology"], "医疗专家系统"),
            ]
        )

    def test_exact_expansion_batch_375_adds_medical_imaging_and_record_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("medical_history_taking", "Medical History Taking", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "病史采集"),
                ("medical_identity_theft", "Medical Identity Theft", ["anthropology_education_sociology_and_social_phenomena", "biomedical"], "医疗身份盗窃"),
                ("medical_image_registration", "Medical Image Registration", ["computer_science"], "医学图像配准"),
                ("medical_image_segmentation_techniqu", "Medical Image Segmentation Techniques", ["computer_science", "physical_sciences"], "医学图像分割技术"),
                ("medical_informatic", "Medical Informatics", ["biomedical", "information_science"], "医学信息学"),
                ("medical_information_system", "Medical Information Systems", ["engineering_in_medicine_and_biology"], "医疗信息系统"),
                ("medical_laboratory_science", "Medical Laboratory Science", ["biomedical", "disciplines_and_occupations"], "医学检验学"),
                ("medical_order_entry_system", "Medical Order Entry Systems", ["biomedical", "information_science"], "医嘱录入系统"),
                ("medical_record_linkage", "Medical Record Linkage", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "医疗记录链接"),
                ("medical_record_system_computerized", "Medical Records Systems, Computerized", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "计算机化病历系统"),
            ]
        )

    def test_exact_expansion_batch_376_adds_medical_staff_and_medication_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("medical_saving_account", "Medical Savings Accounts", ["biomedical", "health_care"], "医疗储蓄账户"),
                ("medical_staff", "Medical Staff", ["biomedical", "named_groups"], "医务人员"),
                ("medical_subject_heading", "Medical Subject Headings", ["biomedical", "information_science"], "医学主题词"),
                ("medical_tourism", "Medical Tourism", ["biomedical", "health_care"], "医疗旅游"),
                ("medical_waste_disposal", "Medical Waste Disposal", ["biomedical", "chemicals_and_drugs"], "医疗废物处置"),
                ("medically_underserved_area", "Medically Underserved Area", ["biomedical", "health_care"], "医疗服务不足地区"),
                ("medically_uninsured", "Medically Uninsured", ["biomedical", "named_groups"], "无医疗保险者"),
                ("medication_adherence", "Medication Adherence", ["biomedical", "psychiatry_and_psychology"], "用药依从性"),
                ("medication_reconciliation", "Medication Reconciliation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "用药核对"),
                ("medication_therapy_management", "Medication Therapy Management", ["biomedical", "health_care"], "药物治疗管理"),
            ]
        )

    def test_exact_expansion_batch_377_adds_medicinal_plant_and_medicine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("medicinal_plant_research", "Medicinal Plant Research", ["agricultural_and_biological_sciences", "life_sciences"], "药用植物研究"),
                ("medicinal_plant_and_bioactive_compound", "Medicinal Plants And Bioactive Compounds", ["biochemistry_genetics_and_molecular_biology", "life_sciences"], "药用植物与生物活性化合物"),
                ("medicine", "Medicine", ["biomedical", "disciplines_and_occupations"], "医学"),
                ("medicine_chest", "Medicine Chests", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "药箱"),
                ("medicine_african_traditional", "Medicine, African Traditional", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "非洲传统医学"),
                ("medicine_chinese_traditional", "Medicine, Chinese Traditional", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "中医"),
                ("medicine_east_asian_traditional", "Medicine, East Asian Traditional", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "东亚传统医学"),
                ("medicine_kampo", "Medicine, Kampo", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "汉方医学"),
                ("medicine_tibetan_traditional", "Medicine, Tibetan Traditional", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "藏医"),
                ("medicine_traditional", "Medicine, Traditional", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "传统医学"),
            ]
        )

    def test_exact_expansion_batch_378_adds_meiotic_and_melanin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("meibomian_gland_dysfunction", "Meibomian Gland Dysfunction", ["biomedical", "diseases"], "睑板腺功能障碍"),
                ("meibomian_gland", "Meibomian Glands", ["anatomy", "biomedical"], "睑板腺"),
                ("meige_syndrome", "Meige Syndrome", ["biomedical", "diseases"], "Meige综合征"),
                ("meiosi", "Meiosis", ["biomedical", "phenomena_and_processes"], "减数分裂"),
                ("meiotic_recombination_protein_spo11", "Meiotic Recombination Protein Spo11", ["biomedical", "chemicals_and_drugs"], "减数分裂重组蛋白Spo11"),
                ("mel_frequency_cepstral_coefficient", "Mel-frequency Cepstral Coefficients", ["computer_science"], "梅尔频率倒谱系数"),
                ("melanocyte_stimulating_hormon", "Melanocyte-stimulating Hormones", ["biomedical", "chemicals_and_drugs"], "促黑素"),
                ("melanoma_specific_antigen", "Melanoma-specific Antigens", ["biomedical", "chemicals_and_drugs"], "黑色素瘤特异性抗原"),
                ("melatonin", "Melatonin", ["biomedical", "chemicals_and_drugs"], "褪黑素"),
                ("melioidosi", "Melioidosis", ["biomedical", "diseases"], "类鼻疽"),
            ]
        )

    def test_exact_expansion_batch_379_adds_membrane_and_memetic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("memantine", "Memantine", ["biomedical", "chemicals_and_drugs"], "美金刚"),
                ("membership_function", "Membership Function", ["computer_science"], "隶属函数"),
                ("membrane_cofactor_protein", "Membrane Cofactor Protein", ["biomedical", "chemicals_and_drugs"], "膜辅因子蛋白"),
                ("membrane_fluidity", "Membrane Fluidity", ["biomedical", "phenomena_and_processes"], "膜流动性"),
                ("membrane_fusion", "Membrane Fusion", ["biomedical", "phenomena_and_processes"], "膜融合"),
                ("membrane_potential_mitochondrial", "Membrane Potential, Mitochondrial", ["biomedical", "phenomena_and_processes"], "线粒体膜电位"),
                ("membrane_transport_protein", "Membrane Transport Proteins", ["biomedical", "chemicals_and_drugs"], "膜转运蛋白"),
                ("membrane_based_ion_separation_techniqu", "Membrane-based Ion Separation Techniques", ["engineering", "physical_sciences"], "膜基离子分离技术"),
                ("membran_artificial", "Membranes, Artificial", ["biomedical", "chemicals_and_drugs"], "人工膜"),
                ("memetic_algorithm", "Memetic Algorithm", ["computer_science"], "模因算法"),
            ]
        )

    def test_exact_expansion_batch_380_adds_memory_and_mems_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("memory_access", "Memory Access", ["computer_science"], "内存访问"),
                ("memory_allocation", "Memory Allocation", ["computer_science"], "内存分配"),
                ("memory_and_learning_test", "Memory And Learning Tests", ["biomedical", "psychiatry_and_psychology"], "记忆与学习测试"),
                ("memory_architecture", "Memory Architecture", ["computer_science"], "存储架构"),
                ("memory_consolidation", "Memory Consolidation", ["biomedical", "psychiatry_and_psychology"], "记忆巩固"),
                ("memory_controller", "Memory Controller", ["computer_science"], "内存控制器"),
                ("memory_disorder", "Memory Disorders", ["biomedical", "diseases"], "记忆障碍"),
                ("memory_hierarchy", "Memory Hierarchy", ["computer_science"], "存储层次结构"),
                ("memory_management", "Memory Management", ["computer_science"], "内存管理"),
                ("memory_episodic", "Memory, Episodic", ["biomedical", "psychiatry_and_psychology"], "情景记忆"),
                ("memristor", "Memristors", ["components_packaging_and_manufacturing_technology"], "忆阻器"),
                ("mems_gyroscope", "Mems Gyroscope", ["computer_science"], "MEMS陀螺仪"),
            ]
        )

    def test_exact_expansion_batch_381_adds_men_and_meningeal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("men", "Men", ["biomedical", "named_groups"], "男性"),
                ("men_s_health", "Men's Health", ["biomedical", "health_care"], "男性健康"),
                ("menarche", "Menarche", ["biomedical", "phenomena_and_processes"], "初潮"),
                ("mendelian_randomization_analysi", "Mendelian Randomization Analysis", ["biomedical"], "孟德尔随机化分析"),
                ("meniere_disease", "Meniere Disease", ["biomedical", "diseases"], "梅尼埃病"),
                ("meningeal_artery", "Meningeal Arteries", ["anatomy", "biomedical"], "脑膜动脉"),
                ("meningeal_neoplasm", "Meningeal Neoplasms", ["biomedical", "diseases"], "脑膜肿瘤"),
            ]
        )

    def test_exact_expansion_batch_382_adds_meningitis_and_menstrual_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mening", "Meninges", ["anatomy", "biomedical"], "脑膜"),
                ("meningism", "Meningism", ["biomedical", "diseases"], "脑膜刺激征"),
                ("meningococcal_infection", "Meningococcal Infections", ["biomedical", "diseases"], "脑膜炎球菌感染"),
                ("meningiti_meningococcal", "Meningococcal Meningitis", ["biomedical", "diseases"], "脑膜炎球菌性脑膜炎"),
                ("meningoencephaliti", "Meningoencephalitis", ["biomedical", "diseases"], "脑膜脑炎"),
                ("menorrhagia", "Menorrhagia", ["biomedical", "diseases"], "月经过多"),
                ("menstrual_hygiene_product", "Menstrual Hygiene Products", ["biomedical"], "月经卫生用品"),
            ]
        )

    def test_exact_expansion_batch_383_adds_mental_status_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mental_competency", "Mental Competency", ["biomedical", "psychiatry_and_psychology"], "精神行为能力"),
                ("mental_disorder__3", "Mental Disorder", ["biomedical", "psychiatry_and_psychology"], "精神障碍"),
                ("mental_fatigue", "Mental Fatigue", ["biomedical", "diseases"], "精神疲劳"),
                ("mental_foramen", "Mental Foramen", ["anatomy", "biomedical"], "颏孔"),
                ("mental_health_servic", "Mental Health Services", ["biomedical", "psychiatry_and_psychology"], "心理健康服务"),
                ("mental_hygiene", "Mental Hygiene", ["biomedical", "psychiatry_and_psychology"], "心理卫生"),
                ("mental_recall", "Mental Recall", ["biomedical", "psychiatry_and_psychology"], "心理回忆"),
            ]
        )

    def test_exact_expansion_batch_384_adds_mental_health_and_mentha_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mental_health_and_well_being", "Mental Health And Well-being", ["social_sciences"], "心理健康与幸福感"),
                ("mental_health_recovery", "Mental Health Recovery", ["biomedical", "health_care"], "心理健康康复"),
                ("mental_health_teletherapy", "Mental Health Teletherapy", ["biomedical"], "心理健康远程治疗"),
                ("mentalization", "Mentalization", ["biomedical", "psychiatry_and_psychology"], "心理化"),
                ("mentalization_based_therapy", "Mentalization-based Therapy", ["biomedical"], "心理化治疗"),
                ("mentha", "Mentha", ["biomedical", "organisms"], "薄荷属"),
                ("menthol", "Menthol", ["biomedical", "chemicals_and_drugs"], "薄荷醇"),
            ]
        )

    def test_exact_expansion_batch_385_adds_meperidine_and_mercury_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("menu_planning", "Menu Planning", ["biomedical"], "膳食计划"),
                ("meperidine", "Meperidine", ["biomedical", "chemicals_and_drugs"], "哌替啶"),
                ("mepivacaine", "Mepivacaine", ["biomedical", "chemicals_and_drugs"], "甲哌卡因"),
                ("meprobamate", "Meprobamate", ["biomedical", "chemicals_and_drugs"], "甲丙氨酯"),
                ("mercaptoethanol", "Mercaptoethanol", ["biomedical", "chemicals_and_drugs"], "巯基乙醇"),
                ("mercaptopurine", "Mercaptopurine", ["biomedical", "chemicals_and_drugs"], "巯嘌呤"),
                ("mercuric_chloride", "Mercuric Chloride", ["biomedical", "chemicals_and_drugs"], "氯化汞"),
            ]
        )

    def test_exact_expansion_batch_386_adds_mercury_and_merkel_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mercury", "Mercury", ["biomedical", "chemicals_and_drugs"], "汞元素"),
                ("mercury_compound", "Mercury Compounds", ["biomedical", "chemicals_and_drugs"], "汞化合物"),
                ("mercury_poisoning", "Mercury Poisoning", ["biomedical", "diseases"], "汞中毒"),
                ("mercury_poisoning_nervou_system", "Mercury Poisoning, Nervous System", ["biomedical", "diseases"], "神经系统汞中毒"),
                ("meridian", "Meridians", ["biomedical"], "经络"),
                ("meristem", "Meristem", ["anatomy", "biomedical"], "分生组织"),
                ("merkel_cell_polyomaviru", "Merkel Cell Polyomavirus", ["biomedical", "organisms"], "默克尔细胞多瘤病毒"),
                ("meropenem", "Meropenem", ["biomedical", "chemicals_and_drugs"], "美罗培南"),
            ]
        )

    def test_exact_expansion_batch_387_adds_mesalamine_and_mesenchymal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mesalamine", "Mesalamine", ["biomedical", "chemicals_and_drugs"], "美沙拉嗪"),
                ("mesangial_cell", "Mesangial Cells", ["anatomy", "biomedical"], "系膜细胞"),
                ("mescaline", "Mescaline", ["biomedical", "chemicals_and_drugs"], "麦司卡林"),
                ("mesencephalon", "Mesencephalon", ["anatomy", "biomedical"], "中脑"),
                ("mesenchymal_stem_cell", "Mesenchymal Stem Cells", ["anatomy", "biomedical"], "间充质干细胞"),
                ("mesenchymal_stem_cell_transplantation", "Mesenchymal Stem Cell Transplantation", ["biomedical"], "间充质干细胞移植"),
                ("mesenteric_artery", "Mesenteric Arteries", ["anatomy", "biomedical"], "肠系膜动脉"),
            ]
        )

    def test_exact_expansion_batch_388_adds_mesenteric_and_mesh_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mesenteric_ischemia", "Mesenteric Ischemia", ["biomedical", "diseases"], "肠系膜缺血"),
                ("mesenteric_lymphadeniti", "Mesenteric Lymphadenitis", ["biomedical", "diseases"], "肠系膜淋巴结炎"),
                ("mesenteric_vein", "Mesenteric Veins", ["anatomy", "biomedical"], "肠系膜静脉"),
                ("mesh_free_method", "Mesh-free Method", ["computer_science"], "无网格法"),
                ("mesh_network__2", "Mesh Network", ["computer_science"], "网状网络"),
                ("mesh_router", "Mesh Routers", ["computer_science"], "网状路由器"),
                ("mesh_topology", "Mesh Topologies", ["computer_science"], "网状拓扑"),
                ("wireless_mesh_network", "Wireless Mesh Networks", ["computer_science"], "无线网状网络"),
                ("multi_hop_wireless_mesh_network", "Multi-hop Wireless Mesh Networks", ["computer_science"], "多跳无线网状网络"),
            ]
        )

    def test_exact_expansion_batch_389_adds_mesoderm_message_and_meta_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mesoderm", "Mesoderm", ["anatomy", "biomedical"], "中胚层"),
                ("mesolimbic_system", "Mesolimbic System", ["anatomy", "biomedical"], "中脑边缘系统"),
                ("mesoporou_material", "Mesoporous Materials", ["materials_elements_and_compounds"], "介孔材料"),
                ("mesothelioma", "Mesothelioma", ["biomedical", "diseases"], "间皮瘤"),
                ("message_authentication__2", "message authentication code", ["computer_science"], "消息认证码"),
                ("message_passing_interface", "Message Passing Interface", ["computer_science"], "消息传递接口"),
                ("meta_analysi", "Meta-analysis", ["biomedical", "publication_characteristics"], "荟萃分析"),
                ("network_meta_analysi", "Network Meta-analysis", ["biomedical", "publication_characteristics"], "网络荟萃分析"),
                ("network_meta_analysi_as_topic", "Network Meta-analysis As Topic", ["biomedical"], "网络荟萃分析专题"),
            ]
        )

    def test_exact_expansion_batch_390_adds_metaheuristic_and_metabolic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("metacognition__2", "Meta-cognition", ["biomedical", "psychiatry_and_psychology"], "元认知"),
                ("meta_heuristic_method", "Meta-heuristic Methods", ["computer_science"], "元启发式方法"),
                ("meta_learning", "Meta-learning", ["computer_science"], "元学习"),
                ("metabolic_clearance_rate", "Metabolic Clearance Rate", ["biomedical"], "代谢清除率"),
                ("metabolic_disease", "Metabolic Diseases", ["biomedical", "diseases"], "代谢性疾病"),
                ("metabolic_engineering", "Metabolic Engineering", ["biomedical"], "代谢工程"),
                ("metabolic_flux_analysi", "Metabolic Flux Analysis", ["biomedical"], "代谢通量分析"),
            ]
        )

    def test_exact_expansion_batch_391_adds_metabolome_and_metagenomics_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("metabolic_reprogramming", "Metabolic Reprogramming", ["biomedical"], "代谢重编程"),
                ("metabolism__3", "Metabolic Process", ["biomedical"], "代谢过程"),
                ("metabolome", "Metabolome", ["biomedical", "phenomena_and_processes"], "代谢组"),
                ("metabolomic", "Metabolomics", ["biomedical", "disciplines_and_occupations"], "代谢组学"),
                ("receptor_metabotropic_glutamate", "Metabotropic Glutamate Receptor", ["biomedical", "chemicals_and_drugs"], "代谢型谷氨酸受体"),
                ("metagenome", "Metagenome", ["biomedical", "phenomena_and_processes"], "宏基因组"),
                ("metagenomic", "Metagenomics", ["biomedical", "disciplines_and_occupations"], "宏基因组学"),
            ]
        )

    def test_exact_expansion_batch_392_adds_metacarpal_and_metal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("metacarpal_bon", "Metacarpal Bones", ["anatomy", "biomedical"], "掌骨"),
                ("metacarpophalangeal_joint", "Metacarpophalangeal Joint", ["anatomy", "biomedical"], "掌指关节"),
                ("metadata_server", "Metadata Servers", ["computer_science"], "元数据服务器"),
                ("metal__2", "Metal", ["biomedical", "chemicals_and_drugs"], "金属"),
                ("metal_cutting", "Metal Cutting", ["computer_science"], "金属切削"),
                ("metal_detector", "Metal Detectors", ["computer_science"], "金属探测器"),
                ("metal_foam", "Metal Foam", ["materials_elements_and_compounds"], "金属泡沫"),
            ]
        )

    def test_exact_expansion_batch_393_adds_metal_framework_and_material_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("metal_gate", "Metal Gate", ["computer_science"], "金属栅"),
                ("metal_insulator_boundary", "Metal Insulator Boundaries", ["computer_science"], "金属-绝缘体边界"),
                ("metal_nanoparticl", "Metal Nanoparticles", ["biomedical"], "金属纳米颗粒"),
                ("metal_organic_framework", "Metal-organic Frameworks", ["biomedical", "chemicals_and_drugs"], "金属有机框架"),
                ("metal_product", "Metal Products", ["industry_applications"], "金属制品"),
                ("metallic_glasse_and_amorphou_alloy", "Metallic Glasses And Amorphous Alloys", ["engineering"], "金属玻璃与非晶合金"),
                ("metallic_material", "Metallic Materials", ["materials_elements_and_compounds"], "金属材料"),
                ("integrated_circuit_metallization", "Integrated Circuit Metallization", ["materials_elements_and_compounds"], "集成电路金属化"),
            ]
        )

    def test_exact_expansion_batch_394_adds_metallo_and_metamaterial_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("metallization", "Metallization", ["materials_elements_and_compounds"], "金属化"),
                ("metalloprotein", "Metalloproteins", ["biomedical", "chemicals_and_drugs"], "金属蛋白"),
                ("metallothionein", "Metallothionein", ["biomedical", "chemicals_and_drugs"], "金属硫蛋白"),
                ("metallurgical_processe_and_thermodynamic", "Metallurgical Processes And Thermodynamics", ["engineering"], "冶金过程与热力学"),
                ("metallurgy_and_material_science", "Metallurgy And Material Science", ["materials_science"], "冶金学与材料科学"),
                ("metamaterial__2", "Metamaterial", ["computer_science"], "超材料"),
                ("metamaterial_antenna", "Metamaterial Antennas", ["computer_science"], "超材料天线"),
            ]
        )

    def test_exact_expansion_batch_395_adds_metaphysics_and_metatarsal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("metaphor", "Metaphor", ["biomedical", "humanities"], "隐喻"),
                ("metaphysic", "Metaphysics", ["biomedical", "humanities"], "形而上学"),
                ("metaplasia", "Metaplasia", ["biomedical", "diseases"], "化生"),
                ("metapneumoviru", "Metapneumovirus", ["biomedical", "organisms"], "偏肺病毒"),
                ("metasurfac", "Metasurfaces", ["materials_elements_and_compounds"], "超表面"),
                ("metatarsal_bon", "Metatarsal Bones", ["anatomy", "biomedical"], "跖骨"),
                ("metatarsophalangeal_joint", "Metatarsophalangeal Joint", ["anatomy", "biomedical"], "跖趾关节"),
            ]
        )

    def test_exact_expansion_batch_396_adds_metered_inhaler_and_methane_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("metencephalon", "Metencephalon", ["anatomy", "biomedical"], "后脑"),
                ("metered_dose_inhaler", "Metered Dose Inhalers", ["biomedical"], "定量吸入器"),
                ("metformin", "Metformin", ["biomedical", "chemicals_and_drugs"], "二甲双胍"),
                ("methacholine_chloride", "Methacholine Chloride", ["biomedical", "chemicals_and_drugs"], "氯化乙酰甲胆碱"),
                ("methacrylat", "Methacrylates", ["biomedical", "chemicals_and_drugs"], "甲基丙烯酸酯类"),
                ("methadone", "Methadone", ["biomedical", "chemicals_and_drugs"], "美沙酮"),
                ("methane", "Methane", ["biomedical", "chemicals_and_drugs"], "甲烷"),
            ]
        )

    def test_exact_expansion_batch_397_adds_methanogen_and_methemoglobin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("methanobacterium", "Methanobacterium", ["biomedical", "organisms"], "甲烷杆菌属"),
                ("methanococcu", "Methanococcus", ["biomedical", "organisms"], "甲烷球菌属"),
                ("methanosarcina", "Methanosarcina", ["biomedical", "organisms"], "甲烷八叠球菌属"),
                ("methemoglobin", "Methemoglobin", ["biomedical", "chemicals_and_drugs"], "高铁血红蛋白"),
                ("methemoglobinemia", "Methemoglobinemia", ["biomedical", "diseases"], "高铁血红蛋白血症"),
                ("methenamine", "Methenamine", ["biomedical", "chemicals_and_drugs"], "乌洛托品"),
                ("methicillin_resistance", "Methicillin Resistance", ["biomedical"], "甲氧西林耐药性"),
            ]
        )

    def test_exact_expansion_batch_398_adds_mrsa_and_methionine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("methicillin", "Methicillin", ["biomedical", "chemicals_and_drugs"], "甲氧西林"),
                ("methicillin_resistant_staphylococcu_aureu", "Methicillin-resistant Staphylococcus Aureus", ["biomedical", "organisms"], "耐甲氧西林金黄色葡萄球菌"),
                ("methimazole", "Methimazole", ["biomedical", "chemicals_and_drugs"], "甲巯咪唑"),
                ("methionine", "Methionine", ["biomedical", "chemicals_and_drugs"], "蛋氨酸"),
                ("methionine_adenosyltransferase", "Methionine Adenosyltransferase", ["biomedical", "chemicals_and_drugs"], "蛋氨酸腺苷转移酶"),
                ("methionine_sulfoxide_reductase", "Methionine Sulfoxide Reductases", ["biomedical", "chemicals_and_drugs"], "蛋氨酸亚砜还原酶"),
                ("methotrexate", "Methotrexate", ["biomedical", "chemicals_and_drugs"], "甲氨蝶呤"),
            ]
        )

    def test_exact_expansion_batch_399_adds_methylation_and_methylene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("method_of_moment", "Method Of Moments", ["computer_science", "mathematics"], "矩量法"),
                ("methyl_chloride", "Methyl Chloride", ["biomedical", "chemicals_and_drugs"], "氯甲烷"),
                ("methyl_cpg_binding_protein_2", "Methyl-cpg-binding Protein 2", ["biomedical", "chemicals_and_drugs"], "甲基CpG结合蛋白2"),
                ("methylation", "Methylation", ["biomedical", "phenomena_and_processes"], "甲基化"),
                ("methylene_blue", "Methylene Blue", ["biomedical", "chemicals_and_drugs"], "亚甲蓝"),
                ("methylenetetrahydrofolate_reductase_nadph2", "Methylenetetrahydrofolate Reductase (nadph2)", ["biomedical", "chemicals_and_drugs"], "亚甲基四氢叶酸还原酶"),
                ("methylprednisolone_acetate", "Methylprednisolone Acetate", ["biomedical", "chemicals_and_drugs"], "醋酸甲泼尼龙"),
                ("methyltransferase", "Methyltransferases", ["biomedical", "chemicals_and_drugs"], "甲基转移酶"),
                ("rna_methylation", "RNA Methylation", ["biomedical", "phenomena_and_processes"], "RNA甲基化"),
            ]
        )

    def test_exact_expansion_batch_400_adds_metoprolol_metric_and_mice_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("metoclopramide", "Metoclopramide", ["biomedical", "chemicals_and_drugs"], "甲氧氯普胺"),
                ("metoprolol", "Metoprolol", ["biomedical", "chemicals_and_drugs"], "美托洛尔"),
                ("metric_space", "Metric Space", ["computer_science"], "度量空间"),
                ("metro_network", "Metro Networks", ["computer_science"], "城域网"),
                ("metronidazole", "Metronidazole", ["biomedical", "chemicals_and_drugs"], "甲硝唑"),
                ("metropoli_hasting_algorithm", "Metropolis-hastings Algorithm", ["computer_science"], "Metropolis-Hastings算法"),
                ("mice", "Mice", ["biomedical", "organisms"], "小鼠"),
            ]
        )

    def test_exact_expansion_batch_401_adds_micro_device_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("micafungin", "Micafungin", ["biomedical", "chemicals_and_drugs"], "米卡芬净"),
                ("micro_and_nano_robotic", "Micro And Nano Robotics", ["physics"], "微纳机器人"),
                ("micro_and_nano_system", "Micro And Nano Systems", ["computer_science"], "微纳系统"),
                ("micro_controller", "Micro-controller", ["computer_science"], "微控制器"),
                ("micro_ct", "Micro Ct", ["computer_science"], "微型CT"),
                ("micro_electrical_mechanical_system__2", "Micro-Electrical-Mechanical System", ["biomedical"], "微机电系统"),
                ("micro_fabrication_techniqu", "Micro-fabrication Techniques", ["computer_science"], "微制造技术"),
            ]
        )

    def test_exact_expansion_batch_402_adds_micro_mechanical_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("micro_cantilever", "Micro-cantilevers", ["computer_science"], "微悬臂梁"),
                ("micro_milling", "Micro Milling", ["computer_science"], "微铣削"),
                ("micro_mirror", "Micro Mirror", ["computer_science"], "微镜"),
                ("micro_mobility", "Micro-mobility", ["computer_science"], "微出行"),
                ("micro_robotic", "Micro Robotics", ["computer_science"], "微机器人学"),
                ("micro_strip_patch_antenna", "Micro-strip Patch Antennas", ["computer_science"], "微带贴片天线"),
                ("micro_structured_optical_fiber", "Micro-structured Optical Fibers", ["computer_science"], "微结构光纤"),
            ]
        )

    def test_exact_expansion_batch_403_adds_microarray_and_microbial_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microalgae", "Microalgae", ["biomedical", "organisms"], "微藻"),
                ("microaneurysm", "Microaneurysm", ["biomedical", "diseases"], "微动脉瘤"),
                ("microarray_analysi", "Microarray Analysis", ["biomedical"], "微阵列分析"),
                ("microautophagy", "Microautophagy", ["biomedical", "phenomena_and_processes"], "微自噬"),
                ("microbial_collagenase", "Microbial Collagenase", ["biomedical", "chemicals_and_drugs"], "微生物胶原酶"),
                ("colony_count_microbial", "Microbial Colony Count", ["biomedical"], "微生物菌落计数"),
                ("microbial_diversity", "Microbial Diversity", ["computer_science"], "微生物多样性"),
            ]
        )

    def test_exact_expansion_batch_404_adds_microbial_ecology_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microbial_bioremediation_and_biosurfactant", "Microbial Bioremediation And Biosurfactants", ["environmental_science"], "微生物生物修复与生物表面活性剂"),
                ("microbial_community_ecology_and_physiology", "Microbial Community Ecology And Physiology", ["environmental_science"], "微生物群落生态学与生理学"),
                ("microbial_consortia", "Microbial Consortia", ["biomedical", "phenomena_and_processes"], "微生物共生体"),
                ("microbial_fuel_cell_and_bioremediation", "Microbial Fuel Cells And Bioremediation", ["environmental_science"], "微生物燃料电池与生物修复"),
                ("microbial_inactivation_method", "Microbial Inactivation Methods", ["life_sciences"], "微生物灭活方法"),
                ("microbial_interaction", "Microbial Interactions", ["biomedical"], "微生物相互作用"),
                ("microbial_sensitivity_test", "Microbial Sensitivity Tests", ["biomedical"], "微生物敏感性试验"),
            ]
        )

    def test_exact_expansion_batch_405_adds_microbiological_and_microchip_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microbiological_phenomena", "Microbiological Phenomena", ["biomedical"], "微生物学现象"),
                ("microbiological_techniqu", "Microbiological Techniques", ["biomedical"], "微生物学技术"),
                ("microbiota", "Microbiota", ["biomedical", "phenomena_and_processes"], "微生物群"),
                ("microbody", "Microbodies", ["anatomy", "biomedical"], "微体"),
                ("microbubbl", "Microbubbles", ["biomedical"], "微泡"),
                ("microcephaly", "Microcephaly", ["biomedical", "diseases"], "小头畸形"),
                ("electrophoresi_microchip", "Microchip Electrophoreses", ["biomedical"], "微芯片电泳"),
            ]
        )

    def test_exact_expansion_batch_406_adds_micrococcus_and_microelectrode_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microclimate", "Microclimate", ["biomedical"], "微气候"),
                ("micrococcal_nuclease", "Micrococcal Nuclease", ["biomedical", "chemicals_and_drugs"], "微球菌核酸酶"),
                ("micrococcu_luteu", "Micrococcus Luteus", ["biomedical", "organisms"], "藤黄微球菌"),
                ("microcomputer__2", "Microcomputer", ["biomedical", "information_science"], "微型计算机"),
                ("microcystin", "Microcystins", ["biomedical", "chemicals_and_drugs"], "微囊藻毒素"),
                ("microdialysi", "Microdialysis", ["biomedical"], "微透析"),
                ("microelectrod__2", "Microelectrode", ["biomedical"], "微电极"),
            ]
        )

    def test_exact_expansion_batch_407_adds_microelectromechanical_and_microfluidic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microelectromechanical_devic", "Microelectromechanical Devices", ["electron_devices"], "微机电器件"),
                ("micro_electrical_mechanical_system", "microelectromechanical system", ["computer_science"], "微机电系统"),
                ("microfabrication_process", "Microfabrication Process", ["computer_science"], "微制造工艺"),
                ("microfilament_protein", "Microfilament Proteins", ["biomedical", "chemicals_and_drugs"], "微丝蛋白"),
                ("microfilariae", "Microfilariae", ["biomedical", "organisms"], "微丝蚴"),
                ("microfiltration", "Microfiltration", ["materials_elements_and_compounds"], "微滤"),
                ("microfluidic__4", "Microfluidic", ["biomedical"], "微流控"),
            ]
        )

    def test_exact_expansion_batch_408_adds_microfluidic_and_microgrid_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microfluidic_analytical_techniqu", "Microfluidic Analytical Techniques", ["biomedical"], "微流控分析技术"),
                ("microfluidic_and_bio_sensing_technology", "Microfluidic And Bio-sensing Technologies", ["engineering"], "微流控与生物传感技术"),
                ("microgel", "Microgels", ["biomedical", "chemicals_and_drugs"], "微凝胶"),
                ("microglia", "Microglia", ["anatomy", "biomedical"], "小胶质细胞"),
                ("micrognathism", "Micrognathism", ["biomedical", "diseases"], "小颌畸形"),
                ("microgrid_control_and_optimization", "Microgrid Control And Optimization", ["engineering"], "微电网控制与优化"),
                ("microinjection__3", "Microinjections", ["biomedical"], "显微注射"),
            ]
        )

    def test_exact_expansion_batch_409_adds_micromechanics_and_micronutrient_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microkernel", "Microkernel", ["computer_science"], "微内核"),
                ("micromagnetic", "Micromagnetics", ["magnetics"], "微磁学"),
                ("micromanipulation", "Micromanipulation", ["biomedical"], "显微操作"),
                ("micromechanical_model", "Micromechanical Model", ["computer_science"], "微力学模型"),
                ("micromechanic", "Micromechanics", ["computer_science"], "微力学"),
                ("micrometer", "Micrometers", ["instrumentation_and_measurement"], "测微计"),
                ("micronutrient", "Micronutrients", ["biomedical", "chemicals_and_drugs"], "微量营养素"),
            ]
        )

    def test_exact_expansion_batch_410_adds_microphone_and_microplastic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microneedle_drug_delivery", "Microneedle Drug Delivery", ["biomedical"], "微针给药"),
                ("micronucleu_test", "Micronucleus Tests", ["biomedical"], "微核试验"),
                ("microoptic", "Microoptics", ["lasers_and_electrooptics"], "微光学"),
                ("microphone", "Microphone", ["computer_science"], "麦克风"),
                ("microphone_array__2", "Microphone Array", ["computer_science"], "麦克风阵列"),
                ("microplastic__2", "Microplastic", ["biomedical", "chemicals_and_drugs"], "微塑料"),
                ("micropore_filter", "Micropore Filters", ["biomedical"], "微孔滤膜"),
            ]
        )

    def test_exact_expansion_batch_411_adds_microrna_and_microsoft_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microrna", "Micrornas", ["biomedical", "chemicals_and_drugs"], "微小RNA"),
                ("microsatellite_dna", "Microsatellite Dna", ["computer_science"], "微卫星DNA"),
                ("microsatellite_repeat", "Microsatellite Repeat", ["biomedical"], "微卫星重复序列"),
                ("microscopic_coliti", "Microscopic Colitis", ["biomedical", "diseases"], "显微镜下结肠炎"),
                ("microservice_architecture", "Microservice Architecture", ["computer_science"], "微服务架构"),
                ("microsoft_sql_server", "Microsoft Sql Server", ["computer_science"], "微软SQL服务器"),
                ("microsoft_window", "Microsoft Windows", ["computer_science"], "微软视窗"),
            ]
        )

    def test_exact_expansion_batch_412_adds_microsporidia_and_microstrip_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microsom", "Microsomes", ["anatomy", "biomedical"], "微粒体"),
                ("microspher", "Microspheres", ["biomedical"], "微球"),
                ("microsporidia", "Microsporidia", ["biomedical", "organisms"], "微孢子虫"),
                ("microsporidiosi", "Microsporidiosis", ["biomedical", "diseases"], "微孢子虫病"),
                ("microstrip", "Microstrip", ["computer_science"], "微带"),
                ("microstrip_antenna__2", "Microstrip Antenna", ["computer_science"], "微带天线"),
                ("microstrip_band_pass_filter", "Microstrip Band-pass Filter", ["computer_science"], "微带带通滤波器"),
            ]
        )

    def test_exact_expansion_batch_413_adds_microstructure_and_microvascular_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microstructure", "Microstructure", ["materials_elements_and_compounds"], "微观结构"),
                ("microstructure_and_mechanical_property", "Microstructure And Mechanical Properties", ["materials_science"], "微观结构与力学性能"),
                ("microtechnology", "Microtechnology", ["biomedical"], "微技术"),
                ("microtubule_organizing_center", "Microtubule-organizing Center", ["anatomy", "biomedical"], "微管组织中心"),
                ("microvascular_angina", "Microvascular Angina", ["biomedical", "diseases"], "微血管性心绞痛"),
                ("microvascular_density", "Microvascular Density", ["biomedical"], "微血管密度"),
                ("microvilli", "Microvilli", ["anatomy", "biomedical"], "微绒毛"),
            ]
        )

    def test_exact_expansion_batch_414_adds_microwave_basic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microwav__2", "Microwave", ["biomedical"], "微波"),
                ("microwave_ablation", "Microwave Ablation", ["microwave_theory_and_techniques"], "微波消融"),
                ("microwave_antenna_array", "Microwave Antenna Arrays", ["antennas_and_propagation"], "微波天线阵列"),
                ("microwave_band", "Microwave Bands", ["microwave_theory_and_techniques"], "微波频段"),
                ("microwave_devic", "Microwave Devices", ["microwave_theory_and_techniques"], "微波器件"),
                ("microwave_filter", "Microwave Filters", ["microwave_theory_and_techniques"], "微波滤波器"),
                ("microwave_generation", "Microwave Generation", ["microwave_theory_and_techniques"], "微波产生"),
            ]
        )

    def test_exact_expansion_batch_415_adds_microwave_engineering_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("microwave_engineering_and_waveguid", "Microwave Engineering And Waveguides", ["engineering"], "微波工程与波导"),
                ("microwave_imaging_and_scattering_analysi", "Microwave Imaging And Scattering Analysis", ["engineering"], "微波成像与散射分析"),
                ("microwave_link", "Microwave Links", ["computer_science"], "微波链路"),
                ("microwave_measurement", "Microwave Measurement", ["instrumentation_and_measurement"], "微波测量"),
                ("microwave_metamaterial", "Microwave Metamaterials", ["electromagnetic_compatibility_and_interference"], "微波超材料"),
                ("microwave_oscillator", "Microwave Oscillators", ["circuits_and_systems"], "微波振荡器"),
                ("microwave_sensor", "Microwave Sensors", ["microwave_theory_and_techniques"], "微波传感器"),
            ]
        )

    def test_exact_expansion_batch_416_adds_midbrain_and_middle_ear_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("midazolam", "Midazolam", ["biomedical", "chemicals_and_drugs"], "咪达唑仑"),
                ("midbrain_raphe_nuclei", "Midbrain Raphe Nuclei", ["anatomy", "biomedical"], "中脑缝核"),
                ("middle_aged", "Middle Aged", ["biomedical", "named_groups"], "中年人"),
                ("middle_cerebral_artery", "Middle Cerebral Artery", ["anatomy", "biomedical"], "大脑中动脉"),
                ("cholesteatoma_middle_ear", "Middle Ear Cholesteatomas", ["biomedical", "diseases"], "中耳胆脂瘤"),
                ("ear_middle", "Middle Ears", ["anatomy", "biomedical"], "中耳"),
                ("middle_east_respiratory_syndrome_coronaviru", "Middle East Respiratory Syndrome Coronavirus", ["biomedical", "organisms"], "中东呼吸综合征冠状病毒"),
            ]
        )

    def test_exact_expansion_batch_417_adds_middle_east_and_migraine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("middle_east", "Middle East", ["biomedical", "geographicals"], "中东"),
                ("middle_eastern_people", "Middle Eastern People", ["biomedical", "named_groups"], "中东人群"),
                ("middleware", "Middleware", ["computers_and_information_processing"], "中间件"),
                ("midodrine", "Midodrine", ["biomedical", "chemicals_and_drugs"], "米多君"),
                ("midwifery", "Midwifery", ["biomedical"], "助产学"),
                ("mifepristone", "Mifepristone", ["biomedical", "chemicals_and_drugs"], "米非司酮"),
                ("migraine_with_aura", "Migraine With Aura", ["biomedical", "diseases"], "有先兆偏头痛"),
            ]
        )

    def test_exact_expansion_batch_418_adds_military_base_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("milieu_therapy", "Milieu Therapy", ["biomedical", "psychiatry_and_psychology"], "环境疗法"),
                ("military_aircraft", "Military Aircraft", ["aerospace_and_electronic_systems"], "军用飞机"),
                ("military_communication", "Military Communication", ["communications_technology"], "军事通信"),
                ("military_computing", "Military Computing", ["computers_and_information_processing"], "军事计算"),
                ("military_equipment", "Military Equipment", ["aerospace_and_electronic_systems"], "军事装备"),
                ("military_health", "Military Health", ["biomedical", "health_care"], "军事健康"),
                ("military_medicine", "Military Medicine", ["biomedical"], "军事医学"),
            ]
        )

    def test_exact_expansion_batch_419_adds_military_and_milk_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("military_personnel", "Military Personnel", ["biomedical", "named_groups"], "军事人员"),
                ("psychology_military", "Military Psychology", ["biomedical", "psychiatry_and_psychology"], "军事心理学"),
                ("military_science", "Military Science", ["biomedical"], "军事科学"),
                ("military_system", "Military Systems", ["systems_engineering_and_theory"], "军事系统"),
                ("milk", "Milk", ["anatomy", "biomedical"], "乳汁"),
                ("milk_bank", "Milk Banks", ["biomedical", "health_care"], "乳库"),
                ("milk_protein", "Milk Proteins", ["anatomy", "biomedical"], "乳蛋白"),
            ]
        )

    def test_exact_expansion_batch_420_adds_millimeter_wave_and_mimo_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("miller_fisher_syndrome", "Miller Fisher Syndrome", ["biomedical", "diseases"], "米勒-费希尔综合征"),
                ("millimeter_wave_communication", "Millimeter Wave Communication", ["communications_technology"], "毫米波通信"),
                ("millimeter_wave_devic", "Millimeter Wave Devices", ["microwave_theory_and_techniques"], "毫米波器件"),
                ("millimeter_wave_propagation", "Millimeter Wave Propagation", ["antennas_and_propagation"], "毫米波传播"),
                ("milling_process", "Milling Process", ["computer_science"], "铣削工艺"),
                ("mimo_antenna", "Mimo Antenna", ["computer_science"], "MIMO天线"),
                ("mimo_system", "Mimo Systems", ["computer_science"], "MIMO系统"),
            ]
        )

    def test_exact_expansion_batch_421_adds_milk_and_millimeter_wave_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("milk_ejection", "Milk Ejection", ["biomedical", "phenomena_and_processes"], "射乳"),
                ("milk_human", "Milk, Human", ["anatomy", "biomedical"], "人乳"),
                ("milk_hypersensitivity", "Milk Hypersensitivity", ["biomedical", "diseases"], "牛奶过敏"),
                ("milk_sickness", "Milk Sickness", ["biomedical", "diseases"], "乳毒病"),
                ("milk_substitut", "Milk Substitutes", ["biomedical", "phenomena_and_processes"], "代乳品"),
                ("millimeter_wave_circuit", "Millimeter Wave Circuits", ["circuits_and_systems"], "毫米波电路"),
                ("millimeter_wave_integrated_circuit", "Millimeter Wave Integrated Circuits", ["circuits_and_systems"], "毫米波集成电路"),
            ]
        )

    def test_exact_expansion_batch_422_adds_millimeter_wave_and_mindfulness_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("millimeter_wave_measurement", "Millimeter Wave Measurements", ["instrumentation_and_measurement"], "毫米波测量"),
                ("millimeter_wave_radar", "Millimeter Wave Radar", ["microwave_theory_and_techniques"], "毫米波雷达"),
                ("millimeter_wave_technology", "Millimeter Wave Technology", ["microwave_theory_and_techniques"], "毫米波技术"),
                ("millimeter_wave_transistor", "Millimeter Wave Transistors", ["electron_devices"], "毫米波晶体管"),
                ("mind_body_therapy", "Mind-body Therapies", ["biomedical"], "身心疗法"),
                ("mindfulness", "Mindfulness", ["biomedical", "psychiatry_and_psychology"], "正念"),
                ("mindfulness_based_cognitive_therapy", "Mindfulness-based Cognitive Therapy", ["biomedical"], "正念认知疗法"),
            ]
        )

    def test_exact_expansion_batch_423_adds_mindfulness_and_mineral_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mindfulness_based_stress_reduction", "Mindfulness-based Stress Reduction", ["biomedical"], "正念减压疗法"),
                ("mineral__4", "Minerals", ["biomedical", "chemicals_and_drugs"], "矿物质"),
                ("mineral_fiber", "Mineral Fibers", ["biomedical", "chemicals_and_drugs"], "矿物纤维"),
                ("mineral_oil", "Mineral Oil", ["biomedical", "chemicals_and_drugs"], "矿物油"),
                ("mineral_water", "Mineral Waters", ["biomedical", "chemicals_and_drugs"], "矿泉水"),
                ("mineralocorticoid", "Mineralocorticoids", ["biomedical", "chemicals_and_drugs"], "盐皮质激素"),
                ("mineralocorticoid_excess_syndrome_apparent", "Mineralocorticoid Excess Syndrome, Apparent", ["biomedical", "diseases"], "表观盐皮质激素过多综合征"),
            ]
        )

    def test_exact_expansion_batch_424_adds_mineralocorticoid_and_minimal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mineralocorticoid_receptor_antagonist", "Mineralocorticoid Receptor Antagonists", ["biomedical", "chemicals_and_drugs"], "盐皮质激素受体拮抗剂"),
                ("miniature_postsynaptic_potential", "Miniature Postsynaptic Potentials", ["biomedical"], "微型突触后电位"),
                ("miniaturization", "Miniaturization", ["biomedical"], "小型化"),
                ("minichromosome_maintenance_protein", "Minichromosome Maintenance Proteins", ["biomedical", "chemicals_and_drugs"], "微小染色体维持蛋白"),
                ("minicomputer", "Minicomputers", ["biomedical", "information_science"], "小型计算机"),
                ("minimal_clinically_important_difference", "Minimal Clinically Important Difference", ["biomedical", "health_care"], "最小临床重要差异"),
                ("minimally_invasive_surgical_procedur", "Minimally Invasive Surgical Procedures", ["biomedical"], "微创外科手术"),
            ]
        )

    def test_exact_expansion_batch_425_adds_minimum_and_mining_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("minimally_invasive_surgical_techniqu", "Minimally Invasive Surgical Techniques", ["medicine"], "微创手术技术"),
                ("minimax_techniqu", "Minimax Techniques", ["mathematics"], "极小极大技术"),
                ("minimization", "Minimization", ["mathematics"], "最小化"),
                ("minimization_method", "Minimization Methods", ["mathematics"], "最小化方法"),
                ("minimum_classification_error", "Minimum Classification Error", ["computer_science"], "最小分类错误"),
                ("minimum_mean_square_error", "Minimum Mean Square Error", ["computer_science"], "最小均方误差"),
                ("minimum_spanning_tree", "Minimum Spanning Tree", ["computer_science"], "最小生成树"),
            ]
        )

    def test_exact_expansion_batch_426_adds_mining_and_minisatellite_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("minimum_spanning_tree_problem", "Minimum Spanning Tree Problem", ["computer_science"], "最小生成树问题"),
                ("mining", "Mining", ["biomedical", "technology_industry_and_agriculture"], "采矿"),
                ("mining_association", "Mining Associations", ["computer_science"], "关联挖掘"),
                ("mining_equipment", "Mining Equipment", ["industry_applications"], "采矿设备"),
                ("mining_industry", "Mining Industry", ["industry_applications"], "采矿业"),
                ("mining_software_repository", "Mining Software Repositories", ["computer_science"], "软件仓库挖掘"),
                ("minisatellite_repeat", "Minisatellite Repeats", ["biomedical", "phenomena_and_processes"], "小卫星重复序列"),
            ]
        )

    def test_exact_expansion_batch_427_adds_minor_and_mirror_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("minor", "Minors", ["biomedical", "named_groups"], "未成年人"),
                ("minor_histocompatibility_antigen", "Minor Histocompatibility Antigens", ["biomedical", "chemicals_and_drugs"], "次要组织相容性抗原"),
                ("minor_histocompatibility_loci", "Minor Histocompatibility Loci", ["biomedical"], "次要组织相容性位点"),
                ("minority_group", "Minority Groups", ["biomedical"], "少数群体"),
                ("minority_health", "Minority Health", ["biomedical", "health_care"], "少数群体健康"),
                ("mirror", "Mirrors", ["lasers_and_electrooptics"], "反射镜"),
                ("mirror_neuron", "Mirror Neurons", ["anatomy", "biomedical"], "镜像神经元"),
            ]
        )

    def test_exact_expansion_batch_428_adds_mirizzi_and_mis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mirror_movement_therapy", "Mirror Movement Therapy", ["biomedical"], "镜像运动疗法"),
                ("mirizzi_syndrome", "Mirizzi Syndrome", ["biomedical", "diseases"], "Mirizzi综合征"),
                ("mirtazapine", "Mirtazapine", ["biomedical", "chemicals_and_drugs"], "米氮平"),
                ("mis_devic", "MIS Devices", ["electron_devices"], "MIS器件"),
                ("misfet", "Misfets", ["solid_state_circuits"], "MIS场效应晶体管"),
                ("misinformation_and_its_impact", "Misinformation And Its Impacts", ["social_sciences"], "错误信息及其影响"),
                ("mismatch_repair_endonuclease_pms2", "Mismatch Repair Endonuclease PMS2", ["biomedical", "chemicals_and_drugs"], "错配修复内切核酸酶PMS2"),
            ]
        )

    def test_exact_expansion_batch_429_adds_miso_missile_and_misoprostol_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("miso", "MISO", ["communications_technology"], "MISO系统"),
                ("misonidazole", "Misonidazole", ["biomedical", "chemicals_and_drugs"], "米索硝唑"),
                ("misoprostol", "Misoprostol", ["biomedical", "chemicals_and_drugs"], "米索前列醇"),
                ("missed_detection", "Missed Detections", ["computer_science"], "漏检"),
                ("missed_diagnosi", "Missed Diagnosis", ["biomedical", "health_care"], "漏诊"),
                ("missil", "Missiles", ["aerospace_and_electronic_systems"], "导弹"),
                ("missile_control", "Missile Control", ["control_systems"], "导弹控制"),
            ]
        )

    def test_exact_expansion_batch_430_adds_mite_and_mitochondrial_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mistletoe", "Mistletoe", ["biomedical", "organisms"], "槲寄生"),
                ("misuse_detection", "Misuse Detection", ["computer_science"], "误用检测"),
                ("mit", "Mites", ["biomedical", "organisms"], "螨类"),
                ("mite_infestation", "Mite Infestations", ["biomedical", "diseases"], "螨虫感染"),
                ("mitobronitol", "Mitobronitol", ["biomedical", "chemicals_and_drugs"], "米托布隆醇"),
                ("mitochondrial_adp_atp_translocase", "Mitochondrial ADP, ATP Translocases", ["biomedical", "chemicals_and_drugs"], "线粒体ADP/ATP转位酶"),
                ("mitochondrial_dynamic", "Mitochondrial Dynamics", ["biomedical"], "线粒体动力学"),
            ]
        )

    def test_exact_expansion_batch_431_adds_mitochondrial_biomed_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mitochondrial_encephalomyopathy", "Mitochondrial Encephalomyopathies", ["biomedical", "diseases"], "线粒体脑肌病"),
                ("mitochondrial_gene", "Mitochondrial Gene", ["computer_science"], "线粒体基因"),
                ("mitochondrial_membrane_transport_protein", "Mitochondrial Membrane Transport Proteins", ["biomedical", "chemicals_and_drugs"], "线粒体膜转运蛋白"),
                ("mitochondrial_permeability_transition_pore", "Mitochondrial Permeability Transition Pore", ["biomedical", "chemicals_and_drugs"], "线粒体通透性转换孔"),
                ("mitochondrial_processing_peptidase", "Mitochondrial Processing Peptidase", ["biomedical", "chemicals_and_drugs"], "线粒体加工肽酶"),
                ("mitochondrial_replacement_therapy", "Mitochondrial Replacement Therapy", ["biomedical"], "线粒体替代疗法"),
                ("mitochondrial_ribosom", "Mitochondrial Ribosomes", ["anatomy", "biomedical"], "线粒体核糖体"),
            ]
        )

    def test_exact_expansion_batch_432_adds_mitochondrial_and_mapk_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mitochondrial_swelling", "Mitochondrial Swelling", ["biomedical"], "线粒体肿胀"),
                ("mitochondrial_uncoupling_protein", "Mitochondrial Uncoupling Proteins", ["biomedical", "chemicals_and_drugs"], "线粒体解偶联蛋白"),
                ("mitogen", "Mitogens", ["biomedical", "chemicals_and_drugs"], "有丝分裂原"),
                ("mitogen_activated_protein_kinase", "Mitogen-activated Protein Kinases", ["biomedical", "chemicals_and_drugs"], "丝裂原活化蛋白激酶"),
                ("mitogen_activated_protein_kinase_1", "Mitogen-activated Protein Kinase 1", ["biomedical", "chemicals_and_drugs"], "丝裂原活化蛋白激酶1"),
                ("mitogen_activated_protein_kinase_kinase", "Mitogen-activated Protein Kinase Kinases", ["biomedical", "chemicals_and_drugs"], "丝裂原活化蛋白激酶激酶"),
                ("mitogenome", "Mitogenome", ["computer_science"], "线粒体基因组"),
            ]
        )

    def test_exact_expansion_batch_433_adds_mitomycin_and_mitosis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mitoguazone", "Mitoguazone", ["biomedical", "chemicals_and_drugs"], "米托胍腙"),
                ("mitomycin", "Mitomycins", ["biomedical", "chemicals_and_drugs"], "丝裂霉素"),
                ("mitophagy", "Mitophagy", ["biomedical", "phenomena_and_processes"], "线粒体自噬"),
                ("mitosi", "Mitosis", ["biomedical", "phenomena_and_processes"], "有丝分裂"),
                ("mitosi_modulator", "Mitosis Modulators", ["biomedical", "chemicals_and_drugs"], "有丝分裂调节剂"),
                ("mitosporic_fungi", "Mitosporic Fungi", ["biomedical", "organisms"], "有丝孢子真菌"),
                ("mitotane", "Mitotane", ["biomedical", "chemicals_and_drugs"], "米托坦"),
            ]
        )

    def test_exact_expansion_batch_434_adds_mitotic_and_mixed_disease_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mitotic_index", "Mitotic Index", ["biomedical"], "有丝分裂指数"),
                ("mitoxantrone", "Mitoxantrone", ["biomedical", "chemicals_and_drugs"], "米托蒽醌"),
                ("mixed_connective_tissue_disease", "Mixed Connective Tissue Disease", ["biomedical", "diseases"], "混合性结缔组织病"),
                ("mixed_dementia", "Mixed Dementias", ["biomedical", "diseases"], "混合性痴呆"),
                ("mixed_finite_element_method", "Mixed Finite Element Method", ["computer_science"], "混合有限元法"),
                ("mixed_function_oxygenase", "Mixed Function Oxygenases", ["biomedical", "chemicals_and_drugs"], "混合功能氧化酶"),
                ("mixed_integer_programming_model", "Mixed Integer Programming Model", ["computer_science"], "混合整数规划模型"),
            ]
        )

    def test_exact_expansion_batch_435_adds_mixed_model_and_signal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mixed_noise", "Mixed Noise", ["computer_science"], "混合噪声"),
                ("mixed_pixel", "Mixed Pixel", ["computer_science"], "混合像元"),
                ("mixed_reality", "Mixed Reality", ["systems_engineering_and_theory"], "混合现实"),
                ("mixed_signal", "Mixed Signal", ["computer_science"], "混合信号"),
                ("mixed_strategy", "Mixed Strategy", ["computer_science"], "混合策略"),
                ("mixed_tumor_malignant", "Mixed Tumor, Malignant", ["biomedical", "diseases"], "恶性混合瘤"),
                ("mixer", "Mixers", ["power_electronics"], "混频器"),
            ]
        )

    def test_exact_expansion_batch_436_adds_mixture_and_ml_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mixing_matrix", "Mixing Matrix", ["computer_science"], "混合矩阵"),
                ("mixture_model", "Mixture Models", ["mathematics"], "混合模型"),
                ("ml_detection", "Ml Detections", ["computer_science"], "最大似然检测"),
                ("ml_estimator", "Ml Estimators", ["computer_science"], "最大似然估计量"),
                ("mlfma", "MLFMA", ["mathematics"], "多层快速多极子算法"),
                ("mlp_neural_network", "Mlp Neural Networks", ["computer_science"], "多层感知机神经网络"),
                ("mlst", "Mlst", ["computer_science"], "多位点序列分型"),
            ]
        )

    def test_exact_expansion_batch_437_adds_mmic_and_mobile_base_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mmic", "Mmics", ["circuits_and_systems"], "单片微波集成电路"),
                ("mmorpg", "Mmorpg", ["computer_science"], "大型多人在线角色扮演游戏"),
                ("mmpi", "MMPI", ["biomedical", "psychiatry_and_psychology"], "明尼苏达多项人格测验"),
                ("mnss_blood_group_system", "Mnss Blood-group System", ["biomedical", "chemicals_and_drugs"], "MNS血型系统"),
                ("mobile_ad_hoc_network", "Mobile Ad Hoc Networks", ["computer_science"], "移动自组织网络"),
                ("mobile_agent", "Mobile Agents", ["computer_science"], "移动智能体"),
                ("mobile_application", "Mobile Applications", ["computer_science"], "移动应用"),
            ]
        )

    def test_exact_expansion_batch_438_adds_mobile_application_and_computing_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mobile_application_development", "Mobile Application Development", ["computer_science"], "移动应用开发"),
                ("mobile_antenna", "Mobile Antennas", ["antennas_and_propagation"], "移动天线"),
                ("mobile_computing", "Mobile Computing", ["computer_science"], "移动计算"),
                ("mobile_crowdsensing_and_crowdsourcing", "Mobile Crowdsensing And Crowdsourcing", ["computer_science"], "移动群智感知与众包"),
                ("mobile_handheld_devic", "Mobile Handheld Devices", ["computer_science"], "移动手持设备"),
                ("mobile_handset", "Mobile Handsets", ["computer_science"], "移动终端"),
                ("mobile_health_unit", "Mobile Health Units", ["biomedical", "health_care"], "流动医疗单位"),
            ]
        )

    def test_exact_expansion_batch_439_adds_mobile_interaction_and_phone_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mobile_interaction", "Mobile Interaction", ["computer_science"], "移动交互"),
                ("mobile_learning", "Mobile Learning", ["computer_science"], "移动学习"),
                ("mobile_manipulation", "Mobile Manipulation", ["computer_science"], "移动操作"),
                ("mobile_operating_system", "Mobile Operating Systems", ["computer_science"], "移动操作系统"),
                ("mobile_payment", "Mobile Payment", ["computer_science"], "移动支付"),
                ("mobile_phone", "Mobile Phone", ["computer_science"], "手机"),
                ("mobile_phone_application", "Mobile Phone Applications", ["computer_science"], "手机应用"),
            ]
        )

    def test_exact_expansion_batch_440_adds_mobile_robot_and_terminal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mobile_phone_camera", "Mobile Phone Cameras", ["computer_science"], "手机摄像头"),
                ("mobile_phone_user", "Mobile-phone Users", ["computer_science"], "手机用户"),
                ("mobile_robot", "Mobile Robots", ["robotics_and_automation"], "移动机器人"),
                ("mobile_security", "Mobile Security", ["computer_science"], "移动安全"),
                ("mobile_sink", "Mobile Sink", ["computer_science"], "移动汇聚节点"),
                ("mobile_system", "Mobile Systems", ["computer_science"], "移动系统"),
                ("mobile_terminal", "Mobile Terminal", ["computer_science"], "移动终端"),
            ]
        )


if __name__ == "__main__":
    unittest.main()


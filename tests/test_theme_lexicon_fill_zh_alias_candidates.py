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
        self.assertEqual(rows["concept:protein"]["zh_alias_candidates"], [])
        self.assertEqual(rows["concept:adrenergic_fiber"]["zh_alias_candidates"], [])
        self.assertEqual(summary["records_filled"], 3)

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
        self.assertEqual(rows["concept:protein"]["zh_alias_candidates"], [])
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
        self.assertEqual(summary["records_filled"], 12)

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
        self.assertEqual(rows["concept:acid_sensing_ion_channel"]["zh_alias_candidates"][0]["alias"], "酸感知离子通道")
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

    def test_long_biomedical_class_suffixes_are_review_gated_not_runtime_accepted(self) -> None:
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
            "氨基酸肽与蛋白",
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


if __name__ == "__main__":
    unittest.main()



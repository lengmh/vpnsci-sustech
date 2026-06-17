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


if __name__ == "__main__":
    unittest.main()


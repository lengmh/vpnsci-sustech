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

    def test_exact_expansion_batch_441_adds_mobile_telecom_and_mobility_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mobile_telecommunication_system", "Mobile Telecommunication Systems", ["computer_science"], "移动通信系统"),
                ("mobile_tv", "Mobile TV", ["communications_technology"], "移动电视"),
                ("mobile_web", "Mobile Web", ["computer_science"], "移动Web"),
                ("mobile_wimax", "Mobile Wimax", ["computer_science"], "移动WiMAX"),
                ("mobility_analysi", "Mobility Analysis", ["computer_science"], "移动性分析"),
                ("mobility_as_a_service", "Mobility As A Service", ["computers_and_information_processing"], "出行即服务"),
                ("mobility_limitation", "Mobility Limitation", ["biomedical", "diseases"], "活动受限"),
            ]
        )

    def test_exact_expansion_batch_442_adds_mobility_management_and_anatomic_model_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mobility_management", "Mobility Management", ["computer_science"], "移动性管理"),
                ("mobility_management_protocol", "Mobility Management Protocol", ["computer_science"], "移动性管理协议"),
                ("mobility_management_scheme", "Mobility Management Scheme", ["computer_science"], "移动性管理方案"),
                ("mobility_model", "Mobility Models", ["computer_science"], "移动性模型"),
                ("mobility_modeling", "Mobility Modeling", ["computer_science"], "移动性建模"),
                ("mobility_pattern", "Mobility Pattern", ["computer_science"], "移动模式"),
                ("mobiluncu", "Mobiluncus", ["biomedical", "organisms"], "动弯杆菌属"),
                ("model_anatomic", "Models, Anatomic", ["biomedical"], "解剖模型"),
            ]
        )

    def test_exact_expansion_batch_443_adds_model_checking_and_biomed_model_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("model_animal", "Models, Animal", ["biomedical"], "动物模型"),
                ("model_based_system_engineering", "Model-based Systems Engineering", ["computer_science"], "基于模型的系统工程"),
                ("model_based_testing", "Model Based Testing", ["computer_science"], "基于模型的测试"),
                ("model_biological", "Models, Biological", ["biomedical"], "生物模型"),
                ("model_biopsychosocial", "Models, Biopsychosocial", ["biomedical"], "生物心理社会模型"),
                ("model_cardiovascular", "Models, Cardiovascular", ["biomedical"], "心血管模型"),
                ("model_checker", "Model Checker", ["computer_science"], "模型检测器"),
                ("model_checking", "Model Checking", ["computer_science"], "模型检测"),
            ]
        )

    def test_exact_expansion_batch_444_adds_model_checking_tools_and_compression_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("model_checking_algorithm", "Model Checking Algorithm", ["computer_science"], "模型检测算法"),
                ("model_checking_problem", "Model Checking Problem", ["computer_science"], "模型检测问题"),
                ("model_checking_techniqu", "Model-checking Techniques", ["computer_science"], "模型检测技术"),
                ("model_checking_tool", "Model Checking Tools", ["computer_science"], "模型检测工具"),
                ("model_chemical", "Models, Chemical", ["biomedical"], "化学模型"),
                ("model_compression", "Model Compression", ["computer_science"], "模型压缩"),
                ("model_dental", "Models, Dental", ["biomedical"], "牙科模型"),
            ]
        )

    def test_exact_expansion_batch_445_adds_model_driven_and_economic_model_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("model_driven_architecture", "Model Driven Architecture", ["computer_science"], "模型驱动架构"),
                ("model_driven_development", "Model-driven Development", ["computer_science"], "模型驱动开发"),
                ("model_driven_software_development", "Model-driven Software Development", ["computer_science"], "模型驱动软件开发"),
                ("model_driven_software_engineering_techniqu", "Model-driven Software Engineering Techniques", ["computer_science"], "模型驱动软件工程技术"),
                ("model_econometric", "Models, Econometric", ["biomedical"], "计量经济模型"),
                ("model_economic", "Models, Economic", ["computer_science"], "经济模型"),
                ("model_educational", "Models, Educational", ["computer_science"], "教育模型"),
            ]
        )

    def test_exact_expansion_batch_446_adds_genetic_molecular_and_reference_model_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("model_genetic", "Models, Genetic", ["biomedical"], "遗传模型"),
                ("model_immunological", "Models, Immunological", ["biomedical"], "免疫学模型"),
                ("model_languag", "Model Languages", ["computer_science"], "模型语言"),
                ("model_molecular", "Models, Molecular", ["biomedical"], "分子模型"),
                ("model_neurological", "Models, Neurological", ["biomedical"], "神经学模型"),
                ("model_reference_adaptive_control", "Model Reference Adaptive Control", ["computer_science"], "模型参考自适应控制"),
                ("model_reference_adaptive_system", "Model Reference Adaptive System", ["computer_science"], "模型参考自适应系统"),
            ]
        )

    def test_exact_expansion_batch_447_adds_psychological_statistical_and_transformation_model_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("model_psychological", "Models, Psychological", ["biomedical"], "心理模型"),
                ("model_spatial_interaction", "Models, Spatial Interaction", ["biomedical"], "空间相互作用模型"),
                ("model_statistical", "Models, Statistical", ["computer_science"], "统计模型"),
                ("model_structural", "Models, Structural", ["biomedical"], "结构模型"),
                ("model_theoretical", "Models, Theoretical", ["biomedical"], "理论模型"),
                ("model_to_model_transformation", "Model To Model Transformation", ["computer_science"], "模型到模型转换"),
                ("model_transformation", "Model Transformation", ["computer_science"], "模型转换"),
                ("model_validation", "Model Validation", ["computer_science"], "模型验证"),
            ]
        )

    def test_exact_expansion_batch_448_adds_mvc_modem_and_modular_math_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("model_view_controller", "Model View Controller", ["computer_science"], "模型-视图-控制器"),
                ("modeling_language", "Modeling Language", ["computer_science"], "建模语言"),
                ("modem", "Modems", ["communications_technology", "computer_science"], "调制解调器"),
                ("modern_logistic", "Modern Logistics", ["computer_science"], "现代物流"),
                ("modified_differential_evolution", "Modified Differential Evolution", ["computer_science"], "改进差分进化"),
                ("modul_abstract_algebra", "Modules (abstract Algebra)", ["mathematics"], "抽象代数模"),
                ("modular_construction", "Modular Construction", ["industry_applications"], "模块化建造"),
                ("modular_exponentiation", "Modular Exponentiation", ["computer_science"], "模幂运算"),
            ]
        )

    def test_exact_expansion_batch_449_adds_modular_modulation_and_molecular_beam_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("modular_multiplication", "Modular Multiplication", ["computer_science"], "模乘"),
                ("modular_robot", "Modular Robots", ["computer_science"], "模块化机器人"),
                ("modular_robotic", "Modular Robotics", ["computer_science"], "模块化机器人学"),
                ("modulation", "Modulation", ["communications_technology"], "调制"),
                ("modulation_and_coding_schem", "Modulation And Coding Schemes", ["computer_science"], "调制编码方案"),
                ("modulation_coding", "Modulation Coding", ["communications_technology"], "调制编码"),
                ("modulo_scheduling", "Modulo Scheduling", ["computer_science"], "模调度"),
                ("molecular_beam", "Molecular Beams", ["science_general"], "分子束"),
            ]
        )

    def test_exact_expansion_batch_450_adds_molecular_biology_and_chaperone_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("molecular_biology", "Molecular Biology", ["biomedical"], "分子生物学"),
                ("molecular_biology_techniqu_and_application", "Molecular Biology Techniques And Applications", ["life_sciences"], "分子生物学技术与应用"),
                ("molecular_biomarker", "Molecular Biomarkers", ["systems_man_and_cybernetics"], "分子生物标志物"),
                ("molecular_biophysic", "Molecular Biophysics", ["science_general"], "分子生物物理学"),
                ("molecular_chaperon", "Molecular Chaperones", ["biomedical", "chemicals_and_drugs"], "分子伴侣"),
                ("molecular_communication", "Molecular Communication", ["communications_technology"], "分子通信"),
                ("molecular_communication_and_nanonetwork", "Molecular Communication And Nanonetworks", ["engineering"], "分子通信与纳米网络"),
            ]
        )

    def test_exact_expansion_batch_451_adds_molecular_computing_diagnostic_and_epidemiology_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("molecular_computing", "Molecular Computing", ["computer_science"], "分子计算"),
                ("molecular_conformation", "Molecular Conformation", ["biomedical"], "分子构象"),
                ("molecular_diagnostic_techniqu", "Molecular Diagnostic Techniques", ["biomedical"], "分子诊断技术"),
                ("molecular_docking_simulation", "Molecular Docking Simulation", ["biomedical"], "分子对接模拟"),
                ("molecular_electronic", "Molecular Electronics", ["nanotechnology"], "分子电子学"),
                ("molecular_epidemiology", "Molecular Epidemiology", ["biomedical"], "分子流行病学"),
                ("molecular_farming", "Molecular Farming", ["biomedical"], "分子农业"),
            ]
        )

    def test_exact_expansion_batch_452_adds_molecular_imaging_and_medicine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("molecular_imaging", "Molecular Imaging", ["imaging"], "分子成像"),
                ("molecular_imprinting", "Molecular Imprinting", ["biomedical"], "分子印迹"),
                ("molecular_mechanism_of_pharmacological_action", "Molecular Mechanisms Of Pharmacological Action", ["biomedical"], "药理作用分子机制"),
                ("molecular_medicine", "Molecular Medicine", ["biomedical"], "分子医学"),
                ("molecular_mimicry", "Molecular Mimicry", ["biomedical"], "分子拟态"),
                ("molecular_motor_protein", "Molecular Motor Proteins", ["biomedical", "chemicals_and_drugs"], "分子马达蛋白"),
                ("molecular_network", "Molecular Networks", ["quantitative_biology"], "分子网络"),
            ]
        )

    def test_exact_expansion_batch_453_adds_molecular_probe_sequence_and_structure_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("molecular_prob", "Molecular Probes", ["biomedical", "chemicals_and_drugs"], "分子探针"),
                ("molecular_probe_techniqu", "Molecular Probe Techniques", ["biomedical"], "分子探针技术"),
                ("molecular_sequence_annotation", "Molecular Sequence Annotation", ["biomedical"], "分子序列注释"),
                ("molecular_sequence_data", "Molecular Sequence Data", ["biomedical", "information_science"], "分子序列数据"),
                ("molecular_structure", "Molecular Structure", ["biomedical"], "分子结构"),
                ("molecular_targeted_therapy", "Molecular Targeted Therapy", ["biomedical"], "分子靶向治疗"),
                ("molecular_typing", "Molecular Typing", ["biomedical"], "分子分型"),
                ("molecular_weight", "Molecular Weight", ["biomedical"], "分子量"),
            ]
        )

    def test_exact_expansion_batch_454_adds_molecularly_imprinted_monitoring_and_morphine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("molecularly_imprinted_polymer", "Molecularly Imprinted Polymers", ["biomedical", "chemicals_and_drugs"], "分子印迹聚合物"),
                ("monitoring", "Monitoring", ["instrumentation_and_measurement"], "监测"),
                ("monitoring_ambulatory", "Monitoring, Ambulatory", ["biomedical"], "动态监测"),
                ("monitoring_intraoperative", "Monitoring, Intraoperative", ["biomedical"], "术中监测"),
                ("monitoring_physiologic", "Monitoring, Physiologic", ["biomedical"], "生理监测"),
                ("monoclonal_gammopathy_of_undetermined_significance", "Monoclonal Gammopathy Of Undetermined Significance", ["biomedical", "diseases"], "意义未明单克隆免疫球蛋白血症"),
                ("morphinan", "Morphinans", ["biomedical", "chemicals_and_drugs"], "吗啡烷类"),
                ("morphine", "Morphine", ["biomedical", "chemicals_and_drugs"], "吗啡"),
            ]
        )

    def test_exact_expansion_batch_455_adds_morphine_morphogenesis_and_morphological_filter_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("morphine_dependence", "Morphine Dependence", ["biomedical", "diseases"], "吗啡依赖"),
                ("morphine_derivativ", "Morphine Derivatives", ["biomedical", "chemicals_and_drugs"], "吗啡衍生物"),
                ("morphodynamic", "Morphodynamics", ["computer_science"], "形态动力学"),
                ("morphogenesi", "Morphogenesis", ["biomedical"], "形态发生"),
                ("morpholin", "Morpholines", ["biomedical", "chemicals_and_drugs"], "吗啉类"),
                ("morpholino", "Morpholinos", ["biomedical", "chemicals_and_drugs"], "吗啉代寡核苷酸"),
                ("morphological_filter", "Morphological Filter", ["computer_science"], "形态滤波器"),
                ("morphological_filtering", "Morphological Filtering", ["computer_science"], "形态滤波"),
            ]
        )

    def test_exact_expansion_batch_456_adds_morphological_mouse_and_moving_object_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("morphological_operation", "Morphological Operations", ["computer_science"], "形态学运算"),
                ("morphological_operator", "Morphological Operator", ["computer_science"], "形态算子"),
                ("mouse_embryonic_stem_cell", "Mouse Embryonic Stem Cells", ["biomedical"], "小鼠胚胎干细胞"),
                ("movement", "Movement", ["biomedical"], "运动"),
                ("moving_and_lifting_patient", "Moving And Lifting Patients", ["biomedical", "health_care"], "患者搬运与抬移"),
                ("moving_least_squar", "Moving Least Squares", ["computer_science"], "移动最小二乘"),
                ("moving_object", "Moving Object", ["computer_science"], "运动物体"),
                ("moving_object_segmentation", "Moving Object Segmentation", ["computer_science"], "运动目标分割"),
            ]
        )

    def test_exact_expansion_batch_457_adds_moving_target_and_multi_agent_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("moving_object_tracking", "Moving Object Tracking", ["computer_science"], "运动目标跟踪"),
                ("moving_obstacl", "Moving Obstacles", ["computer_science"], "移动障碍物"),
                ("moving_platform", "Moving Platform", ["computer_science"], "移动平台"),
                ("moving_target", "Moving Target", ["computer_science"], "移动目标"),
                ("moving_target_detection", "Moving Target Detection", ["computer_science"], "移动目标检测"),
                ("moving_target_tracking", "Moving Target Tracking", ["computer_science"], "移动目标跟踪"),
                ("multi_access_edge_computing", "Multi-access Edge Computing", ["computers_and_information_processing"], "多接入边缘计算"),
                ("multi_agent_approach", "Multi-agent Approach", ["computer_science"], "多智能体方法"),
            ]
        )

    def test_exact_expansion_batch_458_adds_multi_agent_antenna_and_bandit_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_agent_system", "Multi-agent Systems", ["systems_engineering_and_theory"], "多智能体系统"),
                ("multi_agent_system_and_negotiation", "Multi-agent Systems And Negotiation", ["computer_science"], "多智能体系统与协商"),
                ("multi_antenna", "Multi-antenna", ["computer_science"], "多天线"),
                ("multi_antenna_relay", "Multi-antenna Relay", ["computer_science"], "多天线中继"),
                ("multi_antenna_system", "Multi-antenna Systems", ["computer_science"], "多天线系统"),
                ("multi_armed_bandit_problem", "Multi-armed Bandit Problem", ["computer_science"], "多臂老虎机问题"),
                ("multi_band_orthogonal_frequency_division_multiplex", "Multi-band Orthogonal Frequency Division Multiplex", ["computer_science"], "多频带正交频分复用"),
            ]
        )

    def test_exact_expansion_batch_459_adds_multibeam_multibody_and_multicarrier_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_beam", "Multi-beam", ["computer_science"], "多波束"),
                ("multi_body_system_mbs", "Multi-body System (mbs)", ["computer_science"], "多体系统"),
                ("multi_carrier", "Multi Carrier", ["computer_science"], "多载波"),
                ("multi_carrier_code_division_multiple_access_system", "Multi Carrier Code-division Multiple-access System", ["computer_science"], "多载波码分多址系统"),
                ("multi_carrier_system", "Multi Carrier Systems", ["computer_science"], "多载波系统"),
                ("multi_carrier_transmission", "Multi Carrier Transmission", ["computer_science"], "多载波传输"),
                ("multi_channel_mac", "Multi-channel Mac", ["computer_science"], "多信道MAC"),
                ("multi_channel_mac_protocol", "Multi-channel Mac Protocols", ["computer_science"], "多信道MAC协议"),
            ]
        )

    def test_exact_expansion_batch_460_adds_multiclass_multicore_and_multicriteria_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_class_classification", "Multi-class Classification", ["computer_science"], "多类分类"),
                ("multi_class_classifier", "Multi-class Classifier", ["computer_science"], "多类分类器"),
                ("multi_core", "Multi Core", ["computer_science"], "多核"),
                ("multi_core_architectur", "Multi-core Architectures", ["computer_science"], "多核架构"),
                ("multi_core_processor", "Multi-core Processor", ["computer_science"], "多核处理器"),
                ("multi_core_system", "Multi-core Systems", ["computer_science"], "多核系统"),
                ("multi_criteria_decision_analysi", "Multi-criteria Decision Analysis", ["computer_science"], "多准则决策分析"),
                ("multi_criteria_decision_making", "Multi-criteria Decision Making", ["computer_science"], "多准则决策"),
            ]
        )

    def test_exact_expansion_batch_461_adds_multilabel_multimodal_and_multiobject_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_label_classification", "Multi Label Classification", ["computer_science"], "多标签分类"),
                ("multi_layer_neural_network", "Multi-layer Neural Network", ["computer_science"], "多层神经网络"),
                ("multi_modal_biometric", "Multi-modal Biometrics", ["computer_science"], "多模态生物识别"),
                ("multi_modal_interaction", "Multi-modal Interactions", ["computer_science"], "多模态交互"),
                ("multi_modal_interfac", "Multi-modal Interfaces", ["computer_science"], "多模态界面"),
                ("multi_mode_interference", "Multi-mode Interference", ["computer_science"], "多模干涉"),
                ("multi_object_tracking", "Multi-object Tracking", ["computer_science"], "多目标跟踪"),
            ]
        )

    def test_exact_expansion_batch_462_adds_multiobjective_algorithm_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_objective_algorithm", "Multi Objective Algorithm", ["computer_science"], "多目标算法"),
                ("multi_objective_differential_evolution", "Multi-objective Differential Evolutions", ["computer_science"], "多目标差分进化"),
                ("multi_objective_evolutionary_algorithm", "Multi-objective Evolutionary Algorithm", ["computer_science"], "多目标进化算法"),
                ("multi_objective_genetic_algorithm", "Multi-objective Genetic Algorithm", ["computer_science"], "多目标遗传算法"),
                ("multi_objective_learning", "Multi-objective Learning", ["computer_science"], "多目标学习"),
                ("multi_objective_optimisation", "Multi-objective Optimisation", ["computer_science"], "多目标优化"),
                ("multi_objective_optimization_model", "Multi-objective Optimization Models", ["computer_science"], "多目标优化模型"),
                ("multi_objective_optimization_problem", "Multi-objective Optimization Problem", ["computer_science"], "多目标优化问题"),
            ]
        )

    def test_exact_expansion_batch_463_adds_multiparty_and_multipath_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_objective_particle_swarm_optimization", "Multi Objective Particle Swarm Optimization", ["computer_science"], "多目标粒子群优化"),
                ("multi_objective_problem", "Multi-objective Problem", ["computer_science"], "多目标问题"),
                ("multi_objective_programming", "Multi-objective Programming", ["computer_science"], "多目标规划"),
                ("multi_party_computation", "Multi-party Computation", ["computer_science"], "多方计算"),
                ("multi_path_fading_channel", "Multi-path Fading Channels", ["computer_science"], "多径衰落信道"),
                ("multi_path_interference", "Multi-path Interference", ["computer_science"], "多径干扰"),
                ("multi_path_mitigation", "Multi-path Mitigation", ["computer_science"], "多径缓解"),
                ("multi_path_routing", "Multi Path Routing", ["computer_science"], "多路径路由"),
            ]
        )

    def test_exact_expansion_batch_464_adds_multiprocessor_mpls_and_multiresolution_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_processor", "Multi-processors", ["computer_science"], "多处理器"),
                ("multi_processor_architecture", "Multi Processor Architecture", ["computer_science"], "多处理器架构"),
                ("multi_processor_platform", "Multi-processor Platforms", ["computer_science"], "多处理器平台"),
                ("multi_processor_scheduling", "Multi Processor Scheduling", ["computer_science"], "多处理器调度"),
                ("multi_processor_system", "Multi Processor Systems", ["computer_science"], "多处理器系统"),
                ("multi_protocol_label_switching", "Multi Protocol Label Switching", ["computer_science"], "多协议标签交换"),
                ("multi_resolution_analysi", "Multi-resolution Analysis", ["computer_science"], "多分辨率分析"),
                ("multi_resolution_decomposition", "Multi Resolution Decomposition", ["computer_science"], "多分辨率分解"),
            ]
        )

    def test_exact_expansion_batch_465_adds_multirobot_and_multisensor_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_resolution_representation", "Multi Resolution Representation", ["computer_science"], "多分辨率表示"),
                ("multi_robot", "Multi-robot", ["computer_science"], "多机器人"),
                ("multi_robot_cooperation", "Multi-robot Cooperation", ["computer_science"], "多机器人协作"),
                ("multi_robot_coordination", "Multi-robot Coordination", ["computer_science"], "多机器人协调"),
                ("multi_robot_exploration", "Multi-robot Exploration", ["computer_science"], "多机器人探索"),
                ("multi_robot_system", "Multi-robot Systems", ["robotics_and_automation"], "多机器人系统"),
                ("multi_robot_team", "Multi-robot Teams", ["computer_science"], "多机器人团队"),
                ("multi_sensor", "Multi Sensor", ["computer_science"], "多传感器"),
            ]
        )

    def test_exact_expansion_batch_466_adds_multisensor_multiserver_and_multispectral_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_sensor_data", "Multi-sensor Data", ["computer_science"], "多传感器数据"),
                ("multi_sensor_data_fusion", "Multi-sensor Data Fusion", ["computer_science"], "多传感器数据融合"),
                ("multi_sensor_imag", "Multi Sensor Images", ["computer_science"], "多传感器图像"),
                ("multi_sensor_information_fusion", "Multi-sensor Information Fusion", ["computer_science"], "多传感器信息融合"),
                ("multi_sensor_system", "Multi-sensor Systems", ["computer_science"], "多传感器系统"),
                ("multi_server", "Multi-server", ["computer_science"], "多服务器"),
                ("multi_signature", "Multi-signature", ["computer_science"], "多重签名"),
                ("multi_spectral_imaging", "Multi-spectral Imaging", ["computer_science"], "多光谱成像"),
            ]
        )

    def test_exact_expansion_batch_467_adds_multitarget_multitemporal_and_multitenancy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_spectral_imaging_system", "Multi-spectral Imaging Systems", ["computer_science"], "多光谱成像系统"),
                ("multi_standard", "Multi-standard", ["computer_science"], "多标准"),
                ("multi_target", "Multi-target", ["computer_science"], "多目标"),
                ("multi_target_tracking", "Multi-target Tracking", ["computer_science"], "多目标跟踪"),
                ("multi_temporal", "Multi-temporal", ["computer_science"], "多时相"),
                ("multi_temporal_image", "Multi-temporal Image", ["computer_science"], "多时相图像"),
                ("multi_temporal_remote_sensing", "Multi-temporal Remote Sensing", ["computer_science"], "多时相遥感"),
                ("multi_tenancy", "Multi-tenancy", ["computer_science"], "多租户"),
            ]
        )

    def test_exact_expansion_batch_468_adds_multithread_multitier_and_multiuser_detection_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_thread", "Multi-thread", ["computer_science"], "多线程"),
                ("multi_threaded", "Multi-threaded", ["computer_science"], "多线程"),
                ("multi_threaded_application", "Multi-threaded Application", ["computer_science"], "多线程应用"),
                ("multi_threading", "Multi-threading", ["computer_science"], "多线程"),
                ("multi_tier", "Multi-tier", ["computer_science"], "多层"),
                ("multi_tier_application", "Multi-tier Applications", ["computer_science"], "多层应用"),
                ("multi_user_detection", "Multi-user Detection", ["computer_science"], "多用户检测"),
                ("multi_user_diversity", "Multi-user Diversity", ["computer_science"], "多用户分集"),
            ]
        )

    def test_exact_expansion_batch_469_adds_multiuser_mimo_and_multiview_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_user_interference", "Multi-user Interference", ["computer_science"], "多用户干扰"),
                ("multi_user_mimo", "Multi-user Mimo", ["computer_science"], "多用户MIMO"),
                ("multi_user_mimo_downlink", "Multi-user Mimo Downlinks", ["computer_science"], "多用户MIMO下行链路"),
                ("multi_user_mimo_system", "Multi-user Mimo Systems", ["computer_science"], "多用户MIMO系统"),
                ("multi_user_virtual_environment", "Multi-user Virtual Environment", ["computer_science"], "多用户虚拟环境"),
                ("multi_view", "Multi-view", ["computer_science"], "多视图"),
                ("multi_view_consistency", "Multi-view Consistency", ["computer_science"], "多视图一致性"),
                ("multi_view_learning", "Multi-view Learning", ["computer_science"], "多视图学习"),
            ]
        )

    def test_exact_expansion_batch_470_adds_multiview_multiaccess_and_multicarrier_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multi_view_stereo", "Multi-view Stereo", ["computer_science"], "多视图立体"),
                ("multi_wavelet", "Multi-wavelets", ["computer_science"], "多小波"),
                ("multiaccess_communication", "Multiaccess Communication", ["communications_technology"], "多址通信"),
                ("multiagent_architecture", "Multiagent Architecture", ["computer_science"], "多智能体架构"),
                ("multiagent_framework", "Multiagent Framework", ["computer_science"], "多智能体框架"),
                ("multiband_ofdm", "Multiband Ofdm", ["computer_science"], "多频带OFDM"),
                ("multibeam_antenna", "Multibeam Antennas", ["computer_science"], "多波束天线"),
                ("multicarrier_code_division_multiple_access", "Multicarrier Code Division Multiple Access", ["computer_science"], "多载波码分多址"),
            ]
        )

    def test_exact_expansion_batch_471_adds_multicast_basic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multicarrier_modulation", "Multicarrier Modulation", ["computer_science"], "多载波调制"),
                ("multicast_algorithm", "Multicast Algorithms", ["computer_science"], "组播算法"),
                ("multicast_application", "Multicast Application", ["computer_science"], "组播应用"),
                ("multicast_capacity", "Multicast Capacity", ["computer_science"], "组播容量"),
                ("multicast_communication", "Multicast Communication", ["computer_science"], "组播通信"),
                ("multicast_data", "Multicast Data", ["computer_science"], "组播数据"),
                ("multicast_network", "Multicast Network", ["computer_science"], "组播网络"),
                ("multicast_packet", "Multicast Packet", ["computer_science"], "组播数据包"),
            ]
        )

    def test_exact_expansion_batch_472_adds_multicast_routing_and_traffic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multicast_protocol", "Multicast Protocols", ["computer_science"], "组播协议"),
                ("multicast_routing", "Multicast Routing", ["computer_science"], "组播路由"),
                ("multicast_routing_algorithm", "Multicast Routing Algorithms", ["computer_science"], "组播路由算法"),
                ("multicast_routing_protocol", "Multicast Routing Protocol", ["computer_science"], "组播路由协议"),
                ("multicast_scheduling", "Multicast Scheduling", ["computer_science"], "组播调度"),
                ("multicast_session", "Multicast Sessions", ["computer_science"], "组播会话"),
                ("multicast_traffic", "Multicast Traffic", ["computer_science"], "组播流量"),
                ("multicast_vpn", "Multicast VPN", ["communications_technology"], "组播VPN"),
            ]
        )

    def test_exact_expansion_batch_473_adds_multicenter_multichip_and_multicomponent_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multicell_system", "Multicell System", ["computer_science"], "多小区系统"),
                ("multicenter_study", "Multicenter Study", ["biomedical"], "多中心研究"),
                ("multicenter_study_as_topic", "Multicenter Studies As Topic", ["biomedical"], "多中心研究主题"),
                ("multichip_modul", "Multichip Modules", ["computer_science"], "多芯片模块"),
                ("multiclass_classification_problem", "Multiclass Classification Problems", ["computer_science"], "多类分类问题"),
                ("multicomponent_signal", "Multicomponent Signals", ["computer_science"], "多分量信号"),
                ("multicomponent_synthesi_of_heterocycl", "Multicomponent Synthesis Of Heterocycles", ["chemistry"], "杂环多组分合成"),
                ("multicomponent_system", "Multicomponent Systems", ["physics"], "多组分系统"),
            ]
        )

    def test_exact_expansion_batch_474_adds_multicore_multidetector_and_multidimensional_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multicomputer", "Multicomputers", ["computer_science"], "多计算机"),
                ("multicore_processing", "Multicore Processing", ["computer_science"], "多核处理"),
                ("multicore_programming", "Multicore Programming", ["computer_science"], "多核编程"),
                ("multicystic_dysplastic_kidney", "Multicystic Dysplastic Kidney", ["biomedical", "diseases"], "多囊性发育不良肾"),
                ("multidetector_computed_tomography", "Multidetector Computed Tomography", ["biomedical"], "多层探测器CT"),
                ("multidimensional_scaling_analysi", "Multidimensional Scaling Analysis", ["biomedical"], "多维尺度分析"),
                ("multidimensional_signal_processing", "Multidimensional Signal Processing", ["signal_processing"], "多维信号处理"),
                ("multidimensional_system", "Multidimensional Systems", ["systems_engineering_and_theory"], "多维系统"),
            ]
        )

    def test_exact_expansion_batch_475_adds_multidrug_multienzyme_and_multiferroic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multidisciplinary_design_optimization", "Multidisciplinary Design Optimization", ["computer_science"], "多学科设计优化"),
                ("multidrug_resistance_associated_protein_2", "Multidrug Resistance-associated Protein 2", ["biomedical", "chemicals_and_drugs"], "多药耐药相关蛋白2"),
                ("multienzyme_complexe", "Multienzyme Complexes", ["biomedical", "chemicals_and_drugs"], "多酶复合物"),
                ("multifactor_dimensionality_reduction", "Multifactor Dimensionality Reduction", ["biomedical"], "多因子降维"),
                ("multifactorial_inheritance", "Multifactorial Inheritance", ["biomedical"], "多因素遗传"),
                ("multiferroic_and_related_material", "Multiferroics And Related Materials", ["materials_science"], "多铁性及相关材料"),
                ("multifilamentary_superconductor", "Multifilamentary Superconductors", ["superconductivity"], "多丝超导体"),
                ("multifingered_hand", "Multifingered Hands", ["computer_science"], "多指手"),
            ]
        )

    def test_exact_expansion_batch_476_adds_multifocal_multifunctional_and_multigrid_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multifocal_choroiditi", "Multifocal Choroiditis", ["biomedical", "diseases"], "多灶性脉络膜炎"),
                ("multifocal_intraocular_lense", "Multifocal Intraocular Lenses", ["biomedical"], "多焦点人工晶状体"),
                ("multifrequency_antenna", "Multifrequency Antennas", ["antennas_and_propagation"], "多频天线"),
                ("multifunctional_enzym", "Multifunctional Enzymes", ["biomedical", "chemicals_and_drugs"], "多功能酶"),
                ("multifunctional_nanoparticl", "Multifunctional Nanoparticles", ["biomedical"], "多功能纳米颗粒"),
                ("multigene_family", "Multigene Family", ["biomedical"], "多基因家族"),
                ("multigraph", "Multigraph", ["computer_science"], "多重图"),
                ("multigrid_method", "Multigrid Methods", ["mathematics"], "多重网格法"),
            ]
        )

    def test_exact_expansion_batch_477_adds_multihop_multilayer_and_multilevel_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multihop_transmission", "Multihop Transmission", ["computer_science"], "多跳传输"),
                ("multilayer_and_multiplex_network", "Multilayer & Multiplex Networks", ["physics"], "多层与多重网络"),
                ("multilayer_perceptron", "Multilayer Perceptrons", ["computer_science"], "多层感知机"),
                ("multilevel_analysi", "Multilevel Analysis", ["biomedical"], "多层次分析"),
                ("multilevel_converter", "Multilevel Converters", ["power_electronics"], "多电平变换器"),
                ("multilevel_inverter", "Multilevel Inverters", ["power_electronics"], "多电平逆变器"),
                ("multilevel_system", "Multilevel Systems", ["systems_engineering_and_theory"], "多层系统"),
            ]
        )

    def test_exact_expansion_batch_478_adds_multilocus_and_multimedia_basic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multilocu_sequence_typing", "Multilocus Sequence Typing", ["biomedical"], "多位点序列分型"),
                ("multimedia", "Multimedia", ["computer_science"], "多媒体"),
                ("multimedia_communication", "Multimedia Communication", ["computer_science"], "多媒体通信"),
                ("multimedia_computing", "Multimedia Computing", ["consumer_electronics"], "多媒体计算"),
                ("multimedia_content", "Multimedia Content", ["computer_science"], "多媒体内容"),
                ("multimedia_courseware", "Multimedia Courseware", ["computer_science"], "多媒体课件"),
                ("multimedia_data", "Multimedia Data", ["computer_science"], "多媒体数据"),
                ("multimedia_database", "Multimedia Databases", ["consumer_electronics"], "多媒体数据库"),
            ]
        )

    def test_exact_expansion_batch_479_adds_multimedia_service_and_streaming_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multimedia_document", "Multimedia Documents", ["computer_science"], "多媒体文档"),
                ("multimedia_interactive_servic", "Multimedia Interactive Services", ["computer_science"], "多媒体交互服务"),
                ("multimedia_learning_system", "Multimedia Learning Systems", ["computer_science"], "多媒体学习系统"),
                ("multimedia_servic", "Multimedia Services", ["computer_science"], "多媒体服务"),
                ("multimedia_signal_processing", "Multimedia Signal Processing", ["computer_science"], "多媒体信号处理"),
                ("multimedia_stream", "Multimedia Stream", ["computer_science"], "多媒体流"),
                ("multimedia_streaming", "Multimedia Streaming", ["computer_science"], "多媒体流媒体"),
                ("multimedia_system", "Multimedia Systems", ["computer_science"], "多媒体系统"),
            ]
        )

    def test_exact_expansion_batch_480_adds_multimedia_technology_and_multimodal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multimedia_technology", "Multimedia Technologies", ["computer_science"], "多媒体技术"),
                ("multimodal_ai", "Multimodal Ai", ["computer_science"], "多模态AI"),
                ("multimodal_dialogue_system", "Multimodal Dialogue Systems", ["computer_science"], "多模态对话系统"),
                ("multimodal_image_registration", "Multimodal Image Registration", ["computer_science"], "多模态图像配准"),
                ("multimodal_imaging", "Multimodal Imaging", ["biomedical"], "多模态成像"),
                ("multimodal_sensor", "Multimodal Sensors", ["sensors"], "多模态传感器"),
                ("multimode_fiber", "Multimode Fibers", ["computer_science"], "多模光纤"),
                ("multimode_optical_fiber", "Multimode Optical Fibers", ["computer_science"], "多模光纤"),
            ]
        )

    def test_exact_expansion_batch_481_adds_multimorbidity_multiomics_and_multipath_channel_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multimorbidity", "Multimorbidity", ["biomedical", "health_care"], "多病共存"),
                ("multiobjective_combinatorial_optimization", "Multiobjective Combinatorial Optimization", ["computer_science"], "多目标组合优化"),
                ("multiobjective_model", "Multiobjective Models", ["computer_science"], "多目标模型"),
                ("multiomic", "Multiomics", ["biomedical"], "多组学"),
                ("multiparametric_magnetic_resonance_imaging", "Multiparametric Magnetic Resonance Imaging", ["biomedical"], "多参数磁共振成像"),
                ("multiparty_computation", "Multiparty Computation", ["computer_science"], "多方计算"),
                ("multipath_channel", "Multipath Channels", ["information_theory"], "多径信道"),
                ("multipath_environment", "Multipath Environments", ["computer_science"], "多径环境"),
            ]
        )

    def test_exact_expansion_batch_482_adds_multipath_multiphase_and_multiphysics_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multipath_error", "Multipath Error", ["computer_science"], "多径误差"),
                ("multipath_fading", "Multipath Fading", ["computer_science"], "多径衰落"),
                ("multipath_propagation", "Multipath Propagation", ["computer_science"], "多径传播"),
                ("multipath_routing_algorithm", "Multipath Routing Algorithms", ["computer_science"], "多路径路由算法"),
                ("multipath_routing_protocol", "Multipath Routing Protocols", ["computer_science"], "多路径路由协议"),
                ("multiphase_flow", "Multiphase Flows", ["physics"], "多相流"),
                ("multiphasic_screening", "Multiphasic Screening", ["biomedical"], "多相筛查"),
                ("multiphysic", "Multiphysics", ["systems_engineering_and_theory"], "多物理场"),
            ]
        )

    def test_exact_expansion_batch_483_adds_multiple_access_and_acyl_coenzyme_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multiple_access_interference", "Multiple Access Interference", ["computer_science"], "多址干扰"),
                ("multiple_access_relay_channel", "Multiple Access Relay Channel", ["computer_science"], "多址中继信道"),
                ("multiple_access_scheme", "Multiple Access Scheme", ["computer_science"], "多址接入方案"),
                ("multiple_acyl_coenzyme_a_dehydrogenase_deficiency", "Multiple Acyl Coenzyme A Dehydrogenase Deficiency", ["biomedical", "diseases"], "多酰基辅酶A脱氢酶缺乏症"),
                ("multiple_amputation_traumatic", "Multiple Amputations, Traumatic", ["biomedical", "diseases"], "多发性创伤性截肢"),
                ("multiple_antenna", "Multiple Antenna", ["computer_science"], "多天线"),
                ("multiple_attribute_decision_making_problem", "Multiple Attribute Decision Making Problems", ["computer_science"], "多属性决策问题"),
                ("multiple_beam", "Multiple Beam", ["computer_science"], "多波束"),
            ]
        )

    def test_exact_expansion_batch_484_adds_multiple_birth_carboxylase_and_endocrine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multiple_birth_offspring", "Multiple Birth Offspring", ["biomedical", "named_groups"], "多胎后代"),
                ("multiple_carboxylase_deficiency", "Multiple Carboxylase Deficiency", ["biomedical", "diseases"], "多羧化酶缺乏症"),
                ("multiple_chemical_sensitivity", "Multiple Chemical Sensitivity", ["biomedical", "diseases"], "多种化学物质敏感症"),
                ("multiple_chronic_condition", "Multiple Chronic Conditions", ["biomedical", "diseases"], "多种慢性病"),
                ("multiple_endocrine_neoplasia", "Multiple Endocrine Neoplasia", ["biomedical", "diseases"], "多发性内分泌腺瘤病"),
                ("multiple_endocrine_neoplasia_type_1", "Multiple Endocrine Neoplasia Type 1", ["biomedical", "diseases"], "1型多发性内分泌腺瘤病"),
                ("multiple_endocrine_neoplasia_type_2a", "Multiple Endocrine Neoplasia Type 2a", ["biomedical", "diseases"], "2A型多发性内分泌腺瘤病"),
                ("multiple_endocrine_neoplasia_type_2b", "Multiple Endocrine Neoplasia Type 2b", ["biomedical", "diseases"], "2B型多发性内分泌腺瘤病"),
            ]
        )

    def test_exact_expansion_batch_485_adds_mimo_multiple_instance_and_myeloma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multiple_hypothesi_tracking", "Multiple Hypothesis Tracking", ["computer_science"], "多假设跟踪"),
                ("multiple_input_multiple_output_channel", "Multiple-input Multiple-output Channels", ["computer_science"], "MIMO信道"),
                ("multiple_input_multiple_output_mimo_radar", "Multiple Input Multiple Output (mimo) Radars", ["computer_science"], "多输入多输出雷达"),
                ("multiple_input_multiple_output_mimo_system", "Multiple-input-multiple-output (mimo) Systems", ["computer_science"], "MIMO系统"),
                ("multiple_instance_learning_algorithm", "Multiple-instance Learning Algorithms", ["computer_science"], "多示例学习算法"),
                ("multiple_kernel", "Multiple Kernels", ["computer_science"], "多核"),
                ("multiple_lyapunov_function", "Multiple Lyapunov Function", ["computer_science"], "多Lyapunov函数"),
                ("multiple_myeloma_research_and_treatment", "Multiple Myeloma Research And Treatments", ["medicine"], "多发性骨髓瘤研究与治疗"),
            ]
        )

    def test_exact_expansion_batch_486_adds_multiple_sclerosis_signal_and_sulfatase_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multiple_receive_antenna", "Multiple Receive Antennas", ["computer_science"], "多接收天线"),
                ("multiple_regression", "Multiple Regression", ["computer_science"], "多元回归"),
                ("multiple_rout", "Multiple Routes", ["computer_science"], "多路径"),
                ("multiple_sclerosi_chronic_progressive", "Multiple Sclerosis, Chronic Progressive", ["biomedical", "diseases"], "慢性进展型多发性硬化"),
                ("multiple_sclerosi_relapsing_remitting", "Multiple Sclerosis, Relapsing-remitting", ["biomedical", "diseases"], "复发缓解型多发性硬化"),
                ("multiple_sclerosi_research_study", "Multiple Sclerosis Research Studies", ["medicine"], "多发性硬化研究"),
                ("multiple_signal_classification", "Multiple Signal Classification", ["computer_science"], "多重信号分类"),
                ("multiple_sulfatase_deficiency_disease", "Multiple Sulfatase Deficiency Disease", ["biomedical", "diseases"], "多种硫酸酯酶缺乏症"),
            ]
        )

    def test_exact_expansion_batch_487_adds_multiple_system_multiplex_and_trauma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multiple_system_atrophy", "Multiple System Atrophy", ["biomedical", "diseases"], "多系统萎缩"),
                ("multiple_thread", "Multiple Threads", ["computer_science"], "多线程"),
                ("multiple_transmit_antenna", "Multiple Transmit Antennas", ["computer_science"], "多发射天线"),
                ("multiple_trauma", "Multiple Trauma", ["biomedical", "diseases"], "多发伤"),
                ("multiplex_polymerase_chain_reaction", "Multiplex Polymerase Chain Reaction", ["biomedical"], "多重聚合酶链反应"),
                ("multiplex_radio_transmission", "Multiplex Radio Transmission", ["computer_science"], "多路无线电传输"),
                ("multiplexer", "Multiplexer", ["computer_science"], "多路复用器"),
                ("multiplexing", "Multiplexing", ["computer_science"], "多路复用"),
            ]
        )

    def test_exact_expansion_batch_488_adds_multiplexing_and_multiplication_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multiplexing_equipment", "Multiplexing Equipment", ["computer_science"], "多路复用设备"),
                ("multiplexing_frequency_division", "Multiplexing, Frequency Division", ["computer_science"], "频分复用"),
                ("multiplexing_gain", "Multiplexing Gains", ["computer_science"], "复用增益"),
                ("multiplexing_time_division", "Multiplexing, Time Division", ["computer_science"], "时分复用"),
                ("multiplication", "Multiplication", ["computer_science"], "乘法"),
                ("multiplicative_noise", "Multiplicative Noise", ["computer_science"], "乘性噪声"),
                ("multiplicative_updat", "Multiplicative Updates", ["computer_science"], "乘法更新"),
                ("multiplier", "Multiplier", ["computer_science"], "乘法器"),
            ]
        )

    def test_exact_expansion_batch_489_adds_multipotent_and_multiprocessor_interconnect_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multiplying_circuit", "Multiplying Circuits", ["circuits_and_systems"], "乘法电路"),
                ("multipole_matrix_element", "Multipole Matrix Elements", ["physics"], "多极矩阵元"),
                ("multipotent_stem_cell", "Multipotent Stem Cells", ["biomedical"], "多能干细胞"),
                ("multiprocessing_program", "Multiprocessing Programs", ["computer_science"], "多处理程序"),
                ("multiprocessing_system", "Multiprocessing Systems", ["computer_science"], "多处理系统"),
                ("multiprocessor_interconnection", "Multiprocessor Interconnection", ["computer_science"], "多处理器互连"),
                ("multiprocessor_interconnection_network", "Multiprocessor Interconnection Networks", ["communications_technology"], "多处理器互连网络"),
                ("multiprocessor_system_on_chip", "Multiprocessor System On Chips", ["computer_science"], "多处理器片上系统"),
            ]
        )

    def test_exact_expansion_batch_490_adds_multiprotein_multiresolution_and_multisensory_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multiprotein_complexe", "Multiprotein Complexes", ["biomedical", "chemicals_and_drugs"], "多蛋白复合物"),
                ("multiprotocol_label_switching", "Multiprotocol Label Switching", ["communications_technology"], "多协议标签交换"),
                ("multipurpose_robot", "Multipurpose Robots", ["computer_science"], "多用途机器人"),
                ("multiresolution_imag", "Multiresolution Images", ["computer_science"], "多分辨率图像"),
                ("multiresolution_mr", "Multiresolution (mr)", ["computer_science"], "多分辨率"),
                ("multisensory_perception_and_integration", "Multisensory Perception And Integration", ["psychology"], "多感觉感知与整合"),
                ("multisignature_scheme", "Multisignature Scheme", ["computer_science"], "多重签名方案"),
                ("multispectral_imaging", "Multispectral Imaging", ["imaging"], "多光谱成像"),
            ]
        )

    def test_exact_expansion_batch_491_adds_multistage_multistatic_and_multitask_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multistage_interconnection_network", "Multistage Interconnection Network", ["computer_science"], "多级互连网络"),
                ("multistatic_radar", "Multistatic Radar", ["computer_science"], "多基地雷达"),
                ("multistorey_building", "Multistorey Building", ["computer_science"], "多层建筑"),
                ("multitask_learning", "Multitask Learning", ["computer_science"], "多任务学习"),
                ("multitasking", "Multitasking", ["computer_science"], "多任务处理"),
                ("multitasking_behavior", "Multitasking Behavior", ["biomedical"], "多任务行为"),
                ("multithreaded_processor", "Multithreaded Processors", ["computer_science"], "多线程处理器"),
                ("multithreading", "Multithreading", ["computer_science"], "多线程"),
            ]
        )

    def test_exact_expansion_batch_492_adds_multiuser_multivalued_and_multivariate_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multiuser_channel", "Multiuser Channels", ["information_theory"], "多用户信道"),
                ("multiuser_detection", "Multiuser Detection", ["signal_processing"], "多用户检测"),
                ("multiuser_scheduling", "Multiuser Scheduling", ["computer_science"], "多用户调度"),
                ("multiuser_system", "Multiuser System", ["computer_science"], "多用户系统"),
                ("multivalued_logic", "Multivalued Logic", ["computer_science"], "多值逻辑"),
                ("multivariable_control", "Multivariable Control", ["computer_science"], "多变量控制"),
                ("multivariable_control_system", "Multivariable Control Systems", ["computer_science"], "多变量控制系统"),
                ("multivariate_analysi", "Multivariate Analysis", ["biomedical"], "多变量分析"),
            ]
        )

    def test_exact_expansion_batch_493_adds_multivesicular_munchausen_and_municipal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("multivesicular_body", "Multivesicular Bodies", ["biomedical"], "多囊泡体"),
                ("multivibrator", "Multivibrators", ["circuits_and_systems"], "多谐振荡器"),
                ("multiwave_mixing", "Multiwave Mixing", ["lasers_and_electrooptics"], "多波混频"),
                ("multiwavelength", "Multiwavelength", ["computer_science"], "多波长"),
                ("mummy", "Mummies", ["biomedical"], "木乃伊"),
                ("munchausen_syndrome", "Munchausen Syndrome", ["biomedical"], "孟乔森综合征"),
                ("munchausen_syndrome_by_proxy", "Munchausen Syndrome By Proxy", ["biomedical"], "代理型孟乔森综合征"),
                ("municipal_solid_waste_management", "Municipal Solid Waste Management", ["environmental_science"], "城市固体废物管理"),
            ]
        )

    def test_exact_expansion_batch_494_adds_muramic_murine_family_and_muon_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("muntjac", "Muntjacs", ["biomedical", "organisms"], "麂属"),
                ("muon_collider", "Muon Colliders", ["nuclear_and_plasma_sciences"], "μ子对撞机"),
                ("mupirocin", "Mupirocin", ["biomedical", "chemicals_and_drugs"], "莫匹罗星"),
                ("muramic_acid", "Muramic Acids", ["biomedical", "chemicals_and_drugs"], "胞壁酸"),
                ("muramidase", "Muramidase", ["biomedical", "chemicals_and_drugs"], "溶菌酶"),
                ("muramoylpentapeptide_carboxypeptidase", "Muramoylpentapeptide Carboxypeptidase", ["biomedical", "chemicals_and_drugs"], "胞壁酰五肽羧肽酶"),
                ("muridae", "Muridae", ["biomedical", "organisms"], "鼠科"),
                ("murinae", "Murinae", ["biomedical", "organisms"], "鼠亚科"),
            ]
        )

    def test_exact_expansion_batch_495_adds_murine_muromonab_and_muscarinic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("murine_acquired_immunodeficiency_syndrome", "Murine Acquired Immunodeficiency Syndrome", ["biomedical", "diseases"], "小鼠获得性免疫缺陷综合征"),
                ("murine_hepatiti_viru", "Murine Hepatitis Virus", ["biomedical", "organisms"], "小鼠肝炎病毒"),
                ("murine_pneumonia_viru", "Murine Pneumonia Virus", ["biomedical", "organisms"], "小鼠肺炎病毒"),
                ("muromegaloviru", "Muromegalovirus", ["biomedical", "organisms"], "鼠巨细胞病毒"),
                ("muromonab_cd3", "Muromonab-cd3", ["biomedical", "chemicals_and_drugs"], "莫罗单抗-CD3"),
                ("muscarine", "Muscarine", ["biomedical", "chemicals_and_drugs"], "毒蕈碱"),
                ("muscarinic_agonist", "Muscarinic Agonists", ["biomedical", "chemicals_and_drugs"], "毒蕈碱受体激动剂"),
                ("muscarinic_antagonist", "Muscarinic Antagonists", ["biomedical", "chemicals_and_drugs"], "毒蕈碱受体拮抗剂"),
            ]
        )

    def test_exact_expansion_batch_496_adds_muscle_cell_fatigue_and_fiber_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("muscimol", "Muscimol", ["biomedical", "chemicals_and_drugs"], "蝇蕈醇"),
                ("muscle_cell", "Muscle Cells", ["biomedical"], "肌细胞"),
                ("muscle_cramp", "Muscle Cramp", ["biomedical", "diseases"], "肌肉痉挛"),
                ("muscle_denervation", "Muscle Denervation", ["biomedical"], "肌肉去神经支配"),
                ("muscle_development", "Muscle Development", ["biomedical"], "肌肉发育"),
                ("muscle_fatigue", "Muscle Fatigue", ["biomedical"], "肌肉疲劳"),
                ("muscle_fiber_fast_twitch", "Muscle Fibers, Fast-twitch", ["biomedical"], "快肌纤维"),
                ("muscle_fiber_skeletal", "Muscle Fibers, Skeletal", ["biomedical"], "骨骼肌纤维"),
            ]
        )

    def test_exact_expansion_batch_497_adds_muscle_tone_neoplasm_and_smooth_muscle_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("muscle_fiber_slow_twitch", "Muscle Fibers, Slow-twitch", ["biomedical"], "慢肌纤维"),
                ("muscle_hypertonia", "Muscle Hypertonia", ["biomedical", "diseases"], "肌张力增高"),
                ("muscle_hypotonia", "Muscle Hypotonia", ["biomedical", "diseases"], "肌张力减退"),
                ("muscle_neoplasm", "Muscle Neoplasms", ["biomedical", "diseases"], "肌肉肿瘤"),
                ("muscle_protein", "Muscle Proteins", ["biomedical", "chemicals_and_drugs"], "肌肉蛋白"),
                ("muscle_relaxation", "Muscle Relaxation", ["biomedical"], "肌肉松弛"),
                ("muscle_skeletal", "Muscle, Skeletal", ["biomedical"], "骨骼肌"),
                ("muscle_smooth_vascular", "Muscle, Smooth, Vascular", ["biomedical"], "血管平滑肌"),
            ]
        )

    def test_exact_expansion_batch_498_adds_muscle_spasticity_strength_and_atrophy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("muscle_spasticity", "Muscle Spasticity", ["biomedical", "diseases"], "肌痉挛状态"),
                ("muscle_spindl", "Muscle Spindles", ["biomedical"], "肌梭"),
                ("muscle_strength_dynamometer", "Muscle Strength Dynamometer", ["biomedical"], "肌力测力计"),
                ("muscle_stretching_exercise", "Muscle Stretching Exercises", ["biomedical"], "肌肉拉伸运动"),
                ("muscle_striated", "Muscle, Striated", ["biomedical"], "横纹肌"),
                ("muscle_tonu", "Muscle Tonus", ["biomedical"], "肌张力"),
                ("muscular_atrophy", "Muscular Atrophy", ["biomedical", "diseases"], "肌萎缩"),
                ("muscular_atrophy_spinal", "Muscular Atrophy, Spinal", ["biomedical", "diseases"], "脊髓性肌萎缩"),
            ]
        )

    def test_exact_expansion_batch_499_adds_muscular_dystrophy_subtype_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("muscular_disorder_atrophic", "Muscular Disorders, Atrophic", ["biomedical", "diseases"], "萎缩性肌病"),
                ("muscular_dystrophy", "Muscular Dystrophy", ["biomedical", "diseases"], "肌营养不良"),
                ("muscular_dystrophy__2", "Muscular Dystrophies", ["biomedical", "diseases"], "肌营养不良"),
                ("muscular_dystrophy_animal", "Muscular Dystrophy, Animal", ["biomedical", "diseases"], "动物肌营养不良"),
                ("muscular_dystrophy_duchenne", "Muscular Dystrophy, Duchenne", ["biomedical", "diseases"], "杜氏肌营养不良"),
                ("muscular_dystrophy_emery_dreifuss", "Muscular Dystrophy, Emery-dreifuss", ["biomedical", "diseases"], "埃默里-德雷福斯肌营养不良"),
                ("muscular_dystrophy_facioscapulohumeral", "Muscular Dystrophy, Facioscapulohumeral", ["biomedical", "diseases"], "面肩肱型肌营养不良"),
                ("muscular_dystrophy_limb_girdle", "Muscular Dystrophies, Limb-girdle", ["biomedical", "diseases"], "肢带型肌营养不良"),
            ]
        )

    def test_exact_expansion_batch_500_adds_oculopharyngeal_musculoskeletal_and_music_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("muscular_dystrophy_oculopharyngeal", "Muscular Dystrophy, Oculopharyngeal", ["biomedical", "diseases"], "眼咽型肌营养不良"),
                ("musculocutaneou_nerve", "Musculocutaneous Nerve", ["biomedical"], "肌皮神经"),
                ("musculoskeletal_manipulation", "Musculoskeletal Manipulations", ["biomedical"], "肌肉骨骼手法治疗"),
                ("musculoskeletal_physiological_phenomena", "Musculoskeletal Physiological Phenomena", ["biomedical"], "肌肉骨骼生理现象"),
                ("musculoskeletal_system", "Musculoskeletal System", ["biomedical"], "肌肉骨骼系统"),
                ("mushroom_body", "Mushroom Bodies", ["biomedical"], "蘑菇体"),
                ("mushroom_poisoning", "Mushroom Poisoning", ["biomedical", "diseases"], "蘑菇中毒"),
                ("music_information_retrieval", "Music Information Retrieval", ["computer_science"], "音乐信息检索"),
            ]
        )

    def test_exact_expansion_batch_501_adds_music_player_retrieval_and_therapy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("music_player", "Music Players", ["computer_science"], "音乐播放器"),
                ("music_recommendation", "Music Recommendation", ["computer_science"], "音乐推荐"),
                ("music_retrieval", "Music Retrieval", ["computer_science"], "音乐检索"),
                ("music_signal", "Music Signals", ["computer_science"], "音乐信号"),
                ("music_similarity", "Music Similarity", ["computer_science"], "音乐相似性"),
                ("music_therapy", "Music Therapy", ["biomedical"], "音乐疗法"),
                ("musical_instrument", "Musical Instruments", ["education"], "乐器"),
                ("musical_instrument_digital_interfac", "Musical Instrument Digital Interfaces", ["computers_and_information_processing"], "乐器数字接口"),
            ]
        )

    def test_exact_expansion_batch_502_adds_music_performance_mustard_and_mutagen_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("musical_noise", "Musical Noise", ["computer_science"], "音乐噪声"),
                ("musical_performance", "Musical Performance", ["computer_science"], "音乐表演"),
                ("must_carry_regulation", "Must-carry Regulations", ["communications_technology"], "必载规则"),
                ("mustard_compound", "Mustard Compounds", ["biomedical", "chemicals_and_drugs"], "芥子化合物"),
                ("mustard_gas", "Mustard Gas", ["biomedical", "chemicals_and_drugs"], "芥子气"),
                ("mustard_plant", "Mustard Plant", ["biomedical", "organisms"], "芥菜"),
                ("mustelidae", "Mustelidae", ["biomedical", "organisms"], "鼬科"),
                ("mutagen", "Mutagens", ["biomedical", "chemicals_and_drugs"], "诱变剂"),
            ]
        )

    def test_exact_expansion_batch_503_adds_mutagenesis_mutant_and_mutation_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mutagenesi_insertional", "Mutagenesis, Insertional", ["biomedical"], "插入诱变"),
                ("mutagenesi_site_directed", "Mutagenesis, Site-directed", ["biomedical"], "定点诱变"),
                ("mutagenicity_test", "Mutagenicity Tests", ["biomedical"], "致突变性试验"),
                ("mutant_chimeric_protein", "Mutant Chimeric Proteins", ["biomedical", "chemicals_and_drugs"], "突变嵌合蛋白"),
                ("mutant_protein", "Mutant Proteins", ["biomedical", "chemicals_and_drugs"], "突变蛋白"),
                ("mutation_accumulation", "Mutation Accumulation", ["biomedical"], "突变积累"),
                ("mutation_missense", "Mutation, Missense", ["biomedical"], "错义突变"),
                ("mutation_operation", "Mutation Operations", ["computer_science"], "变异操作"),
            ]
        )

    def test_exact_expansion_batch_504_adds_mutation_mutual_and_myasthenia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mutation_operator", "Mutation Operator", ["computer_science"], "变异算子"),
                ("mutation_rate", "Mutation Rate", ["biomedical"], "突变率"),
                ("mutation_strategy", "Mutation Strategy", ["computer_science"], "变异策略"),
                ("mutism", "Mutism", ["biomedical", "diseases"], "缄默症"),
                ("mutual_authentication", "Mutual Authentication", ["computer_science"], "双向认证"),
                ("mutual_coupling", "Mutual Coupling", ["computer_science"], "互耦"),
                ("mutual_coupling_effect", "Mutual Coupling Effects", ["computer_science"], "互耦效应"),
                ("mutual_information", "Mutual Information", ["information_theory"], "互信息"),
            ]
        )

    def test_exact_expansion_batch_505_adds_myalgia_myasthenia_and_mycobacterium_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("myalgia", "Myalgia", ["biomedical", "diseases"], "肌痛"),
                ("myasthenia_gravi_and_thymoma", "Myasthenia Gravis And Thymoma", ["medicine"], "重症肌无力与胸腺瘤"),
                ("myasthenia_gravi_autoimmune_experimental", "Myasthenia Gravis, Autoimmune, Experimental", ["biomedical", "diseases"], "实验性自身免疫性重症肌无力"),
                ("myasthenic_syndrom_congenital", "Myasthenic Syndromes, Congenital", ["biomedical", "diseases"], "先天性肌无力综合征"),
                ("mycelium", "Mycelium", ["biomedical"], "菌丝体"),
                ("mycetoma", "Mycetoma", ["biomedical", "diseases"], "足菌肿"),
                ("mycetozoa", "Mycetozoa", ["biomedical", "organisms"], "黏菌动物"),
                ("mycobacteriaceae", "Mycobacteriaceae", ["biomedical", "organisms"], "分枝杆菌科"),
            ]
        )

    def test_exact_expansion_batch_506_adds_mycobacteriophage_and_avium_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mycobacteriophag", "Mycobacteriophages", ["biomedical", "organisms"], "分枝杆菌噬菌体"),
                ("mycobacterium", "Mycobacterium", ["biomedical", "organisms"], "分枝杆菌属"),
                ("mycobacterium_abscessu", "Mycobacterium Abscessus", ["biomedical", "organisms"], "脓肿分枝杆菌"),
                ("mycobacterium_avium", "Mycobacterium Avium", ["biomedical", "organisms"], "鸟分枝杆菌"),
                ("mycobacterium_avium_complex", "Mycobacterium Avium Complex", ["biomedical", "organisms"], "鸟分枝杆菌复合群"),
                ("mycobacterium_avium_intracellulare_infection", "Mycobacterium Avium-intracellulare Infection", ["biomedical", "diseases"], "鸟分枝杆菌-胞内分枝杆菌感染"),
                ("mycobacterium_avium_subsp_paratuberculosi", "Mycobacterium Avium Subsp. Paratuberculosis", ["biomedical", "organisms"], "副结核分枝杆菌"),
                ("mycobacterium_bovi", "Mycobacterium Bovis", ["biomedical", "organisms"], "牛分枝杆菌"),
            ]
        )

    def test_exact_expansion_batch_507_adds_cheloniae_fortuitum_and_leprae_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mycobacterium_chelonae", "Mycobacterium Chelonae", ["biomedical", "organisms"], "龟分枝杆菌"),
                ("mycobacterium_fortuitum", "Mycobacterium Fortuitum", ["biomedical", "organisms"], "偶发分枝杆菌"),
                ("mycobacterium_haemophilum", "Mycobacterium Haemophilum", ["biomedical", "organisms"], "嗜血分枝杆菌"),
                ("mycobacterium_infection", "Mycobacterium Infections", ["biomedical", "diseases"], "分枝杆菌感染"),
                ("mycobacterium_infection_nontuberculou", "Mycobacterium Infections, Nontuberculous", ["biomedical", "diseases"], "非结核分枝杆菌感染"),
                ("mycobacterium_kansasii", "Mycobacterium Kansasii", ["biomedical", "organisms"], "堪萨斯分枝杆菌"),
                ("mycobacterium_leprae", "Mycobacterium Leprae", ["biomedical", "organisms"], "麻风分枝杆菌"),
                ("mycobacterium_lepraemurium", "Mycobacterium Lepraemurium", ["biomedical", "organisms"], "鼠麻风分枝杆菌"),
            ]
        )

    def test_exact_expansion_batch_508_adds_mycobacterium_marinum_and_mycology_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mycobacterium_marinum", "Mycobacterium Marinum", ["biomedical", "organisms"], "海分枝杆菌"),
                ("mycobacterium_phlei", "Mycobacterium Phlei", ["biomedical", "organisms"], "草分枝杆菌"),
                ("mycobacterium_scrofulaceum", "Mycobacterium Scrofulaceum", ["biomedical", "organisms"], "瘰疬分枝杆菌"),
                ("mycobacterium_smegmati", "Mycobacterium Smegmatis", ["biomedical", "organisms"], "耻垢分枝杆菌"),
                ("mycobacterium_tuberculosi", "Mycobacterium Tuberculosis", ["biomedical", "organisms"], "结核分枝杆菌"),
                ("mycobacterium_ulceran", "Mycobacterium Ulcerans", ["biomedical", "organisms"], "溃疡分枝杆菌"),
                ("mycobiome", "Mycobiome", ["biomedical"], "真菌组"),
                ("mycolic_acid", "Mycolic Acids", ["biomedical", "chemicals_and_drugs"], "分枝菌酸"),
            ]
        )

    def test_exact_expansion_batch_509_adds_mycological_and_mycoplasma_family_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mycological_typing_techniqu", "Mycological Typing Techniques", ["biomedical"], "真菌学分型技术"),
                ("mycology", "Mycology", ["biomedical"], "真菌学"),
                ("mycophenolic_acid", "Mycophenolic Acid", ["biomedical", "chemicals_and_drugs"], "霉酚酸"),
                ("mycoplasma", "Mycoplasma", ["biomedical", "organisms"], "支原体"),
                ("mycoplasma_agalactiae", "Mycoplasma Agalactiae", ["biomedical", "organisms"], "无乳支原体"),
                ("mycoplasma_arthritidi", "Mycoplasma Arthritidis", ["biomedical", "organisms"], "关节炎支原体"),
                ("mycoplasma_bovi", "Mycoplasma Bovis", ["biomedical", "organisms"], "牛支原体"),
                ("mycoplasma_bovigenitalium", "Mycoplasma Bovigenitalium", ["biomedical", "organisms"], "牛生殖道支原体"),
            ]
        )

    def test_exact_expansion_batch_510_adds_mycoplasma_livestock_and_human_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mycoplasma_capricolum", "Mycoplasma Capricolum", ["biomedical", "organisms"], "山羊支原体"),
                ("mycoplasma_conjunctivae", "Mycoplasma Conjunctivae", ["biomedical", "organisms"], "结膜支原体"),
                ("mycoplasma_fermentan", "Mycoplasma Fermentans", ["biomedical", "organisms"], "发酵支原体"),
                ("mycoplasma_gallisepticum", "Mycoplasma Gallisepticum", ["biomedical", "organisms"], "鸡毒支原体"),
                ("mycoplasma_genitalium", "Mycoplasma Genitalium", ["biomedical", "organisms"], "生殖支原体"),
                ("mycoplasma_homini", "Mycoplasma Hominis", ["biomedical", "organisms"], "人型支原体"),
                ("mycoplasma_hyopneumoniae", "Mycoplasma Hyopneumoniae", ["biomedical", "organisms"], "猪肺炎支原体"),
                ("mycoplasma_hyorhini", "Mycoplasma Hyorhinis", ["biomedical", "organisms"], "猪鼻支原体"),
            ]
        )

    def test_exact_expansion_batch_511_adds_mycoplasma_pneumoniae_and_taxonomy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mycoplasma_hyosynoviae", "Mycoplasma Hyosynoviae", ["biomedical", "organisms"], "猪滑液支原体"),
                ("mycoplasma_infection", "Mycoplasma Infections", ["biomedical", "diseases"], "支原体感染"),
                ("mycoplasma_iowae", "Mycoplasma Iowae", ["biomedical", "organisms"], "爱荷华支原体"),
                ("mycoplasma_meleagridi", "Mycoplasma Meleagridis", ["biomedical", "organisms"], "火鸡支原体"),
                ("mycoplasma_orale", "Mycoplasma Orale", ["biomedical", "organisms"], "口腔支原体"),
                ("mycoplasma_ovipneumoniae", "Mycoplasma Ovipneumoniae", ["biomedical", "organisms"], "绵羊肺炎支原体"),
                ("mycoplasma_penetran", "Mycoplasma Penetrans", ["biomedical", "organisms"], "穿透支原体"),
                ("mycoplasma_pneumoniae", "Mycoplasma Pneumoniae", ["biomedical", "organisms"], "肺炎支原体"),
            ]
        )

    def test_exact_expansion_batch_512_adds_mycoplasma_synoviae_and_mycoses_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mycoplasma_pulmoni", "Mycoplasma Pulmonis", ["biomedical", "organisms"], "肺支原体"),
                ("mycoplasma_salivarium", "Mycoplasma Salivarium", ["biomedical", "organisms"], "唾液支原体"),
                ("mycoplasma_synoviae", "Mycoplasma Synoviae", ["biomedical", "organisms"], "滑液支原体"),
                ("mycoplasmataceae", "Mycoplasmataceae", ["biomedical", "organisms"], "支原体科"),
                ("mycoplasmatal", "Mycoplasmatales", ["biomedical", "organisms"], "支原体目"),
                ("mycoplasmatal_infection", "Mycoplasmatales Infections", ["biomedical", "diseases"], "支原体目感染"),
                ("mycorrhizae", "Mycorrhizae", ["biomedical"], "菌根"),
                ("mycose", "Mycoses", ["biomedical", "diseases"], "真菌病"),
            ]
        )

    def test_exact_expansion_batch_513_adds_mycosis_mycotoxin_and_myelin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("mycosi_fungoid", "Mycosis Fungoides", ["biomedical", "diseases"], "蕈样肉芽肿"),
                ("mycosphaerella", "Mycosphaerella", ["biomedical", "organisms"], "球腔菌属"),
                ("mycotoxicosi", "Mycotoxicosis", ["biomedical", "diseases"], "霉菌毒素中毒"),
                ("mycotoxin", "Mycotoxins", ["biomedical", "chemicals_and_drugs"], "霉菌毒素"),
                ("mydriasi", "Mydriasis", ["biomedical", "diseases"], "瞳孔散大"),
                ("mydriatic", "Mydriatics", ["biomedical", "chemicals_and_drugs"], "散瞳药"),
                ("myelencephalon", "Myelencephalon", ["biomedical"], "髓脑"),
                ("myelin_basic_protein", "Myelin Basic Protein", ["biomedical", "chemicals_and_drugs"], "髓鞘碱性蛋白"),
            ]
        )

    def test_exact_expansion_batch_514_adds_myelin_disease_and_myelitis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("myelin_oligodendrocyte_glycoprotein", "Myelin-oligodendrocyte Glycoprotein", ["biomedical", "chemicals_and_drugs"], "髓鞘少突胶质细胞糖蛋白"),
                ("myelin_oligodendrocyte_glycoprotein_antibody_associated_disease", "Myelin Oligodendrocyte Glycoprotein Antibody-associated Disease", ["biomedical", "diseases"], "髓鞘少突胶质细胞糖蛋白抗体相关疾病"),
                ("myelin_proteolipid_protein", "Myelin Proteolipid Protein", ["biomedical", "chemicals_and_drugs"], "髓鞘蛋白脂质蛋白"),
                ("myelinolysi_central_pontine", "Myelinolysis, Central Pontine", ["biomedical", "diseases"], "脑桥中央髓鞘溶解症"),
                ("myeliti", "Myelitis", ["biomedical", "diseases"], "脊髓炎"),
                ("myeliti_transverse", "Myelitis, Transverse", ["biomedical", "diseases"], "横贯性脊髓炎"),
                ("myelodysplastic_myeloproliferative_disease", "Myelodysplastic-myeloproliferative Diseases", ["biomedical", "diseases"], "骨髓增生异常-骨髓增殖性疾病"),
                ("myelodysplastic_syndrom", "Myelodysplastic Syndromes", ["biomedical", "diseases"], "骨髓增生异常综合征"),
            ]
        )

    def test_exact_expansion_batch_515_adds_myeloid_cell_and_myeloproliferative_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("myelography", "Myelography", ["biomedical"], "脊髓造影"),
                ("myeloid_cell", "Myeloid Cells", ["biomedical"], "髓系细胞"),
                ("myeloid_derived_suppressor_cell", "Myeloid-derived Suppressor Cells", ["biomedical"], "髓源性抑制细胞"),
                ("myeloid_differentiation_factor_88", "Myeloid Differentiation Factor 88", ["biomedical", "chemicals_and_drugs"], "髓样分化因子88"),
                ("myeloid_progenitor_cell", "Myeloid Progenitor Cells", ["biomedical"], "髓系祖细胞"),
                ("myelolipoma", "Myelolipoma", ["biomedical", "diseases"], "骨髓脂肪瘤"),
                ("myelopoiesi", "Myelopoiesis", ["biomedical"], "髓系造血"),
                ("myeloproliferative_disorder", "Myeloproliferative Disorders", ["biomedical", "diseases"], "骨髓增殖性疾病"),
            ]
        )

    def test_exact_expansion_batch_516_adds_myenteric_myoblast_and_myocardial_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("myenteric_plexu", "Myenteric Plexus", ["biomedical"], "肌间神经丛"),
                ("myiasi", "Myiasis", ["biomedical", "diseases"], "蝇蛆病"),
                ("myo_inositol_1_phosphate_synthase", "Myo-inositol-1-phosphate Synthase", ["biomedical", "chemicals_and_drugs"], "肌醇-1-磷酸合酶"),
                ("myoblast", "Myoblasts", ["biomedical"], "成肌细胞"),
                ("myoblast_cardiac", "Myoblasts, Cardiac", ["biomedical"], "心肌成肌细胞"),
                ("myoblast_skeletal", "Myoblasts, Skeletal", ["biomedical"], "骨骼肌成肌细胞"),
                ("myoblast_smooth_muscle", "Myoblasts, Smooth Muscle", ["biomedical"], "平滑肌成肌细胞"),
                ("myocardial_bridging", "Myocardial Bridging", ["biomedical", "diseases"], "心肌桥"),
            ]
        )

    def test_exact_expansion_batch_517_adds_myocardial_imaging_and_myoclonic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("myocardial_contraction", "Myocardial Contraction", ["biomedical"], "心肌收缩"),
                ("myocardial_contusion", "Myocardial Contusions", ["biomedical", "diseases"], "心肌挫伤"),
                ("myocardial_depressant_factor", "Myocardial Depressant Factor", ["biomedical", "chemicals_and_drugs"], "心肌抑制因子"),
                ("myocardial_perfusion_imaging", "Myocardial Perfusion Imaging", ["biomedical"], "心肌灌注显像"),
                ("myocardin", "Myocardin", ["biomedical", "chemicals_and_drugs"], "心肌素"),
                ("myoclonic_cerebellar_dyssynergia", "Myoclonic Cerebellar Dyssynergia", ["biomedical", "diseases"], "肌阵挛性小脑协同不能"),
                ("myoclonic_epilepsy_juvenile", "Myoclonic Epilepsy, Juvenile", ["biomedical", "diseases"], "青少年肌阵挛性癫痫"),
                ("myoclonic_epilepsy_progressive", "Myoclonic Epilepsies, Progressive", ["biomedical", "diseases"], "进行性肌阵挛性癫痫"),
            ]
        )

    def test_exact_expansion_batch_518_adds_myoclonus_myocytes_and_myofascial_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("myoclonu", "Myoclonus", ["biomedical", "diseases"], "肌阵挛"),
                ("myocutaneou_flap", "Myocutaneous Flap", ["biomedical"], "肌皮瓣"),
                ("myocyt_cardiac", "Myocytes, Cardiac", ["biomedical"], "心肌细胞"),
                ("myocyt_smooth_muscle", "Myocytes, Smooth Muscle", ["biomedical"], "平滑肌细胞"),
                ("myoelectric_complex_migrating", "Myoelectric Complex, Migrating", ["biomedical"], "移行性肌电复合波"),
                ("myoelectric_control", "Myoelectric Control", ["engineering_in_medicine_and_biology"], "肌电控制"),
                ("myoepithelioma", "Myoepithelioma", ["biomedical", "diseases"], "肌上皮瘤"),
                ("myofascial_pain_syndrom", "Myofascial Pain Syndromes", ["biomedical", "diseases"], "肌筋膜疼痛综合征"),
            ]
        )

    def test_exact_expansion_batch_519_adds_myofibril_myogenic_and_myoglobin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("myofascial_release_therapy", "Myofascial Release Therapy", ["biomedical"], "肌筋膜松解疗法"),
                ("myofibril", "Myofibrils", ["biomedical"], "肌原纤维"),
                ("myofibroblast", "Myofibroblasts", ["biomedical"], "肌成纤维细胞"),
                ("myofibroma", "Myofibroma", ["biomedical", "diseases"], "肌纤维瘤"),
                ("myofibromatosi", "Myofibromatosis", ["biomedical", "diseases"], "肌纤维瘤病"),
                ("myofunctional_therapy", "Myofunctional Therapy", ["biomedical"], "肌功能疗法"),
                ("myogenic_regulatory_factor", "Myogenic Regulatory Factors", ["biomedical", "chemicals_and_drugs"], "肌生成调节因子"),
                ("myogenic_regulatory_factor_5", "Myogenic Regulatory Factor 5", ["biomedical", "chemicals_and_drugs"], "肌生成调节因子5"),
            ]
        )

    def test_exact_expansion_batch_520_adds_myogenin_myoma_and_myosarcoma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("myogenin", "Myogenin", ["biomedical", "chemicals_and_drugs"], "肌生成素"),
                ("myoglobin", "Myoglobin", ["biomedical", "chemicals_and_drugs"], "肌红蛋白"),
                ("myoglobinuria", "Myoglobinuria", ["biomedical", "diseases"], "肌红蛋白尿"),
                ("myokin", "Myokines", ["biomedical", "chemicals_and_drugs"], "肌因子"),
                ("myokymia", "Myokymia", ["biomedical", "diseases"], "肌纤维颤搐"),
                ("myoma", "Myoma", ["biomedical", "diseases"], "肌瘤"),
                ("myometrium", "Myometrium", ["biomedical"], "子宫肌层"),
                ("myosarcoma", "Myosarcoma", ["biomedical", "diseases"], "肌肉肉瘤"),
            ]
        )

    def test_exact_expansion_batch_521_adds_myosin_and_myositis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("myosin_binding_protein_c", "Myosin Binding Protein C", ["biomedical", "chemicals_and_drugs"], "肌球蛋白结合蛋白C"),
                ("myosin_heavy_chain", "Myosin Heavy Chains", ["biomedical", "chemicals_and_drugs"], "肌球蛋白重链"),
                ("myosin_light_chain", "Myosin Light Chains", ["biomedical", "chemicals_and_drugs"], "肌球蛋白轻链"),
                ("myosin_light_chain_kinase", "Myosin-light-chain Kinase", ["biomedical", "chemicals_and_drugs"], "肌球蛋白轻链激酶"),
                ("myosin_light_chain_phosphatase", "Myosin-light-chain Phosphatase", ["biomedical", "chemicals_and_drugs"], "肌球蛋白轻链磷酸酶"),
                ("myosin_subfragment", "Myosin Subfragments", ["biomedical", "chemicals_and_drugs"], "肌球蛋白亚片段"),
                ("myosin_viia", "Myosin Viia", ["biomedical", "chemicals_and_drugs"], "肌球蛋白VIIA"),
                ("myositi", "Myositis", ["biomedical", "diseases"], "肌炎"),
            ]
        )

    def test_exact_expansion_batch_522_adds_myostatin_myotomy_and_myotonia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("myositi_inclusion_body", "Myositis, Inclusion Body", ["biomedical", "diseases"], "包涵体肌炎"),
                ("myositi_ossifican", "Myositis Ossificans", ["biomedical", "diseases"], "骨化性肌炎"),
                ("myostatin", "Myostatin", ["biomedical", "chemicals_and_drugs"], "肌肉生长抑制素"),
                ("myotendinou_junction", "Myotendinous Junction", ["biomedical"], "肌腱连接"),
                ("myotomy", "Myotomy", ["biomedical"], "肌切开术"),
                ("myotonia", "Myotonia", ["biomedical", "diseases"], "肌强直"),
                ("myotonia_congenita", "Myotonia Congenita", ["biomedical", "diseases"], "先天性肌强直"),
                ("myotonic_disorder", "Myotonic Disorders", ["biomedical", "diseases"], "肌强直性疾病"),
            ]
        )

    def test_exact_expansion_batch_523_adds_myotonic_myxoma_and_myxozoa_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("myotonic_dystrophy", "Myotonic Dystrophy", ["biomedical", "diseases"], "肌强直性营养不良"),
                ("myotonin_protein_kinase", "Myotonin-protein Kinase", ["biomedical", "chemicals_and_drugs"], "肌强直蛋白激酶"),
                ("myotoxicity", "Myotoxicity", ["biomedical", "diseases"], "肌毒性"),
                ("myxedema", "Myxedema", ["biomedical", "diseases"], "黏液性水肿"),
                ("myxoma", "Myxoma", ["biomedical", "diseases"], "黏液瘤"),
                ("myxoma_viru", "Myxoma Virus", ["biomedical", "organisms"], "黏液瘤病毒"),
                ("myxomatosi_infectiou", "Myxomatosis, Infectious", ["biomedical", "diseases"], "传染性黏液瘤病"),
                ("myxozoa", "Myxozoa", ["biomedical", "organisms"], "黏体动物门"),
            ]
        )

    def test_exact_expansion_batch_524_adds_n95_and_n_acetyltransferase_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("n95_respirator", "N95 Respirators", ["biomedical"], "N95口罩"),
                ("n_acetylgalactosamine_4_sulfatase", "N-acetylgalactosamine-4-sulfatase", ["biomedical", "chemicals_and_drugs"], "N-乙酰半乳糖胺-4-硫酸酯酶"),
                ("n_acetylgalactosaminyltransferase", "N-acetylgalactosaminyltransferases", ["biomedical", "chemicals_and_drugs"], "N-乙酰半乳糖胺转移酶"),
                ("n_acetylglucosaminyltransferase", "N-acetylglucosaminyltransferases", ["biomedical", "chemicals_and_drugs"], "N-乙酰葡糖胺转移酶"),
                ("n_acetylhexosaminyltransferase", "N-acetylhexosaminyltransferases", ["biomedical", "chemicals_and_drugs"], "N-乙酰己糖胺转移酶"),
                ("n_acetyllactosamine_synthase", "N-acetyllactosamine Synthase", ["biomedical", "chemicals_and_drugs"], "N-乙酰乳糖胺合酶"),
                ("n_acetylmuramoyl_l_alanine_amidase", "N-acetylmuramoyl-l-alanine Amidase", ["biomedical", "chemicals_and_drugs"], "N-乙酰胞壁酰-L-丙氨酸酰胺酶"),
                ("n_acylneuraminate_cytidylyltransferase", "N-acylneuraminate Cytidylyltransferase", ["biomedical", "chemicals_and_drugs"], "N-酰基神经氨酸胞苷酰转移酶"),
            ]
        )

    def test_exact_expansion_batch_525_adds_n_formylmethionine_and_n_terminal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("n_acylsphingosine_galactosyltransferase", "N-acylsphingosine Galactosyltransferase", ["biomedical", "chemicals_and_drugs"], "N-酰基鞘氨醇半乳糖基转移酶"),
                ("n_ethylmaleimide_sensitive_protein", "N-ethylmaleimide-sensitive Proteins", ["biomedical", "chemicals_and_drugs"], "N-乙基马来酰亚胺敏感蛋白"),
                ("n_formylmethionine", "N-formylmethionine", ["biomedical", "chemicals_and_drugs"], "N-甲酰甲硫氨酸"),
                ("n_formylmethionine_leucyl_phenylalanine", "N-formylmethionine Leucyl-phenylalanine", ["biomedical", "chemicals_and_drugs"], "N-甲酰甲硫氨酰亮氨酰苯丙氨酸"),
                ("n_glycosyl_hydrolase", "N-glycosyl Hydrolases", ["biomedical", "chemicals_and_drugs"], "N-糖苷水解酶"),
                ("n_terminal_acetyltransferase", "N-terminal Acetyltransferases", ["biomedical", "chemicals_and_drugs"], "N端乙酰转移酶"),
                ("n_terminal_acetyltransferase_a", "N-terminal Acetyltransferase A", ["biomedical", "chemicals_and_drugs"], "N端乙酰转移酶A"),
                ("n_terminal_acetyltransferase_b", "N-terminal Acetyltransferase B", ["biomedical", "chemicals_and_drugs"], "N端乙酰转移酶B"),
            ]
        )

    def test_exact_expansion_batch_526_adds_n_terminal_and_nad_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("n_terminal_acetyltransferase_c", "N-terminal Acetyltransferase C", ["biomedical", "chemicals_and_drugs"], "N端乙酰转移酶C"),
                ("n_terminal_acetyltransferase_d", "N-terminal Acetyltransferase D", ["biomedical", "chemicals_and_drugs"], "N端乙酰转移酶D"),
                ("n_terminal_acetyltransferase_e", "N-terminal Acetyltransferase E", ["biomedical", "chemicals_and_drugs"], "N端乙酰转移酶E"),
                ("n_terminal_acetyltransferase_f", "N-terminal Acetyltransferase F", ["biomedical", "chemicals_and_drugs"], "N端乙酰转移酶F"),
                ("nabumetone", "Nabumetone", ["biomedical", "chemicals_and_drugs"], "萘丁美酮"),
                ("nacre", "Nacre", ["biomedical", "chemicals_and_drugs"], "珍珠层"),
                ("nad", "NAD", ["biomedical", "chemicals_and_drugs"], "烟酰胺腺嘌呤二核苷酸"),
                ("nad_and_nadp_dependent_alcohol_oxidoreductase", "NAD (+) And NADP (+) Dependent Alcohol Oxidoreductases", ["biomedical", "chemicals_and_drugs"], "烟酰胺腺嘌呤二核苷酸和其磷酸依赖性醇氧化还原酶"),
            ]
        )

    def test_exact_expansion_batch_527_adds_nad_nadh_and_nadolol_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nad_nucleosidase", "NAD+ Nucleosidase", ["biomedical", "chemicals_and_drugs"], "烟酰胺腺嘌呤二核苷酸核苷酶"),
                ("nadh_nadph_oxidoreductase", "Nadh, Nadph Oxidoreductases", ["biomedical", "chemicals_and_drugs"], "还原型烟酰胺腺嘌呤二核苷酸及其磷酸氧化还原酶"),
                ("nadh_tetrazolium_reductase", "NADH Tetrazolium Reductase", ["biomedical", "chemicals_and_drugs"], "还原型烟酰胺腺嘌呤二核苷酸四唑还原酶"),
                ("nadolol", "Nadolol", ["biomedical", "chemicals_and_drugs"], "纳多洛尔"),
                ("nadp", "NADP", ["biomedical", "chemicals_and_drugs"], "烟酰胺腺嘌呤二核苷酸磷酸"),
                ("nadp_transhydrogenase", "NADP Transhydrogenases", ["biomedical", "chemicals_and_drugs"], "烟酰胺腺嘌呤二核苷酸磷酸转氢酶"),
                ("nadp_transhydrogenase_ab_specific", "NADP Transhydrogenase, Ab-specific", ["biomedical", "chemicals_and_drugs"], "AB特异性烟酰胺腺嘌呤二核苷酸磷酸转氢酶"),
                ("nadp_transhydrogenase_b_specific", "NADP Transhydrogenase, B-specific", ["biomedical", "chemicals_and_drugs"], "B特异性烟酰胺腺嘌呤二核苷酸磷酸转氢酶"),
            ]
        )

    def test_exact_expansion_batch_528_adds_nadph_and_nail_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nadph_dehydrogenase", "Nadph Dehydrogenase", ["biomedical", "chemicals_and_drugs"], "还原型烟酰胺腺嘌呤二核苷酸磷酸脱氢酶"),
                ("nadph_ferrihemoprotein_reductase", "Nadph-ferrihemoprotein Reductase", ["biomedical", "chemicals_and_drugs"], "还原型烟酰胺腺嘌呤二核苷酸磷酸铁血红蛋白还原酶"),
                ("nadph_oxidase", "Nadph Oxidases", ["biomedical", "chemicals_and_drugs"], "还原型烟酰胺腺嘌呤二核苷酸磷酸氧化酶"),
                ("nadph_oxidase_1", "Nadph Oxidase 1", ["biomedical", "chemicals_and_drugs"], "还原型烟酰胺腺嘌呤二核苷酸磷酸氧化酶1"),
                ("nadph_oxidase_2", "Nadph Oxidase 2", ["biomedical", "chemicals_and_drugs"], "还原型烟酰胺腺嘌呤二核苷酸磷酸氧化酶2"),
                ("nadph_oxidase_4", "Nadph Oxidase 4", ["biomedical", "chemicals_and_drugs"], "还原型烟酰胺腺嘌呤二核苷酸磷酸氧化酶4"),
                ("nadph_oxidase_5", "Nadph Oxidase 5", ["biomedical", "chemicals_and_drugs"], "还原型烟酰胺腺嘌呤二核苷酸磷酸氧化酶5"),
                ("nadroparin", "Nadroparin", ["biomedical", "chemicals_and_drugs"], "那屈肝素"),
            ]
        )

    def test_exact_expansion_batch_529_adds_naegleria_nafcillin_and_nail_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("naegleria", "Naegleria", ["biomedical", "organisms"], "耐格里属"),
                ("naegleria_fowleri", "Naegleria Fowleri", ["biomedical", "organisms"], "福氏耐格里阿米巴"),
                ("nafarelin", "Nafarelin", ["biomedical", "chemicals_and_drugs"], "那法瑞林"),
                ("nafcillin", "Nafcillin", ["biomedical", "chemicals_and_drugs"], "萘夫西林"),
                ("nafoxidine", "Nafoxidine", ["biomedical", "chemicals_and_drugs"], "萘福昔定"),
                ("nail_biting", "Nail Biting", ["biomedical"], "咬甲癖"),
                ("nail_ingrown", "Nails, Ingrown", ["biomedical", "diseases"], "嵌甲"),
                ("nail_malformed", "Nails, Malformed", ["biomedical", "diseases"], "甲畸形"),
            ]
        )

    def test_exact_expansion_batch_530_adds_nail_patella_naive_bayes_and_nakagami_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nail_patella_syndrome", "Nail-patella Syndrome", ["biomedical", "diseases"], "甲髌综合征"),
                ("nairobi_sheep_disease", "Nairobi Sheep Disease", ["biomedical", "diseases"], "内罗毕绵羊病"),
                ("nairobi_sheep_disease_viru", "Nairobi Sheep Disease Virus", ["biomedical", "organisms"], "内罗毕绵羊病病毒"),
                ("nairoviru", "Nairovirus", ["biomedical", "organisms"], "内罗病毒"),
                ("naive_bay", "Naive Bayes", ["computer_science"], "朴素贝叶斯"),
                ("naive_bay_classifier", "Naive Bayes Classifier", ["computer_science"], "朴素贝叶斯分类器"),
                ("naive_bayesian_classifier", "Naive Bayesian Classifier", ["computer_science"], "朴素贝叶斯分类器"),
                ("nakagami_distribution", "Nakagami Distribution", ["mathematics"], "中上分布"),
            ]
        )

    def test_exact_expansion_batch_531_adds_nakagami_and_naloxone_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nakagami_fading", "Nakagami Fading", ["computer_science"], "Nakagami衰落"),
                ("nakagami_fading_channel", "Nakagami Fading Channel", ["computer_science"], "Nakagami衰落信道"),
                ("nakagami_m", "Nakagami-m", ["computer_science"], "Nakagami-m分布"),
                ("nakagami_m_fading", "Nakagami-m Fading", ["computer_science"], "Nakagami-m衰落"),
                ("nalbuphine", "Nalbuphine", ["biomedical", "chemicals_and_drugs"], "纳布啡"),
                ("nalidixic_acid", "Nalidixic Acid", ["biomedical", "chemicals_and_drugs"], "萘啶酸"),
                ("naloxone", "Naloxone", ["biomedical", "chemicals_and_drugs"], "纳洛酮"),
                ("naltrexone", "Naltrexone", ["biomedical", "chemicals_and_drugs"], "纳曲酮"),
            ]
        )

    def test_exact_expansion_batch_532_adds_name_nand_flash_and_nandrolone_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("name_recognition", "Name Recognition", ["computer_science"], "名称识别"),
                ("named_entity", "Named Entities", ["computer_science"], "命名实体"),
                ("nand_circuit", "Nand Circuits", ["computer_science"], "与非门电路"),
                ("nand_flash", "Nand Flash", ["computer_science"], "NAND闪存"),
                ("nand_flash_memory", "Nand Flash Memory", ["computer_science"], "NAND闪存"),
                ("nandrolone", "Nandrolone", ["biomedical", "chemicals_and_drugs"], "南诺龙"),
                ("nandrolone_decanoate", "Nandrolone Decanoate", ["biomedical", "chemicals_and_drugs"], "癸酸南诺龙"),
                ("nano_electromechanical_system", "Nano Electromechanical Systems", ["computer_science"], "纳米机电系统"),
            ]
        )

    def test_exact_expansion_batch_533_adds_nanoantenna_and_nanobiotechnology_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nanoantenna", "Nanoantennas", ["antennas_and_propagation"], "纳米天线"),
                ("nanoarchaeota", "Nanoarchaeota", ["biomedical", "organisms"], "纳古菌门"),
                ("nanobiophotonic", "Nanobiophotonics", ["lasers_and_electrooptics"], "纳米生物光子学"),
                ("nanobioscience", "Nanobioscience", ["engineering_in_medicine_and_biology"], "纳米生物科学"),
                ("nanobiotechnology", "Nanobiotechnology", ["nanotechnology"], "纳米生物技术"),
                ("nanocantilever", "Nanocantilevers", ["computer_science"], "纳米悬臂梁"),
                ("nanocapsul", "Nanocapsules", ["biomedical", "chemicals_and_drugs"], "纳米胶囊"),
                ("nanocarrier", "Nanocarriers", ["nanotechnology"], "纳米载体"),
            ]
        )

    def test_exact_expansion_batch_534_adds_nanocommunication_and_nanocomposite_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nanocommunication", "Nanocommunication", ["communications_technology"], "纳米通信"),
                ("nanocomposit", "Nanocomposites", ["nanotechnology"], "纳米复合材料"),
                ("nanocomposite_film", "Nanocomposite Films", ["materials_elements_and_compounds"], "纳米复合薄膜"),
                ("nanoconjugat", "Nanoconjugates", ["biomedical", "chemicals_and_drugs"], "纳米偶联物"),
                ("nanocontact", "Nanocontacts", ["nanotechnology"], "纳米接触"),
                ("nanocrystal", "Nanocrystals", ["nanotechnology"], "纳米晶体"),
                ("nanodiamond", "Nanodiamonds", ["biomedical", "chemicals_and_drugs"], "纳米金刚石"),
                ("nanoelectromechanical_system", "Nanoelectromechanical Systems", ["nanotechnology"], "纳米机电系统"),
            ]
        )

    def test_exact_expansion_batch_535_adds_nanoelectronics_nanofabrication_and_nanofibers_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nanoelectronic", "Nanoelectronics", ["nanotechnology"], "纳米电子学"),
                ("nanofabrication", "Nanofabrication", ["nanotechnology"], "纳米制造"),
                ("nanofabrication_and_lithography_techniqu", "Nanofabrication And Lithography Techniques", ["engineering"], "纳米制造与光刻技术"),
                ("nanofiber", "Nanofibers", ["biomedical"], "纳米纤维"),
                ("nanofluid_flow_and_heat_transfer", "Nanofluid Flow And Heat Transfer", ["engineering"], "纳米流体流动与传热"),
                ("nanofluidic", "Nanofluidics", ["nanotechnology"], "纳米流体学"),
                ("nanofluidic_devic", "Nanofluidic Devices", ["physics"], "纳米流体器件"),
                ("nanog_homeobox_protein", "Nanog Homeobox Protein", ["biomedical", "chemicals_and_drugs"], "Nanog同源盒蛋白"),
            ]
        )

    def test_exact_expansion_batch_536_adds_nanogel_nanomaterial_and_nanomedicine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nanogel", "Nanogels", ["biomedical", "chemicals_and_drugs"], "纳米凝胶"),
                ("nanogenerator", "Nanogenerators", ["power_engineering_and_energy"], "纳米发电机"),
                ("nanolithography", "Nanolithography", ["nanotechnology"], "纳米光刻"),
                ("nanomagnetic", "Nanomagnetics", ["nanotechnology"], "纳米磁学"),
                ("nanomaterial", "Nanomaterials", ["nanotechnology"], "纳米材料"),
                ("nanomechatronic", "Nanomechatronics", ["computer_science"], "纳米机电一体化"),
                ("nanomedicine", "Nanomedicine", ["biomedical"], "纳米医学"),
                ("nanometer", "Nanometers", ["instrumentation_and_measurement"], "纳米"),
            ]
        )

    def test_exact_expansion_batch_537_adds_nanoparticle_and_nanophotonics_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nanopackaging", "Nanopackaging", ["nanotechnology"], "纳米封装"),
                ("nanoparticl", "Nanoparticles", ["nanotechnology"], "纳米颗粒"),
                ("nanoparticle_based_drug_delivery", "Nanoparticle-based Drug Delivery", ["materials_science"], "基于纳米颗粒的药物递送"),
                ("nanoparticle_drug_delivery_system", "Nanoparticle Drug Delivery System", ["biomedical", "chemicals_and_drugs"], "纳米颗粒药物递送系统"),
                ("nanopatterning", "Nanopatterning", ["nanotechnology"], "纳米图案化"),
                ("nanophotonic", "Nanophotonics", ["nanotechnology"], "纳米光子学"),
                ("nanoplasmonic", "Nanoplasmonics", ["nanotechnology"], "纳米等离激元学"),
                ("nanopor", "Nanopores", ["nanotechnology"], "纳米孔"),
            ]
        )

    def test_exact_expansion_batch_538_adds_nanopore_nanoporous_and_nanoscale_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nanopore_sequencing", "Nanopore Sequencing", ["biomedical"], "纳米孔测序"),
                ("nanoporou_material", "Nanoporous Materials", ["nanotechnology"], "纳米多孔材料"),
                ("nanoporou_metal_and_alloy", "Nanoporous Metals And Alloys", ["materials_science"], "纳米多孔金属与合金"),
                ("nanopositioning", "Nanopositioning", ["nanotechnology"], "纳米定位"),
                ("nanoribbon", "Nanoribbons", ["nanotechnology"], "纳米带"),
                ("nanorod", "Nanorods", ["nanotechnology"], "纳米棒"),
                ("nanoscale_devic", "Nanoscale Devices", ["nanotechnology"], "纳米尺度器件"),
                ("nanoscale_technology", "Nanoscale Technology", ["nanotechnology"], "纳米尺度技术"),
            ]
        )

    def test_exact_expansion_batch_539_adds_nanosensor_nanoshell_and_nanotube_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nanosensor", "Nanosensors", ["nanotechnology"], "纳米传感器"),
                ("nanoshell", "Nanoshells", ["biomedical"], "纳米壳"),
                ("nanospher", "Nanospheres", ["biomedical"], "纳米球"),
                ("nanostructured_material", "Nanostructured Materials", ["nanotechnology"], "纳米结构材料"),
                ("nanostructure", "Nanostructures", ["nanotechnology"], "纳米结构"),
                ("nanotechnology", "Nanotechnology", ["nanotechnology"], "纳米技术"),
                ("nanotube", "Nanotubes", ["nanotechnology"], "纳米管"),
                ("nanowire", "Nanowires", ["nanotechnology"], "纳米线"),
            ]
        )

    def test_exact_expansion_batch_540_adds_naphthalene_narcissism_and_nasal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("naphthalene", "Naphthalenes", ["biomedical", "chemicals_and_drugs"], "萘类"),
                ("naphthol", "Naphthols", ["biomedical", "chemicals_and_drugs"], "萘酚类"),
                ("naproxen", "Naproxen", ["biomedical", "chemicals_and_drugs"], "萘普生"),
                ("narcissism", "Narcissism", ["biomedical"], "自恋"),
                ("narcolepsy", "Narcolepsy", ["biomedical", "diseases"], "发作性睡病"),
                ("narcotic", "Narcotics", ["biomedical", "chemicals_and_drugs"], "麻醉药品"),
                ("nasal_bone", "Nasal Bone", ["biomedical"], "鼻骨"),
                ("nasal_cavity", "Nasal Cavity", ["biomedical"], "鼻腔"),
            ]
        )

    def test_exact_expansion_batch_541_adds_nasal_mucosa_obstruction_and_polyp_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nasal_decongestant", "Nasal Decongestants", ["biomedical", "chemicals_and_drugs"], "鼻减充血剂"),
                ("nasal_lavage", "Nasal Lavage", ["biomedical"], "鼻腔灌洗"),
                ("nasal_lavage_fluid", "Nasal Lavage Fluid", ["biomedical"], "鼻腔灌洗液"),
                ("nasal_mucosa", "Nasal Mucosa", ["biomedical"], "鼻黏膜"),
                ("nasal_obstruction", "Nasal Obstruction", ["biomedical", "diseases"], "鼻阻塞"),
                ("nasal_polyp", "Nasal Polyps", ["biomedical", "diseases"], "鼻息肉"),
                ("nasal_provocation_test", "Nasal Provocation Tests", ["biomedical"], "鼻激发试验"),
                ("nasal_septal_perforation", "Nasal Septal Perforation", ["biomedical", "diseases"], "鼻中隔穿孔"),
            ]
        )

    def test_exact_expansion_batch_542_adds_nasal_septum_nash_and_nasolacrimal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nasal_septum", "Nasal Septum", ["biomedical"], "鼻中隔"),
                ("nasal_spray", "Nasal Sprays", ["biomedical", "chemicals_and_drugs"], "鼻喷雾剂"),
                ("nasal_surgical_procedur", "Nasal Surgical Procedures", ["biomedical"], "鼻部外科手术"),
                ("nash_bargaining_solution", "Nash Bargaining Solution", ["computer_science"], "纳什讨价还价解"),
                ("nash_equilibria", "Nash Equilibria", ["computer_science"], "纳什均衡"),
                ("nasoalveolar_molding", "Nasoalveolar Molding", ["biomedical"], "鼻牙槽塑形"),
                ("nasolabial_fold", "Nasolabial Fold", ["biomedical"], "鼻唇沟"),
                ("nasolacrimal_duct", "Nasolacrimal Duct", ["biomedical"], "鼻泪管"),
            ]
        )

    def test_exact_expansion_batch_543_adds_nasopharyngeal_and_natal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nasolacrimal_duct_obstruction_treatment", "Nasolacrimal Duct Obstruction Treatments", ["medicine"], "鼻泪管阻塞治疗"),
                ("nasopharyngeal_carcinoma", "Nasopharyngeal Carcinoma", ["biomedical", "diseases"], "鼻咽癌"),
                ("nasopharyngeal_disease", "Nasopharyngeal Diseases", ["biomedical", "diseases"], "鼻咽疾病"),
                ("nasopharyngeal_neoplasm", "Nasopharyngeal Neoplasms", ["biomedical", "diseases"], "鼻咽肿瘤"),
                ("nasopharyngiti", "Nasopharyngitis", ["biomedical", "diseases"], "鼻咽炎"),
                ("nasturtium", "Nasturtium", ["biomedical", "organisms"], "旱金莲属"),
                ("natal_teeth", "Natal Teeth", ["biomedical"], "出生牙"),
                ("natalizumab", "Natalizumab", ["biomedical", "chemicals_and_drugs"], "那他珠单抗"),
            ]
        )

    def test_exact_expansion_batch_544_adds_natamycin_nateglinide_and_natriuretic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("natamycin", "Natamycin", ["biomedical", "chemicals_and_drugs"], "那他霉素"),
                ("nateglinide", "Nateglinide", ["biomedical", "chemicals_and_drugs"], "那格列奈"),
                ("native_polyacrylamide_gel_electrophoresi", "Native Polyacrylamide Gel Electrophoresis", ["biomedical"], "非变性聚丙烯酰胺凝胶电泳"),
                ("natriuresi", "Natriuresis", ["biomedical"], "利钠"),
                ("natriuretic_agent", "Natriuretic Agents", ["biomedical", "chemicals_and_drugs"], "利钠剂"),
                ("natriuretic_peptid", "Natriuretic Peptides", ["biomedical", "chemicals_and_drugs"], "利钠肽"),
                ("natriuretic_peptide_brain", "Natriuretic Peptide, Brain", ["biomedical", "chemicals_and_drugs"], "脑钠肽"),
                ("natriuretic_peptide_c_type", "Natriuretic Peptide, C-type", ["biomedical", "chemicals_and_drugs"], "C型利钠肽"),
            ]
        )

    def test_exact_expansion_batch_545_adds_natural_cytotoxicity_language_and_surgery_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("natural_childbirth", "Natural Childbirth", ["biomedical"], "自然分娩"),
                ("natural_cytotoxicity_triggering_receptor_1", "Natural Cytotoxicity Triggering Receptor 1", ["biomedical", "chemicals_and_drugs"], "自然细胞毒性触发受体1"),
                ("natural_cytotoxicity_triggering_receptor_2", "Natural Cytotoxicity Triggering Receptor 2", ["biomedical", "chemicals_and_drugs"], "自然细胞毒性触发受体2"),
                ("natural_cytotoxicity_triggering_receptor_3", "Natural Cytotoxicity Triggering Receptor 3", ["biomedical", "chemicals_and_drugs"], "自然细胞毒性触发受体3"),
                ("natural_deduction", "Natural Deduction", ["computer_science"], "自然演绎"),
                ("natural_disaster", "Natural Disasters", ["biomedical"], "自然灾害"),
                ("natural_killer_t_cell", "Natural Killer T-cells", ["biomedical"], "自然杀伤T细胞"),
                ("natural_language_understanding", "Natural Language Understanding", ["computer_science"], "自然语言理解"),
            ]
        )

    def test_exact_expansion_batch_546_adds_natural_product_resource_and_nausea_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("natural_orifice_endoscopic_surgery", "Natural Orifice Endoscopic Surgery", ["biomedical"], "经自然腔道内镜手术"),
                ("natural_product_bioactivity_and_synthesi", "Natural Product Bioactivities And Synthesis", ["life_sciences"], "天然产物生物活性与合成"),
                ("natural_resistance_associated_macrophage_protein_1", "Natural Resistance-associated Macrophage Protein 1", ["biomedical", "chemicals_and_drugs"], "自然抗性相关巨噬细胞蛋白1"),
                ("natural_science_disciplin", "Natural Science Disciplines", ["biomedical"], "自然科学学科"),
                ("natural_spring", "Natural Springs", ["biomedical"], "天然泉"),
                ("naturopathy", "Naturopathy", ["biomedical"], "自然疗法"),
                ("nausea_and_vomiting_management", "Nausea And Vomiting Management", ["medicine"], "恶心呕吐管理"),
                ("nautilu", "Nautilus", ["biomedical", "organisms"], "鹦鹉螺属"),
            ]
        )

    def test_exact_expansion_batch_547_adds_nav_voltage_gated_sodium_channel_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nav1_1_voltage_gated_sodium_channel", "Nav1.1 Voltage-gated Sodium Channel", ["biomedical", "chemicals_and_drugs"], "Nav1.1电压门控钠通道"),
                ("nav1_2_voltage_gated_sodium_channel", "Nav1.2 Voltage-gated Sodium Channel", ["biomedical", "chemicals_and_drugs"], "Nav1.2电压门控钠通道"),
                ("nav1_3_voltage_gated_sodium_channel", "Nav1.3 Voltage-gated Sodium Channel", ["biomedical", "chemicals_and_drugs"], "Nav1.3电压门控钠通道"),
                ("nav1_4_voltage_gated_sodium_channel", "Nav1.4 Voltage-gated Sodium Channel", ["biomedical", "chemicals_and_drugs"], "Nav1.4电压门控钠通道"),
                ("nav1_5_voltage_gated_sodium_channel", "Nav1.5 Voltage-gated Sodium Channel", ["biomedical", "chemicals_and_drugs"], "Nav1.5电压门控钠通道"),
                ("nav1_6_voltage_gated_sodium_channel", "Nav1.6 Voltage-gated Sodium Channel", ["biomedical", "chemicals_and_drugs"], "Nav1.6电压门控钠通道"),
                ("nav1_7_voltage_gated_sodium_channel", "Nav1.7 Voltage-gated Sodium Channel", ["biomedical", "chemicals_and_drugs"], "Nav1.7电压门控钠通道"),
                ("nav1_8_voltage_gated_sodium_channel", "Nav1.8 Voltage-gated Sodium Channel", ["biomedical", "chemicals_and_drugs"], "Nav1.8电压门控钠通道"),
            ]
        )

    def test_exact_expansion_batch_548_adds_navigation_neanderthal_and_near_drowning_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nav1_9_voltage_gated_sodium_channel", "Nav1.9 Voltage-gated Sodium Channel", ["biomedical", "chemicals_and_drugs"], "Nav1.9电压门控钠通道"),
                ("navajo_people", "Navajo People", ["biomedical", "named_groups"], "纳瓦霍人"),
                ("naval_medicine", "Naval Medicine", ["biomedical"], "海军医学"),
                ("navier_stok_equation_solution", "Navier-stokes Equation Solutions", ["mathematics"], "纳维-斯托克斯方程解"),
                ("nc_machining", "Nc Machining", ["computer_science"], "数控加工"),
                ("nd_yag", "Nd: Yag", ["computer_science"], "掺钕钇铝石榴石"),
                ("nd_yag_laser", "Nd:yag Laser", ["computer_science"], "Nd:YAG激光器"),
                ("neanderthal", "Neanderthals", ["biomedical", "organisms"], "尼安德特人"),
            ]
        )

    def test_exact_expansion_batch_549_adds_near_field_near_infrared_and_nebivolol_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("near_drowning", "Near Drowning", ["biomedical", "diseases"], "近乎溺水"),
                ("near_field_communication", "Near Field Communication", ["computer_science"], "近场通信"),
                ("near_field_optical_microscopy", "Near-field Optical Microscopy", ["engineering"], "近场光学显微镜"),
                ("near_field_radiation_pattern", "Near-field Radiation Pattern", ["antennas_and_propagation"], "近场辐射方向图"),
                ("near_field_scanning_optical_microscopy", "Near Field Scanning Optical Microscopy", ["computer_science"], "近场扫描光学显微镜"),
                ("near_infrared_imaging", "Near-infrared Imaging", ["computer_science"], "近红外成像"),
                ("near_miss_healthcare", "Near Miss, Healthcare", ["biomedical"], "医疗险些事件"),
                ("near_optimal_solution", "Near-optimal Solutions", ["computer_science"], "近似最优解"),
            ]
        )

    def test_exact_expansion_batch_550_adds_nebivolol_necator_and_neck_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nebivolol", "Nebivolol", ["biomedical", "chemicals_and_drugs"], "奈必洛尔"),
                ("nebramycin", "Nebramycin", ["biomedical", "chemicals_and_drugs"], "奈布霉素"),
                ("nebraska", "Nebraska", ["biomedical"], "内布拉斯加州"),
                ("nebulizer_and_vaporizer", "Nebulizers And Vaporizers", ["biomedical"], "雾化器和汽化器"),
                ("necator", "Necator", ["biomedical", "organisms"], "美洲钩虫属"),
                ("necator_americanu", "Necator Americanus", ["biomedical", "organisms"], "美洲钩虫"),
                ("necatoriasi", "Necatoriasis", ["biomedical", "diseases"], "美洲钩虫病"),
                ("neck", "Neck", ["biomedical"], "颈部"),
            ]
        )

    def test_exact_expansion_batch_551_adds_neck_and_necrobiotic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neck_dissection", "Neck Dissection", ["biomedical"], "颈清扫术"),
                ("neck_injury", "Neck Injuries", ["biomedical", "diseases"], "颈部损伤"),
                ("neck_muscl", "Neck Muscles", ["biomedical"], "颈肌"),
                ("neck_pain", "Neck Pain", ["biomedical", "diseases"], "颈痛"),
                ("necrobiosi_lipoidica", "Necrobiosis Lipoidica", ["biomedical", "diseases"], "类脂质渐进性坏死"),
                ("necrobiotic_xanthogranuloma", "Necrobiotic Xanthogranuloma", ["biomedical", "diseases"], "坏死性黄色肉芽肿"),
                ("necrolytic_migratory_erythema", "Necrolytic Migratory Erythema", ["biomedical", "diseases"], "坏死性游走性红斑"),
                ("necroptosi", "Necroptosis", ["biomedical"], "程序性坏死"),
            ]
        )

    def test_exact_expansion_batch_552_adds_nectin_needles_and_needlestick_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nectin", "Nectins", ["biomedical", "chemicals_and_drugs"], "连接素"),
                ("nedocromil", "Nedocromil", ["biomedical", "chemicals_and_drugs"], "奈多罗米"),
                ("need_assessment", "Needs Assessment", ["biomedical"], "需求评估"),
                ("needl", "Needles", ["industry_applications"], "针具"),
                ("needle_exchange_program", "Needle-exchange Programs", ["biomedical"], "针具交换项目"),
                ("needle_insertion", "Needle Insertion", ["computer_science"], "进针"),
                ("needle_sharing", "Needle Sharing", ["biomedical"], "共用针具"),
                ("needlestick_injury", "Needlestick Injuries", ["biomedical", "diseases"], "针刺伤"),
            ]
        )

    def test_exact_expansion_batch_553_adds_nefopam_negative_and_negativism_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nef_gene_product_human_immunodeficiency_viru", "Nef Gene Products, Human Immunodeficiency Virus", ["biomedical", "chemicals_and_drugs"], "HIV Nef基因产物"),
                ("nefopam", "Nefopam", ["biomedical", "chemicals_and_drugs"], "奈福泮"),
                ("negative_permittivity", "Negative Permittivity", ["computer_science"], "负介电常数"),
                ("negative_pressure_wound_therapy", "Negative-pressure Wound Therapy", ["biomedical"], "负压创面治疗"),
                ("negative_result", "Negative Results", ["biomedical"], "阴性结果"),
                ("negative_sense_rna_viruse", "Negative-sense RNA Viruses", ["biomedical", "organisms"], "负链RNA病毒"),
                ("negative_staining", "Negative Staining", ["biomedical"], "负染色"),
                ("negativism", "Negativism", ["biomedical"], "违拗症"),
            ]
        )

    def test_exact_expansion_batch_554_adds_neglected_neighborhood_and_neisseria_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neglected_disease", "Neglected Diseases", ["biomedical", "diseases"], "被忽视疾病"),
                ("negotiating", "Negotiating", ["biomedical"], "谈判"),
                ("neighborhood_characteristic", "Neighborhood Characteristics", ["biomedical"], "邻里特征"),
                ("neighborhood_graph", "Neighborhood Graphs", ["computer_science"], "邻域图"),
                ("neighborhood_structure", "Neighborhood Structure", ["computer_science"], "邻域结构"),
                ("neisseria", "Neisseria", ["biomedical", "organisms"], "奈瑟菌属"),
                ("neisseria_cinerea", "Neisseria Cinerea", ["biomedical", "organisms"], "灰色奈瑟菌"),
                ("neisseria_elongata", "Neisseria Elongata", ["biomedical", "organisms"], "延长奈瑟菌"),
            ]
        )

    def test_exact_expansion_batch_555_adds_neisseria_gonorrhoeae_and_meningitidis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neisseria_gonorrhoeae", "Neisseria Gonorrhoeae", ["biomedical", "organisms"], "淋病奈瑟菌"),
                ("neisseria_lactamica", "Neisseria Lactamica", ["biomedical", "organisms"], "乳糖奈瑟菌"),
                ("neisseria_meningitidi", "Neisseria Meningitidis", ["biomedical", "organisms"], "脑膜炎奈瑟菌"),
                ("neisseria_meningitidi_serogroup_a", "Neisseria Meningitidis, Serogroup A", ["biomedical", "organisms"], "A群脑膜炎奈瑟菌"),
                ("neisseria_meningitidi_serogroup_b", "Neisseria Meningitidis, Serogroup B", ["biomedical", "organisms"], "B群脑膜炎奈瑟菌"),
                ("neisseria_meningitidi_serogroup_c", "Neisseria Meningitidis, Serogroup C", ["biomedical", "organisms"], "C群脑膜炎奈瑟菌"),
                ("neisseria_meningitidi_serogroup_w_135", "Neisseria Meningitidis, Serogroup W-135", ["biomedical", "organisms"], "W-135群脑膜炎奈瑟菌"),
                ("neisseria_meningitidi_serogroup_y", "Neisseria Meningitidis, Serogroup Y", ["biomedical", "organisms"], "Y群脑膜炎奈瑟菌"),
            ]
        )

    def test_exact_expansion_batch_556_adds_neisseriaceae_nelfinavir_and_nelumbo_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neisseria_mucosa", "Neisseria Mucosa", ["biomedical", "organisms"], "黏膜奈瑟菌"),
                ("neisseria_sicca", "Neisseria Sicca", ["biomedical", "organisms"], "干燥奈瑟菌"),
                ("neisseriaceae", "Neisseriaceae", ["biomedical", "organisms"], "奈瑟菌科"),
                ("neisseriaceae_infection", "Neisseriaceae Infections", ["biomedical", "diseases"], "奈瑟菌科感染"),
                ("nelfinavir", "Nelfinavir", ["biomedical", "chemicals_and_drugs"], "奈非那韦"),
                ("nelson_syndrome", "Nelson Syndrome", ["biomedical", "diseases"], "纳尔逊综合征"),
                ("nelumbo", "Nelumbo", ["biomedical", "organisms"], "莲属"),
                ("nelumbonaceae", "Nelumbonaceae", ["biomedical", "organisms"], "莲科"),
            ]
        )

    def test_exact_expansion_batch_557_adds_nematoda_neoadjuvant_and_neodymium_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nematocera", "Nematocera", ["biomedical", "organisms"], "长角亚目"),
                ("nematocyst", "Nematocyst", ["biomedical"], "刺丝囊"),
                ("nematoda", "Nematoda", ["biomedical", "organisms"], "线虫动物门"),
                ("nematode_infection", "Nematode Infections", ["biomedical", "diseases"], "线虫感染"),
                ("neoadjuvant_therapy", "Neoadjuvant Therapy", ["biomedical"], "新辅助治疗"),
                ("neocortex", "Neocortex", ["biomedical"], "新皮层"),
                ("neodymium", "Neodymium", ["materials_elements_and_compounds"], "钕元素"),
                ("neodymium_alloy", "Neodymium Alloys", ["materials_elements_and_compounds"], "钕合金"),
            ]
        )

    def test_exact_expansion_batch_558_adds_neodymium_neonatal_and_neomycin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neodymium_compound", "Neodymium Compounds", ["materials_elements_and_compounds"], "钕化合物"),
                ("neodymium_laser", "Neodymium Lasers", ["computer_science"], "钕激光器"),
                ("neointima", "Neointima", ["biomedical", "diseases"], "新生内膜"),
                ("neomycin", "Neomycin", ["biomedical", "chemicals_and_drugs"], "新霉素"),
                ("neon", "Neon", ["materials_elements_and_compounds"], "氖元素"),
                ("neonatal_abstinence_syndrome", "Neonatal Abstinence Syndrome", ["biomedical", "diseases"], "新生儿戒断综合征"),
                ("neonatal_and_maternal_infection", "Neonatal And Maternal Infections", ["medicine"], "新生儿和母体感染"),
                ("neonatal_brachial_plexu_palsy", "Neonatal Brachial Plexus Palsy", ["biomedical", "diseases"], "新生儿臂丛神经麻痹"),
            ]
        )

    def test_exact_expansion_batch_559_adds_neonatal_neonicotinoid_and_neoplasm_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neonatal_screening", "Neonatal Screening", ["biomedical"], "新生儿筛查"),
                ("neonatal_sepsi", "Neonatal Sepsis", ["biomedical", "diseases"], "新生儿败血症"),
                ("neonatologist", "Neonatologists", ["biomedical"], "新生儿科医师"),
                ("neonatology", "Neonatology", ["engineering_in_medicine_and_biology"], "新生儿学"),
                ("neonicotinoid", "Neonicotinoids", ["biomedical", "chemicals_and_drugs"], "新烟碱类"),
                ("neoplasm_adipose_tissue", "Neoplasms, Adipose Tissue", ["biomedical", "diseases"], "脂肪组织肿瘤"),
                ("neoplasm_adnexal_and_skin_appendage", "Neoplasms, Adnexal And Skin Appendage", ["biomedical", "diseases"], "附属器和皮肤附件肿瘤"),
                ("neoplasm_basal_cell", "Neoplasms, Basal Cell", ["biomedical", "diseases"], "基底细胞肿瘤"),
            ]
        )

    def test_exact_expansion_batch_560_adds_neoplasm_complex_connective_and_germ_cell_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neoplasm_complex_and_mixed", "Neoplasms, Complex And Mixed", ["biomedical", "diseases"], "复杂和混合性肿瘤"),
                ("neoplasm_connective_and_soft_tissue", "Neoplasms, Connective And Soft Tissue", ["biomedical", "diseases"], "结缔组织和软组织肿瘤"),
                ("neoplasm_connective_tissue", "Neoplasms, Connective Tissue", ["biomedical", "diseases"], "结缔组织肿瘤"),
                ("neoplasm_cystic_mucinou_and_serou", "Neoplasms, Cystic, Mucinous, And Serous", ["biomedical", "diseases"], "囊性黏液性和浆液性肿瘤"),
                ("neoplasm_experimental", "Neoplasms, Experimental", ["biomedical", "diseases"], "实验性肿瘤"),
                ("neoplasm_fibroepithelial", "Neoplasms, Fibroepithelial", ["biomedical", "diseases"], "纤维上皮性肿瘤"),
                ("neoplasm_fibrou_tissue", "Neoplasms, Fibrous Tissue", ["biomedical", "diseases"], "纤维组织肿瘤"),
                ("neoplasm_germ_cell_and_embryonal", "Neoplasms, Germ Cell And Embryonal", ["biomedical", "diseases"], "生殖细胞和胚胎性肿瘤"),
            ]
        )

    def test_exact_expansion_batch_561_adds_neoplasm_grading_and_metastasis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neoplasm_grading", "Neoplasm Grading", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "肿瘤分级"),
                ("neoplasm_invasiveness", "Neoplasm Invasiveness", ["biomedical", "diseases"], "肿瘤侵袭性"),
                ("neoplasm_metastasi", "Neoplasm Metastasis", ["biomedical", "diseases"], "肿瘤转移"),
                ("neoplasm_micrometastasi", "Neoplasm Micrometastasis", ["biomedical", "diseases"], "肿瘤微转移"),
                ("neoplasm_protein", "Neoplasm Proteins", ["biomedical", "chemicals_and_drugs"], "肿瘤蛋白"),
                ("neoplasm_recurrence_local", "Neoplasm Recurrence, Local", ["biomedical", "diseases"], "局部肿瘤复发"),
                ("neoplasm_regression_spontaneou", "Neoplasm Regression, Spontaneous", ["biomedical", "diseases"], "肿瘤自发消退"),
                ("neoplasm_seeding", "Neoplasm Seeding", ["biomedical", "diseases"], "肿瘤种植"),
            ]
        )

    def test_exact_expansion_batch_562_adds_neoplasm_staging_and_classification_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neoplasm_staging", "Neoplasm Staging", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "肿瘤分期"),
                ("neoplasm_transplantation", "Neoplasm Transplantation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "肿瘤移植"),
                ("neoplasm_lymphatic_tissue", "Neoplasm, Lymphatic Tissue", ["biomedical", "diseases"], "淋巴组织肿瘤"),
                ("neoplasm_residual", "Neoplasm, Residual", ["biomedical", "diseases"], "残留肿瘤"),
                ("neoplasm", "Neoplasms", ["biomedical", "diseases"], "肿瘤"),
                ("neoplasm_by_histologic_type", "Neoplasms By Histologic Type", ["biomedical", "diseases"], "按组织学类型分类的肿瘤"),
                ("neoplasm_by_site", "Neoplasms By Site", ["biomedical", "diseases"], "按部位分类的肿瘤"),
                ("neoplasm_bone_tissue", "Neoplasms, Bone Tissue", ["biomedical", "diseases"], "骨组织肿瘤"),
            ]
        )

    def test_exact_expansion_batch_563_adds_neoplasm_tissue_type_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neoplasm_ductal_lobular_and_medullary", "Neoplasms, Ductal, Lobular, And Medullary", ["biomedical", "diseases"], "导管性小叶性和髓样肿瘤"),
                ("neoplasm_glandular_and_epithelial", "Neoplasms, Glandular And Epithelial", ["biomedical", "diseases"], "腺性和上皮性肿瘤"),
                ("neoplasm_gonadal_tissue", "Neoplasms, Gonadal Tissue", ["biomedical", "diseases"], "性腺组织肿瘤"),
                ("neoplasm_hormone_dependent", "Neoplasms, Hormone-dependent", ["biomedical", "diseases"], "激素依赖性肿瘤"),
                ("neoplasm_mesothelial", "Neoplasms, Mesothelial", ["biomedical", "diseases"], "间皮性肿瘤"),
                ("neoplasm_multiple_primary", "Neoplasms, Multiple Primary", ["biomedical", "diseases"], "多原发肿瘤"),
                ("neoplasm_muscle_tissue", "Neoplasms, Muscle Tissue", ["biomedical", "diseases"], "肌肉组织肿瘤"),
                ("neoplasm_nerve_tissue", "Neoplasms, Nerve Tissue", ["biomedical", "diseases"], "神经组织肿瘤"),
            ]
        )

    def test_exact_expansion_batch_564_adds_neoplasm_origin_and_primary_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neoplasm_neuroepithelial", "Neoplasms, Neuroepithelial", ["biomedical", "diseases"], "神经上皮性肿瘤"),
                ("neoplasm_plasma_cell", "Neoplasms, Plasma Cell", ["biomedical", "diseases"], "浆细胞肿瘤"),
                ("neoplasm_post_traumatic", "Neoplasms, Post-traumatic", ["biomedical", "diseases"], "创伤后肿瘤"),
                ("neoplasm_radiation_induced", "Neoplasms, Radiation-induced", ["biomedical", "diseases"], "放射诱发性肿瘤"),
                ("neoplasm_second_primary", "Neoplasms, Second Primary", ["biomedical", "diseases"], "第二原发肿瘤"),
                ("neoplasm_squamou_cell", "Neoplasms, Squamous Cell", ["biomedical", "diseases"], "鳞状细胞肿瘤"),
                ("neoplasm_unknown_primary", "Neoplasms, Unknown Primary", ["biomedical", "diseases"], "原发灶不明肿瘤"),
                ("neoplasm_vascular_tissue", "Neoplasms, Vascular Tissue", ["biomedical", "diseases"], "血管组织肿瘤"),
            ]
        )

    def test_exact_expansion_batch_565_adds_neoplastic_neoprene_and_neorickettsia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neoplastic_cell_circulating", "Neoplastic Cells, Circulating", ["anatomy", "biomedical"], "循环肿瘤细胞"),
                ("neoplastic_processe", "Neoplastic Processes", ["biomedical", "diseases"], "肿瘤性过程"),
                ("neoplastic_stem_cell", "Neoplastic Stem Cells", ["anatomy", "biomedical"], "肿瘤干细胞"),
                ("neoplastic_syndrom_hereditary", "Neoplastic Syndromes, Hereditary", ["biomedical", "diseases"], "遗传性肿瘤综合征"),
                ("neoprene", "Neoprene", ["biomedical", "chemicals_and_drugs"], "氯丁橡胶"),
                ("neoptera", "Neoptera", ["biomedical", "organisms"], "新翅类"),
                ("neopterin", "Neopterin", ["biomedical", "chemicals_and_drugs"], "新蝶呤"),
                ("neorickettsia", "Neorickettsia", ["biomedical", "organisms"], "新立克次体属"),
            ]
        )

    def test_exact_expansion_batch_566_adds_neorickettsia_neospora_and_neovascularization_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neorickettsia_risticii", "Neorickettsia Risticii", ["biomedical", "organisms"], "里氏新立克次体"),
                ("neorickettsia_sennetsu", "Neorickettsia Sennetsu", ["biomedical", "organisms"], "腺热新立克次体"),
                ("neosartorya", "Neosartorya", ["biomedical", "organisms"], "新萨托菌属"),
                ("neospora", "Neospora", ["biomedical", "organisms"], "新孢子虫属"),
                ("neostigmine", "Neostigmine", ["biomedical", "chemicals_and_drugs"], "新斯的明"),
                ("neostriatum", "Neostriatum", ["anatomy", "biomedical"], "新纹状体"),
                ("neotyphodium", "Neotyphodium", ["biomedical", "organisms"], "新麦角菌属"),
                ("neovascularization_pathologic", "Neovascularization, Pathologic", ["biomedical", "diseases"], "病理性新生血管形成"),
            ]
        )

    def test_exact_expansion_batch_567_adds_neovascularization_nepal_and_nephritis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neovascularization_physiologic", "Neovascularization, Physiologic", ["biomedical", "phenomena_and_processes"], "生理性新生血管形成"),
                ("nepal", "Nepal", ["biomedical", "geographicals"], "尼泊尔"),
                ("nepeta", "Nepeta", ["biomedical", "organisms"], "荆芥属"),
                ("nephelometry_and_turbidimetry", "Nephelometry And Turbidimetry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "散射比浊法和透射比浊法"),
                ("nephrectomy", "Nephrectomy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "肾切除术"),
                ("nephriti", "Nephritis", ["biomedical", "diseases"], "肾炎"),
                ("nephriti_hereditary", "Nephritis, Hereditary", ["biomedical", "diseases"], "遗传性肾炎"),
                ("nephriti_interstitial", "Nephritis, Interstitial", ["biomedical", "diseases"], "间质性肾炎"),
            ]
        )

    def test_exact_expansion_batch_568_adds_nephroblastoma_nephrology_and_lithiasis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nephroblastoma_overexpressed_protein", "Nephroblastoma Overexpressed Protein", ["biomedical", "chemicals_and_drugs"], "肾母细胞瘤过表达蛋白"),
                ("nephrocalcinosi", "Nephrocalcinosis", ["biomedical", "diseases"], "肾钙质沉着症"),
                ("nephrogenic_fibrosing_dermopathy", "Nephrogenic Fibrosing Dermopathy", ["biomedical", "diseases"], "肾源性纤维化皮肤病"),
                ("nephrolithiasi", "Nephrolithiasis", ["biomedical", "diseases"], "肾结石"),
                ("nephrolithotomy_percutaneou", "Nephrolithotomy, Percutaneous", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "经皮肾镜取石术"),
                ("nephrologist", "Nephrologists", ["biomedical", "named_groups"], "肾脏科医师"),
                ("nephrology", "Nephrology", ["engineering_in_medicine_and_biology"], "肾脏病学"),
                ("nephrology_nursing", "Nephrology Nursing", ["biomedical", "disciplines_and_occupations"], "肾脏病护理"),
            ]
        )

    def test_exact_expansion_batch_569_adds_nephroma_nephron_and_nephrotic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nephroma_mesoblastic", "Nephroma, Mesoblastic", ["biomedical", "diseases"], "中胚叶肾瘤"),
                ("nephron", "Nephrons", ["anatomy", "biomedical"], "肾单位"),
                ("nephropidae", "Nephropidae", ["biomedical", "organisms"], "海螯虾科"),
                ("nephrosclerosi", "Nephrosclerosis", ["biomedical", "diseases"], "肾硬化"),
                ("nephrosi", "Nephrosis", ["biomedical", "diseases"], "肾病"),
                ("nephrosi_lipoid", "Nephrosis, Lipoid", ["biomedical", "diseases"], "脂性肾病"),
                ("nephrostomy_percutaneou", "Nephrostomy, Percutaneous", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "经皮肾造瘘术"),
                ("nephrotic_syndrome", "Nephrotic Syndrome", ["biomedical", "diseases"], "肾病综合征"),
            ]
        )

    def test_exact_expansion_batch_570_adds_nephrotomy_neprilysin_and_neptunium_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nephrotomy", "Nephrotomy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "肾切开术"),
                ("nephrotoxicity_and_medicinal_plant", "Nephrotoxicity And Medicinal Plants", ["health_sciences", "medicine"], "肾毒性与药用植物"),
                ("nephroureterectomy", "Nephroureterectomy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "肾输尿管切除术"),
                ("nepoviru", "Nepovirus", ["biomedical", "organisms"], "线虫传多面体病毒属"),
                ("neprilysin", "Neprilysin", ["biomedical", "chemicals_and_drugs"], "脑啡肽酶"),
                ("neptune", "Neptune", ["biomedical", "phenomena_and_processes"], "海王星"),
                ("neptunium", "Neptunium", ["materials_elements_and_compounds"], "镎元素"),
                ("nerium", "Nerium", ["biomedical", "organisms"], "夹竹桃属"),
            ]
        )

    def test_exact_expansion_batch_571_adds_nerve_agent_block_and_conduction_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nerve_agent", "Nerve Agents", ["biomedical", "chemicals_and_drugs"], "神经毒剂"),
                ("nerve_block", "Nerve Block", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经阻滞"),
                ("nerve_compression_syndrom", "Nerve Compression Syndromes", ["biomedical", "diseases"], "神经压迫综合征"),
                ("nerve_conduction_study", "Nerve Conduction Studies", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经传导检查"),
                ("nerve_crush", "Nerve Crush", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经挤压"),
                ("nerve_degeneration", "Nerve Degeneration", ["biomedical", "diseases"], "神经变性"),
                ("nerve_ending", "Nerve Endings", ["anatomy", "biomedical"], "神经末梢"),
                ("nerve_expansion", "Nerve Expansion", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经扩张"),
            ]
        )

    def test_exact_expansion_batch_572_adds_nerve_fiber_growth_and_regeneration_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nerve_fiber", "Nerve Fibers", ["anatomy", "biomedical"], "神经纤维"),
                ("nerve_fiber_myelinated", "Nerve Fibers, Myelinated", ["anatomy", "biomedical"], "有髓神经纤维"),
                ("nerve_fiber_unmyelinated", "Nerve Fibers, Unmyelinated", ["anatomy", "biomedical"], "无髓神经纤维"),
                ("nerve_growth_factor", "Nerve Growth Factors", ["biomedical", "chemicals_and_drugs"], "神经生长因子"),
                ("nerve_injury_and_regeneration", "Nerve Injury And Regeneration", ["life_sciences", "neuroscience"], "神经损伤与再生"),
                ("nerve_injury_and_rehabilitation", "Nerve Injury And Rehabilitation", ["health_sciences", "medicine"], "神经损伤与康复"),
                ("nerve_net", "Nerve Net", ["anatomy", "biomedical"], "神经网"),
                ("nerve_regeneration", "Nerve Regeneration", ["biomedical", "phenomena_and_processes"], "神经再生"),
            ]
        )

    def test_exact_expansion_batch_573_adds_nerve_tissue_and_nervous_system_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nerve_sheath_neoplasm", "Nerve Sheath Neoplasms", ["biomedical", "diseases"], "神经鞘肿瘤"),
                ("nerve_tissue", "Nerve Tissue", ["anatomy", "biomedical"], "神经组织"),
                ("nerve_tissue_protein", "Nerve Tissue Proteins", ["biomedical", "chemicals_and_drugs"], "神经组织蛋白"),
                ("nerve_transfer", "Nerve Transfer", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经移位术"),
                ("nervou_system", "Nervous System", ["anatomy", "biomedical"], "神经系统"),
                ("nervou_system_autoimmune_disease_experimental", "Nervous System Autoimmune Disease, Experimental", ["biomedical", "diseases"], "实验性神经系统自身免疫病"),
                ("nervou_system_disease", "Nervous System Diseases", ["biomedical", "diseases"], "神经系统疾病"),
                ("nervou_system_malformation", "Nervous System Malformations", ["biomedical", "diseases"], "神经系统畸形"),
            ]
        )

    def test_exact_expansion_batch_574_adds_nervous_system_nestin_and_net_zero_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nervou_system_neoplasm", "Nervous System Neoplasms", ["biomedical", "diseases"], "神经系统肿瘤"),
                ("nervou_system_physiological_phenomena", "Nervous System Physiological Phenomena", ["biomedical", "phenomena_and_processes"], "神经系统生理现象"),
                ("nesidioblastosi", "Nesidioblastosis", ["biomedical", "diseases"], "胰岛母细胞增生症"),
                ("nested_gen", "Nested Genes", ["biomedical", "phenomena_and_processes"], "嵌套基因"),
                ("nestin", "Nestin", ["biomedical", "chemicals_and_drugs"], "巢蛋白"),
                ("nesting_behavior", "Nesting Behavior", ["biomedical", "psychiatry_and_psychology"], "筑巢行为"),
                ("net_zero", "Net Zero", ["industry_applications"], "净零"),
                ("net_zero_water", "Net Zero Water", ["industry_applications"], "净零用水"),
            ]
        )

    def test_exact_expansion_batch_575_adds_netherlands_netrin_and_netherton_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("netherland", "Netherlands", ["biomedical", "geographicals"], "荷兰"),
                ("netherland_antill", "Netherlands Antilles", ["biomedical", "geographicals"], "荷属安的列斯"),
                ("netherton_syndrome", "Netherton Syndrome", ["biomedical", "diseases"], "内瑟顿综合征"),
                ("netilmicin", "Netilmicin", ["biomedical", "chemicals_and_drugs"], "奈替米星"),
                ("netrin_receptor", "Netrin Receptors", ["biomedical", "chemicals_and_drugs"], "神经导向因子受体"),
                ("netrin_1", "Netrin-1", ["biomedical", "chemicals_and_drugs"], "神经导向因子1"),
                ("netrin", "Netrins", ["biomedical", "chemicals_and_drugs"], "神经导向因子"),
                ("network_address_translation", "Network Address Translation", ["computers_and_information_processing"], "网络地址转换"),
            ]
        )

    def test_exact_expansion_batch_576_adds_network_address_analysis_and_architecture_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("network_address_translation__2", "Network Address Translations", ["computer_science"], "网络地址转换"),
                ("network_analysi", "Network Analysis", ["computer_science"], "网络分析"),
                ("network_analyzer__2", "Network Analyzer", ["computer_science"], "网络分析仪"),
                ("network_analyzer", "Network Analyzers", ["instrumentation_and_measurement"], "网络分析仪"),
                ("network_anomaly", "Network Anomalies", ["computer_science"], "网络异常"),
                ("network_anomaly_detection", "Network Anomaly Detection", ["computer_science"], "网络异常检测"),
                ("network_architecture", "Network Architecture", ["communications_technology", "computer_science"], "网络架构"),
                ("network_attack", "Network Attack", ["computer_science"], "网络攻击"),
            ]
        )

    def test_exact_expansion_batch_577_adds_network_coding_component_and_evolution_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("network_cod", "Network Codes", ["computer_science"], "网络码"),
                ("network_coding", "Network Coding", ["information_theory"], "网络编码"),
                ("network_coding__2", "Network Coding", ["computer_science"], "网络编码"),
                ("network_community", "Network Communities", ["computer_science"], "网络社区"),
                ("network_component", "Network Components", ["computer_science"], "网络组件"),
                ("network_congestion", "Network Congestion", ["computer_science"], "网络拥塞"),
                ("network_evolution", "Network Evolution", ["physics"], "网络演化"),
                ("network_forensic", "Network Forensics", ["computer_science"], "网络取证"),
            ]
        )

    def test_exact_expansion_batch_578_adds_network_function_interface_and_intrusion_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("network_formation_and_growth", "Network Formation & Growth", ["physics"], "网络形成与增长"),
                ("network_function_virtualization", "Network Function Virtualization", ["communications_technology"], "网络功能虚拟化"),
                ("network_function_virtualization__2", "Network Function Virtualization", ["computers_and_information_processing"], "网络功能虚拟化"),
                ("network_interface", "Network Interface", ["computer_science"], "网络接口"),
                ("network_interfac", "Network Interfaces", ["computers_and_information_processing"], "网络接口"),
                ("network_intrusion", "Network Intrusion", ["computer_science"], "网络入侵"),
                ("network_intrusion_detection", "Network Intrusion Detection", ["computer_science"], "网络入侵检测"),
                ("network_intrusion_detection_system", "Network Intrusion Detection Systems", ["computer_science"], "网络入侵检测系统"),
            ]
        )

    def test_exact_expansion_batch_579_adds_network_latency_management_and_model_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("network_latency", "Network Latencies", ["computer_science"], "网络时延"),
                ("network_layer", "Network Layers", ["computer_science"], "网络层"),
                ("network_life_time", "Network Life-time", ["computer_science"], "网络寿命"),
                ("network_management", "Network Management", ["computer_science"], "网络管理"),
                ("network_management_system", "Network Management System", ["computer_science"], "网络管理系统"),
                ("network_mobility", "Network Mobility", ["computer_science"], "网络移动性"),
                ("network_model", "Network Models", ["physics"], "网络模型"),
                ("network_monitoring", "Network Monitoring", ["computer_science"], "网络监测"),
            ]
        )

    def test_exact_expansion_batch_580_adds_network_motif_chip_and_optimization_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("network_motif", "Network Motifs", ["mathematics"], "网络模体"),
                ("network_of_workstation", "Network Of Workstations", ["computer_science"], "工作站网络"),
                ("network_on_chip", "Network On Chip", ["computer_science"], "片上网络"),
                ("network_operation", "Network Operations", ["computer_science"], "网络运维"),
                ("network_optimization", "Network Optimization", ["physics"], "网络优化"),
                ("network_packet_processing_and_optimization", "Network Packet Processing And Optimization", ["computer_science", "physical_sciences"], "网络包处理与优化"),
                ("network_path", "Network Paths", ["computer_science"], "网络路径"),
                ("network_performance", "Network Performance", ["computer_science"], "网络性能"),
            ]
        )

    def test_exact_expansion_batch_581_adds_network_pharmacology_protocol_and_routing_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("network_pharmacology", "Network Pharmacology", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "网络药理学"),
                ("network_phase_transition", "Network Phase Transitions", ["physics"], "网络相变"),
                ("network_protocol", "Network Protocols", ["computer_science"], "网络协议"),
                ("network_reconnaissance", "Network Reconnaissance", ["industry_applications"], "网络侦察"),
                ("network_routing", "Network Routing", ["computer_science"], "网络路由"),
                ("network_search", "Network Searches", ["physics"], "网络搜索"),
                ("network_security__2", "Network Security", ["computer_science"], "网络安全"),
                ("network_selection", "Network Selection", ["computer_science"], "网络选择"),
            ]
        )

    def test_exact_expansion_batch_582_adds_network_server_service_and_slicing_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("network_security_and_intrusion_detection", "Network Security And Intrusion Detection", ["computer_science", "physical_sciences"], "网络安全与入侵检测"),
                ("network_server", "Network Servers", ["communications_technology"], "网络服务器"),
                ("network_server__2", "Network Servers", ["computers_and_information_processing"], "网络服务器"),
                ("network_servic", "Network Services", ["computer_science"], "网络服务"),
                ("network_slicing", "Network Slicing", ["communications_technology"], "网络切片"),
                ("network_stability", "Network Stability", ["physics"], "网络稳定性"),
                ("network_strategy", "Network Strategy", ["computer_science"], "网络策略"),
                ("network_structure", "Network Structure", ["physics"], "网络结构"),
            ]
        )

    def test_exact_expansion_batch_583_adds_network_survivability_theory_and_traffic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("network_survivability", "Network Survivability", ["computer_science"], "网络生存性"),
                ("network_synthesi", "Network Synthesis", ["computers_and_information_processing"], "网络综合"),
                ("network_system", "Network Systems", ["systems_engineering_and_theory"], "网络系统"),
                ("network_theory_graph", "Network Theory (graphs)", ["computers_and_information_processing"], "网络理论"),
                ("network_time_synchronization_technology", "Network Time Synchronization Technologies", ["computer_science", "physical_sciences"], "网络时间同步技术"),
                ("network_topology", "Network Topology", ["communications_technology", "computer_science"], "网络拓扑"),
                ("network_traffic", "Network Traffic", ["computer_science"], "网络流量"),
                ("network_traffic_and_congestion_control", "Network Traffic And Congestion Control", ["computer_science", "physical_sciences"], "网络流量与拥塞控制"),
            ]
        )

    def test_exact_expansion_batch_584_adds_network_classification_virtualization_and_networked_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("network_traffic_classification", "Network Traffic Classification", ["computer_science"], "网络流量分类"),
                ("network_utility_maximization", "Network Utility Maximization", ["computer_science"], "网络效用最大化"),
                ("network_virtualization", "Network Virtualization", ["computer_science"], "网络虚拟化"),
                ("network_visualization", "Network Visualization", ["computer_science"], "网络可视化"),
                ("network_induced_delay", "Network-induced Delay", ["computer_science"], "网络诱导时延"),
                ("network_on_chip_architectur", "Network-on-chip Architectures", ["computer_science"], "片上网络架构"),
                ("networked_control", "Networked Control", ["computer_science"], "网络化控制"),
                ("networked_control_system__2", "Networked Control System", ["computer_science"], "网络化控制系统"),
            ]
        )

    def test_exact_expansion_batch_585_adds_networked_system_and_neural_overview_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("networked_control_system_ncs", "Networked Control System (ncs)", ["computer_science"], "网络化控制系统"),
                ("networked_control_system", "Networked Control Systems", ["control_systems"], "网络化控制系统"),
                ("networked_system", "Networked Systems", ["computer_science"], "网络化系统"),
                ("networking_and_internet_architecture", "Networking And Internet Architecture", ["computer_science"], "网络与互联网架构"),
                ("network_and_random_structur", "Networks & Random Structures", ["physics"], "网络与随机结构"),
                ("network_analysi_tool", "Networks Analysis Tools", ["physics"], "网络分析工具"),
                ("neurabin", "Neurabins", ["biomedical", "chemicals_and_drugs"], "神经结合蛋白"),
                ("neural_and_behavioral_psychology_study", "Neural And Behavioral Psychology Studies", ["life_sciences", "neuroscience"], "神经与行为心理学研究"),
            ]
        )

    def test_exact_expansion_batch_586_adds_neural_computing_adhesion_and_circuit_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neural_and_evolutionary_computing", "Neural And Evolutionary Computing", ["computer_science"], "神经与进化计算"),
                ("neural_architecture_search", "Neural Architecture Search", ["computational_and_artificial_intelligence"], "神经架构搜索"),
                ("neural_cell_adhesion_molecule_l1", "Neural Cell Adhesion Molecule L1", ["biomedical", "chemicals_and_drugs"], "L1神经细胞黏附分子"),
                ("neural_cell_adhesion_molecul", "Neural Cell Adhesion Molecules", ["biomedical", "chemicals_and_drugs"], "神经细胞黏附分子"),
                ("neural_circuit", "Neural Circuits", ["circuits_and_systems"], "神经回路"),
                ("neural_circuit__2", "Neural Circuits", ["engineering_in_medicine_and_biology"], "神经回路"),
                ("neural_conduction", "Neural Conduction", ["biomedical", "phenomena_and_processes"], "神经传导"),
                ("neural_crest", "Neural Crest", ["anatomy", "biomedical"], "神经嵴"),
            ]
        )

    def test_exact_expansion_batch_587_adds_neural_engineering_translation_and_microtechnology_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neural_dynamic_and_brain_function", "Neural Dynamics And Brain Function", ["life_sciences", "neuroscience"], "神经动力学与脑功能"),
                ("neural_engineering", "Neural Engineering", ["engineering_in_medicine_and_biology"], "神经工程"),
                ("neural_fine_tuning", "Neural Fine-tuning", ["computer_science"], "神经微调"),
                ("neural_implant", "Neural Implants", ["engineering_in_medicine_and_biology"], "神经植入物"),
                ("neural_inhibition", "Neural Inhibition", ["biomedical", "phenomena_and_processes"], "神经抑制"),
                ("neural_machine_translation", "Neural Machine Translation", ["systems_man_and_cybernetics"], "神经机器翻译"),
                ("neural_microtechnology", "Neural Microtechnology", ["engineering_in_medicine_and_biology"], "神经微技术"),
                ("neural_nanotechnology", "Neural Nanotechnology", ["engineering_in_medicine_and_biology"], "神经纳米技术"),
            ]
        )

    def test_exact_expansion_batch_588_adds_neural_network_compression_and_hardware_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neural_network_compression", "Neural Network Compression", ["computational_and_artificial_intelligence"], "神经网络压缩"),
                ("neural_network_compression__2", "Neural Network Compression", ["computers_and_information_processing"], "神经网络压缩"),
                ("neural_network_hardware", "Neural Network Hardware", ["computational_and_artificial_intelligence"], "神经网络硬件"),
                ("neural_network_simulation", "Neural Network Simulations", ["physics"], "神经网络仿真"),
                ("neural_network", "Neural Networks", ["computational_and_artificial_intelligence"], "神经网络"),
                ("neural_network_and_application", "Neural Networks And Applications", ["computer_science", "physical_sciences"], "神经网络与应用"),
                ("neural_network_and_reservoir_computing", "Neural Networks And Reservoir Computing", ["computer_science", "physical_sciences"], "神经网络与储备池计算"),
                ("neural_network_stability_and_synchronization", "Neural Networks Stability And Synchronization", ["computer_science", "physical_sciences"], "神经网络稳定性与同步"),
            ]
        )

    def test_exact_expansion_batch_589_adds_neural_network_computer_pathway_and_prosthesis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neural_network_computer", "Neural Networks, Computer", ["biomedical", "phenomena_and_processes"], "计算机神经网络"),
                ("neural_pathway", "Neural Pathways", ["anatomy", "biomedical"], "神经通路"),
                ("neural_plate", "Neural Plate", ["anatomy", "biomedical"], "神经板"),
                ("neural_prosthese", "Neural Prostheses", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经假体"),
                ("neural_prosthesi", "Neural Prosthesis", ["engineering_in_medicine_and_biology"], "神经假体"),
                ("neural_radiance_field", "Neural Radiance Field", ["computers_and_information_processing"], "神经辐射场"),
                ("neural_radiance_field__2", "Neural Radiance Fields", ["computer_science"], "神经辐射场"),
                ("neural_stem_cell", "Neural Stem Cells", ["anatomy", "biomedical"], "神经干细胞"),
            ]
        )

    def test_exact_expansion_batch_590_adds_neural_style_tube_and_neuralgia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neural_style_transfer", "Neural Style Transfer", ["computers_and_information_processing"], "神经风格迁移"),
                ("neural_tube", "Neural Tube", ["anatomy", "biomedical"], "神经管"),
                ("neural_tube_defect", "Neural Tube Defects", ["biomedical", "diseases"], "神经管缺陷"),
                ("neural_symbolic_integration", "Neural-symbolic Integration", ["computer_science"], "神经符号集成"),
                ("neuralgia", "Neuralgia", ["biomedical", "diseases"], "神经痛"),
                ("neuralgia_postherpetic", "Neuralgia, Postherpetic", ["biomedical", "diseases"], "带状疱疹后神经痛"),
                ("neuraminic_acid", "Neuraminic Acids", ["biomedical", "chemicals_and_drugs"], "神经氨酸"),
                ("neuraminidase", "Neuraminidase", ["biomedical", "chemicals_and_drugs"], "神经氨酸酶"),
            ]
        )

    def test_exact_expansion_batch_591_adds_neurasthenia_neuregulin_and_neuritis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neurasthenia", "Neurasthenia", ["biomedical", "psychiatry_and_psychology"], "神经衰弱"),
                ("neuregulin_1", "Neuregulin-1", ["biomedical", "chemicals_and_drugs"], "神经调节蛋白1"),
                ("neuregulin", "Neuregulins", ["biomedical", "chemicals_and_drugs"], "神经调节蛋白"),
                ("neurexin", "Neurexins", ["biomedical", "chemicals_and_drugs"], "神经连接蛋白"),
                ("neurilemma", "Neurilemma", ["anatomy", "biomedical"], "神经膜"),
                ("neurilemmoma", "Neurilemmoma", ["biomedical", "diseases"], "神经鞘瘤"),
                ("neurit", "Neurites", ["anatomy", "biomedical"], "神经突"),
                ("neuriti", "Neuritis", ["biomedical", "diseases"], "神经炎"),
            ]
        )

    def test_exact_expansion_batch_592_adds_neuro_fuzzy_and_neuroanatomy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neuriti_autoimmune_experimental", "Neuritis, Autoimmune, Experimental", ["biomedical", "diseases"], "实验性自身免疫性神经炎"),
                ("neuro_fuzzy", "Neuro-fuzzy", ["computer_science"], "神经模糊"),
                ("neuro_fuzzy_controller", "Neuro-fuzzy Controller", ["computer_science"], "神经模糊控制器"),
                ("neuro_fuzzy_model", "Neuro-fuzzy Model", ["computer_science"], "神经模糊模型"),
                ("neuro_fuzzy_network", "Neuro-fuzzy Network", ["computer_science"], "神经模糊网络"),
                ("neuro_oncological_ventral_antigen", "Neuro-oncological Ventral Antigen", ["biomedical", "chemicals_and_drugs"], "神经肿瘤腹侧抗原"),
                ("neuroacanthocytosi", "Neuroacanthocytosis", ["biomedical", "diseases"], "神经棘红细胞增多症"),
                ("neuroanatomy", "Neuroanatomy", ["biomedical", "disciplines_and_occupations"], "神经解剖学"),
            ]
        )

    def test_exact_expansion_batch_593_adds_neuroanesthesia_neuroblastoma_and_neurochemistry_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neuroanatomical_tract_tracing_techniqu", "Neuroanatomical Tract-tracing Techniques", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经解剖束追踪技术"),
                ("neuroanesthesia", "Neuroanesthesia", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经麻醉"),
                ("neuroaspergillosi", "Neuroaspergillosis", ["biomedical", "diseases"], "神经曲霉病"),
                ("neuroaxonal_dystrophy", "Neuroaxonal Dystrophies", ["biomedical", "diseases"], "神经轴索营养不良"),
                ("neurobehavioral_manifestation", "Neurobehavioral Manifestations", ["biomedical", "diseases"], "神经行为表现"),
                ("neurobiology", "Neurobiology", ["biomedical", "disciplines_and_occupations"], "神经生物学"),
                ("neuroblastoma", "Neuroblastoma", ["biomedical", "diseases"], "神经母细胞瘤"),
                ("neurochemistry", "Neurochemistry", ["biomedical", "disciplines_and_occupations"], "神经化学"),
            ]
        )

    def test_exact_expansion_batch_594_adds_neurocognitive_neurodegenerative_and_neurodevelopment_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neurocognitive_disorder", "Neurocognitive Disorders", ["biomedical", "psychiatry_and_psychology"], "神经认知障碍"),
                ("neurocontroller", "Neurocontrollers", ["systems_man_and_cybernetics"], "神经控制器"),
                ("neurocutaneou_syndrom", "Neurocutaneous Syndromes", ["biomedical", "diseases"], "神经皮肤综合征"),
                ("neurocysticercosi", "Neurocysticercosis", ["biomedical", "diseases"], "神经囊尾蚴病"),
                ("neurocytoma", "Neurocytoma", ["biomedical", "diseases"], "神经细胞瘤"),
                ("neurodegenerative_disease", "Neurodegenerative Diseases", ["biomedical", "diseases"], "神经退行性疾病"),
                ("neurodermatiti", "Neurodermatitis", ["biomedical", "diseases"], "神经性皮炎"),
                ("neurodevelopment", "Neurodevelopment", ["biomedical", "phenomena_and_processes"], "神经发育"),
            ]
        )

    def test_exact_expansion_batch_595_adds_neurodevelopmental_and_neuroendocrine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neurodevelopmental_disorder", "Neurodevelopmental Disorders", ["biomedical", "psychiatry_and_psychology"], "神经发育障碍"),
                ("neuroectodermal_tumor_melanotic", "Neuroectodermal Tumor, Melanotic", ["biomedical", "diseases"], "黑色素性神经外胚层肿瘤"),
                ("neuroectodermal_tumor", "Neuroectodermal Tumors", ["biomedical", "diseases"], "神经外胚层肿瘤"),
                ("neuroeffector_junction", "Neuroeffector Junction", ["anatomy", "biomedical"], "神经效应接头"),
                ("neuroendocrine_cell", "Neuroendocrine Cells", ["anatomy", "biomedical"], "神经内分泌细胞"),
                ("neuroendocrine_regulation_and_behavior", "Neuroendocrine Regulation And Behavior", ["psychology", "social_sciences"], "神经内分泌调节与行为"),
                ("neuroendocrine_tumor", "Neuroendocrine Tumors", ["biomedical", "diseases"], "神经内分泌肿瘤"),
                ("neuroendocrinology", "Neuroendocrinology", ["biomedical", "disciplines_and_occupations"], "神经内分泌学"),
            ]
        )

    def test_exact_expansion_batch_596_adds_neuroendoscopy_neurofeedback_and_neurofibroma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neuroendoscop", "Neuroendoscopes", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经内镜"),
                ("neuroendoscopy", "Neuroendoscopy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经内镜检查"),
                ("neuroepithelial_body", "Neuroepithelial Bodies", ["anatomy", "biomedical"], "神经上皮小体"),
                ("neuroepithelial_cell", "Neuroepithelial Cells", ["anatomy", "biomedical"], "神经上皮细胞"),
                ("neurofeedback", "Neurofeedback", ["circuits_and_systems"], "神经反馈"),
                ("neurofibrillary_tangl", "Neurofibrillary Tangles", ["anatomy", "biomedical"], "神经原纤维缠结"),
                ("neurofibril", "Neurofibrils", ["anatomy", "biomedical"], "神经原纤维"),
                ("neurofibroma", "Neurofibroma", ["biomedical", "diseases"], "神经纤维瘤"),
            ]
        )

    def test_exact_expansion_batch_597_adds_neurofibromatosis_and_neurofilament_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neurofibroma_plexiform", "Neurofibroma, Plexiform", ["biomedical", "diseases"], "丛状神经纤维瘤"),
                ("neurofibromatose", "Neurofibromatoses", ["biomedical", "diseases"], "神经纤维瘤病"),
                ("neurofibromatosi_1", "Neurofibromatosis 1", ["biomedical", "diseases"], "1型神经纤维瘤病"),
                ("neurofibromatosi_2", "Neurofibromatosis 2", ["biomedical", "diseases"], "2型神经纤维瘤病"),
                ("neurofibromin_1", "Neurofibromin 1", ["biomedical", "chemicals_and_drugs"], "神经纤维瘤蛋白1"),
                ("neurofibromin_2", "Neurofibromin 2", ["biomedical", "chemicals_and_drugs"], "神经纤维瘤蛋白2"),
                ("neurofibrosarcoma", "Neurofibrosarcoma", ["biomedical", "diseases"], "神经纤维肉瘤"),
                ("neurofilament_protein", "Neurofilament Proteins", ["biomedical", "chemicals_and_drugs"], "神经丝蛋白"),
            ]
        )

    def test_exact_expansion_batch_598_adds_neurogenesis_neuroglia_and_neuroinflammation_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neurogenesi", "Neurogenesis", ["biomedical", "phenomena_and_processes"], "神经发生"),
                ("neurogenesi_and_neuroplasticity_mechanism", "Neurogenesis And Neuroplasticity Mechanisms", ["life_sciences", "neuroscience"], "神经发生与神经可塑性机制"),
                ("neurogenic_bowel", "Neurogenic Bowel", ["biomedical", "diseases"], "神经源性肠道"),
                ("neurogenic_inflammation", "Neurogenic Inflammation", ["biomedical", "diseases"], "神经源性炎症"),
                ("neuroglia", "Neuroglia", ["anatomy", "biomedical"], "神经胶质"),
                ("neuroglobin", "Neuroglobin", ["biomedical", "chemicals_and_drugs"], "神经珠蛋白"),
                ("neuroimaging__2", "Neuroimaging", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经影像学"),
                ("neuroinflammatory_disease", "Neuroinflammatory Diseases", ["biomedical", "diseases"], "神经炎症性疾病"),
            ]
        )

    def test_exact_expansion_batch_599_adds_neuroinformatics_neurokinin_and_neuroligin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neuroinformatic", "Neuroinformatics", ["engineering_in_medicine_and_biology"], "神经信息学"),
                ("neurokinin_a", "Neurokinin A", ["biomedical", "chemicals_and_drugs"], "神经激肽A"),
                ("neurokinin_b", "Neurokinin B", ["biomedical", "chemicals_and_drugs"], "神经激肽B"),
                ("neurokinin_1_receptor_antagonist", "Neurokinin-1 Receptor Antagonists", ["biomedical", "chemicals_and_drugs"], "神经激肽1受体拮抗剂"),
                ("neuroleptanalgesia", "Neuroleptanalgesia", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经安定镇痛"),
                ("neuroleptic_malignant_syndrome", "Neuroleptic Malignant Syndrome", ["biomedical", "diseases"], "神经阻滞剂恶性综合征"),
                ("neuroligin", "Neuroligins", ["biomedical", "chemicals_and_drugs"], "神经连接蛋白"),
                ("neurolinguistic_programming", "Neurolinguistic Programming", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经语言程序学"),
            ]
        )

    def test_exact_expansion_batch_600_adds_neurologic_neurology_and_neuroma_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neurologic_examination", "Neurologic Examination", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经系统检查"),
                ("neurologic_manifestation", "Neurologic Manifestations", ["biomedical", "diseases"], "神经系统表现"),
                ("neurological_disorder_and_treatment", "Neurological Disorders And Treatments", ["health_sciences", "life_sciences", "medicine", "neuroscience"], "神经系统疾病与治疗"),
                ("neurological_rehabilitation", "Neurological Rehabilitation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经康复"),
                ("neurologist", "Neurologists", ["biomedical", "named_groups"], "神经科医师"),
                ("neurology", "Neurology", ["engineering_in_medicine_and_biology"], "神经病学"),
                ("neuroma", "Neuroma", ["biomedical", "diseases"], "神经瘤"),
                ("neuroma_acoustic", "Neuroma, Acoustic", ["biomedical", "diseases"], "听神经瘤"),
            ]
        )

    def test_exact_expansion_batch_601_adds_neuronal_and_neuron_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neuronal_outgrowth", "Neuronal Outgrowth", ["biomedical", "phenomena_and_processes"], "神经元突起生长"),
                ("neuronal_plasticity", "Neuronal Plasticity", ["biomedical", "phenomena_and_processes"], "神经元可塑性"),
                ("neuronal_tract_tracer", "Neuronal Tract-tracers", ["biomedical", "chemicals_and_drugs"], "神经元束示踪剂"),
                ("neuronavigation", "Neuronavigation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经导航"),
                ("neuron", "Neurons", ["anatomy", "biomedical"], "神经元"),
                ("neuron_and_cognition", "Neurons And Cognition", ["quantitative_biology"], "神经元与认知"),
                ("neuron_afferent", "Neurons, Afferent", ["anatomy", "biomedical"], "传入神经元"),
                ("neuron_efferent", "Neurons, Efferent", ["anatomy", "biomedical"], "传出神经元"),
            ]
        )

    def test_exact_expansion_batch_602_adds_neuropathology_neuropeptide_and_monitoring_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neuropathology", "Neuropathology", ["engineering_in_medicine_and_biology"], "神经病理学"),
                ("neuropathology__2", "Neuropathology", ["biomedical", "disciplines_and_occupations"], "神经病理学"),
                ("neuropeptide_y", "Neuropeptide Y", ["biomedical", "chemicals_and_drugs"], "神经肽Y"),
                ("neuropeptid", "Neuropeptides", ["biomedical", "chemicals_and_drugs"], "神经肽"),
                ("neuropeptid_and_animal_physiology", "Neuropeptides And Animal Physiology", ["life_sciences", "neuroscience"], "神经肽与动物生理学"),
                ("neuropharmacology", "Neuropharmacology", ["biomedical", "disciplines_and_occupations"], "神经药理学"),
                ("neurophysin", "Neurophysins", ["biomedical", "chemicals_and_drugs"], "神经垂体激素运载蛋白"),
                ("neurophysiological_monitoring", "Neurophysiological Monitoring", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经生理监测"),
            ]
        )

    def test_exact_expansion_batch_603_adds_neurophysiology_neuropil_and_neuropilin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neurophysiology", "Neurophysiology", ["biomedical", "disciplines_and_occupations"], "神经生理学"),
                ("neuropil", "Neuropil", ["anatomy", "biomedical"], "神经毡"),
                ("neuropil_thread", "Neuropil Threads", ["anatomy", "biomedical"], "神经毡丝"),
                ("neuropilin_1", "Neuropilin-1", ["biomedical", "chemicals_and_drugs"], "神经纤毛蛋白1"),
                ("neuropilin_2", "Neuropilin-2", ["biomedical", "chemicals_and_drugs"], "神经纤毛蛋白2"),
                ("neuropilin", "Neuropilins", ["biomedical", "chemicals_and_drugs"], "神经纤毛蛋白"),
                ("neuroprostan", "Neuroprostanes", ["biomedical", "chemicals_and_drugs"], "神经前列烷"),
                ("neuroprosthese", "Neuroprostheses", ["engineering_in_medicine_and_biology"], "神经假体"),
            ]
        )

    def test_exact_expansion_batch_604_adds_neuroprotection_and_neuropsychology_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neuroprosthese__2", "Neuroprostheses", ["science_general"], "神经假体"),
                ("neuroprotection", "Neuroprotection", ["biomedical", "phenomena_and_processes"], "神经保护"),
                ("neuroprotective_agent", "Neuroprotective Agents", ["biomedical", "chemicals_and_drugs"], "神经保护剂"),
                ("neuropsychiatry", "Neuropsychiatry", ["biomedical", "psychiatry_and_psychology"], "神经精神病学"),
                ("neuropsychological_test", "Neuropsychological Tests", ["biomedical", "psychiatry_and_psychology"], "神经心理测验"),
                ("neuropsychology", "Neuropsychology", ["science_general"], "神经心理学"),
                ("neuropsychology__2", "Neuropsychology", ["systems_man_and_cybernetics"], "神经心理学"),
                ("neuropsychology__3", "Neuropsychology", ["biomedical", "psychiatry_and_psychology"], "神经心理学"),
            ]
        )

    def test_exact_expansion_batch_605_adds_neuroradiology_and_neuroscience_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neuroradiography", "Neuroradiography", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经放射摄影"),
                ("neuroradiology", "Neuroradiology", ["engineering_in_medicine_and_biology"], "神经放射学"),
                ("neurorehabilitation", "Neurorehabilitation", ["engineering_in_medicine_and_biology"], "神经康复"),
                ("neuroschistosomiasi", "Neuroschistosomiasis", ["biomedical", "diseases"], "神经血吸虫病"),
                ("neuroscience", "Neuroscience", ["science_general"], "神经科学"),
                ("neuroscience_and_music_perception", "Neuroscience And Music Perception", ["life_sciences", "neuroscience"], "神经科学与音乐感知"),
                ("neuroscience_and_neural_engineering", "Neuroscience And Neural Engineering", ["life_sciences", "neuroscience"], "神经科学与神经工程"),
                ("neuroscience_and_neuropharmacology_research", "Neuroscience And Neuropharmacology Research", ["life_sciences", "neuroscience"], "神经科学与神经药理学研究"),
            ]
        )

    def test_exact_expansion_batch_606_adds_neuroscience_and_neurospora_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neuroscience_nursing", "Neuroscience Nursing", ["biomedical", "disciplines_and_occupations"], "神经科学护理"),
                ("neuroscience_of_respiration_and_sleep", "Neuroscience Of Respiration And Sleep", ["life_sciences", "neuroscience"], "呼吸与睡眠神经科学"),
                ("neuroscience_neural_computation_and_artificial_intelligence", "Neuroscience, Neural Computation & Artificial Intelligence", ["physics"], "神经科学、神经计算与人工智能"),
                ("neuroscienc", "Neurosciences", ["biomedical", "disciplines_and_occupations"], "神经科学"),
                ("neurosecretion", "Neurosecretion", ["biomedical", "phenomena_and_processes"], "神经分泌"),
                ("neurosecretory_system", "Neurosecretory Systems", ["anatomy", "biomedical"], "神经分泌系统"),
                ("neuroserpin", "Neuroserpin", ["biomedical", "chemicals_and_drugs"], "神经丝氨酸蛋白酶抑制剂"),
                ("neurospora", "Neurospora", ["biomedical", "organisms"], "脉孢菌属"),
            ]
        )

    def test_exact_expansion_batch_607_adds_neurospora_neurosurgery_and_neurotechnology_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neurospora_crassa", "Neurospora Crassa", ["biomedical", "organisms"], "粗糙脉孢菌"),
                ("neurosteroid", "Neurosteroids", ["biomedical", "chemicals_and_drugs"], "神经甾体"),
                ("neurosurgeon", "Neurosurgeons", ["biomedical", "named_groups"], "神经外科医师"),
                ("neurosurgery", "Neurosurgery", ["biomedical", "disciplines_and_occupations"], "神经外科学"),
                ("neurosurgical_procedur", "Neurosurgical Procedures", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "神经外科手术"),
                ("neurosurgical_procedur_and_complication", "Neurosurgical Procedures And Complications", ["health_sciences", "medicine"], "神经外科手术及并发症"),
                ("neurosymbolic_ai", "Neurosymbolic Ai", ["computer_science"], "神经符号AI"),
                ("neurosyphili", "Neurosyphilis", ["biomedical", "diseases"], "神经梅毒"),
            ]
        )

    def test_exact_expansion_batch_608_adds_neurotensin_neurotoxicity_and_neurotoxin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neurotechnology", "Neurotechnology", ["change"], "神经技术"),
                ("neurotensin", "Neurotensin", ["biomedical", "chemicals_and_drugs"], "神经降压素"),
                ("neurothekeoma", "Neurothekeoma", ["biomedical", "diseases"], "神经鞘黏液瘤"),
                ("neurotic_disorder", "Neurotic Disorders", ["biomedical", "psychiatry_and_psychology"], "神经症性障碍"),
                ("neuroticism", "Neuroticism", ["biomedical", "psychiatry_and_psychology"], "神经质"),
                ("neurotology", "Neurotology", ["biomedical", "disciplines_and_occupations"], "神经耳科学"),
                ("neurotoxicity_syndrom", "Neurotoxicity Syndromes", ["biomedical", "diseases"], "神经毒性综合征"),
                ("neurotoxin", "Neurotoxins", ["biomedical", "chemicals_and_drugs"], "神经毒素"),
                ("receptor_neurotensin", "Receptors, Neurotensin", ["biomedical", "chemicals_and_drugs"], "神经降压素受体"),
            ]
        )

    def test_exact_expansion_batch_609_adds_neurotransmitter_neurotrophin_and_neutral_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neurotransmitter_agent", "Neurotransmitter Agents", ["biomedical", "chemicals_and_drugs"], "神经递质作用剂"),
                ("neurotransmitter_receptor_influence_on_behavior", "Neurotransmitter Receptor Influence On Behavior", ["life_sciences", "neuroscience"], "神经递质受体对行为的影响"),
                ("neurotransmitter_transport_protein", "Neurotransmitter Transport Proteins", ["biomedical", "chemicals_and_drugs"], "神经递质转运蛋白"),
                ("neurotransmitter_uptake_inhibitor", "Neurotransmitter Uptake Inhibitors", ["biomedical", "chemicals_and_drugs"], "神经递质摄取抑制剂"),
                ("neurotransmitter", "Neurotransmitters", ["communications_technology"], "神经递质"),
                ("neurotrophin_3", "Neurotrophin 3", ["biomedical", "chemicals_and_drugs"], "神经营养因子3"),
                ("neurovascular_coupling", "Neurovascular Coupling", ["biomedical", "phenomena_and_processes"], "神经血管耦合"),
                ("neurulation", "Neurulation", ["biomedical", "phenomena_and_processes"], "神经胚形成"),
            ]
        )

    def test_exact_expansion_batch_610_adds_neutralization_neutrino_and_neutron_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neutral_ceramidase", "Neutral Ceramidase", ["biomedical", "chemicals_and_drugs"], "中性神经酰胺酶"),
                ("neutral_glycosphingolipid", "Neutral Glycosphingolipids", ["biomedical", "chemicals_and_drugs"], "中性糖鞘脂"),
                ("neutral_red", "Neutral Red", ["biomedical", "chemicals_and_drugs"], "中性红"),
                ("neutral_system", "Neutral Systems", ["computer_science"], "中立型系统"),
                ("neutralization_test", "Neutralization Tests", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "中和试验"),
                ("neutrino_physic_research", "Neutrino Physics Research", ["physical_sciences", "physics_and_astronomy"], "中微子物理研究"),
                ("neutrino_sourc", "Neutrino Sources", ["nuclear_and_plasma_sciences"], "中微子源"),
                ("neutron_activation_analysi", "Neutron Activation Analysis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "中子活化分析"),
            ]
        )

    def test_exact_expansion_batch_611_adds_neutron_and_neutropenia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neutron_capture_therapy__2", "Neutron Capture Therapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "中子俘获治疗"),
                ("neutron_capture_therapy", "Neutron Capture Therapy", ["engineering_in_medicine_and_biology"], "中子俘获治疗"),
                ("neutron_diffraction", "Neutron Diffraction", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "中子衍射"),
                ("neutron_radiation_effect", "Neutron Radiation Effects", ["nuclear_and_plasma_sciences"], "中子辐射效应"),
                ("neutron_spin_echo", "Neutron Spin Echo", ["instrumentation_and_measurement"], "中子自旋回波"),
                ("neutron_star", "Neutron Stars", ["science_general"], "中子星"),
                ("neutron_techniqu", "Neutron Techniques", ["physics"], "中子技术"),
                ("neutron", "Neutrons", ["nuclear_and_plasma_sciences"], "中子"),
            ]
        )

    def test_exact_expansion_batch_612_adds_neutrophil_nevada_and_nevus_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("neutron__2", "Neutrons", ["biomedical", "phenomena_and_processes"], "中子"),
                ("neutropenia", "Neutropenia", ["biomedical", "diseases"], "中性粒细胞减少症"),
                ("neutropenia_and_cancer_infection", "Neutropenia And Cancer Infections", ["health_sciences", "medicine"], "中性粒细胞减少症与癌症感染"),
                ("neutrophil_activation", "Neutrophil Activation", ["biomedical", "phenomena_and_processes"], "中性粒细胞活化"),
                ("neutrophil_infiltration", "Neutrophil Infiltration", ["biomedical", "phenomena_and_processes"], "中性粒细胞浸润"),
                ("neutrophil", "Neutrophils", ["anatomy", "biomedical"], "中性粒细胞"),
                ("nevada", "Nevada", ["biomedical", "geographicals"], "内华达州"),
                ("nevi_and_melanoma", "Nevi And Melanomas", ["biomedical", "diseases"], "痣和黑色素瘤"),
            ]
        )

    def test_exact_expansion_batch_613_adds_nevirapine_and_specific_nevus_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nevirapine", "Nevirapine", ["biomedical", "chemicals_and_drugs"], "奈韦拉平"),
                ("nevu_of_ota", "Nevus Of Ota", ["biomedical", "diseases"], "太田痣"),
                ("nevu_blue", "Nevus, Blue", ["biomedical", "diseases"], "蓝痣"),
                ("nevu_epithelioid_and_spindle_cell", "Nevus, Epithelioid And Spindle Cell", ["biomedical", "diseases"], "上皮样和梭形细胞痣"),
                ("nevu_halo", "Nevus, Halo", ["biomedical", "diseases"], "晕痣"),
                ("nevu_intradermal", "Nevus, Intradermal", ["biomedical", "diseases"], "皮内痣"),
                ("nevu_pigmented", "Nevus, Pigmented", ["biomedical", "diseases"], "色素痣"),
                ("nevu_spindle_cell", "Nevus, Spindle Cell", ["biomedical", "diseases"], "梭形细胞痣"),
            ]
        )

    def test_exact_expansion_batch_614_adds_new_geographical_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nevu_sebaceou_of_jadassohn", "Nevus, Sebaceous Of Jadassohn", ["biomedical", "diseases"], "贾达松皮脂腺痣"),
                ("new_brunswick", "New Brunswick", ["biomedical", "geographicals"], "新不伦瑞克"),
                ("new_caledonia", "New Caledonia", ["biomedical", "geographicals"], "新喀里多尼亚"),
                ("new_caledonia_indigenou_study", "New Caledonia Indigenous Studies", ["social_sciences"], "新喀里多尼亚原住民研究"),
                ("new_england", "New England", ["biomedical", "geographicals"], "新英格兰"),
                ("new_guinea", "New Guinea", ["biomedical", "geographicals"], "新几内亚"),
                ("new_hampshire", "New Hampshire", ["biomedical", "geographicals"], "新罕布什尔"),
                ("new_jersey", "New Jersey", ["biomedical", "geographicals"], "新泽西"),
            ]
        )

    def test_exact_expansion_batch_615_adds_more_new_geographical_and_newcastle_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("new_mexico", "New Mexico", ["biomedical", "geographicals"], "新墨西哥"),
                ("new_orlean", "New Orleans", ["biomedical", "geographicals"], "新奥尔良"),
                ("new_south_wal", "New South Wales", ["biomedical", "geographicals"], "新南威尔士"),
                ("new_york", "New York", ["biomedical", "geographicals"], "纽约"),
                ("new_york_city", "New York City", ["biomedical", "geographicals"], "纽约市"),
                ("new_zealand", "New Zealand", ["biomedical", "geographicals"], "新西兰"),
                ("new_zealand_economic_and_social_study", "New Zealand Economic And Social Studies", ["economics_econometrics_and_finance", "social_sciences"], "新西兰经济与社会研究"),
                ("newcastle_disease", "Newcastle Disease", ["biomedical", "diseases"], "新城疫"),
            ]
        )

    def test_exact_expansion_batch_616_adds_newcastle_newspaper_and_newtonian_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("newcastle_disease_viru", "Newcastle Disease Virus", ["biomedical", "organisms"], "新城疫病毒"),
                ("newfoundland_and_labrador", "Newfoundland And Labrador", ["biomedical", "geographicals"], "纽芬兰与拉布拉多"),
                ("news", "News", ["biomedical", "publication_characteristics"], "新闻"),
                ("newspaper_article", "Newspaper Article", ["biomedical", "publication_characteristics"], "报纸文章"),
                ("newspaper_as_topic", "Newspapers As Topic", ["biomedical", "information_science"], "报纸专题"),
                ("newton_method", "Newton Method", ["computer_science", "mathematics"], "牛顿法"),
                ("newtonian_flow", "Newtonian Flow", ["computer_science"], "牛顿流"),
                ("newtonian_fluid", "Newtonian Fluid", ["computer_science"], "牛顿流体"),
            ]
        )

    def test_exact_expansion_batch_617_adds_newtonian_next_generation_and_nfe2_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("newtonian_liquid", "Newtonian Liquids", ["computer_science"], "牛顿液体"),
                ("next_generation_networking", "Next Generation Networking", ["communications_technology"], "下一代网络"),
                ("next_generation_networking__2", "Next Generation Networking", ["computers_and_information_processing"], "下一代网络"),
                ("next_generation_wireless_network", "Next-generation Wireless Network", ["computer_science"], "下一代无线网络"),
                ("next_hop", "Next-hop", ["computer_science"], "下一跳"),
                ("nf_e2_transcription_factor", "Nf-e2 Transcription Factor", ["biomedical", "chemicals_and_drugs"], "NF-E2转录因子"),
                ("nf_e2_transcription_factor_p45_subunit", "Nf-e2 Transcription Factor, P45 Subunit", ["biomedical", "chemicals_and_drugs"], "NF-E2转录因子p45亚基"),
                ("nf_e2_related_factor_1", "Nf-e2-related Factor 1", ["biomedical", "chemicals_and_drugs"], "NF-E2相关因子1"),
            ]
        )

    def test_exact_expansion_batch_618_adds_nf_related_and_nfkappab_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nf_e2_related_factor_2", "Nf-e2-related Factor 2", ["biomedical", "chemicals_and_drugs"], "NF-E2相关因子2"),
                ("nf_kappa_b", "Nf-kappa B", ["biomedical", "chemicals_and_drugs"], "核因子κB"),
                ("nf_kappa_b_p50_subunit", "Nf-kappa B P50 Subunit", ["biomedical", "chemicals_and_drugs"], "NF-κB p50亚基"),
                ("nf_kappa_b_p52_subunit", "Nf-kappa B P52 Subunit", ["biomedical", "chemicals_and_drugs"], "NF-κB p52亚基"),
                ("nf_kappab_inhibitor_alpha", "Nf-kappab Inhibitor Alpha", ["biomedical", "chemicals_and_drugs"], "NF-κB抑制蛋白α"),
                ("nf_kappab_inducing_kinase", "Nf-kappab-inducing Kinase", ["biomedical", "chemicals_and_drugs"], "NF-κB诱导激酶"),
                ("nf_b_signaling_pathway", "Nf-κb Signaling Pathways", ["biochemistry_genetics_and_molecular_biology", "life_sciences"], "NF-κB信号通路"),
                ("nfatc_transcription_factor", "Nfatc Transcription Factors", ["biomedical", "chemicals_and_drugs"], "NFATc转录因子"),
            ]
        )

    def test_exact_expansion_batch_619_adds_nfatc_niacin_and_nicaragua_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nfi_transcription_factor", "NFI Transcription Factors", ["biomedical", "chemicals_and_drugs"], "NFI转录因子"),
                ("ng_nitroarginine_methyl_ester", "Ng-nitroarginine Methyl Ester", ["biomedical", "chemicals_and_drugs"], "NG-硝基精氨酸甲酯"),
                ("niacin", "Niacin", ["biomedical", "chemicals_and_drugs"], "烟酸"),
                ("niacinamide", "Niacinamide", ["biomedical", "chemicals_and_drugs"], "烟酰胺"),
                ("nialamide", "Nialamide", ["biomedical", "chemicals_and_drugs"], "尼亚拉胺"),
                ("nicaragua", "Nicaragua", ["biomedical", "geographicals"], "尼加拉瓜"),
                ("nicarbazin", "Nicarbazin", ["biomedical", "chemicals_and_drugs"], "尼卡巴嗪"),
                ("nicardipine", "Nicardipine", ["biomedical", "chemicals_and_drugs"], "尼卡地平"),
            ]
        )

    def test_exact_expansion_batch_620_adds_nicardipine_nickel_and_nicotiana_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nicergoline", "Nicergoline", ["biomedical", "chemicals_and_drugs"], "尼麦角林"),
                ("nickel", "Nickel", ["materials_elements_and_compounds"], "镍元素"),
                ("nickel__2", "Nickel", ["biomedical", "chemicals_and_drugs"], "镍元素"),
                ("nickel_alloy", "Nickel Alloys", ["materials_elements_and_compounds"], "镍合金"),
                ("nickel_cadmium_battery", "Nickel Cadmium Batteries", ["industry_applications"], "镍镉电池"),
                ("nickel_compound", "Nickel Compounds", ["materials_elements_and_compounds"], "镍化合物"),
                ("nicotiana", "Nicotiana", ["biomedical", "organisms"], "烟草属"),
            ]
        )

    def test_exact_expansion_batch_621_adds_nicotinamide_enzyme_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nicotinamidase", "Nicotinamidase", ["biomedical", "chemicals_and_drugs"], "烟酰胺酶"),
                ("nicotinamide_mononucleotide", "Nicotinamide Mononucleotide", ["biomedical", "chemicals_and_drugs"], "烟酰胺单核苷酸"),
                ("nicotinamide_n_methyltransferase", "Nicotinamide N-methyltransferase", ["biomedical", "chemicals_and_drugs"], "烟酰胺N-甲基转移酶"),
                ("nicotinamide_phosphoribosyltransferase", "Nicotinamide Phosphoribosyltransferase", ["biomedical", "chemicals_and_drugs"], "烟酰胺磷酸核糖转移酶"),
                ("nicotinamide_nucleotide_adenylyltransferase", "Nicotinamide-nucleotide Adenylyltransferase", ["biomedical", "chemicals_and_drugs"], "烟酰胺核苷酸腺苷酰转移酶"),
                ("nicotinate_nucleotide_diphosphorylase_carboxylating", "Nicotinate-nucleotide Diphosphorylase (carboxylating)", ["biomedical", "chemicals_and_drugs"], "烟酸核苷酸二磷酸化酶(羧化)"),
                ("nicotine", "Nicotine", ["biomedical", "chemicals_and_drugs"], "尼古丁"),
                ("nicotine_chewing_gum", "Nicotine Chewing Gum", ["biomedical", "chemicals_and_drugs"], "尼古丁口香糖"),
            ]
        )

    def test_exact_expansion_batch_622_adds_nicotine_receptor_and_nidovirales_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nicotine_replacement_therapy", "Nicotine Replacement Therapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "尼古丁替代疗法"),
                ("nicotinic_acetylcholine_receptor_study", "Nicotinic Acetylcholine Receptors Study", ["biochemistry_genetics_and_molecular_biology", "life_sciences"], "烟碱型乙酰胆碱受体研究"),
                ("nicotinic_agonist", "Nicotinic Agonists", ["biomedical", "chemicals_and_drugs"], "烟碱受体激动剂"),
                ("nicotinic_antagonist", "Nicotinic Antagonists", ["biomedical", "chemicals_and_drugs"], "烟碱受体拮抗剂"),
                ("nicotinyl_alcohol", "Nicotinyl Alcohol", ["biomedical", "chemicals_and_drugs"], "烟醇"),
                ("nictitating_membrane", "Nictitating Membrane", ["anatomy", "biomedical"], "瞬膜"),
                ("nidoviral", "Nidovirales", ["biomedical", "organisms"], "套式病毒目"),
                ("nidoviral_infection", "Nidovirales Infections", ["biomedical", "diseases"], "套式病毒目感染"),
            ]
        )

    def test_exact_expansion_batch_623_adds_niemann_pick_and_nifedipine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("niemann_pick_c1_protein", "Niemann-pick C1 Protein", ["biomedical", "chemicals_and_drugs"], "尼曼-匹克C1蛋白"),
                ("niemann_pick_disease_type_a", "Niemann-pick Disease, Type A", ["biomedical", "diseases"], "A型尼曼-匹克病"),
                ("niemann_pick_disease_type_b", "Niemann-pick Disease, Type B", ["biomedical", "diseases"], "B型尼曼-匹克病"),
                ("niemann_pick_disease_type_c", "Niemann-pick Disease, Type C", ["biomedical", "diseases"], "C型尼曼-匹克病"),
                ("niemann_pick_disease", "Niemann-pick Diseases", ["biomedical", "diseases"], "尼曼-匹克病"),
                ("nietzsche_schopenhauer_and_hegel", "Nietzsche, Schopenhauer, And Hegel", ["arts_and_humanities", "social_sciences"], "尼采、叔本华与黑格尔"),
                ("nifedipine", "Nifedipine", ["biomedical", "chemicals_and_drugs"], "硝苯地平"),
                ("niflumic_acid", "Niflumic Acid", ["biomedical", "chemicals_and_drugs"], "尼氟灭酸"),
            ]
        )

    def test_exact_expansion_batch_624_adds_nifuratel_nigella_and_night_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nifuratel", "Nifuratel", ["biomedical", "chemicals_and_drugs"], "硝呋太尔"),
                ("nifurtimox", "Nifurtimox", ["biomedical", "chemicals_and_drugs"], "硝呋替莫"),
                ("nigella", "Nigella", ["biomedical", "organisms"], "黑种草属"),
                ("nigella_damascena", "Nigella Damascena", ["biomedical", "organisms"], "大马士革黑种草"),
                ("nigella_sativa", "Nigella Sativa", ["biomedical", "organisms"], "黑种草"),
                ("nigella_sativa_pharmacological_application", "Nigella Sativa Pharmacological Applications", ["health_sciences", "medicine"], "黑种草药理应用"),
                ("niger", "Niger", ["biomedical", "geographicals"], "尼日尔"),
                ("nigeria", "Nigeria", ["biomedical", "geographicals"], "尼日利亚"),
            ]
        )

    def test_exact_expansion_batch_625_adds_nigericin_night_and_nih_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nigericin", "Nigericin", ["biomedical", "chemicals_and_drugs"], "尼日利亚菌素"),
                ("night_blindness", "Night Blindness", ["biomedical", "diseases"], "夜盲症"),
                ("night_care", "Night Care", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "夜间护理"),
                ("night_eating_syndrome", "Night Eating Syndrome", ["biomedical", "psychiatry_and_psychology"], "夜食综合征"),
                ("night_terror", "Night Terrors", ["biomedical", "diseases"], "夜惊"),
                ("night_vision", "Night Vision", ["imaging"], "夜视"),
                ("night_vision__2", "Night Vision", ["biomedical", "psychiatry_and_psychology"], "夜视"),
                ("nih_3t3_cell", "NIH 3T3 Cells", ["anatomy", "biomedical"], "NIH 3T3细胞"),
            ]
        )

    def test_exact_expansion_batch_626_adds_nijmegen_nima_and_nimaviridae_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("night_time_city_culture", "Night-time City Culture", ["social_sciences"], "夜间城市文化"),
                ("nijmegen_breakage_syndrome", "Nijmegen Breakage Syndrome", ["biomedical", "diseases"], "奈梅亨断裂综合征"),
                ("nikethamide", "Nikethamide", ["biomedical", "chemicals_and_drugs"], "尼可刹米"),
                ("nima_interacting_peptidylprolyl_isomerase", "Nima-interacting Peptidylprolyl Isomerase", ["biomedical", "chemicals_and_drugs"], "NIMA相互作用肽基脯氨酰异构酶"),
                ("nima_related_kinase_1", "Nima-related Kinase 1", ["biomedical", "chemicals_and_drugs"], "NIMA相关激酶1"),
                ("nima_related_kinase", "Nima-related Kinases", ["biomedical", "chemicals_and_drugs"], "NIMA相关激酶"),
                ("nimaviridae", "Nimaviridae", ["biomedical", "organisms"], "尼玛病毒科"),
                ("nimodipine", "Nimodipine", ["biomedical", "chemicals_and_drugs"], "尼莫地平"),
            ]
        )

    def test_exact_expansion_batch_627_adds_nimorazole_niobium_and_nipah_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nimorazole", "Nimorazole", ["biomedical", "chemicals_and_drugs"], "尼莫唑"),
                ("nimustine", "Nimustine", ["biomedical", "chemicals_and_drugs"], "尼莫司汀"),
                ("ninhydrin", "Ninhydrin", ["biomedical", "chemicals_and_drugs"], "茚三酮"),
                ("nintendo_wii", "Nintendo Wii", ["computer_science"], "任天堂Wii"),
                ("niobium", "Niobium", ["materials_elements_and_compounds"], "铌元素"),
                ("niobium__2", "Niobium", ["biomedical", "chemicals_and_drugs"], "铌元素"),
                ("niobium_alloy", "Niobium Alloys", ["materials_elements_and_compounds"], "铌合金"),
                ("niobium_compound", "Niobium Compounds", ["materials_elements_and_compounds"], "铌化合物"),
            ]
        )

    def test_exact_expansion_batch_628_adds_niobium_tin_nipple_and_nissl_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("niobium_tin", "Niobium-tin", ["materials_elements_and_compounds"], "铌锡"),
                ("niobium_tin__2", "Niobium-tin", ["superconductivity"], "铌锡"),
                ("nipah_viru", "Nipah Virus", ["biomedical", "organisms"], "尼帕病毒"),
                ("nipple_aspirate_fluid", "Nipple Aspirate Fluid", ["anatomy", "biomedical"], "乳头抽吸液"),
                ("nipple_discharge", "Nipple Discharge", ["anatomy", "biomedical"], "乳头溢液"),
                ("nippl", "Nipples", ["anatomy", "biomedical"], "乳头"),
                ("nippostrongylu", "Nippostrongylus", ["biomedical", "organisms"], "尼普圆线虫属"),
                ("niridazole", "Niridazole", ["biomedical", "chemicals_and_drugs"], "尼立达唑"),
            ]
        )

    def test_exact_expansion_batch_629_adds_nisin_nitrate_reductase_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nisin", "Nisin", ["biomedical", "chemicals_and_drugs"], "乳酸链球菌素"),
                ("nisoldipine", "Nisoldipine", ["biomedical", "chemicals_and_drugs"], "尼索地平"),
                ("nissl_body", "Nissl Bodies", ["anatomy", "biomedical"], "尼氏体"),
                ("nitella", "Nitella", ["biomedical", "organisms"], "丽藻属"),
                ("nitrate_reductase_nad_p_h", "Nitrate Reductase (nad(p)h)", ["biomedical", "chemicals_and_drugs"], "硝酸还原酶(NAD(P)H)"),
                ("nitrate_reductase_nadh", "Nitrate Reductase (nadh)", ["biomedical", "chemicals_and_drugs"], "硝酸还原酶(NADH)"),
                ("nitrate_reductase_nadph", "Nitrate Reductase (nadph)", ["biomedical", "chemicals_and_drugs"], "硝酸还原酶(NADPH)"),
                ("nitrate_reductase", "Nitrate Reductases", ["biomedical", "chemicals_and_drugs"], "硝酸还原酶"),
            ]
        )

    def test_exact_expansion_batch_630_adds_nitrate_nitric_acid_and_nitric_oxide_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nitrate_transporter", "Nitrate Transporters", ["biomedical", "chemicals_and_drugs"], "硝酸盐转运蛋白"),
                ("nitrat", "Nitrates", ["biomedical", "chemicals_and_drugs"], "硝酸盐"),
                ("nitrazepam", "Nitrazepam", ["biomedical", "chemicals_and_drugs"], "硝西泮"),
                ("nitrendipine", "Nitrendipine", ["biomedical", "chemicals_and_drugs"], "尼群地平"),
                ("nitrergic_neuron", "Nitrergic Neurons", ["anatomy", "biomedical"], "硝能神经元"),
                ("nitric_acid", "Nitric Acid", ["biomedical", "chemicals_and_drugs"], "硝酸"),
                ("nitric_oxide", "Nitric Oxide", ["biomedical", "chemicals_and_drugs"], "一氧化氮"),
                ("nitric_oxide_and_endothelin_effect", "Nitric Oxide And Endothelin Effects", ["health_sciences", "medicine"], "一氧化氮与内皮素效应"),
            ]
        )

    def test_exact_expansion_batch_631_adds_nitric_oxide_synthase_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nitric_oxide_donor", "Nitric Oxide Donors", ["biomedical", "chemicals_and_drugs"], "一氧化氮供体"),
                ("nitric_oxide_synthase", "Nitric Oxide Synthase", ["biomedical", "chemicals_and_drugs"], "一氧化氮合酶"),
                ("nitric_oxide_synthase_type_i", "Nitric Oxide Synthase Type I", ["biomedical", "chemicals_and_drugs"], "I型一氧化氮合酶"),
                ("nitric_oxide_synthase_type_ii", "Nitric Oxide Synthase Type II", ["biomedical", "chemicals_and_drugs"], "II型一氧化氮合酶"),
                ("nitric_oxide_synthase_type_iii", "Nitric Oxide Synthase Type III", ["biomedical", "chemicals_and_drugs"], "III型一氧化氮合酶"),
                ("nitrification", "Nitrification", ["biomedical", "phenomena_and_processes"], "硝化作用"),
                ("nitril", "Nitriles", ["biomedical", "chemicals_and_drugs"], "腈类"),
                ("nitrilotriacetic_acid", "Nitrilotriacetic Acid", ["biomedical", "chemicals_and_drugs"], "次氮基三乙酸"),
            ]
        )

    def test_exact_expansion_batch_632_adds_nitrite_and_nitro_compound_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nitrite_reductase_nad_p_h", "Nitrite Reductase (nad(p)h)", ["biomedical", "chemicals_and_drugs"], "亚硝酸还原酶(NAD(P)H)"),
                ("nitrite_reductase", "Nitrite Reductases", ["biomedical", "chemicals_and_drugs"], "亚硝酸还原酶"),
                ("nitrit", "Nitrites", ["biomedical", "chemicals_and_drugs"], "亚硝酸盐"),
                ("nitro_compound", "Nitro Compounds", ["biomedical", "chemicals_and_drugs"], "硝基化合物"),
                ("nitroanisole_o_demethylase", "Nitroanisole O-demethylase", ["biomedical", "chemicals_and_drugs"], "硝基苯甲醚O-去甲基化酶"),
                ("nitroarginine", "Nitroarginine", ["biomedical", "chemicals_and_drugs"], "硝基精氨酸"),
                ("nitrobacter", "Nitrobacter", ["biomedical", "organisms"], "硝化杆菌属"),
                ("nitrobenzen", "Nitrobenzenes", ["biomedical", "chemicals_and_drugs"], "硝基苯类"),
            ]
        )

    def test_exact_expansion_batch_633_adds_nitrobenzoate_nitrofuran_and_nitrogen_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nitrobenzoat", "Nitrobenzoates", ["biomedical", "chemicals_and_drugs"], "硝基苯甲酸盐"),
                ("nitroblue_tetrazolium", "Nitroblue Tetrazolium", ["biomedical", "chemicals_and_drugs"], "氮蓝四唑"),
                ("nitrofuran", "Nitrofurans", ["biomedical", "chemicals_and_drugs"], "硝基呋喃类"),
                ("nitrofurantoin", "Nitrofurantoin", ["biomedical", "chemicals_and_drugs"], "呋喃妥因"),
                ("nitrofurazone", "Nitrofurazone", ["biomedical", "chemicals_and_drugs"], "呋喃西林"),
                ("nitrogen__2", "Nitrogen", ["biomedical", "chemicals_and_drugs"], "氮元素"),
                ("nitrogen", "Nitrogen", ["materials_elements_and_compounds"], "氮元素"),
                ("nitrogen_and_sulfur_effect_on_brassica", "Nitrogen And Sulfur Effects On Brassica", ["biochemistry_genetics_and_molecular_biology", "life_sciences"], "氮和硫对芸薹属的影响"),
            ]
        )

    def test_exact_expansion_batch_634_adds_nitrogen_compound_cycle_and_fixation_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nitrogen_compound", "Nitrogen Compounds", ["materials_elements_and_compounds"], "氮化合物"),
                ("nitrogen_compound__2", "Nitrogen Compounds", ["biomedical", "chemicals_and_drugs"], "氮化合物"),
                ("nitrogen_cycle", "Nitrogen Cycle", ["biomedical", "phenomena_and_processes"], "氮循环"),
                ("nitrogen_dioxide", "Nitrogen Dioxide", ["biomedical", "chemicals_and_drugs"], "二氧化氮"),
                ("nitrogen_fixation", "Nitrogen Fixation", ["biomedical", "phenomena_and_processes"], "固氮"),
                ("nitrogen_isotop", "Nitrogen Isotopes", ["biomedical", "chemicals_and_drugs"], "氮同位素"),
                ("nitrogen_mustard_compound", "Nitrogen Mustard Compounds", ["biomedical", "chemicals_and_drugs"], "氮芥类化合物"),
                ("nitrogen_oxid", "Nitrogen Oxides", ["biomedical", "chemicals_and_drugs"], "氮氧化物"),
            ]
        )

    def test_exact_expansion_batch_635_adds_nitrogen_radioisotope_and_nitrogenase_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nitrogen_radioisotop", "Nitrogen Radioisotopes", ["biomedical", "chemicals_and_drugs"], "氮放射性同位素"),
                ("nitrogen_fixing_bacteria", "Nitrogen-fixing Bacteria", ["biomedical", "organisms"], "固氮细菌"),
                ("nitrogenase", "Nitrogenase", ["biomedical", "chemicals_and_drugs"], "固氮酶"),
                ("nitrogenou_group_transferase", "Nitrogenous Group Transferases", ["biomedical", "chemicals_and_drugs"], "含氮基团转移酶"),
            ]
        )

    def test_exact_expansion_batch_636_adds_nitroglycerin_and_nitrophenol_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nitroglycerin", "Nitroglycerin", ["biomedical", "chemicals_and_drugs"], "硝酸甘油"),
                ("nitrohydroxyiodophenylacetate", "Nitrohydroxyiodophenylacetate", ["biomedical", "chemicals_and_drugs"], "硝基羟基碘苯乙酸"),
                ("nitroimidazol", "Nitroimidazoles", ["biomedical", "chemicals_and_drugs"], "硝基咪唑类"),
                ("nitromifene", "Nitromifene", ["biomedical", "chemicals_and_drugs"], "硝米芬"),
                ("nitroparaffin", "Nitroparaffins", ["biomedical", "chemicals_and_drugs"], "硝基石蜡"),
                ("nitrophenol", "Nitrophenols", ["biomedical", "chemicals_and_drugs"], "硝基酚类"),
                ("nitrophenylgalactosid", "Nitrophenylgalactosides", ["biomedical", "chemicals_and_drugs"], "硝基苯基半乳糖苷"),
                ("nitroprusside", "Nitroprusside", ["biomedical", "chemicals_and_drugs"], "硝普化物"),
            ]
        )

    def test_exact_expansion_batch_637_adds_nitroquinoline_and_nitroso_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nitroquinolin", "Nitroquinolines", ["biomedical", "chemicals_and_drugs"], "硝基喹啉类"),
                ("nitroreductase", "Nitroreductases", ["biomedical", "chemicals_and_drugs"], "硝基还原酶"),
                ("nitrosamin", "Nitrosamines", ["biomedical", "chemicals_and_drugs"], "亚硝胺类"),
                ("nitrosation", "Nitrosation", ["biomedical", "phenomena_and_processes"], "亚硝化作用"),
                ("nitrosative_stress", "Nitrosative Stress", ["biomedical", "phenomena_and_processes"], "亚硝化应激"),
                ("nitroso_compound", "Nitroso Compounds", ["biomedical", "chemicals_and_drugs"], "亚硝基化合物"),
                ("nitrosoguanidin", "Nitrosoguanidines", ["biomedical", "chemicals_and_drugs"], "亚硝基胍类"),
                ("nitrosomethylurethane", "Nitrosomethylurethane", ["biomedical", "chemicals_and_drugs"], "N-亚硝基-N-甲基氨基甲酸乙酯"),
            ]
        )

    def test_exact_expansion_batch_638_adds_nitrosomonas_nitrous_and_nitrovin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nitrosomonadaceae", "Nitrosomonadaceae", ["biomedical", "organisms"], "亚硝化单胞菌科"),
                ("nitrosomona", "Nitrosomonas", ["biomedical", "organisms"], "亚硝化单胞菌属"),
                ("nitrosomona_europaea", "Nitrosomonas Europaea", ["biomedical", "organisms"], "欧洲亚硝化单胞菌"),
                ("nitrosourea_compound", "Nitrosourea Compounds", ["biomedical", "chemicals_and_drugs"], "亚硝基脲类化合物"),
                ("nitrospirae", "Nitrospirae", ["computer_science"], "硝化螺旋菌门"),
                ("nitrou_acid", "Nitrous Acid", ["biomedical", "chemicals_and_drugs"], "亚硝酸"),
                ("nitrou_oxide", "Nitrous Oxide", ["biomedical", "chemicals_and_drugs"], "一氧化二氮"),
                ("nitrovin", "Nitrovin", ["biomedical", "chemicals_and_drugs"], "硝呋烯腙"),
            ]
        )

    def test_exact_expansion_batch_639_adds_nitroxinil_nk_cell_and_nlms_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nitroxinil", "Nitroxinil", ["biomedical", "chemicals_and_drugs"], "硝碘酚腈"),
                ("nivolumab", "Nivolumab", ["biomedical", "chemicals_and_drugs"], "纳武利尤单抗"),
                ("nizatidine", "Nizatidine", ["biomedical", "chemicals_and_drugs"], "尼扎替丁"),
                ("nk_cell_lectin_like_receptor_subfamily_a", "NK Cell Lectin-like Receptor Subfamily A", ["biomedical", "chemicals_and_drugs"], "NK细胞凝集素样受体A亚家族"),
                ("nk_cell_lectin_like_receptor_subfamily_b", "NK Cell Lectin-like Receptor Subfamily B", ["biomedical", "chemicals_and_drugs"], "NK细胞凝集素样受体B亚家族"),
                ("nk_cell_lectin_like_receptor_subfamily_c", "NK Cell Lectin-like Receptor Subfamily C", ["biomedical", "chemicals_and_drugs"], "NK细胞凝集素样受体C亚家族"),
                ("nk_cell_lectin_like_receptor_subfamily_d", "NK Cell Lectin-like Receptor Subfamily D", ["biomedical", "chemicals_and_drugs"], "NK细胞凝集素样受体D亚家族"),
                ("nlms", "Nlms", ["computer_science"], "归一化LMS"),
            ]
        )

    def test_exact_expansion_batch_640_adds_nlr_nmr_and_no_reflow_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nlms_algorithm", "Nlms Algorithm", ["computer_science"], "归一化LMS算法"),
                ("nlr_family_pyrin_domain_containing_3_protein", "NLR Family, Pyrin Domain-containing 3 Protein", ["biomedical", "chemicals_and_drugs"], "NLR家族含PYRIN结构域蛋白3"),
                ("nlr_protein", "NLR Proteins", ["biomedical", "chemicals_and_drugs"], "NLR蛋白"),
                ("nm23_nucleoside_diphosphate_kinase", "NM23 Nucleoside Diphosphate Kinases", ["biomedical", "chemicals_and_drugs"], "NM23核苷二磷酸激酶"),
                ("nmr_spectroscopy_and_application", "NMR Spectroscopy And Applications", ["physical_sciences", "physics_and_astronomy"], "NMR光谱及应用"),
                ("no_observed_adverse_effect_level", "No-observed-adverse-effect Level", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "未观察到有害作用水平"),
                ("no_reflow_phenomenon", "No-reflow Phenomenon", ["biomedical", "diseases"], "无复流现象"),
                ("no_show_patient", "No-show Patients", ["biomedical", "psychiatry_and_psychology"], "失约患者"),
            ]
        )

    def test_exact_expansion_batch_641_adds_noc_and_nocardia_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nobelium", "Nobelium", ["biomedical", "chemicals_and_drugs"], "锘元素"),
                ("noble_gase", "Noble Gases", ["biomedical", "chemicals_and_drugs"], "稀有气体"),
                ("noc_architectur", "Noc Architectures", ["computer_science"], "NoC架构"),
                ("noc_design", "Noc Design", ["computer_science"], "NoC设计"),
                ("nocardia", "Nocardia", ["biomedical", "organisms"], "诺卡菌属"),
                ("nocardia_asteroid", "Nocardia Asteroides", ["biomedical", "organisms"], "星形诺卡菌"),
                ("nocardia_infection", "Nocardia Infections", ["biomedical", "diseases"], "诺卡菌感染"),
                ("nocardiaceae", "Nocardiaceae", ["biomedical", "organisms"], "诺卡菌科"),
            ]
        )

    def test_exact_expansion_batch_642_adds_nociception_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nocebo_effect", "Nocebo Effect", ["biomedical", "health_care"], "反安慰剂效应"),
                ("nociceptin", "Nociceptin", ["biomedical", "chemicals_and_drugs"], "伤害感受肽"),
                ("nociceptin_receptor", "Nociceptin Receptor", ["biomedical", "chemicals_and_drugs"], "伤害感受肽受体"),
                ("nociception", "Nociception", ["biomedical", "psychiatry_and_psychology"], "伤害感受"),
                ("nociceptive_pain", "Nociceptive Pain", ["biomedical", "diseases"], "伤害感受性疼痛"),
                ("nociceptor", "Nociceptors", ["anatomy", "biomedical"], "伤害感受器"),
                ("nociplastic_pain", "Nociplastic Pain", ["biomedical", "diseases"], "伤害可塑性疼痛"),
                ("nocodazole", "Nocodazole", ["biomedical", "chemicals_and_drugs"], "诺考达唑"),
            ]
        )

    def test_exact_expansion_batch_643_adds_nocturnal_and_nod_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nocturia", "Nocturia", ["biomedical", "diseases"], "夜尿症"),
                ("nocturnal_enuresi", "Nocturnal Enuresis", ["biomedical", "diseases"], "夜间遗尿"),
                ("nocturnal_myoclonu_syndrome", "Nocturnal Myoclonus Syndrome", ["biomedical", "diseases"], "夜间肌阵挛综合征"),
                ("nocturnal_paroxysmal_dystonia", "Nocturnal Paroxysmal Dystonia", ["biomedical", "diseases"], "夜间阵发性肌张力障碍"),
                ("nod1_signaling_adaptor_protein", "Nod1 Signaling Adaptor Protein", ["biomedical", "chemicals_and_drugs"], "NOD1信号接头蛋白"),
                ("nod2_signaling_adaptor_protein", "Nod2 Signaling Adaptor Protein", ["biomedical", "chemicals_and_drugs"], "NOD2信号接头蛋白"),
                ("nod_signaling_adaptor_protein", "Nod Signaling Adaptor Proteins", ["biomedical", "chemicals_and_drugs"], "NOD信号接头蛋白"),
                ("nodal_protein", "Nodal Protein", ["biomedical", "chemicals_and_drugs"], "Nodal蛋白"),
            ]
        )

    def test_exact_expansion_batch_644_adds_nodal_node_and_nogo_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nodal_signaling_ligand", "Nodal Signaling Ligands", ["biomedical", "chemicals_and_drugs"], "Nodal信号配体"),
                ("nodaviridae", "Nodaviridae", ["biomedical", "organisms"], "诺达病毒科"),
                ("nodding_syndrome", "Nodding Syndrome", ["biomedical", "diseases"], "点头综合征"),
                ("node_capture_attack", "Node Capture Attack", ["computer_science"], "节点捕获攻击"),
                ("node_disjoint", "Node-disjoint", ["computer_science"], "节点不相交"),
                ("node_disjoint_path", "Node-disjoint Paths", ["computer_science"], "节点不相交路径"),
                ("nodose_ganglion", "Nodose Ganglion", ["anatomy", "biomedical"], "结状神经节"),
                ("nogalamycin", "Nogalamycin", ["biomedical", "chemicals_and_drugs"], "诺加霉素"),
            ]
        )

    def test_exact_expansion_batch_645_adds_noggin_nogo_and_noise_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("noggin_protein", "Noggin Protein", ["biomedical", "chemicals_and_drugs"], "Noggin蛋白"),
                ("nogo_protein", "Nogo Proteins", ["biomedical", "chemicals_and_drugs"], "Nogo蛋白"),
                ("nogo_receptor", "Nogo Receptors", ["biomedical", "chemicals_and_drugs"], "Nogo受体"),
                ("nogo_receptor_1", "Nogo Receptor 1", ["biomedical", "chemicals_and_drugs"], "Nogo受体1"),
                ("nogo_receptor_2", "Nogo Receptor 2", ["biomedical", "chemicals_and_drugs"], "Nogo受体2"),
                ("noise_covariance_matrix", "Noise Covariance Matrix", ["computer_science"], "噪声协方差矩阵"),
                ("noise_figure", "Noise Figure", ["instrumentation_and_measurement"], "噪声系数"),
                ("noise_removal", "Noise Removal", ["computer_science"], "去噪"),
            ]
        )

    def test_exact_expansion_batch_646_adds_noise_shaping_and_noisy_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("noise_shaping", "Noise Shaping", ["instrumentation_and_measurement"], "噪声整形"),
                ("noise_shaping__2", "Noise Shaping", ["computer_science"], "噪声整形"),
                ("noise_subspace", "Noise Subspace", ["computer_science"], "噪声子空间"),
                ("noisy_environment", "Noisy Environment", ["computer_science"], "噪声环境"),
                ("noisy_image", "Noisy Image", ["computer_science"], "噪声图像"),
                ("noisy_pixel", "Noisy Pixels", ["computer_science"], "噪声像素"),
                ("noisy_speech", "Noisy Speech", ["computer_science"], "噪声语音"),
                ("noisy_speech_signal", "Noisy Speech Signals", ["computer_science"], "噪声语音信号"),
            ]
        )

    def test_exact_expansion_batch_647_adds_nomenclature_and_non_basic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nomenclature", "Nomenclature", ["computer_science"], "命名法"),
                ("nomifensine", "Nomifensine", ["biomedical", "chemicals_and_drugs"], "诺米芬辛"),
                ("nomogram", "Nomograms", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "列线图"),
                ("non_additive_measure", "Non-additive Measure", ["computer_science"], "非加性测度"),
                ("non_alcoholic_fatty_liver_disease", "Non-alcoholic Fatty Liver Disease", ["biomedical", "diseases"], "非酒精性脂肪性肝病"),
                ("non_coherent", "Non-coherent", ["computer_science"], "非相干"),
                ("non_coherent_receiver", "Non-coherent Receivers", ["computer_science"], "非相干接收机"),
                ("non_destructive_testing_techniqu", "Non-destructive Testing Techniques", ["engineering", "physical_sciences"], "无损检测技术"),
            ]
        )

    def test_exact_expansion_batch_648_adds_non_dominated_and_non_filarial_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("non_determinism", "Non-determinism", ["computer_science"], "非确定性"),
                ("non_dominated_sorting", "Non-dominated Sorting", ["computer_science"], "非支配排序"),
                ("non_dominated_sorting_genetic_algorithm", "Non-dominated Sorting Genetic Algorithms", ["computer_science"], "非支配排序遗传算法"),
                ("non_erosive_reflux_disease", "Non-erosive Reflux Disease", ["biomedical", "diseases"], "非糜烂性反流病"),
                ("non_fibrillar_collagen", "Non-fibrillar Collagens", ["biomedical", "chemicals_and_drugs"], "非纤维胶原"),
                ("non_filarial_lymphedema", "Non-filarial Lymphedema", ["biomedical", "diseases"], "非丝虫性淋巴水肿"),
                ("non_fragile", "Non-fragile", ["computer_science"], "非脆弱"),
                ("non_functional_requirement", "Non-functional Requirements", ["computer_science"], "非功能性需求"),
            ]
        )

    def test_exact_expansion_batch_649_adds_non_fungible_and_noninvasive_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("non_fungible_token", "Non-fungible Tokens", ["anthropology_education_sociology_and_social_phenomena", "biomedical"], "非同质化代币"),
                ("non_governmental_organization", "Non-governmental Organizations", ["engineering_management"], "非政府组织"),
                ("non_hermitian_system", "Non-hermitian Systems", ["physics"], "非厄米系统"),
                ("non_holonomic_mobile_robot", "Non-holonomic Mobile Robots", ["computer_science"], "非完整移动机器人"),
                ("non_homogeneou_poisson_process", "Non-homogeneous Poisson Process", ["computer_science"], "非齐次泊松过程"),
                ("non_invasive_vital_sign_monitoring", "Non-invasive Vital Sign Monitoring", ["engineering", "physical_sciences"], "非侵入式生命体征监测"),
                ("non_linear_observer", "Non-linear Observer", ["computer_science"], "非线性观测器"),
                ("non_local_mean", "Non-local Means", ["computer_science"], "非局部均值"),
            ]
        )

    def test_exact_expansion_batch_650_adds_non_melanoma_and_non_player_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("non_muscle_invasive_bladder_neoplasm", "Non-muscle Invasive Bladder Neoplasms", ["biomedical", "diseases"], "非肌层浸润性膀胱肿瘤"),
                ("non_neuronal_cholinergic_system", "Non-neuronal Cholinergic System", ["biomedical", "phenomena_and_processes"], "非神经元胆碱能系统"),
                ("non_nutritive_sweetener", "Non-nutritive Sweeteners", ["biomedical", "chemicals_and_drugs"], "非营养性甜味剂"),
                ("non_parametric_bayesian", "Non-parametric Bayesian", ["computer_science"], "非参数贝叶斯"),
                ("non_player_character", "Non-player Character", ["computer_science"], "非玩家角色"),
                ("non_radiographic_axial_spondyloarthriti", "Non-radiographic Axial Spondyloarthritis", ["biomedical", "diseases"], "非放射学中轴型脊柱关节炎"),
                ("non_regenerative", "Non-regenerative", ["computer_science"], "非再生"),
                ("non_rigid_registration", "Non-rigid Registration", ["computer_science"], "非刚性配准"),
            ]
        )

    def test_exact_expansion_batch_651_adds_non_smoker_and_nonvolatile_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("non_smoker", "Non-smokers", ["biomedical", "named_groups"], "非吸烟者"),
                ("non_st_elevated_myocardial_infarction", "Non-st Elevated Myocardial Infarction", ["biomedical", "diseases"], "非ST段抬高型心肌梗死"),
                ("non_stationary_environment", "Non-stationary Environment", ["computer_science"], "非平稳环境"),
                ("non_uniform_rational_b_splin", "Non-uniform Rational B-splines", ["computer_science"], "非均匀有理B样条"),
                ("non_volatile", "Non-volatile", ["computer_science"], "非易失性"),
                ("non_volatile_memory", "Non-volatile Memories", ["computer_science"], "非易失性存储器"),
                ("nonachlazine", "Nonachlazine", ["biomedical", "chemicals_and_drugs"], "诺那拉嗪"),
                ("nonagenarian", "Nonagenarians", ["biomedical", "named_groups"], "九旬老人"),
            ]
        )

    def test_exact_expansion_batch_652_adds_noncommunicable_and_nondeterministic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("noncoherent_detection", "Noncoherent Detection", ["computer_science"], "非相干检测"),
                ("noncommunicable_disease", "Noncommunicable Diseases", ["biomedical", "diseases"], "非传染性疾病"),
                ("noncommutative_and_quantum_gravity_theory", "Noncommutative And Quantum Gravity Theories", ["physical_sciences", "physics_and_astronomy"], "非交换与量子引力理论"),
                ("nonconvex", "Nonconvex", ["computer_science"], "非凸"),
                ("nondeterministic_automata", "Nondeterministic Automata", ["computer_science"], "非确定性自动机"),
                ("nondeterministic_finite_automaton", "Nondeterministic Finite Automaton", ["computer_science"], "非确定性有限自动机"),
                ("nondisjunction_genetic", "Nondisjunction, Genetic", ["biomedical", "diseases"], "遗传不分离"),
                ("nondominated_solution", "Nondominated Solutions", ["computer_science"], "非支配解"),
            ]
        )

    def test_exact_expansion_batch_653_adds_nonequilibrium_and_noninvasive_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nonequilibrium_statistical_mechanic", "Nonequilibrium Statistical Mechanics", ["physics"], "非平衡统计力学"),
                ("nonequilibrium_system", "Nonequilibrium Systems", ["physics"], "非平衡系统"),
                ("nonexpansive_mapping", "Nonexpansive Mapping", ["computer_science"], "非扩张映射"),
                ("nonfungible_token", "Nonfungible Tokens", ["computers_and_information_processing"], "非同质化代币"),
                ("nonheme_iron_protein", "Nonheme Iron Proteins", ["biomedical", "chemicals_and_drugs"], "非血红素铁蛋白"),
                ("nonholonomic_system", "Nonholonomic System", ["computer_science"], "非完整系统"),
                ("nonhomogeneou_media", "Nonhomogeneous Media", ["materials_elements_and_compounds"], "非均匀介质"),
                ("noninvasive_prenatal_testing", "Noninvasive Prenatal Testing", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "无创产前检测"),
            ]
        )

    def test_exact_expansion_batch_654_adds_noninvasive_and_nonlinear_missing_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("noninvasive_treatment", "Noninvasive Treatment", ["engineering_in_medicine_and_biology"], "无创治疗"),
                ("noninvasive_ventilation", "Noninvasive Ventilation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "无创通气"),
                ("nonlinear_control_laws", "Nonlinear Control Laws", ["computer_science"], "非线性控制律"),
                ("nonlinear_dimensionality_reduction", "Nonlinear Dimensionality Reduction", ["computer_science"], "非线性降维"),
                ("nonlinear_dynamical_system", "Nonlinear Dynamical Systems", ["mathematics"], "非线性动力系统"),
                ("nonlinear_manifold", "Nonlinear Manifolds", ["computer_science"], "非线性流形"),
                ("nonlinear_ordinary_differential_equation", "Nonlinear Ordinary Differential Equation", ["computer_science"], "非线性常微分方程"),
                ("nonlinear_perturbation", "Nonlinear Perturbations", ["computer_science"], "非线性扰动"),
            ]
        )

    def test_exact_expansion_batch_655_adds_nonlinear_physics_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nonlinear_schrodinger_equation", "Nonlinear Schrodinger Equation", ["computer_science"], "非线性薛定谔方程"),
                ("nonlinear_wav_and_soliton", "Nonlinear Waves And Solitons", ["physical_sciences", "physics_and_astronomy"], "非线性波与孤子"),
                ("nonlocal_and_gradient_elasticity_in_micro_nano_structur", "Nonlocal And Gradient Elasticity In Micro/nano Structures", ["materials_science", "physical_sciences"], "微纳结构中的非局部与梯度弹性"),
                ("nonmelanoma_skin_cancer_study", "Nonmelanoma Skin Cancer Studies", ["health_sciences", "medicine"], "非黑色素瘤皮肤癌研究"),
                ("nonmuscle_myosin_type_iia", "Nonmuscle Myosin Type IIA", ["biomedical", "chemicals_and_drugs"], "非肌肉肌球蛋白IIA型"),
                ("nonmuscle_myosin_type_iib", "Nonmuscle Myosin Type IIB", ["biomedical", "chemicals_and_drugs"], "非肌肉肌球蛋白IIB型"),
                ("nonnegative_integer", "Nonnegative Integers", ["computer_science"], "非负整数"),
                ("nonodontogenic_cyst", "Nonodontogenic Cysts", ["biomedical", "diseases"], "非牙源性囊肿"),
            ]
        )

    def test_exact_expansion_batch_656_adds_nonparametric_and_nonstationary_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nonoxynol", "Nonoxynol", ["biomedical", "chemicals_and_drugs"], "壬苯醇醚"),
                ("nonparametric_statistic", "Nonparametric Statistics", ["mathematics"], "非参数统计"),
                ("nonperturbative_method", "Nonperturbative Methods", ["physics"], "非微扰方法"),
                ("nonprescription_drug", "Nonprescription Drugs", ["biomedical", "chemicals_and_drugs"], "非处方药"),
                ("nonprofit_sector_and_volunteering", "Nonprofit Sector And Volunteering", ["social_sciences"], "非营利部门与志愿服务"),
                ("nonrigid_image_registration", "Nonrigid Image Registration", ["computer_science"], "非刚性图像配准"),
                ("nonsense_mediated_mrna_decay", "Nonsense Mediated Mrna Decay", ["biomedical", "phenomena_and_processes"], "无义介导的mRNA降解"),
                ("nonstationary_data", "Nonstationary Data", ["computer_science"], "非平稳数据"),
            ]
        )

    def test_exact_expansion_batch_657_adds_nonstationary_to_nonverbal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nonstationary_noise", "Nonstationary Noise", ["computer_science"], "非平稳噪声"),
                ("nonsteroidal_anti_androgen", "Nonsteroidal Anti-androgens", ["biomedical", "chemicals_and_drugs"], "非甾体抗雄激素"),
                ("nonsubsampled_contourlet_transform", "Nonsubsampled Contourlet Transforms", ["computer_science"], "非下采样轮廓波变换"),
                ("nontherapeutic_human_experimentation", "Nontherapeutic Human Experimentation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "非治疗性人体实验"),
                ("nontuberculou_mycobacteria", "Nontuberculous Mycobacteria", ["biomedical", "organisms"], "非结核分枝杆菌"),
                ("nonuniform_electric_field", "Nonuniform Electric Fields", ["dielectrics_and_electrical_insulation"], "非均匀电场"),
                ("nonuniform_sampling", "Nonuniform Sampling", ["mathematics"], "非均匀采样"),
                ("nonuniformity_correction", "Nonuniformity Correction", ["computer_science"], "非均匀性校正"),
            ]
        )

    def test_exact_expansion_batch_658_adds_nonverbal_and_nor_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nonverbal_behavior", "Nonverbal Behavior", ["computer_science"], "非言语行为"),
                ("nonverbal_communication", "Nonverbal Communication", ["biomedical", "psychiatry_and_psychology"], "非言语交流"),
                ("nonvolatile_memory", "Nonvolatile Memory", ["computers_and_information_processing"], "非易失性存储器"),
                ("nonvolatile_storage", "Nonvolatile Storage", ["computer_science"], "非易失性存储"),
                ("nonvolatility", "Nonvolatility", ["computer_science"], "非易失性"),
                ("noonan_syndrome", "Noonan Syndrome", ["biomedical", "diseases"], "努南综合征"),
                ("nootropic_agent", "Nootropic Agents", ["biomedical", "chemicals_and_drugs"], "益智药"),
                ("norandrostan", "Norandrostanes", ["biomedical", "chemicals_and_drugs"], "去甲雄烷类"),
            ]
        )

    def test_exact_expansion_batch_659_adds_norbornane_to_norfloxacin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("norbornan", "Norbornanes", ["biomedical", "chemicals_and_drugs"], "降冰片烷类"),
                ("nordazepam", "Nordazepam", ["biomedical", "chemicals_and_drugs"], "去甲地西泮"),
                ("nordic_walking", "Nordic Walking", ["biomedical", "phenomena_and_processes"], "北欧式健走"),
                ("norepinephrine", "Norepinephrine", ["biomedical", "chemicals_and_drugs"], "去甲肾上腺素"),
                ("norepinephrine_plasma_membrane_transport_protein", "Norepinephrine Plasma Membrane Transport Proteins", ["biomedical", "chemicals_and_drugs"], "去甲肾上腺素质膜转运蛋白"),
                ("norethindrone", "Norethindrone", ["biomedical", "chemicals_and_drugs"], "炔诺酮"),
                ("norethindrone_acetate", "Norethindrone Acetate", ["biomedical", "chemicals_and_drugs"], "醋酸炔诺酮"),
                ("norfloxacin", "Norfloxacin", ["biomedical", "chemicals_and_drugs"], "诺氟沙星"),
            ]
        )

    def test_exact_expansion_batch_660_adds_norgestrel_to_notch_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("norgestrel", "Norgestrel", ["biomedical", "chemicals_and_drugs"], "诺孕酯"),
                ("nortriptyline", "Nortriptyline", ["biomedical", "chemicals_and_drugs"], "去甲替林"),
                ("norwalk_viru", "Norwalk Virus", ["biomedical", "organisms"], "诺瓦克病毒"),
                ("norway", "Norway", ["biomedical", "geographicals"], "挪威"),
                ("nose_disease", "Nose Diseases", ["biomedical", "diseases"], "鼻部疾病"),
                ("nose_deformity_acquired", "Nose Deformities, Acquired", ["biomedical", "diseases"], "获得性鼻畸形"),
                ("nosocomial_infection_in_icu", "Nosocomial Infections In ICU", ["health_sciences", "medicine"], "ICU医院感染"),
                ("notch_filter", "Notch Filters", ["circuits_and_systems"], "陷波滤波器"),
            ]
        )

    def test_exact_expansion_batch_661_adds_normalized_nor_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("norm_bounded_uncertainty", "Norm-bounded Uncertainty", ["computer_science"], "范数有界不确定性"),
                ("normal_basi", "Normal Basis", ["computer_science"], "正规基"),
                ("normal_behavior", "Normal Behavior", ["computer_science"], "正常行为"),
                ("normalized_cross_correlation", "Normalized Cross Correlation", ["computer_science"], "归一化互相关"),
                ("normalized_cut", "Normalized Cuts", ["computer_science"], "归一化割"),
                ("normalized_difference_vegetation_index", "Normalized Difference Vegetation Index", ["environmental_measurement"], "归一化差异植被指数"),
                ("normalized_difference_water_index", "Normalized Difference Water Index", ["environmental_measurement"], "归一化差异水体指数"),
                ("normalized_least_mean_square", "Normalized Least Mean Square", ["computer_science"], "归一化最小均方"),
            ]
        )

    def test_exact_expansion_batch_662_adds_normetanephrine_to_north_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("normalized_mutual_information", "Normalized Mutual Information", ["computer_science"], "归一化互信息"),
                ("normetanephrine", "Normetanephrine", ["biomedical", "chemicals_and_drugs"], "去甲变肾上腺素"),
                ("noroviru", "Norovirus", ["biomedical", "organisms"], "诺如病毒"),
                ("norfenfluramine", "Norfenfluramine", ["biomedical", "chemicals_and_drugs"], "去甲芬氟拉明"),
                ("norgestrienone", "Norgestrienone", ["biomedical", "chemicals_and_drugs"], "诺孕三烯酮"),
                ("norleucine", "Norleucine", ["biomedical", "chemicals_and_drugs"], "正亮氨酸"),
                ("north_african_history_and_literature", "North African History And Literature", ["arts_and_humanities", "social_sciences"], "北非历史与文学"),
                ("north_african_people", "North African People", ["biomedical", "named_groups"], "北非人群"),
            ]
        )

    def test_exact_expansion_batch_663_adds_north_geography_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("north_america", "North America", ["change"], "北美"),
                ("north_american_people", "North American People", ["biomedical", "named_groups"], "北美人群"),
                ("north_asian_people", "North Asian People", ["biomedical", "named_groups"], "北亚人群"),
                ("north_carolina", "North Carolina", ["biomedical", "geographicals"], "北卡罗来纳州"),
                ("north_dakota", "North Dakota", ["biomedical", "geographicals"], "北达科他州"),
                ("north_pole", "North Pole", ["science_general"], "北极"),
                ("north_sea", "North Sea", ["biomedical", "geographicals"], "北海"),
                ("northern_ireland", "Northern Ireland", ["biomedical", "geographicals"], "北爱尔兰"),
            ]
        )

    def test_exact_expansion_batch_664_adds_northern_to_nose_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("northern_territory", "Northern Territory", ["biomedical", "geographicals"], "北领地"),
                ("northwest_territory", "Northwest Territories", ["biomedical", "geographicals"], "西北地区"),
                ("northwestern_united_stat", "Northwestern United States", ["biomedical", "geographicals"], "美国西北部"),
                ("nortropan", "Nortropanes", ["biomedical", "chemicals_and_drugs"], "去甲托烷类"),
                ("norwood_procedur", "Norwood Procedures", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "诺伍德手术"),
                ("noscapine", "Noscapine", ["biomedical", "chemicals_and_drugs"], "那可汀"),
                ("nose", "Nose", ["anatomy", "biomedical"], "鼻部"),
                ("nose_neoplasm", "Nose Neoplasms", ["biomedical", "diseases"], "鼻肿瘤"),
            ]
        )

    def test_exact_expansion_batch_665_adds_nostoc_to_nuchal_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nosema", "Nosema", ["biomedical", "organisms"], "微孢子虫属"),
                ("nosql", "Nosql", ["computer_science"], "NoSQL技术"),
                ("nosql_database", "Nosql Databases", ["professional_communication"], "NoSQL数据库"),
                ("nostalgia_and_consumer_behavior", "Nostalgia And Consumer Behavior", ["psychology", "social_sciences"], "怀旧与消费者行为"),
                ("nostoc", "Nostoc", ["biomedical", "organisms"], "念珠藻属"),
                ("nostoc_commune", "Nostoc Commune", ["biomedical", "organisms"], "普通念珠藻"),
                ("notochord", "Notochord", ["anatomy", "biomedical"], "脊索"),
                ("nuchal_cord", "Nuchal Cord", ["biomedical", "diseases"], "脐带绕颈"),
            ]
        )

    def test_exact_expansion_batch_666_adds_nuchal_to_nuclear_basic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nuchal_translucency_measurement", "Nuchal Translucency Measurement", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "颈项透明层测量"),
                ("nuclear_and_plasma_scienc", "Nuclear And Plasma Sciences", ["nuclear_and_plasma_sciences"], "核与等离子体科学"),
                ("nuclear_astrophysic", "Nuclear Astrophysics", ["physics"], "核天体物理学"),
                ("nuclear_body", "Nuclear Bodies", ["anatomy", "biomedical"], "核体"),
                ("nuclear_cap_binding_protein_complex", "Nuclear Cap-binding Protein Complex", ["biomedical", "chemicals_and_drugs"], "核帽结合蛋白复合体"),
                ("nuclear_data_analysi_and_compilation", "Nuclear Data Analysis & Compilation", ["physics"], "核数据分析与汇编"),
                ("nuclear_density_functional_theory", "Nuclear Density Functional Theory", ["physics"], "核密度泛函理论"),
                ("nuclear_electronic", "Nuclear Electronics", ["nuclear_and_plasma_sciences"], "核电子学"),
            ]
        )

    def test_exact_expansion_batch_667_adds_nuclear_energy_to_factor_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nuclear_energy", "Nuclear Energy", ["power_engineering_and_energy"], "核能"),
                ("nuclear_engineering", "Nuclear Engineering", ["physics"], "核工程"),
                ("nuclear_engineering_thermal_hydraulic", "Nuclear Engineering Thermal-hydraulics", ["engineering", "physical_sciences"], "核工程热工水力学"),
                ("nuclear_envelope", "Nuclear Envelope", ["anatomy", "biomedical"], "核膜"),
                ("nuclear_experiment", "Nuclear Experiment", ["nuclear_physics"], "核实验"),
                ("nuclear_explosion", "Nuclear Explosions", ["computer_science"], "核爆炸"),
                ("nuclear_export_signal", "Nuclear Export Signals", ["biomedical", "chemicals_and_drugs"], "核输出信号"),
                ("nuclear_factor_45_protein", "Nuclear Factor 45 Protein", ["biomedical", "chemicals_and_drugs"], "核因子45蛋白"),
            ]
        )

    def test_exact_expansion_batch_668_adds_nuclear_factor_to_imaging_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nuclear_factor_90_protein", "Nuclear Factor 90 Proteins", ["biomedical", "chemicals_and_drugs"], "核因子90蛋白"),
                ("nuclear_facility_regulation", "Nuclear Facility Regulation", ["industry_applications"], "核设施监管"),
                ("nuclear_family", "Nuclear Family", ["biomedical", "psychiatry_and_psychology"], "核心家庭"),
                ("nuclear_fission", "Nuclear Fission", ["biomedical", "phenomena_and_processes"], "核裂变"),
                ("nuclear_fusion", "Nuclear Fusion", ["biomedical", "phenomena_and_processes"], "核聚变"),
                ("nuclear_imaging", "Nuclear Imaging", ["imaging"], "核成像"),
                ("nuclear_issu_and_defense", "Nuclear Issues And Defense", ["social_sciences"], "核问题与防务"),
                ("nuclear_lamina", "Nuclear Lamina", ["anatomy", "biomedical"], "核纤层"),
            ]
        )

    def test_exact_expansion_batch_669_adds_nuclear_localization_to_medicine_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nuclear_localization_signal", "Nuclear Localization Signals", ["biomedical", "chemicals_and_drugs"], "核定位信号"),
                ("nuclear_magnetic_resonance", "Nuclear Magnetic Resonance", ["resonance"], "核磁共振"),
                ("nuclear_magnetic_resonance_biomolecular", "Nuclear Magnetic Resonance, Biomolecular", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "生物分子核磁共振"),
                ("nuclear_many_body_theory", "Nuclear Many-body Theory", ["physics"], "核多体理论"),
                ("nuclear_material_and_property", "Nuclear Materials And Properties", ["materials_science", "physical_sciences"], "核材料与性能"),
                ("nuclear_material_and_radiation_effect", "Nuclear Materials And Radiation Effects", ["materials_science", "physical_sciences"], "核材料与辐射效应"),
                ("nuclear_matrix", "Nuclear Matrix", ["anatomy", "biomedical"], "核基质"),
                ("nuclear_medicine_department_hospital", "Nuclear Medicine Department, Hospital", ["biomedical", "health_care"], "医院核医学科"),
            ]
        )

    def test_exact_expansion_batch_670_adds_nuclear_microscopy_to_reactor_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nuclear_microscopy", "Nuclear Microscopy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "核显微术"),
                ("nuclear_pharmacy", "Nuclear Pharmacy", ["biomedical", "disciplines_and_occupations"], "核药学"),
                ("nuclear_phase_transformation", "Nuclear Phase Transformations", ["nuclear_and_plasma_sciences"], "核相变"),
                ("nuclear_physic", "Nuclear Physics", ["nuclear_and_plasma_sciences"], "核物理学"),
                ("nuclear_plant", "Nuclear Plant", ["computer_science"], "核电站"),
                ("nuclear_pore", "Nuclear Pore", ["anatomy", "biomedical"], "核孔"),
                ("nuclear_pore_complex_protein", "Nuclear Pore Complex Proteins", ["biomedical", "chemicals_and_drugs"], "核孔复合体蛋白"),
                ("nuclear_reactor", "Nuclear Reactors", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "核反应堆"),
            ]
        )

    def test_exact_expansion_batch_671_adds_nuclear_reactor_to_receptor_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nuclear_reactor_accident", "Nuclear Reactor Accidents", ["computer_science"], "核反应堆事故"),
                ("nuclear_reactor_physic_and_engineering", "Nuclear Reactor Physics And Engineering", ["engineering", "physical_sciences"], "核反应堆物理与工程"),
                ("nuclear_receptor_and_signaling", "Nuclear Receptors And Signaling", ["life_sciences", "neuroscience"], "核受体与信号传导"),
                ("nuclear_receptor_co_repressor_1", "Nuclear Receptor Co-repressor 1", ["biomedical", "chemicals_and_drugs"], "核受体共抑制因子1"),
                ("nuclear_receptor_co_repressor_2", "Nuclear Receptor Co-repressor 2", ["biomedical", "chemicals_and_drugs"], "核受体共抑制因子2"),
                ("nuclear_receptor_coactivator", "Nuclear Receptor Coactivators", ["biomedical", "chemicals_and_drugs"], "核受体共激活因子"),
                ("nuclear_receptor_coactivator_1", "Nuclear Receptor Coactivator 1", ["biomedical", "chemicals_and_drugs"], "核受体共激活因子1"),
                ("nuclear_receptor_coactivator_2", "Nuclear Receptor Coactivator 2", ["biomedical", "chemicals_and_drugs"], "核受体共激活因子2"),
            ]
        )

    def test_exact_expansion_batch_672_adds_nuclear_receptor_subfamily_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nuclear_receptor_coactivator_3", "Nuclear Receptor Coactivator 3", ["biomedical", "chemicals_and_drugs"], "核受体共激活因子3"),
                ("nuclear_receptor_interacting_protein_1", "Nuclear Receptor Interacting Protein 1", ["biomedical", "chemicals_and_drugs"], "核受体相互作用蛋白1"),
                ("nuclear_receptor_subfamily_1_group_d_member_1", "Nuclear Receptor Subfamily 1, Group D, Member 1", ["biomedical", "chemicals_and_drugs"], "核受体亚家族1D组成员1"),
                ("nuclear_receptor_subfamily_1_group_f_member_1", "Nuclear Receptor Subfamily 1, Group F, Member 1", ["biomedical", "chemicals_and_drugs"], "核受体亚家族1F组成员1"),
                ("nuclear_receptor_subfamily_1_group_f_member_2", "Nuclear Receptor Subfamily 1, Group F, Member 2", ["biomedical", "chemicals_and_drugs"], "核受体亚家族1F组成员2"),
                ("nuclear_receptor_subfamily_1_group_f_member_3", "Nuclear Receptor Subfamily 1, Group F, Member 3", ["biomedical", "chemicals_and_drugs"], "核受体亚家族1F组成员3"),
                ("nuclear_receptor_subfamily_2_group_c_member_1", "Nuclear Receptor Subfamily 2, Group C, Member 1", ["biomedical", "chemicals_and_drugs"], "核受体亚家族2C组成员1"),
                ("nuclear_receptor_subfamily_2_group_c_member_2", "Nuclear Receptor Subfamily 2, Group C, Member 2", ["biomedical", "chemicals_and_drugs"], "核受体亚家族2C组成员2"),
            ]
        )

    def test_exact_expansion_batch_673_adds_nuclear_receptor_to_warfare_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nuclear_receptor_subfamily_4_group_a_member_1", "Nuclear Receptor Subfamily 4, Group A, Member 1", ["biomedical", "chemicals_and_drugs"], "核受体亚家族4A组成员1"),
                ("nuclear_receptor_subfamily_4_group_a_member_2", "Nuclear Receptor Subfamily 4, Group A, Member 2", ["biomedical", "chemicals_and_drugs"], "核受体亚家族4A组成员2"),
                ("nuclear_receptor_subfamily_4_group_a_member_3", "Nuclear Receptor Subfamily 4, Group A, Member 3", ["biomedical", "chemicals_and_drugs"], "核受体亚家族4A组成员3"),
                ("nuclear_receptor_subfamily_6_group_a_member_1", "Nuclear Receptor Subfamily 6, Group A, Member 1", ["biomedical", "chemicals_and_drugs"], "核受体亚家族6A组成员1"),
                ("nuclear_speckl", "Nuclear Speckles", ["anatomy", "biomedical"], "核斑"),
                ("nuclear_structure_and_function", "Nuclear Structure And Function", ["biochemistry_genetics_and_molecular_biology", "life_sciences"], "核结构与功能"),
                ("nuclear_transfer_techniqu", "Nuclear Transfer Techniques", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "核移植技术"),
                ("nuclear_warfare", "Nuclear Warfare", ["anthropology_education_sociology_and_social_phenomena", "biomedical"], "核战争"),
            ]
        )

    def test_exact_expansion_batch_674_adds_nuclear_weapon_to_nucleic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nuclear_weapon", "Nuclear Weapons", ["aerospace_and_electronic_systems"], "核武器"),
                ("nuclease_protection_assay", "Nuclease Protection Assays", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "核酸酶保护实验"),
                ("nucleic_acid_amplification_techniqu", "Nucleic Acid Amplification Techniques", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "核酸扩增技术"),
                ("nucleic_acid_based_vaccin", "Nucleic Acid-based Vaccines", ["biomedical", "chemicals_and_drugs"], "核酸疫苗"),
                ("nucleic_acid_conformation", "Nucleic Acid Conformation", ["biomedical", "phenomena_and_processes"], "核酸构象"),
                ("nucleic_acid_denaturation", "Nucleic Acid Denaturation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "核酸变性"),
                ("nucleic_acid_heteroduplexe", "Nucleic Acid Heteroduplexes", ["biomedical", "chemicals_and_drugs"], "核酸异源双链"),
                ("nucleic_acid_nucleotid_and_nucleosid", "Nucleic Acids, Nucleotides, And Nucleosides", ["biomedical", "chemicals_and_drugs"], "核酸、核苷酸和核苷"),
            ]
        )

    def test_exact_expansion_batch_675_adds_nucleic_probe_to_nucleolin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nucleic_acid_precursor", "Nucleic Acid Precursors", ["biomedical", "chemicals_and_drugs"], "核酸前体"),
                ("nucleic_acid_prob", "Nucleic Acid Probes", ["biomedical", "chemicals_and_drugs"], "核酸探针"),
                ("nucleic_acid_renaturation", "Nucleic Acid Renaturation", ["biomedical", "phenomena_and_processes"], "核酸复性"),
                ("nucleobase_transport_protein", "Nucleobase Transport Proteins", ["biomedical", "chemicals_and_drugs"], "核碱基转运蛋白"),
                ("nucleocapsid", "Nucleocapsid", ["anatomy", "biomedical"], "核衣壳"),
                ("nucleocapsid_protein", "Nucleocapsid Proteins", ["biomedical", "chemicals_and_drugs"], "核衣壳蛋白"),
                ("nucleocytoplasmic_transport_protein", "Nucleocytoplasmic Transport Proteins", ["biomedical", "chemicals_and_drugs"], "核质转运蛋白"),
                ("nucleolin", "Nucleolin", ["biomedical", "chemicals_and_drugs"], "核仁素"),
            ]
        )

    def test_exact_expansion_batch_676_adds_nucleolus_to_nucleoside_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nucleolu_organizer_region", "Nucleolus Organizer Region", ["anatomy", "biomedical"], "核仁组织区"),
                ("nucleon", "Nucleons", ["biomedical", "phenomena_and_processes"], "核子"),
                ("nucleophosmin", "Nucleophosmin", ["biomedical", "chemicals_and_drugs"], "核磷蛋白"),
                ("nucleoprotein", "Nucleoproteins", ["biomedical", "chemicals_and_drugs"], "核蛋白"),
                ("nucleosid", "Nucleosides", ["biomedical", "chemicals_and_drugs"], "核苷"),
                ("nucleoside_deaminase", "Nucleoside Deaminases", ["biomedical", "chemicals_and_drugs"], "核苷脱氨酶"),
                ("nucleoside_diphosphate_kinase", "Nucleoside-diphosphate Kinase", ["biomedical", "chemicals_and_drugs"], "核苷二磷酸激酶"),
                ("nucleoside_diphosphate_sugar", "Nucleoside Diphosphate Sugars", ["biomedical", "chemicals_and_drugs"], "核苷二磷酸糖"),
            ]
        )

    def test_exact_expansion_batch_677_adds_nucleoside_to_nucleus_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nucleoside_phosphate_kinase", "Nucleoside-phosphate Kinase", ["biomedical", "chemicals_and_drugs"], "核苷磷酸激酶"),
                ("nucleoside_transport_protein", "Nucleoside Transport Proteins", ["biomedical", "chemicals_and_drugs"], "核苷转运蛋白"),
                ("nucleoside_triphosphatase", "Nucleoside-triphosphatase", ["biomedical", "chemicals_and_drugs"], "核苷三磷酸酶"),
                ("nucleosom", "Nucleosomes", ["anatomy", "biomedical"], "核小体"),
                ("nucleosome_assembly_protein_1", "Nucleosome Assembly Protein 1", ["biomedical", "chemicals_and_drugs"], "核小体组装蛋白1"),
                ("nucleotid_cyclic", "Nucleotides, Cyclic", ["biomedical", "chemicals_and_drugs"], "环核苷酸"),
                ("nucleotidase", "Nucleotidases", ["biomedical", "chemicals_and_drugs"], "核苷酸酶"),
                ("nucleotide_deaminase", "Nucleotide Deaminases", ["biomedical", "chemicals_and_drugs"], "核苷酸脱氨酶"),
            ]
        )

    def test_exact_expansion_batch_678_adds_nucleotide_to_null_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nucleotide_motif", "Nucleotide Motifs", ["biomedical", "phenomena_and_processes"], "核苷酸基序"),
                ("nucleotide_transport_protein", "Nucleotide Transport Proteins", ["biomedical", "chemicals_and_drugs"], "核苷酸转运蛋白"),
                ("nucleotidyltransferase", "Nucleotidyltransferases", ["biomedical", "chemicals_and_drugs"], "核苷酸转移酶"),
                ("nucleu_accumben", "Nucleus Accumbens", ["anatomy", "biomedical"], "伏隔核"),
                ("nucleu_pulposu", "Nucleus Pulposus", ["anatomy", "biomedical"], "髓核"),
                ("nudix_hydrolase", "Nudix Hydrolases", ["biomedical", "chemicals_and_drugs"], "Nudix水解酶"),
                ("null_space", "Null Space", ["mathematics"], "零空间"),
                ("null_value", "Null Value", ["computers_and_information_processing"], "空值"),
            ]
        )

    def test_exact_expansion_batch_679_adds_number_and_numerical_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("number_needed_to_treat", "Numbers Needed To Treat", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "需治数"),
                ("number_of_cluster", "Number Of Clusters", ["computer_science"], "聚类数"),
                ("number_of_hops", "Number Of Hops", ["computer_science"], "跳数"),
                ("number_of_state", "Number Of State", ["computer_science"], "状态数"),
                ("number_of_thread", "Number Of Threads", ["computer_science"], "线程数"),
                ("number_of_vehicl", "Number Of Vehicles", ["computer_science"], "车辆数"),
                ("numerical_analysi_computer_assisted", "Numerical Analysis, Computer-assisted", ["computer_science"], "计算机辅助数值分析"),
                ("numerical_control", "Numerical Control", ["computer_science"], "数控"),
            ]
        )

    def test_exact_expansion_batch_680_adds_numerical_method_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("numerical_control_system", "Numerical Control Systems", ["computer_science"], "数控系统"),
                ("numerical_experiment", "Numerical Experiments", ["computer_science"], "数值实验"),
                ("numerical_integration", "Numerical Integration", ["computer_science"], "数值积分"),
                ("numerical_integration_method", "Numerical Integration Methods", ["computer_science"], "数值积分方法"),
                ("numerical_method_for_differential_equation", "Numerical Methods For Differential Equations", ["mathematics", "physical_sciences"], "微分方程数值方法"),
                ("numerical_model", "Numerical Models", ["systems_engineering_and_theory"], "数值模型"),
                ("numerical_scheme", "Numerical Scheme", ["computer_science"], "数值格式"),
                ("numerical_solution", "Numerical Solution", ["computer_science"], "数值解"),
            ]
        )

    def test_exact_expansion_batch_681_adds_nurbs_and_nurse_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nurb", "Nurbs", ["computer_science"], "非均匀有理B样条"),
                ("nurb_curv", "Nurbs Curves", ["computer_science"], "NURBS曲线"),
                ("nurb_surface", "Nurbs Surface", ["computer_science"], "NURBS曲面"),
                ("nurse_administrator", "Nurse Administrators", ["biomedical", "named_groups"], "护理管理人员"),
                ("nurse_anesthetist", "Nurse Anesthetists", ["biomedical", "named_groups"], "护士麻醉师"),
                ("nurse_clinician", "Nurse Clinicians", ["biomedical", "named_groups"], "临床护士"),
                ("nurse_community_health", "Nurses, Community Health", ["biomedical", "named_groups"], "社区卫生护士"),
                ("nurse_midwiv", "Nurse Midwives", ["biomedical", "named_groups"], "助产士"),
            ]
        )

    def test_exact_expansion_batch_682_adds_nurse_role_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nurse_neonatal", "Nurses, Neonatal", ["biomedical", "named_groups"], "新生儿护士"),
                ("nurse_patient_relation", "Nurse-patient Relations", ["biomedical", "psychiatry_and_psychology"], "护患关系"),
                ("nurse_pediatric", "Nurses, Pediatric", ["biomedical", "named_groups"], "儿科护士"),
                ("nurse_practitioner", "Nurse Practitioners", ["biomedical", "named_groups"], "执业护士"),
                ("nurse_public_health", "Nurses, Public Health", ["biomedical", "named_groups"], "公共卫生护士"),
                ("nurse_s_role", "Nurse's Role", ["biomedical", "psychiatry_and_psychology"], "护士角色"),
                ("nurse_specialist", "Nurse Specialists", ["biomedical", "named_groups"], "专科护士"),
                ("nursery_hospital", "Nurseries, Hospital", ["biomedical", "health_care"], "医院育婴室"),
            ]
        )

    def test_exact_expansion_batch_683_adds_nursing_care_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nursing_assistant", "Nursing Assistants", ["biomedical", "named_groups"], "护理助理"),
                ("nursing_audit", "Nursing Audit", ["biomedical", "health_care"], "护理审计"),
                ("nursing_care", "Nursing Care", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "护理照护"),
                ("nursing_care_and_research", "Nursing Care And Research", ["health_professions", "health_sciences"], "护理照护与研究"),
                ("nursing_diagnosi", "Nursing Diagnosis", ["biomedical", "health_care"], "护理诊断"),
                ("nursing_diagnosi_and_documentation", "Nursing Diagnosis And Documentation", ["health_sciences", "nursing"], "护理诊断与文书记录"),
                ("nursing_education_and_management", "Nursing Education And Management", ["health_sciences", "nursing"], "护理教育与管理"),
                ("nursing_education_practice_and_leadership", "Nursing Education, Practice, And Leadership", ["health_sciences", "nursing"], "护理教育、实践与领导力"),
            ]
        )

    def test_exact_expansion_batch_684_adds_nursing_education_to_process_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nursing_education_research", "Nursing Education Research", ["biomedical", "disciplines_and_occupations"], "护理教育研究"),
                ("nursing_evaluation_research", "Nursing Evaluation Research", ["biomedical", "disciplines_and_occupations"], "护理评价研究"),
                ("nursing_faculty_practice", "Nursing Faculty Practice", ["biomedical", "health_care"], "护理教师实践"),
                ("nursing_home_resident", "Nursing Home Residents", ["biomedical", "named_groups"], "养老院居民"),
                ("nursing_informatic", "Nursing Informatics", ["biomedical", "information_science"], "护理信息学"),
                ("nursing_practical", "Nursing, Practical", ["biomedical", "disciplines_and_occupations"], "实用护理"),
                ("nursing_private_duty", "Nursing, Private Duty", ["biomedical", "health_care"], "私人护理"),
                ("nursing_process", "Nursing Process", ["biomedical", "health_care"], "护理程序"),
            ]
        )

    def test_exact_expansion_batch_685_adds_nursing_record_to_station_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nursing_record", "Nursing Records", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "护理记录"),
                ("nursing_research", "Nursing Research", ["biomedical", "disciplines_and_occupations"], "护理研究"),
                ("nursing_rol_and_practic", "Nursing Roles And Practices", ["health_professions", "health_sciences"], "护理角色与实践"),
                ("nursing_servic", "Nursing Services", ["biomedical", "health_care"], "护理服务"),
                ("nursing_service_hospital", "Nursing Service, Hospital", ["biomedical", "health_care"], "医院护理服务"),
                ("nursing_staff", "Nursing Staff", ["biomedical", "named_groups"], "护理人员"),
                ("nursing_staff_hospital", "Nursing Staff, Hospital", ["biomedical", "named_groups"], "医院护理人员"),
                ("nursing_station", "Nursing Stations", ["biomedical", "health_care"], "护士站"),
            ]
        )

    def test_exact_expansion_batch_686_adds_nursing_and_nutrition_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nursing_supervisory", "Nursing, Supervisory", ["biomedical", "health_care"], "护理监督"),
                ("nursing_team", "Nursing, Team", ["biomedical", "health_care"], "护理团队"),
                ("nursing_theory", "Nursing Theory", ["biomedical", "disciplines_and_occupations"], "护理理论"),
                ("nut_and_peanut_hypersensitivity", "Nut And Peanut Hypersensitivity", ["biomedical", "diseases"], "坚果和花生超敏反应"),
                ("nut_hypersensitivity", "Nut Hypersensitivity", ["biomedical", "diseases"], "坚果超敏反应"),
                ("nut_protein", "Nut Proteins", ["biomedical", "chemicals_and_drugs"], "坚果蛋白"),
                ("nutrigenomic", "Nutrigenomics", ["biomedical", "disciplines_and_occupations"], "营养基因组学"),
                ("nutrition_and_health_in_aging", "Nutrition And Health In Aging", ["health_sciences", "medicine"], "老龄化中的营养与健康"),
            ]
        )

    def test_exact_expansion_batch_687_adds_nutrition_study_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nutrition_and_health_study", "Nutrition And Health Studies", ["health_sciences", "medicine"], "营养与健康研究"),
                ("nutrition_assessment", "Nutrition Assessment", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "营养评估"),
                ("nutrition_disorder", "Nutrition Disorders", ["biomedical", "diseases"], "营养障碍"),
                ("nutrition_genetic_and_disease", "Nutrition, Genetics, And Disease", ["biochemistry_genetics_and_molecular_biology", "life_sciences"], "营养、遗传与疾病"),
                ("nutrition_health_and_food_behavior", "Nutrition, Health And Food Behavior", ["health_sciences", "nursing"], "营养、健康与食物行为"),
                ("nutrition_health_and_society_study", "Nutrition, Health, And Society Studies", ["agricultural_and_biological_sciences", "life_sciences"], "营养、健康与社会研究"),
                ("nutrition_policy", "Nutrition Policy", ["anthropology_education_sociology_and_social_phenomena", "biomedical"], "营养政策"),
                ("nutrition_survey", "Nutrition Surveys", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "营养调查"),
            ]
        )

    def test_exact_expansion_batch_688_adds_nutritional_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nutrition_therapy", "Nutrition Therapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "营养治疗"),
                ("nutritional_and_metabolic_disease", "Nutritional And Metabolic Diseases", ["biomedical", "diseases"], "营养与代谢性疾病"),
                ("nutritional_physiological_phenomena", "Nutritional Physiological Phenomena", ["biomedical", "phenomena_and_processes"], "营养生理现象"),
                ("nutritional_requirement", "Nutritional Requirements", ["biomedical", "phenomena_and_processes"], "营养需求"),
                ("nutritional_scienc", "Nutritional Sciences", ["biomedical", "disciplines_and_occupations"], "营养科学"),
                ("nutritional_statu", "Nutritional Status", ["biomedical", "phenomena_and_processes"], "营养状况"),
                ("nutritional_study_and_diet", "Nutritional Studies And Diet", ["health_sciences", "medicine"], "营养研究与饮食"),
                ("nutritional_support", "Nutritional Support", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "营养支持"),
            ]
        )

    def test_exact_expansion_batch_689_adds_nutritive_and_nystagmus_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("nutritionist", "Nutritionists", ["biomedical", "named_groups"], "营养师"),
                ("nutritive_sweetener", "Nutritive Sweeteners", ["biomedical", "chemicals_and_drugs"], "营养性甜味剂"),
                ("nutritive_value", "Nutritive Value", ["biomedical", "phenomena_and_processes"], "营养价值"),
                ("nuts", "Nuts", ["anatomy", "biomedical"], "坚果"),
                ("nuts_composition_and_effect", "Nuts Composition And Effects", ["health_sciences", "nursing"], "坚果组成与作用"),
                ("nylon", "Nylons", ["biomedical", "chemicals_and_drugs"], "尼龙类"),
                ("nystagmu_congenital", "Nystagmus, Congenital", ["biomedical", "diseases"], "先天性眼球震颤"),
                ("nystatin", "Nystatin", ["biomedical", "chemicals_and_drugs"], "制霉菌素"),
            ]
        )

    def test_exact_expansion_batch_690_adds_o_antigen_and_obesity_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("o_6_methylguanine_dna_methyltransferase", "O(6)-methylguanine-dna Methyltransferase", ["biomedical", "chemicals_and_drugs"], "O6-甲基鸟嘌呤DNA甲基转移酶"),
                ("o_antigen", "O Antigens", ["biomedical", "chemicals_and_drugs"], "O抗原"),
                ("o_nyong_nyong_viru", "O'nyong-nyong Virus", ["biomedical", "organisms"], "奥尼昂尼昂病毒"),
                ("o_phthalaldehyde", "O-phthalaldehyde", ["biomedical", "chemicals_and_drugs"], "邻苯二甲醛"),
                ("obesity_abdominal", "Obesity, Abdominal", ["biomedical", "diseases"], "腹型肥胖"),
                ("obesity_hypoventilation_syndrome", "Obesity Hypoventilation Syndrome", ["biomedical", "diseases"], "肥胖低通气综合征"),
                ("obesity_morbid", "Obesity, Morbid", ["biomedical", "diseases"], "病态肥胖"),
                ("obesity_paradox", "Obesity Paradox", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "肥胖悖论"),
            ]
        )

    def test_exact_expansion_batch_691_adds_obfuscation_and_object_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("obfuscation", "Obfuscation", ["computer_science"], "混淆"),
                ("obidoxime_chloride", "Obidoxime Chloride", ["biomedical", "chemicals_and_drugs"], "氯解磷定"),
                ("object_appearance", "Object Appearance", ["computer_science"], "目标外观"),
                ("object_attachment", "Object Attachment", ["biomedical", "psychiatry_and_psychology"], "客体依恋"),
                ("object_classification", "Object Classification", ["computer_science"], "目标分类"),
                ("object_constraint_language", "Object Constraint Language", ["computer_science"], "对象约束语言"),
                ("object_contour", "Object Contour", ["computer_science"], "目标轮廓"),
                ("object_detection_algorithm", "Object Detection Algorithms", ["computer_science"], "目标检测算法"),
            ]
        )

    def test_exact_expansion_batch_692_adds_object_detection_and_oriented_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("object_detection_method", "Object Detection Method", ["computer_science"], "目标检测方法"),
                ("object_detection_system", "Object Detection Systems", ["computer_science"], "目标检测系统"),
                ("object_localization", "Object Localization", ["computer_science"], "目标定位"),
                ("object_location", "Object Location", ["computer_science"], "目标定位"),
                ("object_oriented_approach", "Object Oriented Approach", ["computer_science"], "面向对象方法"),
                ("object_oriented_database", "Object Oriented Databases", ["professional_communication"], "面向对象数据库"),
                ("object_oriented_design", "Object Oriented Design", ["computer_science"], "面向对象设计"),
                ("object_oriented_languag", "Object-oriented Languages", ["computer_science"], "面向对象语言"),
            ]
        )

    def test_exact_expansion_batch_693_adds_object_oriented_programming_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("object_oriented_method", "Object Oriented Methods", ["computers_and_information_processing"], "面向对象方法"),
                ("object_oriented_modeling", "Object Oriented Modeling", ["systems_engineering_and_theory"], "面向对象建模"),
                ("object_oriented_programming", "Object Oriented Programming", ["computers_and_information_processing"], "面向对象编程"),
                ("object_oriented_programming_languag", "Object-oriented Programming Languages", ["computer_science"], "面向对象编程语言"),
                ("object_oriented_software", "Object Oriented Software", ["computer_science"], "面向对象软件"),
                ("object_oriented_system", "Object-oriented System", ["computer_science"], "面向对象系统"),
                ("object_pose", "Object Pose", ["computer_science"], "目标姿态"),
                ("object_recognition", "Object Recognition", ["computers_and_information_processing"], "目标识别"),
            ]
        )

    def test_exact_expansion_batch_694_adds_object_tracking_and_observation_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("object_segmentation", "Object Segmentation", ["computers_and_information_processing"], "目标分割"),
                ("object_tracking", "Object Tracking", ["computer_science"], "目标跟踪"),
                ("object_tracking_algorithm", "Object Tracking Algorithm", ["computer_science"], "目标跟踪算法"),
                ("objective_function_of", "Objective Function (of)", ["computer_science"], "目标函数"),
                ("objective_space", "Objective Space", ["computer_science"], "目标空间"),
                ("observability", "Observability", ["computer_science"], "可观测性"),
                ("observability_analysi", "Observability Analysis", ["computer_science"], "可观测性分析"),
                ("observation", "Observation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "观察"),
            ]
        )

    def test_exact_expansion_batch_695_adds_observational_and_obsessive_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("observation_model", "Observation Model", ["computer_science"], "观测模型"),
                ("observational_study", "Observational Study", ["biomedical", "publication_characteristics"], "观察性研究"),
                ("observational_study_as_topic", "Observational Studies As Topic", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "观察性研究主题"),
                ("observatory", "Observatories", ["science_general"], "天文台"),
                ("observer", "Observers", ["computer_science", "mathematics"], "观察者"),
                ("observer_design", "Observer Design", ["computer_science"], "观测器设计"),
                ("obsessive_behavior", "Obsessive Behavior", ["biomedical", "psychiatry_and_psychology"], "强迫行为"),
                ("obsessive_compulsive_disorder", "Obsessive-compulsive Disorder", ["biomedical", "psychiatry_and_psychology"], "强迫症"),
            ]
        )

    def test_exact_expansion_batch_696_adds_obstacle_and_obstetric_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("obsessive_compulsive_spectrum_disorder", "Obsessive-compulsive Spectrum Disorders", ["psychology", "social_sciences"], "强迫谱系障碍"),
                ("obstacle_avoidance", "Obstacle Avoidance", ["computer_science"], "避障"),
                ("obstacle_avoidance_algorithm", "Obstacle Avoidance Algorithms", ["computer_science"], "避障算法"),
                ("obstacle_detection", "Obstacle Detection", ["computer_science"], "障碍物检测"),
                ("obstetric_and_gynecology_department_hospital", "Obstetrics And Gynecology Department, Hospital", ["biomedical", "health_care"], "医院妇产科"),
                ("obstetric_labor_complication", "Obstetric Labor Complications", ["biomedical", "diseases"], "产程并发症"),
                ("obstetric_labor_premature", "Obstetric Labor, Premature", ["biomedical", "diseases"], "早产"),
                ("obstetric_nursing", "Obstetric Nursing", ["biomedical", "disciplines_and_occupations"], "产科护理"),
            ]
        )

    def test_exact_expansion_batch_697_adds_obstetric_to_occludin_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("obstetric_surgical_procedur", "Obstetric Surgical Procedures", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "产科手术"),
                ("obstetrical_forcep", "Obstetrical Forceps", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "产钳"),
                ("obstetrician", "Obstetricians", ["biomedical", "named_groups"], "产科医生"),
                ("obstructive_sleep_apnea_research", "Obstructive Sleep Apnea Research", ["health_sciences", "medicine"], "阻塞性睡眠呼吸暂停研究"),
                ("obturator_nerve", "Obturator Nerve", ["anatomy", "biomedical"], "闭孔神经"),
                ("occipital_bone", "Occipital Bone", ["anatomy", "biomedical"], "枕骨"),
                ("occipital_lobe", "Occipital Lobe", ["anatomy", "biomedical"], "枕叶"),
                ("occludin", "Occludin", ["biomedical", "chemicals_and_drugs"], "闭合蛋白"),
            ]
        )

    def test_exact_expansion_batch_698_adds_occlusion_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("occlusal_adjustment", "Occlusal Adjustment", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "咬合调整"),
                ("occlusal_splint", "Occlusal Splints", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "咬合夹板"),
                ("occlusion_body_matrix_protein", "Occlusion Body Matrix Proteins", ["biomedical", "chemicals_and_drugs"], "包涵体基质蛋白"),
                ("occlusion_body_viral", "Occlusion Bodies, Viral", ["anatomy", "biomedical"], "病毒包涵体"),
                ("occlusion_handling", "Occlusion Handling", ["computer_science"], "遮挡处理"),
                ("occlusive_dressing", "Occlusive Dressings", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "封闭敷料"),
                ("occult_blood", "Occult Blood", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "潜血"),
                ("occultism", "Occultism", ["biomedical", "humanities"], "神秘主义"),
            ]
        )

    def test_exact_expansion_batch_699_adds_occupational_health_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("occupation", "Occupations", ["biomedical", "health_care"], "职业"),
                ("occupational_disease", "Occupational Diseases", ["biomedical", "diseases"], "职业病"),
                ("occupational_exposure", "Occupational Exposure", ["biomedical", "health_care"], "职业暴露"),
                ("occupational_group", "Occupational Groups", ["biomedical", "named_groups"], "职业群体"),
                ("occupational_health_and_safety_in_workplac", "Occupational Health And Safety In Workplaces", ["health_professions", "health_sciences"], "工作场所职业健康与安全"),
                ("occupational_health_and_safety_management", "Occupational Health And Safety Management", ["health_professions", "health_sciences"], "职业健康与安全管理"),
                ("occupational_health_nursing", "Occupational Health Nursing", ["biomedical", "disciplines_and_occupations"], "职业健康护理"),
                ("occupational_health_physician", "Occupational Health Physicians", ["biomedical", "named_groups"], "职业健康医师"),
            ]
        )

    def test_exact_expansion_batch_700_adds_occupational_service_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("occupational_health_servic", "Occupational Health Services", ["biomedical", "health_care"], "职业健康服务"),
                ("occupational_injury", "Occupational Injuries", ["biomedical", "diseases"], "职业伤害"),
                ("occupational_medicine", "Occupational Medicine", ["engineering_in_medicine_and_biology"], "职业医学"),
                ("occupational_safety", "Occupational Safety", ["industry_applications"], "职业安全"),
                ("occupational_stress", "Occupational Stress", ["biomedical", "diseases"], "职业压力"),
                ("occupational_therapist", "Occupational Therapists", ["biomedical", "named_groups"], "职业治疗师"),
                ("occupational_therapy", "Occupational Therapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "职业治疗"),
                ("occupational_therapy_department_hospital", "Occupational Therapy Department, Hospital", ["biomedical", "health_care"], "医院职业治疗科"),
            ]
        )

    def test_exact_expansion_batch_701_adds_ocean_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("occupational_therapy_practice_and_research", "Occupational Therapy Practice And Research", ["health_professions", "health_sciences"], "职业治疗实践与研究"),
                ("ocdma", "Ocdma", ["computer_science"], "光码分多址"),
                ("ocean", "Oceans", ["change"], "海洋"),
                ("ocean_acidification", "Ocean Acidification", ["change"], "海洋酸化"),
                ("ocean_acidification_effect_and_response", "Ocean Acidification Effects And Responses", ["earth_and_planetary_sciences", "physical_sciences"], "海洋酸化效应与响应"),
                ("ocean_and_seas", "Oceans And Seas", ["biomedical", "phenomena_and_processes"], "海洋和海域"),
                ("ocean_circulation", "Ocean Circulation", ["change"], "海洋环流"),
                ("ocean_current", "Ocean Currents", ["computer_science"], "海流"),
            ]
        )

    def test_exact_expansion_batch_702_adds_ocean_dynamics_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ocean_dynamic", "Ocean Dynamics", ["change"], "海洋动力学"),
                ("ocean_salinity", "Ocean Salinity", ["change"], "海洋盐度"),
                ("ocean_temperature", "Ocean Temperature", ["change"], "海洋温度"),
                ("ocean_thermal_energy_conversion", "Ocean Thermal Energy Conversion", ["oceanic_engineering_and_marine_technology"], "海洋热能转换"),
                ("ocean_tide", "Ocean Tide", ["computer_science"], "海潮"),
                ("ocean_wav_and_remote_sensing", "Ocean Waves And Remote Sensing", ["earth_and_planetary_sciences", "physical_sciences"], "海浪与遥感"),
                ("oceania", "Oceania", ["biomedical", "geographicals"], "大洋洲"),
                ("oceanian", "Oceanians", ["biomedical", "named_groups"], "大洋洲人"),
            ]
        )

    def test_exact_expansion_batch_703_adds_oceanographic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oceanic_crust", "Oceanic Crust", ["change"], "洋壳"),
                ("oceanic_current", "Oceanic Current", ["computer_science"], "海流"),
                ("oceanic_engineering_and_marine_technology", "Oceanic Engineering And Marine Technology", ["oceanic_engineering_and_marine_technology"], "海洋工程与海洋技术"),
                ("oceanographic_and_atmospheric_processe", "Oceanographic And Atmospheric Processes", ["earth_and_planetary_sciences", "physical_sciences"], "海洋与大气过程"),
                ("oceanographic_instrument", "Oceanographic Instruments", ["computer_science"], "海洋仪器"),
                ("oceanographic_techniqu", "Oceanographic Techniques", ["oceanic_engineering_and_marine_technology"], "海洋学技术"),
                ("oceanography", "Oceanography", ["change"], "海洋学"),
                ("ochratoxin", "Ochratoxins", ["biomedical", "chemicals_and_drugs"], "赭曲霉毒素类"),
            ]
        )

    def test_exact_expansion_batch_704_adds_ochrobactrum_and_ocr_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ochrobactrum", "Ochrobactrum", ["biomedical", "organisms"], "苍白杆菌属"),
                ("ochrobactrum_anthropi", "Ochrobactrum Anthropi", ["biomedical", "organisms"], "人苍白杆菌"),
                ("ochronosi", "Ochronosis", ["biomedical", "diseases"], "褐黄病"),
                ("ocimum", "Ocimum", ["biomedical", "organisms"], "罗勒属"),
                ("ocimum_basilicum", "Ocimum Basilicum", ["biomedical", "organisms"], "罗勒"),
                ("ocimum_sanctum", "Ocimum Sanctum", ["biomedical", "organisms"], "圣罗勒"),
                ("ocl", "Ocl", ["computer_science"], "对象约束语言"),
                ("ocr", "Ocr", ["computer_science"], "光学字符识别"),
            ]
        )

    def test_exact_expansion_batch_705_adds_octamer_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("octamer_transcription_factor", "Octamer Transcription Factors", ["biomedical", "chemicals_and_drugs"], "八聚体转录因子"),
                ("octamer_transcription_factor_1", "Octamer Transcription Factor-1", ["biomedical", "chemicals_and_drugs"], "八聚体转录因子1"),
                ("octamer_transcription_factor_2", "Octamer Transcription Factor-2", ["biomedical", "chemicals_and_drugs"], "八聚体转录因子2"),
                ("octamer_transcription_factor_3", "Octamer Transcription Factor-3", ["biomedical", "chemicals_and_drugs"], "八聚体转录因子3"),
                ("octamer_transcription_factor_6", "Octamer Transcription Factor-6", ["biomedical", "chemicals_and_drugs"], "八聚体转录因子6"),
                ("octan", "Octanes", ["biomedical", "chemicals_and_drugs"], "辛烷类"),
                ("octanol", "Octanols", ["biomedical", "chemicals_and_drugs"], "辛醇类"),
                ("octogenarian", "Octogenarians", ["biomedical", "named_groups"], "八旬老人"),
            ]
        )

    def test_exact_expansion_batch_706_adds_octopamine_and_ocular_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("octopamine", "Octopamine", ["biomedical", "chemicals_and_drugs"], "章鱼胺"),
                ("octre", "Octrees", ["computers_and_information_processing"], "八叉树"),
                ("octreotide", "Octreotide", ["biomedical", "chemicals_and_drugs"], "奥曲肽"),
                ("ocular_absorption", "Ocular Absorption", ["biomedical", "phenomena_and_processes"], "眼吸收"),
                ("ocular_dominance", "Ocular Dominance", ["computer_science"], "眼优势"),
                ("ocular_hypertension", "Ocular Hypertension", ["biomedical", "diseases"], "高眼压"),
                ("ocular_hypotension", "Ocular Hypotension", ["biomedical", "diseases"], "低眼压"),
                ("ocular_motility_disorder", "Ocular Motility Disorders", ["biomedical", "diseases"], "眼球运动障碍"),
            ]
        )

    def test_exact_expansion_batch_707_adds_oculomotor_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ocular_physiological_phenomena", "Ocular Physiological Phenomena", ["biomedical", "phenomena_and_processes"], "眼生理现象"),
                ("oculocerebrorenal_syndrome", "Oculocerebrorenal Syndrome", ["biomedical", "diseases"], "眼脑肾综合征"),
                ("oculomotor_muscl", "Oculomotor Muscles", ["anatomy", "biomedical"], "动眼肌"),
                ("oculomotor_nerve", "Oculomotor Nerve", ["anatomy", "biomedical"], "动眼神经"),
                ("oculomotor_nerve_disease", "Oculomotor Nerve Diseases", ["biomedical", "diseases"], "动眼神经疾病"),
                ("oculomotor_nerve_injury", "Oculomotor Nerve Injuries", ["biomedical", "diseases"], "动眼神经损伤"),
                ("oculomotor_nuclear_complex", "Oculomotor Nuclear Complex", ["anatomy", "biomedical"], "动眼神经核复合体"),
                ("odds_ratio", "Odds Ratio", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "优势比"),
            ]
        )

    def test_exact_expansion_batch_708_adds_odometry_and_odontogenesis_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ode", "Ode", ["computer_science"], "常微分方程"),
                ("odometer", "Odometers", ["instrumentation_and_measurement"], "里程表"),
                ("odometry", "Odometry", ["computer_science"], "里程计"),
                ("odonata", "Odonata", ["biomedical", "organisms"], "蜻蜓目"),
                ("odontoblast", "Odontoblasts", ["anatomy", "biomedical"], "成牙本质细胞"),
                ("odontodysplasia", "Odontodysplasia", ["biomedical", "diseases"], "牙发育不良"),
                ("odontogenesi", "Odontogenesis", ["biomedical", "phenomena_and_processes"], "牙发生"),
                ("odontogenic_cyst", "Odontogenic Cysts", ["biomedical", "diseases"], "牙源性囊肿"),
            ]
        )

    def test_exact_expansion_batch_709_adds_odontogenic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("odontogenic_cyst_calcifying", "Odontogenic Cyst, Calcifying", ["biomedical", "diseases"], "钙化性牙源性囊肿"),
                ("odontogenic_tumor", "Odontogenic Tumors", ["biomedical", "diseases"], "牙源性肿瘤"),
                ("odontogenic_tumor_squamou", "Odontogenic Tumor, Squamous", ["biomedical", "diseases"], "鳞状牙源性肿瘤"),
                ("odontoid_process", "Odontoid Process", ["anatomy", "biomedical"], "齿突"),
                ("odontoma", "Odontoma", ["biomedical", "diseases"], "牙瘤"),
                ("odontometry", "Odontometry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "牙测量"),
                ("odor_and_emission_control_technology", "Odor And Emission Control Technologies", ["chemical_engineering", "physical_sciences"], "气味与排放控制技术"),
                ("odorant", "Odorants", ["biomedical", "phenomena_and_processes"], "气味物质"),
            ]
        )

    def test_exact_expansion_batch_710_adds_ofdm_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oedipu_complex", "Oedipus Complex", ["biomedical", "psychiatry_and_psychology"], "俄狄浦斯情结"),
                ("ofdm_modulation", "OFDM Modulation", ["communications_technology"], "正交频分复用调制"),
                ("ofdm_signal", "Ofdm Signal", ["computer_science"], "正交频分复用信号"),
                ("ofdm_system", "Ofdm Systems", ["computer_science"], "正交频分复用系统"),
                ("ofdm_transmission", "Ofdm Transmission", ["computer_science"], "正交频分复用传输"),
                ("ofdma", "Ofdma", ["computer_science"], "正交频分多址"),
                ("ofdma_system", "Ofdma Systems", ["computer_science"], "正交频分多址系统"),
                ("ofdma_uplink", "Ofdma Uplinks", ["computer_science"], "正交频分多址上行链路"),
            ]
        )

    def test_exact_expansion_batch_711_adds_office_memory_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ofet", "Ofets", ["solid_state_circuits"], "有机场效应晶体管"),
                ("off_chip_memory", "Off-chip Memories", ["computer_science"], "片外存储器"),
                ("off_label_use", "Off-label Use", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "超说明书用药"),
                ("off_line_algorithm", "Off-line Algorithm", ["computer_science"], "离线算法"),
                ("off_line_handwritten", "Off-line Handwritten", ["computer_science"], "离线手写"),
                ("off_road_motor_vehicl", "Off-road Motor Vehicles", ["biomedical", "technology_industry_and_agriculture"], "越野机动车"),
                ("office_automation", "Office Automation", ["robotics_and_automation"], "办公自动化"),
                ("office_building", "Office Buildings", ["computer_science"], "办公楼"),
            ]
        )

    def test_exact_expansion_batch_712_adds_office_and_offshore_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("office_management", "Office Management", ["biomedical", "health_care"], "办公室管理"),
                ("office_nursing", "Office Nursing", ["biomedical", "health_care"], "诊所护理"),
                ("office_visit", "Office Visits", ["biomedical", "health_care"], "门诊就诊"),
                ("office_worker", "Office Workers", ["computer_science"], "办公室工作人员"),
                ("offline_password_guessing_attack", "Offline Password Guessing Attack", ["computer_science"], "离线密码猜测攻击"),
                ("offset_frequency", "Offset Frequencies", ["computer_science"], "偏移频率"),
                ("offset_printing", "Offset Printing", ["computer_science"], "胶版印刷"),
                ("offshore_engineering_and_technology", "Offshore Engineering And Technologies", ["engineering", "physical_sciences"], "近海工程技术"),
            ]
        )

    def test_exact_expansion_batch_713_adds_oil_and_gas_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("offshore_installation", "Offshore Installations", ["engineering_general"], "海上设施"),
                ("ofloxacin", "Ofloxacin", ["biomedical", "chemicals_and_drugs"], "氧氟沙星"),
                ("ohio", "Ohio", ["biomedical", "geographicals"], "俄亥俄州"),
                ("ohmic_contact", "Ohmic Contacts", ["circuits_and_systems"], "欧姆接触"),
                ("oil_and_gas_field", "Oil And Gas Fields", ["biomedical", "phenomena_and_processes"], "油气田"),
                ("oil_and_gas_industry", "Oil And Gas Industry", ["biomedical", "technology_industry_and_agriculture"], "油气行业"),
                ("oil_and_gas_production_techniqu", "Oil And Gas Production Techniques", ["engineering", "physical_sciences"], "油气生产技术"),
                ("oil_drilling", "Oil Drilling", ["industry_applications"], "石油钻井"),
            ]
        )

    def test_exact_expansion_batch_714_adds_oil_production_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oil_filled_cabl", "Oil Filled Cables", ["dielectrics_and_electrical_insulation"], "充油电缆"),
                ("oil_gas_and_environmental_issu", "Oil, Gas, And Environmental Issues", ["energy", "physical_sciences"], "油气与环境问题"),
                ("oil_insulation", "Oil Insulation", ["dielectrics_and_electrical_insulation"], "油绝缘"),
                ("oil_palm_production_and_sustainability", "Oil Palm Production And Sustainability", ["environmental_science", "physical_sciences"], "油棕生产与可持续性"),
                ("oil_pollution", "Oil Pollution", ["pollution"], "石油污染"),
                ("oil_recovery", "Oil Recoveries", ["computer_science"], "采油"),
                ("oil_refinery", "Oil Refineries", ["industry_applications"], "炼油厂"),
                ("oil_spill_detection_and_mitigation", "Oil Spill Detection And Mitigation", ["environmental_science", "physical_sciences"], "溢油检测与缓解"),
            ]
        )

    def test_exact_expansion_batch_715_adds_oils_and_olap_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oils", "Oils", ["materials_elements_and_compounds"], "油类"),
                ("oils_volatile", "Oils, Volatile", ["biomedical", "chemicals_and_drugs"], "挥发油"),
                ("ointment", "Ointments", ["biomedical", "chemicals_and_drugs"], "软膏"),
                ("ointment_base", "Ointment Bases", ["biomedical", "chemicals_and_drugs"], "软膏基质"),
                ("okadaic_acid", "Okadaic Acid", ["biomedical", "chemicals_and_drugs"], "冈田酸"),
                ("oklahoma", "Oklahoma", ["biomedical", "geographicals"], "俄克拉荷马州"),
                ("olanzapine", "Olanzapine", ["biomedical", "chemicals_and_drugs"], "奥氮平"),
                ("olap", "Olap", ["computer_science"], "联机分析处理"),
            ]
        )

    def test_exact_expansion_batch_716_adds_olecranon_and_oled_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("olap_query", "Olap Queries", ["computer_science"], "OLAP查询"),
                ("old_age_assistance", "Old Age Assistance", ["biomedical", "health_care"], "老年援助"),
                ("older_adult_driving_study", "Older Adults Driving Studies", ["health_professions", "health_sciences"], "老年人驾驶研究"),
                ("oleandomycin", "Oleandomycin", ["biomedical", "chemicals_and_drugs"], "竹桃霉素"),
                ("oleanolic_acid", "Oleanolic Acid", ["biomedical", "chemicals_and_drugs"], "齐墩果酸"),
                ("olecranon_fracture", "Olecranon Fracture", ["biomedical", "diseases"], "鹰嘴骨折"),
                ("olecranon_process", "Olecranon Process", ["anatomy", "biomedical"], "鹰嘴"),
                ("oled_display", "Oled Displays", ["computer_science"], "OLED显示器"),
            ]
        )

    def test_exact_expansion_batch_717_adds_olfactory_bulb_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oleic_acid", "Oleic Acids", ["biomedical", "chemicals_and_drugs"], "油酸"),
                ("olfaction_disorder", "Olfaction Disorders", ["biomedical", "diseases"], "嗅觉障碍"),
                ("olfactometry", "Olfactometry", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "嗅觉测量"),
                ("olfactory_and_sensory_function_study", "Olfactory And Sensory Function Studies", ["life_sciences", "neuroscience"], "嗅觉与感觉功能研究"),
                ("olfactory_bulb", "Olfactory Bulb", ["anatomy", "biomedical"], "嗅球"),
                ("olfactory_cortex", "Olfactory Cortex", ["anatomy", "biomedical"], "嗅皮层"),
                ("olfactory_marker_protein", "Olfactory Marker Protein", ["biomedical", "chemicals_and_drugs"], "嗅觉标志蛋白"),
                ("olfactory_mucosa", "Olfactory Mucosa", ["anatomy", "biomedical"], "嗅黏膜"),
            ]
        )

    def test_exact_expansion_batch_718_adds_olfactory_nerve_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("olfactory_nerve", "Olfactory Nerve", ["anatomy", "biomedical"], "嗅神经"),
                ("olfactory_nerve_disease", "Olfactory Nerve Diseases", ["biomedical", "diseases"], "嗅神经疾病"),
                ("olfactory_nerve_injury", "Olfactory Nerve Injuries", ["biomedical", "diseases"], "嗅神经损伤"),
                ("olfactory_pathway", "Olfactory Pathways", ["anatomy", "biomedical"], "嗅觉通路"),
                ("olfactory_perception", "Olfactory Perception", ["biomedical", "psychiatry_and_psychology"], "嗅觉感知"),
                ("olfactory_receptor_neuron", "Olfactory Receptor Neurons", ["anatomy", "biomedical"], "嗅觉受体神经元"),
                ("olfactory_training", "Olfactory Training", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "嗅觉训练"),
                ("olfactory_tubercle", "Olfactory Tubercle", ["anatomy", "biomedical"], "嗅结节"),
            ]
        )

    def test_exact_expansion_batch_719_adds_oligodendrocyte_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oligo_1_6_glucosidase", "Oligo-1,6-glucosidase", ["biomedical", "chemicals_and_drugs"], "寡-1,6-葡萄糖苷酶"),
                ("oligoclonal_band", "Oligoclonal Bands", ["biomedical", "chemicals_and_drugs"], "寡克隆带"),
                ("oligodendrocyte_myelin_glycoprotein", "Oligodendrocyte-myelin Glycoprotein", ["biomedical", "chemicals_and_drugs"], "少突胶质细胞髓鞘糖蛋白"),
                ("oligodendrocyte_precursor_cell", "Oligodendrocyte Precursor Cells", ["anatomy", "biomedical"], "少突胶质前体细胞"),
                ("oligodendrocyte_transcription_factor_2", "Oligodendrocyte Transcription Factor 2", ["biomedical", "chemicals_and_drugs"], "少突胶质细胞转录因子2"),
                ("oligodendroglia", "Oligodendroglia", ["anatomy", "biomedical"], "少突胶质细胞"),
                ("oligodendroglioma", "Oligodendroglioma", ["biomedical", "diseases"], "少突胶质细胞瘤"),
                ("oligodeoxyribonucleotid", "Oligodeoxyribonucleotides", ["biomedical", "chemicals_and_drugs"], "寡脱氧核糖核苷酸"),
            ]
        )

    def test_exact_expansion_batch_720_adds_oligonucleotide_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oligonucleotid", "Oligonucleotides", ["biomedical", "chemicals_and_drugs"], "寡核苷酸"),
                ("oligonucleotide_array_sequence_analysi", "Oligonucleotide Array Sequence Analysis", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "寡核苷酸阵列序列分析"),
                ("oligonucleotide_prob", "Oligonucleotide Probes", ["biomedical", "chemicals_and_drugs"], "寡核苷酸探针"),
                ("oligopeptid", "Oligopeptides", ["biomedical", "chemicals_and_drugs"], "寡肽"),
                ("oligopoly", "Oligopoly", ["engineering_management"], "寡头垄断"),
                ("oligoribonucleotid", "Oligoribonucleotides", ["biomedical", "chemicals_and_drugs"], "寡核糖核苷酸"),
                ("oligosaccharid", "Oligosaccharides", ["biomedical", "chemicals_and_drugs"], "寡糖"),
                ("oligospermia", "Oligospermia", ["biomedical", "diseases"], "少精子症"),
            ]
        )

    def test_exact_expansion_batch_721_adds_olive_and_olmesartan_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oliguria", "Oliguria", ["biomedical", "diseases"], "少尿"),
                ("olivary_degeneration", "Olivary Degeneration", ["biomedical", "diseases"], "橄榄体变性"),
                ("olivary_nucleu", "Olivary Nucleus", ["anatomy", "biomedical"], "橄榄核"),
                ("olive_oil", "Olive Oil", ["biomedical", "chemicals_and_drugs"], "橄榄油"),
                ("olivomycin", "Olivomycins", ["biomedical", "chemicals_and_drugs"], "橄榄霉素类"),
                ("olivopontocerebellar_atrophy", "Olivopontocerebellar Atrophies", ["biomedical", "diseases"], "橄榄体脑桥小脑萎缩症"),
                ("olmesartan_medoxomil", "Olmesartan Medoxomil", ["biomedical", "chemicals_and_drugs"], "奥美沙坦酯"),
                ("olopatadine_hydrochloride", "Olopatadine Hydrochloride", ["biomedical", "chemicals_and_drugs"], "盐酸奥洛他定"),
            ]
        )

    def test_exact_expansion_batch_722_adds_olsr_and_omni_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("olsr", "Olsr", ["computer_science"], "优化链路状态路由"),
                ("olsr_protocol", "Olsr Protocols", ["computer_science"], "OLSR协议"),
                ("omalizumab", "Omalizumab", ["biomedical", "chemicals_and_drugs"], "奥马珠单抗"),
                ("oman", "Oman", ["biomedical", "geographicals"], "阿曼"),
                ("omasum", "Omasum", ["anatomy", "biomedical"], "瓣胃"),
                ("omentum", "Omentum", ["anatomy", "biomedical"], "网膜"),
                ("omeprazole", "Omeprazole", ["biomedical", "chemicals_and_drugs"], "奥美拉唑"),
                ("omni_directional_antenna", "Omni-directional Antenna", ["computer_science"], "全向天线"),
            ]
        )

    def test_exact_expansion_batch_723_adds_omnidirectional_and_on_chip_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("omnidirectional_antenna", "Omnidirectional Antennas", ["antennas_and_propagation"], "全向天线"),
                ("omnidirectional_mobile_robot", "Omnidirectional Mobile Robot", ["computer_science"], "全向移动机器人"),
                ("omnidirectional_radiation_pattern", "Omnidirectional Radiation Pattern", ["computer_science"], "全向辐射方向图"),
                ("omphalocele", "Omphalocele", ["biomedical", "diseases"], "脐膨出"),
                ("on_board_unit", "On Board Unit", ["communications_technology"], "车载单元"),
                ("on_body", "On-body", ["computer_science"], "体表"),
                ("on_chip_cache", "On-chip Cache", ["computer_science"], "片上缓存"),
                ("on_chip_interconnect", "On Chip Interconnect", ["computer_science"], "片上互连"),
            ]
        )

    def test_exact_expansion_batch_724_adds_online_learning_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("on_chip_interconnection_network", "On-chip Interconnection Network", ["computer_science"], "片上互连网络"),
                ("on_chip_memory", "On Chip Memory", ["computer_science"], "片上存储器"),
                ("on_chip_network", "On-chip Networks", ["computer_science"], "片上网络"),
                ("on_demand_routing_protocol", "On-demand Routing Protocol", ["computer_science"], "按需路由协议"),
                ("on_line_algorithm", "On-line Algorithm", ["computer_science"], "在线算法"),
                ("on_line_community", "On-line Communities", ["computer_science"], "在线社区"),
                ("on_line_education", "On-line Education", ["computer_science"], "在线教育"),
                ("on_line_learning", "On-line Learning", ["computer_science"], "在线学习"),
            ]
        )

    def test_exact_expansion_batch_725_adds_onchocerca_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("on_line_setting", "On-line Setting", ["computer_science"], "在线环境"),
                ("on_line_social_network", "On-line Social Networks", ["computer_science"], "在线社交网络"),
                ("on_the_job_training", "On The Job Training", ["education"], "在职培训"),
                ("onagraceae", "Onagraceae", ["biomedical", "organisms"], "柳叶菜科"),
                ("onchocerca", "Onchocerca", ["biomedical", "organisms"], "盘尾丝虫属"),
                ("onchocerca_volvulu", "Onchocerca Volvulus", ["biomedical", "organisms"], "旋盘尾丝虫"),
                ("onchocerciasi", "Onchocerciasis", ["biomedical", "diseases"], "盘尾丝虫病"),
                ("onchocerciasi_ocular", "Onchocerciasis, Ocular", ["biomedical", "diseases"], "眼盘尾丝虫病"),
            ]
        )

    def test_exact_expansion_batch_726_adds_oncogene_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("onco_anesthesia", "Onco-anesthesia", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "肿瘤麻醉"),
                ("oncogene_addiction", "Oncogene Addiction", ["biomedical", "diseases"], "癌基因成瘾"),
                ("oncogene_fusion", "Oncogene Fusion", ["biomedical", "phenomena_and_processes"], "癌基因融合"),
                ("oncogene_protein", "Oncogene Proteins", ["biomedical", "chemicals_and_drugs"], "癌基因蛋白"),
                ("oncogene_protein_fusion", "Oncogene Proteins, Fusion", ["computer_science"], "融合癌基因蛋白"),
                ("oncogene_protein_gp140_v_fms", "Oncogene Protein Gp140(v-fms)", ["biomedical", "chemicals_and_drugs"], "癌基因蛋白gp140(v-fms)"),
                ("oncogene_protein_p21_ras", "Oncogene Protein P21(ras)", ["biomedical", "chemicals_and_drugs"], "癌基因蛋白p21(ras)"),
                ("oncogene_protein_p55_v_myc", "Oncogene Protein P55(v-myc)", ["biomedical", "chemicals_and_drugs"], "癌基因蛋白p55(v-myc)"),
            ]
        )

    def test_exact_expansion_batch_727_adds_v_oncogene_protein_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oncogene_protein_p65_gag_jun", "Oncogene Protein P65(gag-jun)", ["biomedical", "chemicals_and_drugs"], "癌基因蛋白p65(gag-jun)"),
                ("oncogene_protein_pp60_v_src", "Oncogene Protein Pp60(v-src)", ["biomedical", "chemicals_and_drugs"], "癌基因蛋白pp60(v-src)"),
                ("oncogene_protein_tpr_met", "Oncogene Protein Tpr-met", ["biomedical", "chemicals_and_drugs"], "癌基因蛋白Tpr-met"),
                ("oncogene_protein_v_abl", "Oncogene Proteins V-abl", ["biomedical", "chemicals_and_drugs"], "V-abl癌基因蛋白"),
                ("oncogene_protein_v_akt", "Oncogene Protein V-akt", ["biomedical", "chemicals_and_drugs"], "V-akt癌基因蛋白"),
                ("oncogene_protein_v_cbl", "Oncogene Protein V-cbl", ["biomedical", "chemicals_and_drugs"], "V-cbl癌基因蛋白"),
                ("oncogene_protein_v_crk", "Oncogene Protein V-crk", ["biomedical", "chemicals_and_drugs"], "V-crk癌基因蛋白"),
                ("oncogene_protein_v_erba", "Oncogene Proteins V-erba", ["biomedical", "chemicals_and_drugs"], "V-erba癌基因蛋白"),
            ]
        )

    def test_exact_expansion_batch_728_adds_more_v_oncogene_protein_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oncogene_protein_v_erbb", "Oncogene Proteins V-erbb", ["biomedical", "chemicals_and_drugs"], "V-erbb癌基因蛋白"),
                ("oncogene_protein_v_fos", "Oncogene Proteins V-fos", ["biomedical", "chemicals_and_drugs"], "V-fos癌基因蛋白"),
                ("oncogene_protein_v_maf", "Oncogene Protein V-maf", ["biomedical", "chemicals_and_drugs"], "V-maf癌基因蛋白"),
                ("oncogene_protein_v_mos", "Oncogene Proteins V-mos", ["biomedical", "chemicals_and_drugs"], "V-mos癌基因蛋白"),
                ("oncogene_protein_v_myb", "Oncogene Proteins V-myb", ["biomedical", "chemicals_and_drugs"], "V-myb癌基因蛋白"),
                ("oncogene_protein_v_raf", "Oncogene Proteins V-raf", ["biomedical", "chemicals_and_drugs"], "V-raf癌基因蛋白"),
                ("oncogene_protein_v_rel", "Oncogene Proteins V-rel", ["biomedical", "chemicals_and_drugs"], "V-rel癌基因蛋白"),
                ("oncogene_protein_v_sis", "Oncogene Proteins V-sis", ["biomedical", "chemicals_and_drugs"], "V-sis癌基因蛋白"),
            ]
        )

    def test_exact_expansion_batch_729_adds_oncology_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oncogene_protein_viral", "Oncogene Proteins, Viral", ["biomedical", "chemicals_and_drugs"], "病毒癌基因蛋白"),
                ("oncogenic_viruse", "Oncogenic Viruses", ["biomedical", "organisms"], "致癌病毒"),
                ("oncologist", "Oncologists", ["biomedical", "named_groups"], "肿瘤科医生"),
                ("oncology", "Oncology", ["engineering_in_medicine_and_biology"], "肿瘤学"),
                ("oncology_nursing", "Oncology Nursing", ["biomedical", "disciplines_and_occupations"], "肿瘤护理"),
                ("oncology_service_hospital", "Oncology Service, Hospital", ["biomedical", "health_care"], "医院肿瘤科"),
                ("oncolytic_virotherapy", "Oncolytic Virotherapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "溶瘤病毒疗法"),
                ("oncolytic_viruse", "Oncolytic Viruses", ["biomedical", "organisms"], "溶瘤病毒"),
            ]
        )

    def test_exact_expansion_batch_730_adds_oncorhynchus_and_one_dimensional_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oncorhynchu", "Oncorhynchus", ["biomedical", "organisms"], "大麻哈鱼属"),
                ("oncorhynchu_keta", "Oncorhynchus Keta", ["biomedical", "organisms"], "大麻哈鱼"),
                ("oncorhynchu_kisutch", "Oncorhynchus Kisutch", ["biomedical", "organisms"], "银大麻哈鱼"),
                ("oncorhynchu_mykiss", "Oncorhynchus Mykiss", ["biomedical", "organisms"], "虹鳟"),
                ("oncostatin_m", "Oncostatin M", ["biomedical", "chemicals_and_drugs"], "抑瘤素M"),
                ("oncostatin_m_receptor_beta_subunit", "Oncostatin M Receptor Beta Subunit", ["biomedical", "chemicals_and_drugs"], "抑瘤素M受体β亚基"),
                ("ondansetron", "Ondansetron", ["biomedical", "chemicals_and_drugs"], "昂丹司琼"),
                ("one_dimensional", "One Dimensional", ["computer_science"], "一维"),
            ]
        )

    def test_exact_expansion_batch_731_adds_one_health_and_onion_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("one_carbon_group_transferase", "One-carbon Group Transferases", ["biomedical", "chemicals_and_drugs"], "一碳基团转移酶"),
                ("one_health", "One Health", ["biomedical", "health_care"], "同一健康"),
                ("one_lung_ventilation", "One-lung Ventilation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "单肺通气"),
                ("one_shot_learning", "One Shot Learning", ["computational_and_artificial_intelligence"], "单样本学习"),
                ("one_time_password", "One-time Passwords", ["computer_science"], "一次性密码"),
                ("one_way_hash_function", "One-way Hash Function", ["computer_science"], "单向哈希函数"),
                ("onecut_transcription_factor", "Onecut Transcription Factors", ["biomedical", "chemicals_and_drugs"], "Onecut转录因子"),
                ("onion", "Onions", ["biomedical", "organisms"], "洋葱"),
            ]
        )

    def test_exact_expansion_batch_732_adds_online_service_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("onion_routing", "Onion Routing", ["computer_science"], "洋葱路由"),
                ("onium_compound", "Onium Compounds", ["biomedical", "chemicals_and_drugs"], "鎓化合物"),
                ("online_and_blended_learning", "Online And Blended Learning", ["social_sciences"], "在线与混合式学习"),
                ("online_auction", "Online Auction", ["computer_science"], "在线拍卖"),
                ("online_banking", "Online Banking", ["professional_communication"], "网上银行"),
                ("online_conferencing", "Online Conferencing", ["computer_science"], "在线会议"),
                ("online_consumer", "Online Consumers", ["computer_science"], "在线消费者"),
                ("online_course", "Online Course", ["computer_science"], "在线课程"),
            ]
        )

    def test_exact_expansion_batch_733_adds_online_learning_analytics_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("online_environment", "Online Environments", ["computer_science"], "在线环境"),
                ("online_learning_algorithm", "Online Learning Algorithms", ["computer_science"], "在线学习算法"),
                ("online_learning_and_analytic", "Online Learning And Analytics", ["computer_science", "physical_sciences"], "在线学习与分析"),
                ("online_learning_environment", "Online Learning Environment", ["computer_science"], "在线学习环境"),
                ("online_learning_method_and_innovation", "Online Learning Methods And Innovations", ["social_sciences"], "在线学习方法与创新"),
                ("online_privacy", "Online Privacy", ["computer_science"], "在线隐私"),
                ("online_problem", "Online Problems", ["computer_science"], "在线问题"),
                ("online_product", "Online Products", ["computer_science"], "在线产品"),
            ]
        )

    def test_exact_expansion_batch_734_adds_online_system_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("online_scheduling", "Online Scheduling", ["computer_science"], "在线调度"),
                ("online_searching", "Online Searching", ["computer_science"], "在线搜索"),
                ("online_servic", "Online Services", ["professional_communication"], "在线服务"),
                ("online_shopping", "Online Shopping", ["computer_science"], "网上购物"),
                ("online_social_networking", "Online Social Networkings", ["computer_science"], "在线社交网络"),
                ("online_social_networking__2", "Online Social Networking", ["biomedical", "information_science"], "在线社交网络"),
                ("online_system", "Online System", ["computer_science"], "在线系统"),
                ("online_system__2", "Online Systems", ["biomedical", "information_science"], "在线系统"),
            ]
        )

    def test_exact_expansion_batch_735_adds_ontology_start_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("online_teaching", "Online Teaching", ["computer_science"], "在线教学"),
                ("online_transaction_processing", "Online Transaction Processing", ["computer_science"], "联机事务处理"),
                ("online_version", "Online Versions", ["computer_science"], "在线版本"),
                ("only_child", "Only Child", ["biomedical", "psychiatry_and_psychology"], "独生子女"),
                ("ontario", "Ontario", ["biomedical", "geographicals"], "安大略省"),
                ("ontology", "Ontologies", ["computer_science"], "本体"),
                ("ontology_alignment", "Ontology Alignment", ["computer_science"], "本体对齐"),
                ("ontology_based_data_access", "Ontology-based Data Access", ["computer_science"], "基于本体的数据访问"),
            ]
        )

    def test_exact_expansion_batch_736_adds_ontology_engineering_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ontology_building", "Ontology Building", ["computer_science"], "本体构建"),
                ("ontology_concept", "Ontology Concepts", ["computer_science"], "本体概念"),
                ("ontology_construction", "Ontology Construction", ["computer_science"], "本体构建"),
                ("ontology_design", "Ontology Design", ["computer_science"], "本体设计"),
                ("ontology_development", "Ontology Development", ["computer_science"], "本体开发"),
                ("ontology_evaluation", "Ontology Evaluation", ["computer_science"], "本体评估"),
                ("ontology_evolution", "Ontology Evolution", ["computer_science"], "本体演化"),
                ("ontology_integration", "Ontology Integration", ["computer_science"], "本体集成"),
            ]
        )

    def test_exact_expansion_batch_737_adds_ontology_and_nail_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("ontology_language", "Ontology Language", ["computer_science"], "本体语言"),
                ("ontology_learning", "Ontology Learning", ["computer_science"], "本体学习"),
                ("ontology_merging", "Ontology Merging", ["computer_science"], "本体合并"),
                ("ontology_modeling", "Ontology Modeling", ["computer_science"], "本体建模"),
                ("ontology_pattern", "Ontology Pattern", ["computer_science"], "本体模式"),
                ("ontology_technology", "Ontology Technology", ["computer_science"], "本体技术"),
                ("onycholysi", "Onycholysis", ["biomedical", "diseases"], "甲剥离症"),
                ("onychomycosi", "Onychomycosis", ["biomedical", "diseases"], "甲真菌病"),
            ]
        )

    def test_exact_expansion_batch_738_adds_oocyte_and_ood_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oocyst", "Oocysts", ["anatomy", "biomedical"], "卵囊"),
                ("oocyt", "Oocytes", ["anatomy", "biomedical"], "卵母细胞"),
                ("oocyte_donation", "Oocyte Donation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "卵母细胞捐献"),
                ("oocyte_retrieval", "Oocyte Retrieval", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "取卵"),
                ("ood_detection", "Ood Detection", ["computer_science"], "分布外检测"),
                ("ood_generalization", "Ood Generalization", ["computer_science"], "分布外泛化"),
                ("oogenesi", "Oogenesis", ["biomedical", "phenomena_and_processes"], "卵子发生"),
                ("oogonia", "Oogonia", ["anatomy", "biomedical"], "卵原细胞"),
            ]
        )

    def test_exact_expansion_batch_739_adds_oogonial_and_open_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("oogonial_stem_cell", "Oogonial Stem Cells", ["anatomy", "biomedical"], "卵原干细胞"),
                ("oomycet", "Oomycetes", ["biomedical", "organisms"], "卵菌"),
                ("oophoriti", "Oophoritis", ["biomedical", "diseases"], "卵巢炎"),
                ("open_abdomen_techniqu", "Open Abdomen Techniques", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "开放腹腔技术"),
                ("open_access", "Open Access", ["computers_and_information_processing"], "开放获取"),
                ("open_access_publishing", "Open Access Publishing", ["biomedical", "information_science"], "开放获取出版"),
                ("open_banking", "Open Banking", ["computers_and_information_processing"], "开放银行"),
                ("open_data", "Open Data", ["computers_and_information_processing"], "开放数据"),
            ]
        )

    def test_exact_expansion_batch_740_adds_open_education_and_loop_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("open_education_and_e_learning", "Open Education And E-learning", ["computer_science", "physical_sciences"], "开放教育与电子学习"),
                ("open_educational_resourc", "Open Educational Resources", ["computers_and_information_processing"], "开放教育资源"),
                ("open_field_test", "Open Field Test", ["biomedical", "psychiatry_and_psychology"], "旷场实验"),
                ("open_fracture_reduction", "Open Fracture Reduction", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "开放复位"),
                ("open_loop_control", "Open Loop Control", ["computer_science"], "开环控制"),
                ("open_loop_system", "Open Loop Systems", ["control_systems"], "开环系统"),
                ("open_ran", "Open RAN", ["communications_technology"], "开放式无线接入网"),
                ("open_reading_fram", "Open Reading Frames", ["biomedical", "phenomena_and_processes"], "开放阅读框"),
            ]
        )

    def test_exact_expansion_batch_741_to_760_adds_open_operation_ophthalmic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("open_shortest_path_first", "Open Shortest Path First", ["computer_science"], "开放最短路径优先"),
                ("operating_room", "Operating Rooms", ["biomedical", "health_care"], "手术室"),
                ("operational_amplifier", "Operational Amplifiers", ["circuits_and_systems"], "运算放大器"),
                ("ophthalmic_artery", "Ophthalmic Artery", ["anatomy", "biomedical"], "眼动脉"),
            ]
        )

    def test_exact_expansion_batch_761_to_780_adds_opioid_opportunistic_optic_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("opioid_related_disorder", "Opioid-related Disorders", ["biomedical", "diseases"], "阿片类药物相关障碍"),
                ("opportunistic_routing", "Opportunistic Routing", ["computer_science"], "机会路由"),
                ("optic_nerve", "Optic Nerve", ["anatomy", "biomedical"], "视神经"),
                ("optical_burst_switching", "Optical Burst Switching", ["computer_science"], "光突发交换"),
            ]
        )

    def test_exact_expansion_batch_781_to_800_adds_optical_networking_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("optical_crosstalk", "Optical Crosstalk", ["lasers_and_electrooptics"], "光串扰"),
                ("optical_flow", "Optical Flow", ["computer_science"], "光流"),
                ("optical_network", "Optical Networks", ["computer_science"], "光网络"),
                ("optical_switching", "Optical Switching", ["communications_technology"], "光交换"),
            ]
        )

    def test_exact_expansion_batch_801_to_820_adds_optimization_organ_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("hybrid_optimization_algorithm", "Hybrid Optimization Algorithm", ["computer_science"], "混合优化算法"),
                ("oral_health", "Oral Health", ["biomedical", "health_care"], "口腔健康"),
                ("organ_transplantation", "Organ Transplantation", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "器官移植"),
                ("organic_light_emitting_diod", "Organic Light Emitting Diodes", ["computer_science"], "有机发光二极管"),
            ]
        )

    def test_exact_expansion_batch_821_to_840_adds_ovarian_oxygen_terms(self) -> None:
        self.assert_exact_alias_cases(
            [
                ("outage_probability", "Outage Probabilities", ["computer_science"], "中断概率"),
                ("ovarian_hyperstimulation_syndrome", "Ovarian Hyperstimulation Syndrome", ["biomedical", "diseases"], "卵巢过度刺激综合征"),
                ("oxidative_phosphorylation", "Oxidative Phosphorylation", ["biomedical", "phenomena_and_processes"], "氧化磷酸化"),
                ("oxygen_inhalation_therapy", "Oxygen Inhalation Therapy", ["analytical_diagnostic_and_therapeutic_techniques_and_equipment", "biomedical"], "氧吸入疗法"),
            ]
        )


if __name__ == "__main__":
    unittest.main()


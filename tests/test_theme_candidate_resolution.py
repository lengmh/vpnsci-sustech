from __future__ import annotations

import unittest
from unittest import mock

from vpnsci_sustech import theme_candidate_resolution


class ThemeCandidateResolutionTests(unittest.TestCase):
    def _low_signal_raw(self) -> dict:
        return {
            "themes": [],
            "total_papers": 3,
            "method": "seed_text_frequency_fallback",
            "status": "insufficient_text_theme_signal",
        }

    def _papers(self) -> list[dict]:
        return [
            {
                "paper_id": "p1",
                "title": "网络攻击检测综述",
                "abstract": "本文研究恶意软件、入侵检测和网络攻击流量。",
                "keywords": ["入侵检测", "恶意软件"],
            },
            {
                "paper_id": "p2",
                "title": "网络攻击防御系统",
                "abstract": "网络攻击检测模型用于安全流量分析。",
                "keywords": ["安全"],
            },
            {
                "paper_id": "p3",
                "title": "无关论文",
                "abstract": "没有可用主题。",
                "keywords": [],
            },
        ]

    def _matches(self, paper: dict, *, paper_id: str) -> list[dict]:
        if paper_id not in {"p1", "p2"}:
            return []
        return [
            {
                "alias_key": "zh:网络攻击",
                "surface": "网络攻击",
                "paper_ids": [paper_id],
                "candidates": [
                    {
                        "concept_id": "concept:cyber_attack",
                        "canonical": {"en": "Cyber Attack", "zh": ""},
                        "domains": ["computer_science"],
                        "parents": [],
                        "specificity": 80,
                        "candidate_type": "collision_alias",
                        "risk_tags": ["semantic_neighbor", "needs_context"],
                        "reason": "blocked collision candidate; requires paper context",
                        "source_concept_id": "concept:cyber_attack_source",
                        "target_hint": "security",
                        "resolution_group": "network_attack_security",
                        "requires_context": True,
                        "allow_deterministic_shadow": True,
                        "evidence_aliases": [{"lang": "zh", "alias": "网络攻击"}],
                    }
                ],
            }
        ]

    def test_no_hit_and_insufficient_hit_trigger_candidate_resolution(self) -> None:
        self.assertTrue(
            theme_candidate_resolution.theme_treemap_needs_candidate_resolution(
                self._low_signal_raw(),
                self._papers(),
            )
        )
        enough = {
            "themes": [
                {"name": "Graph Neural Networks", "value": 2, "paper_ids": ["p1", "p2"]},
                {"name": "Molecular Property Prediction", "value": 2, "paper_ids": ["p2", "p3"]},
            ],
            "total_papers": 3,
        }

        self.assertFalse(
            theme_candidate_resolution.theme_treemap_needs_candidate_resolution(enough, self._papers())
        )

    def test_build_request_contains_paper_context_and_deduplicated_candidates(self) -> None:
        with mock.patch(
            "vpnsci_sustech.theme_candidate_resolution._ambiguous_candidate_matches",
            side_effect=self._matches,
        ):
            request, trace = theme_candidate_resolution.build_theme_candidate_resolution_request(
                self._low_signal_raw(),
                self._papers(),
                display_query="网络攻击检测",
                language="zh",
            )

        self.assertEqual(request["schema_version"], "theme_candidate_resolution_request.v1")
        self.assertEqual(request["trigger_reason"], "no_hit")
        self.assertEqual(request["display_query"], "网络攻击检测")
        self.assertEqual([paper["paper_id"] for paper in request["papers"]], ["p1", "p2", "p3"])
        self.assertEqual(len(request["candidate_aliases"]), 1)
        alias = request["candidate_aliases"][0]
        self.assertEqual(alias["alias_key"], "zh:网络攻击")
        self.assertEqual(alias["paper_ids"], ["p1", "p2"])
        self.assertEqual(alias["candidates"][0]["risk_tags"], ["semantic_neighbor", "needs_context"])
        self.assertEqual(alias["candidates"][0]["source_concept_id"], "concept:cyber_attack_source")
        self.assertEqual(alias["candidates"][0]["target_hint"], "security")
        self.assertEqual(alias["candidates"][0]["resolution_group"], "network_attack_security")
        self.assertTrue(alias["candidates"][0]["requires_context"])
        self.assertTrue(alias["candidates"][0]["allow_deterministic_shadow"])
        self.assertEqual(alias["candidates"][0]["evidence_aliases"], [{"lang": "zh", "alias": "网络攻击"}])
        self.assertEqual(trace["reason"], "agent_resolution_not_supplied")

    def test_apply_result_requires_evidence_and_request_candidate_membership(self) -> None:
        with mock.patch(
            "vpnsci_sustech.theme_candidate_resolution._ambiguous_candidate_matches",
            side_effect=self._matches,
        ):
            request, _ = theme_candidate_resolution.build_theme_candidate_resolution_request(
                self._low_signal_raw(),
                self._papers(),
                display_query="网络攻击检测",
                language="zh",
            )
        result = {
            "schema_version": "theme_candidate_resolution_result.v1",
            "decisions": [
                {
                    "decision": "resolved",
                    "alias_key": "zh:网络攻击",
                    "surface": "网络攻击",
                    "concept_id": "concept:cyber_attack",
                    "paper_ids": ["p1", "p2"],
                    "confidence": "high",
                    "evidence": ["title and abstract directly discuss cyber attack traffic"],
                },
                {
                    "decision": "resolved",
                    "alias_key": "zh:网络攻击",
                    "concept_id": "concept:not_in_request",
                    "paper_ids": ["p1"],
                    "evidence": ["invalid target"],
                },
                {
                    "decision": "resolved",
                    "alias_key": "zh:网络攻击",
                    "concept_id": "concept:cyber_attack",
                    "paper_ids": ["p1"],
                    "evidence": [],
                },
                {
                    "decision": "unresolved",
                    "alias_key": "zh:网络攻击",
                    "paper_ids": ["p2"],
                    "reason": "evidence too weak",
                },
            ],
        }

        refined, trace = theme_candidate_resolution.apply_theme_candidate_resolution_result(
            self._low_signal_raw(),
            request,
            result,
        )

        self.assertEqual(trace["applied"], True)
        self.assertEqual(trace["resolved_count"], 1)
        self.assertEqual(trace["unresolved_count"], 3)
        self.assertEqual(len(refined["themes"]), 1)
        theme = refined["themes"][0]
        self.assertEqual(theme["concept_id"], "concept:cyber_attack")
        self.assertEqual(theme["paper_ids"], ["p1", "p2"])
        self.assertEqual(theme["matched_aliases"], {"zh": ["网络攻击"]})
        self.assertEqual(theme["method"], "agent_resolved_ambiguous_alias")

    def test_apply_result_rejects_unsupported_schema_version(self) -> None:
        with mock.patch(
            "vpnsci_sustech.theme_candidate_resolution._ambiguous_candidate_matches",
            side_effect=self._matches,
        ):
            request, _ = theme_candidate_resolution.build_theme_candidate_resolution_request(
                self._low_signal_raw(),
                self._papers(),
                display_query="网络攻击检测",
                language="zh",
            )
        result = {
            "schema_version": "theme_candidate_resolution_result.v0",
            "decisions": [
                {
                    "decision": "resolved",
                    "alias_key": "zh:网络攻击",
                    "concept_id": "concept:cyber_attack",
                    "paper_ids": ["p1"],
                    "evidence": ["title directly discusses 网络攻击"],
                }
            ],
        }

        refined, trace = theme_candidate_resolution.apply_theme_candidate_resolution_result(
            self._low_signal_raw(),
            request,
            result,
        )

        self.assertEqual(refined["themes"], [])
        self.assertEqual(trace["attempted"], True)
        self.assertEqual(trace["applied"], False)
        self.assertEqual(trace["reason"], "invalid_result")


if __name__ == "__main__":
    unittest.main()

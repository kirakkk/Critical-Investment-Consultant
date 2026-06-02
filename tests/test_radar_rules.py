import unittest

from cic.radar_rules import (
    build_radar_claims,
    cross_validate_claim,
    evidence_from_payload,
    normalize_radar_input,
    source_profiles_for,
)


def radar_payload(extra_evidence=None, weak_rank="C", source_family="expert_kol"):
    return {
        "stock_code": "001309.SZ",
        "stock_name": "德明利",
        "theme": "国产存储",
        "weak_signals": [
            {
                "signal_text": "KOL称公司可能受益于AI数据中心SSD需求。",
                "source_family": source_family,
                "source_rank": weak_rank,
                "independence_group": "same_kol_group",
                "kol_profile": {"handle": "@sample", "kol_quality_score": 72},
            }
        ],
        "evidence": extra_evidence or [],
        "risks": ["KOL持仓未知"],
    }


class RadarRulesTest(unittest.TestCase):
    def test_d_rank_source_stays_raw_weak_signal(self):
        radar = normalize_radar_input(radar_payload(weak_rank="D", source_family="social_media"))
        evidence = evidence_from_payload(radar)
        cross = cross_validate_claim(evidence[0], evidence)
        profiles = source_profiles_for(evidence)
        claims = build_radar_claims(radar, evidence, profiles)
        self.assertEqual(cross.result_state, "raw_weak_signal")
        self.assertEqual(claims[0].status, "raw_weak_signal")
        self.assertIn("d_rank_source_gate", claims[0].scores["triggered_rule_ids"])

    def test_kol_only_is_blocked(self):
        radar = normalize_radar_input(radar_payload())
        evidence = evidence_from_payload(radar)
        cross = cross_validate_claim(evidence[0], evidence)
        profiles = source_profiles_for(evidence)
        claims = build_radar_claims(radar, evidence, profiles)
        self.assertEqual(cross.gate_status, "blocked_kol_only")
        self.assertEqual(claims[0].status, "validation_queue")
        self.assertIn("KOL-only", " ".join(claims[0].upgrade_blockers))

    def test_independent_public_source_raises_x_score(self):
        radar = normalize_radar_input(
            radar_payload(
                extra_evidence=[
                    {
                        "claim": "公司官网展示固态硬盘和数据存储产品线。",
                        "source_family": "public_footprint",
                        "source_rank": "C",
                        "independence_group": "company_site_group",
                    }
                ]
            )
        )
        evidence = evidence_from_payload(radar)
        cross = cross_validate_claim(evidence[0], evidence)
        self.assertGreaterEqual(cross.x_score_after, 60)
        self.assertIn(cross.result_state, {"validation_queue", "evidence_convergence"})
        self.assertIn("public_footprint", cross.source_families)

    def test_same_independence_group_does_not_double_count(self):
        radar = normalize_radar_input(
            radar_payload(
                extra_evidence=[
                    {
                        "claim": "同一KOL转述同一观点。",
                        "source_family": "expert_kol",
                        "source_rank": "C",
                        "independence_group": "same_kol_group",
                    }
                ]
            )
        )
        evidence = evidence_from_payload(radar)
        cross = cross_validate_claim(evidence[0], evidence)
        self.assertEqual(cross.support_count, 1)


if __name__ == "__main__":
    unittest.main()

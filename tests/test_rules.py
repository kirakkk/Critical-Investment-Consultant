import unittest

from cic.report import analyze_holdings
from cic.rules import action_from_score, normalize_holding, score_holding


class RulesTest(unittest.TestCase):
    def test_low_rank_source_cannot_upgrade_to_candidate(self):
        holding = normalize_holding(
            {
                "stock_code": "300000.SZ",
                "stock_name": "低等级线索",
                "theme": "AI 应用",
                "thesis": "社媒称公司受益于 AI。",
                "source_rank": "D",
                "stock_20d_return": 0.3,
                "sector_20d_return": 0.1,
                "index_20d_return": 0.0,
                "pe_percentile_5y": 0.2,
                "events": [{"impact_direction": "positive", "source_rank": "D", "claim": "传闻"}],
            }
        )
        score = score_holding(holding)
        signal_type, *_ = action_from_score(score, holding["source_rank"])
        self.assertNotEqual(signal_type, "候选信号")

    def test_hard_risk_blocks_candidate(self):
        holding = normalize_holding(
            {
                "stock_code": "000001.SZ",
                "stock_name": "硬风险公司",
                "theme": "银行",
                "thesis": "基本面改善。",
                "source_rank": "A",
                "stock_20d_return": 0.2,
                "sector_20d_return": 0.1,
                "index_20d_return": 0.0,
                "pe_percentile_5y": 0.1,
                "risks": ["立案调查"],
                "events": [{"impact_direction": "positive", "source_rank": "A", "claim": "公告"}],
            }
        )
        score = score_holding(holding)
        signal_type, _, _, new_state, _ = action_from_score(score, holding["source_rank"])
        self.assertEqual(score.Q, "D")
        self.assertEqual(signal_type, "排除/退出复核")
        self.assertEqual(new_state, "excluded")

    def test_report_keeps_top_changes_to_three(self):
        holdings = []
        for idx in range(5):
            holdings.append(
                {
                    "stock_code": f"00000{idx}.SZ",
                    "stock_name": f"样例{idx}",
                    "theme": "同主题",
                    "thesis": "订单兑现增强。",
                    "source_rank": "A",
                    "stock_20d_return": 0.2,
                    "sector_20d_return": 0.1,
                    "index_20d_return": 0.0,
                    "pe_percentile_5y": 0.2,
                    "events": [{"impact_direction": "positive", "source_rank": "A", "claim": "公告"}],
                }
            )
        report = analyze_holdings(holdings, use_llm=False)
        self.assertLessEqual(len(report["brief"]["top_changes"]), 3)


if __name__ == "__main__":
    unittest.main()

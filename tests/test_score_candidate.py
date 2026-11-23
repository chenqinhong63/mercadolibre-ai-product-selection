#!/usr/bin/env python3
"""Tests for score_candidate.py (V2.1 port). Stdlib unittest, no network."""
import csv
import io
import json
import os
import sys
import tempfile
from pathlib import Path
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from score_candidate import (  # noqa: E402
    competition_score,
    main,
    profit_score,
    score_row,
)


def base_row(**overrides):
    row = {
        "candidate": "Cuerda test",
        "category": "Deportes",
        "price_mxn": "500",
        "cost_mxn": "150",
        "shipping_mxn": "30",
        "platform_fee_pct": "0",
        "other_cost_mxn": "0",
        "return_rate_pct": "0",
        "ad_pct": "0",
        "installment_pct": "0",
        "demand_signal": "strong",
        "competitor_count": "3",
        "supply_status": "ready",
        "brand_status": "own",
        "restricted": "no",
        "ip_risk": "low",
        "demand_source": "damaishuju",
        "differentiation": "strong",
        "risk_demand": "low",
        "risk_competition": "low",
        "risk_profit": "low",
        "risk_supply": "low",
        "risk_inventory": "low",
        "risk_compliance": "low",
        "budget_fit": "strong",
        "supply_advantage": "strong",
        "operating_capability": "strong",
        "logistics_capability": "strong",
        "moq": "100",
        "expected_daily_orders": "10",
        "total_budget_mxn": "100000",
    }
    row.update(overrides)
    return row


class TestBands(unittest.TestCase):
    def test_competition_bands(self):
        self.assertEqual(competition_score(None), 0)
        self.assertEqual(competition_score(5), 20)
        self.assertEqual(competition_score(6), 14)
        self.assertEqual(competition_score(15), 14)
        self.assertEqual(competition_score(16), 8)
        self.assertEqual(competition_score(30), 8)
        self.assertEqual(competition_score(31), 3)

    def test_profit_bands(self):
        self.assertEqual(profit_score(45), 20)
        self.assertEqual(profit_score(40), 20)
        self.assertEqual(profit_score(25), 15)
        self.assertEqual(profit_score(15), 10)
        self.assertEqual(profit_score(0), 5)
        self.assertEqual(profit_score(-1), 0)


class TestVerdicts(unittest.TestCase):
    def test_go_case(self):
        result = score_row(base_row())
        # 25 demand + 20 competition + 20 profit (64% margin) + 15 supply + 20 compliance
        self.assertEqual(result["total"], 100)
        self.assertEqual(result["verdict"], "GO")
        self.assertEqual(result["confidence"], "高")
        self.assertEqual(result["risk_adjusted"], 100)
        self.assertEqual(result["market_score"], 100.0)
        self.assertEqual(result["seller_fit"], 100.0)
        self.assertEqual(result["capital_score"], 100)

    def test_conditional_case(self):
        result = score_row(base_row(
            demand_signal="medium", competitor_count="10",
            cost_mxn="300", supply_status="partial",
            ip_risk="medium", differentiation="medium",
        ))
        # 17 + 14 + 15 (34% margin) + 8 + 10 = 64
        self.assertEqual(result["total"], 64)
        self.assertEqual(result["verdict"], "CONDITIONAL")

    def test_no_go_by_total(self):
        result = score_row(base_row(
            demand_signal="weak", competitor_count="40",
            cost_mxn="450", supply_status="not_ready", ip_risk="medium",
        ))
        # 9 + 3 + 5 (4% margin) + 0 + 10 = 27
        self.assertEqual(result["total"], 27)
        self.assertEqual(result["verdict"], "NO-GO")

    def test_block_unauthorized_brand(self):
        result = score_row(base_row(brand_status="unauthorized_brand"))
        self.assertEqual(result["verdict"], "NO-GO")
        self.assertIn("未授权品牌", result["block_reasons"])

    def test_block_restricted_and_high_ip(self):
        self.assertIn("受限类目或认证未通过",
                      score_row(base_row(restricted="yes"))["block_reasons"])
        self.assertIn("知识产权高风险",
                      score_row(base_row(ip_risk="high"))["block_reasons"])

    def test_negative_profit_no_go(self):
        result = score_row(base_row(cost_mxn="600"))
        self.assertLess(result["profit"]["net_per_unit"], 0)
        self.assertEqual(result["verdict"], "NO-GO")
        self.assertIn("负毛利", result["block_reasons"])


class TestCapsAndAdjustments(unittest.TestCase):
    def test_unknown_data_cap_at_74(self):
        result = score_row(base_row(
            competitor_count="", demand_source="", differentiation="",
            risk_demand="", risk_competition="", risk_profit="",
            risk_supply="", risk_inventory="", risk_compliance="",
        ))
        # Uncapped: 25 + 0 + 20 + 15 + 20 = 80 -> capped at 74
        self.assertEqual(result["total"], 74)
        self.assertEqual(result["risk_adjusted"], 74)
        self.assertNotEqual(result["verdict"], "GO")
        self.assertTrue(result["critical_missing"])

    def test_differentiation_none_caps_competition_at_8(self):
        result = score_row(base_row(differentiation="none"))
        self.assertEqual(result["scores"]["competition"], 8)
        # 25 + 8 + 20 + 15 + 20 = 88
        self.assertEqual(result["total"], 88)
        self.assertIn("无差异点，仅靠价格竞争", result["warnings"])

    def test_risk_adjusted_penalty(self):
        result = score_row(base_row(risk_demand="high", risk_profit="medium"))
        self.assertEqual(result["risk_adjusted"], 100 - 4 - 2)

    def test_risk_penalty_capped_at_20(self):
        result = score_row(base_row(
            risk_demand="high", risk_competition="high", risk_profit="high",
            risk_supply="high", risk_inventory="high", risk_compliance="high",
        ))
        # 6 highs * 4 = 24 -> capped at 20
        self.assertEqual(result["risk_adjusted"], 80)

    def test_confidence_levels(self):
        self.assertEqual(score_row(base_row())["confidence"], "高")
        self.assertEqual(score_row(base_row(demand_source=""))["confidence"], "中")
        self.assertEqual(score_row(base_row(
            competitor_count="", demand_source="", differentiation="",
        ))["confidence"], "低")
        self.assertEqual(score_row(base_row(
            risk_demand="high", risk_competition="high",
        ))["confidence"], "低")
        # One high risk demotes High to Medium.
        self.assertEqual(score_row(base_row(risk_demand="high"))["confidence"], "中")


class TestDowngrade(unittest.TestCase):
    def test_downgrade_low_seller_fit(self):
        result = score_row(base_row(
            budget_fit="weak", supply_advantage="weak",
            operating_capability="weak", logistics_capability="weak",
        ))
        self.assertEqual(result["seller_fit"], 20.0)
        self.assertEqual(result["verdict"], "CONDITIONAL")
        self.assertTrue(result["downgrade_reasons"])

    def test_downgrade_low_capital_score(self):
        # 10% margin -> margin component 10; no moq/days/budget -> 0 + 0.
        result = score_row(base_row(
            cost_mxn="420", moq="", expected_daily_orders="", total_budget_mxn="",
        ))
        # 25 + 20 + 5 + 15 + 20 = 85, GO-eligible on total, but capital 10.
        self.assertEqual(result["total"], 85)
        self.assertEqual(result["capital_score"], 10)
        self.assertEqual(result["verdict"], "CONDITIONAL")
        self.assertTrue(result["downgrade_reasons"])


class TestCli(unittest.TestCase):
    def test_csv_to_md_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "candidates.csv")
            md_path = os.path.join(tmp, "shortlist.md")
            json_path = os.path.join(tmp, "results.json")
            fields = list(base_row().keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(base_row(candidate="GO品"))
                writer.writerow(base_row(
                    candidate="差品", demand_signal="weak", competitor_count="40",
                    cost_mxn="450", supply_status="not_ready", ip_risk="medium",
                ))
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["--input", csv_path, "--output", md_path,
                                       "--json", json_path]), 0)
            md = Path(md_path).read_text(encoding="utf-8")
            self.assertIn("GO品 — GO", md)
            self.assertIn("差品 — NO-GO", md)
            data = json.loads(Path(json_path).read_text(encoding="utf-8"))
            self.assertEqual([d["verdict"] for d in data], ["GO", "NO-GO"])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Tests for profit_estimate.py (V2.1 port). Stdlib unittest, no network."""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from profit_estimate import estimate, main  # noqa: E402


class TestEstimate(unittest.TestCase):
    def test_basic_hand_computed(self):
        # fee 500*10%=50, return 500*5%=25
        # net = 500-50-200-30-10-25 = 185; margin 37%; breakeven 240/0.85=282.35
        result = estimate(500, 200, 30, 10, 10, 5)
        self.assertEqual(result["platform_fee"], 50.0)
        self.assertEqual(result["return_cost"], 25.0)
        self.assertEqual(result["ad_cost"], 0.0)
        self.assertEqual(result["installment_cost"], 0.0)
        self.assertEqual(result["net_per_unit"], 185.0)
        self.assertEqual(result["margin_pct"], 37.0)
        self.assertEqual(result["breakeven_price"], 282.35)

    def test_with_ad_and_installment(self):
        # fee 50, return 25, ad 25, installment 25
        # net = 500-50-200-30-10-25-25-25 = 135; margin 27%; breakeven 240/0.75=320
        result = estimate(500, 200, 30, 10, 10, 5, ad_pct=5, installment_pct=5)
        self.assertEqual(result["ad_cost"], 25.0)
        self.assertEqual(result["installment_cost"], 25.0)
        self.assertEqual(result["net_per_unit"], 135.0)
        self.assertEqual(result["margin_pct"], 27.0)
        self.assertEqual(result["breakeven_price"], 320.0)

    def test_zero_ad_installment_defaults(self):
        result = estimate(500, 200, 30, 0, 0, 0)
        self.assertEqual(result["ad_cost"], 0.0)
        self.assertEqual(result["installment_cost"], 0.0)
        self.assertEqual(result["net_per_unit"], 270.0)
        self.assertEqual(result["margin_pct"], 54.0)
        self.assertEqual(result["breakeven_price"], 230.0)

    def test_breakeven_denominator_negative_returns_none(self):
        # 60% fee + 50% return -> denominator -0.10
        result = estimate(100, 10, 0, 60, 0, 50)
        self.assertIsNone(result["breakeven_price"])

    def test_breakeven_denominator_zero_returns_none(self):
        result = estimate(100, 10, 0, 50, 0, 50)
        self.assertIsNone(result["breakeven_price"])

    def test_negative_margin(self):
        result = estimate(100, 200, 0, 0, 0, 0)
        self.assertEqual(result["net_per_unit"], -100.0)
        self.assertEqual(result["margin_pct"], -100.0)


class TestCli(unittest.TestCase):
    def test_cli_output(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["--price", "500", "--cost", "200", "--shipping", "30",
                                   "--fee-pct", "10", "--other", "10",
                                   "--return-pct", "5"]), 0)
        self.assertIn("net_per_unit: 185.0", out.getvalue())
        self.assertIn("模拟结果，不代表实际费用", out.getvalue())


if __name__ == "__main__":
    unittest.main()

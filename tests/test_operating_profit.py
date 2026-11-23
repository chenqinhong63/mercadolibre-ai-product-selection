#!/usr/bin/env python3
"""Tests for operating_profit.py (V2.1 port). Stdlib unittest, no network."""
import argparse
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from operating_profit import breakdown, main, reverse  # noqa: E402


def make_args(**overrides):
    args = argparse.Namespace(
        price=500.0, procurement=200.0, first_leg=20.0, import_cost=10.0,
        local_shipping=30.0, fee_pct=10.0, tax_pct=8.0, warehousing=5.0,
        packaging=5.0, ad_pct=5.0, installment_pct=0.0, return_pct=5.0,
        after_sales=10.0, moq=100, target_price=None, target_margin_pct=25.0,
        supplier_quote=None, total_budget=10000.0,
    )
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


class TestBreakdown(unittest.TestCase):
    def test_three_layer_hand_computed(self):
        result = breakdown(make_args())
        # gross = 500-200-20-10 = 270; fee 50, tax 40, ad 25
        # contribution = 270-30-50-40-5-5-25-0 = 115
        # net = 115-25-10 = 80; upfront = 200+20+10+5 = 235; batch 23500
        self.assertEqual(result["gross"], 270.0)
        self.assertEqual(result["gross_margin_pct"], 54.0)
        self.assertEqual(result["platform_fee"], 50.0)
        self.assertEqual(result["tax"], 40.0)
        self.assertEqual(result["ad_cost"], 25.0)
        self.assertEqual(result["installment_cost"], 0.0)
        self.assertEqual(result["return_cost"], 25.0)
        self.assertEqual(result["contribution"], 115.0)
        self.assertEqual(result["net"], 80.0)
        self.assertEqual(result["net_margin_pct"], 16.0)
        self.assertEqual(result["upfront_per_unit"], 235.0)
        self.assertEqual(result["batch_cash_outflow"], 23500.0)

    def test_no_moq_no_batch_outflow(self):
        result = breakdown(make_args(moq=0))
        self.assertIsNone(result["batch_cash_outflow"])


class TestReverse(unittest.TestCase):
    def test_reverse_hand_computed(self):
        result = reverse(make_args(target_price=500.0))
        # desired net = 125
        # max_procurement = 500-50-40-30-5-5-25-0-25-10-125-20-10 = 155
        # min_price = 280 / 0.47 = 595.74
        # max_shipping = -15; max_ad_pct = -4.0; max_moq = floor(10000/235) = 42
        self.assertEqual(result["max_procurement"], 155.0)
        self.assertEqual(result["min_price"], 595.74)
        self.assertEqual(result["max_shipping"], -15.0)
        self.assertEqual(result["max_ad_pct"], -4.0)
        self.assertEqual(result["max_moq"], 42)
        self.assertTrue(result["supplier_ok"])

    def test_supplier_quote_over_max(self):
        result = reverse(make_args(target_price=500.0, supplier_quote=200.0))
        self.assertFalse(result["supplier_ok"])

    def test_supplier_quote_under_max(self):
        result = reverse(make_args(target_price=500.0, supplier_quote=100.0))
        self.assertTrue(result["supplier_ok"])

    def test_min_price_none_when_denominator_nonpositive(self):
        result = reverse(make_args(target_price=500.0, target_margin_pct=100.0))
        self.assertIsNone(result["min_price"])

    def test_reverse_needs_price(self):
        with self.assertRaises(ValueError):
            reverse(make_args(price=None, target_price=None))


class TestCli(unittest.TestCase):
    def test_supplier_over_max_prints_exact_message(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main([
                "--price", "500", "--procurement", "200", "--first-leg", "20",
                "--import-cost", "10", "--local-shipping", "30",
                "--fee-pct", "10", "--tax-pct", "8", "--warehousing", "5",
                "--packaging", "5", "--ad-pct", "5", "--return-pct", "5",
                "--after-sales", "10", "--moq", "100",
                "--target-price", "500", "--target-margin-pct", "25",
                "--supplier-quote", "200", "--total-budget", "10000",
            ]), 0)
        text = out.getvalue()
        self.assertIn("最高可接受采购成本：155.0 MXN", text)
        self.assertIn("当前采购条件不符合目标利润要求。", text)

    def test_supplier_ok_prints_no_warning(self):
        out = io.StringIO()
        with redirect_stdout(out):
            main(["--price", "500", "--procurement", "200",
                  "--target-price", "500", "--supplier-quote", "100"])
        self.assertNotIn("当前采购条件不符合目标利润要求。", out.getvalue())


if __name__ == "__main__":
    unittest.main()

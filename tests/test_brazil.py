#!/usr/bin/env python3
"""Brazil (MLB/BRL) tests. Stdlib unittest, no network, no key.

Covers: market parameter + BRL currency in every script, Portuguese
review themes, CJK keyword rejection in the Damaishuju client, and
the rule that Mexico and Brazil fees/currencies are never mixed.
Existing Mexico (MLM/MXN) behaviour is covered by the other test
files and must keep passing unchanged.
"""
import argparse
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from damaishuju_client import DamaishujuError, validate_keyword, validate_market  # noqa: E402
from operating_profit import breakdown, reverse  # noqa: E402
from pricing_stats import compute_stats  # noqa: E402
from profit_estimate import currency_for as profit_currency_for, estimate  # noqa: E402
from review_themes import aggregate  # noqa: E402
from score_candidate import market_and_currency, score_row  # noqa: E402

FIXTURE_BR = os.path.join(os.path.dirname(__file__), "fixtures", "sample-snapshots-br.json")


def br_row(**overrides):
    row = {
        "candidate": "Corda teste",
        "category": "Esportes",
        "market_code": "MLB",
        "price_brl": "249",
        "cost_brl": "68",
        "shipping_brl": "32",
        "platform_fee_pct": "13",
        "other_cost_brl": "32.15",
        "return_rate_pct": "5",
        "ad_pct": "5",
        "installment_pct": "0",
        "demand_signal": "medium",
        "competitor_count": "4",
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
        "moq": "200",
        "expected_daily_orders": "4",
        "total_budget_brl": "50000",
    }
    row.update(overrides)
    return row


class TestMarketValidation(unittest.TestCase):
    def test_mlm_and_mlb_accepted(self):
        self.assertEqual(validate_market("MLM"), "MLM")
        self.assertEqual(validate_market("mlb"), "MLB")

    def test_unknown_market_rejected(self):
        with self.assertRaises(DamaishujuError):
            validate_market("MLA")
        with self.assertRaises(DamaishujuError):
            validate_market("")

    def test_chinese_keyword_rejected_for_both_markets(self):
        for market in ("MLM", "MLB"):
            with self.assertRaises(DamaishujuError):
                validate_keyword("跳绳", market)
            with self.assertRaises(DamaishujuError):
                validate_keyword("corda 跳绳", market)

    def test_portuguese_and_spanish_keywords_pass_cjk_check(self):
        # CJK check only; the skill layer must still confirm the
        # keyword is in the right language with the user.
        self.assertEqual(validate_keyword("corda para pular", "MLB"), "corda para pular")
        self.assertEqual(validate_keyword("cuerda para saltar", "MLM"), "cuerda para saltar")


class TestProfitBRL(unittest.TestCase):
    def test_estimate_brl_same_maths_new_currency(self):
        # Same numbers as the Mexico scoring example (249/68/32/13%/5%):
        # net 59.58 BRL, margin 23.93%, breakeven 171.62 BRL.
        result = estimate(249, 68, 32, 13, 32.15, 5, 5, 0, market_code="MLB")
        self.assertEqual(result["currency"], "BRL")
        self.assertEqual(result["market_code"], "MLB")
        self.assertEqual(result["net_per_unit"], 59.58)
        self.assertEqual(result["margin_pct"], 23.93)
        self.assertEqual(result["breakeven_price"], 171.62)

    def test_estimate_default_is_mlm_mxn(self):
        result = estimate(249, 68, 32, 13, 32.15, 5, 5, 0)
        self.assertEqual(result["currency"], "MXN")
        self.assertEqual(result["market_code"], "MLM")

    def test_unknown_market_rejected(self):
        with self.assertRaises(ValueError):
            profit_currency_for("MLA")


class TestOperatingProfitBRL(unittest.TestCase):
    def _args(self, **overrides):
        args = argparse.Namespace(
            price=500.0, procurement=200.0, first_leg=20.0, import_cost=10.0,
            local_shipping=30.0, fee_pct=10.0, tax_pct=8.0, warehousing=5.0,
            packaging=5.0, ad_pct=5.0, installment_pct=0.0, return_pct=5.0,
            after_sales=10.0, moq=100, target_price=None, target_margin_pct=25.0,
            supplier_quote=None, total_budget=10000.0, market_code="MLB",
        )
        for key, value in overrides.items():
            setattr(args, key, value)
        return args

    def test_breakdown_brl_same_numbers(self):
        result = breakdown(self._args())
        self.assertEqual(result["currency"], "BRL")
        self.assertEqual(result["market_code"], "MLB")
        self.assertEqual(result["gross"], 270.0)
        self.assertEqual(result["net"], 80.0)
        self.assertEqual(result["batch_cash_outflow"], 23500.0)

    def test_reverse_brl(self):
        result = reverse(self._args(target_price=500.0))
        self.assertEqual(result["currency"], "BRL")
        self.assertEqual(result["max_procurement"], 155.0)


class TestPricingStatsBRL(unittest.TestCase):
    def test_brl_currency_labelled(self):
        stats = compute_stats([100, 200, 300, 400, 500], market_code="MLB")
        self.assertEqual(stats["currency"], "BRL")
        self.assertEqual(stats["market_code"], "MLB")
        self.assertEqual(stats["median"], 300.0)

    def test_default_is_mxn(self):
        self.assertEqual(compute_stats([100, 200, 300])["currency"], "MXN")

    def test_unknown_market_rejected(self):
        with self.assertRaises(ValueError):
            compute_stats([100, 200], market_code="MLC")


class TestReviewThemesPortuguese(unittest.TestCase):
    def test_brazil_fixture_themes(self):
        with open(FIXTURE_BR, encoding="utf-8") as handle:
            fixture = json.load(handle)
        self.assertEqual(fixture["market_code"], "MLB")
        themes = {
            "qualidade": ["qualidade", "bom", "boa", "excelente"],
            "entrega": ["entrega", "chegou", "demorou", "atrasada"],
            "preço": ["preço", "caro", "barato"],
        }
        result = aggregate(fixture["reviews"], themes, market_code="MLB")
        self.assertEqual(result["market_code"], "MLB")
        self.assertEqual(result["review_language"], "Portuguese")
        self.assertTrue(result["thin_evidence"])  # only 5 usable reviews
        self.assertEqual(result["themes"]["qualidade"]["mentions"], 4)  # qualidade x3 + "bom" in the price review
        self.assertEqual(result["themes"]["entrega"]["mentions"], 3)
        self.assertEqual(result["themes"]["preço"]["mentions"], 2)

    def test_default_is_spanish(self):
        result = aggregate([{"text": "Buena calidad", "rating": 5}], {"calidad": ["calidad"]})
        self.assertEqual(result["review_language"], "Spanish")

    def test_unknown_market_rejected(self):
        with self.assertRaises(ValueError):
            aggregate([], {}, market_code="MLA")


class TestScoreCandidateBRL(unittest.TestCase):
    def test_brazil_row_scores_and_reports_brl(self):
        result = score_row(br_row())
        self.assertEqual(result["market_code"], "MLB")
        self.assertEqual(result["currency"], "BRL")
        # Same inputs as the Mexico example: total 82, GO.
        self.assertEqual(result["total"], 82)
        self.assertEqual(result["verdict"], "GO")
        self.assertEqual(result["profit"]["net_per_unit"], 59.58)

    def test_mxn_brl_mix_rejected(self):
        with self.assertRaises(ValueError):
            score_row(br_row(currency="MXN"))
        with self.assertRaises(ValueError):
            score_row(br_row(market_code="MLM", price_brl="249", price_mxn=""))

    def test_unknown_market_rejected(self):
        with self.assertRaises(ValueError):
            score_row(br_row(market_code="MLA"))

    def test_mexico_row_still_mxn(self):
        row = br_row()
        del row["market_code"]
        for key in ("price_brl", "cost_brl", "shipping_brl", "other_cost_brl", "total_budget_brl"):
            row[key.replace("_brl", "_mxn")] = row.pop(key)
        result = score_row(row)
        self.assertEqual(result["market_code"], "MLM")
        self.assertEqual(result["currency"], "MXN")
        self.assertEqual(result["total"], 82)

    def test_market_and_currency_helper(self):
        self.assertEqual(market_and_currency({"market_code": "MLB"}), ("MLB", "BRL"))
        self.assertEqual(market_and_currency({}), ("MLM", "MXN"))


class TestBrazilFixture(unittest.TestCase):
    def test_fixture_is_mlb_brl_portuguese(self):
        with open(FIXTURE_BR, encoding="utf-8") as handle:
            fixture = json.load(handle)
        self.assertEqual(fixture["market_code"], "MLB")
        for listing in fixture["listings"]:
            self.assertTrue(listing["sku_id"].startswith("MLB"))
            self.assertIn("price_brl", listing)
            self.assertNotIn("price_mxn", listing)
        for review in fixture["reviews"]:
            self.assertNotIn("跳", review["text"])


if __name__ == "__main__":
    unittest.main()

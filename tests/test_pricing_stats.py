#!/usr/bin/env python3
"""Tests for pricing_stats.py (FlatNine pricing-intel adaptation). No network."""
import json
import os
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from pricing_stats import compute_stats, load_prices, main  # noqa: E402


class TestBasicStats(unittest.TestCase):
    def test_hand_computed_five_values(self):
        stats = compute_stats([100, 200, 300, 400, 500])
        self.assertEqual(stats["min"], 100)
        self.assertEqual(stats["max"], 500)
        self.assertEqual(stats["mean"], 300.0)
        self.assertEqual(stats["median"], 300.0)
        self.assertIsNone(stats["mode"])  # every price unique
        self.assertAlmostEqual(stats["std_dev"], 141.42, places=2)
        self.assertEqual(stats["q1"], 200.0)
        self.assertEqual(stats["q3"], 400.0)
        self.assertEqual(stats["iqr"], 200.0)
        self.assertEqual(stats["confidence"], "low")  # n=5
        self.assertEqual(stats["currency"], "MXN")

    def test_mode_and_std_dev(self):
        stats = compute_stats([100, 200, 200, 300])
        self.assertEqual(stats["mode"], 200)
        # mean 200; population std dev = sqrt((100^2+0+0+100^2)/4) = sqrt(5000)
        self.assertAlmostEqual(stats["std_dev"], 70.71, places=2)

    def test_quartiles_even_count(self):
        # Linear interpolation: Q1 pos 0.25*3=0.75 -> 100*0.25+200*0.75=175
        # Q3 pos 0.75*3=2.25 -> 300*0.75+400*0.25=325
        stats = compute_stats([100, 200, 300, 400])
        self.assertEqual(stats["q1"], 175.0)
        self.assertEqual(stats["median"], 250.0)
        self.assertEqual(stats["q3"], 325.0)
        self.assertEqual(stats["iqr"], 150.0)

    def test_tiers(self):
        stats = compute_stats([100, 200, 300, 400, 500])
        tiers = stats["tiers"]
        self.assertEqual(tiers["budget"]["count"], 2)   # <= Q1=200
        self.assertEqual(tiers["mid"]["count"], 2)      # 200 < p <= 400
        self.assertEqual(tiers["premium"]["count"], 1)  # > Q3=400

    def test_histogram_sums_to_n(self):
        stats = compute_stats([100, 200, 300, 400, 500])
        buckets = stats["histogram_buckets"]
        self.assertTrue(5 <= len(buckets) <= 8)
        self.assertEqual(sum(b["count"] for b in buckets), 5)


class TestOutliers(unittest.TestCase):
    def test_zero_excluded(self):
        stats = compute_stats([0, 100, 200, 300])
        self.assertEqual(stats["n"], 3)
        self.assertEqual(stats["outliers_excluded"], 1)
        self.assertEqual(stats["mean"], 200.0)

    def test_over_ten_times_median_excluded(self):
        # Median of positives = 250, 10x = 2500, so 10000 is excluded.
        stats = compute_stats([100, 200, 300, 10000])
        self.assertEqual(stats["n"], 3)
        self.assertEqual(stats["outliers_excluded"], 1)
        self.assertEqual(stats["max"], 300)
        self.assertEqual(stats["mean"], 200.0)

    def test_empty_input_error(self):
        with self.assertRaises(ValueError):
            compute_stats([])

    def test_all_zero_error(self):
        with self.assertRaises(ValueError):
            compute_stats([0, 0, 0])


class TestConfidence(unittest.TestCase):
    def test_high_at_50(self):
        self.assertEqual(compute_stats(list(range(100, 600, 10)))["confidence"], "high")

    def test_medium_at_20(self):
        self.assertEqual(compute_stats(list(range(100, 300, 10)))["confidence"], "medium")

    def test_low_below_20(self):
        self.assertEqual(compute_stats(list(range(100, 290, 10)))["confidence"], "low")


class TestLoadingAndCli(unittest.TestCase):
    def test_load_json_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "prices.json")
            Path(path).write_text(json.dumps([{"price": 100}, {"price": 200}]), encoding="utf-8")
            self.assertEqual(load_prices(path), [100.0, 200.0])

    def test_load_csv_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "prices.csv")
            Path(path).write_text("sku,price_mxn\nA,100\nB,200\n", encoding="utf-8")
            self.assertEqual(load_prices(path, csv_column="price_mxn"), [100.0, 200.0])

    def test_cli_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "in.json")
            out_path = os.path.join(tmp, "out.json")
            Path(in_path).write_text(json.dumps([100, 200, 300, 400, 500]), encoding="utf-8")
            self.assertEqual(main(["--input", in_path, "--output", out_path]), 0)
            stats = json.loads(Path(out_path).read_text(encoding="utf-8"))
            self.assertEqual(stats["median"], 300.0)
            self.assertEqual(stats["n"], 5)


if __name__ == "__main__":
    unittest.main()

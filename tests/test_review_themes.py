#!/usr/bin/env python3
"""Tests for review_themes.py. Stdlib unittest, no network, no model."""
import json
import os
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from review_themes import aggregate, main  # noqa: E402

THEMES = {
    "calidad": ["calidad", "bueno", "excelente"],
    "envío": ["envío", "llegó", "tarde"],
    "precio": ["precio", "caro", "barato"],
}

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "sample-snapshots.json")


def load_fixture_reviews():
    with open(FIXTURE_PATH, encoding="utf-8") as handle:
        return json.load(handle)["reviews"]


class TestAggregate(unittest.TestCase):
    def test_theme_counts_and_split(self):
        reviews = load_fixture_reviews()
        # 7 extra 5-star "Producto bueno" reviews -> 12 usable, not thin.
        reviews += [{"text": "Producto bueno", "rating": 5, "date": "2026-11-15"}] * 7
        result = aggregate(reviews, THEMES)
        self.assertFalse(result["thin_evidence"])
        self.assertEqual(result["reviews_usable"], 12)
        calidad = result["themes"]["calidad"]
        # Fixture: 4 mentions (praise 2, complaint 1, neutral 1) + 7 praise.
        self.assertEqual(calidad["mentions"], 11)
        self.assertEqual(calidad["praise"], 9)
        self.assertEqual(calidad["complaint"], 1)
        self.assertEqual(calidad["neutral_or_unrated"], 1)
        envio = result["themes"]["envío"]
        self.assertEqual(envio["mentions"], 3)
        self.assertEqual(envio["praise"], 1)
        self.assertEqual(envio["complaint"], 1)
        self.assertEqual(envio["neutral_or_unrated"], 1)
        precio = result["themes"]["precio"]
        self.assertEqual(precio["mentions"], 2)
        self.assertEqual(precio["praise"], 1)
        self.assertEqual(precio["complaint"], 0)

    def test_thin_evidence_flag(self):
        result = aggregate(load_fixture_reviews(), THEMES)
        self.assertEqual(result["reviews_usable"], 5)
        self.assertTrue(result["thin_evidence"])
        self.assertIn("不足 10 条", result["thin_evidence_note"])

    def test_rating_three_is_neutral(self):
        result = aggregate(
            [{"text": "El precio es bueno", "rating": 3, "date": "2026-11-20"}] * 10,
            THEMES,
        )
        self.assertEqual(result["themes"]["precio"]["mentions"], 10)
        self.assertEqual(result["themes"]["precio"]["praise"], 0)
        self.assertEqual(result["themes"]["precio"]["complaint"], 0)
        self.assertEqual(result["themes"]["precio"]["neutral_or_unrated"], 10)

    def test_empty_text_uncounted(self):
        result = aggregate(
            [{"text": "", "rating": 5, "date": "2026-11-20"}] * 10
            + [{"text": "Buena calidad", "rating": 5, "date": "2026-11-20"}],
            THEMES,
        )
        self.assertEqual(result["reviews_uncounted"], 10)
        self.assertEqual(result["reviews_usable"], 1)

    def test_cap_at_500_most_recent(self):
        reviews = [
            {"text": "ok", "rating": 5, "date": f"2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"}
            for i in range(600)
        ]
        result = aggregate(reviews, THEMES)
        self.assertEqual(result["reviews_supplied"], 600)
        self.assertEqual(result["reviews_used"], 500)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            aggregate({"not": "a list"}, THEMES)
        with self.assertRaises(ValueError):
            aggregate([], ["not", "a dict"])


class TestCli(unittest.TestCase):
    def test_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "reviews.json")
            themes_path = os.path.join(tmp, "themes.json")
            out_path = os.path.join(tmp, "report.json")
            Path(in_path).write_text(json.dumps(load_fixture_reviews(), ensure_ascii=False), encoding="utf-8")
            Path(themes_path).write_text(json.dumps(THEMES, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(main(["--input", in_path, "--themes", themes_path,
                                   "--output", out_path]), 0)
            report = json.loads(Path(out_path).read_text(encoding="utf-8"))
            self.assertTrue(report["thin_evidence"])
            self.assertEqual(report["themes"]["calidad"]["mentions"], 4)


if __name__ == "__main__":
    unittest.main()

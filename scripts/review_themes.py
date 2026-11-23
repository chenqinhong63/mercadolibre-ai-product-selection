#!/usr/bin/env python3
"""Light theme aggregation for Mercado Libre product reviews (MLM Spanish / MLB Portuguese).

Input: JSON list of reviews, each ``{"text": ..., "rating": ..., "date": ...}``.
Themes come from a caller-supplied themes JSON file of the form
``{"theme_name": ["keyword1", "keyword2", ...]}`` -- there is NO
hard-coded Spanish sentiment lexicon here and no model pretence:
a review counts for a theme when any of that theme's keywords
appears in its text (case-insensitive substring match), at most
once per theme per review.

Counts only: praise = rating >= 4, complaint = rating <= 2,
rating 3 is neutral and counted in neither. Reviews without a
usable rating are reported as uncounted, not guessed.
Fewer than 10 reviews is flagged as thin evidence.
At most the 500 most recent reviews are used (by ``date`` when
present, otherwise input order).

Usage:
  python3 review_themes.py --input reviews.json --themes themes.json --output themes-report.json
"""
import argparse
import json
import sys
from datetime import datetime


MAX_REVIEWS = 500
THIN_EVIDENCE_THRESHOLD = 10
MARKETS = {"MLM": "Spanish", "MLB": "Portuguese"}


def language_for(market_code):
    code = (market_code or "MLM").strip().upper()
    if code not in MARKETS:
        raise ValueError(f"unknown market_code {market_code!r}; use MLM or MLB")
    return MARKETS[code]


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _rating(value):
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (ValueError, TypeError):
        return None


def aggregate(reviews, themes, market_code="MLM"):
    """Aggregate theme mentions over at most the 500 most recent reviews.

    Theme keywords must be in the review language: Spanish for MLM,
    Portuguese for MLB. This function does not translate keywords.
    """
    if not isinstance(reviews, list):
        raise ValueError("reviews input must be a JSON list")
    if not isinstance(themes, dict):
        raise ValueError("themes input must be a JSON object of theme -> keywords")

    indexed = list(enumerate(reviews))
    dated = [item for item in indexed if _parse_date(item[1].get("date") if isinstance(item[1], dict) else None) is not None]
    undated = [item for item in indexed if _parse_date(item[1].get("date") if isinstance(item[1], dict) else None) is None]
    dated.sort(key=lambda item: (_parse_date(item[1].get("date")), item[0]))
    if len(dated) + len(undated) > MAX_REVIEWS:
        # Keep the most recent reviews; undated ones are dropped first.
        selected = [review for _, review in dated[-MAX_REVIEWS:]]
    else:
        selected = [review for _, review in dated + undated]

    normalized_themes = {}
    for theme, keywords in themes.items():
        if not isinstance(keywords, list):
            raise ValueError(f"theme {theme!r} must map to a list of keywords")
        normalized_themes[theme] = [str(k).lower() for k in keywords if str(k).strip()]

    summary = {}
    for theme in normalized_themes:
        summary[theme] = {"mentions": 0, "praise": 0, "complaint": 0, "neutral_or_unrated": 0}

    usable = 0
    uncounted = 0
    for review in selected:
        if not isinstance(review, dict):
            uncounted += 1
            continue
        text = str(review.get("text") or "")
        if not text.strip():
            uncounted += 1
            continue
        usable += 1
        rating = _rating(review.get("rating"))
        lowered = text.lower()
        for theme, keywords in normalized_themes.items():
            if any(keyword in lowered for keyword in keywords):
                entry = summary[theme]
                entry["mentions"] += 1
                if rating is not None and rating >= 4:
                    entry["praise"] += 1
                elif rating is not None and rating <= 2:
                    entry["complaint"] += 1
                else:
                    entry["neutral_or_unrated"] += 1
    return {
        "market_code": (market_code or "MLM").strip().upper(),
        "review_language": language_for(market_code),
        "reviews_supplied": len(reviews),
        "reviews_used": len(selected),
        "reviews_usable": usable,
        "reviews_uncounted": uncounted,
        "thin_evidence": usable < THIN_EVIDENCE_THRESHOLD,
        "thin_evidence_note": (
            "样本不足 10 条有效评论，主题计数仅为薄弱证据，不宜据此下结论。"
            if usable < THIN_EVIDENCE_THRESHOLD else ""
        ),
        "themes": summary,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Aggregate review themes by keyword matching.")
    parser.add_argument("--input", required=True, help="JSON list of reviews {text, rating, date}")
    parser.add_argument("--themes", required=True, help="JSON file mapping theme names to keyword lists")
    parser.add_argument("--output", required=True, help="JSON output path")
    parser.add_argument("--market-code", default="MLM", help="Market code MLM (Spanish reviews) or MLB (Portuguese reviews)")
    args = parser.parse_args(argv)
    try:
        with open(args.input, encoding="utf-8") as handle:
            reviews = json.load(handle)
        with open(args.themes, encoding="utf-8") as handle:
            themes = json.load(handle)
        result = aggregate(reviews, themes, market_code=args.market_code)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.error(str(error))
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(f"有效评论 {result['reviews_usable']} 条（共 {result['reviews_supplied']} 条），"
          f"薄弱证据：{'是' if result['thin_evidence'] else '否'}")
    for theme, counts in result["themes"].items():
        print(f"{theme}: 提及 {counts['mentions']} 次，好评 {counts['praise']}，差评 {counts['complaint']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

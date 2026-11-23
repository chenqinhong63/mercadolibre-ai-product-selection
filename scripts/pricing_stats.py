#!/usr/bin/env python3
"""Pricing statistics for Mercado Libre listings (MLM: MXN, MLB: BRL).

Adapted from FlatNine ``pricing-intel`` (usecart/ecommerceskills,
MIT): min/max/mean/median/mode/std-dev/quartiles, outlier exclusion,
5-8 bucket histogram, Budget/Mid/Premium tiers and sample-size
confidence. FlatNine's US-dollar examples and Cart API are NOT used;
all prices here are in the market currency (MLM: MXN, MLB: BRL)
supplied by the caller (e.g. from Damaishuju ``search_product_snapshots``).
No data is invented; never mix MXN and BRL in one call.

Conventions (documented because FlatNine leaves them open):
  - Outlier exclusion, in two passes: drop prices <= 0 MXN, then
    drop prices > 10x the median of the remaining prices.
  - Percentiles (Q1/median/Q3): linear interpolation on the sorted
    sample, position = p * (n - 1).
  - Mode: the most frequent price; None when every price is unique
    (no repeated value); ties broken by the smallest price.
  - Std dev: population std dev (divide by n).
  - Histogram: 6 equal-width buckets over [min, max] (within the
    5-8 range); a single bucket when min == max.
  - Tiers: Budget = prices <= Q1 (bottom 25%), Mid = Q1 < price
    <= Q3 (middle 50%), Premium = price > Q3 (top 25%).
  - Confidence by cleaned sample size: high >= 50, medium 20-49,
    low < 20.

Usage:
  python3 pricing_stats.py --input prices.json [--price-field price]
  python3 pricing_stats.py --input listings.csv --csv-column price_mxn
  python3 pricing_stats.py --input prices.json --output stats.json
Input JSON is either a list of numbers or a list of objects; with
objects use --price-field (default "price"). CSV input needs
--csv-column. Empty input (or nothing left after outlier exclusion)
is an error.
"""
import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter


def _percentile(sorted_values, p):
    """Linear-interpolation percentile; p in [0, 1]."""
    n = len(sorted_values)
    if n == 1:
        return float(sorted_values[0])
    pos = p * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(sorted_values[lo])
    frac = pos - lo
    return float(sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac)


def _mode(values):
    counts = Counter(values)
    top = max(counts.values())
    if top == 1:
        return None
    return min(value for value, count in counts.items() if count == top)


MARKETS = {"MLM": "MXN", "MLB": "BRL"}


def currency_for(market_code):
    code = (market_code or "MLM").strip().upper()
    if code not in MARKETS:
        raise ValueError(f"unknown market_code {market_code!r}; use MLM or MLB")
    return MARKETS[code]


def compute_stats(prices, market_code="MLM"):
    """Compute pricing statistics for a list of prices in the market currency.

    Returns a dict. Raises ValueError on empty input or when no
    price survives outlier exclusion.
    """
    raw = [float(p) for p in prices]
    if not raw:
        raise ValueError("no prices supplied")
    excluded = []
    kept = []
    for price in raw:
        if price <= 0:
            excluded.append({"price": price, "reason": "price <= 0"})
        else:
            kept.append(price)
    if not kept:
        raise ValueError("no prices remain after excluding prices <= 0")
    median_raw = _percentile(sorted(kept), 0.5)
    cleaned = []
    for price in kept:
        if price > 10 * median_raw:
            excluded.append({"price": price, "reason": ">10x median"})
        else:
            cleaned.append(price)
    if not cleaned:
        raise ValueError("no prices remain after outlier exclusion")
    cleaned_sorted = sorted(cleaned)
    n = len(cleaned)
    mean = sum(cleaned) / n
    median = _percentile(cleaned_sorted, 0.5)
    q1 = _percentile(cleaned_sorted, 0.25)
    q3 = _percentile(cleaned_sorted, 0.75)
    iqr = q3 - q1
    mode = _mode(cleaned)
    std_dev = statistics.pstdev(cleaned) if n > 1 else 0.0

    bucket_count = 6
    lo, hi = cleaned_sorted[0], cleaned_sorted[-1]
    if hi == lo:
        buckets = [{"low": lo, "high": hi, "count": n, "pct": 100.0}]
    else:
        width = (hi - lo) / bucket_count
        buckets = []
        for i in range(bucket_count):
            b_low = lo + i * width
            b_high = lo + (i + 1) * width
            if i == bucket_count - 1:
                count = sum(1 for p in cleaned if b_low <= p <= b_high)
            else:
                count = sum(1 for p in cleaned if b_low <= p < b_high)
            buckets.append({
                "low": round(b_low, 2),
                "high": round(b_high, 2),
                "count": count,
                "pct": round(count / n * 100, 1),
            })

    budget = [p for p in cleaned if p <= q1]
    mid = [p for p in cleaned if q1 < p <= q3]
    premium = [p for p in cleaned if p > q3]
    if n >= 50:
        confidence = "high"
    elif n >= 20:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "market_code": (market_code or "MLM").strip().upper(),
        "currency": currency_for(market_code),
        "n_raw": len(raw),
        "n": n,
        "outliers_excluded": len(excluded),
        "excluded": excluded,
        "min": round(lo, 2),
        "max": round(hi, 2),
        "mean": round(mean, 2),
        "median": round(median, 2),
        "mode": round(mode, 2) if mode is not None else None,
        "std_dev": round(std_dev, 2),
        "q1": round(q1, 2),
        "q3": round(q3, 2),
        "iqr": round(iqr, 2),
        "histogram_buckets": buckets,
        "tiers": {
            "budget": {"low": round(lo, 2), "high": round(q1, 2), "count": len(budget)},
            "mid": {"low": round(q1, 2), "high": round(q3, 2), "count": len(mid)},
            "premium": {"low": round(q3, 2), "high": round(hi, 2), "count": len(premium)},
        },
        "confidence": confidence,
    }


def load_prices(path, price_field="price", csv_column=None):
    """Load prices from a JSON list or a CSV column."""
    if csv_column:
        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if csv_column not in (reader.fieldnames or []):
                raise ValueError(f"CSV column not found: {csv_column}")
            return [float(row[cvc]) for row in reader for cvc in [csv_column]
                    if (row.get(cvc) or "").strip() != ""]
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("JSON input must be a list of prices or objects")
    prices = []
    for item in data:
        if isinstance(item, (int, float)):
            prices.append(float(item))
        elif isinstance(item, dict):
            value = item.get(price_field)
            if value is None:
                raise ValueError(f"missing price field: {price_field}")
            prices.append(float(value))
        else:
            raise ValueError("JSON items must be numbers or objects")
    return prices


def render_text(stats):
    lines = [
        f"定价统计（{stats['currency']}，样本 {stats['n']} / 原始 {stats['n_raw']}，"
        f"剔除异常值 {stats['outliers_excluded']} 个，置信度 {stats['confidence']}）",
        f"最低：{stats['min']}，最高：{stats['max']}，均值：{stats['mean']}，"
        f"中位数：{stats['median']}，众数：{stats['mode']}，标准差：{stats['std_dev']}",
        f"Q1：{stats['q1']}，Q3：{stats['q3']}，IQR：{stats['iqr']}",
        "价格分布：",
    ]
    for bucket in stats["histogram_buckets"]:
        bar = "█" * max(1, int(bucket["pct"] // 2)) if bucket["count"] else ""
        lines.append(f"  {bucket['low']} - {bucket['high']}: {bar} {bucket['count']} ({bucket['pct']}%)")
    tiers = stats["tiers"]
    lines.append(
        f"Budget（底部 25%）：{tiers['budget']['low']} - {tiers['budget']['high']}，"
        f"{tiers['budget']['count']} 个；Mid（中间 50%）：{tiers['mid']['low']} - {tiers['mid']['high']}，"
        f"{tiers['mid']['count']} 个；Premium（顶部 25%）：{tiers['premium']['low']} - {tiers['premium']['high']}，"
        f"{tiers['premium']['count']} 个"
    )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pricing statistics for Mercado Libre prices (MLM: MXN, MLB: BRL).")
    parser.add_argument("--input", required=True, help="JSON list of prices/objects, or CSV file with --csv-column")
    parser.add_argument("--price-field", default="price", help="Object field holding the price (JSON input)")
    parser.add_argument("--csv-column", default=None, help="CSV column holding the price")
    parser.add_argument("--output", default=None, help="Optional JSON output path")
    parser.add_argument("--market-code", default="MLM", help="Market code MLM (Mexico, MXN) or MLB (Brazil, BRL)")
    args = parser.parse_args(argv)
    try:
        prices = load_prices(args.input, args.price_field, args.csv_column)
        stats = compute_stats(prices, market_code=args.market_code)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(stats, handle, ensure_ascii=False, indent=2)
    print(render_text(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())

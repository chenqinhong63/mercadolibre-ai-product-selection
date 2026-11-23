#!/usr/bin/env python3
"""Score Mercado Libre product candidates from a CSV file (V2.1).

Markets: MLM (Mexico, MXN, default) or MLB (Brazil, BRL). Money
columns accept generic names (price/cost/shipping/other_cost) or
market names (price_mxn/price_brl, cost_mxn/cost_brl, ...). Never
mix MXN and BRL in one row; the row currency is taken from
market_code (or an explicit currency column). Scoring bands and
verdicts are the V2.1 rubric and apply to both markets unless the
user recalibrates them.

Ported exactly from the V2.1 skill script
``~/workspace/custom-skills/mercado-libre-product-selection/scripts/score_candidate.py``.
This copy adds only an optional ``--json`` output flag; all scoring
logic, bands, caps, verdicts and downgrade rules are unchanged.

V2.1 additions, all interpretive and never added to the original total:
  - market opportunity, seller fit and capital efficiency scores
  - entry difficulty and GO downgrade rules for low fit or low capital
  - failure five questions and low-cost verification fields, rendered
    when present in the CSV, never invented by the script

Input columns (see templates/candidate-input.csv in the skill):
  candidate, category, price_mxn, cost_mxn, shipping_mxn,
  platform_fee_pct, other_cost_mxn, return_rate_pct, ad_pct,
  installment_pct, demand_signal, competitor_count, supply_status,
  brand_status, restricted, ip_risk, demand_source, differentiation,
  risk_demand, risk_competition, risk_profit, risk_supply,
  risk_inventory, risk_compliance

Scoring (100 points, internal comparison only, unchanged from V1):
  demand 25, competition 20, profit 20, supply 15, compliance 20.
Gates override the total:
  - unauthorized_brand, restricted=yes, or ip_risk=high -> BLOCK -> NO-GO
  - negative net profit -> NO-GO
Verdicts:
  - BLOCK or negative profit: NO-GO
  - total >= 75 and supply ready and demand medium or strong: GO
  - total >= 50: CONDITIONAL
  - otherwise: NO-GO
V2 additions (original total is never overwritten):
  - unknown-data cap: if a critical field is missing, total is capped at 74
  - new-seller cap: differentiation none caps competition score at 8
  - risk-adjusted score: total minus risk penalty (high 4, medium 2, cap 20)
  - confidence: High / Medium / Low from missing data and high-risk count
  - key risk list: every medium and high risk, by category

All fee percentages are INPUTS from the CSV (default 0.0); no
commission rate is hard-coded here, because no Mercado Libre
commission % was verified directly as of 2026-11-23.

Usage:
  python3 score_candidate.py --input candidates.csv --output shortlist.md
  python3 score_candidate.py --input candidates.csv --output shortlist.md --json results.json
"""
import argparse
import csv
import json
import sys

try:
    from profit_estimate import estimate
except ImportError:  # package-style import (``python -m scripts...``)
    from scripts.profit_estimate import estimate


DEMAND_SCORES = {"strong": 25, "medium": 17, "weak": 9, "none": 0}
SUPPLY_SCORES = {"ready": 15, "partial": 8, "not_ready": 0}
COMPLIANCE_SCORES = {"low": 20, "medium": 10, "high": 0}
RISK_LABELS = {
    "risk_demand": "需求风险",
    "risk_competition": "竞争风险",
    "risk_profit": "利润风险",
    "risk_supply": "供应风险",
    "risk_inventory": "库存风险",
    "risk_compliance": "合规风险",
}
RISK_PENALTIES = {"high": 4, "medium": 2, "low": 0}
FIT_SCORES = {"strong": 100, "medium": 60, "weak": 20}
DIFF_SCORES = {"strong": 30, "medium": 20, "weak": 10, "none": 0}


MARKETS = {"MLM": "MXN", "MLB": "BRL"}


def market_and_currency(row):
    code = (row.get("market_code") or "MLM").strip().upper()
    if code not in MARKETS:
        raise ValueError(f"unknown market_code {code!r}; use MLM or MLB")
    currency = (row.get("currency") or MARKETS[code]).strip().upper()
    if currency != MARKETS[code]:
        raise ValueError(
            f"currency {currency!r} does not match market_code {code} "
            f"(expected {MARKETS[code]}); never mix MXN and BRL in one row"
        )
    # A row must not carry money columns of the other market's currency.
    other = "BRL" if code == "MLM" else "MXN"
    suffix = "_brl" if other == "BRL" else "_mxn"
    for key, value in row.items():
        if key.endswith(suffix) and value is not None and str(value).strip() != "":
            raise ValueError(
                f"column {key!r} is {other} but market_code is {code}; "
                "never mix MXN and BRL in one row"
            )
    return code, currency


def money(row, *names):
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip() != "":
            return to_float(value)
    return 0.0


def fit_score(value):
    return FIT_SCORES.get((value or "").strip().lower())


def risk_level(row, column):
    value = (row.get(column) or "").strip().lower()
    return value if value in RISK_PENALTIES else ""


def to_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except ValueError:
        return default


def to_int_or_none(value):
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(value))
    except ValueError:
        return None


def competition_score(count):
    if count is None:
        return 0
    if count <= 5:
        return 20
    if count <= 15:
        return 14
    if count <= 30:
        return 8
    return 3


def profit_score(margin_pct):
    if margin_pct >= 40:
        return 20
    if margin_pct >= 25:
        return 15
    if margin_pct >= 15:
        return 10
    if margin_pct >= 0:
        return 5
    return 0


def score_row(row):
    market_code, currency = market_and_currency(row)
    price = money(row, "price", "price_mxn", "price_brl")
    cost = money(row, "cost", "cost_mxn", "cost_brl")
    shipping = money(row, "shipping", "shipping_mxn", "shipping_brl")
    fee_pct = to_float(row.get("platform_fee_pct"))
    other = money(row, "other_cost", "other_cost_mxn", "other_cost_brl")
    return_pct = to_float(row.get("return_rate_pct"))
    ad_pct = to_float(row.get("ad_pct"))
    installment_pct = to_float(row.get("installment_pct"))
    profit = estimate(price, cost, shipping, fee_pct, other, return_pct, ad_pct, installment_pct) if price > 0 else {
        "platform_fee": 0, "return_cost": 0, "net_per_unit": 0,
        "margin_pct": 0, "breakeven_price": None,
    }

    demand = (row.get("demand_signal") or "none").strip().lower()
    demand_score = DEMAND_SCORES.get(demand, 0)
    comp_score = competition_score(to_int_or_none(row.get("competitor_count")))
    prof_score = profit_score(profit["margin_pct"])
    supply = (row.get("supply_status") or "not_ready").strip().lower()
    supply_score = SUPPLY_SCORES.get(supply, 0)
    ip_risk = (row.get("ip_risk") or "high").strip().lower()
    comp_risk_score = COMPLIANCE_SCORES.get(ip_risk, 0)

    differentiation = (row.get("differentiation") or "").strip().lower()
    if differentiation == "none":
        comp_score = min(comp_score, 8)

    total = demand_score + comp_score + prof_score + supply_score + comp_risk_score

    # V2: risk ratings, risk-adjusted score, confidence, unknown-data cap.
    risks = {}
    for column in RISK_LABELS:
        level = risk_level(row, column)
        if level:
            risks[column] = level
    risk_penalty = min(20, sum(RISK_PENALTIES[level] for level in risks.values()))
    risk_adjusted = max(0, total - risk_penalty)
    key_risks = [
        f"{RISK_LABELS[column]}：{level}"
        for column, level in risks.items()
        if level in ("medium", "high")
    ]
    high_risk_count = sum(1 for level in risks.values() if level == "high")

    critical_missing = []
    if to_int_or_none(row.get("competitor_count")) is None:
        critical_missing.append("竞争卖家数")
    if not (row.get("demand_source") or "").strip():
        critical_missing.append("需求来源")
    if differentiation == "":
        critical_missing.append("差异点")
    if not risks:
        critical_missing.append("风险等级")
    if critical_missing:
        total = min(total, 74)
        risk_adjusted = min(risk_adjusted, 74)
    missing_count = len(critical_missing)
    if (row.get("brand_status") or "").strip().lower() == "unknown":
        missing_count += 1
    if missing_count == 0:
        confidence = "高"
    elif missing_count <= 2:
        confidence = "中"
    else:
        confidence = "低"
    if high_risk_count >= 2:
        confidence = "低"
    elif high_risk_count == 1 and confidence == "高":
        confidence = "中"

    block_reasons = []
    brand = (row.get("brand_status") or "unknown").strip().lower()
    if brand == "unauthorized_brand":
        block_reasons.append("未授权品牌")
    if (row.get("restricted") or "").strip().lower() == "yes":
        block_reasons.append("受限类目或认证未通过")
    if ip_risk == "high":
        block_reasons.append("知识产权高风险")

    gaps = []
    if to_int_or_none(row.get("competitor_count")) is None:
        gaps.append("竞争卖家数待核实")
    if demand == "none":
        gaps.append("需求信号缺失")
    if supply != "ready":
        gaps.append("供应或物流未就绪")
    if brand == "unknown":
        gaps.append("品牌状态未知，按高风险处理")
    if not (row.get("demand_source") or "").strip():
        gaps.append("需求来源未记录")
    warnings = []
    if price > 0 and shipping / price > 0.35:
        warnings.append(f"运费占比高（{round(shipping / price * 100, 1)}%），低价重货先复核物流和破损成本")
    differentiation = (row.get("differentiation") or "").strip().lower()
    if differentiation == "none":
        warnings.append("无差异点，仅靠价格竞争")
    elif differentiation == "":
        gaps.append("差异点未填写")

    # V2.1: dual scores, interpretive only, never added to the total.
    market_score = round(demand_score / 25 * 40 + comp_score / 20 * 30 + DIFF_SCORES.get(differentiation, 0), 1)
    fit_values = [
        fit_score(row.get(column))
        for column in ("budget_fit", "supply_advantage", "operating_capability", "logistics_capability")
    ]
    fit_values = [value for value in fit_values if value is not None]
    seller_fit = round(sum(fit_values) / len(fit_values), 1) if fit_values else 0.0
    if not fit_values:
        gaps.append("卖家适配未评估")
    moq_value = to_int_or_none(row.get("moq")) or 0
    batch_capital = round(moq_value * (price and (cost + shipping + other) or 0), 2) if moq_value else 0.0
    daily_orders = to_float(row.get("expected_daily_orders"))
    days_of_stock = round(moq_value / daily_orders, 1) if daily_orders > 0 and moq_value else None
    margin_component = 40 if profit["margin_pct"] >= 25 else 25 if profit["margin_pct"] >= 15 else 10 if profit["margin_pct"] >= 0 else 0
    turnover_component = 0 if days_of_stock is None else 40 if days_of_stock < 30 else 20 if days_of_stock <= 90 else 0
    total_budget = money(row, "total_budget", "total_budget_mxn", "total_budget_brl")
    if total_budget > 0 and batch_capital > 0:
        budget_ratio = round(batch_capital / total_budget * 100, 1)
        budget_component = 20 if budget_ratio <= 20 else 10 if budget_ratio <= 50 else 0
    else:
        budget_ratio = None
        budget_component = 0
    capital_score = margin_component + turnover_component + budget_component
    if market_score >= 60 and seller_fit >= 60 and capital_score >= 60:
        entry_difficulty = "低"
    elif market_score < 40 or seller_fit < 40 or capital_score < 40:
        entry_difficulty = "高"
    else:
        entry_difficulty = "中"
    if budget_ratio is not None and budget_ratio > 50:
        warnings.append(f"资金被单一商品过度占用（首批资金占总预算 {budget_ratio}%）")

    downgrade_reasons = []
    if block_reasons:
        verdict = "NO-GO"
    elif profit["net_per_unit"] < 0:
        verdict = "NO-GO"
        block_reasons.append("负毛利")
    elif total >= 75 and supply == "ready" and demand in ("medium", "strong"):
        verdict = "GO"
        if seller_fit < 50:
            verdict = "CONDITIONAL"
            downgrade_reasons.append("市场机会高但卖家适配低，不能直接 GO")
        if capital_score < 30:
            verdict = "CONDITIONAL"
            downgrade_reasons.append("资金效率低，不能直接 GO")
    elif total >= 50:
        verdict = "CONDITIONAL"
    else:
        verdict = "NO-GO"

    return {
        "candidate": row.get("candidate", ""),
        "category": row.get("category", ""),
        "market_code": market_code,
        "currency": currency,
        "price": price,
        "profit": profit,
        "scores": {
            "demand": demand_score,
            "competition": comp_score,
            "profit": prof_score,
            "supply": supply_score,
            "compliance": comp_risk_score,
        },
        "total": total,
        "risk_adjusted": risk_adjusted,
        "confidence": confidence,
        "market_score": market_score,
        "seller_fit": seller_fit,
        "capital_score": capital_score,
        "entry_difficulty": entry_difficulty,
        "downgrade_reasons": downgrade_reasons,
        "batch_capital": batch_capital,
        "budget_ratio": budget_ratio,
        "days_of_stock": days_of_stock,
        "entry_strategy": (row.get("entry_strategy") or "").strip(),
        "failure_cause": (row.get("failure_cause") or "").strip(),
        "underestimated_cost": (row.get("underestimated_cost") or "").strip(),
        "loss_link": (row.get("loss_link") or "").strip(),
        "preverify_risk": (row.get("preverify_risk") or "").strip(),
        "verification_cost": (row.get("verification_cost") or row.get("verification_cost_mxn") or row.get("verification_cost_brl") or "").strip(),
        "verification_days": (row.get("verification_days") or "").strip(),
        "verification_goal": (row.get("verification_goal") or "").strip(),
        "stop_loss": (row.get("stop_loss") or "").strip(),
        "next_step_after_success": (row.get("next_step_after_success") or "").strip(),
        "diff_cost": (row.get("diff_cost") or row.get("diff_cost_mxn") or row.get("diff_cost_brl") or "").strip(),
        "diff_copy_ease": (row.get("diff_copy_ease") or "").strip(),
        "key_risks": key_risks,
        "critical_missing": critical_missing,
        "verdict": verdict,
        "block_reasons": block_reasons,
        "gaps": gaps,
        "warnings": warnings,
    }


def render(results):
    lines = ["# 选品短名单（内部比较结果，不是销量预测）", ""]
    order = {"GO": 0, "CONDITIONAL": 1, "NO-GO": 2}
    for item in sorted(results, key=lambda r: (order[r["verdict"]], -r["risk_adjusted"], -r["total"])):
        scores = item["scores"]
        lines.append(f"## {item['candidate']} — {item['verdict']}（原始分 {item['total']} 分，风险调整分 {item['risk_adjusted']} 分，置信度 {item['confidence']}）")
        lines.append(f"- 双重判断：市场机会分 {item['market_score']} 分，卖家适配分 {item['seller_fit']} 分，资金效率分 {item['capital_score']} 分，进入难度 {item['entry_difficulty']}（三项为解释性指标，不计入原始分）")
        if item.get("budget_ratio") is not None:
            lines.append(f"- 资金占用：首批资金 {item['batch_capital']} {item['currency']}，占总预算 {item['budget_ratio']}%，库存天数 {item['days_of_stock']} 天")
        if item.get("downgrade_reasons"):
            lines.append("- 降级原因：" + "、".join(item["downgrade_reasons"]))
        if item.get("entry_strategy"):
            lines.append(f"- 竞争进入策略：{item['entry_strategy']}")
        if item.get("failure_cause"):
            lines.append(f"- 失败五问：最可能失败的原因 {item['failure_cause']}；最容易被低估的成本 {item['underestimated_cost']}；最可能导致亏损的环节 {item['loss_link']}；最值得提前验证的风险 {item['preverify_risk']}；最大可能损失参考为首批资金占用 {item['batch_capital']} {item['currency']}（滞销且无法清仓时）")
        if item.get("verification_goal"):
            lines.append(f"- 低成本验证方案：最低验证成本 {item['verification_cost']} {item['currency']}，周期 {item['verification_days']} 天，目标 {item['verification_goal']}，止损条件 {item['stop_loss']}，成功后下一步 {item['next_step_after_success']}")
        if item.get("diff_cost"):
            lines.append(f"- 差异化可执行性：差异化成本 {item['diff_cost']} {item['currency']}，复制难度 {item['diff_copy_ease']}")
        lines.append(f"- 市场：{item['market_code']}，品类：{item['category']}，售价：{item['price']} {item['currency']}")
        lines.append(
            "- 分项：需求 {} 分，竞争 {} 分，利润 {} 分，供应 {} 分，合规 {} 分".format(
                scores["demand"], scores["competition"], scores["profit"],
                scores["supply"], scores["compliance"],
            )
        )
        profit = item["profit"]
        lines.append(
            "- 利润：单件净利 {} {}，毛利率 {}%，盈亏平衡售价 {} {}".format(
                profit["net_per_unit"], item["currency"], profit["margin_pct"],
                profit["breakeven_price"], item["currency"],
            )
        )
        if item["block_reasons"]:
            lines.append("- 门禁触发：" + "、".join(item["block_reasons"]))
        if item.get("key_risks"):
            lines.append("- 关键风险清单：" + "、".join(item["key_risks"]))
        if item.get("critical_missing"):
            lines.append("- 关键数据缺失警告：" + "、".join(item["critical_missing"]) + "（原始分已封顶 74 分，不能出 GO）")
        if item["gaps"]:
            lines.append("- 缺口：" + "、".join(item["gaps"]))
        if item.get("warnings"):
            lines.append("- 警告：" + "、".join(item["warnings"]))
        lines.append("")
    lines.append("声明：本短名单是内部比较结果，不是销量预测，不是平台审核结果。所有“待核实”项在上架前必须核实。")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score product candidates.")
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--output", required=True, help="Output markdown path")
    parser.add_argument("--json", default=None, help="Optional JSON output path for the scored results")
    args = parser.parse_args(argv)
    with open(args.input, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        parser.error("input CSV has no rows")
    results = [score_row(row) for row in rows]
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(render(results))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(results, handle, ensure_ascii=False, indent=2)
    for item in results:
        print(f"{item['candidate']}: {item['verdict']} (原始分 {item['total']} 分，风险调整分 {item['risk_adjusted']} 分，置信度 {item['confidence']}，市场机会 {item['market_score']} 分，卖家适配 {item['seller_fit']} 分，资金效率 {item['capital_score']} 分)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

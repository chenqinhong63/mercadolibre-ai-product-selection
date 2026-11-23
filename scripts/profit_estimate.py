#!/usr/bin/env python3
"""Profit estimate for one Mercado Libre candidate (MLM/MXN or MLB/BRL).

Ported exactly from the V2.1 skill script
``~/workspace/custom-skills/mercado-libre-product-selection/scripts/profit_estimate.py``.

All inputs come from the user or a visible page.
Market/currency: MLM prices are MXN, MLB prices are BRL;
pass --market-code MLB for Brazil (default MLM). Never mix currencies. This script invents
no fee, price or return rate. Run it with real numbers only.
All fee/tax percentages are INPUTS supplied by the caller (default 0.0);
no commission, MSI or return rate is hard-coded here, because no
Mercado Libre commission % was verified directly as of 2026-11-23.
Outputs are simulations based on user-supplied assumptions:
"模拟结果，不代表实际费用".

Formula:
  platform_fee = price * platform_fee_pct / 100
  return_cost = price * return_rate_pct / 100
  ad_cost = price * ad_pct / 100
  installment_cost = price * installment_pct / 100
  net = price - platform_fee - cost - shipping - other_cost
        - return_cost - ad_cost - installment_cost
  margin_pct = net / price * 100 when price > 0
  breakeven_price solves net = 0 for price:
    price * (1 - fee_pct/100 - return_pct/100
             - ad_pct/100 - installment_pct/100) = cost + shipping + other
Ad and installment percentages are optional and default to 0.
They must come from the user or a visible page, never invented.
"""
import argparse
import sys


MARKETS = {"MLM": "MXN", "MLB": "BRL"}


def currency_for(market_code):
    code = (market_code or "MLM").strip().upper()
    if code not in MARKETS:
        raise ValueError(f"unknown market_code {market_code!r}; use MLM or MLB")
    return MARKETS[code]


def estimate(price, cost, shipping, fee_pct, other, return_pct,
             ad_pct=0.0, installment_pct=0.0, market_code="MLM"):
    fee = price * fee_pct / 100.0
    return_cost = price * return_pct / 100.0
    ad_cost = price * ad_pct / 100.0
    installment_cost = price * installment_pct / 100.0
    net = price - fee - cost - shipping - other - return_cost - ad_cost - installment_cost
    margin = (net / price * 100.0) if price > 0 else 0.0
    denom = 1.0 - fee_pct / 100.0 - return_pct / 100.0 - ad_pct / 100.0 - installment_pct / 100.0
    breakeven = (cost + shipping + other) / denom if denom > 0 else float("inf")
    return {
        "market_code": (market_code or "MLM").strip().upper(),
        "currency": currency_for(market_code),
        "platform_fee": round(fee, 2),
        "return_cost": round(return_cost, 2),
        "ad_cost": round(ad_cost, 2),
        "installment_cost": round(installment_cost, 2),
        "net_per_unit": round(net, 2),
        "margin_pct": round(margin, 2),
        "breakeven_price": round(breakeven, 2) if breakeven != float("inf") else None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Estimate profit for one candidate.")
    parser.add_argument("--price", type=float, required=True, help="Selling price (MLM: MXN, MLB: BRL)")
    parser.add_argument("--cost", type=float, required=True, help="Purchase cost (MLM: MXN, MLB: BRL)")
    parser.add_argument("--shipping", type=float, default=0.0, help="Shipping (MLM: MXN, MLB: BRL)")
    parser.add_argument("--fee-pct", type=float, default=0.0, help="Platform fee percent")
    parser.add_argument("--other", type=float, default=0.0, help="Other cost per unit (MLM: MXN, MLB: BRL)")
    parser.add_argument("--return-pct", type=float, default=0.0, help="Return rate percent")
    parser.add_argument("--ad-pct", type=float, default=0.0, help="Ad cost percent, user-provided")
    parser.add_argument("--installment-pct", type=float, default=0.0, help="Installment cost percent, user-provided (MSI for MLM, parcelamento for MLB)")
    parser.add_argument("--market-code", default="MLM", help="Market code MLM (Mexico, MXN) or MLB (Brazil, BRL)")
    args = parser.parse_args(argv)
    if args.price <= 0:
        parser.error("price must be greater than 0")
    result = estimate(args.price, args.cost, args.shipping, args.fee_pct, args.other, args.return_pct, args.ad_pct, args.installment_pct, market_code=args.market_code)
    for key, value in result.items():
        print(f"{key}: {value}")
    print("模拟结果，不代表实际费用")
    return 0


if __name__ == "__main__":
    sys.exit(main())

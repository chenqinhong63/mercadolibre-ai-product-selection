#!/usr/bin/env python3
"""Operating profit breakdown and reverse derivation (V2.1).

Ported exactly from the V2.1 skill script
``~/workspace/custom-skills/mercado-libre-product-selection/scripts/operating_profit.py``.

Breakdown, all amounts in the market currency (MLM: MXN, MLB: BRL) unless a percent is named:
  gross = price - procurement - first_leg - import_cost
  platform_fee = price * fee_pct / 100
  tax = price * tax_pct / 100
  ad = price * ad_pct / 100
  installment = price * installment_pct / 100
  return_cost = price * return_pct / 100
  contribution = gross - local_shipping - platform_fee - tax
                 - warehousing - packaging - ad - installment
  net = contribution - return_cost - after_sales
  upfront_per_unit = procurement + first_leg + import_cost + packaging
  batch_cash_outflow = moq * upfront_per_unit, when moq is given.
Reverse derivation, given target price and target margin:
  desired_net = target_price * target_margin_pct / 100
  max_procurement = target_price - platform_fee - tax - local_shipping
    - warehousing - packaging - ad - installment - return_cost
    - after_sales - desired_net - first_leg - import_cost
  min_price = (procurement + first_leg + import_cost + local_shipping
    + warehousing + packaging + after_sales) / (1 - fee_pct/100
    - tax_pct/100 - ad_pct/100 - installment_pct/100
    - return_pct/100 - target_margin_pct/100)
  max_shipping = target_price - platform_fee - tax - warehousing
    - packaging - ad - installment - return_cost - after_sales
    - desired_net - procurement - first_leg - import_cost
  max_ad_amount = target_price - platform_fee - tax - local_shipping
    - warehousing - packaging - installment - return_cost
    - after_sales - desired_net - procurement - first_leg - import_cost
  max_moq = floor(total_budget / upfront_per_unit), when both are given.
If supplier quote exceeds max_procurement, the script prints exactly:
  当前采购条件不符合目标利润要求。
No cost is invented; every percent and amount comes from the user
or a visible page, and simulated results are labeled as simulations
in the calling output, not as real profit.
All fee/tax percentages are INPUTS (default 0.0); no commission or
tax rate is hard-coded here, because no Mercado Libre commission %
was verified directly as of 2026-11-23.
"""
import argparse
import math
import sys

MARKETS = {"MLM": "MXN", "MLB": "BRL"}


def currency_for(market_code):
    code = (market_code or "MLM").strip().upper()
    if code not in MARKETS:
        raise ValueError(f"unknown market_code {market_code!r}; use MLM or MLB")
    return MARKETS[code]


def pct(price, value):
    return price * value / 100.0


def breakdown(args):
    fee = pct(args.price, args.fee_pct)
    tax = pct(args.price, args.tax_pct)
    ad = pct(args.price, args.ad_pct)
    installment = pct(args.price, args.installment_pct)
    return_cost = pct(args.price, args.return_pct)
    gross = args.price - args.procurement - args.first_leg - args.import_cost
    contribution = (gross - args.local_shipping - fee - tax
                    - args.warehousing - args.packaging - ad - installment)
    net = contribution - return_cost - args.after_sales
    upfront = args.procurement + args.first_leg + args.import_cost + args.packaging
    return {
        "market_code": (getattr(args, "market_code", None) or "MLM").strip().upper(),
        "currency": currency_for(getattr(args, "market_code", None) or "MLM"),
        "gross": round(gross, 2),
        "gross_margin_pct": round(gross / args.price * 100, 2) if args.price else 0.0,
        "platform_fee": round(fee, 2),
        "tax": round(tax, 2),
        "ad_cost": round(ad, 2),
        "installment_cost": round(installment, 2),
        "return_cost": round(return_cost, 2),
        "contribution": round(contribution, 2),
        "net": round(net, 2),
        "net_margin_pct": round(net / args.price * 100, 2) if args.price else 0.0,
        "upfront_per_unit": round(upfront, 2),
        "batch_cash_outflow": round(args.moq * upfront, 2) if args.moq else None,
    }


def reverse(args):
    price = args.target_price if args.target_price is not None else args.price
    if price is None or price <= 0:
        raise ValueError("reverse mode needs a target price")
    fee = pct(price, args.fee_pct)
    tax = pct(price, args.tax_pct)
    ad = pct(price, args.ad_pct)
    installment = pct(price, args.installment_pct)
    return_cost = pct(price, args.return_pct)
    desired_net = price * args.target_margin_pct / 100.0
    max_procurement = (price - fee - tax - args.local_shipping - args.warehousing
                       - args.packaging - ad - installment - return_cost
                       - args.after_sales - desired_net - args.first_leg - args.import_cost)
    denom = (1 - args.fee_pct / 100.0 - args.tax_pct / 100.0 - args.ad_pct / 100.0
             - args.installment_pct / 100.0 - args.return_pct / 100.0 - args.target_margin_pct / 100.0)
    numerator = (args.procurement + args.first_leg + args.import_cost
                 + args.local_shipping + args.warehousing + args.packaging + args.after_sales)
    min_price = numerator / denom if denom > 0 else None
    max_shipping = (price - fee - tax - args.warehousing - args.packaging - ad
                    - installment - return_cost - args.after_sales - desired_net
                    - args.procurement - args.first_leg - args.import_cost)
    max_ad_amount = (price - fee - tax - args.local_shipping - args.warehousing
                     - args.packaging - installment - return_cost - args.after_sales
                     - desired_net - args.procurement - args.first_leg - args.import_cost)
    upfront = args.procurement + args.first_leg + args.import_cost + args.packaging
    max_moq = math.floor(args.total_budget / upfront) if args.total_budget and upfront > 0 else None
    return {
        "market_code": (getattr(args, "market_code", None) or "MLM").strip().upper(),
        "currency": currency_for(getattr(args, "market_code", None) or "MLM"),
        "max_procurement": round(max_procurement, 2),
        "min_price": round(min_price, 2) if min_price is not None else None,
        "max_shipping": round(max_shipping, 2),
        "max_ad_pct": round(max_ad_amount / price * 100, 2) if price else None,
        "max_moq": max_moq,
        "supplier_ok": (args.supplier_quote is None or args.supplier_quote <= max_procurement),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Operating profit breakdown and reverse derivation.")
    parser.add_argument("--price", type=float, help="Selling price (MLM: MXN, MLB: BRL)")
    parser.add_argument("--procurement", type=float, default=0.0)
    parser.add_argument("--first-leg", type=float, default=0.0, dest="first_leg")
    parser.add_argument("--import-cost", type=float, default=0.0)
    parser.add_argument("--local-shipping", type=float, default=0.0)
    parser.add_argument("--fee-pct", type=float, default=0.0)
    parser.add_argument("--tax-pct", type=float, default=0.0)
    parser.add_argument("--warehousing", type=float, default=0.0)
    parser.add_argument("--packaging", type=float, default=0.0)
    parser.add_argument("--ad-pct", type=float, default=0.0)
    parser.add_argument("--installment-pct", type=float, default=0.0)
    parser.add_argument("--return-pct", type=float, default=0.0)
    parser.add_argument("--after-sales", type=float, default=0.0)
    parser.add_argument("--moq", type=int, default=0)
    parser.add_argument("--target-price", type=float, help="Target price for reverse mode")
    parser.add_argument("--target-margin-pct", type=float, default=25.0)
    parser.add_argument("--supplier-quote", type=float, help="Supplier quote to check against max procurement")
    parser.add_argument("--total-budget", type=float, default=0.0)
    parser.add_argument("--market-code", default="MLM", help="Market code MLM (Mexico, MXN) or MLB (Brazil, BRL)")
    args = parser.parse_args(argv)

    cur = currency_for(args.market_code)
    if args.price:
        result = breakdown(args)
        print(f"商品毛利：{result['gross']} {cur}，毛利率：{result['gross_margin_pct']}%")
        print(f"经营贡献利润：{result['contribution']} {cur}")
        print(f"预计净利润：{result['net']} {cur}，净利率：{result['net_margin_pct']}%")
        print(f"单件前期现金流出：{result['upfront_per_unit']} {cur}")
        if result["batch_cash_outflow"] is not None:
            print(f"首批现金流出：{result['batch_cash_outflow']} {cur}")
    if args.target_price is not None or args.price:
        result = reverse(args)
        print(f"最高可接受采购成本：{result['max_procurement']} {cur}")
        print(f"最低可接受售价：{result['min_price']} {cur}")
        print(f"最高可接受物流费用：{result['max_shipping']} {cur}")
        print(f"最高可接受广告成本比例：{result['max_ad_pct']}%")
        if result["max_moq"] is not None:
            print(f"最高可接受起订量：{result['max_moq']} 件")
        if args.supplier_quote is not None and not result["supplier_ok"]:
            print("当前采购条件不符合目标利润要求。")
    print("模拟结果，不代表实际费用")
    return 0


if __name__ == "__main__":
    sys.exit(main())

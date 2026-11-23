---
name: ml-product-opportunity-scoring
description: Score Mercado Libre Mexico (MLM) or Mercado Livre Brazil (MLB) product candidates 0–100 with GO / CONDITIONAL / NO-GO verdicts using the V2.1 rubric and score_candidate.py — reads Skills 1–5 outputs plus user cost, supply, brand and risk inputs, no direct data calls. Use when the user asks to score, compare or shortlist candidates, or decide whether a product is worth testing.
version: 1.0.0
license: MIT
---

# ml-product-opportunity-scoring — 产品机会评分

## 目的

给每个候选品打一个 0–100 分，并出 GO / CONDITIONAL / NO-GO 结论。评分规则以用户已有的美客多选品 Skill V2.1 为准；AronLEEdev 的 `score.mjs` 只提供实现形状（分段 band、确定性脚本、null 过滤），数值一律按 V2.1 重标定，**不使用 Aron 的 Amazon 数值**（$20、$5,000、≤500 评论、≤2 lb 等一律不适用）。

**GO 的意思只是“值得进入下一轮人工核查和小批量验证”，不是“可以直接发布”，更不是“可以直接大量备货”。**

## 市场参数（market_code，第一位参数）

- `market_code` 必填，二选一：`MLM` = Mercado Libre México（墨西哥站，货币 MXN）或 `MLB` = Mercado Livre Brasil（巴西站，货币 BRL）。
- **如果 `market_code` 缺失，先问用户，不默认 MLM。** 绝不以“用户没说就按墨西哥”静默处理；用户明确要求巴西时，一律按 MLB 走。
- 货币：MLM 一律 MXN，MLB 一律 BRL。**绝不混用两种货币，绝不用自编汇率换算。** 跨市场对比时，两种货币并列呈现，换算写“待核实”，除非用户提供了汇率 + 日期。
- 评分规则：**V2.1 评分规则同时适用于 MLM 和 MLB**，除非用户明确要求重新校准。不要自编巴西专属分档 / 阈值；墨西哥的阈值、公式、verdict 规则一律不变，巴西沿用同一套。
- 关键词语言：MLM 只用西语，MLB 只用葡语，绝不用中文关键词。

## 输入

本 Skill **不直接调大麦 MCP**，只读上游输出和用户提供的数据。

| 输入来源 | 内容 |
|---|---|
| `market_code` | 必填：`MLM` 或 `MLB`。缺失时先问用户，不默认 MLM。 |
| Skill 1（ml-market-research） | 市场 / 类目结论、需求信号及证据等级 |
| Skill 2（ml-product-discovery） | 候选品、售价（MLM 为 MXN，MLB 为 BRL）、价格带 |
| Skill 3（ml-competitor-analysis） | 同款卖家数、头部卖家结构、价格带 |
| Skill 4（ml-sales-trend-analysis） | 销量趋势结论（趋势方向，不直接当销量数字用） |
| Skill 5（ml-review-intelligence） | 主要痛点、好评、差异化角度、宣称核对结果 |
| Skill 7（ml-profit-analysis） | 单件净利、毛利率、盈亏平衡售价、三层利润（利润分以 Skill 7 的毛利率为准），金额均带市场货币（MXN / BRL） |
| 用户提供（必填） | 采购成本、运费、平台费率、其他单件成本、退货率；品牌状态（四选一）；供应状态；起订量、补货周期、总预算（带市场货币）；六类风险等级；差异化方案；四项卖家适配自评 |
| 用户提供（可选） | 广告占比、分期占比、预期日单量、目标利润率 |

**缺失处理**：关键数据缺失时不编数，先问用户，或按“未知数据上限”处理（见下）。品牌状态只能四选一：通用无品牌 / 自有品牌 / 有书面授权 / 未授权品牌 / 未知——未知按高风险处理，不按无风险处理。

## 脚本

用 `scripts/score_candidate.py`（V2.1 逻辑，从 `~/workspace/custom-skills/mercado-libre-product-selection/scripts/score_candidate.py` 移植，输入 CSV 列名与之一致）。**算术一律交给脚本，不要心算**；脚本输出原始分、风险调整分、置信度、市场机会分、卖家适配分、资金效率分六项。

```text
python3 scripts/score_candidate.py --input candidates.csv --output shortlist.md
```

CSV 列（与 V2.1 脚本一致）：`candidate, category, price_mxn, cost_mxn, shipping_mxn, platform_fee_pct, other_cost_mxn, return_rate_pct, ad_pct, installment_pct, demand_signal, competitor_count, supply_status, brand_status, restricted, ip_risk, demand_source, differentiation, risk_demand, risk_competition, risk_profit, risk_supply, risk_inventory, risk_compliance`，另加 V2.1 列：`budget_fit, supply_advantage, operating_capability, logistics_capability, moq, total_budget_mxn, expected_daily_orders, entry_strategy, failure_cause, underestimated_cost, loss_link, preverify_risk, verification_cost_mxn, verification_days, verification_goal, stop_loss, next_step_after_success, diff_cost_mxn, diff_copy_ease`。

**货币列名（MLM / MLB 对照，同一行只用一套，绝不混用）**：墨西哥用 `price_mxn / cost_mxn / shipping_mxn / other_cost_mxn / total_budget_mxn / verification_cost_mxn / diff_cost_mxn`；巴西用对应的 `price_brl / cost_brl / shipping_brl / other_cost_brl / total_budget_brl / verification_cost_brl / diff_cost_brl`。同一候选品、同一计算里只用一套货币列，绝不在一行里同时出现 `_mxn` 和 `_brl` 列、绝不把 MXN 金额填进 `_brl` 列（反之亦然）。跑脚本前按脚本实际接受的列名核对；列名不符时停下说明，不手工拼一个分数代替脚本结果。

## 评分规则（100 分，内部比较尺度，不是平台排名）

**V2.1 评分规则同时适用于 MLM 和 MLB**，除非用户明确要求重新校准；不要自编巴西专属分档 / 阈值。以下阈值、公式、verdict 规则对两个市场完全相同。

| 维度 | 满分 | 计分 |
|---|---|---|
| 需求证据 | 25 | 强 25（站内多来源需求信号，如畅销区、多卖家在售、页面已售提示，来源已记录）；中 17（单一信号）；弱 9（只有创作者 / 短视频 / Linktree 热度，无站内信号）；无 0。 |
| 竞争结构 | 20 | 同款卖家 ≤5 家 20 分；6–15 家 14 分；16–30 家 8 分；>30 家 3 分；未知 0 分并写待核实。只看数量结构，不看“对手很弱”这类主观判断。 |
| 利润空间 | 20 | 毛利率 ≥40% 20 分；25%–40% 15 分；15%–25% 10 分；0%–15% 5 分；负毛利 0 分且直接 NO-GO。毛利率以 Skill 7 的 `profit_estimate.py` 公式为准。 |
| 供应与物流 | 15 | 已就绪 15（现货货源、起订量可接受、补货周期明确、能提供进货凭证）；部分就绪 8；未就绪 0。 |
| 合规基础 | 20 | 低风险 20（通用 / 自有品牌，无受限宣称，无需特殊认证或认证齐全）；中风险 10（有授权但凭证待复核，或类目 / 认证有一项待核实）；高风险 0（品牌状态未知、受限类目待核实、宣称依据不足）。 |

### 硬性门禁（合规门，触发即 NO-GO，不看总分）

- 未授权品牌（`brand_status = unauthorized_brand`）→ BLOCK。
- 受限类目无认证（`restricted = yes`）→ BLOCK。
- 知识产权高风险（`ip_risk = high`）→ BLOCK。
- 负毛利 → NO-GO。
- 门禁触发时 verdict 直接为 NO-GO，风险调整分再高也不能改回 GO。

### Verdict 规则

- BLOCK 或负毛利：NO-GO。
- 总分 ≥75，且供应已就绪、需求至少中等（medium / strong）：GO。
- 总分 50–74：CONDITIONAL。
- 总分 <50：NO-GO。

### 未知数据上限与警告

- 关键数据缺失时，原始分最高计 74 分，不能出 GO。关键数据：竞争卖家数、需求来源、差异点、风险等级。
- 以下缺失项出现时，输出里必须有警告，不能只扣分不提醒：竞争数未知、需求来源未知、差异点未填、风险等级未填、品牌状态未知。

### 风险调整分与置信度

- 风险调整分 = 原始分 − 风险扣分。六类风险（需求、竞争、利润、供应、库存、合规）中高风险每项扣 4 分，中风险每项扣 2 分，低风险扣 0 分，扣分上限 20 分；风险调整分低于 0 时按 0 计。
- 置信度：高 = 关键数据齐全且高风险 0 项；中 = 缺失 1–2 项，或高风险 1 项；低 = 缺失 3 项及以上，或高风险 2 项及以上。
- 关键风险清单：所有高风险和中风险项单独列出，写清哪一类风险、为什么是这个等级、下一步怎么核实。
- 原始分、风险调整分、置信度必须分别输出，不能只输出一个总分。

### 新卖家规则

- 差异点为无（`differentiation = none`）时，竞争分最高计 8 分。
- 无法回答“这个品为什么适合一个新卖家”时，即使原始分达到 GO 线，也先判 CONDITIONAL，并把“新卖家进入理由不成立”写进关键风险清单。
- 差异化只是价格或一张主图时，复制风险判高。

### 双重判断与资金效率（解释性指标，不计入原始 100 分）

- 市场机会分（0–100）：需求分 ÷ 25 × 40 + 竞争分 ÷ 20 × 30 + 差异化分（强 30 / 中 20 / 弱 10 / 无或未填 0）。
- 卖家适配分（0–100）：预算适配、供应链优势、运营能力、物流和售后能力四项平均，强 100 / 中 60 / 弱 20 / 未评估 0；全部未评估时为 0 分并写缺口。
- 资金效率分（0–100）：毛利率占 40 分（≥25% 计 40，15%–25% 计 25，0%–15% 计 10，负数 0）；库存周转占 40 分（<30 天 40，30–90 天 20，>90 天或未知 0）；首批资金占总预算比例占 20 分（≤20% 计 20，≤50% 计 10，>50% 或未知 0）。
- 进入难度：三项都 ≥60 分为低，任一项 <40 分为高，其余为中。
- **降级规则**：原始 verdict 为 GO，但卖家适配 <50 分，或资金效率 <30 分时，先降为 CONDITIONAL，并写清降级原因。市场机会高但卖家适配低的品，不直接推荐 GO。
- 首批资金占总预算 >50% 时，明确提示资金被单一商品过度占用。

## 失败五问（每个候选品必须回答）

1. 最可能失败的原因是什么？
2. 最容易被低估的成本是什么？
3. 最可能导致亏损的环节是什么？
4. 最值得提前验证的风险是什么？
5. 如果失败，最大可能损失是什么？（参考首批资金占用；滞销且无法清仓时按首批资金占用计，写清这是参考值，不是实际损失预测。）

## 低成本验证方案（每个候选品必须写）

先验证再备货，优先低成本验证：先验证供应商样品、先确认真实采购成本、先测试物流方案、先确认类目限制、先小批量测试、先测试不同规格、先验证买家需求、先确认差异化是否成立。方案必须写清：最低验证成本（带市场货币：MLM 为 MXN，MLB 为 BRL）、验证周期（天）、验证目标、验证失败的止损条件、验证成功后的下一步。验证结果不好，verdict 改回 CONDITIONAL 或 NO-GO，不要直接备货。

## 分析步骤

1. 收齐上游输出（Skills 1–5、7）和用户输入；缺关键数据时先问，或按未知数据上限处理并写警告。
2. 过合规门：触发 BLOCK 直接判 NO-GO，不再算分。
3. 把每个候选品写成一行 CSV，跑 `scripts/score_candidate.py`，取脚本输出的六项分数和 verdict。
4. 人工复核一遍分数背后的证据等级：推测不能打满分；弱信号不能当强需求；缺失项是否都写了警告。
5. 回答失败五问，写低成本验证方案，写一句话核心经营判断（“这个商品值得做 / 不值得做的核心原因是什么？”——不能只重复分数）。
6. 按 verdict、风险调整分、资金效率排序出短名单；置信度低的品即使原始分高，也排在置信度高的品后面，并写清原因。
7. 拒绝清单单独列出，写清是哪个门禁触发的，不要只写“不建议”。

## 输出模板（每个候选品 15 项，只写一次，不重复）

```markdown
# 选品短名单（内部比较结果，不是销量预测）

- 市场：<Mercado Libre México（MLM）/ Mercado Livre Brasil（MLB）>，market_code <MLM / MLB>，货币 <MXN / BRL>。跨市场对比时，MLM 金额（MXN）与 MLB 金额（BRL）并列呈现，换算写“待核实”，除非用户提供了汇率 + 日期；绝不用自编汇率换算。
- 排序：按 verdict、风险调整分、资金效率排序，GO 在前，NO-GO 在后并写清原因。

## <商品名> — <GO / CONDITIONAL / NO-GO>（原始分 <N> 分，风险调整分 <N> 分，置信度 <高 / 中 / 低>）

1. 商品基本信息：<品名、品类、关键规格、售价 <N> <MXN / BRL>>
2. 市场机会判断：<结论>（市场机会分 <N> 分）
3. 卖家适配判断：<结论>（卖家适配分 <N> 分，进入难度 <低 / 中 / 高>，主要经营障碍 <…>）
4. 需求证据：<信号及来源，证据等级>
5. 竞争结构：<同款卖家数、价格带、头部结构>
6. 竞争进入策略：<凭什么获得订单，具体打法>
7. 差异化方案：<方案；可执行性：成本 <N> <MXN / BRL>、物流影响 <…>、买家是否真的需要 <…>、复制难度 <…>、能否支持更高售价 <…>>
8. 利润测算：<商品毛利、经营贡献利润、预计净利润、现金流，来源 Skill 7；金额带市场货币>
9. 利润反向推导：<最高可接受采购成本、最低可接受售价、最高可接受物流和广告成本、最高可接受起订量；供应商超标时写“当前采购条件不符合目标利润要求。”>
10. 资金占用与库存风险：<资金效率分 <N> 分，首批资金占总预算 <N>%，库存天数 <N 天 / 待核实>>
11. 合规与供应风险：<品牌状态、受限 / 认证、供应状态>
12. 最可能失败的原因：<失败五问逐条回答>
13. 低成本验证方案：<最低验证成本 <N> <MXN / BRL>，周期 <N 天>，目标 <…>，止损条件 <…>，成功后下一步 <…>>
14. 最终建议：<GO / CONDITIONAL / NO-GO>（GO 只表示值得进入下一轮人工核查和小批量验证）
15. 下一步行动：<1–3 个最优先的核查动作>

- 一句话核心经营判断：<这个商品值得做 / 不值得做的核心原因>
- 关键风险清单：<高 / 中风险逐项：类别、原因、下一步核实方法>
- 关键数据缺失警告：<如有，逐项列出>
- 门禁触发：<如有，写清触发项；无则写“无”>

## 拒绝清单

- <商品名>：<触发的门禁或 NO-GO 原因>

声明：本短名单是内部比较结果，不是销量预测，不是平台审核结果。所有“待核实”项在上架前必须核实。
```

## 错误处理

| 情况 | 做法 |
|---|---|
| 上游输出缺失（如无 Skill 3 竞争数据） | 竞争卖家数按未知处理（竞争分 0 分，原始分封顶 74 分），写警告，不编卖家数。 |
| 用户未提供成本 / 费率 | 利润分按缺失处理，不编费率；写清缺哪些数字才能算分，请用户提供。 |
| 脚本报错 / CSV 列缺失 | 停下，写清报错内容和缺失的列，不手工拼一个分数代替脚本结果。 |
| 两个上游结论冲突（如 Skill 1 说需求强、Skill 4 说趋势下行） | 两边都写出来，写清冲突点，需求分按较弱的一方就低打，并写需要人工复核。 |
| 候选品触发 BLOCK 但总分高 | verdict 仍为 NO-GO，总分作废，写清门禁触发项。 |

## 证据与局限

- 证据等级（V2.1 五档）：已核实、页面可见、用户提供、待核实、推测。每个结论后面跟证据等级或待核实标记；推测不能用来给需求、利润或合规打满分。
- 禁止的转换：不把搜索排名写成销量，不把页面已售提示写成 30 天销量，不把创作者热度写成销量，不把供应商口头销量写成平台销量，不把一次大促的单日表现写成长期需求。
- 评分是内部比较尺度，不是平台排名，不预测销量、排名或平台通过。
- 费率、税率、物流费以用户提供或官方来源核实为准；本 Skill 不填未经核实的费率数字。**巴西站（MLB）费率 / 税费一律待核实**：不要把墨西哥的 ISR / IVA 代扣（有 RFC：ISR 2.5%、IVA 8%；无 RFC：ISR 20%、IVA 16%）、MXN 费用或 MSI 分期照搬到巴西，也不要自编任何巴西佣金 / 税率。

## 输入 / 输出契约（供串联）

- 输入：`market_code`（必填，`MLM` 或 `MLB`；缺失时先问用户，不默认 MLM）+ Skills 1–5 的输出 + Skill 7 的利润结果 + 用户成本 / 供应 / 品牌 / 风险输入（见“输入”一节）。所有金额带市场货币（MLM 为 MXN，MLB 为 BRL），绝不混用。
- 输出：上节模板的短名单 Markdown（每个候选品 15 项 + 一句话判断 + 关键风险清单 + 拒绝清单）。
- 上游：Skills 1–5、7；下游：Skill 8（ml-market-report-generator）读取本输出的六项分数、verdict、失败五问和验证方案。**不直接调 MCP。**

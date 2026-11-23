# 发现示例（巴西站 MLB）：可调跳绳（corda para pular）

> 示例数据 — 虚构/演示用，不是真实市场数据。所有数字均为教学示例，不代表任何真实商品的销量、价格或利润。

## 说明

- 本文件演示一次巴西站（MLB）**模式 B（发现模式）**的完整走法：发现简报 → 大麦数据 MCP 调用 → 候选表 → 硬筛选淘汰。与墨西哥示例（`discovery-example.md`，MLM/MXN/西语）结构相同，**市场、语言、货币全部不同，不得混用**。
- **本次示例没有做任何真实 MCP 调用。** 下面列出的调用、参数、返回条数、候选 listing 全部是为教学编造的示例，不代表真实市场情况。
- 真实运行时：先调 `get_my_quota_status`（免费）确认剩余额度，再调付费工具；每次调用记录工具名、参数、调用时间、返回条数、调用后剩余额度。

## 1. 发现简报（示例输入）

以下全部是**示例输入**，不是用户真实给出的条件，也不是市场事实：

| 简报项 | 示例输入 |
|---|---|
| 目标市场 | 巴西站 MLB（示例） |
| 目标品类 | Esportes e Fitness（示例） |
| 葡语关键词 | `corda para pular`（示例；MLB 关键词只支持葡语，不支持中文关键词，也不支持西语关键词） |
| 预算（总预算） | 50,000 BRL（示例） |
| 目标售价 | 99–199 BRL（示例） |
| 目标净利率 | ≥ 20%（示例） |
| 供应链条件 | 通用无品牌、可小批量起订（示例假设） |
| 物流方式 | 直发 + Mercado Envios（示例假设） |
| 目标消费者 | 居家健身的成年人（示例） |
| 希望寻找的商品类型 | 可调长度跳绳及配件（示例） |

硬筛选条件（不达标直接淘汰，不进短名单）：售价超出 99–199 BRL；通用无品牌以外的品牌状态且无书面授权；基准情景净利率 < 20%。

**语言检查（MLB 必做）：** 关键词若为中文（如“跳绳”）或西语（如 `cuerda para saltar`），必须拒绝并请用户改成葡语；本示例的 `corda para pular` 为葡语，通过。

**货币检查（MLB 必做）：** 本示例所有金额均为 BRL；不得出现 MXN，不得按任何汇率把 BRL 换算成 MXN，跨市场对比时两币种并列、换算标待核实。

## 2. 本次示例会调的大麦数据 MCP 调用

调用顺序按评估报告 §5.3（Skill 2：产品发现）。参数名按大麦连接器文档与评估报告，`category_id` 须用 `search_categories` 的真实返回值替换，示例里的 `MLB0000` 是占位符。

### 第 0 步：查剩余额度（免费）

```text
python3 ~/workspace/custom-connectors/custom.damaishuju/bin/client.py call-tool \
  --name get_my_quota_status \
  --arguments-file ~/workspace/custom-connectors/custom.damaishuju/bin/empty.json
```

- 目的：付费调用前确认 `available_points` 是否足够。2026-11-23 实测该账号剩 50 点、无套餐（`plan_code` / `plan_name` 均为 null）；单次调用扣几分工具说明未写，真实运行时以调用前后配额差为准。
- 本示例未真实调用，剩余额度未知，写为待核实。

### 第 1 步：查类目（免费）

```json
{
  "tool": "search_categories",
  "arguments": {
    "market_code": "MLB",
    "query": "corda para pular"
  }
}
```

- 目的：拿到 `category_id`，再去查商品快照。中文关键词不支持，须用葡语。
- 示例返回值（虚构）：`category_id = MLB0000`（占位符，真实运行时替换为实际返回值）。

### 第 2 步：查商品快照（付费，消耗点数）

```json
{
  "tool": "search_product_snapshots",
  "arguments": {
    "market_code": "MLB",
    "keyword": "corda para pular",
    "category_id": "MLB0000",
    "price_min": 99,
    "price_max": 199,
    "sales_30d_min": 50,
    "sort_by": "sales_30d",
    "limit": 20
  }
}
```

- 目的：按近 30 天销量排序，取目标价位段内的候选 listing。
- 本示例假设该调用返回 20 条（虚构），下表只列其中 3 条进入候选池的示例 listing。

## 3. 候选表（全部虚构）

| sku_id（示例） | 葡语标题（示例） | 售价 BRL（示例） | sales_30d（示例） | 评分（示例） | 评论数（示例） | 处理 |
|---|---|---|---|---|---|---|
| MLB000000001 | Corda para pular ajustável 300 cm com manopla antiderrapante preta | 149 | 320 | 4.7 | 512 | 进入短名单，主候选；评分见下 §5 |
| MLB000000002 | Corda para pular com rolamentos 280 cm | 119 | 180 | 4.5 | 230 | 进入短名单，备选 |
| MLB000000003 | Corda para pular de PVC infantil 240 cm colorida | 79 | 95 | 4.3 | 87 | 淘汰，见下 |

## 4. 硬筛选淘汰说明（示例）

淘汰的品不进短名单，只留记录，写清触发的硬条件：

| sku_id（示例） | 淘汰原因（示例） |
|---|---|
| MLB000000003 | 售价 79 BRL，低于目标售价下限 99 BRL，硬筛选不通过；且为儿童用品，涉及儿童用品特殊宣称，合规须单独核实。 |
| MLB000000004（示例，未进候选表） | 品牌跳绳，品牌状态为未授权品牌，触发合规门禁 BLOCK，直接淘汰，不看销量。示例销量 410、评分 4.8 均不改变结论。 |
| MLB000000005（示例，未进候选表） | 售价 59 BRL，低于目标售价下限 99 BRL；按示例假设运费测算，运费占售价超 35%，利润不成立，淘汰。 |

## 5. 评分示例（MLB，与脚本输出逐数一致）

主候选 MLB000000001 的评分输入（示例，见 `tests/test_brazil.py` 的 `br_row()`）：售价 249 BRL、采购 68 BRL、运费 32 BRL、平台费率 13%（示例假设，**巴西真实费率待核实**，见 `references/profit-model.md`）、其他成本 32.15 BRL、退货率 5%、广告占比 5%、分期占比 0%；需求 medium、竞品 4 家、供应 ready、自有品牌、无限制、IP 风险 low、六维风险全部 low、预算/供应/运营/物流适配 strong、MOQ 200、日单 4、总预算 50,000 BRL。

脚本输出（`scripts/score_candidate.py`，示例数与测试用例一致）：

```text
Corda teste: GO (原始分 82 分，风险调整分 82 分，置信度 高，市场机会 87.2 分，卖家适配 100.0 分，资金效率 45 分)
- 利润：单件净利 59.58 BRL，毛利率 23.93%，盈亏平衡售价 171.62 BRL
```

利润层（`scripts/profit_estimate.py --market-code MLB`）：净利 59.58 BRL/件，净利率 23.93%，保本价 171.62 BRL。

**注意：** 13% 费率只是示例假设，不是巴西官方费率；真实费率须按 `references/ml-fee-sources.md` 巴西节核实后填入，未核实前不得把本示例的利润结论当作真实结论。

## 6. 下一步（示例流程）

1. 对 MLB000000001、MLB000000002 按模式 A 全套检查：快筛 → 需求 → 竞争 → 新卖家 → 利润压力 → 合规 → 库存 → 评分 → 短名单。跳过任何一步都不得出 GO。
2. 巴西评论为葡语：`scripts/review_themes.py --market-code MLB` 输出 `review_language: Portuguese`；主题词须用葡语词（如 qualidade / entrega / preço），不得用西语主题词。
3. 真实运行时：本示例里所有“示例数据”必须替换为真实 MCP 返回、页面可见或用户提供的数字，并按数据审计表记录来源、采集时间与证据等级；替换前不得把示例结论当作真实结论使用。
4. 巴西费用状态（2026-11-23）：佣金、运费表、税率、分期档位、退货窗口均未从官方页面核实，见 `references/ml-fee-sources.md` 巴西节与 `references/profit-model.md` 巴西节；已核实的只有 NF-e 开具要求（Mercado Pago 博客 2026-11-10）与 Product Ads CPC/Ad Rank（Mercado Ads KnowledgeHub），且 Product Ads 准入条件两处官方来源说法冲突，须实测核对。

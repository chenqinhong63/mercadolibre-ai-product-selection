# 发现示例：可调跳绳（cuerda para saltar）

> 示例数据 — 虚构/演示用，不是真实市场数据。所有数字均为教学示例，不代表任何真实商品的销量、价格或利润。

## 说明

- 本文件演示一次**模式 B（发现模式）**的完整走法：发现简报 → 大麦数据 MCP 调用 → 候选表 → 硬筛选淘汰。
- **本次示例没有做任何真实 MCP 调用。** 下面列出的调用、参数、返回条数、候选 listing 全部是为教学编造的示例，不代表真实市场情况。
- 真实运行时：先调 `get_my_quota_status`（免费）确认剩余额度，再调付费工具；每次调用记录工具名、参数、调用时间、返回条数、调用后剩余额度。

## 1. 发现简报（示例输入）

以下全部是**示例输入**，不是用户真实给出的条件，也不是市场事实：

| 简报项 | 示例输入 |
|---|---|
| 目标品类 | Deportes y Fitness（示例） |
| 西语关键词 | `cuerda para saltar`（示例；MLM 关键词只支持西语，不支持中文关键词） |
| 预算（总预算） | 50,000 MXN（示例） |
| 目标售价 | 150–300 MXN（示例） |
| 目标净利率 | ≥ 20%（示例） |
| 供应链条件 | 通用无品牌、可小批量起订（示例假设） |
| 物流方式 | 直发 + Mercado Envíos（示例假设） |
| 目标消费者 | 居家健身的成年人（示例） |
| 希望寻找的商品类型 | 可调长度跳绳及配件（示例） |

硬筛选条件（不达标直接淘汰，不进短名单）：售价超出 150–300 MXN；通用无品牌以外的品牌状态且无书面授权；基准情景净利率 < 20%。

## 2. 本次示例会调的大麦数据 MCP 调用

调用顺序按评估报告 §5.3（Skill 2：产品发现）。参数名按大麦连接器文档与评估报告，`category_id` 须用 `search_categories` 的真实返回值替换，示例里的 `MLM0000` 是占位符。

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
    "market_code": "MLM",
    "query": "cuerda para saltar"
  }
}
```

- 目的：拿到 `category_id`，再去查商品快照。中文关键词不支持，须用西语。
- 示例返回值（虚构）：`category_id = MLM0000`（占位符，真实运行时替换为实际返回值）。

### 第 2 步：查商品快照（付费，消耗点数）

```json
{
  "tool": "search_product_snapshots",
  "arguments": {
    "market_code": "MLM",
    "keyword": "cuerda para saltar",
    "category_id": "MLM0000",
    "price_min": 150,
    "price_max": 300,
    "sales_30d_min": 50,
    "sort_by": "sales_30d",
    "limit": 20
  }
}
```

- 目的：按近 30 天销量排序，取目标价位段内的候选 listing。
- 本示例假设该调用返回 20 条（虚构），下表只列其中 3 条进入候选池的示例 listing。

## 3. 候选表（全部虚构）

| sku_id（示例） | 西语标题（示例） | 售价 MXN（示例） | sales_30d（示例） | 评分（示例） | 评论数（示例） | 处理 |
|---|---|---|---|---|---|---|
| MLM000000001 | Cuerda para saltar ajustable 300 cm mango antideslizante negra | 249 | 320 | 4.7 | 512 | 进入短名单，主候选；见 `scoring-example.md` 与 `report-example.md` |
| MLM000000002 | Cuerda para saltar con rodamientos de bolas 280 cm | 199 | 180 | 4.5 | 230 | 进入短名单，备选 |
| MLM000000003 | Cuerda para saltar de PVC para niños 240 cm colores | 129 | 95 | 4.3 | 87 | 淘汰，见下 |

## 4. 硬筛选淘汰说明（示例）

淘汰的品不进短名单，只留记录，写清触发的硬条件：

| sku_id（示例） | 淘汰原因（示例） |
|---|---|
| MLM000000003 | 售价 129 MXN，低于目标售价下限 150 MXN，硬筛选不通过；且为儿童用品，涉及儿童用品特殊宣称，合规须单独核实。 |
| MLM000000004（示例，未进候选表） | 品牌跳绳，品牌状态为未授权品牌，触发合规门禁 BLOCK，直接淘汰，不看销量。示例销量 410、评分 4.8 均不改变结论。 |
| MLM000000005（示例，未进候选表） | 售价 89 MXN，低于目标售价下限 150 MXN；按示例假设运费测算，运费占售价超 35%，利润不成立，淘汰。 |

## 5. 下一步（示例流程）

1. 对 MLM000000001、MLM000000002 按模式 A 全套检查：快筛 → 需求 → 竞争 → 新卖家 → 利润压力 → 合规 → 库存 → 评分 → 短名单。跳过任何一步都不得出 GO。
2. `scoring-example.md` 以 MLM000000001 为例演示评分全过程；`report-example.md` 以同一候选品为例演示完整市场报告。
3. 真实运行时：本示例里所有“示例数据”必须替换为真实 MCP 返回、页面可见或用户提供的数字，并按数据审计表记录来源、采集时间与证据等级；替换前不得把示例结论当作真实结论使用。

---
name: ml-product-discovery
description: Discover candidate products on Mercado Libre Mexico (MLM) or Brazil / Mercado Livre (MLB) from a discovery brief (V2.1 Mode B): screen listings by hard filters with Damaishuju and output a candidate list plus a rejection list. Trigger phrases: "按我的条件帮我找品", "主动找符合条件的品", "product discovery", "发现模式", "帮我筛一批候选品".
version: 1.0.0
license: MIT
---

# Mercado Libre Product Discovery — 产品发现（V2.1 模式 B）

## Purpose

按用户给的**发现简报**主动找候选商品，输出一份候选清单 + 一份淘汰清单。

本 Skill 是 V2.1 模式 B（发现模式）的执行层：只负责“找出来、按硬条件筛掉
不合格的”，**不给 GO / CONDITIONAL / NO-GO 结论**——评分与 verdict 是
Skill 6 `ml-product-opportunity-scoring` 的事，利润测算是 Skill 7 的事。
本 Skill 也不做单个商品的深挖（那是 Skill 3 / 4 / 5 的事）。

适用范围：Mercado Libre 墨西哥站（`market_code` MLM）与巴西站 Mercado Livre
（`market_code` MLB）。**`market_code` 是必填参数**：MLM 或 MLB，二选一。
用户没给 `market_code` 时先问用户，**不默认 MLM、不默认墨西哥**；用户明确
要巴西时绝不按墨西哥跑。两站的数据、关键词语言、货币、费率互不通用。

## Input / Output Contract

| 方向 | 内容 |
|---|---|
| 消耗（输入） | 发现简报（见 §Inputs，含必填 `market_code` MLM 或 MLB）；可选：Skill 1 产出的品类概览（含 `category_id` 与检查清单） |
| 产出（输出） | 本文件 §输出模板 的候选清单 + 淘汰清单；下游 Skill 3 / 4 / 5 消费候选清单里的 `sku_id`，Skill 6 消费全部候选 + 淘汰理由 |
| 不产出 | GO / CONDITIONAL / NO-GO verdict、评分、利润测算、单个商品的竞品拆解 |

## Inputs

### 必填：发现简报（8 项硬筛选条件 + 市场代码）

| 简报项 | 说明 |
|---|---|
| 市场代码 `market_code` | MLM（墨西哥站）或 MLB（巴西站），**必填**；缺失先问用户，不默认 MLM |
| 目标品类 | 市场语言品类名：MLM 西语，MLB 葡语；中文名须先译成市场语言并由用户确认 |
| 预算 | 总预算（MLM 用 MXN，MLB 用 BRL），硬上限 |
| 目标利润率 | 例如 30%，硬筛选条件 |
| 目标售价 | 目标售价区间（MLM 用 MXN，MLB 用 BRL） |
| 供应链条件 | 现货 / 起订量 / 补货周期 / 能否提供进货凭证 |
| 物流方式 | 直发 / 海外仓 / Full 等用户已确认的方式 |
| 目标消费者 | 目标人群描述 |
| 希望寻找的商品类型 | 通用描述，不要只写品牌名 |

### 语言检查（必做，付费调用前）

- MLM 关键词只用西语，MLB 关键词只用葡语；**两个市场都不用中文关键词**。
- 用户给了中文关键词，或给了错市场语言的关键词（例如巴西站给西语
  `cuerda para saltar`、墨西哥站给葡语 `corda para pular`），**停下并
  请用户提供/确认正确语言的关键词**。不静默翻译、不把错语言词直接
  拿去调付费接口。
- 正确语言示例：MLM 西语 `cuerda para saltar`；MLB 葡语 `corda para pular`。

### 货币规则

- MLM 价格一律 MXN，MLB 价格一律 BRL；同一张表里不得混用两种货币，
  不得用自编汇率换算。跨市场对比被要求时，MXN 与 BRL 两列并排展示，
  换算栏目标“待核实”，除非用户提供了汇率 + 日期。

### 缺失时怎么办

- **用户没有给的条件，不要自己补一个默认条件去找品。**
  缺硬条件时先问清楚；用户坚持先跑，就按已给的条件找，并在输出里写清
  “缺失条件 ×××，以下候选未按该条件筛选，风险见 Skill 6”。
- 预算和目标利润率是硬筛选条件，不是参考：超出预算或在基准情景下
  达不到目标利润率的候选品，不进候选清单，只进淘汰清单。
- 目标利润率的“基准情景”判定需要采购与物流成本；成本缺失时，候选品
  先标“利润待算（缺成本）”，不直接按利润淘汰、也不放进候选清单当作
  已通过——放进“待补成本复核”小节，等 Skill 7 算完再定去留。

## Damaishuju MCP Calls

唯一数据源：大麦数据 MCP（`custom.damaishuju`）。
本 Skill 只用其中 3 个。调用前先读
`~/workspace/custom-connectors/custom.damaishuju/CONNECTOR.md`。

### 调用顺序

1. **`get_my_quota_status`（免费）——先查配额，再做任何付费调用。**
   无参数。读 `available_points`（2026-11-23 实测为 50，无套餐，
   `plan_code` / `plan_name` 均为 null）。
   剩余点数不足时停下并告诉用户，不静默烧完。
   注意：**单次付费调用扣几分未知**，永远不要声称某次调用扣了多少分；
   只记录调用前后的 `available_points` 实测差值。
2. **`search_categories`（免费）——用市场语言查品类，拿 `category_id`。**
   参数：`{"market_code": "<MLM 或 MLB>", "query": "<市场语言品类名>"}`。
   示例：MLM `{"market_code": "MLM", "query": "cuerdas para saltar"}`；
   MLB `{"market_code": "MLB", "query": "corda para pular"}`。
   若 Skill 1 已给出 `category_id` 且在 14 天缓存期内，直接复用，不重复调用。
   一个市场语言词可能返回多个类目，拿不准时请用户选，不要猜。
3. **`search_product_snapshots`（付费）——按硬条件筛商品快照。**
   参数示例：
   `{"market_code": "<MLM 或 MLB>", "keyword": "<市场语言关键词>", "category_id": "<id>", "price_min": <目标售价下限>, "price_max": <目标售价上限>, "sales_30d_min": <下限，如有>, "sales_30d_max": <上限，如有>, "sort_by": "sales_30d", "limit": <小数目>}`。
   `sku_id` 前缀按市场区分：MLM 开头为 `MLM...`，MLB 开头为 `MLB...`。
   - `keyword` 必须是市场语言（MLM 西语 / MLB 葡语），中文关键词不支持。
   - `price_min` / `price_max` 直接取发现简报的目标售价区间，
     不要自己放宽或收紧。
   - `sales_30d_min` / `sales_30d_max` 只有用户给过销量门槛时才传，
     没给就不传，不要自己编一个门槛。
   - 初筛用小 `limit`（例如 20–30）；只有需要全量时才用大 limit，
     同一关键词 / 类目 14 天内不重复调。

### 缓存（14 天）

- `search_categories` 结果缓存 14 天；`search_product_snapshots` 同一
  关键词 / 类目 / 筛选组合 14 天内不重复调（key 含全部筛选条件 hash）。
- 缓存只在调用完整成功后写；失败、超时、返回为空不写缓存。

### 调用记录

每次调用记录：工具名、参数、调用时间、返回条数、调用前后的
`available_points`。附在输出末尾。

## Analysis Steps

1. **确认简报与语言检查**：先确认 `market_code`（缺失先问，不默认 MLM）
   与关键词语言是否匹配市场（MLM 西语 / MLB 葡语，中文关键词与错市场
   语言关键词一律停下问用户，见 §Inputs 语言检查）；再逐项核对硬条件，
   缺失项先问；问完仍缺的，记入“缺失条件及影响”，不自己补默认值。
2. **定类目与关键词**：`search_categories` 拿 `category_id`；关键词用
   市场语言原文，可准备 1–2 个同义词轮换查，每换一个词都是一次新的
   付费调用，查前先报用户知晓点数消耗。
3. **初筛**：`search_product_snapshots` 按目标售价区间 + `sort_by sales_30d`
   取回快照；先用价格区间做硬筛，再看销量、评分、评论数。
4. **硬条件淘汰**：逐条对照简报，凡触发以下任一的进淘汰清单并写清理由：
   售价超出目标区间；超出预算（首批资金占用超预算时以 Skill 7 复核为准，
   本 Skill 只标“疑似超预算，待 Skill 7 复核”）；目标利润率在基准情景下
   达不到（有成本数据时才判，无成本时标“利润待算”，不直接淘汰）；
   供应链条件不满足（无现货、起订量超预算、补货周期用户不接受）；
   品牌状态为未授权品牌（按 V2.1 门禁思路先标高风险，进淘汰清单，
   最终 BLOCK 判定由 Skill 6 / 合规门禁做）。
5. **候选清单成型**：通过硬筛的进候选清单，只写工具实际返回的字段，
   不补、不推、不排序成推荐顺序（排序是 Skill 6 的事）。
6. **写缺口**：每个候选品写清“哪些数据尚未核实”（成本、品牌授权、
   认证状态等），缺口原样交给 Skill 3 / 6 / 7。

## Output Template

```markdown
# 候选清单：<市场语言品类名>（<category_id>）

- 采集时间：<YYYY-MM-DD HH:mm，时区>
- 数据来源：大麦数据 MCP `search_product_snapshots` / `search_categories`
- 市场：Mercado Libre 墨西哥站（MLM，货币 MXN）或 Mercado Livre 巴西站（MLB，货币 BRL）——按本次 `market_code` 写其中一个
- 发现简报：<市场代码 + 8 项简述，缺失项写“未提供”>
- 证据等级：页面可见（工具返回的原始数据，未经卖家后台复核）

## 候选清单（通过硬筛选）

| # | sku_id | 标题（市场语言原文） | 售价（MXN，MLM / BRL，MLB） | sales_30d | sales_60d | sales_90d | 评分 | 评论数 | 卖家 / 店铺字段（按返回写） |
|---|---|---|---|---|---|---|---|---|---|
| 1 | <sku_id> | <原文标题> | <数值> | <数值> | <数值> | <数值> | <数值> | <数值> | <按工具返回写> |
| … | … | … | … | … | … | … | … | … | … |

> 规则：只写工具实际返回的字段。某字段工具没返回就写“—（工具未返回）”，
> 不编数。`sales_30d/60d/90d` 是工具返回的销量口径，不要改写成其他口径。
> 本表不含任何 GO 结论，不排序推荐。

## 待补成本复核（未进候选、也未淘汰）

| sku_id | 标题（市场语言原文） | 原因 |
|---|---|---|
| <sku_id> | <原文标题> | 利润待算：缺采购/物流成本，待 Skill 7 复核 |

## 淘汰清单（硬条件不通过）

| sku_id | 标题（市场语言原文） | 淘汰原因（具体到哪条硬条件） |
|---|---|---|
| <sku_id> | <原文标题> | 售价 <数值> <MXN，MLM / BRL，MLB>，超出目标区间 <区间> |
| <sku_id> | <原文标题> | 目标利润率基准情景不达标（有成本数据时） |
| <sku_id> | <原文标题> | 未授权品牌 / 供应链条件不满足：<具体> |

## 缺失条件及影响

- <缺失的简报项>：<对本次筛选的影响，例：未给目标利润率，本次未按利润筛，候选须经 Skill 7 复核>

## 每个候选品尚未核实的数据

- <sku_id>：<成本 / 品牌授权 / 认证状态 / …，逐项列>

## 调用记录

| 工具 | 参数摘要 | 调用时间 | 返回条数 | 调用前后 available_points |
|---|---|---|---|---|
| get_my_quota_status | — | <时间> | — | <调用前数值> |
| search_categories | query=<市场语言词>, market_code=<MLM/MLB> | <时间> | <n> | 免费 |
| search_product_snapshots | keyword=<市场语言词>, market_code=<MLM/MLB>, price=<区间> | <时间> | <n> | <调用前 → 调用后> |
```

## Error Handling

| 情况 | 做法 |
|---|---|
| 简报硬条件缺失 | 先问；用户坚持先跑就按已给条件跑，缺失项写进“缺失条件及影响”，不补默认值 |
| `search_categories` 无结果 / 多候选拿不准 | 换同义词再查（免费）；仍无结果就停下，把试过的市场语言词列给用户；多候选请用户选 |
| `search_product_snapshots` 返回空 | 先检查是不是价格区间或销量门槛过严；放宽任何一个筛选条件前必须先问用户，不要自己放宽 |
| 返回字段缺失（如无 sales_60d/90d） | 缺失字段写“—（工具未返回）”，不编、不从 sales_30d 推算 |
| 配额不足 | 停下，告诉用户当前剩余点数和本次需要的调用，不要先烧再说 |
| 调用超时 45 秒 | 先用只读查询确认状态再决定是否重试，失败重试最多 1 次（仅瞬时错误） |
| 401 / 403 | 先查凭证与 placement（见 CONNECTOR.md），不盲重试 |
| 工具返回与简报明显冲突（如价格区间外仍有返回） | 以简报为准做淘汰，冲突写进淘汰理由，不擅自改简报 |

## Evidence & Limits

### 证据等级（五档，V2.1 原样沿用）

- **已核实**：凭证已提供，或在官方页面、卖家后台亲眼看到。
- **页面可见**：平台公开页面可见，但没有后台或凭证复核。
  大麦工具返回的原始数据在本 Skill 里按此档标注。
- **用户提供**：用户提供，还没有外部复核。
- **待核实**：还没有来源，必须在上架前核实。
- **推测**：只是推理，不是事实。推测不能用来给需求、利润或合规打满分。

每条关键数据都要写来源、采集时间、证据等级三项。

### 禁止的转换（一条都不能做）

- 不得把搜索结果排名直接写成销量或市场份额。
- 不得把页面已售提示直接写成近 30 天销量或转化率。
- 不得把创作者推广、短视频热度、Linktree 活动入口直接写成销量。
- 不得把供应商口头描述的销量直接写成平台销量。
- 不得把一次大促的单日表现直接写成长期需求。

### 局限

- 本 Skill 不给 verdict、不评分、不算利润；候选清单里的顺序只是
  `sort_by sales_30d` 的返回顺序，不是推荐顺序。
- `sales_30d/60d/90d` 是工具返回的口径，本 Skill 不验证、不换算、
  不把它当作“未来 30 天一定能卖这么多”。
- 利润是否达标最终由 Skill 7 用用户提供的成本复核；本 Skill 的
  “利润待算”不是通过，也不是淘汰。
- 费率未核实：美客多佣金比例、固定费用、免运费门槛、MSI 分期成本等
  均未核实，本 Skill 不写任何费率数字，不用费率做筛选；
  利润判断只用用户提供的成本与目标利润率。巴西站费率/税费同样待核实，
  不得把墨西哥的费率、MSI 或税率套到巴西站。
- 唯一已核实的税费口径（**仅限墨西哥站**，Mercado Pago 官方博客 2026-05-15，
  2026-11-23 访问）：有 RFC 时 ISR 2.5%、IVA 代扣 8%；
  无 RFC 时 ISR 20%、IVA 16%。本 Skill 不做税务计算。
  **巴西站不适用，巴西税费待核实**——不得把上述 ISR/IVA 数字套到巴西站，
  也不得自编任何巴西佣金/税率。

### 来源

- 方法来源：评估报告 §5（架构与 Skill 规范）、Aron `score.mjs` 的发现
  流程（只复用流程形状，不复用 Helium 10 数据层）、FlatNine
  `product-research` 模板、SkillShelf 徽章框架（定性部分）。
  数据层 100% 替换为大麦 MCP；不复制任何来源项目的品牌、
  付费 API 或 upsell 文案。
- 评分与 verdict 口径以现有美客多选品 Skill V2.1
  （`~/workspace/custom-skills/mercado-libre-product-selection/SKILL.md`）为准，
  评分本身由 Skill 6 执行。

---
name: ml-market-research
description: Research a Mercado Libre Mexico (MLM) or Brazil / Mercado Livre (MLB) category with Damaishuju: category size, monthly sales/GMV/price trend over the past year, listing counts and growth. Trigger phrases: "查一下这个品类市场怎么样", "market research", "品类调研", "这个类目大不大", "帮我看一下市场规模".
version: 1.0.0
license: MIT
---

# Mercado Libre Market Research — 市场研究

## Purpose

回答一个问题：**这个品类在目标站点（墨西哥站 MLM 或巴西站 MLB）值不值得继续研究？**

本 Skill 只做品类层面的事实摸底，不评估单个商品、不给 GO / CONDITIONAL / NO-GO
结论（评分与 verdict 是 Skill 6 `ml-product-opportunity-scoring` 的事）。
输出是一份品类概览 + 一份发现简报检查清单，供 Skill 2
`ml-product-discovery` 直接接手。

适用范围：Mercado Libre 墨西哥站（`market_code` MLM）与巴西站 Mercado Livre（`market_code` MLB）。
**`market_code` 是必填参数**：MLM 或 MLB，二选一。用户没给 `market_code`
时先问用户，**不默认 MLM、不默认墨西哥**；用户明确要巴西时绝不按墨西哥跑。
两站的数据、关键词语言、货币、费率互不通用，不要套用另一站的数据和结论。

## Input / Output Contract

| 方向 | 内容 |
|---|---|
| 消耗（输入） | 目标品类（市场语言，见 §Inputs 语言检查）、`market_code`（MLM 或 MLB，必填）；可选：用户已知的品类关键词、目标价格区间 |
| 产出（输出） | 本文件 §输出模板 的品类概览 Markdown + 发现简报检查清单；下游 Skill 2 消费其中的 `category_id`、品类规模判断与缺口清单 |
| 不产出 | 单个商品推荐、评分、利润测算、GO 结论 |

## Inputs

### 必填

- **市场代码 `market_code`（必填）**：`MLM`（墨西哥站 Mercado Libre）或
  `MLB`（巴西站 Mercado Livre）。缺失时先问用户，不假设、不默认 MLM。
- **目标品类（市场语言原文）**：
  - MLM：西语原文，例如 `cuerdas para saltar`、`termos de acero inoxidable`。
  - MLB：葡语原文，例如 `corda para pular`、`garrafa térmica de aço inoxidável`。
  中文品类名不能直接用，先问用户要市场语言说法，或由用户确认你提供的
  市场语言词。关键词只支持市场语言，不支持中文关键词。

### 语言检查（必做，付费调用前）

- MLM 关键词只用西语，MLB 关键词只用葡语；**两个市场都不用中文关键词**。
- 用户给了中文关键词，或给了错市场语言的关键词（例如巴西站给西语
  `cuerda para saltar`、墨西哥站给葡语 `corda para pular`），**停下并
  请用户提供/确认正确语言的关键词**。不静默翻译、不把错语言词直接
  拿去调付费接口。
- 正确语言示例：MLM 西语 `cuerda para saltar`；MLB 葡语 `corda para pular`。

### 可选

- 用户已经知道的品类关键词（市场语言）、同义词、目标价格区间
  （MLM 用 MXN，MLB 用 BRL，见 §货币规则）。
  有就用，没有就不写，不要自己编一个默认价格区间去查。

### 缺失时怎么办

- 缺市场语言品类名：先问用户，或给出 1–2 个市场语言候选词请用户确认，确认前不调用
  `industry_overview`（它是付费调用，见下）。
- 缺目标价格区间：不影响本 Skill 运行，品类概览照常出，在检查清单里记一笔
  “目标价格区间待确认，Skill 2 初筛时补”。

## Damaishuju MCP Calls

唯一数据源：大麦数据 MCP（`custom.damaishuju`），7 个工具。
本 Skill 只用其中 3 个。调用前先读
`~/workspace/custom-connectors/custom.damaishuju/CONNECTOR.md`。

### 调用顺序

1. **`get_my_quota_status`（免费）——先查配额，再做任何付费调用。**
   无参数。读 `available_points`（2026-11-23 实测为 50，无套餐，
   `plan_code` / `plan_name` 均为 null）。
   剩余点数不足时停下并告诉用户，不静默烧完。
   注意：**单次付费调用扣几分未知**，工具说明没写单价，永远不要在输出里
   声称某次调用扣了多少分；只记录调用前后的 `available_points` 实测差值。
2. **`search_categories`（免费）——用市场语言查品类，拿 `category_id`。**
   参数：`{"market_code": "<MLM 或 MLB>", "query": "<市场语言品类名>"}`。
   示例：MLM `{"market_code": "MLM", "query": "cuerdas para saltar"}`；
   MLB `{"market_code": "MLB", "query": "corda para pular"}`。
   一个市场语言词可能返回多个类目：按名称贴合度挑最贴切的一个；拿不准时把
   候选类目列给用户选，不要猜一个就往下跑。
3. **`industry_overview`（付费）——按 `category_id` 查品类月度表现。**
   参数：`{"category_id": "<上一步返回的 category_id>", "market_code": "<MLM 或 MLB>"}`。
   返回过去一年的按月数据。

### 缓存（14 天）

- `search_categories` 和 `industry_overview` 的结果缓存 14 天（移植 Aron 的
  缓存思路，key 含筛选条件 hash：品类词 + `category_id` + `market_code`）。
- 14 天内同一品类不再重复调用，直接读缓存并在输出里写明缓存日期。
- 缓存只在一次调用完整成功后写；失败、超时、返回为空不写缓存。

### 调用记录

每次调用记录：工具名、参数、调用时间、返回条数、调用前后的
`available_points`。记录附在输出末尾的“调用记录”一节。

## Analysis Steps

0. **语言检查**：先确认 `market_code`（缺失先问，不默认 MLM）与关键词语言
   是否匹配市场（MLM 西语 / MLB 葡语，中文关键词与错市场语言关键词一律
   停下问用户，见 §Inputs 语言检查）。语言未通过不调任何付费接口。
1. **定类目**：用 `search_categories` 确认 `category_id`，记录市场语言品类名、
   `category_id`、候选类目取舍理由。
2. **读月度序列**：取 `industry_overview` 返回的过去 12 个月数据，
   只写工具实际返回的字段（见输出模板）。算环比（MoM）：
   `MoM = (本月 − 上月) / 上月 × 100%`。环比只在相邻两月都有数据时算，
   缺月不补、不插值。
3. **读规模**：总上架数 / 在售数、`sales_30d`、均价、1 个月 GMV，
   全部以工具返回值为准。
4. **判趋势方向**：只描述过去 12 个月实际发生的走势（上升 / 平稳 /
   下滑 / 波动），不预测未来，不写“下个月会涨”。
5. **写检查清单**：对照 §发现简报检查清单，逐项标“已有 / 待确认”，
   缺口原样交给 Skill 2。
6. **写“本 Skill 回答不了的事”**：见输出模板末节，缺什么写什么，
   不用推测填补。

## Output Template

```markdown
# 品类概览：<市场语言品类名>（<category_id>）

- 采集时间：<YYYY-MM-DD HH:mm，时区>
- 数据来源：大麦数据 MCP `industry_overview` / `search_categories`
- 市场：Mercado Libre 墨西哥站（MLM，货币 MXN）或 Mercado Livre 巴西站（MLB，货币 BRL）——按本次 `market_code` 写其中一个
- 证据等级：页面可见（工具返回的原始数据，未经卖家后台复核）

## 品类规模（工具实际返回为准）

| 指标 | 数值 | 证据等级 |
|---|---|---|
| 总上架数 / 在售数 | <数值或 待核实> | <等级> |
| sales_30d | <数值或 待核实> | <等级> |
| 均价（MXN，MLM / BRL，MLB） | <数值或 待核实> | <等级> |
| 1 个月 GMV（MXN，MLM / BRL，MLB） | <数值或 待核实> | <等级> |

> 规则：上表只填工具实际返回的字段。工具没返回的字段写“待核实”，
> 不编数、不从其他品类推算、不把搜索排名当销量。

## 过去 12 个月趋势

| 月份 | 销量 | GMV（MXN，MLM / BRL，MLB） | 均价（MXN，MLM / BRL，MLB） | MoM |
|---|---|---|---|---|
| <YYYY-MM> | <数值> | <数值> | <数值> | <±x.x% 或 —> |
| … | … | … | … | … |

- 趋势判断（只描述已发生）：<上升 / 平稳 / 下滑 / 波动，一两句，附依据月份>
- 季节性提示：<如某几个月明显高于/低于其余月份，写出来；单月高点不等于旺季，见 §证据与局限>

## 发现简报检查清单（交给 Skill 2）

| 简报项 | 状态 | 备注 |
|---|---|---|
| 目标品类（市场语言 + category_id） | 已有 | <品类名 / category_id> |
| 市场 market_code | 已有 | <MLM / MLB> |
| 预算 | 待确认 / 已有 | <用户提供才填> |
| 目标利润率 | 待确认 / 已有 | <用户提供才填> |
| 目标售价 | 待确认 / 已有 | <用户提供才填> |
| 供应链条件 | 待确认 / 已有 | <用户提供才填> |
| 物流方式 | 待确认 / 已有 | <用户提供才填> |
| 目标消费者 | 待确认 / 已有 | <用户提供才填> |
| 希望寻找的商品类型 | 待确认 / 已有 | <用户提供才填> |

## 本 Skill 回答不了的事

- <逐条列出：例如 单个商品的销量、头部卖家是谁、该品类佣金比例、
  具体某个 listing 的评价内容——这些分别是 Skill 2 / 3 / 5 / 7 的事，
  或当前无可靠来源，标待核实>
- 费率现状：美客多佣金比例、固定费用、免运费门槛、MSI 分期成本等
  均未核实（2026-11-23 直接查 mercadolibre.com.mx 被拦，
  第三方说法互相冲突），本 Skill 不写任何费率数字，不用费率做任何判断。
  巴西站费率/税费同样待核实，**不得把墨西哥的费率、MSI 或税率套到巴西站**。

## 调用记录

| 工具 | 参数摘要 | 调用时间 | 返回条数 | 调用前后 available_points |
|---|---|---|---|---|
| get_my_quota_status | — | <时间> | — | <调用前数值> |
| search_categories | query=<市场语言词>, market_code=<MLM/MLB> | <时间> | <n> | 免费 |
| industry_overview | category_id=<id> | <时间> | <n> | <调用前 → 调用后> |
```

## Error Handling

| 情况 | 做法 |
|---|---|
| `search_categories` 无结果 | 换同义词 / 上位类目词再查一次（免费）；仍无结果就停下，把试过的市场语言词列给用户，不要猜一个 `category_id` 继续跑 |
| `search_categories` 多个候选类目拿不准 | 列出候选类目请用户选，选定前不调 `industry_overview` |
| `industry_overview` 返回空 / 字段缺失 | 缺失字段写“待核实”，已有字段照常出；不拿别的品类数据凑数 |
| 配额不足（`available_points` 不够） | 停下，告诉用户当前剩余点数和本次需要的调用，不要先烧再说 |
| 调用超时 45 秒 | 按 MCP 客户端规则处理；先用只读查询确认状态再决定是否重试，失败重试最多 1 次（仅瞬时错误） |
| 401 / 403 | 先查凭证与 placement（见 CONNECTOR.md），不盲重试；凭证问题未解决前不继续调用 |
| 工具返回与常识明显冲突 | 两边都写出来，写清冲突点，标待核实，不只挑有利的一边 |

## Evidence & Limits

### 证据等级（五档，V2.1 原样沿用）

- **已核实**：凭证已提供，或在官方页面、卖家后台亲眼看到。
- **页面可见**：平台公开页面可见，但没有后台或凭证复核。
  大麦工具返回的原始数据在本 Skill 里按此档标注（未经卖家后台复核）。
- **用户提供**：用户提供，还没有外部复核。
- **待核实**：还没有来源，必须在上架前核实。
- **推测**：只是推理，不是事实。推测不能用来给需求打高分。

每条关键数据都要写来源、采集时间、证据等级三项，缺一项就补一项，
补不上就写待核实。

### 禁止的转换（一条都不能做）

- 不得把搜索结果排名直接写成销量或市场份额。
- 不得把页面已售提示直接写成近 30 天销量或转化率。
- 不得把创作者推广、短视频热度、Linktree 活动入口直接写成销量。
- 不得把供应商口头描述的销量直接写成平台销量。
- 不得把一次大促的单日表现直接写成长期需求。

### 局限

- 本 Skill 只看品类总量和过去 12 个月趋势，不回答“某个具体商品好不好卖”。
- 趋势是历史记录，不是销量预测；单月高点可能是大促，不等于长期需求。
- 大麦 `industry_overview` 的字段以实际返回为准；本 Skill 不承诺它一定
  包含 GMV、均价等每一项，缺失即待核实。
- 费率未核实：本 Skill 不涉及利润测算；任何佣金、运费、税费数字都不得
  在本 Skill 的输出里出现，除非是用户提供的模拟假设并明确标注
  “模拟结果，不代表实际费用”。
- 唯一已核实的税费口径（**仅限墨西哥站**，Mercado Pago 官方博客 2026-05-15，
  2026-11-23 访问）：有 RFC 时 ISR 2.5%、IVA 代扣 8%（为 16% 总额的 50%）；
  无 RFC 时 ISR 20%、IVA 16%。本 Skill 不做税务计算，只在用户问到时
  引用该口径，并注明适用条件以原文为准。**巴西站不适用，巴西税费待核实**——
  不得把上述 ISR/IVA 数字套到巴西站，也不得自编任何巴西佣金/税率。

### 货币规则

- MLM 价格一律 MXN，MLB 价格一律 BRL；同一张表里不得混用两种货币，
  不得用自编汇率换算。跨市场对比被要求时，MXN 与 BRL 两列并排展示，
  换算栏目标“待核实”，除非用户提供了汇率 + 日期。

### 来源

- 方法来源：评估报告 §5（架构与 Skill 规范）、SkillShelf `business-context`
  的基础文档串联思路、Nexscope 跨境报告结构、FlatNine `niche-analysis`
  结构。数据层 100% 替换为大麦 MCP；不复制任何来源项目的品牌、
  付费 API 或 upsell 文案。
- 评分口径以现有美客多选品 Skill V2.1
  （`~/workspace/custom-skills/mercado-libre-product-selection/SKILL.md`）为准。

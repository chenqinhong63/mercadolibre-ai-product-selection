---
name: ml-review-intelligence
description: Analyze Mercado Libre Mexico (MLM) or Mercado Livre Brazil (MLB) buyer reviews for one product (sku_id) via Damaishuju review_search — group reviews into themes, surface pain points, praise, feature requests and differentiation angles. Use when the user asks to read reviews, find what buyers complain about or praise, or check whether a product claim holds up.
version: 1.0.0
license: MIT
---

# ml-review-intelligence — 评论洞察

## 目的

读懂一个商品的买家评论，回答三个问题：买家最常夸什么、最常抱怨什么、他们原话里想要什么。本 Skill 只做评论分析，**不给 GO / CONDITIONAL / NO-GO 结论**——评论发现是输入，交给 Skill 6（ml-product-opportunity-scoring）参与打分。

方法来源：SkillShelf `extract-review-insights`（主题按频率、客户原话、宣称核对、Confidence Notes、少于 10 条 / 多于 500 条处理），数据源改为大麦数据 MCP 的 `review_search`。Nexscope `product-review-analysis` 的痛点结构（频率 / 严重度 / 例句 / 根因）只作字段参考，不复用其数据源。

## 市场参数（market_code，第一位参数）

- `market_code` 必填，二选一：`MLM` = Mercado Libre México（墨西哥站，货币 MXN，评论语言西语）或 `MLB` = Mercado Livre Brasil（巴西站，货币 BRL，评论语言葡语）。
- **如果 `market_code` 缺失，先问用户，不默认 MLM。** 绝不以“用户没说就按墨西哥”静默处理；用户明确要求巴西时，一律按 MLB 走。
- 关键词只用评论语言：MLM 只用西语关键词，MLB 只用葡语关键词，**绝不用中文关键词**。
- 同一次分析只针对一个市场，不把 MLM 和 MLB 的评论混在一次分析里；跨市场对比时分开各跑一次，再并列呈现。

## 输入

| 字段 | 必填 | 说明 |
|---|---|---|
| `market_code` | 必填 | `MLM`（墨西哥站）或 `MLB`（巴西站）。缺失时先问用户，不默认 MLM。 |
| `sku_id` | 必填 | 大麦数据的商品 ID（对应 `market_code` 的站点）。没有时先调 `search_product_snapshots`（MLM 用西语关键词，MLB 用葡语关键词）取 `sku_id`，不要猜。 |
| `page` / `limit` | 可选 | 分页参数；默认取最新评论，见“样本规则”。 |
| `claims_to_check` | 可选 | 用户或卖家想核对的宣称清单（如“防水”“静音”），逐条核对。没有就不编。 |
| `product_context` | 可选 | 商品名、规格、售价（MLM 为 MXN，MLB 为 BRL），来自 Skill 2 / Skill 3 的输出，用于判断评论是否针对同一商品。 |

缺 `sku_id` 时先问用户，或先用 Skill 2 的方法取 `sku_id`；不要用商品名直接调 `review_search`。

## 大麦 MCP 调用

唯一数据源是大麦数据 MCP（`custom.damaishuju`）。调用前先调免费的 `get_my_quota_status` 查剩余点数；点数不足时停下并告诉用户，不静默烧完。单次付费调用的点数成本未知，**不要声称某次调用花了几点**。

| 顺序 | 工具 | 参数 | 说明 |
|---|---|---|---|
| 0（可选） | `search_product_snapshots` | `market_code: MLM 或 MLB`，`keyword`（MLM 西语 / MLB 葡语，绝不用中文），`limit` 小值 | 仅在没有 `sku_id` 时用，取目标商品的 `sku_id` 并核对商品名 / 价格一致。 |
| 1 | `review_search` | `sku_id`（必填），`market_code: MLM 或 MLB`，`page`，`limit` | 读该商品的评论。 |

失败重试最多 1 次（瞬时错误）；401 / 403 先查凭证，不盲重试；超时 45 秒按 MCP 客户端规则处理。记录每次调用：工具名、参数、调用时间、返回条数、调用后剩余点数。

## 样本规则

- **少于 10 条评论**：证据薄。输出缩短，只写看到的主题，不排频率名次，并在输出顶部显著提示“评论不足 10 条，证据薄，结论只作方向参考”。
- **多于 500 条评论**：最多用最新 500 条，并写明“共 N 条，本次分析最新 500 条”，不要声称读了全部。
- **10–500 条**：全部读完再归纳，不要只读第一页就下结论。
- 评论语言：MLM 为西语，MLB 为葡语。分析用中文输出，关键词和引用保留评论原文语言（西语或葡语），不翻译后当引用；主题关键词必须用评论语言（西语或葡语）。

## 分析步骤

1. **读全部样本评论**，包括星级、评论文本、评论时间（如返回里有）。先看分布，再看内容。
2. **主题归类**：把“同一件事、不同说法”的评论归为一个主题（如“绳子打结”“手柄打滑”“包装破损”都可能指向不同主题；“绳子太长”“绳子太短”同属“长度不合适”主题）。主题名用中文，附一条评论原文（MLM 西语 / MLB 葡语）例证；主题关键词用评论语言。
3. **频率排序**：主题按提及的评论数从多到少排。频率用 plain language（“多条评论”“少数评论”“一条评论”），**除非能准确计数，不要编造精确数字**；能准确计数时写“X 条（占比 Y%）”，X 必须是你实际数出来的。
4. **痛点分级**：每个痛点标严重度——高（影响使用 / 导致退货 / 多人重复提）、中（体验扣分但能用）、低（个别提及的轻微不满）。写清根因推测时标注为推测，不当事实。
5. **好评主题**：同步骤 2–3，列出买家最常夸的点，按频率排。
6. **功能需求**：买家明确说“希望有 / 要是能……”的内容单独列出，注明是买家原话还是你的归纳。
7. **有用客户原话（Useful Customer Language）**：摘 3–8 条最能代表主题的评论原文（MLM 西语 / MLB 葡语），保留原文，不改写、不翻译后当引用；每条注明它代表哪个主题。
8. **宣称核对（Claims Supported / Careful With）**：对 `claims_to_check` 里的每条宣称逐条判：
   - `supported`（评论支持）、`contradicted`（评论反驳）、`mixed`（有支持有反驳）、`not mentioned`（评论里没提到）。
   - 没有提供宣称清单时写“本次未提供待核对宣称”，不要自己编宣称来核对。
9. **差异化角度**：从痛点和功能需求里提炼 1–3 个可执行的差异化方向（如“加防滑手柄”“附收纳袋”），每个写清它解决哪个痛点、买家是否真的需要（有评论支撑还是推测）。只写“提升质量”“做好服务”不算差异化。
10. **Confidence Notes**：写清样本量、时间跨度（如有）、缺失信息（如无星级分布、无评论时间）、哪些结论是薄证据。

## 禁止的转换

- 不得把评论数量写成销量，不得把好评率写成转化率。
- 不得把一条评论的说法写成“买家普遍认为”。
- 不得把创作者热度、短视频热度写成评论证据。
- 不得编造评论、星级、评论数、引用原话。没有读到的内容写“未见相关评论”，不写“没有这个问题”。
- 不得把搜索排名写成销量，不得把页面已售提示写成 30 天销量。

## 输出模板

```markdown
# 评论洞察：<商品名>（sku_id: <id>）

- 市场：<Mercado Libre México（MLM）/ Mercado Livre Brasil（MLB）>，market_code <MLM / MLB>，货币 <MXN / BRL>
- 数据来源：大麦数据 review_search，market_code <MLM / MLB>
- 采集时间：<YYYY-MM-DD HH:MM>
- 评论样本：共 <N> 条，本次分析 <M> 条（<M> = min(N, 500)，最新优先）
- 证据等级：<已核实 / 页面可见 / 用户提供 / 待核实 / 推测>（见证据等级说明）
- 证据薄提示：<评论 < 10 条时必填：评论不足 10 条，证据薄，结论只作方向参考>

## 主题总览

| 主题 | 提及评论数 | 占比 | 例句（评论原文，西语 / 葡语） |
|---|---|---|---|
| <主题中文名> | <X 条 / 多条评论> | <Y% / —> | “<评论原话>” |

## 痛点（按频率排序）

| 痛点 | 严重度 | 提及 | 例句（评论原文，西语 / 葡语） | 根因（推测请标注） |
|---|---|---|---|---|
| <痛点> | 高 / 中 / 低 | <X 条> | “<评论原话>” | <根因或“待核实”> |

## 好评主题（按频率排序）

| 好评点 | 提及 | 例句（评论原文，西语 / 葡语） |
|---|---|---|
| <好评点> | <X 条> | “<评论原话>” |

## 功能需求（买家原话想要的）

- <需求>——“<评论原话>”（<X 条提及>）

## 有用客户原话

- “<评论原话>”——代表主题：<主题>

## 宣称核对

| 宣称 | 结论 | 依据 |
|---|---|---|
| <宣称> | supported / contradicted / mixed / not mentioned | <评论依据或“评论里未提到”> |

## 差异化角度（供 Skill 6 参考，不作 verdict）

1. <差异化方向>：解决痛点 <痛点>，买家需求证据 <有评论支撑 / 推测>，可执行性 <说明>

## Confidence Notes

- 样本量 <M> 条，<是否覆盖全部评论>；星级分布 <如有则写，无则写“返回数据未含星级分布”>。
- 薄证据结论：<列出哪些结论证据薄>
- 未核实项：<列出需要人工复核的项>

## 交给 Skill 6 的输入

- 主要痛点：<1–3 条>
- 主要好评：<1–3 条>
- 差异化角度：<1–3 条>
- 宣称核对结果：<supported / contradicted / mixed / not mentioned 汇总>
```

## 错误处理

| 情况 | 做法 |
|---|---|
| `sku_id` 无效 / 无评论返回 | 写“该 sku_id 下未返回评论”，不编主题；建议核对 `sku_id` 或换 `search_product_snapshots` 重新确认商品。 |
| 剩余点数不足 | 停止调用，告诉用户当前剩余点数和本次需要的调用，建议用户充值或缩小范围。 |
| `review_search` 超时 / 报错 | 最多重试 1 次；仍失败则写清失败的工具名、参数、时间，不用旧数据冒充本次结果。 |
| 返回评论与商品明显不符（如商品名对不上） | 停止分析，写清不符点，请用户确认 `sku_id` 是否正确。 |
| 评论全是空文本 / 只有星级 | 只做星级分布描述（如有），不编主题，写清“评论文本缺失，无法做主题分析”。 |

## 证据与局限

- 证据等级（沿用 V2.1 五档）：已核实、页面可见、用户提供、待核实、推测。评论内容本身来自大麦数据，来源类型为“第三方公开信息”；评论数、星级以返回数据为准，缺失字段写“返回数据未含”。
- 每条关键数据（评论总数、主题提及数、宣称核对结论）附来源（`review_search`）、采集时间、证据等级。
- 局限：评论是买家自愿留下的，不代表全部买家；差评可能集中在物流 / 包装而非产品本身，归类时要区分；本 Skill 不判断商品能不能卖，只输出评论发现。
- 本 Skill 的输出供 Skill 6 使用；Skill 6 的 verdict 不由本 Skill 单独决定。

## 输入 / 输出契约（供串联）

- 输入：`market_code`（必填，`MLM` 或 `MLB`；缺失时先问用户，不默认 MLM）+ `sku_id`（必填）+ 可选的 `claims_to_check`、`product_context`（售价货币：MLM 为 MXN，MLB 为 BRL）。
- 输出：上节模板的 Markdown，含主题表、痛点表、好评表、功能需求、客户原话、宣称核对、差异化角度、Confidence Notes、“交给 Skill 6 的输入”一节。
- 上游：Skill 2（ml-product-discovery）或 Skill 3（ml-competitor-analysis）提供 `sku_id`；下游：Skill 6（ml-product-opportunity-scoring）读取本输出的痛点、好评、差异化角度和宣称核对结果。

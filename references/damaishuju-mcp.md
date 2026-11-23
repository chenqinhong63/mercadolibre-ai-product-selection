# 大麦数据 MCP（Damaishuju）— 唯一数据源

> 本文件是本系统唯一的数据源说明。所有市场、商品、销量、评论数据只走大麦数据 MCP，不引入其他付费 API。
> 连接器文档：`~/workspace/custom-connectors/custom.damaishuju/CONNECTOR.md`（本地副本；新仓库不复制其中的凭证配置）。
> MCP 端点：`https://mcp.damaishuju.com/tools/mcp`，请求头 `X-API-Key`。
> 密钥只进用户的安全存储 / MCP 客户端配置，**绝不写进代码、文档、日志或聊天记录**。

## 验证状态（2026-11-23）

- `list-tools` 实测返回 7 个工具。
- `get_my_quota_status` 实测返回 `available_points` 50，`plan_code` null，`plan_name` null（无套餐）。
- **单次调用消耗点数未知**：工具说明只写“消耗积分”，未写每次扣几分。**绝不声称任何单价**。第一轮实测时以一次真实商品搜索前后的配额差为准，再定每 Skill 的点数预算。
- 关键词只支持当地语言：MLM（墨西哥站）只支持西语关键词，MLB（巴西站）只支持葡语关键词；两个市场都不支持中文关键词。
- 本连接器只能读 Mercado Libre 市场数据，**不能做卖家账号操作**（不能下单、改价、改 Listing、看卖家后台）。

## 通用规则

- `market_code` 必填：`MLM`（墨西哥站）或 `MLB`（巴西站）。用户没给时先问，不默认 MLM；用户明确要巴西站时绝不得用 MLM 调接口。
- 关键词、类目查询一律用市场语言原文：MLM 用西语，MLB 用葡语；中文只用于分析输出和注释。语言检查：中文关键词与错市场语言关键词（MLM 给葡语、MLB 给西语）一律拒绝并请用户改成正确语言。
- 价格一律用市场货币：MLM 用 MXN，MLB 用 BRL；同一张表里不得混用两种货币，不得用自编汇率换算。
- 每次付费调用前先调 `get_my_quota_status`（免费）；剩余点数不足时停下并告诉用户，不静默烧完。
- 缓存：`search_categories` 与 `industry_overview` 结果缓存 14 天（key 含筛选条件 hash；筛选变化改 hash）。同一关键词 / 类目 14 天内不重复调付费接口。
- `search_product_snapshots`：初筛用小 `limit`，只在需要全量时用 `limit` 100。
- 重试：失败重试最多 1 次，且只针对瞬时错误。401 / 403 先查凭证和 placement，不盲重试。请求 45 秒无响应即按失败处理；重试前先用只读调用确认当前状态，因为第一次请求可能已完成。
- 日志：每次调用记录工具名、参数、调用时间、返回条数、调用后剩余点数（`available_points`）。
- 未实测声明：除 `list-tools` 与 `get_my_quota_status` 外，其余 5 个工具的返回结构在连接器文档中标注为“未实测”（untested）。首次调用后把实际返回字段补进本文件，并标注实测日期；未补之前不把推测的返回字段写成事实。

## 7 个工具

### 1. search_categories — 免费

找 `category_id`，在商品搜索之前调用。

- 参数（JSON 对象）：`market_code`（MLM 或 MLB）、`query`（市场语言类目关键词：MLM 西语，MLB 葡语）。
- 返回：类目候选及其 `category_id`（以实际返回为准）。
- 费用：免费。
- 缓存：14 天。

### 2. search_product_snapshots — 付费（单价未知）

按关键词、类目、价格、销量、评分、评论数、上架日期、库存类型、卖家类型或商品状态找 Mercado Libre 商品快照。

- 参数（JSON 对象）：`market_code`（MLM 或 MLB）、`keyword`（市场语言：MLM 西语，MLB 葡语）、`category_id`（已知时用 `search_categories` 的结果）、`price_min` / `price_max`（市场货币：MLM MXN，MLB BRL）、`sales_30d_min` / `sales_30d_max`、`sort_by`（按近期销量排序用 `sales_30d`）、`limit`。连接器文档另列可用筛选：评分、评论数、上架日期、库存类型（stock_type）、卖家类型、商品状态——具体参数名以 MCP 实际 schema 为准，首次调用前先读 `list-tools` 的 schema，不猜参数名。
- 返回：商品快照列表，含 `sku_id`、价格、30/60/90 天销量、评分、评论数等字段（以实际返回为准）。
- 费用：消耗点数，单价未知。
- 注意：返回的销量字段是工具给出的快照数据；**不得把搜索结果排名写成销量，不得把页面已售提示写成 30 天销量**（见 `evidence-levels.md`）。

### 3. industry_overview — 付费（单价未知）

按月读一个类目过去一年的情况。

- 参数（JSON 对象）：必填 `category_id`，`market_code` MLM 或 MLB。
- 返回：类目月度概览（以实际返回为准）。
- 费用：消耗点数，单价未知。
- 缓存：14 天。

### 4. product_sales_trend — 付费（单价未知）

读单个商品最长 731 天的月度与周度销量。

- 参数（JSON 对象）：必填 `sku_id`，`market_code` MLM 或 MLB，`days`（≤731）。
- 返回：月度与周度销量趋势（以实际返回为准）。
- 费用：消耗点数，单价未知。
- 注意：`sku_id` 来自 `search_product_snapshots` 的结果。

### 5. image_search_products — 付费（单价未知）

以图搜货，从图片找相似商品 ID。

- 参数（JSON 对象）：`market_code` MLM 或 MLB，`image_url` 或 `image_base64` 二选一。
- 返回：相似商品 ID 列表（以实际返回为准）。
- 费用：消耗点数，单价未知。

### 6. review_search — 付费（单价未知）

读单个商品的评论。

- 参数（JSON 对象）：必填 `sku_id`，`market_code` MLM 或 MLB，`page` / `limit`（分页）。
- 返回：评论列表（以实际返回为准）。
- 费用：消耗点数，单价未知。
- 注意：评论为市场语言原文：MLM 西语，MLB 葡语；分析输出用中文，引用原话时保留原文。主题词须用对应语言（见 `ml-review-intelligence`）。

### 7. get_my_quota_status — 免费

查剩余点数与套餐状态。每次付费调用前必调。

- 参数：空 JSON 对象 `{}`。
- 返回：`available_points`、`plan_code`、`plan_name`（2026-11-23 实测：50 / null / null）。
- 费用：免费。

## 各 Skill 的调用顺序

| Skill | 调用顺序 |
|---|---|
| 1. Market Research（`ml-market-research`） | `search_categories`（免费，市场语言：MLM 西语 / MLB 葡语）→ `industry_overview`（`category_id`） |
| 2. Product Discovery（`ml-product-discovery`） | `search_categories` → `search_product_snapshots`（市场语言 keyword：MLM 西语 / MLB 葡语、`category_id`、`price_min`/`max`（市场货币）、`sales_30d_min`/`max`、`sort_by` sales_30d、`limit`） |
| 3. Competitor Analysis（`ml-competitor-analysis`） | `search_product_snapshots`（同类目 Top listing，`shop_query` / `shop_id` 可选）→ 逐个看价格带、评分、评论数、卖家类型 |
| 4. Sales Trend Analysis（`ml-sales-trend-analysis`） | `search_product_snapshots`（取 `sku_id`）→ `product_sales_trend`（`sku_id`，`days` ≤731） |
| 5. Review Intelligence（`ml-review-intelligence`） | `search_product_snapshots`（取 `sku_id`）→ `review_search`（`sku_id`，`page` / `limit`） |
| 6. Product Opportunity Scoring（`ml-product-opportunity-scoring`） | 不直接调 MCP；读 Skill 1–5 的输出 + 用户提供的成本 / 供应数据，用 `score_candidate.py` 算分 |
| 7. Profit Analysis（`ml-profit-analysis`） | 不直接调 MCP；读 Skill 2 / 3 的价格 + 用户提供的采购 / 物流成本，用 `profit_estimate.py` 算三层利润 + 压力测试 |
| 8. Market Report Generator（`ml-market-report-generator`） | 不直接调 MCP；汇总 Skill 1–7 的输出，按统一模板生成报告 |

## 客户端调用示例（本地连接器 helper，仅作参考）

```text
python3 ~/workspace/custom-connectors/custom.damaishuju/bin/client.py list-tools
python3 ~/workspace/custom-connectors/custom.damaishuju/bin/client.py call-tool --name get_my_quota_status --arguments-file ~/workspace/custom-connectors/custom.damaishuju/bin/empty.json
python3 ~/workspace/custom-connectors/custom.damaishuju/bin/client.py call-tool --name search_categories --arguments-file <path-to-json>
python3 ~/workspace/custom-connectors/custom.damaishuju/bin/client.py call-tool --name search_product_snapshots --arguments-file <path-to-json>
```

> 上述路径是用户本地已安装的连接器 helper，不是本仓库的一部分。本仓库不内置大麦客户端、不含任何凭证。

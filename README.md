# Mercado Libre AI Product Selection System

墨西哥站（MLM）+ 巴西站（MLB）AI 选品系统：用大麦数据 MCP 做市场研究、产品发现、竞品分析、销量趋势、评论洞察、机会评分、利润分析与市场报告生成。

市场：`market_code` 必填，`MLM`（墨西哥站 Mercado Libre）或 `MLB`（巴西站 Mercado Livre）；用户没给时先问，不默认 MLM。语言：分析输出用中文，关键词与引用用市场语言原文——MLM 只用西语，MLB 只用葡语，两个市场都不用中文关键词。价格：MLM 一律 MXN，MLB 一律 BRL；不得混用两种货币，不得用自编汇率换算。日期一律写采集时间。

## 这是什么 / 不是什么

**是：**

- 8 个 Skill 的选品工作流（见下表），数据只走大麦数据 MCP。
- 100 分机会评分（V2.1 细则）+ GO / CONDITIONAL / NO-GO 结论 + 三层利润模型。
- 证据等级与数据审计：每个关键数据附来源、采集时间、证据等级；缺失标“待核实”，不编造。

**不是：**

- 不承诺销量、不承诺排名、不承诺平台通过。GO 只表示“值得进入下一轮人工核查和小批量验证”。
- 不是卖家后台工具：大麦 MCP 只读市场数据，不能下单、改价、改 Listing、看卖家后台。
- 不是费率权威来源：平台费、运费、分期、退货等费率在核实前全部标“待核实”，见 `references/ml-fee-sources.md`。墨西哥的 ISR / IVA 代扣率、MSI、佣金比例绝不得搬到巴西站用。

## 8 个 Skill

| # | Skill | 市场 | 输入 | 输出 |
|---|---|---|---|---|
| 1 | `ml-market-research` — 市场研究 | MLM + MLB | 类目（市场语言关键词：MLM 西语 / MLB 葡语） | 类目概览、月度趋势、市场结论 + 证据等级 |
| 2 | `ml-product-discovery` — 产品发现 | MLM + MLB | 类目 / 关键词（市场语言）、价格（市场货币）与销量筛选 | 候选商品清单（按 30 天销量排序） |
| 3 | `ml-competitor-analysis` — 竞品分析 | MLM + MLB | 同类目 Top listing | 竞品并排表：价格带、销量、评分、评论数、卖家类型 |
| 4 | `ml-sales-trend-analysis` — 销量趋势分析 | MLM + MLB | `sku_id` | 最长 731 天的月度 / 周度销量趋势 |
| 5 | `ml-review-intelligence` — 评论洞察 | MLM + MLB | `sku_id` | 评论主题、痛点、好评、宣称核对、Confidence Notes（评论语言：MLM 西语 / MLB 葡语） |
| 6 | `ml-product-opportunity-scoring` — 产品机会评分 | MLM + MLB | Skill 1–5 输出 + 用户提供的成本 / 供应数据 | 100 分评分、风险调整分、置信度、GO / CONDITIONAL / NO-GO（V2.1 细则两市场通用，见 `references/scoring-rubric.md`） |
| 7 | `ml-profit-analysis` — 利润分析 | MLM + MLB | Skill 2 / 3 的价格 + 用户提供的采购 / 物流成本 | 三层利润、反向推导、压力测试（费率待核实项标清；两市场费用分开算，见 `references/profit-model.md`） |
| 8 | `ml-market-report-generator` — 市场报告生成 | MLM + MLB | Skill 1–7 的输出 | 统一市场报告（Markdown / PDF），含数据来源、采集时间、依据表 |

Skill 6 不直接调 MCP，Skill 7 不直接调 MCP，Skill 8 不直接调 MCP（调用顺序见 `references/damaishuju-mcp.md`）。

## 安装

把 `skills/` 复制到你的 Agent 的 skills 目录（按你用的客户端二选一的路径；以下为通用路径，具体以客户端文档为准）：

- Claude Code / Claude：`~/.claude/skills/` 或项目内 `.claude/skills/`
- Codex：`~/.codex/skills/` 或项目内对应 skills 目录
- OpenClaw：`~/.openclaw/skills/` 或项目内对应 skills 目录
- Muse：按 Muse 的 skills 安装路径

也可通过 `.claude-plugin/marketplace.json` 作为 Claude / OpenClaw 插件市场安装（见仓库根目录）。

## 大麦数据 MCP 设置

- 数据源：大麦数据 MCP，端点 `https://mcp.damaishuju.com/tools/mcp`，请求头 `X-API-Key`。
- 密钥获取与填写：按 `~/workspace/custom-connectors/custom.damaishuju/CONNECTOR.md`（用户本地连接器文档）接入；密钥通过用户的安全存储 / MCP 客户端配置填入，**绝不粘贴进代码、文档、日志或聊天记录**。
- 唯一数据源：7 个工具（`search_categories`、`search_product_snapshots`、`industry_overview`、`product_sales_trend`、`image_search_products`、`review_search`、`get_my_quota_status`），详见 `references/damaishuju-mcp.md`。
- 市场代码必填：`MLM`（墨西哥站）或 `MLB`（巴西站）；关键词只用市场语言（MLM 西语，MLB 葡语），不支持中文关键词。
- 配额（2026-11-23 实测）：`available_points` 50，无套餐（`plan_code` / `plan_name` 均为 null）。**单次调用消耗点数未知**——工具说明未写单价，绝不声称任何单价。

## 配额 / 缓存 / 重试规则

- 每次付费调用前先调 `get_my_quota_status`（免费）；剩余点数不足时停下并告诉用户，不静默烧完。
- `search_categories` 与 `industry_overview` 结果缓存 14 天（key 含筛选条件 hash）。
- `search_product_snapshots` 初筛用小 `limit`，只在需要全量时用 `limit` 100；同一关键词 / 类目 14 天内不重复调。
- 失败重试最多 1 次（仅瞬时错误）；401 / 403 先查凭证，不盲重试；45 秒超时按失败处理。
- 所有调用记录：工具名、参数、调用时间、返回条数、调用后剩余点数。

## 快速开始

```bash
# 1. 一次发现：先查类目，再按 30 天销量找候选（Skill 2）
#    MLM：search_categories（免费，西语）→ search_product_snapshots（sort_by=sales_30d）
#    MLB：同样流程，market_code=MLB，关键词用葡语，价格用 BRL

# 2. 一次评分：读 Skill 1–5 的输出 + 用户提供的成本，用确定性脚本算分（Skill 6）
python3 scripts/score_candidate.py --input <scoring-input.csv> --output <scoring-output.md>
#    巴西站：CSV 里加 market_code=MLB，用 price_brl / cost_brl 等 BRL 列（见 examples/discovery-example-br.md）

# 3. 一次利润：读 Skill 2/3 的价格 + 用户提供的采购/物流成本，算三层利润（Skill 7）
python3 scripts/profit_estimate.py --price 249 --cost 68 --shipping 32 --fee-pct 13 --other 32.15 --return-pct 5 --ad-pct 5 --market-code MLB
#    墨西哥站默认 --market-code MLM，价格 MXN；巴西站 --market-code MLB，价格 BRL
```

> 以脚本输出为准，人工不得自行算分。

## 示例

`examples/` 含：墨西哥发现示例（`discovery-example.md`，MLM/MXN/西语）、巴西发现示例（`discovery-example-br.md`，MLB/BRL/葡语）、评分示例（`scoring-example.md`）、报告示例（`report-example.md`），均用脱敏示例数据（明确标注虚构），不含真实密钥。巴西示例的 13% 费率只是示例假设，不是巴西官方费率。

## 测试

```bash
python3 -m unittest discover -s tests
```

- 每个 Skill 至少 1 个测试案例：用 `tests/fixtures/` 里的脱敏示例数据跑脚本，断言分数 / 利润 / 统计值与手工算的一致。
- 评分脚本测试须覆盖：空值处理（null → N/A，不当 0 算）、边界 band 值、GO / CONDITIONAL / NO-GO 阈值。
- 不用真实密钥跑测试；MCP 调用本身只做一次冒烟（`list-tools` + `get_my_quota_status`），不计入测试。

## 许可证与致谢

- 本系统许可证：MIT，见 `LICENSE`。
- 复用来源、许可证、版权方与改动说明：见 `ATTRIBUTION.md`。
- 评估报告与架构方案：`~/workspace/research/mercado-libre-skills-eval/EVALUATION-REPORT.md`（本地研究副本，不在仓库内）。

## 局限：费率待核实清单

以下项目在官方页面重新核实前全部为“待核实”，不得用作系统常量（详见 `references/ml-fee-sources.md` 与 `references/profit-model.md`）。**两市场的费率分开核实、分开记录，绝不混用。**

### 墨西哥站（MLM）

- 佣金比例（Clásica / Premium；第三方说法冲突）
- $299 MXN 以下商品的固定费（传闻分档未核实）
- 免费 Listing 额度
- MSI 分档与成本承担方
- 声誉 / Mercado Líder 门槛数字
- 禁售品清单
- Mi Página 月费
- Mercado Envíos / Full 运费表与免邮门槛
- 退货窗口与退货运费承担方

唯一已核实的税费数字是 Mercado Pago 博客的 ISR / IVA 代扣率（有 RFC：ISR 2.5%、IVA 8%；无 RFC：ISR 20%、IVA 16%），且明确标注为代扣（预缴、可抵扣），不是全部税负。Product Ads 已核实为 CPC 计费，但无公开 CPC 单价、无最低预算。

### 巴西站（MLB）

- 销售佣金 tarifa de venda（Clássico / Premium；第三方报道 10–14% / 15–19%，下限有 10% vs 11% 冲突，**都不采用**）
- Mercado Envios 运费表与免邮门槛（第三方报道的 R$ 数值与 R$79 门槛均未核实）
- 税费：ICMS / Simples Nacional / 其他巴西税（**没有官方页面给出过巴西卖家税率**；第三方报道称平台不代扣卖家税款，未核实）
- 分期 parcelamento 分档与成本承担方
- 退货窗口与退货运费承担方（新品 30 天 / 二手 7 天为第三方报道，二手天数另有冲突说法）
- 声誉 / MercadoLíder 门槛数字
- 免费 Listing（Anúncio Grátis）额度
- 禁售品清单
- Product Ads 最低预算（第三方报道 R$1/天未核实）

巴西站已核实的只有两项事实（2026-11-23）：NF-e 开具要求（Mercado Pago 巴西博客 2026-11-10：平台不替卖家开发票，须 CNPJ + 州税登记 + A1 证书 + 已定税制；**无任何税率**）与 Product Ads CPC 计费 + Ad Rank（Mercado Ads KnowledgeHub）；且 Product Ads 准入条件两处官方来源说法冲突（15 天 + 1/10 笔销售 vs 7 天 + 20 笔销售），须真实浏览器核实后才能定。另外：2026-11-23 文本抓取 `mercadolivre.com.br` 被策略拦截，巴西官方帮助页须用真实浏览器打开核实，见 `references/ml-fee-sources.md` 巴西节复核清单。

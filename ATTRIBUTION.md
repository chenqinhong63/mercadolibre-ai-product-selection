# Attribution

本系统复用了以下 5 个开源项目的结构、模板或公式形状。复用内容均按各自许可证合规使用；各项目的 hosted 服务、付费 API 与品牌均**不是**本系统的依赖。

本仓库的许可证是 MIT（见 `LICENSE`，Copyright (c) 2026 Mercado Libre AI Product Selection System）。

## 1. nexscope-ai/eCommerce-Skills — MIT

- 来源：<https://github.com/nexscope-ai/eCommerce-Skills>
- 许可证：MIT，Copyright (c) 2026 Nexscope AI。
- 复用了什么：竞品 / 价格 / 评论 / 利润报告模板；利润计算器代码骨架（`ProductInput` / `CostBreakdown` / `BreakEvenAnalysis` / `PricingSuggestion` dataclass、批量 CSV/JSON 输入、状态阈值）；跨境 8 维评分矩阵作模板；review 真实性维度 + L1–L4 渐进；到岸成本公式骨架。
- 改了什么：全部 Amazon / TikTok 费率与 Nexscope MCP upsell 已删除；只保留模板与公式骨架，改为 MXN / MLM（墨西哥站）口径；跨境评分矩阵的权重须为美客多重定。
- 未复制：Nexscope 的付费 API 客户端、密钥、品牌 upsell 文案；Nexscope hosted MCP / API 服务不是本系统的依赖（MIT 只覆盖其仓库代码 / 文档，不覆盖其 hosted 服务）。

## 2. AronLEEdev/product-research-skills — MIT

- 来源：<https://github.com/AronLEEdev/product-research-skills>
- 许可证：MIT，Copyright (c) 2026 LEE I HSIU（各子仓库也是 MIT）。
- 复用了什么：确定性评分脚本的结构（band 插值、中位数聚合、null 过滤、确定性排序、Top-3 / runnersUp、顶部可调常量）；流水线 + 交接形态、14 天缓存、计量硬上限、硬停 / null → N/A 规则；评审主题聚类 + PPC 盈亏平衡公式（只复用公式，不复用数据源）。
- 改了什么：Helium 10 / Amazon / 1688 / Profitlee 数据层全部替换为大麦数据 MCP；Amazon 美国 band（价格、收入、评论数、重量等）全部丢弃，按美客多选品 Skill V2.1 重标定；ASIN 改为 MLM `sku_id`；Claude-in-Chrome 抓取改为大麦 MCP 调用。
- 未复制：Helium 10、Amazon、1688、Profitlee 各自的服务与条款；其付费工具不是本系统的依赖（MIT 只覆盖 Skill 代码 / 文本，不覆盖上述第三方服务）。

## 3. timctfl/skillshelf — Apache-2.0

- 来源：<https://github.com/timctfl/skillshelf>
- 许可证：Apache-2.0，维护方 Cartful。
- 复用了什么：评论洞察模板（`extract-review-insights`：主题按频率、客户原话、宣称核对、Confidence Notes、<10 / >500 条处理）；竞品概览模板（`competitor-overview`：用户提供清单、按竞品维度、区分一手 / 三手、Coverage Notes）；基础文档串联（`business-context` + `customer-profile` + `write-positioning-overview`）；Skill 写作规范（`write-skill` / `adapt-skill`、写作指南与 spec）。
- 改了什么：Shopify / DTC 数据源（Shopify CSV、Google Merchant XML、GA4、Yotpo 评论 CSV、品牌官网、G2 / Trustpilot）全部删除，改为大麦数据 MCP；评分、利润、销量趋势、市场报告本身为新建（本仓库没有这些内容可复用）。
- Apache-2.0 合规说明：再分发时须给接收者一份许可证副本；修改过的文件须带显著修改声明；保留源代码形式的版权、专利、商标和署名声明；如有 NOTICE 文件须附上（本仓库根目录未见 NOTICE 文件，分发前须复核）。商标不授权。

## 4. AccioWork/agent-skills — MIT-0

- 来源：<https://github.com/AccioWork/agent-skills>
- 许可证：MIT No Attribution（MIT-0），Copyright 2025 acciowork。无需署名。
- 复用了什么：仅 `SKILL.md` 模板 + 错误处理表写法（章节结构、逐步指令写法、对比表输出写法、批量模式）。
- 改了什么：整个数据源（Accio API、source alibaba、中美默认、Section 301/232、USD、Amazon FBA / Shopify / eBay 受众）全部删除；8 个目标 Skill 除窄关税类比外全部新建。
- 未复制：Accio API 客户端、密钥、品牌文案；Accio API 不是本系统的依赖（MIT-0 只覆盖代码许可，不等于 API 条款；其 API 条款可能变化）。

## 5. FlatNineOrg/ecommerce-skills — MIT（版权方 Cart）

- 来源：<https://github.com/FlatNineOrg/ecommerce-skills>（FlatNineOrg 对 `usecart/ecommerceskills` 的复制 / fork；README 与安装地址仍指向 usecart）
- 许可证：MIT，Copyright (c) 2026 Cart (usecart.com)。**版权方是 Cart，不是 FlatNineOrg**——复用时署名 Cart（usecart.com），2026。
- 复用了什么：Skill 骨架（YAML frontmatter + `# /命令` + System Prompt + Handling input + Error handling + Tools Required + Output Format 模板）；`product-research` 模板；`pricing-intel` 数学（min / max / mean / median / mode / 标准差 / Q1 / Q3 / IQR、离群排除、5–8 桶直方图、Budget / Mid / Premium、定价甜点推理、按样本量的置信度）；`niche-analysis` 结构；`competitor-spy` 并排表；数据诚实写法（不编造、标预估、缺数据明说）。
- 改了什么：全部 10 个 Cart 工具与 Cart MCP / API Key 配置已删除；USD 改为 MXN；新建 MXN 利润 / 费 / 物流 / 退货数学、美客多合规门禁、评论情感分析、带权重和阈值的机会评分公式、证据等级 + 来源 / 时间戳、缓存 / 重试 / 配额管理。
- 未复制：Cart 的付费 API 客户端、密钥、品牌文案；Cart API / Cart MCP 不是本系统的依赖（MIT 只覆盖仓库内容，不覆盖 Cart API 服务）。

## 总声明

- 没有复制 Cart / Nexscope / Accio 的付费 API 客户端、密钥、品牌或 upsell 文案。
- 它们的 hosted 服务（Nexscope MCP / API、Accio API、Cart API、Helium 10、Profitlee 等）都不是本系统的依赖。
- 从各仓库复制的文字 / 代码段，须在文件头注明来源和许可证。

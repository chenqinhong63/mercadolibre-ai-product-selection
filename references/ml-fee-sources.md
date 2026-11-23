# 美客多费率来源日志（Phase 0，2026-11-23；墨西哥 MLM + 巴西 MLB）

> 本文件是费率核查的**来源日志**，不是费率表。
> **本文件里的任何内容在重新核实于官方页面之前，都不得用作系统常量、默认值或计算输入。**
> 核实状态分两档：已核实（附来源 + 访问日期 + 简述）与未核实（附已尝试的方法 + 冲突点 + 应去核实的官方页面）。

## 已核实

### (a) ISR / IVA 代扣 — Mercado Pago 博客

- 来源：<https://www.mercadopago.com.mx/blog/nuevas-retenciones-ventas-en-plataformas>
- 发布日期：2026-05-15；访问日期：2026-11-23。
- 简述：有 RFC 时，ISR 代扣为每笔销售总收入的 2.5%，IVA 代扣为总 IVA 的 50%（即 8%，总 IVA 16%）；无 RFC 时，ISR 代扣 20%，IVA 代扣 16%。自 2026-01-01 起，personas morales（法人）同样适用 2.5% ISR / 50% IVA 代扣。卖家为在墨西哥无常设机构的外国居民，或收款至外国银行账户时，IVA 代扣 100%。代扣是预缴、可抵扣的款项（provisional payments creditable against SAT filings），不是额外税种；平台须在次月前 5 天内开具 CFDI de retenciones。
- **注意**：该来源是 mercadopago.com.mx，不是 mercadolibre.com.mx 卖家中心。代扣率不等于全部税负；最终应缴税额以 SAT 申报为准。
- 可用方式：可作为 `profit-model.md` 中“税费 — ISR / IVA 代扣”的已核实输入，并按上述标注使用。

### (b) Product Ads 计费方式与门槛 — Mercado Ads Knowledge Hub

- 来源：<https://knowledgehub.academy.mercadoads.com/product-ads>
- 访问日期：2026-11-23。
- 简述：Product Ads 按点击付费（CPC-only，“solo pagas cuando una persona hace clic”）；竞价通过 Ad Rank（Listing 质量、相关性、目标 ROAS + 预算）；卖家设定目标 ROAS 与日均预算；预算不累计、不滚存至次日。准入要求：黄色声誉或以上、注册满 15 天以上、至少 1 笔销售（公司）/ 至少 10 笔销售（个人）、无逾期发票。
- **本页未给出 CPC 单价，也未给出最低预算。** 因此广告成本在本系统中只能由用户提供假设并标注，不得引用本页给出任何 CPC 数字。

### (c) 州税 — Mercado Pago 不代扣州税

- 来源：<https://www.mercadopago.com.mx/blog/impuestos-estatales-mexico>
- 访问日期：2026-11-23。
- 简述：Mercado Pago 不代扣州税。
- 可用方式：仅可作为“Mercado Pago 不代扣州税”这一事实；州税本身是否应缴、税率多少，本系统不给数，须按卖家实际情况向税务顾问核实。

## 未核实（不得用作常量）

2026-11-23 尝试文本抓取 mercadolibre.com.mx 卖家中心页面被拦截（blocked for text fetch）；第三方报告之间互相冲突。以下每一项都记录：尝试过什么、冲突在哪里、应去哪个官方页面用真实浏览器核实。

### 1. 佣金比例（Clásica / Premium）

- 已尝试：文本抓取 mercadolibre.com.mx 被拦截；查阅第三方报告。
- 冲突：第三方说法不一，Clásica 有 8–17% 与 8–16% 两个版本，Premium 有 11–21.5% 与 12.5–20.5% 两个版本。**两个版本都不采用。**
- 官方核实页（第三方引用，未独立确认 URL）：卖家中心帮助文章“¿Cuánto pago por vender un producto?”（第三方引用为 ayuda 870）。须在真实浏览器中打开卖家中心核对当前类目费率与生效日期。

### 2. $299 MXN 以下商品的固定费

- 已尝试：文本抓取被拦截；查阅第三方报告。
- 冲突 / 未核实：有 $25 / $30 / $37 三档传闻，分档口径不明。**不得硬编码任何一档。**
- 官方核实页：同上，“¿Cuánto pago por vender un producto?”（ayuda 870，URL 未独立确认）。

### 3. 免费 Listing 额度

- 已尝试：文本抓取被拦截；查阅第三方报告。
- 未核实：有“60 天 / 同时 10 条 / 每年 5 条新品 + 20 条二手”一类说法，未经官方页面确认。**不得用作常量。**
- 官方核实页：卖家中心免费 Listing 相关帮助文章（具体 URL 未独立确认，须在真实浏览器中检索核对）。

### 4. MSI（分期）分档与成本承担方

- 已尝试：文本抓取被拦截；查阅第三方报告。
- 未核实：MSI 分档与由谁承担成本均未核实。
- 官方核实页（第三方引用，未独立确认 URL）：帮助文章“Cantidad de meses sin intereses que ofreces con Premium”（第三方引用为 ayuda 22737）。须在真实浏览器中核对。

### 5. 声誉（reputation）门槛

- 已尝试：文本抓取被拦截；查阅第三方报告。
- 冲突：Mercado Líder 所需的销售额 / 开票额数字在不同来源间冲突。**不得引用任何一组数字。**
- 官方核实页（第三方引用，未独立确认 URL）：声誉相关帮助文章（第三方引用为 ayuda 864）。须在真实浏览器中核对。

### 6. 禁售品清单

- 已尝试：文本抓取被拦截；查阅第三方报告。
- 未核实：完整禁售清单未核实。
- 官方核实页（第三方引用，未独立确认 URL）：`seguro_prohibidos.html`（卖家中心禁售品页面，URL 未独立确认）。须在真实浏览器中核对，并以官方清单为准做合规门禁。

### 7. Mi Página 月费 $437 MXN

- 已尝试：文本抓取被拦截；查阅第三方报告。
- 未核实：$437 MXN/月 的说法未经官方页面确认。**不得用作成本输入。**
- 官方核实页：卖家中心 Mi Página / 订阅相关页面（具体 URL 未独立确认，须在真实浏览器中核对）。

### 8. Mercado Envíos / Full 运费表与免邮门槛

- 已尝试：文本抓取被拦截；查阅第三方报告。
- 未核实：运费成本表与免邮门槛均未核实。
- 官方核实页（第三方引用，未独立确认 URL）：帮助文章“Costos de los Envíos”（第三方引用为 ayuda 40538）。须在真实浏览器中核对。

### 9. 退货窗口与退货运费承担方

- 已尝试：文本抓取被拦截；查阅第三方报告。
- 未核实：退货窗口与退货运费由谁承担均未核实。
- 官方核实页（第三方引用，未独立确认 URL）：卖家中心“Políticas de devolución de productos”。须在真实浏览器中核对。

## 巴西站（MLB）— 2026-11-23 核查

> **关键限制：2026-11-23 的核查中，`mercadolivre.com.br` 帮助 / 卖家中心页面无法直接读取**（`site:mercadolivre.com.br` 搜索返回 0 条；文本抓取官方帮助外链时返回“Domain mercadolivre.com.br is blocked by policy”）。因此本节“已核实”只含能直接打开的 3 个官方集团页面（Mercado Pago 巴西博客 2 篇、Mercado Ads KnowledgeHub 1 篇）；其余全部记入“未核实”，即使多家巴西卖家指南说法一致、并引用同一帮助文章编号。**在真实浏览器打开官方页面核实之前，巴西节的任何数字都不得用作系统常量、默认值或计算输入。**

### 巴西 — 已核实

#### (d) NF-e 开具要求 — Mercado Pago 巴西博客

- 来源：<https://www.mercadopago.com.br/blog/como-emitir-nota-fiscal-mercado-livre>
- 发布日期：2026-11-10；访问日期：2026-11-23。
- 简述：Mercado Livre 不替卖家开发票，平台提供免费开票器（“Faturamento”>“Emissor de NFe”），开票责任在卖家。首次开票前须具备有效的 CNPJ、州税登记（inscrição estadual，商品 NF-e 一般要求）、A1 数字证书、已定税制（Simples Nacional 或一般税制）；每件商品须有正确的 NCM、商品原产地与 CFOP。MEI 向个人消费者销售时一般免于开票（各州与发货方式可能有差异），向企业销售时通常必须开票，须咨询会计。
- **本页没有给出任何税率、ICMS 税率或 Simples Nacional 百分比。** 不得从本页推导任何税率数字。

#### (e) Product Ads 计费方式与 Ad Rank — Mercado Ads KnowledgeHub（巴西）

- 来源：<https://knowledgehub.academy.mercadoads.com/pt/product-ads>
- 访问日期：2026-11-23。
- 简述：Product Ads 按点击付费（CPC，“você só paga quando uma pessoa clica no seu anúncio”）；竞价通过 Ad Rank（广告质量、相关性、目标 ROAS + 预算）；卖家设定目标 ROAS（ROAS Objetivo）与预算；分自动与手动两种活动，另有一个不可删除、可暂停的预配置自动活动。准入要求（本页）：声誉黄色或以上、账号活跃满 15 天、至少 1 笔销售（公司）/ 10 笔销售（个人）、无逾期发票。
- **本页未给出 CPC 单价，也未给出最低预算。** 因此广告成本在本系统中只能由用户提供假设并标注，不得引用本页给出任何 CPC 数字。
- **注意**：本页的准入要求与下面 (f) 的 Mercado Pago 博客说法冲突（见 (f)），不得只取其一。

#### (f) Mercado Ads 说明 — Mercado Pago 巴西博客

- 来源：<https://www.mercadopago.com.br/blog/como-anunciar-no-mercado-ads>
- 发布日期：2026-09-28；访问日期：2026-11-23。
- 简述：Mercado Ads 是 Mercado Livre 的付费广告工具；Product Ads 按点击付费（CPC），是中小卖家常用格式；Display 为横幅/固定位置，面向品牌曝光。准入要求（本页）：“一般须声誉黄色或以上、至少 20 笔销售、账号活跃 7 天以上、无逾期发票、无假冒限制”；Decola 计划活跃状态可能豁免声誉/销售历史要求。
- **冲突**：本页的“7 天 + 20 笔销售”与 (e) KnowledgeHub 的“15 天 + 1 笔（公司）/ 10 笔（个人）”不一致。**在真实浏览器核实当前准入条件之前，不得把任一版本写成已核实门槛。**
- 本页未给出 CPC 单价、R$1/天最低预算或月度账单日。

### 巴西 — 未核实（不得用作常量）

以下每一项均为第三方报道，未在官方页面上独立核实。记录已尝试的方法、冲突点与应去核实的官方页面。

#### B1. 销售佣金（tarifa de venda，Clássico / Premium）

- 已尝试：官方帮助页无法直接读取；查阅多家巴西卖家指南（Appaltum、HunterHub、Nação Digital、EncantoCo、LT Group、MarginMints，均 2026-10/11 访问）。
- 冲突：Clássico 下限有 10% vs 11% 两个版本，Premium 有 15–19% / 16–19% / 15–18% 三个版本；按类目细分的费率表未核实。**所有版本都不采用。**
- 官方核实页（第三方引用，未独立确认 URL）：卖家中心帮助文章“Quanto custa vender um produto?”（第三方引用为 ajuda 870）、“Categorias com desconto na tarifa de venda”（ajuda 51251），以及登录后才能看到的 Simulador de Custos（多家指南称类目精确费率只在模拟器里）。须在真实浏览器中打开核对当前类目费率与生效日期。

#### B2. Mercado Envios 运费表与免邮门槛

- 已尝试：官方帮助页无法直接读取；查阅第三方指南。
- 未核实：运费按单件计、按包装重量（实重与体积重 L×W×H cm ÷ 6,000 取大者）、价格档与声誉颜色定价的结构说法较一致，但**具体 R$ 数值、价格档、R$79 免邮门槛、Flex 固定费（R$6.25 / 6.65 / 7.75 传闻）与 Full 仓储费均未核实**。**不得硬编码任何一档。**
- 官方核实页（第三方引用，未独立确认 URL）：帮助文章“Custos dos Envios no Mercado Livre”（第三方引用为 ajuda 40538 及相关文章）、“Tarifas do Envios Flex”（ajuda 4726）。须在真实浏览器中核对。

#### B3. 税费（ICMS / Simples Nacional / 其他巴西税）

- 已尝试：官方帮助页无法直接读取；查阅第三方指南。
- 未核实：**没有官方页面给出过巴西卖家税率。** 第三方报道称平台不代扣卖家税款，卖家按自身税制（MEI / Simples Nacional / Lucro Presumido）自行申报；MEI 每月固定 R$82.05、Simples Nacional Anexo I 自 4% 起等数字均为第三方报道，**未核实，不得用作输入**。ICMS 各州税率、DIFAL 规则均未核实。2027 年 IBS/CBS 税改（Lei Complementar 214/2025）为第三方报道，不得编入 2026 年模型。
- 官方核实页：ML 帮助“Como calculamos quanto você recebe por venda”、卖家中心税务相关页面，以及巴西会计 / Receita Federal。须向巴西会计核实有效税率。

#### B4. 分期（parcelamento sem juros）分档与成本承担方

- 已尝试：官方帮助页无法直接读取；查阅第三方指南。
- 未核实：Premium 最高 12x 免息、≤R$29.99 无分期、>R$500 可 12x 等分档说法均为第三方报道，且中间档位不完整；成本承担方未核实。**不得用作常量。**
- 官方核实页：ML 帮助分期相关文章（标题与 ajuda 编号未在搜索片段中确认，须在真实浏览器中从“Quanto custa vender”页内检索核对）。

#### B5. 退货窗口与退货运费承担方

- 已尝试：官方帮助页无法直接读取；查阅第三方指南。
- 未核实：新品 30 天、二手 7 天的说法较一致，但二手天数有 5 天 vs 14 天的冲突说法；卖家申诉期限、退货运费由谁承担均未核实。**不得用作常量。**
- 官方核实页：卖家中心“Como funciona a devolução da minha venda?”、“O que fazer quando tem uma devolução”，以及 Compra Garantida 条款。须在真实浏览器中核对。

#### B6. 声誉（reputação）与 MercadoLíder 门槛

- 已尝试：官方帮助页无法直接读取；查阅第三方指南。
- 未核实：绿色声誉 60 天窗口（投诉 ≤2%、卖家取消 ≤1.5%、延迟发货 ≤10%）与 MercadoLíder 奖牌门槛（230 / 575 / 1,725 笔销售，R$37,000 / 118,400 / 296,000）均为第三方报道；旧版数字（60 / 150 / 450 笔）仍在流传，**不得引用任何一组数字**。
- 官方核实页（第三方引用，未独立确认 URL）：“Tudo sobre ser MercadoLíder”、“O que é e como funciona a reputação como vendedor”。须在真实浏览器中核对。

#### B7. 免费 Listing 额度（Anúncio Grátis）

- 已尝试：官方帮助页无法直接读取；查阅第三方指南。
- 未核实：60 天有效期、同时最多 10 条、新品每年最多 5 笔销售、二手每年最多 20 笔销售等说法均未核实。**不得用作常量。**
- 官方核实页：ajuda 870 与 ajuda 1472（第三方引用，未独立确认 URL）。须在真实浏览器中核对。

#### B8. 禁售品清单

- 已尝试：官方政策页未直接读取；查阅第三方汇总。
- 未核实：药品、烟草/电子烟、仿冒品、未获 Anatel 认证的电子产品、需 Anvisa / Inmetro / Mapa 注册而无注册的产品等 30 余类说法为第三方汇总，**不得用作系统拦截清单**。
- 官方核实页：ML“Produtos proibidos”政策页（标题与 URL 未确认，须在真实浏览器中从帮助中心检索定位）。须以官方清单为准做合规门禁。

#### B9. Product Ads 最低预算与其他格式定价

- 已尝试：KnowledgeHub 与 Mercado Pago 博客两篇官方页面已读（见 (e)(f)），均未给出数字；查阅第三方指南。
- 未核实：R$1/天最低日预算、Brand Ads 按 CPM 计费、Display 按程序化计费、14 天归因窗口等说法均为第三方报道，**未核实，不得用作输入**。
- 官方核实页：`https://vendedores.mercadolivre.com.br/nota/o-que-e-e-como-funciona-o-product-ads` 与 `https://vendedores.mercadolivre.com.br/nota/quais-requisitos-devo-cumprir-para-usar-o-product-ads`（两 URL 出现在第三方搜索结果中，未独立打开核实）。须在真实浏览器中打开核对。

### 巴西 — 绝不得从墨西哥复制的项

- ISR 代扣（有 RFC 2.5% / 无 RFC 20%）、IVA 代扣（8% / 16%）、RFC、CFDI、MSI、墨西哥佣金比例与固定费、MXN 价格与门槛——**巴西没有 ISR、没有 IVA、没有 RFC、没有 MSI**。巴西税制为 ICMS（州税）及 PIS/COFINS/IRPJ/CSLL 或 Simples Nacional DAS，且按第三方报道平台不代扣卖家税款（未核实，不得把墨西哥代扣模型套用到巴西）。
- 不得复制 Amazon / 美国站的费率到巴西。

## 真实浏览器复核清单（待办）

在真实浏览器中逐项打开以下官方页面核对，核对后把结果（数值 + 生效日期 + 页面 URL + 核实日期）写回本文件，并把对应项从“未核实”移至“已核实”；未核对前保持“待核实”：

1. “¿Cuánto pago por vender un producto?”（ayuda 870）— 佣金比例、固定费、免费 Listing 额度。
2. “Cantidad de meses sin intereses que ofreces con Premium”（ayuda 22737）— MSI 分档与成本承担方。
3. “Costos de los Envíos”（ayuda 40538）— Mercado Envíos / Full 运费表与免邮门槛。
4. “Políticas de devolución de productos” — 退货窗口与退货运费承担方。
5. 声誉帮助文章（ayuda 864）— 声誉门槛与 Mercado Líder 条件。
6. `seguro_prohibidos.html` — 禁售品清单。
7. Mi Página / 订阅页面 — Mi Página 月费。

> 上述 ayuda 编号与页面名均为第三方引用，URL 未独立确认；复核时以卖家中心站内检索到的当前官方页面为准，并记录实际打开的 URL。

## 巴西站真实浏览器复核清单（待办）

在真实浏览器中逐项打开以下官方页面核对，核对后把结果（数值 + 生效日期 + 页面 URL + 核实日期）写回本文件巴西节，并把对应项从“未核实”移至“已核实”；未核对前保持“待核实”。注意：2026-11-23 文本抓取 `mercadolivre.com.br` 被策略拦截，须用真实浏览器打开：

1. “Quanto custa vender um produto?”（ajuda 870）— 佣金比例（Clássico / Premium，按类目）、固定费、免费 Listing 额度。
2. “Categorias com desconto na tarifa de venda”（ajuda 51251）— 佣金折扣类目。
3. “Custos dos Envios no Mercado Livre”（ajuda 40538 及相关文章）— Mercado Envios 运费表与免邮门槛；“Tarifas do Envios Flex”（ajuda 4726）。
4. 分期帮助文章（标题与 ayuda 编号待检索）— parcelamento 分档与成本承担方。
5. “Como funciona a devolução da minha venda?”、“O que fazer quando tem uma devolução” — 退货窗口与退货运费承担方。
6. “Tudo sobre ser MercadoLíder”、“O que é e como funciona a reputação como vendedor” — 声誉与 MercadoLíder 门槛。
7. “Produtos proibidos”政策页 — 禁售品清单。
8. `vendedores.mercadolivre.com.br/nota/o-que-e-e-como-funciona-o-product-ads` 与 `.../quais-requisitos-devo-cumprir-para-usar-o-product-ads` — Product Ads 准入条件冲突（15 天 + 1/10 笔 vs 7 天 + 20 笔）与最低预算。
9. 登录后 Simulador de Custos — 类目精确佣金（多家指南称精确费率只在模拟器里）。

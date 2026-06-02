# A 股早期多倍股雷达信息源需求与免费/收费划分

验证日期：2026-06-02  
适用规格：`docs/specs/early-multibagger-radar-redesign.md`  
目标：让 MVP 阶段就能用可复核、可交叉验证、可控成本的信息源捕捉早期非共识信号。

## 1. 结论先行

本项目的信息源策略不应该按「贵的数据更好」排序，而应该按「能否更早发现 claim、能否独立验证 claim、能否低成本长期复盘」排序。

MVP 的推荐顺序：

1. 免费官方事实源：交易所、巨潮、监管、政策、政府采购、公共资源交易、专利。
2. 免费或低成本公开足迹：公司官网、客户官网、互动易/上证 e 互动、招聘、产品页面、公众号长文、X/KOL 手动档案。
3. 低成本 API 和开源工具：Tushare Pro 基础权限、手动 CSV、AKShare 研究辅助。
4. 主题相关的单点付费行业数据：只在某条主线确实依赖产品价格、库存、开工率时采购。
5. 专业终端和大额数据库：Wind、iFinD、Choice、RQData 等放到后续阶段，除非 MVP 已证明某类数据能显著提高命中率或降低误报。

最重要的分离原则：

```text
source_rank/source_family 说明证据质量和独立性。
cost_class/access_mode/license_status 说明成本、授权和自动化边界。
LLM 不是信息源，只是解析、比对、总结和推理工具。
```

## 2. 现有需求缺口

当前项目已经有信息可信度分层，但缺少成本和授权分层。

| 位置 | 已有能力 | 缺口 |
| --- | --- | --- |
| `docs/specs/a-share-research-cockpit-mvp.md:126-130` | 定义 A/B/C/D 来源等级。 | 没有区分免费、付费、注册免费、授权受限、不可自动抓取。 |
| `docs/specs/a-share-research-cockpit-mvp.md:133-145` | MVP 首选巨潮、上交所、深交所、Tushare、AKShare，并要求 `source_url`、`source_rank`、`file_hash`。 | 没有 `source_id`、`cost_class`、`access_mode`、`license_status`、`automation_allowed`。 |
| `docs/specs/early-multibagger-radar-redesign.md:93-102` | 定义 `official_disclosure`、`industry_data`、`expert_kol` 等来源家族。 | 没有说明每个来源家族在 MVP 阶段优先用免费还是付费渠道接入。 |
| `docs/specs/early-multibagger-radar-redesign.md:115-143` | 把 X/KOL 作为优质早期线索源，并定义动态等级。 | 没有把 KOL 的手动免费跟踪、官方 API、第三方舆情监控分开。 |
| `cic/models.py:43-50` | `Evidence` 保存 `source_rank`、`source_type`、`source_url`。 | 证据无法追溯到来源目录、授权状态和采购成本。 |
| `cic/rules.py:169-184` | 低等级来源不能直接升级候选。 | 规则只看可信度，不知道来源是否允许自动化、是否付费、是否已过采购复核。 |

因此，本规格新增的是「信息源目录和采购分层」，不是替代 A/B/C/D 证据等级。

## 3. 信息源需求

早期多倍股雷达需要的信息源不是更多新闻，而是更早、更独立、更可复盘的证据。

### 3.1 必须支持的 8 类信号

| 信号类型 | 需要的来源 | MVP 优先渠道 |
| --- | --- | --- |
| 业务拐点 | 订单、客户导入、产能、产品上线、收入拆分 | 公告、客户官网、招投标、政府采购、公司官网 |
| 供需瓶颈 | 涨价、库存下降、开工率变化、交期拉长 | 免费行业新闻初筛，必要时单点采购行业数据 |
| 经营杠杆 | 收入、毛利率、费用率、现金流、合同负债 | 财报、业绩预告、Tushare/RQData/手动 CSV |
| 叙事转事实 | 小作文或 KOL 线索被官方动作验证 | KOL 档案、公告、政策、公开足迹 |
| 技术/产品突破 | 专利、招标参数、客户试用、产品页变化 | 国家知识产权公共服务、客户官网、政府采购 |
| 主题扩散 | 板块强度、龙头/中军/弹性标的扩散 | 行情数据、板块表现、用户自定义 peer |
| 风险证伪 | 问询函、处罚、减持、质押、诉讼、现金流异常 | 交易所监管信息、公告、财报、监管文件 |
| KOL 早期线索 | 产业 KOL、研究员、工程师、渠道商的原创 claim | 手动 curated list，后续再接 X API 或监控服务 |

### 3.2 信息源必须回答的问题

每个来源进入系统前，必须回答：

1. 它能发现哪类早期 claim？
2. 它能验证哪类旧 claim？
3. 它是否独立于已有来源？
4. 它是事实源、指标源、观点源还是情绪源？
5. 它是否免费？如果收费，收费是订阅、点数、终端、API 还是定制合同？
6. 它是否允许程序化采集？
7. 它能否直接触发信号？还是只能生成待验证任务？
8. 它的历史数据能否用于复盘？
9. 它的口径变化和授权变化如何定期复核？

## 4. 新增元数据模型

### 4.1 成本类别

```sql
CREATE TYPE source_cost_class AS ENUM (
  'free_public',
  'free_account',
  'open_source_research',
  'freemium_points',
  'paid_api',
  'paid_terminal',
  'paid_industry_dataset',
  'paid_monitoring',
  'manual_only',
  'restricted_do_not_automate',
  'unknown'
);
```

| cost_class | 含义 | 例子 |
| --- | --- | --- |
| `free_public` | 无登录即可公开访问 | 上交所公告、深交所公告、中国政府采购网 |
| `free_account` | 注册后可浏览或有限使用 | 部分行业网站、投资者互动平台、部分价格页 |
| `open_source_research` | 开源工具或研究用途接口 | AKShare |
| `freemium_points` | 注册可用部分接口，更多权限依赖积分或赞助 | Tushare Pro |
| `paid_api` | 明确按 API、点数、流量、年费收费 | X API、部分数据商 API |
| `paid_terminal` | 专业终端或机构产品 | Wind、iFinD、Choice |
| `paid_industry_dataset` | 行业价格、库存、产量等专业数据 | Mysteel、SMM、卓创、百川盈孚 |
| `paid_monitoring` | 舆情、KOL、研报、招投标监控服务 | X 监控、公众号监控、企业/招投标监控 |
| `manual_only` | 只能人工录入或人工上传，暂不自动化 | KOL 截图、用户产业访谈、付费研报摘要 |
| `restricted_do_not_automate` | 网站声明禁止抓取或授权不明 | 明确禁止机器人、蜘蛛、截屏、抓取的页面 |
| `unknown` | 尚未核验 | 新增来源默认值 |

### 4.2 接入方式

```sql
CREATE TYPE source_access_mode AS ENUM (
  'web_manual',
  'web_scrape_allowed',
  'official_api',
  'vendor_api',
  'csv_upload',
  'terminal_export',
  'browser_cookie',
  'third_party_monitoring',
  'user_manual_note',
  'disabled'
);
```

默认规则：

1. `browser_cookie` 只能用于用户自己可访问的页面，且默认不进入自动任务。
2. `web_scrape_allowed` 必须有 robots、服务条款或明确授权支撑，否则降为 `web_manual`。
3. 付费终端导出的数据必须记录导出时间、终端名、账号备注和许可边界。
4. 用户手动笔记不能伪装成原始事实源，必须保留 `source_family=user_note`。

### 4.3 授权状态

```sql
CREATE TYPE source_license_status AS ENUM (
  'public_terms_ok',
  'account_terms_reviewed',
  'vendor_contract_required',
  'vendor_contract_active',
  'manual_personal_use_only',
  'restricted',
  'unknown'
);
```

授权门禁：

1. `unknown` 不允许自动化采集。
2. `restricted` 不允许自动化采集，也不允许作为系统生产数据源。
3. `manual_personal_use_only` 只能进入个人笔记或手动 evidence，不能自动分发。
4. `vendor_contract_required` 只能进入采购评估，不进入生产。
5. `vendor_contract_active` 必须保存合同范围、到期日和允许用途。

### 4.4 来源目录表

```sql
CREATE TABLE source_catalog (
  source_id TEXT PRIMARY KEY,
  source_name TEXT NOT NULL,
  provider TEXT NOT NULL,
  source_family TEXT NOT NULL,
  source_rank_default source_rank NOT NULL,
  cost_class source_cost_class NOT NULL DEFAULT 'unknown',
  access_mode source_access_mode NOT NULL DEFAULT 'web_manual',
  license_status source_license_status NOT NULL DEFAULT 'unknown',
  official_url TEXT,
  coverage_scope TEXT NOT NULL,
  update_frequency TEXT NOT NULL,
  latency_target TEXT,
  direct_signal_allowed BOOLEAN NOT NULL DEFAULT false,
  automation_allowed BOOLEAN NOT NULL DEFAULT false,
  paid_purchase_required BOOLEAN NOT NULL DEFAULT false,
  replacement_source_ids TEXT[] NOT NULL DEFAULT '{}',
  limitations TEXT NOT NULL DEFAULT '',
  license_notes TEXT NOT NULL DEFAULT '',
  owner_note TEXT NOT NULL DEFAULT '',
  last_verified_at TIMESTAMPTZ NOT NULL,
  next_review_at TIMESTAMPTZ NOT NULL
);
```

应同步扩展：

```sql
ALTER TABLE raw_documents ADD COLUMN source_id TEXT REFERENCES source_catalog(source_id);
ALTER TABLE evidence_observations ADD COLUMN source_id TEXT REFERENCES source_catalog(source_id);
```

## 5. 免费信息源划分

### 5.1 免费官方事实源

这组来源是 MVP 的基础盘，优先级最高。

| source_id | 来源 | cost_class | source_family | 默认等级 | 用途 | 是否可直接触发 |
| --- | --- | --- | --- | --- | --- | --- |
| `sse_announcements` | 上海证券交易所上市公司公告 | `free_public` | `official_disclosure` | A | 沪市公告、定期报告、临时公告 | 是 |
| `szse_announcements` | 深圳证券交易所上市公司公告 | `free_public` | `official_disclosure` | A | 深市公告、定期报告、监管信息 | 是 |
| `cninfo_announcements` | 巨潮资讯网 | `free_public` | `official_disclosure` | A | 深沪京公告、互动、调研、交易公开入口 | 是 |
| `csrc_regulatory` | 中国证监会及派出机构公开信息 | `free_public` | `policy_regulatory` | A | 处罚、立案、监管规则、政策文件 | 是 |
| `exchange_disciplinary` | 交易所监管措施、纪律处分、问询函 | `free_public` | `policy_regulatory` | A | 风险、证伪、问询压力 | 是 |

MVP 处理原则：

1. 先支持手动上传和手动 URL 录入，再做自动抓取。
2. 每份公告必须保存标题、发布时间、文件哈希、原文片段和本地副本。
3. 官方公告可以确认事实，但 AI 对公告的解释仍要拆成「事实、推理、观点」。

### 5.2 免费政策、监管和宏观源

| 来源 | cost_class | source_family | 默认等级 | 用途 |
| --- | --- | --- | --- | --- |
| 国务院、发改委、工信部、财政部、能源局等政策页面 | `free_public` | `policy_regulatory` | A/B | 主题政策、产业方向、补贴、规范 |
| 国家统计局数据 | `free_public` | `policy_regulatory` | B | 宏观和行业统计验证 |
| 央行、外汇局、海关总署 | `free_public` | `policy_regulatory` | B | 宏观、外贸、汇率、流动性 |
| 行业协会公开简报 | `free_public` 或 `free_account` | `industry_data` | B/C | 景气度、产量、库存、价格线索 |

处理原则：

1. 政策源适合发现主题，不适合直接映射到个股候选。
2. 政策 claim 必须补一个公司受益证据或行业指标证据，才能进入强验证。
3. 同一政策被媒体反复解读，只算一个政策来源家族。

### 5.3 免费公开足迹源

这组来源对早期多倍股尤其重要，因为它常常早于财报体现。

| source_id | 来源 | cost_class | source_family | 默认等级 | 可捕捉信号 |
| --- | --- | --- | --- | --- | --- |
| `cnipa_patent` | 国家知识产权公共服务平台 | `free_public` | `public_footprint` | C | 专利、技术方向、研发投入兑现 |
| `ccgp_procurement` | 中国政府采购网 | `free_public` | `public_footprint` | C | 政府采购、订单、客户需求 |
| `ggzy_public_resources` | 全国公共资源交易平台 | `free_public` | `public_footprint` | C | 工程建设、采购、中标、资源交易 |
| `company_website` | 上市公司官网、产品页、投资者关系页 | `free_public` | `public_footprint` | C | 新产品、客户案例、招募渠道、经营变化 |
| `customer_supplier_website` | 客户和供应商官网 | `free_public` | `public_footprint` | C | 客户导入、供应链合作、项目落地 |
| `job_posting_manual` | 招聘网站手动记录 | `manual_only` | `public_footprint` | D/C | 产线扩张、销售扩张、研发方向 |

处理原则：

1. 公开足迹默认不能直接触发候选，只能提高交叉验证分 X。
2. 同一个项目的招标公告、中标公告、合同公告要合并为同一 `claim` 的不同状态。
3. 招聘信息必须降噪，只有岗位数量、地点、技能栈、业务线持续变化才形成 evidence。

### 5.4 免费或低成本投资者互动源

| 来源 | cost_class | source_family | 默认等级 | 用途 |
| --- | --- | --- | --- | --- |
| 互动易 | `free_public` 或 `free_account` | `official_disclosure`/`public_footprint` | C/B | 公司回应、业务口径变化、管理层措辞 |
| 上证 e 互动 | `free_public` 或 `free_account` | `official_disclosure`/`public_footprint` | C/B | 沪市公司回应 |
| 路演平台公开纪要 | `free_public` 或 `manual_only` | `research_media` | C | 调研口径、管理层边际变化 |

处理原则：

1. 互动平台不是公告，不应默认 A 级。
2. 公司回复可作为「公司口径」证据，但必须和财报、公告、客户侧证据交叉验证。
3. 系统要重点追踪措辞变化，例如「暂无」到「正在推进」，或「未涉及」到「已有小批量」。

### 5.5 开源和免费研究工具

| 来源 | cost_class | source_family | 默认等级 | 用途 | 风险 |
| --- | --- | --- | --- | --- | --- |
| AKShare | `open_source_research` | `market_financial_data` | B/C | 研究、原型、交叉验证、补充行情和宏观接口 | 官方说明主要用于学术研究，网页源变化需要维护 |
| 手动 CSV | `manual_only` | `market_financial_data` | B/C | 从终端或网页手动导入行情、财务、估值、行业数据 | 需要记录原始来源和导入人 |
| Tushare 基础权限 | `freemium_points` | `market_financial_data` | B | 日线、基础数据、财务、业绩预告等 | 接口权限和频次受积分或单独权限限制 |

处理原则：

1. AKShare 适合作为研发和辅助验证，不作为唯一生产事实源。
2. Tushare 适合做 MVP 的基础行情/财务 API，但每个接口必须记录积分门槛和更新时间。
3. 手动 CSV 必须带 `source_id`，不能把「用户导入」当作原始数据源。

### 5.6 免费 KOL 和社媒线索

| 来源 | cost_class | source_family | 默认等级 | 用途 |
| --- | --- | --- | --- | --- |
| X/KOL 手动关注清单 | `manual_only` | `expert_kol` | B/C/D 动态 | 早期 claim、产业线索、反方观点 |
| 微信公众号手动摘录 | `manual_only` | `expert_kol`/`research_media` | C/D | 长文、产业链观察、渠道反馈 |
| 雪球、股吧、论坛 | `manual_only` | `social_rumor` | D | 情绪和传闻观察 |

处理原则：

1. 高质量 KOL 可以提高验证优先级，但不能单独升级候选。
2. 每条 KOL claim 必须保存原帖 URL、发布时间、原始摘录、KOL 档案、利益冲突标记。
3. 未经官方 API 或明确授权，不把社媒网页抓取做成后台自动任务。
4. X 官方 API 属于付费或按量 API；MVP 先做手动 curated list，等 KOL 档案验证有效后再采购 API。

## 6. 收费信息源划分

### 6.1 低成本或中成本金融 API

| 来源 | cost_class | source_family | 默认等级 | 适合购买时机 |
| --- | --- | --- | --- | --- |
| Tushare Pro 积分和单独权限 | `freemium_points`/`paid_api` | `market_financial_data` | B | MVP 需要稳定日线、财务、公告、互动、研报等 API 时 |
| JQData/聚宽数据 | `paid_api` | `market_financial_data` | B | 需要量化研究、行情和因子接口时 |
| RQData/米筐 | `paid_api` | `market_financial_data` | B | 需要 point-in-time 财务、因子回测、避免未来数据时 |

采购判断：

1. 如果只是每日持仓评分，Tushare 基础权限加手动 CSV 足够。
2. 如果要做 5/20/60 日信号复盘和因子验证，优先评估 RQData 或其他具备 PIT 口径的数据源。
3. 如果需要盘中策略、分钟级数据或实时新闻，另开独立需求，不混入 MVP。

### 6.2 专业金融终端

| 来源 | cost_class | source_family | 默认等级 | 价值 | MVP 建议 |
| --- | --- | --- | --- | --- | --- |
| Wind | `paid_terminal` | `market_financial_data`/`research_media`/`industry_data` | B/C | 覆盖全球市场、A 股公告、盈利预测、宏观行业、新闻研报、Excel/API | 暂不采购，除非已有账号或需要终端导出 |
| 同花顺 iFinD | `paid_terminal` | `market_financial_data`/`research_media`/`industry_data` | B/C | 智能投研、产业链、宏观指标、工商数据、资讯事件 | 暂不采购，优先作为竞品和人工参考 |
| 东方财富 Choice | `paid_terminal` | `market_financial_data`/`research_media` | B/C | 金融终端、量化 API、AI 搜索/问答、研报摘要 | 暂不采购，优先使用公开网页和手动导出 |

处理原则：

1. 专业终端适合提高覆盖面和效率，不一定提高早期非共识捕捉能力。
2. 终端数据如果通过导出进入系统，必须标记 `access_mode=terminal_export`。
3. 终端研报和新闻默认 C 级，不能替代一手公告和行业数据。

### 6.3 行业高频数据和产业数据库

| 来源 | cost_class | source_family | 默认等级 | 适用主题 |
| --- | --- | --- | --- | --- |
| Mysteel | `paid_industry_dataset` | `industry_data` | B/C | 钢铁、黑色、有色、能源化工、农产品、新能源材料 |
| SMM 上海有色网 | `paid_industry_dataset` | `industry_data` | B/C | 有色金属、稀土、锂电材料、金属价格 |
| 卓创资讯 | `paid_industry_dataset` | `industry_data` | B/C | 化工、能源、农产品、周期品 |
| 百川盈孚 | `paid_industry_dataset` | `industry_data` | B/C | 大宗商品、化工、周期品 |
| 隆众资讯 | `paid_industry_dataset` | `industry_data` | B/C | 能源化工、化工品价格和库存 |

采购判断：

1. 只有当某个主题的核心驱动是价格、库存、开工率、供需缺口时才采购。
2. 每次只采购一个核心主题所需的数据，不做大而全。
3. 采购前用免费新闻、公告、协会数据验证两周，证明该主题确实需要高频数据。
4. 明确禁止抓取声明的网站，必须走会员、API、终端或人工记录。

### 6.4 企业、招投标和信用聚合服务

| 来源 | cost_class | source_family | 默认等级 | 价值 |
| --- | --- | --- | --- | --- |
| 企查查/天眼查/爱企查等 | `paid_api`/`paid_monitoring` | `public_footprint` | C | 工商、股权、司法、招投标、风险监控 |
| 招标雷达、千里马等招投标聚合 | `paid_monitoring` | `public_footprint` | C | 关键词监控、中标通知、行业项目筛选 |
| 企业信用和法院数据 API | `paid_api` | `public_footprint`/`policy_regulatory` | C/B | 风险排雷、诉讼、失信、行政处罚 |

采购判断：

1. 公开官方源能覆盖的先不用买聚合服务。
2. 如果人工筛招标和工商风险每天超过 30 分钟，再采购监控型服务。
3. 聚合服务的原始来源仍要保存，不能只保存聚合平台摘要。

### 6.5 KOL、社媒和舆情 API

| 来源 | cost_class | source_family | 默认等级 | 价值 | 风险 |
| --- | --- | --- | --- | --- | --- |
| X API | `paid_api` | `expert_kol`/`social_rumor` | B/C/D 动态 | 官方程序化访问 X 公共对话、搜索、趋势、流式跟踪 | 按量付费，成本随 usage 变化 |
| 第三方社媒监控 | `paid_monitoring` | `expert_kol`/`social_rumor` | C/D | 公众号、新闻、论坛、舆情关键词监控 | 授权、覆盖和噪声需验证 |
| 研报/新闻监控终端 | `paid_monitoring` | `research_media` | C | 观点差异、行业线索、催化日历 | 版权限制，不能自动分发全文 |

采购判断：

1. 先用 20 到 50 个 curated KOL 手动档案跑 4 周，统计 claim 命中率和噪声。
2. 只有当 KOL claim 能稳定产生待验证任务，且人工收集成为瓶颈，才接 X API 或监控服务。
3. KOL API 的结果必须经过 `source_profiles` 和 `independence_group` 去重。

### 6.6 LLM 推理 API

LLM 费用应归入分析处理层，不归入证据源。

| 来源 | cost_class | source_family | 默认等级 | 用途 |
| --- | --- | --- | --- | --- |
| 智谱 Coding Plan API、OpenAI API、其他 LLM API | `paid_api` | `analysis_tool` | 不适用 | 解析公告、归并 claim、生成反方证据、输出报告 |

处理原则：

1. LLM 输出不能单独成为 evidence。
2. LLM 生成的每条 claim 必须指向原始来源。
3. 所有 LLM 调用要记录模型、prompt 版本、输入文件 ID、输出 JSON 和人工修订。
4. API key 只允许通过环境变量或 secrets 管理，禁止写入文档、issue、测试数据和前端代码。

## 7. MVP 信息源目录

MVP 第一版建议只启用以下目录。

| 优先级 | source_id | 收费/免费 | 用途 | 产出 |
| --- | --- | --- | --- | --- |
| P0 | `cninfo_announcements` | 免费公开 | 公告、定期报告、澄清、风险 | A 级 evidence、风险/证伪 |
| P0 | `sse_announcements` | 免费公开 | 沪市公告和监管 | A 级 evidence |
| P0 | `szse_announcements` | 免费公开 | 深市公告和监管 | A 级 evidence |
| P0 | `exchange_disciplinary` | 免费公开 | 问询函、纪律处分、监管措施 | 风险证据 |
| P0 | `ccgp_procurement` | 免费公开 | 政府采购、订单线索 | public_footprint evidence |
| P0 | `ggzy_public_resources` | 免费公开 | 公共资源交易、中标、工程 | public_footprint evidence |
| P0 | `cnipa_patent` | 免费公开 | 专利和技术方向 | 技术路径验证 |
| P0 | `company_website` | 免费公开 | 产品页、客户案例、IR 信息 | 公开足迹 |
| P0 | `curated_kol_manual` | 手动免费 | X、公众号、产业 KOL claim | 弱信号收件箱 |
| P1 | `tushare_basic` | 积分/低成本 | 日线、财务、业绩预告、质押、回购等 | B 级指标 |
| P1 | `akshare_research` | 开源研究 | 原型、补充、交叉验证 | 辅助数据 |
| P1 | `manual_csv` | 手动 | 终端或网页导出数据 | 临时指标 |
| P2 | `industry_single_vendor` | 主题单点付费 | 核心主题价格、库存、开工率 | B/C 行业验证 |
| P2 | `x_api_kol` | 付费 API | KOL 自动监控 | KOL claim 自动入队 |
| P3 | `rqdata_pit` | 付费 API | 历史复盘、PIT 财务、因子验证 | 复盘和回测 |
| P3 | `wind_ifind_choice_terminal` | 付费终端 | 大覆盖、研报、宏观行业、导出 | 人工参考和导出 |

## 8. 采购门槛

付费源不得因为「看起来专业」而接入。必须先通过采购评审。

### 8.1 付费源准入条件

付费源至少满足 4 条才允许采购：

1. 能覆盖至少 2 类早期信号，或覆盖 1 条用户正在重点跟踪的核心主线。
2. 能提供免费源无法稳定获得的口径、时效、历史或自动化能力。
3. 有明确授权路径，允许个人或本项目用途使用。
4. 能映射到 `source_family`，并能输出结构化字段。
5. 能保存原始记录、发布时间、更新时间和数据版本。
6. 能在 2 周 pilot 中产生至少 5 条有效待验证任务，或减少至少 30% 手动收集时间。
7. 成本上限可控，并有替代免费源或降级方案。

### 8.2 付费源试用指标

| 指标 | 目标 |
| --- | --- |
| 有效线索率 | 进入 `validation_queue` 的线索占比不低于 20% |
| 独立验证贡献 | 至少能贡献一个非已有来源家族 |
| 噪声率 | 明显无关或重复线索低于 60% |
| 人工节省时间 | 每周节省不少于 2 小时，或显著降低漏看风险 |
| 复盘可用性 | 至少保留 6 个月历史，且有发布时间/观察时间 |
| 授权清晰度 | `license_status` 不能是 `unknown` |

### 8.3 明确不建议 MVP 采购

1. 为了「看起来像专业终端」采购 Wind/iFinD/Choice。
2. 为了全市场扫描一次性买多个行业数据库。
3. 为了 KOL 自动化而在没有 KOL 档案验证前购买 X API。
4. 为了盘中交易而购买实时分钟和盘口数据。
5. 为了研报摘要而购买无法保存原始引用和版权边界不清的研报库。

## 9. 免费/收费与信号动作矩阵

| 来源成本 | 来源可信度 | 允许动作 |
| --- | --- | --- |
| 免费官方 A 级 | A | 可直接触发正式信号，但仍需反方证据和人工复核 |
| 免费公开足迹 C 级 | C | 只能触发弱信号、验证任务、X 分提升 |
| 免费 KOL B/C/D 动态 | B/C/D | 只能触发待验证任务；高质量 KOL 也不能单独升级候选 |
| 开源研究工具 B/C | B/C | 可辅助评分，但需记录原始数据口径和来源 |
| 低成本 API B | B | 可用于行情、财务、指标评分 |
| 付费行业数据 B/C | B/C | 可确认行业景气和供需变化，但要和公司受益证据结合 |
| 付费终端 C/B | C/B | 可提高覆盖和效率，研报观点仍需二次确认 |
| 授权不明或禁止自动化 | 任意 | 不允许自动采集，不允许进入生产源 |

硬规则：

1. 收费不提高 source_rank。
2. 免费不降低 source_rank。
3. 授权不明阻断自动化。
4. `restricted_do_not_automate` 阻断后台任务。
5. KOL、研报、媒体、社媒无论收费还是免费，都不能单独触发候选。

## 10. 前端需求

需要新增一个「信息源」页面，先做轻量版本。

### 10.1 信息源列表

每行显示：

```text
来源名称
收费/免费
来源家族
默认等级
接入方式
授权状态
是否可自动化
是否可直接触发
最近核验日期
下一次复核日期
替代来源
```

筛选器：

1. 免费/收费。
2. source_family。
3. source_rank。
4. license_status。
5. automation_allowed。
6. paid_purchase_required。

### 10.2 来源详情

详情页必须显示：

1. 这个来源贡献过哪些 claims。
2. 这些 claims 后续被哪些来源验证或证伪。
3. 这个来源的命中率、噪声率、重复率。
4. 最近 30 天贡献的有效线索。
5. 授权和费用备注。
6. 替代来源和降级方案。

### 10.3 采购评审卡

每个待购买来源必须生成采购评审卡：

```json
{
  "source_id": "x_api_kol",
  "source_name": "X API KOL monitoring",
  "cost_class": "paid_api",
  "requested_by": "user",
  "why_pay": "manual curated KOL list produced 12 validation tasks in 4 weeks and collection became a bottleneck",
  "signal_types_supported": ["kol_early_claim", "narrative_to_fact"],
  "free_alternatives": ["curated_kol_manual"],
  "license_status": "vendor_contract_required",
  "pilot_success_metrics": {
    "min_valid_tasks_2w": 5,
    "max_noise_rate": 0.6,
    "min_time_saved_hours_per_week": 2
  },
  "decision": "pending"
}
```

## 11. 后端和规则需求

### 11.1 证据入库

每条 evidence 必须引用 `source_id`。

```json
{
  "evidence_id": "ev_20260602_000001_001",
  "source_id": "cninfo_announcements",
  "source_family": "official_disclosure",
  "source_rank": "A",
  "cost_class": "free_public",
  "access_mode": "web_manual",
  "license_status": "public_terms_ok",
  "claim": "公司披露重大合同公告",
  "raw_excerpt": "原文摘录不超过必要长度",
  "source_url": "https://www.cninfo.com.cn/..."
}
```

### 11.2 自动化门禁

自动采集任务启动前必须校验：

```python
def can_run_automated_collection(source):
    return (
        source.automation_allowed
        and source.license_status in {"public_terms_ok", "account_terms_reviewed", "vendor_contract_active"}
        and source.cost_class != "restricted_do_not_automate"
        and source.access_mode in {"official_api", "vendor_api", "web_scrape_allowed"}
    )
```

### 11.3 评分和信号门禁

1. `cost_class` 不参与 R/O/T/X 打分。
2. `source_rank` 和 `source_family` 参与打分和交叉验证。
3. `license_status=unknown` 的来源只能进入 `validation_queue`，不能触发正式信号。
4. `source_family=expert_kol` 的证据必须有 `source_profile_id`。
5. `source_family=social_rumor` 只能生成弱信号或情绪观察。

## 12. 实施拆分

### Phase A：文档和目录

1. 新增 `source_catalog` 种子配置，先用 YAML 或 JSON，不急于数据库迁移。
2. 为 P0/P1 来源建立默认条目。
3. 在信号审计卡里显示 `source_id`、`cost_class`、`license_status`。
4. 对 KOL 手动来源建立 `curated_kol_manual`。

### Phase B：后端模型

1. 扩展 `Evidence` 模型，新增 `source_id`、`source_family`、`cost_class`、`license_status`。
2. 增加来源目录加载器。
3. 增加自动化门禁函数。
4. 对现有低等级来源不能升级候选的测试，补充授权门禁测试。

### Phase C：前端页面

1. 新增信息源页面。
2. 新增来源详情抽屉或详情页。
3. 在信号卡和证据包中展示收费/免费、授权和来源家族。

### Phase D：采购和复盘

1. 新增采购评审卡。
2. 统计来源有效线索率、误报率、被验证率。
3. 每月输出来源复盘：哪些免费源贡献最大，哪些付费源不值得续费。

## 13. 验收标准

1. 系统中每个来源都有 `source_id`、`source_family`、`source_rank_default`、`cost_class`、`access_mode`、`license_status`。
2. 任意 evidence 都能追溯到 `source_catalog`。
3. `license_status=unknown` 或 `restricted` 的来源无法启动自动采集任务。
4. `cost_class` 不会影响来源可信度评分。
5. KOL 来源没有 `source_profile_id` 时不能入库为 `expert_kol`。
6. 单一 KOL 来源无论是否付费，都不能让 claim 进入候选状态。
7. 付费源没有采购评审卡时不能标记为生产启用。
8. 信息源页面可以按免费/收费、来源家族、授权状态、可自动化过滤。
9. 信号审计卡显示每条证据的收费/免费状态和授权状态。
10. 每月复盘报告能按来源统计有效线索、验证成功、证伪和噪声。

## 14. 测试计划

| 层级 | 测试 |
| --- | --- |
| Unit | `source_catalog` schema 校验、成本类别枚举、授权门禁、KOL 必须绑定档案 |
| Unit | `cost_class` 不影响 `source_rank` 和 X 分 |
| Integration | evidence 入库时必须引用有效 `source_id` |
| Integration | `license_status=restricted` 的来源不能创建自动采集 job |
| Integration | 付费源没有采购评审卡时不能启用 |
| UI | 信息源页面筛选免费/收费、授权状态、来源家族 |
| UI | 信号审计卡展示来源成本和授权 |
| Regression | 现有低等级来源不能直接升级候选的规则仍然成立 |

## 15. 关键风险

1. 免费网页变化导致采集失效：P0 先支持手动 URL 和本地文件，自动化逐步接入。
2. 授权不明导致合规风险：默认 `unknown` 阻断自动化。
3. 付费源造成虚假安全感：收费不提高 source_rank。
4. KOL 噪声污染：KOL 只生成待验证任务，必须跨来源验证。
5. 研报版权风险：只保存必要摘录和元数据，不保存或分发全文。
6. 数据口径不一致：每个数据源必须记录更新时间、字段口径和来源版本。
7. LLM 幻觉：LLM 输出不是 evidence，必须指向原始来源。

## 16. 参考核验

本规格核验过的代表性官方或源头页面：

1. 上海证券交易所上市公司公告：https://www.sse.com.cn/disclosure/listedinfo/announcement/
2. 深圳证券交易所上市公司公告：https://www.szse.cn/disclosure/listed/notice/index.html
3. 巨潮资讯网：https://www.cninfo.com.cn/new/index
4. Tushare 积分与权限：https://tushare.pro/document/1?doc_id=290
5. Tushare API 权限说明：https://tushare.pro/document/1?doc_id=108
6. AKShare 项目概览：https://akshare.akfamily.xyz/introduction.html
7. Ricequant RQData A 股财务数据：https://www.ricequant.com/doc/rqdata/python/stock-mod
8. X API：https://docs.x.com/x-api/introduction
9. X Enterprise API Pricing：https://docs.x.com/enterprise-api/getting-started/pricing
10. 中国政府采购网：https://www.ccgp.gov.cn/
11. 全国公共资源交易平台：https://www.ggzy.gov.cn/
12. 国家知识产权公共服务平台：https://ggfw.cnipa.gov.cn/
13. Wind 金融终端：https://www.wind.com.cn/portal/zh/WFT/index.html
14. 同花顺 iFinD：https://aifind.com/
15. 东方财富 Choice：https://choice.eastmoney.com/
16. Mysteel Data：https://mysteeldatahub.com/
17. 上海有色网 SMM：https://www.smm.cn/
18. 百川盈孚：https://www.baiinfo.com/

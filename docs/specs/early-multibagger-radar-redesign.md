# 早期非共识多倍股雷达需求规格

验证日期：2026-06-02

工程架构：本规格的 agent-native 实施方案见 `docs/specs/agent-native-radar-architecture.md`。该架构要求 Agent 负责发现、提取、归因、比对和解释，规则引擎负责评分、门禁和状态迁移。

## 1. 重新定位

当前产品不应该继续叫「A 股投研驾驶舱」作为核心定位。驾驶舱天然偏向展示已发生的事实、持仓状态和日报摘要，这会把系统推向普通自选股工具、公告摘要器和静态评分表。

新定位：

> 早期非共识多倍股雷达，用来跟踪 1 年内存在显著上行可选性的标的，但不预测涨跌，不自动给买卖指令。

它的核心任务不是回答「这只股票现在好不好」，而是持续回答：

1. 这个标的是否出现了早期弱信号？
2. 弱信号来自哪个来源家族，独立性如何？
3. 过去系统或用户如何描述过这个逻辑，现在发生了什么变化？
4. 哪些证据互相印证，哪些证据互相矛盾？
5. 如果它要在 12 个月内成为多倍股，需要按时间顺序兑现哪些里程碑？
6. 哪个条件一出现，就说明这条多倍路径应被降级、过期或证伪？

系统输出仍是研究状态和人工复核建议，不是无条件投资建议。

## 2. 已核实现状

当前代码已经能生成一个本地优先的投研 MVP，但它的结构决定了它只能做「今日摘要」，难以成为早期机会发现系统。

| 位置 | 当前能力 | 对多倍股雷达的缺口 |
| --- | --- | --- |
| `README.md:3-9` | MVP 明确围绕 Top 3 变化、假设体检、横向比较、风险雷达、下一验证点。 | 这些是投研产出，但不是早期信号发现、交叉验证和历史演化系统。 |
| `cic/models.py:41-145` | 数据模型有 `Evidence`、`Score`、`Signal`、`ThesisCheck`、`RiskRadar`、`PeerComparison`、`ValidationPoint`、`DailyBrief`。 | 没有 versioned claim、来源家族、独立证据组、矛盾关系、弱信号队列、12 个月路径。 |
| `cic/rules.py:84-166` | `score_holding` 基于当前输入、事件、来源等级、20 日相对强弱、估值分位和风险词计算 R/O/T/Q。 | 评分是当下快照，不衡量「非共识早度」「拐点斜率」「交叉验证强度」「上行路径完整度」。 |
| `cic/rules.py:169-184` | `action_from_score` 用 R/O/T/Q 和来源等级生成候选、等待、风险复核等状态。 | 低等级来源只能被挡住，不能进入可管理的弱信号孵化流程。 |
| `cic/rules.py:187-212` | `evidence_for_holding` 从事件或用户输入生成证据包。 | 没有按来源家族去重，没有判断独立性，也没有要求反向来源或冲突来源。 |
| `cic/rules.py:215-249` | `build_signal` 生成信号卡，并用 `score_before={"R": score.R - 5, "T": score.T - 4}` 模拟前值。 | `score_before` 不是历史记录，无法真实回答「过去怎么说，现在变了什么」。 |
| `cic/report.py:20-95` | 每次请求独立分析持仓，生成 brief、scores、evidence、LLM 状态。 | 没有跨报告读取历史 claims，也没有对旧结论做 diff。 |
| `cic/storage.py:15-48` | JSON store 只保存 reports 和 decisions。 | 没有持久化证据图谱、claim 修订、验证任务、source observation。 |
| `web/index.html:20-95` | 首页是持仓 JSON 输入、Top 3 变化、假设体检、风险、验证点、横向比较、信号审计。 | 首屏没有弱信号收件箱、交叉验证矩阵、过去/现在差异、12 个月路径和证伪地图。 |
| `tests/test_rules.py:8-25` | 测试低等级来源不能升级候选。 | 没有测试低等级来源如何进入孵化队列、如何被独立证据升级。 |

根因：当前 MVP 是「评分后解释」，不是「弱信号到强证据的演化系统」。

## 3. 竞品和方法论观察

外部产品和研究给出三个明确启发：

1. 终端和数据平台强在集成与覆盖。Bloomberg Anywhere 强调金融专业人士需要持续访问新闻、数据和分析；Koyfin 的官方材料强调自定义 dashboard、watchlist、筛选、图表、新闻和组合工具整合在一个工作流里。
2. AI 市场情报强在跨文档检索和一手资料。AlphaSense 官方平台页强调跨大量研究文档寻找公司、数据和主题信息；Quartr API 官方文档强调结构化一手 IR 数据，包括事件、实时/历史 transcript、filings、reports 和 slide presentations。
3. 多倍股研究不支持只靠单一传统指标。Yartseva 的 multibagger 工作论文摘要指出，未来大赢家难以只用现金流、盈利或 EPS 等传统基本面指标识别，但 size、value、profitability、free cash flow yield、投资模式、EBITDA 增长、复杂 momentum 和宏观环境等变量有解释价值。Jegadeesh 的收入增长论文摘要指出，大 revenue surprise 之后存在异常回报，且分析师对永久影响吸收偏慢。

结论：本产品不应复制终端，也不应做泛 AI 搜索。它应该补一个空白：

> 为个人 A 股投研维护「早期弱信号 - 交叉验证 - 历史差异 - 未来路径 - 证伪复盘」的专属记忆系统。

## 4. 产品原则

```text
弱信号可收纳
来源独立可计算
历史判断可对比
未来路径可验证
证伪条件可执行
错过与误报可复盘
```

新增宪法：

1. 系统可以记录低等级弱信号，但不能把低等级弱信号直接升级为候选。
2. 任何升级都必须说明跨了哪几个来源家族，以及这些来源是否独立。
3. 每条新证据必须对比旧 claim：确认、细化、矛盾、过期、证伪或无关。
4. 每个高潜标的必须有 12 个月路径，不允许只有「看好逻辑」。
5. 每个路径必须有失败路径和 kill condition。
6. 系统必须优先显示「下一步要验证什么」，而不是优先显示「AI 怎么评价」。
7. 多倍股雷达默认是高风险研究工具，任何交易动作都必须人工确认。

## 5. 早期信号体系

### 5.1 信号类型

| 类型 | 典型早期表现 | 可观察来源 | 风险 |
| --- | --- | --- | --- |
| 业务拐点 | 订单、产能、客户导入、产品价格、销量、库存周转出现变化 | 公告、定期报告、行业数据、招投标、产品价格 | 财报尚未兑现，可能只是一次性事件 |
| 叙事转事实 | 小作文、产业链传闻、政策线索开始出现官方文件或公司动作 | 政策文件、公告、投资者互动、新闻、用户笔记 | 低等级来源污染判断 |
| 供需瓶颈 | 产能利用率、涨价、缺货、交期、库存下降 | 行业数据、渠道数据、公司公告、客户公告 | 周期顶点误判 |
| 经营杠杆 | 收入增速、毛利率、费用率、现金流出现组合拐点 | 财报、业绩预告、业绩快报 | 会计口径或一次性因素 |
| 资本/治理变化 | 回购、股权激励、实控人变化、质押下降、减持结束 | 公告、监管文件 | 治理信号容易误读 |
| 主题扩散 | 龙头强势后，中军和弹性标的开始跟随 | 行情、板块强度、同主题 peer | 资金驱动可能先于基本面，也可能纯投机 |
| 专业 KOL 早期线索 | X、公众号、播客、产业社区里的专业 KOL 提前指出订单、产品、客户、价格或产业链变化 | KOL 原帖、长文、纪要、附带截图/链接/数据源 | 容易混入持仓喊单、利益冲突和二手消息 |
| 另类公开足迹 | 招聘、专利、招投标、供应商/客户公告、产品上线 | 招聘网站、专利检索、政府采购、客户官网 | 数据噪音高，必须二次验证 |

### 5.2 来源家族

来源家族用于判断证据质量和独立性；免费/收费、授权和自动化边界应由独立的信息源目录管理。具体划分见 `docs/specs/information-source-cost-classification.md`，后续实现时不得用「付费」替代 `source_rank`，也不得用「免费」降低官方事实源等级。

| 家族 | source_family | 默认等级 | 是否独立计数 |
| --- | --- | --- | --- |
| 交易所/巨潮/公司公告 | official_disclosure | A | 是 |
| 财务和行情数据库 | market_financial_data | B | 是 |
| 政府/监管/政策文件 | policy_regulatory | A/B | 是 |
| 行业价格/产量/库存数据 | industry_data | B/C | 是 |
| 招投标/专利/招聘/客户发布 | public_footprint | C/D | 是，但只能作为弱验证 |
| 券商研报/媒体新闻 | research_media | C | 是，但同源观点需降权 |
| 专业 KOL / X / 产业社区 | expert_kol | B/C/D 动态 | 是，但必须绑定来源档案 |
| 社媒/论坛/传闻 | social_rumor | D | 只可记录，不可升级 |
| 用户手动观察 | user_note | C/D | 取决于附件证据 |

独立性规则：

1. 同一篇文章被多个媒体转载，只算 1 个 `independence_group`。
2. 同一公司公告和基于该公告的新闻解读，最多只算公告一个强证据。
3. 同一券商研报系列更新，最多只算同一来源家族一次。
4. 同一 KOL 的连续转发、复述和补充帖，最多只算一个 `independence_group`。
5. 高质量 KOL 可以作为优先级很高的早期线索源，但不能替代公告、财务、行业数据或公开足迹确认事实。
6. 社媒热度只能提高「需要验证」优先级，不能提高候选置信度。
7. A/B 级证据可以确认或证伪 claim；C/D 级证据只能提出或辅助验证 claim。

### 5.3 专业 KOL 来源档案

X 上的产业 KOL、基金经理、卖方/买方研究员、工程师、渠道商、产业链从业者，常常比公告和财报更早暴露非共识线索。系统必须把这类来源从普通社媒里单独拆出来，作为「优质线索源」管理。

但 KOL 的高价值来自长期可审计记录，而不是粉丝数。每个 KOL 必须先进入 `source_profiles`，再参与评分。

| 维度 | 分值 | 说明 |
| --- | ---: | --- |
| 身份和领域稳定性 | 0-20 | 是否长期专注同一产业/主题，是否能识别真实身份或机构背景 |
| 历史命中率 | 0-25 | 过去 claim 是否被公告、财报、行情或行业数据验证 |
| 证据纪律 | 0-25 | 是否给出原始链接、截图、数据口径、渠道来源或可复核事实 |
| 利益冲突透明度 | 0-10 | 是否披露持仓、商业关系、广告或付费推广 |
| 原创信息比例 | 0-10 | 是否提供原创产业观察，而不是搬运新闻和研报 |
| 可证伪程度 | 0-10 | 是否给出明确时间窗口、验证点和失败条件 |

KOL 动态等级：

| `kol_quality_score` | 允许 source_rank | 系统解释 |
| ---: | --- | --- |
| >= 80 | B | 优质早期线索源，可提高验证优先级和 X 上限，但不能单独触发候选 |
| 50-79 | C | 可进入验证队列，需要独立来源确认 |
| < 50 | D | 普通社媒线索，只记录不升级 |

硬性降级规则：

1. 匿名账号、营销号、纯情绪喊单账号最高只能是 D。
2. 只给目标价、涨幅想象或交易口号，不给事实依据，最高只能是 D。
3. 未披露明显利益冲突，且多次出现反向诱导或删除历史帖，降级到 D 并标记 `conflict_flags`。
4. KOL 原创线索即使为 B，也只能把 claim 推到 `validation_queue` 或 `evidence_convergence`；进入 `asymmetric_candidate` 必须至少再有一个 official_disclosure、market_financial_data、industry_data 或 public_footprint 证据。

## 6. 新状态机

旧状态机是股票池状态。新状态机是「多倍路径成熟度」。

```text
raw_weak_signal
  ↓
validation_queue
  ↓
evidence_convergence
  ↓
inflection_watch
  ↓
asymmetric_candidate
  ↓
manual_action_review
  ↓
confirmed_plan / ignored / falsified / expired
```

| 状态 | 含义 | 进入条件 | 用户动作 |
| --- | --- | --- | --- |
| `raw_weak_signal` | 单个早期线索，可能很弱 | 任意来源捕捉到可命名 claim | 不行动，设验证任务 |
| `validation_queue` | 弱信号值得查证 | E >= 50 或用户手动 pin | 补证据、找反方 |
| `evidence_convergence` | 至少两个独立来源支持 | X >= 50，且没有 A 级反证 | 看是否出现业务拐点 |
| `inflection_watch` | 拐点正在形成但未充分兑现 | I >= 55，X >= 60 | 建立 30/90/180 天验证点 |
| `asymmetric_candidate` | 上行路径明确，风险仍可控 | X >= 65，I >= 60，U >= 65，D 为 A/B | 打开人工复核 |
| `manual_action_review` | 允许进入交易计划讨论 | 用户确认候选并记录假设 | 只由用户决策 |
| `confirmed_plan` | 已进入用户计划或持仓观察 | 用户确认 | 跟踪证伪和兑现 |
| `ignored` | 用户认为噪音 | 用户忽略 | 仍保留历史 |
| `falsified` | 核心 claim 被证伪 | A/B 级反证或 kill condition 命中 | 复盘 |
| `expired` | 到期未验证 | 关键里程碑过期 | 降级或关闭 |

## 7. 新评分体系

旧 R/O/T/Q 保留为成熟候选阶段的二级评分。雷达阶段新增 5 个主维度：

```text
E：Earlyness，非共识早度
X：Cross Validation，交叉验证强度
I：Inflection，业务/业绩拐点强度
U：Upside Optionality，12 个月上行路径可选性
D：Downside Gate，下行与毁灭性风险门槛
```

### 7.1 E 非共识早度

回答：这个机会是否还没有被充分定价和充分讨论？

| 规则 | 加分/减分 |
| --- | ---: |
| 标的市值小于同主题龙头，且主题仍有扩散空间 | +15 |
| 过去 60 天涨幅显著低于主题龙头，但出现基本面线索 | +15 |
| 主流公告/研报覆盖少，但 A/B 级事实开始出现 | +15 |
| 弱信号发生在财报兑现前 1-2 个季度 | +10 |
| 已经连续涨停或估值分位 > 90% | -25 |
| 只有社媒热度，没有事实变化 | -20 |

### 7.2 X 交叉验证强度

回答：这个逻辑被多少独立证据支持？

| 条件 | X 上限 |
| --- | ---: |
| 只有 D 级社媒或用户备注 | 30 |
| 一个 C 级来源，未独立验证 | 40 |
| 一个 B 级专业 KOL 原创线索，未独立验证 | 55 |
| 两个来源但同一来源家族 | 50 |
| 两个独立来源家族，其中至少一个 B 级 | 65 |
| A 级公告/财报加一个独立 B/C 级来源 | 80 |
| A 级事实、财务数据、行业数据三方一致 | 95 |

### 7.3 I 拐点强度

回答：这是否可能改变未来 1-4 个季度的收入、利润、现金流或估值叙事？

| 观察项 | 加分 |
| --- | ---: |
| 收入增速连续两个季度抬升 | +15 |
| 毛利率或费用率出现经营杠杆 | +15 |
| 订单/产能/客户导入能映射到收入区间 | +20 |
| 行业价格、销量、库存数据支持公司逻辑 | +15 |
| 管理层表述从探索转向量产/交付/收入确认 | +10 |
| 现金流明显弱于利润，或应收/存货异常 | -20 |

### 7.4 U 上行路径可选性

回答：如果逻辑兑现，12 个月内有没有足够大的价格弹性？

| 观察项 | 加分/减分 |
| --- | ---: |
| 市值/收入/利润弹性足以让基本面变化影响估值 | +15 |
| 同主题中存在已被市场奖励的领先样本 | +10 |
| 估值分位不高，或盈利上修可消化估值 | +15 |
| 存在 3 个以上清晰催化里程碑 | +15 |
| 下行风险可被明确 kill condition 控制 | +10 |
| 已被一致预期充分覆盖 | -20 |
| 路径只依赖估值扩张，不依赖事实兑现 | -25 |

### 7.5 D 下行门槛

D 不是加分项，而是阻断项：

| 等级 | 含义 | 系统动作 |
| --- | --- | --- |
| A | 暂无硬风险 | 可进入 `asymmetric_candidate` |
| B | 普通风险，可跟踪 | 可进入候选，但必须显示风险债务 |
| C | 明显风险 | 只能 `inflection_watch`，需人工复核 |
| D | 硬风险或核心证伪 | 直接 `falsified` 或 `excluded` |

## 8. 交叉验证引擎

每条 claim 都要生成一个矩阵，而不是只有证据列表。

```json
{
  "claim_id": "clm_20260602_300000sz_ai_order_001",
  "stock_code": "300000.SZ",
  "claim_text": "公司 AI 应用订单可能进入收入确认前夜",
  "source_family_matrix": {
    "expert_kol": {
      "support": 1,
      "oppose": 0,
      "best_rank": "B",
      "independence_groups": ["x_kol_ai_chain_20260601"],
      "source_profile_ids": ["src_x_ai_chain_researcher"]
    },
    "social_rumor": {
      "support": 1,
      "oppose": 0,
      "best_rank": "D",
      "independence_groups": ["rumor_20260601"]
    },
    "official_disclosure": {
      "support": 0,
      "oppose": 0,
      "best_rank": null,
      "independence_groups": []
    },
    "market_financial_data": {
      "support": 0,
      "oppose": 1,
      "best_rank": "B",
      "independence_groups": ["quarterly_cashflow_2026q1"]
    }
  },
  "cross_validation_score_X": 25,
  "validation_verdict": "weak_signal_only",
  "required_next_evidence": [
    "公告或投资者互动确认订单事实",
    "财报中收入、合同负债或应收变化支持订单兑现",
    "同主题 peer 出现相似业务拐点"
  ]
}
```

升级规则：

1. `X < 40`：只能是弱信号。
2. `40 <= X < 60`：进入验证队列。
3. `X >= 60`：可进入拐点观察，但必须同时有反方证据。
4. `X >= 65` 且 `I >= 60` 且 `U >= 65` 且 `D in A/B`：才可进入非对称候选。
5. `expert_kol` 即使为 B 级，也必须再被至少一个非 KOL 来源家族验证，才允许进入 `asymmetric_candidate`。
6. 任意 A 级证据与核心 claim 直接矛盾，状态必须降级到 `falsified` 或 `manual_review_required`。

## 9. 历史比对引擎

系统必须把每个「判断」当作可修订 claim，而不是每次重新生成一段新报告。

### 9.1 Claim 生命周期

```text
created
  ↓
supported
  ↓
refined
  ↓
partially_contradicted
  ↓
strengthened / weakened
  ↓
confirmed / falsified / expired
```

### 9.2 新证据进入时的 diff 规则

| 新证据与旧 claim 关系 | 系统动作 |
| --- | --- |
| 完全支持 | 新增 `claim_revision`，提高 X 或 I |
| 支持但缩小范围 | 标记 `refined`，更新 claim 文本和适用范围 |
| 同一来源重复 | 只更新 `last_seen_at`，不加分 |
| 时间过期 | 标记 `stale`，降低 E 或 X |
| 与旧 claim 矛盾 | 创建 `contradiction`，要求人工复核 |
| A/B 级证据证伪核心假设 | 状态改为 `falsified` |

### 9.3 历史差异卡

每个重要更新必须输出：

```json
{
  "diff_card_id": "diff_20260602_300000sz_001",
  "stock_code": "300000.SZ",
  "claim_id": "clm_20260602_300000sz_ai_order_001",
  "previous_claim": "公司可能受益于 AI 应用扩散，但收入兑现不清晰。",
  "new_claim": "公司 AI 应用订单有早期迹象，但尚无公告确认，现金流仍是反证。",
  "change_type": "refined_with_counter_evidence",
  "what_changed": [
    "新增 D 级社媒线索",
    "B 级财务数据显示经营现金流未改善",
    "缺少公告或合同负债验证"
  ],
  "score_delta": {
    "E": 12,
    "X": 10,
    "I": 0,
    "U": 5,
    "D": "B_to_C"
  },
  "user_question": "是否值得为该标的设置公告和合同负债验证任务？"
}
```

## 10. 12 个月多倍路径

系统不能只说「可能涨」。它必须把多倍路径拆成可验证的时间表。

```json
{
  "path_id": "path_300000sz_20260602",
  "stock_code": "300000.SZ",
  "path_name": "AI 应用订单从线索到收入确认",
  "created_at": "2026-06-02T20:00:00+08:00",
  "target_window_months": 12,
  "upside_thesis": "如果订单事实被公告确认，并在两个季度内进入收入和现金流，市场可能重估公司 AI 应用业务。",
  "not_a_prediction": true,
  "milestones": [
    {
      "window": "0-30d",
      "must_happen": "找到 A/B 级证据确认订单或客户导入事实",
      "evidence_family_required": ["official_disclosure", "public_footprint"],
      "score_impact_if_hit": {"X": 20, "I": 10},
      "kill_if_missed": "没有任何独立来源，降级为噪音"
    },
    {
      "window": "31-90d",
      "must_happen": "合同负债、收入增速、毛利率至少一项出现改善",
      "evidence_family_required": ["market_financial_data", "official_disclosure"],
      "score_impact_if_hit": {"I": 20, "U": 10},
      "kill_if_missed": "财务数据继续背离，转入证伪复核"
    },
    {
      "window": "91-180d",
      "must_happen": "同主题 peer 也出现业务兑现，板块扩散不是孤立炒作",
      "evidence_family_required": ["market_financial_data", "industry_data"],
      "score_impact_if_hit": {"U": 15, "T": 10},
      "kill_if_missed": "只有个股题材热度，没有基本面扩散"
    },
    {
      "window": "181-365d",
      "must_happen": "收入和利润弹性被连续财报确认",
      "evidence_family_required": ["official_disclosure", "market_financial_data"],
      "score_impact_if_hit": {"I": 25, "X": 10},
      "kill_if_missed": "兑现窗口关闭，路径过期"
    }
  ],
  "base_case": "继续观察，等待公告或财务确认。",
  "upside_case": "证据连续命中后进入人工候选复核。",
  "failure_case": "社媒线索未被公告或财务验证，降级为噪音并复盘。"
}
```

## 11. 新数据模型

MVP 可以继续本地 JSON 存储，但结构要先按可迁移到 PostgreSQL 的表设计。建议第一版用 SQLite 或 JSONL 实现，第二版迁移 PostgreSQL。

### 11.1 SQL 形状

```sql
CREATE TYPE source_rank AS ENUM ('A', 'B', 'C', 'D');
CREATE TYPE claim_status AS ENUM (
  'created',
  'supported',
  'refined',
  'partially_contradicted',
  'strengthened',
  'weakened',
  'confirmed',
  'falsified',
  'expired'
);
CREATE TYPE radar_state AS ENUM (
  'raw_weak_signal',
  'validation_queue',
  'evidence_convergence',
  'inflection_watch',
  'asymmetric_candidate',
  'manual_action_review',
  'confirmed_plan',
  'ignored',
  'falsified',
  'expired'
);

CREATE TABLE evidence_observations (
  evidence_id TEXT PRIMARY KEY,
  stock_code TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  source_rank source_rank NOT NULL,
  source_family TEXT NOT NULL,
  source_profile_id TEXT,
  independence_group TEXT NOT NULL,
  source_url TEXT,
  title TEXT NOT NULL,
  raw_excerpt TEXT NOT NULL,
  extracted_claim TEXT NOT NULL,
  stance TEXT NOT NULL CHECK (stance IN ('support', 'oppose', 'neutral', 'unknown')),
  extraction_confidence NUMERIC NOT NULL CHECK (extraction_confidence BETWEEN 0 AND 1),
  raw_document_id TEXT
);

CREATE TABLE source_profiles (
  source_profile_id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  handle TEXT NOT NULL,
  display_name TEXT,
  source_family TEXT NOT NULL DEFAULT 'expert_kol',
  expertise_tags TEXT[] NOT NULL DEFAULT '{}',
  kol_quality_score INTEGER NOT NULL CHECK (kol_quality_score BETWEEN 0 AND 100),
  allowed_source_rank source_rank NOT NULL,
  identity_confidence TEXT NOT NULL CHECK (identity_confidence IN ('high', 'medium', 'low', 'unknown')),
  track_record_summary TEXT NOT NULL,
  verified_hit_count INTEGER NOT NULL DEFAULT 0,
  verified_miss_count INTEGER NOT NULL DEFAULT 0,
  conflict_flags TEXT[] NOT NULL DEFAULT '{}',
  last_reviewed_at TIMESTAMPTZ NOT NULL,
  UNIQUE (platform, handle)
);

CREATE TABLE claims (
  claim_id TEXT PRIMARY KEY,
  stock_code TEXT NOT NULL,
  claim_text TEXT NOT NULL,
  claim_type TEXT NOT NULL,
  status claim_status NOT NULL,
  radar_state radar_state NOT NULL,
  first_seen_at TIMESTAMPTZ NOT NULL,
  last_seen_at TIMESTAMPTZ NOT NULL,
  current_scores JSONB NOT NULL,
  source_family_count INTEGER NOT NULL DEFAULT 0,
  contradiction_count INTEGER NOT NULL DEFAULT 0,
  owner_note TEXT
);

CREATE TABLE claim_evidence_links (
  claim_id TEXT NOT NULL REFERENCES claims(claim_id),
  evidence_id TEXT NOT NULL REFERENCES evidence_observations(evidence_id),
  link_type TEXT NOT NULL CHECK (link_type IN ('supports', 'opposes', 'refines', 'duplicates', 'irrelevant')),
  weight NUMERIC NOT NULL CHECK (weight BETWEEN -1 AND 1),
  PRIMARY KEY (claim_id, evidence_id)
);

CREATE TABLE claim_revisions (
  revision_id TEXT PRIMARY KEY,
  claim_id TEXT NOT NULL REFERENCES claims(claim_id),
  revised_at TIMESTAMPTZ NOT NULL,
  previous_claim_text TEXT NOT NULL,
  new_claim_text TEXT NOT NULL,
  change_type TEXT NOT NULL,
  score_before JSONB NOT NULL,
  score_after JSONB NOT NULL,
  diff_summary TEXT NOT NULL,
  triggered_by_evidence_id TEXT REFERENCES evidence_observations(evidence_id),
  review_required BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE contradictions (
  contradiction_id TEXT PRIMARY KEY,
  claim_id TEXT NOT NULL REFERENCES claims(claim_id),
  support_evidence_id TEXT REFERENCES evidence_observations(evidence_id),
  oppose_evidence_id TEXT REFERENCES evidence_observations(evidence_id),
  severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'fatal')),
  contradiction_summary TEXT NOT NULL,
  required_user_decision TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open', 'resolved', 'dismissed'))
);

CREATE TABLE multibagger_paths (
  path_id TEXT PRIMARY KEY,
  stock_code TEXT NOT NULL,
  claim_id TEXT NOT NULL REFERENCES claims(claim_id),
  path_name TEXT NOT NULL,
  target_window_months INTEGER NOT NULL DEFAULT 12,
  upside_thesis TEXT NOT NULL,
  base_case TEXT NOT NULL,
  upside_case TEXT NOT NULL,
  failure_case TEXT NOT NULL,
  not_a_prediction BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE path_milestones (
  milestone_id TEXT PRIMARY KEY,
  path_id TEXT NOT NULL REFERENCES multibagger_paths(path_id),
  window_label TEXT NOT NULL,
  due_date DATE NOT NULL,
  must_happen TEXT NOT NULL,
  evidence_family_required TEXT[] NOT NULL,
  score_impact_if_hit JSONB NOT NULL,
  kill_if_missed TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'hit', 'missed', 'cancelled'))
);

CREATE TABLE validation_tasks (
  task_id TEXT PRIMARY KEY,
  claim_id TEXT NOT NULL REFERENCES claims(claim_id),
  stock_code TEXT NOT NULL,
  task_type TEXT NOT NULL,
  question TEXT NOT NULL,
  required_source_family TEXT[] NOT NULL,
  due_date DATE NOT NULL,
  priority INTEGER NOT NULL CHECK (priority BETWEEN 0 AND 100),
  status TEXT NOT NULL CHECK (status IN ('pending', 'done', 'missed', 'ignored')),
  result_summary TEXT
);
```

### 11.2 JSON Store MVP 形状

```json
{
  "reports": [],
  "decisions": [],
  "evidence_observations": [],
  "source_profiles": [],
  "claims": [],
  "claim_revisions": [],
  "contradictions": [],
  "multibagger_paths": [],
  "path_milestones": [],
  "validation_tasks": []
}
```

## 12. Agent 重组

| Agent | 输入 | 输出 | MVP 是否必须 |
| --- | --- | --- | --- |
| 弱信号捕捉 Agent | 公告、新闻、用户输入、行情异常、公开足迹 | `evidence_observations` 和初始 `claims` | 必须 |
| 来源归因 Agent | 原始来源、URL、文本、发布时间 | `source_rank`、`source_family`、`independence_group` | 必须 |
| KOL 档案 Agent | X/KOL 账号、历史 claim、命中/未命中、利益冲突 | `source_profiles`、`kol_quality_score`、动态 source_rank | 必须 |
| 交叉验证 Agent | claim + evidence graph | `cross_validation_matrix`、X 分数、待验证来源 | 必须 |
| 历史差异 Agent | 新证据 + 旧 claim/revision | `claim_revisions`、diff card、contradictions | 必须 |
| 路径 Agent | 高潜 claim + 估值/财务/催化 | 12 个月 path 和 milestones | 必须 |
| 反方 Agent | 支持证据和路径 | bear case、kill conditions、risk debt | 必须 |
| 主编 Agent | 所有结构化输出 | 雷达 brief 和人工复核队列 | 必须 |
| 数据抓取 Agent | 交易所、巨潮、行情、行业、公开足迹 | 原始文档和 observation | 可先半自动 |

LLM 使用边界：

1. LLM 可提取 claim、归类来源、生成验证问题、总结矛盾和路径。
2. LLM 不可直接改变 `radar_state`，状态由规则引擎根据结构化分数决定。
3. LLM 输出必须走 JSON Schema。
4. 高风险动作前必须 `review_required=true`。

## 13. API 形状

```text
GET    /api/radar/brief
POST   /api/radar/weak-signals
POST   /api/radar/evidence
GET    /api/radar/stocks/{stock_code}
GET    /api/radar/stocks/{stock_code}/evidence-graph
GET    /api/radar/claims/{claim_id}
POST   /api/radar/claims/{claim_id}/decision
POST   /api/radar/run
GET    /api/radar/validation-tasks
POST   /api/radar/validation-tasks/{task_id}/complete
```

### 13.1 创建弱信号

Request:

```json
{
  "stock_code": "300000.SZ",
  "stock_name": "示例公司",
  "signal_text": "某 AI 产业 KOL 称公司产品开始被头部客户试用，并给出客户侧公开页面线索",
  "source_url": "https://x.com/example/status/1",
  "source_family": "expert_kol",
  "source_rank": "C",
  "source_profile": {
    "platform": "x",
    "handle": "@example_ai_chain",
    "kol_quality_score": 72,
    "allowed_source_rank": "C",
    "expertise_tags": ["AI 应用", "产业链跟踪"],
    "conflict_flags": ["持仓未知"]
  },
  "observed_at": "2026-06-02T20:00:00+08:00",
  "user_note": "KOL 线索优先查客户侧公开信息、公告和财报合同负债"
}
```

Response:

```json
{
  "claim_id": "clm_300000sz_20260602_001",
  "radar_state": "validation_queue",
  "scores": {"E": 60, "X": 40, "I": 0, "U": 35, "D": "B"},
  "upgrade_blockers": [
    "只有 KOL 来源，尚未被非 KOL 来源家族验证",
    "缺少 official_disclosure 或 public_footprint 独立验证",
    "缺少财务兑现路径"
  ],
  "validation_tasks": [
    {
      "question": "是否有公告、投资者互动或客户侧公开信息确认产品试用？",
      "required_source_family": ["official_disclosure", "public_footprint"],
      "due_date": "2026-07-02"
    }
  ]
}
```

### 13.2 雷达 Brief

```json
{
  "brief_date": "2026-06-02",
  "weak_signal_inbox": [],
  "cross_validation_queue": [],
  "inflection_watchlist": [],
  "asymmetric_candidates": [],
  "contradictions_requiring_review": [],
  "milestones_due": [],
  "expired_paths": [],
  "generated_by": "cic-radar-rule-engine+llm-adapter"
}
```

## 14. 首版界面

首屏从「今日驾驶舱」改为「信号实验室」。

### 14.1 页面结构

```text
左栏：早期弱信号收件箱
  - 来源等级
  - 非共识早度 E
  - 需要验证的来源家族
  - 最晚验证日期

中栏：交叉验证矩阵
  - 每条 claim 一行
  - 每个来源家族一列
  - 支持/反对/未知用不同状态显示
  - 点击证据显示原文摘录

右栏：12 个月路径和证伪地图
  - 0-30d、31-90d、91-180d、181-365d
  - 必须发生什么
  - 缺什么证据
  - kill condition
```

### 14.2 今日最重要内容排序

排序不再是 Top 3 changes，而是：

1. A/B 级证据与旧 claim 发生矛盾。
2. 弱信号跨越新的独立来源家族。
3. 12 个月路径里程碑命中或错过。
4. 新标的进入 `asymmetric_candidate`。
5. 验证任务即将过期。

### 14.3 公司页

公司页必须固定展示：

```text
当前雷达状态
核心多倍路径
支持证据矩阵
反对证据矩阵
历史 claim 修订时间线
12 个月里程碑
证伪条件
用户历史决策
```

## 15. MVP 实施计划

### Phase 0：保留当前 MVP

不删除当前 R/O/T/Q、风险雷达、假设体检和验证点。它们作为成熟候选阶段的二级视图保留。

### Phase 1：证据观察和弱信号收件箱

1. 扩展 `cic/models.py`：新增 `EvidenceObservation`、`Claim`、`ValidationTask`、`RadarScore`。
2. 扩展 `cic/storage.py`：保存 claims、evidence_observations、validation_tasks。
3. 新增 `/api/radar/weak-signals`。
4. 前端新增弱信号输入和收件箱。

### Phase 2：来源家族和交叉验证

1. 新增 source family normalization。
2. 新增 independence group 去重。
3. 新增 KOL source profile 和动态 source_rank。
4. 新增 `cross_validation_matrix_for_claim`。
5. 写测试：两个同源转载不增加 X，两个独立家族才增加 X，KOL-only 不能升级候选。

### Phase 3：历史差异和 claim revision

1. 每次新增 evidence 时查找关联 claim。
2. 生成 `claim_revision`。
3. 真正使用历史 `score_before`，禁止再模拟前值。
4. UI 显示「过去怎么说 / 现在怎么说 / 为什么变」。

### Phase 4：12 个月路径和证伪地图

1. 新增 `multibagger_paths` 和 `path_milestones`。
2. 每个 `asymmetric_candidate` 必须有至少 4 个里程碑。
3. 里程碑过期自动进入 brief。
4. `kill_if_missed` 命中后降级。

### Phase 5：首屏重设计

1. 首页改为信号实验室。
2. 当前五个 MVP 产出移到「成熟候选」或「报告」区域。
3. 支持从弱信号一路点进证据矩阵、历史差异和路径。

### Phase 6：测试和报告

1. 单元测试覆盖评分、独立性、状态迁移、diff、路径过期。
2. 集成测试覆盖弱信号录入到候选升级。
3. UI 测试覆盖信号实验室首屏。
4. 生成样例「多倍路径报告」供用户过目。

## 16. 验收标准

1. 用户录入 D 级社媒弱信号后，系统必须创建 `raw_weak_signal`，不得创建 `asymmetric_candidate`。
2. D 级弱信号必须生成至少 1 个 `validation_task`，且任务必须指定 `required_source_family`。
3. 两条同源转载证据不得让 `source_family_count` 增加到 2。
4. X/KOL 来源必须创建或引用 `source_profile`，并保存 `kol_quality_score`、`allowed_source_rank` 和 `conflict_flags`。
5. `kol_quality_score >= 80` 的 KOL 可以被映射为 B 级线索源，但系统必须显示「不能单独触发候选」。
6. 单一 KOL 来源无论质量多高，都不得让 claim 进入 `asymmetric_candidate`。
7. 两个独立来源家族支持同一 claim 时，X 分数必须上升，并记录来源家族明细。
8. 新证据进入时，系统必须生成 `claim_revision`，包含 `previous_claim_text`、`new_claim_text`、`score_before`、`score_after`。
9. 不允许再用固定 `R - 5` 或 `T - 4` 伪造 `score_before`。
10. A/B 级反向证据与核心 claim 矛盾时，必须创建 `contradiction` 并 `review_required=true`。
11. 进入 `asymmetric_candidate` 必须满足：X >= 65、I >= 60、U >= 65、D in A/B。
12. 每个 `asymmetric_candidate` 必须有 12 个月路径，且至少包含 4 个 milestone。
13. 每个 milestone 必须有 `must_happen`、`evidence_family_required`、`kill_if_missed`。
14. milestone 过期未完成时，必须进入 `/api/radar/brief` 的 `milestones_due` 或 `expired_paths`。
15. 雷达 brief 必须优先展示矛盾、验证任务过期、独立来源新增和候选升级。
16. 前端首屏必须展示弱信号收件箱、交叉验证矩阵、12 个月路径/证伪地图。
17. 任何 API 响应不得包含无条件买入、卖出、满仓、清仓等交易指令。
18. 所有 LLM 输出必须可被 JSON Schema 校验；校验失败时使用谨慎失败路径。
19. 测试套件必须覆盖以上状态迁移和阻断规则。

## 17. 测试计划

| 层级 | 测试项 | 数量 |
| --- | --- | ---: |
| Unit | source family 归类、KOL 动态等级、independence group 去重 | +10 |
| Unit | E/X/I/U/D 评分和 candidate gate | +8 |
| Unit | claim revision diff、contradiction 创建 | +6 |
| Unit | 12 个月 milestone 过期和 kill condition | +5 |
| Integration | D 级弱信号录入到 validation task | +2 |
| Integration | D 级弱信号经 A/B 级证据升级到 inflection watch | +2 |
| Integration | A/B 级反证降级到 falsified | +2 |
| API | `/api/radar/*` 请求/响应 schema | +6 |
| UI | 首屏三栏渲染、空状态、点击 claim 展开证据 | +4 |
| E2E | 样例多倍路径报告生成 | +1 |

## 18. 子任务拆分

Epic：早期非共识多倍股雷达

| # | 标题 | 优先级 | 预计工作量 | 依赖 |
| --- | --- | --- | --- | --- |
| 1 | 证据观察、claim、validation task 数据模型 | Critical | 1 天 | 无 |
| 2 | JSON/SQLite 存储扩展和历史读取 | Critical | 1 天 | #1 |
| 3 | 弱信号录入 API 和收件箱 | Critical | 1 天 | #1, #2 |
| 4 | 来源家族、独立性和交叉验证引擎 | Critical | 1.5 天 | #1, #2 |
| 5 | claim revision 和历史差异卡 | High | 1.5 天 | #4 |
| 6 | E/X/I/U/D 雷达评分和状态机 | High | 1.5 天 | #4, #5 |
| 7 | 12 个月路径和 milestone 引擎 | High | 1.5 天 | #6 |
| 8 | 信号实验室前端重设计 | High | 2 天 | #3, #4, #7 |
| 9 | LLM JSON Schema 和谨慎失败 | Medium | 1 天 | #1, #4 |
| 10 | 样例报告和完整测试 | High | 1.5 天 | #1-#9 |

依赖图：

```text
#1 数据模型
  └─> #2 存储
        ├─> #3 弱信号 API/UI
        └─> #4 交叉验证
              └─> #5 历史差异
                    └─> #6 雷达评分/状态机
                          └─> #7 12个月路径
                                └─> #8 信号实验室

#9 LLM Schema 依赖 #1/#4，可与 #5 并行
#10 测试和样例报告依赖全部核心能力
```

## 19. 回滚策略

1. 保留当前 `/api/holdings/analyze` 和现有 brief 输出，直到雷达 brief 验收通过。
2. 新接口全部使用 `/api/radar/*`，避免破坏现有前端。
3. JSON store 新字段追加，不覆盖旧 reports/decisions。
4. 若雷达评分产生异常，前端回退到当前 Top 3 变化和风险雷达。
5. LLM 失败时只影响文本提取和问题生成，不影响规则 gate。

## 20. 不在本阶段范围

1. 自动交易或自动下单。
2. 对真实账户仓位给无条件买卖指令。
3. 全市场实时扫描所有 A 股。
4. 高成本商业数据源自动接入。
5. 未经用户确认的社媒传闻自动升级候选。
6. 对 1 年收益做确定性预测。

## 21. Definition of Done

完成后，用户每天打开系统看到的不是普通日报，而是：

1. 哪些弱信号刚出现，为什么只是在收件箱。
2. 哪些弱信号跨过了新的独立来源家族。
3. 哪些历史判断被确认、修正、矛盾或证伪。
4. 哪些标的进入 12 个月多倍路径观察。
5. 每条路径未来 30/90/180/365 天必须发生什么。
6. 哪些 kill condition 已经接近触发。
7. 用户只需要决定：继续验证、忽略、升级人工复核、加入复盘。

## 22. 参考资料

1. Bloomberg Anywhere: https://bba.bloomberg.com/
2. AlphaSense Platform: https://www.alpha-sense.com/platform/
3. Koyfin Custom Dashboards: https://www.koyfin.com/features/custom-dashboards/
4. Koyfin Stock Screeners 2026: https://www.koyfin.com/blog/best-stock-screeners/
5. Quartr API Introduction: https://quartr.com/docs/introduction
6. 上海证券交易所最新公告: https://www.sse.com.cn/disclosure/listedinfo/announcement/
7. 深圳证券交易所上市公司信息披露: https://www.szse.cn/disclosure/notice/company/index.html
8. Anna Yartseva, The Alchemy of Multibagger Stocks: https://econpapers.repec.org/RePEc:akf:cafewp:33
9. Narasimhan Jegadeesh, Revenue Growth and Stock Returns: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=314962
10. MSCI, The rise of fundamental factors in China A shares: https://www.msci.com/research-and-insights/blog-post/the-rise-of-fundamental-factors-in-china-a-shares

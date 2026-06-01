# MVP 投研产出升级设计

状态：需求设计补丁  
日期：2026-06-01  
关联规格：`docs/specs/a-share-research-cockpit-mvp.md`  
目标：让 MVP 第一版就产生超出预期的投研产出，而不只是完成数据、表、页面和 Agent 底座

## 1. 结论

现有 MVP 方向是对的：半自动、强解释、强复核、强复盘，不做自动荐股。但它仍然偏“系统建设清单”，第一版如果只完成股票池、公告解析、评分和信号卡，用户会觉得可信，却未必每天都想打开。

MVP 要超出预期，必须从“功能驱动”改成“产出驱动”：

```text
不要让用户看到一堆数据。
要让用户每天看到 5 个可判断、可追溯、可复盘的研究对象。
```

第一版的核心产出应改成：

1. 今日最重要 3 条变化。
2. 投资假设体检卡。
3. 同板块横向比较卡。
4. 反方证据与风险雷达。
5. 下一验证点日历。

这 5 个产出比“AI 聊天问答”更像真正的投研驾驶舱，也比普通自选股、新闻、公告、行情提醒更有个人价值。

## 2. 外部研究摘要

本次参考了几类产品：

| 产品 | 强项 | 对 MVP 的启发 |
|---|---|---|
| Bloomberg Terminal | 数据、新闻、研究、分析、告警和工作区整合 | MVP 必须有“集成工作流”，不能只是多个页面 |
| Wind 金融终端 | 中国市场数据覆盖、终端、Excel、EDB、报告导出 | A 股系统要重视数据口径、宏观/行业/公司联动 |
| 同花顺 iFinD | 智能投研、产业链、事件驱动、自然语言查询 | 主题和产业链要成为股票池解释层 |
| 东方财富 Choice | AI 搜索、AI 问答、研报总结、资讯摘要等场景 | AI 价值应落在压缩阅读和提炼差异观点 |
| AlphaSense | 文档搜索、市场情报、工作流 Agent、diligence/benchmarking | MVP 要有“问题驱动研究包”，不是泛泛总结 |
| Quartr | 一手 IR 数据、事件、转录、文件、摘要、结构化 API | 事件是核心单位，不能只存文档 |
| TradingView | 图表、watchlist、告警、筛选器、条件触发 | 自选股级别的批量条件告警是高频价值点 |
| Koyfin | 自定义仪表盘、watchlist、组合、图表、screeners、公式 | 用户应能把自己的研究字段固定到表格里 |
| TIKR / Fiscal.ai | 财务、估值、筛选、机构级数据质量 | 基本面系统要突出估值、情景和同业比较 |
| 理杏仁 | 少而精的数据中心，服务中小投资者 | MVP 不应复刻庞大终端，而要减少噪音 |

共同模式：

1. 强产品都不是单点 AI，而是把数据、工作流、告警、研究对象和复盘连起来。
2. 专业终端的优势是覆盖广，但个人系统的优势应是“只关心我的股票池、我的假设、我的证伪条件”。
3. AI 最有用的地方不是预测涨跌，而是压缩阅读、追踪变化、找反方证据、生成下一步研究问题。
4. 终端类产品常见问题是信息密度过高，个人驾驶舱应该少展示低价值信息。

## 3. MVP 的记忆点

第一眼应该让用户记住：

```text
这是一个每天告诉我“哪些投资假设变了”的系统。
```

不是：

```text
这是另一个看行情、看公告、看新闻的终端。
```

所以第一屏不要以行情表或新闻流开头，而要以“研究状态变化”开头。

## 4. MVP 产出重排

原 MVP 页面仍保留，但第一版优先级要重排：

| 原设计 | 问题 | 升级后 |
|---|---|---|
| 今日驾驶舱 | 容易变成信号和新闻列表 | 今日研究增量台 |
| 股票池 | 容易只是自选股表 | 假设驱动股票池 |
| 信号审计 | 正确但偏事后 | 变化解释卡 |
| 公司卡片 | 容易变成百科页 | 公司作战卡 |
| 复盘中心 | 原设计放后续 | MVP 就要做轻量复盘 |

MVP 第一版的主线应是：

```text
公告/行情/财务变化
  ↓
影响了哪个投资假设
  ↓
分数和状态为何变化
  ↓
同板块谁更值得看
  ↓
反方证据是什么
  ↓
下一次用什么事实验证
```

## 5. 五个超预期产出

### 5.1 今日最重要 3 条变化

每天只推 3 条最高价值变化，避免把用户淹没。

卡片字段：

```json
{
  "rank": 1,
  "title": "订单催化增强，但毛利率验证仍缺失",
  "stock_code": "000001.SZ",
  "stock_name": "示例公司",
  "why_it_matters": "该公告直接影响核心假设中的收入弹性，但尚不能证明利润弹性。",
  "changed_object": "investment_thesis",
  "changed_field": "evidence_summary",
  "score_delta": {
    "R": 8,
    "O": -2,
    "T": 6,
    "Q": "unchanged"
  },
  "suggested_user_action": "打开审计卡，重点检查合同毛利率和交付周期。",
  "not_actionable_because": [
    "缺少毛利率数据",
    "未看到经营现金流验证"
  ],
  "source_rank": "A",
  "review_required": true
}
```

排序规则：

1. 持仓风险 > 候选池状态变化 > 核心假设变化 > 新线索。
2. A/B 级来源优先于 C/D 级来源。
3. 涉及证伪条件的变化优先于普通正向变化。
4. 同一股票一天最多进入 Top 3 一次，除非出现重大风险。

验收标准：

1. 每天最多展示 3 条主变化。
2. 每条必须说明 `why_it_matters`。
3. 每条必须说明为什么可行动或暂不可行动。
4. 每条必须关联至少 1 个证据项。

### 5.2 投资假设体检卡

这是 MVP 最关键的新增产出。

用户不是在跟踪股票，而是在跟踪假设。系统每天回答：

```text
这个假设今天增强了、减弱了、未变，还是被证伪了？
```

卡片字段：

```json
{
  "thesis_id": "uuid",
  "stock_code": "000001.SZ",
  "thesis_text": "公司受益于某政策推动，订单有望在未来两个季度兑现。",
  "status_before": "unverified",
  "status_after": "strengthened",
  "confidence_before": "medium",
  "confidence_after": "medium",
  "evidence_added": [
    "新增重大合同公告"
  ],
  "evidence_missing": [
    "合同毛利率",
    "交付周期",
    "现金流匹配"
  ],
  "counter_evidence": [
    "同业龙头尚未披露类似订单"
  ],
  "next_validation_point": {
    "date": "2026-08-31",
    "event": "中报披露",
    "watch_field": "毛利率和经营现金流"
  },
  "research_question": "该合同是否会带来利润弹性，而不是只带来收入规模？"
}
```

新增表：`thesis_checks`

```sql
CREATE TABLE thesis_checks (
  check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thesis_id UUID NOT NULL REFERENCES investment_thesis(thesis_id),
  stock_code TEXT NOT NULL REFERENCES stock_universe(stock_code),
  check_date DATE NOT NULL,
  status_before TEXT NOT NULL,
  status_after TEXT NOT NULL,
  confidence_before TEXT NOT NULL,
  confidence_after TEXT NOT NULL,
  evidence_added UUID[] NOT NULL DEFAULT '{}',
  evidence_missing TEXT[] NOT NULL DEFAULT '{}',
  counter_evidence TEXT[] NOT NULL DEFAULT '{}',
  next_validation_date DATE,
  next_validation_event TEXT,
  watch_fields TEXT[] NOT NULL DEFAULT '{}',
  research_question TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_thesis_checks_stock_date ON thesis_checks(stock_code, check_date DESC);
CREATE INDEX idx_thesis_checks_thesis_date ON thesis_checks(thesis_id, check_date DESC);
```

验收标准：

1. 每条活跃投资假设每天最多生成 1 张体检卡。
2. 没有新增事实时，体检卡可以输出 `unchanged`，但必须说明下一个验证点。
3. 如果新增事实触发证伪条件，状态必须变为 `falsified` 或进入人工复核。
4. 每张体检卡至少有 1 个研究问题。

### 5.3 同板块横向比较卡

A 股投研很容易陷入单票叙事。MVP 要强制回答：

```text
如果这个逻辑成立，为什么是它，不是同板块其他公司？
```

卡片字段：

```json
{
  "theme": "某产业链",
  "focus_stock": "000001.SZ",
  "peer_set": ["000002.SZ", "600000.SH", "300000.SZ"],
  "comparison_dimensions": [
    "真实受益程度",
    "业绩弹性",
    "估值分位",
    "资金确认",
    "风险瑕疵"
  ],
  "winner": "000001.SZ",
  "winner_reason": "订单弹性更直接，估值尚未明显透支。",
  "loser_or_wait": [
    {
      "stock_code": "600000.SH",
      "reason": "龙头更稳，但弹性不足。"
    }
  ],
  "missing_data": [
    "部分公司缺少一致口径订单数据"
  ]
}
```

MVP 约束：

1. 第一版只在同主题股票池内比较，不做全市场挖掘。
2. 每个主题最多展示 5 只股票，避免做成宽泛筛选器。
3. 比较维度固定，减少自由发挥。
4. 结论必须允许输出“无法判断，因为缺数据”。

新增表：`peer_comparisons`

```sql
CREATE TABLE peer_comparisons (
  comparison_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  theme TEXT NOT NULL,
  focus_stock TEXT NOT NULL REFERENCES stock_universe(stock_code),
  peer_set TEXT[] NOT NULL,
  comparison_date DATE NOT NULL,
  dimensions JSONB NOT NULL,
  winner_stock TEXT,
  winner_reason TEXT,
  missing_data TEXT[] NOT NULL DEFAULT '{}',
  generated_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_peer_comparisons_theme_date ON peer_comparisons(theme, comparison_date DESC);
CREATE INDEX idx_peer_comparisons_focus_date ON peer_comparisons(focus_stock, comparison_date DESC);
```

验收标准：

1. 候选池股票必须有最近 7 天内的横向比较卡。
2. 横向比较不能只输出排名，必须输出胜出理由和不确定项。
3. 如果同主题股票少于 2 只，系统必须提示需要补充 peer set。

### 5.4 反方证据与风险雷达

原规格要求每个看多信号提供反方证据，但 MVP 应把反方证据提升成独立模块。

风险雷达分 5 类：

| 风险类 | 示例 |
|---|---|
| 假设风险 | 政策落地慢、订单不持续、景气度拐头 |
| 财务风险 | 应收增长快、现金流弱、毛利率下滑 |
| 估值风险 | 预期透支、同业明显更便宜 |
| 交易风险 | 高位拥挤、放量滞涨、板块退潮 |
| 治理风险 | 减持、质押、问询、处罚、诉讼 |

卡片字段：

```json
{
  "stock_code": "000001.SZ",
  "risk_level": "C",
  "risk_summary": "看多逻辑增强，但财务兑现仍未验证。",
  "bear_cases": [
    {
      "category": "financial",
      "claim": "应收账款增速可能快于收入增速",
      "evidence_id": "uuid",
      "severity": "medium",
      "what_would_reduce_this_risk": "中报经营现金流改善"
    }
  ],
  "blocked_actions": [
    "不得自动进入持仓观察"
  ]
}
```

验收标准：

1. 候选信号必须生成风险雷达。
2. 风险雷达必须有 `what_would_reduce_this_risk`。
3. Q=C/D 时，风险雷达优先显示在今日驾驶舱。

### 5.5 下一验证点日历

超预期来自“系统替你记住该等什么”。每个股票、假设、信号都必须落到一个未来验证点。

新增表：`validation_points`

```sql
CREATE TABLE validation_points (
  validation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stock_code TEXT NOT NULL REFERENCES stock_universe(stock_code),
  thesis_id UUID REFERENCES investment_thesis(thesis_id),
  signal_id TEXT REFERENCES signals(signal_id),
  validation_date DATE,
  validation_type TEXT NOT NULL,
  description TEXT NOT NULL,
  watch_fields TEXT[] NOT NULL DEFAULT '{}',
  expected_direction TEXT,
  invalidates_if TEXT,
  status TEXT NOT NULL CHECK (status IN ('pending', 'hit', 'missed', 'stale', 'cancelled')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_validation_points_date ON validation_points(validation_date, status);
CREATE INDEX idx_validation_points_stock ON validation_points(stock_code, status);
```

验收标准：

1. 候选池股票必须至少有 1 个 pending 验证点。
2. 持仓观察股票必须至少有 1 个证伪验证点。
3. 验证点过期后必须进入日报提醒。
4. 用户处理信号时，如果没有验证点，系统必须要求补充。

## 6. 今日驾驶舱重设计

第一屏顺序：

```text
1. 今日最重要 3 条变化
2. 持仓/候选风险雷达
3. 投资假设体检
4. 横向比较变化
5. 下一验证点日历
6. 原始公告和新闻流
```

设计原则：

1. 风险高于机会。
2. 状态变化高于静态数据。
3. 假设变化高于股票涨跌。
4. 下一步动作高于解释文字。
5. 证据链接永远在一屏内可达。

页面不应该出现大段 AI 散文。每张卡最多 5 行摘要，详情进入审计卡。

## 7. 公司卡片重设计

公司卡不是百科页，而是作战卡。

固定结构：

```text
一句话主逻辑
当前状态
R/O/T/Q
核心假设
最近 3 条变化
同板块位置
最大反方证据
下一验证点
最近一次人工决策
```

MVP 不做长篇公司深度报告。系统只做“当前该不该继续花精力”的判断支持。

## 8. 数据模型补丁

除原规格表以外，MVP 增加 4 张表：

1. `thesis_checks`
2. `peer_comparisons`
3. `validation_points`
4. `daily_research_briefs`

`daily_research_briefs`：

```sql
CREATE TABLE daily_research_briefs (
  brief_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brief_date DATE NOT NULL UNIQUE,
  top_changes JSONB NOT NULL,
  risk_alerts JSONB NOT NULL,
  thesis_checks JSONB NOT NULL,
  peer_comparisons JSONB NOT NULL,
  validation_points JSONB NOT NULL,
  generated_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 9. Agent 调整

原 MVP 的 4 个 Agent 改成 5 个产出型 Agent：

| Agent | 原职责 | 升级职责 |
|---|---|---|
| 公告 Agent | 解析公告 | 输出事件，并标记影响哪个假设 |
| 评分 Agent | 算 R/O/T/Q | 输出分数变化和触发规则 |
| 反方 Agent | 完整版才做 | MVP 必做，生成风险雷达 |
| 比较 Agent | 原未进入 MVP | MVP 必做，生成同板块横向比较 |
| 主编 Agent | 汇总日报 | 生成 Top 3 变化和验证点日历 |

关键调整：

1. 反方 Agent 提前进入 MVP。
2. 横向比较 Agent 提前进入 MVP。
3. 主线/政策 Agent 暂不作为完整 Agent，但主题标签和政策事件必须进入比较上下文。

## 10. 新的 MVP 成功标准

原 MVP 的成功标准是“系统可信”。升级后的成功标准是：

```text
用户连续 5 个交易日打开系统后，
至少 3 次觉得系统提醒了自己原本可能忽略的研究问题。
```

可量化指标：

| 指标 | MVP 目标 |
|---|---:|
| 每日 Top 3 变化命中率 | >= 70% 被用户点开 |
| 信号卡人工处理率 | >= 80% |
| 每个候选股票验证点覆盖率 | 100% |
| 候选信号反方证据覆盖率 | 100% |
| 用户标记“有帮助”的研究问题 | 5 个交易日 >= 3 条 |
| 低等级来源误升级 | 0 |

## 11. 取舍

为了把这些产出放进 MVP，需要推迟部分原计划：

| 推迟项 | 原因 |
|---|---|
| 完整主题/板块页面 | 容易做成大而全，MVP 只需要同主题比较卡 |
| 完整复盘中心 | 先做轻量 `add_to_review` 和验证点命中/错过 |
| 多数据源自动接入 | 先保证固定股票池和证据链质量 |
| Streamlit 大量页面 | 第一版页面少，卡片质量高 |
| 研报知识库 | 先支持手动上传和摘要，不能让 C 级观点污染信号 |

不推迟：

1. 反方证据。
2. 验证点。
3. 横向比较。
4. 人工处理记录。

这四件事是超预期的来源。

## 12. 推荐的首版页面

### 12.1 今日研究增量台

第一屏只放：

1. `Top 3 Changes`
2. `Risk Radar`
3. `Validation Calendar`

第二屏放：

1. `Thesis Checks`
2. `Peer Comparison Changes`
3. `Raw Documents`

### 12.2 股票池

新增列：

```text
核心假设状态
下一验证点
反方风险数
最近体检结果
同板块相对位置
```

### 12.3 信号审计

新增区块：

```text
这个信号影响了哪个投资假设？
如果看错，最可能错在哪里？
同主题里是否有更好的标的？
下一次验证日期是什么？
```

## 13. 实施顺序调整

新顺序：

| # | 子任务 | 说明 |
|---|---|---|
| 1 | 数据库和基础 schema | 原计划保留 |
| 2 | 股票池 + 投资假设 + 验证点 | 验证点提前 |
| 3 | 原始文件 + 证据项 + 事件 | 原计划保留 |
| 4 | 公告 Agent 标记影响假设 | 不只是提取事件 |
| 5 | 评分引擎 | 原计划保留 |
| 6 | 反方 Agent + 风险雷达 | 提前进入 MVP |
| 7 | 横向比较 Agent | 提前进入 MVP |
| 8 | Top 3 变化主编 | 新增 MVP 核心 |
| 9 | 今日研究增量台 | 替代普通驾驶舱 |
| 10 | 信号审计 + 人工处理 | 原计划保留并增强 |
| 11 | 轻量复盘 | 只做验证点命中/错过 |
| 12 | E2E 验收 | 用 5 个产出验收 |

## 14. 更新后的 Definition of Done

在原 DoD 基础上增加：

1. 每个交易日生成不超过 3 条 Top Changes，且每条都有 `why_it_matters`。
2. 每个活跃投资假设能生成体检状态：增强、减弱、未变、证伪或待复核。
3. 每个候选池股票都有最近 7 天内的同板块横向比较卡。
4. 每个候选信号都有风险雷达，且列出至少 1 个 `what_would_reduce_this_risk`。
5. 每个候选池和持仓观察股票都有 pending 验证点。
6. 验证点过期后进入日报提醒。
7. 用户可以把任一研究问题标记为 `有帮助`、`噪音`、`加入复盘`。
8. 连续 5 个交易日样例运行中，至少生成 3 条非重复研究问题。

## 15. 产品判断

这个 MVP 最不该比拼：

```text
数据源数量
页面数量
Agent 数量
长报告长度
```

最该比拼：

```text
今天到底有什么变化？
这件事影响了哪个假设？
为什么不是同板块另一只？
反方证据是什么？
下一次用什么事实验证？
```

只要第一版能稳定回答这五个问题，它就会明显超过普通 AI 问答，也会比一个简化版金融终端更有个人投研价值。

## 16. 参考资料

以下资料在 2026-06-01 做过轻量核验，后续实现前仍需复核授权、接口和费用：

1. Bloomberg Terminal: https://www.bloomberg.com/professional/products/bloomberg-terminal/
2. Bloomberg Professional App: https://professional.bloomberg.com/products/bloomberg-terminal/access/bloomberg-professional-app/
3. Wind 金融终端: https://www.wind.com.cn/portal/zh/WFT/index.html
4. Wind 首页和数据服务: https://www.wind.com.cn/portal/zh/Home/index.html
5. 同花顺 iFinD: https://www.aifind.com/
6. 同花顺 iFinD App Store 页面: https://apps.apple.com/cn/app/id717545196
7. 东方财富 Choice 8.0 研报摘要: https://data.eastmoney.com/report/info/AP202406171636481305.html
8. AlphaSense Generative Search: https://www.alpha-sense.com/platform/generative-search/
9. Quartr API: https://quartr.com/products/quartr-api
10. Quartr Docs: https://quartr.com/docs/
11. TradingView Features: https://www.tradingview.com/features/
12. TradingView Watchlist Alerts: https://in.tradingview.com/support/solutions/43000739708/
13. Koyfin Functionality: https://www.koyfin.com/help/topic/functionality/
14. TIKR Analyze Stocks: https://www.tikr.com/analyze-stocks
15. Fiscal.ai API Docs: https://docs.fiscal.ai/docs/introduction
16. 理杏仁: https://www.lixinger.com/

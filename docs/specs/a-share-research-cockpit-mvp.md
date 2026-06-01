# A 股投研驾驶舱 MVP 需求规格

状态：需求草案  
日期：2026-06-01  
目标版本：MVP v0.1  
定位：半自动、强解释、强复核、强复盘的 A 股投研系统

## 1. 背景

本系统不是荐股机器人，也不是自动交易系统。目标是把个人投研过程里的重复动作标准化：维护股票池、投资假设、证据链、评分、风险、信号和复盘，让用户每天审阅高价值变化，而不是反复问同一只股票“还能不能看”。

核心原则：

```text
事实可追溯
推理可解释
评分可复核
信号可操作
错误可复盘
系统可维护
```

每个正式信号必须回答：

1. 为什么出现？
2. 依据是什么？
3. 原始来源在哪里？
4. 评分从多少变成多少？
5. 反方证据是什么？
6. 用户应该做什么动作？
7. 什么情况下信号失效？

## 2. 已核实现状

核验时间：2026-06-01。

| 项目 | 现状 | 影响 |
|---|---|---|
| 当前项目目录 | `C:\Users\kira5\Documents\Critical-Investment-Consultant` 当前没有可读源码文件 | 本规格按绿地 MVP 设计，不引用既有模块 |
| Git 仓库根目录 | `git rev-parse --show-toplevel` 返回 `C:/Users/kira5` | 后续实现应避免把用户主目录作为项目仓库根目录，建议初始化独立仓库 |
| GitHub CLI | `gh --version` 因 GitHub CLI 配置文件权限失败 | 本次未创建 GitHub issue，需求先归档为本地文档 |
| 外部事实 | 已轻量核验上交所、深交所、巨潮、Tushare、AKShare、Ricequant、OpenAI 官方文档 | 数据源和 AI 技术选型写成可替换适配层 |

## 3. 用户与使用场景

主要用户：个人 A 股投资研究者。

用户风格假设：

```text
政策/主线敏感
+ 基本面验证
+ 个股弹性比较
+ 技术/资金确认
+ 风险排雷
```

日常流程：

1. 盘前看今日驾驶舱，确认重大市场、政策、产业和股票池变化。
2. 盘中只看资金确认、风险预警、候选池变化。
3. 盘后系统解析公告和行情，更新评分，生成信号卡。
4. 晚上用户只处理需要人工判断的信号：确认、忽略、加入复盘。

## 4. 范围

### 4.1 MVP 必须做

MVP 只跟踪固定股票池，只处理最关键的一手公告、基础财务、日线行情、评分、信号卡和人工确认。

MVP 必须包含：

1. 固定股票池管理。
2. 投资假设管理。
3. 原始文件与证据存档。
4. 每日公告扫描和结构化事件提取。
5. R/O/T/Q 四维评分更新。
6. 股票池状态机。
7. 研究状态信号生成。
8. 信号审计卡。
9. 今日驾驶舱、股票池、信号审计、公司卡片四个基础页面。
10. 人工确认、忽略、加入复盘三类操作。
11. 每次评分、信号、人工决策都留痕。
12. 产出驱动的研究增量包：今日最重要 3 条变化、投资假设体检卡、同板块横向比较卡、反方证据与风险雷达、下一验证点日历。详见 `docs/specs/mvp-research-output-upgrade.md`。

### 4.2 MVP 不做

以下明确不在 MVP 范围：

1. 自动下单。
2. 自动生成无条件买入/卖出指令。
3. 全市场自动选股。
4. 高频交易、分钟级策略、盘口策略。
5. 复杂量化回测平台。
6. 多用户权限系统。
7. 商业投顾合规发布系统。
8. 研报版权内容的自动分发。
9. 未经确认的社媒传闻直接触发候选信号。

## 5. 产品宪法

系统最高规则：

```text
你是我的 A 股投研系统，不直接给出无条件买卖指令。

你的任务是：
1. 持续维护股票池、投资假设、事件、评分、风险和复盘；
2. 所有结论必须区分事实、推理和观点；
3. 官方公告、财报、监管文件优先级最高；
4. 新闻、研报、社媒只能作为线索，不能单独触发高等级信号；
5. 每个看多信号必须提供反方证据；
6. 每个候选标的必须有证伪条件；
7. 每个信号必须说明评分变化和触发规则；
8. 数据缺失、来源冲突、评分异常跳变时必须要求人工复核；
9. 风险等级为 D 的股票不得进入候选池；
10. 系统输出研究状态和操作建议，不替代最终投资决策。
```

## 6. 数据源要求

### 6.1 来源等级

| 等级 | 数据源类型 | 用途 | 是否可直接触发正式信号 |
|---|---|---|---|
| A | 交易所公告、巨潮、上市公司定期报告、监管文件 | 事实确认 | 可以 |
| B | 行情、财务数据库、行业数据、产品价格 | 指标计算 | 可以 |
| C | 券商研报、媒体新闻、产业链访谈 | 发现线索 | 需二次确认 |
| D | 社媒、论坛、传闻、小作文 | 情绪观察 | 不可以 |

### 6.2 MVP 数据源

| 数据域 | MVP 首选 | 备用 | 说明 |
|---|---|---|---|
| 公告 | 巨潮资讯、上交所、深交所 | 手动上传 PDF/HTML | 原始公告必须保存文件哈希 |
| 财务 | Tushare Pro 或手动导入 CSV | AKShare | 生产口径需要记录数据供应商和更新时间 |
| 行情 | Tushare Pro 日线/每日指标 | AKShare | MVP 使用日线即可 |
| 风险 | 公告、监管措施、问询函、减持、质押、诉讼 | 手动标签 | 风险等级作为硬门槛 |
| 研报/笔记 | 用户上传文档 | OpenAI File Search 或自建向量库 | 只能补充观点，不能单独升级正式信号 |

数据源适配要求：

1. 每条原始数据必须有 `source`, `source_url`, `source_rank`, `publish_date`, `collected_at`, `file_hash`。
2. 同一公告重复抓取时必须通过 `file_hash` 去重。
3. C/D 级来源只能生成 `待复核线索`，不能生成 `候选信号`。
4. A/B 级来源冲突时，系统不得自动选择一方，必须标记 `人工复核`。

## 7. 系统架构

```text
数据源
  ↓
原始数据层 raw_documents
  ↓
解析与结构化层 parser jobs
  ↓
事件库 / 财务库 / 行情库 / 研究假设库
  ↓
多 Agent 分析层
  ↓
规则评分引擎
  ↓
信号生成器
  ↓
今日驾驶舱 / 股票池排序 / 信号审计卡
  ↓
人工确认
  ↓
交易决策与复盘
  ↓
反馈评分系统
```

### 7.1 推荐技术栈

| 层 | MVP 推荐 |
|---|---|
| 后端 | Python + FastAPI |
| 前端 | Streamlit 起步，后续可迁移 React |
| 数据库 | PostgreSQL |
| 行情/财务历史缓存 | DuckDB + Parquet |
| 原始文件 | 本地文件夹，后续可替换对象存储 |
| AI 编排 | OpenAI Responses API + Agents SDK |
| 模型输出 | JSON Schema / Pydantic |
| 调度 | Windows Task Scheduler / cron / Prefect 三选一 |
| 配置版本 | Git 管理 YAML |
| 审计 | agent run、prompt 版本、规则版本、trace ID、输入输出 JSON |

技术选型约束：

1. 不基于旧 Assistants API 新建系统。
2. Agent 输出必须是结构化 JSON，不接受自由散文作为系统事实。
3. 评分规则必须配置化，不写死在业务代码里。
4. 所有敏感状态迁移必须先进入 `review_required=true`。

## 8. 核心领域模型

### 8.1 股票池状态机

状态枚举：

```text
excluded
theme_watch
stock_tracking
candidate
holding_watch
downgraded
exited
```

状态含义：

| 状态 | 中文 | 含义 | 用户动作 |
|---|---|---|---|
| `excluded` | 排除 | 财务、治理、估值、题材真实性或流动性不符合要求 | 不看，除非重大变化 |
| `theme_watch` | 主题观察 | 行业/政策有逻辑，但个股未筛出 | 跟踪板块和产业数据 |
| `stock_tracking` | 个股跟踪 | 公司有研究价值，但条件不成熟 | 建立公司卡片 |
| `candidate` | 候选池 | 逻辑、催化、估值、资金至少部分共振 | 准备人工判断 |
| `holding_watch` | 持仓观察 | 已有仓位，需要持续跟踪证伪条件 | 看风险和兑现 |
| `downgraded` | 降级 | 逻辑减弱、风险上升或赔率恶化 | 复盘原因 |
| `exited` | 退出 | 用户已卖出或逻辑完成复盘 | 关闭主动跟踪 |

状态迁移规则：

| 从 | 到 | 触发条件 | 是否人工确认 |
|---|---|---|---|
| `theme_watch` | `stock_tracking` | 板块主线成立，且公司被证据证明是真实受益者 | 是 |
| `stock_tracking` | `candidate` | R >= 75, O >= 60, T >= 60, Q in A/B | 是 |
| `candidate` | `holding_watch` | 用户人工确认并记录买入假设、仓位、证伪条件 | 是 |
| `holding_watch` | `downgraded` | 核心假设减弱、资金破位、风险事件出现 | 是 |
| 任意 | `excluded` | 财务造假风险、重大治理风险、流动性失控、逻辑证伪 | 是 |

系统不得允许股票停留在无状态。

### 8.2 评分体系

评分由四个主维度组成：

```text
R: Research Score, 研究分, 0-100
O: Odds Score, 赔率分, 0-100
T: Timing Score, 时点分, 0-100
Q: Quality/Risk Grade, 风险等级, A/B/C/D
```

R 研究分维度：

| 维度 | 权重 |
|---|---:|
| 行业/政策顺风 | 20 |
| 公司真实受益程度 | 15 |
| 公司质量 | 15 |
| 业绩弹性 | 20 |
| 催化剂清晰度 | 15 |
| 证据质量 | 15 |

Q 风险等级是硬门槛，不参与加权总分。Q = D 时不得进入候选池。

### 8.3 动作矩阵

| 条件 | 系统输出 | 用户动作 |
|---|---|---|
| R >= 75, O >= 65, T >= 60, Q in A/B | 候选信号 | 人工检查，考虑纳入交易计划 |
| R >= 75, O >= 65, T < 60 | 等待信号 | 逻辑好，但时点未到 |
| R >= 75, O < 60 | 逻辑好但赔率差 | 不追，等回调或业绩上修 |
| R >= 60, R < 75, T 高 | 交易性观察 | 可能是题材/资金驱动 |
| R < 60 | 只做观察 | 不主动投入精力 |
| Q = C | 风险复核 | 必须打开风险审计卡 |
| Q = D | 排除/退出复核 | 不进入候选池 |
| 核心假设被证伪 | 证伪信号 | 复盘，不再找理由续命 |

## 9. Agent 分工

MVP 可先实现 4 个 Agent，完整版本扩展到 8 个。

### 9.1 MVP Agent

| Agent | 职责 | 输入 | 输出 |
|---|---|---|---|
| 公告 Agent | 解析公告、财报、业绩预告、减持、回购、订单、诉讼 | `raw_documents` | 结构化事件和证据 |
| 财务/风险 Agent | 计算基础财务质量并识别硬风险 | `financial_metrics`, `events` | Q 风险等级、风险原因 |
| 评分 Agent | 按 YAML 规则计算 R/O/T/Q | 事件、财务、行情、假设 | `scores` |
| 主编 Agent | 汇总结果，生成信号卡、日报 | scores, events, thesis | signals, reports |

### 9.2 完整版本 Agent

| Agent | 职责 |
|---|---|
| 公告 Agent | 解析公告、财报、业绩预告、减持、回购、订单、诉讼 |
| 财务 Agent | 收入、利润、毛利率、现金流、负债、应收、存货 |
| 主线/政策 Agent | 政策、产业趋势、行业景气 |
| 估值 Agent | 历史估值、同业估值、情景估值 |
| 资金 Agent | 板块强弱、相对收益、成交、量价、拥挤度 |
| 风险 Agent | 监管、质押、减持、商誉、现金流异常 |
| 反方 Agent | 专门反驳看多逻辑 |
| 主编 Agent | 生成日报、周报、信号审计卡 |

### 9.3 Agent 输出 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AgentAnalysisOutput",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "agent_name",
    "stock_code",
    "claims",
    "evidence",
    "score_impacts",
    "risks",
    "counterarguments",
    "unknowns",
    "confidence"
  ],
  "properties": {
    "agent_name": { "type": "string" },
    "stock_code": { "type": "string", "pattern": "^[0-9]{6}\\.(SH|SZ|BJ)$" },
    "claims": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["claim_type", "text", "is_fact"],
        "properties": {
          "claim_type": { "type": "string", "enum": ["fact", "inference", "opinion"] },
          "text": { "type": "string" },
          "is_fact": { "type": "boolean" }
        }
      }
    },
    "evidence": {
      "type": "array",
      "items": { "type": "string", "description": "evidence_id" }
    },
    "score_impacts": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["score_key", "delta", "rule_id", "reason"],
        "properties": {
          "score_key": { "type": "string", "enum": ["R", "O", "T", "Q"] },
          "delta": { "type": "number" },
          "rule_id": { "type": "string" },
          "reason": { "type": "string" }
        }
      }
    },
    "risks": { "type": "array", "items": { "type": "string" } },
    "counterarguments": { "type": "array", "items": { "type": "string" } },
    "unknowns": { "type": "array", "items": { "type": "string" } },
    "confidence": { "type": "string", "enum": ["low", "medium", "high"] }
  }
}
```

## 10. 数据库设计

PostgreSQL 是事实、状态、决策和审计的主库。行情和财务宽表可以同步到 DuckDB/Parquet，但主库必须保存每次信号生成所依赖的数据版本。

### 10.1 枚举

```sql
CREATE TYPE stock_state AS ENUM (
  'excluded',
  'theme_watch',
  'stock_tracking',
  'candidate',
  'holding_watch',
  'downgraded',
  'exited'
);

CREATE TYPE source_rank AS ENUM ('A', 'B', 'C', 'D');
CREATE TYPE impact_direction AS ENUM ('positive', 'negative', 'neutral');
CREATE TYPE risk_grade AS ENUM ('A', 'B', 'C', 'D');
CREATE TYPE review_decision AS ENUM ('confirm', 'ignore', 'add_to_review');
```

### 10.2 核心表

```sql
CREATE TABLE stock_universe (
  stock_code TEXT PRIMARY KEY,
  stock_name TEXT NOT NULL,
  exchange TEXT NOT NULL CHECK (exchange IN ('SH', 'SZ', 'BJ')),
  industry TEXT,
  theme_tags TEXT[] NOT NULL DEFAULT '{}',
  current_state stock_state NOT NULL DEFAULT 'theme_watch',
  main_logic TEXT,
  invalidating_conditions TEXT[] NOT NULL DEFAULT '{}',
  next_validation_point TEXT,
  owner_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE raw_documents (
  doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,
  source_rank source_rank NOT NULL,
  source_url TEXT,
  title TEXT NOT NULL,
  publish_date DATE,
  collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  file_hash TEXT NOT NULL,
  local_path TEXT NOT NULL,
  parsed_status TEXT NOT NULL DEFAULT 'pending',
  UNIQUE (file_hash)
);

CREATE TABLE evidence_items (
  evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doc_id UUID REFERENCES raw_documents(doc_id),
  source_rank source_rank NOT NULL,
  evidence_date DATE,
  title TEXT NOT NULL,
  claim TEXT NOT NULL,
  raw_excerpt TEXT NOT NULL,
  source_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE investment_thesis (
  thesis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stock_code TEXT NOT NULL REFERENCES stock_universe(stock_code),
  thesis_text TEXT NOT NULL,
  thesis_type TEXT NOT NULL,
  evidence_summary TEXT,
  invalidating_conditions TEXT[] NOT NULL DEFAULT '{}',
  confidence TEXT NOT NULL CHECK (confidence IN ('low', 'medium', 'high')),
  status TEXT NOT NULL CHECK (status IN ('unverified', 'strengthened', 'weakened', 'falsified', 'realized')),
  next_check_date DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stock_code TEXT REFERENCES stock_universe(stock_code),
  event_date DATE NOT NULL,
  source_type TEXT NOT NULL,
  source_rank source_rank NOT NULL,
  event_type TEXT NOT NULL,
  impact_direction impact_direction NOT NULL,
  impact_score NUMERIC NOT NULL CHECK (impact_score >= -10 AND impact_score <= 10),
  raw_source_id UUID REFERENCES raw_documents(doc_id),
  evidence_ids UUID[] NOT NULL DEFAULT '{}',
  extracted_by TEXT NOT NULL,
  reviewed BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE financial_metrics (
  stock_code TEXT NOT NULL REFERENCES stock_universe(stock_code),
  report_period DATE NOT NULL,
  revenue NUMERIC,
  net_profit NUMERIC,
  gross_margin NUMERIC,
  net_margin NUMERIC,
  operating_cash_flow NUMERIC,
  accounts_receivable NUMERIC,
  inventory NUMERIC,
  debt_ratio NUMERIC,
  roe NUMERIC,
  data_source TEXT NOT NULL,
  data_version TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (stock_code, report_period, data_source, data_version)
);

CREATE TABLE scores (
  score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stock_code TEXT NOT NULL REFERENCES stock_universe(stock_code),
  score_date DATE NOT NULL,
  research_score_r INTEGER NOT NULL CHECK (research_score_r BETWEEN 0 AND 100),
  odds_score_o INTEGER NOT NULL CHECK (odds_score_o BETWEEN 0 AND 100),
  timing_score_t INTEGER NOT NULL CHECK (timing_score_t BETWEEN 0 AND 100),
  risk_grade_q risk_grade NOT NULL,
  score_version TEXT NOT NULL,
  change_reason TEXT,
  triggered_rule_ids TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE signals (
  signal_id TEXT PRIMARY KEY,
  stock_code TEXT NOT NULL REFERENCES stock_universe(stock_code),
  signal_type TEXT NOT NULL,
  signal_level TEXT NOT NULL CHECK (signal_level IN ('S0', 'S1', 'S2', 'S3', 'S4', 'S5')),
  signal_direction impact_direction NOT NULL,
  previous_state stock_state,
  new_state stock_state,
  evidence_ids UUID[] NOT NULL DEFAULT '{}',
  score_before JSONB NOT NULL,
  score_after JSONB NOT NULL,
  positive_reasons TEXT[] NOT NULL DEFAULT '{}',
  negative_reasons TEXT[] NOT NULL DEFAULT '{}',
  invalidating_conditions TEXT[] NOT NULL DEFAULT '{}',
  suggested_action TEXT NOT NULL,
  review_required BOOLEAN NOT NULL DEFAULT true,
  final_user_decision TEXT,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE decisions (
  decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stock_code TEXT NOT NULL REFERENCES stock_universe(stock_code),
  decision_date TIMESTAMPTZ NOT NULL DEFAULT now(),
  decision_type TEXT NOT NULL,
  reason TEXT NOT NULL,
  linked_signal_id TEXT REFERENCES signals(signal_id),
  expected_holding_period TEXT,
  stop_condition TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reviews (
  review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stock_code TEXT NOT NULL REFERENCES stock_universe(stock_code),
  review_date DATE NOT NULL,
  initial_thesis TEXT NOT NULL,
  result TEXT NOT NULL,
  mistake_type TEXT CHECK (mistake_type IN ('theme', 'company', 'timing', 'position', 'risk', 'none')),
  lesson TEXT,
  scoring_adjustment BOOLEAN NOT NULL DEFAULT false,
  linked_signal_id TEXT REFERENCES signals(signal_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE agent_runs (
  agent_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_name TEXT NOT NULL,
  model_name TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  input_document_ids UUID[] NOT NULL DEFAULT '{}',
  output_json JSONB NOT NULL,
  trace_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 10.3 索引

```sql
CREATE INDEX idx_events_stock_date ON events(stock_code, event_date DESC);
CREATE INDEX idx_scores_stock_date ON scores(stock_code, score_date DESC);
CREATE INDEX idx_signals_stock_generated ON signals(stock_code, generated_at DESC);
CREATE INDEX idx_signals_review_required ON signals(review_required, generated_at DESC);
CREATE INDEX idx_raw_documents_publish_date ON raw_documents(publish_date DESC);
CREATE INDEX idx_evidence_doc ON evidence_items(doc_id);
```

## 11. 评分规则配置

评分规则必须保存在版本化 YAML 中，例如 `config/scoring/v1.0.yaml`。

```yaml
score_model_version: "v1.0"

research_score:
  industry_policy:
    weight: 20
    rules:
      - id: policy_support_confirmed
        condition: "a_level_policy_source_found == true"
        points: 5
      - id: industry_price_uptrend
        condition: "product_price_30d_change > 0.05"
        points: 5

  company_quality:
    weight: 15
    rules:
      - id: positive_operating_cashflow
        condition: "operating_cashflow_ttm > 0"
        points: 4
      - id: receivable_risk
        condition: "receivable_growth > revenue_growth + 0.20"
        points: -5

odds_score:
  valuation:
    rules:
      - id: valuation_percentile_low
        condition: "pe_percentile_5y < 0.35"
        points: 8
      - id: valuation_overheated
        condition: "pe_percentile_5y > 0.85"
        points: -8

timing_score:
  price_volume:
    rules:
      - id: relative_strength_confirmed
        condition: "stock_20d_return > sector_20d_return and stock_20d_return > index_20d_return"
        points: 6
      - id: high_volume_stalling
        condition: "volume_ratio > 2 and close_to_high < 0.3"
        points: -6

risk_gate:
  hard_exclude:
    - major_accounting_issue
    - regulatory_investigation
    - continuous_negative_cashflow_without_explanation
    - core_thesis_falsified
  force_review:
    - source_conflict
    - score_jump_over_15
    - c_or_d_level_source_only
```

规则引擎要求：

1. 每次打分必须保存 `score_model_version`。
2. 每次分数变化必须保存触发的 `rule_id`。
3. 单日 R/O/T 任一维度变化超过 15 分必须 `review_required=true`。
4. 规则条件表达式必须只读取已结构化字段，不直接让模型自由判断。

## 12. 信号审计卡

正式信号必须落库并生成审计卡。

```json
{
  "signal_id": "20260601-000001SZ-001",
  "stock_code": "000001.SZ",
  "stock_name": "示例公司",
  "signal_type": "候选池上调",
  "signal_direction": "positive",
  "generated_at": "2026-06-01T20:30:00+08:00",
  "previous_state": "stock_tracking",
  "new_state": "candidate",
  "score_before": {
    "R": 68,
    "O": 72,
    "T": 55,
    "Q": "B"
  },
  "score_after": {
    "R": 78,
    "O": 70,
    "T": 64,
    "Q": "B"
  },
  "key_evidence": [
    {
      "source_type": "company_announcement",
      "source_rank": "A",
      "date": "2026-06-01",
      "title": "重大合同公告",
      "claim": "新签合同金额占上一年度收入比例较高",
      "raw_excerpt": "原文摘录不超过必要长度",
      "source_url": "内部保存链接或公告文件ID"
    }
  ],
  "positive_reasons": [
    "订单催化增强",
    "未来两个季度业绩验证点更清晰"
  ],
  "negative_reasons": [
    "毛利率尚未验证",
    "应收账款变化需要跟踪"
  ],
  "invalidating_conditions": [
    "后续订单未继续披露",
    "毛利率未改善",
    "经营现金流明显弱于净利润"
  ],
  "suggested_action": "人工复核，允许进入候选池，但不自动交易",
  "review_required": true
}
```

强制规则：

1. 没有证据包，不允许生成正式信号。
2. 没有反方证据，不允许生成正向候选信号。
3. 没有证伪条件，不允许进入候选池。
4. 来源等级低于 B 时，不允许生成 `candidate` 状态迁移。
5. Q = D 时，强制输出 `排除/退出复核`。

## 13. 后端 API

MVP API 形状：

```text
GET    /api/dashboard/today
GET    /api/stocks
POST   /api/stocks
GET    /api/stocks/{stock_code}
PATCH  /api/stocks/{stock_code}
GET    /api/stocks/{stock_code}/company-card

GET    /api/signals
GET    /api/signals/{signal_id}
POST   /api/signals/{signal_id}/decision

GET    /api/events
GET    /api/raw-documents
POST   /api/raw-documents/upload

POST   /api/jobs/announcement-scan
POST   /api/jobs/score-run
POST   /api/jobs/daily-report

GET    /api/reviews
POST   /api/reviews
```

### 13.1 今日驾驶舱响应

```json
{
  "date": "2026-06-01",
  "market_policy_changes": [],
  "new_positive_events": [],
  "new_negative_events": [],
  "strongest_sectors": [],
  "signals_requiring_review": [],
  "candidate_changes": [],
  "risk_alerts": []
}
```

### 13.2 人工决策请求

```json
{
  "decision": "confirm",
  "reason": "订单催化增强，但仍需跟踪毛利率",
  "next_action": "加入候选池",
  "stop_condition": "中报毛利率未改善或经营现金流明显弱于净利润"
}
```

## 14. 页面需求

### 14.1 今日驾驶舱

必须显示：

1. 今日新增信号。
2. 今日风险预警。
3. 今日候选池变化。
4. 今日需要人工复核的问题。

交互：

1. 点击信号打开信号审计卡。
2. 信号卡支持确认、忽略、加入复盘。
3. 风险预警必须高于正向候选信号展示。

### 14.2 股票池

表格列：

```text
股票
状态
主逻辑
R
O
T
Q
最近信号
下一验证点
```

交互：

1. 支持按状态、主题、Q 风险等级过滤。
2. 支持按 R/O/T 排序。
3. 点击股票进入公司卡片。

### 14.3 信号审计

必须展示：

1. 为什么触发。
2. 依据来源。
3. 原文摘录。
4. 评分变化。
5. 触发规则。
6. 反方证据。
7. 证伪条件。
8. 人工处理记录。

### 14.4 公司卡片

固定格式：

```text
公司一句话
主逻辑
产业链位置
财务摘要
估值区间
催化剂
风险点
证伪条件
历史信号
历史决策
下一验证点
```

### 14.5 后续页面

后续版本再实现：

1. 主题/板块页面。
2. 复盘中心。
3. 周报/月报中心。

## 15. 报告输出

MVP 的报告输出必须以“研究增量”为中心，不以新闻数量、公告数量或行情涨跌为中心。第一版重点不是生成长报告，而是每天稳定生成可判断、可追溯、可复盘的研究对象：

```text
今日最重要 3 条变化
投资假设体检
同板块横向比较
反方证据与风险雷达
下一验证点日历
```

这部分是 MVP 体验的核心，不是后续增强项。详细产品设计见 `docs/specs/mvp-research-output-upgrade.md`。

### 15.1 盘前简报

```text
日期：YYYY-MM-DD

一、今日最重要的市场/政策/产业变化
二、股票池中新增正面事件
三、股票池中新增负面事件
四、昨日资金最强板块与是否延续
五、今日需要人工确认的信号
```

### 15.2 周报

周报比日报更重要。必须回答：

```text
现在市场正在奖励哪类逻辑？
当前股票池是否匹配这个逻辑？
哪些逻辑增强？
哪些逻辑减弱？
哪些票应该移出？
下周最重要的验证点是什么？
```

MVP 可以先只生成日报，周报作为 v0.2。

## 16. 工作流

### 16.1 每日公告扫描

1. 调度任务拉取固定股票池公告。
2. 保存原始文件和哈希。
3. 公告 Agent 结构化提取事件。
4. 提取结果进入待审核或自动通过。
5. 评分 Agent 计算 R/O/T/Q。
6. 信号生成器检查动作矩阵。
7. 主编 Agent 生成信号卡和日报。
8. 用户人工处理需要确认的信号。

### 16.2 谨慎失败

以下情况必须停止强信号生成：

| 情况 | 系统行为 |
|---|---|
| 数据缺失 | 不生成强信号，标记未知项 |
| 来源冲突 | 标记人工复核 |
| 评分异常跳变 | 标记人工复核 |
| 只有 C/D 级来源 | 只能生成线索 |
| Q = D | 阻断候选信号 |
| 核心假设证伪 | 输出证伪信号并要求复盘 |

## 17. 验收标准

MVP 完成必须满足以下可测试标准：

1. 用户可以创建、编辑、删除固定股票池记录，且每只股票都有明确状态。
2. 用户可以为股票创建至少一条投资假设，并保存证伪条件和下一验证点。
3. 系统可以导入一份本地公告文件，保存 `raw_documents` 记录和文件哈希。
4. 同一公告重复导入时不会创建重复 `raw_documents`。
5. 公告 Agent 输出符合 JSON Schema，缺字段时任务失败并记录错误。
6. 系统可以从样例公告生成至少一条 `events` 记录，并关联 `evidence_items`。
7. 评分引擎可以根据 YAML 规则生成 R/O/T/Q，并保存触发规则 ID。
8. 当 R/O/T 任一维度单日变化超过 15 分时，生成的信号必须 `review_required=true`。
9. 当 Q = D 时，股票不得迁移到 `candidate`。
10. 当只有 C/D 级来源时，系统不得生成 `candidate` 信号。
11. 每个正向候选信号必须包含至少一条反方证据和一条证伪条件。
12. 今日驾驶舱能列出新增信号、风险预警、候选池变化和待复核事项。
13. 信号审计页能展示证据、原文摘录、评分前后、规则 ID、反方证据和人工处理记录。
14. 用户可以对信号执行确认、忽略、加入复盘三种动作，动作必须写入 `decisions` 或 `reviews`。
15. 系统不展示“买入”作为默认指令，只展示研究状态和人工动作建议。
16. 所有模型调用保存 agent 名称、模型名、prompt 版本、输入文件 ID、输出 JSON、trace ID。

## 18. 测试计划

| 层级 | 测什么 | 数量 |
|---|---|---:|
| Unit | 状态机迁移、动作矩阵、风险门槛、YAML 规则解释 | +12 |
| Unit | JSON Schema 校验、文件哈希去重、评分变化计算 | +8 |
| Integration | 公告导入到事件提取到评分到信号生成 | +4 |
| Integration | Q=D 阻断、C/D 来源阻断、来源冲突人工复核 | +4 |
| UI | 今日驾驶舱、股票池筛选、信号审计卡、人工决策 | +6 |
| E2E | 导入样例公告后生成待复核候选信号并确认 | +1 |
| E2E | 导入风险公告后阻断候选并加入复盘 | +1 |

测试数据要求：

1. 至少 3 只样例股票。
2. 至少 1 份正向重大合同公告样例。
3. 至少 1 份减持或监管风险公告样例。
4. 至少 1 份 C/D 级来源样例。
5. 至少 1 条来源冲突样例。

## 19. 分期与子任务

### Epic：A 股投研驾驶舱 MVP

| # | 子任务 | 优先级 | 预计工作量 | 依赖 |
|---|---|---|---:|---|
| 1 | 初始化独立项目仓库和基础后端 | Critical | 0.5 天 | 无 |
| 2 | 建立 PostgreSQL schema 和迁移 | Critical | 1 天 | #1 |
| 3 | 固定股票池和投资假设 CRUD | Critical | 1 天 | #2 |
| 4 | 原始文件导入、哈希去重、证据表 | Critical | 1 天 | #2 |
| 5 | 公告 Agent JSON Schema 和样例解析 | High | 1.5 天 | #4 |
| 6 | YAML 评分规则和评分引擎 | High | 1.5 天 | #2, #5 |
| 7 | 状态机、动作矩阵、信号生成器 | High | 1.5 天 | #6 |
| 8 | 今日驾驶舱和信号审计页 | High | 2 天 | #7 |
| 9 | 公司卡片和股票池页面 | Medium | 1.5 天 | #3, #6 |
| 10 | 人工确认、复盘、审计日志 | High | 1 天 | #7, #8 |
| 11 | 日报生成 | Medium | 1 天 | #8, #10 |
| 12 | 测试样例和 E2E 验收 | Critical | 1.5 天 | 全部核心任务 |

补充说明：为了让第一版就产生超出预期的投研价值，实际实施时应优先交付 `docs/specs/mvp-research-output-upgrade.md` 中定义的 5 个产出型能力。若工期冲突，优先保留反方证据、验证点、横向比较和 Top 3 变化，推迟完整主题页、完整复盘中心和多数据源自动接入。

依赖图：

```text
#1 初始化
  └─> #2 数据库
        ├─> #3 股票池/假设
        ├─> #4 原始文件/证据 ──> #5 公告 Agent
        └─> #6 评分引擎 <────── #5
              └─> #7 信号生成
                    ├─> #8 驾驶舱/审计页
                    ├─> #10 人工确认/复盘
                    └─> #11 日报
#12 测试验收依赖 #3-#11
```

## 20. 回滚策略

MVP 主要风险是数据和结论污染，不是线上流量。

回滚要求：

1. 所有 schema 变更必须有迁移回滚脚本。
2. 每次数据导入必须有 `ingestion_run_id`，便于删除某次导入产生的文档、证据、事件和信号。
3. 评分规则版本变更后，旧评分不覆盖，新增 `score_version`。
4. Agent prompt 版本变更后，旧输出保留，不原地改写。
5. UI 错误不允许改写历史决策，只能新增修正记录。

## 21. 风险与待确认问题

待确认但不阻塞 MVP：

1. 第一批固定股票池股票数量：建议 20-50 只，不建议一开始全市场。
2. 数据供应商：Tushare Pro、Ricequant、AKShare、手动 CSV 的优先级需按可用 token、费用、授权确认。
3. 前端选型：Streamlit 最快，自建 Web 更长期。
4. OpenAI 组织数据政策：如果使用 Agents SDK tracing，需要确认是否允许把投研输入进入 OpenAI trace 系统；如不允许，需要关闭或自建 trace。
5. 交易记录是否录入真实价格和仓位：MVP 可只记录决策，不记录敏感仓位。

## 22. Definition of Done

MVP 交付完成定义：

1. 用户每天打开今日驾驶舱即可看到新增信号、风险、候选池变化和待复核事项。
2. 任一信号点击后都能追溯到原始文件、证据摘录、评分变化和规则 ID。
3. 系统不会基于低等级来源生成高等级候选信号。
4. 系统不会在 Q = D 时把股票放入候选池。
5. 用户可以对所有待复核信号做确认、忽略、加入复盘。
6. 日报能基于当日真实事件和评分变化生成，不靠模型自由编造。
7. 测试计划中的核心 Unit、Integration、E2E 测试通过。

升级后的 MVP 还必须满足：

1. 每个交易日生成不超过 3 条 Top Changes，且每条都有 `why_it_matters`。
2. 每个活跃投资假设能生成体检状态：增强、减弱、未变、证伪或待复核。
3. 每个候选池股票都有最近 7 天内的同板块横向比较卡。
4. 每个候选信号都有风险雷达，且列出至少 1 个 `what_would_reduce_this_risk`。
5. 每个候选池和持仓观察股票都有 pending 验证点。
6. 验证点过期后进入日报提醒。
7. 用户可以把任一研究问题标记为 `有帮助`、`噪音`、`加入复盘`。

## 23. 参考资料

以下资料在 2026-06-01 做过轻量核验，后续实现前仍需复核接口、授权、费用和条款：

1. 上海证券交易所上市公司公告：https://www.sse.com.cn/disclosure/listedinfo/announcement/
2. 深圳证券交易所上市公司公告：https://www.szse.cn/disclosure/listed/notice/index.html
3. 巨潮资讯网：https://www.cninfo.com.cn/new/index
4. Tushare 数据接口文档：https://tushare.pro/document/2
5. AKShare 项目概览：https://akshare.akfamily.xyz/introduction.html
6. Ricequant RQData 文档：https://www.ricequant.com/doc/rqdata/python/stock-mod
7. OpenAI Responses API：https://developers.openai.com/api/reference/responses/overview
8. OpenAI Assistants migration guide：https://developers.openai.com/api/docs/assistants/migration
9. OpenAI Structured Outputs：https://developers.openai.com/api/docs/guides/structured-outputs
10. OpenAI Agents guardrails and human review：https://developers.openai.com/api/docs/guides/agents/guardrails-approvals
11. OpenAI Agents SDK tracing：https://openai.github.io/openai-agents-python/tracing/

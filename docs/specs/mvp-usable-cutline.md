# 可用 MVP 开发切线：砍掉平台化动作，先跑出雷达报告

验证日期：2026-06-02

适用文档：

- `docs/specs/early-multibagger-radar-redesign.md`
- `docs/specs/agent-native-radar-architecture.md`
- `docs/specs/information-source-cost-classification.md`

## 1. 结论

当前计划方向正确，但第一版仍然过大。它同时想做 agent runtime、SQLite/job queue、source catalog、KOL 档案、claim graph、path engine、完整 Signal Lab、信息源页面、自动抓取和 eval dashboard。

这会让 MVP 从「能不能帮用户捕捉早期信号」变成「先搭一个投研平台」。应立即砍线。

MVP 的可用定义改为：

> 用户手动输入一批弱信号、证据和测试持仓后，系统能在一次分析里输出早期雷达报告：claim、来源归因、交叉验证矩阵、KOL-only 阻断、历史差异、验证任务、反方证据和人工复核建议。

第一版不追求自动扫描全市场，也不追求完整 Agent SDK 编排。第一版只追求一个研究闭环：

```text
手动输入弱信号/证据
  ↓
结构化 claim
  ↓
来源和 KOL 归因
  ↓
交叉验证和阻断
  ↓
生成验证任务
  ↓
输出雷达报告
  ↓
用户确认/忽略/加入复盘
```

## 2. DX 评审结果

### 2.1 当前计划的开发体验问题

| 问题 | 证据 | 对 MVP 的伤害 |
| --- | --- | --- |
| 计划一次性引入太多基础设施 | `agent-native-radar-architecture.md` 同时规划 SQLite、jobs、agent_runs、tool_calls、providers、tools、workflows、evals。 | 开发先做平台，迟迟不能验证投研产出。 |
| UI 范围太大 | `early-multibagger-radar-redesign.md` 要做弱信号收件箱、交叉验证矩阵、历史时间线、12 个月路径、证伪地图。 | 第一版前端容易拖慢核心引擎。 |
| 数据源计划过早平台化 | `information-source-cost-classification.md` 规划 source_catalog、信息源页面、采购评审、月度来源复盘。 | 这些是治理能力，不是第一份报告的必要条件。 |
| Agent 数量过多 | 当前架构规划 Scout、Extraction、Verification、Reasoning、Editor 多类 Agent。 | Agent 边界未被真实样例校准前，拆太细会增加协调成本。 |
| 12 个月路径过早完整化 | 路径、milestone、expiry worker、kill map 都在首版范围里。 | 对早期线索而言，先有 30/90 天验证任务即可。 |

### 2.2 DX 分数

| 维度 | 当前计划 | 砍线后目标 | 说明 |
| --- | ---: | ---: | --- |
| Time to First Useful Report | 3/10 | 8/10 | 从多阶段平台建设改为一次分析生成雷达报告。 |
| Implementation Clarity | 5/10 | 8/10 | 从 10 个子系统砍到 5 个模块。 |
| Debuggability | 5/10 | 8/10 | 保留同步流程和 JSON store，先避免 job queue 并发问题。 |
| Scope Control | 4/10 | 9/10 | 自动抓取、采购、完整 UI、eval dashboard 全部后置。 |
| User-visible Value | 6/10 | 8/10 | 第一版直接围绕测试持仓和早期线索出报告。 |

TTHW 目标：

```text
开发者启动现有服务：< 2 分钟
接入第一批测试线索：< 10 分钟
生成第一份雷达报告：< 30 秒
完成第一轮人工处理：< 15 分钟
```

## 3. MVP 必须保留

只保留能让第一份雷达报告可信的能力。

### 3.1 手动弱信号输入

必须支持 JSON 输入，不做自动抓取。

```json
{
  "stock_code": "300000.SZ",
  "stock_name": "示例公司",
  "theme": "AI 应用",
  "weak_signals": [
    {
      "signal_text": "某 AI 产业 KOL 称公司产品被头部客户试用",
      "source_family": "expert_kol",
      "source_rank": "C",
      "source_url": "https://x.com/example/status/1",
      "raw_excerpt": "原文必要摘录",
      "kol_profile": {
        "handle": "@example_ai_chain",
        "kol_quality_score": 72,
        "conflict_flags": ["持仓未知"]
      }
    }
  ],
  "evidence": [
    {
      "claim": "客户官网出现相关产品页面",
      "source_family": "public_footprint",
      "source_rank": "C",
      "source_url": "https://customer.example/product",
      "raw_excerpt": "页面必要摘录"
    }
  ],
  "prior_claims": [
    {
      "claim_text": "公司 AI 应用收入尚未验证",
      "status": "created",
      "scores": {"E": 45, "X": 20, "I": 0, "U": 30, "D": "B"}
    }
  ],
  "risks": ["KOL 持仓未知", "尚无公告确认"]
}
```

### 3.2 最小领域对象

MVP 只需要这些对象，不建完整数据库表：

```text
RadarEvidence
RadarClaim
SourceProfile
CrossValidationResult
ClaimRevision
ValidationTask
BearCase
RadarReport
```

继续用 JSON store 保存最新报告和用户决策即可。追加 `radar_reports`、`radar_decisions`、`radar_claims_snapshot` 三个 key，不做 SQLite 迁移。

### 3.3 最小 Agent 集

把多个 Agent 合并成 4 个产出型 Agent/步骤：

| MVP Agent | 合并范围 | 输出 |
| --- | --- | --- |
| Intake Agent | 弱信号捕捉 + 来源归因 + KOL 初评 | evidence、source_profile、初始 claim |
| Validation Agent | 交叉验证 + claim link + 阻断规则解释 | cross_validation_result、upgrade_blockers |
| Diff/Risk Agent | 历史差异 + 反方证据 | claim_revision、bear_cases |
| Editor Agent | 主编报告 | radar_report |

这些 Agent 可以先是普通 Python 函数 + LLM JSON 调用，不需要 OpenAI Agents SDK、handoff、streaming 或工具编排。

最小 skill 配置以 `cic/agent_skills.py` 为准：

| MVP Agent | 默认 skill |
| --- | --- |
| Intake Agent | 手动信源导入、来源归因、claim 提取、KOL 档案查询、证据去重 |
| Validation Agent | claim 图谱查询、交叉验证、验证任务生成、来源授权门禁 |
| Diff/Risk Agent | 历史差异、反证挖掘、财务质量分析、行情/板块分析、验证任务生成 |
| Editor Agent | claim 图谱查询、引用包生成、雷达 brief 主编；不配置网页抓取或公告抓取 |

凡是 `public_web_scrape`、`official_disclosure_fetch`、`market_snapshot_analysis`、`financial_statement_analysis` 这类自动访问或外部数据 skill，都必须经过 `source_catalog_gate`。KOL Scout 默认只吃人工导入，不自动抓社媒。

### 3.4 最小规则

必须实现：

1. KOL-only 不得进入候选。
2. D 级来源只能进入弱信号。
3. 两个同一 `independence_group` 不重复加分。
4. 两个独立来源家族支持时 X 上升。
5. A/B 级反证优先置顶。
6. 每个弱信号至少生成一个验证任务。
7. 所有建议都必须是人工复核，不得给无条件买卖指令。

### 3.5 最小 UI

保留现有页面结构，不重做完整 Signal Lab。

新增一个区域即可：

```text
早期雷达报告
  - 弱信号
  - 交叉验证
  - 阻断原因
  - 历史差异
  - 下一验证任务
  - 反方证据
```

现有输入框复用，支持粘贴 radar JSON。现有“生成投研报告”按钮可以改成支持两种输入：

1. holdings JSON：走旧 `/api/holdings/analyze`。
2. radar JSON：走新 `/api/radar/analyze`。

## 4. MVP 明确砍掉

这些不是不要，而是第一版不做。

| 砍掉项 | 原计划位置 | 为什么砍 | 后续触发条件 |
| --- | --- | --- | --- |
| SQLite migration | `agent-native-radar-architecture.md` Phase 1 | JSON store 足够跑第一批测试线索。 | 报告历史超过 50 份或 claim 查询变慢。 |
| Job queue | 同上 | MVP 用同步分析即可，少一个并发和状态复杂度。 | 自动抓取或长任务超过 30 秒。 |
| OpenAI Agents SDK / handoff | Provider 架构 | 当前智谱兼容接口已经可用，先统一 JSON 输出。 | 需要多工具自动编排时再接。 |
| tool_calls 全审计 | Observability | 第一版只有手动输入和 LLM 调用，`agent_runs` 简化记录即可。 | 接入自动工具后再补。 |
| 完整 source_catalog 数据库 | 信息源规格 Phase A/B | 先用常量/YAML-like dict，不做页面。 | 自动化来源超过 5 个。 |
| 信息源页面 | 信息源规格 Phase C | 不影响第一份报告。 | 用户开始管理多个付费/授权来源。 |
| 采购评审卡 | 信息源规格 Phase D | MVP 先不用付费源。 | 准备采购 X API、Wind、行业数据时。 |
| 自动抓取交易所/巨潮/X | 多处 | 自动化会带来授权和稳定性问题。 | 手动输入验证价值后再做。 |
| 完整 12 个月 path engine | 雷达规格 Phase 4 | 早期 MVP 先输出 30/90 天验证任务。 | 至少 5 条 claim 进入 inflection watch 后。 |
| milestone expiry worker | 同上 | 没有 job queue 前不做 worker。 | 引入 job queue 后。 |
| 完整 Signal Lab 重设计 | 雷达规格 Phase 5 | 先复用现有页面，避免前端拖慢闭环。 | 引擎产出稳定后再设计。 |
| Agent eval dashboard | 架构规格 Phase 4 | 固定样例测试先够用。 | prompt 版本频繁迭代后。 |
| 月度来源复盘 | 信息源规格 Phase D | 没有足够历史数据。 | 累积 30 天以上信号结果。 |

## 5. 精简后的开发任务

### Task 1：Radar 数据模型和规则函数

文件：

```text
cic/models.py
cic/radar_rules.py
tests/test_radar_rules.py
```

范围：

1. 新增 dataclass：`RadarEvidence`、`RadarClaim`、`SourceProfile`、`ValidationTask`、`RadarReport`。
2. 实现 source family normalization。
3. 实现 KOL-only gate。
4. 实现 simple X score。
5. 实现 validation task generation。

验收：

1. D 级社媒输入后只产生 `raw_weak_signal`。
2. 单一 KOL 不能进入候选。
3. KOL + public_footprint 可以进入 `validation_queue` 或 `evidence_convergence`。
4. 每条弱信号都有验证任务。

### Task 2：同步 Radar 分析服务

文件：

```text
cic/radar_report.py
cic/llm.py
tests/test_radar_report.py
```

范围：

1. 实现 `analyze_radar_input(payload, use_llm=True)`。
2. 复用当前 `LLMClient`，新增 radar prompt。
3. LLM 失败时 fallback 到 deterministic report。
4. 输出 `cross_validation`、`claim_revisions`、`bear_cases`、`validation_tasks`。

验收：

1. 不配置 API key 也能生成报告。
2. 配置 API key 时只影响摘要和问题质量，不影响 gate。
3. 输出不包含无条件买卖建议。

### Task 3：API 和存储

文件：

```text
cic/server.py
cic/storage.py
tests/test_server.py
```

范围：

1. 新增 `POST /api/radar/analyze`。
2. 新增 `GET /api/radar/latest`。
3. JSON store 追加 `radar_reports`。
4. 保留旧 API 不变。

验收：

1. 旧 `/api/holdings/analyze` 继续通过测试。
2. 新 radar API 能保存并返回最新报告。
3. 非法 payload 返回清晰错误。

### Task 4：最小前端

文件：

```text
web/index.html
web/app.js
web/styles.css
```

范围：

1. 输入区增加模式选择：持仓分析 / 早期雷达。
2. 增加雷达报告区域。
3. 展示交叉验证、阻断原因、验证任务、反方证据。
4. 不做完整三栏 Signal Lab。

验收：

1. 用户可粘贴样例 radar JSON。
2. 点击生成后看到报告。
3. 空状态和错误状态可读。
4. 移动端不发生明显重叠。

### Task 5：样例和测试

文件：

```text
data/sample_radar_signals.json
tests/test_radar_rules.py
tests/test_radar_report.py
```

范围：

1. 新增一个 KOL-only 样例。
2. 新增一个 KOL + public_footprint 样例。
3. 新增一个 A/B 级反证样例。
4. 测试 report 输出字段和 gate。

验收：

1. `python -m unittest discover -s tests` 全部通过。
2. 本地页面能用样例生成第一份雷达报告。

## 6. 精简后的依赖图

```text
Task 1 Radar 规则和模型
  └─> Task 2 Radar 分析服务
        ├─> Task 3 API/存储
        └─> Task 5 样例/测试
              └─> Task 4 最小前端
```

可以并行：

- Task 3 的 API 路由可在 Task 2 函数形状确定后并行。
- Task 4 可先做静态渲染，等 Task 3 接入。

不要并行：

- 不要在 Task 1 未稳定前做完整 UI。
- 不要在 Task 2 未输出稳定 JSON 前接 Agents SDK。

## 7. 新的 MVP Definition of Done

MVP 完成只需要满足以下 12 条：

1. 用户能加载 `data/sample_radar_signals.json`。
2. 用户能粘贴自己的 radar JSON。
3. 系统能生成至少 1 条 claim。
4. 系统能展示来源家族和 source_rank。
5. 系统能展示交叉验证矩阵或等价列表。
6. 单一 KOL 来源被明确阻断候选升级。
7. 系统能生成下一验证任务。
8. 系统能展示至少 1 条反方证据或未知项。
9. 系统能展示历史差异；若没有历史，则显示“无历史 claim”。
10. 用户能对报告执行确认、忽略、加入复盘三类动作中的至少一种。
11. 没有 API key 时仍可生成 fallback 报告。
12. 全部测试通过，现有持仓分析不回退。

## 8. 暂缓后的 Phase 2

第一版跑通后，再按真实痛点扩展：

1. 如果手动输入太慢，再做 source_catalog 和自动抓取。
2. 如果报告历史难查，再迁移 SQLite。
3. 如果单次分析超过 30 秒，再做 job queue。
4. 如果 LLM prompt 版本频繁变化，再做 agent_runs 和 evals。
5. 如果用户开始依赖 KOL 档案，再做 source_profiles 页面。
6. 如果验证任务变多，再做 Signal Lab 三栏 UI。

## 9. DevEx 评审结论

**CRITICAL GAP**：当前计划的第一版交付物不够锋利。它描述了完整平台，却没有强制第一周内产出第一份早期雷达报告。

**CUT**：SQLite、job queue、Agents SDK、自动抓取、完整信息源页面、采购卡、完整 12 个月 path engine、完整 Signal Lab、eval dashboard 全部后置。

**KEEP**：手动 radar JSON 输入、来源/KOL 归因、KOL-only gate、交叉验证、验证任务、反方证据、fallback 报告、最小前端展示。

**NEXT BUILD TARGET**：实现 `POST /api/radar/analyze` 和 `data/sample_radar_signals.json`，让用户可以在本地页面生成第一份可审阅的早期雷达报告。

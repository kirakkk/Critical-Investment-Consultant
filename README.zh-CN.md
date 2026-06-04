# Critical Investment Consultant

语言：[English](README.md) | 简体中文

一个本地优先的 A 股投研驾驶舱。当前 MVP 围绕每日投研产出，而不是荐股或交易提示：

1. 今日最重要 3 条变化。
2. 投资假设体检。
3. 同板块横向比较卡片。
4. 反方风险雷达。
5. 下一验证日历。
6. 早期弱信号雷达，包含 KOL-only 阻断、交叉验证、历史差异、验证任务和反方证据。
7. 证伪自动驾驶深挖，把高价值阻断项转成有证据支撑的 verdict，再允许进入升级复核。
8. 前瞻实验室，用于全市场信源探索、前端观测、交叉比对、传导假设和情景测算。

系统不会自动交易，也不会输出无条件买入或卖出指令。LLM 用于阅读、摘要、反方生成和研究问题生成；规则代码负责评分、硬门禁和状态迁移。

下一阶段产品方向不是通用 dashboard，而是早期非共识多倍股雷达。重设计后的弱信号、交叉验证、历史差异和 12 个月路径规格见 `docs/specs/early-multibagger-radar-redesign.md`。从“共识证据收集”转向“供应链瓶颈传导”的第一性原理设计见 `docs/specs/non-consensus-alpha-first-principles.md`。Agent-native 执行架构见 `docs/specs/agent-native-radar-architecture.md`。精简后的 MVP 开发切线见 `docs/specs/mvp-usable-cutline.md`。

## 本地运行

```powershell
python -m cic.server
```

然后打开：

```text
http://127.0.0.1:8765
```

## 可选 LLM

运行前创建本地 `.env`，或直接设置环境变量：

```powershell
$env:ZHIPU_BASE_URL="https://open.bigmodel.cn/api/coding/paas/v4"
$env:ZHIPU_API_KEY="your-local-key"
$env:ZHIPU_MODEL="glm-5.1"
$env:LLM_TIMEOUT_SECONDS="120"
```

即使没有 LLM key，应用也会使用确定性 fallback 逻辑继续运行，这能保持测试稳定，并避免误用本地密钥。

## 可选 Obsidian LLM Wiki

早期雷达也可以把每次分析编译成 Obsidian 友好的 LLM Wiki 旁路知识库。启动服务前设置路径：

```powershell
$env:CIC_OBSIDIAN_WIKI_PATH="D:\Obsidian\Critical-Investment-Consultant"
```

之后 `POST /api/radar/analyze` 会在该路径下写出 Markdown 页面：

```text
raw/      不可变原始来源捕获
company/  公司档案，并保留人工笔记
theme/    行业和主题档案
claim/    claim 级证据页面
source/   来源和 KOL 画像
task/     验证任务笔记
inbox/    Obsidian 输入模板
```

数据库仍然是结构化事实层。Wiki 是人可读的第二大脑，用于浏览、链接、人工笔记和后续综合分析。

设计分岔、最终架构和分阶段导入计划见 `docs/specs/obsidian-llm-wiki-second-brain.md`。

## 早期雷达 MVP

使用网页按钮 `德明利雷达`，或直接调用 API：

```text
GET  /api/sample-radar-signals
POST /api/radar/analyze
GET  /api/radar/latest
GET  /api/radar/deep-dives
POST /api/radar/deep-dives/{task_id}/run
POST /api/radar/deep-dives/{task_id}/decision
POST /api/radar/claims/{claim_id}/decision
GET  /api/radar/decisions
POST /api/radar/forward-alpha/run
GET  /api/radar/forward-alpha/latest
GET  /api/radar/forward-alpha/runs/{run_id}
GET  /api/radar/forward-alpha/sources
POST /api/radar/forward-alpha/source-decisions/{source_id}
POST /api/radar/forward-alpha/manual-imports/{task_id}
```

样例雷达输入位于 `data/sample_radar_signals.json`。它使用德明利 (`001309.SZ`) 验证核心机制：KOL 弱信号、公司和官方证据、交叉验证、财务反向信号，以及后续验证任务。

`POST /api/radar/analyze` 现在会自动创建 deep-dive 任务，并默认只自动运行优先级最高的 1-2 个任务。Deep-dive verdict 被限制为 `blocker_maintained`、`blocker_softened`、`blocker_removed`、`claim_falsified` 或 `insufficient_evidence`；它们都是待复核草稿，永远不会直接升级股票状态。

同一次雷达分析也会默认运行前瞻实验室。它会把德明利这类输入自动展开成 NAND/DRAM 价格、渠道价格、招投标/订单、产能利用率、KOL 弱信号和现金流质量等前瞻信源候选。授权受限或授权未知的来源不会自动抓取，只会进入待人工导入任务，直到你授权或手动粘贴证据。前瞻实验室默认把运行记录保存在 `data/forward_alpha.db`，也可以通过 `CIC_FORWARD_ALPHA_DB_PATH` 指定路径。

## 测试

```powershell
python -m unittest discover -s tests
```

## 样例持仓

`data/sample_holdings.json` 包含一组可以粘贴进网页的小型合成持仓。等你提供真实测试持仓后，同一个 `/api/holdings/analyze` 路径会对它们评分，并生成第一份复核报告。

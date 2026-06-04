# Critical Investment Consultant

Languages: English | [简体中文](README.zh-CN.md)

A local-first A-share investment research cockpit. The current MVP is built around daily research outputs rather than stock tips:

1. Top 3 changes.
2. Investment thesis checks.
3. Peer comparison cards.
4. Bear-case risk radar.
5. Next validation calendar.
6. Early weak-signal radar with KOL-only blocking, cross-validation, historical diffs, validation tasks, and bear cases.
7. Falsification Autopilot deep dives that turn high-value blockers into evidence-backed verdicts before any upgrade.
8. Forward Alpha Lab for source discovery, forward sensor observations, cross-source comparison, transmission hypotheses, and scenario analysis.

The system does not auto-trade and does not produce unconditional buy/sell instructions. LLM output is used for reading, summarizing, counterargument generation, and research questions; rule code controls scoring, hard gates, and state transitions.

The next product direction is an early non-consensus multibagger radar rather than a generic dashboard. See `docs/specs/early-multibagger-radar-redesign.md` for the redesigned weak-signal, cross-validation, historical-diff, and 12-month path spec. See `docs/specs/non-consensus-alpha-first-principles.md` for the first-principles design note that shifts the product from consensus evidence collection to supply-chain bottleneck transmission. See `docs/specs/agent-native-radar-architecture.md` for the agent-native execution architecture, and `docs/specs/mvp-usable-cutline.md` for the trimmed MVP build plan.

## Run Locally

```powershell
python -m cic.server
```

Then open:

```text
http://127.0.0.1:8765
```

## Optional LLM

Create a local `.env` or set environment variables before running:

```powershell
$env:ZHIPU_BASE_URL="https://open.bigmodel.cn/api/coding/paas/v4"
$env:ZHIPU_API_KEY="your-local-key"
$env:ZHIPU_MODEL="glm-5.1"
$env:LLM_TIMEOUT_SECONDS="120"
```

The app also works without an LLM key using deterministic fallback logic, which keeps tests stable and prevents accidental secret usage.

## Optional Obsidian LLM Wiki

The radar can also compile each analysis into an Obsidian-friendly LLM Wiki sidecar. Set this path before running the server:

```powershell
$env:CIC_OBSIDIAN_WIKI_PATH="D:\Obsidian\Critical-Investment-Consultant"
```

Then `POST /api/radar/analyze` writes Markdown pages under:

```text
raw/      immutable source captures
company/  company dossiers with preserved human notes
theme/    industry/theme dossiers
claim/    claim-level evidence pages
source/   source and KOL profiles
task/     validation task notes
inbox/    Obsidian input templates
```

The database remains the structured fact store. The wiki is the human-readable second brain for browsing, linking, manual notes, and later synthesis.

See `docs/specs/obsidian-llm-wiki-second-brain.md` for the design variants, selected architecture, and phased import plan.

## Early Radar MVP

Use the web button `德明利雷达` or call the API directly:

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

The sample radar input is `data/sample_radar_signals.json`. It uses 德明利 (`001309.SZ`) to validate the mechanics: a KOL weak signal, company/official evidence, cross-validation, a financial counter-signal, and follow-up validation tasks.

`POST /api/radar/analyze` now creates deep-dive tasks automatically and, by default, only auto-runs the highest-priority one or two tasks. Deep-dive verdicts are constrained to `blocker_maintained`, `blocker_softened`, `blocker_removed`, `claim_falsified`, or `insufficient_evidence`; they are drafts for review and never directly upgrade a stock.

The same radar analysis also runs Forward Alpha Lab by default. It expands 德明利-style inputs into forward-looking source candidates such as NAND/DRAM pricing, channel prices, tender/order checks, capacity-utilization evidence, KOL weak signals, and cash-flow quality. Restricted or unknown-license sources are never fetched automatically; they become manual import tasks until you authorize or paste the evidence yourself. Forward Alpha Lab stores runs in `data/forward_alpha.db` by default, or the path set by `CIC_FORWARD_ALPHA_DB_PATH`.

## Test

```powershell
python -m unittest discover -s tests
```

## Sample Holdings

`data/sample_holdings.json` contains a small synthetic portfolio you can paste into the web app. When you provide your real test holdings, the same `/api/holdings/analyze` path will score them and generate the first review report.

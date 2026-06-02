# Critical Investment Consultant

A local-first A-share investment research cockpit. The current MVP is built around daily research outputs rather than stock tips:

1. Top 3 changes.
2. Investment thesis checks.
3. Peer comparison cards.
4. Bear-case risk radar.
5. Next validation calendar.

The system does not auto-trade and does not produce unconditional buy/sell instructions. LLM output is used for reading, summarizing, counterargument generation, and research questions; rule code controls scoring, hard gates, and state transitions.

The next product direction is an early non-consensus multibagger radar rather than a generic dashboard. See `docs/specs/early-multibagger-radar-redesign.md` for the redesigned weak-signal, cross-validation, historical-diff, and 12-month path spec.

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
$env:ZHIPU_MODEL="glm-4.6"
```

The app also works without an LLM key using deterministic fallback logic, which keeps tests stable and prevents accidental secret usage.

## Test

```powershell
python -m unittest discover -s tests
```

## Sample Holdings

`data/sample_holdings.json` contains a small synthetic portfolio you can paste into the web app. When you provide your real test holdings, the same `/api/holdings/analyze` path will score them and generate the first review report.

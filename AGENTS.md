# Repository Agent Guide

本项目是本地优先的 A 股投研驾驶舱 / 早期非共识多倍股雷达。Agent 的角色是研究劳动力：发现、阅读、提取、归因、比对、反驳和生成验证任务。Agent 不能替代规则引擎、不能直接给买卖建议，也不能绕过来源授权。

本文件给代码协作 agent 使用。CIC 产品内部的研究 agent skill 配置在 `cic/agent_skills.py`，设计说明见 `docs/specs/agent-native-radar-architecture.md`。

## Operating Boundary

- Keep the product framed as `A股投研驾驶舱，而不是荐股机器人`.
- Preserve deterministic gates in `cic/rules.py`, `cic/radar_rules.py`, and related tests.
- Treat KOL / X sources as early-signal inputs, not authorities. `expert_kol` stays separate from `social_rumor`.
- KOL-only claims must stay blocked or in validation until corroborated by a non-KOL source family.
- Keep source credibility separate from procurement and automation policy. `license_status=unknown` or restricted access blocks automation.
- Favor Chinese-visible product labels and research outputs unless the user asks otherwise.
- For changes, prefer the durable repo workflow: spec under `docs/specs/`, focused implementation, then `python -m unittest discover -s tests`.

## Coding Workflow Skills

Project agents should have access to the local gstack skill sidecar at `.agents/skills/gstack`. This directory is a local link to the installed gstack checkout and should not be vendored into git. See `.agents/README.md`.

Use these skills when the request matches:

| Situation | Skill |
| --- | --- |
| Turn a vague idea into an executable spec or issue | `/spec` |
| Challenge product scope, positioning, or MVP value | `/plan-ceo-review` |
| Lock architecture, schemas, source gates, jobs, and tests | `/plan-eng-review` |
| Explore UI directions for Signal Lab, radar views, or cockpit screens | `/design-shotgun` |
| Review visual polish after UI changes | `/design-review` |
| Debug a failing behavior or suspicious result | `/investigate` |
| Test the local web app in a real browser and fix issues | `/qa` |
| Test without changing code | `/qa-only` |
| Review code before landing | `/review` |
| Ship a branch / PR with tests and review | `/ship` |
| Save or restore long-running context | `/context-save`, `/context-restore` |

## Agent Role Routing

- Product / radar strategy agent: use `/plan-ceo-review`, `/spec`, and `/autoplan` for major scope changes.
- Engineering agent: use `/plan-eng-review`, `/investigate`, `/review`, and `/health` for schema, workflow, and reliability work.
- Source-governance agent: use `/spec` or `/plan-eng-review`; never automate unknown or restricted sources without explicit authorization.
- UI / design agent: use `/design-shotgun` for variants and `/design-review` plus `/qa` for verification.
- Release agent: use `/ship`, `/document-release`, and `python -m unittest discover -s tests`.

## Design-Shotgun Notes

Use `/design-shotgun` when the user asks for visual alternatives, says the app is not relatable enough, wants design variants, or is deciding how the radar / cockpit should feel. For this product, design variants must support fast research review: dense but scannable evidence, provenance, validation state, contradiction visibility, and human-review actions. Avoid marketing-page hero treatments for operational screens.

## Source And Research Rules

- Official disclosures, exchange / CNINFO, financial data, and clearly licensed public-footprint evidence can support validation.
- KOL, social, forum, or screenshot-only evidence can raise priority but cannot confirm a claim alone.
- Automation must pass the source catalog / license gate first. Manual paste or manual upload is the fallback for restricted or unknown sources.
- Any agent-generated fact needs object IDs, raw excerpts, source family, source rank, and unknowns before it can influence scoring.

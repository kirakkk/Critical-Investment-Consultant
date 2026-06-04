from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .models import utc_now_iso


USER_SECTION_START = "<!-- CIC:USER-NOTES:START -->"
USER_SECTION_END = "<!-- CIC:USER-NOTES:END -->"
SCHEMA_FILE = "CIC-LLM-WIKI.md"
WIKI_ENV_VARS = ("CIC_OBSIDIAN_WIKI_PATH", "CIC_OBSIDIAN_VAULT_PATH")


def export_radar_wiki_if_configured(payload: dict[str, Any]) -> dict[str, Any]:
    target = configured_wiki_path()
    if not target:
        return {"status": "disabled", "message": "Set CIC_OBSIDIAN_WIKI_PATH to enable Obsidian wiki export."}
    try:
        return write_radar_wiki(payload, target)
    except (OSError, ValueError) as exc:
        return {"status": "failed", "error": str(exc), "root": str(target)}


def configured_wiki_path() -> Path | None:
    for key in WIKI_ENV_VARS:
        value = os.getenv(key)
        if value:
            return Path(value).expanduser()
    return None


def write_radar_wiki(payload: dict[str, Any], root: str | Path) -> dict[str, Any]:
    root_path = Path(root).expanduser()
    root_path.mkdir(parents=True, exist_ok=True)
    _ensure_structure(root_path)

    report = payload.get("radar_report") if isinstance(payload.get("radar_report"), dict) else payload
    if not isinstance(report, dict):
        raise ValueError("payload must include radar_report")

    now = utc_now_iso()
    report_id = str(report.get("report_id") or "radar-report")
    generated_date = str(report.get("generated_at") or now)[:10]
    stock_code = str(report.get("stock_code") or "UNKNOWN")
    stock_name = str(report.get("stock_name") or stock_code)
    theme = str(report.get("theme") or "未分类")

    paths = _page_paths(root_path, report, generated_date)
    raw_created = _write_raw_page(paths["raw"], payload, report, now)
    _write_schema_if_missing(root_path)
    _write_inbox_template_if_missing(root_path)

    company_link = _obsidian_link(root_path, paths["company"], stock_name)
    theme_link = _obsidian_link(root_path, paths["theme"], theme)
    report_link = _obsidian_link(root_path, paths["report"], f"{stock_name} 雷达报告 {generated_date}")

    _write_report_page(root_path, paths["report"], payload, report, paths, now)
    _write_company_page(root_path, paths["company"], report, paths, company_link, theme_link, report_link, now)
    _write_theme_page(root_path, paths["theme"], report, paths, company_link, theme_link, report_link, now)
    _write_claim_pages(root_path, report, paths, company_link, theme_link, report_link, now)
    _write_source_pages(root_path, report, paths, company_link, report_link, now)
    _write_task_pages(root_path, report, paths, company_link, report_link, now)
    index_path = _write_index(root_path, report, paths, now)
    log_path = _append_log(root_path, report, paths, now, raw_created)

    files = {name: str(path) for name, path in paths.items()}
    files["index"] = str(index_path)
    files["log"] = str(log_path)
    files["schema"] = str(root_path / SCHEMA_FILE)

    return {
        "status": "exported",
        "root": str(root_path),
        "updated_at": now,
        "report_id": report_id,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "files": files,
    }


def _ensure_structure(root: Path) -> None:
    for folder in ("raw", "report", "company", "theme", "claim", "source", "task", "inbox"):
        (root / folder).mkdir(parents=True, exist_ok=True)


def _page_paths(root: Path, report: dict[str, Any], generated_date: str) -> dict[str, Path]:
    report_id = str(report.get("report_id") or "radar-report")
    stock_code = str(report.get("stock_code") or "UNKNOWN")
    stock_name = str(report.get("stock_name") or stock_code)
    theme = str(report.get("theme") or "未分类")
    return {
        "raw": root / "raw" / generated_date / f"{_safe_filename(report_id)}.md",
        "report": root / "report" / f"{generated_date}-{_safe_filename(stock_code)}-{_safe_filename(report_id)}.md",
        "company": root / "company" / f"{_safe_filename(stock_code)}-{_safe_filename(stock_name)}.md",
        "theme": root / "theme" / f"{_safe_filename(theme)}.md",
    }


def _write_raw_page(path: Path, payload: dict[str, Any], report: dict[str, Any], now: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = _frontmatter(
        {
            "id": report.get("report_id"),
            "type": "raw_radar_report",
            "stock_code": report.get("stock_code"),
            "stock_name": report.get("stock_name"),
            "theme": report.get("theme"),
            "created_at": now,
            "immutable": True,
            "tags": ["cic/raw", "a-share", "radar"],
        }
    )
    text = "\n".join(
        [
            frontmatter,
            f"# Raw Radar Source - {report.get('stock_name', '')}",
            "",
            "This page is the immutable source capture for one radar run. Do not edit it; add human notes under linked company/theme/claim pages instead.",
            "",
            "## Report JSON",
            "",
            "```json",
            json.dumps(payload, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    _atomic_write(path, text)
    return True


def _write_report_page(
    root: Path,
    path: Path,
    payload: dict[str, Any],
    report: dict[str, Any],
    paths: dict[str, Path],
    now: str,
) -> None:
    company = _obsidian_link(root, paths["company"], str(report.get("stock_name") or report.get("stock_code")))
    theme = _obsidian_link(root, paths["theme"], str(report.get("theme") or "未分类"))
    raw = _obsidian_link(root, paths["raw"], "raw source")
    frontmatter = _frontmatter(
        {
            "id": report.get("report_id"),
            "type": "radar_report",
            "stock_code": report.get("stock_code"),
            "stock_name": report.get("stock_name"),
            "theme": report.get("theme"),
            "radar_state": report.get("radar_state"),
            "generated_at": report.get("generated_at"),
            "updated_at": now,
            "tags": ["cic/report", "a-share", "radar"],
        }
    )
    text = "\n".join(
        [
            frontmatter,
            f"# {report.get('stock_name')} 雷达报告",
            "",
            f"- 公司: {company}",
            f"- 主题: {theme}",
            f"- Raw: {raw}",
            f"- 状态: `{report.get('radar_state', 'unknown')}`",
            f"- 评分: {_score_text(report.get('scores'))}",
            "",
            "## 摘要",
            "",
            str(report.get("summary") or "暂无摘要"),
            "",
            "## Claims",
            "",
            _claim_bullets(root, report, paths),
            "",
            "## 交叉验证",
            "",
            _cross_validation_table(report.get("cross_validation", [])),
            "",
            "## 阻断原因",
            "",
            _list_or_empty(report.get("upgrade_blockers", [])),
            "",
            "## 下一验证任务",
            "",
            _task_bullets(root, report, paths),
            "",
            "## 反方证据",
            "",
            _bear_case_bullets(report.get("bear_cases", [])),
            "",
            "## Editor Questions",
            "",
            _list_or_empty(payload.get("editor_questions", [])),
            "",
        ]
    )
    _atomic_write(path, text)


def _write_company_page(
    root: Path,
    path: Path,
    report: dict[str, Any],
    paths: dict[str, Path],
    company_link: str,
    theme_link: str,
    report_link: str,
    now: str,
) -> None:
    existing = _read_existing(path)
    frontmatter = _frontmatter(
        {
            "id": report.get("stock_code"),
            "type": "company",
            "stock_code": report.get("stock_code"),
            "stock_name": report.get("stock_name"),
            "theme": report.get("theme"),
            "radar_state": report.get("radar_state"),
            "updated_at": now,
            "tags": ["cic/company", "a-share", "radar"],
        }
    )
    text = "\n".join(
        [
            frontmatter,
            f"# {report.get('stock_name')} ({report.get('stock_code')})",
            "",
            f"- 主题: {theme_link}",
            f"- 最新报告: {report_link}",
            f"- 当前状态: `{report.get('radar_state', 'unknown')}`",
            f"- 最新评分: {_score_text(report.get('scores'))}",
            "",
            "## 核心 Claims",
            "",
            _claim_bullets(root, report, paths),
            "",
            "## 证据摘要",
            "",
            _evidence_table(report.get("evidence", [])),
            "",
            "## 下一验证任务",
            "",
            _task_bullets(root, report, paths),
            "",
            _user_section(existing, "## 我的笔记\n\n- \n\n## 待验证问题\n\n- \n"),
            "",
            "## 反方和阻断",
            "",
            _list_or_empty(report.get("upgrade_blockers", [])),
            "",
            _bear_case_bullets(report.get("bear_cases", [])),
            "",
            "## 相关链接",
            "",
            f"- 公司页: {company_link}",
            f"- Raw: {_obsidian_link(root, paths['raw'], 'latest raw source')}",
            "",
        ]
    )
    _atomic_write(path, text)


def _write_theme_page(
    root: Path,
    path: Path,
    report: dict[str, Any],
    paths: dict[str, Path],
    company_link: str,
    theme_link: str,
    report_link: str,
    now: str,
) -> None:
    existing = _read_existing(path)
    frontmatter = _frontmatter(
        {
            "id": _safe_filename(str(report.get("theme") or "未分类")),
            "type": "theme",
            "theme": report.get("theme"),
            "updated_at": now,
            "tags": ["cic/theme", "a-share", "radar"],
        }
    )
    text = "\n".join(
        [
            frontmatter,
            f"# {report.get('theme')}",
            "",
            f"- 最新公司: {company_link}",
            f"- 最新报告: {report_link}",
            "",
            "## 主题内公司",
            "",
            f"- {company_link}: `{report.get('radar_state', 'unknown')}` / {_score_text(report.get('scores'))}",
            "",
            "## 主题 Claims",
            "",
            _claim_bullets(root, report, paths),
            "",
            "## 证据来源家族",
            "",
            _source_family_bullets(report.get("evidence", [])),
            "",
            _user_section(existing, "## 我的主题笔记\n\n- \n\n## 想继续补的来源\n\n- \n"),
            "",
            "## 主题链接",
            "",
            f"- 当前主题页: {theme_link}",
            "",
        ]
    )
    _atomic_write(path, text)


def _write_claim_pages(
    root: Path,
    report: dict[str, Any],
    paths: dict[str, Path],
    company_link: str,
    theme_link: str,
    report_link: str,
    now: str,
) -> None:
    evidence_by_id = {str(item.get("evidence_id")): item for item in report.get("evidence", []) if isinstance(item, dict)}
    cross_by_claim = {
        str(item.get("claim_id")): item for item in report.get("cross_validation", []) if isinstance(item, dict)
    }
    tasks_by_claim: dict[str, list[dict[str, Any]]] = {}
    for task in report.get("validation_tasks", []):
        if isinstance(task, dict):
            tasks_by_claim.setdefault(str(task.get("claim_id")), []).append(task)

    for claim in report.get("claims", []):
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("claim_id") or "claim")
        path = root / "claim" / f"{_safe_filename(str(report.get('stock_code')))}-{_safe_filename(claim_id)}.md"
        paths[f"claim:{claim_id}"] = path
        existing = _read_existing(path)
        related_evidence = [evidence_by_id[item] for item in claim.get("evidence_ids", []) if item in evidence_by_id]
        cross = cross_by_claim.get(claim_id, {})
        frontmatter = _frontmatter(
            {
                "id": claim_id,
                "type": "claim",
                "stock_code": claim.get("stock_code"),
                "stock_name": claim.get("stock_name"),
                "theme": claim.get("theme"),
                "status": claim.get("status"),
                "updated_at": now,
                "tags": ["cic/claim", "a-share", "radar"],
            }
        )
        text = "\n".join(
            [
                frontmatter,
                f"# Claim - {claim.get('stock_name')}",
                "",
                f"- 公司: {company_link}",
                f"- 主题: {theme_link}",
                f"- 最新报告: {report_link}",
                f"- 状态: `{claim.get('status', 'unknown')}`",
                f"- 阶段: `{claim.get('thesis_stage', 'unknown')}`",
                f"- 评分: {_score_text(claim.get('scores'))}",
                "",
                "## Claim",
                "",
                str(claim.get("claim_text") or ""),
                "",
                "## 交叉验证",
                "",
                _claim_cross_summary(cross),
                "",
                "## 相关证据",
                "",
                _evidence_table(related_evidence),
                "",
                "## 阻断原因",
                "",
                _list_or_empty(claim.get("upgrade_blockers", [])),
                "",
                "## 下一验证任务",
                "",
                _task_list_for_claim(tasks_by_claim.get(claim_id, [])),
                "",
                _user_section(existing, "## 我的判断\n\n- \n\n## 后续补证\n\n- \n"),
                "",
            ]
        )
        _atomic_write(path, text)


def _write_source_pages(
    root: Path,
    report: dict[str, Any],
    paths: dict[str, Path],
    company_link: str,
    report_link: str,
    now: str,
) -> None:
    evidence = [item for item in report.get("evidence", []) if isinstance(item, dict)]
    evidence_by_group = {}
    for item in evidence:
        key = (str(item.get("source_family")), str(item.get("independence_group")))
        evidence_by_group.setdefault(key, []).append(item)

    for source in report.get("source_profiles", []):
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("source_id") or "source")
        path = root / "source" / f"{_safe_filename(source_id)}-{_safe_filename(str(source.get('source_name') or 'source'))}.md"
        paths[f"source:{source_id}"] = path
        existing = _read_existing(path)
        related = evidence_by_group.get(
            (str(source.get("source_family")), str(source.get("independence_group"))),
            [],
        )
        frontmatter = _frontmatter(
            {
                "id": source_id,
                "type": "source",
                "source_family": source.get("source_family"),
                "source_rank": source.get("source_rank"),
                "cost_class": source.get("cost_class"),
                "updated_at": now,
                "tags": ["cic/source", "a-share", "radar"],
            }
        )
        text = "\n".join(
            [
                frontmatter,
                f"# {source.get('source_name')}",
                "",
                f"- 来源家族: `{source.get('source_family')}`",
                f"- 等级: `{source.get('source_rank')}`",
                f"- 可信度: `{source.get('credibility_score')}`",
                f"- 成本类别: `{source.get('cost_class')}`",
                f"- 独立组: `{source.get('independence_group')}`",
                f"- 相关公司: {company_link}",
                f"- 最新报告: {report_link}",
                "",
                "## 偏差和冲突",
                "",
                _list_or_empty([*(source.get("known_biases") or []), *(source.get("conflict_flags") or [])]),
                "",
                "## 相关证据",
                "",
                _evidence_table(related),
                "",
                _user_section(existing, "## 来源复盘\n\n- \n"),
                "",
            ]
        )
        _atomic_write(path, text)


def _write_task_pages(
    root: Path,
    report: dict[str, Any],
    paths: dict[str, Path],
    company_link: str,
    report_link: str,
    now: str,
) -> None:
    for task in report.get("validation_tasks", []):
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id") or "task")
        path = root / "task" / f"{_safe_filename(task_id)}.md"
        paths[f"task:{task_id}"] = path
        existing = _read_existing(path)
        claim_path = paths.get(f"claim:{task.get('claim_id')}")
        claim_link = _obsidian_link(root, claim_path, str(task.get("claim_id"))) if claim_path else str(task.get("claim_id"))
        frontmatter = _frontmatter(
            {
                "id": task_id,
                "type": "validation_task",
                "claim_id": task.get("claim_id"),
                "status": task.get("status"),
                "priority": task.get("priority"),
                "due_date": task.get("due_date"),
                "updated_at": now,
                "tags": ["cic/task", "a-share", "radar"],
            }
        )
        text = "\n".join(
            [
                frontmatter,
                f"# 验证任务 - {task.get('task_type')}",
                "",
                f"- 公司: {company_link}",
                f"- Claim: {claim_link}",
                f"- 最新报告: {report_link}",
                f"- 优先级: `{task.get('priority')}`",
                f"- 截止日期: `{task.get('due_date')}`",
                f"- 目标来源家族: `{task.get('target_source_family')}`",
                "",
                "## 问题",
                "",
                str(task.get("question") or ""),
                "",
                "## 成功标准",
                "",
                str(task.get("success_criteria") or ""),
                "",
                "## 失败标准",
                "",
                str(task.get("failure_criteria") or ""),
                "",
                _user_section(existing, "## 验证记录\n\n- [ ] \n"),
                "",
            ]
        )
        _atomic_write(path, text)


def _write_index(root: Path, report: dict[str, Any], paths: dict[str, Path], now: str) -> Path:
    path = root / "index.md"
    pages = _catalog_pages(root)
    text = "\n".join(
        [
            _frontmatter({"type": "index", "updated_at": now, "tags": ["cic/index", "a-share", "radar"]}),
            "# Critical Investment Consultant LLM Wiki",
            "",
            "这个 vault 是 A 股投研雷达的第二大脑：`raw/` 保留不可变事实源，`company/`、`theme/`、`claim/`、`source/` 和 `task/` 是可读、可链接、可人工补充的知识层。",
            "",
            "## 最新导出",
            "",
            f"- 公司: {_obsidian_link(root, paths['company'], str(report.get('stock_name') or report.get('stock_code')))}",
            f"- 主题: {_obsidian_link(root, paths['theme'], str(report.get('theme') or '未分类'))}",
            f"- 报告: {_obsidian_link(root, paths['report'], str(report.get('report_id') or 'latest report'))}",
            f"- Raw: {_obsidian_link(root, paths['raw'], 'latest raw source')}",
            "",
            "## 页面目录",
            "",
            _catalog_markdown(root, pages),
            "",
            "## 使用约定",
            "",
            f"- 规则见 [[{SCHEMA_FILE.removesuffix('.md')}|{SCHEMA_FILE}]]。",
            "- 你可以编辑每页 `CIC:USER-NOTES` 标记之间的人工笔记区；自动导出会保留这部分。",
            "- 不要编辑 `raw/` 下的页面，它们是事实捕获层。",
            "",
        ]
    )
    _atomic_write(path, text)
    return path


def _append_log(root: Path, report: dict[str, Any], paths: dict[str, Path], now: str, raw_created: bool) -> Path:
    path = root / "log.md"
    entry = "\n".join(
        [
            f"## [{now}] ingest | {report.get('stock_name')} | {report.get('report_id')}",
            "",
            f"- 公司: {_obsidian_link(root, paths['company'], str(report.get('stock_name') or report.get('stock_code')))}",
            f"- 主题: {_obsidian_link(root, paths['theme'], str(report.get('theme') or '未分类'))}",
            f"- 报告: {_obsidian_link(root, paths['report'], str(report.get('report_id') or 'report'))}",
            f"- Raw: {_obsidian_link(root, paths['raw'], 'raw source')} ({'created' if raw_created else 'already existed'})",
            f"- Claims: {len(report.get('claims', []))}",
            f"- Evidence: {len(report.get('evidence', []))}",
            f"- Tasks: {len(report.get('validation_tasks', []))}",
            "",
        ]
    )
    if path.exists():
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n" + entry)
    else:
        _atomic_write(path, "# Wiki Log\n\n" + entry)
    return path


def _write_schema_if_missing(root: Path) -> None:
    path = root / SCHEMA_FILE
    if path.exists():
        return
    text = """# CIC LLM Wiki Schema

This wiki follows the Karpathy LLM Wiki pattern for the Critical Investment Consultant project.

## Layers

- `raw/`: immutable source captures. Do not edit.
- `company/`: company dossiers compiled from radar reports and human notes.
- `theme/`: industry/theme dossiers.
- `claim/`: versioned investment research claims and their evidence.
- `source/`: source profiles, KOL notes, bias flags, and evidence history.
- `task/`: validation tasks and manual verification records.
- `inbox/`: human-authored notes waiting to be processed.

## Editing Rules

- Preserve evidence provenance. Never turn a user note or KOL claim into an official fact.
- Keep `source_family/source_rank` separate from `cost_class/access_mode/license_status`.
- KOL-only evidence can raise validation priority, but it cannot confirm a claim alone.
- Human edits should go inside `CIC:USER-NOTES` blocks or `inbox/`.
- Generated sections can be rewritten by the exporter.
- Answers should cite wiki pages and raw sources where possible.

## Intake Workflow

1. Drop new notes, copied article text, screenshots references, or company observations into `inbox/`.
2. Convert each useful observation into a claim, evidence item, source profile update, or validation task.
3. Update related `company/`, `theme/`, `claim/`, and `source/` pages.
4. Append a short entry to `log.md`.

## Research Policy

This system is a research-validation assistant, not a stock-picking robot. It should produce questions, evidence chains, contradiction maps, and validation tasks, not unconditional buy/sell instructions.
"""
    _atomic_write(path, text)


def _write_inbox_template_if_missing(root: Path) -> None:
    path = root / "inbox" / "_template.md"
    if path.exists():
        return
    text = """---
type: inbox_note
status: unprocessed
tags:
  - cic/inbox
---

# 新投研输入

## 观察对象

- 公司:
- 主题:
- 来源:
- 日期:

## 原始材料


## 我想验证的问题

- 

## 可能的 Claim

- 
"""
    _atomic_write(path, text)


def _catalog_pages(root: Path) -> dict[str, list[Path]]:
    catalog: dict[str, list[Path]] = {}
    for folder in ("company", "theme", "claim", "source", "task", "report"):
        folder_path = root / folder
        catalog[folder] = sorted(folder_path.glob("*.md")) if folder_path.exists() else []
    return catalog


def _catalog_markdown(root: Path, pages: dict[str, list[Path]]) -> str:
    lines: list[str] = []
    labels = {
        "company": "Companies",
        "theme": "Themes",
        "claim": "Claims",
        "source": "Sources",
        "task": "Tasks",
        "report": "Reports",
    }
    for folder, files in pages.items():
        lines.append(f"### {labels.get(folder, folder)}")
        lines.append("")
        if not files:
            lines.append("- 暂无")
        else:
            for path in files:
                lines.append(f"- {_obsidian_link(root, path, path.stem)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _claim_bullets(root: Path, report: dict[str, Any], paths: dict[str, Path]) -> str:
    lines = []
    for claim in report.get("claims", []):
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("claim_id") or "claim")
        path = paths.get(f"claim:{claim_id}") or root / "claim" / f"{_safe_filename(str(report.get('stock_code')))}-{_safe_filename(claim_id)}.md"
        link = _obsidian_link(root, path, str(claim.get("claim_text") or claim_id)[:60])
        lines.append(f"- {link} - `{claim.get('status', 'unknown')}` / {_score_text(claim.get('scores'))}")
    return "\n".join(lines) if lines else "- 暂无"


def _task_bullets(root: Path, report: dict[str, Any], paths: dict[str, Path]) -> str:
    lines = []
    for task in report.get("validation_tasks", []):
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id") or "task")
        path = paths.get(f"task:{task_id}") or root / "task" / f"{_safe_filename(task_id)}.md"
        link = _obsidian_link(root, path, str(task.get("question") or task_id)[:60])
        lines.append(f"- {link} - `{task.get('priority', 'P1')}` / due `{task.get('due_date', '')}`")
    return "\n".join(lines) if lines else "- 暂无"


def _task_list_for_claim(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return "- 暂无"
    return "\n".join(
        f"- `{task.get('priority', 'P1')}` {task.get('question', '')} (due `{task.get('due_date', '')}`)"
        for task in tasks
    )


def _bear_case_bullets(items: list[Any]) -> str:
    lines = []
    for item in items:
        if isinstance(item, dict):
            lines.append(
                f"- `{item.get('severity', 'unknown')}` {item.get('claim', '')} 缓解条件: {item.get('what_would_reduce_this_risk', '')}"
            )
    return "\n".join(lines) if lines else "- 暂无"


def _source_family_bullets(items: list[Any]) -> str:
    counts: dict[str, int] = {}
    for item in items:
        if isinstance(item, dict):
            family = str(item.get("source_family") or "unknown")
            counts[family] = counts.get(family, 0) + 1
    return "\n".join(f"- `{family}`: {count}" for family, count in sorted(counts.items())) if counts else "- 暂无"


def _cross_validation_table(items: list[Any]) -> str:
    rows = ["| Claim | Gate | Supports | Contradictions | X |", "| --- | --- | ---: | ---: | ---: |"]
    for item in items:
        if isinstance(item, dict):
            rows.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(item.get("claim_id")),
                        _md_cell(item.get("gate_status")),
                        str(item.get("support_count", 0)),
                        str(item.get("contradiction_count", 0)),
                        str(item.get("x_score_after", "")),
                    ]
                )
                + " |"
            )
    return "\n".join(rows) if len(rows) > 2 else "- 暂无"


def _claim_cross_summary(cross: dict[str, Any]) -> str:
    if not cross:
        return "- 暂无"
    return "\n".join(
        [
            f"- Gate: `{cross.get('gate_status', 'unknown')}`",
            f"- Result: `{cross.get('result_state', 'unknown')}`",
            f"- Source families: {', '.join(str(item) for item in cross.get('source_families', [])) or '暂无'}",
            f"- Independent groups: {', '.join(str(item) for item in cross.get('independent_groups', [])) or '暂无'}",
            f"- X: `{cross.get('x_score_before', 0)} -> {cross.get('x_score_after', 0)}`",
            "",
            "### Strongest Support",
            _evidence_table(cross.get("strongest_support", [])),
            "",
            "### Strongest Contradictions",
            _evidence_table(cross.get("strongest_contradictions", [])),
        ]
    )


def _evidence_table(items: list[Any]) -> str:
    rows = ["| Date | Source | Rank | Stance | Claim | URL |", "| --- | --- | --- | --- | --- | --- |"]
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("source_url") or "")
        link = f"[link]({url})" if url.startswith(("http://", "https://")) else _md_cell(url or "-")
        rows.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("evidence_date")),
                    _md_cell(item.get("source_title") or item.get("source_name") or item.get("source_family")),
                    _md_cell(item.get("source_rank")),
                    _md_cell(item.get("stance")),
                    _md_cell(item.get("claim")),
                    link,
                ]
            )
            + " |"
        )
    return "\n".join(rows) if len(rows) > 2 else "- 暂无"


def _list_or_empty(items: list[Any]) -> str:
    values = [str(item) for item in items if str(item).strip()]
    return "\n".join(f"- {item}" for item in values) if values else "- 暂无"


def _score_text(scores: Any) -> str:
    if not isinstance(scores, dict):
        return "`E 0 / X 0 / I 0 / U 0 / D ?`"
    return (
        f"`E {scores.get('E', 0)} / X {scores.get('X', 0)} / "
        f"I {scores.get('I', 0)} / U {scores.get('U', 0)} / D {scores.get('D', '?')}`"
    )


def _user_section(existing: str, default_body: str) -> str:
    body = default_body.strip()
    if USER_SECTION_START in existing and USER_SECTION_END in existing:
        start = existing.index(USER_SECTION_START) + len(USER_SECTION_START)
        end = existing.index(USER_SECTION_END, start)
        body = existing[start:end].strip()
    return f"{USER_SECTION_START}\n{body}\n{USER_SECTION_END}"


def _read_existing(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _frontmatter(values: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_yaml_scalar(item)}")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _obsidian_link(root: Path, path: Path | None, alias: str) -> str:
    if path is None:
        return alias
    relative = path.relative_to(root).with_suffix("").as_posix()
    return f"[[{relative}|{alias}]]"


def _safe_filename(value: str, fallback: str = "untitled") -> str:
    text = str(value or fallback).strip()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip(" .-")
    if not text:
        text = fallback
    return text[:120].rstrip(" .-")


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")
    tmp.replace(path)

from __future__ import annotations

import json
from typing import Any

from .llm import LLMClient
from .models import RadarReport, to_jsonable, utc_now_iso
from .radar_rules import (
    bear_cases_for,
    build_radar_claims,
    claim_revisions_for,
    cross_validate_claim,
    evidence_from_payload,
    normalize_radar_input,
    prior_x_score_for,
    related_evidence,
    source_profiles_for,
    stable_id,
    unique_items,
    validation_tasks_for,
)


def analyze_radar_input(payload: dict[str, Any], llm_client: LLMClient | None = None, use_llm: bool = True) -> dict[str, Any]:
    radar = normalize_radar_input(payload)
    evidence = evidence_from_payload(radar)
    profiles = source_profiles_for(evidence)
    claims = build_radar_claims(radar, evidence, profiles)
    cross_results = []
    for claim in claims:
        seed = next((item for item in evidence if item.claim == claim.claim_text), evidence[0] if evidence else None)
        if seed:
            cross_results.append(cross_validate_claim(seed, related_evidence(seed, evidence), prior_x_score_for(radar, seed.claim)))

    revisions = claim_revisions_for(radar, claims)
    validation_tasks = validation_tasks_for(radar, claims, cross_results)
    bear_cases = bear_cases_for(radar, claims, evidence)
    blockers = unique_items(blocker for claim in claims for blocker in claim.upgrade_blockers)
    state = strongest_state([claim.status for claim in claims])
    scores = aggregate_scores([claim.scores for claim in claims])

    fallback_editor = heuristic_radar_editor(radar, claims, cross_results, validation_tasks, bear_cases)
    llm_status = "disabled"
    llm_error = ""
    editor = fallback_editor
    if use_llm:
        client = llm_client or LLMClient()
        system_prompt, user_prompt = build_radar_prompt(radar, claims, cross_results, validation_tasks, bear_cases)
        result = client.chat_json(system_prompt, user_prompt, fallback_editor)
        editor = safe_editor_payload(result.data, fallback_editor)
        llm_status = result.status
        llm_error = result.error

    report = RadarReport(
        report_id=stable_id(radar["stock_code"], utc_now_iso(), "radar", prefix="rrp_"),
        stock_code=radar["stock_code"],
        stock_name=radar["stock_name"],
        theme=radar["theme"],
        generated_at=utc_now_iso(),
        generated_by="radar-rule-engine+llm-editor",
        summary=str(editor.get("summary") or fallback_editor["summary"]),
        radar_state=state,
        scores=scores,
        claims=[to_jsonable(item) for item in claims],
        evidence=[to_jsonable(item) for item in evidence],
        source_profiles=[to_jsonable(item) for item in profiles],
        cross_validation=[to_jsonable(item) for item in cross_results],
        claim_revisions=[to_jsonable(item) for item in revisions],
        validation_tasks=[to_jsonable(item) for item in validation_tasks],
        bear_cases=[to_jsonable(item) for item in bear_cases],
        upgrade_blockers=blockers,
        suggested_user_action=suggested_user_action(state, blockers),
        llm_status=llm_status,
    )

    return {
        "radar_report": to_jsonable(report),
        "editor_questions": editor.get("editor_questions", fallback_editor["editor_questions"]),
        "input": radar,
        "llm": {
            "status": llm_status,
            "error": llm_error,
            "provider": "zhipu-openai-compatible",
        },
    }


def strongest_state(states: list[str]) -> str:
    order = {
        "blocked_risk": 6,
        "contradicted_review": 5,
        "inflection_watch": 4,
        "evidence_convergence": 3,
        "validation_queue": 2,
        "raw_weak_signal": 1,
    }
    if not states:
        return "raw_weak_signal"
    return max(states, key=lambda item: order.get(item, 0))


def aggregate_scores(scores: list[dict[str, Any]]) -> dict[str, Any]:
    if not scores:
        return {"E": 0, "X": 0, "I": 0, "U": 0, "D": "B"}
    risk_order = {"A": 1, "B": 2, "C": 3, "D": 4}
    return {
        "E": max(int(item.get("E", 0)) for item in scores),
        "X": max(int(item.get("X", 0)) for item in scores),
        "I": max(int(item.get("I", 0)) for item in scores),
        "U": max(int(item.get("U", 0)) for item in scores),
        "D": max((str(item.get("D", "B")) for item in scores), key=lambda item: risk_order.get(item, 0)),
    }


def suggested_user_action(state: str, blockers: list[str]) -> str:
    if state == "inflection_watch":
        return "进入强验证观察清单；仍需人工复核，不生成无条件交易动作。"
    if state == "evidence_convergence":
        return "证据开始交叉验证，优先完成公告/财务/客户侧验证任务。"
    if state == "contradicted_review":
        return "先处理 A/B 级反证，反证未解除前不要升级。"
    if blockers:
        return "保留早期线索，逐项验证阻断原因。"
    return "保留为弱信号，等待第二独立来源。"


def heuristic_radar_editor(
    radar: dict[str, Any],
    claims: list[Any],
    cross_results: list[Any],
    validation_tasks: list[Any],
    bear_cases: list[Any],
) -> dict[str, Any]:
    if not claims:
        return {
            "summary": f"{radar['stock_name']} 暂未形成可分析的早期 claim。",
            "editor_questions": ["先补充至少一条弱信号或证据。"],
        }
    claim = claims[0]
    cross = cross_results[0] if cross_results else None
    blockers = "；".join(claim.upgrade_blockers[:2]) if claim.upgrade_blockers else "暂无硬阻断，但仍需人工复核"
    summary = (
        f"{radar['stock_name']} 当前处于 {claim.status}。"
        f"核心原因是 X={claim.scores.get('X')}，独立来源数={cross.support_count if cross else 0}，"
        f"阻断项：{blockers}。系统建议继续做验证任务，不输出自动交易结论。"
    )
    questions = [
        task.question
        for task in validation_tasks[:3]
    ] or ["下一步需要寻找非 KOL 独立来源。"]
    if bear_cases:
        questions.append(f"反方优先核查：{bear_cases[0].claim}")
    return {"summary": summary, "editor_questions": questions[:4]}


def build_radar_prompt(
    radar: dict[str, Any],
    claims: list[Any],
    cross_results: list[Any],
    validation_tasks: list[Any],
    bear_cases: list[Any],
) -> tuple[str, str]:
    system = (
        "你是 A 股早期翻倍雷达的主编。"
        "只输出 JSON，不输出 Markdown。"
        "不要给无条件买入、卖出、加仓、减仓建议。"
        "你只能总结规则结果，并提出人工复核问题。"
        "JSON 字段必须为 summary 和 editor_questions。"
    )
    user = {
        "task": "根据规则产物生成一段克制摘要和 2-4 个下一步人工复核问题。",
        "schema": {"summary": "string", "editor_questions": ["string"]},
        "stock": {"code": radar["stock_code"], "name": radar["stock_name"], "theme": radar["theme"]},
        "claims": [to_jsonable(item) for item in claims],
        "cross_validation": [to_jsonable(item) for item in cross_results],
        "validation_tasks": [to_jsonable(item) for item in validation_tasks],
        "bear_cases": [to_jsonable(item) for item in bear_cases[:5]],
    }
    return system, json.dumps(user, ensure_ascii=False)


def safe_editor_payload(data: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    forbidden = ("买入", "卖出", "加仓", "减仓", "满仓", "梭哈")
    summary = str(data.get("summary") or "")
    questions = data.get("editor_questions")
    if any(word in summary for word in forbidden):
        return fallback
    if not isinstance(questions, list):
        questions = fallback["editor_questions"]
    clean_questions = [str(item) for item in questions if not any(word in str(item) for word in forbidden)]
    return {"summary": summary or fallback["summary"], "editor_questions": clean_questions[:4] or fallback["editor_questions"]}


def latest_radar_report_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {
            "radar_report": {
                "stock_code": "",
                "stock_name": "",
                "theme": "",
                "summary": "暂无早期雷达报告",
                "radar_state": "not_run",
                "scores": {"E": 0, "X": 0, "I": 0, "U": 0, "D": "B"},
                "claims": [],
                "evidence": [],
                "source_profiles": [],
                "cross_validation": [],
                "claim_revisions": [],
                "validation_tasks": [],
                "bear_cases": [],
                "upgrade_blockers": [],
                "suggested_user_action": "先载入样例或粘贴 radar JSON。",
                "llm_status": "not_run",
            },
            "editor_questions": [],
            "llm": {"status": "not_run", "error": "", "provider": "zhipu-openai-compatible"},
        }
    return report

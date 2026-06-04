from __future__ import annotations

import time
from typing import Any

from .models import (
    DeepDiveFinding,
    DeepDiveRun,
    DeepDiveTask,
    DeepDiveVerdict,
    to_jsonable,
    utc_now_iso,
)
from .rules import stable_id


ALLOWED_VERDICTS = {
    "blocker_maintained",
    "blocker_softened",
    "blocker_removed",
    "claim_falsified",
    "insufficient_evidence",
}
DEFAULT_BUDGET = {"max_sources": 5, "max_llm_calls": 2, "timeout_seconds": 120, "max_token_estimate": 3200}
FULL_SOURCE_FAMILIES = [
    "official_disclosure",
    "exchange_regulator",
    "financial_data",
    "market_data",
    "industry_data",
    "company_website",
    "public_footprint",
    "media_news",
    "research_report",
    "expert_kol",
    "forum",
    "social_media",
    "manual",
]
SOURCE_POLICY = {
    "official_disclosure": {"license_status": "known", "automation": "auto"},
    "exchange_regulator": {"license_status": "known", "automation": "auto"},
    "financial_data": {"license_status": "known", "automation": "auto"},
    "market_data": {"license_status": "known", "automation": "auto"},
    "industry_data": {"license_status": "known", "automation": "auto"},
    "company_website": {"license_status": "known", "automation": "auto"},
    "public_footprint": {"license_status": "known", "automation": "auto"},
    "media_news": {"license_status": "known", "automation": "auto"},
    "expert_kol": {"license_status": "manual_supplied", "automation": "manual_review"},
    "research_report": {"license_status": "restricted", "automation": "manual_input_only"},
    "forum": {"license_status": "unknown", "automation": "manual_input_only"},
    "social_media": {"license_status": "unknown", "automation": "manual_input_only"},
    "manual": {"license_status": "manual_supplied", "automation": "manual_review"},
}
RANK_VALUE = {"A": 4, "B": 3, "C": 2, "D": 1}
SOFT_SOURCE_FAMILIES = {"expert_kol", "forum", "social_media", "media_news", "research_report"}
CASHFLOW_TERMS = ("现金流", "经营活动", "经营现金流", "应收", "存货", "回款", "结算周期")
CUSTOMER_ORDER_TERMS = ("客户", "订单", "出货", "批量", "产能消化", "大客户", "采购", "定点")
EXPANSION_TERMS = ("SSD", "DRAM", "扩产", "募投", "产能", "毛利", "产能利用率", "利用率")
RESOLUTION_TERMS = ("现金流转正", "现金流改善", "回款改善", "应收下降", "存货下降", "结算周期缩短", "产能利用率提升", "毛利率改善")
FALSIFICATION_TERMS = ("财务造假", "重大违法", "立案调查", "核心客户流失", "项目终止", "订单取消")


def build_deep_dive_bundle(
    report_payload: dict[str, Any],
    auto_run: bool = True,
    max_auto_runs: int = 2,
) -> dict[str, list[dict[str, Any]]]:
    tasks = [to_jsonable(task) for task in deep_dive_tasks_for_report(report_payload)]
    bundle: dict[str, list[dict[str, Any]]] = {"tasks": tasks, "runs": [], "findings": [], "verdicts": []}
    if not auto_run:
        return bundle

    runnable = [task for task in tasks if should_auto_run(task, report_payload)]
    runnable.sort(key=task_sort_key)
    for task in runnable[:max_auto_runs]:
        bundle = merge_deep_dive_bundles(bundle, run_deep_dive_task(task, report_payload))
    return bundle


def deep_dive_tasks_for_report(report_payload: dict[str, Any]) -> list[DeepDiveTask]:
    report = report_payload.get("radar_report", report_payload)
    claims = report.get("claims") if isinstance(report.get("claims"), list) else []
    bears = report.get("bear_cases") if isinstance(report.get("bear_cases"), list) else []
    validation_tasks = report.get("validation_tasks") if isinstance(report.get("validation_tasks"), list) else []
    evidence = report.get("evidence") if isinstance(report.get("evidence"), list) else []
    tasks: list[DeepDiveTask] = []

    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        related_bears = [item for item in bears if str(item.get("claim_id") or "") == claim_id]
        related_validation = [item for item in validation_tasks if str(item.get("claim_id") or "") == claim_id]
        text = combined_text(claim, *related_bears, *related_validation, *evidence)

        cashflow_bear = first_matching_bear(related_bears, CASHFLOW_TERMS, require_high=False)
        high_counter = first_high_counter_bear(related_bears)
        if cashflow_bear or (high_counter and has_any(combined_text(high_counter), CASHFLOW_TERMS)):
            bear = cashflow_bear or high_counter or {}
            tasks.append(
                task_for(
                    report,
                    claim,
                    "cashflow_quality",
                    "现金流为负是否证伪业绩弹性",
                    str(bear.get("bear_case_id") or claim_id),
                    "A/B 级现金流反证会阻断早期业绩弹性 claim，必须优先解释。",
                    "P0" if str(bear.get("severity")) == "high" else "P1",
                )
            )

        customer_validation = first_validation_task(related_validation, ("official_check", "source_validation"))
        if customer_validation or has_any(text, CUSTOMER_ORDER_TERMS):
            tasks.append(
                task_for(
                    report,
                    claim,
                    "customer_order_capacity_validation",
                    "是否存在客户、订单或产能消化证据",
                    str(customer_validation.get("task_id") if customer_validation else claim_id),
                    "早期翻倍线索必须从叙事推进到客户、订单、出货或产能消化证据。",
                    "P1",
                )
            )

        expansion_bear = first_matching_bear(related_bears, EXPANSION_TERMS, require_high=False)
        expansion_evidence = first_matching_evidence(evidence, EXPANSION_TERMS)
        if expansion_bear or expansion_evidence or has_any(text, EXPANSION_TERMS):
            trigger_ref = str(
                (expansion_bear or {}).get("bear_case_id")
                or (expansion_evidence or {}).get("evidence_id")
                or claim_id
            )
            tasks.append(
                task_for(
                    report,
                    claim,
                    "capacity_margin_stress",
                    "SSD/DRAM 扩产是否压低毛利率和产能利用率",
                    trigger_ref,
                    "扩产是向前展望的正面线索，也可能带来价格周期、产能利用率和毛利率压力。",
                    "P1",
                )
            )

    return unique_tasks(tasks)


def task_for(
    report: dict[str, Any],
    claim: dict[str, Any],
    trigger_type: str,
    question: str,
    trigger_ref_id: str,
    trigger_reason: str,
    priority: str,
) -> DeepDiveTask:
    stock_name = str(report.get("stock_name") or claim.get("stock_name") or "")
    stock_code = str(report.get("stock_code") or claim.get("stock_code") or "")
    claim_id = str(claim.get("claim_id") or "")
    return DeepDiveTask(
        task_id=stable_id(report.get("report_id"), claim_id, trigger_type, question, prefix="ddt_"),
        report_id=str(report.get("report_id") or ""),
        claim_id=claim_id,
        stock_code=stock_code,
        stock_name=stock_name,
        question=f"{stock_name}：{question}？",
        trigger_type=trigger_type,
        trigger_ref_id=trigger_ref_id,
        trigger_reason=trigger_reason,
        priority=priority,
        allowed_source_families=list(FULL_SOURCE_FAMILIES),
        budget=dict(DEFAULT_BUDGET),
        status="pending",
        auto_run_eligible=True,
    )


def should_auto_run(task: dict[str, Any], report_payload: dict[str, Any]) -> bool:
    if not task.get("auto_run_eligible", True):
        return False
    report = report_payload.get("radar_report", report_payload)
    claim = next((item for item in report.get("claims", []) if item.get("claim_id") == task.get("claim_id")), {})
    scores = claim.get("scores") if isinstance(claim.get("scores"), dict) else {}
    high_value = (
        str(task.get("priority")) in {"P0", "P1"}
        or report.get("radar_state") == "contradicted_review"
        or int(scores.get("X") or report.get("scores", {}).get("X") or 0) >= 65
        or bool(report_payload.get("input", {}).get("is_holding") or report_payload.get("input", {}).get("focus"))
    )
    if task.get("trigger_type") == "cashflow_quality":
        return True
    return high_value


def run_deep_dive_task(task: dict[str, Any], report_payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    start = time.monotonic()
    started_at = utc_now_iso()
    budget = normalized_budget(task.get("budget"))
    if budget["timeout_seconds"] <= 0:
        return stopped_bundle(task, "timeout_budget_exhausted", started_at, start)
    if budget["max_sources"] <= 0:
        return stopped_bundle(task, "source_budget_exhausted", started_at, start)
    if budget["max_llm_calls"] < 0:
        return stopped_bundle(task, "llm_budget_exhausted", started_at, start)

    source_pool, policy_findings = source_pool_for_task(task, report_payload)
    source_pool = sort_sources_for_task(task, dedupe_sources(source_pool))
    stop_reason = ""
    if len(source_pool) > budget["max_sources"]:
        source_pool = source_pool[: budget["max_sources"]]
        stop_reason = "source_budget_reached"

    token_estimate = estimate_tokens(source_pool)
    if token_estimate > budget["max_token_estimate"]:
        source_pool = trim_to_token_budget(source_pool, budget["max_token_estimate"])
        token_estimate = estimate_tokens(source_pool)
        stop_reason = "token_budget_reached"

    findings = [*policy_findings]
    findings.extend(findings_for_sources(task, source_pool))
    findings.extend(unknown_findings_for_task(task, findings))
    verdict = verdict_for_task(task, findings)
    run = DeepDiveRun(
        run_id=stable_id(task.get("task_id"), started_at, "run", prefix="ddr_"),
        task_id=str(task.get("task_id") or ""),
        status="stopped" if stop_reason else "completed",
        model="rule-falsification-autopilot-v1",
        sources_checked=[source_summary(item) for item in source_pool],
        llm_calls_used=0,
        elapsed_ms=int((time.monotonic() - start) * 1000),
        token_estimate=token_estimate,
        stop_reason=stop_reason,
        started_at=started_at,
        finished_at=utc_now_iso(),
    )
    updated_task = dict(task)
    updated_task["status"] = "ran"
    return {
        "tasks": [updated_task],
        "runs": [to_jsonable(run)],
        "findings": [to_jsonable(item) for item in findings],
        "verdicts": [to_jsonable(verdict)],
    }


def source_pool_for_task(task: dict[str, Any], report_payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[DeepDiveFinding]]:
    report = report_payload.get("radar_report", report_payload)
    claim_id = str(task.get("claim_id") or "")
    claim = next((item for item in report.get("claims", []) if item.get("claim_id") == claim_id), {})
    evidence_ids = set(claim.get("evidence_ids") or [])
    pool: list[dict[str, Any]] = []
    policy_findings: list[DeepDiveFinding] = []
    for item in report.get("evidence", []):
        if evidence_ids and item.get("evidence_id") not in evidence_ids:
            continue
        if not policy_allows_automation(item):
            policy_findings.append(
                finding(
                    task,
                    "policy_block",
                    "来源授权不明或受限，只生成待人工录入任务，不能自动抓取。",
                    item,
                    score_impact=0,
                    confidence="high",
                )
            )
            continue
        pool.append(item)
    return pool, policy_findings


def findings_for_sources(task: dict[str, Any], sources: list[dict[str, Any]]) -> list[DeepDiveFinding]:
    findings: list[DeepDiveFinding] = []
    trigger_type = str(task.get("trigger_type") or "")
    for item in sources:
        text = combined_text(item)
        if trigger_type == "cashflow_quality":
            if item.get("stance") == "contradict" and has_any(text, CASHFLOW_TERMS):
                findings.append(finding(task, "counter", "经营现金流反证仍然成立。", item, score_impact=-10, confidence="high"))
            elif has_any(text, RESOLUTION_TERMS):
                findings.append(finding(task, "support", "出现现金流改善或解释线索。", item, score_impact=4, confidence="medium"))
        elif trigger_type == "customer_order_capacity_validation":
            if has_any(text, CUSTOMER_ORDER_TERMS) and item.get("stance") != "contradict":
                impact = 5 if non_soft_source(item) else 1
                findings.append(finding(task, "support", "出现客户、订单、出货或产能消化线索。", item, score_impact=impact, confidence="medium"))
            elif item.get("stance") == "contradict" and has_any(text, CUSTOMER_ORDER_TERMS):
                findings.append(finding(task, "counter", "客户、订单或产能消化方向出现反证。", item, score_impact=-8, confidence="high"))
        elif trigger_type == "capacity_margin_stress":
            if has_any(text, EXPANSION_TERMS) and item.get("stance") != "contradict":
                findings.append(finding(task, "support", "扩产事实存在，但尚未证明产能消化和毛利率改善。", item, score_impact=2, confidence="medium"))
            if item.get("stance") == "contradict" and has_any(text, ("毛利", "价格周期", "产能利用率", "现金流")):
                findings.append(finding(task, "counter", "扩产相关压力仍需优先验证。", item, score_impact=-6, confidence="medium"))
    return findings


def unknown_findings_for_task(task: dict[str, Any], findings: list[DeepDiveFinding]) -> list[DeepDiveFinding]:
    trigger_type = str(task.get("trigger_type") or "")
    finding_types = {item.finding_type for item in findings}
    support_text = " ".join(item.raw_excerpt for item in findings if item.finding_type == "support")
    unknowns: list[DeepDiveFinding] = []
    if trigger_type == "cashflow_quality" and "counter" in finding_types and not has_any(support_text, RESOLUTION_TERMS):
        unknowns.append(unknown_finding(task, "未找到现金流为负到底来自应收、存货还是结算周期的独立解释。"))
    if trigger_type == "customer_order_capacity_validation" and "support" not in finding_types:
        unknowns.append(unknown_finding(task, "未找到大客户订单、出货或产能消化的新增独立证据。"))
    if trigger_type == "capacity_margin_stress" and not has_any(support_text, ("产能利用率", "毛利率改善", "回款改善", "订单")):
        unknowns.append(unknown_finding(task, "未找到 SSD/DRAM 扩产后的产能利用率、毛利率和价格压力数据。"))
    if not findings:
        unknowns.append(unknown_finding(task, "未找到可进入深挖的新增独立证据。"))
    return unknowns


def verdict_for_task(task: dict[str, Any], findings: list[DeepDiveFinding]) -> DeepDiveVerdict:
    counters = [item for item in findings if item.finding_type == "counter"]
    supports = [item for item in findings if item.finding_type == "support"]
    unknowns = [item for item in findings if item.finding_type == "unknown"]
    high_counter = any(RANK_VALUE.get(item.source_rank, 0) >= 3 for item in counters)
    direct_resolution = any(has_any(combined_text(item.claim, item.raw_excerpt), RESOLUTION_TERMS) and non_soft_family(item.source_family) for item in supports)
    non_soft_support = [item for item in supports if non_soft_family(item.source_family)]
    soft_only_support = bool(supports) and not non_soft_support
    falsified = any(has_any(combined_text(item.claim, item.raw_excerpt), FALSIFICATION_TERMS) for item in counters)

    if falsified:
        verdict = "claim_falsified"
        summary = "出现足以证伪核心 claim 的高风险反证。"
        effect = "claim_falsified"
        score_impact = {"X": -20, "I": -15, "U": 18}
    elif high_counter and direct_resolution:
        verdict = "blocker_softened"
        summary = "A/B 级反证得到部分解释，但不能自动解除阻断或升级候选。"
        effect = "softened_only_human_review_required"
        score_impact = {"X": 4, "I": 0, "U": -4}
    elif high_counter:
        verdict = "blocker_maintained"
        summary = "A/B 级反证仍未被独立解释，阻断维持。"
        effect = "blocker_still_active"
        score_impact = {"X": -6, "I": -4, "U": 6}
    elif soft_only_support:
        verdict = "insufficient_evidence"
        summary = "目前只有 KOL、新闻、论坛或研报类辅助线索，不能解除阻断。"
        effect = "manual_or_non_kol_source_needed"
        score_impact = {"X": 0, "I": 0, "U": 4}
    elif non_soft_support and unknowns:
        verdict = "blocker_softened"
        summary = "找到部分非 KOL 证据，但关键未知项仍在，阻断仅缓解。"
        effect = "softened_not_removed"
        score_impact = {"X": 3, "I": 1, "U": -2}
    elif non_soft_support:
        verdict = "blocker_removed"
        summary = "找到非 KOL 独立证据，当前任务对应阻断可提交人工复核解除。"
        effect = "draft_removal_needs_rules_and_human"
        score_impact = {"X": 6, "I": 3, "U": -4}
    else:
        verdict = "insufficient_evidence"
        summary = "未找到新增独立证据，不能改变原始 claim 状态。"
        effect = "no_state_change"
        score_impact = {"X": 0, "I": 0, "U": 2}

    assert verdict in ALLOWED_VERDICTS
    return DeepDiveVerdict(
        task_id=str(task.get("task_id") or ""),
        verdict=verdict,
        summary=summary,
        blocker_effect=effect,
        score_impact=score_impact,
        review_required=verdict in {"blocker_maintained", "blocker_softened", "blocker_removed", "claim_falsified"},
    )


def stopped_bundle(task: dict[str, Any], reason: str, started_at: str, start: float) -> dict[str, list[dict[str, Any]]]:
    run = DeepDiveRun(
        run_id=stable_id(task.get("task_id"), started_at, reason, prefix="ddr_"),
        task_id=str(task.get("task_id") or ""),
        status="stopped",
        model="rule-falsification-autopilot-v1",
        sources_checked=[],
        llm_calls_used=0,
        elapsed_ms=int((time.monotonic() - start) * 1000),
        token_estimate=0,
        stop_reason=reason,
        started_at=started_at,
        finished_at=utc_now_iso(),
    )
    updated_task = dict(task)
    updated_task["status"] = "stopped"
    verdict = DeepDiveVerdict(
        task_id=str(task.get("task_id") or ""),
        verdict="insufficient_evidence",
        summary="深挖预算已耗尽，未产生可用新增证据。",
        blocker_effect=reason,
        score_impact={"X": 0, "I": 0, "U": 3},
        review_required=True,
    )
    return {"tasks": [updated_task], "runs": [to_jsonable(run)], "findings": [], "verdicts": [to_jsonable(verdict)]}


def merge_deep_dive_bundles(base: dict[str, list[dict[str, Any]]], incoming: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    merged = {key: list(base.get(key, [])) for key in ("tasks", "runs", "findings", "verdicts")}
    unique_keys = {
        "tasks": "task_id",
        "runs": "run_id",
        "findings": "finding_id",
        "verdicts": "task_id",
    }
    for key, id_key in unique_keys.items():
        by_id = {str(item.get(id_key) or ""): item for item in merged[key]}
        for item in incoming.get(key, []):
            item_id = str(item.get(id_key) or "")
            if item_id:
                by_id[item_id] = item
            else:
                merged[key].append(item)
        merged[key] = list(by_id.values()) + [item for item in merged[key] if not item.get(id_key)]
    return merged


def normalized_budget(value: Any) -> dict[str, int]:
    budget = dict(DEFAULT_BUDGET)
    if isinstance(value, dict):
        budget.update(value)
    return {key: int(budget[key]) for key in DEFAULT_BUDGET}


def task_sort_key(task: dict[str, Any]) -> tuple[int, str]:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return (order.get(str(task.get("priority")), 9), str(task.get("task_id") or ""))


def source_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": item.get("evidence_id", ""),
        "source_family": item.get("source_family", ""),
        "source_rank": item.get("source_rank", ""),
        "source_title": item.get("source_title", ""),
        "source_url": item.get("source_url", ""),
    }


def sort_sources_for_task(task: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: (source_relevance(task, item), -RANK_VALUE.get(str(item.get("source_rank") or "D"), 0)))


def source_relevance(task: dict[str, Any], item: dict[str, Any]) -> int:
    trigger_type = str(task.get("trigger_type") or "")
    text = combined_text(item)
    if trigger_type == "cashflow_quality":
        if item.get("stance") == "contradict" and has_any(text, CASHFLOW_TERMS):
            return 0
        if has_any(text, RESOLUTION_TERMS):
            return 1
        if has_any(text, CASHFLOW_TERMS):
            return 2
    if trigger_type == "customer_order_capacity_validation":
        if has_any(text, CUSTOMER_ORDER_TERMS):
            return 0
    if trigger_type == "capacity_margin_stress":
        if has_any(text, EXPANSION_TERMS):
            return 0
        if has_any(text, ("价格周期", "毛利率", "产能利用率")):
            return 1
    return 5


def finding(
    task: dict[str, Any],
    finding_type: str,
    claim: str,
    source: dict[str, Any],
    score_impact: int,
    confidence: str,
) -> DeepDiveFinding:
    return DeepDiveFinding(
        finding_id=stable_id(task.get("task_id"), finding_type, source.get("evidence_id"), claim, prefix="ddf_"),
        task_id=str(task.get("task_id") or ""),
        finding_type=finding_type,
        claim=claim,
        evidence_ref_ids=[str(source.get("evidence_id") or "")],
        source_family=str(source.get("source_family") or "manual"),
        source_rank=str(source.get("source_rank") or "D"),
        raw_excerpt=str(source.get("raw_excerpt") or source.get("claim") or "")[:500],
        source_url=str(source.get("source_url") or ""),
        source_title=str(source.get("source_title") or ""),
        score_impact=score_impact,
        confidence=confidence,
    )


def unknown_finding(task: dict[str, Any], text: str) -> DeepDiveFinding:
    return DeepDiveFinding(
        finding_id=stable_id(task.get("task_id"), "unknown", text, prefix="ddf_"),
        task_id=str(task.get("task_id") or ""),
        finding_type="unknown",
        claim=text,
        evidence_ref_ids=[],
        source_family="manual",
        source_rank="D",
        raw_excerpt=text,
        score_impact=0,
        confidence="medium",
    )


def policy_allows_automation(item: dict[str, Any]) -> bool:
    family = str(item.get("source_family") or "manual")
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    license_status = str(metadata.get("license_status") or SOURCE_POLICY.get(family, {}).get("license_status") or "known")
    automation = str(SOURCE_POLICY.get(family, {}).get("automation") or "auto")
    if license_status in {"restricted", "unknown"} or automation == "manual_input_only":
        return bool(metadata.get("manual_supplied"))
    return True


def dedupe_sources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = "|".join(
            [
                str(item.get("independence_group") or ""),
                canonical_url(str(item.get("source_url") or "")),
                normalized_text(str(item.get("claim") or item.get("raw_excerpt") or ""))[:120],
            ]
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def canonical_url(value: str) -> str:
    return value.strip().lower().removesuffix("/")


def normalized_text(value: str) -> str:
    return "".join(str(value).lower().split())


def estimate_tokens(items: list[dict[str, Any]]) -> int:
    total_chars = sum(len(str(item.get("claim") or "")) + len(str(item.get("raw_excerpt") or "")) for item in items)
    return max(1, total_chars // 4) if items else 0


def trim_to_token_budget(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in items:
        output.append(item)
        if estimate_tokens(output) >= limit:
            return output[:-1] if len(output) > 1 else output
    return output


def non_soft_source(item: dict[str, Any]) -> bool:
    return non_soft_family(str(item.get("source_family") or ""))


def non_soft_family(value: str) -> bool:
    return value not in SOFT_SOURCE_FAMILIES


def first_high_counter_bear(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in items:
        if item.get("risk_type") == "counter_evidence" and item.get("severity") == "high":
            return item
    return None


def first_matching_bear(items: list[dict[str, Any]], terms: tuple[str, ...], require_high: bool) -> dict[str, Any] | None:
    for item in items:
        if require_high and item.get("severity") != "high":
            continue
        if has_any(combined_text(item), terms):
            return item
    return None


def first_validation_task(items: list[dict[str, Any]], task_types: tuple[str, ...]) -> dict[str, Any] | None:
    for item in items:
        if str(item.get("task_type") or "") in task_types:
            return item
    return items[0] if items else None


def first_matching_evidence(items: list[dict[str, Any]], terms: tuple[str, ...]) -> dict[str, Any] | None:
    for item in items:
        if has_any(combined_text(item), terms):
            return item
    return None


def unique_tasks(items: list[DeepDiveTask]) -> list[DeepDiveTask]:
    output: list[DeepDiveTask] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item.claim_id, item.trigger_type)
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    haystack = str(text).lower()
    return any(term.lower() in haystack for term in terms)


def combined_text(*items: Any) -> str:
    parts: list[str] = []
    for item in items:
        if isinstance(item, dict):
            for key in ("claim", "claim_text", "question", "risk_type", "success_criteria", "failure_criteria", "raw_excerpt", "source_title"):
                if item.get(key):
                    parts.append(str(item[key]))
        elif isinstance(item, (list, tuple)):
            parts.append(combined_text(*item))
        else:
            parts.append(str(item or ""))
    return " ".join(parts)

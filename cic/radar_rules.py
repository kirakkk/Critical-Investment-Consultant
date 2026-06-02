from __future__ import annotations

from collections import OrderedDict
from datetime import date, timedelta
from typing import Any

from .models import (
    BearCase,
    ClaimRevision,
    CrossValidationResult,
    RadarClaim,
    RadarEvidence,
    RadarValidationTask,
    SourceProfile,
    to_jsonable,
)
from .rules import clamp_score, stable_id


SOURCE_RANK_VALUE = {"A": 4, "B": 3, "C": 2, "D": 1}
DEFAULT_RANK_BY_FAMILY = {
    "official_disclosure": "A",
    "exchange_regulator": "A",
    "financial_data": "B",
    "market_data": "B",
    "industry_data": "B",
    "company_website": "C",
    "public_footprint": "C",
    "media_news": "C",
    "research_report": "C",
    "expert_kol": "C",
    "social_media": "D",
    "forum": "D",
    "rumor": "D",
    "manual": "D",
}
SOURCE_FAMILY_ALIASES = {
    "kol": "expert_kol",
    "x_kol": "expert_kol",
    "expert": "expert_kol",
    "twitter": "social_media",
    "x": "social_media",
    "news": "media_news",
    "announcement": "official_disclosure",
    "company_announcement": "official_disclosure",
    "cninfo": "official_disclosure",
    "szse": "exchange_regulator",
    "sse": "exchange_regulator",
    "official": "official_disclosure",
    "company_site": "company_website",
    "website": "company_website",
}
CONTRADICTION_STANCES = {"contradict", "negative", "bear", "against", "反证", "负面"}
HARD_RISK_TERMS = ("财务造假", "立案调查", "重大违法", "退市", "regulatory_investigation")
HIGH_RISK_TERMS = ("监管", "处罚", "问询", "诉讼", "质押", "减持", "现金流为负", "经营现金流")
INFLECTION_TERMS = (
    "订单",
    "客户",
    "供应链",
    "批量",
    "出货",
    "量产",
    "扩产",
    "募投",
    "收入",
    "利润",
    "毛利",
    "AI",
    "数据中心",
    "企业级",
    "国产化",
)


def normalize_source_family(value: Any) -> str:
    family = str(value or "manual").strip().lower().replace("-", "_").replace(" ", "_")
    return SOURCE_FAMILY_ALIASES.get(family, family or "manual")


def normalize_source_rank(value: Any, source_family: str) -> str:
    rank = str(value or "").strip().upper()
    if rank in SOURCE_RANK_VALUE:
        return rank
    return DEFAULT_RANK_BY_FAMILY.get(source_family, "D")


def normalize_stance(value: Any) -> str:
    stance = str(value or "support").strip().lower()
    return "contradict" if stance in CONTRADICTION_STANCES else "support"


def normalize_radar_input(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("radar") if isinstance(payload.get("radar"), dict) else payload
    stock_code = str(raw.get("stock_code") or raw.get("code") or "").upper().strip()
    if not stock_code:
        raise ValueError("radar payload missing stock_code")
    stock_name = str(raw.get("stock_name") or raw.get("name") or stock_code).strip()
    weak_signals = raw.get("weak_signals") or []
    evidence = raw.get("evidence") or []
    prior_claims = raw.get("prior_claims") or []
    risks = raw.get("risks") or []
    if isinstance(risks, str):
        risks = [risks]
    return {
        **raw,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "theme": str(raw.get("theme") or "未分类").strip(),
        "weak_signals": weak_signals if isinstance(weak_signals, list) else [],
        "evidence": evidence if isinstance(evidence, list) else [],
        "prior_claims": prior_claims if isinstance(prior_claims, list) else [],
        "risks": [str(item) for item in risks],
    }


def evidence_from_payload(radar: dict[str, Any]) -> list[RadarEvidence]:
    items: list[RadarEvidence] = []
    for index, raw in enumerate(radar["weak_signals"], start=1):
        if isinstance(raw, dict):
            claim = str(raw.get("signal_text") or raw.get("claim") or "").strip()
            items.append(_evidence_from_item(radar, raw, claim, index, is_weak_signal=True))
    offset = len(items)
    for index, raw in enumerate(radar["evidence"], start=1):
        if isinstance(raw, dict):
            claim = str(raw.get("claim") or raw.get("signal_text") or "").strip()
            items.append(_evidence_from_item(radar, raw, claim, offset + index, is_weak_signal=False))
    return [item for item in items if item.claim]


def _evidence_from_item(
    radar: dict[str, Any],
    raw: dict[str, Any],
    claim: str,
    index: int,
    is_weak_signal: bool,
) -> RadarEvidence:
    family = normalize_source_family(raw.get("source_family") or raw.get("source_type"))
    rank = normalize_source_rank(raw.get("source_rank"), family)
    source_name = _source_name(raw, family)
    independence_group = str(raw.get("independence_group") or "").strip()
    if not independence_group:
        independence_group = stable_id(family, raw.get("source_url") or source_name or claim[:48], prefix="grp_")
    metadata = dict(raw.get("metadata") or {})
    if raw.get("kol_profile"):
        metadata["kol_profile"] = raw["kol_profile"]
    metadata["is_weak_signal"] = is_weak_signal
    return RadarEvidence(
        evidence_id=stable_id(radar["stock_code"], index, claim, family, prefix="rev_"),
        stock_code=radar["stock_code"],
        stock_name=radar["stock_name"],
        claim=claim,
        source_family=family,
        source_rank=rank,
        source_url=str(raw.get("source_url") or ""),
        raw_excerpt=str(raw.get("raw_excerpt") or claim)[:500],
        stance=normalize_stance(raw.get("stance") or raw.get("impact_direction")),
        source_title=str(raw.get("title") or source_name or family),
        independence_group=independence_group,
        evidence_date=str(raw.get("date") or raw.get("evidence_date") or date.today().isoformat()),
        metadata=metadata,
    )


def _source_name(raw: dict[str, Any], family: str) -> str:
    if family == "expert_kol":
        profile = raw.get("kol_profile") if isinstance(raw.get("kol_profile"), dict) else {}
        return str(profile.get("handle") or raw.get("source_name") or "未命名KOL")
    return str(raw.get("source_name") or raw.get("publisher") or raw.get("source_url") or family)


def source_profiles_for(evidence: list[RadarEvidence]) -> list[SourceProfile]:
    profiles: OrderedDict[str, SourceProfile] = OrderedDict()
    for item in evidence:
        source_name = item.source_title or item.source_family
        source_id = stable_id(item.source_family, item.independence_group, source_name, prefix="src_")
        if source_id in profiles:
            continue
        profile = item.metadata.get("kol_profile") if isinstance(item.metadata.get("kol_profile"), dict) else {}
        quality = int(profile.get("kol_quality_score") or 0)
        base = {"A": 88, "B": 72, "C": 52, "D": 24}.get(item.source_rank, 24)
        credibility = clamp_score((base * 0.45 + quality * 0.55) if quality else base)
        profiles[source_id] = SourceProfile(
            source_id=source_id,
            source_family=item.source_family,
            source_rank=item.source_rank,
            source_name=source_name,
            independence_group=item.independence_group,
            credibility_score=credibility,
            cost_class=str(profile.get("cost_class") or item.metadata.get("cost_class") or "free"),
            known_biases=[str(v) for v in profile.get("known_biases", [])],
            conflict_flags=[str(v) for v in profile.get("conflict_flags", [])],
            notes=str(profile.get("notes") or ""),
        )
    return list(profiles.values())


def build_radar_claims(radar: dict[str, Any], evidence: list[RadarEvidence], profiles: list[SourceProfile]) -> list[RadarClaim]:
    weak_signals = [item for item in evidence if item.metadata.get("is_weak_signal")]
    claim_seeds = weak_signals or evidence[:1]
    claims: list[RadarClaim] = []
    for seed in claim_seeds:
        related = related_evidence(seed, evidence)
        cross = cross_validate_claim(seed, related, prior_x_score=prior_x_score_for(radar, seed.claim))
        scores = score_claim(radar, seed, related, cross)
        status = state_from_scores(scores, cross)
        blockers = unique_items([*cross.upgrade_blockers, *risk_blockers(radar["risks"])])
        profile_ids = profile_ids_for_evidence(related, profiles)
        claims.append(
            RadarClaim(
                claim_id=stable_id(radar["stock_code"], seed.claim, prefix="rcl_"),
                stock_code=radar["stock_code"],
                stock_name=radar["stock_name"],
                claim_text=seed.claim,
                theme=radar["theme"],
                thesis_stage=stage_from_status(status),
                status=status,
                scores=scores,
                evidence_ids=[item.evidence_id for item in related],
                source_profile_ids=profile_ids,
                upgrade_blockers=blockers,
                suggested_action=suggested_action_for_status(status, blockers),
                review_required=True,
            )
        )
    return claims


def related_evidence(seed: RadarEvidence, evidence: list[RadarEvidence]) -> list[RadarEvidence]:
    return [item for item in evidence if item.stock_code == seed.stock_code]


def prior_x_score_for(radar: dict[str, Any], claim_text: str) -> int:
    prior_claims = radar.get("prior_claims", [])
    if prior_claims and isinstance(prior_claims[0], dict):
        scores = prior_claims[0].get("scores") if isinstance(prior_claims[0].get("scores"), dict) else {}
        if isinstance(scores.get("X"), (int, float)):
            return clamp_score(float(scores["X"]))
    return 20 if claim_text else 0


def profile_ids_for_evidence(evidence: list[RadarEvidence], profiles: list[SourceProfile]) -> list[str]:
    profile_by_group = {(item.source_family, item.independence_group): item.source_id for item in profiles}
    return unique_items(profile_by_group.get((item.source_family, item.independence_group), "") for item in evidence)


def cross_validate_claim(seed: RadarEvidence, evidence: list[RadarEvidence], prior_x_score: int = 0) -> CrossValidationResult:
    support = [item for item in evidence if item.stance == "support"]
    contradiction = [item for item in evidence if item.stance == "contradict"]
    grouped_support = best_evidence_by_group(support)
    source_families = unique_items(item.source_family for item in grouped_support)
    independent_groups = unique_items(item.independence_group for item in grouped_support)
    ranks = [item.source_rank for item in grouped_support]
    high_rank_contra = [item for item in contradiction if SOURCE_RANK_VALUE.get(item.source_rank, 0) >= 3]
    blockers: list[str] = []

    if grouped_support and all(rank == "D" for rank in ranks):
        x_after = min(30, 18 + len(grouped_support) * 4)
        blockers.append("D 级来源只能进入弱信号，不允许升级。")
        gate_status = "blocked_d_rank_only"
        result_state = "raw_weak_signal"
    else:
        x_after = 28
        if grouped_support:
            x_after += min(18, len(grouped_support) * 6)
        if len(source_families) >= 2:
            x_after += 14
        if len(source_families) >= 3:
            x_after += 8
        if any(item.source_rank == "A" for item in grouped_support):
            x_after += 18
        elif any(item.source_rank == "B" for item in grouped_support):
            x_after += 10
        if "public_footprint" in source_families or "company_website" in source_families:
            x_after += 8
        if "financial_data" in source_families or "market_data" in source_families:
            x_after += 8

        if source_families == ["expert_kol"] or (source_families and set(source_families) == {"expert_kol"}):
            x_after = min(x_after, 55)
            blockers.append("KOL-only：缺少非 KOL 独立来源，不能进入候选。")
            gate_status = "blocked_kol_only"
            result_state = "validation_queue"
        else:
            gate_status = "passed_with_review"
            result_state = "evidence_convergence" if x_after >= 60 else "validation_queue"

    if high_rank_contra:
        x_after -= 18
        blockers.insert(0, "存在 A/B 级反证，先做人工复核。")
        gate_status = "blocked_by_high_rank_contradiction"
        result_state = "contradicted_review"

    x_after = clamp_score(x_after)
    return CrossValidationResult(
        claim_id=stable_id(seed.stock_code, seed.claim, prefix="rcl_"),
        gate_status=gate_status,
        result_state=result_state,
        source_families=source_families,
        independent_groups=independent_groups,
        support_count=len(grouped_support),
        contradiction_count=len(contradiction),
        x_score_before=prior_x_score,
        x_score_after=x_after,
        upgrade_blockers=unique_items(blockers),
        strongest_support=[to_jsonable(item) for item in grouped_support[:4]],
        strongest_contradictions=[to_jsonable(item) for item in high_rank_contra[:3] or contradiction[:3]],
    )


def best_evidence_by_group(evidence: list[RadarEvidence]) -> list[RadarEvidence]:
    groups: OrderedDict[str, RadarEvidence] = OrderedDict()
    for item in evidence:
        current = groups.get(item.independence_group)
        if not current or SOURCE_RANK_VALUE.get(item.source_rank, 0) > SOURCE_RANK_VALUE.get(current.source_rank, 0):
            groups[item.independence_group] = item
    return list(groups.values())


def score_claim(
    radar: dict[str, Any],
    seed: RadarEvidence,
    evidence: list[RadarEvidence],
    cross: CrossValidationResult,
) -> dict[str, Any]:
    text = " ".join([seed.claim, *(item.claim for item in evidence), *radar.get("risks", [])])
    e_score = 30 + min(30, sum(1 for term in INFLECTION_TERMS if term in text) * 4)
    if any(item.source_family == "expert_kol" for item in evidence):
        e_score += 5
    if any(item.source_rank in {"A", "B"} for item in evidence):
        e_score += 8

    i_score = 25
    if any(term in text for term in ("订单", "客户", "批量", "出货", "量产")):
        i_score += 18
    if any(term in text for term in ("收入", "利润", "毛利", "现金流")):
        i_score += 14
    if any(term in text for term in ("数据中心", "AI", "企业级", "国产化", "扩产", "募投")):
        i_score += 12

    u_score = 35 + max(0, 70 - cross.x_score_after) // 2
    if cross.result_state in {"raw_weak_signal", "validation_queue"}:
        u_score += 8
    if cross.contradiction_count:
        u_score += 6

    return {
        "E": clamp_score(e_score),
        "X": cross.x_score_after,
        "I": clamp_score(i_score),
        "U": clamp_score(u_score),
        "D": risk_grade_for(radar.get("risks", [])),
        "triggered_rule_ids": triggered_rules_for(cross),
    }


def triggered_rules_for(cross: CrossValidationResult) -> list[str]:
    rules = ["manual_weak_signal_intake", "dedupe_independence_group"]
    if cross.gate_status == "blocked_kol_only":
        rules.append("kol_only_gate")
    if cross.gate_status == "blocked_d_rank_only":
        rules.append("d_rank_source_gate")
    if len(cross.source_families) >= 2:
        rules.append("independent_source_family_boost")
    if cross.gate_status == "blocked_by_high_rank_contradiction":
        rules.append("high_rank_counter_evidence_first")
    return rules


def risk_grade_for(risks: list[str]) -> str:
    risk_text = " ".join(risks)
    if any(term in risk_text for term in HARD_RISK_TERMS):
        return "D"
    if any(term in risk_text for term in HIGH_RISK_TERMS):
        return "C"
    if risks:
        return "B"
    return "A"


def risk_blockers(risks: list[str]) -> list[str]:
    grade = risk_grade_for(risks)
    if grade == "D":
        return ["风险等级 D：阻断候选升级。"]
    if grade == "C":
        return ["存在需要优先复核的风险。"]
    return []


def state_from_scores(scores: dict[str, Any], cross: CrossValidationResult) -> str:
    if scores["D"] == "D":
        return "blocked_risk"
    if cross.result_state in {"raw_weak_signal", "contradicted_review"}:
        return cross.result_state
    if cross.gate_status == "blocked_kol_only":
        return "validation_queue"
    if scores["X"] >= 70 and scores["I"] >= 60 and scores["D"] in {"A", "B"}:
        return "inflection_watch"
    if scores["X"] >= 60:
        return "evidence_convergence"
    return "validation_queue"


def stage_from_status(status: str) -> str:
    stages = {
        "raw_weak_signal": "raw_weak_signal",
        "validation_queue": "validation_queue",
        "evidence_convergence": "evidence_convergence",
        "inflection_watch": "inflection_watch",
        "contradicted_review": "risk_review",
        "blocked_risk": "blocked",
    }
    return stages.get(status, "validation_queue")


def suggested_action_for_status(status: str, blockers: list[str]) -> str:
    if status == "inflection_watch":
        return "进入强验证观察；只允许人工复核，不自动交易。"
    if status == "evidence_convergence":
        return "证据开始收敛；补足财务或公告验证后再考虑升级。"
    if status == "contradicted_review":
        return "先处理反证；反证未解除前不得升级。"
    if status == "blocked_risk":
        return "风险阻断；先做风险审计。"
    if blockers:
        return "继续验证阻断项；不能作为候选或交易依据。"
    return "保留为早期弱信号，等待独立来源验证。"


def claim_revisions_for(radar: dict[str, Any], claims: list[RadarClaim]) -> list[ClaimRevision]:
    prior = radar.get("prior_claims", [])
    prior_item = prior[0] if prior and isinstance(prior[0], dict) else {}
    previous_status = str(prior_item.get("status") or "none")
    previous_scores = prior_item.get("scores") if isinstance(prior_item.get("scores"), dict) else {}
    revisions: list[ClaimRevision] = []
    for claim in claims:
        before = {
            "E": int(previous_scores.get("E", 30)),
            "X": int(previous_scores.get("X", 20)),
            "I": int(previous_scores.get("I", 20)),
            "U": int(previous_scores.get("U", 45)),
            "D": str(previous_scores.get("D", "B")),
        }
        changes = score_changes(before, claim.scores)
        revisions.append(
            ClaimRevision(
                claim_id=claim.claim_id,
                previous_status=previous_status,
                new_status=claim.status,
                score_before=before,
                score_after=claim.scores,
                changes=changes,
                reason=revision_reason(changes, claim.upgrade_blockers),
            )
        )
    return revisions


def score_changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    for key in ("E", "X", "I", "U"):
        delta = int(after.get(key, 0)) - int(before.get(key, 0))
        if abs(delta) >= 5:
            direction = "上升" if delta > 0 else "下降"
            changes.append(f"{key} {direction} {abs(delta)} 分")
    if str(before.get("D")) != str(after.get("D")):
        changes.append(f"D 从 {before.get('D')} 变为 {after.get('D')}")
    return changes or ["核心分数变化不足 5 分"]


def revision_reason(changes: list[str], blockers: list[str]) -> str:
    if blockers:
        return f"出现阻断项：{'；'.join(blockers[:2])}"
    return "；".join(changes[:2])


def validation_tasks_for(radar: dict[str, Any], claims: list[RadarClaim], cross_results: list[CrossValidationResult]) -> list[RadarValidationTask]:
    cross_by_claim = {item.claim_id: item for item in cross_results}
    tasks: list[RadarValidationTask] = []
    for claim in claims:
        cross = cross_by_claim.get(claim.claim_id)
        if cross and cross.gate_status == "blocked_kol_only":
            tasks.append(_task(radar, claim, "source_validation", "寻找非 KOL 独立来源验证该线索", "public_footprint", 14))
        tasks.append(_task(radar, claim, "official_check", "检查公告、年报、互动问答或监管披露是否出现同方向事实", "official_disclosure", 30))
        tasks.append(_task(radar, claim, "financial_check", "下一期财报验证收入、毛利率、经营现金流是否支持该逻辑", "financial_data", 90, priority="P2"))
    return tasks


def _task(
    radar: dict[str, Any],
    claim: RadarClaim,
    task_type: str,
    question: str,
    target_source_family: str,
    days: int,
    priority: str = "P1",
) -> RadarValidationTask:
    return RadarValidationTask(
        task_id=stable_id(claim.claim_id, task_type, target_source_family, prefix="rvt_"),
        claim_id=claim.claim_id,
        stock_code=radar["stock_code"],
        stock_name=radar["stock_name"],
        task_type=task_type,
        question=f"{radar['stock_name']}：{question}",
        target_source_family=target_source_family,
        success_criteria="出现 A/B/C 级独立来源，且能落到客户、订单、产能、收入、利润或产品进展之一。",
        failure_criteria="30-90 天内仍只有 KOL/社媒讨论，或高等级来源出现反证。",
        due_date=(date.today() + timedelta(days=days)).isoformat(),
        priority=priority,
    )


def bear_cases_for(radar: dict[str, Any], claims: list[RadarClaim], evidence: list[RadarEvidence]) -> list[BearCase]:
    bears: list[BearCase] = []
    contradictions = [item for item in evidence if item.stance == "contradict"]
    for claim in claims:
        for item in contradictions:
            bears.append(
                BearCase(
                    bear_case_id=stable_id(claim.claim_id, item.evidence_id, prefix="bear_"),
                    claim_id=claim.claim_id,
                    stock_code=radar["stock_code"],
                    stock_name=radar["stock_name"],
                    risk_type="counter_evidence",
                    claim=item.claim,
                    evidence_ids=[item.evidence_id],
                    severity="high" if item.source_rank in {"A", "B"} else "medium",
                    what_would_reduce_this_risk="用更高等级公告、财务或客户侧证据解释该反证。",
                )
            )
        for risk in radar.get("risks", []) or ["缺少公告或财务验证，早期线索可能只是主题情绪。"]:
            bears.append(
                BearCase(
                    bear_case_id=stable_id(claim.claim_id, risk, prefix="bear_"),
                    claim_id=claim.claim_id,
                    stock_code=radar["stock_code"],
                    stock_name=radar["stock_name"],
                    risk_type="risk_item",
                    claim=str(risk),
                    evidence_ids=[],
                    severity="high" if any(term in str(risk) for term in HIGH_RISK_TERMS + HARD_RISK_TERMS) else "medium",
                    what_would_reduce_this_risk="用 A/B 级来源证明该风险被消化、改善或与核心假设无关。",
                )
            )
    return unique_bear_cases(bears)


def unique_bear_cases(items: list[BearCase]) -> list[BearCase]:
    seen: set[str] = set()
    output: list[BearCase] = []
    for item in items:
        if item.bear_case_id in seen:
            continue
        seen.add(item.bear_case_id)
        output.append(item)
    return output


def unique_items(items: Any) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output

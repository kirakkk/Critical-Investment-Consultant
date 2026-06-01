from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from .models import (
    Evidence,
    PeerComparison,
    RiskRadar,
    Score,
    Signal,
    ThesisCheck,
    ValidationPoint,
    to_jsonable,
)


SOURCE_RANK_VALUE = {"A": 4, "B": 3, "C": 2, "D": 1}
HIGH_RISK_TERMS = ("监管", "处罚", "造假", "问询", "诉讼", "质押", "减持", "negative_cashflow")
HARD_RISK_TERMS = ("财务造假", "立案调查", "重大违法", "退市", "regulatory_investigation")


def clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def stable_id(*parts: Any, prefix: str = "") -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}{digest}" if prefix else digest


def normalize_holding(raw: dict[str, Any]) -> dict[str, Any]:
    stock_code = str(raw.get("stock_code") or raw.get("code") or "").upper().strip()
    if not stock_code:
        raise ValueError("holding missing stock_code")
    stock_name = str(raw.get("stock_name") or raw.get("name") or stock_code).strip()
    theme = str(raw.get("theme") or raw.get("industry") or "未分类").strip()
    state = str(raw.get("state") or "theme_watch").strip()
    events = raw.get("events") or []
    risks = raw.get("risks") or []
    if isinstance(risks, str):
        risks = [risks]
    return {
        **raw,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "theme": theme,
        "state": state,
        "thesis": str(raw.get("thesis") or raw.get("main_logic") or "尚未填写核心投资假设").strip(),
        "events": events if isinstance(events, list) else [],
        "risks": [str(risk) for risk in risks],
        "source_rank": str(raw.get("source_rank") or "C").upper(),
        "stock_20d_return": float(raw.get("stock_20d_return") or 0),
        "sector_20d_return": float(raw.get("sector_20d_return") or 0),
        "index_20d_return": float(raw.get("index_20d_return") or 0),
        "pe_percentile_5y": float(raw.get("pe_percentile_5y") if raw.get("pe_percentile_5y") is not None else 0.5),
        "current_price": float(raw.get("current_price") or 0),
        "cost_price": float(raw.get("cost_price") or 0),
    }


def risk_grade_for(holding: dict[str, Any]) -> tuple[str, list[str]]:
    risks = [str(risk) for risk in holding.get("risks", [])]
    risk_text = " ".join(risks)
    triggered: list[str] = []
    if any(term in risk_text for term in HARD_RISK_TERMS):
        triggered.append("hard_exclude_risk")
        return "D", triggered
    if any(term in risk_text for term in HIGH_RISK_TERMS):
        triggered.append("force_risk_review")
        return "C", triggered
    if holding.get("pe_percentile_5y", 0.5) > 0.9:
        triggered.append("valuation_overheated_risk")
        return "C", triggered
    if risks:
        triggered.append("ordinary_monitorable_risk")
        return "B", triggered
    return "A", triggered


def score_holding(holding: dict[str, Any]) -> Score:
    triggered: list[str] = []
    events = holding.get("events", [])
    source_rank = holding.get("source_rank", "C")
    source_value = SOURCE_RANK_VALUE.get(source_rank, 2)

    research = 48
    odds = 50
    timing = 50

    if holding.get("thesis") and holding["thesis"] != "尚未填写核心投资假设":
        research += 8
        triggered.append("thesis_exists")
    if holding.get("theme") and holding["theme"] != "未分类":
        research += 5
        triggered.append("theme_tag_exists")
    if source_value >= 3:
        research += 7
        triggered.append("evidence_rank_b_or_above")
    elif source_rank == "D":
        research -= 12
        triggered.append("low_rank_source_penalty")

    for event in events:
        direction = event.get("impact_direction", "neutral")
        event_type = str(event.get("event_type", ""))
        if direction == "positive":
            research += 5
            triggered.append(f"positive_event:{event_type or 'unknown'}")
        elif direction == "negative":
            research -= 8
            triggered.append(f"negative_event:{event_type or 'unknown'}")

    pe_percentile = holding.get("pe_percentile_5y", 0.5)
    if pe_percentile < 0.35:
        odds += 14
        triggered.append("valuation_percentile_low")
    elif pe_percentile > 0.85:
        odds -= 16
        triggered.append("valuation_overheated")

    cost = holding.get("cost_price", 0)
    current = holding.get("current_price", 0)
    if cost > 0 and current > 0:
        gain = (current - cost) / cost
        if gain > 0.25:
            odds -= 8
            triggered.append("position_gain_may_reduce_odds")
        elif gain < -0.12:
            odds += 5
            triggered.append("price_drawdown_may_improve_odds")

    stock_ret = holding.get("stock_20d_return", 0)
    sector_ret = holding.get("sector_20d_return", 0)
    index_ret = holding.get("index_20d_return", 0)
    if stock_ret > sector_ret and stock_ret > index_ret:
        timing += 12
        triggered.append("relative_strength_confirmed")
    elif stock_ret < index_ret:
        timing -= 8
        triggered.append("weak_vs_index")
    if stock_ret > 0.22 and pe_percentile > 0.8:
        timing -= 8
        triggered.append("high_position_crowding")

    q, risk_rules = risk_grade_for(holding)
    triggered.extend(risk_rules)
    if q == "C":
        research -= 8
        odds -= 6
    elif q == "D":
        research -= 25
        odds -= 20
        timing -= 10

    return Score(
        R=clamp_score(research),
        O=clamp_score(odds),
        T=clamp_score(timing),
        Q=q,
        triggered_rule_ids=triggered,
        change_reason="; ".join(triggered[:6]),
    )


def action_from_score(score: Score, source_rank: str) -> tuple[str, str, str, str, bool]:
    if score.Q == "D":
        return "排除/退出复核", "S5", "negative", "excluded", True
    if score.Q == "C":
        return "风险复核", "S4", "negative", "stock_tracking", True
    if SOURCE_RANK_VALUE.get(source_rank, 1) < 3 and score.R >= 75:
        return "待复核线索", "S2", "neutral", "stock_tracking", True
    if score.R >= 75 and score.O >= 65 and score.T >= 60 and score.Q in {"A", "B"}:
        return "候选信号", "S3", "positive", "candidate", True
    if score.R >= 75 and score.O >= 65 and score.T < 60:
        return "等待信号", "S2", "neutral", "stock_tracking", True
    if score.R >= 75 and score.O < 60:
        return "逻辑好但赔率差", "S2", "neutral", "stock_tracking", True
    if 60 <= score.R < 75 and score.T >= 60:
        return "交易性观察", "S1", "neutral", "stock_tracking", True
    return "只做观察", "S0", "neutral", "theme_watch", False


def evidence_for_holding(holding: dict[str, Any]) -> list[Evidence]:
    evidence: list[Evidence] = []
    for idx, event in enumerate(holding.get("events", []), start=1):
        evidence.append(
            Evidence(
                evidence_id=stable_id(holding["stock_code"], idx, event.get("claim", ""), prefix="ev_"),
                source_rank=str(event.get("source_rank") or holding.get("source_rank") or "C").upper(),
                title=str(event.get("event_type") or "持仓事件"),
                claim=str(event.get("claim") or "事件未提供摘要"),
                source_type=str(event.get("source_type") or "portfolio_input"),
                raw_excerpt=str(event.get("raw_excerpt") or event.get("claim") or ""),
                source_url=str(event.get("source_url") or ""),
            )
        )
    if not evidence:
        evidence.append(
            Evidence(
                evidence_id=stable_id(holding["stock_code"], holding.get("thesis", ""), prefix="ev_"),
                source_rank=holding.get("source_rank", "C"),
                title="用户持仓输入",
                claim=holding.get("thesis", "尚未填写核心投资假设"),
                source_type="portfolio_input",
                raw_excerpt=holding.get("thesis", ""),
            )
        )
    return evidence


def build_signal(holding: dict[str, Any], score: Score, evidence: list[Evidence]) -> Signal:
    signal_type, _level, direction, new_state, review_required = action_from_score(score, holding.get("source_rank", "C"))
    negative_reasons = list(holding.get("risks", [])) or ["仍需验证财务兑现、估值位置和资金持续性"]
    positive_reasons = []
    if score.R >= 70:
        positive_reasons.append("研究分接近或超过候选阈值")
    if score.T >= 60:
        positive_reasons.append("时点分显示相对强度较好")
    if score.O >= 60:
        positive_reasons.append("赔率分未显示明显透支")
    if not positive_reasons:
        positive_reasons.append("当前更适合观察，等待更高等级证据")

    invalidating = holding.get("invalidating_conditions") or [
        "核心事件后续未继续兑现",
        "经营现金流明显弱于利润",
        "同主题强度退潮或个股明显弱于指数",
    ]
    return Signal(
        signal_id=f"{date.today():%Y%m%d}-{holding['stock_code'].replace('.', '')}-{stable_id(score.triggered_rule_ids, prefix='')[:4]}",
        stock_code=holding["stock_code"],
        stock_name=holding["stock_name"],
        signal_type=signal_type,
        signal_direction=direction,
        previous_state=holding.get("state", "theme_watch"),
        new_state=new_state,
        score_before={"R": max(0, score.R - 5), "O": score.O, "T": max(0, score.T - 4), "Q": score.Q},
        score_after={"R": score.R, "O": score.O, "T": score.T, "Q": score.Q},
        key_evidence=[to_jsonable(item) for item in evidence[:3]],
        positive_reasons=positive_reasons,
        negative_reasons=negative_reasons,
        invalidating_conditions=[str(item) for item in invalidating],
        suggested_action=suggested_action_for(signal_type),
        review_required=review_required,
    )


def suggested_action_for(signal_type: str) -> str:
    actions = {
        "候选信号": "打开审计卡，人工复核后才允许进入候选池，不自动交易。",
        "等待信号": "逻辑较好但时点不足，写入下一验证点，等待资金或催化确认。",
        "逻辑好但赔率差": "不追高，等待回调、业绩上修或估值消化。",
        "交易性观察": "只作为交易性观察，不当作基本面核心票。",
        "风险复核": "优先打开风险雷达，风险下降前不得升级。",
        "排除/退出复核": "阻断候选升级，要求人工确认是否排除或退出。",
        "待复核线索": "低等级来源只能作为线索，等待公告、财报或行情数据二次确认。",
    }
    return actions.get(signal_type, "保持观察，等待更高质量证据。")


def thesis_check_for(holding: dict[str, Any], score: Score, evidence: list[Evidence], llm_item: dict[str, Any] | None) -> ThesisCheck:
    status_after = "unchanged"
    if score.Q == "D":
        status_after = "falsified"
    elif score.R >= 75:
        status_after = "strengthened"
    elif score.R < 55:
        status_after = "weakened"
    elif score.Q == "C":
        status_after = "review_required"

    missing = ["后续公告验证", "经营现金流验证"]
    if holding.get("pe_percentile_5y", 0.5) > 0.75:
        missing.append("估值消化或盈利上修")
    if llm_item and llm_item.get("evidence_missing"):
        missing = [str(item) for item in llm_item["evidence_missing"]][:5]

    counter = list(holding.get("risks", [])) or ["同主题比较和财务兑现仍需跟踪"]
    if llm_item and llm_item.get("counter_evidence"):
        counter = [str(item) for item in llm_item["counter_evidence"]][:5]

    research_question = (
        llm_item.get("research_question")
        if llm_item and llm_item.get("research_question")
        else f"{holding['stock_name']} 的核心假设能否在下一次公告、财报或行业数据中被验证？"
    )

    return ThesisCheck(
        thesis_id=stable_id(holding["stock_code"], holding["thesis"], prefix="th_"),
        stock_code=holding["stock_code"],
        stock_name=holding["stock_name"],
        thesis_text=holding["thesis"],
        status_before="unverified",
        status_after=status_after,
        confidence_before="medium",
        confidence_after="medium" if status_after not in {"falsified", "review_required"} else "low",
        evidence_added=[item.claim for item in evidence[:3]],
        evidence_missing=missing,
        counter_evidence=counter,
        next_validation_point=to_jsonable(validation_point_for(holding, score)),
        research_question=str(research_question),
    )


def risk_radar_for(holding: dict[str, Any], score: Score, evidence: list[Evidence], llm_item: dict[str, Any] | None) -> RiskRadar:
    bear_cases: list[dict[str, Any]] = []
    risks = list(holding.get("risks", [])) or ["尚未形成明确反方证据，需要补充同业、财务和公告验证"]
    if llm_item and llm_item.get("counter_evidence"):
        risks = [str(item) for item in llm_item["counter_evidence"]]

    for idx, risk in enumerate(risks[:5], start=1):
        category = "governance" if any(term in risk for term in ("监管", "问询", "诉讼", "质押", "减持")) else "thesis"
        if "估值" in risk or "贵" in risk or "透支" in risk:
            category = "valuation"
        if "现金流" in risk or "毛利" in risk or "应收" in risk:
            category = "financial"
        bear_cases.append(
            {
                "category": category,
                "claim": risk,
                "evidence_id": evidence[min(idx - 1, len(evidence) - 1)].evidence_id,
                "severity": "high" if score.Q in {"C", "D"} else "medium",
                "what_would_reduce_this_risk": reduction_condition_for(category),
            }
        )
    blocked_actions = []
    if score.Q in {"C", "D"}:
        blocked_actions.append("风险等级下降前不得升级为候选或持仓观察")
    if holding.get("source_rank") in {"C", "D"}:
        blocked_actions.append("低等级来源不得单独触发候选信号")
    return RiskRadar(
        stock_code=holding["stock_code"],
        stock_name=holding["stock_name"],
        risk_level=score.Q,
        risk_summary=risk_summary_for(score),
        bear_cases=bear_cases,
        blocked_actions=blocked_actions or ["不自动交易，所有动作需要人工确认"],
    )


def reduction_condition_for(category: str) -> str:
    return {
        "governance": "后续公告或监管文件显示风险解除或影响可控",
        "valuation": "估值分位下降，或盈利预测上修消化估值",
        "financial": "经营现金流、毛利率和应收账款变化出现改善",
        "thesis": "更高等级来源证明核心假设继续兑现",
    }.get(category, "出现 A/B 级证据消除该风险")


def risk_summary_for(score: Score) -> str:
    if score.Q == "D":
        return "存在重大风险或硬阻断，必须排除或退出复核。"
    if score.Q == "C":
        return "存在明显瑕疵，只能观察或风险复核。"
    if score.Q == "B":
        return "存在普通风险，可监控但不能忽略。"
    return "暂未识别硬风险，仍需跟踪证伪条件。"


def validation_point_for(holding: dict[str, Any], score: Score) -> ValidationPoint:
    days = 30 if score.T >= 60 else 60
    validation_date = (date.today() + timedelta(days=days)).isoformat()
    watch_fields = ["公告进展", "经营现金流", "毛利率"]
    if holding.get("theme"):
        watch_fields.append(f"{holding['theme']}板块强度")
    return ValidationPoint(
        validation_id=stable_id(holding["stock_code"], validation_date, prefix="vp_"),
        stock_code=holding["stock_code"],
        stock_name=holding["stock_name"],
        validation_date=validation_date,
        validation_type="thesis_check",
        description=f"验证 {holding['stock_name']} 的核心假设是否继续成立。",
        watch_fields=watch_fields,
        expected_direction="高等级证据增强，且 R/O/T 至少两项不恶化",
        invalidates_if="核心公告、财报或行情数据与投资假设相反，或 Q 降为 D",
    )


def peer_comparisons_for(holdings: list[dict[str, Any]], scores: dict[str, Score]) -> list[PeerComparison]:
    by_theme: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for holding in holdings:
        by_theme[holding["theme"]].append(holding)

    comparisons: list[PeerComparison] = []
    dimensions = ["真实受益程度", "业绩弹性", "估值分位", "资金确认", "风险瑕疵"]
    for theme, group in by_theme.items():
        if len(group) < 2:
            only = group[0]
            comparisons.append(
                PeerComparison(
                    theme=theme,
                    focus_stock=only["stock_code"],
                    focus_stock_name=only["stock_name"],
                    peer_set=[],
                    comparison_dimensions=dimensions,
                    winner=None,
                    winner_reason="同主题股票少于 2 只，需要补充 peer set 后才能比较。",
                    loser_or_wait=[],
                    missing_data=["peer_set"],
                )
            )
            continue
        ranked = sorted(group, key=lambda item: (scores[item["stock_code"]].R, scores[item["stock_code"]].O, scores[item["stock_code"]].T), reverse=True)
        winner = ranked[0]
        winner_score = scores[winner["stock_code"]]
        for focus in group:
            peer_set = [item["stock_code"] for item in group if item["stock_code"] != focus["stock_code"]]
            loser_or_wait = [
                {"stock_code": item["stock_code"], "reason": wait_reason_for(scores[item["stock_code"]])}
                for item in ranked[1:4]
            ]
            comparisons.append(
                PeerComparison(
                    theme=theme,
                    focus_stock=focus["stock_code"],
                    focus_stock_name=focus["stock_name"],
                    peer_set=peer_set,
                    comparison_dimensions=dimensions,
                    winner=winner["stock_code"],
                    winner_reason=f"{winner['stock_name']} 在 R/O/T 综合排序领先，当前 R={winner_score.R}, O={winner_score.O}, T={winner_score.T}, Q={winner_score.Q}。",
                    loser_or_wait=loser_or_wait,
                    missing_data=[],
                )
            )
    return comparisons


def wait_reason_for(score: Score) -> str:
    if score.Q in {"C", "D"}:
        return "风险等级限制升级。"
    if score.O < 60:
        return "赔率不足，等待估值消化。"
    if score.T < 60:
        return "时点未确认，等待资金或催化。"
    return "综合排序暂未领先。"


def top_changes_for(signals: list[Signal], thesis_checks: list[ThesisCheck], risk_radars: list[RiskRadar]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    risk_by_code = {risk.stock_code: risk for risk in risk_radars}
    for signal in signals:
        risk = risk_by_code.get(signal.stock_code)
        priority = 50
        if signal.signal_type in {"排除/退出复核", "风险复核"}:
            priority = 100
        elif signal.signal_type == "候选信号":
            priority = 85
        elif signal.signal_type in {"等待信号", "逻辑好但赔率差"}:
            priority = 70
        score_delta = {
            "R": signal.score_after["R"] - signal.score_before["R"],
            "O": signal.score_after["O"] - signal.score_before["O"],
            "T": signal.score_after["T"] - signal.score_before["T"],
            "Q": "unchanged" if signal.score_after["Q"] == signal.score_before["Q"] else signal.score_after["Q"],
        }
        candidates.append(
            {
                "priority": priority,
                "title": f"{signal.stock_name}: {signal.signal_type}",
                "stock_code": signal.stock_code,
                "stock_name": signal.stock_name,
                "why_it_matters": why_it_matters_for(signal, risk),
                "changed_object": "signal",
                "changed_field": "state_and_score",
                "score_delta": score_delta,
                "suggested_user_action": signal.suggested_action,
                "not_actionable_because": signal.negative_reasons[:3],
                "source_rank": signal.key_evidence[0].get("source_rank", "C") if signal.key_evidence else "C",
                "review_required": signal.review_required,
            }
        )
    for check in thesis_checks:
        if check.status_after in {"strengthened", "weakened", "falsified", "review_required"}:
            candidates.append(
                {
                    "priority": 78 if check.status_after == "strengthened" else 88,
                    "title": f"{check.stock_name}: 投资假设{status_label(check.status_after)}",
                    "stock_code": check.stock_code,
                    "stock_name": check.stock_name,
                    "why_it_matters": f"该变化直接影响核心假设：{check.thesis_text}",
                    "changed_object": "investment_thesis",
                    "changed_field": "status",
                    "score_delta": {},
                    "suggested_user_action": f"回答研究问题：{check.research_question}",
                    "not_actionable_because": check.evidence_missing,
                    "source_rank": "B",
                    "review_required": True,
                }
            )
    ranked = sorted(candidates, key=lambda item: item["priority"], reverse=True)
    deduped: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for item in ranked:
        if item["stock_code"] in seen_codes and item["priority"] < 100:
            continue
        clean = {k: v for k, v in item.items() if k != "priority"}
        clean["rank"] = len(deduped) + 1
        deduped.append(clean)
        seen_codes.add(item["stock_code"])
        if len(deduped) == 3:
            break
    return deduped


def why_it_matters_for(signal: Signal, risk: RiskRadar | None) -> str:
    if signal.signal_type in {"风险复核", "排除/退出复核"}:
        return "该变化可能影响是否继续跟踪或持有，风险处理优先于机会判断。"
    if signal.signal_type == "候选信号":
        return "该标的的研究分、赔率分、时点分出现共振，但仍需要人工确认反方证据。"
    if signal.signal_type == "待复核线索":
        return "低等级来源提供了线索，但还不能升级为正式候选。"
    if risk and risk.risk_level in {"C", "D"}:
        return "研究逻辑之外存在明显风险，需要先看风险雷达。"
    return "该变化会影响股票池状态、下一验证点或后续研究优先级。"


def status_label(status: str) -> str:
    return {
        "strengthened": "增强",
        "weakened": "减弱",
        "falsified": "证伪",
        "review_required": "待复核",
        "unchanged": "未变",
    }.get(status, status)

from __future__ import annotations

from typing import Any

from .llm import LLMClient, build_research_prompt, heuristic_insights
from .models import DailyBrief, to_jsonable, today_iso
from .rules import (
    build_signal,
    evidence_for_holding,
    normalize_holding,
    peer_comparisons_for,
    risk_radar_for,
    score_holding,
    thesis_check_for,
    top_changes_for,
    validation_point_for,
)


def analyze_holdings(holdings_input: list[dict[str, Any]], llm_client: LLMClient | None = None, use_llm: bool = True) -> dict[str, Any]:
    holdings = [normalize_holding(item) for item in holdings_input]
    fallback = heuristic_insights(holdings)
    llm_status = "disabled"
    llm_error = ""
    insights = fallback

    if use_llm:
        client = llm_client or LLMClient()
        system_prompt, user_prompt = build_research_prompt(holdings)
        result = client.chat_json(system_prompt, user_prompt, fallback)
        insights = result.data
        llm_status = result.status
        llm_error = result.error

    insight_by_code = {
        str(item.get("stock_code", "")).upper(): item
        for item in insights.get("items", [])
        if isinstance(item, dict)
    }

    scores = {}
    signals = []
    thesis_checks = []
    risk_radars = []
    validation_points = []
    evidence_package = []

    for holding in holdings:
        score = score_holding(holding)
        evidence = evidence_for_holding(holding)
        llm_item = insight_by_code.get(holding["stock_code"])
        signal = build_signal(holding, score, evidence)
        thesis_check = thesis_check_for(holding, score, evidence, llm_item)
        risk_radar = risk_radar_for(holding, score, evidence, llm_item)
        validation = validation_point_for(holding, score)

        scores[holding["stock_code"]] = score
        signals.append(signal)
        thesis_checks.append(thesis_check)
        risk_radars.append(risk_radar)
        validation_points.append(validation)
        evidence_package.extend(evidence)

    peer_comparisons = peer_comparisons_for(holdings, scores)
    top_changes = top_changes_for(signals, thesis_checks, risk_radars)
    risk_alerts = sorted(
        [to_jsonable(item) for item in risk_radars],
        key=lambda item: {"D": 4, "C": 3, "B": 2, "A": 1}.get(item["risk_level"], 0),
        reverse=True,
    )

    brief = DailyBrief(
        brief_date=today_iso(),
        top_changes=top_changes,
        risk_alerts=risk_alerts,
        thesis_checks=[to_jsonable(item) for item in thesis_checks],
        peer_comparisons=[to_jsonable(item) for item in peer_comparisons],
        validation_points=[to_jsonable(item) for item in validation_points],
        signals=[to_jsonable(item) for item in signals],
        generated_by="cic-rule-engine+llm-adapter",
        llm_status=llm_status,
    )

    output = {
        "brief": to_jsonable(brief),
        "holdings": holdings,
        "scores": {code: to_jsonable(score) for code, score in scores.items()},
        "evidence": [to_jsonable(item) for item in evidence_package],
        "llm": {
            "status": llm_status,
            "error": llm_error,
            "provider": "zhipu-openai-compatible",
        },
    }
    return output


def latest_report_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {
            "brief": {
                "brief_date": today_iso(),
                "top_changes": [],
                "risk_alerts": [],
                "thesis_checks": [],
                "peer_comparisons": [],
                "validation_points": [],
                "signals": [],
                "generated_by": "empty",
                "llm_status": "not_run",
            }
        }
    return report

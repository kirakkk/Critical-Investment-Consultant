from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timezone
from typing import Any


SOURCE_RANKS = {"A", "B", "C", "D"}
STOCK_STATES = {
    "excluded",
    "theme_watch",
    "stock_tracking",
    "candidate",
    "holding_watch",
    "downgraded",
    "exited",
}
RISK_GRADES = {"A", "B", "C", "D"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_iso() -> str:
    return date.today().isoformat()


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


@dataclass(slots=True)
class Evidence:
    evidence_id: str
    source_rank: str
    title: str
    claim: str
    source_type: str = "manual"
    raw_excerpt: str = ""
    source_url: str = ""
    evidence_date: str = field(default_factory=today_iso)


@dataclass(slots=True)
class Score:
    R: int
    O: int
    T: int
    Q: str
    triggered_rule_ids: list[str] = field(default_factory=list)
    change_reason: str = ""


@dataclass(slots=True)
class Signal:
    signal_id: str
    stock_code: str
    stock_name: str
    signal_type: str
    signal_direction: str
    previous_state: str
    new_state: str
    score_before: dict[str, Any]
    score_after: dict[str, Any]
    key_evidence: list[dict[str, Any]]
    positive_reasons: list[str]
    negative_reasons: list[str]
    invalidating_conditions: list[str]
    suggested_action: str
    review_required: bool = True
    generated_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class ThesisCheck:
    thesis_id: str
    stock_code: str
    stock_name: str
    thesis_text: str
    status_before: str
    status_after: str
    confidence_before: str
    confidence_after: str
    evidence_added: list[str]
    evidence_missing: list[str]
    counter_evidence: list[str]
    next_validation_point: dict[str, Any]
    research_question: str


@dataclass(slots=True)
class RiskRadar:
    stock_code: str
    stock_name: str
    risk_level: str
    risk_summary: str
    bear_cases: list[dict[str, Any]]
    blocked_actions: list[str]


@dataclass(slots=True)
class PeerComparison:
    theme: str
    focus_stock: str
    focus_stock_name: str
    peer_set: list[str]
    comparison_dimensions: list[str]
    winner: str | None
    winner_reason: str
    loser_or_wait: list[dict[str, str]]
    missing_data: list[str]


@dataclass(slots=True)
class ValidationPoint:
    validation_id: str
    stock_code: str
    stock_name: str
    validation_date: str
    validation_type: str
    description: str
    watch_fields: list[str]
    expected_direction: str
    invalidates_if: str
    status: str = "pending"


@dataclass(slots=True)
class DailyBrief:
    brief_date: str
    top_changes: list[dict[str, Any]]
    risk_alerts: list[dict[str, Any]]
    thesis_checks: list[dict[str, Any]]
    peer_comparisons: list[dict[str, Any]]
    validation_points: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    generated_by: str
    llm_status: str
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class Decision:
    signal_id: str
    decision: str
    reason: str
    next_action: str = ""
    stop_condition: str = ""
    decided_at: str = field(default_factory=utc_now_iso)

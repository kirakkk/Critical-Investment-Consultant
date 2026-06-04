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


@dataclass(slots=True)
class RadarDecision:
    claim_id: str
    decision: str
    reason: str
    report_id: str = ""
    stock_code: str = ""
    stock_name: str = ""
    next_action: str = ""
    decided_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class DeepDiveTask:
    task_id: str
    report_id: str
    claim_id: str
    stock_code: str
    stock_name: str
    question: str
    trigger_type: str
    trigger_ref_id: str
    trigger_reason: str
    priority: str
    allowed_source_families: list[str]
    budget: dict[str, Any]
    status: str = "pending"
    auto_run_eligible: bool = True
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class DeepDiveRun:
    run_id: str
    task_id: str
    status: str
    model: str
    sources_checked: list[dict[str, Any]]
    llm_calls_used: int
    elapsed_ms: int
    token_estimate: int
    stop_reason: str = ""
    error: str = ""
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class DeepDiveFinding:
    finding_id: str
    task_id: str
    finding_type: str
    claim: str
    evidence_ref_ids: list[str]
    source_family: str
    source_rank: str
    raw_excerpt: str
    source_url: str = ""
    source_title: str = ""
    score_impact: int = 0
    confidence: str = "medium"


@dataclass(slots=True)
class DeepDiveVerdict:
    task_id: str
    verdict: str
    summary: str
    blocker_effect: str
    score_impact: dict[str, Any]
    review_required: bool = True
    decided_by: str = "rule-engine"
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class DeepDiveDecision:
    task_id: str
    decision: str
    reason: str
    next_action: str = ""
    decided_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class SourceCandidate:
    source_id: str
    run_id: str
    source_name: str
    source_family: str
    source_rank: str
    theme: str
    sensor_type: str
    source_url: str = ""
    cost_class: str = "free"
    access_mode: str = "public_web"
    license_status: str = "clear"
    automation_allowed: bool = False
    collection_status: str = "manual_import_required"
    reason: str = ""
    independence_group: str = ""
    raw_excerpt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class SensorObservation:
    observation_id: str
    run_id: str
    source_id: str
    stock_code: str
    stock_name: str
    theme: str
    sensor_type: str
    metric: str
    value: str
    unit: str
    direction: str
    signal_strength: int
    source_family: str
    source_rank: str
    independence_group: str
    source_url: str = ""
    raw_excerpt: str = ""
    observation_date: str = field(default_factory=today_iso)


@dataclass(slots=True)
class SensorComparison:
    comparison_id: str
    run_id: str
    theme: str
    sensor_type: str
    metric: str
    result_state: str
    source_ids: list[str]
    independent_groups: list[str]
    support_count: int
    contradiction_count: int
    forward_score_delta: int
    summary: str
    requires_deep_dive: bool = False


@dataclass(slots=True)
class TransmissionHypothesis:
    hypothesis_id: str
    run_id: str
    stock_code: str
    stock_name: str
    theme: str
    hypothesis: str
    upstream_signals: list[str]
    affected_dimensions: list[str]
    assumptions: list[str]
    confidence: str
    evidence_ids: list[str]
    invalidating_conditions: list[str]
    score_impact: dict[str, Any]


@dataclass(slots=True)
class ScenarioRun:
    scenario_id: str
    run_id: str
    hypothesis_id: str
    stock_code: str
    stock_name: str
    base_case: dict[str, Any]
    upside_case: dict[str, Any]
    downside_case: dict[str, Any]
    key_variables: list[str]
    notes: str


@dataclass(slots=True)
class ManualImportTask:
    task_id: str
    run_id: str
    source_id: str
    source_name: str
    theme: str
    requested_input: str
    reason: str
    status: str = "pending"
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class ForwardAlphaRun:
    run_id: str
    stock_code: str
    stock_name: str
    themes: list[str]
    status: str
    summary: str
    budget: dict[str, Any]
    budget_used: dict[str, Any]
    source_candidates: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    comparisons: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    scenarios: list[dict[str, Any]]
    manual_import_tasks: list[dict[str, Any]]
    deep_dive_tasks: list[dict[str, Any]]
    llm_status: str = "disabled"
    generated_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class RadarEvidence:
    evidence_id: str
    stock_code: str
    stock_name: str
    claim: str
    source_family: str
    source_rank: str
    source_url: str = ""
    raw_excerpt: str = ""
    stance: str = "support"
    source_title: str = ""
    independence_group: str = ""
    evidence_date: str = field(default_factory=today_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceProfile:
    source_id: str
    source_family: str
    source_rank: str
    source_name: str
    independence_group: str
    credibility_score: int
    cost_class: str = "free"
    known_biases: list[str] = field(default_factory=list)
    conflict_flags: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(slots=True)
class RadarClaim:
    claim_id: str
    stock_code: str
    stock_name: str
    claim_text: str
    theme: str
    thesis_stage: str
    status: str
    scores: dict[str, Any]
    evidence_ids: list[str]
    source_profile_ids: list[str]
    upgrade_blockers: list[str]
    suggested_action: str
    review_required: bool = True


@dataclass(slots=True)
class CrossValidationResult:
    claim_id: str
    gate_status: str
    result_state: str
    source_families: list[str]
    independent_groups: list[str]
    support_count: int
    contradiction_count: int
    x_score_before: int
    x_score_after: int
    upgrade_blockers: list[str]
    strongest_support: list[dict[str, Any]]
    strongest_contradictions: list[dict[str, Any]]


@dataclass(slots=True)
class ClaimRevision:
    claim_id: str
    previous_status: str
    new_status: str
    score_before: dict[str, Any]
    score_after: dict[str, Any]
    changes: list[str]
    reason: str


@dataclass(slots=True)
class RadarValidationTask:
    task_id: str
    claim_id: str
    stock_code: str
    stock_name: str
    task_type: str
    question: str
    target_source_family: str
    success_criteria: str
    failure_criteria: str
    due_date: str
    priority: str = "P1"
    status: str = "pending"


@dataclass(slots=True)
class BearCase:
    bear_case_id: str
    claim_id: str
    stock_code: str
    stock_name: str
    risk_type: str
    claim: str
    evidence_ids: list[str]
    severity: str
    what_would_reduce_this_risk: str


@dataclass(slots=True)
class RadarReport:
    report_id: str
    stock_code: str
    stock_name: str
    theme: str
    generated_at: str
    generated_by: str
    summary: str
    radar_state: str
    scores: dict[str, Any]
    claims: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    source_profiles: list[dict[str, Any]]
    cross_validation: list[dict[str, Any]]
    claim_revisions: list[dict[str, Any]]
    validation_tasks: list[dict[str, Any]]
    bear_cases: list[dict[str, Any]]
    upgrade_blockers: list[str]
    suggested_user_action: str
    llm_status: str

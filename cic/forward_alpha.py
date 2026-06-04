from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any

from .llm import LLMClient
from .models import (
    DeepDiveTask,
    ForwardAlphaRun,
    ManualImportTask,
    ScenarioRun,
    SensorComparison,
    SensorObservation,
    SourceCandidate,
    TransmissionHypothesis,
    to_jsonable,
    utc_now_iso,
)
from .radar_rules import normalize_radar_input, normalize_source_family, normalize_source_rank, unique_items
from .rules import clamp_score, stable_id


DEFAULT_BUDGET = {
    "max_themes": 8,
    "max_source_candidates": 24,
    "max_auto_sources": 10,
    "max_llm_calls": 6,
    "timeout_seconds": 120,
    "allow_network_fetch": False,
}

RESTRICTED_LICENSE_STATUSES = {"restricted", "unknown"}
MANUAL_ACCESS_MODES = {"manual_input", "paid_terminal", "login_required", "field_research"}
SUPPORT_DIRECTIONS = {"positive", "support", "mixed"}
CONTRADICTION_DIRECTIONS = {"negative", "contradict"}


SOURCE_TEMPLATES = [
    {
        "source_id": "trendforce_memory_price",
        "source_name": "TrendForce 存储价格与供需报告",
        "source_family": "industry_data",
        "source_rank": "B",
        "theme": "NAND/DRAM 价格周期",
        "sensor_type": "industry_price",
        "source_url": "https://www.trendforce.com/",
        "cost_class": "mixed",
        "access_mode": "paid_terminal",
        "license_status": "restricted",
        "automation_allowed": False,
        "reason": "NAND/DRAM 合约价、库存和供需判断是存储链条最关键的前端数据。",
        "requested_input": "录入最近一期 NAND/DRAM 价格变化、库存判断、供需结论和原文短摘录。",
    },
    {
        "source_id": "chinaflashmarket_channel_price",
        "source_name": "ChinaFlashMarket / 闪存市场价格",
        "source_family": "industry_data",
        "source_rank": "B",
        "theme": "NAND/DRAM 价格周期",
        "sensor_type": "channel_price",
        "source_url": "https://www.chinaflashmarket.com/",
        "cost_class": "paid",
        "access_mode": "paid_terminal",
        "license_status": "restricted",
        "automation_allowed": False,
        "reason": "渠道和现货价格可早于财报反映价格周期变化。",
        "requested_input": "录入主流 NAND、DRAM、SSD 现货价周/月变化和价格分歧。",
    },
    {
        "source_id": "huaqiangbei_storage_channel",
        "source_name": "华强北存储渠道价格",
        "source_family": "public_footprint",
        "source_rank": "C",
        "theme": "存储模组渠道价格",
        "sensor_type": "channel_price",
        "source_url": "",
        "cost_class": "free",
        "access_mode": "field_research",
        "license_status": "unknown",
        "automation_allowed": False,
        "reason": "渠道报价、缺货和库存变化常常早于正式研究报告。",
        "requested_input": "录入华强北 SSD/内存模组报价、库存、缺货描述和询价日期。",
    },
    {
        "source_id": "cninfo_company_disclosure",
        "source_name": "巨潮/交易所公司公告",
        "source_family": "official_disclosure",
        "source_rank": "A",
        "theme": "公告与募投验证",
        "sensor_type": "official_disclosure",
        "source_url": "https://www.cninfo.com.cn/",
        "cost_class": "free",
        "access_mode": "public_web",
        "license_status": "clear",
        "automation_allowed": True,
        "reason": "公告是反证、募投、订单、客户和现金流验证的一手事实层。",
        "requested_input": "补充最新公告链接、标题和与订单/客户/募投/风险相关的短摘录。",
    },
    {
        "source_id": "procurement_tender_watch",
        "source_name": "招投标/采购平台",
        "source_family": "public_footprint",
        "source_rank": "C",
        "theme": "客户订单与产能消化",
        "sensor_type": "customer_order",
        "source_url": "",
        "cost_class": "free",
        "access_mode": "public_web",
        "license_status": "unknown",
        "automation_allowed": False,
        "reason": "中标、采购、集采和客户侧招标能提前暴露订单和需求兑现。",
        "requested_input": "录入客户、项目、采购品类、金额、日期、链接和是否可映射到公司产品。",
    },
    {
        "source_id": "expert_kol_memory_cycle",
        "source_name": "存储周期专家/KOL 观察",
        "source_family": "expert_kol",
        "source_rank": "C",
        "theme": "非共识弱信号",
        "sensor_type": "kol_weak_signal",
        "source_url": "",
        "cost_class": "free",
        "access_mode": "manual_input",
        "license_status": "unknown",
        "automation_allowed": False,
        "reason": "KOL 适合发现早期线索，但不能单独形成强结论。",
        "requested_input": "录入 KOL 原始观点、发布时间、过往准确性、是否持仓未知和待验证事实。",
    },
    {
        "source_id": "policy_industry_chain",
        "source_name": "政策/产业资金/国产替代目录",
        "source_family": "exchange_regulator",
        "source_rank": "A",
        "theme": "政策与产业链扩散",
        "sensor_type": "policy_signal",
        "source_url": "",
        "cost_class": "free",
        "access_mode": "public_web",
        "license_status": "clear",
        "automation_allowed": False,
        "reason": "政策、目录、补贴和产业资金决定主题能否从情绪走向订单。",
        "requested_input": "补充政策名称、发布日期、适用环节、资金口径和公司映射逻辑。",
    },
    {
        "source_id": "capacity_utilization_field",
        "source_name": "产能利用率/排产/募投消化线索",
        "source_family": "public_footprint",
        "source_rank": "C",
        "theme": "产能利用率与募投消化",
        "sensor_type": "capacity",
        "source_url": "",
        "cost_class": "free",
        "access_mode": "field_research",
        "license_status": "unknown",
        "automation_allowed": False,
        "reason": "扩产后利用率和毛利率是判断业绩弹性是否兑现的关键。",
        "requested_input": "录入排产、招聘、设备到位、产线爬坡、产能利用率或毛利率验证证据。",
    },
]


def run_forward_alpha_lab(
    payload: dict[str, Any],
    llm_client: LLMClient | None = None,
    use_llm: bool = False,
    budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged_budget = {**DEFAULT_BUDGET, **(budget or {})}
    radar = normalize_forward_payload(payload)
    generated_at = utc_now_iso()
    run_id = stable_id(radar["stock_code"], radar["theme"], generated_at, "forward-alpha", prefix="far_")
    themes = planned_themes_for(radar, int(merged_budget["max_themes"]))
    source_candidates = source_candidates_for(radar, run_id, themes, int(merged_budget["max_source_candidates"]))
    observations = observations_for(radar, run_id, source_candidates, int(merged_budget["max_auto_sources"]))
    comparisons = comparisons_for(run_id, observations)
    hypotheses = hypotheses_for(radar, run_id, themes, observations, comparisons, source_candidates)
    scenarios = scenarios_for(radar, run_id, hypotheses)
    manual_tasks = manual_import_tasks_for(run_id, source_candidates)
    deep_dive_tasks = deep_dive_tasks_for_forward_run(radar, run_id, comparisons)
    fallback_editor = forward_editor_payload(radar, source_candidates, observations, comparisons, hypotheses, manual_tasks)
    llm_status = "disabled"
    editor = fallback_editor
    if use_llm:
        client = llm_client or LLMClient()
        system_prompt, user_prompt = build_forward_alpha_prompt(radar, source_candidates, observations, comparisons, hypotheses, scenarios)
        result = client.chat_json(system_prompt, user_prompt, fallback_editor)
        editor = safe_forward_editor(result.data, fallback_editor)
        llm_status = result.status

    run = ForwardAlphaRun(
        run_id=run_id,
        stock_code=radar["stock_code"],
        stock_name=radar["stock_name"],
        themes=themes,
        status="completed",
        summary=str(editor.get("summary") or fallback_editor["summary"]),
        budget=merged_budget,
        budget_used={
            "themes": len(themes),
            "source_candidates": len(source_candidates),
            "auto_sources": len([item for item in source_candidates if item.collection_status == "auto_collectable"]),
            "observations": len(observations),
            "llm_calls": 1 if llm_status == "ok" else 0,
        },
        source_candidates=[to_jsonable(item) for item in source_candidates],
        observations=[to_jsonable(item) for item in observations],
        comparisons=[to_jsonable(item) for item in comparisons],
        hypotheses=[to_jsonable(item) for item in hypotheses],
        scenarios=[to_jsonable(item) for item in scenarios],
        manual_import_tasks=[to_jsonable(item) for item in manual_tasks],
        deep_dive_tasks=[to_jsonable(item) for item in deep_dive_tasks],
        llm_status=llm_status,
        generated_at=generated_at,
    )
    return {
        "forward_alpha": to_jsonable(run),
        "editor_questions": editor.get("editor_questions", fallback_editor["editor_questions"]),
        "deep_dives": {"tasks": [to_jsonable(item) for item in deep_dive_tasks], "runs": [], "findings": [], "verdicts": [], "decisions": []},
    }


def normalize_forward_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("radar") if isinstance(payload.get("radar"), dict) else payload
    if isinstance(raw.get("radar_report"), dict):
        report = raw["radar_report"]
        source = raw.get("input") if isinstance(raw.get("input"), dict) else {}
        raw = {
            **source,
            "stock_code": report.get("stock_code") or source.get("stock_code"),
            "stock_name": report.get("stock_name") or source.get("stock_name"),
            "theme": report.get("theme") or source.get("theme"),
            "evidence": source.get("evidence") or report.get("evidence") or [],
            "weak_signals": source.get("weak_signals") or [],
            "risks": source.get("risks") or report.get("upgrade_blockers") or [],
        }
    return normalize_radar_input(raw)


def planned_themes_for(radar: dict[str, Any], max_themes: int) -> list[str]:
    text = " ".join(
        [
            radar.get("theme", ""),
            radar.get("stock_name", ""),
            *(item.get("claim", "") for item in radar.get("evidence", []) if isinstance(item, dict)),
            *(item.get("signal_text", "") for item in radar.get("weak_signals", []) if isinstance(item, dict)),
            *radar.get("risks", []),
        ]
    )
    themes = [
        radar.get("theme", ""),
        "渠道价格/库存",
        "客户订单与产能消化",
        "政策与产业链扩散",
        "KOL/专家弱信号",
        "现金流质量",
    ]
    if any(term in text for term in ("NAND", "DRAM", "SSD", "存储", "内存")):
        themes = [
            "NAND/DRAM 价格周期",
            "存储模组渠道价格",
            "企业级 SSD 需求",
            "产能利用率与募投消化",
            "现金流质量",
            "客户订单与产能消化",
            "政策与国产替代",
            "KOL/专家弱信号",
            *themes,
        ]
    return unique_items(themes)[:max_themes]


def source_candidates_for(radar: dict[str, Any], run_id: str, themes: list[str], max_candidates: int) -> list[SourceCandidate]:
    candidates: OrderedDict[str, SourceCandidate] = OrderedDict()
    for item in candidates_from_input_evidence(radar, run_id, themes):
        candidates[item.source_id] = item
    stock_text = " ".join([radar["stock_name"], radar["theme"], *themes])
    for template in SOURCE_TEMPLATES:
        if not template_matches(template, stock_text, themes):
            continue
        item = candidate_from_template(run_id, template)
        candidates.setdefault(item.source_id, item)
    return list(candidates.values())[:max_candidates]


def candidates_from_input_evidence(radar: dict[str, Any], run_id: str, themes: list[str]) -> list[SourceCandidate]:
    output: list[SourceCandidate] = []
    rows = [*radar.get("evidence", []), *radar.get("weak_signals", [])]
    for index, raw in enumerate(rows, start=1):
        if not isinstance(raw, dict):
            continue
        claim = str(raw.get("claim") or raw.get("signal_text") or raw.get("raw_excerpt") or "").strip()
        family = normalize_source_family(raw.get("source_family") or raw.get("source_type"))
        rank = normalize_source_rank(raw.get("source_rank"), family)
        source_name = str(raw.get("source_name") or raw.get("title") or raw.get("source_url") or family)
        source_url = str(raw.get("source_url") or "")
        theme = theme_for_text(claim, themes)
        access_mode = str(raw.get("access_mode") or "public_web")
        license_status = str(raw.get("license_status") or "clear")
        automation_allowed = bool(raw.get("automation_allowed", family not in {"expert_kol", "social_media", "forum", "rumor"}))
        candidate = SourceCandidate(
            source_id=stable_id(run_id, index, source_name, source_url, claim[:80], prefix="fas_"),
            run_id=run_id,
            source_name=source_name,
            source_family=family,
            source_rank=rank,
            theme=theme,
            sensor_type=sensor_type_for_text(claim, family),
            source_url=source_url,
            cost_class=str(raw.get("cost_class") or "free"),
            access_mode=access_mode,
            license_status=license_status,
            automation_allowed=automation_allowed,
            reason="来自当前雷达输入，可作为前瞻链路的已知事实或反证基线。",
            independence_group=str(raw.get("independence_group") or stable_id(family, source_url or source_name, prefix="grp_")),
            raw_excerpt=str(raw.get("raw_excerpt") or claim)[:600],
            metadata={"claim": claim, "source_index": index},
        )
        candidate.collection_status = collection_status_for(candidate)
        output.append(candidate)
    return output


def template_matches(template: dict[str, Any], stock_text: str, themes: list[str]) -> bool:
    combined = " ".join([stock_text, *themes])
    theme = str(template.get("theme") or "")
    if any(term in combined for term in ("NAND", "DRAM", "SSD", "存储", "内存")):
        return True
    return any(term in combined for term in theme.split("/")) or template["source_id"] in {
        "policy_industry_chain",
        "procurement_tender_watch",
        "expert_kol_memory_cycle",
    }


def candidate_from_template(run_id: str, template: dict[str, Any]) -> SourceCandidate:
    item = SourceCandidate(
        source_id=stable_id(run_id, template["source_id"], prefix="fas_"),
        run_id=run_id,
        source_name=str(template["source_name"]),
        source_family=str(template["source_family"]),
        source_rank=str(template["source_rank"]),
        theme=str(template["theme"]),
        sensor_type=str(template["sensor_type"]),
        source_url=str(template.get("source_url") or ""),
        cost_class=str(template.get("cost_class") or "free"),
        access_mode=str(template.get("access_mode") or "public_web"),
        license_status=str(template.get("license_status") or "unknown"),
        automation_allowed=bool(template.get("automation_allowed")),
        reason=str(template.get("reason") or ""),
        independence_group=stable_id(template["source_id"], template.get("source_url") or template["source_name"], prefix="grp_"),
        metadata={"template_id": template["source_id"], "requested_input": template.get("requested_input", "")},
    )
    item.collection_status = collection_status_for(item)
    return item


def collection_status_for(candidate: SourceCandidate) -> str:
    if candidate.license_status in RESTRICTED_LICENSE_STATUSES:
        return "manual_import_required"
    if candidate.access_mode in MANUAL_ACCESS_MODES:
        return "manual_import_required"
    if not candidate.automation_allowed:
        return "manual_import_required"
    if not candidate.source_url and not candidate.raw_excerpt:
        return "manual_import_required"
    return "auto_collectable"


def observations_for(
    radar: dict[str, Any],
    run_id: str,
    candidates: list[SourceCandidate],
    max_auto_sources: int,
) -> list[SensorObservation]:
    observations: list[SensorObservation] = []
    auto_candidates = [item for item in candidates if item.collection_status == "auto_collectable"][:max_auto_sources]
    seen: set[str] = set()
    for candidate in auto_candidates:
        for metric, value, direction, strength in extract_metrics(candidate):
            content_key = stable_id(candidate.independence_group, metric, value, direction, prefix="")
            if content_key in seen:
                continue
            seen.add(content_key)
            observations.append(
                SensorObservation(
                    observation_id=stable_id(run_id, candidate.source_id, metric, value, prefix="fao_"),
                    run_id=run_id,
                    source_id=candidate.source_id,
                    stock_code=radar["stock_code"],
                    stock_name=radar["stock_name"],
                    theme=candidate.theme,
                    sensor_type=candidate.sensor_type,
                    metric=metric,
                    value=value,
                    unit="text",
                    direction=direction,
                    signal_strength=clamp_score(strength),
                    source_family=candidate.source_family,
                    source_rank=candidate.source_rank,
                    independence_group=candidate.independence_group,
                    source_url=candidate.source_url,
                    raw_excerpt=candidate.raw_excerpt or str(candidate.metadata.get("claim") or candidate.reason),
                )
            )
    return observations


def extract_metrics(candidate: SourceCandidate) -> list[tuple[str, str, str, int]]:
    text = " ".join([candidate.raw_excerpt, str(candidate.metadata.get("claim") or ""), candidate.reason])
    output: list[tuple[str, str, str, int]] = []
    if any(term in text for term in ("经营活动现金流", "现金流为负", "现金流量净额为负")):
        output.append(("operating_cashflow_quality", "经营现金流为负或弱于利润", "negative", 84))
    if any(term in text for term in ("SSD扩产", "DRAM扩产", "募投", "扩产")):
        output.append(("capacity_expansion", "存在 SSD/DRAM/募投扩产，需要验证产能消化和毛利率", "mixed", 74))
    if any(term in text for term in ("存储控制芯片", "固态硬盘", "内存模组", "存储模组", "解决方案提供商")):
        output.append(("business_exposure", "业务暴露于存储主控/模组/SSD链条", "support", 64))
    if any(term in text for term in ("订单", "客户", "中标", "采购", "批量")):
        output.append(("customer_order_validation", "出现客户/订单/批量交付线索", "positive", 72))
    if any(term in text for term in ("涨价", "价格上涨", "供不应求", "缺货")):
        output.append(("industry_price_inflection", "价格或供需出现正向变化", "positive", 78))
    if not output and candidate.source_family in {"official_disclosure", "company_website"}:
        output.append(("official_baseline", "一手或公司侧事实可作为前瞻链路基线", "support", 48))
    return output


def comparisons_for(run_id: str, observations: list[SensorObservation]) -> list[SensorComparison]:
    by_metric: OrderedDict[str, list[SensorObservation]] = OrderedDict()
    for item in observations:
        by_metric.setdefault(item.metric, []).append(item)
    comparisons: list[SensorComparison] = []
    for metric, items in by_metric.items():
        groups = unique_items(item.independence_group for item in items)
        supports = [item for item in items if item.direction in SUPPORT_DIRECTIONS]
        contradictions = [item for item in items if item.direction in CONTRADICTION_DIRECTIONS]
        families = {item.source_family for item in supports}
        kol_only = bool(families) and families == {"expert_kol"}
        boost_allowed = len(groups) >= 2 and len(supports) >= 2 and not kol_only
        if contradictions and supports:
            state = "divergent_review"
            delta = 0
        elif contradictions:
            state = "risk_blocker"
            delta = -8
        elif boost_allowed:
            state = "cross_source_converging"
            delta = min(16, len(groups) * 4 + len(families) * 4)
        else:
            state = "single_source_watch"
            delta = 0
        comparisons.append(
            SensorComparison(
                comparison_id=stable_id(run_id, metric, ",".join(groups), prefix="fac_"),
                run_id=run_id,
                theme=items[0].theme,
                sensor_type=items[0].sensor_type,
                metric=metric,
                result_state=state,
                source_ids=[item.source_id for item in items],
                independent_groups=groups,
                support_count=len(supports),
                contradiction_count=len(contradictions),
                forward_score_delta=delta,
                summary=comparison_summary(metric, state, len(supports), len(contradictions), delta),
                requires_deep_dive=bool(contradictions),
            )
        )
    return comparisons


def comparison_summary(metric: str, state: str, support_count: int, contradiction_count: int, delta: int) -> str:
    if state == "cross_source_converging":
        return f"{metric} 已有 {support_count} 条独立支持，前瞻强度提高 {delta}。"
    if state == "risk_blocker":
        return f"{metric} 出现反证或风险阻断，需要先深挖。"
    if state == "divergent_review":
        return f"{metric} 同时存在支持和反证，不能强行合并结论。"
    return f"{metric} 仍是单来源观察，不增加前瞻强度。"


def hypotheses_for(
    radar: dict[str, Any],
    run_id: str,
    themes: list[str],
    observations: list[SensorObservation],
    comparisons: list[SensorComparison],
    sources: list[SourceCandidate],
) -> list[TransmissionHypothesis]:
    hypotheses: list[TransmissionHypothesis] = []
    metrics = {item.metric for item in observations}
    source_themes = {item.theme for item in sources}
    score_delta = sum(item.forward_score_delta for item in comparisons)
    if any("NAND" in theme or "存储" in theme or "SSD" in theme for theme in [*themes, *source_themes]):
        hypotheses.append(
            TransmissionHypothesis(
                hypothesis_id=stable_id(run_id, "memory-price-transmission", prefix="fah_"),
                run_id=run_id,
                stock_code=radar["stock_code"],
                stock_name=radar["stock_name"],
                theme="NAND/DRAM 价格周期",
                hypothesis="如果 NAND/DRAM 价格、渠道库存和企业级 SSD 需求同步改善，公司收入弹性可能先于公告体现。",
                upstream_signals=["NAND/DRAM 合约价", "华强北渠道价", "企业级 SSD 需求", "库存/缺货"],
                affected_dimensions=["收入增速", "毛利率", "存货跌价风险", "产能利用率"],
                assumptions=["价格改善能传导到公司主要产品", "客户需求不是短期囤货", "扩产节奏不显著压低毛利率"],
                confidence="medium" if "business_exposure" in metrics else "low",
                evidence_ids=[item.observation_id for item in observations if item.metric in {"business_exposure", "industry_price_inflection"}],
                invalidating_conditions=["价格改善未延续", "渠道库存上升但出货未改善", "毛利率下降抵消收入增长"],
                score_impact={"E": 8, "X": max(0, score_delta), "I": 10, "U": -4},
            )
        )
    if "capacity_expansion" in metrics:
        hypotheses.append(
            TransmissionHypothesis(
                hypothesis_id=stable_id(run_id, "capacity-utilization", prefix="fah_"),
                run_id=run_id,
                stock_code=radar["stock_code"],
                stock_name=radar["stock_name"],
                theme="产能利用率与募投消化",
                hypothesis="SSD/DRAM 扩产提高收入天花板，但需要客户订单和产能利用率证据，否则可能压低毛利率。",
                upstream_signals=["募投扩产", "产线爬坡", "客户订单", "产能利用率"],
                affected_dimensions=["收入规模", "固定成本摊薄", "毛利率", "现金流"],
                assumptions=["扩产项目按期释放", "客户消化能力同步提高"],
                confidence="medium",
                evidence_ids=[item.observation_id for item in observations if item.metric == "capacity_expansion"],
                invalidating_conditions=["新增产能利用率低于预期", "毛利率连续下滑", "经营现金流继续弱于净利润"],
                score_impact={"E": 6, "X": 0, "I": 8, "U": 6},
            )
        )
    if "operating_cashflow_quality" in metrics:
        hypotheses.append(
            TransmissionHypothesis(
                hypothesis_id=stable_id(run_id, "cashflow-falsification", prefix="fah_"),
                run_id=run_id,
                stock_code=radar["stock_code"],
                stock_name=radar["stock_name"],
                theme="现金流质量",
                hypothesis="经营现金流为负可能证伪业绩弹性，必须拆分应收、存货和结算周期来源。",
                upstream_signals=["应收账款", "存货", "结算周期", "现金流量净额"],
                affected_dimensions=["财务质量", "风险等级", "估值容忍度"],
                assumptions=["现金流短期承压可被结算周期解释", "存货没有明显跌价压力"],
                confidence="high",
                evidence_ids=[item.observation_id for item in observations if item.metric == "operating_cashflow_quality"],
                invalidating_conditions=["应收和存货继续快于收入增长", "现金流连续为负且无合理解释"],
                score_impact={"E": 0, "X": -8, "I": -4, "U": 12},
            )
        )
    return hypotheses[:4]


def scenarios_for(radar: dict[str, Any], run_id: str, hypotheses: list[TransmissionHypothesis]) -> list[ScenarioRun]:
    scenarios: list[ScenarioRun] = []
    for item in hypotheses:
        is_cashflow = "现金流" in item.theme
        base_growth = 18 if is_cashflow else 28
        upside_growth = 30 if is_cashflow else 55
        downside_growth = 5 if is_cashflow else 8
        scenarios.append(
            ScenarioRun(
                scenario_id=stable_id(run_id, item.hypothesis_id, "scenario", prefix="fasn_"),
                run_id=run_id,
                hypothesis_id=item.hypothesis_id,
                stock_code=radar["stock_code"],
                stock_name=radar["stock_name"],
                base_case={
                    "revenue_growth_pct": base_growth,
                    "gross_margin_change_pct": -1 if is_cashflow else 1,
                    "cash_conversion": "需要解释现金流来源" if is_cashflow else "等待订单和回款验证",
                    "expected_effect": "维持观察，不能升级为无条件候选。",
                },
                upside_case={
                    "revenue_growth_pct": upside_growth,
                    "gross_margin_change_pct": 2 if is_cashflow else 4,
                    "cash_conversion": "现金流改善或结算周期被解释",
                    "expected_effect": "前瞻强度提高，但仍需规则引擎和人工确认。",
                },
                downside_case={
                    "revenue_growth_pct": downside_growth,
                    "gross_margin_change_pct": -6 if is_cashflow else -5,
                    "cash_conversion": "应收/存货继续恶化",
                    "expected_effect": "触发证伪或风险复核。",
                },
                key_variables=item.upstream_signals,
                notes="场景测算是研究假设，不是买卖建议；需要后续来源持续更新。",
            )
        )
    return scenarios


def manual_import_tasks_for(run_id: str, sources: list[SourceCandidate]) -> list[ManualImportTask]:
    tasks: list[ManualImportTask] = []
    for source in sources:
        if source.collection_status != "manual_import_required":
            continue
        requested = str(source.metadata.get("requested_input") or "补充来源原文、日期、链接、核心字段和短摘录。")
        tasks.append(
            ManualImportTask(
                task_id=stable_id(run_id, source.source_id, "manual-import", prefix="fmi_"),
                run_id=run_id,
                source_id=source.source_id,
                source_name=source.source_name,
                theme=source.theme,
                requested_input=requested,
                reason=source.reason,
            )
        )
    return tasks[:12]


def deep_dive_tasks_for_forward_run(radar: dict[str, Any], run_id: str, comparisons: list[SensorComparison]) -> list[DeepDiveTask]:
    tasks: list[DeepDiveTask] = []
    for comparison in comparisons:
        if not comparison.requires_deep_dive:
            continue
        label = metric_label(comparison.metric)
        tasks.append(
            DeepDiveTask(
                task_id=stable_id(run_id, comparison.comparison_id, "forward-alpha-deep-dive", prefix="ddt_"),
                report_id=run_id,
                claim_id=comparison.comparison_id,
                stock_code=radar["stock_code"],
                stock_name=radar["stock_name"],
                question=f"{radar['stock_name']}：前瞻信号 {label} 是否构成阻断或证伪？",
                trigger_type="forward_alpha_conflict",
                trigger_ref_id=comparison.comparison_id,
                trigger_reason=comparison.summary,
                priority="P0" if comparison.contradiction_count else "P1",
                allowed_source_families=["official_disclosure", "financial_data", "industry_data", "market_data", "public_footprint"],
                budget={"max_sources": 5, "max_llm_calls": 2, "timeout_seconds": 120},
                auto_run_eligible=False,
            )
        )
    return tasks


def metric_label(metric: str) -> str:
    labels = {
        "operating_cashflow_quality": "现金流质量",
        "capacity_expansion": "产能扩张",
        "business_exposure": "业务暴露",
        "customer_order_validation": "客户订单",
        "industry_price_inflection": "价格拐点",
        "official_baseline": "官方事实基线",
    }
    return labels.get(metric, metric)


def forward_editor_payload(
    radar: dict[str, Any],
    sources: list[SourceCandidate],
    observations: list[SensorObservation],
    comparisons: list[SensorComparison],
    hypotheses: list[TransmissionHypothesis],
    manual_tasks: list[ManualImportTask],
) -> dict[str, Any]:
    auto_count = len([item for item in sources if item.collection_status == "auto_collectable"])
    restricted_count = len(manual_tasks)
    converging = [item for item in comparisons if item.result_state == "cross_source_converging"]
    blockers = [item for item in comparisons if item.requires_deep_dive]
    summary = (
        f"{radar['stock_name']} 前瞻探索完成：发现 {len(sources)} 个候选信源，"
        f"{auto_count} 个可自动采集，{restricted_count} 个需人工导入；"
        f"形成 {len(observations)} 条前端观测、{len(hypotheses)} 条传导假设。"
        f"当前只有 {len(converging)} 个指标达到多来源收敛，{len(blockers)} 个指标需要证伪优先深挖。"
    )
    questions = [
        "先补 TrendForce/CFM 或渠道价格，验证 NAND/DRAM 价格是否真正传导。",
        "补客户订单、采购或产能利用率证据，判断扩产是否能被消化。",
        "拆分经营现金流为负来自应收、存货还是结算周期。",
    ]
    return {"summary": summary, "editor_questions": questions[:4]}


def build_forward_alpha_prompt(
    radar: dict[str, Any],
    sources: list[SourceCandidate],
    observations: list[SensorObservation],
    comparisons: list[SensorComparison],
    hypotheses: list[TransmissionHypothesis],
    scenarios: list[ScenarioRun],
) -> tuple[str, str]:
    system = (
        "你是 A 股前瞻信号实验室主编。只输出 JSON。"
        "你不能给无条件买卖建议，只能总结前端数据、交叉验证、传导假设和待人工复核问题。"
    )
    user = {
        "task": "生成克制摘要和 2-4 个下一步复核问题。",
        "schema": {"summary": "string", "editor_questions": ["string"]},
        "stock": {"code": radar["stock_code"], "name": radar["stock_name"], "theme": radar["theme"]},
        "source_candidates": [to_jsonable(item) for item in sources[:12]],
        "observations": [to_jsonable(item) for item in observations[:12]],
        "comparisons": [to_jsonable(item) for item in comparisons],
        "hypotheses": [to_jsonable(item) for item in hypotheses],
        "scenarios": [to_jsonable(item) for item in scenarios],
    }
    return system, json.dumps(user, ensure_ascii=False)


def safe_forward_editor(data: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    forbidden = ("买入", "卖出", "加仓", "减仓", "满仓", "梭哈")
    summary = str(data.get("summary") or "")
    if any(word in summary for word in forbidden):
        return fallback
    questions = data.get("editor_questions")
    if not isinstance(questions, list):
        return fallback
    clean_questions = [str(item) for item in questions if not any(word in str(item) for word in forbidden)]
    return {"summary": summary or fallback["summary"], "editor_questions": clean_questions[:4] or fallback["editor_questions"]}


def theme_for_text(text: str, themes: list[str]) -> str:
    for theme in themes:
        if any(term and term in text for term in theme.replace("/", " ").split()):
            return theme
    if any(term in text for term in ("现金流", "应收", "存货")):
        return "现金流质量"
    if any(term in text for term in ("SSD", "DRAM", "扩产", "募投")):
        return "产能利用率与募投消化"
    if any(term in text for term in ("NAND", "DRAM", "价格", "存储")):
        return "NAND/DRAM 价格周期"
    return themes[0] if themes else "全市场前瞻探索"


def sensor_type_for_text(text: str, family: str) -> str:
    if any(term in text for term in ("现金流", "应收", "存货")):
        return "financial_quality"
    if any(term in text for term in ("SSD", "DRAM", "扩产", "募投", "产能")):
        return "capacity"
    if any(term in text for term in ("订单", "客户", "采购", "中标")):
        return "customer_order"
    if any(term in text for term in ("NAND", "DRAM", "价格", "库存")):
        return "industry_price"
    if family == "expert_kol":
        return "kol_weak_signal"
    if family == "official_disclosure":
        return "official_disclosure"
    return "business_footprint"


def default_forward_alpha_summary() -> dict[str, Any]:
    return {
        "forward_alpha": {
            "run_id": "",
            "stock_code": "",
            "stock_name": "",
            "themes": [],
            "status": "not_run",
            "summary": "暂无前瞻探索结果",
            "budget": DEFAULT_BUDGET,
            "budget_used": {},
            "source_candidates": [],
            "observations": [],
            "comparisons": [],
            "hypotheses": [],
            "scenarios": [],
            "manual_import_tasks": [],
            "deep_dive_tasks": [],
            "llm_status": "not_run",
            "generated_at": "",
        },
        "editor_questions": [],
        "deep_dives": {"tasks": [], "runs": [], "findings": [], "verdicts": [], "decisions": []},
    }

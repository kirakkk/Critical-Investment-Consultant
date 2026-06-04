from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentSkill:
    skill_id: str
    display_name: str
    category: str
    description: str
    outputs: tuple[str, ...] = ()
    requires_source_gate: bool = False
    allowed_access_modes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AgentSkillProfile:
    agent_id: str
    display_name: str
    stage: str
    mission: str
    required_skill_ids: tuple[str, ...]
    optional_skill_ids: tuple[str, ...] = ()
    source_family_scope: tuple[str, ...] = ()
    default_budget: dict[str, int] = field(default_factory=dict)
    guardrails: tuple[str, ...] = ()

    def all_skill_ids(self) -> tuple[str, ...]:
        return unique_items((*self.required_skill_ids, *self.optional_skill_ids))


DEFAULT_AGENT_BUDGET = {"max_sources": 5, "max_llm_calls": 2, "max_token_estimate": 3200}
NO_SOURCE_BUDGET = {"max_sources": 0, "max_llm_calls": 1, "max_token_estimate": 2400}


SKILL_REGISTRY: dict[str, AgentSkill] = {
    "source_catalog_gate": AgentSkill(
        skill_id="source_catalog_gate",
        display_name="来源授权门禁",
        category="governance",
        description="检查 cost_class、access_mode、license_status、automation_allowed，决定是否允许自动访问。",
        outputs=("source_gate_decision", "blocked_reason", "manual_fallback"),
    ),
    "manual_source_ingest": AgentSkill(
        skill_id="manual_source_ingest",
        display_name="手动信源导入",
        category="source_access",
        description="接收用户粘贴的文本、链接、截图转写或文件摘录，保留原始片段和导入理由。",
        outputs=("raw_document", "manual_import_task", "raw_excerpt"),
        allowed_access_modes=("manual_upload", "manual_paste", "web_manual"),
    ),
    "public_web_scrape": AgentSkill(
        skill_id="public_web_scrape",
        display_name="公开网页抓取",
        category="source_access",
        description="抓取已授权的公开网页、公司官网、招投标、政策网页和公开足迹页面。",
        outputs=("raw_document", "source_observation", "capture_metadata"),
        requires_source_gate=True,
        allowed_access_modes=("public_web", "web_scrape_allowed", "official_api"),
    ),
    "official_disclosure_fetch": AgentSkill(
        skill_id="official_disclosure_fetch",
        display_name="公告/交易所抓取",
        category="source_access",
        description="获取交易所、巨潮、监管公告、公司公告和公开财报文件。",
        outputs=("raw_document", "official_disclosure_event"),
        requires_source_gate=True,
        allowed_access_modes=("official_api", "public_web", "web_scrape_allowed"),
    ),
    "pdf_announcement_extract": AgentSkill(
        skill_id="pdf_announcement_extract",
        display_name="PDF/公告解析",
        category="extraction",
        description="从公告、财报和上传 PDF 中提取表格、事件、原文摘录和页码。",
        outputs=("document_text", "tables", "raw_excerpt", "page_ref"),
    ),
    "source_attribution": AgentSkill(
        skill_id="source_attribution",
        display_name="来源归因",
        category="governance",
        description="识别 source_family、source_rank、independence_group 和来源身份稳定性。",
        outputs=("source_family", "source_rank", "independence_group", "source_profile_id"),
    ),
    "evidence_dedupe": AgentSkill(
        skill_id="evidence_dedupe",
        display_name="证据去重",
        category="governance",
        description="按 URL、内容哈希、独立来源组和语义相似度合并重复证据。",
        outputs=("canonical_evidence_id", "duplicate_group", "similarity_score"),
    ),
    "claim_extraction": AgentSkill(
        skill_id="claim_extraction",
        display_name="Claim 结构化提取",
        category="extraction",
        description="把原文拆成事实、推断、观点、未知项和可验证 claim。",
        outputs=("claims", "facts", "inferences", "opinions", "unknowns"),
    ),
    "claim_graph_lookup": AgentSkill(
        skill_id="claim_graph_lookup",
        display_name="Claim 图谱查询",
        category="memory",
        description="查询已有 claim、evidence、revision、contradiction 和 validation task。",
        outputs=("related_claims", "evidence_links", "claim_revisions"),
    ),
    "cross_source_validation": AgentSkill(
        skill_id="cross_source_validation",
        display_name="交叉验证分析",
        category="analysis",
        description="检查支持证据是否跨来源家族、跨独立组，并识别缺失验证来源。",
        outputs=("cross_validation_matrix", "missing_source_families", "validation_tasks"),
    ),
    "historical_diff": AgentSkill(
        skill_id="historical_diff",
        display_name="历史差异分析",
        category="analysis",
        description="比较新旧 claim、证据和叙事变化，生成 revision 草案。",
        outputs=("claim_revision", "changed_fields", "diff_summary"),
    ),
    "kol_profile_lookup": AgentSkill(
        skill_id="kol_profile_lookup",
        display_name="KOL 档案查询",
        category="analysis",
        description="查询 KOL 身份稳定性、历史命中、利益冲突、证据纪律和原创性。",
        outputs=("source_profile", "kol_quality_score", "conflict_flags"),
    ),
    "market_snapshot_analysis": AgentSkill(
        skill_id="market_snapshot_analysis",
        display_name="行情/板块数据分析",
        category="analysis",
        description="读取行情、板块、peer、成交、相对收益和拥挤度快照。",
        outputs=("market_observation", "relative_strength", "peer_context"),
        requires_source_gate=True,
        allowed_access_modes=("official_api", "vendor_api", "open_source_research", "manual_upload"),
    ),
    "financial_statement_analysis": AgentSkill(
        skill_id="financial_statement_analysis",
        display_name="财务质量分析",
        category="analysis",
        description="分析收入、利润、毛利率、现金流、应收、存货、负债和异常项。",
        outputs=("financial_observation", "quality_flags", "risk_flags"),
        requires_source_gate=True,
        allowed_access_modes=("official_api", "open_source_research", "manual_upload"),
    ),
    "peer_comparison_analysis": AgentSkill(
        skill_id="peer_comparison_analysis",
        display_name="同业比较分析",
        category="analysis",
        description="构造同业集合，比较业务弹性、估值、财务质量和主题暴露。",
        outputs=("peer_set", "comparison_dimensions", "relative_position"),
    ),
    "contradiction_mining": AgentSkill(
        skill_id="contradiction_mining",
        display_name="反证挖掘",
        category="analysis",
        description="围绕核心 claim 查找负面事实、缺失证据、互斥解释和 kill condition。",
        outputs=("contradictions", "bear_cases", "kill_conditions", "risk_debt"),
    ),
    "scenario_sensitivity": AgentSkill(
        skill_id="scenario_sensitivity",
        display_name="情景/敏感性分析",
        category="analysis",
        description="生成 base、upside、failure 情景和关键变量敏感性，不输出收益承诺。",
        outputs=("scenarios", "sensitivity_drivers", "failure_case"),
    ),
    "validation_task_builder": AgentSkill(
        skill_id="validation_task_builder",
        display_name="验证任务生成",
        category="workflow",
        description="把缺失证据和待证伪问题转成 30/90 天验证任务。",
        outputs=("validation_tasks", "failure_criteria", "review_priority"),
    ),
    "citation_pack_builder": AgentSkill(
        skill_id="citation_pack_builder",
        display_name="引用包生成",
        category="reporting",
        description="把报告中的结论绑定到 evidence_id、source_profile_id 和原文摘录。",
        outputs=("citation_pack", "evidence_refs"),
    ),
    "radar_brief_composition": AgentSkill(
        skill_id="radar_brief_composition",
        display_name="雷达 brief 主编",
        category="reporting",
        description="只基于已有结构化对象生成 brief、人工复核队列和下一步问题。",
        outputs=("radar_brief", "review_queue", "editor_notes"),
    ),
}


AGENT_SKILL_PROFILES: dict[str, AgentSkillProfile] = {
    "intake_agent": AgentSkillProfile(
        agent_id="intake_agent",
        display_name="弱信号捕捉 Agent",
        stage="mvp",
        mission="从用户输入、手动链接、KOL 片段和公告文本中生成 evidence、source_profile 和初始 claim。",
        required_skill_ids=(
            "source_catalog_gate",
            "manual_source_ingest",
            "source_attribution",
            "evidence_dedupe",
            "claim_extraction",
            "kol_profile_lookup",
        ),
        optional_skill_ids=("official_disclosure_fetch", "pdf_announcement_extract", "public_web_scrape"),
        source_family_scope=("official_disclosure", "public_footprint", "expert_kol", "manual"),
        default_budget=DEFAULT_AGENT_BUDGET,
        guardrails=(
            "KOL-only claims stay in validation and cannot become confirmed facts.",
            "Every extracted claim must keep raw_excerpt and unknowns.",
        ),
    ),
    "validation_agent": AgentSkillProfile(
        agent_id="validation_agent",
        display_name="交叉验证 Agent",
        stage="mvp",
        mission="验证 claim 是否跨非 KOL 来源家族收敛，并生成缺失来源和验证任务。",
        required_skill_ids=(
            "source_catalog_gate",
            "claim_graph_lookup",
            "cross_source_validation",
            "source_attribution",
            "evidence_dedupe",
            "validation_task_builder",
        ),
        optional_skill_ids=("official_disclosure_fetch", "public_web_scrape", "market_snapshot_analysis"),
        source_family_scope=("official_disclosure", "financial_data", "market_data", "public_footprint", "industry_data"),
        default_budget=DEFAULT_AGENT_BUDGET,
        guardrails=(
            "The agent may propose X-score evidence, but the rule engine recomputes final score.",
            "Missing non-KOL corroboration must remain visible in the output.",
        ),
    ),
    "diff_risk_agent": AgentSkillProfile(
        agent_id="diff_risk_agent",
        display_name="历史差异/风险 Agent",
        stage="mvp",
        mission="比较新旧 claim，挖掘反方证据，解释风险阻断和 claim revision。",
        required_skill_ids=(
            "source_catalog_gate",
            "claim_graph_lookup",
            "historical_diff",
            "contradiction_mining",
            "financial_statement_analysis",
            "market_snapshot_analysis",
            "validation_task_builder",
        ),
        optional_skill_ids=("official_disclosure_fetch", "public_web_scrape", "peer_comparison_analysis"),
        source_family_scope=("official_disclosure", "financial_data", "market_data", "industry_data", "public_footprint"),
        default_budget=DEFAULT_AGENT_BUDGET,
        guardrails=(
            "A/B rank contradictions must stay pinned until deterministic rules clear them.",
            "The agent cannot remove blockers; it can only propose findings and tasks.",
        ),
    ),
    "editor_agent": AgentSkillProfile(
        agent_id="editor_agent",
        display_name="主编 Agent",
        stage="mvp",
        mission="把结构化对象编译成雷达报告、复核队列和下一步研究问题。",
        required_skill_ids=("claim_graph_lookup", "citation_pack_builder", "radar_brief_composition"),
        source_family_scope=(),
        default_budget=NO_SOURCE_BUDGET,
        guardrails=(
            "The editor cannot fetch new sources or add new facts.",
            "Every conclusion must cite existing evidence or mark the unknown explicitly.",
        ),
    ),
    "official_disclosure_scout": AgentSkillProfile(
        agent_id="official_disclosure_scout",
        display_name="公告 Scout",
        stage="full",
        mission="发现并解析交易所、巨潮、监管和公司公告。",
        required_skill_ids=(
            "source_catalog_gate",
            "official_disclosure_fetch",
            "pdf_announcement_extract",
            "source_attribution",
            "claim_extraction",
            "evidence_dedupe",
        ),
        source_family_scope=("official_disclosure", "exchange_regulator", "company_website"),
        default_budget=DEFAULT_AGENT_BUDGET,
    ),
    "public_footprint_scout": AgentSkillProfile(
        agent_id="public_footprint_scout",
        display_name="公开足迹 Scout",
        stage="full",
        mission="发现公司官网、客户官网、招聘、专利、招投标和政策公开足迹。",
        required_skill_ids=(
            "source_catalog_gate",
            "public_web_scrape",
            "source_attribution",
            "claim_extraction",
            "evidence_dedupe",
        ),
        optional_skill_ids=("validation_task_builder",),
        source_family_scope=("public_footprint", "company_website", "policy_industry", "industry_data"),
        default_budget=DEFAULT_AGENT_BUDGET,
    ),
    "kol_scout": AgentSkillProfile(
        agent_id="kol_scout",
        display_name="KOL Scout",
        stage="full",
        mission="处理手动录入的 X/KOL/公众号片段，维护 KOL 档案和待验证事实。",
        required_skill_ids=(
            "manual_source_ingest",
            "source_attribution",
            "kol_profile_lookup",
            "claim_extraction",
            "evidence_dedupe",
            "validation_task_builder",
        ),
        source_family_scope=("expert_kol", "media_news", "manual"),
        default_budget=DEFAULT_AGENT_BUDGET,
        guardrails=(
            "Do not automate social or restricted sources unless source_catalog explicitly allows it.",
            "KOL quality can raise validation priority but cannot confirm a claim alone.",
        ),
    ),
    "market_scout": AgentSkillProfile(
        agent_id="market_scout",
        display_name="行情/同业 Scout",
        stage="full",
        mission="读取行情、板块、peer 和成交数据，形成市场观测。",
        required_skill_ids=(
            "source_catalog_gate",
            "market_snapshot_analysis",
            "peer_comparison_analysis",
            "evidence_dedupe",
        ),
        source_family_scope=("market_data", "financial_data", "industry_data"),
        default_budget=DEFAULT_AGENT_BUDGET,
    ),
    "contradiction_agent": AgentSkillProfile(
        agent_id="contradiction_agent",
        display_name="反证 Agent",
        stage="full",
        mission="主动查找支持链条中的反证、互斥解释、财务质量缺口和高等级负面来源。",
        required_skill_ids=(
            "source_catalog_gate",
            "claim_graph_lookup",
            "contradiction_mining",
            "public_web_scrape",
            "official_disclosure_fetch",
            "pdf_announcement_extract",
            "financial_statement_analysis",
            "market_snapshot_analysis",
            "peer_comparison_analysis",
            "validation_task_builder",
        ),
        optional_skill_ids=("historical_diff", "scenario_sensitivity"),
        source_family_scope=("official_disclosure", "financial_data", "market_data", "public_footprint", "industry_data"),
        default_budget=DEFAULT_AGENT_BUDGET,
        guardrails=(
            "Every contradiction must bind to evidence_id, source_url, raw_excerpt, or a named unknown.",
            "The agent cannot soften or clear blockers; the rule engine decides.",
        ),
    ),
    "bear_case_agent": AgentSkillProfile(
        agent_id="bear_case_agent",
        display_name="反方 Agent",
        stage="full",
        mission="反驳看多路径，生成 bear case、kill condition、risk debt 和需要人工复核的问题。",
        required_skill_ids=(
            "source_catalog_gate",
            "claim_graph_lookup",
            "contradiction_mining",
            "public_web_scrape",
            "official_disclosure_fetch",
            "financial_statement_analysis",
            "market_snapshot_analysis",
            "peer_comparison_analysis",
            "scenario_sensitivity",
            "citation_pack_builder",
        ),
        optional_skill_ids=("pdf_announcement_extract", "historical_diff", "validation_task_builder"),
        source_family_scope=("official_disclosure", "financial_data", "market_data", "industry_data", "public_footprint"),
        default_budget=DEFAULT_AGENT_BUDGET,
        guardrails=(
            "Do not invent bear cases; bind each one to evidence, contradiction, or explicit unknown.",
            "Do not output buy/sell advice or deterministic upside/downside returns.",
        ),
    ),
    "path_builder_agent": AgentSkillProfile(
        agent_id="path_builder_agent",
        display_name="路径 Agent",
        stage="full",
        mission="为高潜 claim 生成 12 个月路径、milestone、failure case 和 kill condition。",
        required_skill_ids=(
            "source_catalog_gate",
            "claim_graph_lookup",
            "financial_statement_analysis",
            "market_snapshot_analysis",
            "peer_comparison_analysis",
            "scenario_sensitivity",
            "validation_task_builder",
        ),
        source_family_scope=("financial_data", "market_data", "industry_data", "official_disclosure"),
        default_budget=DEFAULT_AGENT_BUDGET,
        guardrails=("Path output must include failure case and kill condition.",),
    ),
    "data_fetch_agent": AgentSkillProfile(
        agent_id="data_fetch_agent",
        display_name="数据抓取 Agent",
        stage="full",
        mission="在 source_catalog 授权范围内抓取公告、公开网页、行情和行业原始数据。",
        required_skill_ids=(
            "source_catalog_gate",
            "official_disclosure_fetch",
            "public_web_scrape",
            "market_snapshot_analysis",
            "pdf_announcement_extract",
            "evidence_dedupe",
        ),
        source_family_scope=("official_disclosure", "exchange_regulator", "market_data", "industry_data", "public_footprint"),
        default_budget={"max_sources": 10, "max_llm_calls": 0, "max_token_estimate": 800},
        guardrails=("Restricted or unknown-license sources become manual_import_tasks, never automatic fetches.",),
    ),
}


def unique_items(items: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return tuple(output)


def get_skill(skill_id: str) -> AgentSkill:
    try:
        return SKILL_REGISTRY[skill_id]
    except KeyError as exc:
        raise KeyError(f"unknown agent skill: {skill_id}") from exc


def get_agent_profile(agent_id: str) -> AgentSkillProfile:
    try:
        return AGENT_SKILL_PROFILES[agent_id]
    except KeyError as exc:
        raise KeyError(f"unknown agent profile: {agent_id}") from exc


def skills_for_agent(agent_id: str, include_optional: bool = False) -> list[AgentSkill]:
    profile = get_agent_profile(agent_id)
    skill_ids = profile.all_skill_ids() if include_optional else profile.required_skill_ids
    return [get_skill(skill_id) for skill_id in skill_ids]


def agent_skill_manifest(agent_id: str, include_optional: bool = True) -> dict[str, Any]:
    profile = get_agent_profile(agent_id)
    skills = skills_for_agent(agent_id, include_optional=include_optional)
    return {
        "agent_id": profile.agent_id,
        "display_name": profile.display_name,
        "stage": profile.stage,
        "mission": profile.mission,
        "skills": [
            {
                "skill_id": skill.skill_id,
                "display_name": skill.display_name,
                "category": skill.category,
                "requires_source_gate": skill.requires_source_gate,
                "allowed_access_modes": list(skill.allowed_access_modes),
                "outputs": list(skill.outputs),
            }
            for skill in skills
        ],
        "source_family_scope": list(profile.source_family_scope),
        "default_budget": dict(profile.default_budget),
        "guardrails": list(profile.guardrails),
    }


def validate_agent_skill_profiles() -> list[str]:
    errors: list[str] = []
    for agent_id, profile in AGENT_SKILL_PROFILES.items():
        all_skill_ids = profile.all_skill_ids()
        missing = [skill_id for skill_id in all_skill_ids if skill_id not in SKILL_REGISTRY]
        if missing:
            errors.append(f"{agent_id}: unknown skills {', '.join(missing)}")
            continue

        gated_skills = [SKILL_REGISTRY[skill_id].skill_id for skill_id in all_skill_ids if SKILL_REGISTRY[skill_id].requires_source_gate]
        if gated_skills and "source_catalog_gate" not in profile.required_skill_ids:
            errors.append(f"{agent_id}: source-gated skills require source_catalog_gate: {', '.join(gated_skills)}")

        if profile.default_budget.get("max_sources", 0) == 0:
            source_access = [
                skill_id
                for skill_id in profile.required_skill_ids
                if SKILL_REGISTRY[skill_id].category == "source_access" or SKILL_REGISTRY[skill_id].requires_source_gate
            ]
            if source_access:
                errors.append(f"{agent_id}: no-source budget cannot include source access skills: {', '.join(source_access)}")

    return errors

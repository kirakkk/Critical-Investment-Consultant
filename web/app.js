const els = {
  holdingsInput: document.querySelector("#holdingsInput"),
  loadSampleBtn: document.querySelector("#loadSampleBtn"),
  loadRadarSampleBtn: document.querySelector("#loadRadarSampleBtn"),
  analyzeBtn: document.querySelector("#analyzeBtn"),
  useLlm: document.querySelector("#useLlm"),
  runForwardAlphaBtn: document.querySelector("#runForwardAlphaBtn"),
  statusText: document.querySelector("#statusText"),
  inputTitle: document.querySelector("#inputTitle"),
  inputHelp: document.querySelector("#inputHelp"),
  metricOneLabel: document.querySelector("#metricOneLabel"),
  metricTwoLabel: document.querySelector("#metricTwoLabel"),
  metricThreeLabel: document.querySelector("#metricThreeLabel"),
  metricFourLabel: document.querySelector("#metricFourLabel"),
  topChangeCount: document.querySelector("#topChangeCount"),
  riskCount: document.querySelector("#riskCount"),
  thesisCount: document.querySelector("#thesisCount"),
  validationCount: document.querySelector("#validationCount"),
  holdingsSections: document.querySelector("#holdingsSections"),
  radarSections: document.querySelector("#radarSections"),
  llmStatus: document.querySelector("#llmStatus"),
  topChanges: document.querySelector("#topChanges"),
  thesisChecks: document.querySelector("#thesisChecks"),
  riskRadar: document.querySelector("#riskRadar"),
  validationPoints: document.querySelector("#validationPoints"),
  peerComparisons: document.querySelector("#peerComparisons"),
  signals: document.querySelector("#signals"),
  radarState: document.querySelector("#radarState"),
  radarSummary: document.querySelector("#radarSummary"),
  radarLlmStatus: document.querySelector("#radarLlmStatus"),
  deepDiveStatus: document.querySelector("#deepDiveStatus"),
  forwardAlphaStatus: document.querySelector("#forwardAlphaStatus"),
  forwardSources: document.querySelector("#forwardSources"),
  manualImports: document.querySelector("#manualImports"),
  sensorObservations: document.querySelector("#sensorObservations"),
  sensorComparisons: document.querySelector("#sensorComparisons"),
  transmissionHypotheses: document.querySelector("#transmissionHypotheses"),
  scenarioRuns: document.querySelector("#scenarioRuns"),
  deepDiveTasks: document.querySelector("#deepDiveTasks"),
  deepDiveVerdicts: document.querySelector("#deepDiveVerdicts"),
  radarClaims: document.querySelector("#radarClaims"),
  claimRevisions: document.querySelector("#claimRevisions"),
  upgradeBlockers: document.querySelector("#upgradeBlockers"),
  bearCases: document.querySelector("#bearCases"),
  radarTasks: document.querySelector("#radarTasks"),
  sourceProfiles: document.querySelector("#sourceProfiles"),
};

let currentMode = "holdings";
let lastRadarReport = null;
let lastRadarPayload = null;
let lastDeepDiveBundle = { tasks: [], runs: [], findings: [], verdicts: [], decisions: [] };
let lastForwardAlpha = null;

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

function setStatus(text) {
  els.statusText.textContent = text;
}

function setMode(mode) {
  currentMode = mode;
  const isRadar = mode === "radar";
  els.holdingsSections.classList.toggle("hidden", isRadar);
  els.radarSections.classList.toggle("hidden", !isRadar);
  els.inputTitle.textContent = isRadar ? "早期雷达输入" : "持仓输入";
  els.inputHelp.textContent = isRadar
    ? "粘贴弱信号 JSON，系统会输出 claim、交叉验证、阻断原因、历史差异、验证任务和反方证据。"
    : "粘贴持仓 JSON，系统会生成 Top 3 变化、假设体检、风险雷达、横向比较和验证点。";
  els.analyzeBtn.textContent = isRadar ? "生成早期雷达报告" : "生成投研报告";
  els.metricOneLabel.textContent = isRadar ? "Claims" : "Top Changes";
  els.metricTwoLabel.textContent = isRadar ? "反方证据" : "风险雷达";
  els.metricThreeLabel.textContent = isRadar ? "交叉验证" : "假设体检";
  els.metricFourLabel.textContent = isRadar ? "深挖任务" : "验证点";
}

async function loadSample() {
  const sample = await fetchJson("/api/sample-holdings");
  setMode("holdings");
  els.holdingsInput.value = JSON.stringify(sample, null, 2);
  setStatus("样例持仓已载入");
}

async function loadRadarSample() {
  const sample = await fetchJson("/api/sample-radar-signals");
  setMode("radar");
  els.holdingsInput.value = JSON.stringify(sample, null, 2);
  setStatus("德明利雷达样例已载入");
}

async function analyze() {
  let payload;
  try {
    payload = JSON.parse(els.holdingsInput.value || currentEmptyPayload());
  } catch (error) {
    setStatus("JSON 格式不正确");
    return;
  }

  const inputMode = detectMode(payload);
  setMode(inputMode);
  setStatus("分析中...");
  els.analyzeBtn.disabled = true;
  try {
    if (inputMode === "radar") {
      const report = await fetchJson("/api/radar/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ radar: payload, use_llm: els.useLlm.checked }),
      });
      renderRadarReport(report);
      setStatus(radarStatusText(report));
    } else {
      const holdings = Array.isArray(payload) ? payload : payload.holdings;
      if (!Array.isArray(holdings) || holdings.length === 0) {
        setStatus("请提供至少一只持仓");
        return;
      }
      const report = await fetchJson("/api/holdings/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ holdings, use_llm: els.useLlm.checked }),
      });
      renderReport(report);
      setStatus("报告已生成");
    }
  } catch (error) {
    setStatus(error.message);
  } finally {
    els.analyzeBtn.disabled = false;
  }
}

function radarStatusText(report) {
  const wiki = report.wiki || {};
  if (wiki.status === "exported") {
    return `早期雷达报告已生成，Obsidian wiki 已更新：${wiki.root}`;
  }
  if (wiki.status === "failed") {
    return `早期雷达报告已生成，Obsidian wiki 导出失败：${wiki.error}`;
  }
  return "早期雷达报告已生成";
}

function currentEmptyPayload() {
  return currentMode === "radar" ? "{}" : "[]";
}

function detectMode(payload) {
  if (Array.isArray(payload) || Array.isArray(payload.holdings)) {
    return "holdings";
  }
  if (payload && typeof payload === "object" && (payload.weak_signals || payload.evidence || payload.radar)) {
    return "radar";
  }
  return currentMode;
}

function renderReport(report) {
  const brief = report.brief || {};
  els.topChangeCount.textContent = (brief.top_changes || []).length;
  els.riskCount.textContent = (brief.risk_alerts || []).length;
  els.thesisCount.textContent = (brief.thesis_checks || []).length;
  els.validationCount.textContent = (brief.validation_points || []).length;
  els.llmStatus.textContent = `LLM: ${(report.llm && report.llm.status) || brief.llm_status || "unknown"}`;

  renderCards(els.topChanges, brief.top_changes || [], topChangeCard);
  renderCards(els.thesisChecks, brief.thesis_checks || [], thesisCard);
  renderCards(els.riskRadar, brief.risk_alerts || [], riskCard);
  renderCards(els.validationPoints, brief.validation_points || [], validationCard);
  renderCards(els.peerComparisons, brief.peer_comparisons || [], peerCard);
  renderCards(els.signals, brief.signals || [], signalCard);
}

function renderRadarReport(payload) {
  const report = payload.radar_report || {};
  const forwardAlpha = normalizeForwardAlpha(payload.forward_alpha || {});
  const deepDiveBundle = mergeDeepDiveBundles(payload.deep_dives || {}, { tasks: forwardAlpha.deep_dive_tasks || [] });
  lastRadarReport = report;
  lastRadarPayload = payload;
  lastDeepDiveBundle = deepDiveBundle;
  lastForwardAlpha = forwardAlpha;
  els.topChangeCount.textContent = (report.claims || []).length;
  els.riskCount.textContent = (report.bear_cases || []).length;
  els.thesisCount.textContent = (report.cross_validation || []).length;
  els.validationCount.textContent = (deepDiveBundle.tasks || []).length;
  els.radarState.textContent = report.radar_state || "unknown";
  els.radarSummary.textContent = report.summary || "暂无摘要";
  els.radarLlmStatus.textContent = `LLM: ${(payload.llm && payload.llm.status) || report.llm_status || "unknown"}`;
  els.deepDiveStatus.textContent = `${(deepDiveBundle.runs || []).length} 个已运行 / ${(deepDiveBundle.tasks || []).length} 个任务`;
  renderForwardAlpha(forwardAlpha);

  const crossByClaim = Object.fromEntries((report.cross_validation || []).map((item) => [item.claim_id, item]));
  renderCards(els.deepDiveTasks, deepDiveBundle.tasks || [], (item) => deepDiveTaskCard(item, deepDiveBundle));
  renderCards(els.deepDiveVerdicts, deepDiveBundle.verdicts || [], (item) => deepDiveVerdictCard(item, deepDiveBundle));
  renderCards(els.radarClaims, report.claims || [], (item) => radarClaimCard(item, crossByClaim[item.claim_id], report));
  renderCards(els.claimRevisions, report.claim_revisions || [], revisionCard);
  renderCards(els.upgradeBlockers, report.upgrade_blockers || [], blockerCard);
  renderCards(els.bearCases, report.bear_cases || [], bearCard);
  renderCards(els.radarTasks, report.validation_tasks || [], radarTaskCard);
  renderCards(els.sourceProfiles, report.source_profiles || [], sourceProfileCard);
}

function renderCards(container, items, renderer) {
  container.classList.remove("empty");
  if (!items.length) {
    container.classList.add("empty");
    container.textContent = "暂无数据";
    return;
  }
  container.innerHTML = items.map(renderer).join("");
}

function normalizeDeepDiveBundle(bundle) {
  return {
    tasks: Array.isArray(bundle.tasks) ? bundle.tasks : [],
    runs: Array.isArray(bundle.runs) ? bundle.runs : [],
    findings: Array.isArray(bundle.findings) ? bundle.findings : [],
    verdicts: Array.isArray(bundle.verdicts) ? bundle.verdicts : [],
    decisions: Array.isArray(bundle.decisions) ? bundle.decisions : [],
  };
}

function normalizeForwardAlpha(forwardAlpha) {
  return {
    run_id: forwardAlpha.run_id || "",
    stock_code: forwardAlpha.stock_code || "",
    stock_name: forwardAlpha.stock_name || "",
    summary: forwardAlpha.summary || "暂无前瞻探索结果",
    status: forwardAlpha.status || "not_run",
    budget_used: forwardAlpha.budget_used || {},
    source_candidates: Array.isArray(forwardAlpha.source_candidates) ? forwardAlpha.source_candidates : [],
    observations: Array.isArray(forwardAlpha.observations) ? forwardAlpha.observations : [],
    comparisons: Array.isArray(forwardAlpha.comparisons) ? forwardAlpha.comparisons : [],
    hypotheses: Array.isArray(forwardAlpha.hypotheses) ? forwardAlpha.hypotheses : [],
    scenarios: Array.isArray(forwardAlpha.scenarios) ? forwardAlpha.scenarios : [],
    manual_import_tasks: Array.isArray(forwardAlpha.manual_import_tasks) ? forwardAlpha.manual_import_tasks : [],
    deep_dive_tasks: Array.isArray(forwardAlpha.deep_dive_tasks) ? forwardAlpha.deep_dive_tasks : [],
  };
}

function renderForwardAlpha(forwardAlpha) {
  const used = forwardAlpha.budget_used || {};
  els.forwardAlphaStatus.textContent = `${forwardAlpha.status || "not_run"} · ${used.source_candidates || 0} 源 / ${used.observations || 0} 观测`;
  renderCards(els.sensorComparisons, forwardAlpha.comparisons || [], sensorComparisonCard);
  renderCards(els.transmissionHypotheses, forwardAlpha.hypotheses || [], transmissionHypothesisCard);
  renderCards(els.manualImports, forwardAlpha.manual_import_tasks || [], manualImportCard);
  renderCards(els.scenarioRuns, forwardAlpha.scenarios || [], scenarioRunCard);
  renderCards(els.forwardSources, forwardAlpha.source_candidates || [], forwardSourceCard);
  renderCards(els.sensorObservations, forwardAlpha.observations || [], sensorObservationCard);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function badges(items, extraClass = "") {
  return `<div class="badge-row">${(items || [])
    .filter(Boolean)
    .map((item) => `<span class="badge ${extraClass}">${escapeHtml(item)}</span>`)
    .join("")}</div>`;
}

function itemsForTask(bundle, key, taskId) {
  return (bundle[key] || []).filter((item) => item.task_id === taskId);
}

function latestRunForTask(bundle, taskId) {
  return itemsForTask(bundle, "runs", taskId).slice(-1)[0] || null;
}

function verdictForTask(bundle, taskId) {
  return itemsForTask(bundle, "verdicts", taskId).slice(-1)[0] || null;
}

function findingSummary(findings, type) {
  const items = findings.filter((item) => item.finding_type === type);
  if (!items.length) {
    return "暂无";
  }
  return items.map((item) => item.claim || item.raw_excerpt).slice(0, 2).join("；");
}

function verdictBadgeClass(verdict) {
  if (verdict === "claim_falsified" || verdict === "blocker_maintained") {
    return "warn";
  }
  if (verdict === "blocker_removed") {
    return "ok";
  }
  return "";
}

function topChangeCard(item) {
  return `<article class="card">
    <div class="card-head">
      <h3>#${escapeHtml(item.rank)} ${escapeHtml(item.title)}</h3>
      <span class="badge">${escapeHtml(item.source_rank)}</span>
    </div>
    <p>${escapeHtml(item.why_it_matters)}</p>
    <p><strong>动作：</strong>${escapeHtml(item.suggested_user_action)}</p>
    ${badges(item.not_actionable_because || [], "warn")}
  </article>`;
}

function thesisCard(item) {
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.stock_name)}：${escapeHtml(item.status_after)}</h3>
      <span class="badge">${escapeHtml(item.confidence_after)}</span>
    </div>
    <p>${escapeHtml(item.thesis_text)}</p>
    <p><strong>研究问题：</strong>${escapeHtml(item.research_question)}</p>
    ${badges(item.evidence_missing || [], "warn")}
  </article>`;
}

function riskCard(item) {
  const first = (item.bear_cases || [])[0] || {};
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.stock_name)}</h3>
      <span class="badge risk-${escapeHtml(item.risk_level)}">Q=${escapeHtml(item.risk_level)}</span>
    </div>
    <p>${escapeHtml(item.risk_summary)}</p>
    <p><strong>反方：</strong>${escapeHtml(first.claim || "暂无")}</p>
    <p><strong>缓解条件：</strong>${escapeHtml(first.what_would_reduce_this_risk || "等待更高等级证据")}</p>
  </article>`;
}

function validationCard(item) {
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.stock_name)}</h3>
      <span class="badge ok">${escapeHtml(item.validation_date)}</span>
    </div>
    <p>${escapeHtml(item.description)}</p>
    <p><strong>证伪：</strong>${escapeHtml(item.invalidates_if)}</p>
    ${badges(item.watch_fields || [])}
  </article>`;
}

function peerCard(item) {
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.theme)}：${escapeHtml(item.focus_stock_name)}</h3>
      <span class="badge">${escapeHtml(item.winner || "无赢家")}</span>
    </div>
    <p>${escapeHtml(item.winner_reason)}</p>
    ${badges(item.missing_data || [], "warn")}
  </article>`;
}

function signalCard(item) {
  const score = item.score_after || {};
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.stock_name)}：${escapeHtml(item.signal_type)}</h3>
      <span class="badge">${escapeHtml(item.signal_direction)}</span>
    </div>
    <p>${escapeHtml(item.suggested_action)}</p>
    ${badges([`R ${score.R}`, `O ${score.O}`, `T ${score.T}`, `Q ${score.Q}`])}
  </article>`;
}

function deepDiveTaskCard(item, bundle) {
  const run = latestRunForTask(bundle, item.task_id);
  const verdict = verdictForTask(bundle, item.task_id);
  const findings = itemsForTask(bundle, "findings", item.task_id);
  const budget = item.budget || {};
  const sourcesChecked = (run && run.sources_checked) || [];
  return `<article class="card deep-dive-card">
    <div class="card-head">
      <h3>${escapeHtml(item.question)}</h3>
      <span class="badge ${item.priority === "P0" ? "warn" : "ok"}">${escapeHtml(item.priority)}</span>
    </div>
    <p><strong>触发：</strong>${escapeHtml(item.trigger_reason)}</p>
    <p><strong>已查来源：</strong>${escapeHtml(sourcesChecked.length)} / ${escapeHtml(budget.max_sources || 5)}；${escapeHtml((run && run.stop_reason) || "预算内")}</p>
    <p><strong>支持证据：</strong>${escapeHtml(findingSummary(findings, "support"))}</p>
    <p><strong>反方证据：</strong>${escapeHtml(findingSummary(findings, "counter"))}</p>
    <p><strong>未知项：</strong>${escapeHtml(findingSummary(findings, "unknown"))}</p>
    <p><strong>阻断变化：</strong>${escapeHtml((verdict && verdict.summary) || "尚未运行")}</p>
    ${badges([item.trigger_type, `LLM ${budget.max_llm_calls || 2}`, `${budget.timeout_seconds || 120}s`])}
    <div class="decision-row">
      <button class="mini deep-dive-run" data-task-id="${escapeHtml(item.task_id)}">运行</button>
      <button class="mini ghost deep-dive-decision" data-action="confirm" data-task-id="${escapeHtml(item.task_id)}">确认</button>
      <button class="mini ghost deep-dive-decision" data-action="ignore" data-task-id="${escapeHtml(item.task_id)}">忽略</button>
      <button class="mini ghost deep-dive-decision" data-action="add_to_review" data-task-id="${escapeHtml(item.task_id)}">复盘</button>
    </div>
  </article>`;
}

function deepDiveVerdictCard(item, bundle) {
  const task = (bundle.tasks || []).find((candidate) => candidate.task_id === item.task_id) || {};
  const impact = item.score_impact || {};
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.verdict)}</h3>
      <span class="badge ${verdictBadgeClass(item.verdict)}">${escapeHtml(item.review_required ? "需复核" : "记录")}</span>
    </div>
    <p>${escapeHtml(task.question || item.task_id)}</p>
    <p><strong>结论：</strong>${escapeHtml(item.summary)}</p>
    <p><strong>状态影响：</strong>${escapeHtml(item.blocker_effect)}</p>
    ${badges([`X ${impact.X ?? 0}`, `I ${impact.I ?? 0}`, `U ${impact.U ?? 0}`])}
  </article>`;
}

function radarClaimCard(item, cross, report) {
  const score = item.scores || {};
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.stock_name)}：${escapeHtml(item.status)}</h3>
      <span class="badge ok">${escapeHtml(item.thesis_stage)}</span>
    </div>
    <p>${escapeHtml(item.claim_text)}</p>
    <p><strong>交叉验证：</strong>${escapeHtml((cross && cross.gate_status) || "unknown")}，独立来源 ${escapeHtml((cross && cross.support_count) || 0)} 组。</p>
    <p><strong>动作：</strong>${escapeHtml(item.suggested_action)}</p>
    ${badges([`E ${score.E}`, `X ${score.X}`, `I ${score.I}`, `U ${score.U}`, `D ${score.D}`])}
    ${badges(item.upgrade_blockers || [], "warn")}
    <div class="decision-row" data-report-id="${escapeHtml(report.report_id)}">
      <button class="mini claim-decision" data-action="confirm" data-claim-id="${escapeHtml(item.claim_id)}">确认</button>
      <button class="mini ghost claim-decision" data-action="ignore" data-claim-id="${escapeHtml(item.claim_id)}">忽略</button>
      <button class="mini ghost claim-decision" data-action="add_to_review" data-claim-id="${escapeHtml(item.claim_id)}">复盘</button>
    </div>
  </article>`;
}

function revisionCard(item) {
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.previous_status)} → ${escapeHtml(item.new_status)}</h3>
      <span class="badge">${escapeHtml(item.claim_id)}</span>
    </div>
    <p>${escapeHtml(item.reason)}</p>
    ${badges(item.changes || [])}
  </article>`;
}

function blockerCard(item) {
  return `<article class="card">
    <div class="card-head">
      <h3>升级阻断</h3>
      <span class="badge warn">Review</span>
    </div>
    <p>${escapeHtml(item)}</p>
  </article>`;
}

function bearCard(item) {
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.risk_type)}</h3>
      <span class="badge risk-${item.severity === "high" ? "C" : "B"}">${escapeHtml(item.severity)}</span>
    </div>
    <p>${escapeHtml(item.claim)}</p>
    <p><strong>缓解：</strong>${escapeHtml(item.what_would_reduce_this_risk)}</p>
  </article>`;
}

function radarTaskCard(item) {
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.task_type)}</h3>
      <span class="badge ok">${escapeHtml(item.due_date)}</span>
    </div>
    <p>${escapeHtml(item.question)}</p>
    <p><strong>成功：</strong>${escapeHtml(item.success_criteria)}</p>
    <p><strong>失败：</strong>${escapeHtml(item.failure_criteria)}</p>
    ${badges([item.priority, item.target_source_family])}
  </article>`;
}

function sourceProfileCard(item) {
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.source_name)}</h3>
      <span class="badge">${escapeHtml(item.source_rank)} / ${escapeHtml(item.credibility_score)}</span>
    </div>
    <p>${escapeHtml(item.source_family)} · ${escapeHtml(item.independence_group)}</p>
    ${badges([...(item.known_biases || []), ...(item.conflict_flags || [])], "warn")}
  </article>`;
}

function forwardSourceCard(item) {
  const statusClass = item.collection_status === "auto_collectable" ? "ok" : item.collection_status === "blocked" ? "warn" : "";
  return `<article class="card forward-card">
    <div class="card-head">
      <h3>${escapeHtml(item.source_name)}</h3>
      <span class="badge ${statusClass}">${escapeHtml(item.collection_status)}</span>
    </div>
    <p>${escapeHtml(item.reason)}</p>
    <p><strong>授权：</strong>${escapeHtml(item.license_status)} · ${escapeHtml(item.access_mode)} · ${escapeHtml(item.cost_class)}</p>
    ${badges([item.theme, item.sensor_type, item.source_family, item.source_rank])}
    <div class="decision-row">
      <button class="mini ghost source-decision" data-action="approve_manual" data-source-id="${escapeHtml(item.source_id)}">人工</button>
      <button class="mini ghost source-decision" data-action="mark_authorized" data-source-id="${escapeHtml(item.source_id)}">授权</button>
      <button class="mini ghost source-decision" data-action="block" data-source-id="${escapeHtml(item.source_id)}">阻断</button>
    </div>
  </article>`;
}

function manualImportCard(item) {
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.source_name)}</h3>
      <span class="badge warn">${escapeHtml(item.status || "pending")}</span>
    </div>
    <p>${escapeHtml(item.requested_input)}</p>
    <p><strong>原因：</strong>${escapeHtml(item.reason)}</p>
    ${badges([item.theme])}
    <div class="decision-row">
      <button class="mini manual-import" data-task-id="${escapeHtml(item.task_id)}">录入</button>
    </div>
  </article>`;
}

function sensorObservationCard(item) {
  const badgeClass = item.direction === "negative" ? "warn" : item.direction === "positive" || item.direction === "support" ? "ok" : "";
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.metric)}</h3>
      <span class="badge ${badgeClass}">${escapeHtml(item.direction)} / ${escapeHtml(item.signal_strength)}</span>
    </div>
    <p>${escapeHtml(item.value)}</p>
    <p>${escapeHtml(item.raw_excerpt)}</p>
    ${badges([item.theme, item.sensor_type, item.source_family, item.source_rank])}
  </article>`;
}

function sensorComparisonCard(item) {
  const badgeClass = item.requires_deep_dive ? "warn" : item.result_state === "cross_source_converging" ? "ok" : "";
  return `<article class="card forward-card">
    <div class="card-head">
      <h3>${escapeHtml(item.metric)}</h3>
      <span class="badge ${badgeClass}">${escapeHtml(item.result_state)}</span>
    </div>
    <p>${escapeHtml(item.summary)}</p>
    ${badges([`支持 ${item.support_count}`, `反证 ${item.contradiction_count}`, `Δ ${item.forward_score_delta}`])}
  </article>`;
}

function transmissionHypothesisCard(item) {
  const impact = item.score_impact || {};
  return `<article class="card">
    <div class="card-head">
      <h3>${escapeHtml(item.theme)}</h3>
      <span class="badge">${escapeHtml(item.confidence)}</span>
    </div>
    <p>${escapeHtml(item.hypothesis)}</p>
    <p><strong>证伪：</strong>${escapeHtml((item.invalidating_conditions || []).join("；"))}</p>
    ${badges([`E ${impact.E ?? 0}`, `X ${impact.X ?? 0}`, `I ${impact.I ?? 0}`, `U ${impact.U ?? 0}`])}
  </article>`;
}

function scenarioRunCard(item) {
  const base = item.base_case || {};
  const upside = item.upside_case || {};
  const downside = item.downside_case || {};
  return `<article class="card">
    <div class="card-head">
      <h3>三情景</h3>
      <span class="badge">非交易建议</span>
    </div>
    <p><strong>中性：</strong>收入 ${escapeHtml(base.revenue_growth_pct)}%，毛利变化 ${escapeHtml(base.gross_margin_change_pct)}%</p>
    <p><strong>乐观：</strong>收入 ${escapeHtml(upside.revenue_growth_pct)}%，毛利变化 ${escapeHtml(upside.gross_margin_change_pct)}%</p>
    <p><strong>保守：</strong>收入 ${escapeHtml(downside.revenue_growth_pct)}%，毛利变化 ${escapeHtml(downside.gross_margin_change_pct)}%</p>
    ${badges(item.key_variables || [])}
  </article>`;
}

function mergeDeepDiveBundles(base, incoming) {
  const merged = normalizeDeepDiveBundle(base);
  const next = normalizeDeepDiveBundle(incoming);
  const specs = {
    tasks: "task_id",
    runs: "run_id",
    findings: "finding_id",
    verdicts: "task_id",
    decisions: "decided_at",
  };
  Object.entries(specs).forEach(([key, idKey]) => {
    const byId = Object.fromEntries((merged[key] || []).filter((item) => item[idKey]).map((item) => [item[idKey], item]));
    const noId = (merged[key] || []).filter((item) => !item[idKey]);
    (next[key] || []).forEach((item) => {
      if (item[idKey]) {
        byId[item[idKey]] = item;
      } else {
        noId.push(item);
      }
    });
    merged[key] = [...Object.values(byId), ...noId];
  });
  return merged;
}

els.loadSampleBtn.addEventListener("click", loadSample);
els.loadRadarSampleBtn.addEventListener("click", loadRadarSample);
els.analyzeBtn.addEventListener("click", analyze);
els.runForwardAlphaBtn.addEventListener("click", runForwardAlpha);
document.addEventListener("click", handleClaimDecisionClick);
document.addEventListener("click", handleDeepDiveClick);
document.addEventListener("click", handleForwardAlphaClick);
loadRadarSample().catch(() => loadSample().catch(() => setStatus("样例载入失败")));

async function handleClaimDecisionClick(event) {
  const button = event.target.closest(".claim-decision");
  if (!button) {
    return;
  }
  const claimId = button.dataset.claimId;
  const action = button.dataset.action;
  const claim = (lastRadarReport && (lastRadarReport.claims || []).find((item) => item.claim_id === claimId)) || {};
  const label = { confirm: "确认", ignore: "忽略", add_to_review: "加入复盘" }[action] || action;
  const defaultReason = `${label}：${claim.status || "manual_review"}`;
  const reason = window.prompt("记录一句处理理由", defaultReason);
  if (reason === null) {
    return;
  }
  button.disabled = true;
  try {
    await fetchJson(`/api/radar/claims/${encodeURIComponent(claimId)}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision: action,
        reason,
        report_id: lastRadarReport ? lastRadarReport.report_id : "",
        stock_code: lastRadarReport ? lastRadarReport.stock_code : "",
        stock_name: lastRadarReport ? lastRadarReport.stock_name : "",
        next_action: claim.suggested_action || "",
      }),
    });
    setStatus(`已记录：${label}`);
  } catch (error) {
    setStatus(error.message);
  } finally {
    button.disabled = false;
  }
}

async function handleDeepDiveClick(event) {
  const runButton = event.target.closest(".deep-dive-run");
  if (runButton) {
    await runDeepDiveTask(runButton);
    return;
  }
  const decisionButton = event.target.closest(".deep-dive-decision");
  if (decisionButton) {
    await recordDeepDiveDecision(decisionButton);
  }
}

async function runDeepDiveTask(button) {
  const taskId = button.dataset.taskId;
  button.disabled = true;
  setStatus("深挖中...");
  try {
    const result = await fetchJson(`/api/radar/deep-dives/${encodeURIComponent(taskId)}/run`, { method: "POST" });
    lastDeepDiveBundle = mergeDeepDiveBundles(lastDeepDiveBundle, result.deep_dives || {});
    if (lastRadarPayload) {
      lastRadarPayload.deep_dives = lastDeepDiveBundle;
      renderRadarReport(lastRadarPayload);
    }
    setStatus("深挖已完成");
  } catch (error) {
    setStatus(error.message);
  } finally {
    button.disabled = false;
  }
}

async function recordDeepDiveDecision(button) {
  const taskId = button.dataset.taskId;
  const action = button.dataset.action;
  const task = (lastDeepDiveBundle.tasks || []).find((item) => item.task_id === taskId) || {};
  const label = { confirm: "确认", ignore: "忽略", add_to_review: "加入复盘" }[action] || action;
  const reason = window.prompt("记录一句处理理由", `${label}：${task.trigger_type || "deep_dive"}`);
  if (reason === null) {
    return;
  }
  button.disabled = true;
  try {
    const result = await fetchJson(`/api/radar/deep-dives/${encodeURIComponent(taskId)}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision: action,
        reason,
        next_action: task.trigger_reason || "",
      }),
    });
    lastDeepDiveBundle = mergeDeepDiveBundles(lastDeepDiveBundle, { decisions: [result.decision] });
    setStatus(`已记录深挖处理：${label}`);
  } catch (error) {
    setStatus(error.message);
  } finally {
    button.disabled = false;
  }
}

async function runForwardAlpha() {
  if (!lastRadarPayload) {
    setStatus("请先生成早期雷达报告");
    return;
  }
  els.runForwardAlphaBtn.disabled = true;
  setStatus("前瞻探索中...");
  try {
    const result = await fetchJson("/api/radar/forward-alpha/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ radar: lastRadarPayload.input || lastRadarPayload, use_llm: els.useLlm.checked }),
    });
    lastForwardAlpha = normalizeForwardAlpha(result.forward_alpha || {});
    if (lastRadarPayload) {
      lastRadarPayload.forward_alpha = lastForwardAlpha;
      lastDeepDiveBundle = mergeDeepDiveBundles(lastDeepDiveBundle, result.deep_dives || {});
      lastRadarPayload.deep_dives = lastDeepDiveBundle;
      renderRadarReport(lastRadarPayload);
    }
    setStatus("前瞻探索已完成");
  } catch (error) {
    setStatus(error.message);
  } finally {
    els.runForwardAlphaBtn.disabled = false;
  }
}

async function handleForwardAlphaClick(event) {
  const sourceButton = event.target.closest(".source-decision");
  if (sourceButton) {
    await recordSourceDecision(sourceButton);
    return;
  }
  const importButton = event.target.closest(".manual-import");
  if (importButton) {
    await recordManualImport(importButton);
  }
}

async function recordSourceDecision(button) {
  const sourceId = button.dataset.sourceId;
  const action = button.dataset.action;
  const source = (lastForwardAlpha && (lastForwardAlpha.source_candidates || []).find((item) => item.source_id === sourceId)) || {};
  const label = { approve_manual: "人工导入", mark_authorized: "授权采集", block: "阻断来源" }[action] || action;
  const reason = window.prompt("记录一句处理理由", `${label}：${source.source_name || "source"}`);
  if (reason === null) {
    return;
  }
  button.disabled = true;
  try {
    await fetchJson(`/api/radar/forward-alpha/source-decisions/${encodeURIComponent(sourceId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision: action, reason }),
    });
    setStatus(`已记录信源决策：${label}`);
  } catch (error) {
    setStatus(error.message);
  } finally {
    button.disabled = false;
  }
}

async function recordManualImport(button) {
  const taskId = button.dataset.taskId;
  const task = (lastForwardAlpha && (lastForwardAlpha.manual_import_tasks || []).find((item) => item.task_id === taskId)) || {};
  const raw = window.prompt("录入短证据", task.requested_input || "录入来源短摘录");
  if (raw === null) {
    return;
  }
  button.disabled = true;
  try {
    await fetchJson(`/api/radar/forward-alpha/manual-imports/${encodeURIComponent(taskId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_excerpt: raw }),
    });
    setStatus("已记录人工导入");
  } catch (error) {
    setStatus(error.message);
  } finally {
    button.disabled = false;
  }
}

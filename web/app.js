const els = {
  holdingsInput: document.querySelector("#holdingsInput"),
  loadSampleBtn: document.querySelector("#loadSampleBtn"),
  loadRadarSampleBtn: document.querySelector("#loadRadarSampleBtn"),
  analyzeBtn: document.querySelector("#analyzeBtn"),
  useLlm: document.querySelector("#useLlm"),
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
  radarClaims: document.querySelector("#radarClaims"),
  claimRevisions: document.querySelector("#claimRevisions"),
  upgradeBlockers: document.querySelector("#upgradeBlockers"),
  bearCases: document.querySelector("#bearCases"),
  radarTasks: document.querySelector("#radarTasks"),
  sourceProfiles: document.querySelector("#sourceProfiles"),
};

let currentMode = "holdings";

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
  els.metricFourLabel.textContent = isRadar ? "验证任务" : "验证点";
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
      setStatus("早期雷达报告已生成");
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
  els.topChangeCount.textContent = (report.claims || []).length;
  els.riskCount.textContent = (report.bear_cases || []).length;
  els.thesisCount.textContent = (report.cross_validation || []).length;
  els.validationCount.textContent = (report.validation_tasks || []).length;
  els.radarState.textContent = report.radar_state || "unknown";
  els.radarSummary.textContent = report.summary || "暂无摘要";
  els.radarLlmStatus.textContent = `LLM: ${(payload.llm && payload.llm.status) || report.llm_status || "unknown"}`;

  const crossByClaim = Object.fromEntries((report.cross_validation || []).map((item) => [item.claim_id, item]));
  renderCards(els.radarClaims, report.claims || [], (item) => radarClaimCard(item, crossByClaim[item.claim_id]));
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

function radarClaimCard(item, cross) {
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

els.loadSampleBtn.addEventListener("click", loadSample);
els.loadRadarSampleBtn.addEventListener("click", loadRadarSample);
els.analyzeBtn.addEventListener("click", analyze);
loadRadarSample().catch(() => loadSample().catch(() => setStatus("样例载入失败")));

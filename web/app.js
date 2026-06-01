const els = {
  holdingsInput: document.querySelector("#holdingsInput"),
  loadSampleBtn: document.querySelector("#loadSampleBtn"),
  analyzeBtn: document.querySelector("#analyzeBtn"),
  useLlm: document.querySelector("#useLlm"),
  statusText: document.querySelector("#statusText"),
  topChangeCount: document.querySelector("#topChangeCount"),
  riskCount: document.querySelector("#riskCount"),
  thesisCount: document.querySelector("#thesisCount"),
  validationCount: document.querySelector("#validationCount"),
  llmStatus: document.querySelector("#llmStatus"),
  topChanges: document.querySelector("#topChanges"),
  thesisChecks: document.querySelector("#thesisChecks"),
  riskRadar: document.querySelector("#riskRadar"),
  validationPoints: document.querySelector("#validationPoints"),
  peerComparisons: document.querySelector("#peerComparisons"),
  signals: document.querySelector("#signals"),
};

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

async function loadSample() {
  const sample = await fetchJson("/api/sample-holdings");
  els.holdingsInput.value = JSON.stringify(sample, null, 2);
  setStatus("样例已载入");
}

async function analyze() {
  let holdings;
  try {
    holdings = JSON.parse(els.holdingsInput.value || "[]");
  } catch (error) {
    setStatus("JSON 格式不正确");
    return;
  }
  if (!Array.isArray(holdings) || holdings.length === 0) {
    setStatus("请提供至少一只持仓");
    return;
  }
  setStatus("分析中...");
  els.analyzeBtn.disabled = true;
  try {
    const report = await fetchJson("/api/holdings/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ holdings, use_llm: els.useLlm.checked }),
    });
    renderReport(report);
    setStatus("报告已生成");
  } catch (error) {
    setStatus(error.message);
  } finally {
    els.analyzeBtn.disabled = false;
  }
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
  return `<div class="badge-row">${items
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

els.loadSampleBtn.addEventListener("click", loadSample);
els.analyzeBtn.addEventListener("click", analyze);
loadSample().catch(() => setStatus("样例载入失败"));

const state = {
  view: "today",
  polling: null,
};

const el = {
  total: document.getElementById("stat-total"),
  avg: document.getElementById("stat-avg"),
  best: document.getElementById("stat-best"),
  countToday: document.getElementById("count-today"),
  countTomorrow: document.getElementById("count-tomorrow"),
  countSourcesLoaded: document.getElementById("count-sources-loaded"),
  empty: document.getElementById("empty-state"),
  emptyMsg: document.getElementById("empty-message"),
  list: document.getElementById("opp-list"),
  panelOpportunities: document.getElementById("panel-opportunities"),
  panelSources: document.getElementById("panel-sources"),
  sourcesEmpty: document.getElementById("sources-empty"),
  sourceList: document.getElementById("source-list"),
  error: document.getElementById("error-banner"),
  lastRun: document.getElementById("last-run"),
  refreshBtn: document.getElementById("btn-refresh"),
  refreshLabel: document.getElementById("btn-refresh-label"),
  tabs: document.querySelectorAll(".tab"),
  slipDialog: document.getElementById("slip-dialog"),
  slipTitle: document.getElementById("slip-title"),
  slipYield: document.getElementById("slip-yield"),
  slipLegs: document.getElementById("slip-legs"),
  slipClose: document.getElementById("slip-close"),
};

function formatPct(n) {
  return `${Number(n).toFixed(2)}%`;
}

function formatLastRun(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return `Last run: ${d.toLocaleString()}`;
  } catch {
    return "";
  }
}

function setLoading(loading) {
  el.refreshBtn.disabled = loading;
  el.refreshBtn.classList.toggle("loading", loading);
  el.refreshLabel.textContent = loading ? "Running…" : "Refresh run";
}

function statusPillClass(status) {
  const map = {
    loaded: "status-pill--loaded",
    empty: "status-pill--empty",
    error: "status-pill--error",
    stub: "status-pill--stub",
  };
  return map[status] || "status-pill--empty";
}

function channelLabel(channel) {
  if (channel === "gateway") return "Data gateway";
  if (channel === "direct") return "Direct adapter";
  return "Via Odds API";
}

function renderOpportunities(opportunities) {
  el.list.innerHTML = "";
  if (!opportunities.length) {
    el.empty.classList.remove("hidden");
    el.list.classList.add("hidden");
    const label = state.view === "today" ? "today" : "tomorrow";
    el.emptyMsg.textContent = `No opportunities for ${label}.`;
    return;
  }

  el.empty.classList.add("hidden");
  el.list.classList.remove("hidden");

  opportunities.forEach((opp) => {
    const row = document.createElement("div");
    row.className = "opp-row";
    row.innerHTML = `
      <div>
        <div class="opp-event">${escapeHtml(opp.event_name)}</div>
        <div class="opp-meta">${escapeHtml(opp.sport_key)} · ${formatCommence(opp.commence_time)}</div>
      </div>
      <span class="opp-market">${escapeHtml(opp.market_type)}</span>
      <span class="opp-yield">${formatPct(opp.yield_pct)}</span>
    `;
    row.addEventListener("click", () => openSlip(opp));
    el.list.appendChild(row);
  });
}

function renderSources(sources) {
  el.sourceList.innerHTML = "";
  if (!sources || !sources.length) {
    el.sourcesEmpty.classList.remove("hidden");
    el.sourceList.classList.add("hidden");
    return;
  }

  el.sourcesEmpty.classList.add("hidden");
  el.sourceList.classList.remove("hidden");

  sources.forEach((src) => {
    const row = document.createElement("div");
    row.className = "source-row";
    const pillClass = statusPillClass(src.status);
    row.innerHTML = `
      <div>
        <div class="source-name">${escapeHtml(src.name)}</div>
        <div class="source-channel">${escapeHtml(channelLabel(src.channel))}</div>
        <div class="source-message">${escapeHtml(src.message)}</div>
      </div>
      <span class="status-pill ${pillClass}">${escapeHtml(src.status_label)}</span>
    `;
    el.sourceList.appendChild(row);
  });
}

function updatePanels() {
  const isSources = state.view === "sources";
  el.panelOpportunities.classList.toggle("hidden", isSources);
  el.panelSources.classList.toggle("hidden", !isSources);
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

function formatCommence(iso) {
  if (!iso) return "Time TBD";
  try {
    return new Date(iso).toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function openSlip(opp) {
  el.slipTitle.textContent = opp.event_name;
  el.slipYield.textContent = `Profit: ${formatPct(opp.yield_pct)}`;
  el.slipLegs.innerHTML = "";
  (opp.legs || []).forEach((leg) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <strong>${escapeHtml(leg.outcome)}</strong>
      <span class="leg-detail">${escapeHtml(leg.source)} · ${leg.price.toFixed(2)} decimal · stake ${(leg.stake_weight * 100).toFixed(1)}%</span>
    `;
    el.slipLegs.appendChild(li);
  });
  el.slipDialog.showModal();
}

function applyPayload(data) {
  const stats = data.stats || {};
  el.total.textContent = String(stats.total_opportunities ?? 0);
  el.avg.textContent = formatPct(stats.avg_profit_pct ?? 0);
  el.best.textContent = formatPct(stats.best_available_pct ?? 0);

  const counts = data.counts || {};
  el.countToday.textContent = String(counts.today ?? 0);
  el.countTomorrow.textContent = String(counts.tomorrow ?? 0);

  const summary = data.source_summary || {};
  el.countSourcesLoaded.textContent = String(summary.loaded ?? 0);

  el.lastRun.textContent = formatLastRun(data.last_run_at);

  if (data.error && state.view !== "sources") {
    el.error.textContent = data.error;
    el.error.classList.remove("hidden");
  } else if (!data.api_key_configured) {
    el.error.textContent = "ODDS_API_KEY is not set in harvester/.env";
    el.error.classList.remove("hidden");
  } else {
    el.error.classList.add("hidden");
  }

  if (state.view === "today" || state.view === "tomorrow") {
    renderOpportunities(data.opportunities || []);
  }

  renderSources(data.sources || []);
  updatePanels();
  setLoading(Boolean(data.running));
}

async function fetchStatus() {
  const day = state.view === "tomorrow" ? "tomorrow" : "today";
  const res = await fetch(`/api/status?day=${day}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function triggerRun() {
  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function startPolling() {
  stopPolling();
  state.polling = setInterval(async () => {
    try {
      const data = await fetchStatus();
      applyPayload(data);
      if (!data.running) stopPolling();
    } catch (e) {
      console.error(e);
      stopPolling();
      setLoading(false);
    }
  }, 2000);
}

function stopPolling() {
  if (state.polling) {
    clearInterval(state.polling);
    state.polling = null;
  }
}

async function onRefresh() {
  try {
    setLoading(true);
    await triggerRun();
    startPolling();
    const data = await fetchStatus();
    applyPayload(data);
  } catch (e) {
    el.error.textContent = e.message || String(e);
    el.error.classList.remove("hidden");
    setLoading(false);
  }
}

el.tabs.forEach((tab) => {
  tab.addEventListener("click", async () => {
    state.view = tab.dataset.view;
    el.tabs.forEach((t) => {
      const active = t === tab;
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
    updatePanels();
    try {
      const data = await fetchStatus();
      applyPayload(data);
    } catch (e) {
      console.error(e);
    }
  });
});

el.refreshBtn.addEventListener("click", onRefresh);
el.slipClose.addEventListener("click", () => el.slipDialog.close());

(async function init() {
  updatePanels();
  try {
    const data = await fetchStatus();
    applyPayload(data);
    if (data.running) startPolling();
  } catch (e) {
    el.error.textContent = "Could not load dashboard. Is the server running?";
    el.error.classList.remove("hidden");
  }
})();

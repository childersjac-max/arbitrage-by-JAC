const state = {
  view: "today",
  polling: null,
  pollStartedAt: 0,
  maxPollMs: 12 * 60 * 1000,
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

function setLoading(loading, statusText) {
  el.refreshBtn.disabled = loading;
  el.refreshBtn.classList.toggle("loading", loading);
  if (loading && statusText) {
    el.refreshLabel.textContent = statusText.length > 42 ? "Running…" : statusText;
    el.refreshBtn.title = statusText;
  } else {
    el.refreshLabel.textContent = loading ? "Running…" : "Refresh run";
    el.refreshBtn.title = loading ? "Pipeline in progress" : "Fetch odds and scan for arbitrage";
  }
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
    const method = opp.arb_method ? ` · ${opp.arb_method}` : "";
    row.innerHTML = `
      <div>
        <div class="opp-event">${escapeHtml(opp.event_name)}</div>
        <div class="opp-meta">${escapeHtml(opp.sport_key)} · ${formatCommence(opp.commence_time)}${escapeHtml(method)}</div>
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

  let lastCategory = "";
  sources.forEach((src) => {
    const catLabel = src.category_label || "";
    if (catLabel && catLabel !== lastCategory && src.category !== "gateway") {
      lastCategory = catLabel;
      const heading = document.createElement("div");
      heading.className = "source-category";
      heading.textContent = catLabel;
      el.sourceList.appendChild(heading);
    } else if (src.category === "gateway" && catLabel !== lastCategory) {
      lastCategory = catLabel;
    }

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
  let yieldLine = `Profit: ${formatPct(opp.yield_pct)}`;
  if (opp.arb_method) yieldLine += ` (${opp.arb_method})`;
  el.slipYield.textContent = yieldLine;
  if (opp.llm_reasoning) {
    const note = document.createElement("p");
    note.className = "slip-note";
    note.textContent = opp.llm_reasoning;
    el.slipYield.after(note);
  }
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
  const statusText = data.run_status || (data.running ? "Running pipeline…" : "");
  setLoading(Boolean(data.running), statusText);

  if (data.running && data.run_status) {
    el.error.classList.add("hidden");
  }
}

async function fetchStatus() {
  const day = state.view === "tomorrow" ? "tomorrow" : "today";
  const res = await fetch(`/api/status?day=${day}`);
  const text = await res.text();
  if (!res.ok) {
    throw new Error(text || res.statusText);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error("Invalid response from server");
  }
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

async function forceResetRun() {
  try {
    await fetch("/api/reset-run", { method: "POST" });
  } catch {
    /* ignore */
  }
}

function startPolling() {
  stopPolling();
  state.pollStartedAt = Date.now();
  state.polling = setInterval(async () => {
    if (Date.now() - state.pollStartedAt > state.maxPollMs) {
      stopPolling();
      await forceResetRun();
      setLoading(false);
      el.error.textContent =
        "Run took too long and was stopped. Try turning off LLM in harvester/.env " +
        "(HARVESTER_USE_LLM_ARBITRAGE=false) or ensure Ollama is running.";
      el.error.classList.remove("hidden");
      return;
    }
    try {
      const data = await fetchStatus();
      applyPayload(data);
      if (!data.running) {
        stopPolling();
        if (data.error) {
          el.error.textContent = data.error;
          el.error.classList.remove("hidden");
        }
      }
    } catch (e) {
      console.error(e);
      stopPolling();
      setLoading(false);
      el.error.textContent =
        "Could not reach server during run. Restart web_app.py and try again. " +
        (e.message || String(e));
      el.error.classList.remove("hidden");
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

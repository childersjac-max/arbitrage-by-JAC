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
  portfolioPanel: document.getElementById("portfolio-panel"),
  portfolioProfit: document.getElementById("portfolio-profit"),
  portfolioDeployed: document.getElementById("portfolio-deployed"),
  portfolioSelected: document.getElementById("portfolio-selected"),
  portfolioBalance: document.getElementById("portfolio-balance"),
  portfolioBooks: document.getElementById("portfolio-books"),
  portfolioSub: document.getElementById("portfolio-sub"),
  potentialPlayCard: document.getElementById("potential-play-card"),
  potentialPlayTitle: document.getElementById("potential-play-title"),
  potentialPlayMeta: document.getElementById("potential-play-meta"),
  potentialPlayProfit: document.getElementById("potential-play-profit"),
  potentialPlayCurrent: document.getElementById("potential-play-current"),
  potentialPlayUplift: document.getElementById("potential-play-uplift"),
  potentialPlayStake: document.getElementById("potential-play-stake"),
  potentialPlayFundList: document.getElementById("potential-play-fund-list"),
};

function formatPct(n) {
  return `${Number(n).toFixed(2)}%`;
}

function formatMoney(n) {
  return `$${Number(n || 0).toFixed(2)}`;
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

function renderScannedEvents(events, summary) {
  el.list.innerHTML = "";
  if (!events.length) {
    el.empty.classList.remove("hidden");
    el.list.classList.add("hidden");
    const label = state.view === "today" ? "today" : "tomorrow";
    if (summary && summary.events_total > 0) {
      el.emptyMsg.textContent = `No games scheduled for ${label} in this sport.`;
      el.empty.querySelector(".empty-hint").textContent =
        `Scanned ${summary.events_total} total event(s) · ${summary.sources_loaded} source(s) loaded. Try Tomorrow tab.`;
    } else {
      el.emptyMsg.textContent = `No data for ${label}.`;
    }
    return;
  }

  el.empty.classList.add("hidden");
  el.list.classList.remove("hidden");

  events.forEach((ev) => {
    const row = document.createElement("div");
    row.className = ev.is_opportunity ? "opp-row" : "opp-row opp-row--scan";
    let right = "";
    if (ev.is_opportunity) {
      right = `<span class="opp-yield">${formatPct(ev.yield_pct)}</span>`;
    } else if (ev.overround_pct != null) {
      right = `<span class="opp-market">+${ev.overround_pct.toFixed(2)}% vig</span>`;
    } else {
      right = `<span class="opp-market">No arb</span>`;
    }
    row.innerHTML = `
      <div>
        <div class="opp-event">${escapeHtml(ev.event_name)}</div>
        <div class="opp-meta">${escapeHtml(ev.sport_key)} · ${formatCommence(ev.commence_time)} · ${ev.books_count} books</div>
      </div>
      <span class="opp-market">${escapeHtml(ev.market_type)}</span>
      ${right}
    `;
    if (ev.is_opportunity && ev.legs && ev.legs.length) {
      row.addEventListener("click", () => openSlip(ev));
      row.style.cursor = "pointer";
    }
    el.list.appendChild(row);
  });
}

function renderPotentialPlay(play, opportunities) {
  if (!el.potentialPlayCard) return;
  if (!play) {
    el.potentialPlayCard.classList.add("hidden");
    return;
  }
  el.potentialPlayCard.classList.remove("hidden");
  el.potentialPlayTitle.textContent = play.event_name || "—";
  el.potentialPlayMeta.textContent =
    `${play.sport_key || ""} · ${play.market_type || ""} · ${formatPct(play.roi_pct)} ROI`;
  el.potentialPlayProfit.textContent = formatMoney(play.potential_profit_usd);
  el.potentialPlayCurrent.textContent = formatMoney(play.current_profit_usd);
  el.potentialPlayUplift.textContent = `+${formatMoney(play.profit_uplift_usd)}`;
  el.potentialPlayStake.textContent = formatMoney(play.max_stake_usd);

  el.potentialPlayFundList.innerHTML = "";
  const needs = (play.fund_targets || []).filter((t) => t.delta_usd > 0);
  const sources = play.funding_sources || [];

  if (!needs.length) {
    const li = document.createElement("li");
    li.textContent = "Balances already aligned — you can deploy without moving funds.";
    el.potentialPlayFundList.appendChild(li);
  } else {
    needs.forEach((target) => {
      const li = document.createElement("li");
      const name = target.book_name || target.book;
      li.innerHTML = `<strong>${escapeHtml(name)}</strong>: add ${formatMoney(target.delta_usd)} ` +
        `(have ${formatMoney(target.current_usd)}, need ${formatMoney(target.required_usd)})`;
      el.potentialPlayFundList.appendChild(li);
    });
    if (sources.length) {
      const li = document.createElement("li");
      li.className = "potential-play-fund-source";
      const names = sources
        .slice(0, 4)
        .map((s) => `${s.book_name || s.book} (${formatMoney(s.available_usd)})`)
        .join(", ");
      li.textContent = `Fund from: ${names}`;
      el.potentialPlayFundList.appendChild(li);
    }
  }

  el.potentialPlayCard.onclick = () => {
    const match = (opportunities || []).find((o) => o.id === play.opportunity_id);
    if (match) openSlip(match);
  };
}

function renderPortfolio(portfolio, balances) {
  if (!el.portfolioPanel) return;
  if (!portfolio && !balances) {
    el.portfolioPanel.classList.add("hidden");
    return;
  }
  el.portfolioPanel.classList.remove("hidden");
  if (!portfolio) return;

  el.portfolioProfit.textContent = formatMoney(portfolio.total_expected_profit_usd);
  el.portfolioDeployed.textContent = formatMoney(portfolio.total_deployed_usd);
  el.portfolioSelected.textContent = String(portfolio.opportunities_selected ?? 0);
  el.portfolioBalance.textContent = formatMoney(balances?.total_usd ?? 0);

  const skipped = portfolio.opportunities_skipped ?? 0;
  const hasPortfolio = portfolio.opportunities_selected > 0 || portfolio.total_deployed_usd > 0;
  el.portfolioSub.textContent =
    hasPortfolio
      ? `Greedy optimizer · ${portfolio.opportunities_selected} selected · ${skipped} skipped`
      : "No executable arbs at current balances — adjust balances or wait for new opportunities";

  el.portfolioBooks.innerHTML = "";
  const util = portfolio.book_utilization || {};
  (balances?.books || []).forEach((book) => {
    if (!book.available && !util[book.key]) return;
    const chip = document.createElement("div");
    chip.className = "portfolio-book-chip";
    const usedPct = ((util[book.key] || 0) * 100).toFixed(0);
    chip.innerHTML = `
      <span class="portfolio-book-name">${escapeHtml(book.name)}</span>
      <span class="portfolio-book-bal">${formatMoney(book.balance_usd)}</span>
      <span class="portfolio-book-util">${usedPct}% used</span>
    `;
    el.portfolioBooks.appendChild(chip);
  });
}

function renderOpportunities(opportunities, scannedEvents, summary) {
  if (opportunities.length) {
    el.list.innerHTML = "";
    el.empty.classList.add("hidden");
    el.list.classList.remove("hidden");
    opportunities.forEach((opp) => {
      const row = document.createElement("div");
      row.className = "opp-row";
      if (opp.is_best_potential) row.classList.add("opp-row--potential");
      const method = opp.arb_method ? ` · ${opp.arb_method}` : "";
      const alloc = opp.allocation || {};
      let allocLine = "";
      if (alloc.selected) {
        allocLine = `<div class="opp-alloc">+${formatMoney(alloc.expected_profit_usd)} @ ${formatMoney(alloc.total_stake_usd)} · limit: ${escapeHtml(alloc.limiting_book || "—")}</div>`;
      } else if (opp.is_best_potential && alloc.potential_profit_usd) {
        allocLine = `<div class="opp-alloc opp-alloc--potential">Potential ${formatMoney(alloc.potential_profit_usd)} if rebalanced (+${formatMoney(alloc.profit_uplift_usd || 0)})</div>`;
      } else if (alloc.limiting_book) {
        allocLine = `<div class="opp-alloc opp-alloc--skip">Skipped · limit: ${escapeHtml(alloc.limiting_book)}</div>`;
      }
      row.innerHTML = `
        <div>
          <div class="opp-event">${escapeHtml(opp.event_name)}</div>
          <div class="opp-meta">${escapeHtml(opp.sport_key)} · ${formatCommence(opp.commence_time)}${escapeHtml(method)}</div>
          ${allocLine}
        </div>
        <span class="opp-market">${escapeHtml(opp.market_type)}</span>
        <span class="opp-yield">${formatPct(opp.yield_pct)}</span>
      `;
      row.addEventListener("click", () => openSlip(opp));
      el.list.appendChild(row);
    });
    return;
  }
  renderScannedEvents(scannedEvents || [], summary);
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
  const alloc = opp.allocation || {};
  let yieldLine = `ROI: ${formatPct(opp.yield_pct)}`;
  if (alloc.selected) {
    yieldLine += ` · Profit ${formatMoney(alloc.expected_profit_usd)} on ${formatMoney(alloc.total_stake_usd)}`;
  }
  if (opp.arb_method) yieldLine += ` (${opp.arb_method})`;
  el.slipYield.textContent = yieldLine;
  el.slipLegs.innerHTML = "";
  (opp.legs || []).forEach((leg) => {
    const li = document.createElement("li");
    const stakeLine = leg.stake_usd != null
      ? `${formatMoney(leg.stake_usd)} → payout ${formatMoney(leg.payout_usd)}`
      : `stake ${(leg.stake_weight * 100).toFixed(1)}%`;
    li.innerHTML = `
      <strong>${escapeHtml(leg.outcome)}</strong>
      <span class="leg-detail">${escapeHtml(leg.source)} · ${leg.price.toFixed(2)} decimal · ${stakeLine}</span>
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
    renderPotentialPlay(data.potential_play, data.opportunities);
    renderPortfolio(data.portfolio, data.balances);
    renderOpportunities(data.opportunities || [], data.scanned_events || [], data.run_summary);
    const s = data.run_summary;
    if (s && !data.opportunities?.length && (s.events_today || s.events_tomorrow)) {
      const hint = el.empty.querySelector(".empty-hint");
      if (hint && s.events_total) {
        hint.textContent =
          `Scanned ${s.events_total} event(s), ${s.sources_loaded} books loaded. ` +
          `No arb above threshold for this tab — see game list above or Sources tab.`;
      }
    }
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

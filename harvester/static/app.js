const BOOK_URLS = {
  draftkings: "https://sportsbook.draftkings.com/",
  fanduel: "https://sportsbook.fanduel.com/",
  betmgm: "https://sports.betmgm.com/",
  caesars: "https://www.caesars.com/sportsbook-and-casino",
  fanatics: "https://sportsbook.fanatics.com/",
  betcris: "https://www.betcris.com/",
  bet365: "https://www.bet365.com/",
  thescore: "https://www.thescore.com/betting",
};

const STORAGE_KEY = "arb_filter_preset";

const state = {
  view: "today",
  viewMode: "arbs",
  timing: "pregame",
  polling: null,
  pollStartedAt: 0,
  maxPollMs: 12 * 60 * 1000,
  autoRefreshTimer: null,
  allOpportunities: [],
  scannedEvents: [],
  runSummary: null,
  filterOptions: null,
  defaults: { wager_usd: 1000, sort_by: "roi_pct" },
  filterState: {
    wagerUsd: 1000,
    sortBy: "roi_pct",
    sportsbooks: new Set(),
    sportsLeagues: new Set(),
    marketTypes: new Set(),
  },
  cardStakes: new Map(),
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
  arbCards: document.getElementById("arb-cards"),
  scannedSection: document.getElementById("scanned-section"),
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
  btnFilters: document.getElementById("btn-filters"),
  filtersPanel: document.getElementById("filters-panel"),
  filtersBackdrop: document.getElementById("filters-backdrop"),
  filtersClose: document.getElementById("filters-close"),
  filterWager: document.getElementById("filter-wager"),
  filterApply: document.getElementById("filter-apply"),
  filterReset: document.getElementById("filter-reset"),
  filterSave: document.getElementById("filter-save"),
  filterActiveBadge: document.getElementById("filter-active-badge"),
  listSportsbooks: document.getElementById("list-sportsbooks"),
  listLeagues: document.getElementById("list-leagues"),
  listMarkets: document.getElementById("list-markets"),
  badgeSportsbooks: document.getElementById("badge-sportsbooks"),
  badgeLeagues: document.getElementById("badge-leagues"),
  badgeMarkets: document.getElementById("badge-markets"),
  metricBooks: document.getElementById("metric-books"),
  metricLeagues: document.getElementById("metric-leagues"),
  ingameNotice: document.getElementById("ingame-notice"),
  presetsDropdown: document.getElementById("presets-dropdown"),
  presetsMenu: document.getElementById("presets-menu"),
  presetsTrigger: document.getElementById("presets-trigger"),
  autoRefreshToggle: document.getElementById("auto-refresh-toggle"),
  navSources: document.getElementById("nav-sources"),
  segmentMode: document.getElementById("segment-mode"),
  segmentTiming: document.getElementById("segment-timing"),
};

function setVisible(node, visible) {
  if (!node) return;
  if (visible) {
    node.classList.remove("hidden");
    node.removeAttribute("hidden");
  } else {
    node.classList.add("hidden");
    node.setAttribute("hidden", "");
  }
}

function formatPct(n) {
  return `${Number(n).toFixed(2)}%`;
}

function formatMoney(n) {
  return `$${Number(n).toFixed(2)}`;
}

function formatAmerican(n) {
  if (n == null || n === 0) return "—";
  return n > 0 ? `+${n}` : String(n);
}

function formatLastRun(iso) {
  if (!iso) return "";
  try {
    return `Last run: ${new Date(iso).toLocaleString()}`;
  } catch {
    return "";
  }
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

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
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

function openBook(source) {
  const url = BOOK_URLS[source];
  if (url) window.open(url, "_blank", "noopener");
}

function allocateStakes(legs, wagerUsd) {
  if (!legs.length) return [];
  const weights = legs.map((leg) => leg.stake_weight || 1 / legs.length);
  const sumW = weights.reduce((a, b) => a + b, 0) || 1;
  return legs.map((leg, i) => ({
    ...leg,
    stake: (wagerUsd * weights[i]) / sumW,
    payout: ((wagerUsd * weights[i]) / sumW) * leg.price,
  }));
}

function profitAndRoi(legs, wagerUsd) {
  const allocated = allocateStakes(legs, wagerUsd);
  const totalStake = allocated.reduce((s, l) => s + l.stake, 0);
  const payout = allocated.length ? Math.min(...allocated.map((l) => l.payout)) : 0;
  const profit = payout - totalStake;
  const roi = totalStake > 0 ? (profit / totalStake) * 100 : 0;
  return { profit, roi, allocated };
}

function loadPreset() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const preset = JSON.parse(raw);
    if (preset.wagerUsd) state.filterState.wagerUsd = preset.wagerUsd;
    if (preset.sortBy) state.filterState.sortBy = preset.sortBy;
    if (Array.isArray(preset.sportsbooks)) state.filterState.sportsbooks = new Set(preset.sportsbooks);
    if (Array.isArray(preset.sportsLeagues)) state.filterState.sportsLeagues = new Set(preset.sportsLeagues);
    if (Array.isArray(preset.marketTypes)) state.filterState.marketTypes = new Set(preset.marketTypes);
    el.filterWager.value = state.filterState.wagerUsd;
    const sortRadio = document.querySelector(`input[name="sort-by"][value="${state.filterState.sortBy}"]`);
    if (sortRadio) sortRadio.checked = true;
  } catch {
    /* ignore */
  }
}

function savePreset() {
  const payload = {
    wagerUsd: state.filterState.wagerUsd,
    sortBy: state.filterState.sortBy,
    sportsbooks: [...state.filterState.sportsbooks],
    sportsLeagues: [...state.filterState.sportsLeagues],
    marketTypes: [...state.filterState.marketTypes],
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function openFilters() {
  setVisible(el.filtersPanel, true);
  el.filtersPanel.classList.add("open");
  el.filtersPanel.setAttribute("aria-hidden", "false");
  setVisible(el.filtersBackdrop, true);
  el.filtersBackdrop.setAttribute("aria-hidden", "false");
}

function closeFilters() {
  el.filtersPanel.classList.remove("open");
  el.filtersPanel.setAttribute("aria-hidden", "true");
  setVisible(el.filtersPanel, false);
  setVisible(el.filtersBackdrop, false);
  el.filtersBackdrop.setAttribute("aria-hidden", "true");
}

function updateFilterBadges() {
  const sb = state.filterOptions?.sportsbooks?.length || 0;
  const lg = state.filterOptions?.sports_leagues?.length || 0;
  const mk = state.filterOptions?.market_types?.length || 0;
  const sbSel = state.filterState.sportsbooks.size || sb;
  const lgSel = state.filterState.sportsLeagues.size || lg;
  const mkSel = state.filterState.marketTypes.size || mk;
  el.badgeSportsbooks.textContent = `${sbSel} Selected`;
  el.badgeLeagues.textContent = `${lgSel} Selected`;
  el.badgeMarkets.textContent = `${mkSel} Selected`;

  let active = 0;
  if (state.filterState.wagerUsd !== (state.defaults.wager_usd || 1000)) active += 1;
  if (state.filterState.sortBy !== (state.defaults.sort_by || "roi_pct")) active += 1;
  if (state.filterState.sportsbooks.size && state.filterState.sportsbooks.size < sb) active += 1;
  if (state.filterState.sportsLeagues.size && state.filterState.sportsLeagues.size < lg) active += 1;
  if (state.filterState.marketTypes.size && state.filterState.marketTypes.size < mk) active += 1;
  el.filterActiveBadge.textContent = String(active);
  el.filterActiveBadge.classList.toggle("active", active > 0);
}

function populateFilterLists() {
  const opts = state.filterOptions;
  if (!opts) return;

  const fill = (container, items, groupKey, set, keyField = "key", labelFn = (i) => i.name || i.label) => {
    container.innerHTML = "";
    const groups = {};
    items.forEach((item) => {
      const g = item[groupKey] || "";
      groups[g] = groups[g] || [];
      groups[g].push(item);
    });
    Object.keys(groups)
      .sort()
      .forEach((group) => {
        if (group && groupKey) {
          const gl = document.createElement("div");
          gl.className = "filter-group-label";
          gl.textContent = group;
          container.appendChild(gl);
        }
        groups[group].forEach((item) => {
          const id = `${container.id}-${item[keyField]}`;
          const label = document.createElement("label");
          label.className = "filter-check";
          const checked = !set.size || set.has(item[keyField]);
          label.innerHTML = `<input type="checkbox" id="${id}" data-key="${escapeHtml(item[keyField])}" ${checked ? "checked" : ""} /> ${escapeHtml(labelFn(item))} (${item.count})`;
          container.appendChild(label);
        });
      });
  };

  fill(el.listSportsbooks, opts.sportsbooks || [], null, state.filterState.sportsbooks, "key", (i) => i.name);
  fill(el.listLeagues, opts.sports_leagues || [], "group", state.filterState.sportsLeagues, "key", (i) => i.name);
  fill(el.listMarkets, opts.market_types || [], null, state.filterState.marketTypes, "key", (i) => i.label);
  updateFilterBadges();
}

function readFiltersFromUi() {
  state.filterState.wagerUsd = Number(el.filterWager.value) || 1000;
  state.filterState.sortBy = document.querySelector('input[name="sort-by"]:checked')?.value || "roi_pct";

  const readSet = (container) => {
    const set = new Set();
    container.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
      if (cb.checked) set.add(cb.dataset.key);
    });
    return set;
  };

  state.filterState.sportsbooks = readSet(el.listSportsbooks);
  state.filterState.sportsLeagues = readSet(el.listLeagues);
  state.filterState.marketTypes = readSet(el.listMarkets);
}

function resetFilters() {
  state.filterState.wagerUsd = state.defaults.wager_usd || 1000;
  state.filterState.sortBy = state.defaults.sort_by || "roi_pct";
  state.filterState.sportsbooks = new Set();
  state.filterState.sportsLeagues = new Set();
  state.filterState.marketTypes = new Set();
  el.filterWager.value = state.filterState.wagerUsd;
  document.querySelector(`input[name="sort-by"][value="${state.filterState.sortBy}"]`)?.click();
  populateFilterLists();
  savePreset();
  renderFilteredOpportunities();
  updateFilterBadges();
}

function filterOpportunities(opportunities) {
  const fs = state.filterState;
  const sbAll = !fs.sportsbooks.size;
  const lgAll = !fs.sportsLeagues.size;
  const mkAll = !fs.marketTypes.size;

  let filtered = opportunities.filter((opp) => {
    if (!lgAll && !fs.sportsLeagues.has(opp.sport_key)) return false;
    if (!mkAll && !fs.marketTypes.has(opp.market_type)) return false;
    if (!sbAll) {
      const legBooks = (opp.legs || []).map((l) => l.source);
      if (!legBooks.some((b) => fs.sportsbooks.has(b))) return false;
    }
    return true;
  });

  filtered.sort((a, b) => {
    if (fs.sortBy === "profit_usd") {
      return (b.profit_usd_at_1000 || 0) - (a.profit_usd_at_1000 || 0);
    }
    return (b.roi_pct || b.yield_pct || 0) - (a.roi_pct || a.yield_pct || 0);
  });

  return filtered;
}

function renderComparisonTable(matrix) {
  if (!matrix || !matrix.outcomes?.length) return "";
  const { outcomes, books, prices, market_avg: marketAvg } = matrix;
  let html = '<div class="arb-comparison"><table><thead><tr><th>Market</th><th>Mkt Avg</th>';
  books.forEach((b) => {
    html += `<th>${escapeHtml(b)}</th>`;
  });
  html += "</tr></thead><tbody>";
  outcomes.forEach((outcome) => {
    const rowPrices = prices[outcome] || {};
    const best = Math.max(...Object.values(rowPrices).filter(Boolean), 0);
    html += `<tr><td>${escapeHtml(outcome)}</td>`;
    const avg = marketAvg[outcome];
    html += `<td class="muted-odds">${avg ? formatAmerican(Math.round((avg >= 2 ? (avg - 1) * 100 : -100 / (avg - 1)))) : "—"}</td>`;
    books.forEach((book) => {
      const p = rowPrices[book];
      const cls = p && p >= best - 1e-9 ? "best-odds" : "muted-odds";
      const am = p ? formatAmerican(p >= 2 ? Math.round((p - 1) * 100) : Math.round(-100 / (p - 1))) : "—";
      html += `<td class="${cls}">${am}</td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table></div>";
  return html;
}

function renderArbCard(opp) {
  const wager = state.filterState.wagerUsd;
  const { profit, roi, allocated } = profitAndRoi(opp.legs, wager);
  const card = document.createElement("article");
  card.className = "arb-card";
  card.dataset.oppId = opp.id;

  const legsHtml = allocated
    .map((leg, idx) => {
      const lineStr = leg.line != null ? ` ${leg.line}` : "";
      return `
        <div class="arb-leg" data-leg-idx="${idx}">
          <div class="arb-leg-book">${escapeHtml(leg.source_display || leg.source)}</div>
          <div class="arb-leg-outcome">${escapeHtml(leg.outcome)}${lineStr}</div>
          <div class="arb-leg-odds">${formatAmerican(leg.american)}</div>
          <div class="arb-leg-avg">Mkt avg ${formatAmerican(leg.market_avg_american)}</div>
          <div class="arb-stake-row">
            <span>$</span>
            <input type="number" class="leg-stake-input" min="1" step="1" value="${leg.stake.toFixed(2)}" data-leg="${idx}" />
          </div>
          <div class="arb-payout">Payout ${formatMoney(leg.payout)}</div>
          ${leg.is_bet_first ? '<span class="bet-first-chip">Bet First</span>' : ""}
          <button type="button" class="btn-bet-leg" data-source="${escapeHtml(leg.source)}">Bet</button>
        </div>
      `;
    })
    .join("");

  card.innerHTML = `
    <header class="arb-card-header">
      <div class="arb-card-title-wrap">
        <span class="arb-sport-badge">${escapeHtml(opp.sport_label || opp.sport_key)}</span>
        <div class="arb-event-name">${escapeHtml(opp.event_name)}</div>
        <div class="arb-market-meta">${escapeHtml(opp.market_label || opp.market_type)} · ${formatCommence(opp.commence_time)}</div>
      </div>
      <div class="arb-roi-pill">+${formatMoney(profit)} · ${roi.toFixed(1)}% ROI</div>
    </header>
    <div class="arb-card-body">
      ${legsHtml}
      <div class="arb-place-both">
        <button type="button" class="btn-place-both">⚡ Place Both</button>
      </div>
    </div>
    ${renderComparisonTable(opp.quote_matrix)}
  `;

  card.querySelector(".btn-place-both")?.addEventListener("click", () => {
    opp.legs.forEach((leg) => openBook(leg.source));
  });
  card.querySelectorAll(".btn-bet-leg").forEach((btn) => {
    btn.addEventListener("click", () => openBook(btn.dataset.source));
  });

  return card;
}

function renderArbCards(opportunities) {
  el.arbCards.innerHTML = "";
  if (!opportunities.length) {
    setVisible(el.arbCards, false);
    return;
  }
  setVisible(el.empty, false);
  setVisible(el.arbCards, true);
  opportunities.forEach((opp) => {
    el.arbCards.appendChild(renderArbCard(opp));
  });
}

function sortLowHoldEvents(events) {
  return [...events].sort((a, b) => {
    const av = a.overround_pct ?? 999;
    const bv = b.overround_pct ?? 999;
    return av - bv;
  });
}

function renderScannedEvents(events, summary) {
  el.list.innerHTML = "";
  const showLowHold = state.viewMode === "lowhold";
  const sorted = showLowHold ? sortLowHoldEvents(events) : events;

  if (!sorted.length) {
    if (!showLowHold && state.viewMode === "arbs") {
      setVisible(el.scannedSection, false);
    }
    const label = state.view === "today" ? "today" : "tomorrow";
    if (summary && summary.events_total > 0 && state.viewMode === "arbs") {
      el.emptyMsg.textContent = `No arbitrage opportunities for ${label}.`;
      el.empty.querySelector(".empty-hint").textContent =
        `Scanned ${summary.events_total} event(s) · ${summary.sources_loaded} source(s). Try Low Hold or Filters.`;
    } else if (!sorted.length && showLowHold) {
      setVisible(el.scannedSection, false);
    } else {
      el.emptyMsg.textContent = `No data for ${label}.`;
    }
    return;
  }

  setVisible(el.scannedSection, true);
  if (showLowHold) {
    setVisible(el.empty, false);
    setVisible(el.arbCards, false);
  }

  sorted.forEach((ev) => {
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
    if (ev.is_opportunity && ev.legs?.length) {
      row.addEventListener("click", () => openSlip(ev));
      row.style.cursor = "pointer";
    }
    el.list.appendChild(row);
  });
}

function updateMetricStrip() {
  const books = state.filterOptions?.sportsbooks?.length ?? 0;
  const leagues = state.filterOptions?.sports_leagues?.length ?? 0;
  if (el.metricBooks) el.metricBooks.textContent = String(books || state.runSummary?.sources_loaded || 0);
  if (el.metricLeagues) el.metricLeagues.textContent = String(leagues);
}

function renderFilteredOpportunities() {
  if (state.timing === "ingame") return;
  const filtered = filterOpportunities(state.allOpportunities);
  el.total.textContent = String(filtered.length);
  if (filtered.length) {
    const yields = filtered.map((o) => o.roi_pct || o.yield_pct || 0);
    el.avg.textContent = formatPct(yields.reduce((a, b) => a + b, 0) / yields.length);
    el.best.textContent = formatPct(Math.max(...yields));
  } else if (state.runSummary) {
    el.avg.textContent = formatPct(0);
    el.best.textContent = formatPct(0);
  }
  if (state.viewMode === "arbs") {
    renderArbCards(filtered);
    if (!filtered.length) {
      setVisible(el.empty, true);
    }
  }
}

function renderMainView() {
  if (state.timing === "ingame") {
    setVisible(el.ingameNotice, true);
    setVisible(el.arbCards, false);
    setVisible(el.scannedSection, false);
    setVisible(el.empty, false);
    return;
  }
  setVisible(el.ingameNotice, false);

  if (state.viewMode === "lowhold") {
    setVisible(el.arbCards, false);
    renderScannedEvents(state.scannedEvents, state.runSummary);
    if (!state.scannedEvents.length) {
      setVisible(el.empty, true);
      el.emptyMsg.textContent = "No scanned markets for this tab.";
    }
    return;
  }

  renderFilteredOpportunities();
  if (state.allOpportunities.length) {
    renderScannedEvents(state.scannedEvents, state.runSummary);
  } else {
    renderScannedEvents(state.scannedEvents, state.runSummary);
  }
}

function renderOpportunities(opportunities, scannedEvents, summary) {
  state.allOpportunities = opportunities || [];
  state.scannedEvents = scannedEvents || [];
  state.runSummary = summary || null;
  renderMainView();
}

function renderSources(sources) {
  el.sourceList.innerHTML = "";
  if (!sources?.length) {
    setVisible(el.sourcesEmpty, true);
    setVisible(el.sourceList, false);
    return;
  }
  setVisible(el.sourcesEmpty, false);
  setVisible(el.sourceList, true);
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
    row.innerHTML = `
      <div>
        <div class="source-name">${escapeHtml(src.name)}</div>
        <div class="source-channel">${escapeHtml(channelLabel(src.channel))}</div>
        <div class="source-message">${escapeHtml(src.message)}</div>
      </div>
      <span class="status-pill ${statusPillClass(src.status)}">${escapeHtml(src.status_label)}</span>
    `;
    el.sourceList.appendChild(row);
  });
}

function updatePanels() {
  const isSources = state.view === "sources";
  setVisible(el.panelOpportunities, !isSources);
  setVisible(el.panelSources, isSources);
  document.querySelectorAll(".os-nav-link").forEach((link) => {
    const nav = link.dataset.nav;
    link.classList.toggle("os-nav-link--active", (nav === "sources") === isSources);
  });
}

function setViewMode(mode) {
  state.viewMode = mode;
  el.segmentMode?.querySelectorAll(".os-segment-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });
  renderMainView();
}

function setTiming(timing) {
  state.timing = timing;
  el.segmentTiming?.querySelectorAll(".os-segment-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.timing === timing);
  });
  renderMainView();
}

function togglePresetsMenu(open) {
  let show = open;
  if (show === undefined) {
    show = el.presetsMenu?.hasAttribute("hidden");
  }
  setVisible(el.presetsMenu, show);
  el.presetsTrigger?.setAttribute("aria-expanded", show ? "true" : "false");
}

function startAutoRefresh() {
  stopAutoRefresh();
  state.autoRefreshTimer = setInterval(() => {
    onRefresh().catch(() => {});
  }, 60000);
}

function stopAutoRefresh() {
  if (state.autoRefreshTimer) {
    clearInterval(state.autoRefreshTimer);
    state.autoRefreshTimer = null;
  }
}

function openSlip(opp) {
  el.slipTitle.textContent = opp.event_name;
  let yieldLine = `Profit: ${formatPct(opp.yield_pct)}`;
  if (opp.arb_method) yieldLine += ` (${opp.arb_method})`;
  el.slipYield.textContent = yieldLine;
  el.slipLegs.innerHTML = "";
  (opp.legs || []).forEach((leg) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <strong>${escapeHtml(leg.outcome)}</strong>
      <span class="leg-detail">${escapeHtml(leg.source_display || leg.source)} · ${leg.price?.toFixed?.(2) ?? leg.price} decimal</span>
    `;
    el.slipLegs.appendChild(li);
  });
  el.slipDialog.showModal();
}

function applyPayload(data) {
  const stats = data.stats || {};
  if (!(data.opportunities || []).length) {
    el.total.textContent = String(stats.total_opportunities ?? 0);
    el.avg.textContent = formatPct(stats.avg_profit_pct ?? 0);
    el.best.textContent = formatPct(stats.best_available_pct ?? 0);
  }

  const counts = data.counts || {};
  el.countToday.textContent = String(counts.today ?? 0);
  el.countTomorrow.textContent = String(counts.tomorrow ?? 0);
  el.countSourcesLoaded.textContent = String(data.source_summary?.loaded ?? 0);
  el.lastRun.textContent = formatLastRun(data.last_run_at);

  if (data.filter_options) {
    state.filterOptions = data.filter_options;
    populateFilterLists();
    updateMetricStrip();
  }
  if (data.defaults) {
    state.defaults = data.defaults;
  }

  if (data.error && state.view !== "sources") {
    el.error.textContent = data.error;
    setVisible(el.error, true);
  } else if (!data.api_key_configured) {
    el.error.textContent = "ODDS_API_KEY is not set in harvester/.env";
    setVisible(el.error, true);
  } else {
    setVisible(el.error, false);
  }

  if (state.view === "today" || state.view === "tomorrow") {
    renderOpportunities(data.opportunities || [], data.scanned_events || [], data.run_summary);
    const s = data.run_summary;
    if (s && !data.opportunities?.length && (s.events_today || s.events_tomorrow)) {
      const hint = el.empty.querySelector(".empty-hint");
      if (hint && s.events_total) {
        hint.textContent =
          `Scanned ${s.events_total} event(s), ${s.sources_loaded} books loaded. ` +
          `No arb above threshold — use Filters or see scanned games below.`;
      }
    }
  }

  renderSources(data.sources || []);
  updatePanels();
  setLoading(Boolean(data.running), data.run_status || (data.running ? "Running pipeline…" : ""));
}

async function fetchStatus() {
  const day = state.view === "tomorrow" ? "tomorrow" : "today";
  const res = await fetch(`/api/status?day=${day}`);
  const text = await res.text();
  if (!res.ok) throw new Error(text || res.statusText);
  return JSON.parse(text);
}

async function triggerRun() {
  const res = await fetch("/api/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
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

function stopPolling() {
  if (state.polling) {
    clearInterval(state.polling);
    state.polling = null;
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
      el.error.textContent = "Run took too long and was stopped.";
      el.error.classList.remove("hidden");
      return;
    }
    try {
      const data = await fetchStatus();
      applyPayload(data);
      if (!data.running) stopPolling();
    } catch (e) {
      stopPolling();
      setLoading(false);
      el.error.textContent = e.message || String(e);
      el.error.classList.remove("hidden");
    }
  }, 2000);
}

async function onRefresh() {
  try {
    setLoading(true);
    await triggerRun();
    startPolling();
    applyPayload(await fetchStatus());
  } catch (e) {
    el.error.textContent = e.message || String(e);
    el.error.classList.remove("hidden");
    setLoading(false);
  }
}

async function switchView(view) {
  state.view = view;
  el.tabs.forEach((t) => {
    const active = t.dataset.view === view;
    t.classList.toggle("active", active);
    t.setAttribute("aria-selected", active ? "true" : "false");
  });
  updatePanels();
  try {
    applyPayload(await fetchStatus());
  } catch (e) {
    console.error(e);
  }
}

el.tabs.forEach((tab) => {
  tab.addEventListener("click", () => switchView(tab.dataset.view));
});

el.navSources?.addEventListener("click", () => switchView("sources"));
document.querySelector('.os-nav-link[data-nav="arbitrage"]')?.addEventListener("click", () => switchView("today"));

el.segmentMode?.querySelectorAll(".os-segment-btn").forEach((btn) => {
  btn.addEventListener("click", () => setViewMode(btn.dataset.mode));
});

el.segmentTiming?.querySelectorAll(".os-segment-btn").forEach((btn) => {
  btn.addEventListener("click", () => setTiming(btn.dataset.timing));
});

el.presetsTrigger?.addEventListener("click", (e) => {
  e.stopPropagation();
  togglePresetsMenu();
});

el.presetsMenu?.querySelectorAll(".os-dropdown-item").forEach((item) => {
  item.addEventListener("click", () => {
    togglePresetsMenu(false);
    if (item.dataset.preset === "load") loadPreset();
    if (item.dataset.preset === "save") {
      readFiltersFromUi();
      savePreset();
      updateFilterBadges();
    }
    if (item.dataset.preset === "reset") resetFilters();
    populateFilterLists();
    renderMainView();
  });
});

document.addEventListener("click", (e) => {
  if (!el.presetsDropdown?.contains(e.target)) togglePresetsMenu(false);
});

el.autoRefreshToggle?.addEventListener("change", () => {
  if (el.autoRefreshToggle.checked) startAutoRefresh();
  else stopAutoRefresh();
});

el.refreshBtn.addEventListener("click", onRefresh);
el.slipClose.addEventListener("click", () => el.slipDialog.close());
el.btnFilters.addEventListener("click", openFilters);
el.filtersClose.addEventListener("click", closeFilters);
el.filtersBackdrop.addEventListener("click", closeFilters);

el.filterApply.addEventListener("click", () => {
  readFiltersFromUi();
  savePreset();
  renderFilteredOpportunities();
  updateFilterBadges();
  closeFilters();
});

el.filterReset.addEventListener("click", resetFilters);
el.filterSave.addEventListener("click", () => {
  readFiltersFromUi();
  savePreset();
  updateFilterBadges();
});

el.filterWager.addEventListener("change", () => {
  state.filterState.wagerUsd = Number(el.filterWager.value) || 1000;
  renderFilteredOpportunities();
});

document.querySelectorAll(".filter-section-toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    const body = btn.parentElement.querySelector(".filter-section-body");
    body?.classList.toggle("filter-section-body--open");
  });
});

loadPreset();

(async function init() {
  updatePanels();
  try {
    const data = await fetchStatus();
    applyPayload(data);
    if (data.running) startPolling();
  } catch {
    el.error.textContent = "Could not load dashboard. Is the server running?";
    setVisible(el.error, true);
  }
})();

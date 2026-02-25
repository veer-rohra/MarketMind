const SIGNALS_PATH = "marketmind_signals.csv";
const PORTFOLIO_PATH = "marketmind_portfolio_plan.csv";
const LIVE_DATA_PATH = "marketmind_ml/live_market_data.csv";
const SITE_URL = "https://veer-rohra.github.io/MarketMind/";
const CONFIG = window.MARKETMIND_CONFIG || {};
const WAITLIST_ENDPOINT = CONFIG.waitlistEndpoint || "";
const FOUNDERS = Array.isArray(CONFIG.founders) && CONFIG.founders.length
  ? CONFIG.founders
  : [
      {
        name: "Your Name",
        title: "Founder",
        phone: "+1-000-000-0000",
        email: "",
        socials: [{ label: "Profile", url: "https://x.com/yourprofile" }],
      },
    ];

const els = {
  metricEnter: document.getElementById("metricEnter"),
  metricWait: document.getElementById("metricWait"),
  metricRisk: document.getElementById("metricRisk"),
  signalsBody: document.getElementById("signalsBody"),
  signalsMeta: document.getElementById("signalsMeta"),
  portfolioMeta: document.getElementById("portfolioMeta"),
  portfolioCards: document.getElementById("portfolioCards"),
  refreshBtn: document.getElementById("refreshBtn"),
  waitlistForm: document.getElementById("waitlistForm"),
  waitlistMessage: document.getElementById("waitlistMessage"),
  waitlistName: document.getElementById("waitlistName"),
  waitlistEmail: document.getElementById("waitlistEmail"),
  waitlistRole: document.getElementById("waitlistRole"),
  trustLastDate: document.getElementById("trustLastDate"),
  trustFreshness: document.getElementById("trustFreshness"),
  trustModelVersion: document.getElementById("trustModelVersion"),
  shareXBtn: document.getElementById("shareXBtn"),
  shareLinkedInBtn: document.getElementById("shareLinkedInBtn"),
  copyLinkBtn: document.getElementById("copyLinkBtn"),
  founderName: document.getElementById("founderName"),
  founderPhone: document.getElementById("founderPhone"),
  founderSocialsContainer: document.getElementById("founderSocialsContainer"),
  foundingTeam: document.getElementById("foundingTeam"),
  signalFilter: document.getElementById("signalFilter"),
  clearFiltersBtn: document.getElementById("clearFiltersBtn"),
  data30Meta: document.getElementById("data30Meta"),
  statAvgPred: document.getElementById("statAvgPred"),
  statBestSignal: document.getElementById("statBestSignal"),
  statSignalMix: document.getElementById("statSignalMix"),
  trendChart: document.getElementById("trendChart"),
  chartViewport: document.getElementById("chartViewport"),
  chartTooltip: document.getElementById("chartTooltip"),
  zoomOutBtn: document.getElementById("zoomOutBtn"),
  zoomInBtn: document.getElementById("zoomInBtn"),
  resetZoomBtn: document.getElementById("resetZoomBtn"),
};

const chartState = {
  initialized: false,
  points: [],
  zoom: 1,
  minZoom: 1,
  maxZoom: 4,
};

let signalsCache = [];

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  if (!lines.length) return [];

  const headers = splitCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = splitCsvLine(line);
    const row = {};
    headers.forEach((h, i) => {
      row[h] = cells[i] ?? "";
    });
    return row;
  });
}

function splitCsvLine(line) {
  const out = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      inQuotes = !inQuotes;
      continue;
    }
    if (ch === "," && !inQuotes) {
      out.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  out.push(current);
  return out;
}

function fmtPct(v) {
  const num = Number(v);
  if (Number.isNaN(num)) return "n/a";
  return `${(num * 100).toFixed(2)}%`;
}

function fmtUsd(v) {
  const num = Number(v);
  if (Number.isNaN(num)) return "n/a";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(num);
}

function badge(action) {
  const label =
    action === "ENTER" ? "LONG ENTRY" : action === "EXIT" ? "SHORT/EXIT" : action === "WAIT" ? "WAIT" : "AVOID";
  return `<span class="badge ${action}">${label}</span>`;
}

function actionBucket(action) {
  if (action === "ENTER") return "long";
  if (action === "EXIT") return "short";
  return "neutral";
}

function applySignalFilter(rows) {
  const filter = els.signalFilter.value;
  if (filter === "all") return rows;
  return rows.filter((r) => actionBucket(r.action) === filter);
}

function renderSignals(rows) {
  signalsCache = rows;
  els.signalsBody.innerHTML = "";
  const filteredRows = applySignalFilter(rows);
  if (!filteredRows.length) {
    els.signalsBody.innerHTML = `<tr><td colspan="5">No signal data found. Run marketmind_ml/run_daily.sh first.</td></tr>`;
    els.metricEnter.textContent = "0";
    els.metricWait.textContent = "0";
    els.metricRisk.textContent = "n/a";
    return;
  }

  const enterCount = filteredRows.filter((r) => r.action === "ENTER").length;
  const waitCount = filteredRows.filter((r) => r.action === "WAIT" || r.action === "AVOID").length;
  const avgVol = filteredRows.reduce((acc, r) => acc + (Number(r.volatility_20d) || 0), 0) / filteredRows.length;

  els.metricEnter.textContent = String(enterCount);
  els.metricWait.textContent = String(waitCount);
  els.metricRisk.textContent = fmtPct(avgVol);
  els.trustModelVersion.textContent = CONFIG.modelVersion || "v1.0";

  const dates = filteredRows.map((r) => new Date(r.date)).filter((d) => !Number.isNaN(d.getTime()));
  if (dates.length) {
    const latest = new Date(Math.max(...dates.map((d) => d.getTime())));
    const now = new Date();
    const diffHours = Math.round((now.getTime() - latest.getTime()) / 36e5);
    els.trustLastDate.textContent = latest.toISOString().slice(0, 10);
    els.trustFreshness.textContent = diffHours <= 24 ? `${diffHours}h old` : `${Math.round(diffHours / 24)}d old`;
  } else {
    els.trustLastDate.textContent = "n/a";
    els.trustFreshness.textContent = "n/a";
  }

  filteredRows.forEach((row, idx) => {
    const tr = document.createElement("tr");
    tr.className = "fade-in";
    tr.style.animationDelay = `${idx * 35}ms`;
    tr.innerHTML = `
      <td>${row.ticker || "-"}</td>
      <td>${badge(row.action || "WAIT")}</td>
      <td>${fmtPct(row.pred_forward_return_5d)}</td>
      <td>${fmtPct(row.volatility_20d)}</td>
      <td>${Number(row.close || 0).toFixed(2)}</td>
    `;
    els.signalsBody.appendChild(tr);
  });

  els.signalsMeta.textContent = `Loaded ${filteredRows.length} rows`;
}

function renderPortfolio(rows) {
  els.portfolioCards.innerHTML = "";
  if (!rows.length) {
    els.portfolioCards.innerHTML = `<article class="card">No ranked portfolio yet. Run the daily pipeline.</article>`;
    els.portfolioMeta.textContent = "No data";
    return;
  }

  const sorted = [...rows].sort((a, b) => Number(a.rank) - Number(b.rank));
  sorted.forEach((r, idx) => {
    const card = document.createElement("article");
    card.className = "card fade-in";
    card.style.animationDelay = `${idx * 45}ms`;
    card.innerHTML = `
      <h4>#${r.rank} ${r.ticker}</h4>
      <p>Action: ${r.action}</p>
      <p>Pred 5D: ${fmtPct(r.pred_forward_return_5d)}</p>
      <p>Volatility: ${fmtPct(r.volatility_20d)}</p>
      <p>Weight: ${fmtPct(r.allocation_weight)}</p>
      <p>Capital: ${fmtUsd(r.allocated_capital_usd)}</p>
    `;
    els.portfolioCards.appendChild(card);
  });

  els.portfolioMeta.textContent = `Loaded ${rows.length} ranked positions`;
}

async function fetchCsv(path) {
  const response = await fetch(`${path}?t=${Date.now()}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${path}`);
  }
  return parseCsv(await response.text());
}

async function loadDashboard() {
  try {
    const [signals, portfolio] = await Promise.all([fetchCsv(SIGNALS_PATH), fetchCsv(PORTFOLIO_PATH)]);
    renderSignals(signals);
    renderPortfolio(portfolio);
    updateDataSummary(signals);
  } catch (err) {
    els.signalsMeta.textContent = "Data unavailable";
    els.portfolioMeta.textContent = "Data unavailable";
    els.signalsBody.innerHTML = `<tr><td colspan="5">${err.message}</td></tr>`;
    els.portfolioCards.innerHTML = `<article class="card">${err.message}</article>`;
  }
}

function updateDataSummary(signals) {
  if (!signals.length) {
    els.statAvgPred.textContent = "n/a";
    els.statBestSignal.textContent = "n/a";
    els.statSignalMix.textContent = "n/a";
    return;
  }
  const avgPred = signals.reduce((acc, r) => acc + (Number(r.pred_forward_return_5d) || 0), 0) / signals.length;
  const best = [...signals].sort((a, b) => Number(b.pred_forward_return_5d) - Number(a.pred_forward_return_5d))[0];
  const longCount = signals.filter((s) => s.action === "ENTER").length;
  const shortCount = signals.filter((s) => s.action === "EXIT").length;
  const neutralCount = signals.length - longCount - shortCount;

  els.statAvgPred.textContent = fmtPct(avgPred);
  els.statBestSignal.textContent = `${best.ticker} ${fmtPct(best.pred_forward_return_5d)}`;
  els.statSignalMix.textContent = `L:${longCount} S:${shortCount} N:${neutralCount}`;
}

function drawChart() {
  const canvas = els.trendChart;
  const ctx = canvas.getContext("2d");
  const width = canvas.clientWidth;
  const height = Math.max(220, Math.round(width * 0.32));
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const points = chartState.points;
  if (!points.length) {
    ctx.fillStyle = "#9fb4cb";
    ctx.font = "14px Space Grotesk";
    ctx.fillText("No 30-day chart data yet.", 14, 32);
    return;
  }

  const visibleCount = Math.max(8, Math.round(points.length / chartState.zoom));
  const start = Math.max(0, points.length - visibleCount);
  const visible = points.slice(start);
  const values = visible.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = 28;
  const innerW = width - pad * 2;
  const innerH = height - pad * 2;

  ctx.strokeStyle = "rgba(150,180,210,0.2)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = pad + (innerH * i) / 4;
    ctx.beginPath();
    ctx.moveTo(pad, y);
    ctx.lineTo(width - pad, y);
    ctx.stroke();
  }

  const scaleY = (v) => {
    if (max === min) return pad + innerH / 2;
    return pad + ((max - v) / (max - min)) * innerH;
  };
  const scaleX = (idx) => pad + (idx / Math.max(visible.length - 1, 1)) * innerW;

  ctx.strokeStyle = "#5eead4";
  ctx.lineWidth = 2;
  ctx.beginPath();
  visible.forEach((p, idx) => {
    const x = scaleX(idx);
    const y = scaleY(p.value);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#d6e9fb";
  ctx.font = "12px IBM Plex Mono";
  ctx.fillText(visible[0].label, pad, height - 8);
  ctx.fillText(visible[visible.length - 1].label, width - pad - 72, height - 8);

  chartState.visible = visible;
  chartState.scaleX = scaleX;
  chartState.scaleY = scaleY;
  chartState.pad = pad;
  chartState.width = width;
  chartState.height = height;
}

function onChartPointerMove(event) {
  if (!chartState.visible?.length) return;
  const rect = els.trendChart.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const idx = Math.round(((x - chartState.pad) / (chartState.width - chartState.pad * 2)) * (chartState.visible.length - 1));
  const safeIdx = Math.max(0, Math.min(chartState.visible.length - 1, idx));
  const point = chartState.visible[safeIdx];
  if (!point) return;

  const px = chartState.scaleX(safeIdx);
  const py = chartState.scaleY(point.value);
  els.chartTooltip.hidden = false;
  els.chartTooltip.style.left = `${px}px`;
  els.chartTooltip.style.top = `${py}px`;
  els.chartTooltip.textContent = `${point.label} | ${point.ticker}: ${point.value.toFixed(2)}`;
}

function onChartLeave() {
  els.chartTooltip.hidden = true;
}

function wireChartControls() {
  els.zoomInBtn.addEventListener("click", () => {
    chartState.zoom = Math.min(chartState.maxZoom, chartState.zoom + 0.5);
    drawChart();
  });
  els.zoomOutBtn.addEventListener("click", () => {
    chartState.zoom = Math.max(chartState.minZoom, chartState.zoom - 0.5);
    drawChart();
  });
  els.resetZoomBtn.addEventListener("click", () => {
    chartState.zoom = 1;
    drawChart();
  });
  els.trendChart.addEventListener("mousemove", onChartPointerMove);
  els.trendChart.addEventListener("mouseleave", onChartLeave);
  els.trendChart.addEventListener("wheel", (event) => {
    event.preventDefault();
    chartState.zoom = Math.max(chartState.minZoom, Math.min(chartState.maxZoom, chartState.zoom + (event.deltaY < 0 ? 0.25 : -0.25)));
    drawChart();
  });
  window.addEventListener("resize", () => {
    if (chartState.initialized) drawChart();
  });
}

function normalizeChartPointsFromLive(rows) {
  const byTicker = new Map();
  rows.forEach((r) => {
    if (!byTicker.has(r.ticker)) byTicker.set(r.ticker, []);
    byTicker.get(r.ticker).push(r);
  });
  const [ticker, series] = [...byTicker.entries()].sort((a, b) => b[1].length - a[1].length)[0] || [];
  if (!series) return [];
  return series
    .sort((a, b) => new Date(a.date) - new Date(b.date))
    .slice(-30)
    .map((r) => ({ label: r.date, value: Number(r.close), ticker }));
}

async function initChartLazy() {
  const observer = new IntersectionObserver(
    async (entries) => {
      if (!entries.some((e) => e.isIntersecting) || chartState.initialized) return;
      chartState.initialized = true;
      observer.disconnect();
      try {
        const liveRows = await fetchCsv(LIVE_DATA_PATH);
        chartState.points = normalizeChartPointsFromLive(liveRows);
        els.data30Meta.textContent = chartState.points.length
          ? `Interactive 30-day close trend (hover + zoom) from ${chartState.points[0].ticker}`
          : "No live 30-day data file found.";
      } catch {
        chartState.points = signalsCache.slice(-30).map((s) => ({
          label: s.date,
          value: Number(s.pred_forward_return_5d || 0) * 100,
          ticker: s.ticker,
        }));
        els.data30Meta.textContent = "Fallback chart from predicted return data.";
      }
      drawChart();
    },
    { threshold: 0.25 }
  );
  observer.observe(els.chartViewport);
}

function showWaitlistMessage(text, isError = false) {
  els.waitlistMessage.textContent = text;
  els.waitlistMessage.style.color = isError ? "#fb7185" : "#5eead4";
}

async function submitWaitlist(formData) {
  if (!WAITLIST_ENDPOINT) {
    const entry = {
      name: formData.get("name"),
      email: formData.get("email"),
      role: formData.get("role"),
      timestamp: new Date().toISOString(),
    };
    const existing = JSON.parse(localStorage.getItem("marketmind_waitlist") || "[]");
    existing.push(entry);
    localStorage.setItem("marketmind_waitlist", JSON.stringify(existing));
    return;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  const response = await fetch(WAITLIST_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal: controller.signal,
    body: JSON.stringify({
      name: formData.get("name"),
      email: formData.get("email"),
      role: formData.get("role"),
      source: "marketmind-site",
    }),
  });
  clearTimeout(timeout);
  if (!response.ok) {
    throw new Error("Waitlist submission failed");
  }
}

function initFounderInfo() {
  const primary = FOUNDERS[0];
  els.founderName.textContent = primary.name || "Founder";
  els.founderPhone.textContent = primary.phone || "-";
  els.founderSocialsContainer.innerHTML = "";
  const socials = primary.socials || [];
  socials.forEach((s, idx) => {
    const a = document.createElement("a");
    a.href = s.url;
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = s.label || s.url;
    els.founderSocialsContainer.appendChild(a);
    if (idx < socials.length - 1) {
      els.founderSocialsContainer.append(" | ");
    }
  });
}

function renderFoundingTeam() {
  els.foundingTeam.innerHTML = "";
  FOUNDERS.forEach((f) => {
    const socials = (f.socials || [])
      .map((s) => `<a href="${s.url}" target="_blank" rel="noopener">${s.label}</a>`)
      .join(" | ");
    const card = document.createElement("article");
    card.className = "card founder-card";
    card.innerHTML = `
      <h4>${f.name || "-"}</h4>
      <p class="founder-title">${f.title || "Team"}</p>
      <p class="team-line"><span class="team-label">Phone:</span> <span class="team-value">${f.phone || "-"}</span></p>
      <p class="team-line"><span class="team-label">Email:</span> <span class="team-value">${f.email ? `<a href="mailto:${f.email}">${f.email}</a>` : "-"}</span></p>
      <p class="team-line team-socials"><span class="team-label">Socials:</span> <span class="team-value">${socials || "-"}</span></p>
    `;
    els.foundingTeam.appendChild(card);
  });
}

function initShareButtons() {
  const shareText =
    "I built MarketMind: an AI analyst that tracks stocks 24/7 and gives ENTER/EXIT/WAIT/AVOID decisions.";
  els.shareXBtn.addEventListener("click", () => {
    const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(SITE_URL)}`;
    window.open(url, "_blank", "noopener");
  });
  els.shareLinkedInBtn.addEventListener("click", () => {
    const url = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(SITE_URL)}`;
    window.open(url, "_blank", "noopener");
  });
  els.copyLinkBtn.addEventListener("click", async () => {
    await navigator.clipboard.writeText(SITE_URL);
    els.copyLinkBtn.textContent = "Copied";
    setTimeout(() => {
      els.copyLinkBtn.textContent = "Copy Link";
    }, 1200);
  });
}

async function onWaitlistSubmit(event) {
  event.preventDefault();
  const formData = new FormData(els.waitlistForm);
  try {
    await submitWaitlist(formData);
    showWaitlistMessage("You are on the waitlist. Welcome email may take a minute.");
    els.waitlistForm.reset();
  } catch (err) {
    if (err.name === "AbortError") {
      showWaitlistMessage("Request timed out. Please try once more in a few seconds.", true);
      return;
    }
    showWaitlistMessage("Could not submit right now. Try again in a minute.", true);
  }
}

els.refreshBtn.addEventListener("click", loadDashboard);
els.signalFilter.addEventListener("change", () => renderSignals(signalsCache));
els.clearFiltersBtn.addEventListener("click", () => {
  els.signalFilter.value = "all";
  renderSignals(signalsCache);
});
els.waitlistForm.addEventListener("submit", onWaitlistSubmit);
wireChartControls();
initFounderInfo();
renderFoundingTeam();
initShareButtons();
initChartLazy();
loadDashboard();

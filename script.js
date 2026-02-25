const SIGNALS_PATH = "marketmind_signals.csv";
const PORTFOLIO_PATH = "marketmind_portfolio_plan.csv";
const WAITLIST_ENDPOINT = "";

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
};

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
  return `<span class="badge ${action}">${action}</span>`;
}

function renderSignals(rows) {
  els.signalsBody.innerHTML = "";
  if (!rows.length) {
    els.signalsBody.innerHTML = `<tr><td colspan="5">No signal data found. Run marketmind_ml/run_daily.sh first.</td></tr>`;
    els.metricEnter.textContent = "0";
    els.metricWait.textContent = "0";
    els.metricRisk.textContent = "n/a";
    return;
  }

  const enterCount = rows.filter((r) => r.action === "ENTER").length;
  const waitCount = rows.filter((r) => r.action === "WAIT").length;
  const avgVol = rows.reduce((acc, r) => acc + (Number(r.volatility_20d) || 0), 0) / rows.length;

  els.metricEnter.textContent = String(enterCount);
  els.metricWait.textContent = String(waitCount);
  els.metricRisk.textContent = fmtPct(avgVol);

  rows.forEach((row, idx) => {
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

  els.signalsMeta.textContent = `Loaded ${rows.length} rows`;
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
  } catch (err) {
    els.signalsMeta.textContent = "Data unavailable";
    els.portfolioMeta.textContent = "Data unavailable";
    els.signalsBody.innerHTML = `<tr><td colspan="5">${err.message}</td></tr>`;
    els.portfolioCards.innerHTML = `<article class="card">${err.message}</article>`;
  }
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

  const response = await fetch(WAITLIST_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: formData.get("name"),
      email: formData.get("email"),
      role: formData.get("role"),
      source: "marketmind-site",
    }),
  });
  if (!response.ok) {
    throw new Error("Waitlist submission failed");
  }
}

async function onWaitlistSubmit(event) {
  event.preventDefault();
  const formData = new FormData(els.waitlistForm);
  try {
    await submitWaitlist(formData);
    showWaitlistMessage("You are on the waitlist. Watch your inbox for private beta access.");
    els.waitlistForm.reset();
  } catch (err) {
    showWaitlistMessage("Could not submit right now. Try again in a minute.", true);
  }
}

els.refreshBtn.addEventListener("click", loadDashboard);
els.waitlistForm.addEventListener("submit", onWaitlistSubmit);
loadDashboard();

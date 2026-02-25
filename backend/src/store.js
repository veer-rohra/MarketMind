import fs from "fs";
import path from "path";

const filePath = path.resolve("backend/data/waitlist.json");

function ensureFile() {
  if (!fs.existsSync(filePath)) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, "[]", "utf8");
  }
}

export function getWaitlist() {
  ensureFile();
  const raw = fs.readFileSync(filePath, "utf8");
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function saveWaitlist(rows) {
  ensureFile();
  fs.writeFileSync(filePath, JSON.stringify(rows, null, 2), "utf8");
}

export function upsertSubscriber(entry) {
  const rows = getWaitlist();
  const email = String(entry.email || "").trim().toLowerCase();
  const idx = rows.findIndex((r) => String(r.email || "").toLowerCase() === email);

  const next = {
    name: entry.name,
    email,
    role: entry.role,
    source: entry.source || "website",
    subscribed_at: new Date().toISOString(),
  };

  if (idx >= 0) {
    rows[idx] = { ...rows[idx], ...next, updated_at: new Date().toISOString() };
  } else {
    rows.push(next);
  }

  saveWaitlist(rows);
  return { created: idx < 0, record: next, total: rows.length };
}

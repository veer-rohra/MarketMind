import "dotenv/config";
import express from "express";
import cors from "cors";
import fs from "fs";
import path from "path";

import { getWaitlist, upsertSubscriber } from "./store.js";
import { sendWelcomeEmail, sendEmail, generateAiReply } from "./mailer.js";

const app = express();
const port = Number(process.env.PORT || 8080);
const siteOrigin = process.env.SITE_ORIGIN || "https://veer-rohra.github.io";
const adminToken = process.env.ADMIN_TOKEN || "";
const adminPagePath = path.resolve("backend/src/admin.html");

app.use(cors({ origin: [siteOrigin, "http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:3000"] }));
app.use(express.json());

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email || ""));
}

app.get("/health", (_req, res) => {
  res.json({ ok: true, service: "marketmind-backend" });
});

app.get("/admin", (_req, res) => {
  if (!fs.existsSync(adminPagePath)) {
    return res.status(404).send("Admin page not found.");
  }
  return res.sendFile(adminPagePath);
});

app.get("/api/waitlist", (req, res) => {
  const token = req.headers.authorization?.replace("Bearer ", "");
  if (!adminToken || token !== adminToken) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  const rows = getWaitlist();
  return res.json({ count: rows.length, rows });
});

app.post("/api/waitlist", async (req, res) => {
  const name = String(req.body?.name || "").trim();
  const email = String(req.body?.email || "").trim().toLowerCase();
  const role = String(req.body?.role || "retail-investor").trim();
  const source = String(req.body?.source || "website").trim();

  if (!name || !isValidEmail(email)) {
    return res.status(400).json({ error: "Valid name and email are required." });
  }

  const result = upsertSubscriber({ name, email, role, source });

  // Return immediately so frontend never appears stuck; send email in background.
  sendWelcomeEmail({ name, email, role }).catch((err) => {
    console.error(`welcome-email-failed: ${email} -> ${err.message}`);
  });

  return res.status(201).json({
    ok: true,
    created: result.created,
    total: result.total,
    message: "Signup stored. Welcome email is being sent.",
  });
});

app.post("/api/campaign/send", async (req, res) => {
  const token = req.headers.authorization?.replace("Bearer ", "");
  if (!adminToken || token !== adminToken) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  const rows = getWaitlist();
  const customSubject = String(req.body?.subject || "").trim();
  const subject = customSubject || "MarketMind Early Access Update";

  const outcomes = [];
  for (const row of rows) {
    try {
      const text = await generateAiReply({ name: row.name, role: row.role });
      await sendEmail({ to: row.email, subject, text });
      outcomes.push({ email: row.email, status: "sent" });
    } catch (err) {
      outcomes.push({ email: row.email, status: "failed", error: err.message });
    }
  }

  return res.json({
    ok: true,
    sent: outcomes.filter((o) => o.status === "sent").length,
    failed: outcomes.filter((o) => o.status === "failed").length,
    outcomes,
  });
});

app.listen(port, () => {
  console.log(`MarketMind backend running on port ${port}`);
});

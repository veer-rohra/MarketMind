import "dotenv/config";

import { getWaitlist } from "./store.js";
import { generateAiReply, sendEmail } from "./mailer.js";

async function run() {
  const rows = getWaitlist();
  const subject = process.env.BROADCAST_SUBJECT || "MarketMind Early Access Update";

  console.log(`Sending broadcast to ${rows.length} subscribers...`);

  let sent = 0;
  let failed = 0;

  for (const row of rows) {
    try {
      const text = await generateAiReply({ name: row.name, role: row.role });
      await sendEmail({ to: row.email, subject, text });
      sent += 1;
      console.log(`sent: ${row.email}`);
    } catch (err) {
      failed += 1;
      console.error(`failed: ${row.email} -> ${err.message}`);
    }
  }

  console.log(`Done. sent=${sent}, failed=${failed}`);
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});

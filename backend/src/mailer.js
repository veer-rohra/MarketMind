import nodemailer from "nodemailer";
import OpenAI from "openai";

const REQUIRED_PHRASE = "thnks for being a part of our team";

export function getFounderSignature() {
  return {
    name: process.env.FOUNDER_NAME || "Founder Name",
    phone: process.env.FOUNDER_PHONE || "+1-000-000-0000",
    socials: process.env.FOUNDER_SOCIALS || "https://x.com/yourprofile",
  };
}

export function createTransport() {
  const host = process.env.SMTP_HOST;
  const port = Number(process.env.SMTP_PORT || 587);
  const user = process.env.SMTP_USER;
  const pass = process.env.SMTP_PASS;
  const from = process.env.SMTP_FROM;

  if (!host || !user || !pass || !from) {
    throw new Error("SMTP configuration missing. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM.");
  }

  return nodemailer.createTransport({
    host,
    port,
    secure: port === 465,
    auth: { user, pass },
  });
}

export async function generateAiReply({ name, role }) {
  const apiKey = process.env.OPENAI_API_KEY;
  const founder = getFounderSignature();

  if (!apiKey) {
    return [
      `Hi ${name},`,
      "",
      "thnks for being a part of our team.",
      "Your early access request for MarketMind has been received.",
      `We will share your invite soon with a role-tailored setup for ${role}.`,
      "",
      `Founder: ${founder.name}`,
      `Phone: ${founder.phone}`,
      `Socials: ${founder.socials}`,
    ].join("\n");
  }

  try {
    const client = new OpenAI({ apiKey });
    const response = await client.responses.create({
      model: process.env.OPENAI_MODEL || "gpt-4o-mini",
      input: [
        {
          role: "system",
          content:
            "You draft concise onboarding emails. Keep tone warm and professional. Include the exact phrase 'thnks for being a part of our team'.",
        },
        {
          role: "user",
          content: `Write a short welcome email for ${name}, role: ${role}. Include founder signature details: ${founder.name}, ${founder.phone}, ${founder.socials}.`,
        },
      ],
    });

    const text = response.output_text?.trim();
    if (!text) {
      throw new Error("AI did not return email text");
    }

    return text.includes(REQUIRED_PHRASE) ? text : `${text}\n\n${REQUIRED_PHRASE}`;
  } catch {
    return [
      `Hi ${name},`,
      "",
      "thnks for being a part of our team.",
      "Your early access request for MarketMind has been received.",
      `We will share your invite soon with a role-tailored setup for ${role}.`,
      "",
      `Founder: ${founder.name}`,
      `Phone: ${founder.phone}`,
      `Socials: ${founder.socials}`,
    ].join("\n");
  }
}

export async function sendEmail({ to, subject, text }) {
  const transporter = createTransport();
  const from = process.env.SMTP_FROM;
  await transporter.sendMail({ from, to, subject, text });
}

export async function sendWelcomeEmail({ name, email, role }) {
  const text = await generateAiReply({ name, role });
  const subject = process.env.WELCOME_SUBJECT || "Welcome to MarketMind Early Access";
  await sendEmail({ to: email, subject, text });
}

# MarketMind Backend Setup

## 1) Deploy backend (Render quick path)

1. Create a new Render web service from this repo.
2. Use `backend/render.yaml` (or set root dir `backend`).
3. Add env vars from `backend/.env.example`.

## 2) Configure frontend

Edit `/site-config.js`:

```js
window.MARKETMIND_CONFIG = {
  waitlistEndpoint: "https://<your-render-domain>/api/waitlist",
  founderName: "Your Full Name",
  founderPhone: "+1-...",
  founderSocial: "https://x.com/<yourhandle>",
  modelVersion: "v1.0",
};
```

## 3) Test signup

Submit the waitlist form on the site and verify:
- entry appears in backend `GET /api/waitlist` (with admin token)
- welcome email arrives in inbox

## 4) Send campaign to all signups

```bash
curl -X POST \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"subject":"MarketMind Founder Update"}' \
  https://<your-render-domain>/api/campaign/send
```

This sends AI-generated replies and always includes:
`thnks for being a part of our team`

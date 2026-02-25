# MarketMind Backend

Collects early-access emails and sends automatic AI-powered replies.

## Features

- `POST /api/waitlist`: stores subscriber and sends welcome mail
- `GET /api/waitlist`: admin-only list of all subscribers
- `POST /api/campaign/send`: admin-only broadcast to all subscribers
- JSON persistence at `backend/data/waitlist.json`

## Setup

```bash
cd backend
npm install
cp .env.example .env
# fill .env values
npm run start
```

Server runs on `http://localhost:8080` by default.

## Frontend hookup

Set in `script.js`:

```js
const WAITLIST_ENDPOINT = "https://your-backend-domain/api/waitlist";
```

## Admin usage

List waitlist:

```bash
curl -H "Authorization: Bearer <ADMIN_TOKEN>" http://localhost:8080/api/waitlist
```

Broadcast to all:

```bash
curl -X POST \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"subject":"MarketMind Founder Update"}' \
  http://localhost:8080/api/campaign/send
```

## Required phrase in replies

Every AI/fallback message includes this exact text:

`thnks for being a part of our team`

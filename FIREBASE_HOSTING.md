# Firebase Hosting Setup (MarketMind)

## 1) Install and login (run on your local machine)

```bash
npm install -g firebase-tools
firebase login
```

## 2) Set your Firebase project id

Edit `.firebaserc` and replace:

- `your-firebase-project-id` -> your real Firebase project id

Or run:

```bash
firebase use --add
```

## 3) Deploy

From repo root:

```bash
firebase deploy --only hosting
```

## 4) Verify

Firebase will print URLs like:

- `https://<project-id>.web.app`
- `https://<project-id>.firebaseapp.com`

## 5) Connect custom domain

In Firebase Console:

- Hosting -> Add custom domain
- Use `marketmind24.shop`
- Follow Firebase DNS verification steps

## Notes

- Current `firebase.json` deploys static frontend files from repo root.
- Backend (`backend/`) and ML pipeline (`marketmind_ml/`) are excluded from Hosting deploy.
- If you keep GitHub Pages custom domain active, avoid using the same domain simultaneously on Firebase.

# Morning Digest — Setup Walkthrough

End-to-end setup for your personal Morning Digest PWA + daily Claude-generated briefing.

You'll do this once. After that, the app runs itself: every morning at **8:00 AM Brisbane time** the GitHub Action fetches data, generates the digest, commits it to the repo, and fires a push notification to your phone. You open the home screen icon — digest is there.

---

## Overview of what you're setting up

| Piece | What it does | Where it lives | Cost |
|---|---|---|---|
| GitHub repo | Stores the code + the daily JSON digest | github.com | Free |
| GitHub Actions | Runs the digest script daily at 8 AM AEST | github.com | Free (well under quota) |
| Vercel | Hosts the PWA frontend | vercel.com | Free (hobby tier) |
| OneSignal | Sends push notifications to your phone | onesignal.com | Free |
| Claude API | Generates the digest summary | console.anthropic.com | ~5-15c AUD per day |

**Total ongoing cost: ~$2-5 AUD/month** (just Claude API usage).

---

## Step 1 — Create the GitHub repo (5 min)

1. Open [github.com/new](https://github.com/new).
2. **Repository name:** `morning-digest`
3. **Visibility:** Private (recommended) — keeps your portfolio config out of public view.
4. Leave everything else default. **Don't** initialise with a README, .gitignore, or license — we already have those.
5. Click **Create repository**.

GitHub will show you the push instructions. Run these from the project folder:

```bash
cd ~/Documents/morning-digest
git init
git branch -M main
git add .
git commit -m "Initial commit: morning digest scaffold"
git remote add origin https://github.com/Possum-Parker/morning-digest.git
git push -u origin main
```

If git asks you to log in, use a [Personal Access Token](https://github.com/settings/tokens) instead of your password (GitHub has required this for years). When generating one, scope it to `repo` access.

---

## Step 2 — Add your Claude API key as a GitHub secret (2 min)

1. Go to your new repo on github.com → **Settings** (top tab) → **Secrets and variables** → **Actions**.
2. Click **New repository secret**.
3. Name: `ANTHROPIC_API_KEY`
4. Secret: paste your Claude API key from [console.anthropic.com](https://console.anthropic.com)
5. Click **Add secret**.

GitHub encrypts this — you can never view it again, only update or delete it. The workflow file reads it as an environment variable at runtime.

---

## Step 3 — Test the digest generator locally (5 min)

Before wiring up the cron job, let's confirm everything works end-to-end on your Mac.

```bash
cd ~/Documents/morning-digest
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt

export ANTHROPIC_API_KEY="sk-ant-..."   # paste your key, this stays in terminal memory only
python scripts/generate_digest.py
```

You should see:

```
[digest] gathering raw data…
[digest] got 8 holdings, 6 indicators.
[digest] calling Claude for summary…
[digest] wrote /Users/ryanparker/Documents/morning-digest/data/latest.json
[push] OneSignal credentials not set — skipping push notification.
```

Open `data/latest.json` and you'll see a real, generated digest. If anything errors, run it again — yfinance occasionally rate-limits.

When happy:

```bash
git add data/latest.json
git commit -m "Test digest"
git push
deactivate
```

---

## Step 4 — Deploy the PWA to Vercel (5 min)

1. Go to [vercel.com/signup](https://vercel.com/signup) and **sign up with your GitHub account**. This gives Vercel permission to see your repos.
2. After signup, click **Add New… → Project**.
3. Pick the `morning-digest` repo.
4. **Root Directory:** click "Edit" and set it to `web`.
5. **Framework Preset:** Next.js (auto-detected).
6. **Environment Variables** — add these now (they're public, fine to embed):
   - `NEXT_PUBLIC_GITHUB_OWNER` = `Possum-Parker`
   - `NEXT_PUBLIC_GITHUB_REPO`  = `morning-digest`
   - `NEXT_PUBLIC_GITHUB_BRANCH` = `main`
   - (We'll add `NEXT_PUBLIC_ONESIGNAL_APP_ID` in Step 5 once we have it.)
7. Click **Deploy**.

After ~1 minute Vercel gives you a live URL like `https://morning-digest-xyz.vercel.app`. Open it in any browser — you'll see the placeholder digest. Open it in Safari on your iPhone to test the install flow:
- Tap the **Share** button (square with up-arrow) in Safari.
- Scroll down → **Add to Home Screen**.
- Tap **Add** in the top-right.

You'll now see a Morning Digest icon on your home screen. Tap it — full screen, no browser chrome, behaves like a real app.

---

## Step 5 — Set up OneSignal for push notifications (10 min)

1. Sign up at [onesignal.com](https://onesignal.com) (free).
2. Click **New App/Website**, name it `Morning Digest`.
3. Choose **Web** as the platform → **Typical Site**.
4. **Site URL:** paste your Vercel URL (e.g. `https://morning-digest-xyz.vercel.app`)
5. **Default icon:** upload `web/public/icon-192.png` from your repo.
6. Click **Save**. OneSignal gives you:
   - An **App ID** (looks like a UUID)
   - A **REST API Key** (under Settings → Keys & IDs)

Now add these to GitHub and Vercel:

**GitHub** (Settings → Secrets and variables → Actions):
- New secret: `ONESIGNAL_APP_ID` = (paste App ID)
- New secret: `ONESIGNAL_REST_API_KEY` = (paste REST API Key)
- New variable (under "Variables" tab, not secrets): `PWA_URL` = your Vercel URL

**Vercel** (Project Settings → Environment Variables):
- Add `NEXT_PUBLIC_ONESIGNAL_APP_ID` = (paste App ID)
- Click **Save**, then **Redeploy** the latest deployment so the change picks up.

After redeploy, open the PWA from your home screen, allow notifications when prompted, and you're subscribed.

---

## Step 6 — Trigger the workflow manually to verify (2 min)

1. Go to your repo on github.com → **Actions** tab.
2. Click **Daily Digest** in the left sidebar.
3. Click **Run workflow** → **Run workflow** (green button).
4. Watch it run — should complete in ~30-60 seconds.
5. Once green, check:
   - `data/latest.json` in the repo now has a fresh digest with today's date.
   - Your phone gets a push notification.
   - Opening the home screen app shows the fresh digest.

From here, it runs automatically every day at 22:00 UTC = 08:00 AEST.

---

## Maintenance

- **Add/remove tickers:** edit `config/portfolio.json`, commit, push. Takes effect next run.
- **Tweak news topics or exclude words:** edit `config/topics.json`.
- **Change tone or sections:** edit `SYSTEM_PROMPT` in `scripts/claude_summary.py`.
- **Run on demand:** Actions tab → Daily Digest → Run workflow.
- **See past digests:** they're in git history under `data/latest.json`.

## Troubleshooting

- **PWA shows old data:** the page already cache-busts with `?ts=`. If you still see stale data, force-quit the app and reopen.
- **No push notification:** make sure you allowed notifications when prompted, and that you opened the PWA *from the home screen icon* (not Safari) — iOS only delivers PWA pushes when launched from the home screen.
- **Action fails on `yfinance`:** Yahoo occasionally rate-limits. Re-run the workflow; usually fine on second try.
- **Action fails on Claude:** check `ANTHROPIC_API_KEY` is set in repo secrets and your Anthropic account has credit.

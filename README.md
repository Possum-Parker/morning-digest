# Daily Digest

A personal, AI-generated daily briefing for an Australian investor.

- **What you get:** every morning at 8 AM Brisbane time, an opinionated digest covering your share portfolio, global markets & commodities, Australian politics, the AI industry, and major sport — delivered as a PWA on your phone with a push notification.
- **Who it's for:** just you. This is a personal repo. Keep it private.

## Architecture

```
┌──────────────────────────┐    08:00 AEST daily     ┌──────────────────────────┐
│  GitHub Actions (cron)   │ ──────────────────────► │  scripts/generate_       │
│                          │                          │  digest.py               │
└──────────────────────────┘                          │   • yfinance (prices)    │
                                                      │   • Google News RSS      │
                                                      │   • Claude API (summary) │
                                                      └────────────┬─────────────┘
                                                                   │
                                              writes data/latest.json + push
                                                                   │
                ┌──────────────────────────┐                        ▼
                │   iPhone home screen     │      reads JSON     ┌──────────────────┐
                │   PWA (Next.js/Vercel)   │ ◄──────────────────│  GitHub repo     │
                └──────────────────────────┘                     └──────────────────┘
```

## Project layout

```
config/             Portfolio holdings + news topics (edit these to tweak)
scripts/            Python: fetch prices, fetch news, call Claude, send push
web/                Next.js PWA frontend
data/latest.json    Today's digest (overwritten daily by the Action)
.github/workflows/  GitHub Actions cron job
docs/SETUP.md       Step-by-step deployment walkthrough
```

## Setup

See [docs/SETUP.md](docs/SETUP.md) for the full walkthrough.

## Cost

- GitHub Actions, Vercel hobby, OneSignal: **free**
- Claude API: **~$2-5 AUD/month** for one digest a day

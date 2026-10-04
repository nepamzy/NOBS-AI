# NOBS AI — Spend Tracker

Live ledger of every real-money cost for this project. Updated whenever
something is added, changed, or stopped. "Estimated" = not yet confirmed
against a real invoice; "Confirmed" = matches an actual bill/receipt.

**Status key:** 🟢 Active (billing now) · 🟡 Pending (set up, not billing yet) · 🔴 Stopped/Cancelled

---

## Fixed monthly hosting

| Service | Category | Plan | Cost/month | Status | Notes |
|---|---|---|---|---|---|
| Render — Web Service (`nobs-ai-api`) | Hosting | Free tier | $0 | 🟢 Active | Sleeps after ~15min idle |
| Render — Background Worker | Hosting | Starter (estimated) | ~$7 (ESTIMATED) | 🟢 Active | Runs pipeline jobs; not yet confirmed against an actual Render invoice |
| Redis Cloud | Hosting | Free tier (30MB) | $0 | 🟢 Active | Replaced Render's paid Redis add-on |
| Render — paid Redis (`nobs-ai-redis`) | Hosting | Starter | $10 | 🔴 Cancelled | Was running since Sep 7 unnoticed; deleted per your instruction |
| Supabase | Database/Storage | Free tier | $0 | 🟢 Active | Postgres + file storage |
| Vercel | Hosting | Free tier (Hobby) | $0 | 🟢 Active | Frontend only |

**Fixed monthly subtotal (confirmed-free items excluded): ~$7/month ESTIMATED**

---

## Usage-based (only bills when actually used)

| Service | Category | Billing type | Rate | Status | Notes |
|---|---|---|---|---|---|
| Runpod | GPU | Hourly while pod runs + storage while it exists | $0.74/hr (RTX 4090) + $0.10-0.20/GB storage | 🟡 Pending | $10 minimum credit required to deploy — not yet added/confirmed as of this message |
| Anthropic API (LLM — script/research/assistant) | LLM | Per-token | Varies by call | 🟢 Active (key set) | No real video generated end-to-end yet, so real spend so far ≈ $0, but the key is live and chat-use this session does cost real tokens |
| Chatterbox (self-hosted) | TTS | N/A — free software | $0 | 🟡 Pending | Open-source, no per-call cost; only cost is whatever hardware runs it (your own PC = free, Runpod = above) |

---

## One-time / not recurring

| Item | Cost | Date | Notes |
|---|---|---|---|
| (none yet) | — | — | — |

---

## Open questions / needs your confirmation

- [ ] Confirm exact Render Background Worker plan/price from your Render billing page (currently an estimate)
- [ ] Confirm whether the $10 Runpod credit was actually added
- [ ] Decide: Chatterbox local-only (free) vs. Runpod-hosted (paid) — affects the "Pending" row above

*Last updated: 2026-10-04*

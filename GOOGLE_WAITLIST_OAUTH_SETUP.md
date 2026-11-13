# Waitlist "Continue with Google / YouTube" setup

The public landing pages (apps/web/src/landing, `/waitlist`) has two sign-in buttons
alongside the plain email form: "Continue with Google" and "Continue with
YouTube." Both are code-complete and gated exactly like every other
external engine in this app (Wan, Chatterbox, the Gmail/GitHub/Vercel
connectors) — they do nothing until you do the one-time setup below, and
fail gracefully (a friendly message on the page, not a broken link) until
then.

This is a **different kind of OAuth** from the Gmail/YouTube connectors
elsewhere in this app. Those are pre-authorized once, by you, for your own
account (you run a one-time flow and paste a refresh token into Render).
This one runs a real, live consent screen for a stranger clicking a public
button on the waitlist page — no refresh token is stored, it just reads
their verified email (and, for the YouTube button, their channel name) once
and creates a waitlist signup.

## What each button does

- **Continue with Google**: asks for `openid email profile` — just a
  verified email + name, used to join the waitlist without typing it.
- **Continue with YouTube**: asks for the same, plus
  `youtube.readonly` — lets us also show their YouTube channel name as a
  qualifying signal on who's on the waitlist. **Read-only, nothing is
  uploaded/changed/deleted on their channel.**

## ⚠️ Read this before setting it up: the YouTube button has a real limitation

Google treats `youtube.readonly` as a **sensitive scope**. For an app in
"Testing" mode, that scope only works for Google accounts you've explicitly
added as test users (up to 100) — it will NOT work for a random visitor
clicking the button on your public waitlist page. To make it work for
everyone, Google requires an **app verification process** (a privacy policy
URL, a demo video showing the consent flow, and a review by Google that can
take real time — days to weeks, not minutes, and isn't guaranteed to be
approved quickly for a small/solo project).

**Practical recommendation:** set up the "Continue with Google" button
first (plain `openid email profile` isn't a sensitive scope — it works for
any public visitor immediately, no verification needed). Treat "Continue
with YouTube" as optional/future — it'll work for you and anyone you add as
a test user right away, but won't work for the general public until you've
gone through Google's verification, if you decide that's worth it.

## One-time setup

1. Go to https://console.cloud.google.com
2. Create a new project (or reuse the one from Gmail/YouTube connector
   setup — a project can hold multiple OAuth clients)
3. "APIs & Services" → "OAuth consent screen":
   - Choose "External"
   - App name, support email, developer email
   - Scopes: add `openid`, `email`, `profile`, and (only if you want the
     YouTube button to eventually work publicly)
     `https://www.googleapis.com/auth/youtube.readonly`
   - Test users: add your own Google account (and anyone else you want the
     YouTube button to work for before full verification)
4. "APIs & Services" → "Library" → search "YouTube Data API v3" → Enable
   (only needed for the YouTube button's channel-name lookup)
5. "APIs & Services" → "Credentials" → "Create Credentials" → "OAuth
   Client ID" → type **"Web application"**:
   - Authorized redirect URIs — add BOTH:
     - `<your Render backend URL>/waitlist/oauth/google/callback`
     - `<your Render backend URL>/waitlist/oauth/youtube/callback`
6. Note the resulting `client_id` and `client_secret`

## Add to Render

```
GOOGLE_WAITLIST_CLIENT_ID=<from step 6>
GOOGLE_WAITLIST_CLIENT_SECRET=<from step 6>
API_BASE_URL=<your Render backend's public URL, e.g. https://nobs-ai-api.onrender.com>
LANDING_BASE_URL=<the public site URL — the same site as the dashboard, e.g. https://nobs-ai.vercel.app>
```

`API_BASE_URL` must exactly match the redirect URIs registered in step 5 —
Google rejects the request otherwise.

## Using it

Nothing to do — once those four values are set and the backend redeploys,
both buttons on `/waitlist` work immediately. Signups from either path show
up in `GET /admin/waitlist` with `source: "google_oauth"` or
`"youtube_oauth"`, and the YouTube path also carries
`youtube_channel_title` when Google grants that scope.

# YouTube upload setup

Uploads a finished video to YouTube as **private**, always — there is no
setting, flag, or code path that makes it public on upload. Making a video
public (`publish_video`) is a separate, deliberate action you (or the
assistant, only when you explicitly ask it to, by name, for that specific
video) take afterward, after actually watching the result.

This uses its own Google OAuth client — separate from the one Gmail uses,
because it needs a different scope (`youtube.upload`, not Gmail's).

## One-time setup

1. Go to https://console.cloud.google.com
2. Create a new project (or reuse the one from Gmail's setup — a project
   can hold both OAuth clients, you'll just add a second one here)
3. "APIs & Services" → "Library" → search "YouTube Data API v3" → Enable
4. "APIs & Services" → "OAuth consent screen" (skip if you already did
   this for Gmail — same consent screen can cover both):
   - Choose "External"
   - App name, support email, developer email
   - Scopes: add `https://www.googleapis.com/auth/youtube.upload`
   - Test users: add your own Google account
5. "APIs & Services" → "Credentials" → "Create Credentials" → "OAuth
   Client ID" → type "Desktop application" → name it
6. Download the resulting JSON, note `client_id` and `client_secret`
7. Get a refresh token (run locally, once):
   ```python
   from google_auth_oauthlib.flow import InstalledAppFlow

   SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
   flow = InstalledAppFlow.from_client_secrets_file("google_oauth.json", SCOPES)
   credentials = flow.run_local_server(port=8080)
   print("GOOGLE_YOUTUBE_REFRESH_TOKEN=", credentials.refresh_token)
   ```
   (needs `pip install google-auth-oauthlib` first; a browser window opens
   for you to approve access to your own channel)

## Add to Render

```
GOOGLE_YOUTUBE_CLIENT_ID=<from step 6>
GOOGLE_YOUTUBE_CLIENT_SECRET=<from step 6>
GOOGLE_YOUTUBE_REFRESH_TOKEN=<from step 7>
```

## Using it

Once a video reaches COMPLETED, ask the assistant (chat or voice) to
upload it — it'll call `youtube_upload_video` and come back as private.
Watch it in YouTube Studio, then, when and only when you're happy with it,
explicitly ask the assistant to publish that specific video — it calls
`youtube_publish_video`, the one and only thing that makes it public.

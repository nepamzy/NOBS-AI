# NOBS AI — Full Project Context for Claude Code

**Owner:** Nobert Agu
**Objective:** Build a personal YouTube automation AI (V1), later expanding to business automation + a general assistant. All under one system called NOBS AI.

Read this entire file before doing any work in this project.

---

# PART 1 — OPERATING RULES (NON-NEGOTIABLE)

You may freely: plan, research, design, write code, create/edit local files, run local tests/dev servers, prepare configs/Dockerfiles/Terraform, propose architecture, identify costs, explain trade-offs.

You MUST STOP and ask Nobert before:
- Spending money in any form (paid API calls, GPU rentals, subscriptions, domain purchases, paid storage/DBs, paid model inference)
- Starting a paid cloud resource (e.g. a Runpod GPU pod/endpoint)
- Connecting or authorizing an external account (Runpod, YouTube, GitHub remote, cloud provider, payment info)
- Any irreversible or externally-visible action (publishing, production deployment, deleting real data/resources, force-pushing git history, sending external messages/emails)

## Cost warning format (use before ANY action that may cost money)
```
### PAYMENT / COST WARNING
Action:
Service:
Expected cost:
Billing type: Hourly / per request / per token / monthly / usage-based / unknown
Maximum expected cost for this action:
Risk: Low/Medium/High/Unknown
Why it is needed:
Approval required: YES
```
Then STOP and wait for Nobert. Never bury this inside a long explanation. Never say "I'll run this" if it might incur a charge — say what it costs BEFORE the charge happens.

## Unknown cost rule
If cost can't be determined confidently: say "COST UNKNOWN — I need your approval before proceeding," then research pricing if permitted. If still unclear: "I cannot confidently determine the cost. I recommend we do not execute this action until the cost is confirmed."

## Free vs paid — quick reference
**Safe without extra approval:** writing/editing local code, reading/analyzing files, local dev servers, static analysis, mock data/API responses, planning infra, preparing Dockerfiles/Terraform, researching pricing, UI design, implementation plans.

**Approval required:** paid API calls, GPU rentals (Runpod etc.), cloud deployments, paid model inference (video/voice gen at scale), paid storage/DB, domain purchases, subscription upgrades, production deployment, sending external comms, publishing content, uploading to YouTube, public repos, changing/deleting production infra.

## Spending & budget tracking
Once paid infra is in use, track: Estimated cost, Actual cost, Purpose, Date, Service, Project/video — categorized as GPU / LLM / TTS / Video Generation / Storage / Database / Hosting / Networking / Domain / Other. Mark anything not measured directly as **ESTIMATED**. Warn Nobert if a task may exceed budget, needs unusually high GPU time, requires many retries, or a resource could keep billing after the task completes. Recommend the cheapest reasonable test first (e.g. one 8-second test clip before a full render).

## Never leave paid resources running
Watch resources that bill by time (GPU pods, VMs, DB instances, containers, inference endpoints). Tell Nobert when something starts billing, stops billing, needs manual shutdown, or could keep charging after the task completes. Propose shutdown when safe; ask approval if externally consequential.

## Credentials & secrets
Never ask Nobert to paste API keys, passwords, tokens, credit card numbers, or recovery codes into chat or source code. Use `.env`/`.env.local`/secret managers instead. Never commit secrets to git. If an exposed secret is discovered, warn Nobert immediately.

## Account authorization
Stop when an action needs Nobert to log into a service, authorize OAuth, connect an external account, enter payment info, or accept terms (Runpod, YouTube, GitHub, cloud providers, etc.). Explain exactly what Nobert needs to do.

## Clarification rule
Ask a concise question when multiple reasonable interpretations exist AND choosing wrong could waste significant time/money, change architecture, delete data, or cause major rework. Otherwise, don't ask — see next section.

## When NOT to ask
If a decision is reversible, free, doesn't affect external systems, doesn't significantly change product direction, and follows existing architecture/conventions — just make the call and briefly document it. Don't interrupt Nobert for trivial implementation choices.

## Architecture change rule
If existing architecture needs to change, explain: current approach → problem discovered → proposed change → why necessary → advantages → disadvantages → cost implications → migration impact → whether approval is required. Never silently replace major architecture.

## Destructive action rule
STOP → EXPLAIN → ASK → WAIT before: deleting important files/DBs, dropping tables, destroying infra, removing production resources, force-resetting git history, overwriting significant existing work, deleting generated assets permanently.

## Production rule
Dev/test/production are separate environments — never assume dev = production. Before any production action, identify: environment, target, expected impact, rollback strategy, cost, downtime risk, data risk. Production deployment always requires explicit approval.

## Test-first cost control
For expensive operations, escalate gradually: LOCAL MOCK → SMALL TEST → SINGLE SCENE → SHORT VIDEO → FULL VIDEO. Never jump straight to a large paid generation.

## Licensing rule
Before integrating any open-source model/component: check license, commercial-use restrictions, redistribution/attribution requirements. If unclear, stop and inform Nobert before production use.

## Research rule
Use current information for anything that changes (pricing, capabilities, APIs). Prefer official docs. Never invent capabilities or prices. Clearly flag uncertainty.

## No fake completion
Never claim "Done," "Deployed," "Uploaded," "Tested," "Generated," or "Verified" unless actually performed/verified.
- Only prepared → "Prepared, not executed."
- Only estimated → "Estimated, not measured."
- Only planned → "Planned, not implemented."

## No invented information
Never invent API capabilities, pricing, model capabilities, GPU performance, generation speed, licensing terms, deployment status, or test results. Say "Unknown — needs verification" instead.

## Error handling
On failure, report: WHAT FAILED / WHY IT APPEARS TO HAVE FAILED / WHAT WAS ATTEMPTED / WHAT REMAINS WORKING / PROPOSED FIX / COST IMPLICATION / NEXT ACTION. Continue only if the fix is safe and approved.

## Phase control
Always know the current phase. Before starting a new major phase, run through: CURRENT PHASE → OBJECTIVE → REQUIREMENTS → DEPENDENCIES → IMPLEMENTATION → TESTING → APPROVAL → NEXT PHASE. Don't silently jump phases.

## The one rule that matters most
**Claude may think ahead, but it must not spend ahead.** No payment, no unexpected billing, no paid GPU, no paid API usage, no subscription, no production deployment, no external publishing, no destructive action — without approval.

---

# PART 2 — PRODUCT SCOPE

**V1 (current phase — build this only):** YouTube automation for a SINGLE user (Nobert).

Pipeline: `Topic → Research → Script (scene-structured) → Storyboard → Approval → Video Engine (Wan) + Voice Engine (Chatterbox) → FFmpeg Assembly → Captions → Thumbnail → Final MP4`

**Explicitly OUT of scope for V1** (don't build even if it seems like a logical next step):
- Multi-user accounts
- Business automation agent
- General day-to-day assistant chat product
- Automatic YouTube publishing (V2)
- Analytics-driven content intelligence (V3)

**V2 (later, needs approval to start):** YouTube API upload/scheduling/publishing automation.
**V3 (later):** Analytics feedback loop (which videos/topics/hooks/thumbnails perform) informing future generation.

**Eventual long-term vision (not now):** NOBS AI branches into three specialized agents — YouTube AI, Business AI, Personal AI — but V1 must work standalone first.

---

# PART 3 — FULL APPLICATION STRUCTURE

## Core objective
User gives NOBS AI a prompt like "Create a 3-minute YouTube video about 5 mistakes new developers make." NOBS AI handles: Idea → Research → Script → Scenes → Video → Voice → Assembly → Captions → Final MP4. Initially single-user (Nobert only).

## Interface concept
Professional creative-studio style app. Sidebar: Dashboard, Create, Projects, Scripts, Videos, Assets, Settings. Main "Create Video" screen: a prompt box for the topic, plus Duration / Voice / Style selectors, and a Create Video button. The user should never need to understand Wan, Chatterbox, FFmpeg, GPUs, Runpod, or job queues — those are internal.

## Dashboard
Shows a greeting, stat cards (Videos total, This Week's count vs goal, Processing count), and a Recent Projects list with status (Completed / Processing %) and quick actions.

## Create Video flow (guided, not one big form)
**Step 1 — Topic.** Text input for the topic, plus optional toggles: let NOBS AI research the topic / I already have research / I already have a script.

## Research engine
When enabled, runs and displays a live checklist: finding info → comparing sources → identifying key facts → building story angles → checking conflicting info. Output is **structured data**, not a blob of text:
```
Research
├── Topic
├── Key facts
├── Statistics
├── Sources
├── Interesting findings
├── Counterarguments
└── Story opportunities
```

## Script engine
Produces title, estimated duration, word count, hook, and numbered scenes with Regenerate / Edit / Approve actions.

**Critical architectural decision:** store the script as structured scenes, not a flat text blob:
```
Video
 ├── Scene 1 → narration, visual_prompt, duration, transition
 ├── Scene 2 → narration, visual_prompt, duration, transition
 └── Scene N
```
This structure is what makes the video-generation stage tractable.

## Storyboard
Before spending any GPU credits, show the full scene-by-scene plan (narration + visual description + duration + preview) for explicit approval. Flow must be: **Script → Storyboard → Approval → GPU generation** — never generate first and discover a bad script after the fact.

## Video generation
Uses Wan for text-to-video, but Wan must sit behind an abstraction layer (`NOBS AI → VIDEO ENGINE → Wan`) so Runway/Kling/Luma/Veo/Pika can be added later without rebuilding the app.

**Key change from the original plan:** generate short clips (5–12 seconds) per scene — not one long 3-minute generation. A 3-minute video = ~15–25 scenes/clips, assembled after with FFmpeg. This allows regenerating a single bad scene instead of the whole video, and is a major architectural advantage.

## GPU infrastructure
The application server never runs the GPU permanently. Flow: `NOBS AI SERVER → request GPU → RUNPOD → GPU WORKER → WAN → generated clips → Object Storage`. The GPU disappears when the job finishes — this is what keeps fixed infrastructure cheap. **Every GPU provisioning action is a paid, approval-required action per Part 1.**

## Voice engine
Uses Chatterbox, also behind an abstraction (`VOICE_ENGINE → Chatterbox | ElevenLabs | OpenAI TTS | future`), so providers can change later without rebuilding.

## Audio + video assembly
FFmpeg combines: scene video clips + voiceover + music + captions → final MP4 (e.g. `NOBS_AI_FINAL.mp4`).

## Captions
First-class pipeline: Voice → speech recognition → word timestamps → subtitle generator → styled captions → FFmpeg. Eventually offer styles: Minimal, YouTube, Bold, Cinematic, Highlight.

## Thumbnail generation
After the video completes, generate several thumbnail options (A/B/C) for the user to pick from.

## Project page
Each video is a "project" showing pipeline status checklist (Research/Script/Storyboard/Voice/Video/Assembly/Captions), an embedded video player, and an Assets list (Script, Voiceover, each Scene, Thumbnail, Captions, Final Video).

## Backend architecture
```
NOBS AI
  Web Application
    API / Backend
      ├── AI CORE (LLM Router → Script / Research / Planning)
      ├── JOB SYSTEM (Queue)
      └── DATABASE (PostgreSQL)

JOB SYSTEM
  ├── Video Job   → Runpod → Wan
  ├── Voice Job   → CPU/GPU → Chatterbox
  └── Render Job  → FFmpeg → Assembly
```

## Recommended folder/layer structure
```
apps/
  web/       → NOBS AI interface
  worker/    → background processing

services/
  ai/
    script/
    research/
    orchestration/
  video/
    wan/
    generation/
  voice/
    chatterbox/
  rendering/
    ffmpeg/
  storage/
```

## Database (PostgreSQL)
Tables: users, projects, videos, scripts, scenes, voiceovers, video_clips, assets, render_jobs, generation_jobs, research, research_sources, thumbnails, settings.

Relationship shape:
```
USER → PROJECT → VIDEO
                   ├── SCRIPT → SCENES
                   ├── RESEARCH
                   ├── VOICEOVER
                   ├── VIDEO CLIPS
                   ├── THUMBNAIL
                   └── FINAL RENDER
```

## Job/queue system — critical
Never make the web request wait on Wan's generation time. Correct flow:
```
Browser → API → Create Job → Queue → "Processing..."
Queue → Worker → Runpod → Wan → Storage → Database → Notification
```
Frontend polls/receives real progress (e.g. "Generating video... 72% — Scene 8 of 11").

## Full production pipeline
```
USER → TOPIC → RESEARCH → LLM → SCRIPT → STORYBOARD → USER APPROVAL
  → [VIDEO ENGINE (Wan) + VOICE ENGINE (Chatterbox)] → ASSETS
  → FFmpeg → CAPTIONS → FINAL RENDER → THUMBNAIL → COMPLETED
```

## V1 infrastructure (keep deliberately simple)
```
INTERNET → NOBS AI WEB → API SERVER → [PostgreSQL, Redis, Storage]
API SERVER → JOB QUEUE → WORKER → RUNPOD → WAN → Chatterbox → FFmpeg → Final MP4
```

## V1 scope (repeated for emphasis)
Input: Topic. AI: Research, Script, Storyboard. Generation: Wan, Chatterbox. Production: FFmpeg, Captions. Output: MP4, Thumbnail. That's it — nothing more for V1.

## V2 (future, needs approval before starting)
YouTube API integration: automatic upload → title/description/tags/thumbnail → schedule → publish.

## V3 (future)
YouTube Analytics feedback loop: which videos/topics/hooks/thumbnails/retention patterns perform best → informs what to generate next. At this point NOBS AI moves from "makes videos" to "learns what performs and decides what to make."

## Long-term three-AI vision (not now)
```
NOBS AI → YOUTUBE AI (automation) | BUSINESS AI (automation) | PERSONAL AI (assistant)
```
Do not build these three in parallel. Get YouTube Automation V1 fully working first, then expand.

## Build order
1. Product architecture ✅
2. UX/UI design (design the complete application)
3. Backend foundation (database, auth, API, jobs, storage)
4. AI orchestration (LLM → research → script → storyboard)
5. Voice engine (Chatterbox)
6. Video engine (Wan + Runpod)
7. Rendering engine (FFmpeg + audio + captions)
8. Project management (assets, projects, history, regeneration)
9. Testing (generate real 3-minute videos repeatedly)
10. YouTube integration (upload/schedule/publish) — V2, needs approval
11. Analytics (use performance data to improve future videos) — V3
12. Automation (three videos per week, hands-off)

---

# PART 4 — COST BASELINE (research-derived estimates, re-verify before spending)

For Nobert alone (1 user), 3-min videos, 3x/week (~13 videos/month), self-hosted on-demand GPU:
- Video gen (GPU rental, on-demand only): ~$1–$6.50/month
- Voiceover (Chatterbox self-hosted or cheap TTS): ~$1.75/month
- Script generation LLM calls: under $1/month
- Basic backend hosting (non-GPU): ~$10–15/month
- **Total estimate: ~$13–24/month**

GPU rental options identified (verify current rates before committing spend):
- Vast.ai — cheapest, ~$1.10–2.00/hr for A100 80GB
- Runpod — ~$1.19–1.99/hr for A100 80GB, most ready-made Wan templates/community support (best starting point)
- Jarvislabs — ~$1.49–2.69/hr, H100 tier

Note on VRAM: Wan needs 40–80GB VRAM to run. This is GPU working memory, not disk storage, and does NOT run on Nobert's local PC — it runs on the rented cloud GPU only during active generation, then releases. Only the model files themselves (~20–50GB) are stored on disk (server-side, not Nobert's laptop, in this architecture). A lighter variant, Wan T2V-1.3B, needs only ~8GB VRAM if a cheaper/lower-quality path is ever wanted.

⚠️ These are estimates from research done on 2026-09-05 — re-check current pricing before any real spend, and always issue a cost warning before provisioning anything.

Open source tools identified:
- **Video:** Wan (Alibaba) — best quality/motion, most self-hosted community support. Lighter alternative: LTX or Wan T2V-1.3B.
- **Voice:** Chatterbox — MIT license, free, strong voice cloning, has a ready-made self-hosted API server (e.g. `devnen/Chatterbox-TTS-Server` on GitHub, OpenAI-compatible endpoints). Lighter alternative: Kokoro (runs even on CPU).

---

# PART 5 — ENVIRONMENT

- OS: Windows
- Editor: VS Code, with Claude Code extension/session active (session name: "nobs ai")
- Planned stack: Python backend (FastAPI likely, TBD — confirm with Nobert if not yet decided), PostgreSQL, Redis/queue for jobs, Node.js for frontend tooling
- Python virtual environment setup in progress at project root (`venv`)

---

# PART 6 — CURRENT STATUS

Stage: 7 (Rendering engine) code-complete at the orchestration level; stages 3, 4, and 8 (backend foundation, AI orchestration, project management) are also built. Concretely: FastAPI + PostgreSQL + Redis/RQ backend, React/Vite frontend, and the full state machine (Topic → Research → Script → Storyboard → Approval → Voice → Video Generation → Assembly → Captions → Thumbnail → Completed) all exist and are tested. Voice and video generation run per scene, each clip's requested duration is synced to its scene's *measured* voiceover length (not the script's estimate), and assembly conforms clips to that length before muxing/concatenating — no drift, no manual cut-and-join. Captions burn in from real word-timestamp data; thumbnails are extracted frames (A/B/C), no paid image-gen needed.

**What's still gated, not started:** stages 5 and 6 (Voice engine, Video engine) have their abstractions and adapters (`services/voice/chatterbox`, `services/video/wan`) but no real provider is connected — `ChatterboxEngine`/`WanEngine` raise `ApprovalRequiredError` on first real use, exactly as designed, until Nobert approves a specific spend and provides `CHATTERBOX_API_URL` or `RUNPOD_API_KEY`/`WAN_ENDPOINT_ID` (or an ElevenLabs key, if that's the voice path chosen — see chat history on cost). No paid resources have been provisioned. No external accounts connected yet. Stage 9 (testing with real generated video) can't start until one of those is wired.

**Next action:** Nobert decides voice provider (Chatterbox self-hosted/free vs. ElevenLabs paid) and video provider (Wan/Runpod), approves the specific cost, and provides the corresponding `.env` value — that's the one remaining blocker before a real end-to-end video can be produced.

---

# PART 7 — COMMUNICATION STYLE

Direct, professional, no unnecessary jargon or over-explaining. When a decision is needed, give a clear recommendation rather than just listing options. Always separate "planned/prepared" from "actually done." Challenge unnecessary complexity — for every component, ask "does NOBS AI actually need this in the current phase?"

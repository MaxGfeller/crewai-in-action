# Chapter 6 — Gmail Support Inbox Flow

A CrewAI **Flow** that triages an email inbox, enriches tickets with customer context, routes to specialist crews, drafts replies, and escalates stuck cases to Slack. The example stays production-minded — it creates Gmail **drafts only** and never auto-sends.

The Flow demonstrates:

- `@start`, `@listen`, `@listen(and_(...))`, `@listen(or_(...))`, `@router`
- Typed Pydantic state with fan-out/fan-in
- `@persist` for restart/recovery
- Retry-via-router (no hidden `try/except`)
- Event listeners that record runs to `artifacts/runs/<run_id>/events.jsonl`
- `flow.plot()` for a chapter figure

## Setup

Customer data and the knowledge base live in a **separate HTTP service**, `../support-service`. This mirrors how real Flows call out to external systems over a network, rather than reaching into a local file.

Start the service first (once, in its own terminal):

```bash
cd chapter-06/support-service
cp .env.example .env
uv sync
uv run seed                         # customers: 8  orders: 20  incidents: 3  kb: 10
uv run support-service              # listens on http://127.0.0.1:8077
```

Then set up the Flow:

```bash
cd chapter-06/gmail_support_flow
cp .env.example .env                # fake mode by default
uv sync
```

You need an `OPENAI_API_KEY` in `.env` for the LLM calls (triage, specialist drafting, escalation summary).

## Run

```bash
# Single-ticket demo (happy-path billing)
uv run run-one --thread-id t_003

# Retry + escalation demo (poison ticket fails twice → Slack escalation)
uv run run-one --thread-id t_011

# Full batch (all 14 tickets)
uv run gmail_support_flow

# Chapter figure
uv run plot

# Resume a specific flow by id (after a Ctrl-C)
uv run replay --flow-id <hex>

# Smoke test: expects 1 escalation, 0 sends
uv run test
```

If the support service is down, the Flow fails fast with an instruction to start it. The Flow never falls back to a local file.

Each run writes artefacts under `artifacts/runs/<run_id>/`:

- `state.json` — terminal state snapshot
- `events.jsonl` — one line per flow event (intake, routing, LLM calls)
- `draft_<thread_id>.md` — the Gmail draft body the Flow produced

Escalations append to `artifacts/slack_outbox.jsonl` in fake mode.

## Fake vs. real providers

Controlled by `PROVIDERS_MODE` in `.env`:

- `fake` (default) — reads the inbox from `data/fixtures/inbox_tickets.json`, writes drafts to disk, records Slack posts to a JSONL audit log. No external credentials needed.
- `real` — calls Gmail via `google-api-python-client` and Slack via `slack_sdk`.

The support service is HTTP in both modes; `PROVIDERS_MODE` does not affect it.

### Real-mode Gmail setup

The Flow uses OAuth for a desktop "installed app" — simpler than a service account for a personal test inbox, and it works against any regular Gmail address.

1. **Google Cloud Console — create a project** (one-time, free). Visit <https://console.cloud.google.com/> and create or pick a project.
2. **Enable the Gmail API.** APIs & Services → Library → search "Gmail API" → Enable.
3. **Configure the OAuth consent screen.** APIs & Services → OAuth consent screen → External. Fill in the app name (e.g. "Chapter 6 demo") and a support email. On the "Test users" step add your own Gmail address — the app can stay in "Testing" mode.
4. **Create OAuth credentials.** APIs & Services → Credentials → Create Credentials → OAuth client ID → **Desktop app**. Download the JSON file (it contains `client_id` and `client_secret`). Save it somewhere outside the repo, e.g. `~/.config/gmail_support_flow/client_secret.json`.
5. **Create the label** you want the Flow to poll in Gmail's web UI (default: `book-support-demo`). Apply it to a couple of unread test emails.
6. **Point `.env` at the credentials:**
   ```env
   PROVIDERS_MODE=real
   GOOGLE_CREDENTIALS_JSON=/absolute/path/to/client_secret.json
   GMAIL_USER_EMAIL=you@example.com
   GMAIL_LABEL=book-support-demo
   ```
7. **First run opens a browser** for consent. Start by listing the Gmail API thread ids for your labelled messages:
   ```bash
   uv run list-gmail-threads
   ```
   Then process one of those ids:
   ```bash
   uv run run-one --thread-id <api-thread-id>
   ```
   Gmail's web URL uses a different id format, so don't copy the `FMfc...` value from the browser address bar. The first real-mode command caches the token to `artifacts/gmail_token.json` for future runs. Re-running does not re-prompt.

Scopes requested: **`gmail.modify` only** — enough to list, label, and create drafts. `gmail.send` is deliberately not requested.

Delete `artifacts/gmail_token.json` to force re-authentication (e.g. to switch accounts).

### Real-mode Slack setup

1. **Create a Slack app.** <https://api.slack.com/apps> → Create New App → From scratch. Pick your workspace.
2. **Add a Bot Token scope.** OAuth & Permissions → Scopes → Bot Token Scopes → add `chat:write`. (Optionally `chat:write.public` if you want the bot to post in channels it has not been invited to.)
3. **Install to workspace.** OAuth & Permissions → Install to Workspace → Allow. Copy the **Bot User OAuth Token** (starts with `xoxb-`).
4. **Invite the bot to the escalation channel** in Slack: `/invite @YourAppName` in `#support-escalations` (or whichever channel you configure).
5. **Wire up `.env`:**
   ```env
   PROVIDERS_MODE=real
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL=#support-escalations
   ```

Quick sanity check, without kicking the Flow:

```bash
uv run python -c "
from gmail_support_flow.providers.slack_real import SlackReal
ts = SlackReal().post_message(
    channel='#support-escalations',
    title='chapter 6 smoke test',
    body_markdown='ignore this message',
    severity='low',
)
print('posted ts=', ts)
"
```

### Mixing modes

`PROVIDERS_MODE` is a single switch; both Gmail and Slack follow it. To run Gmail real but Slack fake (or vice-versa), override `get_gmail_provider` / `get_slack_provider` in a small local script — or just leave `PROVIDERS_MODE=fake` and eyeball the JSONL audit files. 

## Chapter 6.6 failure simulation

The support service accepts `?simulate=fail` on every endpoint and returns a `503`. The Flow uses this to make the retry-via-router scene reproducible: thread `t_011`'s body carries a `KB-POISON` marker, and `_run_specialist` translates it into a `simulate=fail` call. The resulting `httpx.HTTPStatusError` is the exact failure shape production Flows see when an upstream misbehaves. 

## Layout

- `src/gmail_support_flow/state.py` — the flow state schema
- `src/gmail_support_flow/flow.py` — the `SupportInboxFlow` class
- `src/gmail_support_flow/services/` — HTTP client for `../support-service`
- `src/gmail_support_flow/crews/` — triage + billing + technical + feature +
  escalation specialists
- `src/gmail_support_flow/providers/` — Gmail and Slack provider protocols
- `src/gmail_support_flow/events/listeners.py` — observability listener
- `src/gmail_support_flow/persistence/store.py` — `@persist` helper + resume

## Resetting state

- To reset Customer 360 data: `cd ../support-service && uv run seed --reset`
- To reset Flow persistence (after editing `state.py`):
  `rm artifacts/flow_state.sqlite`

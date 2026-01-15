# SlackAgent Bot (A2A)

This service listens for a trigger emoji reaction on Slack messages and forwards the thread context to a generic A2A agent. It keeps per-thread context so replies stay coherent across multiple reactions.

## Why HTTP mode (no Socket Mode)

The bot uses Slack Events API with an HTTP endpoint. This fits k8s deployments and avoids Socket Mode.

## Setup

1) Create a virtual environment

```bash
uv venv
```

2) Install dependencies

```bash
uv sync
```

3) Configure environment

```bash
cp .env.example .env
```

4) Run the bot

```bash
uv run python -m slackagent
```

## Slack app configuration

- Request these OAuth scopes (add as needed for your workspace):
  - `chat:write`
  - `reactions:read`
  - `channels:history`
  - `groups:history`
  - `im:history`
  - `mpim:history`
- Enable Event Subscriptions and set the Request URL to:
  - `https://<your-host>/slack/events`
- Subscribe to bot events:
  - `reaction_added`

## Environment variables

Required:
- `SLACK_BOT_TOKEN`
- `SLACK_SIGNING_SECRET`
- `SLACKAGENT_A2A_URL` (preferred) or `KAGENT_A2A_URL` (fallback), pointing at the agent's AgentCard endpoint

Optional:
- `SLACK_APP_TOKEN` (set to enable Socket Mode for local development)
- `SLACK_TRIGGER_EMOJI` (default: `slackagent`, without surrounding colons)
- `SLACK_TRIGGER_REACTION` (default: `eyes`, added by the bot when triggering)
- `SLACK_AGENT_ACK_REACTION` (default: `white_check_mark`, added by the agent)
- `PORT` (default: `3000`)
- `HOST` (default: `0.0.0.0`)

A2A options (optional):
- `SLACKAGENT_A2A_HEADERS_JSON` or `KAGENT_A2A_HEADERS_JSON` (JSON object of headers)
- `SLACKAGENT_A2A_TRANSPORTS` (comma-separated, default: `jsonrpc,http+json`)
- `SLACKAGENT_A2A_TIMEOUT_S` (default: `600`)
- `SLACKAGENT_A2A_POLL_INTERVAL_S` (default: `0.5`)
- `SLACKAGENT_A2A_POLL_TIMEOUT_S` (default: unset)
- `SLACKAGENT_A2A_USE_EXTENDED_CARD` (default: `false`)
- `SLACKAGENT_A2A_INSECURE` (default: `false`)

## Behavior

- Add the trigger emoji (default `:slackagent:`) to any message in a thread.
- The bot sends a lightweight trigger to the agent, including channel and thread identifiers; the agent fetches the thread via Slack tools and posts the reply itself.
- The bot uses a deterministic A2A context id per Slack thread (`slack:<team>:<channel>:<thread_ts>`), so kagent stores and reuses the full context in Postgres even across restarts.

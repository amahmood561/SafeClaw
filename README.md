# SafeClaw

SafeClaw: a self-hosted agent with explicit permissions.

SafeClaw is a small terminal and WhatsApp assistant you can run on your own
computer. It is focused on trust, local control, and clear safety boundaries.

## What it does

- Runs from your terminal
- Takes a task like: `safeclaw run "research RV parks near SF"`
- Uses an LLM provider through an API key
- Can read/write files inside a local workspace
- Has a simple tool system you can extend
- Keeps task logs locally

## Setup

```bash
cd safeclaw
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add your API key.

## Run

```bash
python -m safeclaw.cli run "make me a todo list app plan"
```

Or install as editable:

```bash
pip install -e .
safeclaw run "summarize what files are in this folder"
```

## Commands

```bash
safeclaw run "your task here" --session default
safeclaw chat --session default
safeclaw tools
safeclaw sessions
safeclaw reset --session default
safeclaw compact --session default
safeclaw whatsapp --port 8080
```

## WhatsApp

This starter supports the bare minimum Twilio WhatsApp webhook.

1. Start the webhook:

```bash
safeclaw whatsapp --port 8080
```

2. Expose it with a tunnel such as ngrok or Cloudflare Tunnel.
3. In Twilio's WhatsApp sandbox/sender settings, set the incoming message webhook to:

```text
https://your-public-url/whatsapp
```

Each WhatsApp sender gets a persistent session named from their phone number. Send
`reset` or `/reset` in WhatsApp to start a new session.

Outbound WhatsApp tool calls require:

```env
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

## Sessions and tools

Conversations are saved under `.safeclaw_sessions` in your workspace. The agent now
uses OpenAI-style structured tool calls for file reads, file writes, shell commands,
and optional WhatsApp sends.

## Safety

By default, shell command execution is disabled. To allow it:

```bash
ALLOW_SHELL=true safeclaw run "list files"
```

Keep it disabled unless you trust the task.

## SafeClaw roadmap

The goal is to keep SafeClaw a smaller, safer, self-hosted assistant focused on
trust, local control, and clear permissions.

SafeClaw is not trying to be the biggest agent. It is trying to be the one you
can actually trust running on your machine.

### Phase 1: Rename and identity

- Done: the package, app, prompts, logs, and docs are named SafeClaw.
- Done: the CLI command is `safeclaw`.
- Done: the tagline is `SafeClaw: a self-hosted agent with explicit permissions.`

### Phase 2: Make the current core reliable

- Add a `.gitignore` for `.env`, `workspace/`, `__pycache__/`, logs, and session data.
- Add tests for session save/load/reset/compact.
- Add tests for safe path protection and tool dispatch.
- Add tests for the WhatsApp webhook reset/reply flow.
- Add better errors when API keys or Twilio settings are missing.
- Add a `safeclaw doctor` command that checks local setup.

### Phase 3: Safety model

- Replace the single `ALLOW_SHELL=true/false` flag with permission profiles:
  - `readonly`
  - `workspace-write`
  - `shell-ask`
  - `shell-allow`
- Add allowlists and denylists for shell commands.
- Add approval mode before dangerous actions.
- Log every tool call with timestamp, session, arguments, and result.
- Add a panic switch to disable shell and outbound messaging.
- Keep workspace-only file access as a hard rule.

### Phase 4: WhatsApp production readiness

- Validate Twilio webhook signatures.
- Add a sender allowlist with `SAFECLAW_ALLOWED_SENDERS`.
- Add rate limiting per sender.
- Add max response length and message chunking for WhatsApp.
- Add WhatsApp commands:
  - `/reset`
  - `/memory`
  - `/help`
  - `/model`
  - `/status`

### Phase 5: Better agent loop

- Add automatic compaction when session history gets too long.
- Trim large tool results before sending them back to the model.
- Add more structured tools:
  - `edit_file`
  - `apply_patch`
  - `search_files`
  - `remember`
  - `forget`
  - `session_status`
- Add model fallback handling.
- Add max spend or max token limits per session.

### Phase 6: Install and run

- Add a clean install path:
  - `pip install -e .`
  - `safeclaw init`
  - `safeclaw doctor`
- Add `safeclaw.toml` config support.
- Add launch options:
  - macOS LaunchAgent
  - systemd service
  - Dockerfile
- Support both local-only mode and WhatsApp mode.

### Phase 7: Product polish

- Make the README simple and opinionated.
- Add screenshots or terminal examples.
- Add example configs:
  - personal assistant
  - coding assistant
  - family WhatsApp helper
  - business inbox helper
- Add clear warnings about what SafeClaw can and cannot do.

### Phase 8: Open source trust

- Add `SECURITY.md`.
- Add `PRIVACY.md`.
- Add a threat model explaining:
  - what data stays local
  - what goes to the LLM provider
  - what Twilio can see
  - what files the agent can touch
- Keep defaults safe.
- Make "no telemetry" explicit if that remains true.
- Add signed releases later if the project grows.

## Immediate next steps

1. Rename everything to SafeClaw.
2. Add `.gitignore`.
3. Add `safeclaw doctor`.
4. Add Twilio webhook signature validation.
5. Add sender allowlist.
6. Add tests for sessions, tools, and WhatsApp.
7. Add `safeclaw init` to generate `.env` and config.
8. Add permission profiles so safety is built into the product, not just promised in the README.

# SafeClaw

SafeClaw: a self-hosted agent with explicit permissions.

SafeClaw is a small terminal and WhatsApp assistant you can run on your own
computer. It is focused on trust, local control, and clear safety boundaries.

## Landing page and docs site

This repo includes a static multi-page product site in `site/`.

- `site/index.html` is the landing page.
- `site/install.html` explains quick install, guided install, Mac setup,
  Ollama, WhatsApp, and verification.
- `site/docs.html` documents commands, permissions, memory, WhatsApp, and repo
  structure.
- `site/api.html` is the CLI/tool/environment reference.
- `site/roadmap.html` explains the current roadmap and contribution areas.

You can open `site/index.html` directly in a browser, or publish the `site`
folder with GitHub Pages, Netlify, Vercel, or any static host.

For Cloudflare deployment with Web Analytics kept out of git, use:

```text
Build command: bash scripts/build-site.sh
Deploy command: npx wrangler deploy
Build output: site-dist
```

Set `CF_WEB_ANALYTICS_TOKEN` in Cloudflare's build environment. The script
injects the analytics beacon into `site-dist/` only during deploy.

## What it does

- Runs from your terminal
- Takes a task like: `safeclaw run "research RV parks near SF"`
- Uses an LLM provider through an API key
- Can read/write files inside a local workspace
- Has a simple tool system you can extend
- Keeps task logs locally

## Feature list

### Core assistant

- Terminal one-shot tasks with `safeclaw run`.
- Interactive chat with `safeclaw chat`.
- OpenAI-compatible LLM support.
- Per-session conversation history.
- Local task logs.
- Automatic long-session compaction.

### Install and setup

- Fast installer with `install.sh`.
- Guided non-developer installer with `guided-install.sh`.
- Double-click macOS setup wizard in `mac-setup/`.
- Optional user-level `safeclaw` launcher for on-demand use from any terminal.
- Manual Python setup.
- Editable CLI install.
- `.env.example` config template.
- Pytest test framework with coverage.
- Mocked default tests plus opt-in live/unmocked tests.

### WhatsApp

- Twilio WhatsApp webhook.
- `safeclaw whatsapp`.
- `safeclaw whatsapp-setup`.
- Persistent WhatsApp sessions per sender.
- Sender allowlist with `SAFECLAW_ALLOWED_SENDERS`.
- WhatsApp commands:
  - `/help`
  - `/status`
  - `/memory`
  - `/reset`
  - `/permissions`
  - `/permissions readonly`
  - `/model gpt-4.1-mini`

### Persistent background mode

- macOS LaunchAgent service.
- `safeclaw service-install`.
- `safeclaw service-start`.
- `safeclaw service-stop`.
- `safeclaw service-status`.
- `safeclaw service-uninstall`.
- Logs written to `~/Library/Logs/SafeClaw/`.

### File and workspace tools

- `list_files`.
- `read_file`.
- `write_file`.
- `search_files`.
- `edit_file`.
- `apply_patch`.
- Workspace-only file access.
- Path traversal protection.
- File backups before writes, edits, and patches.
- Large file and output trimming.

### Web and network tools

- `fetch_url`.
- `web_search`.
- Network tools gated by permission profile.

### Memory and sessions

- Durable session memory.
- `remember`.
- `recall_memory`.
- `search_memory`.
- `forget`.
- CLI memory commands:
  - `safeclaw memory`
  - `safeclaw memory-search`
  - `safeclaw memory-forget`
  - `safeclaw memory-edit`
- `safeclaw status`.
- `safeclaw session-config`.
- `safeclaw export`.
- `safeclaw import`.

### Safety and permissions

- Enforced permission profiles:
  - `readonly`
  - `workspace-write`
  - `network-allow`
  - `shell-ask`
  - `shell-allow`
  - `messaging-allow`
- Approval modes:
  - `ask`
  - `deny`
  - `auto`
- Approval prompts for risky actions:
  - file writes
  - file edits
  - patches
  - network fetch/search
  - shell commands
  - outbound WhatsApp sends
- Shell disabled by default with `ALLOW_SHELL=false`.
- WhatsApp blocks approval-required actions instead of hanging.

### CLI commands

- `safeclaw run`
- `safeclaw chat`
- `safeclaw tools`
- `safeclaw doctor`
- `safeclaw sessions`
- `safeclaw status`
- `safeclaw session-config`
- `safeclaw memory`
- `safeclaw memory-search`
- `safeclaw memory-forget`
- `safeclaw memory-edit`
- `safeclaw reset`
- `safeclaw compact`
- `safeclaw export`
- `safeclaw import`
- `safeclaw whatsapp`
- `safeclaw whatsapp-setup`
- `safeclaw service-install`
- `safeclaw service-start`
- `safeclaw service-stop`
- `safeclaw service-status`
- `safeclaw service-uninstall`

## Quick install

Install SafeClaw into `~/safeclaw`, create a virtual environment, install the
CLI, copy `.env.example` to `.env`, and run a local CLI check:

```bash
curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh | bash
```

Install somewhere else:

```bash
curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh | SAFECLAW_DIR="$HOME/apps/safeclaw" bash
```

Install and immediately run a task:

```bash
curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh | OPENAI_API_KEY=sk-your-key SAFECLAW_TASK="make me a todo list app plan" bash
```

For a friendlier step-by-step installer that asks for your settings:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/guided-install.sh)
```

On macOS, there is also a double-click setup wizard:

```text
mac-setup/SafeClaw Setup.command
```

## Setup

### Mac double-click setup

For Mac users who do not want to use Terminal prompts, use the setup wizard in
the `mac-setup` folder.

1. Open the `mac-setup` folder.
2. Double-click `SafeClaw Setup.command`.
3. Follow the macOS dialog prompts.
4. Keep the Terminal window open while installation runs.

If macOS blocks it, right-click `SafeClaw Setup.command`, choose **Open**, then
confirm.

The Mac setup wizard asks for:

- Install folder.
- Git repo and branch.
- Whether to install a global `safeclaw` command.
- OpenAI API key.
- OpenAI-compatible base URL.
- Model name.
- Workspace path.
- Permission profile.
- Approval mode.
- Whether shell commands should be allowed.
- Optional guided Twilio WhatsApp setup.
- Optional persistent WhatsApp service setup.

If you choose WhatsApp setup, the wizard walks you through Twilio Sandbox or
Sender setup, explains how to expose SafeClaw with ngrok or Cloudflare Tunnel,
builds the exact webhook URL ending in `/whatsapp`, can copy that URL to your
clipboard, and asks for the Twilio credentials and allowed WhatsApp senders.

The wizard writes logs to:

```text
~/Library/Logs/SafeClaw/mac-setup.log
```

### One-line setup

For most users, use the install script:

```bash
curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh | bash
```

The script will:

- Clone or update SafeClaw in `~/safeclaw`.
- Create `.venv`.
- Install Python dependencies.
- Install the `safeclaw` CLI in editable mode.
- Copy `.env.example` to `.env` if `.env` does not exist.
- Run `safeclaw tools` as a local smoke check.

Install a global `safeclaw` launcher too:

```bash
curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh | SAFECLAW_GLOBAL=true bash
```

When `SAFECLAW_GLOBAL=true` is set, the installer creates
`~/.local/bin/safeclaw` and adds `~/.local/bin` to your shell startup file if it
is not already on `PATH`.

Install to a custom directory:

```bash
curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh | SAFECLAW_DIR="$HOME/apps/safeclaw" bash
```

Install the global launcher somewhere else:

```bash
curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh | SAFECLAW_GLOBAL=true SAFECLAW_BIN_DIR="$HOME/bin" bash
```

Install from a different repo or branch:

```bash
curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh | SAFECLAW_REPO="https://github.com/yourname/SafeClaw.git" SAFECLAW_REF="main" bash
```

Install and immediately run a task:

```bash
curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh | OPENAI_API_KEY=sk-your-key SAFECLAW_TASK="make me a todo list app plan" bash
```

After install:

```bash
safeclaw doctor
safeclaw run "make me a todo list app plan"
```

Without `SAFECLAW_GLOBAL=true`, use the venv command directly:

```bash
~/safeclaw/.venv/bin/safeclaw doctor
```

If you installed globally and your current terminal cannot find `safeclaw` yet,
run:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

New terminal windows should pick this up automatically. Edit `~/safeclaw/.env`
and set `OPENAI_API_KEY`.

### Guided setup for non-developers

If you want the installer to walk you through setup step by step, use the guided
installer:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/guided-install.sh)
```

This is the recommended path for non-developers because it explains each choice
as it goes and keeps safer defaults enabled.

The guided installer asks for:

- Install folder.
- Whether to install a global `safeclaw` command.
- Command install folder, if global install is enabled. The default is `~/.local/bin`.
- Whether to add that command folder to your shell startup file, if global install is enabled.
- Git repo and branch.
- OpenAI API key. This can be left blank and added later.
- OpenAI-compatible base URL. The default is `https://api.openai.com/v1`.
- Model name. The default is `gpt-4.1-mini`.
- Workspace folder.
- Whether shell commands should be allowed. The default is no.
- Maximum tool steps per task. The default is `6`.
- Optional Twilio WhatsApp settings.
- Whether to run a quick AI test task.

The guided installer does this for you:

- Checks for `git` and `python3`.
- Clones or updates SafeClaw.
- Creates `.venv`.
- Upgrades `pip`.
- Installs Python dependencies from `requirements.txt`.
- Installs the `safeclaw` CLI in editable mode.
- Optionally creates a launcher so `safeclaw` works from any terminal.
- Optionally adds the launcher folder to your shell startup file if you approve it.
- Backs up an existing `.env` if one already exists.
- Writes a new `.env` with your answers.
- Sets `.env` permissions to owner-read/write only.
- Runs `safeclaw tools` as a local smoke check.
- Optionally runs a short AI test task if you entered an API key.
- Prints the exact commands to start using SafeClaw.

The generated `.env` includes:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
WORKSPACE=./workspace
ALLOW_SHELL=false
MAX_TOOL_STEPS=6
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

After guided setup, start using SafeClaw:

```bash
~/safeclaw/.venv/bin/safeclaw run "make me a todo list app plan"
```

If you chose global command install during guided setup, you can use:

```bash
safeclaw run "make me a todo list app plan"
```

Start chat mode:

```bash
safeclaw chat
```

Start the WhatsApp webhook:

```bash
safeclaw whatsapp --port 8080
```

If you skipped the API key during setup, edit `.env` and set `OPENAI_API_KEY`
before running an AI task.

### Manual setup

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

Check your local setup:

```bash
safeclaw doctor
```

`safeclaw doctor` checks Python, `.env`, API key, model settings, workspace
permissions, permission profile, approval mode, shell status, Twilio config,
WhatsApp sender allowlist, webhook port availability, and macOS service status.
Use `safeclaw doctor --strict` if you want failures to exit with a non-zero
status for scripts.

## Testing

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the default mocked test suite:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=safeclaw --cov-report=term-missing
```

Run opt-in live/unmocked checks:

```bash
pytest --run-live
```

By default, tests marked `live` are skipped. Live tests run selected commands
without mocks, so they may depend on local config, services, or ports. The
regular test suite mocks command side effects such as LLM calls, WhatsApp
servers, and macOS service operations.

## Commands

```bash
safeclaw run "your task here" --session default
safeclaw chat --session default
safeclaw tools
safeclaw doctor
safeclaw sessions
safeclaw status --session default
safeclaw session-config --session default --model gpt-4.1-mini --permission-profile readonly
safeclaw memory --session default
safeclaw memory-search "thing to find" --session default
safeclaw memory-forget "memory id or text" --session default
safeclaw memory-edit 1 "updated memory note" --session default
safeclaw reset --session default
safeclaw compact --session default
safeclaw export --session default
safeclaw import path/to/session-export.json --session restored
safeclaw whatsapp-setup
safeclaw whatsapp --port 8080
safeclaw service-install
safeclaw service-status
safeclaw service-stop
```

## Project structure and feature map

SafeClaw is intentionally small. Most of the product lives in the `safeclaw/`
Python package, while install scripts and project metadata live at the repo
root.

### Repo root

| Path | What it is | Features it supports |
| --- | --- | --- |
| `README.md` | Main project documentation. | Install instructions, setup flow, commands, WhatsApp setup, safety model, roadmap, and feature overview. |
| `install.sh` | Fast non-interactive installer. | Clones SafeClaw, creates `.venv`, installs dependencies, installs the CLI, optionally creates a global launcher, copies `.env.example`, and runs `safeclaw tools`. |
| `guided-install.sh` | Step-by-step installer for non-developers. | Asks for install folder, optional global command setup, API key, model, workspace, permission profile, approval mode, shell setting, Twilio settings, and optional test run. |
| `mac-setup/` | Double-click macOS setup wizard. | Uses macOS dialogs to collect setup choices, installs SafeClaw, writes `.env`, runs diagnostics, and can configure persistent WhatsApp service mode. |
| `.env.example` | Example local config file. | Shows all supported environment variables for models, workspace, permissions, approval mode, shell, Twilio, and allowed WhatsApp senders. |
| `requirements.txt` | Runtime Python dependencies. | Installs `python-dotenv`, `requests`, `rich`, and `typer`. |
| `pyproject.toml` | Python package metadata. | Defines the `safeclaw` package and the `safeclaw` CLI command. |
| `workspace/` | Local working area created at runtime. | Stores files SafeClaw can touch, plus local sessions, memories, logs, backups, and exports. |

### `safeclaw/` package

| Path | What it is | Features it supports |
| --- | --- | --- |
| `safeclaw/__init__.py` | Package marker. | Lets Python import SafeClaw as a package. |
| `safeclaw/config.py` | Environment/config loader. | Loads API settings, model name, workspace path, shell flag, permission profile, approval mode, Twilio credentials, and WhatsApp sender allowlist. |
| `safeclaw/cli.py` | Typer command-line interface. | Powers `safeclaw run`, `chat`, `tools`, sessions, memory commands, export/import, WhatsApp setup, and persistent service commands. |
| `safeclaw/agent.py` | Main agent loop. | Builds task context, sends messages to the LLM, handles structured tool calls, saves logs, remembers session state, and auto-compacts long sessions. |
| `safeclaw/llm.py` | OpenAI-compatible LLM client. | Sends chat-completion requests to `OPENAI_BASE_URL`, supports structured tool calls, and validates missing API keys. |
| `safeclaw/tools.py` | Local tool system and safety gate. | Provides file tools, search/edit/patch tools, URL/web tools, shell, WhatsApp sending, workspace path protection, permission profiles, and approval prompts. |
| `safeclaw/sessions.py` | Session and memory storage. | Saves conversations, JSON-backed memories, memory search/edit/forget, session status, compaction, export/import, and per-session model/permission settings. |
| `safeclaw/whatsapp.py` | Twilio WhatsApp webhook. | Receives WhatsApp messages, maps senders to sessions, supports `/help`, `/status`, `/memory`, `/reset`, `/permissions`, `/model`, and sender allowlist checks. |
| `safeclaw/service.py` | Persistent macOS service helper. | Installs, starts, stops, checks, and uninstalls a LaunchAgent that keeps the WhatsApp webhook running after login. |

### Runtime workspace folders

These folders are created inside `WORKSPACE`, which defaults to `./workspace`.
They are local state, not product source code.

| Path | What it stores |
| --- | --- |
| `.safeclaw_sessions/` | Per-session conversation JSON files. |
| `.safeclaw_memory/` | Durable memory notes for each session. |
| `.safeclaw_logs/` | Markdown task logs with task/result summaries. |
| `.safeclaw_backups/` | Backups created before file writes, edits, and patches. |
| `.safeclaw_exports/` | Exported session and memory bundles. |

### Main features by area

**Terminal assistant**

- `safeclaw run "task"` for one-shot tasks.
- `safeclaw chat` for an interactive local chat loop.
- Session-specific model and permission settings.
- Local task logs written under the workspace.

**WhatsApp assistant**

- Twilio-compatible `/whatsapp` webhook.
- Persistent session per WhatsApp sender.
- Sender allowlist with `SAFECLAW_ALLOWED_SENDERS`.
- Built-in WhatsApp commands for help, status, memory, reset, permissions, and model selection.
- Non-interactive safety behavior: actions that require terminal approval are blocked instead of hanging.

**Persistent background mode**

- `safeclaw service-install` installs a macOS LaunchAgent.
- `safeclaw service-status` shows whether the WhatsApp service is installed and loaded.
- `safeclaw service-start`, `service-stop`, and `service-uninstall` manage the service.
- Logs are written to `~/Library/Logs/SafeClaw/`.

**File and workspace tools**

- List and read files inside the configured workspace.
- Write files with backup support.
- Search file names and file contents.
- Edit files by replacing text.
- Apply patches with backups.
- Prevent path traversal outside the workspace.

**Web and network tools**

- `fetch_url` retrieves a URL and trims large responses.
- `web_search` performs basic web search.
- Network tools require the `network-allow` profile.

**Memory and sessions**

- Save durable memory notes with `remember`.
- Recall, search, edit, and forget memories.
- Show session status.
- Export and import sessions with memory.
- Auto-compact long sessions.

### Memory handler implementation

SafeClaw memory is implemented in `safeclaw/sessions.py`. It is deliberately
plain, local, and inspectable.

How memory is stored:

- Memory lives inside the configured `WORKSPACE`.
- The default memory folder is `.safeclaw_memory/`.
- Each session gets its own JSON file:
  - `default` uses `.safeclaw_memory/default.json`
  - WhatsApp senders use session IDs derived from their sender address
- Each memory item is stored as a JSON object with:
  - `id`
  - `created_at`
  - `updated_at`
  - `note`

The current memory shape looks like this:

```json
[
  {
    "id": 1,
    "created_at": "2026-05-16T10:30:00",
    "updated_at": null,
    "note": "User prefers readonly mode by default."
  }
]
```

Memory operations:

- `remember(session_id, note)` trims and saves a durable note.
- `recall(session_id)` formats all saved notes for display or agent context.
- `list_memory(session_id)` returns structured memory entries.
- `search_memory(session_id, query)` performs case-insensitive local search.
- `edit_memory(session_id, memory_id, note)` updates one memory item.
- `forget_memory(session_id, target)` deletes by ID or matching text.
- `reset_session(session_id)` removes both session history and memory.
- `export_session(session_id)` includes memory in the export bundle.
- `import_session(path, session_id)` restores memory if the export includes it.

Legacy memory migration:

- Older `.md` memory files are still recognized.
- If `.safeclaw_memory/<session>.md` exists and no JSON memory file exists,
  SafeClaw reads the markdown lines and writes a JSON memory file.
- Once JSON memory exists, JSON takes precedence.

What memory does not do:

- No remote memory database.
- No cloud sync.
- No telemetry.
- No hidden callbacks.
- No external memory hooks.
- No webhook-based memory writes.
- No non-English or Chinese-language prompt hooks.
- No third-party storage unless you manually place the workspace in synced
  storage such as iCloud, Dropbox, or Google Drive.

The memory handler is intentionally boring: local files, explicit session IDs,
and simple JSON that users can inspect or delete.

**Safety model**

- Enforced permission profiles:
  - `readonly`
  - `workspace-write`
  - `network-allow`
  - `shell-ask`
  - `shell-allow`
  - `messaging-allow`
- Approval modes:
  - `ask`
  - `deny`
  - `auto`
- Risky actions can require approval:
  - file writes
  - file edits
  - patches
  - network fetch/search
  - shell commands
  - outbound WhatsApp sends
- Shell still requires `ALLOW_SHELL=true`, even with a shell permission profile.

## WhatsApp

This starter supports a Twilio WhatsApp webhook.

For an easy setup checklist and config status, run:

```bash
safeclaw whatsapp-setup
```

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
SAFECLAW_ALLOWED_SENDERS=whatsapp:+15551234567
```

`SAFECLAW_ALLOWED_SENDERS` is strongly recommended. If it is set, only those
WhatsApp senders can use your SafeClaw instance. If it is blank, any sender that
can reach the webhook can talk to it.

WhatsApp commands:

- `/help`
- `/status`
- `/memory`
- `/reset`
- `/permissions`
- `/permissions readonly`
- `/model gpt-4.1-mini`

### Persistent WhatsApp mode on macOS

If you want to walk away from your computer and keep receiving/replying through
WhatsApp, install the SafeClaw WhatsApp service:

```bash
safeclaw service-install
```

This creates a macOS LaunchAgent that runs:

```bash
safeclaw whatsapp --host 0.0.0.0 --port 8080
```

The service starts at login and macOS will keep it alive while you are signed
in. Your computer still needs to be awake and connected to the internet. If it
sleeps, the webhook will not receive messages until it wakes again.

Check status:

```bash
safeclaw service-status
```

Start or stop it:

```bash
safeclaw service-start
safeclaw service-stop
```

Remove it:

```bash
safeclaw service-uninstall
```

Logs are written to:

```text
~/Library/Logs/SafeClaw/whatsapp.out.log
~/Library/Logs/SafeClaw/whatsapp.err.log
```

For truly always-on access, run SafeClaw on a machine that stays awake, such as
a Mac mini, home server, or VPS, and point your Twilio WhatsApp webhook at that
machine through ngrok, Cloudflare Tunnel, or another stable public URL.

Risky actions that require terminal approval are blocked over WhatsApp instead
of hanging. For a personal always-available WhatsApp assistant, keep the profile
at `readonly` or only enable the narrow profile you need.

## Sessions and tools

Conversations are saved under `.safeclaw_sessions` in your workspace. Durable
memory is saved under `.safeclaw_memory`. The agent now uses OpenAI-style
structured tool calls for file reads, file writes, file search, file edits,
patches, URL fetches, web search, shell commands, session status, memory, and
optional WhatsApp sends.

Available local tools include:

- `list_files(path='.')`
- `read_file(path)`
- `write_file(path, content, backup=True, overwrite=True)`
- `search_files(query, path='.', include_content=True)`
- `edit_file(path, old, new, replace_all=False, backup=True)`
- `apply_patch(patch, backup=True)`
- `fetch_url(url)`
- `web_search(query)`
- `shell(command)`, disabled unless `ALLOW_SHELL=true`
- `send_whatsapp(to, body)`, if Twilio env vars are configured

Available session and memory tools include:

- `remember(note)`
- `recall_memory()`
- `search_memory(query)`
- `forget(target)`
- `session_status()`

File writes and edits create backups by default under `.safeclaw_backups`.
Sessions can store per-session model and permission-profile settings with
`safeclaw session-config`.

## Safety

By default, shell command execution is disabled. To allow it:

```bash
ALLOW_SHELL=true safeclaw run "list files"
```

Keep it disabled unless you trust the task.

SafeClaw also supports enforced permission profiles:

- `readonly`: can list, read, and search workspace files.
- `workspace-write`: `readonly` plus `write_file`, `edit_file`, and `apply_patch`.
- `network-allow`: `readonly` plus `fetch_url` and `web_search`.
- `shell-ask`: `readonly` plus `shell`, with approval and `ALLOW_SHELL=true`.
- `shell-allow`: `readonly` plus `shell`, without approval, and `ALLOW_SHELL=true`.
- `messaging-allow`: `readonly` plus `send_whatsapp`.

Set the default profile in `.env`:

```env
SAFECLAW_PERMISSION_PROFILE=readonly
SAFECLAW_APPROVAL_MODE=ask
```

Or set it per session:

```bash
safeclaw session-config --session default --permission-profile workspace-write
```

Approval modes:

- `ask`: ask in the terminal before risky actions.
- `deny`: block risky actions that require approval.
- `auto`: skip approval prompts.

SafeClaw asks before file writes, file edits, patches, network fetches, shell
commands, and outbound WhatsApp sends when approval is enabled. WhatsApp runs in
non-interactive mode, so actions that need approval are blocked.

## SafeClaw roadmap

The goal is to keep SafeClaw a smaller, safer, self-hosted assistant focused on
trust, local control, and clear permissions.

SafeClaw is not trying to be the biggest agent. It is trying to be the one you
can actually trust running on your machine.

Compared with larger agent platforms such as OpenClaw, SafeClaw should compete
on being understandable, auditable, and safe by construction. The product
promise is:

> SafeClaw is a self-hosted assistant you can trust with local tasks because
> every capability is bounded, inspectable, and permissioned.

### Current positioning

SafeClaw today is a small Python assistant with:

- Terminal tasks through `safeclaw run` and `safeclaw chat`.
- Basic Twilio WhatsApp webhook support.
- OpenAI-compatible chat completions.
- Structured tool calls for file reads, file writes, shell commands, and WhatsApp sends.
- Workspace-only file access.
- Local session files and memory notes.
- Shell execution disabled by default.

OpenClaw is positioned more like a full agent platform and ecosystem, with many
channels, skills, model providers, sandboxing, config, cost controls, and
installation/onboarding flows. SafeClaw should not copy all of that blindly. It
should borrow the parts that help a small agent become trustworthy and useful.

### OpenClaw comparison

| Area | SafeClaw today | Larger OpenClaw-style platform | Missing in SafeClaw |
| --- | --- | --- | --- |
| Channels | Terminal and basic Twilio WhatsApp | Many channels such as WhatsApp, Telegram, Discord, Slack, Teams, Signal, Matrix, iMessage, and WebChat | Channel adapter architecture, Telegram, Discord, Slack, and web UI |
| Skills | Hardcoded Python tools | Installable skills with manifests, config, lifecycle commands, and registry | Skill system, skill install/update/configure, marketplace or registry |
| Security | Workspace path guard and shell disabled by default | Sandbox, permissions, audit logs, network controls, and rate limits | Real sandboxing, permission grants, audit log, outbound network controls |
| Models | OpenAI-compatible API only | Multiple cloud and local model providers | Provider abstraction, local model support, fallback models |
| Memory | Per-session markdown memory | Persistent scoped user and agent memory | Better memory model, search, forget/edit memory, memory scopes |
| Automation | One-shot task loop and chat | Persistent background agent with triggers | Daemon mode, schedules, recurring jobs, wake commands |
| Browser and web | None | Browser automation, web extraction, web search | Browser tool, fetch URL, search provider, form automation |
| Config | `.env` only | YAML/TOML config for agents, models, channels, and permissions | `safeclaw.toml`, profiles, config validation |
| Operations | Manual run | Onboarding, install scripts, daemon, reload, status | `init`, `doctor`, service install, health/status commands |
| Observability | Local markdown task logs | Audit logging, usage tracking, monitoring hooks | Structured logs, token/cost tracking, tool history commands |
| Multi-agent | Single agent loop only | Multiple named agents with roles and permissions | Safe sub-agent orchestration, bounded worker agents, verifier agents, per-agent model/permission config |
| Files and coding | read/write/list/shell | Broader file operations, code execution, scripts, integrations | patch/edit/search tools, git/GitHub integration |

### Phase 1: Foundation and reliability

- Done: the package, app, prompts, logs, and docs are named SafeClaw.
- Done: the CLI command is `safeclaw`.
- Done: the tagline is `SafeClaw: a self-hosted agent with explicit permissions.`
- Add a `.gitignore` for `.env`, `workspace/`, `__pycache__/`, logs, and session data.
- Add tests for session save/load/reset/compact.
- Add tests for safe path protection and tool dispatch.
- Add tests for the WhatsApp webhook reset/reply flow.
- Add better errors when API keys or Twilio settings are missing.
- Add a `safeclaw doctor` command that checks local setup.
- Add a `safeclaw init` command that generates starter `.env` and config files.

### Phase 2: Safety model

- Replace the single `ALLOW_SHELL=true/false` flag with permission profiles:
  - `readonly`
  - `workspace-write`
  - `shell-ask`
  - `shell-allow`
- Add optional network profiles:
  - `network-deny`
  - `network-allowlist`
  - `network-allow`
- Add allowlists and denylists for shell commands.
- Add approval mode before dangerous actions.
- Log every tool call with timestamp, session, tool name, arguments, result preview, permission profile, and approved/blocked status.
- Add a panic switch to disable shell and outbound messaging.
- Keep workspace-only file access as a hard rule.
- Redact secrets from logs and tool outputs.
- Add output limits, command timeouts, and max file read sizes.

### Phase 3: Sandbox and trust

- Add real isolation for risky tools where possible.
- Run shell commands with tighter environment variables and working-directory controls.
- Add disk/output quotas for tool execution.
- Add outbound domain allowlists for network-capable tools.
- Add `SECURITY.md`.
- Add `PRIVACY.md`.
- Add a threat model explaining:
  - what data stays local
  - what goes to the LLM provider
  - what Twilio can see
  - what files the agent can touch
  - what shell access means
- Make "no telemetry" explicit if that remains true.

### Phase 4: WhatsApp production readiness

- Validate Twilio webhook signatures.
- Add a sender allowlist with `SAFECLAW_ALLOWED_SENDERS`.
- Add rate limiting per sender.
- Add max response length and message chunking for WhatsApp.
- Add WhatsApp commands:
  - `/help`
  - `/reset`
  - `/memory`
  - `/status`
  - `/model`
  - `/permissions`
- Add better error handling for slow model responses.
- Add channel-specific message rendering for plain text, long messages, and command responses.

### Phase 5: Better agent capabilities

Agent tools:

- Add `search_files`.
- Add `edit_file`.
- Add `apply_patch`.
- Add `fetch_url`.
- Add `web_search`.
- Add `session_status`.
- Add `forget`.
- Add safer file overwrite and backup behavior.
- Trim large tool results before sending them back to the model.
- Add task summaries and structured run records.
- Add browser automation only after the permission model is strong enough.

Memory and sessions:

- Add better memory management.
- Add memory search.
- Add edit/delete for saved memories.
- Add automatic session compaction when session history gets too long.
- Add session export/import.
- Add per-session model and permission settings.
- Keep structured tools for:
  - `search_files`
  - `edit_file`
  - `apply_patch`
  - `fetch_url`
  - `web_search`
  - `session_status`
  - `remember`
  - `forget`
- Add model fallback handling.
- Add max spend or max token limits per session.

### Phase 6: Model provider abstraction

- Support provider/model identifiers such as:
  - `openai/gpt-4.1-mini`
  - `anthropic/claude-sonnet`
  - `google/gemini`
  - `ollama/llama`
- Support local models through Ollama or another OpenAI-compatible local endpoint.
- Add fallback models for outages, rate limits, and cost limits.
- Track token usage by session and model.
- Add daily and monthly budget limits.
- Add `safeclaw models` and `safeclaw usage` commands.

### Phase 7: Safe sub-agent orchestration

SafeClaw can handle tasks today through one main agent loop. It can call tools,
save sessions, use memory, and respect permission profiles. It does not yet
automatically split work across multiple sub-agents.

Planned sub-agent support should stay aligned with SafeClaw's safety model:

- Add an optional `--agents auto` mode for larger tasks.
- Keep the main agent responsible for planning, final answers, and risky
  approvals.
- Add read-only explorer agents for codebase or workspace inspection.
- Add bounded worker agents for file edits inside the configured workspace.
- Add verifier agents for tests, `safeclaw doctor`, and setup checks.
- Add optional messenger agents for WhatsApp updates after long tasks finish.
- Give each sub-agent its own permission profile instead of inheriting broad
  access from the main session.
- Store sub-agent actions in the session log so users can see what each agent
  read, changed, ran, or blocked.
- Make sub-agent spawning explicit by default, then experiment with automatic
  task splitting after the audit trail is strong.

Example target flow:

```bash
safeclaw run "build the installer docs and run tests" --agents auto
```

Target role model:

| Role | Default permission profile | Responsibility |
| --- | --- | --- |
| Main agent | Current session profile | Plan, coordinate, approve risky actions, produce final answer |
| Explorer | `readonly` | Inspect files, summarize structure, identify relevant code |
| Worker | `workspace-write` | Make bounded file changes inside the workspace |
| Verifier | `shell-ask` | Run tests and checks only after approval |
| Messenger | `messaging-allow` | Send completion updates only when explicitly enabled |

The goal is not to make SafeClaw feel like a swarm. The goal is to make bigger
tasks easier to manage while keeping each worker narrow, inspectable, and
permissioned.

### Phase 8: Channels and adapters

- Introduce a channel adapter interface for:
  - inbound message normalization
  - outbound message rendering
  - channel authentication
  - webhook health checks
- Keep WhatsApp as the first production channel.
- Add Telegram as the next easiest mobile channel.
- Add Discord or Slack for team/workflow use.
- Add a simple WebChat interface for local/private use.
- Keep channel-specific capabilities outside the core agent loop.

### Phase 9: Skills and plugins

- Distinguish low-level tools from higher-level skills.
- Define a local skill manifest format.
- Add lifecycle commands:
  - `safeclaw skill list`
  - `safeclaw skill install`
  - `safeclaw skill configure`
  - `safeclaw skill run`
  - `safeclaw skill update`
- Require declared permissions for each skill.
- Show permissions before install or enable.
- Support local skills before adding any public registry.
- Add example skills:
  - web research
  - daily brief
  - coding helper
  - family WhatsApp helper
  - business inbox helper

### Phase 10: Install and run

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
- Add daemon mode for persistent operation.
- Add `safeclaw status`, `safeclaw reload`, and `safeclaw stop`.
- Add scheduled tasks and recurring jobs after daemon mode exists.

### Phase 11: Product polish

- Make the README simple and opinionated.
- Add screenshots or terminal examples.
- Add example configs:
  - personal assistant
  - coding assistant
  - family WhatsApp helper
  - business inbox helper
- Add clear warnings about what SafeClaw can and cannot do.
- Add a concise comparison page explaining why SafeClaw is intentionally smaller than larger agent platforms.
- Keep defaults safe and boring.
- Add signed releases later if the project grows.

## Strategic product direction

SafeClaw should not try to become a giant agent ecosystem first. The strongest
path is:

> OpenClaw-style usefulness, but smaller, auditable, and safe by construction.

That means the next versions should prioritize trust primitives before breadth:

1. Permission profiles.
2. Structured audit logs.
3. Twilio signature validation.
4. Sender allowlist.
5. `safeclaw doctor`.
6. `safeclaw init`.
7. Structured config.
8. Tests for sessions, tools, and WhatsApp.
9. Approval flow for risky tools.
10. Better file editing/search tools.

Only after that should SafeClaw expand into more channels, skills, browser
automation, and persistent background operation.

## Immediate next steps

1. Add `.gitignore`.
2. Add tests for sessions, tools, and WhatsApp.
3. Add `safeclaw doctor`.
4. Add `safeclaw init` to generate `.env` and config.
5. Add Twilio webhook signature validation.
6. Add sender allowlist.
7. Add permission profiles so safety is built into the product, not just promised in the README.
8. Add structured audit logs for every tool call.

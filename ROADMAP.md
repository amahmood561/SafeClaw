# SafeClaw Roadmap

Ordered by what unblocks what, not by what is fun. Each milestone has a gate written in terms
of **use**, not shipping: a milestone marked done because the tickets closed is how you get a
product nobody opens.

`ROADMAP_TODO.md` covers the previous cycle (the Mac chat workspace) and is fully checked off.
This is what comes next.

---

## M1 — Make it work

**Thesis:** it currently underdelivers on every non-trivial task, and no amount of positioning
fixes that.

- [x] `MAX_TOOL_STEPS` 6 → 50. Stop when the model stops asking for tools, not when a counter
      runs out. Keep the counter as a safety net that **reports** when it trips instead of
      silently ending the turn.
- [x] Feed tool errors back into the loop. Today a failure ends the turn. An agent that hits
      an error, adapts and continues is the single biggest perceived-competence difference.
- [x] Parallel reads when the model requests several independent ones.
- [x] Auto-compact when history grows. The `compact` command already exists — call it.

**Gate:** ask it to find and fix a real bug in a real repo and it finishes without hitting a
limit.

---

## M2 — Make the product match the pitch

**Thesis:** the differentiator is trust, and the first thirty seconds currently spends it.
The README says self-hosted and local; `.env.example` defaults to `api.openai.com` and the
first thing `doctor` says is **OpenAI API key — FAIL**.

- [x] Ollama becomes the default path. `init` asks one question and defaults local. An API key
      becomes the opt-in, not the requirement.
- [x] Stage the doctor: BLOCKING / OPTIONAL / HEALTHY. Today fifteen checks sit at equal
      weight and four of the warnings are Twilio and Telegram, which nobody cares about on
      day one.
- [x] Delete the keyword block from the README. On a trust product, SEO spam in the face of a
      developer evaluating you is the worst possible signal. Move it to the site's meta tags.
- [ ] Put a GIF at the top. We sell a desktop app with no screenshot in the README.
      **Needs a human with a screen recorder — cannot be generated.**

**Gate:** a stranger with Ollama installed gets a useful answer without entering a key.

---

## M3 — Make it distinct

**Thesis:** "no API key required" is a real differentiator against every other local agent
wrapper. Verified working: `claude -p --output-format json` uses an existing Claude Code login,
returns structured JSON and a resumable `session_id`, with no key anywhere.

- [x] `claude-cli` provider — subprocess to the Claude Code the user already has.
- [~] Session resume: **deliberately not used.** SafeClaw compacts its own
      history, so a resumed CLI session would keep everything and the two would
      silently diverge. Each call sends the full rendered history instead.
- [x] Cost surfaced live. A one-word test reply cost $0.28; users must see the meter.
- [x] Claude Code's own tools stay **disabled** (`--disallowed-tools`). Claude is the brain,
      SafeClaw keeps the hands. Otherwise the permission model is bypassed and the product has
      no point.
- [x] Three modes, offered by `safeclaw init`:

| Mode | Data leaves? | Cost | Needs |
|---|---|---|---|
| Private | No | Free | Ollama |
| Bring your own Claude | Yes | Their subscription | Claude Code login |
| API key | Yes | Per token | OpenAI / OpenRouter key |

**Gate:** install → log into Claude Code → useful result, with zero keys entered anywhere.
**Met.** A two-step task (list the workspace, read a file, report) ran end to end in 10.4s.

### Measured while building this

- Replacing Claude Code's system prompt rather than appending to it took a call
  from **80s / $0.71 to 14s / $0.24**. Appending left the CLI answering as a
  coding assistant that had lost its tools, explaining what it could not do
  instead of requesting a SafeClaw tool.
- Without an explicit "you have no direct access to this machine", the model
  **invented a plausible file listing** rather than calling `list_files`. With
  it, 3/3 runs produced a tool call. This is prompt adherence, not a guarantee:
  the loop must keep tolerating a prose reply where a tool call was expected.
- Invocations are isolated. Verified by planting a code word in one call and
  failing to recall it in the next.
- Cost is real: **$0.03 to $0.24 per call** on the user's own subscription. The
  meter is surfaced on every message as `_cost_usd`.

---

## M4 — Make it sell

**Thesis:** the permission model **is** the product, and it is currently buried in a chat tray.
Every tool has chat. Nobody else has this.

- [ ] Persistent permission ledger beside the chat: profile, workspace, and a running list of
      what it actually touched this session. That is the screenshot that sells it.
- [ ] Profile switcher in the chrome, not a config file.
- [ ] Diff preview inside approval cards, before the write.
- [ ] "Why did it do that?" — one click from any result to the tool calls behind it.
      Inspectable tool use is in the pitch; make it a button.
- [ ] Pick one audience and write their landing page:
      1. **People who cannot send data to OpenAI** — lawyers, clinics, accountants. Real
         budget, unsolved problem, and "runs entirely on your machine" is the whole pitch.
      2. Developers who will not `curl | bash` from an unknown org.
      3. Homelab and self-hosted hobbyists — enthusiastic, will not pay.

**Gate:** someone who is not the author installs from Gumroad and completes a task without
asking for help.

---

## M5 — Make it stick

- [ ] `safeclaw try` — five recipes as the front door, so the thirty CLI commands become the
      back door.
- [ ] Exportable audit log of everything it touched. This is what sells to the regulated
      audience.
- [ ] A one-page "what leaves your machine" doc.

---

## Not doing, and why

- **Native Anthropic adapter** — OpenRouter and LiteLLM already cover it and M3 makes it
  unnecessary.
- **More tools** — the current 24 are the right set. `apply_patch`, `diff_file`, `run_tests`
  and `git_status` are the core loop.
- **Windows / Linux packaging** — not until one macOS user is happy and paying.
- **Web UI** — a local-first pitch and a browser app fight each other.

---

**M1 makes it work. M2 makes it honest. M3 makes it different. M4 makes it sell.**

If only one happens, it is M1. A six-step agent feels broken to everyone regardless of how
good the rest is.

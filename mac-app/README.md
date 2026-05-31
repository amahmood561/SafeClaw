# SafeClaw Mac App

This folder contains a separate Electron desktop app for SafeClaw.

The app gives non-terminal users a clearer setup and control surface while
using a bundled SafeClaw runtime in packaged DMG builds. Developer source
installs can still call the existing SafeClaw installer when needed.

## What the app does

- Use the bundled SafeClaw runtime from the DMG when available.
- Save setup without requiring Git, pip, or Xcode developer tools for normal
  Gumroad users.
- Install or update SafeClaw into `~/safeclaw` only from the advanced developer
  install path.
- Save a local `.env` file.
- Pick provider presets for OpenAI, Ollama, Groq, OpenRouter/Claude, LiteLLM, or a custom OpenAI-compatible endpoint.
- Test the configured provider from the app before running tasks.
- Run `safeclaw doctor`.
- Run one-off SafeClaw tasks.
- Chat with SafeClaw inside the app interface.
- Enable or disable Jarvis mode from the app sidebar or Setup screen.
- Use Jarvis mode as a command center for queued tasks, active context, approvals, and WhatsApp service controls.
- Stream command output into the active chat response while keeping raw logs in Output.
- Browse, rename, delete, and export local SafeClaw sessions.
- Drag and drop files or links into chat.
- Preview attachments, choose reference vs included content, and see workspace/size warnings.
- Handle approval prompts with in-chat allow/deny cards when the CLI asks for confirmation.
- Use starter actions, message states, workspace awareness, and memory controls from the chat surface.
- Open the SafeClaw install folder.
- Start the WhatsApp webhook.
- Install, start, stop, and inspect the macOS WhatsApp service.

## How to use

1. Install Node.js if needed.
2. Open Terminal in `mac-app/`.
3. Run `npm install`.
4. Run `npm start`.
5. Use the **First run** panel:
   - **Save Setup**
   - **Test Provider**
   - **Run Doctor**
   - **Send Test Prompt**
6. Use **Runtime health** to confirm the bundled runtime, provider config, workspace, and Telegram status.
7. Click **Copy Diagnostic Report** when asking for help. The report avoids API keys and other secrets.
8. Turn on **Jarvis mode** when you want the higher-level command center instead of the standard Chat view.

## Claude setup

SafeClaw does not call Anthropic's native API yet. To use Claude today, choose
**OpenRouter / Claude** or **LiteLLM gateway** in the provider preset selector.
The app saves those values into the normal OpenAI-compatible fields:

```env
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=anthropic/claude-3.5-sonnet
```

## Build a macOS app bundle

```bash
bash scripts/build-mac-runtime.sh
npm --prefix mac-app install
npm --prefix mac-app run build:mac
```

From inside `mac-app/`, the final build command is:

```bash
npm run build:mac
```

The build output is written to:

```text
mac-app/dist/
```

## Notes

- This app does not replace the CLI.
- Packaged DMG builds include a `runtime/safeclaw-bin` backend built with
  PyInstaller.
- Gumroad users should not need `python3`, `git`, `pip`, or Xcode developer
  tools for the normal app flow.
- `python3` and `git` are only expected for developer/source installs.
- It keeps the actual SafeClaw install separate, usually at `~/safeclaw`.
- The existing `mac-setup/` wizard is unchanged.
- Dropped text files are sent with a capped preview. Larger or binary files are sent as local file references so users do not accidentally dump huge content into a chat request.

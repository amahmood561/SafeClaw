# SafeClaw Mac App

This folder contains a separate Electron desktop app for SafeClaw.

The app gives non-terminal users a clearer setup and control surface while
still calling the existing SafeClaw installer and CLI commands underneath.

## What the app does

- Install or update SafeClaw into `~/safeclaw` by default.
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
5. Click **Install / Update**.
6. Choose a provider preset and add API/model/workspace settings.
7. Click **Save Config**.
8. Click **Test Provider**.
9. Click **Run Doctor**.
10. Turn on **Jarvis mode** when you want the higher-level command center instead of the standard Chat view.

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
cd mac-app
npm install
npm run build:mac
```

The build output is written to:

```text
mac-app/dist/
```

## Notes

- This app does not replace the CLI.
- It does not bundle Python or SafeClaw dependencies yet.
- It expects `python3` and `git` to be available on the Mac.
- It keeps the actual SafeClaw install separate, usually at `~/safeclaw`.
- The existing `mac-setup/` wizard is unchanged.
- Dropped text files are sent with a capped preview. Larger or binary files are sent as local file references so users do not accidentally dump huge content into a chat request.

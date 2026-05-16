# SafeClaw Mac Setup

This folder contains a double-clickable macOS setup wizard for SafeClaw.

## How to use

1. Open the `mac-setup` folder.
2. Double-click `SafeClaw Setup.command`.
3. Follow the macOS dialog prompts.
4. Keep the Terminal window open while installation runs.

The setup wizard will ask for:

- Install folder
- Git repo and branch
- Whether to install a global `safeclaw` command
- OpenAI API key
- OpenAI-compatible base URL
- Model name
- Workspace path
- Permission profile
- Approval mode
- Whether shell commands should be allowed
- Optional guided Twilio WhatsApp setup
- Optional persistent WhatsApp service setup

## WhatsApp walkthrough

If you choose to configure WhatsApp, the wizard walks through:

- Twilio WhatsApp Sandbox or Sender setup.
- Joining the Twilio Sandbox from your phone if needed.
- Creating a public URL with ngrok, Cloudflare Tunnel, or another HTTPS tunnel.
- Building the exact webhook URL:

```text
https://your-public-url/whatsapp
```

- Where to paste that webhook URL in Twilio.
- How to format allowed WhatsApp senders:

```text
whatsapp:+15551234567
```

- Entering Twilio credentials:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_WHATSAPP_FROM`
  - `SAFECLAW_ALLOWED_SENDERS`

The wizard can also copy the webhook URL to your clipboard and open the Twilio
Console in your browser.

## What it does

- Installs SafeClaw into the folder you choose.
- Creates a Python virtual environment.
- Installs SafeClaw dependencies.
- Writes a local `.env` file.
- Runs `safeclaw doctor`.
- Shows the exact Twilio webhook URL if WhatsApp is configured.
- Optionally installs a macOS LaunchAgent for persistent WhatsApp mode.

## Notes

- Global command install is optional.
- If enabled, the global command defaults to `~/.local/bin/safeclaw`.
- Shell access defaults to disabled.
- Permission profile defaults to `readonly`.
- The setup log is written to:

```text
~/Library/Logs/SafeClaw/mac-setup.log
```

If macOS blocks the command file, right-click it, choose **Open**, then confirm.

#!/usr/bin/env bash
set -euo pipefail

DEFAULT_REPO_URL="https://github.com/amahmood561/SafeClaw.git"
DEFAULT_REF="main"
DEFAULT_INSTALL_DIR="$HOME/safeclaw"
DEFAULT_BIN_DIR="$HOME/.local/bin"
DEFAULT_BASE_URL="https://api.openai.com/v1"
DEFAULT_MODEL="gpt-4.1-mini"
DEFAULT_WORKSPACE="./workspace"
DEFAULT_PERMISSION_PROFILE="readonly"
DEFAULT_APPROVAL_MODE="ask"
DEFAULT_MAX_TOOL_STEPS="6"
DEFAULT_TWILIO_FROM="whatsapp:+14155238886"
DEFAULT_PUBLIC_URL="https://your-public-url"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$HOME/Library/Logs/SafeClaw/mac-setup.log"
mkdir -p "$(dirname "$LOG_FILE")"

exec > >(tee -a "$LOG_FILE") 2>&1

info() {
  printf '\033[1;36m==>\033[0m %s\n' "$1"
}

fail() {
  local message="$1"
  printf '\033[1;31merror:\033[0m %s\n' "$message" >&2
  osascript -e "display dialog \"SafeClaw setup failed: $(printf "%s" "$message" | sed 's/"/\\"/g')\" buttons {\"OK\"} default button \"OK\" with icon stop" >/dev/null 2>&1 || true
  exit 1
}

need_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

osa_escape() {
  printf "%s" "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

dialog_text() {
  local prompt
  local default_value
  prompt="$(osa_escape "$1")"
  default_value="$(osa_escape "${2:-}")"
  osascript -e "text returned of (display dialog \"$prompt\" default answer \"$default_value\" buttons {\"Cancel\", \"Continue\"} default button \"Continue\")"
}

dialog_secret() {
  local prompt
  prompt="$(osa_escape "$1")"
  osascript -e "text returned of (display dialog \"$prompt\" default answer \"\" hidden answer true buttons {\"Skip\", \"Continue\"} default button \"Continue\")" || true
}

dialog_yes_no() {
  local prompt
  local default_button
  prompt="$(osa_escape "$1")"
  default_button="${2:-No}"
  local answer
  answer="$(osascript -e "button returned of (display dialog \"$prompt\" buttons {\"No\", \"Yes\"} default button \"$default_button\")")"
  [ "$answer" = "Yes" ]
}

dialog_choice() {
  local prompt
  local choices
  local default_choice
  prompt="$(osa_escape "$1")"
  choices="$2"
  default_choice="$(osa_escape "$3")"
  osascript <<APPLESCRIPT
set selectedItem to choose from list {$choices} with prompt "$prompt" default items {"$default_choice"}
if selectedItem is false then error number -128
return item 1 of selectedItem
APPLESCRIPT
}

show_message() {
  local title
  local message
  title="$(osa_escape "$1")"
  message="$(osa_escape "$2")"
  osascript -e "display dialog \"$message\" with title \"$title\" buttons {\"Continue\"} default button \"Continue\" with icon note" >/dev/null
}

show_whatsapp_walkthrough() {
  show_message "WhatsApp setup overview" "SafeClaw uses Twilio WhatsApp.\n\nYou need:\n1. A Twilio account\n2. A WhatsApp Sandbox or WhatsApp Sender\n3. A public URL that points to your Mac or server\n4. Your own WhatsApp number in the SafeClaw allowlist"

  show_message "Step 1: Twilio WhatsApp" "Open Twilio Console, then go to Messaging > Try it out > Send a WhatsApp message, or use your configured WhatsApp Sender.\n\nIf you use the Sandbox, join the sandbox from your phone first by sending the join code shown by Twilio."

  show_message "Step 2: Public URL" "Twilio must reach your SafeClaw webhook from the internet.\n\nCommon options:\n- ngrok: ngrok http 8080\n- Cloudflare Tunnel\n- a server/VPS with a public HTTPS URL\n\nYour webhook path will be /whatsapp."

  PUBLIC_URL_VALUE="$(dialog_text "Paste your public HTTPS URL. Do not include /whatsapp unless it is already part of your tunnel URL." "$DEFAULT_PUBLIC_URL")"
  PUBLIC_URL_VALUE="${PUBLIC_URL_VALUE%/}"
  WEBHOOK_URL_VALUE="$PUBLIC_URL_VALUE/whatsapp"

  show_message "Step 3: Twilio webhook URL" "In Twilio's WhatsApp Sandbox or Sender settings, set the incoming message webhook to:\n\n$WEBHOOK_URL_VALUE\n\nHTTP method: POST"

  show_message "Step 4: Sender allowlist" "SafeClaw can restrict who may talk to your bot.\n\nUse your WhatsApp sender address in this format:\nwhatsapp:+15551234567\n\nYou will enter this in the next prompts as SAFECLAW_ALLOWED_SENDERS."

  if dialog_yes_no "Open Twilio Console in your browser now?" "No"; then
    open "https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn"
  fi

  if dialog_yes_no "Copy the webhook URL to your clipboard?" "Yes"; then
    printf "%s" "$WEBHOOK_URL_VALUE" | pbcopy
  fi
}

write_env() {
  local env_file="$1"
  cat > "$env_file" <<EOF
# Use OpenAI-compatible API endpoint
OPENAI_API_KEY=$OPENAI_API_KEY_VALUE
OPENAI_BASE_URL=$OPENAI_BASE_URL_VALUE
OPENAI_MODEL=$OPENAI_MODEL_VALUE

# Agent settings
WORKSPACE=$WORKSPACE_VALUE
ALLOW_SHELL=$ALLOW_SHELL_VALUE
SAFECLAW_PERMISSION_PROFILE=$PERMISSION_PROFILE_VALUE
SAFECLAW_APPROVAL_MODE=$APPROVAL_MODE_VALUE
MAX_TOOL_STEPS=$MAX_TOOL_STEPS_VALUE

# Optional Twilio WhatsApp outbound support.
# For inbound replies, point your Twilio WhatsApp webhook to:
#   https://your-public-url/whatsapp
TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID_VALUE
TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN_VALUE
TWILIO_WHATSAPP_FROM=$TWILIO_WHATSAPP_FROM_VALUE
SAFECLAW_ALLOWED_SENDERS=$SAFECLAW_ALLOWED_SENDERS_VALUE
EOF
  chmod 600 "$env_file"
}

osascript -e 'display dialog "Welcome to the SafeClaw Mac setup wizard. This will install SafeClaw, create local config, and optionally set up WhatsApp service mode." buttons {"Cancel", "Start"} default button "Start" with icon note' >/dev/null

need_command git
need_command python3

if [ -f "$REPO_ROOT/install.sh" ]; then
  INSTALL_SCRIPT="$REPO_ROOT/install.sh"
  REPO_URL_DEFAULT="file://$REPO_ROOT"
else
  tmp_dir="$(mktemp -d)"
  INSTALL_SCRIPT="$tmp_dir/install.sh"
  curl -fsSL "https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh" -o "$INSTALL_SCRIPT"
  chmod +x "$INSTALL_SCRIPT"
  REPO_URL_DEFAULT="$DEFAULT_REPO_URL"
fi

INSTALL_DIR_VALUE="$(dialog_text "Where should SafeClaw be installed?" "$DEFAULT_INSTALL_DIR")"
REPO_URL_VALUE="$(dialog_text "Git repo URL" "$REPO_URL_DEFAULT")"
REF_VALUE="$(dialog_text "Branch or tag" "$DEFAULT_REF")"

if dialog_yes_no "Do you want a global safeclaw command available from any new terminal?" "No"; then
  GLOBAL_INSTALL_VALUE="true"
  BIN_DIR_VALUE="$(dialog_text "Where should the safeclaw command launcher be installed?" "$DEFAULT_BIN_DIR")"
else
  GLOBAL_INSTALL_VALUE="false"
  BIN_DIR_VALUE="$DEFAULT_BIN_DIR"
fi

OPENAI_API_KEY_VALUE="$(dialog_secret "OpenAI API key. Leave blank to add it later in .env.")"
OPENAI_BASE_URL_VALUE="$(dialog_text "OpenAI-compatible base URL" "$DEFAULT_BASE_URL")"
OPENAI_MODEL_VALUE="$(dialog_text "Model name" "$DEFAULT_MODEL")"

WORKSPACE_VALUE="$(dialog_text "Workspace path. Relative paths are relative to the SafeClaw install folder." "$DEFAULT_WORKSPACE")"
PERMISSION_PROFILE_VALUE="$(dialog_choice "Choose a permission profile" '"readonly", "workspace-write", "network-allow", "shell-ask", "shell-allow", "messaging-allow"' "$DEFAULT_PERMISSION_PROFILE")"
APPROVAL_MODE_VALUE="$(dialog_choice "Choose approval mode" '"ask", "deny", "auto"' "$DEFAULT_APPROVAL_MODE")"
MAX_TOOL_STEPS_VALUE="$(dialog_text "Maximum tool steps per task" "$DEFAULT_MAX_TOOL_STEPS")"

if dialog_yes_no "Allow shell commands? For most users, choose No." "No"; then
  ALLOW_SHELL_VALUE="true"
else
  ALLOW_SHELL_VALUE="false"
fi

TWILIO_ACCOUNT_SID_VALUE=""
TWILIO_AUTH_TOKEN_VALUE=""
TWILIO_WHATSAPP_FROM_VALUE="$DEFAULT_TWILIO_FROM"
SAFECLAW_ALLOWED_SENDERS_VALUE=""
PUBLIC_URL_VALUE=""
WEBHOOK_URL_VALUE=""

if dialog_yes_no "Configure WhatsApp/Twilio now?" "No"; then
  show_whatsapp_walkthrough
  TWILIO_ACCOUNT_SID_VALUE="$(dialog_text "Twilio Account SID" "")"
  TWILIO_AUTH_TOKEN_VALUE="$(dialog_secret "Twilio Auth Token")"
  TWILIO_WHATSAPP_FROM_VALUE="$(dialog_text "Twilio WhatsApp From number" "$DEFAULT_TWILIO_FROM")"
  SAFECLAW_ALLOWED_SENDERS_VALUE="$(dialog_text "Allowed WhatsApp sender numbers, comma-separated. Example: whatsapp:+15551234567" "")"
fi

info "Installing SafeClaw"
SAFECLAW_REPO="$REPO_URL_VALUE" \
SAFECLAW_REF="$REF_VALUE" \
SAFECLAW_DIR="$INSTALL_DIR_VALUE" \
SAFECLAW_BIN_DIR="$BIN_DIR_VALUE" \
SAFECLAW_GLOBAL="$GLOBAL_INSTALL_VALUE" \
SAFECLAW_UPDATE_SHELL_RC="true" \
bash "$INSTALL_SCRIPT"

cd "$INSTALL_DIR_VALUE"

if [ -f .env ]; then
  backup=".env.backup.$(date +%Y%m%d-%H%M%S)"
  info "Backing up existing .env to $backup"
  cp .env "$backup"
fi

info "Writing SafeClaw .env"
write_env "$INSTALL_DIR_VALUE/.env"

SAFECLAW_CMD="$INSTALL_DIR_VALUE/.venv/bin/safeclaw"
if [ "$GLOBAL_INSTALL_VALUE" = "true" ] && [ -x "$BIN_DIR_VALUE/safeclaw" ]; then
  SAFECLAW_CMD="$BIN_DIR_VALUE/safeclaw"
fi

info "Running diagnostics"
"$SAFECLAW_CMD" doctor || true

if [ -n "$WEBHOOK_URL_VALUE" ]; then
  info "WhatsApp webhook URL: $WEBHOOK_URL_VALUE"
  "$SAFECLAW_CMD" whatsapp-setup --public-url "$PUBLIC_URL_VALUE" || true
fi

if dialog_yes_no "Install persistent WhatsApp service on this Mac? Your Mac must stay awake and online to receive messages." "No"; then
  "$SAFECLAW_CMD" service-install || true
fi

if [ -n "$OPENAI_API_KEY_VALUE" ] && dialog_yes_no "Run a quick AI test task now?" "No"; then
  "$SAFECLAW_CMD" run "Reply with one short sentence confirming SafeClaw is installed."
fi

completion_message="SafeClaw setup is complete.\n\nInstall folder:\n$INSTALL_DIR_VALUE\n\nConfig:\n$INSTALL_DIR_VALUE/.env\n\nLogs:\n$LOG_FILE\n\nRun diagnostics with:\n$SAFECLAW_CMD doctor"
if [ -n "$WEBHOOK_URL_VALUE" ]; then
  completion_message="$completion_message\n\nTwilio WhatsApp webhook:\n$WEBHOOK_URL_VALUE"
fi
osascript -e "display dialog \"$(osa_escape "$completion_message")\" buttons {\"OK\"} default button \"OK\" with icon note" >/dev/null

info "SafeClaw setup complete"
printf "Install folder: %s\n" "$INSTALL_DIR_VALUE"
printf "Config file: %s/.env\n" "$INSTALL_DIR_VALUE"
printf "Command: %s\n" "$SAFECLAW_CMD"
printf "Log file: %s\n" "$LOG_FILE"
if [ -n "$WEBHOOK_URL_VALUE" ]; then
  printf "WhatsApp webhook URL: %s\n" "$WEBHOOK_URL_VALUE"
fi

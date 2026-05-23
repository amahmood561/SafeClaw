#!/usr/bin/env bash
set -euo pipefail

REPO_URL_DEFAULT="https://github.com/amahmood561/SafeClaw.git"
INSTALL_DIR_DEFAULT="$HOME/safeclaw"
REF_DEFAULT="main"
BASE_URL_DEFAULT="https://api.openai.com/v1"
MODEL_DEFAULT="gpt-4.1-mini"
PROVIDER_PRESET_DEFAULT="openai"
WORKSPACE_DEFAULT="./workspace"
PERMISSION_PROFILE_DEFAULT="readonly"
APPROVAL_MODE_DEFAULT="ask"
MAX_TOOL_STEPS_DEFAULT="6"
BIN_DIR_DEFAULT="$HOME/.local/bin"

if [ -r /dev/tty ]; then
  exec 3</dev/tty
else
  echo "This guided installer needs an interactive terminal." >&2
  echo "Use install.sh for non-interactive installs." >&2
  exit 1
fi

info() {
  printf '\033[1;36m==>\033[0m %s\n' "$1"
}

warn() {
  printf '\033[1;33mwarning:\033[0m %s\n' "$1"
}

fail() {
  printf '\033[1;31merror:\033[0m %s\n' "$1" >&2
  exit 1
}

need_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

shell_rc_file() {
  case "${SHELL:-}" in
    */zsh) printf "%s" "$HOME/.zshrc" ;;
    */bash) printf "%s" "$HOME/.bashrc" ;;
    *) printf "%s" "$HOME/.profile" ;;
  esac
}

install_launcher() {
  local install_dir="$1"
  local bin_dir="$2"
  local update_shell_rc="$3"
  local launcher="$bin_dir/safeclaw"
  mkdir -p "$bin_dir"
  cat > "$launcher" <<EOF
#!/usr/bin/env bash
exec "$install_dir/.venv/bin/safeclaw" "\$@"
EOF
  chmod +x "$launcher"

  case ":$PATH:" in
    *":$bin_dir:"*) ;;
    *)
      if [ "$update_shell_rc" = "true" ]; then
        local rc_file
        rc_file="$(shell_rc_file)"
        touch "$rc_file"
        if ! grep -Fq "$bin_dir" "$rc_file"; then
          {
            printf "\n# SafeClaw CLI\n"
            printf 'export PATH="%s:$PATH"\n' "$bin_dir"
          } >> "$rc_file"
        fi
      fi
      ;;
  esac
}

prompt() {
  local label="$1"
  local default_value="${2:-}"
  local value
  if [ -n "$default_value" ]; then
    printf "%s [%s]: " "$label" "$default_value" >/dev/tty
  else
    printf "%s: " "$label" >/dev/tty
  fi
  IFS= read -r value <&3
  if [ -z "$value" ]; then
    value="$default_value"
  fi
  printf "%s" "$value"
}

prompt_secret() {
  local label="$1"
  local value
  printf "%s: " "$label" >/dev/tty
  stty -echo < /dev/tty
  IFS= read -r value <&3
  stty echo < /dev/tty
  printf "\n" >/dev/tty
  printf "%s" "$value"
}

prompt_yes_no() {
  local label="$1"
  local default_value="$2"
  local suffix
  local value
  case "$default_value" in
    y|Y|yes|YES) suffix="Y/n" ;;
    *) suffix="y/N" ;;
  esac
  while true; do
    printf "%s [%s]: " "$label" "$suffix" >/dev/tty
    IFS= read -r value <&3
    value="${value:-$default_value}"
    case "$value" in
      y|Y|yes|YES) return 0 ;;
      n|N|no|NO) return 1 ;;
      *) echo "Please answer yes or no." >/dev/tty ;;
    esac
  done
}

write_env() {
  local env_file="$1"
  local api_key="$2"
  local base_url="$3"
  local model="$4"
  local workspace="$5"
  local allow_shell="$6"
  local permission_profile="$7"
  local approval_mode="$8"
  local max_tool_steps="$9"
  local twilio_sid="${10}"
  local twilio_token="${11}"
  local twilio_from="${12}"
  local allowed_senders="${13}"
  local provider_preset="${14:-custom}"

  cat > "$env_file" <<EOF
# Use OpenAI-compatible API endpoint
SAFECLAW_PROVIDER_PRESET=$provider_preset
OPENAI_API_KEY=$api_key
OPENAI_BASE_URL=$base_url
OPENAI_MODEL=$model

# Agent settings
WORKSPACE=$workspace
ALLOW_SHELL=$allow_shell
SAFECLAW_PERMISSION_PROFILE=$permission_profile
SAFECLAW_APPROVAL_MODE=$approval_mode
MAX_TOOL_STEPS=$max_tool_steps

# Optional Twilio WhatsApp outbound support.
# For inbound replies, point your Twilio WhatsApp webhook to:
#   https://your-public-url/whatsapp
TWILIO_ACCOUNT_SID=$twilio_sid
TWILIO_AUTH_TOKEN=$twilio_token
TWILIO_WHATSAPP_FROM=$twilio_from
SAFECLAW_ALLOWED_SENDERS=$allowed_senders
EOF
  chmod 600 "$env_file"
}

cat <<'EOF'

SafeClaw guided installer

This will ask a few questions, install SafeClaw, and write a local .env file.
SafeClaw keeps shell access disabled by default.

EOF

need_command git
need_command python3

repo_url="$(prompt "Git repo URL" "$REPO_URL_DEFAULT")"
install_dir="$(prompt "Install folder" "$INSTALL_DIR_DEFAULT")"
ref="$(prompt "Branch or tag" "$REF_DEFAULT")"
if prompt_yes_no "Install safeclaw command globally for any terminal" "n"; then
  global_install="true"
  bin_dir="$(prompt "Command install folder" "$BIN_DIR_DEFAULT")"
  if prompt_yes_no "Add command folder to shell startup file if needed" "y"; then
    update_shell_rc="true"
  else
    update_shell_rc="false"
  fi
else
  global_install="false"
  bin_dir="$BIN_DIR_DEFAULT"
  update_shell_rc="false"
fi

cat <<'EOF'

LLM settings

SafeClaw uses an OpenAI-compatible API. Leave the key blank if you want to add
it later in the .env file.

Provider presets:
  openai     https://api.openai.com/v1
  ollama     http://localhost:11434/v1
  groq       https://api.groq.com/openai/v1
  openrouter https://openrouter.ai/api/v1, useful for Claude
  litellm    http://localhost:4000/v1
  custom     enter your own OpenAI-compatible endpoint

EOF

provider_preset="$(prompt "Provider preset: openai, ollama, groq, openrouter, litellm, custom" "$PROVIDER_PRESET_DEFAULT")"
case "$provider_preset" in
  openai) BASE_URL_DEFAULT="https://api.openai.com/v1"; MODEL_DEFAULT="gpt-4.1-mini" ;;
  ollama) BASE_URL_DEFAULT="http://localhost:11434/v1"; MODEL_DEFAULT="llama3.1" ;;
  groq) BASE_URL_DEFAULT="https://api.groq.com/openai/v1"; MODEL_DEFAULT="openai/gpt-oss-20b" ;;
  openrouter) BASE_URL_DEFAULT="https://openrouter.ai/api/v1"; MODEL_DEFAULT="anthropic/claude-3.5-sonnet" ;;
  litellm) BASE_URL_DEFAULT="http://localhost:4000/v1"; MODEL_DEFAULT="anthropic/claude-3-5-sonnet-latest" ;;
  *) provider_preset="custom" ;;
esac
api_key="$(prompt_secret "OpenAI API key, hidden input, optional")"
base_url="$(prompt "OpenAI-compatible base URL" "$BASE_URL_DEFAULT")"
model="$(prompt "Model" "$MODEL_DEFAULT")"

cat <<'EOF'

Safety settings

SafeClaw can read and write files only inside its configured workspace.
Shell commands are disabled by default. For non-dev users, keep shell disabled.

EOF

workspace="$(prompt "Workspace path, relative to SafeClaw install folder is OK" "$WORKSPACE_DEFAULT")"
permission_profile="$(prompt "Permission profile: readonly, workspace-write, network-allow, shell-ask, shell-allow, messaging-allow" "$PERMISSION_PROFILE_DEFAULT")"
approval_mode="$(prompt "Approval mode: ask, auto, deny" "$APPROVAL_MODE_DEFAULT")"
if prompt_yes_no "Allow shell commands" "n"; then
  allow_shell="true"
  warn "Shell commands will be enabled. Only do this if you trust the tasks you run."
else
  allow_shell="false"
fi
max_tool_steps="$(prompt "Maximum tool steps per task" "$MAX_TOOL_STEPS_DEFAULT")"

cat <<'EOF'

WhatsApp settings

WhatsApp is optional. You can skip it now and edit .env later.

EOF

twilio_sid=""
twilio_token=""
twilio_from="whatsapp:+14155238886"
allowed_senders=""
if prompt_yes_no "Configure Twilio WhatsApp outbound now" "n"; then
  twilio_sid="$(prompt "Twilio Account SID" "")"
  twilio_token="$(prompt_secret "Twilio Auth Token, hidden input")"
  twilio_from="$(prompt "Twilio WhatsApp From number" "$twilio_from")"
  allowed_senders="$(prompt "Allowed WhatsApp sender numbers, comma-separated, optional" "")"
fi

info "Installing prerequisites and SafeClaw"

if [ -d "$install_dir/.git" ]; then
  info "Updating existing checkout in $install_dir"
  git -C "$install_dir" fetch origin "$ref"
  git -C "$install_dir" checkout "$ref"
  git -C "$install_dir" pull --ff-only origin "$ref" || warn "Could not fast-forward pull. Continuing with current checkout."
elif [ -e "$install_dir" ]; then
  fail "$install_dir already exists but is not a git checkout. Choose another install folder."
else
  info "Cloning SafeClaw into $install_dir"
  git clone --branch "$ref" "$repo_url" "$install_dir"
fi

cd "$install_dir"

info "Creating virtual environment"
python3 -m venv .venv

info "Installing Python dependencies"
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e .

if [ "$global_install" = "true" ]; then
  info "Installing global safeclaw launcher"
  install_launcher "$install_dir" "$bin_dir" "$update_shell_rc"
fi

if [ -f .env ]; then
  backup=".env.backup.$(date +%Y%m%d-%H%M%S)"
  info "Backing up existing .env to $backup"
  cp .env "$backup"
fi

info "Writing .env"
write_env ".env" "$api_key" "$base_url" "$model" "$workspace" "$allow_shell" "$permission_profile" "$approval_mode" "$max_tool_steps" "$twilio_sid" "$twilio_token" "$twilio_from" "$allowed_senders" "$provider_preset"

info "Checking SafeClaw CLI"
.venv/bin/safeclaw tools

run_demo="n"
if [ -n "$api_key" ]; then
  if prompt_yes_no "Run a quick AI test task now" "y"; then
    run_demo="y"
  fi
else
  warn "No API key was entered, so the AI test task will be skipped."
fi

if [ "$run_demo" = "y" ]; then
  info "Running a quick SafeClaw task"
  .venv/bin/safeclaw run "Reply with one short sentence confirming SafeClaw is installed."
fi

cat <<EOF

SafeClaw is ready.

Installed at:
  $install_dir

Config file:
  $install_dir/.env

To use it:
  "$install_dir/.venv/bin/safeclaw" run "make me a todo list app plan"

To invoke safeclaw from any terminal, rerun the guided installer and choose:
  Install safeclaw command globally for any terminal: yes

Then use:
  safeclaw run "make me a todo list app plan"

If your current terminal cannot find safeclaw yet, run:
  export PATH="$bin_dir:\$PATH"

New terminal windows should pick this up automatically.

To start chat mode:
  safeclaw chat

To start WhatsApp webhook mode:
  safeclaw whatsapp --port 8080

EOF

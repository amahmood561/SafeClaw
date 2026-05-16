#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${SAFECLAW_REPO:-https://github.com/amahmood561/SafeClaw.git}"
INSTALL_DIR="${SAFECLAW_DIR:-$HOME/safeclaw}"
REF="${SAFECLAW_REF:-main}"
TASK="${SAFECLAW_TASK:-}"
BIN_DIR="${SAFECLAW_BIN_DIR:-$HOME/.local/bin}"
UPDATE_SHELL_RC="${SAFECLAW_UPDATE_SHELL_RC:-true}"
GLOBAL_INSTALL="${SAFECLAW_GLOBAL:-false}"

info() {
  printf '\033[1;36m==>\033[0m %s\n' "$1"
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
  local launcher="$BIN_DIR/safeclaw"
  mkdir -p "$BIN_DIR"
  cat > "$launcher" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/.venv/bin/safeclaw" "\$@"
EOF
  chmod +x "$launcher"

  case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
      if [ "$UPDATE_SHELL_RC" = "true" ]; then
        local rc_file
        rc_file="$(shell_rc_file)"
        touch "$rc_file"
        if ! grep -Fq "$BIN_DIR" "$rc_file"; then
          {
            printf "\n# SafeClaw CLI\n"
            printf 'export PATH="%s:$PATH"\n' "$BIN_DIR"
          } >> "$rc_file"
        fi
      fi
      ;;
  esac
}

need_command git
need_command python3

if [ -d "$INSTALL_DIR/.git" ]; then
  info "Updating SafeClaw in $INSTALL_DIR"
  git -C "$INSTALL_DIR" fetch --depth 1 origin "$REF"
  git -C "$INSTALL_DIR" checkout "$REF"
  git -C "$INSTALL_DIR" pull --ff-only origin "$REF"
elif [ -e "$INSTALL_DIR" ]; then
  fail "$INSTALL_DIR already exists but is not a git checkout. Set SAFECLAW_DIR to another path."
else
  info "Cloning SafeClaw into $INSTALL_DIR"
  git clone --depth 1 --branch "$REF" "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

info "Creating virtual environment"
python3 -m venv .venv

info "Installing SafeClaw"
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e .

if [ "$GLOBAL_INSTALL" = "true" ]; then
  info "Installing global safeclaw launcher"
  install_launcher
fi

if [ ! -f .env ]; then
  info "Creating .env from .env.example"
  cp .env.example .env
fi

info "Checking the CLI"
.venv/bin/safeclaw tools

if [ -n "$TASK" ]; then
  if [ -z "${OPENAI_API_KEY:-}" ]; then
    fail "SAFECLAW_TASK was set, but OPENAI_API_KEY is missing."
  fi
  info "Running SafeClaw task"
  .venv/bin/safeclaw run "$TASK"
else
  cat <<EOF

SafeClaw is installed.

Next steps:
  cd "$INSTALL_DIR"
  edit .env and set OPENAI_API_KEY
  "$INSTALL_DIR/.venv/bin/safeclaw" run "make me a todo list app plan"

To invoke safeclaw from any terminal, reinstall with:
  curl -fsSL https://raw.githubusercontent.com/amahmood561/SafeClaw/main/install.sh | SAFECLAW_GLOBAL=true bash

Then use:
  safeclaw run "make me a todo list app plan"

If your current terminal cannot find safeclaw yet, run:
  export PATH="$BIN_DIR:\$PATH"

New terminal windows should pick this up automatically.

To install and run a task in one command:
  OPENAI_API_KEY=sk-... SAFECLAW_TASK="summarize this workspace" bash install.sh
EOF
fi

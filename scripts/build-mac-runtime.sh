#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="$ROOT/.build/mac-runtime"
VENV="$BUILD_ROOT/.venv"
RUNTIME_DIR="$ROOT/mac-app/runtime"
LAUNCHER="$BUILD_ROOT/safeclaw_launcher.py"

info() {
  printf '\033[1;36m==>\033[0m %s\n' "$1"
}

fail() {
  printf '\033[1;31merror:\033[0m %s\n' "$1" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || fail "Missing python3"

info "Preparing isolated Python build environment"
rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT" "$RUNTIME_DIR"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install pyinstaller
"$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt"
"$VENV/bin/python" -m pip install "$ROOT"

cat > "$LAUNCHER" <<'PY'
from safeclaw.cli import app

if __name__ == "__main__":
    app()
PY

info "Building bundled SafeClaw CLI runtime"
rm -f "$RUNTIME_DIR/safeclaw-bin"
"$VENV/bin/pyinstaller" \
  --clean \
  --onefile \
  --name safeclaw-bin \
  --distpath "$RUNTIME_DIR" \
  --workpath "$BUILD_ROOT/pyinstaller-work" \
  --specpath "$BUILD_ROOT/pyinstaller-spec" \
  --collect-submodules safeclaw \
  "$LAUNCHER"

chmod +x "$RUNTIME_DIR/safeclaw-bin"

info "Bundled runtime ready: mac-app/runtime/safeclaw-bin"

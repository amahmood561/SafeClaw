#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-}"
REMOTE="${SAFECLAW_REMOTE:-origin}"
BRANCH_PREFIX="${SAFECLAW_RELEASE_BRANCH_PREFIX:-release}"
COMMIT="${SAFECLAW_RELEASE_COMMIT:-true}"
COMMIT_MESSAGE="${SAFECLAW_RELEASE_COMMIT_MESSAGE:-Release $VERSION}"

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

if [ -z "$VERSION" ]; then
  fail "Usage: scripts/release-mac-dmg.sh 0.0.6"
fi

case "$VERSION" in
  v*) TAG="$VERSION" ;;
  *) TAG="$VERSION" ;;
esac

RELEASE_BRANCH="$BRANCH_PREFIX/$VERSION"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

need_command git
need_command npm
need_command python3

CURRENT_BRANCH="$(git branch --show-current)"
if [ -z "$CURRENT_BRANCH" ]; then
  fail "Not on a branch. Checkout a release branch first."
fi

if [ "$CURRENT_BRANCH" != "$RELEASE_BRANCH" ]; then
  fail "Current branch is '$CURRENT_BRANCH'. Checkout '$RELEASE_BRANCH' or run: git checkout -b $RELEASE_BRANCH"
fi

if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  if [ "$COMMIT" != "true" ]; then
    info "Working tree has uncommitted changes."
    git status --short
    fail "Commit or stash changes before releasing, or set SAFECLAW_RELEASE_COMMIT=true."
  fi
  info "Committing release changes"
  git status --short
  git add .
  if git diff --cached --quiet; then
    info "No staged changes to commit"
  else
    git commit -m "$COMMIT_MESSAGE"
  fi
fi

info "Running Python tests"
python3 -m pytest -q

info "Checking Electron app"
npm --prefix mac-app run check

info "Installing Electron dependencies"
npm --prefix mac-app install

info "Building macOS DMG"
rm -rf mac-app/dist
npm --prefix mac-app run build:mac

DMG_COUNT="$(find mac-app/dist -maxdepth 1 -name '*.dmg' | wc -l | tr -d ' ')"
if [ "$DMG_COUNT" = "0" ]; then
  fail "No DMG found in mac-app/dist."
fi

info "Pushing release branch"
git push --set-upstream "$REMOTE" "$RELEASE_BRANCH"

if git rev-parse "$TAG" >/dev/null 2>&1; then
  EXISTING_TAG_COMMIT="$(git rev-list -n 1 "$TAG")"
  HEAD_COMMIT="$(git rev-parse HEAD)"
  if [ "$EXISTING_TAG_COMMIT" != "$HEAD_COMMIT" ]; then
    fail "Tag '$TAG' already exists on a different commit."
  fi
  info "Tag $TAG already exists on this commit"
else
  info "Creating tag $TAG"
  git tag "$TAG"
fi

info "Pushing tag $TAG"
git push "$REMOTE" "$TAG"

info "Release branch, tag, and DMG are ready"
printf "\nNext manual GitHub steps:\n"
printf "1. Open: https://github.com/amahmood561/SafeClaw/releases/new?tag=%s\n" "$TAG"
printf "2. Release title: SafeClaw %s\n" "$VERSION"
printf "3. Upload this DMG:\n"
find mac-app/dist -maxdepth 1 -name '*.dmg' -print
printf "4. Publish the release.\n"

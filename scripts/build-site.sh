#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/site"
OUTPUT_DIR="$ROOT_DIR/site-dist"
TOKEN="${CF_WEB_ANALYTICS_TOKEN:-}"

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
cp -R "$SOURCE_DIR"/. "$OUTPUT_DIR"/

if [[ -z "$TOKEN" ]]; then
  echo "CF_WEB_ANALYTICS_TOKEN is not set; building site without Cloudflare Web Analytics."
  exit 0
fi

if [[ ! "$TOKEN" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "CF_WEB_ANALYTICS_TOKEN contains unsupported characters." >&2
  exit 1
fi

SNIPPET="    <!-- Cloudflare Web Analytics --><script defer src=\"https://static.cloudflareinsights.com/beacon.min.js\" data-cf-beacon='{\"token\":\"$TOKEN\"}'></script><!-- End Cloudflare Web Analytics -->"

for file in "$OUTPUT_DIR"/*.html; do
  tmp="${file}.tmp"
  awk -v snippet="$SNIPPET" '
    /<\/body>/ && inserted == 0 {
      print snippet
      inserted = 1
    }
    { print }
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
done

echo "Built site-dist with Cloudflare Web Analytics injected."

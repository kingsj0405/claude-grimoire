#!/usr/bin/env bash
# Registers claude-grimoire as a local dev plugin via a local marketplace wrapper.
# Safe to run multiple times (idempotent).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MP_ROOT="${HOME}/.claude/plugins/marketplaces/local-dev"
MP_FILE="${MP_ROOT}/.claude-plugin/marketplace.json"
SETTINGS="${HOME}/.claude/settings.json"

if ! command -v jq >/dev/null 2>&1; then
  echo "[error] jq required. brew install jq" >&2
  exit 1
fi

mkdir -p "${MP_ROOT}/.claude-plugin"

cat > "$MP_FILE" <<EOF
{
  "name": "local-dev",
  "owner": {"name": "angelo.yang"},
  "plugins": [
    {
      "name": "grimoire",
      "description": "Circle-based Claude Code maturity tracker",
      "version": "0.1.0",
      "author": {"name": "angelo.yang"},
      "source": "${PLUGIN_ROOT}"
    }
  ]
}
EOF
echo "✓ marketplace.json written: $MP_FILE"

if [[ ! -f "$SETTINGS" ]]; then
  mkdir -p "$(dirname "$SETTINGS")"
  echo '{}' > "$SETTINGS"
fi

BACKUP="${SETTINGS}.bak.$(date +%Y%m%d-%H%M%S)"
cp "$SETTINGS" "$BACKUP"

tmp="$(mktemp)"
jq --arg path "$MP_ROOT" '
  .extraKnownMarketplaces["local-dev"] = {
    source: {source: "local", path: $path}
  }
' "$SETTINGS" > "$tmp"
mv "$tmp" "$SETTINGS"

echo "✓ settings.json updated"
echo "  backup: $BACKUP"
echo
echo "다음 단계:"
echo "  1) Claude Code 재시작"
echo "  2) /plugin install grimoire@local-dev"
echo "  3) /grimoire scan"

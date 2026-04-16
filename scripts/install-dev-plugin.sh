#!/usr/bin/env bash
# Registers claude-grimoire as a local dev plugin via a local marketplace wrapper.
# Safe to run multiple times (idempotent).
#
# Marketplace 내부의 plugin `source`는 marketplace 루트 기준 **상대 경로**만 허용되므로,
# 레포 위치를 옮기지 않기 위해 `plugins/grimoire` 심볼릭 링크로 연결한다.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MP_ROOT="${HOME}/.claude/plugins/marketplaces/local-dev"
MP_FILE="${MP_ROOT}/.claude-plugin/marketplace.json"
PLUGIN_LINK="${MP_ROOT}/plugins/grimoire"
SETTINGS="${HOME}/.claude/settings.json"
AUTHOR="${GRIMOIRE_AUTHOR:-$(git -C "$PLUGIN_ROOT" config user.name 2>/dev/null || echo "you")}"

if ! command -v jq >/dev/null 2>&1; then
  echo "[error] jq required. brew install jq" >&2
  exit 1
fi

mkdir -p "${MP_ROOT}/.claude-plugin" "${MP_ROOT}/plugins"
ln -sfn "$PLUGIN_ROOT" "$PLUGIN_LINK"
echo "✓ symlink: $PLUGIN_LINK → $PLUGIN_ROOT"

cat > "$MP_FILE" <<EOF
{
  "name": "local-dev",
  "owner": {"name": "${AUTHOR}"},
  "plugins": [
    {
      "name": "grimoire",
      "description": "Circle-based Claude Code maturity tracker",
      "version": "0.1.0",
      "author": {"name": "${AUTHOR}"},
      "source": "./plugins/grimoire"
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
    source: {source: "directory", path: $path}
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

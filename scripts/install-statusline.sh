#!/usr/bin/env bash
# Registers claude-grimoire statusline in ~/.claude/settings.json.
# Backs up the existing settings file before modifying.
set -euo pipefail

SETTINGS="${HOME}/.claude/settings.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUSLINE="$(cd "$SCRIPT_DIR/.." && pwd)/statusline/statusline.sh"

if ! command -v jq >/dev/null 2>&1; then
  echo "[error] jq required. brew install jq" >&2
  exit 1
fi

if [[ ! -f "$STATUSLINE" ]]; then
  echo "[error] statusline script not found: $STATUSLINE" >&2
  exit 1
fi

chmod +x "$STATUSLINE"

if [[ ! -f "$SETTINGS" ]]; then
  mkdir -p "$(dirname "$SETTINGS")"
  echo '{}' > "$SETTINGS"
fi

BACKUP="${SETTINGS}.bak.$(date +%Y%m%d-%H%M%S)"
cp "$SETTINGS" "$BACKUP"

tmp="$(mktemp)"
jq --arg cmd "$STATUSLINE" '.statusLine = {type: "command", command: $cmd}' \
   "$SETTINGS" > "$tmp"
mv "$tmp" "$SETTINGS"

echo "✓ statusLine 등록 완료"
echo "  command: $STATUSLINE"
echo "  backup:  $BACKUP"
echo
echo "새 Claude Code 세션에서 상태줄 확인하세요."

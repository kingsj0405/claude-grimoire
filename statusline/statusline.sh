#!/usr/bin/env bash
# claude-grimoire statusline — prints "🔮 C{N} · {title}" from state.json.
# If state.json is missing or malformed, prints a fallback hint.
set -uo pipefail

STATE_FILE="${HOME}/.claude/grimoire/state.json"

if [[ ! -f "$STATE_FILE" ]]; then
  printf '🔮 ? · scan 필요'
  exit 0
fi

if command -v jq >/dev/null 2>&1; then
  line="$(jq -r '"🔮 C\(.circle) · \(.title)"' "$STATE_FILE" 2>/dev/null)"
  if [[ -n "${line:-}" && "$line" != "null"* ]]; then
    printf '%s' "$line"
    exit 0
  fi
fi

# jq가 없거나 파싱 실패 시 Python fallback.
python3 - "$STATE_FILE" <<'PY' 2>/dev/null || printf '🔮 ? · parse 실패'
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        s = json.load(f)
    print(f"🔮 C{s.get('circle','?')} · {s.get('title','?')}", end="")
except Exception:
    print("🔮 ? · parse 실패", end="")
PY

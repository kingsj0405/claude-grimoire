#!/usr/bin/env bash
# claude-grimoire statusline — prints circle prefix for Claude Code statusLine.
#
# Usage:
#   statusline.sh            → single-line "🔮 C{N} · {title}"
#   statusline.sh --mascot   → 3-line ASCII sprite + circle line
#
# Mascot mode outputs sprite lines BEFORE the circle line so that even if the
# info line is long and gets cli-truncated, the sprite is already displayed.
#
# Enable mascot in ~/.claude/statusline-command.sh:
#   export GRIMOIRE_MASCOT=1  (set in your shell profile, e.g. ~/.zshrc)
set -uo pipefail

MASCOT=0
for arg in "$@"; do
    case "$arg" in
        --mascot) MASCOT=1 ;;
    esac
done

STATE_FILE="${HOME}/.claude/grimoire/state.json"
SPRITE_FILE="${HOME}/.claude/grimoire/sprite.txt"

if [[ ! -f "$STATE_FILE" ]]; then
    printf '🔮 ? · scan 필요'
    exit 0
fi

if command -v jq >/dev/null 2>&1; then
    circle="$(jq -r '.circle // empty' "$STATE_FILE" 2>/dev/null)"
    title="$(jq -r '.title // empty' "$STATE_FILE" 2>/dev/null)"
else
    # Python fallback
    read -r circle title < <(python3 - "$STATE_FILE" <<'PY' 2>/dev/null
import json, sys
try:
    s = json.load(open(sys.argv[1], encoding="utf-8"))
    print(s.get("circle", "?"), s.get("title", "?"))
except Exception:
    print("? ?")
PY
    )
fi

circle="${circle:-?}"
title="${title:-?}"

if [[ "$MASCOT" -eq 1 ]] && [[ -f "$SPRITE_FILE" ]]; then
    cat "$SPRITE_FILE"
fi

printf '🔮 C%s · %s' "$circle" "$title"

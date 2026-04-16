---
description: 환경을 스캔해서 내 Claude Code 서클을 판정하고 state.json에 기록합니다.
allowed-tools:
  - Bash
---

현재 작업 디렉토리에서 claude-grimoire 스캐너를 실행하여 사용자의
서클(1-10)을 판정하고 `~/.claude/grimoire/state.json`에 기록한다.

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/grimoire.py" scan`

스캔이 끝나면 Claude는 출력된 강점/성장 포인트 중 가장 중요한 1-2가지를
한글로 요약해서 사용자에게 전달한다. 그 외 장황한 해설은 하지 않는다.

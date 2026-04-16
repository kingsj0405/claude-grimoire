---
description: 현재 서클 기반의 ASCII 마법사 카드를 출력합니다. 같은 이름·같은 서클이면 항상 동일 결과.
allowed-tools:
  - Bash
---

state.json의 username + circle 으로 결정적 마법사 카드를 출력한다.
`--name` 이나 `--circle` 인자는 `$ARGUMENTS`로 전달된다.

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/grimoire.py" card $ARGUMENTS`

카드 출력 뒤에 Claude는 풋터의 룰 텍스트 의미를 한 줄로 설명한다
(git commit은 되돌릴 수 없다 / git revert는 있다는 메타포).

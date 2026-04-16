---
description: N서클 마법책(멘탈 모델 + CLAUDE.md 규약 + 승급 의식)을 출력합니다. 인자에 서클 번호를 주세요 (예. /grimoire book 4).
argument-hint: <circle-number 1-10>
allowed-tools:
  - Bash
---

사용자가 지정한 N서클의 마법책을 출력한다. 인자는 `$ARGUMENTS`에 들어온다.

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/grimoire.py" book $ARGUMENTS`

출력 뒤에 Claude는 다음을 한 문장으로 요약한다:
"이 서클에서 당신이 오늘 시도해볼 만한 한 가지는 X입니다."
(X는 승급 의식에서 즉시 실행 가능한 단계 하나를 골라 제안.)

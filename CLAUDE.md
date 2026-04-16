# claude-grimoire

매 세션 시작 시 반드시 `docs/GUIDELINES.md`를 읽고 프로젝트 컨텍스트를 파악할 것.
작업 상태는 `docs/TODO.md`, `docs/PROGRESS.md`에서 확인할 것.

## 코딩 컨벤션

- Python 3.11+, 표준 라이브러리만 (외부 의존성 없음).
- bash 스크립트는 `set -euo pipefail`.
- 템플릿은 순수 마크다운 + `{{placeholder}}` 미니 문법.

## 금지 패턴

- DO NOT: 외부 의존성 추가 (requests, handlebars, etc.). 필요하면 사유를 TODO.md에.
- DO NOT: ASCII 아트를 스크립트 중간에 인라인으로 박기 — `templates/`에 분리.
- DO NOT: `~/.claude/settings.json`을 백업 없이 수정.
- DO NOT: 절대 경로 하드코딩 (`${CLAUDE_PLUGIN_ROOT}` 또는 `$HOME` 사용).

## 세션 관리

- 시작 시 `docs/TODO.md` 체크
- 종료 시 `docs/PROGRESS.md` 업데이트
- 큰 기능은 feature 브랜치 분리

## 테스트 규칙

- `scripts/grimoire.py`의 스코어링 로직은 경계값에서 수동 확인 (이번 MVP는 자동 테스트 미포함).
- identity 생성기는 같은 입력 2회 호출 시 동일 출력 확인.

## 커밋 메시지

- `feat:` 새 기능
- `fix:` 버그 수정
- `docs:` 문서 수정
- `refactor:` 리팩토링
- `chore:` 빌드/설정 변경

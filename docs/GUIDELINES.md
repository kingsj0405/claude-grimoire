# claude-grimoire 개발 가이드라인

> 이 문서는 claude-grimoire를 개발/확장할 때 참고할 핵심 컨텍스트를 모은다.

## 한 문장 정의

> Claude Code 사용자의 숙련도를 1~10 **서클**로 측정하고, 다음 서클로 성장하기 위한
> 개인 맞춤 **마법책**(CLAUDE.md 규약 + 멘탈 모델)을 생성하는 도구.

## 아키텍처

```
사용자 환경 (CLAUDE.md, tmux, ~/.claude/)
       │
       ▼
  grimoire.py scan
   └→ ~/.claude/grimoire/state.json  ← 단일 상태 파일
       │
       ├→ grimoire.py book <N>  → 마법책 (templates/spellbooks/)
       ├→ grimoire.py card      → ASCII 카드 (동일 입력 → 동일 출력)
       └→ statusline/statusline.sh → 🔮 C{N} · {title}
```

## 서클 체계

| 서클 | 이름 | 핵심 전환점 |
|------|------|-------------|
| 1 | 견습 마법사 | Claude Code를 도구로 인식 |
| 2 | 서기관 | 반복 지시를 문서화 |
| 3 | 이중 시전자 | 작업 간 의존성 판별 |
| 4 | 바람의 직조사 | 작업을 DAG로 시각화 |
| 5 | 성좌 술사 | 감시 세션 분리 |
| 6 | 시간 굴절사 | 세션 간 핸드오프 자동화 |
| 7 | 차원 설계사 | Claude가 Claude를 지시 |
| 8 | 혼돈의 지배자 | 실패를 전제로 한 설계 |
| 9 | 세계수의 현자 | 개인 도구 → 팀 인프라 |
| 10 | 대마법사 | 새 워크플로우 발명 |

각 서클의 **마법책**은 `docs/circles/circle-{N}.md`에 있다 (사용자 노출).
**템플릿**은 `templates/spellbooks/circle-{N}.md`에 있다 (렌더러 입력).

## 채점 루브릭 (0~100 → 1~10)

| 차원 | 최대 | 관측점 |
|------|------|--------|
| claudeMdMaturity | 25 | CLAUDE.md 줄 수, 세션 관리 키워드, 자가 진화 흔적 |
| parallelSessions | 30 | `tmux list-sessions` 개수, 감시/오케스트레이터 역할 |
| automation | 20 | `.claude/commands/` 개수, save-state/resume 커맨드 |
| taskStructure | 15 | `ACTIVE_TASK` 포인터, 태스크 디렉토리 분리 |
| collaboration | 10 | 팀 CLAUDE.md 존재, 공유 프로토콜 |

## 매핑

| 점수 | 서클 |
|------|------|
| 0-10 | 1 |
| 11-20 | 2 |
| 21-30 | 3 |
| 31-40 | 4 |
| 41-50 | 5 |
| 51-60 | 6 |
| 61-70 | 7 |
| 71-80 | 8 |
| 81-90 | 9 |
| 91+ | 10 |

## state.json 스키마

```json
{
  "version": "0.1.0",
  "circle": 5,
  "title": "성좌 술사",
  "score": 45,
  "breakdown": {
    "claudeMdMaturity": 20,
    "parallelSessions": 15,
    "automation": 5,
    "taskStructure": 5,
    "collaboration": 0
  },
  "strengths": ["CLAUDE.md 규약이 성숙합니다"],
  "gaps": ["감시 세션 패턴이 없습니다"],
  "scanned_at": "2026-04-16T10:30:00+09:00",
  "scan_dir": "/path/to/your/project",
  "username": "<current-user>"
}
```

## 결정성 규칙 (카드 생성)

```python
import hashlib
seed = int.from_bytes(
    hashlib.sha256(f"{username}:{circle}".encode()).digest()[:8],
    "big"
)
rng = random.Random(seed)
# 이후 rng로 무기/방어구/스펠 선택 → 같은 입력 2회 호출 시 동일 출력
```

## 원본 가이드

로컬 원본 설계 가이드 (`claude-grimoire-dev-guide.md`)에
Phase 2 MCP, Phase 3 커뮤니티 등 후속 기능이 포함돼 있으나 공개 repo에는 포함하지 않는다.
당장은 MVP만 관심.

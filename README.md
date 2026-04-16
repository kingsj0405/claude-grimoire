# claude-grimoire

> 병렬 마법의 서 · Book of Spells for Claude Code

`claude-grimoire`는 당신의 Claude Code 사용 패턴을 **서클(1~10)** 체계로 판정하고,
다음 서클로 올라가기 위한 **마법책**을 생성하는 CLI + Claude Code 플러그인입니다.

## 빠른 시작 (dev install)

```bash
# 1) 플러그인 루트로 이동
cd /Users/angelo.yang/Projects/src/claude-grimoire

# 2) statusline 등록
bash scripts/install-statusline.sh

# 3) 플러그인을 로컬 마켓플레이스에 등록 (최초 1회)
bash scripts/install-dev-plugin.sh  # 아직 미구현 — docs/INSTALL.md 수동 절차 참고

# 4) Claude Code에서
/plugin install grimoire@local-dev
/grimoire scan
```

statusline에 `🔮 C{N} · {title}`이 뜨면 성공.

## 슬래시 커맨드 (MVP)

- `/grimoire scan` — 환경 스캔 → 서클 판정 → state.json 기록
- `/grimoire book <N>` — N서클 마법책 출력
- `/grimoire card` — ASCII 마법사 카드

## 서클 (1~10)

자세한 내용은 `docs/circles/circle-{1..10}.md`.

## 레퍼런스 가이드

- 설치: `docs/INSTALL.md`
- 개발 가이드라인: `docs/GUIDELINES.md`
- TODO / PROGRESS: `docs/TODO.md`, `docs/PROGRESS.md`

## 라이선스

MIT. See `LICENSE`.

---

> *"No spell of the Grimmerie can be reversed,
> but a loophole exists — another spell to counteract."*

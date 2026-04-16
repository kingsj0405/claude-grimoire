# 설치 가이드

## 1. 사전 요구사항

- macOS (Linux도 대부분 동작하나 MVP 테스트는 macOS만)
- Python 3.11+
- `jq` (`brew install jq`)
- Claude Code 최신

## 2. 플러그인을 dev 모드로 설치

### 2.1. statusline 등록

```bash
cd /Users/angelo.yang/Projects/src/claude-grimoire
bash scripts/install-statusline.sh
```

스크립트가 하는 일:
1. `~/.claude/settings.json`을 `.bak.{타임스탬프}`로 백업.
2. `statusLine.command`를 `<repo>/statusline/statusline.sh`로 설정.

### 2.2. 로컬 마켓플레이스 등록 (최초 1회, 수동)

```bash
mkdir -p ~/.claude/plugins/marketplaces/local-dev/.claude-plugin
```

`~/.claude/plugins/marketplaces/local-dev/.claude-plugin/marketplace.json`:

```json
{
  "name": "local-dev",
  "owner": {"name": "angelo.yang"},
  "plugins": [
    {
      "name": "grimoire",
      "description": "Circle-based Claude Code maturity tracker",
      "version": "0.1.0",
      "author": {"name": "angelo.yang"},
      "source": "/Users/angelo.yang/Projects/src/claude-grimoire"
    }
  ]
}
```

`~/.claude/settings.json`에 (백업 후):

```json
{
  "extraKnownMarketplaces": {
    "local-dev": {
      "source": {
        "source": "local",
        "path": "/Users/angelo.yang/.claude/plugins/marketplaces/local-dev"
      }
    }
  }
}
```

### 2.3. Claude Code 재시작 + 설치

```
/plugin install grimoire@local-dev
```

`/plugin list`에 `grimoire@local-dev`가 보이면 성공.

## 3. 검증

```
/grimoire scan                 # 스캔 + state.json 생성
cat ~/.claude/grimoire/state.json | jq
/grimoire book 3               # 3서클 마법책
/grimoire card                 # ASCII 카드
```

새 Claude Code 세션을 열었을 때 statusline에 `🔮 C{N} · {title}`이 뜨면 완료.

## 4. 문제 해결

### statusline이 뜨지 않는다
- `~/.claude/settings.json`의 `statusLine.command`를 확인.
- `bash statusline/statusline.sh` 직접 실행해서 출력이 나오는지 확인.
- state.json이 없으면 `🔮 ?` fallback이 떠야 한다.

### `/grimoire scan`이 작동하지 않는다
- `/plugin list`로 grimoire가 있는지.
- `${CLAUDE_PLUGIN_ROOT}`이 설정됐는지 (플러그인 컨텍스트 밖에서는 비어있음).
- `python3 scripts/grimoire.py scan`으로 직접 실행해보기.

### 한글이 깨진다
- 터미널 로케일 확인: `echo $LANG` → `en_US.UTF-8` 권장.

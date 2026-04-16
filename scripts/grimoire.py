#!/usr/bin/env python3
"""grimoire — Circle-based Claude Code maturity tracker.

Subcommands:
  scan         환경 수집 → 서클 판정 → state.json 갱신
  book <N>     N서클 마법책 렌더링
  card         현재 서클 기반 ASCII 마법사 카드 렌더링
  show         state.json 요약 출력

State file: ~/.claude/grimoire/state.json
Templates:  ${CLAUDE_PLUGIN_ROOT:-<repo>}/templates/spellbooks/circle-{N}.md
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KST = timezone(timedelta(hours=9))
STATE_DIR = Path.home() / ".claude" / "grimoire"
STATE_FILE = STATE_DIR / "state.json"

REPO_ROOT = Path(
    os.environ.get("CLAUDE_PLUGIN_ROOT")
    or Path(__file__).resolve().parent.parent
)
TEMPLATES_DIR = REPO_ROOT / "templates" / "spellbooks"

# Circle ASCII sprites (3 lines × ~8 cols, pure ASCII — safe for all terminals)
# Written to ~/.claude/grimoire/sprite.txt by `scan`; read by statusline in mascot mode.
CIRCLE_SPRITES: dict[int, str] = {
    1:  "  ,-.  \n ( o ) \n  `-'  ",   # 견습 마법사
    2:  " [mdl] \n (o.o) \n  ---  ",   # 서기관
    3:  "  o o  \n (o-o) \n  \\_/  ",  # 이중 시전자
    4:  " ~v~~v \n (>.o) \n  ---  ",   # 바람의 직조사
    5:  " * . * \n (^.^) \n * . * ",   # 성좌 술사
    6:  " /=o=\\ \n |o.o| \n \\===/ ",  # 시간 굴절사
    7:  " .-o-. \n |X.X| \n `---' ",   # 차원 설계사
    8:  " #X#X# \n (X.X) \n  ---  ",   # 혼돈의 지배자
    9:  "  /|\\  \n (9.9) \n  ---  ",  # 세계수의 현자
    10: " \\*/*/ \n (*.*) \n  ---  ",  # 대마법사
}

CIRCLE_TITLES = {
    1: ("견습 마법사", "Apprentice"),
    2: ("서기관", "Scribe"),
    3: ("이중 시전자", "Dual Caster"),
    4: ("바람의 직조사", "Wind Weaver"),
    5: ("성좌 술사", "Constellation Sorcerer"),
    6: ("시간 굴절사", "Time Refracter"),
    7: ("차원 설계사", "Dimensional Architect"),
    8: ("혼돈의 지배자", "Chaos Master"),
    9: ("세계수의 현자", "World Tree Sage"),
    10: ("대마법사", "Grand Mage"),
}

# 점수 → 서클 경계 (<=)
SCORE_CUTS = [10, 20, 30, 40, 50, 60, 70, 80, 90]

JOB_DIR_RE = re.compile(r"\d{6}-\d{4}-KST")

# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


@dataclass
class Collection:
    project_claude_md: str | None
    global_claude_md: str | None
    project_commands: list[str]
    tmux_sessions: int
    has_tmux_conf: bool
    claude_projects_exists: bool
    has_job_dirs: bool
    has_active_task_tracker: bool
    has_scripts_dir: bool
    git_branches: int


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _tmux_session_count() -> int:
    tmux = shutil.which("tmux")
    if not tmux:
        return 0
    try:
        out = subprocess.run(
            [tmux, "list-sessions"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (subprocess.SubprocessError, OSError):
        return 0
    if out.returncode != 0:
        return 0
    return len([line for line in out.stdout.splitlines() if line.strip()])


def _git_branch_count(cwd: Path) -> int:
    git = shutil.which("git")
    if not git:
        return 0
    try:
        out = subprocess.run(
            [git, "branch", "--list"],
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=3,
        )
    except (subprocess.SubprocessError, OSError):
        return 0
    if out.returncode != 0:
        return 0
    return len([line for line in out.stdout.splitlines() if line.strip()])


def _git_commit_count(cwd: Path, path: str = "CLAUDE.md") -> int:
    """Count how many times a file has been committed (evidence of active maintenance)."""
    git = shutil.which("git")
    if not git:
        return 0
    try:
        out = subprocess.run(
            [git, "log", "--oneline", "--", path],
            capture_output=True, text=True, cwd=str(cwd), timeout=5,
        )
        if out.returncode != 0:
            return 0
        return len([ln for ln in out.stdout.splitlines() if ln.strip()])
    except (subprocess.SubprocessError, OSError):
        return 0


def _count_agent_tool_calls() -> int:
    """Count Agent tool_use lines in messages.jsonl files (metadata scan, no content read)."""
    projects = Path.home() / ".claude" / "projects"
    if not projects.is_dir():
        return 0
    count = 0
    for jsonl in projects.rglob("messages.jsonl"):
        try:
            text = jsonl.read_bytes().decode("utf-8", errors="ignore")
            for line in text.splitlines():
                if '"Agent"' in line and '"tool_use"' in line:
                    count += 1
        except OSError:
            continue
    return count


def collect(cwd: Path) -> Collection:
    project_claude_md = _read(cwd / "CLAUDE.md")
    global_claude_md = _read(Path.home() / ".claude" / "CLAUDE.md")

    commands_dir = cwd / ".claude" / "commands"
    project_commands = (
        sorted(p.name for p in commands_dir.glob("*.md"))
        if commands_dir.is_dir()
        else []
    )

    tmux_sessions = _tmux_session_count()
    has_tmux_conf = (Path.home() / ".tmux.conf").exists()
    claude_projects_exists = (Path.home() / ".claude" / "projects").is_dir()

    docs_dir = cwd / "docs"
    has_job_dirs = False
    has_active_task_tracker = False
    if docs_dir.is_dir():
        for sub in docs_dir.iterdir():
            if sub.is_dir() and JOB_DIR_RE.search(sub.name):
                has_job_dirs = True
                break
        todo = docs_dir / "_todo"
        if todo.is_dir():
            for p in todo.glob("material-*active-task-tracker*.md"):
                has_active_task_tracker = True
                break

    has_scripts_dir = (cwd / "scripts").is_dir()
    git_branches = _git_branch_count(cwd)

    return Collection(
        project_claude_md=project_claude_md,
        global_claude_md=global_claude_md,
        project_commands=project_commands,
        tmux_sessions=tmux_sessions,
        has_tmux_conf=has_tmux_conf,
        claude_projects_exists=claude_projects_exists,
        has_job_dirs=has_job_dirs,
        has_active_task_tracker=has_active_task_tracker,
        has_scripts_dir=has_scripts_dir,
        git_branches=git_branches,
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


SESSION_KEYWORDS = ("session", "세션", "task-save", "task-resume", "/clear", "/save-state")
SELF_EVOL_KEYWORDS = ("self-evolving", "자가 진화", "자가진화", "auto-update")
PIPELINE_KEYWORDS = ("pipeline", "핸드오프", "handoff", "파이프라인")
META_KEYWORDS = ("orchestrator", "오케스트레이터", "메타 오케스트레이션", "분배")
TEAM_KEYWORDS = ("팀 ", "team ", "multi-agent", "다중 에이전트", "shared operating model")


def _score_claude_md(text: str | None) -> tuple[int, list[str], list[str]]:
    strengths: list[str] = []
    gaps: list[str] = []
    if not text:
        gaps.append("CLAUDE.md가 없습니다 — 규약을 문서화해 2서클로 올라가세요.")
        return 0, strengths, gaps

    lines = [ln for ln in text.splitlines() if ln.strip()]
    line_count = len(lines)

    if line_count < 5:
        strengths.append(f"CLAUDE.md가 있습니다 ({line_count}줄).")
        return 5, strengths, gaps

    score = 10
    strengths.append(f"CLAUDE.md가 {line_count}줄로 구체화되어 있습니다.")

    lower = text.lower()
    if any(k in text or k.lower() in lower for k in SESSION_KEYWORDS):
        score = 15
        strengths.append("세션 관리 규약이 포함되어 있습니다.")
    else:
        gaps.append("세션 관리 규약(task-save/resume 등)이 없습니다.")

    # 태스크 분리 (active task tracker, job dir 규약 언급)
    if "active-task-tracker" in lower or "active_task" in lower or "job-dir" in lower or "job dir" in lower:
        score = 20
        strengths.append("태스크별 분리/부트스트랩 규약이 있습니다.")

    if any(k in text or k.lower() in lower for k in SELF_EVOL_KEYWORDS):
        score = 25
        strengths.append("자가 진화 규칙(Claude가 CLAUDE.md를 갱신)을 가지고 있습니다.")

    return score, strengths, gaps


def _score_parallel(col: Collection) -> tuple[int, list[str], list[str]]:
    strengths: list[str] = []
    gaps: list[str] = []

    n = col.tmux_sessions
    if n == 0:
        score = 0
        gaps.append("tmux 세션이 감지되지 않습니다.")
    elif n <= 2:
        score = 10
        strengths.append(f"tmux 세션 {n}개 — 이중 시전이 가능한 기반입니다.")
    elif n <= 4:
        score = 15
        strengths.append(f"tmux 세션 {n}개 — 바람의 직조사 범위에 있습니다.")
    else:
        score = 20
        strengths.append(f"tmux 세션 {n}개 — 성좌 술사 이상의 규모입니다.")

    text = (col.project_claude_md or "") + (col.global_claude_md or "")
    lower = text.lower()

    if any(k in text or k.lower() in lower for k in PIPELINE_KEYWORDS):
        score = max(score, 25)
        strengths.append("핸드오프/파이프라인 언급이 있습니다.")
    else:
        if score < 25:
            gaps.append("파이프라인/핸드오프 규약이 보이지 않습니다.")

    if any(k in text or k.lower() in lower for k in META_KEYWORDS):
        score = max(score, 30)
        strengths.append("메타 오케스트레이션 개념이 문서화되어 있습니다.")
    else:
        if score < 30:
            gaps.append("메타 오케스트레이션(Claude가 Claude를 분배) 규약이 없습니다.")

    return score, strengths, gaps


def _score_automation(col: Collection) -> tuple[int, list[str], list[str]]:
    strengths: list[str] = []
    gaps: list[str] = []

    cmds = col.project_commands
    nc = len(cmds)
    if nc == 0:
        score = 0
        gaps.append(".claude/commands가 없습니다.")
    elif nc <= 3:
        score = 5
        strengths.append(f"커스텀 커맨드 {nc}개.")
    else:
        score = 10
        strengths.append(f"커스텀 커맨드 {nc}개.")

    joined = " ".join(cmds).lower()
    if "save-state" in joined or "task-save" in joined:
        score = max(score, 10)
    if "resume" in joined or "task-resume" in joined:
        score = max(score, 10)
    if "switch-task" in joined or "task-new" in joined:
        score = max(score, 15)
        strengths.append("태스크 전환 자동화 커맨드가 있습니다.")

    if col.has_scripts_dir:
        score = max(score, 20) if score >= 15 else score + 5
        strengths.append("scripts/ 디렉토리에 셸 자동화가 있습니다.")

    return min(score, 20), strengths, gaps


def _score_task_structure(col: Collection) -> tuple[int, list[str], list[str]]:
    strengths: list[str] = []
    gaps: list[str] = []
    score = 0

    if col.has_job_dirs:
        score += 10
        strengths.append("docs/ 아래 YYMMDD-HHMM-KST job 디렉토리가 있습니다.")
    else:
        gaps.append("태스크별 job 디렉토리 구조가 없습니다.")

    if col.has_active_task_tracker:
        score += 5
        strengths.append("active-task-tracker가 운영되고 있습니다.")

    return min(score, 15), strengths, gaps


def _score_collaboration(col: Collection) -> tuple[int, list[str], list[str]]:
    strengths: list[str] = []
    gaps: list[str] = []
    score = 0

    text = col.project_claude_md or ""
    lower = text.lower()

    if text:
        # 팀 언급이 있으면 +5
        if any(k in text or k.lower() in lower for k in TEAM_KEYWORDS):
            score += 5
            strengths.append("팀/다중 에이전트 계약이 CLAUDE.md에 있습니다.")
    if "multi-agent role contract" in lower or "shared operating model" in lower:
        score += 5
        strengths.append("공유 프로토콜(multi-agent role contract)이 정의되어 있습니다.")

    if score == 0:
        gaps.append("팀 공유 규약/프로토콜이 없습니다.")

    return min(score, 10), strengths, gaps


# ---------------------------------------------------------------------------
# Scoring v2 helpers
# ---------------------------------------------------------------------------


def _score_claude_md_v2(
    text: str | None, claude_md_commits: int
) -> tuple[int, list[str], list[str]]:
    """claudeMdMaturity v2: same structure as v1 + git-commit evidence bonus (max 5)."""
    score, strengths, gaps = _score_claude_md(text)
    if claude_md_commits >= 5:
        bonus = 5
        strengths.append(f"CLAUDE.md를 {claude_md_commits}회 이상 커밋하며 운영 중입니다.")
    elif claude_md_commits >= 2:
        bonus = 3
        strengths.append(f"CLAUDE.md를 {claude_md_commits}회 이상 수정했습니다.")
    elif claude_md_commits >= 1:
        bonus = 1
        strengths.append("CLAUDE.md가 최소 1회 커밋되었습니다.")
    else:
        bonus = 0
    return min(score + bonus, 25), strengths, gaps


def _score_parallel_v2(
    col: Collection, agent_call_count: int
) -> tuple[int, list[str], list[str]]:
    """parallelSessions v2: keyword-only boosts capped at 5 when no tmux/agent evidence."""
    strengths: list[str] = []
    gaps: list[str] = []

    n = col.tmux_sessions
    if n == 0:
        base = 0
        has_evidence = False
        gaps.append("tmux 세션이 감지되지 않습니다.")
    elif n <= 2:
        base = 10
        has_evidence = True
        strengths.append(f"tmux 세션 {n}개 — 이중 시전이 가능한 기반입니다.")
    elif n <= 4:
        base = 15
        has_evidence = True
        strengths.append(f"tmux 세션 {n}개 — 바람의 직조사 범위에 있습니다.")
    else:
        base = 20
        has_evidence = True
        strengths.append(f"tmux 세션 {n}개 — 성좌 술사 이상의 규모입니다.")

    # Agent-call evidence bonus (max +5)
    if agent_call_count >= 10:
        base = min(base + 5, 25)
        has_evidence = True
        strengths.append(
            f"서브에이전트 호출 {agent_call_count}회 확인 — 메타 오케스트레이션 실적이 있습니다."
        )
    elif agent_call_count >= 1:
        base = min(base + 2, 25)
        has_evidence = True
        strengths.append(f"서브에이전트 호출 {agent_call_count}회 확인.")

    text = (col.project_claude_md or "") + (col.global_claude_md or "")
    lower = text.lower()

    kw_boost = 0
    if any(k in text or k.lower() in lower for k in PIPELINE_KEYWORDS):
        kw_boost += 15
        strengths.append("핸드오프/파이프라인 언급이 있습니다.")
    else:
        gaps.append("파이프라인/핸드오프 규약이 보이지 않습니다.")

    if any(k in text or k.lower() in lower for k in META_KEYWORDS):
        kw_boost += 10
        strengths.append("메타 오케스트레이션 개념이 문서화되어 있습니다.")
    else:
        gaps.append("메타 오케스트레이션(Claude가 Claude를 분배) 규약이 없습니다.")

    # Keyword cap: no real evidence → max 5 total from keywords
    if not has_evidence:
        kw_boost = min(kw_boost, 5)

    return min(base + kw_boost, 30), strengths, gaps


def score_collection_v2(col: Collection, cwd: Path) -> dict:
    """Rubric v2: evidence-weighted scoring.

    Key differences from v1:
    - claudeMdMaturity: +5 bonus for active git maintenance of CLAUDE.md
    - parallelSessions: keyword-only boosts capped at 5 when tmux=0 and no agent calls
    - Evidence subkey added to result for transparency
    """
    claude_md_commits = _git_commit_count(cwd, "CLAUDE.md")
    agent_calls = _count_agent_tool_calls()

    cm_score, cm_s, cm_g = _score_claude_md_v2(col.project_claude_md, claude_md_commits)
    par_score, par_s, par_g = _score_parallel_v2(col, agent_calls)
    auto_score, auto_s, auto_g = _score_automation(col)
    ts_score, ts_s, ts_g = _score_task_structure(col)
    coll_score, coll_s, coll_g = _score_collaboration(col)

    breakdown = {
        "claudeMdMaturity": cm_score,
        "parallelSessions": par_score,
        "automation": auto_score,
        "taskStructure": ts_score,
        "collaboration": coll_score,
    }
    total = sum(breakdown.values())

    circle = 10
    for idx, cut in enumerate(SCORE_CUTS, start=1):
        if total <= cut:
            circle = idx
            break

    title_ko, _ = CIRCLE_TITLES[circle]
    return {
        "score": total,
        "circle": circle,
        "title": title_ko,
        "breakdown": breakdown,
        "strengths": cm_s + par_s + auto_s + ts_s + coll_s,
        "gaps": cm_g + par_g + auto_g + ts_g + coll_g,
        "evidence": {
            "claude_md_commits": claude_md_commits,
            "tmux_sessions": col.tmux_sessions,
            "agent_tool_calls": agent_calls,
        },
    }


def score_collection(col: Collection) -> dict:
    cm_score, cm_s, cm_g = _score_claude_md(col.project_claude_md)
    par_score, par_s, par_g = _score_parallel(col)
    auto_score, auto_s, auto_g = _score_automation(col)
    ts_score, ts_s, ts_g = _score_task_structure(col)
    coll_score, coll_s, coll_g = _score_collaboration(col)

    breakdown = {
        "claudeMdMaturity": cm_score,
        "parallelSessions": par_score,
        "automation": auto_score,
        "taskStructure": ts_score,
        "collaboration": coll_score,
    }
    total = sum(breakdown.values())

    circle = 10
    for idx, cut in enumerate(SCORE_CUTS, start=1):
        if total <= cut:
            circle = idx
            break

    title_ko, _ = CIRCLE_TITLES[circle]
    return {
        "score": total,
        "circle": circle,
        "title": title_ko,
        "breakdown": breakdown,
        "strengths": cm_s + par_s + auto_s + ts_s + coll_s,
        "gaps": cm_g + par_g + auto_g + ts_g + coll_g,
    }


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------


def load_state() -> dict | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_state(data: dict) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return STATE_FILE


def write_sprite(circle: int) -> Path:
    """Write the circle's ASCII sprite to ~/.claude/grimoire/sprite.txt."""
    sprite_path = STATE_DIR / "sprite.txt"
    sprite = CIRCLE_SPRITES.get(circle, CIRCLE_SPRITES[1])
    sprite_path.write_text(sprite + "\n", encoding="utf-8")
    return sprite_path


# ---------------------------------------------------------------------------
# Subcommand: scan
# ---------------------------------------------------------------------------


def cmd_scan(args: argparse.Namespace) -> int:
    cwd = Path(args.dir).resolve() if args.dir else Path.cwd()
    col = collect(cwd)

    rubric = getattr(args, "rubric", "v1")
    if rubric == "v2":
        result = score_collection_v2(col, cwd)
        version = "0.2.0"
    else:
        result = score_collection(col)
        version = "0.1.0"

    state = {
        "version": version,
        "rubric": rubric,
        "circle": result["circle"],
        "title": result["title"],
        "score": result["score"],
        "breakdown": result["breakdown"],
        "strengths": result["strengths"],
        "gaps": result["gaps"],
        "scanned_at": datetime.now(KST).isoformat(timespec="seconds"),
        "scan_dir": str(cwd),
        "username": os.environ.get("USER") or getpass.getuser(),
        "tmux_sessions": col.tmux_sessions,
        "project_commands": col.project_commands,
    }
    if rubric == "v2" and "evidence" in result:
        state["evidence"] = result["evidence"]
    path = save_state(state)
    write_sprite(result["circle"])

    _, title_en = CIRCLE_TITLES[result["circle"]]
    print(f"✦ 당신의 서클: {result['circle']} ◈ {result['title']} ({title_en})")
    print(f"  총점: {result['score']}/100")
    print()
    print("  강점:")
    for s in result["strengths"] or ["  (없음)"]:
        print(f"    ✓ {s}")
    print()
    print("  성장 포인트:")
    for g in result["gaps"] or ["  (없음)"]:
        print(f"    △ {g}")
    print()
    print(f"  state: {path}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: book
# ---------------------------------------------------------------------------


PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


def render(template: str, context: dict) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        val = context.get(key)
        return str(val) if val is not None else m.group(0)

    return PLACEHOLDER_RE.sub(repl, template)


def cmd_book(args: argparse.Namespace) -> int:
    n = args.circle
    if n < 1 or n > 10:
        print(f"[error] circle must be 1..10, got {n}", file=sys.stderr)
        return 2

    tpl_path = TEMPLATES_DIR / f"circle-{n}.md"
    if not tpl_path.exists():
        print(f"[error] template not found: {tpl_path}", file=sys.stderr)
        return 3

    state = load_state() or {}
    title_ko, title_en = CIRCLE_TITLES[n]
    context = {
        "circle": n,
        "circle_name_ko": title_ko,
        "circle_name_en": title_en,
        "username": state.get("username", os.environ.get("USER") or getpass.getuser()),
        "strengths": "\n".join(f"  - {s}" for s in state.get("strengths", [])) or "  - (scan 먼저 실행)",
        "gaps": "\n".join(f"  - {g}" for g in state.get("gaps", [])) or "  - (scan 먼저 실행)",
    }
    print(render(tpl_path.read_text(encoding="utf-8"), context))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: card (ASCII wizard card)
# ---------------------------------------------------------------------------


WEAPONS = [
    ("분기의 쌍검", "  ╲   ╱\n   ╲ ╱\n    ╳\n   ╱ ╲"),
    ("문서의 룬스태프", "  ╔══╗\n  ║md║\n  ╚══╝\n   ||"),
    ("실행의 지팡이", "   ▲\n   │\n   │\n   ●"),
    ("병렬의 부채", " ╱│╲\n╱ │ ╲\n  │\n  ▼"),
    ("오케스트라의 지휘봉", " ◆\n │\n │\n ●"),
]
ARMORS = [
    ("서기관의 가죽갑옷", "  ╭┬┬╮\n  ┃││┃\n  ┃││┃\n  ╰┴┴╯"),
    ("감시자의 망토", "  ▓▓▓▓\n  ▓░░▓\n  ▓░░▓\n  ▓▓▓▓"),
    ("직조사의 로브", "  ~~~~\n ~~  ~~\n~~    ~~\n~~~~~~~~"),
    ("대마법사의 관", "  ♔\n ╱│╲\n  │\n  │"),
]
ARTIFACTS = [
    ("CLAUDE.md 두루마리", " ▒══▒\n ║md║\n ▒══▒"),
    ("tmux 결정의 구슬", "  ▒▒▒\n ▒◯◯▒\n ▒▒▒▒"),
    ("세션 나침반", "  ╔═╗\n  ║✦║\n  ╚═╝"),
    ("Grimmerie 파편", "  ╔══╗\n  ║☾ ║\n  ╚══╝"),
]
PREFIXES = [
    "심연의", "고독한", "바람의", "별의", "불꽃의", "서리의", "새벽의", "황혼의", "침묵의", "천둥의",
]
EPITHETS = [
    "디버거", "직조사", "수호자", "순례자", "필사자", "조율자", "관측자", "설계사", "해석자", "기록자",
]

SPELL_POOL = [
    "claude --help",
    "CLAUDE.md 작성술",
    "tmux split-window",
    "/save-state 결계",
    "/resume 소환",
    "/task-new 선언",
    "/task-list 순례",
    "git commit 맹세",
    "git revert 역주문",
    "DAG 직조",
    "감시 세션 배치",
    "handoff 파이프라인",
    "orchestrator 위임",
    "체크포인트 봉인",
    "team CLAUDE.md 전승",
]


def _seeded_rng(username: str, circle: int) -> random.Random:
    h = hashlib.sha256(f"{username}:{circle}".encode()).digest()
    seed = int.from_bytes(h[:8], "big")
    return random.Random(seed)


@dataclass
class Equipment:
    name: str
    art: str


@dataclass
class Spell:
    name: str
    level: int


@dataclass
class Identity:
    username: str
    circle: int
    magic_name: str
    title: str
    weapon: Equipment
    armor: Equipment
    artifact: Equipment
    spells: list[Spell]


def generate_identity(username: str, circle: int) -> Identity:
    rng = _seeded_rng(username, circle)
    title_ko, _ = CIRCLE_TITLES[circle]
    magic_name = f"{rng.choice(PREFIXES)} {rng.choice(EPITHETS)} {username}"
    weapon = Equipment(*rng.choice(WEAPONS))
    armor = Equipment(*rng.choice(ARMORS))
    artifact = Equipment(*rng.choice(ARTIFACTS))

    # 5개 스펠: 서클이 높을수록 레벨 up 가능성 증가
    pool = rng.sample(SPELL_POOL, k=min(5, len(SPELL_POOL)))
    spells = []
    for i, name in enumerate(pool):
        max_lv = min(5, circle)
        lv = rng.randint(1, max_lv) if max_lv >= 1 else 1
        spells.append(Spell(name=name, level=lv))

    return Identity(
        username=username,
        circle=circle,
        magic_name=magic_name,
        title=title_ko,
        weapon=weapon,
        armor=armor,
        artifact=artifact,
        spells=spells,
    )


def _char_width(c: str) -> int:
    if ord(c) == 0:
        return 0
    if unicodedata.east_asian_width(c) in ("W", "F"):
        return 2
    # 이모지(보통 Neutral로 분류)는 별도 처리: 2 col로 카운트
    if 0x1F300 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF:
        return 2
    return 1


def _visual_width(text: str) -> int:
    return sum(_char_width(c) for c in text)


def _pad(line: str, width: int) -> str:
    visual = _visual_width(line)
    if visual > width:
        # 넘치면 잘라내기 (MVP: 단순 절단)
        out = ""
        acc = 0
        for c in line:
            w = _char_width(c)
            if acc + w > width:
                break
            out += c
            acc += w
        return out + " " * max(0, width - acc)
    return line + " " * max(0, width - visual)


def render_card(identity: Identity) -> str:
    inner = 40
    top = "╔" + "═" * (inner + 2) + "╗"
    bot = "╚" + "═" * (inner + 2) + "╝"
    sep = "╠" + "═" * (inner + 2) + "╣"

    lines: list[str] = [top]
    lines.append(f"║ {_pad('🔮 CLAUDE GRIMOIRE — 마법사 카드', inner)} ║")
    lines.append(sep)
    lines.append(f"║ {_pad('', inner)} ║")
    lines.append(f"║ {_pad('✦ ' + identity.magic_name, inner)} ║")
    lines.append(f"║ {_pad('「' + identity.title + '」· ' + str(identity.circle) + '서클', inner)} ║")
    lines.append(f"║ {_pad('', inner)} ║")
    lines.append(sep)
    lines.append(f"║ {_pad('⚔ ' + identity.weapon.name, inner)} ║")
    for art_line in identity.weapon.art.splitlines():
        lines.append(f"║ {_pad('  ' + art_line, inner)} ║")
    lines.append(f"║ {_pad('🛡 ' + identity.armor.name, inner)} ║")
    for art_line in identity.armor.art.splitlines():
        lines.append(f"║ {_pad('  ' + art_line, inner)} ║")
    lines.append(f"║ {_pad('💎 ' + identity.artifact.name, inner)} ║")
    for art_line in identity.artifact.art.splitlines():
        lines.append(f"║ {_pad('  ' + art_line, inner)} ║")
    lines.append(sep)
    lines.append(f"║ {_pad('📖 습득 마법', inner)} ║")
    for sp in identity.spells:
        line = f" · {sp.name:<22} Lv.{sp.level}"
        lines.append(f"║ {_pad(line, inner)} ║")
    lines.append(sep)
    if identity.circle <= 5:
        rule_lines = ["No spell of the Grimmerie", "can be reversed."]
    else:
        rule_lines = ["But a loophole exists —", "another spell to counteract."]
    for rl in rule_lines:
        lines.append(f"║ {_pad(rl, inner)} ║")
    if identity.circle == 10:
        lines.append(f"║ {_pad('The Grimmerie has opened for you.', inner)} ║")
    lines.append(bot)
    return "\n".join(lines)


CLIPBOARD_COMMANDS = (
    ["pbcopy"],
    ["wl-copy"],
    ["xclip", "-selection", "clipboard"],
    ["xsel", "--clipboard", "--input"],
)


def _copy_to_clipboard(payload: str) -> tuple[bool, str]:
    for cmd in CLIPBOARD_COMMANDS:
        if not shutil.which(cmd[0]):
            continue
        try:
            subprocess.run(cmd, input=payload, text=True, check=True, timeout=5)
        except (subprocess.SubprocessError, OSError) as exc:
            return False, f"{cmd[0]}: {exc}"
        return True, cmd[0]
    return False, "no clipboard tool found (pbcopy/wl-copy/xclip/xsel)"


def cmd_card(args: argparse.Namespace) -> int:
    state = load_state()
    username = (
        args.name
        or (state or {}).get("username")
        or os.environ.get("USER")
        or getpass.getuser()
    )
    circle = args.circle or (state or {}).get("circle")
    if circle is None:
        print("[hint] state.json이 없습니다. `grimoire scan`을 먼저 실행하세요.", file=sys.stderr)
        circle = 1
    if circle < 1 or circle > 10:
        print(f"[error] circle must be 1..10, got {circle}", file=sys.stderr)
        return 2
    identity = generate_identity(username, circle)
    payload = render_card(identity)
    if args.markdown:
        payload = "```\n" + payload + "\n```"

    did_side_effect = False
    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
        print(f"[card] saved to {out_path}", file=sys.stderr)
        did_side_effect = True
    if args.copy:
        ok, info = _copy_to_clipboard(payload)
        if ok:
            print(f"[card] copied to clipboard via {info}", file=sys.stderr)
        else:
            print(f"[card] clipboard copy failed: {info}", file=sys.stderr)
            return 4
        did_side_effect = True

    if not did_side_effect:
        print(payload)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: show
# ---------------------------------------------------------------------------


def cmd_show(_: argparse.Namespace) -> int:
    state = load_state()
    if not state:
        print("[hint] state.json이 없습니다. `grimoire scan`을 먼저 실행하세요.")
        return 1
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grimoire", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="환경 수집 + 서클 판정 + state.json 기록")
    p_scan.add_argument("--dir", help="스캔할 프로젝트 루트 (기본: cwd)")
    p_scan.add_argument(
        "--rubric",
        choices=["v1", "v2"],
        default="v1",
        help="채점 루브릭 버전 (v1: 기본/keyword-only, v2: evidence-weighted)",
    )
    p_scan.set_defaults(func=cmd_scan)

    p_book = sub.add_parser("book", help="N서클 마법책 출력")
    p_book.add_argument("circle", type=int, help="서클 번호 (1~10)")
    p_book.set_defaults(func=cmd_book)

    p_card = sub.add_parser("card", help="ASCII 마법사 카드 출력")
    p_card.add_argument("--name", help="이름 오버라이드 (기본: state.json의 username)")
    p_card.add_argument("--circle", type=int, help="서클 오버라이드")
    p_card.add_argument("--out", help="렌더링 결과를 파일로 저장 (stdout 출력은 생략)")
    p_card.add_argument("--copy", action="store_true", help="클립보드에 복사 (pbcopy/wl-copy/xclip/xsel)")
    p_card.add_argument("--markdown", action="store_true", help="``` 코드블록으로 래핑")
    p_card.set_defaults(func=cmd_card)

    p_show = sub.add_parser("show", help="state.json 요약 출력")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

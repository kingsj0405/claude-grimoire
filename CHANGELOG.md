# Changelog

All notable changes to **claude-grimoire** are documented in this file.

This project adheres to [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-04-17

### Added
- **Rubric v2** (`--rubric v2`): evidence-weighted scoring that complements the
  default keyword-only v1 rubric. New evidence collectors:
  - `_git_commit_count(cwd, "CLAUDE.md")` — counts commits touching CLAUDE.md
    as a maturity signal (≥5 → +5, ≥2 → +3, ≥1 → +1; max 25 in `claudeMdMaturity`).
  - `_count_agent_tool_calls()` — scans `~/.claude/projects/**/messages.jsonl`
    metadata for `Agent` tool_use lines (no message content read).
  - When `tmux=0 AND agent_tool_calls=0`, `parallelSessions` keyword boost is
    capped at 5 points (deterministic anti-inflation). `agent_calls ≥10 → +5`,
    `≥1 → +2` evidence bonuses.
  - `score_collection_v2()` returns an `evidence` sub-key alongside the
    breakdown for transparency.
- **Mascot ASCII sprite** in statusline (`statusline/statusline.sh --mascot` +
  `GRIMOIRE_MASCOT=1` env var):
  - `CIRCLE_SPRITES` — 10 circle-specific 3-line ASCII sprites (~8 cols, pure
    ASCII, `cli-truncate` safe).
  - `write_sprite(circle)` — emits `~/.claude/grimoire/sprite.txt` on every scan.
  - Statusline prints the sprite first so the mascot survives even when the
    info line gets truncated.
- **`grimoire card` share flags**:
  - `--out <path>` — write card to file (parent `mkdir -p`, stderr ack).
  - `--copy` — clipboard copy with `pbcopy → wl-copy → xclip → xsel` fallback.
  - `--markdown` — wrap payload in a fenced code block for Slack/Discord/GitHub.
  - When a side-effect flag is set, stdout output is suppressed for quiet sharing.
- **`commands/grimoire-scan.md`**: documents `--rubric v2` and `GRIMOIRE_MASCOT`
  activation.
- **`CHANGELOG.md`** (this file).

### Changed
- **`install-dev-plugin.sh`** — author placeholderized:
  `${GRIMOIRE_AUTHOR:-$(git config user.name)}` instead of hardcoded
  `angelo.yang`. Heredoc switched from `'EOF'` (literal) to `EOF` (interpolating)
  to allow variable substitution.
- **Marketplace integration** — `marketplace.json` `source` field now uses
  marketplace-relative `./plugins/grimoire` (the only format Claude Code
  accepts) instead of an absolute path. The `install-dev-plugin.sh` script
  creates a `plugins/grimoire` symlink to the canonical repo location.
- **`README.md` / `docs/INSTALL.md` / `docs/GUIDELINES.md`** — removed all
  hardcoded local paths (`/Users/angelo.yang/...`) for public-repo readiness.
  Replaced with `/path/to/claude-grimoire`, `<your-name>`, and `$HOME`
  placeholders. Added marketplace-source schema warning to INSTALL.

### Empirical Validation
- 3-repo × v1/v2 scan benchmark on 2026-04-17 confirms v2 deterministically
  caps keyword inflation:
  - `claude-grimoire` (small repo): 20/C2 → 21/C3 (**+1**, fairer to small projects)
  - `exaone_individual` (keyword-rich): 75/C8 → 60/C6 (**−15**)
  - `lgair_sejong_root` (keyword-rich): 90/C9 → 75/C8 (**−15**)
- Pattern: keyword-rich CLAUDE.md repos consistently lose 15 points to v2
  cap; small repos gain from CLAUDE.md commit evidence bonus.
- Distribution narrows from C2~C9 (v1) to C3~C8 (v2).

## [0.1.0] — 2026-04-16

### Added
- Initial **MVP**: Claude Code plugin + CLI that scores a repo's
  Claude-Code skill level on a 1~10 circle ladder.
- `scripts/grimoire.py` — `scan` / `book` / `card` / `show` subcommands,
  stdlib-only, deterministic card generation.
- `scripts/install-dev-plugin.sh` + `scripts/install-statusline.sh` —
  dev plugin / marketplace bootstrap.
- `templates/spellbooks/circle-{1..10}.md` — 10 spellbook templates,
  4-section format (mental model + CLAUDE.md conventions + ascension ritual + lore).
- `commands/grimoire-{scan,book,card}.md` — 3 slash commands.
- `statusline/statusline.sh` — base statusline rendering current circle
  (`🔮 C{N} · {title}` prefix).
- `CLAUDE.md`, `README.md`, `LICENSE`, `docs/INSTALL.md`,
  `docs/GUIDELINES.md`, `docs/circles/README.md`, `.claude-plugin/plugin.json`.
- `~/.claude/grimoire/state.json` schema.

### Validated
- Initial scan of `lgair_sejong_root` returns circle 9 / 90 points (within
  the predicted 75–90 band).
- Card generation is deterministic across repeated invocations.
- Spellbook output structure aligns with the original 6.3 design guide.

[0.2.0]: https://github.com/kingsj0405/claude-grimoire/releases/tag/v0.2.0
[0.1.0]: https://github.com/kingsj0405/claude-grimoire/releases/tag/v0.1.0

# Trail — phased implementation discipline for Claude Code

Trail makes long implementations recoverable by leaving the repo with a
durable, structured trail of decisions and phase boundaries — so any
future session, agent, or teammate can rejoin without re-deriving why
things are the way they are.

Sibling to [trail-codex-skill](https://github.com/anuj81/trail-codex-skill);
shares the methodology, rebuilt around Claude Code's skill model with
tag-based capsules, dynamic context injection, opt-in hook enforcement,
and an independent audit subagent.

## Quick start

```
/trail plan          → write the trace plan in plan mode, sign off, scaffold branch
/trail phase <N>     → start phase N (risk-classified, TaskCreate-backed)
/trail commit        → close phase: validate → capsule → tag → update NEXT.md
/trail audit         → independent Plan-subagent review (auto-required after N%3==0)
/trail finalize      → prepare for merge: gap-check phases, generate PR body
/ts                  → show current state (read-only, instant)
```

## What Trail does

Implementations larger than a few hours have predictable failure modes:
plans drift from execution, validation gets skipped under pressure, the
implementation log lies once it's no longer being honestly maintained,
and context compaction destroys the reasoning that made the code make
sense. Trail addresses each of these structurally rather than relying on
discipline alone:

- **Feature-branch + micro-commits.** Work happens on
  `claude/<feature-slug>`. Inside a phase, commit freely with meaningful
  messages — these are the bisect targets and the safety net against
  mid-phase loss.
- **Tag-based phase boundaries.** Each phase ends with
  `git tag -a phase/<feature-slug>-N -F /tmp/trail-capsule.txt`. The
  capsule lives in the tag annotation: immutable, atomic with the code
  state it describes, visible in `git show` and GitHub.
- **Live handoff in `.trail/NEXT.md`.** Editable mid-phase so you can
  leave a marker before walking away. `.trail/` is in `.gitignore`;
  feature-branch commits use `git add -f` (Trail commands handle this
  automatically). On merge to main, `.trail/` doesn't follow.
- **Risk-graduated discipline.** Each phase is classified low/medium/high
  at plan time and re-classified at start. High risk requires `/review`
  and (if it touches auth/secrets/deps) `/security-review` before tag.
  Re-classification is upgrade-only — risk ratchets, never relaxes.
- **Plan amendment ritual.** Every capsule includes a one-line answer to
  "are remaining phases still right?" Forces re-planning to be a
  deliberate act, not a silent drift.
- **Mechanically enforced audit at every 3rd phase.** A forked Plan
  subagent reviews plan-vs-reality using tag annotations only.
  `/trail commit` writes a `.trail/audit-required-N.flag` file; the
  guard-tag hook blocks the next phase tag until `/trail audit` clears
  the flag. The cadence isn't optional.
- **Post-compaction recovery.** Source of truth is git tags + NEXT.md +
  plan.md, in that order. The chat transcript is not trusted.

## Install

```bash
git clone https://github.com/anuj81/trail-claude-skill.git
cd trail-claude-skill

# Personal install (recommended)
mkdir -p ~/.claude/skills
cp -R skills/trail ~/.claude/skills/
cp -R skills/ts ~/.claude/skills/

# Or symlink to track upstream:
ln -s "$(pwd)/skills/trail" ~/.claude/skills/trail
ln -s "$(pwd)/skills/ts"    ~/.claude/skills/ts
```

`references/` lives inside `skills/trail/`, so the copy above includes
everything Claude needs. For project-only install, use `.claude/skills/`
in the project root instead.

Add `.trail/` to your project's `.gitignore` so plan/NEXT files stay on
feature branches and don't merge to main:

```bash
echo ".trail/" >> .gitignore
```

(Trail commands use `git add -f` to commit `.trail/plan.md` and
`.trail/NEXT.md` on the feature branch despite the gitignore. This is
the standard pattern for branch-local working files.)

Verify:

```
claude
> /ts
```

Should print "(no phase tags yet)" / "(no .trail/NEXT.md on this branch)"
in a non-Trail repo, or actual state in a Trail-managed one.

## Permissions & trust

Default `allowed-tools` in `/trail` cover read-only git inspection,
script execution under the skill's `scripts/` directory, `Read`/`Grep`/`Glob`,
and `Write` scoped to `/tmp/trail-*` (for capsule and audit-prompt files).
**No mutating git operations are pre-approved.** Branch creation, commits,
tags, and resets all prompt for permission per use.

This is deliberate: silent execution of `git tag` or `git reset` against
your repo is exactly the kind of "I didn't realize Claude could do that"
surprise that erodes trust. Trade-off is one extra approval click per
mutation. Worth it.

If you want lower friction after you've audited the skill, paste a
permissions snippet into `~/.claude/settings.json` (or project
`.claude/settings.json` for per-repo scope):

```jsonc
{
  "permissions": {
    "allow": [
      "Bash(git switch -c claude/*)",
      "Bash(git tag -a phase/*)",
      "Bash(git commit *)",
      "Bash(git add -f .trail/*)"
    ]
  }
}
```

## Opt-in hooks

Two hooks deepen Trail's discipline. They're shipped as a snippet, not
auto-installed, because **opt-in hooks are functionally equivalent to
`allowed-tools` from a trust perspective** — you're granting the script
permission to execute on every matching tool call. Review the script
sources under `skills/trail/scripts/` before installing.

### `guard-tag` (PreToolUse on Bash)

Blocks `git tag phase/*` when:

- the tag name doesn't follow `phase/<feature-slug>-N[-attempt-K]`
- the annotation message is missing required capsule sections for the
  declared risk level
- the message uses `-m "$(cat ...)"` (which arrives at the hook as
  unevaluated literal text — use `-F /path/to/file` instead)
- `.trail/NEXT.md` exists but doesn't reference the next phase
- a prior phase has a pending `audit-required-*.flag` file

Silent on every other Bash invocation. Set `TRAIL_HOOK_DEBUG=1` in your
environment to log raw hook payloads to stderr if the hook seems silent
when you expected it to fire.

### `Stop` trace_status

Prints current Trail state at session end as a safety net for context
loss. Self-suppresses on non-Trail repos so non-Trail sessions stay quiet.

Install both by merging `hooks/settings.snippet.json` into your
`~/.claude/settings.json`. The snippet uses `$HOME` for portability; if
your hook runner doesn't expand environment variables, replace with the
absolute path to your home directory.

## Sub-commands

| Command | Purpose |
|---|---|
| `/trail plan` | New feature: write trace plan in plan mode, sign off, scaffold branch |
| `/trail phase <N>` | Start phase N: classify risk, create tasks, implement with micro-commits |
| `/trail commit` | Close phase: run validation, compose capsule, update NEXT.md, tag |
| `/trail audit` | Independent Plan-subagent review (required after every 3rd phase + on risk upgrade) |
| `/trail finalize` | Prepare for merge: phase-count gap check, generate PR body from tags |
| `/trail resume` | Continue from current state (reads NEXT.md + latest tag) |
| `/trail capsule [N]` | Show tag annotation for phase N (latest if omitted) |
| `/trail rollback <N>` | Guided rollback walking through soft/medium/hard options |
| `/ts` | Read-only status: phase tags, latest capsule, NEXT.md, branch state |

`/ts` is its own skill rather than `/trail status` because it's used many
times per session and deserves the shorter command.

**Name-collision note:** `/ts` is a very short slash command. If a future
Claude Code release ships a bundled skill named `ts` (TypeScript helper,
say), it will shadow this one. Rename to `/trail-status` if you'd rather
own the namespace yourself — just rename the directory after copying:
`mv ~/.claude/skills/ts ~/.claude/skills/trail-status`.

## Risk classification

Cheap signals run at phase start via `phase_check.py classify-risk`:

- **High** if any path matches `auth|secret|credential|migration|schema|crypto` or sits under `migrations/`, `db/`, `schemas/`
- **Medium** if any path was touched by ≥3 distinct authors in the last 7 days
- **Low** otherwise

Re-classification is upgrade-only — if signals say a planned-low phase is
actually high, upgrade and tell the user. Never silently relax.

## Recovery

Things go wrong. `skills/trail/references/recovery.md` covers:

- Resuming after compaction or in a new session
- Three rollback options (branch-from-tag, revert, hard reset)
- Recording a failed phase as a permanent attempt tag
- Recovering when `.trail/NEXT.md` is missing
- Handling guard-tag blocks (including the audit-flag block)
- Reconciling when the transcript and the repo disagree (repo always wins)

## Differences vs the codex sibling

Same methodology, redesigned around Claude Code:

- Capsule lives in the **git tag annotation** instead of a markdown log
  file → atomic with code state, no drift, no file to clean up
- Phase boundaries are **annotated tags** instead of squash commits →
  micro-commits preserved for bisect
- **Two skills** (`/trail` + `/ts`) instead of resume commands inside one
  workflow doc → status gets its own one-key entry
- **Risk-graduated discipline** with classify-risk script driving M+
  section requirements → not all phases pay the full ritual cost
- **Mechanically enforced audit** every 3rd phase via audit-required
  flag file + guard-tag check → cadence isn't optional, not just prose
- **Opt-in hooks** for guard-tag + Stop trace_status → mechanical
  enforcement layered on top of prose discipline
- **Dynamic context injection** in SKILL.md → skill loads with live repo
  state, no negotiation
- Branch prefix `claude/<slug>`, tag namespace `phase/<slug>-N`

The codex version is simpler. If you don't need the audit/risk/hook
layers, that version is a fine choice and the methodology transfers.

## Limitations

- Requires git. Tags are the spine; non-git VCS is out of scope.
- Phase tag namespace can collide across teammates if you push and two
  developers both tag `phase/add-export-1`. Slug discrimination
  (`phase/<feature-slug>-N`) makes collision unlikely but not impossible
  on parallel features.
- `guard-tag` checks capsule structure, not truth. Validation results
  can be faked by typing them into the capsule without running the
  commands. For high-stakes work, configure CI to re-run validation
  against each `phase/*` tag.
- Skill content stays in context across the session. `/trail` is heavy;
  if you're not actively using it, use `/ts` for status checks instead.

## Validation

Smoke-test the scripts against any git repo (including this one):

```bash
# trace_status self-suppresses on non-Trail repos
python3 skills/trail/scripts/trace_status.py .

# Namespace enforcement
python3 skills/trail/scripts/phase_check.py enforce-namespace phase/add-export-1   # ok
python3 skills/trail/scripts/phase_check.py enforce-namespace phase/BAD_NAME       # exit 1

# Risk classification
python3 skills/trail/scripts/phase_check.py classify-risk src/auth/middleware.ts   # high
python3 skills/trail/scripts/phase_check.py classify-risk src/components/Btn.tsx   # low

# Audit-flag lifecycle (run inside a git repo)
python3 skills/trail/scripts/phase_check.py mark-audit-required 3
ls .trail/audit-required-3.flag
python3 skills/trail/scripts/phase_check.py clear-audit-flags

# Audit prompt generation (requires .trail/plan.md to exist)
python3 skills/trail/scripts/phase_check.py build-audit-prompt
```

## License

MIT. See LICENSE.

---
name: trail
description: Plan and implement large or risky changes as traceable phases on a feature branch. Micro-commits during phases, tag-based phase boundaries with capsules in tag annotations, .trail/NEXT.md for live handoff, plan amendment ritual, risk-graduated discipline, optional independent audit. Use for multi-phase features, refactors, architecture changes, work that may exceed context, or any change you want to bisect and resume cleanly.
when_to_use: |
  Trigger on phrases like "use trail", "with phase commits", "trace this",
  "resumable", "auditable", "large refactor", "architecture change",
  "phased implementation", or when the user opens any file under .trail/.
  Skip typo fixes, one-line patches, and isolated bug fixes.
effort: high
paths:
  - .trail/**
allowed-tools: Bash(git status *) Bash(git log *) Bash(git diff *) Bash(git show *) Bash(git tag -l*) Bash(git tag -n*) Bash(git branch --show-current) Bash(git branch -l*) Bash(git rev-parse *) Bash(git for-each-ref *) Bash(git rev-list *) Bash(python3 *trail/scripts/*) Read Write(/tmp/trail-*) Grep Glob
---

# Trail

Mutating git operations (branch creation, tag creation, commits, resets)
are intentionally NOT pre-approved. Confirm with the user before each.

## Current state

- Branch + worktree: !`git status --short --branch 2>/dev/null || echo '(not a git repo)'`
- Recent commits: !`git log --oneline -n 10 2>/dev/null || echo '(no commits)'`
- Phase tags: !`git tag -l 'phase/*' --sort=-taggerdate 2>/dev/null | head -20 || true`
- Trail snapshot: !`python3 ${CLAUDE_SKILL_DIR}/scripts/trace_status.py . 2>/dev/null || true`

## Dispatch

Read `$ARGUMENTS`. The first word is the sub-command. If absent or
unrecognized, infer from the snapshot above (e.g., no `.trail/plan.md` →
`plan`; latest tag exists and validation pending → `commit`).

### `plan` — write the trace plan

For new features. Run in plan mode so the user signs off before any code.

1. `EnterPlanMode`.
2. Inspect repo: existing architecture docs, CLAUDE.md, manifests for
   test/build/lint commands, ownership boundaries.
3. Propose feature-slug and branch `claude/<feature-slug>`. Confirm with
   user before creating the branch. Never implement directly on `main`,
   `master`, `trunk`, `develop`, release branches, or anything protected.
4. Write the trace plan per `references/templates.md` (Trace plan template).
   Include risk classification per phase with one-line rationale.
5. `ExitPlanMode` for approval.
6. After approval, create the feature branch and scaffold `.trail/`.
   `.trail/` is in the repo's `.gitignore` (Trail ships with this), so
   plan and NEXT files require `-f` to commit on the feature branch:
   ```bash
   git switch -c claude/<feature-slug>
   mkdir -p .trail
   # write .trail/plan.md (Write tool)
   git add -f .trail/plan.md
   git commit -m "chore(trail): scaffold trace plan"
   ```
   Confirm before each git operation.

### `phase <N>` — start phase N

1. Read `.trail/plan.md` (use `${CLAUDE_SKILL_DIR}/references/templates.md`
   if you need to remind yourself of the format).
2. Read latest `phase/<feature-slug>-K` annotation:
   `git show <tag> --no-patch --format='%(contents)'`.
3. Read `.trail/NEXT.md` for in-flight notes.
4. Re-classify risk for the files this phase will touch:
   `python3 ${CLAUDE_SKILL_DIR}/scripts/phase_check.py classify-risk <files...>`.
   Risk ratchets upward only — if the script returns higher than the plan,
   upgrade and tell the user; never downgrade.
5. Create TaskCreate entries for the phase's checklist so progress is
   visible. Update as tasks complete.
6. Implement. **Micro-commit freely** on the feature branch with meaningful
   messages — these are the bisect targets. Update architecture docs
   inline where structure changes (required for medium and high risk).
7. Mid-phase: if you hit a natural sub-task boundary, edit `.trail/NEXT.md`
   (then `git add -f .trail/NEXT.md && git commit -m "wip(trail): mid-phase note"`)
   so a future session has a marker.

### `commit` — close out the current phase

1. Run validation commands from the plan. Capture exact output.
2. Compose the capsule per `references/templates.md`. **Write it to
   `/tmp/trail-capsule.txt` using the Write tool** — `Write(/tmp/trail-*)`
   is pre-approved so this is silent. The file must include a `Risk: <level>`
   line; required sections depend on risk and `guard-tag` enforces them.
3. Overwrite `.trail/NEXT.md` with the next-phase handoff.
4. Confirm capsule + NEXT update with user. Then tag using `-F` (not `-m`):
   ```bash
   git tag -a phase/<feature-slug>-N -F /tmp/trail-capsule.txt HEAD
   git add -f .trail/NEXT.md
   git commit -m "chore(trail): phase N capsule + NEXT update"
   ```
   `-F` is required for multi-line capsules: the guard-tag hook reads the
   shell command before substitution, so `-m "$(cat ...)"` arrives as
   literal text and is rejected.
5. If risk is medium or high, offer `/review` of the diff range from the
   previous phase tag (or branch start) to HEAD. For high risk touching
   auth, secrets, or dependencies, also offer `/security-review`.
6. If `N % 3 == 0` OR risk just upgraded, mark audit as required:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/phase_check.py mark-audit-required N
   ```
   `guard-tag` will block the next phase tag until `/trail audit` runs.
   This is mechanical enforcement of the audit cadence.
7. Show the user the new tag with `git show phase/<feature-slug>-N --no-patch`.

### `audit` — independent plan-vs-reality review

Build the audit prompt:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/phase_check.py build-audit-prompt > /tmp/trail-audit-prompt.txt
```

Spawn a forked Plan subagent (Agent tool, `subagent_type=Plan`) with the
contents of `/tmp/trail-audit-prompt.txt` as the prompt. The script
reads `.trail/plan.md` and all phase tag annotations and constructs the
prompt deterministically — the subagent gets annotations only, never
diffs, so the audit stays cheap.

When the subagent returns:

1. Append its report to `.trail/NEXT.md` under `## Audit findings`,
   prefixed with the date and the phase number at which the audit ran.
2. Clear the audit-required flag:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/phase_check.py clear-audit-flags
   ```
3. `git add -f .trail/NEXT.md && git commit -m "chore(trail): audit after phase N"`.

If the audit recommends plan changes, surface them clearly and ask the user
whether to amend `.trail/plan.md` before the next phase starts.

### `resume` — continue from current state

1. Read `.trail/NEXT.md` and latest phase tag annotation.
2. Infer next sub-command: `phase N+1` if the latest phase is tagged and
   complete, `commit` if mid-phase work is pending, or `audit` if NEXT
   contains an audit-required flag reference.
3. Confirm with user before proceeding.

### `capsule [N]` — show a tag annotation

```bash
git show phase/<feature-slug>-${N:-$(latest)} --no-patch --format='%(contents)'
```

### `rollback <N>` — guided rollback

Walk the user through three options without doing any silently:

1. Branch from tag (safest): `git switch -c claude/<slug>-rework phase/<feature-slug>-N`
2. Revert range (preserves history with inverse commits)
3. Hard reset (destructive — confirm twice; never on shared branches)

Show the SHA of the target tag and the affected commit range before
recommending. Do not mutate without explicit user confirmation.

### `finalize` — prepare for merge

1. Verify all planned phases are tagged: compare `git tag -l 'phase/<slug>-*'`
   against `.trail/plan.md` phase count. Surface any gaps.
2. Verify no audit-required flags remain (run `pending_audit_flags` via
   the trace_status script).
3. Offer to copy `.trail/plan.md` and `.trail/NEXT.md` to
   `docs/trail/<feature-slug>/` (committed normally, no `-f` needed
   since they're outside `.trail/`). This preserves the trail for
   post-merge retrospective.
4. Generate a PR description from tag annotations:
   ```bash
   git tag -l 'phase/<slug>-*' --sort=taggerdate \
     --format='## %(refname:short) — %(contents:subject)%0a%(contents:body)%0a'
   ```
   Offer to write this to `/tmp/trail-pr-body.md` for the user to paste.
5. Suggest the merge command but don't run it.

## Failure modes

If a phase approach turns out wrong mid-implementation:
1. Don't tag.
2. Reset or revert the micro-commits.
3. Optionally tag the dead end as `phase/<feature-slug>-N-attempt-2` with
   `Status: failed` and `Why: <reason>` at the top of the capsule (see
   `references/templates.md`, Failed phase section).

If a tagged capsule is wrong: record the correction in the next phase's
`Plan amendment` or `Decisions`. Tags are immutable; never `git tag -f`
to overwrite shared phase tags.

## Post-compaction recovery

The chat transcript is not trusted. Source of truth, in order:

1. `git tag -l 'phase/*' --sort=-taggerdate`
2. `git show <latest-tag> --no-patch --format='%(contents)'`
3. `.trail/NEXT.md`
4. `.trail/plan.md`

`/ts` shows all four in one invocation. If state looks inconsistent,
trust the tags first and NEXT.md second.

## References

- `references/workflow.md` — full discipline guide, risk semantics, audit cadence
- `references/templates.md` — canonical formats for plan, capsule, NEXT.md
- `references/recovery.md` — rollback recipes, failed-phase handling, recovery from corrupted state

Resolve paths via `${CLAUDE_SKILL_DIR}/references/<file>` when you need
to Read them directly.

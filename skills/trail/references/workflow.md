# Trail workflow

The full discipline guide. The skill body summarizes; this file is the
authority. Read here when a sub-command isn't behaving the way the SKILL.md
description suggested, or when designing a new phase.

## Mental model

Trail leaves the repo with a durable, structured trail of decisions and
phase boundaries so any future session, agent, or teammate can rejoin
without re-deriving why things are the way they are. Compaction efficiency
is a side effect; durability across sessions and across context losses is
the goal.

The durable trail lives in **git tags + their annotations**. The live
handoff lives in `.trail/NEXT.md`. The chat transcript is not trusted for
anything.

## When to use

Use Trail for: large features, risky refactors, architecture changes,
multi-module changes, work that may exceed context, any change you'd want
to bisect cleanly later.

Skip Trail for: typo fixes, one-line patches, isolated bug fixes with a
single commit. The branch-discipline and dirty-worktree checks below
still apply to small work; the full phase ritual does not.

## Repository inspection (before planning)

- `git status --short --branch`
- `git log --oneline -n 10`
- existing architecture docs: `docs/`, `README.md`, `ARCHITECTURE.md`, `adr/`
- CLAUDE.md and project manifests for test/build/lint commands
- module ownership boundaries

If the worktree is dirty, identify which changes existed before Trail
started. Never stage or revert unrelated user changes without explicit
permission.

## Branch discipline

Do not implement large work directly on `main`, `master`, `trunk`,
`develop`, release branches, or anything that looks protected.

Use `claude/<feature-slug>`. Confirm with the user before creating the
branch. If the user refuses branch creation, proceed only after they
acknowledge the traceability risk.

## Phase mechanics: micro-commits + tags

During a phase, commit freely. Micro-commits are the bisect targets and
the safety net against mid-phase work loss. Messages should be meaningful
("add export request type", "fix off-by-one in serializer") but they do
not need to follow the capsule format.

At phase end:

1. Run validation. Capture exact output.
2. Compose the capsule body per `templates.md`. **Write it to
   `/tmp/trail-capsule.txt`** — the file path matters because `-F` reads
   from a file, not from a `-m` argument.
3. Update `.trail/NEXT.md` with one-screen handoff for phase N+1.
4. Create the phase tag:

   ```bash
   git tag -a phase/<feature-slug>-N -F /tmp/trail-capsule.txt HEAD
   ```

   The tag points at the latest micro-commit. No empty boundary commit.

   **Use `-F` for multi-line capsules, not `-m "$(cat ...)"`** — the
   guard-tag hook reads the shell command before it runs, so command
   substitution arrives as literal text and the hook can't validate the
   real body. `-F` lets the hook read the file directly.

5. Commit the updated NEXT.md (force-add because `.trail/` is gitignored):

   ```bash
   git add -f .trail/NEXT.md
   git commit -m "chore(trail): phase N capsule + NEXT update"
   ```

6. If the `guard-tag` hook is installed, it blocks tag creation when the
   capsule is incomplete for the phase's declared risk level, when the
   tag name is wrong, when NEXT.md doesn't reference the next phase, or
   when a prior phase has a pending audit-required flag. Fix and retry.

## Why `.trail/` is gitignored and how `-f` works

`.trail/` is in the repo's `.gitignore` so plan/NEXT files do not merge
to main. But they DO need to survive across sessions on the feature
branch — otherwise context loss destroys the trail. Resolution: use
`git add -f` to force-track `.trail/plan.md` and `.trail/NEXT.md` on
the feature branch. Once `git add -f` has added a file, subsequent
`git add` on the same path works without `-f` (until the file is
removed from the index).

On merge to main, `.trail/` is still gitignored, so the merge does not
re-introduce the files. Phase tags travel with the commits — the durable
trail is preserved without `.trail/` clutter on main.

If you want plan/NEXT preserved for retrospective, `/trail finalize`
copies them to `docs/trail/<feature-slug>/`, which is outside `.trail/`
and merges normally.

## Capsule discipline

The capsule lives in the tag annotation and is **immutable** once tagged.
This is by design: post-hoc rewriting of phase history destroys the trail.

If you later realize a capsule is wrong, record the correction in the
*next* phase's capsule under `Plan amendment` or `Decisions`. Never
`git tag -f` to overwrite a phase tag in shared branches.

Required sections (see `templates.md` for exact format):

- Implementation — factually what was built
- Decisions — durable choices and reasons
- Rejected — approaches considered and discarded
- Validation — exact commands and results
- Risks / follow-ups — what's left open
- Plan amendment — remaining plan still right? one line answer required
- Next — one-line handoff

For medium and high risk phases, also required:

- Mental model — 2-3 lines on internalized structure
- Investigated and parked — libraries/approaches considered with outcomes

The Mental Model and Investigated-and-Parked sections are the highest-value
parts of the capsule for the next phase. Don't skip them by writing
trivia — the next phase (or the next teammate) is the audience.

## Risk classification

Classify each phase at plan time. Re-classify at phase start using
`phase_check.py classify-risk <files>`. **Re-classification is
upgrade-only** — if signals say a phase is now higher risk than planned,
upgrade and tell the user. Never silently downgrade.

| Risk | Architecture update | `/review` | `/security-review` | M+ sections |
|---|---|---|---|---|
| low | optional | optional | no | optional |
| medium | required if structure changed | recommended | no | required |
| high | required | required before tag | required if touches auth/secrets/deps | required |

Signals that bump to high regardless of plan:

- path matches `auth|secret|credential|migration|schema|crypto`
- path under `migrations/`, `db/`, `schemas/`
- changes that cross trust boundaries

Signals that bump to medium:

- file touched by >=3 distinct authors in last 7 days (ownership churn)

## Plan amendment ritual

At every phase end (in the capsule):

1. Re-read `.trail/plan.md`.
2. List remaining phases.
3. For each, write a one-line justification of why scope/order/existence
   is still correct, OR propose a change.
4. If proposing change, the next phase cannot start until the user
   approves the amendment.

This forces evidence over rationalization. Optional power: run
`/trail audit` for an independent subagent review.

## /trail audit (mechanically enforced)

`/trail commit` writes `.trail/audit-required-N.flag` when:

- current phase number is divisible by 3, OR
- risk just upgraded (low->medium or medium->high)

The `guard-tag` hook checks for any `audit-required-*.flag` files before
allowing a new phase tag. If one exists, the next phase cannot be tagged
until `/trail audit` runs and clears the flag. **The audit cadence is
not optional** — it's a filesystem state check, not a prose reminder.

`/trail audit` does:

1. Build the audit prompt from plan + tag annotations:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/phase_check.py build-audit-prompt > /tmp/trail-audit-prompt.txt
   ```
2. Spawn a forked Plan subagent (Agent tool, `subagent_type=Plan`) with
   the prompt contents.
3. When the subagent returns, append its report to `.trail/NEXT.md`
   under `## Audit findings`.
4. Clear the flag:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/phase_check.py clear-audit-flags
   ```

The audit gets only tag annotations, not diffs — the annotations are
designed for this and keep the audit cheap. `build-audit-prompt`
constructs the prompt deterministically so Claude doesn't have to
assemble it manually.

To skip an audit despite the flag, delete `.trail/audit-required-N.flag`
manually. Document the skip in the next phase's `Plan amendment` line.

## Failed phase recording

If a phase approach turns out to be wrong:

1. Don't tag.
2. Reset or revert the micro-commits.
3. Write a capsule with `Status: failed` and `Why: <one line>`.
4. Tag as `phase/<feature-slug>-N-attempt-2` (or next K).
5. Plan attempt K+1 with the learnings.

Failed-attempt tags are kept permanently. `trace_status.py` shows only the
latest attempt of each phase number unless asked for full history. The
naming convention does the work — no separate "failed" registry.

## Post-compaction recovery

If you're reading this after compaction or in a fresh session, do not
trust the chat transcript. The source of truth is, in order:

1. `git tag -l 'phase/*' --sort=-taggerdate` — what was actually done
2. `git show phase/<latest>` — what was decided
3. `.trail/NEXT.md` — where to resume
4. `.trail/plan.md` — original intent

`/ts` shows all four in one invocation. `/trail resume` interprets them
and proposes the next action.

If `.trail/NEXT.md` is missing (e.g., switched branches), the latest tag's
`Next:` line is the fallback handoff. If both are missing, the phase
number is `max(phase/* tags) + 1` and you re-plan.

## Compaction hygiene during a phase

Mid-phase compaction loses exploration context. Two practices reduce
damage:

1. **Update `.trail/NEXT.md` mid-phase** when you hit a checkpoint
   ("halfway, decided X, next sub-task is Y"). The file is editable for
   exactly this reason.
2. **Make a micro-commit at every sub-task boundary** even if incomplete.
   `wip: serializer half done` is fine. Commits are durable; in-memory
   reasoning is not.

## Branch merge

When the feature branch merges to main:

- Phase tags travel with the commits — preserved.
- `.trail/` is in `.gitignore` on main, so `.trail/NEXT.md` and
  `.trail/plan.md` do not merge back.
- Architecture doc updates that were made during phases do merge — they're
  not under `.trail/`.

If you want plan + NEXT to survive merge for retrospective purposes,
manually copy them to `docs/trail/<feature-slug>/` and commit before merge.
This is opt-in; the default is feature-branch-only.

## What Trail does not do

- Run validation for you. Validation commands come from the plan; the
  human or Claude runs them and pastes results into the capsule.
- Enforce honesty. `guard-tag` checks structure, not truth. For
  high-stakes work, configure CI to re-run validation against each
  phase tag.
- Replace code review. `/review` and `/security-review` integrate but
  Trail does not gate on their results — that's the user's call.
- Work without git. Tags are the spine; non-git VCS is out of scope.

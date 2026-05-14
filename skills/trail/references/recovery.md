# Trail recovery recipes

When something goes sideways, look here. Each recipe assumes you're on the
feature branch unless noted.

## Resume after compaction (same session)

Symptom: context was just summarized; you're not sure what state Trail is in.

```
/ts
```

Read the output. The Phase tags section + latest capsule + NEXT.md tell
you everything Trail knows. If the next action is obvious, proceed.
Otherwise:

```
/trail resume
```

## Resume in a new session

Symptom: fresh `claude` invocation; you want to continue an in-flight feature.

1. Make sure you're on the feature branch:
   ```bash
   git branch --show-current   # should print claude/<feature-slug>
   ```
2. `/ts` to see state.
3. `/trail resume` to continue.

If `.trail/NEXT.md` is missing because the branch was cloned fresh and the
`.trail/` directory wasn't pushed (it's gitignored), reconstruct from the
latest tag's `Next:` line:

```bash
git show phase/<feature-slug>-N --no-patch --format='%(contents)' | grep -A1 '^Next:'
```

## Rollback to a phase tag

Three operations, in increasing safety:

### Soft: branch from the phase tag

Preserves everything; lets you experiment from a known-good point.

```bash
git switch -c claude/<feature-slug>-rework phase/<feature-slug>-N
```

Original branch untouched.

### Medium: revert intervening commits

Preserves history; adds inverse commits.

```bash
git revert --no-commit phase/<feature-slug>-N..HEAD
git commit -m "revert: roll back to phase N for <reason>"
```

Phase tags after N are still in the repo; the working state matches phase N.

### Hard: reset to phase tag

Destructive. Loses every commit (and every phase tag) after N. Confirm
before doing this. Never do this on a shared branch.

```bash
git reset --hard phase/<feature-slug>-N
# Delete now-orphaned later phase tags if you don't want them around:
git tag -d phase/<feature-slug>-{N+1} phase/<feature-slug>-{N+2} ...
```

`/trail rollback <N>` walks through these choices interactively rather
than picking one. Use the slash command unless you're sure which you want.

## Record a failed phase

You started phase 3, made it 80% of the way, then discovered the approach
was wrong.

1. Don't tag the work-in-progress.
2. Decide: keep the micro-commits as history of the failed attempt, or
   reset them away?

### Keep them as history

```bash
# Write capsule with Status: failed, Why: <one line>, and what you tried.
git tag -a phase/<feature-slug>-3-attempt-2 -F /tmp/failed-capsule.txt HEAD
# Now reset to the previous phase tag and re-plan:
git reset --hard phase/<feature-slug>-2
```

The failed-attempt tag is preserved. Next successful attempt at phase 3
is tagged `phase/<feature-slug>-3` (or `phase/<feature-slug>-3-attempt-3`
if you want explicit lineage).

### Discard them

```bash
git reset --hard phase/<feature-slug>-2
# Capsule lives only in NEXT.md notes: "phase 3 attempt 1 failed; tried X; try Y next"
```

Trade-off: cleaner history, but the next attempt doesn't have a permanent
record of what was tried.

## Recover when NEXT.md is missing

Switched branches, fresh clone, or accidentally deleted:

- The latest phase tag's `Next:` line is the authoritative fallback.
- The plan (`.trail/plan.md`) is gone too unless you re-create it; you
  can reconstruct it from the phase tags if you have them.

```bash
# Reconstruct a minimal NEXT.md from the latest tag:
LATEST=$(git tag -l 'phase/*' --sort=-taggerdate --format='%(refname:short)' | head -1)
mkdir -p .trail
{
  echo "# NEXT — recovered from $LATEST"
  echo ""
  echo "Latest tag: $LATEST"
  echo ""
  echo "## What's next (from tag annotation)"
  git show "$LATEST" --no-patch --format='%(contents)' | sed -n '/^Next:/,/^$/p'
} > .trail/NEXT.md
git add -f .trail/NEXT.md
git commit -m "chore(trail): recover NEXT.md from latest tag"
```

The `-f` is required because `.trail/` is gitignored — see
`workflow.md` for the rationale.

## Audit says the plan is wrong

`/trail audit` returned a report saying remaining phases need restructuring.

1. Read the audit report (appended to `.trail/NEXT.md` under `## Audit findings`).
2. Update `.trail/plan.md` with the new phase structure.
3. Commit the plan change as a single commit: `chore(trail): amend plan after phase N audit`.
4. Note the amendment in the next phase's capsule under `Plan amendment`.

The original plan is preserved in git history. The amended plan is what
subsequent phases follow.

## guard-tag is blocking and you think it's wrong

The hook is conservative. The block reasons, with fixes:

- **"capsule missing required sections for risk=X"** — write the missing
  sections. If risk is wrong, add a literal `Risk: low` line (case
  insensitive) to drop the M+ section requirements.
- **"-m argument contains unevaluated shell substitution syntax"** —
  you used `git tag -m "$(cat ...)"`. Switch to `git tag -F /path/to/file`.
  The hook reads the shell command before it runs, so `$()` and backticks
  arrive as literal text.
- **"phase tag created without -m or -F"** — provide the capsule via
  `-F /tmp/trail-capsule.txt`.
- **"tag '...' does not match phase/<feature-slug>-N"** — use lowercase
  slug + integer phase number, e.g. `phase/add-export-1`.
- **".trail/NEXT.md does not reference phase N+1"** — update NEXT.md
  with the next phase number before tagging.
- **"audit required from phase(s) N before tagging the next phase"** —
  run `/trail audit`, which clears the flag after writing findings. To
  intentionally skip, delete `.trail/audit-required-N.flag` and document
  the skip in the next capsule's `Plan amendment`.

To debug a hook that seems silent when it shouldn't be, set
`TRAIL_HOOK_DEBUG=1` in your environment and re-run; the script will
print the raw payload to stderr.

To debug interactively:
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"git tag -a phase/foo-1 -F /tmp/x"}}' \
  | python3 $HOME/.claude/skills/trail/scripts/phase_check.py guard-tag
```

Escape hatch: disable the hook in `~/.claude/settings.json` temporarily;
do not edit history of already-tagged phases.

## Context says one thing, repo says another

When the chat transcript and the repo disagree, the repo wins. Always.
The capsule + tag annotation + NEXT.md are designed to survive context
loss precisely so a confused transcript can't corrupt the record.

If Claude says "I just completed phase 4" but `git tag -l 'phase/*'`
shows only up to phase 3, no tag was created. Phase 4 is not complete.

## Diverged from the plan and don't realize until phase 5

`/trail audit` exists to catch this earlier, but if you're here:

1. `/trail audit` now, even if not at the automatic cadence.
2. Read the report.
3. Decide: amend plan, rollback to last known-good phase, or accept
   divergence and document it.
4. The decision lives in the next phase's `Plan amendment` section.

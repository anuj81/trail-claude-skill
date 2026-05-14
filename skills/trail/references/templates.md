# Trail templates

Canonical formats Trail uses. The skill body refers back here; keep edits
backward-compatible. `phase_check.py` enforces capsule structure literally
against the section headers below — if you rename a section, update the
script too.

## Trace plan

Produced by `/trail plan`, approved via plan mode, then committed as
`.trail/plan.md` on the feature branch.

```markdown
# Trace plan: <feature>

Branch: `claude/<feature-slug>`
Tag namespace: `phase/<feature-slug>-N`
NEXT pointer: `.trail/NEXT.md`
Validation: <commands or manual checks>

| Phase | Goal | Risk | Tasks | Validation | Docs |
| --- | --- | --- | --- | --- | --- |
| 1 | <goal> | low\|medium\|high | <task summary> | <check> | <doc update> |
| 2 | <goal> | low\|medium\|high | <task summary> | <check> | <doc update> |

## Risk rationale

- Phase 1 is <risk> because <signal: e.g. touches schema, isolated refactor, etc.>
- Phase 2 is <risk> because <signal>

## Notes

- Compaction strategy: phase tag annotations are the durable trail; .trail/NEXT.md is the live handoff
- /trail audit will run automatically after phases 3, 6, 9, ... and on any risk upgrade
```

## Capsule (tag annotation)

Written to the phase tag at phase end. Compose the capsule body, write
it to `/tmp/trail-capsule.txt` with the Write tool, then tag with `-F`:

```bash
git tag -a phase/<feature-slug>-N -F /tmp/trail-capsule.txt HEAD
```

`-F` is required (not `-m "$(cat ...)"`): the guard-tag hook reads the
shell command before substitution runs.

**Immutable once tagged.** If you later realize a capsule is wrong, record
the correction in the *next* phase's capsule under `Plan amendment` or
`Decisions`. Do not rewrite history.

Sections marked **(M+)** are required for medium and high risk phases.
Other sections are always required. `phase_check.py guard-tag` enforces
this; opt out per-phase by including a `Risk: low` line.

```text
phase N: <slug>

Risk: <low|medium|high>

Implementation:
  <2-3 lines: what this phase actually built, factually. No marketing.>

Decisions:
  - <durable choice>: <reason>

Rejected:
  - <approach>: <why not>

Validation:
  - <exact command>: <result, including last few lines of output if useful>

Mental model: (M+)
  <2-3 lines describing the structure you internalized — call graph, data
  flow, key invariants. Next phase should not have to re-derive this.>

Investigated and parked: (M+)
  - <option/library/approach>: <one-line outcome — saves next phase from
    redoing this investigation>

Risks / follow-ups:
  - <item or "none">

Plan amendment:
  <one line: remaining phases still right given what we learned? If yes,
  say so explicitly. If not, propose change.>

Next:
  <one-line handoff to next phase>
```

## NEXT.md

`.trail/NEXT.md` is the live handoff file on the feature branch. Overwritten
each phase end. **Editable mid-phase** to leave interim notes for a future
session — that mid-phase capability is its main reason for existing as a
real file instead of being derived from tags.

`.trail/` is gitignored repo-wide; on the feature branch the file is
force-added with `git add -f .trail/NEXT.md` so it survives across
sessions. On merge to main, the gitignore prevents it from following.
See `workflow.md` for the rationale.

```markdown
# NEXT — <feature>

Branch: `claude/<feature-slug>`
Latest tag: `phase/<feature-slug>-N`
Next phase: phase/<feature-slug>-<N+1> — <title>

## What's next

<one screen of guidance: what to do first, where to look, what to confirm
before starting the next phase>

## In-flight notes

Edit mid-phase to leave a marker for your next session. Examples:

- 2026-05-14: halfway through phase 2; struggling with auth middleware
  ordering; try express-session before passport.initialize next
- 2026-05-15: blocked on schema decision; need product input on whether
  exports should be per-project or per-org

## Audit findings

(Populated by `/trail audit` when it runs. Each entry includes phase number
of the audit and the subagent's verdict.)
```

## Failed phase

Failed attempts are kept as permanent history. Tag as
`phase/<feature-slug>-N-attempt-K` where K starts at 2 (the original attempt
without a suffix is implicitly attempt 1).

Capsule body adds two lines at the top:

```text
phase N: <slug> (attempt K)

Status: failed
Why: <one-line reason>

Risk: <level>

Implementation:
  <what was attempted>

Decisions:
  ...
```

Rest of capsule documents what was tried so attempt K+1 doesn't repeat the
same mistake. The next successful attempt gets a new tag without `-attempt-K`
(or with `-attempt-K+1` if you want to preserve the lineage).

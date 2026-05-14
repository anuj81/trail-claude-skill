# Sample session: full /trail walkthrough

A condensed transcript showing what a Trail-managed feature looks like
from `/trail plan` through phase commits. Annotations in `>` lines.

---

**User:** I want to add a project export feature. Use trail.

**Claude (auto-loads /trail because of "use trail"):**

> Pulls live context: git status (clean, on main), git log, no phase tags,
> no .trail/ directory.

Entering plan mode to draft the trace plan.

[EnterPlanMode]

Inspecting the repo:
- `package.json` shows test = `npm test`, build = `npm run build`
- `docs/architecture.md` exists with an "API surface" section
- `CLAUDE.md` notes: "no new permissions without product sign-off"

Proposed feature-slug: `add-export`. Branch: `claude/add-export`.
Tag namespace: `phase/add-export-N`. Three phases (domain, API, UI).

[Writes plan — see examples/sample-trace-plan.md]

[ExitPlanMode — requests user approval]

**User:** approved.

**Claude:**

Creating the branch. Confirm: `git switch -c claude/add-export` from main?

**User:** yes.

> Branch created. .trail/plan.md written. Single scaffolding commit.

```
$ git switch -c claude/add-export
$ mkdir -p .trail
$ # [Write tool writes .trail/plan.md from the approved plan]
$ git add -f .trail/plan.md      # -f because .trail/ is gitignored
$ git commit -m "chore(trail): scaffold trace plan"
```

Phase 1 ready to start. Type `/trail phase 1`.

---

**User:** /trail phase 1

**Claude:**

Phase 1: add export domain model + serializer.

> Reads .trail/plan.md, classifies risk:

```
$ python3 ~/.claude/skills/trail/scripts/phase_check.py classify-risk \
    src/domain/export/serializer.ts src/domain/export/types.ts
low
```

Risk classification matches plan (low). Creating tasks:

[TaskCreate]
- Add ExportRequest type in src/domain/export/types.ts
- Add serializeExport function in src/domain/export/serializer.ts
- Add 4 focused tests covering empty/single/multi/unicode cases

Implementing...

> Several micro-commits during the phase:

```
$ git commit -m "add ExportRequest type"
$ git commit -m "add serializeExport with project + tasks"
$ git commit -m "add unicode test case"
$ git commit -m "fix off-by-one in nested task serialization"
```

> Each commit is a bisect target. None require capsule format.

Phase 1 implementation done. Type `/trail commit` to close it out.

---

**User:** /trail commit

**Claude:**

Running validation:

```
$ npm test -- export
PASS  src/domain/export/__tests__/serializer.test.ts
  4 passed, 0 failed (0.42s)
```

Composing capsule. Risk is low so M+ sections (Mental model,
Investigated and parked) are optional but I'll include them anyway since
phase 2 will benefit.

[Shows capsule body — see examples/sample-capsule.txt]

Updating .trail/NEXT.md:

[Shows NEXT.md — see examples/sample-NEXT.md]

Confirm capsule + NEXT update, then I'll tag `phase/add-export-1`?

**User:** confirmed.

**Claude:**

```
$ # [Write tool writes capsule body to /tmp/trail-capsule.txt — pre-approved]
$ git tag -a phase/add-export-1 -F /tmp/trail-capsule.txt HEAD
$ git add -f .trail/NEXT.md
$ git commit -m "chore(trail): phase 1 capsule + NEXT update"
```

> Note: `-F /path/to/file` is the right way to pass multi-line capsules.
> Don't use `-m "$(cat /tmp/capsule.txt)"` — the guard-tag hook reads the
> shell command before substitution runs, so it would see literal $(...)
> and reject the tag.

> guard-tag hook fires on the tag command:
>   - Tag name matches phase/<slug>-N: ok
>   - -F file readable; capsule body has all required base sections: ok
>   - Risk: low present, so M+ sections not enforced
>   - NEXT.md references "phase/add-export-2": ok
>   - No pending audit-required flags: ok
> Tag created.

```
$ git show phase/add-export-1 --no-patch
tag phase/add-export-1
Tagger: ...
phase 1: add-export
[full capsule body]
```

Phase 1 closed. Phase number 1 not divisible by 3, risk didn't upgrade,
so no audit-required flag is written.

Next: `/trail phase 2` (high risk, will require /review and
/security-review before tag).

---

**User:** (next day, new session)
/ts

**Claude (auto-loads /ts):**

> Pure dynamic injection — no scripts, instant.

```
## Branch + worktree
## claude/add-export

## Phase tags
phase/add-export-1  phase 1: add-export

## Latest capsule
=== phase/add-export-1 ===
[full capsule]

## NEXT.md
[NEXT.md content]

## Plan (first 40 lines)
[plan]
```

You're on `claude/add-export`. Phase 1 is tagged; phase 2 is next (API
endpoint with auth, high risk). NEXT.md says start by reading
`src/api/middleware/rbac.ts`. Type `/trail phase 2` to begin.

---

**User:** /trail phase 2

> Implementation continues with high-risk discipline: TaskCreate,
> micro-commits, /review before tag, /security-review because phase touches
> auth. Tag created with full M+ capsule. Phase 2 risk is high, so
> auto-audit doesn't fire here (audits fire at phase 3 by cadence anyway).

---

**User:** /trail phase 3 ... /trail commit

> Phase 3 closes. N = 3, so /trail commit writes
> `.trail/audit-required-3.flag`. If the user tried `/trail phase 4` and
> attempted to tag without auditing, the guard-tag hook would block.

**Claude:**

Phase 3 tagged. `audit-required-3.flag` written. Run `/trail audit` next
— the next phase tag is blocked until the audit completes.

---

**User:** /trail audit

**Claude:**

```
$ python3 ~/.claude/skills/trail/scripts/phase_check.py build-audit-prompt \
    > /tmp/trail-audit-prompt.txt
```

[Agent tool with subagent_type=Plan, prompt loaded from /tmp/trail-audit-prompt.txt]

Audit report (from subagent):

> "Plan is being followed faithfully. One observation: phase 3's UI tests
> assume the API returns 403 (not 401) on RBAC denial, which matches
> phase 2's implementation. No remaining phases to amend (this was the
> final phase). Ready for merge review."

Appending to .trail/NEXT.md under "## Audit findings" and clearing the
audit flag.

```
$ # [Write tool appends to .trail/NEXT.md]
$ git add -f .trail/NEXT.md
$ git commit -m "chore(trail): audit after phase 3"
$ python3 ~/.claude/skills/trail/scripts/phase_check.py clear-audit-flags
1
```

---

**User:** /trail finalize

**Claude:**

All 3 planned phases tagged: phase/add-export-{1,2,3}. No pending audit
flags. Plan is satisfied.

Generating PR description from tag annotations:

```
$ git tag -l 'phase/add-export-*' --sort=taggerdate \
    --format='## %(refname:short) — %(contents:subject)%0a%(contents:body)%0a' \
    > /tmp/trail-pr-body.md
```

Copy `/tmp/trail-pr-body.md` into your PR description. Also offering to
preserve plan + NEXT for retrospective:

> Copy .trail/plan.md and .trail/NEXT.md to docs/trail/add-export/ ?
> (These would be committed normally since docs/ is not gitignored.)

**User:** yes

**Claude:**

```
$ mkdir -p docs/trail/add-export
$ cp .trail/plan.md .trail/NEXT.md docs/trail/add-export/
$ git add docs/trail/add-export/
$ git commit -m "docs(trail): preserve add-export trace"
```

Ready to merge `claude/add-export` to `main`. Suggest:
```
$ git switch main
$ git merge --no-ff claude/add-export
```

`.trail/` is gitignored so plan + NEXT don't follow. Phase tags travel
with the commits. docs/trail/add-export/ preserves the trail in main.

---

End of session.

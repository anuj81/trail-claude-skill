# Trail install testing checklist

Run these in order after installing:

```
cp -R skills/trail ~/.claude/skills/
cp -R skills/ts ~/.claude/skills/
```

Record findings in the **Result** lines so the outcomes are preserved for future contributors.

---

## 0. Prerequisites

- [ ] Skills copied to `~/.claude/skills/trail/` and `~/.claude/skills/ts/`
- [ ] Hook merged into `~/.claude/settings.json` (see `hooks/README.md`)
- [ ] Test repo ready: a git repo with at least one commit

---

## 1. Hook payload schema (highest priority)

**Why:** If the hook reads the wrong key, it silently passes every `git tag` command — the entire enforcement mechanism fails.

**Steps:**
1. In a terminal, set `TRAIL_HOOK_DEBUG=1`
2. Start a Claude session in the test repo
3. Run any `git tag` command through Claude (doesn't need to be a phase tag): `git tag test-probe HEAD`
4. Check stderr for the raw JSON payload the hook received

- [x] Hook fires and logs a payload to stderr
- [x] Hook correctly blocks bad tag names (exit 2 = hard block confirmed 2026-05-13)
- [ ] Identify the key used for the command string: `tool_input` / `input` / `parameters`
- [ ] Identify the key used for the tool name: `tool_name` / `tool` / `name`

**Result:**
```
command key: _______________
tool name key: _______________
actual payload (paste excerpt): _______________
```

**Confirmed finding (2026-05-13):** Claude Code exit codes — exit 1 = non-blocking warning (Claude proceeds anyway), exit 2 = blocking (tool call is prevented). The script was updated to return 2 on all block conditions.

**Follow-up:** If the real keys differ from what `phase_check.py` tries first, open an issue or update `_extract_payload_command()` to put the confirmed key first.

---

## 2. Dynamic injection (`!`cmd``)

**Why:** `/ts` and `/trail` both rely on shell commands being executed and their output injected into the skill context. If injection is broken, Claude sees raw backtick lines.

**Steps:**
1. Open a Claude session in the test repo (on any branch with at least one commit)
2. Type `/ts`
3. Observe whether the response contains live branch name, actual tag list, and real NEXT.md content

- [ ] Branch name shown correctly
- [ ] Phase tags section populated (or says "no phase tags yet" — not a raw command)
- [ ] NEXT.md section populated (or says "no .trail/NEXT.md" — not a raw command)
- [ ] Plan section populated (or says "no .trail/plan.md" — not a raw command)

**Confirmed finding (2026-05-13):** `!`cmd`` blocks cannot contain ANY shell variable expansion. Both `${VAR}` (complex) and `$VAR` (simple_expansion) are rejected. This includes `$HOME`, `$CLAUDE_SKILL_DIR`, `$LATEST`, etc. Rules for `!`cmd`` blocks: use only literal arguments, no variable references, no command substitution, no conditionals. Pipelines (`|`) and `||`/`&&` are allowed.

**Result:**
```
Injection works: yes — confirmed 2026-05-13
Notes: git for-each-ref --count=1 works for latest capsule; $HOME path works for scripts
```

---

## 3. `paths:` frontmatter auto-load

**Why:** `paths: [.trail/**]` in `skills/trail/SKILL.md` is intended to make `/trail` auto-suggest when `.trail/` files are present. Behavior is undocumented — may auto-invoke, may just surface as a suggestion, or may do nothing.

**Steps:**
1. Create a test repo with a `.trail/plan.md` file
2. Start a fresh Claude session in that repo
3. Type a natural-language prompt without `/trail` — e.g. "what's the current phase?" or "let's continue the work"
4. Observe whether Claude loads the trail skill automatically

- [x] Skill auto-loaded (full invocation without explicit `/trail`)
- [ ] Skill suggested but not auto-loaded
- [ ] No effect — `paths:` appears to be metadata only

**Result:**
```
Observed behavior: confirmed 2026-05-13 — with .trail/plan.md present, asking "what's the plan
here?" caused Claude to proactively call Skill(ts) without explicit invocation. Claude chose
/ts (status) over /trail (implementation), which is correct for a status question.
NOTE: paths: and effort: were later found to cause /trail to fail to load entirely — both
removed from SKILL.md on 2026-05-13. Auto-load of /ts was driven by Claude inference, not paths:.
```

---

## 4. `effort: high` behavior

**Confirmed finding (2026-05-13):** Both `effort: high` and `paths:` are non-standard SKILL.md
fields that cause Claude Code to reject the skill (it won't appear in the skill list at all).
Both have been removed from `skills/trail/SKILL.md`.

- [ ] Visible cost/effort warning shown before `/trail` executes
- [x] No difference observed — `effort:` and `paths:` are not valid SKILL.md fields; removed.

**Result:**
```
Observed behavior: skill failed to load entirely when either field was present.
Removed both fields. /trail loads correctly without them.
```

---

## 5. End-to-end smoke test

Run the condensed flow from `examples/sample-session.md`:

- [ ] `/trail plan` — enters plan mode, writes `.trail/plan.md`, scaffolding commit succeeds
- [ ] `/trail phase 1` — implements phase, micro-commits land on branch
- [ ] `/trail commit` — capsule written to `/tmp/trail-capsule.txt`, tag created with `-F` (not `-m`), guard-tag hook passes
- [ ] `/ts` — shows correct phase tag, latest capsule annotation, NEXT.md content
- [ ] guard-tag blocks a bad tag name (test: `git tag phase/BADNAME HEAD`)
- [ ] guard-tag blocks a tag with incomplete capsule
- [ ] Phase 3 commit writes `audit-required-3.flag`
- [ ] `/trail audit` clears the flag
- [ ] `/trail finalize` generates PR body from tag annotations

**Result:**
```
Steps completed: ___/9
Failures: _______________
```

---

## Summary

| # | Assumption | Status |
|---|-----------|--------|
| 1 | Hook payload schema | ✅ confirmed — exit 2 blocks, exit 1 warns only |
| 2 | Dynamic injection | ✅ confirmed — works; no `$VAR` in `!`cmd`` blocks |
| 3 | `paths:` auto-load | ✅ confirmed — but field causes skill to fail to load; removed |
| 4 | `effort: high` | ✅ confirmed — invalid field; causes skill to fail to load; removed |
| 5 | End-to-end smoke | pending |

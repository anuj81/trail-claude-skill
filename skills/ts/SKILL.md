---
name: ts
description: Show Trail status — phase tags, latest capsule, NEXT.md, branch state. Read-only, instant. Companion to /trail. Use whenever the user asks "where am I", "what's next", "what's the latest phase", "show trail status".
when_to_use: |
  Trigger on "ts", "trail status", "where am I", "what phase", "latest
  capsule", "what's next", "show trail". Use frequently — it has no side
  effects.
allowed-tools: Bash(git status *) Bash(git tag -l*) Bash(git tag -n*) Bash(git show *) Bash(git for-each-ref *) Bash(cat *) Bash(git branch --show-current)
---

# Trail status

## Branch + worktree

!`git status --short --branch 2>/dev/null || echo '(not a git repo)'`

## Phase tags

!`git tag -l 'phase/*' --sort=-version:refname --format='%(refname:short)  %(contents:subject)' 2>/dev/null | head -20 || echo '(no phase tags yet)'`

## Latest capsule

!`LATEST=$(git tag -l 'phase/*' --sort=-version:refname --format='%(refname:short)' 2>/dev/null | head -1); if [ -n "$LATEST" ]; then echo "=== $LATEST ==="; git for-each-ref "refs/tags/$LATEST" --format='%(contents)'; else echo '(no phase tags yet)'; fi`

## NEXT.md

!`cat .trail/NEXT.md 2>/dev/null || echo '(no .trail/NEXT.md on this branch)'`

## Plan (first 40 lines)

!`head -40 .trail/plan.md 2>/dev/null || echo '(no .trail/plan.md)'`

## What to do

Summarize the state above in 3-5 lines: which phase is in flight, what
the next action is, anything that looks inconsistent (e.g., NEXT.md
references a phase that's not yet tagged, or vice versa). If the user
should run `/trail resume`, `/trail commit`, or `/trail phase <N>`, say
which and why.

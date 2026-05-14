# Trail hooks

`settings.snippet.json` contains the hooks block to merge into `~/.claude/settings.json`.

## What each hook does

**PreToolUse `guard-tag`** — fires on every `Bash` tool call. Silently passes unless the command is `git tag phase/*`, in which case it validates:
- Tag name follows `phase/<feature-slug>-N` (or `-attempt-K` suffix)
- Capsule annotation contains all required sections for the phase's risk level
- No prior-phase audit is still pending
- `-m "$(cat ...)"` anti-pattern is rejected (use `-F /path/to/file` instead)

**Stop `trace_status`** — prints current Trail state at session end. Self-suppresses on non-Trail repos, so non-Trail sessions stay quiet.

## Install

Merge the `hooks` key from `settings.snippet.json` into your `~/.claude/settings.json`. If you already have a `hooks` block, append Trail's entries to the existing arrays.

## Notes

- Paths use `$HOME` (not `~`) for portability. If your hook runner doesn't expand `$HOME`, replace it with the absolute path to your home directory.
- Set `TRAIL_HOOK_DEBUG=1` in your environment to log raw hook payloads to stderr — useful if the hook seems silent when it shouldn't be.
- These hooks are functionally equivalent to `allowed-tools` from a trust perspective: they execute on every matching tool call. Review `~/.claude/skills/trail/scripts/phase_check.py` before installing.

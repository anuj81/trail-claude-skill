#!/usr/bin/env python3
"""Phase check helpers for the Trail skill.

Sub-commands:
  guard-tag             Hook entry: validate a `git tag` invocation before it
                        runs. Reads Claude Code hook JSON payload on stdin.
  classify-risk PATHS   Estimate risk (low|medium|high) for the given files.
  validate-capsule      Read tag annotation body from stdin; verify required
                        sections are present for the declared risk level.
  enforce-namespace TAG Verify TAG follows phase/<feature-slug>-N[-attempt-K].
  mark-audit-required N Create .trail/audit-required-N.flag so the next phase
                        tag is blocked until /trail audit runs.
  clear-audit-flags     Remove .trail/audit-required-*.flag (call from
                        /trail audit after writing findings).
  build-audit-prompt    Emit the audit prompt (plan + tag annotations) on
                        stdout, ready to feed to a forked Plan subagent.

guard-tag is silent for any tool call that is not a phase tag creation.
Exits 2 with a stderr message if the tag should be blocked (exit 2 = blocking
in Claude Code hooks; exit 1 = non-blocking warning that Claude ignores).

Debug: set TRAIL_HOOK_DEBUG=1 to print the raw hook payload to stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


# Non-greedy slug + trailing -N, with optional attempt suffix.
PHASE_TAG_RE = re.compile(
    r"^phase/(?P<slug>[a-z0-9][a-z0-9-]*?)-(?P<n>\d+)(?:-attempt-(?P<k>\d+))?$"
)

REQUIRED_SECTIONS_BASE = (
    "Implementation:",
    "Decisions:",
    "Rejected:",
    "Validation:",
    "Risks / follow-ups:",
    "Plan amendment:",
    "Next:",
)
REQUIRED_SECTIONS_M_PLUS = (
    "Mental model:",
    "Investigated and parked:",
)


def find_repo_root(start: Path | None = None) -> Path:
    """Return the git repo root, or `start` (default cwd) if not in a repo."""
    cwd = start if start is not None else Path(".")
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return cwd.resolve()


def classify_risk_files(paths: list[str], repo: Path | None = None) -> str:
    """Estimate risk using cheap signals. Upgrade-only by contract."""
    repo = repo or find_repo_root()
    high_patterns = re.compile(r"auth|secret|credential|migration|schema|crypto", re.I)
    high_dirs = ("migrations/", "db/", "schemas/")

    for raw in paths:
        p = raw.strip()
        if not p:
            continue
        if high_patterns.search(p):
            return "high"
        if any(seg in p for seg in high_dirs):
            return "high"

    risk = "low"
    for raw in paths:
        p = raw.strip()
        if not p:
            continue
        result = subprocess.run(
            ["git", "-C", str(repo), "log", "--since=7.days", "--format=%an", "--", p],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        if result.returncode == 0:
            authors = {ln for ln in result.stdout.splitlines() if ln}
            if len(authors) >= 3:
                risk = "medium"

    return risk


def validate_capsule_body(body: str, risk: str) -> list[str]:
    missing: list[str] = []
    for section in REQUIRED_SECTIONS_BASE:
        if section not in body:
            missing.append(section)
    if risk in ("medium", "high"):
        for section in REQUIRED_SECTIONS_M_PLUS:
            if section not in body:
                missing.append(section)
    return missing


def enforce_namespace(tag: str) -> str | None:
    if not tag.startswith("phase/"):
        return None  # Not a phase tag; not our concern.
    if not PHASE_TAG_RE.match(tag):
        return (
            f"Tag '{tag}' does not match phase/<feature-slug>-N[-attempt-K]. "
            "Use lowercase slug + integer phase number, e.g. phase/add-export-1."
        )
    return None


def parse_git_tag_command(command: str) -> tuple[str | None, str | None]:
    """Parse a shell command for `git tag [-a|-s] <name> [-m <msg>|-F <file>]`.

    Returns (tag_name, message_body) if a phase tag creation is detected,
    else (None, None). Conservative on parse failure (allows command).

    For multi-line capsules, callers MUST use `-F <path>`: the hook receives
    the unevaluated shell command, so `-m "$(cat ...)"` arrives as literal
    `$(cat ...)` text. With `-F`, the hook reads the file directly.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None, None

    tag_args: list[str] | None = None
    for i in range(len(tokens) - 1):
        if tokens[i] == "git" and tokens[i + 1] == "tag":
            tag_args = tokens[i + 2:]
            break
    if tag_args is None:
        return None, None

    tag_name: str | None = None
    message: str | None = None
    j = 0
    while j < len(tag_args):
        tok = tag_args[j]
        if tok in ("-a", "-s", "--annotate", "--sign", "-f", "--force"):
            j += 1
            continue
        if tok in ("-m", "--message"):
            if j + 1 < len(tag_args):
                message = tag_args[j + 1]
                j += 2
                continue
        if tok.startswith("-m") and len(tok) > 2:
            message = tok[2:]
            j += 1
            continue
        if tok.startswith("--message="):
            message = tok.split("=", 1)[1]
            j += 1
            continue
        if tok in ("-F", "--file"):
            if j + 1 < len(tag_args):
                message = _read_capsule_file(tag_args[j + 1])
                j += 2
                continue
        if tok.startswith("--file="):
            message = _read_capsule_file(tok.split("=", 1)[1])
            j += 1
            continue
        if tok in ("-l", "--list", "-n", "-d", "--delete", "-v", "--verify"):
            # Read-only or unrelated subcommands — not a creation; bail out.
            return None, None
        if tok.startswith("-"):
            j += 1
            continue
        if tag_name is None:
            tag_name = tok
        j += 1

    return tag_name, message


def _read_capsule_file(path: str) -> str | None:
    try:
        return Path(path).expanduser().read_text(errors="replace")
    except (OSError, ValueError):
        return None


def _extract_payload_command(payload: dict) -> tuple[str, str]:
    """Try common hook payload schemas. Returns (tool_name, command)."""
    tool_name = (
        payload.get("tool_name")
        or payload.get("tool")
        or payload.get("name")
        or ""
    )
    tool_input = (
        payload.get("tool_input")
        or payload.get("input")
        or payload.get("parameters")
        or {}
    )
    command = ""
    if isinstance(tool_input, dict):
        command = tool_input.get("command") or tool_input.get("cmd") or ""
    return tool_name, command


def pending_audit_flags(repo: Path) -> list[Path]:
    flag_dir = repo / ".trail"
    if not flag_dir.exists():
        return []
    return sorted(flag_dir.glob("audit-required-*.flag"))


def cmd_guard_tag() -> int:
    raw = sys.stdin.read()

    if os.environ.get("TRAIL_HOOK_DEBUG"):
        print(f"Trail guard-tag DEBUG: payload={raw!r}", file=sys.stderr)

    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0  # Not a recognized hook payload; let it through.

    tool_name, command = _extract_payload_command(payload)
    if tool_name != "Bash" or not command:
        return 0
    if "git tag" not in command:
        return 0

    tag_name, message = parse_git_tag_command(command)
    if tag_name is None or not tag_name.startswith("phase/"):
        return 0

    err = enforce_namespace(tag_name)
    if err:
        print(f"Trail guard-tag: {err}", file=sys.stderr)
        return 2

    if not message:
        print(
            "Trail guard-tag: phase tag created without -m '<capsule>' or "
            "-F <capsule-file>. Phase tags must carry a capsule annotation. "
            "Use -F /path/to/capsule.txt for multi-line capsules. See "
            "references/templates.md.",
            file=sys.stderr,
        )
        return 2

    # Detect the -m "$(cat ...)" anti-pattern. Hooks see the unevaluated shell
    # command, so command substitution arrives as literal text. Give a
    # specific error rather than the confusing "missing sections" output.
    if any(token in message for token in ("$(", "${", "`")):
        print(
            "Trail guard-tag: -m argument contains unevaluated shell "
            "substitution syntax. Hooks read the shell command before it "
            "runs, so $() and backticks arrive as literal text. Use "
            "-F /path/to/capsule.txt instead.",
            file=sys.stderr,
        )
        return 2

    risk = "high"  # Default to strictest until we find a Risk: line.
    m = re.search(r"^Risk:\s*(low|medium|high)\s*$", message, re.M | re.I)
    if m:
        risk = m.group(1).lower()

    missing = validate_capsule_body(message, risk)
    if missing:
        print(
            f"Trail guard-tag: capsule missing required sections for "
            f"risk={risk}: {', '.join(missing)}. See references/templates.md.",
            file=sys.stderr,
        )
        return 2

    # NEXT.md freshness: best-effort check that NEXT references the next
    # phase number. Skipped if NEXT.md is absent.
    repo = find_repo_root()
    next_path = repo / ".trail" / "NEXT.md"
    if next_path.exists():
        m2 = PHASE_TAG_RE.match(tag_name)
        if m2:
            n = int(m2.group("n"))
            slug = m2.group("slug")
            next_n = n + 1
            text = next_path.read_text(errors="replace").lower()
            wanted_tag = f"phase/{slug}-{next_n}".lower()
            wanted_words = f"phase {next_n}"
            final_markers = ("final", "finalize", "merge", "no more phase", "last phase")
            is_final = any(m in text for m in final_markers)
            if wanted_tag not in text and wanted_words not in text and not is_final:
                print(
                    f"Trail guard-tag: .trail/NEXT.md does not reference "
                    f"phase {next_n}. Update NEXT.md before tagging phase {n}, "
                    f"or include 'final'/'finalize'/'merge' if this is the last phase.",
                    file=sys.stderr,
                )
                return 2

    # Audit-required flag check: block if a prior phase still has a pending
    # audit. /trail audit clears the flag after writing findings to NEXT.md.
    pending = pending_audit_flags(repo)
    if pending:
        names = [p.name.replace("audit-required-", "").replace(".flag", "") for p in pending]
        print(
            f"Trail guard-tag: audit required from phase(s) {', '.join(names)} "
            "before tagging the next phase. Run /trail audit, or remove the "
            "flag file(s) under .trail/ if you intentionally want to skip.",
            file=sys.stderr,
        )
        return 2

    return 0


def cmd_classify_risk(paths: list[str]) -> int:
    print(classify_risk_files(paths))
    return 0


def cmd_validate_capsule(risk: str) -> int:
    body = sys.stdin.read()
    missing = validate_capsule_body(body, risk)
    if missing:
        print(f"Missing sections for risk={risk}: {', '.join(missing)}", file=sys.stderr)
        return 1
    print("ok")
    return 0


def cmd_enforce_namespace(tag: str) -> int:
    err = enforce_namespace(tag)
    if err:
        print(err, file=sys.stderr)
        return 1
    print("ok")
    return 0


def cmd_mark_audit_required(phase_n: int) -> int:
    repo = find_repo_root()
    flag_dir = repo / ".trail"
    flag_dir.mkdir(exist_ok=True)
    flag = flag_dir / f"audit-required-{phase_n}.flag"
    flag.write_text(f"audit required after phase {phase_n}\n")
    print(str(flag))
    return 0


def cmd_clear_audit_flags() -> int:
    repo = find_repo_root()
    flag_dir = repo / ".trail"
    if not flag_dir.exists():
        print("0")
        return 0
    removed = 0
    for flag in flag_dir.glob("audit-required-*.flag"):
        flag.unlink()
        removed += 1
    print(str(removed))
    return 0


def cmd_build_audit_prompt() -> int:
    repo = find_repo_root()
    plan = repo / ".trail" / "plan.md"
    if not plan.exists():
        print("Trail build-audit-prompt: no .trail/plan.md found", file=sys.stderr)
        return 1
    plan_text = plan.read_text(errors="replace")
    result = subprocess.run(
        ["git", "-C", str(repo), "tag", "-l", "phase/*",
         "--sort=taggerdate",
         "--format==== %(refname:short) ===%0a%(contents)%0a---"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    annotations = result.stdout.strip() if result.returncode == 0 else "(failed to list tags)"

    print(f"""You are auditing a Trail-managed implementation. Review the plan
against what has actually been built and decided. Tag annotations are
your only input — do not request diffs.

Plan:
{plan_text}

Phase tag annotations (in chronological order):

{annotations}

Questions to answer:
1. Are the remaining phases still right given what has been built?
2. Where has reality diverged from the plan?
3. What should change in scope, order, or existence of remaining phases?

Return a short report (under 30 lines). Be specific about phase numbers.""")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Trail phase check helpers.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("guard-tag", help="Hook entry; reads JSON on stdin.")

    p_risk = sub.add_parser("classify-risk", help="Classify risk for given paths.")
    p_risk.add_argument("paths", nargs="+")

    p_val = sub.add_parser("validate-capsule", help="Validate capsule body from stdin.")
    p_val.add_argument("--risk", default="high", choices=("low", "medium", "high"))

    p_ns = sub.add_parser("enforce-namespace", help="Check phase tag namespace.")
    p_ns.add_argument("tag")

    p_mark = sub.add_parser("mark-audit-required", help="Create audit-required flag.")
    p_mark.add_argument("phase_n", type=int)

    sub.add_parser("clear-audit-flags", help="Remove all audit-required flags.")

    sub.add_parser("build-audit-prompt", help="Emit audit prompt on stdout.")

    args = parser.parse_args(argv)

    if args.cmd == "guard-tag":
        return cmd_guard_tag()
    if args.cmd == "classify-risk":
        return cmd_classify_risk(args.paths)
    if args.cmd == "validate-capsule":
        return cmd_validate_capsule(args.risk)
    if args.cmd == "enforce-namespace":
        return cmd_enforce_namespace(args.tag)
    if args.cmd == "mark-audit-required":
        return cmd_mark_audit_required(args.phase_n)
    if args.cmd == "clear-audit-flags":
        return cmd_clear_audit_flags()
    if args.cmd == "build-audit-prompt":
        return cmd_build_audit_prompt()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

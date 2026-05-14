#!/usr/bin/env python3
"""Read-only status helper for the Trail skill.

Reads phase tags + .trail/ artifacts from a repository and prints a structured
status view. Self-suppresses (exits 0 with no output) when no Trail state
exists, so it can be wired into a Stop hook without producing noise on
non-Trail sessions.

Usage:
  trace_status.py [REPO_PATH]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


PHASE_TAG_NUMBER_RE = re.compile(
    r"^phase/[a-z0-9][a-z0-9-]*?-(\d+)(?:-attempt-(\d+))?$"
)


def run_git(repo: Path, args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return result.returncode, result.stdout.strip()


def _phase_sort_key(tag: str) -> tuple[int, int]:
    """Sort key: (phase_number desc, attempt_number desc).

    Sorting by taggerdate alone is unreliable when tags are created within
    the same second (common in tests, but possible in real bursts too).
    Phase tags carry their order in the name; trust that.

    Returns (large-N, large-K) so that descending sort puts later phases
    first. For non-matching tags, returns (-1, -1) so they sort last.
    """
    m = PHASE_TAG_NUMBER_RE.match(tag)
    if not m:
        return (-1, -1)
    n = int(m.group(1))
    k = int(m.group(2)) if m.group(2) else 1  # implicit attempt 1
    return (n, k)


def phase_tags(repo: Path) -> list[str]:
    code, out = run_git(repo, [
        "tag", "-l", "phase/*",
        "--format=%(refname:short)",
    ])
    if code != 0 or not out:
        return []
    tags = out.splitlines()
    # Descending: highest phase number first, then highest attempt within phase.
    tags.sort(key=_phase_sort_key, reverse=True)
    return tags


def tag_annotation(repo: Path, tag: str) -> str:
    code, out = run_git(repo, [
        "for-each-ref", f"refs/tags/{tag}",
        "--format=%(contents)",
    ])
    if code != 0:
        return ""
    return out.strip()


def tag_subject(repo: Path, tag: str) -> str:
    code, out = run_git(repo, [
        "for-each-ref", f"refs/tags/{tag}",
        "--format=%(contents:subject)",
    ])
    return out.strip() if code == 0 else ""


def has_trail_state(repo: Path) -> bool:
    if phase_tags(repo):
        return True
    trail_dir = repo / ".trail"
    if not trail_dir.exists():
        return False
    return any((trail_dir / name).exists() for name in ("NEXT.md", "plan.md"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Show Trail status for a repository.")
    parser.add_argument("repo", nargs="?", default=".", help="Repository path (default: cwd)")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()

    # Self-suppress on non-git or non-Trail repos so the Stop hook stays quiet.
    code, _ = run_git(repo, ["rev-parse", "--git-dir"])
    if code != 0:
        return 0
    if not has_trail_state(repo):
        return 0

    print(f"Trail status: {repo}")

    code, status = run_git(repo, ["status", "--short", "--branch"])
    print()
    print("Branch + worktree:")
    print(status if status else "(clean)")

    tags = phase_tags(repo)
    print()
    print(f"Phase tags ({len(tags)}):")
    if tags:
        for tag in tags:
            print(f"  {tag}  {tag_subject(repo, tag)}")
    else:
        print("  (none yet)")

    print()
    plan_path = repo / ".trail" / "plan.md"
    if plan_path.exists():
        print(f"Plan: {plan_path.relative_to(repo)} ({plan_path.stat().st_size} bytes)")
    else:
        print("Plan: (no .trail/plan.md)")

    print()
    next_path = repo / ".trail" / "NEXT.md"
    if next_path.exists():
        print(f"NEXT ({next_path.relative_to(repo)}):")
        print(next_path.read_text(errors="replace").rstrip())
    else:
        print("NEXT: (no .trail/NEXT.md)")

    print()
    if tags:
        latest = tags[0]
        print(f"Latest capsule ({latest}):")
        print(tag_annotation(repo, latest))
    else:
        print("Latest capsule: (no phase tags yet)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

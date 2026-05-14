# Trace plan: hello-cli

Branch: `claude/hello-cli`
Tag namespace: `phase/hello-cli-N`
NEXT pointer: `.trail/NEXT.md`
Validation: `python3 -m pytest tests/ -v`

| Phase | Goal | Risk | Tasks | Validation |
| --- | --- | --- | --- | --- |
| 1 | Core greet function | low | `greet.py` with `greet(name)` returning `"Hello, <name>!"`, edge cases for empty/whitespace name | `python3 -m pytest tests/test_greet.py -v` |
| 2 | CLI entry point | low | `main.py` with argparse, reads name from `--name` flag, prints greeting, tests for CLI invocation | `python3 -m pytest tests/ -v`, `python3 main.py --name World` |

## Risk rationale

- Phase 1 is **low**: pure function, no I/O, no external dependencies.
- Phase 2 is **low**: argparse CLI wrapper over phase 1's function. Isolated, no auth or data concerns.

## Notes

- No audit cadence fires (only 2 phases, neither a multiple of 3, no risk upgrade).
- After phase 2 tag, run `/trail finalize` to generate a PR description from the tag annotations.

# Trace plan: Add project export

Branch: `claude/add-export`
Tag namespace: `phase/add-export-N`
NEXT pointer: `.trail/NEXT.md`
Validation: `npm test`, `npm run build`

| Phase | Goal | Risk | Tasks | Validation | Docs |
| --- | --- | --- | --- | --- | --- |
| 1 | Define export domain model + serializer | low | export request type, serializer for project metadata + tasks, focused tests | `npm test -- export` | inline in src + update domain README |
| 2 | Add export API endpoint with auth | high | route, request validation, RBAC check, error handling, integration tests | `npm test`, manual `curl` with auth header | `docs/architecture.md` API section |
| 3 | Add UI entry point (download button + state) | medium | button placement, success/error toasts, loading state, e2e test | `npm test`, `npm run build`, Playwright e2e | inline in components README |

## Risk rationale

- Phase 1 is **low**: pure domain code, no external touchpoints, fully tested in isolation. No prior author churn on these files.
- Phase 2 is **high**: touches auth/RBAC (matches `auth` signal in classify-risk), crosses trust boundary, externally visible API surface. `/review` and `/security-review` required before tagging.
- Phase 3 is **medium**: UI changes only, but the success/error pathway must integrate cleanly with phase 2's API contract. Architecture-affecting if state management shape changes.

## Notes

- Compaction strategy: phase tag annotations are the durable trail; `.trail/NEXT.md` is the live handoff. Use `/ts` to recover state in new sessions.
- `/trail audit` will run automatically after phase 3 (3 % 3 == 0) and on any risk upgrade. Phase 2 is already at the ceiling, so an audit there only fires if the audit cadence hits.
- Validation discipline: phase 2 requires both unit and manual API verification before tag. Capsule must quote the manual verification command and response code.

# NEXT — add project export

Branch: `claude/add-export`
Latest tag: `phase/add-export-1`
Next phase: `phase/add-export-2` — Add export API endpoint with auth

## What's next

Phase 2 begins by wiring the export route. The domain serializer from phase
1 lives at `src/domain/export/serializer.ts` and exposes `serializeExport()`
— call it from the route handler. Before writing the route:

1. Read `src/api/middleware/rbac.ts` to confirm the existing RBAC pattern.
2. Decide on the export permission name (`export:read` vs `project:export`).
3. Confirm with user before introducing a new permission string.

The handler should `await` the serializer, set `Content-Type: application/json`
with a `Content-Disposition: attachment` header, and return 403 (not 401)
when RBAC denies. Tests under `tests/api/export.test.ts`.

Risk for this phase is **high** (auth + external API). `/review` and
`/security-review` are required before tagging `phase/add-export-2`.

## In-flight notes

- 2026-05-14: phase 1 complete; phase 2 not yet started

## Audit findings

(none yet — next audit fires after phase 3 unless risk upgrades earlier)

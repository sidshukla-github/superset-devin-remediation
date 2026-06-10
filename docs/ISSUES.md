# Remediation Issues — Superset Fork

Target repository: [sidshukla-github/superset](https://github.com/sidshukla-github/superset)

Create these issues on the fork, then label each with `devin-remediate` to trigger remediation (or use `docker compose run --rm cli simulate --issue N` locally).

| # | Title | Type | Status | Issue | PR |
|---|-------|------|--------|-------|-----|
| 1 | Replace `any` types in TimeTable visualization utils | Code quality | pending | — | — |
| 2 | Add type hints to MCP system utils placeholder | Code quality | pending | — | — |
| 3 | Enforce dependency-review failures on critical CVEs | Supply chain | pending | — | — |
| 4 | Bump pinned GitHub Actions in dependency-review workflow | Dependency | pending | — | — |

Update this table with issue and PR URLs after creation.

---

## Issue 1 — Replace `any` types in TimeTable utils

**Labels:** `devin-remediate`, `code-quality`

```markdown
## Problem
The TimeTable visualization utilities use `any` types, which conflicts with Superset's TypeScript modernization standards.

## Scope
- Files:
  - `superset-frontend/src/visualizations/TimeTable/utils/sortUtils/sortUtils.ts`
  - `superset-frontend/src/visualizations/TimeTable/types.ts`
- Out of scope: other visualizations, unrelated refactors

## Acceptance criteria
- [ ] Replace `any` with proper types in scoped files
- [ ] `npm run test -- sortUtils.test.ts` passes in `superset-frontend/`
- [ ] `pre-commit run` passes on changed files
- [ ] PR references this issue

## Automation
Label `devin-remediate` to trigger external remediation orchestrator.
```

---

## Issue 2 — Add type hints to MCP system utils

**Labels:** `devin-remediate`, `code-quality`

```markdown
## Problem
`superset/mcp_service/system/system_utils.py` contains placeholder functions without complete type hints.

## Scope
- Files: `superset/mcp_service/system/system_utils.py`
- Out of scope: other MCP modules

## Acceptance criteria
- [ ] Add type hints to functions in scoped file
- [ ] `pre-commit run mypy` passes on changed files
- [ ] Existing unit tests pass
- [ ] PR references this issue

## Automation
Label `devin-remediate` to trigger external remediation orchestrator.
```

---

## Issue 3 — Enforce dependency-review on critical CVEs

**Labels:** `devin-remediate`, `security`

```markdown
## Problem
The dependency-review GitHub Action uses `continue-on-error: true`, so critical CVEs do not block merges.

## Scope
- Files: `.github/workflows/dependency-review.yml`
- Change: set `continue-on-error: false` on the dependency-review step

## Acceptance criteria
- [ ] `continue-on-error: false` on dependency-review action
- [ ] No other workflow changes
- [ ] PR references this issue

## Automation
Label `devin-remediate` to trigger external remediation orchestrator.
```

---

## Issue 4 — Bump pinned GitHub Actions

**Labels:** `devin-remediate`, `dependencies`

```markdown
## Problem
Pinned GitHub Actions in the dependency-review workflow may be behind latest patch releases.

## Scope
- Files: `.github/workflows/dependency-review.yml`
- Bump `actions/checkout` and `actions/dependency-review-action` to latest stable patch versions

## Acceptance criteria
- [ ] Action SHAs or tags updated to current stable versions
- [ ] Workflow YAML remains valid
- [ ] PR references this issue

## Automation
Label `devin-remediate` to trigger external remediation orchestrator.
```

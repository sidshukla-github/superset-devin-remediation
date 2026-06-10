#!/usr/bin/env bash
# Create remediation issues on the Superset fork via GitHub CLI.
set -euo pipefail

REPO="${TARGET_REPO:-sidshukla-github/superset}"

gh label create devin-remediate --repo "$REPO" --color 0E8A16 --force 2>/dev/null || true
gh label create devin-completed --repo "$REPO" --color 1D76DB --force 2>/dev/null || true
gh label create devin-failed --repo "$REPO" --color D93F0B --force 2>/dev/null || true

create_issue() {
  local title="$1"
  local labels="$2"
  local body="$3"
  gh issue create --repo "$REPO" --title "$title" --label "$labels" --body "$body"
}

create_issue \
  "Replace any types in TimeTable visualization utils" \
  "devin-remediate,code-quality" \
  "$(cat <<'BODY'
## Problem
The TimeTable visualization utilities use `any` types, which conflicts with Superset's TypeScript modernization standards.

## Scope
- Files:
  - `superset-frontend/src/visualizations/TimeTable/utils/sortUtils/sortUtils.ts`
  - `superset-frontend/src/visualizations/TimeTable/types.ts`

## Acceptance criteria
- [ ] Replace `any` with proper types in scoped files
- [ ] `npm run test -- sortUtils.test.ts` passes in `superset-frontend/`
- [ ] `pre-commit run` passes on changed files
- [ ] PR references this issue
BODY
)"

create_issue \
  "Add type hints to MCP system utils placeholder" \
  "devin-remediate,code-quality" \
  "$(cat <<'BODY'
## Problem
`superset/mcp_service/system/system_utils.py` contains placeholder functions without complete type hints.

## Scope
- Files: `superset/mcp_service/system/system_utils.py`

## Acceptance criteria
- [ ] Add type hints to functions in scoped file
- [ ] `pre-commit run mypy` passes on changed files
- [ ] PR references this issue
BODY
)"

create_issue \
  "Enforce dependency-review failures on critical CVEs" \
  "devin-remediate,security" \
  "$(cat <<'BODY'
## Problem
The dependency-review GitHub Action uses `continue-on-error: true`, so critical CVEs do not block merges.

## Scope
- Files: `.github/workflows/dependency-review.yml`
- Change: set `continue-on-error: false` on the dependency-review step

## Acceptance criteria
- [ ] `continue-on-error: false` on dependency-review action
- [ ] PR references this issue
BODY
)"

create_issue \
  "Bump pinned GitHub Actions in dependency-review workflow" \
  "devin-remediate,dependencies" \
  "$(cat <<'BODY'
## Problem
Pinned GitHub Actions in the dependency-review workflow may be behind latest patch releases.

## Scope
- Files: `.github/workflows/dependency-review.yml`

## Acceptance criteria
- [ ] Action SHAs or tags updated to current stable versions
- [ ] Workflow YAML remains valid
- [ ] PR references this issue
BODY
)"

echo "Done. Update docs/ISSUES.md with the new issue URLs."

## Problem
The dependency-review GitHub Action uses `continue-on-error: true`, so critical CVEs do not block merges.

## Scope
- Files: `.github/workflows/dependency-review.yml`
- Change: set `continue-on-error: false` on the dependency-review step

## Acceptance criteria
- [ ] `continue-on-error: false` on dependency-review action
- [ ] PR references this issue

## Problem
The dependency-review workflow cannot be triggered manually from the GitHub Actions UI.

## Scope
- **Only** edit `.github/workflows/dependency-review.yml`
- **Only** add a top-level `workflow_dispatch:` trigger under the existing `on:` block
- Do **not** modify any other files (no frontend, Python, Docker, or dependency changes)
- Do **not** run `npm install`, frontend tests, or full `pre-commit` — this is a one-line YAML change

## Acceptance criteria
- [ ] `workflow_dispatch:` is present under `on:` in `.github/workflows/dependency-review.yml`
- [ ] PR touches only that workflow file
- [ ] PR title: `ci(dependency-review): enable manual workflow dispatch`
- [ ] PR body references this issue (`Fixes #N`)

## Automation
Label `devin-remediate` to trigger external remediation orchestrator.

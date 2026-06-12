#!/usr/bin/env bash
# Create remediation issues on the Superset fork via GitHub CLI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${TARGET_REPO:-sidshukla-github/superset}"

ensure_label() {
  gh label create "$1" --repo "$REPO" --color "$2" --force 2>/dev/null || true
}

ensure_label devin-remediate 0E8A16
ensure_label devin-completed 1D76DB
ensure_label devin-failed D93F0B
ensure_label code-quality 1D76DB
ensure_label security D93F0B
ensure_label dependencies FBCA04

# Create without devin-remediate first, then add it — avoids duplicate webhook triggers.
create_remediation_issue() {
  local title="$1"
  local extra_labels="$2"
  local body_file="$3"
  local number
  number=$(gh issue create --repo "$REPO" --title "$title" --body-file "$body_file" --json number -q .number)
  gh issue edit "$number" --repo "$REPO" --add-label "${extra_labels},devin-remediate"
  echo "Created issue #${number}: https://github.com/${REPO}/issues/${number}"
}

# create_issue \
#   "Replace any types in TimeTable visualization utils" \
#   "devin-remediate,code-quality" \
#   "$SCRIPT_DIR/issue-bodies/01-timetable-any.md"
#
# create_issue \
#   "Add type hints to MCP system utils placeholder" \
#   "devin-remediate,code-quality" \
#   "$SCRIPT_DIR/issue-bodies/02-mcp-type-hints.md"
#
# create_issue \
#   "Enforce dependency-review failures on critical CVEs" \
#   "devin-remediate,security" \
#   "$SCRIPT_DIR/issue-bodies/03-dependency-review.md"
#
# create_issue \
#   "Bump pinned GitHub Actions in dependency-review workflow" \
#   "devin-remediate,dependencies" \
#   "$SCRIPT_DIR/issue-bodies/04-bump-actions.md"

# Fast demo issue: single-file YAML change (~2–5 min with Devin). Use for video walkthroughs.
create_remediation_issue \
  "[Demo] Enable manual trigger for dependency-review workflow" \
  "dependencies" \
  "$SCRIPT_DIR/issue-bodies/05-demo-workflow-dispatch.md"

echo "Done. Update docs/ISSUES.md with the new issue URLs."

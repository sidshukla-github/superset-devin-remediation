from typing import Any

from remediation.config import settings

STRUCTURED_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "fixed": {"type": "boolean"},
        "pr_url": {"type": "string"},
        "summary": {"type": "string"},
        "tests_run": {"type": "string"},
    },
    "required": ["fixed", "summary"],
}


def build_remediation_prompt(issue: dict[str, Any]) -> str:
    number = issue["number"]
    title = issue.get("title", "")
    body = issue.get("body") or ""
    url = issue.get("html_url", "")

    return f"""You are remediating a scoped issue in the Apache Superset fork.

Repository: {settings.target_repo}
Issue: #{number} — {title}
Issue URL: {url}

## Issue description
{body}

## Instructions
1. Read AGENTS.md and SECURITY.md in the repository before making changes.
2. Limit changes to the files and scope described in the issue.
3. Run `pre-commit run` on changed files before opening a PR.
4. Open a pull request against `{settings.target_repo}` with title format: `fix(scope): <description>`
5. Reference the issue in the PR body: `Fixes #{number}`
6. Do not attempt large migrations (SQLAlchemy 2.x, React 19, etc.).

## Acceptance criteria
Follow the acceptance criteria in the issue body. If tests are specified, run them and report results.

When finished, summarize what you changed and which tests you ran.
"""

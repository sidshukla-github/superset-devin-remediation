import logging
import time
from datetime import datetime, timezone
from typing import Any

from remediation.config import settings
from remediation.devin_client import DevinClient
from remediation.github_client import GitHubClient, SESSION_MARKER
from remediation.metrics import append_run
from remediation.prompts import STRUCTURED_OUTPUT_SCHEMA, build_remediation_prompt

logger = logging.getLogger(__name__)


class RemediationOrchestrator:
    def __init__(self) -> None:
        self.devin = DevinClient()
        self.github = GitHubClient()

    def remediate_issue(self, issue_number: int, force: bool = False) -> dict[str, Any]:
        started = time.time()
        issue = self.github.get_issue(issue_number)

        if not force and self.github.has_existing_session(issue_number):
            logger.info("Issue #%s already has a Devin session; skipping", issue_number)
            return {"skipped": True, "issue_number": issue_number, "reason": "already_processed"}

        prompt = build_remediation_prompt(issue)
        tags = ["superset-remediation", f"issue-{issue_number}"]

        session = self.devin.create_session(
            prompt=prompt,
            repos=[settings.target_repo],
            tags=tags,
            structured_output_schema=STRUCTURED_OUTPUT_SCHEMA,
        )
        session_id = session["session_id"]
        session_url = session.get("url", f"https://app.devin.ai/sessions/{session_id}")

        self.github.add_comment(
            issue_number,
            (
                f"## Devin remediation started\n\n"
                f"{SESSION_MARKER} `{session_id}`\n\n"
                f"- **Session**: {session_url}\n"
                f"- **Status**: running\n"
                f"- **Repo**: `{settings.target_repo}`"
            ),
        )

        if settings.dry_run:
            final_session = session
        else:
            final_session = self.devin.poll_until_terminal(session_id)

        pr_urls = [pr.get("pr_url") for pr in final_session.get("pull_requests", []) if pr.get("pr_url")]
        structured = final_session.get("structured_output") or {}
        status = final_session.get("status", "unknown")
        success = status == "exit" and (structured.get("fixed", True) or bool(pr_urls))

        result_label = "devin-completed" if success else "devin-failed"
        self.github.add_label(issue_number, result_label)

        summary = structured.get("summary", "Remediation finished.")
        self.github.add_comment(
            issue_number,
            (
                f"## Devin remediation {'completed' if success else 'failed'}\n\n"
                f"- **Session**: {session_url}\n"
                f"- **Status**: {status}\n"
                f"- **Success**: {success}\n"
                f"- **ACU consumed**: {final_session.get('acus_consumed', 'n/a')}\n"
                f"- **PRs**: {', '.join(pr_urls) if pr_urls else 'none'}\n\n"
                f"### Summary\n{summary}"
            ),
        )

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "issue_number": issue_number,
            "issue_url": issue.get("html_url"),
            "session_id": session_id,
            "session_url": session_url,
            "status": status,
            "success": success,
            "pr_urls": pr_urls,
            "acus_consumed": final_session.get("acus_consumed"),
            "duration_seconds": round(time.time() - started, 1),
        }
        append_run(record)
        logger.info("Remediation for issue #%s finished: success=%s", issue_number, success)
        return record

    def poll_unprocessed_issues(self) -> list[dict[str, Any]]:
        issues = self.github.list_issues_with_label()
        results = []
        for issue in issues:
            if issue.get("pull_request"):
                continue
            number = issue["number"]
            if self.github.has_existing_session(number):
                continue
            results.append(self.remediate_issue(number))
        return results

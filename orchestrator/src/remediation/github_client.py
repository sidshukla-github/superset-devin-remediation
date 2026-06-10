from typing import Any

import httpx

from remediation.config import settings

GITHUB_API = "https://api.github.com"
SESSION_MARKER = "devin-session:"


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or settings.github_token
        self.owner = settings.github_owner
        self.repo = settings.github_repo
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get_issue(self, issue_number: int) -> dict[str, Any]:
        if settings.dry_run:
            return {
                "number": issue_number,
                "title": f"Dry-run issue #{issue_number}",
                "body": "Dry-run issue body for local simulation.",
                "html_url": f"https://github.com/{settings.target_repo}/issues/{issue_number}",
                "labels": [{"name": settings.remediation_label}],
            }

        with httpx.Client(timeout=30) as client:
            response = client.get(
                f"{GITHUB_API}/repos/{self.owner}/{self.repo}/issues/{issue_number}",
                headers=self._headers,
            )
            response.raise_for_status()
            return response.json()

    def list_issues_with_label(self, label: str | None = None) -> list[dict[str, Any]]:
        label = label or settings.remediation_label
        if settings.dry_run:
            return []

        with httpx.Client(timeout=30) as client:
            response = client.get(
                f"{GITHUB_API}/repos/{self.owner}/{self.repo}/issues",
                headers=self._headers,
                params={"labels": label, "state": "open", "per_page": 100},
            )
            response.raise_for_status()
            return response.json()

    def list_issue_comments(self, issue_number: int) -> list[dict[str, Any]]:
        if settings.dry_run:
            return []

        with httpx.Client(timeout=30) as client:
            response = client.get(
                f"{GITHUB_API}/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
                headers=self._headers,
                params={"per_page": 100},
            )
            response.raise_for_status()
            return response.json()

    def has_existing_session(self, issue_number: int) -> bool:
        comments = self.list_issue_comments(issue_number)
        return any(SESSION_MARKER in c.get("body", "") for c in comments)

    def add_comment(self, issue_number: int, body: str) -> dict[str, Any]:
        if settings.dry_run:
            print(f"[dry-run] Comment on issue #{issue_number}:\n{body}\n")
            return {"id": 0, "body": body}

        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{GITHUB_API}/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
                headers=self._headers,
                json={"body": body},
            )
            response.raise_for_status()
            return response.json()

    def add_label(self, issue_number: int, label: str) -> None:
        if settings.dry_run:
            print(f"[dry-run] Add label '{label}' to issue #{issue_number}")
            return

        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{GITHUB_API}/repos/{self.owner}/{self.repo}/issues/{issue_number}/labels",
                headers=self._headers,
                json={"labels": [label]},
            )
            response.raise_for_status()

    def ensure_label_exists(self, label: str, color: str = "0E8A16") -> None:
        if settings.dry_run:
            return

        with httpx.Client(timeout=30) as client:
            response = client.get(
                f"{GITHUB_API}/repos/{self.owner}/{self.repo}/labels",
                headers=self._headers,
                params={"per_page": 100},
            )
            response.raise_for_status()
            existing = {item["name"] for item in response.json()}
            if label in existing:
                return

            client.post(
                f"{GITHUB_API}/repos/{self.owner}/{self.repo}/labels",
                headers=self._headers,
                json={"name": label, "color": color},
            ).raise_for_status()

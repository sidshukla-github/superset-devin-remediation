import logging
import time
from typing import Any

import httpx

from remediation.config import settings
from remediation.http_utils import http_client

logger = logging.getLogger(__name__)

BASE_URL = "https://api.devin.ai/v3"
TERMINAL_STATUSES = {"exit", "error", "suspended"}
ACTIVE_STATUSES = {"new", "claimed", "running", "resuming"}


class DevinClient:
    def __init__(self, api_key: str | None = None, org_id: str | None = None) -> None:
        self.api_key = api_key or settings.devin_api_key
        self.org_id = org_id or settings.devin_org_id
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{BASE_URL}/organizations/{self.org_id}{path}"

    def verify(self) -> dict[str, Any]:
        with http_client() as client:
            response = client.get(f"{BASE_URL}/self", headers=self._headers)
            response.raise_for_status()
            return response.json()

    def create_session(
        self,
        prompt: str,
        repos: list[str],
        tags: list[str],
        max_acu_limit: int | None = None,
        structured_output_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if settings.dry_run:
            return {
                "session_id": "devin-dry-run-001",
                "url": "https://app.devin.ai/sessions/devin-dry-run-001",
                "status": "exit",
                "pull_requests": [
                    {
                        "pr_url": f"https://github.com/{settings.target_repo}/pull/1",
                        "pr_state": "open",
                    }
                ],
                "structured_output": {
                    "fixed": True,
                    "pr_url": f"https://github.com/{settings.target_repo}/pull/1",
                    "summary": "Dry-run remediation completed successfully.",
                    "tests_run": "pre-commit run (dry-run)",
                },
                "acus_consumed": 0.0,
            }

        payload: dict[str, Any] = {
            "prompt": prompt,
            "repos": repos,
            "tags": tags,
            "max_acu_limit": max_acu_limit or settings.max_acu_limit,
        }
        if structured_output_schema:
            payload["structured_output_schema"] = structured_output_schema

        with http_client(timeout=60) as client:
            response = self._request_with_retry(
                client, "POST", self._url("/sessions"), json=payload
            )
            if response.status_code >= 400:
                detail = response.text[:500]
                raise httpx.HTTPStatusError(
                    f"Devin API error {response.status_code}: {detail}",
                    request=response.request,
                    response=response,
                )
            return response.json()

    def get_session(self, session_id: str) -> dict[str, Any]:
        if settings.dry_run:
            return {
                "session_id": session_id,
                "status": "exit",
                "status_detail": "finished",
                "pull_requests": [
                    {
                        "pr_url": f"https://github.com/{settings.target_repo}/pull/1",
                        "pr_state": "open",
                    }
                ],
                "structured_output": {
                    "fixed": True,
                    "pr_url": f"https://github.com/{settings.target_repo}/pull/1",
                    "summary": "Dry-run remediation completed successfully.",
                    "tests_run": "pre-commit run (dry-run)",
                },
                "acus_consumed": 0.0,
            }

        with http_client() as client:
            response = self._request_with_retry(
                client, "GET", self._url(f"/sessions/{session_id}")
            )
            response.raise_for_status()
            return response.json()

    def terminate_session(self, session_id: str, archive: bool | None = None) -> dict[str, Any]:
        """Stop a running session. Archives by default so it remains visible in Devin UI."""
        if settings.dry_run:
            session = self.get_session(session_id)
            session["status"] = "exit"
            return session

        archive = settings.terminate_session_archive if archive is None else archive
        params = {"archive": "true"} if archive else {}

        with http_client() as client:
            response = self._request_with_retry(
                client,
                "DELETE",
                self._url(f"/sessions/{session_id}"),
                params=params,
            )
            if response.status_code >= 400:
                detail = response.text[:500]
                raise httpx.HTTPStatusError(
                    f"Devin terminate error {response.status_code}: {detail}",
                    request=response.request,
                    response=response,
                )
            return response.json()

    def stop_if_pr_open(self, session_id: str, session: dict[str, Any]) -> dict[str, Any]:
        """Terminate an active session once it has opened a PR."""
        if not settings.terminate_session_on_pr:
            return session
        if session.get("status") not in ACTIVE_STATUSES:
            return session
        if not any(pr.get("pr_url") for pr in session.get("pull_requests", [])):
            return session

        logger.info("PR detected on active session %s; terminating", session_id)
        try:
            return self.terminate_session(session_id)
        except httpx.HTTPError as exc:
            logger.warning("Could not terminate session %s: %s", session_id, exc)
            return session

    def send_message(self, session_id: str, message: str) -> dict[str, Any]:
        if settings.dry_run:
            return {"ok": True}

        with http_client() as client:
            response = self._request_with_retry(
                client,
                "POST",
                self._url(f"/sessions/{session_id}/messages"),
                json={"message": message},
            )
            response.raise_for_status()
            return response.json()

    def list_sessions(self, tags: list[str] | None = None, first: int = 50) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"first": first}
        if tags:
            for tag in tags:
                params.setdefault("tags", []).append(tag)

        with http_client() as client:
            response = self._request_with_retry(
                client, "GET", self._url("/sessions"), params=params
            )
            response.raise_for_status()
            data = response.json()
            return data.get("items", data if isinstance(data, list) else [])

    def poll_until_terminal(
        self,
        session_id: str,
        interval: int | None = None,
        on_update: Any | None = None,
    ) -> dict[str, Any]:
        interval = interval or settings.poll_interval_seconds
        while True:
            session = self.get_session(session_id)
            if on_update:
                on_update(session)

            status = session.get("status", "")
            status_detail = session.get("status_detail", "")

            if status in TERMINAL_STATUSES:
                return session

            # Devin often keeps status=running after opening a PR — terminate and finish.
            if any(pr.get("pr_url") for pr in session.get("pull_requests", [])):
                return self.stop_if_pr_open(session_id, session)

            if status_detail == "finished":
                return session

            if status_detail in {"waiting_for_user", "waiting_for_approval"}:
                self.send_message(
                    session_id,
                    "Proceed without asking for approval. Open a draft PR and run "
                    "pre-commit on changed files.",
                )

            time.sleep(interval)

    def _request_with_retry(
        self,
        client: httpx.Client,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        delay = 2
        for attempt in range(5):
            response = client.request(method, url, headers=self._headers, **kwargs)
            if response.status_code != 429:
                return response
            time.sleep(delay)
            delay = min(delay * 2, 60)
        return response

import hashlib
import hmac
import json
import logging
from typing import Any
from urllib.parse import parse_qs

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from remediation.config import settings
from remediation.devin_client import DevinClient
from remediation.metrics import format_report_html, format_report_markdown, generate_report
from remediation.orchestrator import RemediationOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Superset Devin Remediation",
    description="Webhook receiver and metrics API for automated issue remediation",
    version="0.1.0",
)


def parse_github_payload(body: bytes, content_type: str | None) -> dict[str, Any]:
    if not body:
        raise HTTPException(status_code=400, detail="Empty webhook body")

    if content_type and "application/json" in content_type:
        return json.loads(body)

    # GitHub default webhook content type: x-www-form-urlencoded with payload=...
    if content_type and "application/x-www-form-urlencoded" in content_type:
        parsed = parse_qs(body.decode("utf-8"))
        payload = parsed.get("payload", [None])[0]
        if not payload:
            raise HTTPException(status_code=400, detail="Missing payload field")
        return json.loads(payload)

    # Fallback: try JSON first, then form encoding.
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        parsed = parse_qs(body.decode("utf-8"))
        payload = parsed.get("payload", [None])[0]
        if not payload:
            raise HTTPException(status_code=400, detail="Unrecognized webhook body format")
        return json.loads(payload)


def verify_github_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    if not secret:
        return True
    if not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_labeled_issue(issue_number: int) -> None:
    try:
        RemediationOrchestrator().remediate_issue(issue_number)
    except Exception:
        logger.exception("Remediation failed for issue #%s", issue_number)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "target_repo": settings.target_repo,
        "devin_configured": settings.devin_configured,
        "github_configured": settings.github_configured,
        "dry_run": settings.dry_run,
    }


@app.get("/report", response_model=None)
def report(format: str = "markdown") -> Response:
    live_sessions = []
    if settings.devin_configured and not settings.dry_run:
        try:
            live_sessions = DevinClient().list_sessions(tags=["superset-remediation"])
        except Exception:
            logger.exception("Failed to fetch live Devin sessions")

    data = generate_report(live_sessions)
    if format == "json":
        return JSONResponse(data)
    if format == "html":
        return Response(format_report_html(data), media_type="text/html")
    return PlainTextResponse(format_report_markdown(data), media_type="text/markdown")


@app.post("/webhooks/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> dict[str, str]:
    payload = await request.body()

    if not verify_github_signature(payload, x_hub_signature_256, settings.webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    content_type = request.headers.get("content-type")
    event = parse_github_payload(payload, content_type)

    if x_github_event != "issues":
        return {"status": "ignored", "reason": f"event={x_github_event}"}

    action = event.get("action")
    issue = event.get("issue", {})
    issue_number = issue.get("number")
    if not issue_number:
        raise HTTPException(status_code=400, detail="Missing issue number")

    repo_full_name = event.get("repository", {}).get("full_name")
    if repo_full_name != settings.target_repo:
        return {"status": "ignored", "reason": f"repo={repo_full_name}"}

    # Only handle explicit label application. "issues.opened" with labels at creation
    # also emits "issues.labeled" — handling both causes duplicate Devin sessions.
    if action != "labeled":
        return {"status": "ignored", "reason": f"action={action}"}

    label = event.get("label", {}).get("name")
    if label != settings.remediation_label:
        return {"status": "ignored", "reason": f"label={label}"}

    background_tasks.add_task(handle_labeled_issue, issue_number)
    return {"status": "accepted", "issue_number": str(issue_number), "action": action}

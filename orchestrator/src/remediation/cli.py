import argparse
import logging
import sys

from remediation.config import settings
from remediation.devin_client import DevinClient
from remediation.metrics import format_report_html, format_report_markdown, generate_report
from remediation.orchestrator import RemediationOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def cmd_simulate(args: argparse.Namespace) -> int:
    settings.dry_run = True
    result = RemediationOrchestrator().remediate_issue(args.issue, force=args.force)
    print(result)
    return 0


def cmd_poll(args: argparse.Namespace) -> int:
    results = RemediationOrchestrator().poll_unprocessed_issues()
    print(f"Processed {len(results)} issue(s)")
    for result in results:
        print(result)
    return 0


def cmd_remediate(args: argparse.Namespace) -> int:
    if not settings.devin_configured:
        logger.error("DEVIN_API_KEY and DEVIN_ORG_ID are required")
        return 1
    if not settings.github_configured:
        logger.error("GITHUB_TOKEN is required")
        return 1

    result = RemediationOrchestrator().remediate_issue(args.issue, force=args.force)
    print(result)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    live_sessions = []
    if settings.devin_configured and not settings.dry_run:
        try:
            live_sessions = DevinClient().list_sessions(tags=["superset-remediation"])
        except Exception as exc:
            logger.warning("Could not fetch live sessions: %s", exc)

    report = generate_report(live_sessions)
    if args.format == "json":
        import json
        print(json.dumps(report, indent=2))
    elif args.format == "html":
        print(format_report_html(report))
    else:
        print(format_report_markdown(report))
    return 0


def cmd_finalize(args: argparse.Namespace) -> int:
    if not settings.devin_configured or not settings.github_configured:
        logger.error("DEVIN_API_KEY, DEVIN_ORG_ID, and GITHUB_TOKEN are required")
        return 1
    result = RemediationOrchestrator().finalize_issue(args.issue, session_id=args.session)
    print(result)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    if not settings.devin_configured:
        logger.error("DEVIN_API_KEY and DEVIN_ORG_ID are required")
        return 1
    identity = DevinClient().verify()
    print("Devin API connection OK:", identity)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Superset Devin remediation CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    simulate = sub.add_parser("simulate", help="Dry-run remediation for an issue")
    simulate.add_argument("--issue", type=int, required=True)
    simulate.add_argument("--force", action="store_true")
    simulate.set_defaults(func=cmd_simulate)

    poll = sub.add_parser("poll", help="Process all open labeled issues without sessions")
    poll.set_defaults(func=cmd_poll)

    remediate = sub.add_parser("remediate", help="Run live remediation for an issue")
    remediate.add_argument("--issue", type=int, required=True)
    remediate.add_argument("--force", action="store_true")
    remediate.set_defaults(func=cmd_remediate)

    report = sub.add_parser("report", help="Print remediation metrics report")
    report.add_argument("--format", choices=["markdown", "json", "html"], default="markdown")
    report.set_defaults(func=cmd_report)

    finalize = sub.add_parser(
        "finalize",
        help="Post completion comment/labels from existing Devin session (e.g. after PR opens)",
    )
    finalize.add_argument("--issue", type=int, required=True)
    finalize.add_argument("--session", type=str, default=None)
    finalize.set_defaults(func=cmd_finalize)

    verify = sub.add_parser("verify", help="Verify Devin API credentials")
    verify.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

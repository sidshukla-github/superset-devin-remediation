import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from remediation.config import settings


def append_run(record: dict[str, Any]) -> None:
    path = Path(settings.metrics_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_runs() -> list[dict[str, Any]]:
    path = Path(settings.metrics_path)
    if not path.exists():
        return []

    runs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            runs.append(json.loads(line))
    return runs


def generate_report(live_sessions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    runs = load_runs()
    live_sessions = live_sessions or []

    total = len(runs)
    successes = sum(1 for r in runs if r.get("success"))
    failures = total - successes
    success_rate = round((successes / total) * 100, 1) if total else 0.0

    acus = [r.get("acus_consumed", 0) for r in runs if r.get("acus_consumed") is not None]
    durations = [r.get("duration_seconds", 0) for r in runs if r.get("duration_seconds")]

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    throughput: dict[str, int] = defaultdict(int)
    for run in runs:
        ts = run.get("timestamp")
        if not ts:
            continue
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt >= cutoff:
            throughput[dt.date().isoformat()] += 1

    active = [
        s for s in live_sessions if s.get("status") in {"new", "claimed", "running", "resuming"}
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_runs": total,
            "successes": successes,
            "failures": failures,
            "success_rate_percent": success_rate,
            "active_sessions": len(active),
            "avg_acu_consumed": round(sum(acus) / len(acus), 2) if acus else 0.0,
            "avg_duration_seconds": round(sum(durations) / len(durations), 1) if durations else 0.0,
        },
        "throughput_last_7_days": dict(sorted(throughput.items())),
        "recent_runs": runs[-10:],
        "active_sessions": [
            {
                "session_id": s.get("session_id"),
                "status": s.get("status"),
                "url": s.get("url"),
            }
            for s in active
        ],
    }


def format_report_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Remediation Report",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total runs | {s['total_runs']} |",
        f"| Successes | {s['successes']} |",
        f"| Failures | {s['failures']} |",
        f"| Success rate | {s['success_rate_percent']}% |",
        f"| Active sessions | {s['active_sessions']} |",
        f"| Avg ACU consumed | {s['avg_acu_consumed']} |",
        f"| Avg duration (s) | {s['avg_duration_seconds']} |",
        "",
        "## Throughput (last 7 days)",
        "",
    ]

    if report["throughput_last_7_days"]:
        for day, count in report["throughput_last_7_days"].items():
            lines.append(f"- {day}: {count} run(s)")
    else:
        lines.append("_No runs in the last 7 days._")

    lines.extend(["", "## Recent runs", ""])
    if report["recent_runs"]:
        for run in reversed(report["recent_runs"]):
            status = "success" if run.get("success") else "failed"
            lines.append(
                f"- Issue #{run.get('issue_number')} — {status} — "
                f"session `{run.get('session_id')}` — PRs: {', '.join(run.get('pr_urls', []) or ['none'])}"
            )
    else:
        lines.append("_No runs recorded yet._")

    return "\n".join(lines)

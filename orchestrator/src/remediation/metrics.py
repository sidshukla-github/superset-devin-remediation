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


def format_report_html(report: dict[str, Any]) -> str:
    s = report["summary"]
    recent_rows = ""
    for run in reversed(report["recent_runs"]):
        badge = "success" if run.get("success") else "failed"
        prs = ", ".join(run.get("pr_urls") or []) or "—"
        recent_rows += f"""
        <tr>
          <td>#{run.get('issue_number')}</td>
          <td><span class="badge {badge}">{badge}</span></td>
          <td><code>{run.get('session_id', '—')}</code></td>
          <td>{run.get('duration_seconds', '—')}s</td>
          <td>{run.get('acus_consumed', '—')}</td>
          <td>{prs}</td>
        </tr>"""

    throughput_rows = "".join(
        f"<tr><td>{day}</td><td>{count}</td></tr>"
        for day, count in report["throughput_last_7_days"].items()
    ) or "<tr><td colspan='2'>No runs in the last 7 days</td></tr>"

    active_rows = "".join(
        f"""<tr>
          <td><code>{s.get('session_id', '—')}</code></td>
          <td>{s.get('status', '—')}</td>
          <td><a href="{s.get('url', '#')}">open</a></td>
        </tr>"""
        for s in report["active_sessions"]
    ) or "<tr><td colspan='3'>No active sessions</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Remediation Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f6f8fa; color: #1f2328; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .muted {{ color: #656d76; margin-bottom: 2rem; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
    .card {{ background: white; border: 1px solid #d0d7de; border-radius: 8px; padding: 1rem; }}
    .card .value {{ font-size: 2rem; font-weight: 700; }}
    .card .label {{ color: #656d76; font-size: 0.9rem; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d0d7de; border-radius: 8px; overflow: hidden; margin-bottom: 2rem; }}
    th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #d0d7de; }}
    th {{ background: #f6f8fa; }}
    .badge {{ padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }}
    .badge.success {{ background: #dafbe1; color: #116329; }}
    .badge.failed {{ background: #ffebe9; color: #82071e; }}
    section {{ margin-bottom: 2rem; }}
  </style>
</head>
<body>
  <h1>Superset Devin Remediation Dashboard</h1>
  <p class="muted">Generated {report['generated_at']}</p>

  <div class="cards">
    <div class="card"><div class="value">{s['total_runs']}</div><div class="label">Total runs</div></div>
    <div class="card"><div class="value">{s['successes']}</div><div class="label">Completed (success)</div></div>
    <div class="card"><div class="value">{s['failures']}</div><div class="label">Failed</div></div>
    <div class="card"><div class="value">{s['success_rate_percent']}%</div><div class="label">Success rate</div></div>
    <div class="card"><div class="value">{s['active_sessions']}</div><div class="label">Active sessions</div></div>
    <div class="card"><div class="value">{s['avg_acu_consumed']}</div><div class="label">Avg ACU / run</div></div>
  </div>

  <section>
    <h2>Active sessions</h2>
    <table>
      <thead><tr><th>Session</th><th>Status</th><th>Link</th></tr></thead>
      <tbody>{active_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>Throughput (last 7 days)</h2>
    <table>
      <thead><tr><th>Date</th><th>Runs</th></tr></thead>
      <tbody>{throughput_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>Recent runs</h2>
    <table>
      <thead><tr><th>Issue</th><th>Result</th><th>Session</th><th>Duration</th><th>ACU</th><th>PRs</th></tr></thead>
      <tbody>{recent_rows or "<tr><td colspan='6'>No runs recorded yet</td></tr>"}</tbody>
    </table>
  </section>
</body>
</html>"""

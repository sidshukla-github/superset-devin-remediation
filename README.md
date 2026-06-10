# Superset Devin Remediation Orchestrator

Automated remediation system for [Apache Superset](https://github.com/apache/superset) fork issues using the [Devin API](https://docs.devin.ai/api-reference/overview).

## Architecture

This repository is the **solution repo** (Docker + orchestrator). The Superset fork is separate:

| Repository | URL | Role |
|------------|-----|------|
| **Solution** (this repo) | `sidshukla-github/superset-devin-remediation` | Orchestrator, Docker, metrics |
| **Superset fork** | [sidshukla-github/superset](https://github.com/sidshukla-github/superset) | Issues + remediated PRs |

```
Fork issue labeled "devin-remediate"
        │
        ▼
  Webhook → this service (port 8080)
        │
        ├── POST Devin API /sessions
        ├── Poll until complete
        ├── Comment on fork issue + open PR
        └── Append metrics to data/runs.jsonl
```

## Prerequisites

- Docker and Docker Compose
- [Devin service user API key](https://docs.devin.ai/api-reference/authentication) (`cog_...`) and org ID
- GitHub PAT with `repo` scope on `sidshukla-github/superset`
- Issues created on the fork (see [docs/ISSUES.md](docs/ISSUES.md))

## Quick start

```bash
cp .env.example .env
# Edit .env with your credentials

docker compose up --build
```

Verify:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/report
```

## Simulate workflow (no API keys required)

Dry-run mode exercises the full flow without calling Devin or GitHub:

```bash
docker compose --profile cli run --rm cli simulate --issue 1
docker compose --profile cli run --rm cli report
```

This writes a metrics row to `data/runs.jsonl` and prints status to the console.

## Live remediation

### Option A — Webhook (recommended for production)

1. Start the service: `docker compose up --build`
2. Expose port 8080 (ngrok, Cloudflare Tunnel, or deploy to a host)
3. In [fork repo settings → Webhooks](https://github.com/sidshukla-github/superset/settings/hooks):
   - **Payload URL**: `https://<your-host>/webhooks/github`
   - **Content type**: `application/json`
   - **Secret**: same as `WEBHOOK_SECRET` in `.env`
   - **Events**: Issues
4. Create an issue from [docs/ISSUES.md](docs/ISSUES.md) and add label `devin-remediate`

### Option B — CLI (manual trigger)

```bash
docker compose --profile cli run --rm cli verify
docker compose --profile cli run --rm cli remediate --issue 3
```

### Option C — Poll labeled issues

```bash
docker compose --profile cli run --rm cli poll
```

Processes all open issues with `devin-remediate` that do not yet have a Devin session comment.

## CLI reference

| Command | Description |
|---------|-------------|
| `simulate --issue N` | Dry-run remediation (no API calls) |
| `remediate --issue N` | Live Devin session for issue N |
| `poll` | Process all unprocessed labeled issues |
| `report` | Print metrics report (markdown) |
| `report --format json` | Print metrics as JSON |
| `verify` | Test Devin API credentials |

Run via Docker:

```bash
docker compose --profile cli run --rm cli <command>
```

## Analytics / leadership view

**Question: "How do I know this is working?"**

1. **HTTP report**: `curl http://localhost:8080/report` — success rate, ACU spend, throughput
2. **Fork issues**: each run posts start + completion comments with session URL and PR link
3. **Metrics file**: `data/runs.jsonl` — append-only audit log
4. **Devin dashboard**: filter sessions by tag `superset-remediation`

Sample metrics are in `data/runs.sample.jsonl`. Copy to `data/runs.jsonl` for a demo:

```bash
cp data/runs.sample.jsonl data/runs.jsonl
curl http://localhost:8080/report
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DEVIN_API_KEY` | Live runs | Devin service user key (`cog_...`) |
| `DEVIN_ORG_ID` | Live runs | Devin organization ID |
| `GITHUB_TOKEN` | Live runs | GitHub PAT with repo access |
| `TARGET_REPO` | No | Default: `sidshukla-github/superset` |
| `WEBHOOK_SECRET` | Webhooks | HMAC secret for GitHub webhooks |
| `REMEDIATION_LABEL` | No | Default: `devin-remediate` |
| `MAX_ACU_LIMIT` | No | Per-session ACU cap (default: 15) |
| `DRY_RUN` | No | Set `true` to skip API calls |

## Project structure

```
.
├── Dockerfile
├── docker-compose.yml
├── orchestrator/
│   └── src/remediation/
│       ├── main.py           # FastAPI webhook + /report
│       ├── orchestrator.py   # Core remediation flow
│       ├── devin_client.py   # Devin API v3 client
│       ├── github_client.py  # GitHub issue comments/labels
│       ├── metrics.py        # runs.jsonl + reporting
│       └── cli.py            # CLI entrypoint
├── docs/
│   └── ISSUES.md             # Issue templates for the fork
└── data/
    └── runs.jsonl            # Metrics (gitignored, volume-mounted)
```

## Creating fork issues

Use the templates in [docs/ISSUES.md](docs/ISSUES.md), or with GitHub CLI:

```bash
gh issue create --repo sidshukla-github/superset \
  --title "Enforce dependency-review failures on critical CVEs" \
  --label "devin-remediate,security" \
  --body-file - <<'BODY'
## Problem
The dependency-review GitHub Action uses continue-on-error: true.

## Scope
- Files: .github/workflows/dependency-review.yml

## Acceptance criteria
- [ ] continue-on-error: false on dependency-review step
- [ ] PR references this issue
BODY
```

## Submission checklist

- [ ] Solution repo pushed with Docker setup and README
- [ ] Fork at https://github.com/sidshukla-github/superset with 4 issues created
- [ ] At least one issue remediated (PR linked in issue + `docs/ISSUES.md`)
- [ ] `/report` shows success metrics
- [ ] Reviewer can run `docker compose --profile cli run --rm cli simulate --issue 1`

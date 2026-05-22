# ReleaseGuard

Enterprise AI-assisted release governance platform that evaluates pull requests against configurable risk policies and delivers structured recommendations before code ships.

---

## Problem Statement

Engineering teams at scale struggle to enforce consistent release standards across hundreds of pull requests per day. Manual code review cannot catch every security vulnerability, failing test suite, or policy violation before deployment. ReleaseGuard closes that gap by running an extensible plugin pipeline on every PR, calculating a weighted risk score, and posting an AI-generated summary directly to the pull request — giving reviewers actionable intelligence without adding process overhead.

---

## How It Works

```
GitHub PR event
      |
      v
 POST /webhook
      |
      v
 Verify signature
      |
      v
 Clone repo at PR sha
      |
      v
 Run plugins in parallel
  +-----------+   +-----------+
  | security  |   | test_check|   ... more plugins
  +-----------+   +-----------+
      |               |
      v               v
 PluginResult    PluginResult
      \               /
       \             /
        v           v
     Decision engine
     (weighted score)
            |
            v
     AI summary (GPT-4o-mini)
            |
            v
     Post comment to PR
```

Risk score is the weighted average of all plugin scores (0-100, higher = more risk). The decision engine maps the score to a recommendation: auto-approve, requires review, requires senior review, or block deployment.

---

## Architecture

### Components

| File | Role |
|------|------|
| `app/main.py` | FastAPI app, webhook handler, plugin orchestration, `/demo` and `/health` endpoints |
| `app/decision.py` | Weighted score aggregation, risk level classification, recommendation output |
| `app/ai_summary.py` | Builds GPT-4o-mini prompt from decision data; falls back to plain-text summary if no API key |
| `app/github_client.py` | GitHub REST API client — fetches PR metadata, posts comments, shallow-clones the repo |
| `config.yaml` | Plugin registry with weights and per-plugin config |
| `app/plugins/base.py` | Abstract `BasePlugin` interface, `ReleaseContext`, `PluginResult`, `Finding`, `Severity` |
| `app/plugins/security.py` | Runs Bandit on changed Python files; maps issue severity to a weighted risk score |
| `app/plugins/test_check.py` | Queries GitHub check runs for the PR sha; flags failed or timed-out test suites |

### Plugin System

Each plugin is an async class that extends `BasePlugin` and returns a `PluginResult`. Plugins run in parallel via `asyncio.gather`. Results feed the decision engine, which applies per-plugin weights from `config.yaml`.

### Risk Levels

| Score | Level | Recommendation |
|-------|-------|----------------|
| 0-30 | LOW | Auto-approve |
| 31-60 | MEDIUM | Requires review |
| 61-80 | HIGH | Requires senior review |
| 81-100 | CRITICAL | Block deployment |

---

## Quick Start

### Prerequisites

- Python 3.11+
- `git` available on PATH
- Bandit (`pip install bandit`) for the security plugin

### Install

```bash
git clone <repo-url>
cd releaseguard

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

### Run

```bash
uvicorn app.main:app --reload --port 8000
```

The server starts at `http://localhost:8000`.

---

## Demo

No GitHub token or OpenAI key required for the demo endpoint. It runs the full decision pipeline with pre-built findings and returns structured output.

```bash
curl http://localhost:8000/demo | python -m json.tool
```

### Sample Response

```json
{
  "status": "demo",
  "risk_score": 69.0,
  "risk_level": "high",
  "recommendation": "Requires senior review",
  "plugin_results": [
    {
      "name": "security",
      "score": 75.0,
      "passed": false,
      "findings": [
        {
          "title": "SQL Injection",
          "severity": "high",
          "file": "app/db/queries.py",
          "line": 42,
          "description": "String concatenation in SQL query — use parameterized queries"
        },
        {
          "title": "Hardcoded Secret",
          "severity": "critical",
          "file": "app/config.py",
          "line": 15,
          "description": "API key hardcoded in source — move to environment variable"
        },
        {
          "title": "Weak Hash Algorithm",
          "severity": "medium",
          "file": "app/auth/utils.py",
          "line": 88,
          "description": "MD5 used for password hashing — use bcrypt or argon2"
        }
      ]
    },
    {
      "name": "test_check",
      "score": 60.0,
      "passed": false,
      "findings": [
        {
          "title": "Test Failure: test_user_login",
          "severity": "high",
          "file": "tests/test_auth.py",
          "line": 23,
          "description": "AssertionError — expected 200, got 401. Likely auth regression."
        },
        {
          "title": "Flaky Test: test_payment_timeout",
          "severity": "medium",
          "file": "tests/test_payments.py",
          "line": 156,
          "description": "Intermittent timeout — failed 3 of last 10 runs"
        }
      ]
    }
  ],
  "summary": "ReleaseGuard Analysis — acme-corp/payments-service PR #247\nPR: Add payment processing endpoint\nSHA: a1b2c3d4e5f6\n\nOverall Risk Score : 69.0 / 100\nRisk Level         : HIGH\nRecommendation     : Requires senior review\n..."
}
```

---

## Configuration

`config.yaml` controls which plugins run, their contribution to the overall score, and risk classification thresholds.

```yaml
plugins:
  - name: security
    enabled: true
    weight: 0.6          # 60% of the overall score
    config:
      block_on_critical: true
  - name: test_check
    enabled: true
    weight: 0.4          # 40% of the overall score
    config: {}

risk_thresholds:
  low: 30
  medium: 60
  high: 80

ai_summary:
  enabled: true
  model: gpt-4o-mini
```

**Plugin weight** determines how much each plugin's score contributes to the final weighted average. Weights do not need to sum to 1.0 — the engine normalizes them. To disable a plugin without removing it, set `enabled: false`.

---

## Adding a Plugin

1. Create a file in `app/plugins/`, e.g. `app/plugins/dependency_check.py`.
2. Extend `BasePlugin` and implement `name()` and `evaluate()`.

```python
from .base import BasePlugin, Finding, PluginResult, ReleaseContext, Severity


class DependencyCheckPlugin(BasePlugin):
    def name(self) -> str:
        return "dependency_check"

    async def evaluate(self, context: ReleaseContext) -> PluginResult:
        # context.clone_dir  — path to shallow clone of the repo
        # context.changed_files  — list of file paths changed in the PR
        # context.repo, context.pr_number, context.sha, context.pr_title, context.pr_body

        findings = []

        # ... your analysis logic ...

        # Score: 0 = clean, 100 = maximum risk
        score = len(findings) * 20
        score = min(100.0, score)

        return PluginResult(
            plugin_name=self.name(),
            score=score,
            passed=score < 50,
            findings=findings,
            metadata={"files_checked": len(context.changed_files)},
        )
```

3. Register the plugin in `app/main.py`:

```python
from plugins.dependency_check import DependencyCheckPlugin

PLUGINS = {
    "security": SecurityPlugin(),
    "test_check": TestCheckPlugin(),
    "dependency_check": DependencyCheckPlugin(),   # add this
}
```

4. Add an entry to `config.yaml`:

```yaml
plugins:
  - name: dependency_check
    enabled: true
    weight: 0.3
    config: {}
```

The plugin will be picked up on the next server start.

---

## API Endpoints

### `POST /webhook`

GitHub webhook receiver. Accepts `pull_request` events for actions `opened`, `synchronize`, and `reopened`. All other events and actions are acknowledged and ignored.

**Headers required by GitHub:**
- `x-hub-signature-256` — HMAC-SHA256 of the payload, signed with `WEBHOOK_SECRET`
- `x-github-event: pull_request`

**Response (evaluated):**
```json
{
  "status": "evaluated",
  "risk_score": 69.0,
  "risk_level": "high",
  "recommendation": "Requires senior review"
}
```

### `GET /demo`

Runs the full pipeline with pre-built findings. No GitHub or OpenAI credentials required. Use this to verify the deployment and explore output structure.

### `GET /health`

Liveness check. Returns `{"status": "ok", "version": "0.1.0"}`.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | Personal access token or GitHub App token. Needs `repo` scope to read PR data, post comments, and clone private repositories. |
| `OPENAI_API_KEY` | No | If set, ReleaseGuard generates an AI narrative summary via GPT-4o-mini. If absent, a structured plain-text summary is used instead. |
| `WEBHOOK_SECRET` | Recommended | Secret configured in the GitHub webhook settings. Used to verify payload signatures. If unset, signature verification is skipped (acceptable for local development only). |

Copy `.env.example` to `.env` and fill in values. Load it before starting the server (`export $(cat .env | xargs)` or use `python-dotenv`).

---

## GitHub Webhook Setup

1. In your repository, go to **Settings > Webhooks > Add webhook**.
2. Set **Payload URL** to `https://<your-host>/webhook`.
3. Set **Content type** to `application/json`.
4. Set **Secret** to the value of `WEBHOOK_SECRET`.
5. Select **Pull requests** under individual events.

---

## Roadmap

- **OPA compliance plugin** — enforce organizational policy rules (branch naming, required reviewers, file ownership) via Open Policy Agent Rego rules
- **React dashboard** — real-time view of PR risk scores, plugin results, and historical trends across repositories
- **Audit trail** — persistent log of every evaluation with decision, findings, and the engineer who merged, suitable for compliance reporting
- **Docker + Helm** — containerized deployment with a Helm chart for Kubernetes; environment-based config injection
- **License scanner plugin** — detect dependency license violations before they reach production
- **Secrets detection plugin** — pattern-based scanning for credentials, tokens, and keys in changed files using truffleHog or detect-secrets
- **Slack / Teams notifications** — post risk summaries to team channels in addition to PR comments
- **Custom threshold overrides** — per-repository risk threshold configuration without modifying the global `config.yaml`

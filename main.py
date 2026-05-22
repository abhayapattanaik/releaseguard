import asyncio
import hashlib
import hmac
import os
import tempfile
import shutil

import yaml
from fastapi import FastAPI, Request, HTTPException

from plugins.base import ReleaseContext
from plugins.security import SecurityPlugin
from plugins.test_check import TestCheckPlugin
from decision import make_decision
from ai_summary import generate_summary
import github_client

app = FastAPI(title="ReleaseGuard", version="0.1.0")

# Load config
with open("config.yaml") as f:
    CONFIG = yaml.safe_load(f)

# Plugin registry
PLUGINS = {
    "security": SecurityPlugin(),
    "test_check": TestCheckPlugin(),
}

def verify_signature(payload: bytes, signature: str | None) -> bool:
    """Verify GitHub webhook signature."""
    secret = os.environ.get("WEBHOOK_SECRET")
    if not secret:
        return True  # skip verification if no secret configured
    if not signature:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("x-hub-signature-256")

    if not verify_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("x-github-event")
    if event != "pull_request":
        return {"status": "ignored", "event": event}

    data = await request.json()
    action = data.get("action")
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "ignored", "action": action}

    pr = data["pull_request"]
    repo = data["repository"]["full_name"]
    pr_number = pr["number"]
    sha = pr["head"]["sha"]

    # Get PR details
    pr_info = await github_client.get_pr_info(repo, pr_number)
    changed_files = pr_info.get("changed_files", []) if pr_info else []

    # Clone repo for analysis
    clone_dir = tempfile.mkdtemp(prefix="releaseguard-")
    try:
        await github_client.clone_repo(repo, sha, clone_dir)

        # Build context
        context = ReleaseContext(
            repo=repo,
            pr_number=pr_number,
            sha=sha,
            changed_files=changed_files,
            pr_title=pr.get("title", ""),
            pr_body=pr.get("body", "") or "",
            clone_dir=clone_dir,
        )

        # Run enabled plugins
        enabled_plugins = [
            p for p in CONFIG["plugins"] if p["enabled"]
        ]

        tasks = []
        for plugin_config in enabled_plugins:
            plugin = PLUGINS.get(plugin_config["name"])
            if plugin:
                tasks.append(plugin.evaluate(context))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        plugin_results = [r for r in results if not isinstance(r, Exception)]

        # Calculate decision
        weights = {p["name"]: p["weight"] for p in enabled_plugins}
        decision = make_decision(plugin_results, weights)

        # Generate AI summary
        summary = await generate_summary(decision, context)

        # Post comment to PR
        await github_client.post_comment(repo, pr_number, summary)

        return {
            "status": "evaluated",
            "risk_score": decision.overall_score,
            "risk_level": decision.risk_level,
            "recommendation": decision.recommendation,
        }
    finally:
        shutil.rmtree(clone_dir, ignore_errors=True)


@app.get("/demo")
async def demo():
    """Run full pipeline with realistic fake findings. No tokens needed."""
    from plugins.base import Finding, PluginResult, Severity

    # Simulate security plugin finding SQL injection + hardcoded secret
    security_result = PluginResult(
        plugin_name="security",
        score=75.0,
        passed=False,
        findings=[
            Finding(
                title="SQL Injection",
                description="String concatenation in SQL query — use parameterized queries",
                severity=Severity.HIGH,
                file="app/db/queries.py",
                line=42,
            ),
            Finding(
                title="Hardcoded Secret",
                description="API key hardcoded in source — move to environment variable",
                severity=Severity.CRITICAL,
                file="app/config.py",
                line=15,
            ),
            Finding(
                title="Weak Hash Algorithm",
                description="MD5 used for password hashing — use bcrypt or argon2",
                severity=Severity.MEDIUM,
                file="app/auth/utils.py",
                line=88,
            ),
        ],
    )

    # Simulate test plugin — 2 tests failed
    test_result = PluginResult(
        plugin_name="test_check",
        score=60.0,
        passed=False,
        findings=[
            Finding(
                title="Test Failure: test_user_login",
                description="AssertionError — expected 200, got 401. Likely auth regression.",
                severity=Severity.HIGH,
                file="tests/test_auth.py",
                line=23,
            ),
            Finding(
                title="Flaky Test: test_payment_timeout",
                description="Intermittent timeout — failed 3 of last 10 runs",
                severity=Severity.MEDIUM,
                file="tests/test_payments.py",
                line=156,
            ),
        ],
    )

    # Run decision engine
    weights = {p["name"]: p["weight"] for p in CONFIG["plugins"]}
    decision = make_decision([security_result, test_result], weights)

    # Build fake context
    context = ReleaseContext(
        repo="acme-corp/payments-service",
        pr_number=247,
        sha="a1b2c3d4e5f6",
        changed_files=[
            "app/db/queries.py",
            "app/config.py",
            "app/auth/utils.py",
            "tests/test_auth.py",
        ],
        pr_title="Add payment processing endpoint",
        pr_body="Implements POST /api/payments with Stripe integration",
    )

    # Generate summary (fallback mode — no OpenAI key needed)
    summary = await generate_summary(decision, context)

    return {
        "status": "demo",
        "risk_score": decision.overall_score,
        "risk_level": decision.risk_level.value,
        "recommendation": decision.recommendation,
        "plugin_results": [
            {
                "name": r.plugin_name,
                "score": r.score,
                "passed": r.passed,
                "findings": [
                    {
                        "title": f.title,
                        "severity": f.severity.value,
                        "file": f.file,
                        "line": f.line,
                        "description": f.description,
                    }
                    for f in r.findings
                ],
            }
            for r in decision.plugin_results
        ],
        "summary": summary,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}

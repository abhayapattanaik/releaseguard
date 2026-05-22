import os

import httpx

from .base import BasePlugin, Finding, PluginResult, ReleaseContext, Severity


class TestCheckPlugin(BasePlugin):
    def name(self) -> str:
        return "test_check"

    async def evaluate(self, context: ReleaseContext) -> PluginResult:
        token = os.environ.get("GITHUB_TOKEN", "")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = f"https://api.github.com/repos/{context.repo}/commits/{context.sha}/check-runs"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            return PluginResult(
                plugin_name=self.name(),
                score=20,
                passed=True,
                metadata={"reason": f"github api error: {e}"},
            )

        all_runs = data.get("check_runs", [])
        test_runs = [
            r for r in all_runs if "test" in r.get("name", "").lower()
        ]

        if not test_runs:
            return PluginResult(
                plugin_name=self.name(),
                score=20,
                passed=True,
                metadata={"reason": "no test check runs found"},
            )

        failed = [
            r for r in test_runs
            if r.get("conclusion") in ("failure", "timed_out", "cancelled")
        ]

        if failed:
            findings = [
                Finding(
                    title=f"Test suite failed: {r['name']}",
                    description=f"Check run '{r['name']}' concluded with: {r.get('conclusion')}",
                    severity=Severity.HIGH,
                )
                for r in failed
            ]
            return PluginResult(
                plugin_name=self.name(),
                score=80,
                passed=False,
                findings=findings,
                metadata={
                    "total_test_runs": len(test_runs),
                    "failed_runs": len(failed),
                },
            )

        return PluginResult(
            plugin_name=self.name(),
            score=0,
            passed=True,
            metadata={
                "total_test_runs": len(test_runs),
                "failed_runs": 0,
            },
        )

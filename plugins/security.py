import asyncio
import json
import os
from pathlib import Path

from .base import BasePlugin, Finding, PluginResult, ReleaseContext, Severity

_SEVERITY_MAP = {
    "LOW": Severity.LOW,
    "MEDIUM": Severity.MEDIUM,
    "HIGH": Severity.HIGH,
    "CRITICAL": Severity.CRITICAL,
}

_SCORE_WEIGHT = {
    Severity.LOW: 2,
    Severity.MEDIUM: 10,
    Severity.HIGH: 25,
    Severity.CRITICAL: 50,
}


class SecurityPlugin(BasePlugin):
    def name(self) -> str:
        return "security"

    async def evaluate(self, context: ReleaseContext) -> PluginResult:
        py_files = [f for f in context.changed_files if f.endswith(".py")]

        if not py_files:
            return PluginResult(
                plugin_name=self.name(),
                score=0,
                passed=True,
                metadata={"reason": "no python files changed"},
            )

        if not context.clone_dir:
            return PluginResult(
                plugin_name=self.name(),
                score=0,
                passed=True,
                metadata={"reason": "no clone_dir provided"},
            )

        abs_files = [
            str(Path(context.clone_dir) / f)
            for f in py_files
            if (Path(context.clone_dir) / f).exists()
        ]

        if not abs_files:
            return PluginResult(
                plugin_name=self.name(),
                score=0,
                passed=True,
                metadata={"reason": "changed python files not found in clone_dir"},
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                "bandit",
                "-f", "json",
                "-q",
                *abs_files,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
        except FileNotFoundError:
            return PluginResult(
                plugin_name=self.name(),
                score=0,
                passed=True,
                metadata={"reason": "bandit not installed"},
            )
        except Exception as e:
            return PluginResult(
                plugin_name=self.name(),
                score=0,
                passed=True,
                metadata={"reason": f"bandit error: {e}"},
            )

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return PluginResult(
                plugin_name=self.name(),
                score=0,
                passed=True,
                metadata={"reason": "could not parse bandit output"},
            )

        findings = []
        for issue in data.get("results", []):
            raw_severity = issue.get("issue_severity", "LOW").upper()
            severity = _SEVERITY_MAP.get(raw_severity, Severity.LOW)
            findings.append(
                Finding(
                    title=issue.get("test_id", "unknown"),
                    description=issue.get("issue_text", ""),
                    severity=severity,
                    file=issue.get("filename"),
                    line=issue.get("line_number"),
                )
            )

        raw_score = sum(_SCORE_WEIGHT[f.severity] for f in findings)
        score = min(100.0, raw_score)
        passed = score < 50

        return PluginResult(
            plugin_name=self.name(),
            score=score,
            passed=passed,
            findings=findings,
            metadata={"files_scanned": len(abs_files), "total_issues": len(findings)},
        )

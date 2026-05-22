import asyncio
import json
from pathlib import Path

from .base import BasePlugin, Finding, PluginResult, ReleaseContext, Severity

_SEVERITY_MAP = {
    "ERROR": Severity.CRITICAL,
    "WARNING": Severity.HIGH,
    "INFO": Severity.MEDIUM,
}

_SCORE_WEIGHT = {
    Severity.CRITICAL: 50,
    Severity.HIGH: 25,
    Severity.MEDIUM: 10,
    Severity.LOW: 2,
}


class SecurityPlugin(BasePlugin):
    def name(self) -> str:
        return "security"

    async def evaluate(self, context: ReleaseContext) -> PluginResult:
        if not context.clone_dir:
            return PluginResult(
                plugin_name=self.name(),
                score=0,
                passed=True,
                metadata={"reason": "no clone_dir provided"},
            )

        clone_path = Path(context.clone_dir)
        if not clone_path.exists():
            return PluginResult(
                plugin_name=self.name(),
                score=0,
                passed=True,
                metadata={"reason": "clone_dir does not exist"},
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                "semgrep",
                "scan",
                "--config", "auto",
                "--json",
                str(clone_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
        except FileNotFoundError:
            return PluginResult(
                plugin_name=self.name(),
                score=0,
                passed=True,
                metadata={"reason": "semgrep not installed"},
            )
        except Exception as e:
            return PluginResult(
                plugin_name=self.name(),
                score=0,
                passed=True,
                metadata={"reason": f"semgrep error: {e}"},
            )

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return PluginResult(
                plugin_name=self.name(),
                score=0,
                passed=True,
                metadata={"reason": "could not parse semgrep output"},
            )

        changed_files_set = set(context.changed_files)

        findings = []
        for result in data.get("results", []):
            # Filter to only changed files; semgrep returns paths relative to cwd
            # or absolute — normalise to repo-relative for comparison
            raw_path = result.get("path", "")
            try:
                rel_path = str(Path(raw_path).relative_to(clone_path))
            except ValueError:
                rel_path = raw_path

            if rel_path not in changed_files_set:
                continue

            extra = result.get("extra", {})
            raw_severity = extra.get("severity", "INFO").upper()
            severity = _SEVERITY_MAP.get(raw_severity, Severity.MEDIUM)

            metadata = extra.get("metadata", {})
            cwe = metadata.get("cwe")
            description = extra.get("message", "")
            if cwe:
                description = f"{description} [{cwe}]" if description else str(cwe)

            findings.append(
                Finding(
                    title=result.get("check_id", "unknown"),
                    description=description,
                    severity=severity,
                    file=rel_path,
                    line=result.get("start", {}).get("line"),
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
            metadata={
                "total_semgrep_results": len(data.get("results", [])),
                "filtered_findings": len(findings),
            },
        )

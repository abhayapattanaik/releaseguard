import os

from decision import Decision
from plugins.base import ReleaseContext


def _fallback_summary(decision: Decision, context: ReleaseContext) -> str:
    lines = [
        f"ReleaseGuard Analysis — {context.repo} PR #{context.pr_number}",
        f"PR: {context.pr_title}",
        f"SHA: {context.sha}",
        "",
        f"Overall Risk Score : {decision.overall_score:.1f} / 100",
        f"Risk Level         : {decision.risk_level.value.upper()}",
        f"Recommendation     : {decision.recommendation}",
        "",
        "Plugin Results:",
    ]
    for r in decision.plugin_results:
        status = "PASS" if r.passed else "FAIL"
        lines.append(f"  [{status}] {r.plugin_name}: score={r.score:.1f}")
        for f in r.findings:
            loc = f" ({f.file}:{f.line})" if f.file else ""
            lines.append(f"    - [{f.severity.value.upper()}] {f.title}{loc}: {f.description}")

    return "\n".join(lines)


def _build_prompt(decision: Decision, context: ReleaseContext) -> str:
    findings_text = []
    for r in decision.plugin_results:
        findings_text.append(f"Plugin: {r.plugin_name} | Score: {r.score}/100 | Passed: {r.passed}")
        for f in r.findings:
            loc = f" at {f.file}:{f.line}" if f.file else ""
            findings_text.append(f"  Finding [{f.severity.value}]{loc}: {f.title} — {f.description}")
        if not r.findings:
            findings_text.append("  No findings.")

    findings_block = "\n".join(findings_text) if findings_text else "No findings."

    return f"""You are a senior engineer reviewing a pull request risk assessment.

PR: {context.pr_title}
Repo: {context.repo} | PR #{context.pr_number} | SHA: {context.sha}
Changed files: {", ".join(context.changed_files) or "none"}

PR Description:
{context.pr_body or "(none)"}

Risk Assessment:
Overall Score: {decision.overall_score}/100
Risk Level: {decision.risk_level.value.upper()}
Recommendation: {decision.recommendation}

Plugin Analysis:
{findings_block}

Write a concise plain English summary (3-5 sentences) covering:
1. Overall risk assessment and what's driving it
2. Key findings that engineers should know about
3. Clear recommendation on whether to approve, review, or block
"""


async def generate_summary(decision: Decision, context: ReleaseContext) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return _fallback_summary(decision, context)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": _build_prompt(decision, context)}],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        fallback = _fallback_summary(decision, context)
        return f"{fallback}\n\n[AI summary unavailable: {e}]"

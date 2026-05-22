from dataclasses import dataclass, field

from plugins.base import PluginResult, Severity


@dataclass
class Decision:
    overall_score: float
    risk_level: Severity
    recommendation: str
    plugin_results: list[PluginResult] = field(default_factory=list)


_THRESHOLDS = [
    (30, Severity.LOW, "Auto-approve"),
    (60, Severity.MEDIUM, "Requires review"),
    (80, Severity.HIGH, "Requires senior review"),
    (100, Severity.CRITICAL, "Block deployment"),
]


def make_decision(
    plugin_results: list[PluginResult],
    weights: dict[str, float] | None = None,
) -> Decision:
    """Calculate weighted risk score and return a Decision.

    weights: maps plugin_name -> weight multiplier (default 1.0 for each).
    Final score is the weighted average of plugin scores, clamped to [0, 100].
    """
    if not plugin_results:
        return Decision(
            overall_score=0,
            risk_level=Severity.LOW,
            recommendation="Auto-approve",
            plugin_results=[],
        )

    weights = weights or {}
    total_weight = 0.0
    weighted_sum = 0.0

    for result in plugin_results:
        w = weights.get(result.plugin_name, 1.0)
        weighted_sum += result.score * w
        total_weight += w

    overall_score = weighted_sum / total_weight if total_weight else 0.0
    overall_score = max(0.0, min(100.0, overall_score))

    risk_level = Severity.CRITICAL
    recommendation = "Block deployment"
    for threshold, level, rec in _THRESHOLDS:
        if overall_score <= threshold:
            risk_level = level
            recommendation = rec
            break

    return Decision(
        overall_score=round(overall_score, 2),
        risk_level=risk_level,
        recommendation=recommendation,
        plugin_results=plugin_results,
    )

import pytest
from app.plugins.base import Finding, PluginResult, Severity
from app.decision import make_decision, Decision


class TestMakeDecision:
    def test_empty_results_returns_low_risk(self):
        decision = make_decision([])
        assert decision.overall_score == 0
        assert decision.risk_level == Severity.LOW
        assert decision.recommendation == "Auto-approve"

    def test_single_low_score_plugin(self):
        results = [PluginResult(plugin_name="test", score=20.0, passed=True)]
        decision = make_decision(results)
        assert decision.overall_score == 20.0
        assert decision.risk_level == Severity.LOW

    def test_single_high_score_plugin(self):
        results = [PluginResult(plugin_name="test", score=75.0, passed=False)]
        decision = make_decision(results)
        assert decision.overall_score == 75.0
        assert decision.risk_level == Severity.HIGH
        assert decision.recommendation == "Requires senior review"

    def test_critical_score(self):
        results = [PluginResult(plugin_name="test", score=95.0, passed=False)]
        decision = make_decision(results)
        assert decision.risk_level == Severity.CRITICAL
        assert decision.recommendation == "Block deployment"

    def test_weighted_scoring(self):
        results = [
            PluginResult(plugin_name="security", score=80.0, passed=False),
            PluginResult(plugin_name="tests", score=20.0, passed=True),
        ]
        weights = {"security": 0.6, "tests": 0.4}
        decision = make_decision(results, weights)
        # (80 * 0.6 + 20 * 0.4) / (0.6 + 0.4) = 56.0
        assert decision.overall_score == 56.0
        assert decision.risk_level == Severity.MEDIUM

    def test_equal_weights_is_average(self):
        results = [
            PluginResult(plugin_name="a", score=40.0, passed=True),
            PluginResult(plugin_name="b", score=60.0, passed=False),
        ]
        decision = make_decision(results)
        assert decision.overall_score == 50.0

    def test_score_clamped_to_100(self):
        results = [PluginResult(plugin_name="test", score=150.0, passed=False)]
        decision = make_decision(results)
        assert decision.overall_score == 100.0

    def test_score_clamped_to_0(self):
        results = [PluginResult(plugin_name="test", score=-10.0, passed=True)]
        decision = make_decision(results)
        assert decision.overall_score == 0.0

    def test_plugin_results_preserved_in_decision(self):
        results = [
            PluginResult(plugin_name="sec", score=50.0, passed=True, findings=[
                Finding(title="XSS", description="reflected XSS", severity=Severity.HIGH, file="app.py", line=10)
            ]),
        ]
        decision = make_decision(results)
        assert len(decision.plugin_results) == 1
        assert len(decision.plugin_results[0].findings) == 1
        assert decision.plugin_results[0].findings[0].title == "XSS"

    def test_boundary_score_30_is_low(self):
        results = [PluginResult(plugin_name="test", score=30.0, passed=True)]
        decision = make_decision(results)
        assert decision.risk_level == Severity.LOW

    def test_boundary_score_31_is_medium(self):
        results = [PluginResult(plugin_name="test", score=31.0, passed=True)]
        decision = make_decision(results)
        assert decision.risk_level == Severity.MEDIUM

    def test_boundary_score_60_is_medium(self):
        results = [PluginResult(plugin_name="test", score=60.0, passed=False)]
        decision = make_decision(results)
        assert decision.risk_level == Severity.MEDIUM

    def test_boundary_score_61_is_high(self):
        results = [PluginResult(plugin_name="test", score=61.0, passed=False)]
        decision = make_decision(results)
        assert decision.risk_level == Severity.HIGH

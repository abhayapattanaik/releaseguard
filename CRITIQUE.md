# ReleaseGuard — Honest Critique

## 1. Risk Score Lacks Calibration
Weights (0.6 security, 0.4 tests) are arbitrary. No ML model, no historical data backing them. A real platform would train on past deployment failures or at minimum let teams calibrate from their own incident data.

## 2. AI Summary Is Reformatting
Current AI usage: feed structured findings to GPT, get English paragraph back. The structured output is already readable. Real AI value would be root cause analysis — correlating test failures with specific code changes, predicting blast radius.

## 3. Demo Relies on Fake Data
/demo endpoint uses hardcoded findings. Proves the pipeline works but doesn't prove the evaluators work. Need a sample vulnerable repo that triggers real Semgrep findings for a convincing live demo.

## 4. No Scale Story
Single FastAPI process, synchronous evaluation within request. 50 concurrent PRs would queue up. Production needs async workers (Celery/Redis), request queuing, and webhook retry handling.

## 5. Competing with GitHub Native Features
GitHub already offers CodeQL (free SAST), Dependabot (dependency vulns), required status checks, and branch protection rules. ReleaseGuard must clearly articulate what it adds beyond these — the aggregation and risk scoring layer.

## 6. OPA Integration Is Roadmap Only
Policy-as-code is listed as a key differentiator but not built yet. Zero Rego files in the repo. Until it exists, the enterprise governance claim is aspirational.

## 7. Limited Test Coverage
13 unit tests for the decision engine only. No tests for plugins, AI summary, GitHub client, or webhook handler. Integration tests would strengthen the quality engineering story.

## 8. No Docker/Deployment Story
No Dockerfile, no docker-compose, no Helm chart. "Enterprise platform" without containerized deployment is incomplete. One-command local setup (docker compose up) would dramatically improve first impression.

## 9. Single-Tenant Design
No concept of organizations, teams, or per-repo configuration. Enterprise deployment means multi-tenancy. Current design serves one team on one instance.

## 10. Interview Risk Areas
Likely questions and current weak answers:
- "How does the risk model work?" — Configurable weights, but no data-driven calibration
- "How does this scale?" — Single process, needs async workers
- "What happens when the LLM hallucinates?" — No validation of AI output
- "How is this different from GitHub's built-in tools?" — Aggregation layer argument needs sharpening

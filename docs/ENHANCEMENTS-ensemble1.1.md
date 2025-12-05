# Ensemble 1.1 — Minimal observability and CI smoke checks

Summary
-------

Ensemble 1.1 focuses on small, additive changes which improve observability, reduce operational unknowns, and provide a safe path to validate runtime behavior via CI smoke tests. The goal is to avoid any behavioral or algorithmic changes to trading logic, and to keep all edits low risk and easy to review.

What was implemented (and why it helps)
-------------------------------------

- core/config.py (added)
  - What: Small helper exposing strategy_id and schema_version using environment variables with safe defaults.
  - Why: Centralized and explicit source of strategy metadata makes emitted logs consistent across processes and easier to identify.
  - Why in 1.1: Low-risk, non-functional addition that helps monitoring without changing behavior.

- ops/log_emitter.py (patched)
  - What: Injects `strategy_id` and `schema_version` metadata into all emitted JSON events.
  - Why: Makes logs self-describing and easier to trace back to a running strategy/version.
  - Why in 1.1: Non-invasive metadata only — no algorithmic change.

- ops/heartbeat.py (added)
  - What: Lightweight heartbeat writer which writes a short heartbeat file for basic monitoring.
  - Why: Provides a simple indicator that a bot process started and is active; useful for operations and CI smoke checks.
  - Why in 1.1: Very low-risk observability improvement.

- start_project.py (patched)
  - What: Emits an initial, non-blocking startup heartbeat so processes are visible to monitoring / smoke checks in early startup.
  - Why: Guarantees a heartbeat is written on startup so CI / operators can detect a running process quickly.
  - Why in 1.1: Small boot-time hook only; safe and useful.

- tests/test_heartbeat_and_emitters.py (added)
  - What: Hermetic unit tests that exercise heartbeat writes and metadata injection.
  - Why: Keeps the change safe and verifiable by CI / maintainers.

- .github/workflows/ensemble1.1-smoke.yml (added)
  - What: CI workflow that runs the small unit tests on pushes and PRs for the ensemble1.1 branch.
  - Why: Enables automated verification of the new observability features without running the entire test suite.

- scripts/validate_emitted_records.py (added)
  - What: CLI that scans emitted JSONL logs and enforces required telemetry fields such as `strategy_id`/`schema_version`.
  - Why: Running it in `--strict` mode inside CI ensures telemetry regressions fail fast; developers can point it at freshly generated logs to reproduce locally.

Remaining (recommended) items for 1.1
-------------------------------------

These are small, low-risk items that are good fits for a 1.1 release if you'd like to include them:

- Add a lightweight CI smoke step to verify the presence of heartbeat files at runtime (e.g., integration smoke harness).  (Planned: small script + workflow job)
- Add a short README snippet/README section documenting where heartbeat files and logs live (paper_trading_outputs/logs/... ) and how to run the smoke tests locally.
- Add a permissive but useful JSON schema validator for emitted records (optional strict-mode for CI in later 1.1 patch).

Deferred / out of scope for 1.1
--------------------------------

- Large refactors (tests across many timeframe packages, overlay rollup redesign, algorithmic changes) — target for 1.2 or later.

Notes about safety
------------------

Everything added in 1.1 is additive and non-destructive: metadata in emitted records is added without changing existing fields and heartbeats are separate files intended only for monitoring.

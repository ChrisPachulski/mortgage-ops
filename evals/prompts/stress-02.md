---
id: stress-02
mode: stress
description: TBD — 50-scenario rate-shock requiring stress-test-agent dispatch; oracle deferred until Phase 13+ adds a transcript-fixture-driven oracle for subagent invocations.
numeric_status: skip
defer_until_phase: "13.0"
expected_numbers: []
expected_route_keywords:
  - stress
  - stress_test.py
  - stress-test-agent
expected_scripts:
  - script: stress_test.py
    args_must_include: ["--input"]
---

I have a $400,000 mortgage application at 6.5%. Run a 50-scenario rate-shock
sweep from 4% to 9% in 0.1% increments. Summarize the affordability cliff
and tell me the worst-case monthly P&I. SUBA-05 routing rule: this MUST
dispatch to stress-test-agent (>5 scenarios).

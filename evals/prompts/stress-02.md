---
id: stress-02
mode: stress
description: 51-scenario rate-shock sweep from 4.0% to 9.0% in 0.1% increments on $400k/30yr loan. Dispatched via stress-test-agent (>5 scenarios per SUBA-05). Engine-derived 2026-05-23 via stress_test.py — baseline 6.5% = $2,528.27, worst-case 9.0% = $3,218.49.
expected_route_keywords:
  - stress
  - stress_test.py
  - stress-test-agent
expected_scripts:
  - script: stress_test.py
    args_must_include: ["--input"]
expected_numbers:
  - label: baseline_monthly_pi_at_6_5pct
    value: "2528.27"
    tolerance: "0.005"
    source_script: stress_test.py
    provenance: stdout
  - label: worst_case_monthly_pi_at_9pct
    value: "3218.49"
    tolerance: "0.01"
    source_script: stress_test.py
    provenance: stdout
---

I have a $400,000 mortgage application at 6.5%. Run a 50-scenario rate-shock
sweep from 4% to 9% in 0.1% increments. Summarize the affordability cliff
and tell me the worst-case monthly P&I. SUBA-05 routing rule: this MUST
dispatch to stress-test-agent (>5 scenarios).

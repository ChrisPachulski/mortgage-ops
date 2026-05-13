---
id: stress-01
mode: stress
description: Rate-shock at $400k/30yr baseline 6.0%; row at 6.5% pins to CONVENTIONS.md $2528.27 (Phase 8 STRS-01 anchor).
expected_route_keywords:
  - stress
  - stress_test.py
expected_scripts:
  - script: stress_test.py
    args_must_include: ["--input"]
expected_numbers:
  - label: monthly_pi_at_6_5pct
    value: "2528.27"
    tolerance: "0.005"
    source_script: stress_test.py
    provenance: stdout
---

I have a $400,000 mortgage application at 6.0% / 30yr baseline. Run a
rate-shock sweep across 6.0%, 6.5%, 7.0%, 7.5%, and 8.0% so I can see how
sensitive my monthly P&I is to rate changes. Note that ≤5-cell sweeps run
inline (not via the stress subagent).

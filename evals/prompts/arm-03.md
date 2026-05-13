---
id: arm-03
mode: arm
description: TBD — 5/6 SOFR ARM with 6-month reset cadence; oracle deferred until Phase 13+ ships AmericU SOFR cross-validated fixture (Phase 5 D-08 Wave 6).
numeric_status: skip
defer_until_phase: "13.0"
expected_numbers: []
expected_route_keywords:
  - arm
  - arm_simulate.py
expected_scripts:
  - script: arm_simulate.py
    args_must_include: ["--input"]
---

I'm offered a 5/6 SOFR ARM at $400k, 5.875% initial, 30yr term, with caps
1/1/5 and margin 2.75%. Reset cadence is every 6 months. Compare total
interest to a 30-year fixed at 6.5%.

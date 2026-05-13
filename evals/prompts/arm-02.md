---
id: arm-02
mode: arm
description: TBD — 5/1 ARM full-horizon schedule with periodic + lifetime caps; oracle deferred until Phase 13+ extends Phase 5 ARM fixtures.
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

Simulate a 5/1 ARM at $400k, 5.5% initial, 30yr term, 2/2/5 caps (initial cap
2%, periodic cap 2%, lifetime cap 5%), margin 2.75%, with an index path that
rises 100bps per year for the first 5 reset years then stabilizes. Report
total interest and final balance.

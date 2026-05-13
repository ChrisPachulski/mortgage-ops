---
id: stress-03
mode: stress
description: TBD — ARM-reset rate-path sweep (parallel-shift, gradual-rise, fall-then-rise); oracle deferred until Phase 13+ ships a 3-path total-interest fixture.
numeric_status: skip
defer_until_phase: "13.0"
expected_numbers: []
expected_route_keywords:
  - stress
  - stress_test.py
expected_scripts:
  - script: stress_test.py
    args_must_include: ["--input"]
---

For a 5/1 ARM at $400,000, 6.0% initial / 30yr term, simulate three rate paths
over the full 30-year horizon: (1) parallel-shift +200bps at month 60,
(2) gradual-rise +25bps every reset, (3) fall-then-rise -100bps at month 60
then +300bps at month 120. Report total-interest for each path.

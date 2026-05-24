---
id: arm-02
mode: arm
description: 5/1 ARM full-horizon schedule with 2/2/5 caps and a +100bps/yr index rise through year 5 then stabilize. Engine-derived 2026-05-23 via arm_simulate.py against $400k @ 5.5% initial, margin 2.75%, assumed_index 5.0%, index_path stepping 6%/7%/8%/9% at periods 61/73/85/97 and holding through term.
expected_route_keywords:
  - arm
  - arm_simulate.py
expected_scripts:
  - script: arm_simulate.py
    args_must_include: ["--input"]
expected_numbers:
  - label: initial_period_monthly_pi
    value: "2271.16"
    tolerance: "0.01"
    source_script: arm_simulate.py
    provenance: stdout
  - label: total_interest
    value: "616697.48"
    tolerance: "0.50"
    source_script: arm_simulate.py
    provenance: stdout
---

Simulate a 5/1 ARM at $400k, 5.5% initial, 30yr term, 2/2/5 caps (initial cap
2%, periodic cap 2%, lifetime cap 5%), margin 2.75%, with an index path that
rises 100bps per year for the first 5 reset years then stabilizes. Report
total interest and final balance.

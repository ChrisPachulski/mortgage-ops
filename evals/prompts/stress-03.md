---
id: stress-03
mode: stress
description: ARM-reset 3-path total-interest sweep on 5/1 ARM ($400k, 6.0% initial, 30yr, 5/2/5 caps, margin 2.5%, assumed_index 5.0%). Engine-derived 2026-05-23 via stress_test.py arm-reset paths — parallel-shift +200bps = $719,508.17, gradual-rise +25bps/reset = $720,666.78, fall-then-rise (-100 then +300bps) = $584,695.22.
expected_route_keywords:
  - stress
  - stress_test.py
expected_scripts:
  - script: stress_test.py
    args_must_include: ["--input"]
expected_numbers:
  - label: parallel_shift_total_interest
    value: "719508.17"
    tolerance: "0.50"
    source_script: stress_test.py
    provenance: stdout
  - label: gradual_rise_total_interest
    value: "720666.78"
    tolerance: "0.50"
    source_script: stress_test.py
    provenance: stdout
  - label: fall_then_rise_total_interest
    value: "584695.22"
    tolerance: "0.50"
    source_script: stress_test.py
    provenance: stdout
---

For a 5/1 ARM at $400,000, 6.0% initial / 30yr term, simulate three rate paths
over the full 30-year horizon: (1) parallel-shift +200bps at month 60,
(2) gradual-rise +25bps every reset, (3) fall-then-rise -100bps at month 60
then +300bps at month 120. Report total-interest for each path.

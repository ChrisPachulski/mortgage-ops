---
id: arm-01
mode: arm
description: 5/1 ARM initial-period monthly P&I — $400k at 6.0% initial, 5yr / 1yr reset (Phase 5 + Phase 8 engine-actual anchor).
expected_route_keywords:
  - arm
  - arm_simulate.py
expected_scripts:
  - script: arm_simulate.py
    args_must_include: ["--input"]
expected_numbers:
  - label: initial_period_monthly_pi
    value: "2398.20"
    tolerance: "0.01"
    source_script: arm_simulate.py
    provenance: stdout
---

I'm considering a 5/1 ARM at $400,000, 6.0% initial rate, 30-year amortization.
What's the monthly P&I during the initial 5-year fixed period?

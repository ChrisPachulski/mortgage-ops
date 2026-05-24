---
id: arm-03
mode: arm
description: 5/6 SOFR ARM with 6-month reset cadence and 1/1/5 caps. Engine-derived 2026-05-23 via arm_simulate.py against $400k @ 5.875% initial, margin 2.75%, reset_period_months=6, assumed_index 5.0%, no explicit index_path (engine uses assumed_index post-initial-period).
expected_route_keywords:
  - arm
  - arm_simulate.py
expected_scripts:
  - script: arm_simulate.py
    args_must_include: ["--input"]
expected_numbers:
  - label: initial_period_monthly_pi
    value: "2366.15"
    tolerance: "0.01"
    source_script: arm_simulate.py
    provenance: stdout
  - label: total_interest
    value: "582015.18"
    tolerance: "0.50"
    source_script: arm_simulate.py
    provenance: stdout
---

I'm offered a 5/6 SOFR ARM at $400k, 5.875% initial, 30yr term, with caps
1/1/5 and margin 2.75%. Reset cadence is every 6 months. Compare total
interest to a 30-year fixed at 6.5%.

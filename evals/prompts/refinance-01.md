---
id: refinance-01
mode: refinance
description: Rate-and-term refi positive-NPV scenario (Phase 6 positive_npv_200bps_drop_2k_costs.json).
expected_route_keywords:
  - refinance
  - refi_npv.py
expected_scripts:
  - script: refi_npv.py
    args_must_include: ["--input"]
expected_numbers:
  - label: npv
    value: "60705.48"
    tolerance: "0.01"
    source_script: refi_npv.py
    provenance: stdout
---

I have a $300,000 mortgage at 7.0% / 25-year remaining term. A new lender
offers 5.0% / 25yr with $2,000 in closing costs and I'd use a 5% discount
rate. Should I refinance? Compute the NPV from my (borrower) perspective.

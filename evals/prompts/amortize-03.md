---
id: amortize-03
mode: amortize
description: CFPB LE oracle amortization — $162k @ 3.875%/30yr.
expected_route_keywords:
  - amortize
  - amortize.py
expected_scripts:
  - script: amortize.py
    args_must_include: ["--input"]
expected_numbers:
  - label: monthly_pi
    value: "761.78"
    tolerance: "0.005"
    source_script: amortize.py
    provenance: stdout
---

Amortize a $162,000 mortgage at 3.875% fixed for 30 years (this matches the
CFPB Loan Estimate worked example). What's the monthly P&I?

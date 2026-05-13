---
id: evaluate-02
mode: evaluate
description: Single-loan evaluation — $400k conforming 30yr at 6.5% (CONVENTIONS.md anchor).
expected_route_keywords:
  - evaluate
  - amortize.py
expected_scripts:
  - script: amortize.py
    args_must_include: ["--input"]
expected_numbers:
  - label: monthly_pi
    value: "2528.27"
    tolerance: "0.005"
    source_script: amortize.py
    provenance: stdout
---

Evaluate a $400,000 mortgage at 6.5% fixed for 30 years. I want the exact
monthly P&I and a sanity check that it's within conforming limits.

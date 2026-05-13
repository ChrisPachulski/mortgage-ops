---
id: evaluate-01
mode: evaluate
description: Single-loan evaluation — $200k conforming 30yr at 6.5% (Wikipedia oracle).
expected_route_keywords:
  - evaluate
  - amortize.py
expected_scripts:
  - script: amortize.py
    args_must_include: ["--input"]
expected_numbers:
  - label: monthly_pi
    value: "1264.14"
    tolerance: "0.005"
    source_script: amortize.py
    provenance: stdout
---

I'm evaluating a $200,000 mortgage at 6.5% fixed for 30 years. What's my
monthly principal-and-interest payment, and is this a typical conforming loan?

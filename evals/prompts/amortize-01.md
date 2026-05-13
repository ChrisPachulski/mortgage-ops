---
id: amortize-01
mode: amortize
description: Full amortization schedule — Wikipedia oracle ($200k @ 6.5%/30yr).
expected_route_keywords:
  - amortize
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

Generate a full amortization schedule for a $200,000 loan at 6.5% fixed for
30 years. Show me the monthly P&I and verify the final balance hits exactly $0.

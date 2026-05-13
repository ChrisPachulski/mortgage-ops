---
id: amortize-02
mode: amortize
description: 15-year amortization — computed $200k @ 7%/15yr oracle.
expected_route_keywords:
  - amortize
  - amortize.py
expected_scripts:
  - script: amortize.py
    args_must_include: ["--input"]
expected_numbers:
  - label: monthly_pi
    value: "1797.66"
    tolerance: "0.005"
    source_script: amortize.py
    provenance: stdout
---

Run a 15-year fixed amortization on $200,000 at 7%. I want the monthly P&I
and the total interest paid over the life of the loan.

---
id: evaluate-03
mode: evaluate
description: Single-loan evaluate with estimated-APR reporting. Engine-derived 2026-05-23 from $400k @ 6.5%/30yr + $5,000 finance charges. apr_reg_z.py emits estimated APR; amortize.py emits monthly P&I = $2,528.27 (CONVENTIONS.md hand-calc oracle).
expected_route_keywords:
  - evaluate
  - apr_reg_z.py
  - amortize.py
  - "estimated APR"
expected_scripts:
  - script: apr_reg_z.py
    args_must_include: ["--input"]
  - script: amortize.py
    args_must_include: ["--input"]
expected_numbers:
  - label: monthly_pi
    value: "2528.27"
    tolerance: "0.005"
    source_script: amortize.py
    provenance: stdout
---

Evaluate a $400,000 mortgage at 6.5% nominal rate for 30 years with $5,000 in
finance charges. Tell me the estimated APR and the monthly P&I.

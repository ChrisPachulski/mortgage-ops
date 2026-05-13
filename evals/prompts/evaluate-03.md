---
id: evaluate-03
mode: evaluate
description: TBD — single-loan evaluation with estimated-APR reporting; oracle deferred until Phase 13+ ships a Reg Z worked-example anchor.
numeric_status: skip
defer_until_phase: "13.0"
expected_numbers: []
expected_route_keywords:
  - evaluate
  - apr_reg_z.py
expected_scripts:
  - script: apr_reg_z.py
    args_must_include: ["--input"]
---

Evaluate a $400,000 mortgage at 6.5% nominal rate for 30 years with $5,000 in
finance charges. Tell me the estimated APR and the monthly P&I.

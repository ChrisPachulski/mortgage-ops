---
id: affordability-03
mode: affordability
description: Forward affordability — VA loan blocked by DTI cap (back-end DTI 0.534 > 0.43 max_dti). Engine-derived 2026-05-23 from $450k VA loan @ 6.25%/30yr, $8k/mo income, $1.5k monthly debts, WA WEST family-4. blocked_by='DTI-CAP-VA' surfaces in stdout per Phase 2 D-11 citation format.
expected_route_keywords:
  - affordability
  - affordability.py
  - blocked_by
expected_scripts:
  - script: affordability.py
    args_must_include: ["--input"]
expected_numbers:
  - label: monthly_pi
    value: "2770.73"
    tolerance: "0.005"
    source_script: affordability.py
    provenance: stdout
---

A West-Coast 4-person household earning $8,000 / month gross with $1,500 in
monthly debts wants a $450,000 VA loan at 6.25% / 30yr. Will VA residual
income allow this? If blocked, name the binding regulatory citation.

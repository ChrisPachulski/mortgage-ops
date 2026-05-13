---
id: affordability-01
mode: affordability
description: Forward affordability — single applicant $10k/mo income, $400k conforming target, 6.5%/30yr (Phase 4 anchor).
expected_route_keywords:
  - affordability
  - affordability.py
expected_scripts:
  - script: affordability.py
    args_must_include: ["--input"]
expected_numbers:
  - label: monthly_pi
    value: "2528.27"
    tolerance: "0.005"
    source_script: affordability.py
    provenance: stdout
---

A single-applicant household earns $10,000 / month gross. They want to buy a
$500,000 home with a $400,000 conforming mortgage at 6.5% / 30yr. Compute
front-end and back-end DTI and tell me if they qualify under standard QM rules.

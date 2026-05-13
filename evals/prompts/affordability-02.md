---
id: affordability-02
mode: affordability
description: Reverse affordability — max loan at 43% DTI cap, $10k/mo income, conforming 7%/30yr (Phase 4 round-trip anchor).
expected_route_keywords:
  - affordability
  - affordability.py
expected_scripts:
  - script: affordability.py
    args_must_include: ["--input"]
expected_numbers:
  - label: max_loan_amount
    value: "646322.54"
    tolerance: "0.01"
    source_script: affordability.py
    provenance: stdout
---

A two-applicant household earns $10,000 / month gross combined with $0 in
monthly debts. What's the max loan amount they can qualify for at a 43% back-end
DTI cap with a conforming 30-year fixed at 7%, assuming an 80% LTV target?

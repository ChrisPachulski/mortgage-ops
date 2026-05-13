---
id: affordability-03
mode: affordability
description: TBD — VA-residual-income blocker scenario; oracle deferred until Phase 13+ ships a green VA fixture that exercises the blocker_by citation path (Phase 4 has blocked_by tests but the prompt-driven citation flow needs a new fixture).
numeric_status: skip
defer_until_phase: "13.0"
expected_numbers: []
expected_route_keywords:
  - affordability
  - affordability.py
  - blocked_by
expected_scripts:
  - script: affordability.py
    args_must_include: ["--input"]
---

A West-Coast 4-person household earning $8,000 / month gross with $1,500 in
monthly debts wants a $450,000 VA loan at 6.25% / 30yr. Will VA residual
income allow this? If blocked, name the binding regulatory citation.

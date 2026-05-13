---
id: compare-03
mode: compare
description: TBD — 3-way comparison including a refi candidate; oracle deferred until Phase 13+ ships ranked-NPV table fixture.
numeric_status: skip
defer_until_phase: "13.0"
expected_numbers: []
expected_route_keywords:
  - compare
  - refi_npv.py
  - amortize.py
expected_scripts:
  - script: refi_npv.py
    args_must_include: ["--input"]
---

I have my current $400k @ 6.5% / 30yr (24 months in) and three refi offers:
(A) 5.875% / $3,200 cc, (B) 5.750% / $5,800 cc, (C) 6.000% / $2,400 cc.
Rank them by NPV and tell me which to pick.

---
id: compare-03
mode: compare
description: 3-way refi-NPV ranking against $400k @ 6.5%/30yr 24 months in (current balance $390,758.85, 336 months remaining). Engine-derived 2026-05-23 via refi_npv.py for each offer at 5% discount rate, full-term horizon. Offer B (5.75%, $5.8k cc) wins.
expected_route_keywords:
  - compare
  - refi_npv.py
  - amortize.py
expected_scripts:
  - script: refi_npv.py
    args_must_include: ["--input"]
expected_numbers:
  - label: offer_a_npv
    value: "37182.13"
    tolerance: "0.01"
    source_script: refi_npv.py
    provenance: stdout
  - label: offer_b_npv
    value: "40381.08"
    tolerance: "0.01"
    source_script: refi_npv.py
    provenance: stdout
  - label: offer_c_npv
    value: "32149.65"
    tolerance: "0.01"
    source_script: refi_npv.py
    provenance: stdout
---

I have my current $400k @ 6.5% / 30yr (24 months in) and three refi offers:
(A) 5.875% / $3,200 cc, (B) 5.750% / $5,800 cc, (C) 6.000% / $2,400 cc.
Rank them by NPV and tell me which to pick.

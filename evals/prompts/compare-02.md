---
id: compare-02
mode: compare
description: Compare CFPB LE oracle ($162k @ 3.875%/30yr) vs Wikipedia ($200k @ 6.5%/30yr).
expected_route_keywords:
  - compare
  - amortize.py
expected_scripts:
  - script: amortize.py
    args_must_include: ["--input"]
expected_numbers:
  - label: offer_a_monthly_pi
    value: "761.78"
    tolerance: "0.005"
    source_script: amortize.py
    provenance: stdout
  - label: offer_b_monthly_pi
    value: "1264.14"
    tolerance: "0.005"
    source_script: amortize.py
    provenance: stdout
---

I have two offers on different houses: (A) $162,000 at 3.875% / 30yr, and
(B) $200,000 at 6.5% / 30yr. Which has the lower monthly payment, and by
how much?

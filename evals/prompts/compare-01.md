---
id: compare-01
mode: compare
description: Compare $400k 30yr at 6.5% vs $200k 15yr at 7% (CONVENTIONS.md two-oracle pair).
expected_route_keywords:
  - compare
  - amortize.py
expected_scripts:
  - script: amortize.py
    args_must_include: ["--input"]
expected_numbers:
  - label: offer_a_monthly_pi
    value: "2528.27"
    tolerance: "0.005"
    source_script: amortize.py
    provenance: stdout
  - label: offer_b_monthly_pi
    value: "1797.66"
    tolerance: "0.005"
    source_script: amortize.py
    provenance: stdout
---

Compare two mortgage offers: (A) $400,000 at 6.5% for 30 years, and
(B) $200,000 at 7% for 15 years. What's each monthly P&I and which makes
more sense if my budget is $2,800/month?

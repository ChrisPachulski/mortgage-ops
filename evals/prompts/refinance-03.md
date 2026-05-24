---
id: refinance-03
mode: refinance
description: Rate-and-term refi with discount-rate sensitivity sweep at 3%/5%/7%; 3-year horizon makes NPV negative across all three rates (closing costs not recovered). Engine-derived 2026-05-23 via refi_npv.py against $300k @ 6.25%/30yr → 6.0%/30yr, $6k closing, 36-month horizon. Discount-rate-invariant numerics (old/new monthly P&I + monthly_savings) anchor the pin; NPV varies (-4332.26 / -4381.76 / -4429.26) and is narrated qualitatively.
expected_route_keywords:
  - refinance
  - refi_npv.py
expected_scripts:
  - script: refi_npv.py
    args_must_include: ["--input"]
expected_numbers:
  - label: old_monthly_pi
    value: "1847.15"
    tolerance: "0.01"
    source_script: refi_npv.py
    provenance: stdout
  - label: new_monthly_pi
    value: "1798.65"
    tolerance: "0.01"
    source_script: refi_npv.py
    provenance: stdout
  - label: monthly_savings
    value: "48.50"
    tolerance: "0.01"
    source_script: refi_npv.py
    provenance: stdout
---

I have a $300k mortgage at 6.25% / 30yr. A lender offers 6.0% / 30yr with
$6,000 in closing costs. Is this worth it if I plan to sell in 3 years?
Try multiple discount-rate assumptions (3%, 5%, 7%).

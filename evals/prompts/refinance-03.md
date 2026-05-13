---
id: refinance-03
mode: refinance
description: TBD — negative-NPV scenario with discount-rate sensitivity analysis; oracle deferred until Phase 13+ extends Phase 6 negative_npv fixture with discount-rate sweep.
numeric_status: skip
defer_until_phase: "13.0"
expected_numbers: []
expected_route_keywords:
  - refinance
  - refi_npv.py
expected_scripts:
  - script: refi_npv.py
    args_must_include: ["--input"]
---

I have a $300k mortgage at 6.25% / 30yr. A lender offers 6.0% / 30yr with
$6,000 in closing costs. Is this worth it if I plan to sell in 3 years?
Try multiple discount-rate assumptions (3%, 5%, 7%).

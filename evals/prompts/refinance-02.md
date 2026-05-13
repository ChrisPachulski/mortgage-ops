---
id: refinance-02
mode: refinance
description: TBD — cash-out refi; oracle deferred until Phase 13+ ships a richer cash-out fixture (Phase 6 has cash_out_proceeds_50k but the deal terms here are different).
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

I owe $250,000 on a $500,000 house and want to do a cash-out refi for $350,000
at 6.0% / 30yr with $4,500 in closing costs. Compute the NPV and tell me the
cash proceeds after closing costs.

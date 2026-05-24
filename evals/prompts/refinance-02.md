---
id: refinance-02
mode: refinance
description: "Cash-out refi — $250k owed on $500k house, refi to $350k at 6.0%/30yr, $4.5k closing costs, 5% discount, full-term horizon. Engine-derived 2026-05-23 via refi_npv.py: NPV $25,295.25, cash_proceeds $95,500.00 (cash_out_amount $100k minus closing $4,500)."
expected_route_keywords:
  - refinance
  - refi_npv.py
expected_scripts:
  - script: refi_npv.py
    args_must_include: ["--input"]
expected_numbers:
  - label: npv
    value: "25295.25"
    tolerance: "0.01"
    source_script: refi_npv.py
    provenance: stdout
  - label: cash_proceeds
    value: "95500.00"
    tolerance: "0.01"
    source_script: refi_npv.py
    provenance: stdout
---

I owe $250,000 on a $500,000 house and want to do a cash-out refi for $350,000
at 6.0% / 30yr with $4,500 in closing costs. Compute the NPV and tell me the
cash proceeds after closing costs.

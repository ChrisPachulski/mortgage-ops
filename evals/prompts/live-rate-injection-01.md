---
id: live-rate-injection-01
mode: evaluate
description: SC-1 closure eval — borrower asks current 30-yr rate; skill reads fixture cache (D-12-SC1-01).
expected_route_keywords:
  - data/cache/fred_MORTGAGE30US.json
  - "6.50"
expected_scripts: []
expected_numbers:
  - label: current_30yr_rate
    value: "6.50"
    tolerance: "0.01"
    source_script: fixture_cache
    provenance: static
---

What's the current 30-year fixed mortgage rate? I want to anchor my budgeting
on today's typical rate, not last year's.

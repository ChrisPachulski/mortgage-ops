---
id: property-analysis-01
mode: property
description: Full property analysis end-to-end — SFH conforming King County WA against synthetic Phase 11 D-02 fixture (sfh_conforming_001.json). Closes ROADMAP SC-6. No live WebFetch in CI per Phase 11 D-02 + Phase 12 contract; replay-stub mode injects FRED rates via the fixture wrapper's fred_rates block.
expected_route_keywords:
  - property
  - property_analyze.py
  - "WATCH"
expected_scripts:
  - script: property_analyze.py
    args_must_include:
      - "--listing"
      - "--household"
      - "--profile"
      - "--output-dir"
expected_numbers:
  - label: conv30_preferred_dp_piti
    value: "3760.34"
    tolerance: "0.50"
    source_script: property_analyze.py
    provenance: stdout
  - label: first_year_interest_conv30
    value: "32335.43"
    tolerance: "0.50"
    source_script: property_analyze.py
    provenance: stdout
  - label: verdict_reasons_count
    value: "3.0"
    tolerance: "0.0"
    source_script: property_analyze.py
    provenance: stdout
---

Analyze this Zillow listing for me: https://www.zillow.com/homedetails/synthetic/1_zpid/

---
phase: 16
slug: reference-data
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-22
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 9.0 (already installed; `pyproject.toml` line 20) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_rules/test_pmi.py tests/test_rules/test_insurance.py -x` |
| **Full suite command** | `uv run pytest tests/` |
| **Citation coverage gate** | `uv run pytest tests/test_rules/test_citation_coverage.py` |
| **Estimated runtime** | ~1s quick run; ~60s full suite (645+ tests) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (~1s)
- **After every plan wave:** `uv run pytest tests/test_rules/ tests/test_property_analysis.py tests/test_property_verdict.py -x` (~6-10s)
- **Before `/gsd-verify-work`:** Full suite green (645+ tests)
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

> Populated by gsd-planner from RESEARCH.md Validation Architecture; refined per-task during planning. Task ID format: `{phase}-{plan}-{taskN}`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | REF-09 | — | property-analysis-heuristics.yml loads w/ source+effective | unit | `uv run pytest tests/test_rules/test_pmi.py::test_yaml_loads_with_metadata -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REF-09 | — | PMI lookup correct for FICO 760 × LTV 95 in-band | unit | `uv run pytest tests/test_rules/test_pmi.py::test_lookup_in_band_760_95 -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REF-09 | — | PMI lookup caps for FICO 680 × LTV 96 out-of-band + tag | unit | `uv run pytest tests/test_rules/test_pmi.py::test_lookup_out_of_band_caps -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REF-09 | — | PMI module citation/source/effective in docstring | meta | `uv run pytest tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring[pmi] -x` | ✅ (auto-discover) | ⬜ pending |
| TBD | TBD | 0 | REF-09 | — | PMI ≥1 fixture file under tests/fixtures/rules/pmi_*.json | meta | `uv run pytest tests/test_rules/test_citation_coverage.py::test_predicate_has_at_least_one_fixture[pmi] -x` | ✅ (auto-discover) | ⬜ pending |
| TBD | TBD | 0 | REF-10 | — | insurance-estimate-defaults.yml loads w/ source+effective | unit | `uv run pytest tests/test_rules/test_insurance.py::test_yaml_loads_with_metadata -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REF-10 | — | State base lookup correct for WA | unit | `uv run pytest tests/test_rules/test_insurance.py::test_lookup_state_base_wa -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REF-10 | — | Composition: state + flood multiplier + earthquake (WA × X) | unit | `uv run pytest tests/test_rules/test_insurance.py::test_composition_wa_zone_x -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REF-10 | T-V5 | Earthquake silent-zero for non-CA/OR/WA | unit | `uv run pytest tests/test_rules/test_insurance.py::test_earthquake_silent_zero_for_other_state -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REF-10 | — | Insurance module citation hygiene | meta | `uv run pytest tests/test_rules/test_citation_coverage.py::test_predicate_has_citation_in_docstring[insurance] -x` | ✅ (auto-discover) | ⬜ pending |
| TBD | TBD | 2 | REF-09+10 | — | Phase 14 full regression green after wire-in | integration | `uv run pytest tests/test_property_analysis.py tests/test_property_verdict.py -x` | ✅ (re-anchor) | ⬜ pending |
| TBD | TBD | 2 | REF-09 | — | test_conv_pmi_warning_surfaces passes with new tag pattern | unit | `uv run pytest tests/test_property_analysis.py::test_conv_pmi_warning_surfaces -x` | ✅ (assertion update) | ⬜ pending |
| TBD | TBD | 2 | REF-09 | — | test_analyze_warnings_dedup_pmi_estimated passes | unit | `uv run pytest tests/test_property_analysis.py::test_analyze_warnings_dedup_pmi_estimated -x` | ✅ (label update) | ⬜ pending |
| TBD | TBD | 0 | REF-09+10 | — | Module imports work | smoke | `uv run python -c "from lib.rules.pmi import lookup_rate; from lib.rules.insurance import lookup_default, fips_to_usps"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_rules/test_pmi.py` — REF-09 stubs (yaml-loads, in-band, out-of-band-capped, citation hygiene)
- [ ] `tests/test_rules/test_insurance.py` — REF-10 stubs (yaml-loads, state-base, composition, silent-zero, citation hygiene)
- [ ] `tests/fixtures/rules/pmi_*.json` — ≥5 hand-calc anchored fixture files (one per representative cell + capped)
- [ ] `tests/fixtures/rules/insurance_*.json` — ≥3 fixture files (WA+X baseline, CA+AE high-risk, TX+unknown non-quake)
- [ ] `data/reference/property-analysis-heuristics.yml` — placeholder schema (PMI 4×4); real values populated in dedicated task
- [ ] `data/reference/insurance-estimate-defaults.yml` — placeholder schema (51 states + 4 flood + 3 quake); real values populated in dedicated task
- [ ] `lib/rules/pmi.py` — predicate module skeleton with required docstring header + `lookup_rate()`
- [ ] `lib/rules/insurance.py` — predicate module skeleton with required docstring + `lookup_default()` + `fips_to_usps()` + `_FIPS_TO_USPS` constant

*No new framework install needed — pytest 9.x already shipped.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MGIC Rate Card bulletin pinned + archived | REF-09 | MGIC bulletin PDFs are gated/404. Must be manually captured by planner at YAML-write time. | Download from mgic.com/rate-cards; archive in `.planning/sources/`; pin form-number + revision date in YAML notes. |
| NAIC report version + CA/TX exclusion documented | REF-10 | NAIC's latest is "Data for 2022" published 2025-05-21; CA + TX systematically excluded. Mixed-provenance per-row. | Cite NAIC for 49 covered states + DC; cite III for CA + TX in row-level notes; per-row source URL allowed. |
| Flood-zone uplift source documented per Risk Rating 2.0 | REF-10 | FEMA Risk Rating 2.0 (2021-04) decoupled NFIP premium from FIRM zones. Cannot cite FEMA NFIP as source. | Cite "v1.1 representative private-market estimate" with the specific carrier filing or actuarial study used as the basis. |
| CA/OR/WA earthquake add-on values sourced | REF-10 | CEA published averages for CA; OR + WA non-CEA from private market — no single canonical source. | CEA for CA; PNW carrier filing or state insurance dept survey for OR/WA. Pin source URLs per row. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

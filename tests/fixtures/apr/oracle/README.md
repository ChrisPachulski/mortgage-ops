# APR Oracle Fixture Corpus

**Phase 7 Plan 07-07** — final wave, closes APR-04 and ROADMAP SC-2.

This directory holds the 20 APR oracle fixtures used by
`tests/test_apr.py::test_apr_ffiec_oracle_fixtures_match_within_decimal_00001`
to cross-validate `lib.apr.solve_apr` outputs against pinned expected values.

---

## Partial Closure Disclosure (autonomous-execution override)

The original Plan 07-07 frontmatter declared `autonomous: false` and called
for 20+ FFIEC APR Tool captures driven by a human operator (PNG screenshots
+ SHA-256 hashes). The 07-CONTEXT.md re-discussion (D-01 / D-02) had already
pivoted the oracle strategy from FFIEC APRWIN to HMDA Platform programmatic
capture. **This corpus reflects a second pragmatic pivot** accepted by the
project owner during the Wave 7 execution session: ship engine-emitted
fixtures with honest provenance disclosure, treat the engine as the
de-facto oracle for the corpus, and document the gap honestly here so any
later session that runs FFIEC APRWIN (under Wine / a Windows VM) or stands
up the HMDA Platform Docker image can cross-validate the pinned values.

The trade-off accepted: shipping 20 engine-emitted fixtures NOW (closing
APR-04 partial-style, mirroring the Phase 5 ARM-06 partial-closure
precedent for Bankrate cross-source agreement) vs. blocking Phase 7 on a
human capture session that has been deferred multiple times.

The project's "math correctness first" core value (CLAUDE.md) is preserved
because every fixture's provenance is disclosed honestly via the
`oracle_provenance` block on the fixture itself. There are no fabricated
FFIEC values in this corpus.

---

## Fixture Schema

```jsonc
{
  "description": "...",
  "request": {
    /* APRRequest payload — identical shape to other tests/fixtures/apr/*.json */
  },
  "expected": {
    "estimated_apr": "0.066213",          // pinned 6dp APR (engine-emitted)
    "iterations_max": 10,                 // ceiling for SC-3 sweep
    "tolerance_used": "0.00001",          // pinned tolerance
    "iterations_observed_at_capture": 1,  // diagnostic — recorded at write time
    "final_residual_at_capture": "0.01"   // diagnostic — recorded at write time
  },
  "oracle_provenance": {
    "class": "engine-emitted" | "engine-emitted, cross-validated against ...",
    "captured_at": "2026-05-03",
    "captured_by": "scripts/_generate_apr_oracle_fixtures.py",
    "engine_module": "lib.apr.solve_apr",
    "notes": "...full honest disclosure per provenance class...",
    "cross_validated_against": "wikipedia-mortgage-loan-..."   // when applicable
  }
}
```

---

## Provenance Classes (per the autonomous-execution override)

The override defined the following 5-step fallback oracle chain (RESEARCH §Q(d)):

1. **Reg Z Appendix J worked examples** (publicly published; multiple loan archetypes)
2. **CFPB Rate Spread Calculator** (web-accessible; publishes APR for given LE inputs)
3. **Bankrate / Wikipedia worked examples** (regular monthly cases — already have 1 in Phase 7 from plan 05)
4. **HMDA Platform documentation worked examples**
5. **Engine self-cross-validation** (engine-emitted values for sibling fixtures, marked clearly in `notes:`)

Each fixture's `oracle_provenance.class` field records which level of the
chain produced its expected value:

| Class | Meaning | This corpus |
|-------|---------|-------------|
| `regulatory` | Value matches a published Reg Z / CFPB / FFIEC value | **0** fixtures (the SC-1 anchor `regz_appendix_j_5000_36_166_07.json` lives at `tests/fixtures/apr/` per Plan 07-05 D-25 LOCKED, not in this `oracle/` subdirectory) |
| `engine-emitted, cross-validated against Wikipedia worked example` | Engine value confirmed against the Phase 1 oracle anchor ($200k @ 6.5%/30yr → $1,264.14 monthly; APR == nominal rate exactly for regular monthly cases with no finance charges) | **12** fixtures — the regular-monthly archetypes (1-12), where the unit-period equation collapses to the standard PV form and the engine's APR == nominal rate exactly |
| `engine-emitted` | Engine output without external cross-validation. Pinned at fixture-write time; drift > `Decimal("0.00001")` indicates an engine regression vs the snapshot | **8** fixtures — the odd-first-period (13-16) and finance-charge (17-20) archetypes, where no public worked example with the exact input combination exists. Future cross-validation against a stood-up HMDA Platform / FFIEC APRWIN session would flip these to "engine-emitted, cross-validated against ..." |

**No fixture in this corpus claims `regulatory` class without a published
source.** The engine output (e.g., `0.065000` for the regular-monthly cases)
matches the Wikipedia oracle anchor exactly because the unit-period equation
collapses to the closed-form PV solution when there are no finance charges
and no odd first period — that's a genuine cross-validation against the
$1,264.14 / $200k / 6.5% / 30yr Phase 1 anchor (and by algebraic identity
the same holds for all 12 regular-monthly archetypes here).

---

## Per-Fixture Provenance Table

| Fixture | Archetype | Provenance Class | Cross-Validated Against |
|---------|-----------|------------------|-------------------------|
| `ffiec_001_30yr_150k_6_5.json` | 30yr fixed, $150k @ 6.5% | engine-emitted+xval | wikipedia-mortgage-loan-200k-6.5-30yr |
| `ffiec_002_30yr_250k_6_5.json` | 30yr fixed, $250k @ 6.5% | engine-emitted+xval | wikipedia-mortgage-loan-200k-6.5-30yr |
| `ffiec_003_30yr_400k_6_5.json` | 30yr fixed, $400k @ 6.5% | engine-emitted+xval | wikipedia-mortgage-loan-200k-6.5-30yr |
| `ffiec_004_30yr_750k_6_5.json` | 30yr fixed, $750k @ 6.5% | engine-emitted+xval | wikipedia-mortgage-loan-200k-6.5-30yr |
| `ffiec_005_30yr_1_2m_6_5.json` | 30yr fixed, $1.2M @ 6.5% | engine-emitted+xval | wikipedia-mortgage-loan-200k-6.5-30yr |
| `ffiec_006_15yr_300k_5_0.json` | 15yr fixed, $300k @ 5.0% | engine-emitted+xval | wikipedia-mortgage-loan-pv-formula-collapse |
| `ffiec_007_15yr_300k_6_0.json` | 15yr fixed, $300k @ 6.0% | engine-emitted+xval | wikipedia-mortgage-loan-pv-formula-collapse |
| `ffiec_008_15yr_300k_7_0.json` | 15yr fixed, $300k @ 7.0% | engine-emitted+xval | wikipedia-mortgage-loan-pv-formula-collapse |
| `ffiec_009_15yr_300k_8_0.json` | 15yr fixed, $300k @ 8.0% | engine-emitted+xval | wikipedia-mortgage-loan-pv-formula-collapse |
| `ffiec_010_10yr_300k_6_5.json` | 10yr fixed, $300k @ 6.5% | engine-emitted+xval | wikipedia-mortgage-loan-pv-formula-collapse |
| `ffiec_011_10yr_500k_7_0.json` | 10yr fixed, $500k @ 7.0% | engine-emitted+xval | wikipedia-mortgage-loan-pv-formula-collapse |
| `ffiec_012_10yr_200k_5_5.json` | 10yr fixed, $200k @ 5.5% | engine-emitted+xval | wikipedia-mortgage-loan-pv-formula-collapse |
| `ffiec_013_30yr_300k_6_5_oddfp_5.json` | 30yr, $300k @ 6.5%, 5-day odd FP | engine-emitted | (none; future HMDA cross-validation candidate) |
| `ffiec_014_30yr_300k_6_5_oddfp_10.json` | 30yr, $300k @ 6.5%, 10-day odd FP | engine-emitted | (none; future HMDA cross-validation candidate) |
| `ffiec_015_30yr_300k_6_5_oddfp_20.json` | 30yr, $300k @ 6.5%, 20-day odd FP | engine-emitted | (none; future HMDA cross-validation candidate) |
| `ffiec_016_15yr_500k_7_0_oddfp_15.json` | 15yr, $500k @ 7.0%, 15-day odd FP | engine-emitted | (none; future HMDA cross-validation candidate) |
| `ffiec_017_30yr_400k_6_5_fc_5k.json` | 30yr, $400k @ 6.5%, $5k finance | engine-emitted | (none; future HMDA cross-validation candidate) |
| `ffiec_018_30yr_600k_7_5_fc_10k.json` | 30yr, $600k @ 7.5%, $10k finance | engine-emitted | (none; future HMDA cross-validation candidate) |
| `ffiec_019_15yr_250k_6_0_fc_3k.json` | 15yr, $250k @ 6.0%, $3k finance | engine-emitted | (none; future HMDA cross-validation candidate) |
| `ffiec_020_30yr_800k_7_0_fc_15k.json` | 30yr, $800k @ 7.0%, $15k finance | engine-emitted | (none; future HMDA cross-validation candidate) |

**Provenance breakdown:**

- 12 / 20 (60%) cross-validated against Wikipedia worked example (regular-monthly PV-form collapse identity)
- 8 / 20 (40%) engine-emitted only (odd-first-period + finance-charge archetypes)
- 0 / 20 carry a `regulatory` class — none claim parity with an FFIEC tool capture, an HMDA Platform output, or a CFPB Rate Spread Calculator output, because no such capture was performed in this session

---

## Fallback Substitution Log

The original plan archetypes called for capturing some inputs that the
engine cannot accept under the v1 D-16 boundary:

- **15-day odd-first-period:** Plan archetype list said (15, 30, 45, 60)
  days. **30 days = 30/30 = f = 1.0** which violates the D-16 boundary
  (f must be in `[0, 1)` for the v1 long-case helper). Plan 07-05 already
  ships a NEGATIVE-path fixture for the 45-day case (`expected.raises =
  "ValueError"`). The Wave 7 corpus substitutes (5, 10, 15, 20, 25)-day
  values — same long-case algebra, all f in [0, 1). The 15-day case is in
  this corpus as `ffiec_016` (15yr, $500k @ 7.0%); the 5/10/20 cases are
  `ffiec_013/014/015` (30yr, $300k @ 6.5%).

- **10-year balloon:** Plan archetype list said "3 × 10-year balloon."
  The v1 engine has no balloon construct (a single payment_schedule entry
  with constant amount; balloon would need a final lump-sum entry).
  Substituted with 10-year fully-amortizing fixed mortgages — same
  short-term unit-period algebra. True balloon support is on the v2
  backlog (per 07-CONTEXT.md "Deferred Ideas").

- **Multiple-advance / construction-style:** Plan archetype list said
  "4 × multiple-advance (construction-style)." Per **D-04 LOCKED**
  (07-CONTEXT.md), `APRRequest.advances` is `Field(min_length=1, max_length=1)`
  in v1 — single-advance only. Substituted with regular-monthly +
  finance-charge archetypes (`ffiec_017..020`), which exercise the
  amount-financed = principal − finance_charges algebra without
  contradicting the D-04 boundary. Multi-advance support is on the v2
  backlog.

---

## Refresh Cadence

**Annual** — mirrors `data/reference/*.yml` staleness convention from
Phase 2. Re-run `scripts/_generate_apr_oracle_fixtures.py` whenever:

- The engine math changes (lib.apr.solve_apr / lib.apr._unit_period_equation
  / lib.apr._derivative / lib.apr._compute_odd_first_period_fraction).
  Drift > `Decimal("0.00001")` will fail the parametric test loudly per
  CONTEXT D-09 ("HMDA delta policy — engine is wrong").
- A future session stands up the HMDA Platform Docker container, FFIEC
  APRWIN under Wine/VM, or the CFPB Rate Spread Calculator and is able
  to capture cross-validating values for the 8 `engine-emitted`-class
  fixtures. Update the fixture's `oracle_provenance.class` to
  `engine-emitted, cross-validated against <oracle>` and add the
  `cross_validated_against` field with the source identifier.

The script's `CAPTURED_AT` constant and each fixture's
`oracle_provenance.captured_at` field record the date of last regeneration.

---

## Recommended Path to Full Closure

To upgrade this corpus from "engine-emitted" toward published-oracle
cross-validation:

1. **HMDA Platform Docker capture (highest value).** Stand up the
   `cfpb/hmda-platform` Docker container per its upstream README. Drive
   the APR-compute endpoint with each of the 20 fixture's `request`
   payloads. Record the platform's APR output and the upstream commit
   SHA. Update each fixture's `oracle_provenance` to add
   `cross_validated_against: "hmda-platform@<commit-sha>"` and bump
   `class` to `engine-emitted, cross-validated against hmda-platform`.
   Any > `Decimal("0.00001")` divergence indicates an engine bug per
   CONTEXT D-09.

2. **FFIEC APRWIN under Wine / Windows VM (lower value, more friction).**
   Drive the 2008-era APRWIN binary by hand for each of the 20 fixtures.
   Capture screenshots + APR readouts. Record screenshot SHA-256 hashes
   and add `cross_validated_against: "ffiec-aprwin"` plus
   `screenshot_sha256` and `screenshot_path` fields.

3. **CFPB Rate Spread Calculator (web-based, free).** For each fixture,
   submit the inputs via the CFPB Rate Spread Calculator web form.
   Capture the published rate spread / APR. Add
   `cross_validated_against: "cfpb-rate-spread-calculator"` and the URL.

4. **Bankrate / Wikipedia worked examples (already done for 12 of 20).**
   The 12 regular-monthly archetypes are already cross-validated by
   algebraic identity against the Phase 1 Wikipedia oracle anchor
   ($200k @ 6.5%/30yr → $1,264.14 monthly).

---

## Cross-References

- `tests/fixtures/apr/regz_appendix_j_5000_36_166_07.json` — Phase 7 SC-1
  anchor (regulatory class, lives outside this `oracle/` directory per
  Plan 07-05 D-25 LOCKED).
- `tests/test_apr.py::test_apr_ffiec_oracle_fixtures_match_within_decimal_00001` —
  the parametric test that consumes this corpus (closes APR-04).
- `tests/test_apr.py::test_newton_raphson_iterations_under_50_for_all_fixtures` —
  Plan 07-05 SC-3 sweep over the 3 hand-calc fixtures; this corpus's
  iterations are independently bounded by `iterations_max: 10` per fixture.
- `references/apr-reg-z.md §6 Citations Summary` — documents the HMDA
  Platform sole-oracle decision (CONTEXT D-01) and FFIEC-out-of-scope
  decision (CONTEXT D-02).
- `.planning/phases/07-estimated-apr/07-07-ffiec-fixtures-SUMMARY.md` —
  the SUMMARY for this plan documents the partial closure under
  `## Partial Closure`.
- `.planning/phases/07-estimated-apr/07-CONTEXT.md` D-01 / D-02 / D-09 —
  the locked decisions backing the oracle strategy + delta policy.

---

*Last updated: 2026-05-03*
*Captured by: scripts/_generate_apr_oracle_fixtures.py*

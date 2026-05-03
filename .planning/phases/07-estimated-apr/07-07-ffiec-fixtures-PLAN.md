---
phase: 07
plan: 07
type: execute-with-human-checkpoint
wave: 7
depends_on: ["07-06"]
files_modified:
  - tests/fixtures/apr/oracle/ffiec_001_30yr_400k_6_5.json
  - tests/fixtures/apr/oracle/ffiec_002_..  # ≥20 total
  - tests/fixtures/apr/oracle/README.md
  - tests/test_apr.py
autonomous: false  # human checkpoint — FFIEC capture
requirements: [APR-04]
tags:
  - phase-07
  - estimated-apr
  - ffiec-oracle
  - human-checkpoint
must_haves:
  truths:
    - "≥20 FFIEC oracle fixtures shipped under tests/fixtures/apr/oracle/"
    - "Each fixture pair includes (a) JSON request + expected_apr (b) screenshot SHA-256 hash + capture URL"
    - "tests/fixtures/apr/oracle/README.md documents the capture protocol + fallback substitution log"
    - "Wave 0 stub test_apr_ffiec_oracle_fixtures_match_within_decimal_00001 flips to PASS (parametric over all 20+)"
    - "All 20+ fixtures pass solver validation within Decimal('0.00001')"
  artifacts:
    - path: "tests/fixtures/apr/oracle/ffiec_*.json (≥20 files)"
      provides: "FFIEC APR Tool capture corpus per ROADMAP SC-2"
    - path: "tests/fixtures/apr/oracle/README.md"
      provides: "Capture protocol + per-fixture provenance + fallback substitutions"
    - path: "tests/fixtures/apr/oracle/screenshots/ (≥20 files)"
      provides: "PNG/PDF screenshots of FFIEC tool with SHA-256-pinned hashes"
---

## Goal

Capture 20+ FFIEC APR Tool oracle fixtures spanning the input feature
space (loan amount, term, rate, advance schedule, finance charges,
day-count, odd first period). Flip the final Wave 0 stub
`test_apr_ffiec_oracle_fixtures_match_within_decimal_00001`. Mirrors
Phase 5 Plan 05-06 oracle capture pattern.

**HUMAN CHECKPOINT:** This wave requires manual interaction with the
FFIEC APR Tool (or fallback substitute). The agent CANNOT run this wave
fully autonomously; it MUST pause for human capture, then resume to
write fixtures + flip the stub.

## Tasks

### Task 1 — Pause for human capture

Print to operator:

```
Phase 7 Wave 7 requires manual FFIEC APR Tool capture.

Tool URL (primary): https://www.ffiec.gov/aprwin.htm
Fallback URLs (per RESEARCH §Q(d) if primary unreachable):
  - https://ffiec.cfpb.gov/tools/rate-spread (web-based)
  - https://www.consumerfinance.gov/owning-a-home/loan-estimate/
  - https://www.bankrate.com/mortgages/mortgage-apr-calculator/

Capture 20 input scenarios spanning the feature space:
  - 5 × 30-year fixed at varying loan amounts ($150k, $250k, $400k, $750k, $1.2M)
  - 4 × 15-year fixed at varying rates (5%, 6%, 7%, 8%)
  - 3 × 10-year balloon
  - 4 × odd-first-period (15, 30, 45, 60 days)
  - 4 × multiple-advance (construction-style)

For each: enter inputs, capture screenshot (PNG or PDF), note APR result
to 6 decimal places. Save screenshots to:
  tests/fixtures/apr/oracle/screenshots/ffiec_001_<descr>.png
  ...

Then re-invoke this plan with --resume to ingest the captures.
```

### Task 2 — On resume, generate fixture JSON files from captures

For each captured screenshot, write a JSON fixture:

```json
{
  "description": "FFIEC capture #001 — 30-year fixed, $400k, 6.5%",
  "request": {
    "loan": {"principal": "400000.00", "annual_rate": "0.065000", "term_months": 360, "loan_type": "fixed"},
    "finance_charges": "5000.00",
    "advance_schedule": [{"unit_period_offset": 0, "amount": "400000.00"}],
    "payment_schedule": [{"starting_unit_period": 1, "periods": 360, "amount": "2528.27"}],
    "day_count": "30/360",
    "unit_periods_per_year": 12,
    "odd_first_period_days": 0
  },
  "expected": {
    "estimated_apr": "0.066123",
    "captured_at": "2026-05-02",
    "ffiec_tool_url": "https://www.ffiec.gov/aprwin.htm",
    "screenshot_path": "tests/fixtures/apr/oracle/screenshots/ffiec_001_30yr_400k_6_5.png",
    "screenshot_sha256": "<computed via shasum -a 256>",
    "tolerance_used": "0.00001"
  }
}
```

### Task 3 — Write `tests/fixtures/apr/oracle/README.md`

Document:
- Capture protocol (which tool, which inputs, when captured, by whom)
- Per-fixture provenance table
- Fallback substitution log (if FFIEC primary unreachable, document
  which substitute was used per fixture, why, and the URL)
- Refresh cadence (annual, mirroring `data/reference/*.yml` staleness
  convention from Phase 2)

### Task 4 — Add parametric per-fixture coverage

```python
@pytest.mark.parametrize("stem", [
    f"oracle/ffiec_{i:03d}_..." for i in range(1, 21)  # 20+ fixtures
])
def test_apr_ffiec_oracle_fixtures_match_within_decimal_00001(
    apr_fixture: Callable[[str], dict[str, Any]],
    stem: str,
) -> None:
    """APR-04 + ROADMAP SC-2: every FFIEC capture passes within Decimal('0.00001')."""
    from lib.apr import APRRequest, solve_apr
    fix = apr_fixture(stem)
    request = APRRequest.model_validate(fix["request"])
    response = solve_apr(request)
    expected = Decimal(fix["expected"]["estimated_apr"])
    diff = abs(response.estimated_apr - expected)
    assert diff <= Decimal("0.00001"), \
        f"FFIEC oracle {stem}: expected {expected}, got {response.estimated_apr} (diff {diff})"
    # SC-3 sanity: also confirm iterations <= 50 for irregular FFIEC schedules
    assert response.iterations <= 50, \
        f"FFIEC oracle {stem} required {response.iterations} iterations (cap=50)"
```

Remove the Wave 0 single-stub xfail; the parametric replacement covers it.

### Task 5 — Fallback substitution if FFIEC unreachable

Mirror Phase 5 BLOCKER-1 pattern (MGIC swap for Bankrate). If FFIEC
primary URL is unreachable:

1. Document the unavailability in `tests/fixtures/apr/oracle/README.md`.
2. Substitute fixtures from CFPB Rate Spread / Bankrate / HMDA Platform.
3. Each substituted fixture's `ffiec_tool_url` field becomes
   `"<substitute-url> (FFIEC primary unreachable; substituted per Plan 07-07 §Task 5)"`.
4. Flag for `/gsd-discuss-phase` re-entry on the substitution to ratify
   the swap as a LOCKED DECISION (mirrors Phase 5 D-04 swap from MGIC
   to Bankrate after BLOCKER-1).

### Task 6 — Cap-bound fixtures get hand_calc_check witness

Per orchestrator brief: "format as JSON with hand_calc_check witness for
any whose APR is cap-bound." If any FFIEC capture happens to have an APR
that the lender's tool labels as cap-bound (e.g., max APR from a
floor-rate constraint), the fixture includes:

```json
{
  ...,
  "expected": {
    "estimated_apr": "0.099000",
    "hand_calc_check": {
      "method": "hand-verified U-equation evaluation at i=0.0825 monthly",
      "residual_at_expected_apr": "0.0001",
      "verifier_initials": "<operator>",
      "witnessed_at": "2026-05-02"
    },
    ...
  }
}
```

Mirrors Phase 5 D-04 [REVISED] cap-bound fixture pattern.

## Acceptance

- ≥20 fixture files in `tests/fixtures/apr/oracle/ffiec_*.json`
- `tests/fixtures/apr/oracle/README.md` exists with capture-protocol §
- `pytest tests/test_apr.py::test_apr_ffiec_oracle_fixtures_match_within_decimal_00001 -v` PASSES (≥20 parametric cases)
- All 13 Wave 0 stubs now flipped (zero xfails remaining for APR-XX)
- `pytest -q 2>&1 | tail -5` shows ≥432 + ≥25 passed (Phase 5 + Phase 7 full surface)
- mypy + ruff clean

## LOCKED DECISIONS

- **D-31:** ≥20 FFIEC fixtures is the hard floor (ROADMAP SC-2 + APR-04).
  If FFIEC primary tool yields fewer than 20, fall back per §Task 5; if
  fallback also fails to reach 20, document and flag for human re-discuss.
- **D-32:** Each fixture pins a SHA-256 of the captured screenshot. Future
  re-verification (annual cadence) compares hashes; mismatch triggers
  re-capture.
- **D-33:** Cap-bound fixtures (where the lender's tool returns an APR
  that hits a floor/ceiling rather than the actuarial value) get a
  `hand_calc_check` witness. Mirrors Phase 5 D-04 [REVISED] pattern.
- **D-34:** Phase 7 ships even if Wave 7 lands fewer than 20 fixtures —
  partial closure of APR-04 is acceptable per Phase 5 precedent (ARM-06
  partial → 5/1 cross-source deferred to Phase 8). Document any partial
  closure in `.planning/STATE.md` for parent rollup.

## Verify Block

```bash
cd /Users/cujo253/Documents/mortgage-ops
ls tests/fixtures/apr/oracle/ffiec_*.json | wc -l   # expect ≥20
ls tests/fixtures/apr/oracle/screenshots/ | wc -l   # expect ≥20
cat tests/fixtures/apr/oracle/README.md | head -20
pytest tests/test_apr.py -v --tb=no 2>&1 | tail -30
pytest -q 2>&1 | tail -5
```

## Deviation Rules

- Rule-1: <20 fixtures captured → partial-closure documented in SUMMARY +
  STATE.md; do NOT silently lower the parametric count.
- Rule-2: any captured value disagreeing with engine by >Decimal("0.00001")
  → STOP and investigate. Likely causes: (a) day-count mismatch (FFIEC
  using 365 vs engine 360); (b) finance-charges classification difference;
  (c) odd-first-period definition difference.
- Rule-3: hygiene only.

## Cross-wave Dependency Notes

- **Upstream:** Waves 0-6 (full engine + CLI + references doc).
- **Downstream:** none. Wave 7 is the final Phase 7 wave.
- **External:** FFIEC APR Tool deliverability (RISK; see RESEARCH OPEN Q4).
  If unreachable, fall back per §Task 5 + flag for human re-discuss.
- APR-04 fully closed by this wave (or partial-closed and documented).

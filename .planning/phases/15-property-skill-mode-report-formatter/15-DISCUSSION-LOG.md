# Phase 15 Discussion Log

**Date:** 2026-05-20
**Phase:** 15 — `property` Skill Mode + Report Formatter
**Mode:** default (4 gray areas, multi-question turns)

---

## Areas Discussed

User selected all 4 areas via multiSelect:
1. Mode routing precedence
2. YOUR FIT matrix layout
3. Citation footer placement
4. Orchestrator input shape + eval fixture

---

## Area 1: Mode routing precedence

### Q1.1 — URL-pin priority position in SKILL.md precedence table

**Options presented:**
- Top of table (Recommended) — `zillow.com` overrides everything, even explicit slash-commands
- Below explicit slash-commands — slash-command wins, then `zillow.com` overrides keyword routing
- Below explicit + refinance verb — refi verb wins over zillow.com

**User selected:** Top of table

**Rationale captured:** URL is load-bearing; if the user pasted it, the listing context is more valuable than the verb. Even `/mortgage-ops refinance <URL>` should route to property.

### Q1.2 — Bare "analyze listing" phrase routing

**Options presented:**
- Same row as zillow.com (Recommended) — combined trigger
- Below keyword routing — treated like other keyword triggers
- Only with URL present — drop bare phrase as trigger

**User selected:** Same row as zillow.com

**Rationale captured:** Phase 15 SC-1 wording supports the combined trigger. Claude follows up asking for URL when only the phrase is present.

---

## Area 2: YOUR FIT matrix layout

### Q2.1 — Matrix orientation

**Options presented:**
- Rows = Program, Cols = DP% (Recommended)
- Rows = DP%, Cols = Program
- Two tables, one per axis

**User selected:** Rows = Program, Cols = DP%

### Q2.2 — Cell content

**Options presented:**
- PITI + eligible flag (Recommended) — `$X,XXX/mo ✓` or `$X,XXX/mo ✗ (BLOCKER-CODE)`
- PITI only, ineligible cells = em-dash
- Full numerics (PITI / DTI / LTV / cash-to-close)

**User selected:** PITI + eligible flag

### Q2.3 — Ineligible cell rendering

**Options presented:**
- Render all cells, mark ineligible (Recommended)
- Filter ineligible rows entirely
- Two sections: eligible + ineligible

**User selected:** Render all cells, mark ineligible

**Rationale captured:** D-14-MATRIX-02 spent compute populating ineligible numerics — actionable for the user ("why don't I qualify here").

---

## Area 3: Citation footer placement

### Q3.1 — Footer granularity

**Options presented:**
- Per section (Recommended) — 6 footers total
- Per table — ~6-8 footers
- Per row — 50+ footers
- Single footer at report bottom — 1 footer

**User selected:** Per section

### Q3.2 — Footer target (orchestrator vs primitives)

**Options presented:**
- Orchestrator only (Recommended) — always cite `scripts/property_analyze.py`
- Per-block primitive citation — `scripts/amortize.py` for YOUR FIT, etc.
- Both — orchestrator + primitive list appendix

**User selected:** Orchestrator only

**Rationale captured:** Phase 14 composes primitives in-process; citing per-primitive would mislead because the user can't re-run a primitive standalone and get the matrix back.

---

## Area 4: Orchestrator input shape + eval fixture

### Q4.1 — `scripts/property_analyze.py` input contract

**Options presented:**
- JSON file only (Recommended) — `--listing path.json --household path.yml --profile path.yml`
- URL or JSON (dual mode)
- URL only

**User selected:** JSON file only

**Rationale captured:** Clean separation, no network in script, Phase 12 D-12-LIVE02-01 honored.

### Q4.2 — Eval fixture location + content type

**Options presented:**
- `evals/fixtures/property/` + extracted JSON (Recommended)
- `evals/fixtures/property/` + sanitized Zillow HTML
- `tests/fixtures/property_report/` + JSON (co-locate with Phase 14 fixtures)

**User selected:** `evals/fixtures/property/` + extracted JSON

**Rationale captured:** Phase 11 D-02 PII risk minimized by synthetic-only; tests the analysis→format pipeline; pair with tiny synthetic HTML smoke fixture for extraction recipe.

### Q4.3 — Oracle pins for eval

**Options presented:**
- Conv30 @ preferred-DP PITI + verdict reason count + tax first-year-interest (Recommended)
- Eligible-program count + total matrix cells + verdict level (coarse)
- All 30 matrix PITI values + verdict reasons (exhaustive)

**User selected:** Conv30 PITI + verdict reason count + tax first-year-interest

**Rationale captured:** Covers matrix, verdict cascade integrity, and tax-block IRS Pub 936 path. Avoids brittle exhaustive pinning that breaks on reference-data refresh.

---

## Claude's Discretion (planner decides)

- Report header layout (address / price / Zestimate delta / escrow / household snapshot hash / FRED snapshot — exact field order)
- VERDICT section prose around `verdict.reasons[]` rendering
- Long blocker_reasons truncation strategy in matrix cells
- Specific implementation details of the NNN counter logic (atomic write, lockfile, etc.)

---

## Deferred to other phases

- DuckDB analyzed_listings persistence (v1.2 watchlist mode)
- Comparable property lookup (v1.2+ per PROJECT.md)
- PDF export (downstream tooling)
- Paid scraper API fallback (v1.2)
- Real Zillow HTML in evals (Phase 11 D-02 forbids)
- Multi-property side-by-side (out of scope)

---

*Discussion captured by /gsd-discuss-phase on 2026-05-20*

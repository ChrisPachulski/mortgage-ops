# Phase 15: `property` Skill Mode + Report Formatter — Pattern Map

**Mapped:** 2026-05-20
**Files analyzed:** 11 (8 create + 1 modify + 2 generated test surfaces)
**Analogs found:** 11 / 11 (every Phase 15 file has a concrete in-repo precedent)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.claude/skills/mortgage-ops/modes/property.md` | mode-file | request-response (Claude→WebFetch→Bash) | `.claude/skills/mortgage-ops/modes/evaluate.md` | exact (mode-file + multi-step orchestration) |
| `.claude/skills/mortgage-ops/scripts/property_analyze.py` | orchestrator-CLI | JSON-in / markdown-file-out + envelope-stdout | `.claude/skills/mortgage-ops/scripts/property_fetch.py` | exact (always-exit-0 envelope + lazy-import) |
| `lib/property_report.py` | formatter-library | pure transform (AnalysisReport → str) | `lib/property_analysis.py` (model+helper composition idiom) | role-match (no existing renderer; closest pure-Pydantic-consuming lib module) |
| `evals/prompts/property-analysis-01.md` | eval-prompt | frontmatter-pinned route+numeric oracle | `evals/prompts/amortize-01.md` + `evals/prompts/live-rate-injection-01.md` | exact (frontmatter shape) + partial (route-keyword oracle for non-numeric verdict) |
| `evals/expected/property-analysis-01.json` | eval-oracle | oracle JSON | `evals/expected/amortize-01.json` | exact |
| `evals/fixtures/property/sfh_conforming_001.json` | synthetic-fixture | static JSON | `tests/fixtures/property_analysis/sfh_conforming_king_county.json` | exact (PropertyListing+expected_response shape) |
| `evals/fixtures/property/sfh_conforming_001.html` | synthetic-fixture | static HTML stub | `tests/fixtures/zillow/sfh_conforming_happy_path.html` | exact |
| `tests/test_property_report.py` | unit-test | in-process Pydantic-fixture → render() assertions | `tests/test_property_analysis.py` (golden-fixture round-trip pattern) | role-match (formatter is new surface; closest fixture-driven test module) |
| `tests/test_property_analyze_cli.py` | unit-test | subprocess CLI invocations | `tests/test_property_fetch.py` | exact (SCRIPT_PATH + `_run_cli` + envelope assertions) |
| `tests/test_skill_routing.py` | unit-test | filesystem-introspection (token budget, grep, mode-file presence) | `tests/test_skill.py` | exact (tiktoken budget + frontmatter parse + mode-file presence parametrize) |
| `.claude/skills/mortgage-ops/SKILL.md` | SKILL.md edit | static markdown insertion | (self — existing 9-row routing table) | self-reference |

---

## Pattern Assignments

### `.claude/skills/mortgage-ops/modes/property.md` (mode-file, request-response)

**Analog:** `.claude/skills/mortgage-ops/modes/evaluate.md`

**Why this analog:** `evaluate.md` is the canonical multi-script-composition mode (calls TWO scripts: `amortize.py` + `affordability.py`). Phase 15's `property.md` is a one-script-composition mode (single orchestrator), but the WebFetch + gap-fill + Bash-dispatch flow inherits the same "narrate, build JSON, invoke script, narrate result" template structure verbatim.

**Header convention** (mirror `evaluate.md` lines 1-6):

```markdown
# Mode: property — Zillow listing → underwriting workup

Loaded by SKILL.md routing per the dispatch table. Read modes/_shared.md
FIRST (per D-10), then this file.
```

**"When to invoke" section pattern** (mirror `evaluate.md` lines 5-22):

```markdown
## When to invoke

Route here when (a) the user pasted a Zillow URL OR (b) said
"analyze listing". The URL-pin wins over refi/afford/stress/arm/amortize/
amortize/evaluate verbs (D-15-ROUTE-01).

Do NOT route here if:
- No URL AND no "analyze listing" phrase → existing precedence applies
- ...
```

**"What scripts to call" pattern** (mirror `evaluate.md` lines 24-89):

```markdown
## Orchestrator dispatch

Run `python .claude/skills/mortgage-ops/scripts/property_analyze.py --help`
first if you have not invoked it this session.

After WebFetch → gap-fill → tempfile write, invoke:

\`\`\`bash
python .claude/skills/mortgage-ops/scripts/property_analyze.py \
  --listing /tmp/listing-{uuid}.json \
  --household config/household.yml \
  --profile config/profile.yml \
  --output-dir reports/
\`\`\`

Parse stdout JSON envelope `{report_path, verdict, error}`. On
`error != null`, narrate the error code + message per `_shared.md` §
Error Narration Template.
```

**"Edge cases" pattern** (mirror `evaluate.md` lines 119-133): bulleted recovery list, one bullet per error code emitted by the orchestrator (`fred_cache_cold`, `household_yaml_invalid`, `profile_yaml_invalid`, `listing_validation_failed`, `output_dir_unwritable`).

**"RELATED REFERENCES" footer pattern** (mirror `evaluate.md` lines 135-143):

```markdown
## RELATED REFERENCES

(Load on demand only — D-09 progressive disclosure.)

- `references/property-analysis.md` (Phase 18 — ships ≥250 lines doc)
- `.planning/research/v1.1-property-analysis.md` (Pattern 1 verbatim extractor prompt)
```

---

### `.claude/skills/mortgage-ops/scripts/property_analyze.py` (orchestrator-CLI, JSON-in / file-out + envelope-stdout)

**Analog:** `.claude/skills/mortgage-ops/scripts/property_fetch.py`

**Why this analog:** Both are property-domain CLIs with **always-exit-0 envelopes** and **lazy-import discipline**. `property_fetch.py` is the closest precedent because (a) it already mirrors the 5-deep skill-folder path (`parents[4]` to project root), (b) it implements the three-shape envelope (success / awaiting / error) that Phase 15 simplifies to two shapes, (c) it has a documented outer `try/except` that converts arbitrary exceptions to envelope-and-exit-0. `amortize.py` is a secondary analog for the 6-key Pydantic envelope docstring.

**Note (OQ2):** Research §"Recommended Project Structure" + Open Q2 says the planner picks between (a) `.claude/skills/mortgage-ops/scripts/property_analyze.py` (matches Phase 13 `property_fetch.py` precedent — RECOMMENDED) and (b) project-root `scripts/property_analyze.py` (matches CONTEXT.md wording). This PATTERNS.md is path-agnostic; pick the location in planning, then mirror the `parents[N]` injection from whichever analog matches.

**Module docstring shape** (mirror `property_fetch.py` lines 1-40 + `amortize.py` lines 1-61):

```python
#!/usr/bin/env python3
"""scripts/property_analyze.py — PropertyListing JSON → AnalysisReport markdown report.

Phase 15 MODE-03 + D-15-ORCH-01..04. Pure compute (no network); WebFetch + URL
handling lives in `modes/property.md`. Mirrors Phase 12 always-exit-0 contract
and Phase 3 6-key Pydantic envelope on validation errors.

Envelope contract (single-line JSON on stdout, ALWAYS exit 0):

  success:  {report_path: "reports/NNN-property-{zpid}-{date}.md",
             verdict: "GO" | "WATCH" | "NO_GO", error: null}
  error:    {report_path: null, verdict: null,
             error: {code: "household_yaml_invalid|profile_yaml_invalid|
                           listing_validation_failed|fred_cache_cold|
                           missing_county_data|analyze_internal_error|
                           output_dir_unwritable",
                     message: "human-readable detail"}}

Pydantic ValidationError on listing JSON emits the 6-key envelope on stderr
(WR-02 closure shape; verbatim from scripts/amortize.py lines 36-60).

Usage:
  python scripts/property_analyze.py \\
    --listing data/property-listings/{zpid}-{date}.json \\
    --household config/household.yml \\
    --profile config/profile.yml \\
    --output-dir reports/

Always exits 0; argparse parse errors are the one documented exit-2 exception
(Phase 12 WR-02 + D-12-LIVE02-01).
"""
```

**Argparse + lazy-import pattern** (mirror `property_fetch.py` lines 173-225 and `amortize.py` lines 71-103):

```python
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="property_analyze",
        description=(
            "Compose Phase 14 analyze() into a markdown underwriting report. "
            "Always exits 0 (argparse parse errors return exit 2)."
        ),
        epilog=(
            "Envelope shapes (single-line JSON on stdout):\n"
            '  success: {"report_path": "...", "verdict": "GO|WATCH|NO_GO", "error": null}\n'
            '  error:   {"report_path": null, "verdict": null, "error": {"code", "message"}}\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--listing", required=True, type=Path)
    parser.add_argument("--household", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    # sys.path injection AFTER argparse (D-18: --help fast path unaffected).
    # parents[4] from .claude/skills/mortgage-ops/scripts/{name}.py mirrors
    # property_fetch.py:213 + amortize.py:99-100.
    project_root = Path(__file__).resolve().parents[4]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Lazy imports per D-18: heavy deps (numpy_financial, pydantic, pyyaml,
    # lib.property_analysis) are NOT loaded on the --help fast path.
    from lib.property_analysis import analyze
    # ... (continue per orchestrator steps below)
```

**Outer try/except always-exit-0 pattern** (mirror `property_fetch.py` lines 419-437 — VERBATIM idiom):

```python
if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise  # argparse parse errors (exit 2) — the one documented non-zero exit
    except Exception as exc:
        # Phase 12 D-12-LIVE02-01 + D-15-ORCH-03: ALL uncaught exceptions
        # convert to error envelope and exit 0.
        print(
            json.dumps(
                {
                    "report_path": None,
                    "verdict": None,
                    "error": {
                        "code": "analyze_internal_error",
                        "message": f"unexpected_failure: {exc!r}",
                    },
                }
            )
        )
        sys.exit(0)
```

**6-key Pydantic envelope pattern** (mirror `amortize.py` lines 149-154 VERBATIM):

```python
try:
    listing = PropertyListing.model_validate_json(args.listing.read_text())
except ValidationError as e:
    # WR-02 closure: 6-key envelope on stderr, error envelope on stdout, exit 0.
    print(e.json(), file=sys.stderr)
    print(json.dumps({
        "report_path": None, "verdict": None,
        "error": {"code": "listing_validation_failed",
                  "message": "PropertyListing failed Pydantic validation; see stderr"}
    }))
    return 0  # NOT exit 2 — Phase 15 D-15-ORCH-03 always-exit-0
```

Note: `amortize.py` returns 2 on ValidationError; Phase 15 D-15-ORCH-03 supersedes — return 0 with envelope, while ALSO emitting the 6-key on stderr (the dual emission preserves Pydantic envelope contract while honoring Phase 15's tighter always-exit-0).

**YAML loader pattern** (mirror `lib/rules/_loader.py` line 70 — the project's only existing YAML load call site):

```python
import yaml  # lazy-imported after argparse

raw = yaml.safe_load(args.household.read_text())  # NEVER yaml.load (V5 ASVS)
```

**Household multi-applicant → flat Phase-14 mapping** (NEW logic — no precedent; from RESEARCH Pitfall 2 lines 484-501):

```python
from decimal import Decimal
from lib.household import Household
from lib.money import quantize_cents  # if it exists; else use Decimal("0.01") quantize manually

def _load_phase14_household_from_yaml(path: Path) -> Household:
    raw = yaml.safe_load(path.read_text())["household"]
    monthly_income = sum(Decimal(a["gross_monthly_income"]) for a in raw["applicants"])
    monthly_obligations = sum(
        Decimal(raw["monthly_debts"][k])
        for k in ("auto", "student_loans", "credit_cards", "other")
    )
    fico = min(a["credit_score"] for a in raw["applicants"])
    return Household(
        monthly_income=monthly_income.quantize(Decimal("0.01")),
        monthly_obligations=monthly_obligations.quantize(Decimal("0.01")),
        fico=fico,
        liquid_reserves=Decimal(raw.get("liquid_reserves", "0.00")),
        state_fips=raw["location"]["state_fips"],
        county_fips=raw["location"]["county_fips"],
        county_name=raw["location"]["county_name"],
        preferred_down_payment_pct=Decimal(raw.get("preferred_down_payment_pct", "0.200000")),
    )
```

**NNN sequencer pattern** (NEW logic; from RESEARCH Pitfall 6 lines 580-591):

```python
import re

def _resolve_filename(out_dir: Path, zpid: str, today: str) -> Path:
    pattern = re.compile(r"^(\d{3})-")
    existing_nnns = [
        int(m.group(1))
        for f in out_dir.glob("*.md")
        if (m := pattern.match(f.name))
    ]
    next_nnn = (max(existing_nnns) + 1) if existing_nnns else 1
    base = f"{next_nnn:03d}-property-{zpid}-{today}"
    dupes = list(out_dir.glob(f"*-property-{zpid}-{today}*.md"))
    if not dupes:
        return out_dir / f"{base}.md"
    return out_dir / f"{base}-r{len(dupes) + 1}.md"
```

**Citation-footer reproducibility (Pitfall 10 + Assumption A3) — sidecar listing JSON write:** before writing the report, copy the validated listing JSON to `data/property-listings/{zpid}-{YYYY-MM-DD}.json` and cite THAT stable path in the footer. Mirrors Phase 13's `data/cache/property-{zpid}.json` pattern in `property_fetch.py` line 241.

---

### `lib/property_report.py` (formatter-library, pure transform)

**Analog:** `lib/property_analysis.py` (module structure + Pydantic-consumer idiom; no existing renderer in repo)

**Why this analog:** No existing `lib/` module renders Pydantic models to markdown. The closest precedent is `lib/property_analysis.py` itself — a module that consumes one set of Pydantic inputs and produces a Pydantic output. Phase 15's formatter inverts the pattern: consumes one Pydantic input, produces a string.

**Module docstring pattern** (mirror `lib/household.py` lines 1-38 structure):

```python
"""Phase 15 AnalysisReport → markdown formatter (RPRT-01, RPRT-02).

D-15-MATRIX-01..04 (matrix shape), D-15-CITATION-01..03 (per-section citation
footer), D-15-ORCH-04 (invocation citation full-args). Pure transform: NO I/O,
NO math (every dollar in the rendered markdown traces to a field on
AnalysisReport, which traces to lib.property_analysis.analyze()).

Public surface:
  render(report: AnalysisReport, orchestrator_argv: list[str]) -> str
    Returns the full markdown body (header + 6 sections + 6 citation footers).
    The orchestrator owns the file write — keeps render() I/O-coupled-free for
    testability (Assumption A9).

Six markdown sections per ROADMAP SC-4:
  1. Header (address, price, Zestimate delta, escrow snapshot, FRED snapshot,
     household_snapshot_hash, fetched_at)
  2. YOUR FIT — 5×6 matrix (Program × DP%), preferred-DP col bold (D-15-MATRIX-04)
  3. RATE STRESS — stress.rows table
  4. POINTS BREAKEVEN — points.rows table
  5. REFI OPPORTUNITY — refi.rows table (handles NEGATIVE monthly_savings/npv_60mo
     per Pitfall 4)
  6. TAX — IRS Pub 936 first-year interest + $750k cap flag
  7. VERDICT — level + headline + reasons[] (predicate_code + computed_value)

Each section ends with: *Computed by: scripts/property_analyze.py {full args}*
"""
```

**Render() public entry pattern:**

```python
from decimal import Decimal
from lib.property_analysis import AnalysisReport


def render(report: AnalysisReport, orchestrator_argv: list[str]) -> str:
    """Render an AnalysisReport to one-page markdown body.

    Args:
      report: Phase 14 AnalysisReport (frozen Pydantic).
      orchestrator_argv: sys.argv[1:] from the calling orchestrator; reconstructed
                         into the citation footer per D-15-CITATION-03.

    Returns:
      Markdown body as str. Caller writes to disk; this function does NO I/O.
    """
    footer = _render_footer(orchestrator_argv)
    return "\n\n".join([
        _render_header(report),
        _render_your_fit(report.matrix, report.listing_snapshot, report.household_snapshot_hash) + "\n\n" + footer,
        _render_rate_stress(report.stress) + "\n\n" + footer,
        _render_points_breakeven(report.points) + "\n\n" + footer,
        _render_refi_opportunity(report.refi) + "\n\n" + footer,
        _render_tax(report.tax, report.matrix) + "\n\n" + footer,
        _render_verdict(report.verdict) + "\n\n" + footer,
    ])
```

**Matrix renderer pattern** (mirror RESEARCH Code Examples lines 693-727 VERBATIM):

```python
def _render_matrix(matrix, preferred_dp: Decimal) -> str:
    programs = matrix.programs_present
    dps = matrix.down_payment_pcts
    cell_map = {(c.program, c.down_payment_pct): c for c in matrix.cells}

    header_cells = ["Program"]
    for dp in dps:
        label = f"{dp:.0%} DP"
        if dp == preferred_dp:
            label = f"**{label}** *(your DP)*"  # D-15-MATRIX-04
        header_cells.append(label)
    rows = ["| " + " | ".join(header_cells) + " |"]
    rows.append("|" + "---|" * (len(dps) + 1))

    for prog in programs:
        row = [prog]
        for dp in dps:
            cell = cell_map[(prog, dp)]
            piti_disp = f"${cell.piti:,.0f}/mo"  # whole dollars per Pitfall 11
            if cell.eligible:
                txt = f"{piti_disp} ✓"
            else:
                code = (cell.blocker_reasons[0] if cell.blocker_reasons else "BLOCKED")
                code = code.split(":")[0].split("(")[0].strip()  # D-15-MATRIX-02
                extra = (
                    f" (+{len(cell.blocker_reasons) - 1} more)"
                    if len(cell.blocker_reasons) > 1 else ""
                )
                txt = f"{piti_disp} ✗ ({code}{extra})"
            if dp == preferred_dp:
                txt = f"**{txt}**"
            row.append(txt)
        rows.append("| " + " | ".join(row) + " |")
    return "\n".join(rows)
```

**Signed-money formatter** (NEW; per Pitfall 4 lines 556-560):

```python
def _fmt_signed_money(d: Decimal) -> str:
    """Format negative dollars as -$X,XXX.XX (not $-X,XXX.XX). Required for
    refi.rows.monthly_savings and refi.rows.npv_60mo which CAN be negative."""
    return f"-${abs(d):,.2f}" if d < 0 else f"${d:,.2f}"
```

**Citation-footer renderer** (mirror RESEARCH lines 734-737 + D-15-CITATION-03):

```python
def _render_footer(argv: list[str]) -> str:
    # D-15-CITATION-03: FULL invocation with resolved path strings.
    # NOTE: the orchestrator should rewrite --listing to the stable sidecar
    # path (data/property-listings/{zpid}-{date}.json) BEFORE passing argv
    # here, so the footer is re-runnable copy-paste (Pitfall 10 + A3).
    return f"*Computed by: scripts/property_analyze.py {' '.join(argv)}*"
```

**ARM-reset row ordering** (Pitfall 5 lines 565-569): when rendering `_render_rate_stress`, sort `stress.rows` by `(program, stress_kind)` with `stress_kind` ordered `["rate_shock", "income_shock", "arm_reset"]` to prevent visual collapse.

**Tax over-cap copy** (Assumption A8): when `tax.over_750k_cap_per_program[program] == True`, render a "see CPA" callout — do NOT compute partial-deduction dollars (would violate calc-engine separation per CLAUDE.md).

---

### `evals/prompts/property-analysis-01.md` (eval-prompt, frontmatter-pinned)

**Primary analog:** `evals/prompts/amortize-01.md` (frontmatter shape)
**Secondary analog:** `evals/prompts/live-rate-injection-01.md` (route-keyword for non-numeric value)

**Why these analogs:** `amortize-01.md` is the canonical frontmatter shape for an eval prompt with `expected_route_keywords` + `expected_scripts` + `expected_numbers`. `live-rate-injection-01.md` is the precedent for pinning a non-numeric value (`"6.50"` rate string) via `expected_route_keywords` substring match — directly applicable to Phase 15's `verdict.level == "GO"` assertion since `score_numeric_match` requires a decimal point (RESEARCH line 775).

**Frontmatter pattern** (mirror `amortize-01.md` lines 1-17 + RESEARCH lines 741-773):

```yaml
---
id: property-analysis-01
mode: property
description: Full property analysis — SFH conforming King County WA; ROADMAP SC-6 anchor.
expected_route_keywords:
  - property
  - property_analyze.py
  - "GO"           # D-15-EVAL-03 #1: verdict.level via route-keyword (string match)
expected_scripts:
  - script: property_analyze.py
    args_must_include: ["--listing", "--household", "--profile"]
expected_numbers:
  - label: conv30_preferred_dp_piti      # D-15-EVAL-03 #2
    value: "3760.34"
    tolerance: "0.50"
    source_script: property_analyze.py
    provenance: stdout
  - label: first_year_interest_conv30    # D-15-EVAL-03 #4
    value: "32335.43"
    tolerance: "0.50"
    source_script: property_analyze.py
    provenance: stdout
  - label: verdict_reasons_count          # D-15-EVAL-03 #3
    value: "1.0"                         # cast to decimal-point form so NUMBER_REGEX matches
    tolerance: "0.0"
    source_script: property_analyze.py
    provenance: stdout
---

Analyze this Zillow listing for me: https://www.zillow.com/homedetails/synthetic/1_zpid/
```

**Note (Assumption A4):** the verdict-level oracle uses `expected_route_keywords: ["GO"]` rather than `expected_numbers` because `evals/metrics.py` `NUMBER_REGEX` requires a decimal point. This matches the `live-rate-injection-01.md` precedent (line 6: `- "6.50"` in keywords).

---

### `evals/expected/property-analysis-01.json` (eval-oracle)

**Analog:** `evals/expected/amortize-01.json` (VERBATIM shape)

**Pattern** (mirror `amortize-01.json` lines 1-23):

```json
{
  "schema_version": 1,
  "id": "property-analysis-01",
  "mode": "property",
  "numeric_status": "anchored",
  "expected_scripts": [
    {
      "script": "property_analyze.py",
      "args_must_include": ["--listing", "--household", "--profile"]
    }
  ],
  "expected_numbers": [
    {"label": "conv30_preferred_dp_piti", "value": "3760.34", "tolerance": "0.50", "source_script": "property_analyze.py", "provenance": "stdout"},
    {"label": "first_year_interest_conv30", "value": "32335.43", "tolerance": "0.50", "source_script": "property_analyze.py", "provenance": "stdout"},
    {"label": "verdict_reasons_count", "value": "1.0", "tolerance": "0.0", "source_script": "property_analyze.py", "provenance": "stdout"}
  ],
  "expected_route_keywords": ["property", "property_analyze.py", "GO"],
  "v1_frozen_at": "2026-05-20"
}
```

---

### `evals/fixtures/property/sfh_conforming_001.json` (synthetic-fixture, static JSON)

**Analog:** `tests/fixtures/property_analysis/sfh_conforming_king_county.json`

**Why this analog:** This Phase 14 fixture IS the canonical AnalysisReport-anchor shape. Phase 15's eval fixture should mirror its structure exactly (listing block, household block, profile block, fred_rates block, expected_response block with verdict + matrix.preferred_dp_cells + tax block).

**Key fields to mirror** (from `sfh_conforming_king_county.json` lines 17-131):

| Section | Required keys |
|---------|---------------|
| top-level | `$schema`, `id`, `source` (hand-calc citation), `rounding: "ROUND_HALF_UP"`, `notes` (cascade-level derivation + per-program hand-calc citations), `_meta` (citation, engine_version, requirements list) |
| `listing` | `price`, `zip`, `property_type`, `tax_annual` (ProvenancedMoney shape), `insurance_estimate_annual`, `hoa_monthly`, `source_url` (synthetic: `https://www.zillow.com/homedetails/synthetic/N_zpid/`), `zpid` ("1" or higher), `fetched_at` (ISO-Z) |
| `household` | flat Phase-14 shape: `monthly_income`, `monthly_obligations`, `fico`, `liquid_reserves`, `state_fips`, `county_fips`, `county_name`, `preferred_down_payment_pct` |
| `profile` | `va_eligible`, `first_time_buyer`, `military_status`, `filing_status`, `marginal_tax_rate` |
| `fred_rates` | `MORTGAGE30US`, `MORTGAGE15US` (six-decimal-string rates for test injection per Phase 14 `analyze(fred_mortgage_*us=...)` kwargs) |
| `expected_response` | `verdict.level`, `verdict.headline_reason`, `verdict.reasons[]`, `matrix.cells_count`, `matrix.programs_present`, `matrix.preferred_dp_cells[]` (one entry per program; full ProgramResult JSON), `tax.qualified_loan_limit`, `tax.over_750k_cap_per_program`, `tax.first_year_interest_per_program`, `tax.filing_status`, `warnings[]` |

**Decimal-as-string discipline:** every money/rate value in the fixture is a JSON string (CLAUDE.md money discipline). The Phase 14 fixture demonstrates this throughout.

---

### `evals/fixtures/property/sfh_conforming_001.html` (synthetic-fixture, static HTML stub)

**Analog:** `tests/fixtures/zillow/sfh_conforming_happy_path.html` (~6.5KB, full `__NEXT_DATA__` block at lines 80-108)

**Why this analog:** Phase 13's happy-path HTML fixture is the canonical "synthetic Zillow page with valid `__NEXT_DATA__`" shape. CONTEXT D-15-EVAL-01 calls for a 2KB stub (vs Phase 13's 6.5KB — Phase 13 needed body-padding to exceed `MIN_BODY_BYTES=5000` for block-detection tests; Phase 15 does NOT need that padding because the orchestrator never sees the HTML).

**Key elements to mirror** (from `sfh_conforming_happy_path.html`):

1. **`<script id="__NEXT_DATA__" type="application/json">{...}</script>` block** containing the JSON payload that matches the JSON fixture's `listing` block, transposed to Zillow's wire field names:
   - `zpid` → string in `__NEXT_DATA__` matches fixture's `listing.zpid`
   - `price` → number in `__NEXT_DATA__` (Zillow emits JSON numbers; Sonnet extractor stringifies)
   - `zipcode` → matches `listing.zip`
   - `propertyTypeDimension` → "SingleFamily" maps to `listing.property_type: "SFH"`
   - `taxAnnualAmount`, `hoaFee`, `zestimate` → match fixture's ProvenancedMoney values

2. **No PII or real listing data** (per Phase 11 D-02 + Phase 13 README §"What NOT to put here" lines 128-145).

3. **Synthetic source-URL alignment:** the HTML's address fields + the fixture's `listing.source_url` agree (both point to `synthetic/1_zpid/` or equivalent).

**Smaller body acceptable:** Phase 13's 6.5KB padding existed for `body_too_short` detection. Phase 15 D-15-EVAL-01 specifies ≤2KB; the body can be a minimal `<html><head><title/></head><body><script id="__NEXT_DATA__">{...}</script></body></html>` shell.

---

### `tests/test_property_report.py` (unit-test, in-process)

**Primary analog:** `tests/test_property_analysis.py` (fixture-driven Pydantic round-trip pattern)

**Pattern: load fixture → instantiate AnalysisReport → call render() → assert structural invariants**

Required test cases (per RESEARCH Validation Architecture table lines 893-901):

```python
def test_render_emits_six_sections(sample_report: AnalysisReport) -> None:
    """RPRT-01: report has all 6 sections (YOUR FIT, RATE STRESS, POINTS BREAKEVEN,
    REFI OPPORTUNITY, TAX, VERDICT)."""
    md = render(sample_report, orchestrator_argv=[...])
    for section in ("## YOUR FIT", "## RATE STRESS", "## POINTS BREAKEVEN",
                    "## REFI OPPORTUNITY", "## TAX", "## VERDICT"):
        assert section in md

def test_six_citation_footers(sample_report: AnalysisReport) -> None:
    """RPRT-02 + D-15-CITATION-01: exactly 6 footers (one per section)."""
    md = render(sample_report, orchestrator_argv=[...])
    assert md.count("*Computed by: scripts/property_analyze.py") == 6

def test_footer_is_full_invocation(sample_report: AnalysisReport) -> None:
    """D-15-CITATION-03: footer carries the FULL invocation."""
    argv = ["--listing", "data/property-listings/1-2026-05-20.json",
            "--household", "config/household.yml",
            "--profile", "config/profile.yml",
            "--output-dir", "reports/"]
    md = render(sample_report, orchestrator_argv=argv)
    assert "--listing data/property-listings/1-2026-05-20.json" in md

def test_matrix_renders_all_cells(sample_report: AnalysisReport) -> None:
    """D-15-MATRIX-03: every cell (eligible + ineligible) appears in the table."""
    md = render(sample_report, ...)
    expected_cells = len(sample_report.matrix.cells)
    # count "/mo" occurrences in the YOUR FIT section as cell-count proxy
    your_fit = md.split("## YOUR FIT")[1].split("## RATE STRESS")[0]
    assert your_fit.count("/mo") >= expected_cells

def test_cell_eligibility_marks(sample_report: AnalysisReport) -> None:
    """D-15-MATRIX-02: eligible cells show ✓; ineligible show ✗ + blocker code."""
    md = render(sample_report, ...)
    your_fit = md.split("## YOUR FIT")[1].split("## RATE STRESS")[0]
    eligible_count = sum(1 for c in sample_report.matrix.cells if c.eligible)
    assert your_fit.count("✓") == eligible_count

def test_preferred_dp_column_bolded(sample_report: AnalysisReport) -> None:
    """D-15-MATRIX-04: preferred-DP column header is bold + has '(your DP)' annotation."""
    md = render(sample_report, ...)
    pref = sample_report.matrix.cells[0].down_payment_pct  # all cells share preferred via household
    # Find the bold marker on the preferred-DP column header
    assert "*(your DP)*" in md

def test_signed_money_negative_format(sample_report_with_negative_refi: AnalysisReport) -> None:
    """Pitfall 4: -$X,XXX.XX format, not $-X,XXX.XX."""
    md = render(sample_report_with_negative_refi, ...)
    # No occurrence of $-
    assert "$-" not in md.split("## REFI OPPORTUNITY")[1].split("## TAX")[0]
```

**Fixture loading pattern** (mirror `tests/test_property_analysis.py` golden-fixture loading):

```python
import json
from pathlib import Path
import pytest
from lib.property_analysis import analyze

FIXTURES = Path(__file__).parent / "fixtures" / "property_analysis"

@pytest.fixture
def sample_report() -> AnalysisReport:
    raw = json.loads((FIXTURES / "sfh_conforming_king_county.json").read_text())
    listing = PropertyListing.model_validate(raw["listing"])
    household = Household(**raw["household"])
    profile = Profile(**raw["profile"])
    return analyze(
        listing, household, profile,
        fred_mortgage_30us=Decimal(raw["fred_rates"]["MORTGAGE30US"]),
        fred_mortgage_15us=Decimal(raw["fred_rates"]["MORTGAGE15US"]),
    )
```

---

### `tests/test_property_analyze_cli.py` (unit-test, subprocess)

**Analog:** `tests/test_property_fetch.py` (VERBATIM patterns for SCRIPT_PATH + `_run_cli`)

**SCRIPT_PATH constant** (mirror `tests/test_property_fetch.py` lines 29-36 — adjust last segment):

```python
SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude" / "skills" / "mortgage-ops" / "scripts" / "property_analyze.py"
)
```

**`_run_cli` helper pattern** (mirror lines 78-101 — VERBATIM, drop ANTHROPIC_API_KEY-stripping since orchestrator doesn't call Sonnet):

```python
def _run_cli(*args: str, env: dict[str, str] | None = None,
             timeout: float = 15) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT_PATH), *args]
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
        env=merged_env, check=False,
    )
```

**Test cases** (per Validation Architecture table):

```python
def test_help_fast_no_heavy_imports() -> None:
    """D-18 + MODE-03: --help <300ms; no pydantic / yaml / lib.property_analysis."""
    start = time.perf_counter()
    result = _run_cli("--help")
    elapsed = time.perf_counter() - start
    assert result.returncode == 0
    assert elapsed < 0.3

def test_argparse_error_exit_2() -> None:
    """Phase 12 WR-02: argparse parse error is the documented exit-2 exception."""
    result = _run_cli()  # missing required --listing
    assert result.returncode == 2

def test_success_envelope_shape(tmp_path: Path, golden_listing: Path,
                                 household_yml: Path, profile_yml: Path) -> None:
    """MODE-03 + D-15-ORCH-03: success envelope {report_path, verdict, error:null}."""
    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    result = _run_cli("--listing", str(golden_listing),
                       "--household", str(household_yml),
                       "--profile", str(profile_yml),
                       "--output-dir", str(out_dir))
    assert result.returncode == 0
    env = json.loads(result.stdout)
    assert env["error"] is None
    assert env["verdict"] in ("GO", "WATCH", "NO_GO")
    assert env["report_path"].endswith(".md")
    assert Path(env["report_path"]).is_file()

def test_error_envelope_always_exit_0(tmp_path: Path) -> None:
    """D-15-ORCH-03: bad listing input → error envelope + exit 0."""
    bad = tmp_path / "bad.json"
    bad.write_text("{}")  # missing required PropertyListing fields
    result = _run_cli("--listing", str(bad),
                       "--household", "config/household.yml",
                       "--profile", "config/profile.yml",
                       "--output-dir", str(tmp_path))
    assert result.returncode == 0  # KEY assertion: always-exit-0
    env = json.loads(result.stdout)
    assert env["error"] is not None
    assert env["error"]["code"]
    assert env["report_path"] is None
    assert env["verdict"] is None

def test_pydantic_validation_envelope_on_stderr(tmp_path: Path) -> None:
    """WR-02 closure: 6-key envelope on stderr for listing validation failure."""
    bad = tmp_path / "bad.json"
    bad.write_text('{"price": 625000.00}')  # JSON float (Decimal violation)
    result = _run_cli("--listing", str(bad), ...)
    assert result.returncode == 0
    stderr_envelope = json.loads(result.stderr)
    assert isinstance(stderr_envelope, list)
    for err in stderr_envelope:
        assert set(err.keys()) >= {"type", "loc", "msg", "input", "url"}

def test_filename_format(tmp_path: Path, ...) -> None:
    """RPRT-01 + D-15-ORCH-04: filename matches reports/NNN-property-{zpid}-{YYYY-MM-DD}.md."""
    result = _run_cli(...)
    env = json.loads(result.stdout)
    pattern = re.compile(r"reports/\d{3}-property-\w+-\d{4}-\d{2}-\d{2}\.md$")
    assert pattern.search(env["report_path"])

def test_same_day_zpid_suffix(tmp_path: Path, ...) -> None:
    """RPRT-01 + Pitfall 6: same-day same-zpid duplicate gets -r2 suffix."""
    # Run orchestrator twice with same listing+date
    result1 = _run_cli(...); env1 = json.loads(result1.stdout)
    result2 = _run_cli(...); env2 = json.loads(result2.stdout)
    assert env2["report_path"].endswith("-r2.md")

def test_household_yaml_mapping(tmp_path: Path, ...) -> None:
    """MODE-03 + Pitfall 2: Phase 4 multi-applicant household.yml maps to Phase 14 flat Household."""
    # Use the real config/household.example.yml shape
    result = _run_cli(...)
    assert result.returncode == 0
    assert json.loads(result.stdout)["error"] is None
```

---

### `tests/test_skill_routing.py` (unit-test, filesystem-introspection)

**Analog:** `tests/test_skill.py` (token-budget + mode-file presence + grep tests)

**Pattern: load helpers (`count_tokens` from `tests._skill_helpers`), introspect SKILL.md + modes/property.md, assert structural invariants.**

**Token budget test pattern** (mirror `tests/test_skill.py` lines 121-129 VERBATIM):

```python
from tests._skill_helpers import count_tokens

def test_skill_md_token_budget(skill_root: Path) -> None:
    """MODE-02 + Pitfall 1: SKILL.md ≤ 4500 cl100k tokens after Row 0 insertion."""
    skill_md = (skill_root / "SKILL.md").read_text()
    n_tokens = count_tokens(skill_md)
    assert n_tokens <= 4500, (
        f"SKILL.md is {n_tokens} cl100k tokens (budget 4500); "
        f"Phase 15 Row 0 insertion overflowed. Trim references table per "
        f"Phase 10 deferred recovery."
    )
```

**Property mode Row 0 presence test:**

```python
def test_property_mode_row0_present(skill_root: Path) -> None:
    """MODE-01 + D-15-ROUTE-01: SKILL.md routing table includes Row 0 for zillow.com."""
    skill_md = (skill_root / "SKILL.md").read_text()
    head = "\n".join(skill_md.splitlines()[:200])  # first 200 lines per SKLL-02
    assert "zillow.com" in head
    assert "analyze listing" in head
    assert "property" in head
    assert "property_analyze.py" in head

def test_property_mode_file_exists(skill_root: Path) -> None:
    """MODE-01: modes/property.md exists."""
    assert (skill_root / "modes" / "property.md").is_file()

def test_skill_md_cross_references_property_mode(skill_root: Path) -> None:
    """MODE-02: SKILL.md cross-references modes/property.md."""
    skill_md = (skill_root / "SKILL.md").read_text()
    assert "modes/property.md" in skill_md OR "property" in skill_md  # planner picks

def test_property_mode_contains_extractor_prompt(skill_root: Path) -> None:
    """MODE-01: modes/property.md embeds the Pattern 1 __NEXT_DATA__ extractor prompt verbatim."""
    body = (skill_root / "modes" / "property.md").read_text()
    assert "__NEXT_DATA__" in body
    assert "WebFetch" in body
```

---

### `.claude/skills/mortgage-ops/SKILL.md` (SKILL.md edit, static insertion)

**Self-reference:** the existing 9-row routing table (lines 23-31) + precedence list (lines 37-47).

**Insertion pattern** (per D-15-ROUTE-01..03 + RESEARCH lines 379-417):

**Routing table — INSERT AT TOP** (above the existing 7 rows, line ~24):

```markdown
| Input pattern | Mode | Script |
|---|---|---|
| Zillow URL substring (`zillow.com`) OR phrase "analyze listing" | `property` | `scripts/property_analyze.py` |
| Single loan + payment question (`"$400k @ 6.5%/30yr, what's my payment?"`) | `evaluate` | ... (existing) |
| ... (remaining 6 existing rows unchanged) |
```

**Precedence — INSERT AS Row 0** (above existing line 39 `1. Explicit sub-command...`):

```markdown
0. URL pin: `zillow.com` substring OR phrase "analyze listing"
                                  → `property` (HIGHEST — overrides ALL verbs and explicit slash-commands)
1. Explicit sub-command           → `/mortgage-ops {mode}`
2. "refinance" / "refi" verb      → `refinance` (overrides arm/amortize/stress vocabulary)
3. "afford" / "borrow" verb       → `affordability` (overrides amortize)
... (existing rows renumber but otherwise unchanged)
```

**Token-budget guard:** keep the routing-row insertion to ONE line and the precedence-row to ONE compact entry. RESEARCH Pitfall 1 lines 459-473 estimates ~120 token headroom; the planner should run `count_tokens` in Wave 0 before locking the design.

---

## Shared Patterns

### Always-exit-0 envelope discipline (Phase 12 inheritance)

**Source:** `.claude/skills/mortgage-ops/scripts/property_fetch.py` lines 419-437 (outer try/except) and `.claude/skills/mortgage-ops/scripts/amortize.py` lines 36-60 (envelope contract docstring)

**Apply to:** `scripts/property_analyze.py`

**Excerpt:**

```python
if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise  # argparse parse errors (exit 2)
    except Exception as exc:
        print(json.dumps({"report_path": None, "verdict": None,
                          "error": {"code": "analyze_internal_error",
                                    "message": f"unexpected_failure: {exc!r}"}}))
        sys.exit(0)
```

### Lazy-import + sys.path injection (D-18)

**Source:** `.claude/skills/mortgage-ops/scripts/property_fetch.py` lines 209-225 + `.claude/skills/mortgage-ops/scripts/amortize.py` lines 92-103

**Apply to:** `scripts/property_analyze.py`

**Excerpt:**

```python
def main() -> int:
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args()  # --help SystemExits here

    # sys.path injection happens AFTER argparse so --help is fast.
    project_root = Path(__file__).resolve().parents[4]  # 5-deep: skill/scripts/X.py
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Lazy imports — heavy deps not loaded on --help fast path.
    from lib.property_analysis import analyze
    from lib.property_listing import PropertyListing
    from lib.household import Household
    from lib.profile import Profile
    from lib.property_report import render
    import yaml
    from pydantic import ValidationError
```

### Money/Decimal discipline (CLAUDE.md non-negotiable)

**Source:** `CLAUDE.md` "Money discipline" + `tests/fixtures/property_analysis/sfh_conforming_king_county.json` (Decimal-as-string demonstration throughout)

**Apply to:** Every Phase 15 file that touches money/rates — orchestrator, formatter, fixtures.

**Rules:**
- Construct `Decimal` from strings: `Decimal("0.065")` NOT `Decimal(0.065)`.
- Money/rate fields in JSON fixtures + orchestrator I/O are JSON strings.
- Format negative Decimals as `-$X,XXX.XX`, not `$-X,XXX.XX` (Pitfall 4).
- Display formatters use Decimal directly: `f"{val:,.2f}"`. NEVER coerce to float.
- The stdout envelope's `verdict` is a string Literal (`"GO"/"WATCH"/"NO_GO"`); NO Decimal crosses the JSON boundary (Pitfall 8).

### Citation footer convention (Phase 11 stress-test-agent precedent)

**Source:** `.planning/phases/11-subagents/11-03-stress-test-agent-PLAN.md` line 116 ("the line `Computed by: bash python ... stress_test.py --input <path>` MUST appear at the bottom of every response")

**Apply to:** `lib/property_report.py` (every one of the 6 sections gets one footer)

**Excerpt:**

```python
# D-15-CITATION-01..03: italicized line, prefix "*Computed by:", full re-runnable command.
footer = f"*Computed by: scripts/property_analyze.py {' '.join(orchestrator_argv)}*"
```

### Synthetic-only-in-CI fixture policy (Phase 11 D-02)

**Source:** `tests/fixtures/zillow/README.md` lines 56-79 + `tests/fixtures/property_analysis/README.md` lines 15-22

**Apply to:** `evals/fixtures/property/sfh_conforming_001.json` + `evals/fixtures/property/sfh_conforming_001.html`

**Rules:**
- Synthetic addresses only (`123 Synthetic St` style); ZIP can stay real.
- No PII, no agent contact info, no AI-attribution markers.
- Hand-calculated golden values with citation comments in `notes` field.
- `source_url` uses synthetic `https://www.zillow.com/homedetails/synthetic/{N}_zpid/`.
- `zpid` is digit-only string (`"1"`, `"2"`, ...).
- `fetched_at` is ISO-8601 UTC with Z suffix.

### Read-only User Layer (DATA_CONTRACT.md)

**Source:** `.claude/skills/mortgage-ops/modes/_shared.md` lines 246-264 ("Forbidden Behaviors")

**Apply to:** `scripts/property_analyze.py` (reads `config/household.yml` + `config/profile.yml`; NEVER writes them) + `modes/property.md` (orchestrator dispatch instructions never trigger user-layer writes)

**Verification:** subprocess test that runs the orchestrator and asserts `config/household.yml` mtime is unchanged.

### Path-traversal hardening for `--output-dir` (ASVS V5)

**Source:** RESEARCH §"Security Domain" line 945

**Apply to:** `scripts/property_analyze.py`

**Excerpt:**

```python
# Reject --output-dir paths that escape project root (defense-in-depth)
output_dir = args.output_dir.resolve()
if not str(output_dir).startswith(str(project_root)):
    print(json.dumps({"report_path": None, "verdict": None,
                      "error": {"code": "output_dir_unwritable",
                                "message": "output-dir must be under project root"}}))
    return 0
```

### Save-Report skip (Phase 15 deviation from `_shared.md` D-13-01..05)

**Source:** `.claude/skills/mortgage-ops/modes/_shared.md` lines 187-243

**Apply to:** `modes/property.md` MUST skip the DuckDB `insert-report` flow (deferred to v1.2 per CONTEXT §Deferred Ideas line 153). The mode explicitly opts out — the orchestrator writes the markdown to `reports/` but does NOT call `node orchestration/db-write.mjs insert-report`.

**Distinction from existing modes:** `evaluate.md` + 6 other modes invoke Save Report. `property.md` is the first mode that writes a report file but skips DuckDB persistence — document this in the mode body so it isn't mistaken for an omission.

---

## No Analog Found

| File | Role | Why no analog |
|------|------|---------------|
| `lib/property_report.py` (partial) | formatter-library | No existing `lib/` module renders Pydantic models to markdown. Use `lib/household.py` for the docstring/module-structure idiom and RESEARCH Code Examples (lines 692-737) for the matrix-rendering algorithm. |
| YAML multi-applicant → flat Household mapping | helper function inside orchestrator | No `lib/household.from_yaml()` precedent; no script currently loads either Household model from disk. Use RESEARCH Pitfall 2 lines 484-501 as the verbatim implementation template. |
| NNN sequencer with same-day-zpid `-r2` suffix | helper function inside orchestrator | Phase 10 D-13-02 ships `reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md` via the Node `orchestration/db-write.mjs query` flow; Phase 15 inlines the scan into Python (no Node round-trip). Use RESEARCH Pitfall 6 lines 580-591 as the verbatim implementation template. |

These three sub-components have no direct in-repo analog; the planner relies on RESEARCH.md Code Examples + Pitfalls sections (already cited above) for implementation guidance.

---

## Metadata

**Analog search scope:**
- `.claude/skills/mortgage-ops/modes/` (10 files; primary analog: `evaluate.md` + `_shared.md`)
- `.claude/skills/mortgage-ops/scripts/` (10 files; primary analog: `property_fetch.py`, `amortize.py`)
- `lib/` (16 files; structural analog: `property_analysis.py`, `household.py`, `profile.py`)
- `evals/prompts/` (22 files; primary analog: `amortize-01.md`, `live-rate-injection-01.md`)
- `evals/expected/` (22 files; primary analog: `amortize-01.json`)
- `tests/` (35 files; primary analog: `test_skill.py`, `test_property_fetch.py`, `test_property_analysis.py`)
- `tests/fixtures/property_analysis/` (3 fixtures; primary analog: `sfh_conforming_king_county.json`)
- `tests/fixtures/zillow/` (3 fixtures; primary analog: `sfh_conforming_happy_path.html`)
- `.planning/phases/11-subagents/` (Phase 11 PLANs; citation-footer + report-emit precedent)

**Files scanned:** ~120 (focused on Phase 13/14/12/10/11 surfaces — the immediate-predecessor and contract-source phases)

**Pattern extraction date:** 2026-05-20

## PATTERN MAPPING COMPLETE

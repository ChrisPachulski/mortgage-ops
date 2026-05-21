# Phase 15: `property` Skill Mode + Report Formatter - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the Phase 14 `analyze(listing, household, profile) → AnalysisReport` pipeline into the Claude skill via a new `property` mode AND ship the markdown report formatter that turns the frozen AnalysisReport into a one-page underwriting workup persisted to `reports/`. Closes MODE-01, MODE-02, MODE-03, RPRT-01, RPRT-02.

**In scope:**
- `.claude/skills/mortgage-ops/modes/property.md` — new mode file with WebFetch + JSON extraction recipe, then orchestrator dispatch.
- `.claude/skills/mortgage-ops/SKILL.md` — routing edits: new top-of-table row for `zillow.com` substring OR "analyze listing" phrase; cross-reference to `modes/property.md`; ≤4500 cl100k token budget preserved.
- `scripts/property_analyze.py` — JSON-in / report-out orchestrator (Phase 12 always-exit-0 envelope).
- `lib/property_report.py` — AnalysisReport → markdown string formatter.
- `evals/prompts/property-analysis-01.md` + `evals/fixtures/property/` — one eval prompt + extracted-JSON fixture + synthetic HTML smoke fixture.

**Out of scope:** Zillow HTML extraction logic beyond the recipe in `modes/property.md` (handled by Claude + WebFetch at mode-body time, not by the orchestrator script). DuckDB persistence of analyzed_listings (deferred — Phase 13 already ships the table; Phase 15 only WRITES the markdown file, not the DB row). Watchlist mode (v1.2). Comparable-listing or assessor-tax lookups (PROJECT.md out-of-scope).

</domain>

<decisions>
## Implementation Decisions

### Mode routing precedence (MODE-01, MODE-02)

- **D-15-ROUTE-01 (URL-pin overrides everything):** A new precedence row inserts at **Row 0** of SKILL.md, ABOVE explicit `/mortgage-ops {mode}` slash-commands. Trigger: user message contains `zillow.com` substring OR the literal phrase `analyze listing`. Effect: dispatch to `property` mode regardless of any other verb (refi, afford, compare, stress, arm, amortize, evaluate). The URL is load-bearing; if the user pasted it, the listing context dominates the verb. Rationale: pasting a Zillow URL is unambiguous intent; even `/mortgage-ops refinance https://www.zillow.com/...` routes to property (the listing-grounded analysis subsumes the refi math).
- **D-15-ROUTE-02 (single trigger row):** Both the `zillow.com` substring AND the bare `analyze listing` phrase route to the same row. If only the phrase is present (no URL), Claude follows up by asking for a URL before invoking the orchestrator. The bare phrase doesn't auto-promote a different mode.
- **D-15-ROUTE-03 (existing precedence preserved):** The existing 9-row precedence table (Phase 10 SKILL.md) shifts down by one — explicit slash-command becomes Row 2, refi verb becomes Row 3, etc. No other row is reordered or rewritten.

### YOUR FIT matrix layout (RPRT-01)

- **D-15-MATRIX-01 (orientation):** Rows = Program (Conv30, Conv15, FHA30, VA30 when `profile.va_eligible`, Jumbo30 when `listing.price > conforming_limit`). Cols = DP% in order (3, 5, 10, 15, 20, 25). 5 rows × 6 cols = 30 cells max, 18 cells baseline (no VA, no Jumbo). Reads left-to-right as "as you put more down...".
- **D-15-MATRIX-02 (cell content):** Each cell shows `$X,XXX/mo ✓` for eligible OR `$X,XXX/mo ✗ (<BLOCKER-CODE>)` for ineligible. PITI is the headline number (one of the most decision-relevant). The eligibility flag + first blocker code from `cell.blocker_reasons[0]` (truncated to the bare code, no parenthetical) makes the matrix scannable.
- **D-15-MATRIX-03 (ineligible cells rendered):** Every cell (eligible + ineligible) appears in the table — D-14-MATRIX-02 spent compute populating ineligible numerics specifically so the report could show them. The blocker code inline tells the user WHY they don't qualify (actionable: "DTI breaches Conv ceiling — try FHA at 0.20 DP instead"). DO NOT filter ineligible cells.
- **D-15-MATRIX-04 (preferred-DP column highlighted):** The column matching `household.preferred_down_payment_pct` is visually distinguished (markdown bold the column header, or wrap with `**`). Quick eye-anchor for the user's decision point.

### Citation footer (RPRT-02)

- **D-15-CITATION-01 (per-section, 6 footers total):** Exactly one citation footer at the END of each of the 6 markdown sections (YOUR FIT, RATE STRESS, POINTS BREAKEVEN, REFI OPPORTUNITY, TAX, VERDICT). Not per-cell, not per-row, not per-table. Reads like: `*Computed by: scripts/property_analyze.py --listing path/to/extracted.json --household config/household.yml --profile config/profile.yml*`. Italicized footer line.
- **D-15-CITATION-02 (orchestrator only, not primitives):** Every section cites the orchestrator entry point `scripts/property_analyze.py`. Phase 14 composes 7 primitives in-process — citing per-primitive would be misleading because the user can't actually re-run `scripts/amortize.py` standalone and reproduce the matrix. Reproducibility = re-run the same `scripts/property_analyze.py` command. NO appendix listing primitives.
- **D-15-CITATION-03 (full args):** Each footer carries the FULL invocation including flag values (resolved path strings). Not `scripts/property_analyze.py {args}` placeholder text. The footer must be re-runnable copy-paste.

### `scripts/property_analyze.py` orchestrator contract (MODE-03)

- **D-15-ORCH-01 (JSON-file inputs only, no network):** CLI signature: `python scripts/property_analyze.py --listing <path-to-extracted-listing.json> --household <path-to-household.yml> --profile <path-to-profile.yml> --output-dir <reports/>`. Script does NO WebFetch, NO HTTP. Phase 12 D-12-LIVE02-01 separation honored: scripts are pure compute.
- **D-15-ORCH-02 (mode body owns extraction):** `modes/property.md` instructs Claude to: (1) WebFetch the URL with the Pattern-1 `__NEXT_DATA__` extractor prompt from `.planning/research/v1.1-property-analysis.md`, (2) validate via PropertyListing Pydantic round-trip, (3) interactive gap-fill for missing critical fields, (4) write the JSON to a tempfile, (5) invoke `scripts/property_analyze.py` against the tempfile. The orchestrator never sees a URL.
- **D-15-ORCH-03 (Phase 12 always-exit-0 envelope):** stdout returns JSON `{"report_path": "reports/001-property-12345-2026-05-20.md", "verdict": "GO", "error": null}` on success; on error returns `{"report_path": null, "verdict": null, "error": {"code": "...", "message": "..."}}` and STILL exits 0. Stderr carries the standard 6-key Pydantic validation envelope on input errors (Phase 3 / 10 / 12 D-19 contract).
- **D-15-ORCH-04 (report filename: NNN counter from reports/ scan):** `reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md`. `NNN` = zero-padded 3-digit sequential counter computed from the highest existing `reports/NNN-*.md` file (scan + max + 1). Resets are manual (not auto). Same-day same-zpid: append a `-r2`/`-r3` suffix only after the same-day same-zpid duplicate is detected.

### Eval fixture + oracle (SC-6)

- **D-15-EVAL-01 (fixture location):** New directory `evals/fixtures/property/`. Holds:
  - `sfh_conforming_001.json` — extracted PropertyListing JSON (no HTML), synthetic per Phase 11 D-02 (synthetic source_url + zpid="1" + fetched_at).
  - `sfh_conforming_001.html` — tiny synthetic HTML stub (≤2KB) containing only the `__NEXT_DATA__` block with the same JSON payload — exercises the extractor recipe without committing a real Zillow page.
- **D-15-EVAL-02 (single eval prompt for v1.1):** `evals/prompts/property-analysis-01.md` exercises the JSON→analysis→report path end-to-end. NO live WebFetch in eval mode (Phase 11 D-02 + Phase 12 contract). The prompt feeds the extracted JSON directly to the orchestrator and asserts on report content.
- **D-15-EVAL-03 (oracle pins 3 numerics + verdict):** Oracle pins:
  1. `verdict.level` — exact string match (ROADMAP SC-6).
  2. Conv30 cell PITI at `household.preferred_down_payment_pct` — anchors the headline number; catches matrix drift.
  3. `verdict.reasons` count — exact integer; catches cascade mis-fires (extra/missing reason rows).
  4. `tax_block.first_year_interest` — anchors the IRS Pub 936 path through amortize.build_schedule.
  Gate: route_match (matrix shape + section presence) ≥ 0.95 AND numeric_match (the 3 numerics within tolerance) ≥ 0.95 (ROADMAP SC-6).

### Claude's Discretion

- **Report header layout:** ROADMAP says "header (address / price / Zestimate delta / tax-HOA-insurance escrow)" — the exact field ordering and any additional metadata (zpid, fetched_at, FRED-rate snapshot, household snapshot hash) is the planner's call. Recommend including FRED rate snapshot + household_snapshot_hash for auditability.
- **VERDICT section copy:** ROADMAP locks the verdict-cascade behavior; the prose around it (intro sentence, formatting of `verdict.reasons[]` items) is the planner's call. CONTEXT.md (Phase 14, D-14-VERDICT-04) requires predicate_code + computed_value on every reason — the formatter just renders them.
- **Truncation of long blocker_reasons in matrix cells:** D-15-MATRIX-02 says "first blocker code" — exactly how to display when there are 3+ blockers per cell is the planner's choice (recommend: show first code, append `+N more` suffix).
- **Token budget for SKILL.md edit:** D-15-ROUTE-03 says the existing 9 rows shift down. The planner verifies the new SKILL.md stays ≤4500 cl100k tokens (MODE-02 hard limit).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 15 planning artifacts (this phase)
- `.planning/REQUIREMENTS.md` — MODE-01..03, RPRT-01..02 (pending → must close in Phase 15)
- `.planning/ROADMAP.md` §"Phase 15: `property` Skill Mode + Report Formatter" — 6 success criteria
- `.planning/PROJECT.md` — math-correctness-first principle; v1.1 milestone scope

### Prior-phase decisions (carry forward)
- `.planning/phases/14-property-analysis-pipeline/14-CONTEXT.md` — D-14-MATRIX-01..03 (matrix shape Phase 15 consumes), D-14-VERDICT-04 (predicate+computed citation Phase 15 renders)
- `.planning/phases/14-property-analysis-pipeline/14-VERIFICATION.md` — confirms AnalysisReport schema frozen
- `.planning/phases/13-property-ingestion/13-CONTEXT.md` — PropertyListing Pydantic shape (input to scripts/property_analyze.py)
- `.planning/phases/12-fred-eval/12-CONTEXT.md` — D-12-LIVE02-01 always-exit-0 envelope; pure-compute scripts (no network)
- `.planning/phases/11-subagents/` — D-11-D-02 synthetic-only-in-CI fixture policy; stress-test-agent ≤1000-token markdown summary precedent (RPRT-01 mirrors this)
- `.planning/phases/10-claude-skill/10-CONTEXT.md` — D-09 progressive disclosure (modes/*.md cross-ref pattern); SKILL.md ≤4500 cl100k token budget

### Existing code Phase 15 EXTENDS or READS
- `.claude/skills/mortgage-ops/SKILL.md` — current 9-row routing precedence table (Phase 15 inserts Row 0)
- `.claude/skills/mortgage-ops/modes/evaluate.md` — analog for the new modes/property.md (two-script composition pattern; modes/property.md is one-script composition)
- `.claude/skills/mortgage-ops/modes/_shared.md` — load-first convention (modes/property.md must also load _shared.md first)
- `lib/property_analysis.py` (Phase 14) — `analyze()` entrypoint; AnalysisReport contract
- `lib/property_listing.py` (Phase 13) — PropertyListing model (orchestrator input)
- `lib/household.py`, `lib/profile.py` (Phase 14) — input contracts for orchestrator
- `scripts/amortize.py`, `scripts/stress_test.py`, etc. — existing CLI patterns Phase 15 mirrors

### External references (research domain)
- `.planning/research/v1.1-property-analysis.md` §"Pattern 1: Zillow HTML extraction" — the WebFetch + `__NEXT_DATA__` extractor prompt template for modes/property.md to embed verbatim
- `evals/runner.py` + `evals/metrics.py` — existing eval harness Phase 15 hooks into
- `evals/prompts/amortize-01.md` — analog eval prompt structure (oracle field pinning)
- `reports/` — destination directory (created if absent; mirrors Phase 11 report-emit precedent)

### What NOT to consult
- Phase 14's threat model `<threat_model>` blocks — Phase 15 inherits the contract but does not need to re-verify the math threats.
- Real Zillow HTML captures from `.planning/research/` — those are research artifacts, NOT fixtures; Phase 15 creates clean synthetic fixtures.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`lib/property_analysis.py:analyze()`** — Phase 14's frozen entry point. Phase 15's orchestrator script loads Listing/Household/Profile from disk, calls `analyze()`, then passes the resulting `AnalysisReport` to `lib/property_report.py:render()`.
- **`AnalysisReport` Pydantic model** — Already strict/frozen/extra=forbid. Phase 15 ONLY reads it; does not mutate.
- **`scripts/amortize.py` envelope pattern** — Phase 15 orchestrator mirrors: argparse → load JSON → validate Pydantic → compute → emit JSON envelope on stdout, always exit 0.
- **`scripts/_generate_arm_fixtures.py`** — Underscore-prefixed dev-only helper precedent. Phase 15 may ship `_generate_property_fixtures.py` if hand-crafting synthetic JSON gets repetitive (planner's call).
- **`evals/runner.py` + `evals/metrics.py`** — `route_match` + `numeric_match` already implemented. Phase 15 adds one prompt + one fixture; no harness changes needed.

### Established Patterns
- **Modes/*.md load `_shared.md` first** (Phase 10 D-09). `modes/property.md` MUST also start with this.
- **Phase 12 always-exit-0** for scripts. Phase 15 orchestrator stdout JSON envelope: `{"report_path": "...", "verdict": "...", "error": null|{...}}`.
- **Reports written to `reports/` with `{NNN}-{kind}-{key}-{date}.md` naming** (Phase 11 amortization-agent precedent). Phase 15 uses `kind=property`, `key=zpid`.
- **Synthetic-only fixtures in CI** (Phase 11 D-02). Eval fixture in `evals/fixtures/property/` is synthetic, NOT a real Zillow capture.
- **Decimal-as-string in JSON I/O** (CLAUDE.md money discipline). Orchestrator input + output preserves this.
- **Citation footer style** (Phase 11 stress-test-agent precedent): italicized line, prefix `*Computed by:*`, full re-runnable command.

### Integration Points
- **SKILL.md routing table** — Phase 15 inserts Row 0 (zillow.com URL-pin) above the existing 9 rows; existing rows renumber but otherwise unchanged.
- **modes/ directory** — Phase 15 adds `property.md`; no other mode files touched.
- **scripts/ directory** — Phase 15 adds `property_analyze.py`; no other scripts touched.
- **lib/ directory** — Phase 15 adds `property_report.py`; lib/property_analysis.py from Phase 14 is READ-ONLY this phase.
- **evals/ directory** — Phase 15 adds one prompt + one fixture directory; runner.py + metrics.py untouched.
- **reports/ directory** — Phase 15 may need to CREATE this directory if it doesn't exist (orchestrator should `mkdir -p`).

</code_context>

<specifics>
## Specific Ideas

- **Falsifiable verdict copy continues:** Phase 14's verdict reasons (`<PREDICATE>: <value> (program=X, dp=Y)`) flow into Phase 15 as-is. The report formatter does NOT rewrite or paraphrase them. The user's strong preference for "verdict copy is short and falsifiable" (Phase 4 / Phase 8 lineage) is honored by passthrough.
- **Two-step matrix readability:** With 5 rows × 6 cols and PITI inline, the table is wide. The planner should consider whether to wrap the PITI value with thousands separators (`$2,528` not `$2528`) and use compact eligibility marks (`✓` / `✗`) to minimize cell width.
- **Preferred-DP column callout:** Beyond just bolding the column header, consider a small `→` arrow or `(your DP)` annotation under the column header in the markdown source. Subtle but the user's eye should land there first.
- **Mode body example dialog:** `modes/property.md` should include a worked example showing the URL → WebFetch extraction prompt → JSON validation → gap-fill question → orchestrator invocation → report file path → user-facing summary. Pattern mirrors `modes/evaluate.md` worked-example precedent.

</specifics>

<deferred>
## Deferred Ideas

- **DuckDB `analyzed_listings` persistence in Phase 15** — Phase 13 already ships the table. Writing the analysis row from Phase 15 is plausible but NOT in this phase's scope (no requirement IDs cover it). Belongs in a follow-up milestone (v1.2 watchlist mode) where the persistence enables querying.
- **Comparable-property lookup integrated in report** — out of scope per PROJECT.md (v1.2+).
- **Multi-property side-by-side rendering** — out of scope per PROJECT.md.
- **Paid scraper API fallback when WebFetch fails** — research notes Apify / ScrapingBee as v1.2 candidates. Phase 15 stays with WebFetch + interactive gap-fill.
- **PDF export of the markdown report** — markdown is the v1.1 output; PDF rendering is downstream tooling.
- **Real Zillow HTML capture in evals/** — Phase 11 D-02 forbids this in CI. If we ever want real-fidelity testing, it goes in a separate `tests/manual/` directory that CI skips.
- **Watchlist mode (saved analyses by criteria)** — explicitly deferred to v1.2 per PROJECT.md.

</deferred>

---

*Phase: 15-property-skill-mode-report-formatter*
*Context gathered: 2026-05-20*

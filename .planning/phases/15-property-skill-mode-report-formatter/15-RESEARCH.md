# Phase 15: `property` Skill Mode + Report Formatter — Research

**Researched:** 2026-05-20
**Domain:** Claude-skill mode wiring + Pydantic-AnalysisReport-to-markdown formatter + Phase 12 always-exit-0 orchestrator + eval-harness fixture authoring
**Confidence:** HIGH

## Summary

Phase 15 is the v1.1 closing-act for the property-analysis milestone: it wires the already-shipped `lib.property_analysis.analyze()` pipeline (Phase 14, 7/7 SCs verified, AnalysisReport frozen) into the Claude skill via a new `modes/property.md`, ships `scripts/property_analyze.py` as the always-exit-0 orchestrator, and renders the AnalysisReport into a one-page markdown report at `reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md`. Every dollar in the report carries a `*Computed by: scripts/property_analyze.py ...*` footer (one per section, 6 total). A single new eval prompt (`evals/prompts/property-analysis-01.md`) pins the route + 3 numerics + verdict against a synthetic Zillow fixture. No new calc primitives ship; this phase is pure composition + rendering + UX wiring.

The single biggest planner-actionable risk surfaces in the orchestrator input layer: `config/household.yml` carries the Phase 4 multi-applicant nested schema, but `lib.household.Household` (Phase 14) is a flat single-snapshot model — there is **no existing `from_yaml()` adapter and no precedent script that loads either model from disk** [VERIFIED: grep `yaml.safe_load|from_yaml|load_household` across `lib/` and `.claude/skills/mortgage-ops/scripts/` returned only `lib/rules/_loader.py`]. Phase 15 must invent this mapping; the existing example YAML is multi-applicant and incompatible with Phase 14's flat Household. The CLI envelope, mode-routing, citation convention, and matrix-rendering layers are all mechanical — but the household-yaml-shape mismatch is load-bearing.

**Primary recommendation:** Plan the orchestrator in 4 layers — (1) YAML-to-Pydantic loaders for household.yml/profile.yml that map Phase-4 schema → Phase-14 `Household`/`Profile` (aggregate income, take min FICO, default `preferred_down_payment_pct=0.20`); (2) PropertyListing JSON load + Pydantic validation (already exists via Phase 13 `PropertyListing.model_validate_json`); (3) thin call to `lib.property_analysis.analyze()`; (4) `lib/property_report.render(AnalysisReport) -> str` markdown formatter. Mode body owns the WebFetch+gap-fill loop (per Pattern 1 in `.planning/research/v1.1-property-analysis.md`) and writes the listing JSON tempfile that the orchestrator consumes.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Zillow URL detection + dispatch routing | Claude skill (SKILL.md) | — | Routing is the skill's job; URL-pin trigger is a substring/phrase check in the routing table (D-15-ROUTE-01..03). |
| WebFetch + `__NEXT_DATA__` extraction + gap-fill UX | Claude mode body (`modes/property.md`) | — | Mode body is Claude+WebFetch territory by D-15-ORCH-02. Orchestrator never sees a URL. |
| PropertyListing Pydantic validation (input gate) | Python orchestrator (scripts/property_analyze.py) | — | Schema gate at the script boundary, Phase 3 D-19 + Phase 13 contract. |
| Multi-program × DP matrix math, stress, refi, points, tax, verdict | Phase 14 lib (`lib/property_analysis.py:analyze`) | — | Frozen Phase 14 surface; Phase 15 imports and calls; never recomputes. |
| AnalysisReport → markdown rendering | Phase 15 lib (`lib/property_report.py`) | — | Pure formatter (Decimal-aware, locale-free, deterministic). Separated from the orchestrator script for testability (Plan 14-02 PATTERNS.md L461 co-location idiom inverted: formatter is its own module since it's downstream of analyze()). |
| Filename sequencing (NNN-property-{zpid}-{date}.md) | Python orchestrator | — | Orchestrator scans `reports/` for max NNN, increments, writes; same-day-same-zpid suffix `-r2`/`-r3` per D-15-ORCH-04. |
| Always-exit-0 envelope + stderr 6-key Pydantic error format | Python orchestrator | — | Phase 12 D-12-LIVE02-01 inherited contract; mirrors `scripts/amortize.py` + `scripts/property_fetch.py`. |
| Eval scoring (route_match + numeric_match) | `evals/runner.py` + `evals/metrics.py` | — | Already shipped Phase 12; Phase 15 only adds a prompt + oracle JSON pair. No harness changes. |
| DuckDB persistence of analyzed_listings rows | OUT OF SCOPE (deferred per CONTEXT) | — | Phase 13 ships the table; Phase 15 writes only the markdown file, NOT the DB row. v1.2 watchlist mode handles that. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | ≥2.13 | Validate PropertyListing JSON input, AnalysisReport schema round-trip | Already the project's strict-mode boundary library; AnalysisReport is `ConfigDict(strict=True, frozen=True, extra="forbid")` per Phase 14. |
| `pyyaml` (`yaml.safe_load`) | shipped via `lib/rules/_loader.py` pattern | Parse `config/household.yml` + `config/profile.yml` | Project-wide YAML loader convention; `lib/rules/_loader.py:70` is the only existing call site. |
| `frontmatter` | (already in evals/runner.py) | Parse eval prompt frontmatter | Already in use by `evals/runner.py:31`; Phase 15 oracle prompt mirrors the amortize-01 shape. |
| stdlib `argparse` + `pathlib` + `json` + `re` + `datetime` | Python 3.12 | CLI shell, JSON envelope, NNN counter regex, ISO date | Phase 3 D-18 (lazy imports after argparse for fast `--help`); Phase 10 `scripts/_cli_helpers.py` provides argparse boilerplate. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tiktoken` (cl100k) | — | Verify SKILL.md token budget after Row 0 insertion (≤4500 cl100k) | One-off measurement step in Wave 0 or a Wave 5 test (test asserts `len(enc.encode(open(SKILL.md).read())) <= 4500`). Phase 10 used the same idiom. |
| `freezegun` (already in pyproject dev deps from Phase 12) | — | Pin `analyzed_at`/`fetched_at` timestamps for golden-report regression | Eval fixture relies on deterministic timestamps; Phase 12 D-04-04 established this. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Module-level Python markdown templates in `lib/property_report.py` | Jinja2 templates under `lib/templates/property_report.md.j2` | Jinja adds a runtime dep + template-vs-code split for a one-template feature. Reject — keep markdown as f-strings/concatenation in pure Python (matches `lib/affordability.py` blocker-cascade prose pattern). |
| Per-primitive citation footers (`amortize.py`, `stress_test.py`, ...) | — | Rejected by D-15-CITATION-02: user can't actually re-run those primitives standalone and get the matrix back. Orchestrator-only footers preserve reproducibility. |
| Apify / scraping-bee paid fallback for Zillow ingestion | — | Rejected by Phase 13 D-13-MODEL-01 + research §"Pitfalls / Open Questions Q7" — v1.2 only. |

**Installation:** No new third-party deps. `pyyaml`, `pydantic`, `frontmatter`, `freezegun` all already in `pyproject.toml` (Phases 1, 12). `tiktoken` may already be present from Phase 10 token-budget testing — Wave 0 should verify (`uv pip show tiktoken`).

**Version verification:** Phase 15 introduces no new runtime libraries. `pydantic≥2.13` and `numpy-financial` versions are already pinned. Confidence: HIGH that no `npm view` / `pip index versions` is required.

## Architecture Patterns

### System Architecture Diagram

```
                ┌──────────────────────────────────────────────────────────┐
                │                  Claude (main thread)                    │
                │                                                          │
   USER ───────▶│  1. URL substring "zillow.com" OR "analyze listing"      │
   prompt       │     ↓ (SKILL.md Row 0; D-15-ROUTE-01)                    │
                │  2. Load modes/_shared.md, modes/property.md             │
                │  3. WebFetch(url, prompt=__NEXT_DATA__ extractor)        │
                │     ↓ Pattern 1 prompt from v1.1-research                │
                │  4. Pydantic validate via PropertyListing.model_validate │
                │  5. Interactive gap-fill (price/zip/property_type MUST)  │
                │  6. Write /tmp/listing-{uuid}.json                       │
                │  7. Bash: python scripts/property_analyze.py \           │
                │       --listing /tmp/listing.json \                      │
                │       --household config/household.yml \                 │
                │       --profile config/profile.yml \                     │
                │       --output-dir reports/                              │
                └──────────────────────────────────────────────────────────┘
                                            │
                                            ▼
                ┌──────────────────────────────────────────────────────────┐
                │             scripts/property_analyze.py                  │
                │             (Python subprocess; always exits 0)          │
                │                                                          │
                │  Step A — argparse (--help fast; lazy imports after)     │
                │  Step B — load PropertyListing JSON; Pydantic validate   │
                │            (6-key envelope on stderr if invalid)         │
                │  Step C — load household.yml → Phase-14 Household        │
                │            ★ map multi-applicant → flat snapshot         │
                │  Step D — load profile.yml → Phase-14 Profile            │
                │  Step E — call lib.property_analysis.analyze(...)        │
                │            → AnalysisReport                              │
                │  Step F — call lib.property_report.render(report)        │
                │            → markdown str                                │
                │  Step G — scan reports/ for max NNN; compute filename    │
                │            same-day same-zpid → -r2/-r3 suffix           │
                │  Step H — write file; emit stdout envelope:              │
                │   {"report_path": "...", "verdict": "GO",                │
                │    "error": null}                                        │
                │                                                          │
                │  ALL exceptions → catch, emit error envelope, exit 0     │
                │  Argparse usage errors → exit 2 (Phase 12 documented)    │
                └──────────────────────────────────────────────────────────┘
                                            │
                                            ▼
                ┌──────────────────────────────────────────────────────────┐
                │                  lib/property_report.py                  │
                │                  (pure renderer, no I/O)                 │
                │                                                          │
                │  render(report: AnalysisReport) -> str                   │
                │    Section 1: Header (address, price, Zestimate δ,       │
                │               escrow snapshot, household_snapshot_hash)  │
                │    Section 2: ## YOUR FIT — 5×6 matrix (Program × DP%)   │
                │               each cell = "$X,XXX/mo ✓" or "$X,XXX ✗     │
                │               (BLOCKER-CODE)"; preferred-DP col bold;    │
                │               footer per D-15-CITATION-01                │
                │    Section 3: ## RATE STRESS — stress.rows table         │
                │               (program / kind / baseline_piti /          │
                │               stressed_piti / stressed_dti / breaches)   │
                │    Section 4: ## POINTS BREAKEVEN — points.rows table    │
                │    Section 5: ## REFI OPPORTUNITY — refi.rows table      │
                │               (minus_100bps + fred_times_0_85)           │
                │    Section 6: ## TAX — IRS Pub 936 block (first-year     │
                │               interest, $750k cap flag)                  │
                │    Section 7: ## VERDICT — level + headline +            │
                │               reasons[] (predicate_code + computed_val)  │
                │    Each section ends with italic citation footer.        │
                └──────────────────────────────────────────────────────────┘
                                            │
                                            ▼
                       reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md
                       Claude reads back, narrates path + verdict to user.
```

### Recommended Project Structure

```
.claude/skills/mortgage-ops/
├── SKILL.md                            # MODIFIED: insert Row 0 for zillow.com / analyze listing
└── modes/
    ├── _shared.md                      # READ-ONLY (load-first convention)
    └── property.md                     # NEW: mode body — WebFetch + gap-fill + orchestrator dispatch

scripts/                                # NEW: project-root scripts (NOT under .claude/skills/)
└── property_analyze.py                 # NEW orchestrator
                                        # Note: CONTEXT specifies project-root scripts/, mirroring
                                        # scripts/_generate_arm_fixtures.py pattern (dev-only helpers
                                        # at project root). Other v1.0 calc CLIs live under
                                        # .claude/skills/mortgage-ops/scripts/ — Phase 15
                                        # orchestrator is NOT a skill-internal primitive; it composes
                                        # primitives and orchestrates DuckDB-adjacent I/O. Planner
                                        # decides whether to colocate inside the skill folder for
                                        # consistency or place at project root for orchestration-tier
                                        # alignment. Recommend: project root, since the orchestrator
                                        # depends on lib/property_analysis (which lives at project
                                        # root) and writes to reports/ (project root).

lib/
├── property_analysis.py                # READ-ONLY (Phase 14, frozen)
├── property_listing.py                 # READ-ONLY (Phase 13)
├── property_verdict.py                 # READ-ONLY (Phase 14)
├── household.py                        # READ-ONLY (Phase 14 flat snapshot)
├── profile.py                          # READ-ONLY (Phase 14 preferences)
└── property_report.py                  # NEW: AnalysisReport → markdown formatter

evals/
├── prompts/
│   └── property-analysis-01.md         # NEW: route + numeric anchor prompt
├── expected/
│   └── property-analysis-01.json       # NEW: oracle (3 numerics + verdict.level)
└── fixtures/
    └── property/                       # NEW directory
        ├── sfh_conforming_001.json     # NEW: extracted PropertyListing fixture
        └── sfh_conforming_001.html     # NEW: 2KB synthetic HTML stub with __NEXT_DATA__

reports/                                # MAY-CREATE-IF-ABSENT (already exists per `ls`)
└── (gitignored; orchestrator writes here)
```

### Pattern 1: Mode Body — WebFetch + Gap-Fill + Orchestrator Dispatch

**What:** `modes/property.md` instructs Claude to detect the URL, WebFetch with the extractor prompt, validate, gap-fill, then invoke `scripts/property_analyze.py`.

**When to use:** Always — Phase 15 ships exactly one mode body for this trigger.

**Example structure (mirrors `modes/evaluate.md`):**

```markdown
# Mode: property — Zillow listing → underwriting workup

Loaded by SKILL.md routing (Row 0) when the prompt contains a `zillow.com`
substring OR the literal phrase `analyze listing`. Read `modes/_shared.md`
FIRST (D-10), then this file.

## When to invoke

Route here when (a) the user pasted a Zillow URL OR (b) said "analyze
listing". The URL-pin wins over refi/afford/stress/arm/amortize verbs
(D-15-ROUTE-01).

If only "analyze listing" with no URL: ask "Sure — paste the Zillow URL".

## Ingestion subroutine

Step 1. WebFetch the user-supplied URL with the extractor prompt:
        (verbatim from `.planning/research/v1.1-property-analysis.md`
        Pattern 1, lines 100-138 — embed verbatim).

Step 2. Parse the WebFetch response as JSON. Check for sentinel keys:
        - `_block_detected: true` → narrate captcha/block; switch to manual
        - `_truncated: true` → narrate WebFetch truncation; switch to manual

Step 3. Validate via Pydantic round-trip:
        `python -c "from lib.property_listing import PropertyListing; \
                   PropertyListing.model_validate_json(open('/tmp/listing.json').read())"`
        On error, surface the 6-key envelope; ask user to fix or paste manually.

Step 4. Interactive gap-fill for MUST-HAVE fields (price, zip, property_type)
        if any are null. ONE question per missing field; user types value;
        merge with `provenance: user_provided` tagging.

Step 5. Write the validated listing JSON to /tmp/listing-{uuid}.json.

## Orchestrator dispatch

Invoke the orchestrator:

```bash
python scripts/property_analyze.py \
  --listing /tmp/listing-{uuid}.json \
  --household config/household.yml \
  --profile config/profile.yml \
  --output-dir reports/
```

Parse stdout JSON envelope. On `error != null`, narrate the error code +
message. On success, narrate:

> Saved underwriting report to **reports/NNN-property-{zpid}-{date}.md**.
> Verdict: **{verdict.level}** — {verdict.headline_reason}.
> *(computed by scripts/property_analyze.py at {fetched_at})*

## Edge cases

- WebFetch 403 / captcha → fall back to "paste these 13 fields manually"
- No `__NEXT_DATA__` → same fallback
- Pydantic validation fails after gap-fill → narrate the 6-key envelope
  field-by-field; offer to retry
- Orchestrator emits `error.code == "household_yaml_invalid"` →
  point user to config/household.example.yml; do NOT auto-edit
- `error.code == "fred_cache_cold"` → narrate, suggest
  `python .claude/skills/mortgage-ops/scripts/fred_cli.py get MORTGAGE30US --latest`

## RELATED REFERENCES (load on demand only — D-09)

- `references/property-analysis.md` (Phase 18 — ships ≥250 lines doc)
- `.planning/research/v1.1-property-analysis.md` for full pattern derivation
```

### Pattern 2: Orchestrator Envelope (Phase 12 always-exit-0)

**What:** stdout JSON; ALWAYS exit 0 (except argparse usage errors → exit 2).

**Source:** `.claude/skills/mortgage-ops/scripts/fred_cli.py:_emit()`, `scripts/property_fetch.py` (envelope shapes 1/2/3), Phase 12 D-12-LIVE02-01.

**Success envelope:**
```json
{
  "report_path": "reports/001-property-12345678-2026-05-20.md",
  "verdict": "GO",
  "error": null
}
```

**Error envelope:**
```json
{
  "report_path": null,
  "verdict": null,
  "error": {
    "code": "household_yaml_invalid|profile_yaml_invalid|listing_validation_failed|fred_cache_cold|missing_county_data|analyze_internal_error|output_dir_unwritable",
    "message": "human-readable detail"
  }
}
```

**Pydantic 6-key envelope on stderr (only for `listing_validation_failed`):**
```json
[{"type": "<error_type>", "loc": [...], "msg": "...", "input": "...",
  "url": "https://errors.pydantic.dev/{MAJOR.MINOR}/v/{type}", "ctx": {...}}]
```

(Source: `scripts/amortize.py` lines 36-60 — verbatim docstring of the 6-key contract.)

### Pattern 3: Markdown Report Layout

**Source:** Synthesizing CONTEXT D-15-MATRIX-01..04 + D-15-CITATION-01..03 + ROADMAP SC-4 (sections: Header + YOUR FIT + RATE STRESS + POINTS BREAKEVEN + REFI OPPORTUNITY + TAX + VERDICT).

```markdown
# Property Analysis: {listing.address or "ZPID {zpid}"}

| Field | Value |
|-------|-------|
| Listed price | $625,000.00 |
| Zestimate | $612,400.00 *(estimated; -2.0% vs list)* |
| Tax / Insurance / HOA (monthly) | $500.00 / $100.00 / $0.00 |
| ZIP | 98101 (King County, WA) |
| FRED 30yr / 15yr | 6.500% / 5.800% (cached 2026-05-20) |
| Household snapshot hash | `a7f2b9c1...` (8-char prefix) |
| Fetched at | 2026-05-20T14:32:11Z |

## YOUR FIT (Program × Down Payment)

| Program  |  3% DP  |  5% DP  | 10% DP | 15% DP | **20% DP** *(your DP)* | 25% DP |
|----------|---------|---------|--------|--------|------------------------|--------|
| Conv30   | $X,XXX/mo ✗ (DTI-CEILING-CONV) | $X,XXX/mo ✗ (LTV-CAP) | $X,XXX/mo ✓ | $X,XXX/mo ✓ | **$X,XXX/mo ✓** | $X,XXX/mo ✓ |
| Conv15   | $X,XXX/mo ✗ (DTI-CEILING-CONV) | ... | ... | ... | **$X,XXX/mo ✓** | ... |
| FHA30    | $X,XXX/mo ✓ | ... | ... | ... | **$X,XXX/mo ✓** | ... |
| (VA30 row only if profile.va_eligible)                                        |
| (Jumbo30 row only if listing.price > county conforming limit)                 |

*Computed by: scripts/property_analyze.py --listing /tmp/listing-abc.json --household config/household.yml --profile config/profile.yml --output-dir reports/*

## RATE STRESS

| Program | Stress | Baseline PITI | Stressed PITI | Stressed DTI | Breaches ceiling? |
|---------|--------|---------------|---------------|--------------|-------------------|
| Conv30  | +200bps rate shock | $X,XXX.XX | $X,XXX.XX | 41.5% | No |
| Conv30  | -30% income shock | $X,XXX.XX | (n/a) | 51.2% | **Yes (CONV ceiling 50.0%)** |
| Conv30  | ARM-5/1 reset @ peak cap | $X,XXX.XX | $X,XXX.XX | 47.0% | No |
| Conv15  | ... | ... | ... | ... | ... |

*Computed by: scripts/property_analyze.py {same full invocation}*

## POINTS BREAKEVEN

| Program | Points | Rate drop | Simple breakeven | NPV breakeven | Note |
|---------|--------|-----------|------------------|---------------|------|
| Conv30  | 1pt | 25bps | 42 mo | 48 mo | — |
| Conv30  | 2pt | 50bps | 38 mo | 43 mo | — |
| FHA30   | 1pt | — | — | — | WARNING-NO-POINTS-FOR-FHA-VA |
| ...     |     |   |    |    |   |

*Computed by: scripts/property_analyze.py {same}*

## REFI OPPORTUNITY

| Program | Scenario | Target rate | Monthly savings | Breakeven months | 60-mo NPV |
|---------|----------|-------------|-----------------|------------------|-----------|
| Conv30  | -100bps | 5.500% | $250.00 | 24 | $5,432.10 |
| Conv30  | FRED × 0.85 | 5.525% | $238.50 | 25 | $5,187.40 |
| ...     | ...     | ...   | ... | ... | ... |

*Computed by: scripts/property_analyze.py {same}*

## TAX (IRS Pub 936)

- First-year deductible interest (Conv30 at preferred DP): **$32,335.43**
- Qualified loan limit (filing_status=mfj): **$750,000.00**
- Over-cap flag: No
- Marginal-tax savings: (computed if profile.marginal_tax_rate is set; else "see CPA")

*Computed by: scripts/property_analyze.py {same}*

## VERDICT — **GO**

**Headline:** 2 non-FHA program(s) eligible at preferred DP 20.0%

- `GO-ALL-GREEN`: 2 (count of non-FHA eligible programs at preferred DP)

(If level=WATCH or NO_GO, reasons[] expands with predicate_code + computed_value
per VerdictReason model. Each reason renders as a bullet.)

*Computed by: scripts/property_analyze.py {same}*
```

### Pattern 4: SKILL.md Row 0 Insertion

**Current routing block (verbatim, SKILL.md L23-30):**

```
| Input pattern | Mode | Script |
|---|---|---|
| Single loan + payment question | `evaluate` | `scripts/amortize.py` + `lib.affordability` composition |
| Multiple offers, "compare", "rank by NPV" | `compare` | `scripts/refi_npv.py` per offer |
| "refi", "refinance", "should I refi" | `refinance` | `scripts/refi_npv.py` |
| "afford", "qualify", "max loan", "DTI" | `affordability` | `scripts/affordability.py` |
| "stress", "shock", "what if rates jump", "sweep" | `stress` | `scripts/stress_test.py` |
| "amortization schedule", "amortize", "extra principal" | `amortize` | `scripts/amortize.py` |
| "ARM", "5/1", "7/1", "10/1", "5/6", "SOFR ARM" | `arm` | `scripts/arm_simulate.py` |
```

**Current precedence ordering (verbatim, SKILL.md L37-47):**

```
1. Explicit sub-command           → `/mortgage-ops {mode}`
2. "refinance" / "refi" verb      → `refinance` (overrides arm/amortize/stress vocabulary)
3. "afford" / "borrow" verb       → `affordability` (overrides amortize)
...
```

**Phase 15 inserts at the TOP of routing table AND precedence:**

```
| Zillow URL substring (`zillow.com`) OR phrase "analyze listing" | `property` | `scripts/property_analyze.py` |
```

Precedence becomes:
```
0. URL pin: `zillow.com` substring OR phrase "analyze listing"
                                  → `property` (HIGHEST — overrides ALL verbs and explicit slash-commands)
1. Explicit sub-command           → `/mortgage-ops {mode}`
2. "refinance" / "refi" verb      → `refinance` (overrides arm/amortize/stress)
...  (existing numbering shifts down by one)
```

### Anti-Patterns to Avoid

- **Computing the matrix or PITI inside `lib/property_report.py`.** The formatter is PURE rendering — no math, no Decimal arithmetic beyond display formatting. CLAUDE.md money discipline is non-negotiable: Phase 14's analyze() is the source of every number.
- **Per-cell or per-row citation footers.** D-15-CITATION-01 locks "exactly 6 footers, one per section." Per-cell footers would make the matrix unreadable.
- **Citing per-primitive scripts (`scripts/amortize.py`, `scripts/stress_test.py`).** D-15-CITATION-02 forbids this — those scripts can't reproduce the matrix standalone. Cite the orchestrator only.
- **Adding `tax_block.first_year_interest` to the YOUR FIT matrix.** It belongs in `## TAX`; matrix is PITI + eligibility flag only.
- **Letting the orchestrator import Anthropic SDK or call WebFetch.** D-15-ORCH-01 says scripts are pure compute (Phase 12 inheritance). WebFetch is mode-body territory.
- **Auto-writing analyzed_listings DuckDB row in Phase 15.** Out of scope; deferred to v1.2 watchlist mode. Phase 15 writes the markdown file ONLY.
- **Hand-rolling a markdown table formatter.** Decimal-aware Python string interpolation with `:,.2f` for money + `:.1%` for ratios suffices; respect D-NUM-01..04 from `_shared.md`. Do NOT introduce `tabulate` or `rich`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AnalysisReport / PropertyListing schema validation | Custom dict checks | `AnalysisReport.model_validate_json` / `PropertyListing.model_validate_json` | Phase 13/14 already shipped strict Pydantic; rebuilding validation duplicates `frozen=True / extra="forbid"`. |
| 6-key Pydantic envelope on stderr | Custom error JSON | `e.json()` pass-through (see `scripts/amortize.py:36-60` for the verbatim contract) | Phase 3 WR-02 closure shipped this idiom; Phase 13 + Phase 12 use it; eval harness depends on it. |
| Eval metrics (route_match, numeric_match) | New scoring logic | Existing `evals/metrics.py` + `evals/runner.py` (Phase 12 — no harness changes per CONTEXT) | Phase 12 D-12-SC3-01 + D-12-SC4-01 contracts already validated; Phase 15 only adds a prompt + oracle pair. |
| Sequential NNN counter | Hand-rolled DB query or filesystem walk inline | `_next_seq()` helper that scans `reports/*.md` with regex `^(\d{3})-` and returns max+1; same-day-same-zpid detection appends `-r2`/`-r3` suffix | Mirrors Phase 10 D-13-02 filename pattern; logic is 15 lines. Don't reach for DuckDB — `reports/` filename scan is the source of truth (D-15-ORCH-04). |
| Markdown table rendering | Hand-rolled column-width computation | f-string + Python format-spec (`f"{val:,.2f}"`) inside `\| {a} \| {b} \|` rows | GitHub Flavored Markdown is column-width-tolerant; one Python f-string per row is 30 lines for a 5×6 matrix. |
| Zillow `__NEXT_DATA__` extraction logic | Direct Python parsing in the orchestrator | WebFetch+Haiku prompt from `.planning/research/v1.1-python-analysis.md` Pattern 1 (embedded VERBATIM in `modes/property.md`) | D-15-ORCH-02: extraction lives in Claude+WebFetch territory. Orchestrator never sees URL or HTML. |
| YAML loading + multi-applicant→flat mapping | Custom complex YAML walker | `yaml.safe_load(path.read_text())` then explicit field-by-field mapping (15-line function) | `lib/rules/_loader.py:70` is the existing precedent; map: `sum(applicants[i].gross_monthly_income) → monthly_income`; `min(applicants[i].credit_score) → fico`; etc. |

**Key insight:** Phase 15 is composition + rendering. Every primitive needed already ships (Phase 13/14 Pydantic models, Phase 12 always-exit-0 envelope, Phase 12 eval harness). The only NEW logic is: YAML→Pydantic mapping, markdown formatter, NNN sequencer, and a 5×6 matrix renderer. Anything beyond that is over-building.

## Runtime State Inventory

> Not a rename/refactor phase — section limited to additive-state checks.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `reports/` directory already exists (`ls /Users/cujo253/Documents/mortgage-ops/reports` returned path; contents empty or gitignored). DuckDB `analyzed_listings` table shipped Phase 13 but Phase 15 DOES NOT write to it (deferred to v1.2). | None — orchestrator writes new .md files; no DB row written. |
| Live service config | None — orchestrator is pure compute, no external services. | None. |
| OS-registered state | None. | None. |
| Secrets/env vars | `ANTHROPIC_API_KEY` (for Phase 13 Sonnet extractor) is NOT needed by Phase 15 (orchestrator does not call Anthropic SDK). `FRED_API_KEY` is consumed by `lib.fred_cache` only when cache is cold — Phase 15 inherits Phase 12's "cache-first, error if cold" path. | None — orchestrator emits `error.code == "fred_cache_cold"` if cache absent; mode body narrates the recovery command. |
| Build artifacts | None — no new packages installed. | None. |

**Nothing found in category:** "OS-registered state" — verified by inspection of Phase 13/14 install footprint (no Task Scheduler / launchd / systemd entries shipped).

## Common Pitfalls

### Pitfall 1: SKILL.md token-budget overflow on Row 0 insertion

**What goes wrong:** Adding the new routing row, the new precedence row, and the cross-reference paragraph for `modes/property.md` could push SKILL.md over the 4500 cl100k token budget (MODE-02 hard limit).

**Why it happens:** Current SKILL.md is ~14,025 chars / ~1,965 words [VERIFIED via `wc` + Python char-count]. cl100k token estimate is 4,000–5,000 (chars/3.5 to chars/2.8 envelope). The budget headroom is genuinely narrow — Phase 10 D-SUBA-FW-01 already absorbed ~80-120 tokens; Phase 12 absorbed ~80 for the `## Live Mortgage Rates` section.

**How to avoid:** Plan Wave 5 to ship a tiktoken assertion test:
```python
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
assert len(enc.encode(open(".claude/skills/mortgage-ops/SKILL.md").read())) <= 4500
```
Keep the new routing row to ONE line; precedence row to ONE line; do NOT add a sub-section for property mode (the routing table row + the cross-reference table row in "Loading Additional Context" should suffice). If the budget binds, compact the references table to a 1-line-per-ref form (Phase 10 deferred-budget-recovery plan §"Deferred Ideas" bullet 6).

**Warning signs:** If the planner adds more than 3 new lines to SKILL.md, run the tiktoken count BEFORE locking the design.

### Pitfall 2: `config/household.yml` schema mismatch with Phase 14 `Household`

**What goes wrong:** `config/household.example.yml` ships a multi-applicant nested schema (Phase 4 / AFFD-09): `household.applicants[].gross_monthly_income`, `household.monthly_debts.auto`, `household.escrow.*`, `household.va.*`. The Phase 14 `lib/household.py:Household` model is a FLAT snapshot: single `monthly_income`, single `monthly_obligations`, single `fico`, single `liquid_reserves`, `state_fips`, `county_fips`, `county_name`, `preferred_down_payment_pct`. `Household(**yaml.safe_load(open("config/household.yml")))` will FAIL with `extra_forbidden` validation errors.

**Why it happens:** Phase 14 invented a new flat Household specifically to keep the analysis-time snapshot clean (per `lib/household.py` docstring lines 8-15 + L153 PATTERNS rationale). NO mapper exists between the two. There is NO `lib/household.from_yaml()` helper. There is NO precedent in `scripts/` of loading either model from YAML.

**How to avoid:** Plan an explicit mapping function in the orchestrator (or a helper in `lib/property_analysis.py` if planner prefers — recommend orchestrator scope to keep lib pure):

```python
def _load_phase14_household_from_yaml(path: Path) -> Household:
    raw = yaml.safe_load(path.read_text())["household"]
    monthly_income = sum(Decimal(a["gross_monthly_income"]) for a in raw["applicants"])
    monthly_obligations = sum(
        Decimal(raw["monthly_debts"][k]) for k in ("auto", "student_loans", "credit_cards", "other")
    )
    fico = min(a["credit_score"] for a in raw["applicants"])
    return Household(
        monthly_income=quantize_cents(monthly_income),
        monthly_obligations=quantize_cents(monthly_obligations),
        fico=fico,
        liquid_reserves=Decimal(raw.get("liquid_reserves", "0.00")),  # NOTE: field doesn't exist in Phase 4 yaml!
        state_fips=raw["location"]["state_fips"],
        county_fips=raw["location"]["county_fips"],
        county_name=raw["location"]["county_name"],
        preferred_down_payment_pct=Decimal(raw.get("preferred_down_payment_pct", "0.200000")),
    )
```

**Warning signs:** `liquid_reserves` and `preferred_down_payment_pct` are NOT in `config/household.example.yml` (the example was frozen at Phase 4 / AFFD-09). The orchestrator must either:
  (a) extend `config/household.example.yml` with the two new optional fields (User Layer; commit-discipline-aware — block-user-layer.py hook may need to allowlist the example file edit — verify with planner), OR
  (b) default `liquid_reserves=Decimal("0.00")` and `preferred_down_payment_pct=Decimal("0.20")` and emit `warnings: ["liquid_reserves defaulted to $0; affordability stress may be too conservative"]` in the envelope.

Recommend option (a) — extend `household.example.yml` with optional `liquid_reserves` + `preferred_down_payment_pct` keys (one-line YAML additions; documented as Phase 14 fields). The user's actual `household.yml` is gitignored — they edit it themselves; the example is the canonical schema.

This is the LARGEST landmine in Phase 15. Plan-check should explicitly verify the mapping.

### Pitfall 3: AnalysisReport field-name drift since Phase 14 freeze

**What goes wrong:** The formatter references field names that don't exist on AnalysisReport, or formats the wrong type (e.g., assumes `stress.rate_shock_results` when actual is `stress.rows`).

**Why it happens:** AnalysisReport's actual surface per `lib/property_analysis.py` lines 464-489:
- `listing_snapshot: PropertyListing`
- `household_snapshot_hash: str`
- `fetched_at: datetime`
- `fred_mortgage_30us: Rate`
- `fred_mortgage_15us: Rate`
- `matrix: DownPaymentMatrix` → `.cells`, `.programs_present`, `.down_payment_pcts`
- `stress: StressBlock` → `.preferred_down_payment_pct`, `.rows: list[StressRow]`
- `refi: RefiBlock` → `.rows: list[RefiRow]`
- `points: PointsBlock` → `.rows: list[PointsRow]`
- `tax: TaxBlock` → `.first_year_interest_per_program: dict[str, Money]`, `.over_750k_cap_per_program: dict[str, bool]`, `.qualified_loan_limit: Money`, `.filing_status: Literal[...]`
- `verdict: Verdict` → `.level`, `.headline_reason`, `.reasons: list[VerdictReason]`
- `warnings: list[str]`

Per-cell `ProgramResult` carries: `program`, `down_payment_pct`, `loan_amount`, `monthly_pi`, `monthly_tax`, `monthly_insurance`, `monthly_hoa`, `monthly_mi`, `piti`, `cash_to_close`, `dti_back`, `ltv`, `eligible`, `blocker_reasons: list[str]`, `eligible_reasons: list[str]`, `closing_costs_estimated: bool`.

`StressRow`: `program`, `stress_kind: Literal["rate_shock", "income_shock", "arm_reset"]`, `baseline_piti`, `stressed_piti: Money | None`, `stressed_dti_back`, `breaches_dti_ceiling`, `blocker_reasons`.

`RefiRow`: `program`, `target_rate`, `scenario_label: Literal["minus_100bps", "fred_times_0_85"]`, `monthly_savings: Decimal`, `breakeven_months: int | None`, `npv_60mo: Decimal`. (NOTE: `monthly_savings` + `npv_60mo` can be NEGATIVE — formatter must handle negative dollars; do NOT use `Money` alias which has `ge=0`.)

`PointsRow`: `program`, `points_purchased: Literal[1, 2]`, `rate_drop: Rate`, `simple_breakeven_months: int | None`, `npv_breakeven_months: int | None`, `note: str | None`.

`VerdictReason`: `predicate_code: str`, `computed_value: str` (string, polymorphic), `program: str | None`, `dp_pct: Rate | None`.

`VERDICT_*` constants (from `lib/property_verdict.py`):
- `VERDICT_NO_GO_DTI_ALL_PROGRAMS = "DTI-CEILING-ALL-PROGRAMS"`
- `VERDICT_NO_GO_NO_ELIGIBLE_AT_PREFERRED_DP = "NO-ELIGIBLE-AT-PREFERRED-DP"`
- `VERDICT_WATCH_STRESS_INCOME_FAIL = "STRESS-INCOME-SHOCK"`
- `VERDICT_WATCH_FHA_MIP_BURDEN = "MIP-BURDEN-FHA"`
- `VERDICT_GO = "GO-ALL-GREEN"`

**How to avoid:** Plan Wave 0 to ship a test that imports `AnalysisReport` and asserts the formatter handles every field. Pin the formatter to one of the existing Phase 14 golden fixtures (`tests/fixtures/property_analysis/sfh_conforming_king_county.json`) — it carries the canonical AnalysisReport shape.

**Warning signs:** If the formatter computes a number not present on AnalysisReport (e.g., "total interest over 30 years"), STOP — that's a math primitive call masquerading as rendering, which violates CLAUDE.md money discipline.

### Pitfall 4: Negative dollars in refi rows break the formatter

**What goes wrong:** `RefiRow.monthly_savings` and `RefiRow.npv_60mo` use raw `Decimal` (NOT `Money` alias) because they CAN be negative (refi target rate > lock rate). A naive `f"${val:,.2f}"` works, but `f"${val:,.2f}"` on `Decimal("-250.00")` produces `$-250.00` not `-$250.00`. Some readers parse this as a positive `$250.00` minus sign typo.

**Why it happens:** Documented at `lib/property_analysis.py:351-358` — RefiRow Pitfall 3 explicitly notes signed Decimals.

**How to avoid:** Format negatives as `-$X,XXX.XX` not `$-X,XXX.XX`:
```python
def _fmt_signed_money(d: Decimal) -> str:
    return f"-${abs(d):,.2f}" if d < 0 else f"${d:,.2f}"
```
Add a unit test pinning both positive and negative values.

### Pitfall 5: ARM-reset stress row vs Conv30 program label

**What goes wrong:** Phase 14 emits an ARM-reset stress row with `program="Conv30"` and `stress_kind="arm_reset"`. The formatter, scanning `stress.rows` and grouping by `program`, may collapse the arm_reset row into the rate_shock row visually, or render it under a non-existent "Conv30-ARM" program.

**Why it happens:** D-14-STRESS-03 + `_CONV_5_1_ARM_TERMS` constant in property_analysis.py — only Conv30 fires the ARM-reset, but it's not a separate program; it's a stress-kind on Conv30.

**How to avoid:** Render the RATE STRESS table sorted by `(program, stress_kind)` with stress_kind values in fixed order: `["rate_shock", "income_shock", "arm_reset"]`. The `arm_reset` row appears ONLY for Conv30 (1 row per stress block).

### Pitfall 6: NNN counter collision on same-day same-zpid analyses

**What goes wrong:** User re-analyzes the same Zillow URL twice on the same day after household.yml edits. Both runs target `reports/001-property-12345-2026-05-20.md` (assuming NNN=001 is the next free slot). The second run overwrites the first.

**Why it happens:** D-15-ORCH-04 explicitly addresses this: "Same-day same-zpid: append a `-r2`/`-r3` suffix only after the same-day same-zpid duplicate is detected."

**How to avoid:** Plan the NNN sequencer to detect same-day-same-zpid via glob: `reports/{NNN-prefix}-property-{zpid}-{date}*.md`. If 0 matches: write to base name. If 1 match: write to `-{base}-r2.md`. If N matches: write to `-{base}-r{N+1}.md`. NNN counter still increments to the next free slot — the suffix is additive to disambiguate the duplicate.

```python
def _resolve_filename(out_dir: Path, zpid: str, today: str) -> Path:
    # Step 1: scan max existing NNN (3-digit zero-padded)
    pattern = re.compile(r"^(\d{3})-")
    existing_nnns = [int(m.group(1)) for f in out_dir.glob("*.md")
                     if (m := pattern.match(f.name))]
    next_nnn = (max(existing_nnns) + 1) if existing_nnns else 1
    base = f"{next_nnn:03d}-property-{zpid}-{today}"
    # Step 2: check for same-day same-zpid duplicates regardless of NNN
    dupes = list(out_dir.glob(f"*-property-{zpid}-{today}*.md"))
    if not dupes:
        return out_dir / f"{base}.md"
    return out_dir / f"{base}-r{len(dupes) + 1}.md"
```

### Pitfall 7: Phase 12 always-exit-0 violation on unhandled exception

**What goes wrong:** Inside `analyze()` or YAML loading, an uncaught exception bubbles up past `main()`. Python emits a traceback to stderr and exits with code 1, breaking the Phase 12 contract.

**Why it happens:** Easy to forget a `try/except Exception as e: emit_error(...)` outer wrap when refactoring.

**How to avoid:** Mirror `scripts/property_fetch.py` exactly — outer `try / except BaseException as exc` in `main()` that emits the error envelope and returns 0. Argparse usage errors (`SystemExit` from argparse) are the ONLY documented exit-2 case. Add a Wave 5 test:
```python
def test_orchestrator_handles_arbitrary_exception_with_envelope():
    # Pass listing JSON missing required fields → Pydantic raises → caught → envelope + exit 0
    result = subprocess.run([...], capture_output=True)
    assert result.returncode == 0
    envelope = json.loads(result.stdout)
    assert envelope["error"]["code"] is not None
```

### Pitfall 8: Decimal-as-string round-trip drift in JSON I/O

**What goes wrong:** PropertyListing serialized to JSON tempfile carries `"price": "625000.00"` (string). After Pydantic validation, the model's `price` field is `Decimal("625000.00")`. If the orchestrator's `print(json.dumps({..., "verdict": report.verdict.level, ...}))` re-serializes ANY Decimal field via `json.dumps`, Python's default JSON encoder rejects Decimal types with `TypeError`.

**Why it happens:** Money discipline (CLAUDE.md, Phase 1, Phase 12) requires Decimal-from-strings; JSON has no native Decimal type.

**How to avoid:** The orchestrator's stdout envelope only carries `report_path` (str), `verdict` (str — `Verdict.level` is `Literal["GO", "WATCH", "NO_GO"]`), and `error` (None or dict). NO Decimals cross the stdout JSON boundary. Verify with a meta-test that `json.dumps(envelope)` succeeds on a representative envelope.

If the planner adds richer envelope fields (e.g., headline PITI), use the `pydantic.BaseModel.model_dump_json()` round-trip; never `json.dumps(decimal_value)` directly.

### Pitfall 9: WebFetch returns text >100KB; `__NEXT_DATA__` is truncated

**What goes wrong:** Zillow's HTML can be 2-3MB. WebFetch truncates to ~100KB for the Haiku sub-prompt. The `__NEXT_DATA__` JSON blob may fall off the end.

**Why it happens:** Documented in v1.1 research §Pitfall 9 + 1.

**How to avoid:** Already mitigated by Phase 13's `_truncated:true` sentinel in the extractor prompt. Phase 15 simply re-uses the prompt verbatim. Plan to test the path: when the synthetic HTML fixture is >100KB, intentionally test the truncation branch.

### Pitfall 10: Citation footer copy-paste not actually re-runnable

**What goes wrong:** D-15-CITATION-03 requires the footer be a re-runnable copy-paste invocation. If the orchestrator was called with `--listing /tmp/listing-abc.json` and the report includes that path verbatim — when the user re-runs minutes later, `/tmp/listing-abc.json` is gone.

**Why it happens:** Tempfile paths are ephemeral. The citation reads like a copy-paste invocation, but it isn't reproducible.

**How to avoid:** Plan one of:
  (a) Orchestrator COPIES the listing JSON to a stable path before writing the report, e.g., `data/property-listings/{zpid}-{date}.json`, and cites THAT path in the footer. (Reproducibility WIN; small disk cost.)
  (b) Orchestrator cites a `--listing-zpid {zpid}` flag in the footer and the orchestrator supports re-loading from `data/property-listings/`. (More CLI surface.)
  (c) Accept that the footer is an audit anchor, not a literal re-run command. Footer text reads `Computed by: scripts/property_analyze.py --listing data/property-listings/{zpid}-2026-05-20.json --household config/household.yml --profile config/profile.yml` where the listing JSON is recoverable.

Recommend option (a): orchestrator writes a sidecar `data/property-listings/{zpid}-{YYYY-MM-DD}.json` alongside the report. This is one-time disk write per analysis. Bonus: enables v1.2 watchlist mode without re-fetching Zillow.

The planner's call. Whichever path is chosen, the footer must NOT cite a tempfile path.

### Pitfall 11: Matrix readability when 5×6 = 30 cells (jumbo + VA)

**What goes wrong:** GitHub-rendered markdown tables with 6 columns of `$X,XXX/mo ✓` cells get visually noisy. Bold-marking the preferred-DP column (D-15-MATRIX-04) helps but does not fix width.

**Why it happens:** Each cell is potentially up to ~22 chars (`$1,234,567.89/mo ✗ (DTI-CEILING-CONV)`). Six such cells per row = ~150 chars wide table.

**How to avoid:** Plan two tactics:
  (a) Use compact eligibility marks (`✓` / `✗`) and trim PITI to thousands (`$1,234/mo` not `$1,234.56/mo`). Round-trip via `.quantize(Decimal("1"))` for display only — internal Decimal stays cents-precise (D-NUM-05).
  (b) For long blocker chains (`blocker_reasons[1:]` exists), show only the first code + `(+N more)` annotation. Per CONTEXT "Claude's Discretion" — planner picks the exact suffix syntax.

### Pitfall 12: `analyzed_listings` DuckDB row creation expected, not delivered

**What goes wrong:** Phase 13 ships the `analyzed_listings` table schema (D-13-REANALYSIS-01). A reader of REQUIREMENTS.md might assume Phase 15 writes rows to it (PERS-08). PERS-08 is marked `[x]` and "Closed (Plan 13-05)" — that's the SCHEMA closure, not the WRITE closure.

**Why it happens:** CONTEXT.md explicitly defers DuckDB persistence to v1.2 watchlist mode. But REQUIREMENTS.md doesn't say "writes happen in v1.2"; the gap is in the requirement description.

**How to avoid:** The planner should annotate `15-PLAN-CHECK.md` or `15-VERIFICATION.md` that PERS-08 closure refers to schema only; row writes are out of scope. Plan a test that the orchestrator does NOT call `node orchestration/db-write.mjs insert-analyzed-listing` (or asserts no such subcommand is invoked).

## Code Examples

### Loading PropertyListing from JSON (orchestrator step B)

```python
# Source: Phase 13 lib/property_listing.py:44 + Pydantic v2 idiom
from lib.property_listing import PropertyListing
from pathlib import Path
import json

def _load_listing(path: Path) -> PropertyListing:
    return PropertyListing.model_validate_json(path.read_text())
```

### Calling analyze() (orchestrator step E)

```python
# Source: lib/property_analysis.py:1433
from lib.property_analysis import analyze
from lib.household import Household
from lib.profile import Profile

report = analyze(listing, household, profile)
# Optional test injection:
# report = analyze(listing, household, profile,
#                  fred_mortgage_30us=Decimal("0.065"),
#                  fred_mortgage_15us=Decimal("0.058"))
```

### Markdown matrix rendering (formatter step)

```python
# Source: Synthesized from D-15-MATRIX-01..04
def _render_matrix(matrix, preferred_dp: Decimal) -> str:
    programs = matrix.programs_present  # order-preserving
    dps = matrix.down_payment_pcts       # [0.03, 0.05, 0.10, 0.15, 0.20, 0.25]
    # Index cells by (program, dp_pct)
    cell_map = {(c.program, c.down_payment_pct): c for c in matrix.cells}

    # Header row — bold the preferred-DP column
    header_cells = ["Program"]
    for dp in dps:
        label = f"{dp:.0%} DP"
        if dp == preferred_dp:
            label = f"**{label}** *(your DP)*"
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
                code = cell.blocker_reasons[0] if cell.blocker_reasons else "BLOCKED"
                # Truncate to bare code (strip parenthetical) per D-15-MATRIX-02
                code = code.split(":")[0].split("(")[0].strip()
                extra = f" (+{len(cell.blocker_reasons)-1} more)" if len(cell.blocker_reasons) > 1 else ""
                txt = f"{piti_disp} ✗ ({code}{extra})"
            if dp == preferred_dp:
                txt = f"**{txt}**"
            row.append(txt)
        rows.append("| " + " | ".join(row) + " |")
    return "\n".join(rows)
```

### Citation footer rendering

```python
# Source: D-15-CITATION-01..03 synthesized
def _render_footer(orchestrator_args: list[str]) -> str:
    # orchestrator_args is sys.argv[1:] OR a reconstruction from the parsed argparse
    return f"*Computed by: scripts/property_analyze.py {' '.join(orchestrator_args)}*"
```

### Eval prompt frontmatter (mirror amortize-01.md)

```yaml
---
id: property-analysis-01
mode: property
description: Full property analysis — SFH conforming King County WA; ROADMAP SC-6 anchor.
expected_route_keywords:
  - property
  - property_analyze.py
expected_scripts:
  - script: property_analyze.py
    args_must_include: ["--listing", "--household", "--profile"]
expected_numbers:
  - label: verdict_level
    value: "GO"
    provenance: stdout
    # NOTE: verdict.level is a string, not a number. Eval prompt may need
    # a separate route_match keyword check for verdict text rather than
    # numeric_match — or use a non-numeric oracle field. Planner picks.
  - label: conv30_preferred_dp_piti
    value: "3760.34"      # Conv30 @ 20% DP on $625k = $3,160.34 P&I + $500.00 tax + $100.00 insurance + $0.00 HOA + $0.00 PMI = $3,760.34
    tolerance: "0.50"
    source_script: property_analyze.py
    provenance: stdout
  - label: first_year_interest_conv30
    value: "32335.43"     # From fixture sfh_conforming_king_county.json hand-calc anchor
    tolerance: "0.50"
    source_script: property_analyze.py
    provenance: stdout
---
Analyze this Zillow listing for me: https://www.zillow.com/homedetails/synthetic/1_zpid/
(Eval prompt; in CI the synthetic JSON fixture is fed directly to the
orchestrator — no live WebFetch per Phase 11 D-02 + Phase 12 contract.)
```

**Open detail:** `score_numeric_match` extracts numbers via `NUMBER_REGEX = r"\$?(\d{1,3}(?:,\d{3})*|\d+)\.\d{1,4}\b"` — requires a decimal point. The verdict level `"GO"` is a string, not a numeric match. Plan to anchor the verdict via `expected_route_keywords: ["GO"]` (substring match) rather than `expected_numbers`. This is consistent with how `live-rate-injection-01.md` pins a string (`"6.50"`) via `expected_route_keywords`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 14 reads FRED at analyze() time, may fail if cache cold | Phase 14 also accepts `fred_mortgage_30us` / `fred_mortgage_15us` kwargs for test injection | Phase 14 Plan 14-05 | Orchestrator can pass explicit overrides for eval determinism — no need to mock the cache. |
| Phase 10 SKILL.md routing precedence had 9 rows | Phase 15 inserts Row 0 → 10 rows total | Phase 15 (this phase) | URL pin wins over all verbs. Existing rows renumber but no other reordering. |
| PROP-02 contemplated automatic DuckDB persistence on every analysis | Phase 15 writes markdown ONLY; DuckDB write deferred to v1.2 watchlist | Phase 15 CONTEXT (Deferred Ideas) | Cleaner phase boundary; less coupling. |
| Research §Pattern 7 envisioned `--format {json,markdown}` flag on orchestrator | Orchestrator emits markdown always (writes file), JSON envelope on stdout | Phase 15 CONTEXT (D-15-ORCH-03 + RPRT-01 path) | Simpler CLI surface; aligns with Phase 11 amortization-agent CSV-path precedent. |

**Deprecated/outdated:**
- None — Phase 15 builds on green Phase 13/14; nothing is being torn down.

## Project Constraints (from CLAUDE.md)

These directives carry the same authority as locked CONTEXT decisions. The planner must verify compliance on every plan.

| Directive | Source section | Implication for Phase 15 |
|-----------|----------------|--------------------------|
| `Decimal` for all dollar amounts and rates; construct from strings; quantize at end-of-period only | Money discipline | Formatter uses Decimal arithmetic for display formatting only; no float anywhere. AnalysisReport already enforces this. |
| Never mix `float` and `Decimal` in same expression | Money discipline | Formatter f-strings must use Decimal directly (`f"{val:,.2f}"`) — never coerce to float. |
| Every dollar figure is computed by Python in `lib/`; Claude never owns numbers | Calc engine separation | `lib/property_report.py` MUST NOT compute any new number. Every value in the markdown traces to a field on AnalysisReport, which traces to `lib.property_analysis.analyze()`. |
| Bundled scripts: run `--help` first; do not read source unless customization needed | Calc engine separation | `modes/property.md` instructs Claude to run `python scripts/property_analyze.py --help` before invoking. |
| Rules-as-predicates with citations | Rules-as-predicates | Not directly relevant (Phase 15 doesn't add rule predicates). |
| Reference data: YAML with `source:` + `effective:` | Reference data discipline | Not directly relevant (no new YAMLs in Phase 15; Phase 16 ships those). |
| SKILL.md ≤ 500 lines, ≤ 5k tokens; load-bearing routing in first 200 lines | Skill portability | Phase 15 hard-caps at 4500 cl100k tokens per MODE-02. Tiktoken assertion test required. |
| `references/*.md` loaded on demand only (progressive disclosure) | Skill portability | New `modes/property.md` follows the load-after-`_shared.md` convention. |
| User Layer files (`config/household.yml`, `config/profile.yml`, `modes/_profile.md`) are READ-ONLY by system code | Data Contract | Orchestrator READS household.yml and profile.yml; never writes them. Pre-commit hook `scripts/hooks/block-user-layer.py` already enforces this. |
| Data Layer (`reports/`) is generated; gitignored | Data Contract | Orchestrator writes to `reports/`; gitignored already (FND-08). |
| Hand-calculated golden-value fixtures with citation comments | Testing | Eval fixture `evals/fixtures/property/sfh_conforming_001.json` must carry hand-calc citation comments (re-use Phase 14 fixture format from `tests/fixtures/property_analysis/`). |
| Exact Decimal equality, never `assertAlmostEqual` for money | Testing | Phase 15 tests use Decimal equality; tolerances only inside eval `numeric_match` (which is intentional per Phase 12 D-12-SC4-01). |
| No Co-Authored-By or AI attribution in commits | Commits | Standard project rule; verify the auto-commit step in Phase 15 plans (D-15 has commit_docs: true). |

## Assumptions Log

> Items below need user/planner confirmation before becoming locked decisions.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `config/household.example.yml` will be extended with optional `liquid_reserves` and `preferred_down_payment_pct` keys (Pitfall 2 option a) | Pitfall 2 + Open Q1 | If planner prefers defaults-with-warnings instead, the orchestrator must emit `warnings: ["liquid_reserves defaulted to $0"]` and verdict accuracy degrades silently for users who don't notice. User-layer commit-hook `scripts/hooks/block-user-layer.py` may need to allowlist the example file. |
| A2 | `scripts/property_analyze.py` lives at project-root `scripts/`, NOT inside `.claude/skills/mortgage-ops/scripts/` | Recommended Project Structure | If planner colocates inside skill folder for consistency with v1.0 calc CLIs, the script's `sys.path` injection must shift (mirror `amortize.py` parents[4] vs parents[1] pattern). |
| A3 | Orchestrator copies listing JSON to `data/property-listings/{zpid}-{date}.json` for citation-footer reproducibility | Pitfall 10 | If planner prefers the "audit anchor not literal re-run" path, the footer text changes and Phase 15 doesn't ship the sidecar dir. |
| A4 | Eval oracle anchors verdict via `expected_route_keywords: ["GO"]` rather than a numeric match | Code Examples §"Eval prompt" | If the planner wants `verdict.level` in a numeric oracle, `evals/metrics.py` needs a third oracle slot for string equality — adds harness surface area. The CONTEXT D-15-EVAL-03 wording ("verdict.level — exact string match") is closer to the route-keyword path. |
| A5 | Phase 15's same-day-same-zpid `-r2`/`-r3` suffix logic is in the orchestrator's `_resolve_filename()`, not in a separate utility | Pitfall 6 | If planner prefers a shared `lib.report_naming` module for future reusability (v1.2 watchlist), the logic moves and tests follow. Phase 15-only is the simpler path. |
| A6 | The new `modes/property.md` will NOT add a "Subagents" section (no property-specific subagent in v1.1) | Architecture Diagram | If a property-summary subagent is desired later, that's Phase 18+ scope. |
| A7 | The token budget for Row 0 + cross-reference + precedence row stays ≤120 cl100k tokens of new content | Pitfall 1 | If new content exceeds budget, planner must trim — recommended trim targets are the references topic→reference table (compact to 1 line per ref) per Phase 10 deferred recovery. |
| A8 | Tax block over-cap formatting uses "see CPA" callout when `tax_block.over_750k_cap_per_program[program] == True` rather than computing partial-deduction dollars | CONTEXT Claude's Discretion + Phase 14 D-14-TAX | Phase 14 ships the flag only; Phase 15 formatter picks the copy. "See CPA" is safer (no partial-deduction math owned by formatter); computing partial dollars would violate calc-engine separation. |
| A9 | `lib/property_report.render()` returns `str` (entire markdown body); the orchestrator owns the file write | Architecture Diagram | If planner prefers `render()` to accept a `Path` and write directly, testability suffers (renderer becomes I/O-coupled). Keep `render()` pure — that's the standard Phase 14 idiom. |

**If this table is empty:** Not applicable — 9 assumptions logged.

## Open Questions (RESOLVED)

1. **`liquid_reserves` and `preferred_down_payment_pct` extension to `config/household.example.yml`** (Pitfall 2)
   - What we know: Phase 14 `Household` requires `liquid_reserves` (Money, no default) and accepts `preferred_down_payment_pct` (default 0.20). Phase 4 yaml doesn't carry either.
   - What's unclear: Does the planner extend `household.example.yml` (touching User Layer example, potentially nudging block-user-layer.py allowlist), or default-with-warning in the orchestrator?
   - Recommendation: Extend `household.example.yml` with both optional keys; the example file is allowlisted under `*.example.yml` in the User-Layer pre-commit hook (Phase 1 FND-04). Real `household.yml` is gitignored — the user adds the fields when they pull v1.1.
   - **RESOLVED:** Extend `config/household.example.yml` with optional `liquid_reserves` (Decimal-string default `"0.00"`) and `preferred_down_payment_pct` (Decimal-string default `"0.200000"`) fields per Plan 15-03 Task 1. Additive, non-breaking. The orchestrator defaults both when absent so existing user `household.yml` files keep working.

2. **Where does `scripts/property_analyze.py` live?** (Recommended Project Structure)
   - What we know: v1.0 calc CLIs live at `.claude/skills/mortgage-ops/scripts/`. Dev-only helpers (`_generate_*.py`) and hooks (`scripts/hooks/`) live at project-root `scripts/`. Phase 13's `property_fetch.py` lives at `.claude/skills/mortgage-ops/scripts/`.
   - What's unclear: Does Phase 15's orchestrator follow the calc-CLI convention (inside skill folder) or the orchestration convention (project root, since it composes lib + writes to reports/)?
   - Recommendation: **Inside `.claude/skills/mortgage-ops/scripts/`** to match Phase 13's `property_fetch.py` precedent. SKILL.md already references that path in routing. Project-root `scripts/` should remain dev-only helpers per the existing pattern. This is a REVERSAL of CONTEXT's "scripts/property_analyze.py" wording, which CONTEXT.md uses loosely. Confirm with user/planner.
   - **RESOLVED:** Orchestrator lives at `.claude/skills/mortgage-ops/scripts/property_analyze.py` (per Phase 13 `property_fetch.py` precedent — repo inspection confirms ALL production scripts live in the skill folder; project-root `scripts/` contains only dev-only helpers + hooks). CONTEXT's shorthand `scripts/property_analyze.py` is interpreted as the skill-relative path (which is also how SKILL.md routing tables reference it). Citation footers rendered IN THE REPORT use the full re-runnable form `.claude/skills/mortgage-ops/scripts/property_analyze.py` (per D-15-CITATION-03 — runs from project-root cwd).

3. **Citation-footer reproducibility** (Pitfall 10)
   - What we know: Footers must be re-runnable copy-paste (D-15-CITATION-03). Tempfile paths are ephemeral.
   - What's unclear: Sidecar `data/property-listings/{zpid}-{date}.json` write vs. stable filesystem path vs. accept-non-reproducible-but-audit-anchored.
   - Recommendation: Sidecar write. One-line additional disk I/O; enables v1.2 watchlist; preserves D-15-CITATION-03 spirit.
   - **RESOLVED:** Write sidecar `data/property-listings/{zpid}-{YYYY-MM-DD}.json` before render() so the citation footer points to a stable, re-runnable path (Plan 15-03 Step F). Orchestrator rewrites the `--listing` argv to cite the sidecar path (not the input tempfile) when assembling the footer argv passed to `render()`.

4. **Verdict-level oracle: route_keyword vs numeric_match** (Code Examples)
   - What we know: `verdict.level` is `Literal["GO", "WATCH", "NO_GO"]`. `numeric_match` requires decimal-point numbers.
   - What's unclear: How to encode a string-equality oracle in the existing Phase 12 metrics.
   - Recommendation: `expected_route_keywords: ["GO"]` for verdict; `expected_numbers` for the 3 numerics. This avoids extending `evals/metrics.py` and matches `live-rate-injection-01.md` precedent.
   - **RESOLVED:** Use `expected_route_keywords: ["GO"]` (alongside `"property"` and `"property_analyze.py"`) for the non-numeric `verdict.level` assertion. Mirrors `evals/prompts/live-rate-injection-01.md` precedent. The 3 numeric anchors stay in `expected_numbers` per D-15-EVAL-03.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Orchestrator runtime | ✓ (project requirement) | 3.12+ | — |
| `pydantic` | PropertyListing / AnalysisReport validation | ✓ (already in pyproject) | ≥2.13 | — |
| `pyyaml` | household.yml / profile.yml load | ✓ (already in pyproject via lib/rules/_loader.py) | — | — |
| `python-frontmatter` | eval prompt parsing | ✓ (already in evals/runner.py) | — | — |
| `tiktoken` (cl100k) | SKILL.md token-budget assertion | ✓ likely (Phase 10 budget test) | — | If absent, fall back to char/3.5 estimate as soft check and document in README. Recommend confirming Wave 0. |
| FRED cache (`data/cache/fred_*.json`) | analyze() rate resolution | conditionally present | — | Orchestrator emits `error.code = "fred_cache_cold"` envelope; mode body narrates the recovery command. Test injection via `fred_mortgage_*us` kwargs (analyze() accepts these). |
| `freezegun` | Deterministic timestamps in eval fixtures | ✓ (dev dep from Phase 12) | — | — |
| `numpy-financial` | Inside analyze() (Phase 14 dependency) | ✓ | — | — |
| `node` + `orchestration/db-write.mjs` | DuckDB writes | ✓ shipped Phase 9 | — | NOT USED in Phase 15 (DuckDB row write deferred to v1.2). |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** FRED cache may be cold on a fresh checkout — orchestrator handles via envelope error code; mode body has documented recovery.

## Validation Architecture

> Included per .planning/config.json `workflow.nyquist_validation: true`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` (Phase 14 verified — 644+ tests passing project-wide; 84 Phase-14 tests in `tests/test_household.py` + `tests/test_profile.py` + `tests/test_property_analysis.py` + `tests/test_property_verdict.py`) |
| Config file | `pyproject.toml` (project-wide pytest config) |
| Quick run command | `uv run pytest tests/test_property_report.py tests/test_property_analyze_cli.py -x` |
| Full suite command | `uv run pytest -x` (Phase 14 reference; 5.66s execution per verification report) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODE-01 | `modes/property.md` exists and matches URL-pin routing trigger; SKILL.md Row 0 dispatches | unit (filesystem-introspection) | `uv run pytest tests/test_skill_routing.py::test_property_mode_row0_present -x` | ❌ Wave 0 |
| MODE-01 | `modes/property.md` contains the verbatim Pattern 1 extractor prompt from research | unit (grep meta-test) | `uv run pytest tests/test_skill_routing.py::test_property_mode_contains_extractor_prompt -x` | ❌ Wave 0 |
| MODE-02 | SKILL.md ≤ 4500 cl100k tokens after Row 0 insertion | unit (tiktoken assertion) | `uv run pytest tests/test_skill_routing.py::test_skill_md_token_budget -x` | ❌ Wave 0 |
| MODE-02 | SKILL.md routing table cross-references `modes/property.md` | unit (grep) | `uv run pytest tests/test_skill_routing.py::test_skill_md_cross_references_property_mode -x` | ❌ Wave 0 |
| MODE-03 | `scripts/property_analyze.py --help` works without heavy imports (lazy-import) | subprocess | `uv run pytest tests/test_property_analyze_cli.py::test_help_fast_no_heavy_imports -x` | ❌ Wave 0 |
| MODE-03 | Orchestrator emits success envelope `{report_path, verdict, error:null}` on golden input | subprocess | `uv run pytest tests/test_property_analyze_cli.py::test_success_envelope_shape -x` | ❌ Wave 0 |
| MODE-03 | Orchestrator emits error envelope `{report_path:null, verdict:null, error:{code,message}}` AND exits 0 on bad listing input | subprocess | `uv run pytest tests/test_property_analyze_cli.py::test_error_envelope_always_exit_0 -x` | ❌ Wave 0 |
| MODE-03 | Pydantic ValidationError on listing JSON emits 6-key envelope on stderr | subprocess | `uv run pytest tests/test_property_analyze_cli.py::test_pydantic_validation_envelope_on_stderr -x` | ❌ Wave 0 |
| MODE-03 | `household.yml` (Phase 4 multi-applicant) loads + maps to Phase 14 flat Household correctly | unit | `uv run pytest tests/test_property_analyze_cli.py::test_household_yaml_mapping -x` | ❌ Wave 0 |
| RPRT-01 | `lib/property_report.render(report)` returns markdown with all 6 sections | unit | `uv run pytest tests/test_property_report.py::test_render_emits_six_sections -x` | ❌ Wave 0 |
| RPRT-01 | Filename matches `reports/{NNN:03d}-property-{zpid}-{YYYY-MM-DD}.md` pattern | unit | `uv run pytest tests/test_property_analyze_cli.py::test_filename_format -x` | ❌ Wave 0 |
| RPRT-01 | Same-day same-zpid duplicate gets `-r2` suffix | unit | `uv run pytest tests/test_property_analyze_cli.py::test_same_day_zpid_suffix -x` | ❌ Wave 0 |
| RPRT-01 | YOUR FIT matrix renders all program rows × all DP cols; preferred-DP col bolded | unit | `uv run pytest tests/test_property_report.py::test_matrix_renders_all_cells -x` | ❌ Wave 0 |
| RPRT-01 | Ineligible cells render with blocker code; eligible cells with ✓ | unit | `uv run pytest tests/test_property_report.py::test_cell_eligibility_marks -x` | ❌ Wave 0 |
| RPRT-02 | Every section ends with italic `*Computed by: scripts/property_analyze.py ...*` footer (6 footers total) | unit | `uv run pytest tests/test_property_report.py::test_six_citation_footers -x` | ❌ Wave 0 |
| RPRT-02 | Citation footer carries the FULL orchestrator invocation (re-runnable copy-paste) | unit | `uv run pytest tests/test_property_report.py::test_footer_is_full_invocation -x` | ❌ Wave 0 |
| SC-6 | `python -m evals.runner evals/prompts/` exits 0 with new prompt (route_match + numeric_match ≥ 0.95) | subprocess | `uv run python -m evals.runner` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_property_report.py tests/test_property_analyze_cli.py tests/test_skill_routing.py -x` (~5–10s)
- **Per wave merge:** `uv run pytest -x` (full project suite; ~10–20s per Phase 14 reference of 5.66s for 84 tests, scaling to 644+ tests)
- **Phase gate:** Full suite green AND `python -m evals.runner` exits 0 before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_property_report.py` — RPRT-01, RPRT-02 coverage (formatter unit tests)
- [ ] `tests/test_property_analyze_cli.py` — MODE-03 coverage (subprocess CLI shape tests, envelope tests, NNN sequencer, YAML mapping)
- [ ] `tests/test_skill_routing.py` — MODE-01, MODE-02 coverage (filesystem-introspection tests; tiktoken budget; routing-row grep)
- [ ] `evals/fixtures/property/sfh_conforming_001.json` — synthetic PropertyListing JSON (mirror Phase 14 fixture `sfh_conforming_king_county.json` shape; new zpid; new fetched_at)
- [ ] `evals/fixtures/property/sfh_conforming_001.html` — 2KB synthetic HTML stub with `__NEXT_DATA__` (for extractor recipe smoke; optional in CI per CONTEXT D-15-EVAL-01)
- [ ] `evals/expected/property-analysis-01.json` — oracle pinning 3 numerics + verdict route-keyword
- [ ] Framework install: no new framework needed; pytest already shipped.

**Phase 15 inherits frozen validation from prior phases for:**
- Math correctness (Phase 14 `analyze()` 7/7 SCs verified; 49 tests + 13 verdict tests + 3 golden fixtures)
- PropertyListing validation (Phase 13)
- 6-key Pydantic envelope contract (Phase 3 WR-02)
- Always-exit-0 contract (Phase 12 D-12-LIVE02-01)
- Eval harness (Phase 12 D-12-SC3-01 + D-12-SC4-01)

**Phase 15 must validate (delta surface):**
- Orchestrator envelope shape on success + error paths
- household.yml → Phase 14 Household mapping correctness
- Markdown report structure (6 sections, citation footers, matrix layout)
- Filename sequencer + same-day-zpid suffix logic
- SKILL.md token budget after Row 0 insertion
- Mode-routing dispatch on Zillow URL substring + "analyze listing" phrase
- Eval prompt + oracle internal consistency (route_match + numeric_match passes in replay-stub mode)

## Security Domain

> `.planning/config.json` does not set `security_enforcement: false`; treat as enabled. Phase 15 introduces minimal new attack surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Personal-use CLI; no authentication boundary. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | yes | User-Layer files (`config/household.yml`, `config/profile.yml`) are READ-ONLY by system code (DATA_CONTRACT.md + pre-commit hook `scripts/hooks/block-user-layer.py`). Phase 15 orchestrator MUST NOT write to these. Verify via test: subprocess run of orchestrator does not modify the YAML files. |
| V5 Input Validation | yes | PropertyListing JSON input validated via Pydantic strict mode (Phase 13 contract). household.yml + profile.yml YAML loaded via `yaml.safe_load` (NOT `yaml.load`) — already established convention via `lib/rules/_loader.py:70`. CLI argparse handles path traversal indirectly (output-dir is a path; planner should consider whether to constrain it to project subdir; if user passes `--output-dir /etc`, we write there). Recommend: validate `--output-dir` resolves to a path under project root or `reports/`; reject otherwise. |
| V6 Cryptography | no | No new crypto. |

### Known Threat Patterns for Python CLI orchestrator + markdown formatter

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `--output-dir` arg | Tampering | Validate output_dir resolves under project root; reject absolute paths outside |
| YAML deserialization injection (loading attacker-controlled YAML) | Tampering | `yaml.safe_load` only (established convention) |
| JSON injection via PropertyListing fields rendered to markdown (e.g., `address: "<script>alert(1)</script>"`) | XSS-via-markdown | Markdown is not executed in viewer; GitHub renders raw HTML conservatively; for personal-use scope, this is acceptable. If reports are ever served to a browser, plan an HTML-escape pass. Document the residual risk. |
| Citation footer contains user-controllable input (e.g., listing path containing shell-metacharacters) | Command-injection-via-display | Citation footer is RENDERED IN MARKDOWN ONLY — never re-executed by the orchestrator. User copy-pasting the line to a shell takes their own risk; standard CLI convention. |
| FRED cache poisoning via attacker writing to `data/cache/fred_*.json` | Tampering | Out of scope for Phase 15 (Phase 12 owns FRED cache; lock-serialized writes via `with_cache_lock`). |
| Stale household_snapshot_hash collisions | Spoofing | SHA256 of household+profile JSON dump (Phase 14); collision probability is astronomically low. |

**Residual risks documented:** Personal-use scope; markdown rendering in a browser/Markdown viewer (e.g., VS Code) is not a defended threat boundary in v1.1.

## Sources

### Primary (HIGH confidence)

- `lib/property_analysis.py` (Phase 14, 1534 lines) — `analyze()` entrypoint at L1433; `AnalysisReport` at L464; all output models (DownPaymentMatrix, StressBlock, RefiBlock, PointsBlock, TaxBlock, Verdict, VerdictReason) co-located.
- `lib/property_verdict.py` (Phase 14, 258 lines) — `synthesize()` cascade; 5 `VERDICT_*` Final constants.
- `lib/property_listing.py` (Phase 13, 105 lines) — `PropertyListing` model + `ProvenancedMoney` wrapper.
- `lib/household.py` (Phase 14, 75 lines) — flat Household snapshot model.
- `lib/profile.py` (Phase 14, 61 lines) — eligibility + tax preferences model.
- `.claude/skills/mortgage-ops/SKILL.md` (Phase 10/12, 277 lines, ~14KB) — current routing table + precedence + Live Mortgage Rates section.
- `.claude/skills/mortgage-ops/modes/evaluate.md` + `modes/_shared.md` — mode-file shape precedent.
- `.claude/skills/mortgage-ops/scripts/amortize.py` (Phase 3/10) — 6-key envelope contract docstring (L36-60); lazy-import pattern (L92-100).
- `.claude/skills/mortgage-ops/scripts/property_fetch.py` (Phase 13) — three-shape envelope precedent; argparse + lazy-import pattern.
- `evals/runner.py` (Phase 12, 306 lines) — eval harness; `run_replay_stub`, `synthesize_stub_transcript`, `HarnessReport`, `SC4_GATE_THRESHOLD=0.95`.
- `evals/metrics.py` (Phase 12, 212 lines) — `score_numeric_match` (3-state), `score_route_match`, `NUMBER_REGEX`, `_sourced_via_stdout`.
- `evals/prompts/amortize-01.md` + `evals/expected/amortize-01.json` — analog prompt+oracle structure.
- `evals/prompts/live-rate-injection-01.md` — `expected_route_keywords` substring-match precedent for non-numeric assertions.
- `tests/fixtures/property_analysis/sfh_conforming_king_county.json` — Phase 14 golden fixture; canonical AnalysisReport shape.
- `tests/fixtures/zillow/sfh_conforming_happy_path.html` + `README.md` — synthetic Zillow HTML fixture precedent.
- `.planning/phases/15-property-skill-mode-report-formatter/15-CONTEXT.md` — locked decisions D-15-ROUTE-01..03, D-15-MATRIX-01..04, D-15-CITATION-01..03, D-15-ORCH-01..04, D-15-EVAL-01..03.
- `.planning/phases/14-property-analysis-pipeline/14-VERIFICATION.md` — confirms AnalysisReport schema frozen; 7/7 SCs verified.
- `.planning/phases/13-property-ingestion/13-CONTEXT.md` — Phase 13 envelope shapes; PropertyListing audit fields.
- `.planning/phases/12-fred-eval/12-CONTEXT.md` — D-12-LIVE02-01 always-exit-0; D-12-SC3-01 stdout-only sourcing; D-12-SC4-01 three-bucket numeric scoring.
- `.planning/phases/10-claude-skill/10-CONTEXT.md` — SKILL.md 4500 cl100k budget; D-NUM-01..06 formatters; D-13-01..05 reports-flow; D-PROF-04 fallback defaults; D-09 progressive disclosure.
- `.planning/research/v1.1-property-analysis.md` — Pattern 1 verbatim extractor prompt (L100-138); 12 pitfalls; 8 open questions.
- `CLAUDE.md` — money discipline + calc-engine separation + skill portability + DATA_CONTRACT + No Co-Authored-By.
- `config/household.example.yml` + `config/profile.example.yml` — Phase 4 schema baseline.

### Secondary (MEDIUM confidence)

- `.planning/phases/11-subagents/11-03-stress-test-agent-PLAN.md` — markdown-report emit precedent (1000-token budget) mirrored for citation discipline.
- Phase 10 D-13-02 filename convention — `reports/{NNN:03d}-{mode}-{YYYY-MM-DD}.md`; Phase 15 extends with `-{zpid}-{date}` and same-day-`-r2` suffix.

### Tertiary (LOW confidence)

- Cl100k token estimate for SKILL.md is currently a char/3.5 calculation (~4007 tokens); actual tiktoken measurement should be done in Wave 0 to confirm budget headroom. (LOW because no tiktoken run was performed in this research session — fallback estimate only.)

## Metadata

**Confidence breakdown:**
- Mode routing + SKILL.md edits: HIGH — Phase 10 + Phase 12 established the idioms verbatim.
- Orchestrator envelope: HIGH — Phase 3 WR-02 + Phase 12 D-12-LIVE02-01 + Phase 13 property_fetch.py all converge.
- AnalysisReport schema consumption: HIGH — Phase 14 7/7 verified; field names + types directly inspected in source.
- Markdown formatter design: HIGH — pure rendering, no math; AnalysisReport surface is fully enumerated.
- household.yml → Phase 14 Household mapping: MEDIUM — no precedent loader exists; mapping is straightforward but the `liquid_reserves` extension to `household.example.yml` is a user-layer-edge decision (Assumption A1).
- Eval prompt + oracle: MEDIUM — frontmatter shape matches `amortize-01.md`; oracle metric for `verdict.level` (string) needs route-keyword path (Assumption A4).
- Pitfall coverage: HIGH — synthesized from Phase 14 + Phase 13 inherited pitfalls + Phase 12 envelope discipline.

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (30 days — Phase 14/13 frozen, no upstream changes expected; only the v1.1 milestone-internal landings could invalidate).

## RESEARCH COMPLETE

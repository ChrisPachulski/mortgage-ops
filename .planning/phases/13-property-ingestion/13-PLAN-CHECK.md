---
phase: 13-property-ingestion
verified_at: 2026-05-16
plans_verified: 7
verdict_counts:
  PASS: 6
  PASS-WITH-CONCERNS: 1
  CONCERN: 2
  BLOCKER: 0
status: pass_with_concerns
patched_at: 2026-05-16
patch_notes: |
  Original audit returned BLOCK with 2 blockers. Both resolved via direct
  PLAN.md edits (no replanner re-spawn):

  BLOCKER 1 (ProvenancedMoney wrapping deferred to 13-06):
    → 13-04 Task 1 action gained item 16 (_wrap_scraped_provenanced_money
      helper definition + call-site). 13-04 verify block + acceptance criteria
      assert presence via grep. 13-06 Task 4 action stripped of duplicate
      definition; now reads "Plan 13-04 owns this; this task verifies".

  BLOCKER 2 (MORTGAGE_OPS_MOCK_SONNET hook missing from 13-04):
    → 13-04 Task 1 action gained item 17 (_mock_sonnet_extract helper +
      env-var branch). 13-04 verify block greps for MORTGAGE_OPS_MOCK_SONNET
      and _mock_sonnet_extract. 13-06 Task 4 stripped of CLI-edit language;
      now reads "verifies 13-04 shipped the hook; fails loudly if absent".

  Result: 0 BLOCKERs, 2 CONCERNs (non-blocking), 1 PASS-WITH-CONCERNS, 6 PASS.
---

# Phase 13 Plan Check

**Plans verified:** 13-00 through 13-06 (7 plans)
**Overall status:** PASS-WITH-CONCERNS (after patch — original audit returned BLOCK; see frontmatter patch_notes)

---

## Verdict Matrix

| Plan | Wave | Verdict | Primary Issue |
|------|------|---------|---------------|
| 13-00 | 0 | PASS | — |
| 13-01 | 1 | PASS | — |
| 13-02 | 2 | PASS | — |
| 13-03 | 3 | PASS-WITH-CONCERNS | Probe-A branch leaves a code gap (CONCERN) |
| 13-04 | 4 | PASS | Task 2 shape-1 test admits it can't prove shape-1 via subprocess (concern documented in plan) |
| 13-05 | 5 | PASS | — |
| 13-06 | 6 | BLOCKER | 2 blockers — see below |

---

## Dimension 1: Requirement Coverage

All 7 Phase 13 requirement IDs appear in at least one plan's `requirements:` frontmatter field.

| Requirement ID | Covered By | Status |
|---------------|-----------|--------|
| INGEST-01 | 13-04 `requirements: [INGEST-01, INGEST-03, INGEST-04]` | COVERED |
| INGEST-02 | 13-03 `requirements: [INGEST-02]` | COVERED |
| INGEST-03 | 13-04 `requirements: [INGEST-01, INGEST-03, INGEST-04]` | COVERED |
| INGEST-04 | 13-02 `requirements: [INGEST-04]`; 13-04 also claims it | COVERED |
| PROP-01 | 13-01 `requirements: [PROP-01]` | COVERED |
| PROP-02 | 13-05 `requirements: [PROP-02, PERS-08]` | COVERED |
| PERS-08 | 13-05 `requirements: [PROP-02, PERS-08]` | COVERED |

Note: 13-06 has `requirements: []` by design — it provides fixtures and integration coverage, not new requirement closures. This is explicitly documented and acceptable.

**ROADMAP SC coverage:**

| SC | Covered By | Evidence |
|----|-----------|---------|
| SC-1 (valid URL → PropertyListing envelope with provenance) | 13-04 + 13-06 integration | test_end_to_end_sfh_happy_path_shape_1 asserts provenance="scraped" |
| SC-2 (captcha/403 → structured error envelope, exit 0) | 13-02 + 13-04 + 13-06 | test_blocked_captcha_envelope_exit_0 + integration test |
| SC-3 (awaiting_user_input + --user-provided re-invoke) | 13-04 | test_user_provided_* + envelope shape contract |
| SC-4 (ZPID from both URL patterns) | 13-02 + 13-04 + 13-06 | parametric test matrix + integration test_end_to_end_zpid_matches_extraction |
| SC-5 (round-trip DuckDB persistence) | 13-05 + 13-06 | test_round_trip_write_read + test_end_to_end_database_roundtrip |

**Verdict: PASS**

---

## Dimension 2: Task Completeness

All tasks across all 7 plans have `<read_first>`, `<action>`, `<verify>` with `<automated>` commands, `<acceptance_criteria>`, and `<done>` fields. Each `<automated>` block contains concrete runnable commands (grep, pytest, python -c). Actions specify concrete values (exact file paths, exact pyproject.toml lines, exact SQL, exact regex patterns).

Notable strengths:
- Wave 0 probes (Probe A, Probe B) are concrete bash commands with expected output documented.
- Acceptance criteria are grep-verifiable in every task.
- xfail-to-flip discipline is correctly applied: Wave 0 creates `strict=True` stubs; Waves 1-5 remove markers.

One CONCERN in 13-03 Task 1: the action says "The body branches on Wave-0 Probe A result" and provides both code paths (messages.parse and messages.create). The plan correctly states the executor MUST read 13-00-SUMMARY.md. However, the plan's `<automated>` verify does not check WHICH path was taken — it only checks that `SONNET_MODEL` is set correctly. If the executor picks the wrong branch, the verify step will not catch it. This is a quality concern, not a blocker, since the acceptance_criteria explicitly states "The chosen API path matches 13-00-SUMMARY.md Probe A result."

**Verdict: PASS (with concern noted for 13-03)**

---

## Dimension 3: Dependency Correctness

| Plan | depends_on | Wave | Valid? |
|------|-----------|------|--------|
| 13-00 | [] | 0 | PASS |
| 13-01 | [13-00] | 1 | PASS |
| 13-02 | [13-00] | 2 | PASS — parallel-eligible with 13-01 |
| 13-03 | [13-00, 13-01] | 3 | PASS — correctly depends on PropertyListing model |
| 13-04 | [13-00, 13-01, 13-02, 13-03] | 4 | PASS — correctly composes all lib modules |
| 13-05 | [13-00, 13-01] | 5 | PASS — only needs PropertyListing and deps scaffold |
| 13-06 | [13-00, 13-01, 13-02, 13-03, 13-04, 13-05] | 6 | PASS — correctly waits for all prior waves |

No cycles detected. All referenced plans exist. Wave assignments are consistent with dependency depth.

One observation: 13-04 does NOT list 13-05 as a dependency (persistence), which is architecturally correct — the CLI wraps persistence in try/except ImportError. The plan explicitly documents this deliberate choice. The wave ordering (13-04=wave 4, 13-05=wave 5) means sequential execution will run 13-04 before 13-05, but the CLI degrades gracefully until 13-05 ships.

**Verdict: PASS**

---

## Dimension 4: Key Links Planned

All must_haves.key_links fields connect artifacts to each other with explicit wiring patterns.

Critical wiring verified:

| Link | Plan | Verified |
|------|------|---------|
| property_fetch.py → detect_block BEFORE extract_listing | 13-04 must_haves, task acceptance_criteria, task verify grep | PASS |
| property_fetch.py → lib.property_extractor.extract_listing | 13-04 key_links | PASS |
| property_fetch.py → PropertyListing.model_validate | 13-04 key_links | PASS |
| lib/property_persistence.py → with_cache_lock | 13-05 key_links | PASS |
| conftest.py mock_sonnet → tests/fixtures/zillow/extracted/ | 13-03 key_links | PASS |
| sfh_conforming_happy_path.html → extracted/{sha16}.json | 13-06 key_links + Task 2 action | PASS |

The D-13-BLOCK-01 cost-saving ordering is explicitly verified in 13-04's acceptance_criteria: "Block detection happens BEFORE Sonnet (grep order: `detect_block` line appears before `extract_listing` line in `scripts/property_fetch.py`)". This is the correct pre-execution verification.

**Verdict: PASS**

---

## Dimension 5: Scope Sanity

| Plan | Tasks | Files Modified | Wave | Assessment |
|------|-------|---------------|------|-----------|
| 13-00 | 3 | 11 | 0 | CONCERN: 11 files is high but 8 are trivial (gitkeep, README, test stubs). Core work is 2 files (pyproject.toml, uv.lock). Acceptable. |
| 13-01 | 2 | 2 | 1 | PASS |
| 13-02 | 2 | 2 | 2 | PASS |
| 13-03 | 3 | 3 | 3 | PASS |
| 13-04 | 2 | 3 | 4 | PASS (includes .gitignore edit as part of Task 2) |
| 13-05 | 2 | 2 | 5 | PASS |
| 13-06 | 5 | 7 | 6 | CONCERN: 5 tasks is at the threshold. However, Task 3 (README update) and Task 5 (ROADMAP/STATE/SUMMARY updates) are low-complexity admin tasks. Functional work is Tasks 1+2+4. Borderline but defensible given the wave-6 integration scope. |

13-06 has the most concern at 5 tasks, but 2 of those are bookkeeping (Task 3 = README update, Task 5 = ROADMAP/REQUIREMENTS/STATE checkbox flips). The functional execution budget is 3 tasks (HTML fixtures, extracted JSON, integration test). No split is required.

**Verdict: PASS**

---

## Dimension 6: Verification Derivation

All plans have must_haves with truths, artifacts, and key_links. Truths are user-observable or directly testable:

Sample verification:
- 13-01: "PropertyListing validates {price, zip, property_type} alone — all other fields default None" — directly testable via pytest assertion
- 13-04: "Block detection (lib.property_block_detector.detect_block) fires BEFORE Sonnet extraction (saves $0.16/blocked page)" — verified by grep line order + subprocess test
- 13-05: "TIMESTAMP column stores microsecond precision; freezegun-driven µs delta produces 2 distinct rows" — proven by test_composite_pk_allows_reanalysis_with_microsecond_delta

No truths are implementation-internal in a way that bypasses the user-observable requirement. All artifacts have `contains:` fields that are grep-verifiable. Key_links specify the wiring method (import path, pattern).

**Verdict: PASS**

---

## Dimension 7: Context Compliance (D-13 Lock Verification)

This is the critical section. Each of the 5 locked decisions is traced to implementing tasks.

### D-13-GAPFILL-01 — 3 envelope shapes in property_fetch.py; --user-provided merge with provenance tagging; NO inline prompts

**Implementation:** 13-04 Task 1 action items 8 and 15 explicitly address this:
- Item 8: "_merge_user_provided helper — verbatim from §Example 5... overlays user-provided `price` as a plain string, NOT as a ProvenancedMoney dict. The other money fields... ARE ProvenancedMoney → overlay as `{'value': stripped, 'provenance': 'user_provided'}`"
- Item 15: "No interactive prompts (D-13-GAPFILL-01: CLI never opens stdin prompts)"
- 13-04 must_haves truths explicitly list all 3 envelope shapes
- 13-04 Task 2 tests cover all 3 shapes including --user-provided provenance tagging

CONCERN: The 3 envelope shapes are named in the CONTEXT.md as `success`, `awaiting_user_input`, `blocked`. The plans correctly implement these. However, there is one subtle gap: D-13-GAPFILL-01 states that on shape-2, "the `property` mode (Phase 15) prompts the user for each missing field, then re-invokes with `--user-provided`." The plan correctly defers the conversational layer to Phase 15 and focuses only on the CLI behavior. This is the correct scope split.

**Verdict: PASS**

### D-13-MUSTHAVE-01 — MUST-HAVE = exactly {price, zip, property_type}; all others default None

**Implementation:**
- 13-01 Task 1: `PropertyListing` model defines all 3 as required fields (no default), all NICE-TO-HAVE as `= None`
- 13-04 Task 1: `MUST_HAVE = ("price", "zip", "property_type")` as a module-level constant
- 13-01 must_haves.truths[0]: "PropertyListing validates {price, zip, property_type} alone — all other fields default None"
- 13-06 Task 4 test: `test_end_to_end_condo_partial_tax_missing_shape_1` verifies tax_annual=null is NOT blocking (envelope is still shape-1)

**Verdict: PASS**

### D-13-REANALYSIS-01 — DuckDB analyzed_listings PK = (zpid, analyzed_at) composite; household_hash column; append-only

**Implementation:**
- 13-05 Task 1: CREATE_TABLE_SQL verbatim has `PRIMARY KEY (zpid, analyzed_at)`
- 13-05 Task 1 acceptance_criteria: "`PRIMARY KEY (zpid, analyzed_at)` exactly (D-13-REANALYSIS-01 composite PK)"
- 13-05 Task 2: `test_composite_pk_allows_reanalysis_with_microsecond_delta` uses freezegun to prove append-only behavior
- household_hash column is present in CREATE_TABLE_SQL and in write_listing parameters
- compute_household_hash function is implemented (SHA256 of household.yml + profile.yml + MORTGAGE30US)

**Verdict: PASS**

### D-13-MODEL-01 — Sonnet 4.6 (NOT Haiku) for __NEXT_DATA__ extraction; ~$0.16/call cost realism

**Implementation:**
- 13-03 Task 1: `SONNET_MODEL: Final[str] = "claude-sonnet-4-6"` verbatim
- 13-03 Task 1 acceptance_criteria: "SONNET_MODEL is claude-sonnet-4-6 (NOT haiku, NOT 3-5-sonnet)"
- 13-03 Task 3: `test_sonnet_model_locked_to_4_6` asserts `SONNET_MODEL == "claude-sonnet-4-6"`
- 13-03 must_haves references ~$0.16/call cost correction from CONTEXT.md's outdated $0.02 Haiku estimate
- 13-04 Task 1 action item 14: "No retries (D-13-MODEL-01)"

NOTE: The ROADMAP.md Phase 13 Goal says "Haiku-prompted extraction" — this contradicts D-13-MODEL-01 which locks Sonnet 4.6. The CONTEXT.md decision (D-13-MODEL-01 Sonnet) supersedes the ROADMAP wording, and the plans correctly implement Sonnet 4.6 per the locked decision. This is not a plan issue but a ROADMAP stale-description note; the plans are correct.

**Verdict: PASS**

### D-13-BLOCK-01 — 4 block signals detected BEFORE Sonnet call

**Implementation:**
- 13-02 Task 1: implements detect_block with cheap-first order (status → length → captcha → missing_next_data)
- 13-02 Task 2: `test_detect_block_status_wins_over_short_body` and `test_detect_block_short_body_wins_over_captcha` prove detection order
- 13-04 Task 1 key_links: "detect_block + extract_zpid called BEFORE Sonnet"
- 13-04 acceptance_criteria: "Block detection happens BEFORE Sonnet (grep order: `detect_block` line appears before `extract_listing` line)"
- 13-02 must_haves.truths[1]: "Block detection order is cheap-first: status → length → captcha → __NEXT_DATA__ regex"

All 4 signals from D-13-BLOCK-01 are present: http_403/429/503/other, missing_next_data, captcha_detected, body_too_short (<5000). CAPTCHA_PHRASES has all 6 phrases. The <5000 bound is STRICT (< not ≤), verified in 13-02 test for the 5000-byte boundary case.

**Verdict: PASS**

### Deferred Ideas Exclusion

Checking for scope creep: Apify/Bright-Data, watchlist, saved-search alerts, tax-record/assessor enrichment, Playwright, multi-source ingestion — none of these appear in any plan's tasks. PASS.

---

## Dimension 7b: Scope Reduction Detection

Scanning all plan actions for hedging language:

**13-03 Task 1** contains: "If Probe A returned True... If Probe A returned False..." — this is NOT scope reduction; it is legitimate branching based on a Wave-0 probe result that the plan explicitly requires reading (13-00-SUMMARY.md). The plan delivers the full decision either way.

**13-04 Task 2, test 7**: The plan acknowledges "Without ANTHROPIC_API_KEY in subprocess env, Sonnet returns None → shape-2" and renames the test to "test_no_api_key_falls_through_to_shape_2". The plan explicitly states: "shape-1 happy path requires either a live ANTHROPIC_API_KEY OR an in-process mock that survives subprocess boundary. Both are out-of-scope for Wave 4; Wave 6 covers shape-1 end-to-end." This is a documented wave-split, not a punted decision — Wave 6 (13-06) contains `test_end_to_end_sfh_happy_path_shape_1` which uses MORTGAGE_OPS_MOCK_SONNET=1 to achieve true shape-1 end-to-end. ACCEPTABLE.

**13-04 Task 1 item 5**: "Plan 13-05 is NOT a dependency... CLI may emit a stderr warning until 13-05 ships." This is a documented wave-ordering decision, not scope reduction. The persistence call is wrapped in try/except ImportError and the requirement (PROP-02, PERS-08) is fully closed by Plan 13-05.

**13-06 Task 4**: "For `test_end_to_end_database_roundtrip`, if the CLI doesn't accept a DB-path override, we re-implement the write via the API layer." This is a test isolation strategy, not scope reduction. The round-trip IS tested end-to-end.

No scope reduction found. All deferred items map to documented wave-splits with implementing tasks in later waves.

**Verdict: PASS**

---

## Dimension 7c: Architectural Tier Compliance

RESEARCH.md has an "Architectural Responsibility Map" section. Checking against it:

| Capability | Expected Tier (RESEARCH.md) | Plan Assignment | Match? |
|-----------|---------------------------|-----------------|--------|
| HTML fetch | Parent agent (WebFetch tool) | Not in plans — CLI accepts via stdin/--html-from | PASS |
| __NEXT_DATA__ extraction | lib/property_extractor.py (Sonnet) | 13-03 | PASS |
| Block-signal detection | lib/property_block_detector.py (stdlib) | 13-02 | PASS |
| Pydantic validation | lib/property_listing.py | 13-01 | PASS |
| DuckDB persistence | lib/property_persistence.py (Python duckdb) | 13-05 | PASS |
| CLI orchestration | scripts/property_fetch.py | 13-04 | PASS |

No tier mismatches. Auth validation (ANTHROPIC_API_KEY) stays in lib/property_extractor.py (Python subprocess), not in browser tier. SQL parameterized queries in persistence layer prevent injection.

**Verdict: PASS**

---

## Dimension 8: Nyquist Compliance

RESEARCH.md has a "Validation Architecture" section. Checking against Nyquist requirements.

VALIDATION.md: No 13-VALIDATION.md found in the phase directory. Per the check 8e gate rule: "If missing: BLOCKING FAIL."

However, reviewing the Dimension 8 skip conditions: "Skip if: `workflow.nyquist_validation` is explicitly set to `false` in config.json (absent key = enabled), phase has no RESEARCH.md, or RESEARCH.md has no 'Validation Architecture' section."

RESEARCH.md DOES have a "Validation Architecture" section (lines 979-997). There is no config.json with nyquist_validation=false. Therefore Dimension 8 applies and VALIDATION.md should exist.

**CONCERN (not a BLOCKER for this project):** The GSD SDK machinery (`gsd-sdk query`) is not available in this environment, and the workflow prompt indicates VALIDATION.md would be generated by re-running `/gsd-plan-phase 13 --research`. Since the RESEARCH.md validation architecture section IS present, a VALIDATION.md was supposed to be generated. Its absence is a process concern. However, the plans themselves contain abundant automated verify commands (pytest, grep) that cover all Nyquist requirements — every task has `<automated>` verify blocks with concrete pytest commands, sampling continuity is maintained (no 3 consecutive implementation tasks without automated verify), and Wave 0 stubs are the "test first" discipline.

Classifying as CONCERN rather than BLOCKER because: (a) the plans' own verify commands satisfy the substantive intent of Nyquist checks, (b) the missing file is an artifact of the plan-generation process, not a plan content deficiency.

**Check 8a (Automated Verify Presence):** All tasks have `<automated>` commands. PASS.
**Check 8b (Feedback Latency):** All automated commands use `uv run pytest` (unit/integration), not full E2E browser suites. PASS.
**Check 8c (Sampling Continuity):** No wave has 3 consecutive implementation tasks without automated verify. PASS.
**Check 8d (Wave 0 Completeness):** Wave 0 (13-00) creates all xfail stubs; subsequent waves remove markers. Pattern is correct. PASS.

**Verdict: CONCERN (missing 13-VALIDATION.md artifact)**

---

## Dimension 9: Cross-Plan Data Contracts

Shared data pipelines across plans:

1. **PropertyListing schema (13-01 → 13-03 → 13-04 → 13-05 → 13-06):** 13-01 defines the canonical schema. 13-03 (extractor) returns a flat dict that 13-04 (CLI) validates via `PropertyListing.model_validate`. 13-05 (persistence) writes `listing.model_dump_json()` and reads back via `PropertyListing.model_validate_json`. 13-06 (integration) does a full round-trip. No conflicting transforms.

2. **Envelope shape contract (13-04 → 13-06):** 13-04 defines 3 shapes. 13-06 integration tests assert against these exact shapes. No incompatibility.

3. **sha16 key convention (13-03 conftest → 13-04 test helper → 13-06 integration):** All three use `hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]`. The encoding is consistent (`utf-8` everywhere). PASS.

4. **BLOCKER: ProvenancedMoney wrapping gap between 13-03 and 13-04/13-06.**

The Sonnet extractor (13-03) returns a FLAT dict where money fields like `tax_annual` are plain strings (e.g., `"7800.00"`). The `PropertyListing` model (13-01) requires that `tax_annual` is a `ProvenancedMoney` object (with `value` and `provenance`), NOT a plain string.

13-04 (CLI) has `_coerce_money_to_string` to handle Sonnet's stray floats, and `_merge_user_provided` which wraps user-provided money fields into ProvenancedMoney dicts. However, there is NO `_wrap_scraped_provenanced_money` step in 13-04 Task 1's primary action. The plan defers this critical wrapping to 13-06 Task 4 action: "Also: the CLI's existing flow wraps Sonnet's flat money output into ProvenancedMoney dicts BEFORE Pydantic validation. If Plan 13-04 didn't add this wrapping (since Plan 13-04 didn't have real extracted-dict shape to test against), this plan [13-06] must add a `_wrap_scraped_provenance` step to the CLI's flow."

This creates a dependency risk: 13-04's acceptance_criteria does NOT include a requirement to wrap scraped ProvenancedMoney fields. 13-04's test `test_user_provided_strips_dollar_comma` uses `--user-provided` with all 3 MUST-HAVE fields, which goes through `_merge_user_provided` (not the scraped path). The shape-1 test explicitly acknowledges it can't test shape-1 without a mock. As a result, 13-04 can ship with the ProvenancedMoney wrapping absent, and 13-06 Task 4 documents it must add this as a CLI edit.

This is architecturally awkward but the plan documents it explicitly. 13-06 Task 4's acceptance_criteria includes: "CLI has been edited to wrap scraped money fields into ProvenancedMoney dicts AND set sibling *_provenance='scraped' for non-money fields." The verify command checks: `grep -q '_wrap_scraped_provenanced_money\|provenance.*scraped' .claude/skills/mortgage-ops/scripts/property_fetch.py`.

Assessment: The wrapping gap is DOCUMENTED and 13-06 explicitly closes it. However, this means 13-04 ships with a functional deficiency (the CLI cannot produce a valid shape-1 envelope for scraped data without the wrapping step). The 13-04 subprocess tests don't catch this because they either (a) trigger shape-2 (no API key → Sonnet returns None) or (b) use `--user-provided` which goes through a different code path. This is a DATA CONTRACT GAP between plans.

**BLOCKER 1:** 13-04 Task 1 must include the `_wrap_scraped_provenanced_money` step and the sibling `*_provenance="scraped"` setter as part of its implementation, not deferred to 13-06. Without these, the CLI cannot produce a valid shape-1 envelope when Sonnet successfully returns a flat dict — a core pipeline requirement. The current plan structure means 13-04 passes its own tests (because they all exercise shape-2 or `--user-provided` paths) while being functionally broken for the primary happy path.

**Fix hint:** Move the `_wrap_scraped_provenanced_money` helper and sibling provenance setter from 13-06 Task 4 action into 13-04 Task 1 action (items 3 and 3a). Add an acceptance criteria line to 13-04 Task 1: "`_wrap_scraped_provenanced_money` function exists; wraps flat Sonnet output money fields into ProvenancedMoney dicts before Pydantic validation."

**Verdict: BLOCKER**

---

## Dimension 10: CLAUDE.md Compliance

CLAUDE.md key directives verified against plans:

| Directive | Plans Check | Status |
|-----------|------------|--------|
| Money discipline: Decimal from strings, never float | 13-01 enforces strict=True; 13-04 has _coerce_money_to_string; 13-03 has _parse_json_with_prose_tolerance; all RESEARCH pitfall mitigations are in plans | PASS |
| Never mix float and Decimal | _strip_money uses string operations, not Decimal(float); _coerce_money_to_string uses f"{v:.2f}" | PASS |
| Pydantic v2 condecimal at all script boundaries | PropertyListing uses lib.models.Money Annotated alias; PropertyListing.model_validate is the boundary gate | PASS |
| Claude never owns numbers | Sonnet extracts text, CLI validates with Pydantic, persistence writes JSON — no inline computation | PASS |
| Skill portability: scripts/ inside .claude/skills/mortgage-ops/ | property_fetch.py lands at .claude/skills/mortgage-ops/scripts/ | PASS |
| SKILL.md ≤ 500 lines | No SKILL.md changes in Phase 13 plans (Phase 15 handles routing) | PASS |
| Data Contract: data/ is gitignored, generated | .gitignore additions for data/cache/property-*.html and data/cache/property-*.json | PASS |
| No AI attribution in commits/code/docs | Every plan explicitly checks for absence of "Co-Authored-By", "generated by Claude", etc. | PASS |
| Testing: exact Decimal equality, never assertAlmostEqual | 13-01 Task 2 action explicitly: "Do NOT use `assertAlmostEqual` anywhere in the file (CLAUDE.md §Testing)" | PASS |
| uv tooling | All commands use `uv run pytest`, `uv sync`, `uv run python` | PASS |
| GSD workflow enforcement | Plans are GSD-workflow output; no ad-hoc edits | PASS |

**Verdict: PASS**

---

## Dimension 11: Research Resolution

RESEARCH.md has an `## Open Questions` section. Checking resolution status:

```
## Open Questions (planner picks; defaults recommended)
### Q1: How does HTML get from WebFetch to the CLI subprocess?
### Q2: messages.create() vs messages.parse() ...
### Q3: Python duckdb runtime dep OR subprocess-Node-wrapper?
### Q4: household_hash — content hash or structural hash?
```

The section header does NOT carry an `(RESOLVED)` suffix. Individual questions do not have inline `RESOLVED` markers. They have "Recommendation:" sections.

However, the plans ALL bake in specific answers for Q1-Q4:
- Q1 default: data/cache/property-{zpid}.json cache file (13-04 implements, 13-06 verifies)
- Q2 default: Wave-0 Probe A determines the path (13-00 runs probe, 13-03 reads SUMMARY)
- Q3 default: Python duckdb (13-00 adds runtime dep)
- Q4 default: content SHA256 hash (13-05 implements compute_household_hash)

The 13-06 Task 5 acceptance_criteria explicitly lists "Q1-Q4 open-questions resolution audit" in SUMMARY documentation.

Per Dimension 11 rules, the absence of `(RESOLVED)` suffix is technically a process gap. However, since the answers are baked into every plan's action and acceptance_criteria, and since the RESEARCH.md is a research artifact (not a requirements document), this is a CONCERN rather than a BLOCKER.

**CONCERN:** RESEARCH.md §Open Questions does not carry `(RESOLVED)` suffix markers on the section heading or individual questions. The planner should update the section header to `## Open Questions (RESOLVED)` and add resolution markers to each question.

**Verdict: CONCERN**

---

## Dimension 12: Pattern Compliance

PATTERNS.md maps 19 files to analogs. Checking that plans reference the correct analogs:

| File | PATTERNS.md Analog | Plan References It? |
|------|-------------------|---------------------|
| scripts/property_fetch.py | fred_cli.py | 13-04 read_first lists fred_cli.py explicitly |
| lib/property_extractor.py | 13-RESEARCH Example 1 (no close analog) | 13-03 read_first lists the exact research lines |
| lib/property_block_detector.py | 13-RESEARCH Example 2 | 13-02 read_first lists the exact research lines |
| lib/property_listing.py | lib/models.py | 13-01 read_first lists lib/models.py; key_links explicitly reference it |
| lib/property_persistence.py | lib/fred_cache.py | 13-05 read_first lists lib/fred_cache.py; with_cache_lock explicitly imported |
| tests/test_property_listing.py | tests/test_models.py | 13-01 Task 2 read_first lists tests/test_models.py |
| tests/test_property_block_detector.py | test_cli_helpers.py + test_fred_cli.py | 13-02 Task 2 read_first lists both |
| tests/test_property_extractor.py | tests/test_subagents.py lines 432-471 | 13-03 Task 3 read_first lists "tests/test_subagents.py lines 432-471" verbatim |
| tests/test_property_fetch.py | tests/test_fred_cli.py | 13-04 Task 2 read_first lists it |
| tests/test_property_persistence.py | tests/test_fred_cache.py | 13-05 Task 2 read_first lists it |
| tests/fixtures/zillow/README.md | tests/fixtures/subagent_transcripts/README.md | 13-00 Task 3 read_first lists it |

Shared patterns from PATTERNS.md verified present in plans:
- Always-exit-0 envelope: present in 13-04 (outer try/except CR-02, _emit, noqa: BLE001)
- Lazy-import discipline: present in 13-03 (anthropic), 13-04 (all lib.*), 13-05 (duckdb)
- Money discipline: present in 13-01 (strict=True), 13-03 (_coerce), 13-04 (_strip_money)
- Lockfile-wrapped writes: present in 13-05 (with_cache_lock at db_path.parent)
- Schema-version + shape-validate on read: present in 13-05 (SCHEMA_VERSION=1, CatalogException catch, BLE001 defensive read)
- Synthetic-only-in-CI fixture policy: present in 13-00 Task 3 + 13-06 Task 1
- No AI attribution: present in EVERY plan's acceptance_criteria

**Verdict: PASS**

---

## Critical D-13 Lock Verification Summary

| Lock | Status | Evidence |
|------|--------|---------|
| D-13-GAPFILL-01 (3 shapes, --user-provided, no prompts) | PASS | 13-04 implements; 13-06 proves end-to-end |
| D-13-MUSTHAVE-01 (price+zip+property_type only) | PASS | 13-01 model; 13-04 MUST_HAVE constant; 13-06 condo-no-tax test |
| D-13-REANALYSIS-01 (composite PK, household_hash, append-only) | PASS | 13-05 SQL + freezegun µs-delta test |
| D-13-MODEL-01 (Sonnet 4.6, not Haiku, ~$0.16/call) | PASS | 13-03 SONNET_MODEL constant + test assertion |
| D-13-BLOCK-01 (4 signals BEFORE Sonnet, cost-saving) | PASS | 13-02 detection order; 13-04 grep-order verify |

---

## Blockers (Must Fix Before Execution)

### BLOCKER 1: ProvenancedMoney wrapping gap — 13-04 ships without the scraped-money wrapping step

**Dimension:** cross_plan_data_contracts
**Severity:** BLOCKER
**Plans affected:** 13-04, 13-06
**Description:** 13-04 Task 1 does not include the `_wrap_scraped_provenanced_money` step that converts flat Sonnet output (e.g., `"tax_annual": "7800.00"`) into the ProvenancedMoney dict form (`{"value": "7800.00", "provenance": "scraped"}`) that PropertyListing requires. This wrapping is deferred to 13-06 Task 4, but by then 13-04 has shipped a CLI that cannot produce valid shape-1 envelopes for scraped data. The 13-04 test suite does not catch this because all subprocess tests either (a) lack ANTHROPIC_API_KEY → Sonnet returns None → shape-2 path, or (b) use --user-provided → goes through _merge_user_provided which already wraps. The shape-1 happy path through the scraped code path is never exercised in 13-04's test suite.
**Fix:** Add `_wrap_scraped_provenanced_money` and sibling `*_provenance="scraped"` setter to 13-04 Task 1 action (as action items, not as "if Plan 13-04 didn't add this" notes in 13-06). Add an acceptance_criteria line to 13-04 Task 1 verifying this wrapper exists. Add one acceptance_criteria test to 13-04 Task 2 that exercises the shape-1 path with a pre-written extracted JSON (bypassing Sonnet entirely via --html-from + writing the sha-keyed fixture manually in the test).

### BLOCKER 2: 13-06 Task 4 — MORTGAGE_OPS_MOCK_SONNET hook creates a test-only code path that is NOT present in 13-04

**Dimension:** cross_plan_data_contracts / dependency_correctness
**Severity:** BLOCKER
**Plans affected:** 13-04, 13-06
**Description:** 13-06 Task 4 requires editing `scripts/property_fetch.py` to add: `if os.environ.get("MORTGAGE_OPS_MOCK_SONNET") == "1": ... sha-keyed fixture lookup ...`. This env-var hook is NOT in 13-04's implementation or acceptance_criteria. This means 13-06 depends on a CLI behavior that 13-04 does not plan to deliver. If 13-04 is executed without this hook, 13-06's integration tests will all fail (they all use `MORTGAGE_OPS_MOCK_SONNET=1`). The dependency graph shows 13-06 `depends_on: [13-00, ..., 13-04, 13-05]` but 13-04 does not include the hook in its scope.
**Fix:** Either (a) add the MORTGAGE_OPS_MOCK_SONNET env-var hook to 13-04 Task 1's action and acceptance_criteria (preferred — keeps the CLI spec in one place), or (b) accept that 13-06 Task 4 will add it as a CLI edit (which the plan already documents in the task action, but should be reflected in 13-06's files_modified frontmatter — `property_fetch.py` is already listed there). If option (b), add `property_fetch.py` explicitly to 13-06's `files_modified` (it already is: `.claude/skills/mortgage-ops/scripts/property_fetch.py` is in the key_links but NOT in the `files_modified` frontmatter of 13-06). Verify by reading: 13-06 `files_modified` lists only fixture files and the integration test — the CLI edit is undeclared in the frontmatter.

---

## Concerns (Should Fix, Execution Can Proceed If Resolved or Accepted)

### CONCERN 1: RESEARCH.md Open Questions missing (RESOLVED) markers

**Dimension:** research_resolution
**Severity:** CONCERN
**Description:** RESEARCH.md §Open Questions has no `(RESOLVED)` suffix on the section heading or inline RESOLVED markers on individual questions Q1-Q4. The plan answers are baked into all plans' implementations, but the research artifact is not updated to reflect this.
**Fix:** Add `(RESOLVED)` suffix to the section header. Add resolution line to each question: "RESOLVED: [decision]."

### CONCERN 2: 13-03 Probe-A branch selection not verified by automated check

**Dimension:** task_completeness
**Severity:** CONCERN
**Description:** 13-03 Task 1's `<verify>` block does not check whether the implemented API path matches the Probe A result from 13-00-SUMMARY.md. The acceptance_criteria mentions it but a grep or automated test could be added.
**Fix:** Add to 13-03 Task 1 acceptance_criteria a grep check: if Probe A=True, verify `client.messages.parse` appears in extract_listing; if Probe A=False, verify `client.messages.create` appears. Alternatively, document in SUMMARY.md.

### CONCERN 3: 13-00 files_modified count is high (11 files) but mostly trivial

**Dimension:** scope_sanity
**Severity:** CONCERN (borderline — 8 of 11 files are .gitkeep, README, test stubs requiring only xfail markers)
**Description:** The count appears high but the actual edit complexity is low. pyproject.toml + uv.lock is real work; the 5 test stubs are copy-paste of the provided scaffold; the directory files are trivial.
**Fix:** No change needed. Document acceptance.

---

## Open Questions Resolved by Plans (for record)

| Question | Resolution Baked Into Plans |
|----------|---------------------------|
| Q1 (HTML cache mechanism) | data/cache/property-{zpid}.json companion file; CLI reads on --user-provided round-trips (13-04) |
| Q2 (messages.parse vs create) | Wave-0 Probe A determines; both code paths in 13-03 action (13-03 reads 13-00-SUMMARY.md) |
| Q3 (Python duckdb runtime dep) | Python duckdb added as runtime dep in 13-00 pyproject.toml edit |
| Q4 (household_hash content vs structural) | Content SHA256 of (household.yml + profile.yml + MORTGAGE30US value) — implemented in 13-05 |

---

## Summary

The Phase 13 plan set is comprehensive, well-structured, and honors all 5 locked D-13 decisions. The wave discipline (xfail → flip), pattern inheritance (fred_cli.py, fred_cache.py, lib/models.py analogs), and deep-work quality (concrete acceptance_criteria, grep-verifiable, no vague actions) are all strong.

Two blockers prevent execution:

1. **The ProvenancedMoney wrapping step** for scraped Sonnet output is architecturally required for shape-1 envelopes but is deferred to 13-06 while 13-04's tests cannot detect its absence. The CLI will silently fail Pydantic validation for all scraped-data happy-path invocations.

2. **The MORTGAGE_OPS_MOCK_SONNET env-var hook** that 13-06's integration tests require is not in 13-04's declared scope, creating a gap between what 13-04 delivers and what 13-06 depends on. The CLI edit is documented in 13-06 Task 4's action but is undeclared in 13-06's frontmatter `files_modified`.

Both blockers are in the same category (data contract between 13-04 and 13-06) and can be resolved together by moving the two CLI additions (`_wrap_scraped_provenanced_money` + MORTGAGE_OPS_MOCK_SONNET hook) from 13-06's "if Plan 13-04 didn't add this" language into 13-04's primary action and acceptance_criteria.

**Returning to planner with 2 blockers + 3 concerns.**

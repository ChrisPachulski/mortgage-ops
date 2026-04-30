---
phase: 05
plan: 05
type: execute
wave: 5
depends_on:
  - "05-00"
  - "05-02"
  - "05-03"
files_modified:
  - references/arm-mechanics.md
  - lib/arm.py
  - tests/test_arm.py
autonomous: true
requirements:
  - ARM-09
tags:
  - phase-05
  - arm-modeling
  - documentation
  - selling-guide-citations
  - arm-09
must_haves:
  truths:
    - "references/arm-mechanics.md exists at repo root with all 7 D-08 sections (the 6 originally enumerated + the LM-3 teaser-ARM section per D-08 [REVISED])"
    - "All citation URLs in references/arm-mechanics.md resolve to the corrected Selling Guide sections per D-08 [REVISED 2026-04-30]: Fannie B2-1.4-02 (NOT B5-3.5-01), Freddie 6302.7(b) + SOFR-Indexed-ARMs product page (NOT §4404), CFPB §1951, AmericU 5/6 disclosure"
    - "lib/arm.py ARMTerms model docstring includes a verbatim citation line: 'See references/arm-mechanics.md for reset/cap/floor convention.'"
    - "Wave 0 stubs test_arm_mechanics_doc_sections_present, test_arm_terms_docstring_cites_arm_mechanics, test_arm_mechanics_citations all flip from xfail to passing"
    - "ROADMAP SC-5 verified: references/arm-mechanics.md cites Selling Guides AND is referenced from the ARMTerms model docstring"
    - "Phase 4 + Phase 3 baselines preserved unchanged"
  artifacts:
    - path: "references/arm-mechanics.md"
      provides: "Phase 5 ARM mechanics reference doc with corrected Selling Guide + CFPB + AmericU citations"
      min_lines: 120
    - path: "lib/arm.py"
      provides: "ARMTerms docstring extended with a one-line citation to references/arm-mechanics.md"
      contains: "See references/arm-mechanics.md"
  key_links:
    - from: "lib/arm.py ARMTerms class docstring"
      to: "references/arm-mechanics.md"
      via: "literal text reference 'See references/arm-mechanics.md for ...'"
      pattern: "See references/arm-mechanics.md"
    - from: "references/arm-mechanics.md Section 1 (Reset month convention)"
      to: "https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms"
      via: "URL citation"
      pattern: "selling-guide.fanniemae.com/sel/b2-1.4-02"
---

<objective>
Ship `references/arm-mechanics.md` at repo root with the 7 D-08 [REVISED 2026-04-30] sections — using the corrected Selling Guide section numbers (Fannie B2-1.4-02, Freddie 6302.7(b)) instead of the originally-locked-but-wrong B5-3.5-01 + §4404. Add the inline docstring citation to ARMTerms in lib/arm.py per ROADMAP SC-5.

Closes ARM-09 ("`references/arm-mechanics.md` documents conventions with Freddie/Fannie Selling Guide citations") + ROADMAP SC-5 ("references/arm-mechanics.md cites Selling Guides; cited from ARMTerms docstring").

Purpose: Two reasons:
1. **Regulatory traceability** — every documented engine choice (reset month convention, cap precedence, floor algebra, lifetime cap base for teaser ARMs) MUST cite a regulatory source. RESEARCH §Q4 verified the original D-08 citations were wrong (B5-3.5-01 returns 404; §4404 is stale); this plan ships the verified-correct citations: B2-1.4-02 (last updated 2025-12-10), Freddie 6302.7(b) + SOFR-Indexed-ARMs product page, CFPB §1951, AmericU 5/6 disclosure.
2. **Discoverability via docstring** — Phase 11 amortization-agent + Phase 8 stress + any user invoking `python -c "from lib.arm import ARMTerms; help(ARMTerms)"` lands on the docstring; the inline reference makes the doc location grep-discoverable from the model.

Output: `references/arm-mechanics.md` ~120 lines with 7 sections + citations; lib/arm.py ARMTerms docstring +1 line; 3 ARM-09 stubs flipped.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/05-arm-modeling/05-CONTEXT.md
@.planning/phases/05-arm-modeling/05-RESEARCH.md
@.planning/phases/05-arm-modeling/05-PATTERNS.md
@CLAUDE.md
@lib/arm.py
@tests/test_arm.py

<interfaces>
D-08 [REVISED 2026-04-30] (CONTEXT.md lines 196-209) — locked content for references/arm-mechanics.md:

1. **Reset month convention** — locked: rate change at START of month 61 (5/1), 85 (7/1), 121 (10/1), 61 (5/6 with second reset at 67). Citations:
   - Fannie Mae Selling Guide §B2-1.4-02 "Adjustable-Rate Mortgages (ARMs)" (last updated 2025-12-10): https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms
   - Freddie Mac Single-Family Seller/Servicer Guide §6302.7(b)
   - Freddie SOFR-Indexed ARMs product page: https://sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms

2. **Cap precedence** — initial_cap at first reset; periodic_cap at every subsequent reset; lifetime_cap measured against note_rate. Citations: Fannie B2-1.4-02 + Freddie 6302.7(b) + CFPB §1951 (https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/)

3. **Floor algebra** — effective_floor = max(margin, floor_rate); floor_rate is REQUIRED in this engine — no implicit margin fallback. Citations: Fannie B2-1.4-02 ("Mortgage interest rates may never decrease to less than the ARM's margin"), Freddie 6302.7(b)

4. **Quantization** — rate quantize at 6 decimal places per Phase 4 D-09 / promoted lib.money.quantize_rate (Phase 5 D-14). Engine convention; not regulator-mandated.

5. **Negative amortization OUT of scope** — Phase 5 supports only fully-amortizing ARMs (D-12). Cite CONTEXT.md D-12.

6. **`index_series_id` semantics** — metadata only in Phase 5; Phase 12 maps to FRED MCP series IDs.

7. **Teaser-ARM lifetime cap base — engine choice, not regulator-mandated** (D-08 [REVISED] item 7 / LM-3): D-02 measures the lifetime ceiling against `arm_terms.note_rate` (with `note_rate=None` collapsing to `loan.annual_rate`). CFPB §1951 describes the lifetime cap as measured "from the initial rate" — for teaser-rate ARMs, this engine deliberately uses `note_rate` as the lifetime base because that matches industry practice for teaser products. Document as explicit engine choice.

ROADMAP SC-5 — `references/arm-mechanics.md` cites Selling Guides AND is referenced from ARMTerms model docstring.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create references/arm-mechanics.md with the 7 D-08 sections + corrected citations</name>
  <files>references/arm-mechanics.md</files>
  <read_first>
    - 05-CONTEXT.md D-08 [REVISED 2026-04-30] block (lines 196-209) — locked content
    - 05-RESEARCH.md §Q4 (lines 93-122) — full citation table with corrected URLs
    - 05-RESEARCH.md §LM-3 (lines 654-658) — teaser-ARM section content
    - CLAUDE.md project rules — no AI attribution anywhere
  </read_first>
  <action>
    Create the file `references/arm-mechanics.md` at repo root. Phase 10 will mirror or symlink it into `.claude/skills/mortgage-ops/references/`; Phase 5 ships only the repo-root copy.

    File content (literal Markdown — no YAML frontmatter; this is documentation, not config):

    ```
    # ARM Mechanics — mortgage-ops Phase 5 Reference

    This document records the conventions implemented by `lib/arm.py` (ARM
    adjustable-rate mortgage engine) and pairs each convention with its
    regulatory citation. All section numbers and URLs were verified on
    2026-04-30 against the live Selling Guides + CFPB explainer.

    Cited from `lib.arm.ARMTerms.__doc__` per ROADMAP SC-5.

    ---

    ## 1. Reset Month Convention

    The rate change applies at the START of the post-fixed-period month:

    | Product | Initial fixed period | First reset month | Subsequent resets |
    |---------|---------------------|-------------------|-------------------|
    | 5/1     | 60 months            | Month 61          | Every 12 months (73, 85, ...) |
    | 7/1     | 84 months            | Month 85          | Every 12 months (97, 109, ...) |
    | 10/1    | 120 months           | Month 121         | Every 12 months (133, 145, ...) |
    | 5/6 SOFR| 60 months            | Month 61          | Every 6 months (67, 73, 79, ...) |

    The off-by-one — payment at month 60 still uses the initial rate; payment
    at month 61 uses the new rate — is the source of PITFALL 5 in
    `.planning/research/PITFALLS.md`. ROADMAP SC-3 mandates fixtures covering
    BOTH directions (month 59 still old rate; month 61 already new rate).

    **Citations:**
    - Fannie Mae Selling Guide §B2-1.4-02 "Adjustable-Rate Mortgages (ARMs)" (last updated 2025-12-10):
      https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms
    - Freddie Mac Single-Family Seller/Servicer Guide §6302.7(b) (delivery instructions for ARM mortgages)
    - Freddie SOFR-Indexed ARMs product page (3/6, 5/6, 7/6, 10/6 reset cadence):
      https://sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms
    - AmericU 5/6 SOFR ARM Disclosure (worked example confirming month 61 first reset, month 67 second reset):
      https://www.americu.com/wp-content/uploads/2022/06/5_6-SOFR-ARM-Program-Disclosure-2_1_5-CAPS.pdf

    > **Citation correction note (2026-04-30):** The originally locked
    > references in CONTEXT.md D-08 cited Fannie §B5-3.5-01 (which returns
    > 404; that section group is about VA-related underwriting, not ARMs)
    > and Freddie §4404 (stale section number; modern Freddie URLs use
    > §6302.7(b) + Chapter 4203). Both have been corrected to the
    > verified-current sections shown above.

    ---

    ## 2. Cap Precedence

    Three caps apply to every reset event:

    | Cap | Applied at | Formula |
    |-----|------------|---------|
    | `initial_cap_bps` | First reset only (epoch_idx == 1) | `prior_rate + initial_cap_bps / 10000` |
    | `periodic_cap_bps` | Every reset after the first | `prior_rate + periodic_cap_bps / 10000` |
    | `lifetime_cap_bps` | Every reset (a single ceiling for the loan's life) | `note_rate + lifetime_cap_bps / 10000` |

    The binding ceiling for any reset = `min(applicable_cap_ceiling, lifetime_ceiling)`.
    The `applied_cap` field on `ResetEvent` records WHICH constraint bound the new rate
    (`"initial"`, `"periodic"`, `"lifetime"`, `"floor"`, or `"none"`); D-10 citation-coverage
    requires every Literal value to be exercised by at least one fixture.

    **Citations:**
    - Fannie Mae Selling Guide §B2-1.4-02 (cap structure, periodic cap precedence)
    - Freddie Mac Single-Family Seller/Servicer Guide §6302.7(b)
    - CFPB §1951 (lifetime cap explainer):
      https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/

    ---

    ## 3. Floor Algebra

    The post-reset rate is never below the effective floor:

    ```
    effective_floor = max(margin_bps / 10000, floor_rate)
    ```

    `floor_rate` is REQUIRED on the `ARMTerms` model — there is no default and no
    implicit margin fallback. This is a deliberate "fail loud, no inference" choice
    (CLAUDE.md money discipline + project's "Claude never owns numbers" doctrine):
    every caller must explicitly choose a floor.

    Fannie Mae Selling Guide §B2-1.4-02 specifies:
    > "Mortgage interest rates may never decrease to less than the ARM's margin,
    > regardless of any downward interest rate cap."

    The engine's `max(margin, floor_rate)` is a strict generalization (allows the
    caller to set a configured floor higher than margin); industry-standard but
    engine-specific in the sense that the configured floor is an extension beyond
    the regulatory minimum.

    **Citations:**
    - Fannie Mae Selling Guide §B2-1.4-02 (no rate decrease below margin)
    - Freddie Mac Single-Family Seller/Servicer Guide §6302.7(b)

    ---

    ## 4. Quantization

    All `Rate`-typed values flow through `lib.money.quantize_rate(...)` at 6 decimal
    places using ROUND_HALF_UP (CLAUDE.md money discipline; Phase 4 D-09 / Phase 5 D-14).

    Quantize ONCE at end-of-period; never quantize mid-calculation (Phase 1 PITFALLS,
    Phase 3 D-04 inherited).

    The 6-decimal-place quantum matches `lib.models.Rate` constraint
    (`Annotated[Decimal, Field(max_digits=7, decimal_places=6)]`). Values computed
    via division — LTV, DTI, fully-indexed ARM rate — can otherwise produce 28-digit
    Decimals that the model rejects.

    **Engine choice; not regulator-mandated.** Selling Guides specify the cap formulas
    but not the rate quantum. The 6-decimal choice aligns with project's `lib.models.Rate`
    type contract (Phase 1).

    ---

    ## 5. Negative Amortization OUT of Scope

    Phase 5's engine assumes the per-period payment is recomputed at each epoch via
    `npf.pmt(period_rate, remaining_term, remaining_balance)`. Negative-amortization
    products — Option ARM, payment-cap ARMs where the borrower may pay less than
    full interest — are explicitly OUT of v1 (CONTEXT.md D-12).

    Conventional fully-amortizing ARMs only: every payment fully covers interest;
    principal balance trends to zero by the loan's term_months.

    Add support only if a real consumer needs to model these products (rare for
    personal-use household analysis).

    **Citation:** CONTEXT.md D-12 (project decision).

    ---

    ## 6. `index_series_id` Semantics

    `ARMTerms.index_series_id` is metadata only in Phase 5: a free-form string
    identifying the rate index ("MORTGAGE30US", "SOFR1Y", etc.). The engine does
    NOT look up the index value at runtime — Phase 5 takes caller-supplied
    `assumed_index_rate` + optional `index_path` overrides per D-01.

    Phase 12 will integrate the FRED MCP server (`stefanoamorelli/fred-mcp-server`)
    to populate `assumed_index_rate` from `MORTGAGE30US` weekly value at SKILL.md
    narration time. At that point `index_series_id` may be tightened from a free-form
    string to a Literal-or-enum constraint mapping to FRED series IDs.

    **Citation:** Phase 12 plans (deferred); CONTEXT.md D-13.

    ---

    ## 7. Teaser-ARM Lifetime Cap Base — Engine Choice

    For non-teaser ARMs, `loan.annual_rate == initial_rate == note_rate` and the
    lifetime ceiling computation is unambiguous: `note_rate + lifetime_cap_bps / 10000`.

    For TEASER ARMs, where `loan.annual_rate < note_rate` (e.g., a 3% teaser
    introductory rate with a 5% post-teaser note rate), there are two valid conventions:

    - **Engine choice (locked in CONTEXT.md D-02):** Lifetime ceiling = `note_rate + lifetime_cap_bps / 10000`.
      For the example above (note_rate=0.05, lifetime_cap_bps=500), ceiling = 0.10.
      Callers supply the post-teaser note rate explicitly via `arm_terms.note_rate`;
      this engine produces a 10% ceiling.
    - **CFPB §1951 description:** "the rate can never be more than five percentage
      points either higher or lower from the **initial rate**." For the same
      example with initial=0.03, this would yield a ceiling of 0.08 (3pp lower).

    The engine deliberately uses the post-teaser `note_rate` as the lifetime base
    because that matches industry practice for teaser products and is the convention
    in Fannie B2-1.4-02 "Standard ARM" worked examples (where teaser products use
    the post-teaser rate as the regulatory note rate). The CFPB phrasing is a
    consumer-explainer simplification that conflates teaser and non-teaser ARMs.

    **Disclosed as explicit engine choice** rather than left silent so a teaser-rate
    ARM consumer (e.g., Phase 8 stress, Phase 11 amortization-agent) gets a
    reproducible 10% ceiling regardless of which convention the user expected.

    **Citations:**
    - CFPB §1951 (alternative convention):
      https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/
    - Fannie Mae Selling Guide §B2-1.4-02 (industry convention; engine-aligned)

    ---

    ## Appendix — Citation Index

    | URL | Section / Anchor | Last verified |
    |-----|------------------|----------------|
    | https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms | §B2-1.4-02 ARM eligibility, cap structure, floor convention | 2026-04-30 (last updated 2025-12-10) |
    | https://sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms | Freddie SOFR-Indexed ARMs (3/6, 5/6, 7/6, 10/6) | 2026-04-30 |
    | https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/ | CFPB Ask CFPB §1951 ARM rate caps | 2026-04-30 |
    | https://www.americu.com/wp-content/uploads/2022/06/5_6-SOFR-ARM-Program-Disclosure-2_1_5-CAPS.pdf | AmericU 5/6 SOFR ARM Disclosure (2/1/5 caps) | 2026-04-30 (frozen lender artifact, 2022) |

    Annual re-validation cadence: each calendar year, confirm each URL still
    resolves; if any have moved, update the index above.
    ```

    Notes:
    - The file uses pure Markdown; no YAML frontmatter; no AI attribution per CLAUDE.md project rules.
    - The "Citation correction note" callout at the end of Section 1 documents the D-08 [REVISED] history.
    - Section 7 (teaser-ARM choice) is the LM-3 disclosure mandated by D-08 [REVISED 2026-04-30].
  </action>
  <verify>
    <automated>test -f references/arm-mechanics.md &amp;&amp; wc -l references/arm-mechanics.md</automated>
  </verify>
  <acceptance_criteria>
    - File `references/arm-mechanics.md` exists with at least 120 lines
    - `grep -c '^## ' references/arm-mechanics.md` returns at least 7 (the 7 D-08 sections; appendix may add an 8th `##`)
    - `grep -c 'b2-1.4-02' references/arm-mechanics.md` returns at least 1 (Fannie B2-1.4-02 section)
    - `grep -c '6302.7(b)' references/arm-mechanics.md` returns at least 1 (Freddie modern section)
    - `grep -c '1951' references/arm-mechanics.md` returns at least 1 (CFPB §1951)
    - `grep -c 'AmericU' references/arm-mechanics.md` returns at least 1 (5/6 SOFR disclosure citation)
    - `grep -c 'B5-3.5-01' references/arm-mechanics.md` returns 0 (the BROKEN citation must NOT appear)
    - `grep -c '4404' references/arm-mechanics.md` returns 0 (the STALE Freddie citation must NOT appear)
    - `grep -c 'selling-guide.fanniemae.com/sel/b2-1.4-02' references/arm-mechanics.md` returns at least 1 (verified-current Fannie URL)
    - `grep -c 'sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms' references/arm-mechanics.md` returns at least 1 (verified-current Freddie URL)
    - `grep -c 'consumerfinance.gov/ask-cfpb/what-are-rate-caps' references/arm-mechanics.md` returns at least 1 (verified-current CFPB URL)
    - `grep -c '5_6-SOFR-ARM-Program-Disclosure' references/arm-mechanics.md` returns at least 1 (AmericU PDF URL)
    - `grep -ciE 'reset month convention' references/arm-mechanics.md` returns at least 1 (Section 1 header text)
    - `grep -ciE 'cap precedence' references/arm-mechanics.md` returns at least 1 (Section 2)
    - `grep -ciE 'floor algebra' references/arm-mechanics.md` returns at least 1 (Section 3)
    - `grep -ciE 'quantization' references/arm-mechanics.md` returns at least 1 (Section 4)
    - `grep -ciE 'negative amortization' references/arm-mechanics.md` returns at least 1 (Section 5)
    - `grep -ciE 'index_series_id' references/arm-mechanics.md` returns at least 1 (Section 6)
    - `grep -ciE 'teaser' references/arm-mechanics.md` returns at least 1 (Section 7)
    - `grep -c 'co-authored' references/arm-mechanics.md` returns 0 (no AI attribution per CLAUDE.md)
    - `grep -c -i 'claude' references/arm-mechanics.md` returns 0 (no AI attribution)
    - `grep -c -i 'anthropic' references/arm-mechanics.md` returns 0 (no AI attribution)
  </acceptance_criteria>
  <done>
    references/arm-mechanics.md exists with all 7 sections + corrected citations; no broken legacy citations present; no AI attribution.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add ARMTerms docstring citation to references/arm-mechanics.md</name>
  <files>lib/arm.py</files>
  <read_first>
    - lib/arm.py (Wave 3 state — ARMTerms class with current docstring)
    - 05-CONTEXT.md D-08 line 209 ("Cited from ARMTerms model docstring as an inline reference")
    - ROADMAP SC-5
  </read_first>
  <action>
    Modify the `ARMTerms` class docstring in lib/arm.py to add an explicit citation line referencing references/arm-mechanics.md.

    Locate the ARMTerms docstring (created in Wave 2):

    Current docstring (Wave 2 baseline; preserve verbatim except for the inline citation insertion):

    ```
    """ARM contractual terms (8 explicit fields per ARM-01 + optional note_rate per D-02).

    Field schema locked in CONTEXT.md D-06. Every field is REQUIRED except
    note_rate; floor_rate has NO default per D-02 (forces explicit caller
    choice; matches mortgage-ops 'fail loud, no inference' discipline).

    Wave 5 (Plan 05-05) appends a docstring citation:
        See references/arm-mechanics.md for reset/cap/floor convention.
    """
    ```

    Replace with:

    ```
    """ARM contractual terms (8 explicit fields per ARM-01 + optional note_rate per D-02).

    See references/arm-mechanics.md for reset/cap/floor convention, including
    Selling Guide citations (Fannie B2-1.4-02, Freddie 6302.7(b)), CFPB §1951,
    and the AmericU 5/6 SOFR ARM disclosure (Phase 5 ARM-09 + ROADMAP SC-5).

    Field schema locked in CONTEXT.md D-06. Every field is REQUIRED except
    note_rate; floor_rate has NO default per D-02 (forces explicit caller
    choice; matches mortgage-ops 'fail loud, no inference' discipline).
    """
    ```

    The citation line `See references/arm-mechanics.md for reset/cap/floor convention.`
    is the load-bearing token that test_arm_terms_docstring_cites_arm_mechanics will grep for.

    Do NOT modify any other class or function docstring in this task. Wave 5 only touches ARMTerms.
  </action>
  <verify>
    <automated>python -c "from lib.arm import ARMTerms; assert 'references/arm-mechanics.md' in (ARMTerms.__doc__ or ''); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'See references/arm-mechanics.md' lib/arm.py` returns at least 1
    - `grep -c 'B2-1.4-02' lib/arm.py` returns at least 1 (Selling Guide cite in docstring)
    - `python -c 'from lib.arm import ARMTerms; assert "references/arm-mechanics.md" in ARMTerms.__doc__'` exits 0
    - `mypy --strict lib/arm.py` exits 0
    - `ruff check lib/arm.py` exits 0
    - `ruff format --check lib/arm.py` exits 0
    - The remaining ARMTerms field declarations (from Wave 2) and engine code (from Wave 3) are unchanged
    - `grep -c 'def build_arm_schedule' lib/arm.py` still returns 1 (Wave 3 engine intact)
  </acceptance_criteria>
  <done>
    ARMTerms docstring cites references/arm-mechanics.md with verbatim load-bearing string; mypy + ruff clean; engine code untouched.
  </done>
</task>

<task type="auto">
  <name>Task 3: Flip 3 ARM-09 Wave-0 stubs in tests/test_arm.py</name>
  <files>tests/test_arm.py</files>
  <read_first>
    - tests/test_arm.py (Wave 4 state: 14 xfails)
    - references/arm-mechanics.md (just created)
    - lib/arm.py (just modified)
    - 05-VALIDATION.md ARM-09 rows
  </read_first>
  <action>
    Flip exactly 3 ARM-09 stubs to passing tests. Each test reads files (references/arm-mechanics.md or lib/arm.py via importlib) and asserts content via grep-style string checks.

    Stubs to flip:
    1. `test_arm_mechanics_doc_sections_present` — file exists with the 7 D-08 sections
    2. `test_arm_terms_docstring_cites_arm_mechanics` — ARMTerms docstring contains the citation token
    3. `test_arm_mechanics_citations` — file contains all 4 verified-correct URL fragments AND zero of the 2 broken legacy citation tokens

    For each, REMOVE the `@pytest.mark.xfail(...)` decorator AND replace the body.

    **Flip 1: test_arm_mechanics_doc_sections_present**

    Remove decorator. Body:

    ```
    """ARM-09 + D-08: references/arm-mechanics.md exists with all 7 D-08 sections."""
    project_root = Path(__file__).resolve().parent.parent
    doc_path = project_root / "references" / "arm-mechanics.md"
    assert doc_path.is_file(), f"references/arm-mechanics.md missing at {doc_path}"
    content = doc_path.read_text().lower()
    # 7 D-08 [REVISED 2026-04-30] sections must all appear (case-insensitive token match):
    required_section_tokens = [
        "reset month convention",        # Section 1
        "cap precedence",                # Section 2
        "floor algebra",                 # Section 3
        "quantization",                  # Section 4
        "negative amortization",         # Section 5
        "index_series_id",               # Section 6
        "teaser",                        # Section 7
    ]
    for token in required_section_tokens:
        assert token in content, f"Section token '{token}' missing from references/arm-mechanics.md"
    # Document must have at least 6 ## headings (the 7 sections; appendix may add another)
    heading_count = sum(1 for line in content.splitlines() if line.startswith("## "))
    assert heading_count >= 7, f"Expected at least 7 ## headings, got {heading_count}"
    ```

    **Flip 2: test_arm_terms_docstring_cites_arm_mechanics**

    Remove decorator. Body:

    ```
    """ARM-09 + ROADMAP SC-5: ARMTerms model docstring cites references/arm-mechanics.md."""
    from lib.arm import ARMTerms
    docstring = ARMTerms.__doc__ or ""
    # Load-bearing citation token (see Wave 5 Plan 05-05 Task 2)
    assert "references/arm-mechanics.md" in docstring, (
        "ARMTerms.__doc__ must reference references/arm-mechanics.md per ROADMAP SC-5"
    )
    # Bonus: docstring should mention at least one regulatory citation
    assert "B2-1.4-02" in docstring or "Fannie" in docstring or "Selling Guide" in docstring
    ```

    **Flip 3: test_arm_mechanics_citations**

    Remove decorator. Body:

    ```
    """ARM-09 + D-08 [REVISED 2026-04-30]: references/arm-mechanics.md cites the verified-correct
    Selling Guide sections + CFPB + AmericU disclosure, AND does NOT carry forward the broken
    legacy citations B5-3.5-01 / §4404.
    """
    project_root = Path(__file__).resolve().parent.parent
    doc_path = project_root / "references" / "arm-mechanics.md"
    content = doc_path.read_text()
    # 4 required URL/section fragments:
    required_fragments = [
        "selling-guide.fanniemae.com/sel/b2-1.4-02",  # Fannie B2-1.4-02 verified
        "sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms",  # Freddie SOFR-Indexed
        "consumerfinance.gov/ask-cfpb/what-are-rate-caps",  # CFPB §1951
        "5_6-SOFR-ARM-Program-Disclosure",  # AmericU PDF
    ]
    for frag in required_fragments:
        assert frag in content, f"Required citation fragment '{frag}' missing from references/arm-mechanics.md"

    # 2 forbidden legacy fragments (must NOT appear — prevents D-08 regression):
    forbidden_fragments = [
        "B5-3.5-01",  # broken; returns 404 — RESEARCH §Q4 verified
        "§4404",      # stale Freddie section — RESEARCH §Q4 verified
    ]
    for frag in forbidden_fragments:
        assert frag not in content, (
            f"Forbidden legacy citation '{frag}' found in references/arm-mechanics.md "
            f"(D-08 [REVISED 2026-04-30] removed this; revert detected)"
        )

    # Section 6302.7(b) (Freddie modern equivalent of legacy §4404) must appear
    assert "6302.7(b)" in content, "Freddie 6302.7(b) section must be cited (D-08 [REVISED])"
    ```

    Notes:
    - Tests use `Path(__file__).resolve().parent.parent` to locate project root (consistent with SCRIPT_PATH pattern at module top).
    - The forbidden-fragment assertions are the load-bearing tests that prevent a future revert from accidentally restoring the broken citations.
  </action>
  <verify>
    <automated>pytest tests/test_arm.py -k "test_arm_mechanics_doc_sections_present or test_arm_terms_docstring_cites_arm_mechanics or test_arm_mechanics_citations" -xvs</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_arm.py::test_arm_mechanics_doc_sections_present -x` exits 0 with 1 passed
    - `pytest tests/test_arm.py::test_arm_terms_docstring_cites_arm_mechanics -x` exits 0 with 1 passed
    - `pytest tests/test_arm.py::test_arm_mechanics_citations -x` exits 0 with 1 passed
    - `grep -c '@pytest.mark.xfail' tests/test_arm.py` returns 11 (14 - 3 = 11)
    - `mypy --strict tests/test_arm.py` exits 0
    - `ruff check tests/test_arm.py` exits 0
    - `ruff format --check tests/test_arm.py` exits 0
  </acceptance_criteria>
  <done>
    All 3 ARM-09 stubs flipped to passing; xfail count drops from 14 to 11; mypy + ruff clean.
  </done>
</task>

<task type="auto">
  <name>Task 4: Verify zero regression to all prior baselines</name>
  <files>(verification only)</files>
  <read_first>
    - 05-VALIDATION.md "Phase gate" row
    - Plan 05-04b SUMMARY for prior baseline (418 passed + 4 skipped + 14 xfailed; downstream of 05-04a)
  </read_first>
  <action>
    Run the full pytest suite. Expected counts after this plan:
    - Plan 05-04b baseline (downstream of 05-04a): 418 passed + 4 skipped + 14 xfailed
    - Plan 05-05 delta: +3 ARM-09 stubs flipped (xfail → pass) → +3 passed, -3 xfailed
    - Final expected: 421 passed + 4 skipped + 11 xfailed + 0 failed + 0 errored

    Run: `pytest -q`

    Run mypy + ruff on every Phase 5 file Wave 0..5 has touched (no new files in this wave; lib/arm.py + tests/test_arm.py are the only CODE files modified):
    - `mypy --strict lib/arm.py lib/money.py lib/affordability.py scripts/arm_simulate.py scripts/_cli_helpers.py scripts/amortize.py scripts/affordability.py tests/test_arm.py tests/test_money.py tests/test_cli_helpers.py tests/conftest.py`
    - `ruff check ...` (same files)
    - `ruff format --check ...` (same files)

    All MUST be clean.

    Also verify the new doc file's URL hygiene by attempting a quick connectivity check (this is informational; don't fail the plan if a URL is temporarily unreachable):
    - The acceptance_criteria for Task 1 already grep-pinned the 4 verified URL fragments. Re-running that assertion is sufficient.
  </action>
  <verify>
    <automated>pytest -q &amp;&amp; mypy --strict lib/arm.py lib/money.py lib/affordability.py scripts/arm_simulate.py scripts/_cli_helpers.py scripts/amortize.py scripts/affordability.py tests/test_arm.py tests/test_money.py tests/test_cli_helpers.py tests/conftest.py &amp;&amp; ruff check lib/arm.py lib/money.py lib/affordability.py scripts/arm_simulate.py scripts/_cli_helpers.py scripts/amortize.py scripts/affordability.py tests/test_arm.py tests/test_money.py tests/test_cli_helpers.py tests/conftest.py</automated>
  </verify>
  <acceptance_criteria>
    - `pytest -q` final summary shows passed >= 421
    - `pytest -q` final summary shows xfailed = 11
    - `pytest -q` final summary shows skipped >= 4
    - `pytest -q` final summary shows failed = 0
    - `pytest -q` final summary shows errors = 0
    - `pytest tests/test_amortize.py -q` byte-equivalent to Phase 3 closure
    - `pytest tests/test_affordability.py -q` byte-equivalent to Phase 4 closure
    - `mypy --strict` across 11 files exits 0
    - `ruff check` across 11 files exits 0
    - `ruff format --check` across 11 files exits 0
  </acceptance_criteria>
  <done>
    Full suite green; ARM-09 closed; ROADMAP SC-5 verified; all baselines preserved.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Documentation → engine semantics | A doc-only change cannot regress engine math, but stale citations could mislead a user investigating regulatory compliance |
| ARMTerms.__doc__ → user inspection | Phase 11 amortization-agent + interactive Python users land on the docstring; the citation MUST point to a current, accessible reference doc |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-27 | Information Disclosure (broken citation) | references/arm-mechanics.md citation URLs | mitigate | RESEARCH §Q4 verified all 4 URLs on 2026-04-30; Task 1 acceptance_criteria pin the verified fragments AND assert the broken legacy fragments are absent |
| T-05-28 | Tampering (citation regression) | references/arm-mechanics.md vs locked D-08 [REVISED] | mitigate | test_arm_mechanics_citations greps for forbidden tokens (B5-3.5-01, §4404); a future commit that reintroduces the legacy citations fails this test |
| T-05-29 | Repudiation (docstring drift from doc file) | lib/arm.py ARMTerms.__doc__ | mitigate | test_arm_terms_docstring_cites_arm_mechanics asserts the verbatim "references/arm-mechanics.md" token; if the file is renamed or removed, this test catches it |
| T-05-30 | Information Disclosure (LM-3 teaser-ARM convention silent) | references/arm-mechanics.md Section 7 | mitigate | Section 7 explicitly documents the engine choice + CFPB alternative + the rationale; test_arm_mechanics_doc_sections_present greps for "teaser" token |
| T-05-31 | Tampering (AI attribution sneaks into docs) | references/arm-mechanics.md content | mitigate | Acceptance criteria assert zero matches for "co-authored", "claude", "anthropic" per CLAUDE.md global rule |
</threat_model>

<verification>
- references/arm-mechanics.md exists with 7 sections + verified citations
- ARMTerms.__doc__ contains the load-bearing "references/arm-mechanics.md" token
- 3 ARM-09 stubs flipped to passing
- Forbidden legacy citations (B5-3.5-01, §4404) are NOT present anywhere in references/arm-mechanics.md
- 4 verified-correct URL fragments ARE present
- 421 passed; 11 xfailed; 4 skipped; 0 failed; 0 errors
- mypy + ruff clean across 11 files
- No AI attribution anywhere in the new doc
</verification>

<success_criteria>
- ARM-09 closed (references/arm-mechanics.md ships with corrected D-08 [REVISED 2026-04-30] citations)
- ROADMAP SC-5 closed (ARMTerms docstring cites the doc)
- Forbidden legacy citations cannot regress (test asserts absence)
- LM-3 teaser-ARM convention disclosed as engine choice (Section 7)
- All baselines preserved
</success_criteria>

<output>
After completion, create `.planning/phases/05-arm-modeling/05-05-SUMMARY.md` documenting:
- references/arm-mechanics.md shipped (~120+ lines; 7 sections; appendix)
- lib/arm.py ARMTerms docstring extended (+1 citation)
- 3 ARM-09 stubs flipped
- xfail count: 14 → 11
- Pass count: 418 → 421
- ARM-09 + ROADMAP SC-5 closure status
- Citation-correction-history note (D-08 [REVISED] now reflected verbatim in repo)
</output>

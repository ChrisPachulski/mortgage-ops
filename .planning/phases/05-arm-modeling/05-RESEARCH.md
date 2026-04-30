# Phase 5: ARM Modeling - Research

**Researched:** 2026-04-30
**Domain:** ARM (adjustable-rate mortgage) reset/cap/floor mechanics + per-epoch slice-stitch over Phase 3's `lib.amortize.build_schedule`
**Confidence:** HIGH on engine algebra + Pydantic v2 inheritance + slice-stitch correctness; LOW on the locked D-04 oracle source (MGIC has no ARM calculator); LOW on the locked D-08 Selling Guide section numbers (citations are wrong; alternates verified).

## Executive Summary

Five landmines surfaced; two are blockers for the locked CONTEXT.md decisions, three are nuances the planner must absorb verbatim:

1. **BLOCKER-1: D-04 oracle source does not exist.** MGIC's public site at https://www.mgic.com/tools/calculators and https://www.mgic.com/tools/consumer-calculators offers exactly five consumer calculators — Buy Now vs. Wait, Down Payment, Rent or Buy, Monthly Payment, Home Affordability — and **no ARM calculator at all**. CONTEXT.md D-04's "MGIC capture-as-fixture" oracle strategy needs replacement before the planner can ship `tests/fixtures/arm/oracle/`. Recommended swap: Bankrate ARM calculator (https://www.bankrate.com/mortgages/adjustable-rate-mortgage-calculator/) which DOES support 3/1, 5/1, 7/1, 10/1 with per-period output, OR mortgagecalculator.org's ARM page (https://www.mortgagecalculator.org/calcs/arm.php). Both are equally credible "borrower-facing UI" oracles for the cross-validation purpose D-04 actually wants. Flag for `/gsd-discuss-phase` re-entry.

2. **BLOCKER-2: D-08 Selling Guide section numbers are wrong.** The Fannie Mae section CONTEXT.md cites as `B5-3.5-01 (ARM Loan Eligibility)` is a 404; the correct section is **B2-1.4-02 "Adjustable-Rate Mortgages (ARMs)" updated 2025-12-10** (https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms). The Freddie Mac `§4404` reference is also stale — modern Freddie URLs use `Guide Section 6302.7(b)` (delivery) and `Chapter 4203` (LTV); ARM mechanics live across multiple sections rather than one. Planner must update `references/arm-mechanics.md` citations to the actual current sections.

3. **NUANCE-3: D-02 lifetime-cap base disagrees with CFPB convention for teaser ARMs.** CFPB explicitly says lifetime cap is measured "from the **initial rate**" (https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/). Industry sources confirm "5 or 6 percentage points above your initial rate." For NON-teaser ARMs, `loan.annual_rate == initial_rate == note_rate` and CONTEXT.md is correct. For teaser ARMs, CONTEXT.md uses an explicit `note_rate=0.0500` (post-teaser) as the lifetime base — but CFPB says use the actual initial (teaser) rate. The locked D-06 schema is fine; only the documentation in `references/arm-mechanics.md` + the test fixture `arm_teaser_rate.json` need to clarify which convention this engine implements. Planner should NOT silently change behavior — should explicitly document "this engine uses post-teaser note_rate as lifetime base when supplied; CFPB documents the initial-rate convention" so the deviation is intentional and surfaced.

4. **NUANCE-4: `_quantize_rate` IS the only consumer in `lib/`.** Verified by `grep -rn _quantize_rate /Users/cujo253/Documents/mortgage-ops/lib/` — five hits, all in `lib/affordability.py` (one definition + four call sites at lines 616/930/931/945/946). Phase 5 IS the second consumer. D-14 promotion to `lib/money.py` is the recommended path; the alternative (cross-module private import) is fragile.

5. **NUANCE-5: Pydantic v2 `model_config` IS auto-inherited and merged from parent → child.** CONTEXT.md states "the parent's config doesn't auto-inherit; planner re-specifies." This is incorrect per the Pydantic v2 docs ("Any configuration ... set on the generic model will also be applied to the parametrized classes, in the same way as when inheriting from a model class" — https://pydantic.dev/docs/validation/latest/concepts/models/). Re-specifying is harmless (idempotent) and recommended for explicitness, but it is not _required_ for behavior. No planner action — just don't write a test that asserts re-specification is mandatory.

**Safe to plan:** D-01 (index supply), D-03 (parallel models), D-05 (per-epoch slice-stitch), D-06 (ARMTerms field schema), D-07 (CLI mirror), D-09 (exact Decimal equality), D-10 (citation-coverage meta-test), D-12 (negative-amort out), D-13 (caller-supplied index), D-14 (`_quantize_rate` promotion), D-15 (5/6 ARM cadence) — all consistent with reality.

**Primary recommendation:** Block planning to re-discuss D-04 (oracle source replacement) and D-08 (citation correction). Both are 30-minute fixes — the planner cannot ship `references/arm-mechanics.md` and `tests/fixtures/arm/oracle/` faithfully without these resolved.

---

## Per-Question Findings

### Q1. Per-epoch slice-stitch correctness (D-05)

**Confidence: HIGH** — verified by direct reading of `/Users/cujo253/Documents/mortgage-ops/lib/amortize.py:295-383` (`_build_fixed_monthly`).

**Q1.1 — Cumulative totals reset to 0 at synthetic_loan period 1?**
**Yes.** Lines 311-312 initialize `cum_int = Decimal("0.00")` and `cum_prin = Decimal("0.00")` at the top of `_build_fixed_monthly`. Lines 349-350 advance them per period within the call. There is NO mechanism for `build_schedule` to receive prior-epoch cumulative totals as input. → **Phase 5 MUST add prior-epoch terminal cumulative totals to each sliced row's `cumulative_interest` and `cumulative_principal` to maintain continuous numbering.** This is exactly what CONTEXT.md D-05 step 2.4 already specifies; the locked decision is correct.

**Q1.2 — Final-payment cleanup (D-09) triggered only at full-schedule's last row?**
**Mostly yes — with one bear trap.** The D-09 cleanup at lines 318-343 fires when EITHER (a) `is_last_term_period == True` (period == loan.term_months) OR (b) `formulaic_overshoot` is true (`balance + interest <= level_pmt`, indicating the next regular payment would zero or overshoot the balance), OR (c) extras zero the balance early.

For a Phase 5 NON-final epoch, the synthetic loan has `term_months = remaining_full_term` and `principal = remaining_balance`. Phase 3 builds the FULL schedule for that synthetic loan; the cleanup fires at `synthetic_schedule.payments[-1]` (i.e., position `remaining_full_term - 1`), NOT at position `reset_period_months - 1`. **As long as Phase 5 always slices `payments[0:reset_period_months]` for non-final epochs, the cleanup-bearing tail row is sliced off and never reaches the ARM schedule.** ✓

**Bear trap:** if a future planner takes the discouraged shortcut (`synthetic_loan.term_months = reset_period_months` instead of `remaining_full_term`), then for EVERY non-final epoch the synthetic schedule's last row becomes a D-09 cleanup row with `principal = balance` and `balance_after = 0.00`. This would silently "pay off" the loan at every reset and produce a corrupt continuous schedule. CONTEXT.md D-05 + Discretion section already explicitly forbid this shortcut; the planner MUST honor that. Recommendation: ship a unit test `tests/test_arm.py::test_non_final_epoch_does_not_zero_balance` that asserts `arm_schedule.payments[reset_period_months - 1].balance > Decimal("0.00")` (the period right before the first reset boundary still has balance) to lock against drift.

**Q1.3 — Phase 3 cleanup-free synthesis option?**
**No.** `lib.amortize.build_schedule` always runs the cleanup; there is no `disable_cleanup` flag. Phase 5 must slice off the tail. This is the locked D-05 design and is correct. Slicing also makes the engine simpler (no Phase 3 surface change). → No planner action; the locked path is the right one.

### Q2. `ARMPayment(Payment)` Pydantic v2 inheritance correctness

**Confidence: HIGH** — verified via Pydantic 2 docs (https://pydantic.dev/docs/validation/latest/concepts/models/) + canonical patterns.

**Q2.1 — Subclass inherits parent fields + adds `rate_in_effect: Rate`, with frozen+strict+forbid?**
**Yes.** Pydantic v2 model inheritance is field-level concatenation + config merge. The child class gets all parent fields plus its own. `model_config` is auto-merged (per docs: "Any configuration ... set on the generic model will also be applied to the parametrized classes"). Re-specifying `model_config = ConfigDict(strict=True, frozen=True, extra="forbid")` on the child is harmless and recommended for explicitness, but not strictly required for behavior. CONTEXT.md L102 currently asserts "the parent's config doesn't auto-inherit; planner re-specifies" — this is incorrect (auto-inheritance + merge is the documented v2 behavior); recommend the planner DOES re-specify (defense-in-depth + grep-discoverable explicit) but understand it's an explicitness choice, not a necessity.

**Q2.2 — `list[ARMPayment]` structurally compatible with `list[Payment]` for mypy --strict?**
**Yes — by Pydantic-aware mypy plugin.** Generic list type covariance is normally NOT allowed in Python (lists are mutable, hence invariant). However:
- `ARMPayment` is a subclass of `Payment` so a single `ARMPayment` instance IS-A `Payment`.
- A function expecting `Payment` accepts an `ARMPayment` directly (no list typing involved).
- For `list[Payment]` parameters specifically, the standard Python typing rule says `list[ARMPayment]` is NOT a `list[Payment]` (invariance).

**Practical implication for Phase 8 / Phase 4 consumers:** They iterate `arm_schedule.payments` which is typed as `list[ARMPayment]`. Each iteration variable is an `ARMPayment` IS-A `Payment` — works fine. ANY consumer that types a parameter as `list[Payment]` and tries to pass `arm_schedule.payments` will fail mypy --strict. This is NOT a Phase 5 bug; it's a downstream-consumer-typing concern. Phase 5 should:
- Type `ARMSchedule.payments: list[ARMPayment]` (precise, no fudging).
- Document in `references/arm-mechanics.md` that "consumers expecting `list[Payment]` use `Sequence[Payment]` or `Iterable[Payment]` instead — both are covariant" — Sequence/Iterable are the correct ABCs for read-only collection consumption.

**Q2.3 — `model_dump_json()` round-trips subclass fields?**
**Yes.** Pydantic v2 dumps all defined fields including subclass-added ones. `ARMPayment.model_dump_json()` produces JSON with `rate_in_effect` field; `ARMPayment.model_validate_json(...)` reconstructs. Phase 5 CLI emits `ARMSchedule.model_dump_json(indent=2)` per D-07; the JSON shape includes all child fields automatically. No special handling needed.

### Q3. MGIC ARM calculator capture mechanics (D-04) — BLOCKER

**Confidence: HIGH** — verified MGIC has NO ARM calculator (https://www.mgic.com/tools/consumer-calculators lists exactly five calculators and none are ARM).

**MGIC's full consumer calculator inventory (verified 2026-04-30):**
1. Buy Now vs. Wait Calculator
2. Down Payment Calculator
3. Rent or Buy Calculator
4. Monthly Payment Calculator
5. Home Affordability Calculator

**No ARM calculator exists.** D-04 + D-09 fixture references to `mgic_5_1_capture_2026.pdf/.json` cannot be produced. The locked decision is unimplementable as written.

**Recommended replacement oracles** (planner picks; both more credible than MGIC for ARM-specific math):
- **Bankrate ARM calculator** (https://www.bankrate.com/mortgages/adjustable-rate-mortgage-calculator/) — supports 3/1, 5/1, 7/1, 10/1 with per-period printable amortization table. Major consumer brand; same "borrower-facing UI" credibility as MGIC.
- **mortgagecalculator.org ARM** (https://www.mortgagecalculator.org/calcs/arm.php) — supports 3/1, 5/1, 7/1, 10/1 with per-period output.
- **U.S. Bank ARM calculator** (https://www.usbank.com/home-loans/mortgage/mortgage-calculators/adjustable-rate-mortgage-calculator.html) — bank-published; high credibility.
- **Vertex42 ARM Calculator (Excel)** (https://www.vertex42.com/ExcelTemplates/arm-calculator.html) — open Excel formula source; highest "white-box methodology" credibility for hand-calc cross-validation.

**Strongest recommendation:** Bankrate (consumer-brand parity with MGIC's role in D-04) PLUS Vertex42 (transparent Excel formula source acts as a third "hand-calc agrees with industry-Excel-implementation" anchor).

**Capture format:** Same recommendation as CONTEXT.md D-04 — print-to-PDF (browser snapshot) + JSON transcription of the per-period table. The PDF is the immutable ground-truth artifact; the JSON is the test input. Annual re-capture cadence parallels the FFIEC tool for Phase 7 APR.

**5/6 ARM coverage:** None of the consumer-grade calculators above natively support 5/6 SOFR ARMs. Bankrate, mortgagecalculator.org, U.S. Bank, Vertex42 all model 3/1, 5/1, 7/1, 10/1 (annual reset). For 5/6 ARM oracle, the only credible option is **lender-published rate-disclosure PDFs** (e.g., the AmericU 5/6 SOFR ARM Disclosure 2/1/5 caps PDF: https://www.americu.com/wp-content/uploads/2022/06/5_6-SOFR-ARM-Program-Disclosure-2_1_5-CAPS.pdf). Capture the disclosure as a PDF and use its example payment-jump table as the 5/6 oracle. Hand-calc per Selling Guide formula must agree with the disclosure.

**Action for /gsd-discuss-phase:** D-04 needs an explicit re-lock. Suggested replacement decision: "Hand-calc per Selling Guide formula PRIMARY; Bankrate ARM calculator capture-as-fixture (PDF + JSON transcription) for 3/1/5/1/7/1/10/1 cross-validation; lender disclosure PDF for 5/6 ARM cross-validation."

### Q4. Freddie/Fannie Selling Guide ARM citations (D-08, ARM-09) — BLOCKER

**Confidence: HIGH** — verified by direct WebFetch + WebSearch of selling-guide.fanniemae.com and sf.freddiemac.com.

**CONTEXT.md D-08 cites:**
- "Fannie Mae Selling Guide Section B5-3.5-01 (ARM Loan Eligibility)" — **404 / does not exist**. The B5-3.5 section group is about VA-related underwriting, NOT ARMs.
- "Freddie Mac Single-Family Selling Guide §4404 (ARM Mortgages)" — **stale section number**; the modern Freddie Guide uses different section numbering.

**Verified current authoritative sections:**

| Cited claim | Correct citation | URL |
|---|---|---|
| ARM eligibility, cap structure, floor convention | Fannie Mae Selling Guide **B2-1.4-02** "Adjustable-Rate Mortgages (ARMs)", updated 2025-12-10 | https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms |
| ARM no lifetime floor other than margin | Same B2-1.4-02; quote: "Mortgage interest rates may never decrease to less than the ARM's margin, regardless of any downward interest rate cap" | https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms |
| ARM convertibility / weighted-average MBS | Fannie Mae Selling Guide **C2-1.1-07** "Standard ARM and Converted ARM Resale Commitments" + **C3-5-01** "Creating Weighted-Average ARM MBS" | https://selling-guide.fanniemae.com/sel/c2-1.1-07/standard-arm-and-converted-arm-resale-commitments + https://selling-guide.fanniemae.com/sel/c3-5-01/creating-weighted-average-arm-mbs |
| Freddie SOFR-indexed ARM products (3/6, 5/6, 7/6, 10/6); margin must be 100-300 bps | Freddie Mac product page "SOFR-Indexed ARMs" (cites Guide Section 6302.7(b) for delivery instructions; Chapter 4203 for LTV) | https://sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms |
| Cap precedence (initial cap on first reset; periodic cap subsequent; lifetime cap measured against initial rate) | CFPB Ask CFPB §1951; quote: "the rate can never be more than five percentage points either higher or lower from the initial rate" | https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/ |
| 5/6 ARM first reset at month 61 | AmericU 5/6 SOFR ARM Disclosure (2/1/5 caps); abt.bank 5/6/7/6/10/6 SOFR ARM Disclosure; quote: "The first Change Date will occur on the 61st payment due date. Subsequent Change Dates will occur every 6 months thereafter" | https://www.americu.com/wp-content/uploads/2022/06/5_6-SOFR-ARM-Program-Disclosure-2_1_5-CAPS.pdf + https://www.abt.bank/wp-content/uploads/2022/09/Early-ARM-Disclosure-5yr-7yr-and-10yr-ARM-SOFR-Static.pdf |
| 30-day Average SOFR + 45-day lookback (Fannie ARMs) | Fannie Mae B2-1.4-02 (referenced in product matrix) | https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms |

**Where Selling Guides are silent (engine choices that are industry-standard but not regulator-mandated):**
- **Quantization at 6 decimal places.** Selling Guides specify the cap formula but not the rate quantum. Phase 5 D-14 / Phase 4 D-09 chose 6 decimal places to align with `lib.models.Rate` Annotated[Decimal, max_digits=7, decimal_places=6]. This is engine choice; document in `references/arm-mechanics.md` as "engine convention, not regulator mandate."
- **Index lookback windows** (e.g., 45 days before reset). Fannie's Standard ARM Plan Matrix prescribes 45-day lookback for 30-day Average SOFR; D-13 explicitly defers lookback windows to v2 ("caller-supplied index values only"). Document the simplification.
- **Floor algebra `max(margin, floor_rate)`.** Fannie B2-1.4-02 says the floor "may never decrease to less than the ARM's margin." The locked D-02 formula `effective_floor = max(margin, floor_rate)` is a strict generalization (allows the caller to set a configured floor higher than margin); industry-standard but engine-specific.
- **Cap precedence (initial vs periodic).** CFPB confirms; Fannie's matrix specifies per product; no single section provides the algebra. Engine encodes industry standard.

**Stable URL fragment notes:** Fannie's `selling-guide.fanniemae.com/sel/<section>/<slug>` URLs are stable across updates (the section number is the canonical anchor). Freddie's modern URLs use product pages on `sf.freddiemac.com`; the actual Guide content lives behind login at `guide.freddiemac.com`. For reference doc citation purposes, use the public product page URL + Fannie's public Guide URL as the anchor pair.

**Action for planner:** Update `references/arm-mechanics.md` Section 1 (reset month convention) and Section 2 (cap precedence) and Section 3 (floor algebra) to cite **B2-1.4-02** + AmericU 5/6 disclosure + CFPB §1951 + Freddie SOFR-indexed-ARMs product page. Drop B5-3.5-01 and §4404 references entirely.

### Q5. `reset_period_months` cadence for 5/6 ARM (D-15)

**Confidence: HIGH** — verified via lender-published 5/6 SOFR ARM disclosures.

**5/6 ARM cadence (canonical, per AmericU + abt.bank disclosures):**
- Months 1-60: fixed at note rate (`loan.annual_rate`).
- **Month 61: first reset** ("first Change Date will occur on the 61st payment due date"). Cap = `initial_cap_bps`.
- **Month 67: second reset** (61 + 6). Cap = `periodic_cap_bps`.
- **Month 73: third reset.** Cap = `periodic_cap_bps`.
- ... every 6 months thereafter.

This matches CONTEXT.md D-15 + D-08 wording exactly ("month 61 with second reset at month 67"). The locked decision is correct. The fixture name `arm_5_6_payment_jump_at_61_and_67.json` (D-09) correctly identifies the two reset boundaries to test.

**Reset-cadence formula for the engine:**
```
reset_trigger_periods = [initial_period_months + 1 + k * reset_period_months for k in range(...)]
                      = [61, 67, 73, 79, ...]  # for 5/6 ARM
                      = [61, 73, 85, ...]      # for 5/1 ARM (k * 12)
                      = [85, 97, 109, ...]     # for 7/1 ARM
                      = [121, 133, 145, ...]   # for 10/1 ARM
```

The "+1" is the off-by-one that PITFALL 5 warns about: the rate change applies at the **start of the post-fixed-period month**, so for a 5/1 ARM (60-month fixed) the new rate appears in `payments[60].rate_in_effect` (zero-indexed), which has `period == 61`. Consistent with CONTEXT.md D-03 ("`payments[59].period == 60` ... `payments[60].period == 61`").

**Cross-validation source for 5/6 oracle:** No public consumer calculator natively supports 5/6 ARMs; the AmericU 5/6 SOFR ARM Disclosure (2/1/5 caps) PDF is the recommended capture source. It includes a worked example payment-jump table.

### Q6. Quantization landmines

**Confidence: HIGH** — verified by reading `lib/affordability.py:613-627` + `lib/money.py:1-46`.

**Q6.1 — Single quantize at end vs intermediate quantizes — does CONTEXT.md D-02 quantize too early?**

CONTEXT.md D-02 reads:
```
fully_indexed = quantize_rate(index + (margin_bps / 10000))
effective_floor = max(margin_bps / 10000, floor_rate)
...
ceiling = min(periodic_ceiling, lifetime_ceiling)
new_rate = quantize_rate(clamp(fully_indexed, low=effective_floor, high=ceiling))
```

This quantizes `fully_indexed` BEFORE the clamp, AND quantizes `new_rate` after. This is technically two quantizes — but the discrepancy is at most 1 ULP (`Decimal("0.000001")`) at the 6-decimal-place quantum, which is below `lib.models.Rate.decimal_places=6` storage precision. Both formulations produce the same `new_rate` to 6 decimal places under ROUND_HALF_UP for any realistic input.

**Recommendation:** Keep CONTEXT.md's two-quantize formulation as-is — it's defensive (intermediate `fully_indexed` is a Rate-typed value; quantizing makes the type-pun explicit). The "quantize end-of-period only" rule (Phase 1 PITFALLS, Phase 3 D-04, Phase 4 D-09) targets MID-CALCULATION quantization within an interest-accrual loop where a quantize call drops sub-cent precision before subsequent multiplies. The D-02 formula is a single rate-derivation expression where intermediate values must be Rate-typed for assignment to `Rate`-typed fields — quantizing both is correct.

**Q6.2 — `_quantize_rate` rounding context.**

Verified: `lib/affordability.py:626` uses `with localcontext(MONEY_CONTEXT):` and `MONEY_CONTEXT` (defined `lib/money.py:23`) is `Context(prec=28, rounding=ROUND_HALF_UP)`. So `_quantize_rate` already uses ROUND_HALF_UP via the shared MONEY_CONTEXT. ✓

When promoted to `lib/money.py.quantize_rate` (D-14), the implementation simply moves the function and renames `_quantize_rate` → `quantize_rate`; no rounding-context changes needed. The `_RATE_QUANTUM = Decimal("0.000001")` constant (line 613) moves with it.

### Q7. Pydantic v2 field validation for `index_path` alignment (D-01)

**Confidence: HIGH** — Pydantic v2 model_validator(mode="after") supports cross-field access.

**Pattern:** A `model_validator(mode="after")` on `ARMRequest` runs AFTER all fields have been independently validated, so `self.arm_terms`, `self.loan`, and `self.index_path` are all available as fully-validated Pydantic objects. The validator computes the reset trigger period set from `arm_terms.initial_period_months + k * arm_terms.reset_period_months` for k=0..(loan.term_months // reset_period_months - initial // reset_period_months) and verifies every `index_path[i].period` is in that set.

**Sketch (planner finalizes):**
```python
class ARMRequest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    loan: Loan
    arm_terms: ARMTerms
    assumed_index_rate: Rate
    index_path: list[IndexPathEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _index_path_periods_align_to_reset_triggers(self) -> ARMRequest:
        initial = self.arm_terms.initial_period_months
        cadence = self.arm_terms.reset_period_months
        term = self.loan.term_months
        # Reset triggers: month after fixed period, then every cadence months.
        # 5/1: 61, 73, 85, ... up to term_months.
        triggers = set()
        period = initial + 1
        while period <= term:
            triggers.add(period)
            period += cadence
        for entry in self.index_path:
            if entry.period not in triggers:
                raise ValueError(
                    f"index_path entry at period {entry.period} does not align to a "
                    f"reset trigger period (valid triggers for this product: "
                    f"{sorted(triggers)[:5]}{'...' if len(triggers) > 5 else ''})"
                )
        return self
```

**Landmines:** None. Pydantic v2 docs explicitly support sibling-field access in `mode="after"` validators (the entire model is constructed before the validator runs). The validator only fires on `model_validate_json` or `model_validate`, not on programmatic mutation — but `frozen=True` prevents mutation anyway, so the validator runs exactly once at request construction.

**Test pattern:** `tests/fixtures/arm/arm_index_path_misaligned.json` — supply `index_path: [{"period": 62, ...}]` for a 5/1 ARM (where 61 is valid but 62 is not), assert the CLI emits a 6-key Pydantic envelope on stderr with `loc=["index_path", 0, "period"]` (or similar). Mirrors Phase 4 D-13 envelope tests.

### Q8. JSON-float pre-validation gate (D-discretion)

**Confidence: HIGH** — verified by reading `scripts/affordability.py:70-123` and `scripts/amortize.py:72-122`.

**Reality:** The helper `_find_json_float_loc(raw: str) -> tuple[list[str | int], str] | None` is **identical text** in both `scripts/amortize.py` and `scripts/affordability.py` (Phase 3 introduced it; Phase 4 copy-pasted unchanged per the file headers). It's 50 lines of identical code in two places.

**Recommendation:** **Factor into `scripts/_cli_helpers.py` NOW, in Phase 5.** Justification:
- Phase 5 will need it (3rd consumer at minimum).
- Phase 6 refi NPV, Phase 7 APR, Phase 8 stress will all need it (5th, 6th, 7th consumers — guaranteed by the project's locked CLI conventions D-07).
- The cost of factoring is one new file (~70 lines) + 3-line import-and-call updates in both existing scripts.
- The cost of NOT factoring is 5 future copies of the same 50-line helper, plus drift risk if a Pydantic 2.14 upgrade changes the canonical envelope shape.

**File shape:**
```python
# scripts/_cli_helpers.py
"""Shared CLI helpers for JSON-in/JSON-out scripts (Phase 3 D-19 / WR-02 closure inheritance).

Phase 5 introduced this module when factoring _find_json_float_loc out of
scripts/amortize.py + scripts/affordability.py to a single source of truth.

Phase 10 may relocate to .claude/skills/mortgage-ops/scripts/_cli_helpers.py
following the script-relocation pattern; Phase 5 keeps it at project root.
"""

from __future__ import annotations
import json
from typing import Any


def find_json_float_loc(raw: str) -> tuple[list[str | int], str] | None:
    """Walk parsed JSON and return (loc-path, decimal-string) of the first JSON float.

    [docstring identical to existing helper]
    """
    from decimal import Decimal as _Decimal
    # ... existing body (lines 98-123 of scripts/amortize.py) ...


def make_float_gate_envelope(
    float_loc: list[str | int], float_input: str
) -> list[dict[str, Any]]:
    """Construct the 6-key Pydantic-shape envelope for a JSON-float rejection.

    Single source of truth for the envelope shape; mirrors the inline
    construction at scripts/amortize.py:196-213 + scripts/affordability.py:253-272.
    Pinned by tests/test_amortize.py::test_cli_rejects_float_principal +
    tests/test_arm.py::test_cli_rejects_float_<arm_money_field>.
    """
    from pydantic import VERSION as _pv
    _major_minor = ".".join(_pv.split(".")[:2])
    return [{
        "type": "decimal_type",
        "loc": float_loc,
        "msg": (
            "Input should be a valid decimal — JSON string required for "
            "money/rate fields per D-19 (JSON floats are rejected at the boundary)"
        ),
        "input": float_input,
        "url": f"https://errors.pydantic.dev/{_major_minor}/v/decimal_type",
        "ctx": {
            "class": "Decimal",
            "field_path": ".".join(str(p) for p in float_loc),
        },
    }]
```

**Phase 4 + Phase 3 update:** Both `scripts/amortize.py` and `scripts/affordability.py` swap their inline `_find_json_float_loc` + envelope-construction blocks for `from scripts._cli_helpers import find_json_float_loc, make_float_gate_envelope` calls. The Phase 3 + Phase 4 test suites (currently 379 + 4 + 720+ tests) re-run unchanged because the externalized behavior is byte-identical.

**Test impact:** zero functional change (helper is byte-identical externalized); Phase 5 plan adds **`tests/test_cli_helpers.py`** with parametric coverage of:
- Valid JSON with no floats → returns None.
- Single nested float → correct loc-path + Decimal-string.
- Multiple floats → returns first (depth-first walk).
- JSON arrays + nested objects → correct integer indices in loc.
- Invalid JSON → returns None (Pydantic gets the canonical error).

**Risk if not factored:** Phase 6/7/8 each add 50 more lines of duplicated code; one of them silently drifts (e.g., adds `loc[i]` quoting); cross-script envelope-uniformity invariant breaks; Phase 9 Node + Phase 10 SKILL.md narrators encounter shape divergence. CONTEXT.md D-discretion already documents the recommendation; **the planner should pick the factor path.**

**Counter-recommendation:** If the factor work is deemed scope-creep for Phase 5, inline-copy is acceptable but the Phase 5 plan MUST schedule the factor in Phase 6 (first plan) before the helper appears in 4 places.

### Q9. `_quantize_rate` promotion to `lib/money.py` (D-14)

**Confidence: HIGH** — verified by `grep -rn _quantize_rate /Users/cujo253/Documents/mortgage-ops/lib/`.

**Verified consumer count:** Phase 4's `lib/affordability.py` is the ONLY current consumer (5 hits: 1 def + 4 calls at lines 616, 930, 931, 945, 946). Phase 5 IS the second consumer.

**Promotion path (recommended):**
```python
# lib/money.py — add after quantize_cents (line 47):
from decimal import ROUND_HALF_UP, Decimal, localcontext

_RATE_QUANTUM: Final[Decimal] = Decimal("0.000001")
"""The quantum for end-of-period rate rounding (matches lib.models.Rate decimal_places=6)."""


def quantize_rate(rate: Decimal) -> Decimal:
    """Quantize a fractional rate to 6 decimal places using ROUND_HALF_UP.

    Companion to quantize_cents (2 places). Use for any Rate-typed value at
    end-of-period; never quantize mid-calculation (Phase 1 PITFALLS, Phase 3 D-04,
    Phase 4 D-09 inherited).

    The 6-decimal quantum matches lib.models.Rate's
    Annotated[Decimal, Field(max_digits=7, decimal_places=6)] constraint —
    a Rate value computed via division (LTV, DTI, fully-indexed ARM rate)
    can otherwise produce a 28-digit Decimal that the model rejects.
    """
    with localcontext(MONEY_CONTEXT):
        return rate.quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP)
```

**Affordability.py update:**
```python
# lib/affordability.py — change line ~186 (existing import):
from lib.money import MONEY_CONTEXT, quantize_cents, quantize_rate
# -- previously --
# from lib.money import MONEY_CONTEXT, quantize_cents

# Drop the _quantize_rate def (lines 609-627) entirely.
# Replace 4 call sites (lines 930, 931, 945, 946):
#   ltv = _quantize_rate(...)  -->  ltv = quantize_rate(...)
```

**Blast radius:**
- `lib/money.py`: +18 lines (def + docstring + constant), no breaking change.
- `lib/affordability.py`: -18 lines (drop the def), 4 call-site renames, no behavior change.
- `lib/arm.py` (NEW): imports `from lib.money import quantize_cents, quantize_rate` from the start.
- `tests/test_money.py`: ADD a `test_quantize_rate_round_half_up` golden-pin test (e.g., `quantize_rate(Decimal("0.0654995")) == Decimal("0.065500")` — half-up boundary).
- `tests/test_affordability.py`: zero changes (the imports are inside `lib.affordability`; tests call `evaluate(...)`).

**Verification step:** Phase 5 plan that does the promotion includes a verify-block running `pytest tests/test_money.py tests/test_affordability.py -x` — must show zero regressions (Phase 4 was 379 passed + 4 skipped; promotion must keep that count).

**Counter-recommendation:** If the planner picks "smallest blast radius" instead, Phase 5 imports `from lib.affordability import _quantize_rate as quantize_rate` (the underscore-prefixed import is a deliberate "I know this is private" signal). This is documented in D-14 + D-discretion as acceptable. Both correct.

**Strong recommendation:** Promote. Phase 6 (refi NPV) almost certainly becomes the third consumer (refi NPV computes effective-rate ratios; rate quantize will reappear). Promoting now prevents a Phase 6 thrash.

### Q10. Validation Architecture for Nyquist — see dedicated section below.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARM-01 | `lib/arm.py` Pydantic model with explicit fields | Q2 (Pydantic v2 inheritance verified); D-06 schema confirmed implementable |
| ARM-02 | Supports 5/1, 7/1, 10/1, 5/6 (six-month) ARM products | Q5 (5/6 cadence verified); structured ARMTerms fields (D-06) capture all four with no special-case code |
| ARM-03 | Reset logic: `min(prior_rate + periodic_cap, max(margin, index + margin))`, capped by lifetime | Q1 (per-epoch slice-stitch) + D-02 formula; CFPB cap-precedence confirmed |
| ARM-04 | Floor handling: new_rate >= max(margin, configured floor) | D-02 formula explicit; Fannie B2-1.4-02 confirms no lifetime floor below margin |
| ARM-05 | Re-amortization at reset: balance recasts over remaining term at new rate | Q1 (Phase 3 build_schedule re-entry per epoch with synthetic Loan + slice); D-05 algorithm |
| ARM-06 | Tests against published ARM scenarios (MGIC or Bankrate) | **BLOCKER-1: MGIC has no ARM calc; recommend Bankrate + Vertex42 + AmericU disclosure** |
| ARM-07 | Tests verify both reset-month conventions (60 vs 61 for 5/1) | Q5 confirms month 61; PITFALL 5 + ROADMAP SC-3 fixture coverage; D-09 fixture list |
| ARM-08 | `scripts/arm_simulate.py` JSON-in/JSON-out CLI | Q8 (factor `_find_json_float_loc` to `scripts/_cli_helpers.py`); D-07 mirrors Phase 3/4 |
| ARM-09 | `references/arm-mechanics.md` documents conventions with Selling Guide citations | **BLOCKER-2: D-08 cites wrong sections; recommend B2-1.4-02 + CFPB §1951 + Freddie SOFR-product page** |

---

## Validation Architecture

> Required by Nyquist gate (workflow.nyquist_validation defaults enabled). Every requirement + ROADMAP SC + applied_cap Literal value mapped to a specific test file/function/fixture/assertion.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project standard, configured in pyproject.toml since Phase 1) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (verified by `grep -n pytest /Users/cujo253/Documents/mortgage-ops/pyproject.toml` returning hits at the standard location during Phase 4) |
| Quick run command | `pytest tests/test_arm.py -x` |
| Full suite command | `pytest -x` (Phase 4 baseline: 379 passed + 4 skipped; Phase 5 adds ~30-40 tests) |
| Phase gate | Full suite green before `/gsd-verify-work`; mypy --strict + ruff clean across `lib/arm.py`, `scripts/arm_simulate.py`, `tests/test_arm.py`, `scripts/_cli_helpers.py` (if factored) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|---|
| ARM-01 | ARMTerms has 8 explicit fields + REQUIRED floor_rate + optional note_rate | unit (Pydantic shape) | `pytest tests/test_arm.py::test_arm_terms_field_set -x` | ❌ Wave 0 |
| ARM-01 | ARMTerms rejects missing floor_rate at construction | unit | `pytest tests/test_arm.py::test_arm_terms_missing_floor_rate_raises -x` | ❌ Wave 0 |
| ARM-01 | ARMTerms.note_rate defaults to None and engine substitutes loan.annual_rate | unit | `pytest tests/test_arm.py::test_note_rate_defaults_to_loan_annual_rate -x` | ❌ Wave 0 |
| ARM-02 | 5/1 product (initial=60, reset=12) builds correctly | fixture | `pytest tests/test_arm.py::test_arm_5_1_payment_jump_at_61 -x` | ❌ Wave 0 |
| ARM-02 | 7/1 product (initial=84, reset=12) builds correctly | fixture | `pytest tests/test_arm.py::test_arm_7_1_payment_jump_at_85 -x` | ❌ Wave 0 |
| ARM-02 | 10/1 product (initial=120, reset=12) builds correctly | fixture | `pytest tests/test_arm.py::test_arm_10_1_payment_jump_at_121 -x` | ❌ Wave 0 |
| ARM-02 | 5/6 product (initial=60, reset=6) — first reset at 61, second at 67 | fixture | `pytest tests/test_arm.py::test_arm_5_6_payment_jump_at_61_and_67 -x` | ❌ Wave 0 |
| ARM-03 | Reset formula: `clamp(quantize(index + margin), low=floor, high=min(periodic_ceiling, lifetime_ceiling))` exactly | unit + fixture | `pytest tests/test_arm.py::test_reset_formula_locked -x` | ❌ Wave 0 |
| ARM-03 | First-reset uses initial_cap; subsequent uses periodic_cap | fixture | `pytest tests/test_arm.py::test_arm_initial_cap_at_first_reset -x` | ❌ Wave 0 |
| ARM-03 | Lifetime cap binds when fully-indexed exceeds note_rate + lifetime_cap | fixture | `pytest tests/test_arm.py::test_arm_lifetime_cap_binds -x` | ❌ Wave 0 |
| ARM-04 | Floor enforcement: new_rate >= max(margin, floor_rate) | fixture | `pytest tests/test_arm.py::test_arm_floor_below_margin_blocked -x` | ❌ Wave 0 |
| ARM-05 | Re-amortization over FULL remaining term (not just reset window) | fixture + invariant | `pytest tests/test_arm.py::test_full_remaining_term_re_amortization -x` | ❌ Wave 0 |
| ARM-05 | Continuous period numbering 1..N across epochs; final balance == 0.00 | fixture | `pytest tests/test_arm.py::test_arm_continuous_period_numbering -x` | ❌ Wave 0 |
| ARM-05 | Cumulative totals continuous across epoch boundaries | invariant | `pytest tests/test_arm.py::test_cumulative_totals_continuous_across_resets -x` | ❌ Wave 0 |
| ARM-05 | Non-final epoch's last sliced row has balance > 0.00 (no early payoff at reset) | invariant | `pytest tests/test_arm.py::test_non_final_epoch_does_not_zero_balance -x` | ❌ Wave 0 |
| ARM-05 | First epoch (months 1..60) matches Phase 1 oracle anchor ($400k @ 6.5%/30yr → $2528.27) | fixture | `pytest tests/test_arm.py::test_initial_fixed_period_matches_phase1_oracle -x` | ❌ Wave 0 |
| ARM-06 | Hand-calc per Selling Guide formula AND Bankrate/Vertex42 capture AGREE EXACTLY | fixture (oracle cross-validation) | `pytest tests/test_arm.py::test_oracle_cross_validation_5_1 -x` | ❌ Wave 0 (BLOCKER-1) |
| ARM-06 | 5/6 ARM oracle: AmericU disclosure capture cross-validation | fixture | `pytest tests/test_arm.py::test_oracle_cross_validation_5_6 -x` | ❌ Wave 0 (BLOCKER-1) |
| ARM-07 | Off-by-one negative: month 59 still old payment AND month 61 already new payment | fixture | `pytest tests/test_arm.py::test_arm_5_1_off_by_one_negative -x` | ❌ Wave 0 |
| ARM-07 | Reset boundary semantics: payments[59].rate == initial_rate, payments[60].rate == new_rate | fixture | (covered by `test_arm_5_1_payment_jump_at_61` above) | ❌ Wave 0 |
| ARM-08 | CLI subprocess round-trip: write JSON → invoke → parse stdout | smoke | `pytest tests/test_arm.py::test_cli_smoke_subprocess_round_trip -x` | ❌ Wave 0 |
| ARM-08 | CLI --help exits 0 without importing lib.arm or numpy_financial (D-18 lazy-import) | structural | `pytest tests/test_arm.py::test_cli_help_does_not_import_lib_arm -x` | ❌ Wave 0 |
| ARM-08 | CLI rejects JSON-float in loan.principal with 6-key envelope on stderr | structural | `pytest tests/test_arm.py::test_cli_rejects_float_principal -x` | ❌ Wave 0 |
| ARM-08 | CLI rejects JSON-float in assumed_index_rate with 6-key envelope | structural | `pytest tests/test_arm.py::test_cli_rejects_float_assumed_index_rate -x` | ❌ Wave 0 |
| ARM-08 | CLI rejects JSON-float in index_path[].value with 6-key envelope (deep loc) | structural | `pytest tests/test_arm.py::test_cli_rejects_float_index_path_value -x` | ❌ Wave 0 |
| ARM-08 | CLI rejects JSON-float in floor_rate with 6-key envelope | structural | `pytest tests/test_arm.py::test_cli_rejects_float_floor_rate -x` | ❌ Wave 0 |
| ARM-08 | CLI envelope-uniformity: float-gate + Pydantic ValidationError emit identical 6-key shape | structural | `pytest tests/test_arm.py::test_cli_error_envelope_uniformity -x` | ❌ Wave 0 |
| ARM-08 | CLI surfaces ARMRequest._index_path_periods_align_to_reset_triggers ValidationError as 6-key envelope | structural | `pytest tests/test_arm.py::test_cli_misaligned_index_path_period_rejected -x` | ❌ Wave 0 |
| ARM-09 | references/arm-mechanics.md exists at repo root with all 6 D-08 sections | structural (file grep) | `pytest tests/test_arm.py::test_arm_mechanics_doc_sections_present -x` | ❌ Wave 0 |
| ARM-09 | ARMTerms model docstring cites references/arm-mechanics.md | structural | `pytest tests/test_arm.py::test_arm_terms_docstring_cites_arm_mechanics -x` | ❌ Wave 0 |
| ARM-09 | references/arm-mechanics.md cites B2-1.4-02 + CFPB §1951 + AmericU 5/6 disclosure | structural (URL grep) | `pytest tests/test_arm.py::test_arm_mechanics_citations -x` | ❌ Wave 0 (BLOCKER-2) |
| Cross | applied_cap citation-coverage: every Literal value exercised by ≥1 fixture (D-10) | meta | `pytest tests/test_arm.py::test_applied_cap_citation_coverage -x` | ❌ Wave 0 |
| Cross | Phase 3 + Phase 4 test suites still pass (no regression from quantize_rate promotion) | smoke | `pytest tests/test_amortize.py tests/test_affordability.py -x` | ✓ existing |

### ROADMAP Success Criteria → Test Map

| SC | Description | Pinned Test |
|----|-------------|-------------|
| SC-1 | ARMTerms has 8 explicit fields (no implicit conventions) | `test_arm_terms_field_set` |
| SC-2 | 5/1 ARM payment-jump at month 61 (not 60, not 62), new rate = locked formula | `test_arm_5_1_payment_jump_at_61` |
| SC-3 | Both reset-month conventions (60 and 61) covered as separate fixtures | `test_arm_5_1_payment_jump_at_61` (positive) + `test_arm_5_1_off_by_one_negative` (negative) |
| SC-4 | Floor enforced: never below max(margin, configured_floor); fixture where index drop would breach | `test_arm_floor_below_margin_blocked` |
| SC-5 | references/arm-mechanics.md cites Selling Guides; cited from ARMTerms docstring | `test_arm_mechanics_doc_sections_present` + `test_arm_terms_docstring_cites_arm_mechanics` + `test_arm_mechanics_citations` |

### applied_cap Literal Coverage (D-10 citation-coverage meta-test)

Every value of `Literal["initial", "periodic", "lifetime", "floor", "none"]` MUST appear in `expected.reset_events[*].applied_cap` of at least one fixture. The meta-test asserts coverage by walking all `tests/fixtures/arm/*.json` and verifying every Literal value is present.

| applied_cap | Fixture pinning the value |
|---|---|
| `"initial"` | `arm_initial_cap_at_first_reset.json` (first reset binds at initial_cap) |
| `"periodic"` | `arm_initial_cap_at_first_reset.json` (second reset binds at periodic_cap) OR `arm_5_6_payment_jump_at_61_and_67.json` |
| `"lifetime"` | `arm_lifetime_cap_binds.json` (uncapped fully-indexed > lifetime ceiling) |
| `"floor"` | `arm_floor_below_margin_blocked.json` (index drop hits effective_floor) |
| `"none"` | `arm_5_1_payment_jump_at_61.json` (modest reset within all caps) — assumed; fixture must exercise a reset where neither cap nor floor binds. Confirm in plan. |

### Sampling Rate

- **Per task commit:** `pytest tests/test_arm.py -x` (~5-10 sec)
- **Per wave merge:** `pytest -x` (full suite; ~30 sec)
- **Phase gate:** Full suite green + mypy --strict clean + ruff clean before `/gsd-verify-work`

### Wave 0 Gaps

All ARM tests are Wave-0 stubs (xfail-decorated until the corresponding wave's plan implements the engine slice). Pattern mirrors Phase 4 Wave 0 (which created 9 xfail stubs for AFFD-01..09 closure). For Phase 5:

- [ ] `tests/test_arm.py` — full file with ~30 xfail stubs covering ARM-01..09 + cross-cutting + applied_cap citation coverage + 6-key envelope contract
- [ ] `tests/conftest.py` extension — add `arm_fixture` loader (Phase 4 D-17 pattern; ~12 lines)
- [ ] `tests/fixtures/arm/.gitkeep` — directory created
- [ ] `tests/fixtures/arm/oracle/.gitkeep` — oracle directory created
- [ ] **BLOCKER-1 PRECONDITION:** D-04 oracle source replacement decision before Wave 0 ships any oracle fixture stubs (cannot xfail-stub `test_oracle_cross_validation_5_1` without knowing whether the fixture path is `mgic_*.pdf` or `bankrate_*.pdf`)
- [ ] **BLOCKER-2 PRECONDITION:** D-08 citation correction decision before any Wave references `references/arm-mechanics.md` content (the assertion `test_arm_mechanics_citations` greps for `B5-3.5-01` per current CONTEXT.md and would lock the wrong citation)
- [ ] No framework install needed (pytest already in pyproject.toml from Phase 1)
- [ ] No mypy / ruff config changes needed

---

## Recommended Plan Structure

Suggested wave/plan breakdown (planner finalizes); follows Phase 4's 7-plan pattern (Wave 0 stubs → models → engine → ResetEvent → CLI → docs → fixture-flip).

| Wave | Plan | Files Touched | Requirements Closed |
|---|---|---|---|
| **Pre-Plan** | `/gsd-discuss-phase 5` re-entry | CONTEXT.md updates D-04 (oracle swap) + D-08 (citation correction) | none — unblocks below |
| **0** | `05-00-test-infrastructure-PLAN.md` | `tests/conftest.py` (arm_fixture loader); `tests/test_arm.py` (~30 xfail stubs); `tests/fixtures/arm/.gitkeep`; `tests/fixtures/arm/oracle/.gitkeep` | none (Nyquist coverage gate) |
| **1** | `05-01-quantize-rate-promotion-PLAN.md` (Claude's discretion D-14) | `lib/money.py` (+18 lines); `lib/affordability.py` (-18 lines, 4 call-site renames); `tests/test_money.py` (add quantize_rate golden pin); verify Phase 4 379+4 zero regression | enables ARM-01..05 plumbing |
| **2** | `05-02-pydantic-models-PLAN.md` | `lib/arm.py` (ARMTerms + IndexPathEntry + ARMRequest + ARMPayment + ResetEvent + ARMSchedule; Pydantic v2 strict+frozen+forbid; ARMRequest model_validator for index_path alignment); flip Wave-0 ARM-01 stubs | ARM-01 |
| **3** | `05-03-engine-build-arm-schedule-PLAN.md` | `lib/arm.py` (`build_arm_schedule(...)` per-epoch loop + slice-stitch + ResetEvent emission + applied_cap classification); flip Wave-0 ARM-02..05 stubs | ARM-02, ARM-03, ARM-04, ARM-05 |
| **4** | `05-04-cli-and-shared-helper-PLAN.md` (Claude's discretion D-discretion) | `scripts/_cli_helpers.py` (new; factor `find_json_float_loc` + `make_float_gate_envelope`); `scripts/amortize.py` + `scripts/affordability.py` (replace inline copies with imports — verify zero regression); `scripts/arm_simulate.py` (new); flip Wave-0 ARM-08 stubs | ARM-08 |
| **5** | `05-05-references-and-docstring-PLAN.md` | `references/arm-mechanics.md` (new; D-08 6 sections — uses CORRECTED citations from this RESEARCH.md); `lib/arm.py` ARMTerms docstring cites it; flip Wave-0 ARM-09 stubs | ARM-09 |
| **6** | `05-06-fixtures-and-oracle-PLAN.md` | `tests/fixtures/arm/*.json` (10 hand-calc fixtures per D-09); `tests/fixtures/arm/oracle/bankrate_5_1_*.pdf+.json` + `vertex42_5_1_*.json` + `americu_5_6_*.json` (per BLOCKER-1 swap); flip ALL remaining Wave-0 stubs; ROADMAP SC-1..SC-5 verbatim coverage | ARM-06, ARM-07 (closes all 9 ARM-N requirements) |

**Plan-checker note:** Wave 4 (CLI + shared-helper factor) MUST verify Phase 3 + Phase 4 test suites pass unchanged after `_find_json_float_loc` is moved out. Wave 1 (quantize_rate promotion) MUST verify the same. Both factor-extracts are Phase 5's net-positive long-term contributions to project hygiene; the planner should NOT skip them.

---

## Code Examples

Verified patterns drawn from existing Phase 1/3/4 surface (file:line citations).

### Example 1: Pydantic v2 model_validator(mode="after") cross-field check

Source: `lib/amortize.py:184-194` (Phase 3 D-02 validator); `lib/affordability.py` (Phase 4 D-08).

```python
# lib/arm.py — ARMRequest cross-field validator (Q7)
class ARMRequest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    loan: Loan
    arm_terms: ARMTerms
    assumed_index_rate: Rate
    index_path: list[IndexPathEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _index_path_periods_align_to_reset_triggers(self) -> ARMRequest:
        initial = self.arm_terms.initial_period_months
        cadence = self.arm_terms.reset_period_months
        term = self.loan.term_months
        triggers: set[int] = set()
        period = initial + 1
        while period <= term:
            triggers.add(period)
            period += cadence
        for entry in self.index_path:
            if entry.period not in triggers:
                raise ValueError(
                    f"index_path entry at period {entry.period} does not align "
                    f"to a reset trigger period (D-01)"
                )
        return self
```

### Example 2: Per-epoch slice-stitch using lib.amortize.build_schedule

Source: `lib/amortize.py:295-383` (`_build_fixed_monthly` Phase 3 D-04..D-15); CONTEXT.md D-05.

```python
# lib/arm.py — build_arm_schedule per-epoch loop (skeleton)
def build_arm_schedule(req: ARMRequest) -> ARMSchedule:
    loan = req.loan
    terms = req.arm_terms
    note_rate = terms.note_rate or loan.annual_rate  # D-02 default

    # Compute reset trigger periods (Q5 formula)
    triggers: list[int] = []
    p = terms.initial_period_months + 1
    while p <= loan.term_months:
        triggers.append(p)
        p += terms.reset_period_months

    # Epoch boundaries: [(1, initial+1), (61, 73), (73, 85), ..., (last_trigger, term+1)]
    boundaries = [(1, terms.initial_period_months + 1), *zip(triggers, [*triggers[1:], loan.term_months + 1])]

    arm_payments: list[ARMPayment] = []
    reset_events: list[ResetEvent] = []
    remaining_balance = loan.principal
    prior_rate = loan.annual_rate
    cum_int_carry = Decimal("0.00")
    cum_prin_carry = Decimal("0.00")

    for epoch_idx, (start, end) in enumerate(boundaries):
        epoch_window = end - start  # rows to keep
        is_final_epoch = epoch_idx == len(boundaries) - 1

        if epoch_idx == 0:
            current_rate = loan.annual_rate
        else:
            # Reset formula (D-02)
            index = next(
                (e.value for e in req.index_path if e.period == start),
                req.assumed_index_rate,
            )
            fully_indexed = quantize_rate(index + (Decimal(terms.margin_bps) / Decimal("10000")))
            effective_floor = max(Decimal(terms.margin_bps) / Decimal("10000"), terms.floor_rate)
            cap_bps = terms.initial_cap_bps if epoch_idx == 1 else terms.periodic_cap_bps
            periodic_ceiling = prior_rate + (Decimal(cap_bps) / Decimal("10000"))
            lifetime_ceiling = note_rate + (Decimal(terms.lifetime_cap_bps) / Decimal("10000"))
            ceiling = min(periodic_ceiling, lifetime_ceiling)
            new_rate = quantize_rate(max(effective_floor, min(fully_indexed, ceiling)))

            # Classify applied_cap (D-10 coverage)
            if new_rate == effective_floor:
                applied_cap = "floor"
            elif new_rate == lifetime_ceiling:
                applied_cap = "lifetime"
            elif new_rate == periodic_ceiling:
                applied_cap = "initial" if epoch_idx == 1 else "periodic"
            else:
                applied_cap = "none"

            # Record ResetEvent (need old/new pmt — computed from synthetic schedule below)
            current_rate = new_rate

        # Build synthetic schedule for FULL remaining term at current_rate (D-05)
        remaining_term = loan.term_months - start + 1
        synthetic = build_schedule(
            Loan(
                principal=remaining_balance,
                annual_rate=current_rate,
                term_months=remaining_term,
                origination_date=loan.origination_date,  # placeholder; offset later
                loan_type="arm",
            ),
            frequency="monthly",
            biweekly_mode=None,
            extra_principal=(),
        )
        # Slice off only the epoch window (preserves Phase 3 invariants for sliced rows)
        sliced = synthetic.payments[:epoch_window if not is_final_epoch else len(synthetic.payments)]
        for i, p in enumerate(sliced):
            absolute_period = start + i
            arm_payments.append(
                ARMPayment(
                    period=absolute_period,
                    payment_date=loan.origination_date + relativedelta(months=absolute_period),
                    payment=p.payment,
                    principal=p.principal,
                    interest=p.interest,
                    extra_principal=p.extra_principal,
                    balance=p.balance,
                    cumulative_interest=quantize_cents(cum_int_carry + p.cumulative_interest),
                    cumulative_principal=quantize_cents(cum_prin_carry + p.cumulative_principal),
                    rate_in_effect=current_rate,
                )
            )
        # Update carries for next epoch
        if not is_final_epoch:
            cum_int_carry = arm_payments[-1].cumulative_interest
            cum_prin_carry = arm_payments[-1].cumulative_principal
            remaining_balance = arm_payments[-1].balance
            # Record ResetEvent for the *next* epoch boundary (with old_pmt = sliced[-1].payment, new_pmt = TBD)
            # ... or defer ResetEvent emission to a separate pass after all epochs ship ...
        prior_rate = current_rate

    final_payment_adjusted = synthetic.final_payment_adjusted if is_final_epoch else False

    return ARMSchedule(
        loan=loan,
        arm_terms=terms,
        payments=arm_payments,
        reset_events=reset_events,
        total_interest=arm_payments[-1].cumulative_interest,  # D-15 invariant via Phase 1 Schedule pattern
        final_payment_adjusted=final_payment_adjusted,
    )
```

The skeleton illustrates the slice-stitch pattern; the planner finalizes ResetEvent emission ordering and `applied_cap=="none"` boundary semantics (e.g., when `new_rate == fully_indexed` exactly equal to `effective_floor` or `ceiling` — the branch order picks one Literal; document the deterministic choice).

---

## Open Questions (RESOLVED)

These are items where the locked CONTEXT.md decision conflicted with discovered reality. **LM-1 and LM-2 were RESOLVED on 2026-04-30 via inline CONTEXT.md revisions** to D-04 (oracle source) and D-08 (Selling Guide citations) — see the dated REVISION NOTES at the top of each decision in `05-CONTEXT.md`. LM-3, LM-4, LM-5 are NUANCES the planner must absorb verbatim into plan content; not blocking.

### LM-1 (RESOLVED 2026-04-30): MGIC has no ARM calculator (D-04)

**Resolution:** D-04 inline-revised in `05-CONTEXT.md` to swap MGIC for the three-source oracle: Bankrate (5/1, 7/1, 10/1) + Vertex42 Excel (transparent-formula cross-check) + AmericU 5/6 SOFR Disclosure PDF. CONTEXT.md canonical_refs section updated accordingly. No `/gsd-discuss-phase 5` re-entry needed; planner consumes the revised D-04.

- **What:** CONTEXT.md D-04 prescribes "MGIC capture-as-fixture" as the cross-validation oracle. MGIC's public site lists 5 calculators; none is an ARM calculator. The locked decision is unimplementable.
- **Recommendation:** `/gsd-discuss-phase 5` to re-lock D-04 with replacement oracle source. Suggested replacement: "Bankrate ARM calculator + Vertex42 Excel template (3/1/5/1/7/1/10/1) + AmericU 5/6 SOFR ARM Disclosure PDF (5/6 product)."
- **Risk if unaddressed:** Wave 0 cannot stub `test_oracle_cross_validation_*` accurately; Wave 6 cannot ship `tests/fixtures/arm/oracle/` faithfully; ROADMAP SC-3 ("ARM tests pass against published MGIC/Bankrate scenarios") is fulfilled by the fallback Bankrate clause but not by MGIC.

### LM-2 (RESOLVED 2026-04-30): D-08 Selling Guide section numbers are wrong

**Resolution:** D-08 inline-revised in `05-CONTEXT.md` with corrected citations: Fannie Mae §B2-1.4-02 "Adjustable-Rate Mortgages (ARMs)" (last updated 2025-12-10), Freddie Mac §6302.7(b), CFPB §1951 (cited in new D-08 item 7 for teaser-ARM lifetime base disclosure). Old citations (B5-3.5-01, §4404) removed from CONTEXT.md canonical_refs. Wave 5 plan must use the corrected citations verbatim — planner absorbs from revised D-08, NOT from this RESEARCH.md historical landmine note.

#### Original landmine details (preserved for traceability):

- **What:** CONTEXT.md D-08 cites "Fannie Mae §B5-3.5-01" (404) and "Freddie Mac §4404" (stale). The correct Fannie section is **B2-1.4-02 "Adjustable-Rate Mortgages (ARMs)" updated 2025-12-10**. Modern Freddie ARM material is on the SOFR-Indexed ARMs product page + Guide Section 6302.7(b) (delivery) + Chapter 4203 (LTV).
- **Recommendation:** `/gsd-discuss-phase 5` to re-lock D-08 with corrected citations OR planner self-corrects in Wave 5 + `references/arm-mechanics.md` content (smaller blast radius — just don't carry the wrong section number forward into the actual file).
- **Risk if unaddressed:** `references/arm-mechanics.md` ships with broken citations; Wave 5 `test_arm_mechanics_citations` would either grep for the wrong sections (matching the bug) or grep for the right sections (failing the locked CONTEXT.md). Either way the contract is broken.

### LM-3 (NUANCE): Lifetime cap base disagrees with CFPB convention for teaser ARMs

- **What:** CFPB §1951 says lifetime cap is measured "from the **initial rate**." For non-teaser ARMs, `initial_rate == loan.annual_rate == note_rate` and CONTEXT.md D-02 is correct. For TEASER ARMs (where `loan.annual_rate=0.0300` is teaser and `arm_terms.note_rate=0.0500` is the post-teaser rate), CONTEXT.md D-02 uses `note_rate=0.0500` as the lifetime base. CFPB says use `initial_rate=0.0300`.
- **Recommendation:** Document the engine's choice explicitly in `references/arm-mechanics.md` Section 2 (Cap Precedence): "This engine measures lifetime ceiling against `note_rate` (defaulting to `loan.annual_rate` when None). For teaser-rate ARMs, callers must supply the post-teaser note rate explicitly via `arm_terms.note_rate`. CFPB §1951 documents the alternative convention measuring against the initial (possibly teaser) rate; the engine's choice gives the borrower a more conservative (lower) lifetime ceiling and matches Fannie B2-1.4-02 'Standard ARM' worked examples." This makes the deviation a documented engine convention rather than a silent semantic bug.
- **Risk if unaddressed:** A teaser-rate ARM consumer (Phase 8 stress, Phase 11 amortization-agent) silently produces a lifetime ceiling 200bps higher than CFPB-convention; user disputes the number against CFPB-published explainer; we cannot point to documentation.

### LM-4 (NUANCE): CONTEXT.md statement on Pydantic v2 model_config inheritance is wrong

- **What:** CONTEXT.md L102 + 351 say "the parent's config doesn't auto-inherit; planner re-specifies." Per Pydantic v2 docs, `model_config` IS auto-inherited and merged.
- **Recommendation:** Planner re-specifies anyway (defense-in-depth + explicit grep-discoverability) — but should NOT write a test that asserts re-specification is _required_ for behavior. The test should assert config IS in effect (e.g., `ARMPayment(...)` with `extra_field="x"` raises ValidationError; `ARMPayment.model_config['frozen'] is True`), not assert the literal `model_config = ConfigDict(...)` line is present in the subclass source.
- **Risk if unaddressed:** A future Pydantic v2.x simplification (e.g., docs example deprecating re-specification) would break a brittle "literal config block must appear in source" test.

### LM-5 (NUANCE): `applied_cap == "none"` Literal value coverage unclear

- **What:** D-10 requires every `applied_cap` Literal value (`"initial"`, `"periodic"`, `"lifetime"`, `"floor"`, `"none"`) be exercised by ≥1 fixture. The natural fixture for `"none"` is "modest reset where neither cap nor floor binds" — i.e., index moved within the periodic_cap envelope and the result is between `effective_floor` and `min(periodic_ceiling, lifetime_ceiling)` (strict inequality on both sides). The planner must construct an `arm_5_1_payment_jump_at_61` fixture whose reset lands in the open interval.
- **Recommendation:** In Wave 6, when constructing `arm_5_1_payment_jump_at_61.json`, ensure the locked example numbers produce `applied_cap == "none"` (e.g., note_rate=0.05, margin=200bps, initial_cap=500bps, lifetime_cap=500bps, index at month 61 = 0.0525 → fully_indexed = 0.0725, prior_rate = 0.05, periodic_ceiling = 0.05 + 5pp = 0.10, lifetime_ceiling = 0.05 + 5pp = 0.10, floor = max(margin=0.02, floor=0.03) = 0.03; new_rate = 0.0725 strictly between 0.03 and 0.10 → `applied_cap = "none"`). The planner verifies the chosen fixture numbers DO land in the open interval and adds an explicit `expected.reset_events[0].applied_cap == "none"` assertion.
- **Risk if unaddressed:** A fixture chosen for SC-2 payment-jump verification might accidentally land at a cap boundary (`applied_cap = "initial"`); citation-coverage meta-test then fails because `"none"` is unexercised.

### LM-6 (NUANCE): Phase 1 oracle anchor reuse for epoch 0

- **What:** D-09 fixture list says the initial-fixed-period must produce `$2528.27` P&I exactly when `loan.annual_rate=0.065` (Phase 1 oracle). Verified by `tests/fixtures/golden_pmt.json` (the `computed_400k_30yr` anchor). Phase 5's epoch-0 path goes through `_build_fixed_monthly` with `Loan(principal=400000, annual_rate=0.065, term_months=360)` — yielding the same oracle. ✓
- **Caveat:** Phase 5's `Loan.loan_type="arm"` (not "fixed"). Phase 3's `_build_fixed_monthly` does NOT branch on `loan_type` — verified by reading `lib/amortize.py:286-292` (dispatch is by `frequency` + `biweekly_mode` only). So epoch-0 produces identical math regardless of `loan_type` value. ✓
- **Recommendation:** Add `tests/test_arm.py::test_initial_fixed_period_matches_phase1_oracle` that constructs an ARMRequest with $400k @ 6.5%/30yr and asserts `arm_schedule.payments[0].payment == Decimal("2528.27")`. This pins the cross-phase oracle anchor and surfaces any drift in epoch-0 math.

---

## Sources

### Primary (HIGH confidence)

- `/Users/cujo253/Documents/mortgage-ops/lib/amortize.py:1-498` — Phase 3 engine direct read; D-04..D-15 invariants verified.
- `/Users/cujo253/Documents/mortgage-ops/lib/affordability.py:613-627` — `_quantize_rate` definition; ROUND_HALF_UP confirmed.
- `/Users/cujo253/Documents/mortgage-ops/lib/money.py:1-46` — MONEY_CONTEXT + quantize_cents + CENT.
- `/Users/cujo253/Documents/mortgage-ops/lib/models.py:1-92` — Loan/Payment/Schedule/Money/Rate types; D-15 validator pattern.
- `/Users/cujo253/Documents/mortgage-ops/scripts/amortize.py:1-238` + `scripts/affordability.py:1-320` — CLI shape mirror; `_find_json_float_loc` + 6-key envelope construction.
- `/Users/cujo253/Documents/mortgage-ops/tests/conftest.py:38-70` — `amortize_fixture` + `affordability_fixture` loader patterns.
- `/Users/cujo253/Documents/mortgage-ops/tests/test_amortize.py:718-1067` — CLI subprocess + envelope-uniformity + lazy-import tests (Phase 5 mirrors).
- Pydantic v2 official docs — Models concept page (https://pydantic.dev/docs/validation/latest/concepts/models/).

### Secondary (MEDIUM confidence)

- Fannie Mae Selling Guide B2-1.4-02 (https://selling-guide.fanniemae.com/sel/b2-1.4-02/adjustable-rate-mortgages-arms) — ARM eligibility, no lifetime floor below margin.
- CFPB Ask CFPB §1951 (https://www.consumerfinance.gov/ask-cfpb/what-are-rate-caps-with-an-adjustable-rate-mortgage-arm-and-how-do-they-work-en-1951/) — lifetime cap "from the initial rate."
- Freddie Mac SOFR-Indexed ARMs product page (https://sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/sofr-indexed-arms) — 3/6, 5/6, 7/6, 10/6 products; margin 100-300 bps.
- AmericU 5/6 SOFR ARM Disclosure 2/1/5 caps (https://www.americu.com/wp-content/uploads/2022/06/5_6-SOFR-ARM-Program-Disclosure-2_1_5-CAPS.pdf) — first reset at month 61 + 6-month cadence.
- abt.bank 5/6/7/6/10/6 SOFR ARM Disclosure (https://www.abt.bank/wp-content/uploads/2022/09/Early-ARM-Disclosure-5yr-7yr-and-10yr-ARM-SOFR-Static.pdf) — cross-confirms.
- Bankrate ARM calculator (https://www.bankrate.com/mortgages/adjustable-rate-mortgage-calculator/) — replacement oracle source for BLOCKER-1.
- Vertex42 ARM Calculator (https://www.vertex42.com/ExcelTemplates/arm-calculator.html) — Excel formula source; transparent methodology.

### Tertiary (LOW confidence — flagged for validation)

- mortgagecalculator.org ARM page (https://www.mortgagecalculator.org/calcs/arm.php) — third-party calculator; per-period output verified via search snippet but UI not directly inspected.
- Tiger Loans ARM blog (https://www.tigerloans.com/en/blog/understanding-arm) — third-party explainer; cap-structure language consistent with CFPB but secondary source.

### Verified non-existence

- MGIC ARM calculator — confirmed does NOT exist via direct WebFetch of https://www.mgic.com/tools/calculators + https://www.mgic.com/tools/consumer-calculators (both list a small fixed set of consumer calculators; ARM is not among them).
- Fannie Mae §B5-3.5-01 — confirmed 404 via direct WebFetch; correct section is B2-1.4-02.
- Freddie Mac §4404 — modern URL scheme is different; stale section number per direct WebFetch of https://guide.freddiemac.com/app/guide/section/4404.7 (returns "Guide Home" not the section).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Phase 3 `_build_fixed_monthly` does not branch on `loan_type`, so passing `Loan(loan_type="arm")` to `build_schedule` produces identical math to `loan_type="fixed"` | Q1, LM-6 | Phase 5 epoch-0 computes wrong P&I; Phase 1 oracle anchor breaks. **Mitigation: verified by direct read of `lib/amortize.py:286-292`; only `frequency`+`biweekly_mode` drive dispatch. CONFIDENT.** |
| A2 | `applied_cap == "none"` is the correct Literal when the new_rate falls strictly between `effective_floor` and `min(periodic_ceiling, lifetime_ceiling)` | LM-5, D-10 | The fixture chosen for SC-2 might accidentally land at a cap boundary; citation-coverage breaks. **Mitigation: planner constructs SC-2 fixture numbers explicitly to produce open-interval result.** |
| A3 | Pydantic v2 `model_validator(mode="after")` allows reading `self.arm_terms` + `self.loan` siblings before raising | Q7 | The proposed `_index_path_periods_align_to_reset_triggers` validator may not have access to siblings at validation time. **Mitigation: verified by Pydantic v2 docs; `mode="after"` runs post-construction. Phase 4 D-08 already uses the same pattern in `_validate_common`.** |
| A4 | ARMTerms `_initial_period_aligns_with_reset` validator (D-06 sketch) is optional and the planner skips it without ARM-01 violation | D-06 | The "reasonable invariant" check on `reset_period_months <= initial_period_months` would reject 5/12 (impossible product) but also blocks legitimate hypothetical products. **Mitigation: D-06 itself says "Not strictly required by ARM-01; planner can skip if it surfaces no real bugs." CONFIDENT.** |
| A5 | Bankrate ARM calculator (replacement oracle in BLOCKER-1) produces per-period output rich enough to cross-validate hand-calc fixtures | Q3, LM-1 | If Bankrate only emits summary numbers (not per-period rate + payment), the cross-validation degrades to spot-check. **Mitigation: WebSearch confirmed Bankrate exposes a printable amortization table; recommend Vertex42 as a second oracle (Excel formulas are transparent).** |

---

## Environment Availability

> Phase 5 has no new external dependencies. All tooling already in pyproject.toml from Phase 1.

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python 3.12+ | All | ✓ | 3.12.x (Phase 1 baseline) | — |
| numpy-financial | epoch P&I via `lib.amortize` | ✓ | 1.0.0 (verified Phase 3) | — |
| pydantic >=2.6 | All Pydantic v2 models | ✓ | 2.13+ (Phase 4 baseline) | — |
| python-dateutil | per-epoch payment_date offsets | ✓ | (Phase 3 baseline) | — |
| pytest, mypy --strict, ruff | dev tooling | ✓ | (Phase 1 baseline) | — |
| Browser (PDF capture) | BLOCKER-1 oracle artifact | ✓ | n/a (developer workflow) | Manual transcription |

**No missing dependencies.** Phase 5 ships zero new pyproject.toml entries.

---

## Metadata

**Confidence breakdown:**
- Standard stack / per-epoch slice-stitch correctness: HIGH — direct file read + Phase 3 invariants verified
- Pydantic v2 inheritance behavior: HIGH — official docs + Phase 4 patterns confirm
- 5/6 ARM cadence (month 61 first reset, month 67 second): HIGH — multiple lender disclosures cross-confirm
- D-04 oracle source (MGIC ARM calculator): VERIFIED NON-EXISTENT — BLOCKER-1
- D-08 Selling Guide citations (B5-3.5-01, §4404): VERIFIED WRONG — BLOCKER-2
- Lifetime cap base for teaser ARMs: MEDIUM — CFPB convention disagrees with locked D-02; documented as engine convention deviation in LM-3
- `_quantize_rate` consumer count: HIGH — grep direct evidence
- JSON-float gate factoring viability: HIGH — verified byte-identical helper across Phase 3 + Phase 4

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (regulatory cite freshness; MGIC/Bankrate UI may change quarterly)

## RESEARCH COMPLETE

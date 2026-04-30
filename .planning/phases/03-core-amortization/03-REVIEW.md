---
phase: 03-core-amortization
reviewed: 2026-04-29T00:00:00Z
depth: standard
diff_base: 599fb0f
files_reviewed: 3
files_reviewed_list:
  - lib/amortize.py
  - scripts/amortize.py
  - tests/test_amortize.py
findings:
  blocker: 0
  warning: 4
  total: 4
status: issues_found
---

# Phase 3: Code Review Report (Gap-Closure Delta)

**Reviewed:** 2026-04-29
**Depth:** standard
**Diff base:** `599fb0f` (pre-CR-01/WR-02 baseline)
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Adversarial review of the 4-commit gap-closure delta covering CR-01 (`AmortizeRequest._no_duplicate_recurring_periods` validator) and WR-02 (uniform 6-key Pydantic-shaped error envelope in `scripts/amortize.py`).

**Math correctness (CR-01) — clean.** The new `_no_duplicate_recurring_periods` validator correctly closes the D-05 order-of-list ambiguity at the request boundary: it raises `ValueError` (Pydantic-wraps to `ValidationError`), is scoped to `recurring=True` only, runs in O(n) over the entries list, leaves the engine's `_resolve_extra` math path untouched, and is exercised by 6 well-shaped tests (3 negative orderings + 3 positive sibling cases). The Decimal-only money discipline is preserved — the validator does no arithmetic.

**Envelope contract (WR-02) — substantively clean, with documented contract drift.** The 6-key envelope (`type, loc, msg, input, url, ctx`) is unified across the float-gate path and the native Pydantic `e.json()` path. `_find_json_float_loc` was correctly refactored to return `tuple[list[str | int], str] | None` so the envelope can populate `input` without re-walking. `pydantic.VERSION` is lazy-imported INSIDE `main()` after `argparse.parse_args()`, preserving D-18.

**Concerns surfaced below:**
1. The float-gate misses JSON **integer** money values — the docstring claims money/rate fields "must be JSON strings" but the gate only catches JSON floats. A user submitting `"principal": 400000` (no decimal point) bypasses the gate and is silently coerced by Pydantic.
2. `_find_json_float_loc` reports only the FIRST JSON float; a multi-float input surfaces one error at a time, contradicting the unified-envelope claim that downstream consumers see "the rejection" in one pass.
3. The 6-key envelope uniformity test only inspects `errors[0]`; if Pydantic emits multiple errors, the contract is unverified for `errors[1:]`.
4. The CR-01 validator's `ValueError` message is interpolated into `loc=[]` by Pydantic's wrapper (since `mode="after"` model validators have no field anchor); downstream Phase 9/10 narration cannot rely on `loc` to distinguish CR-01 from D-02 — only `msg` substring matching works.

None of these rise to BLOCKER. The math correctness contract holds; the D-19 envelope contract holds for the cases tested.

---

## Warnings

### WR-01: Float-gate accepts JSON integer money values, contradicting documented "JSON strings only" contract

**File:** `scripts/amortize.py:89-95` (gate docstring), `scripts/amortize.py:100` (parser invocation)

**Issue:**
The docstring claims:
> The schema has zero fields that legitimately accept JSON floats:
>   - principal / annual_rate / amount: must be JSON strings (Money/Rate)
>   ...
> A blanket "reject any JSON float" check is therefore correct.

The "therefore" inference is incomplete. `parse_float=Decimal` only intercepts JSON numbers that contain `.` or `e` (the Python `json` module's definition of "float"). A JSON **integer** literal — e.g. `"principal": 400000` — is parsed as a Python `int`, NOT a `Decimal`. The walker only checks `isinstance(node, _Decimal)`, so int-shaped money values pass straight through to Pydantic, which (per Pydantic v2 JSON-mode strict semantics) coerces JSON ints to `Decimal`. The user's input never gets to "must be JSON string" enforcement.

Math correctness is NOT compromised — `Decimal("400000")` is exact. But the documented D-19 contract ("JSON strings required for money/rate fields") is violated silently. Phase 9/10 consumers expecting the float-gate to be the single chokepoint for "non-string money" will be surprised by integer-shaped submissions reaching the engine.

Concrete reproducer (would NOT exit 2 via the float-gate path):
```json
{"loan": {"principal": 400000, "annual_rate": "0.065000", "term_months": 360}}
```

**Fix (preferred — tighten the gate):** Walk for JSON ints in money/rate fields too, OR drop the "must be JSON strings" claim from the docstring and accept that the gate's contract is narrower than D-19.

```python
# In _find_json_float_loc, also intercept ints in known money/rate fields.
MONEY_FIELDS = {"principal", "annual_rate", "amount"}

def _walk(node, path):
    if isinstance(node, _Decimal):
        return (path, str(node))
    if (isinstance(node, int) and not isinstance(node, bool)
            and path and path[-1] in MONEY_FIELDS):
        return (path, str(node))
    ...
```

**Fix (alternative — accept narrower scope):** Update the docstring at `scripts/amortize.py:89-95` to acknowledge that the gate catches floats only; integers in money fields are accepted by Pydantic's JSON-mode coercion. Remove the "therefore correct" claim.

---

### WR-02: Envelope reports only the first JSON float; multi-float inputs surface errors one-at-a-time, contradicting "unified envelope" framing

**File:** `scripts/amortize.py:105-120` (`_walk` early-return on first hit)

**Issue:**
The envelope-shape contract paragraph (`scripts/amortize.py:36-60`) and the WR-02 closure narrative (03-06-SUMMARY.md) frame the 6-key envelope as the canonical format Phase 9/10 consumers parse. But native Pydantic `ValidationError.json()` returns a **list** of all violations (one entry per violating field). The float-gate path returns a **list of length 1** because `_walk` returns the first Decimal it encounters and the caller emits a single envelope.

A user submitting two JSON floats:
```json
{"loan": {"principal": 400000.00, "annual_rate": 0.065}}
```
gets ONE error envelope (for `principal`), fixes it to a string, re-runs, and gets a SECOND error (for `annual_rate`). The "uniform shape" claim still holds (both are 6-key dicts in a list), but the implied "single end-to-end pass" UX consumers expect from Pydantic-style ValidationError surfaces is broken: the float-gate path is iterative-discovery, the Pydantic path is exhaustive.

Phase 9 db-write.mjs and Phase 10 SKILL.md narration that aggregate "all the things wrong with this input" will under-report on float-gate rejections.

**Fix:** Make `_walk` collect ALL hits, not just the first:

```python
def _find_json_float_locs(raw: str) -> list[tuple[list[str | int], str]]:
    ...
    hits: list[tuple[list[str | int], str]] = []
    def _walk(node, path):
        if isinstance(node, _Decimal):
            hits.append((path, str(node)))
            return  # Decimal is a leaf
        if isinstance(node, dict):
            for k, v in node.items():
                _walk(v, [*path, k])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                _walk(v, [*path, i])
    _walk(parsed, [])
    return hits

# Caller emits one envelope per hit:
hits = _find_json_float_locs(raw)
if hits:
    envelope = [_build_envelope(loc, val, _pydantic_version) for loc, val in hits]
    print(json.dumps(envelope), file=sys.stderr)
    return 2
```

The current single-hit behavior is not a math correctness issue; it's a UX/contract drift relative to Pydantic's exhaustive-error semantics that the WR-02 documentation invokes.

---

### WR-03: Uniformity contract test only verifies errors[0]; downstream consumers reading errors[1:] could see drift uncaught by the suite

**File:** `tests/test_amortize.py:996-1067` (`test_cli_error_envelope_uniformity`)

**Issue:**
The test extracts `float_errors[0]` and `d02_errors[0]` and asserts identical 6-key keysets. If Pydantic ever emits >1 error for the D-02 path (e.g. a future Pydantic version splits the cross-field validation into a primary + ancillary error), `errors[1:]` could carry a different keyset (legacy 3-key, missing `ctx`, etc.) and this test would NOT catch it. The test docstring acknowledges the scope ("first-error level") but Phase 9 db-write.mjs ingests the full list, so downstream regression would slip past the suite.

Risk is low for the specific D-02 reproducer used (current Pydantic 2.13 emits exactly one error for that input class), but the contract being asserted is "uniform shape across ALL ValidationError-class boundary failures" and the test only proves it for `errors[0]`.

**Fix:** Iterate all errors in both lists:

```python
expected_keys = {"type", "loc", "msg", "input", "url", "ctx"}
for i, err in enumerate(float_errors):
    assert set(err.keys()) == expected_keys, (
        f"float_errors[{i}] keys drifted: got {sorted(err.keys())}"
    )
for i, err in enumerate(d02_errors):
    assert set(err.keys()) == expected_keys, (
        f"d02_errors[{i}] keys drifted: got {sorted(err.keys())}"
    )
```

This costs nothing and pins the contract on the WHOLE list, which is what the documentation claims.

---

### WR-04: CR-01 ValidationError emits `loc=[]`; downstream narration cannot distinguish CR-01 from D-02 via `loc`, only via `msg` substring matching

**File:** `lib/amortize.py:196-223` (`_no_duplicate_recurring_periods` validator)

**Issue:**
Pydantic v2 model-level `@model_validator(mode="after")` validators that raise `ValueError` produce a `ValidationError` whose `loc` is `[]` (empty tuple in Pydantic ErrorDetails) — there's no field anchor because the validator inspected the whole model. Consequence: the structured envelope for CR-01 looks like:

```json
[{"type": "value_error", "loc": [], "msg": "duplicate recurring extra_principal at period 1; ...",
  "input": {<entire request dict>}, "url": "...", "ctx": {...}}]
```

The 03-05-SUMMARY claims "CLI run on CR-01 reproducer JSON exits 2 with parseable JSON list whose first error contains `duplicate recurring`" — true, but the empty `loc` means Phase 9/10 narration MUST string-match on `msg` to identify the violation type. Compare with Pydantic's per-field validators (e.g. `ExtraPrincipalEntry.amount`'s `gt=0`) where `loc=["extra_principal", 0, "amount"]` provides structured field-routing.

This isn't a bug in the validator — it's the canonical Pydantic v2 idiom. But the WR-02 docstring (`scripts/amortize.py:36-60`) says Phase 10 SKILL.md narration "narrates the rejection by reading `loc` (which field) + `msg` (why) + `input` (the rejected value)". For CR-01 (and D-02) the `loc` carries no field information; the narration falls back to `msg` parsing exclusively. The 6-key shape is uniform but the SEMANTIC content of `loc` varies by surface.

**Fix (preferred):** Construct the CR-01 envelope manually like the float-gate does, with an explicit `loc` like `["extra_principal", i, "period"]` so downstream consumers can field-route:

```python
# In scripts/amortize.py, before model_validate_json — pre-scan extra_principal
# for duplicate recurring periods and emit an envelope with loc populated.
# Or: convert the model_validator into a per-list-item validator using
# Pydantic's AfterValidator on extra_principal, which gives Pydantic enough
# context to populate loc=['extra_principal', i].
```

**Fix (alternative — document the limitation):** Update `scripts/amortize.py:36-60` to acknowledge that model-level validators (CR-01, D-02) emit empty `loc` and that downstream narration falls back to `msg` substring matching for those cases. Currently the docstring implies all 6 keys carry semantic information uniformly.

This is contract-shape drift, not math drift. The CR-01 closure WORKS — duplicate inputs are rejected deterministically. But the unified-envelope claim is weaker than the docstring implies.

---

## Defect Hunts That Came Back Clean

The following adversarial probes were performed and found NO defect; recording them so the next reviewer doesn't re-run them:

- **CR-01 validator scoping:** Confirmed the `if not entry.recurring: continue` early-out correctly excludes one-shot entries from the dedup set. Three-way recurring duplicates (test pinned). Recurring + one-shot at same period (test pinned). One-shot + one-shot at same period (test pinned).
- **CR-01 validator iteration:** `set[int]` lookup is O(1); full pass is O(n). No quadratic surface introduced.
- **CR-01 validator order vs D-02:** Pydantic v2 `mode="after"` runs validators in declaration order. D-02 fires first; if input violates both, D-02 wins. 03-05-SUMMARY documents this as intentional. No test crosses both, but the ordering is stable.
- **`_resolve_extra` engine math:** Untouched in this delta. With the validator gating the input class, the `max(...)` selector in `_resolve_extra` is now well-defined (no recurring ties on `entry.period`). Math correctness contract preserved.
- **Decimal-only money discipline:** Both `_no_duplicate_recurring_periods` and the float-gate envelope construction are float-free. No Decimal/float mixing introduced. `quantize_cents` not invoked in either change (correctly — no money arithmetic to round).
- **Lazy-import D-18 preservation:** `from pydantic import VERSION` is INSIDE `main()`, INSIDE the `if float_hit is not None:` block, AFTER `args = parser.parse_args()`. The `--help` fast path is byte-identical to pre-WR-02. Pinned by `test_cli_help_does_not_import_lib_amortize`.
- **`pydantic.VERSION` shape:** Pinned project version is `pydantic>=2.13.3` (`pyproject.toml:7`). `"2.13.3".split(".")[:2]` -> `["2", "13"]` -> `"2.13"`. URL emits `https://errors.pydantic.dev/2.13/v/decimal_type`, matches Pydantic's docs URL convention. No IndexError surface for any well-formed semver.
- **`_find_json_float_loc` walker safety:** Recursive descent through dict/list; terminates at first Decimal. No infinite recursion (JSON is a tree). No mutation of input. List/dict path-building uses `[*path, k]` (new list per recursive call); no aliasing.
- **Walker handles JSON null/bool/string/int correctly:** `isinstance` checks for Decimal/dict/list only; everything else falls through to `return None`. Non-Decimal numerics (ints) silently skipped (related to WR-01 above).
- **`str(Decimal)` round-trip preservation:** `Decimal("400000.00")` -> `"400000.00"` (preserves trailing zeros via Decimal's lexical form). Pinned by `test_cli_rejects_float_principal` line 923 (`err["input"] == "400000.00"`).
- **6-key envelope JSON-serializability:** All 6 values are JSON-serializable (str/list/str/str/str/dict). `loc` mixes str+int for nested array paths; ints serialize as JSON numbers (matches Pydantic's native `loc` shape). No serialization risk.
- **Test substring assertions for CR-01 message:** `"duplicate"`, `"period"`, `"recurring"` are all in the pinned message; future message tweaks must preserve all three substrings. Symmetric tests for `[100,200]` and `[200,100]` orderings pin order-independence.
- **AMRT-07 invariant (sum of principal+extra == original):** Engine path untouched in this delta; `assert_schedule_invariants` continues to pin via Decimal exact-equality across all 4 oracles + biweekly modes + extra-principal scenarios.
- **D-15 invariant (`Schedule.total_interest == payments[-1].cumulative_interest`):** Engine path untouched; `assert_schedule_invariants` continues to pin.
- **No new external surfaces / network calls / file writes:** Validator + envelope construction are pure functions over already-loaded inputs. No new I/O attack surface.
- **`extra="forbid"` on `AmortizeRequest`:** Unknown keys at request top-level are rejected by Pydantic. The float-gate runs BEFORE Pydantic, so unknown-key + JSON-float in unknown-key would emit a float-gate envelope with `field_path = "<unknown_key>"`. User-controlled JSON keys flow into `ctx.field_path` as opaque text — no injection risk (no shell/SQL/HTML interpolation downstream); 03-06-SUMMARY documents this under T-03-06-04/T-03-06-08.

---

_Reviewed: 2026-04-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Diff range: 599fb0f..HEAD (4 source-modifying commits: 973456c, f8c1ddb, 450d8d9, 1bb2cc6; plus 4bdd5eb, 359f7a7 docs)_

---
phase: 03-core-amortization
plan: 06
subsystem: amortization-cli-envelope
gap_closure: true
tags: [amortization, cli, error-envelope, d-19, wr-02, gap-closure]
requirements: [AMRT-06]
requires:
  - scripts/amortize.py::_find_json_float_loc (existing 3-key envelope shape; refactored)
  - scripts/amortize.py::main float-gate envelope construction (existing 3-key emission; replaced)
  - scripts/amortize.py module docstring (existing structure preserved; extended)
  - lib/amortize.py::AmortizeRequest (Pydantic-native ValidationError surface; unchanged — Pydantic emits 6-key shape natively)
provides:
  - scripts/amortize.py::_find_json_float_loc returns tuple[list[str | int], str] | None (loc-path AND offending value as Decimal-string)
  - scripts/amortize.py float-gate envelope construction emits all 6 Pydantic v2 keys (type, loc, msg, input, url, ctx) — uniform with native ValidationError shape
  - scripts/amortize.py module docstring "Envelope Shape Contract (WR-02 closure)" paragraph naming Phase 9 / Phase 10 consumers
  - tests/test_amortize.py::test_cli_rejects_float_principal asserts 6-key keyset + per-key value contracts (type, loc, msg, input, url-prefix/suffix, ctx.class)
  - tests/test_amortize.py::test_cli_error_envelope_uniformity asserts cross-shape uniformity contract (float-gate keyset == D-02 path keyset == 6 Pydantic keys)
affects:
  - scripts/amortize.py D-19 boundary contract (ValidationError-class surfaces now uniformly emit 6-key Pydantic v2 e.json() shape)
  - Phase 9 (Node orchestration / DuckDB persistence) downstream consumer surface — db-write.mjs can ingest a single uniform envelope
  - Phase 10 (Claude SKILL.md narration) downstream consumer surface — modes/_shared.md narrates rejections with one shape across all ValidationError-class gates
decisions:
  - Lazy-import `pydantic.VERSION` INSIDE main() (not at module top) to preserve D-18 fast --help — the version segment in the docs URL is computed at runtime so a future Pydantic minor upgrade auto-aligns without code change
  - URL pattern uses prefix/suffix matching in test (startswith "https://errors.pydantic.dev/" + endswith "/v/decimal_type") rather than exact-string match so the test stays green across Pydantic minor upgrades
  - ctx contains BOTH `class: "Decimal"` (mirrors Pydantic native ctx convention) AND project-specific `field_path: "<dotted path>"` (matches downstream narration convention; allows Phase 10 SKILL.md to render "loan.principal" without re-walking loc)
  - File-not-found and OSError envelopes left on legacy `{"error": "<message>"}` shape per explicit out-of-scope clause in the WR-02 gap entry — these are NOT Pydantic ValidationError surfaces and predate the envelope contract; backward compatibility for test_cli_file_not_found_returns_structured_error and test_cli_invalid_json_input is preserved
  - Argparse usage errors stay on argparse's stderr formatting (also out of scope) — no change to test_cli_no_input_returns_argparse_error
  - Float-gate `msg` starts with "Input should be" (matches Pydantic's canonical decimal_type prefix per substring assertion) and continues with the project-specific D-19 context after the canonical prefix
  - Validator declaration order in lib/amortize.py::AmortizeRequest unchanged (D-02 _biweekly_mode_consistency runs first, D-05 _no_duplicate_recurring_periods runs second from 03-05) — this plan only touches the CLI surface, not the model
key-files:
  modified:
    - scripts/amortize.py
    - tests/test_amortize.py
  created: []
metrics:
  duration: ~4 min
  tasks: 2
  commits: 2
  tests_added: 1 (test_cli_error_envelope_uniformity)
  tests_tightened: 1 (test_cli_rejects_float_principal)
  files_modified: 2
  files_created: 0
  full_suite: 301 passed (was 300; +1 new uniformity test)
  phase_3_file: 42 passed (was 41; +1 new uniformity test; tightened test stays the same count)
  completed: 2026-04-30
---

# Phase 3 Plan 6: WR-02 Error Envelope Uniformity (CLI 6-Key Shape) Summary

**One-liner:** Closes gap WR-02 by unifying `scripts/amortize.py` ValidationError-class boundary envelopes to Pydantic v2's full 6-key e.json() shape (`type, loc, msg, input, url, ctx`) — Phase 9 Node orchestration and Phase 10 SKILL.md narration now parse stderr as a single uniform JSON contract regardless of which gate fired.

## Objective

Phase requirement closed: **AMRT-06** (`scripts/amortize.py` provides JSON-in / JSON-out CLI for skill use; the boundary error envelope is part of that contract).

Verification gap closed: **WR-02** — `scripts/amortize.py` previously emitted a 3-key envelope `{type, loc, msg}` for the float-in-money pre-validation gate but a 6-key envelope `{type, loc, msg, input, url, ctx}` for native Pydantic ValidationError surfaces. Per UAT decision option (a), all ValidationError-class boundary surfaces now emit the same 6-key Pydantic v2 shape — eliminating conditional shape detection in downstream Phase 9 / Phase 10 consumers.

## What Shipped

### scripts/amortize.py

1. **`_find_json_float_loc` refactored:** Return type changed from `list[str | int] | None` to `tuple[list[str | int], str] | None`. The function now returns BOTH the JSON-pointer loc-path AND the offending input value (as a Decimal-string via `str(Decimal)`) so the caller can populate the envelope's `input` key without re-walking the JSON. Inner `_walk` helper return type updated to match.

2. **Float-gate envelope construction replaced (lines 184-211):** All 6 Pydantic v2 keys are now populated:
   - `type`: `"decimal_type"` (unchanged from pre-fix)
   - `loc`: loc-path from `_find_json_float_loc` (unchanged from pre-fix)
   - `msg`: starts with "Input should be" (Pydantic's canonical decimal_type prefix); the project-specific D-19 context "JSON string required for money/rate fields per D-19 (JSON floats are rejected at the boundary)" follows after the canonical prefix
   - `input`: `float_input` from the new tuple shape (e.g. `"400000.00"` — str() of the parsed Decimal; round-trips exactly through JSON)
   - `url`: `f"https://errors.pydantic.dev/{_major_minor}/v/decimal_type"` where `_major_minor` is the first two dotted components of `pydantic.VERSION` (lazy-imported INSIDE main() so D-18 fast --help is preserved)
   - `ctx`: `{"class": "Decimal", "field_path": ".".join(str(p) for p in float_loc)}` — `class` mirrors Pydantic's native ctx convention; `field_path` is project-specific dotted-path for downstream narration

3. **Module docstring extended with "Envelope Shape Contract (WR-02 closure)" paragraph** (lines 36-57). The new section block documents:
   - The uniform 6-key shape applies to BOTH native Pydantic ValidationError (e.json() pass-through) AND the pre-validation float-gate (manually constructed)
   - The canonical URL pattern `https://errors.pydantic.dev/{MAJOR.MINOR}/v/{error_type}` and the pydantic.VERSION-driven runtime construction
   - Phase 9 (Node orchestration / DuckDB persistence — db-write.mjs) and Phase 10 (Claude SKILL.md narration — modes/_shared.md) named explicitly as the consumers
   - File-not-found / OSError stay on `{"error": "<message>"}` shape; argparse usage errors stay on argparse's stderr formatting — both out of scope per the WR-02 gap entry

### tests/test_amortize.py

1. **`test_cli_rejects_float_principal` tightened in place** (replacement, not delete-and-append). The previous test asserted only that ONE error referenced principal/decimal_type/Input-should-be. The replacement asserts the EXACT 6-key keyset on the first error AND specific values for every key:
   - `set(err.keys()) == {"type", "loc", "msg", "input", "url", "ctx"}` — exact-shape match
   - `err["type"] == "decimal_type"`
   - `err["loc"] == ["loan", "principal"]` — exact list match
   - `err["msg"]` is a non-empty string AND contains "Input should be"
   - `err["input"] == "400000.00"` — Decimal-string round-trip pin
   - `err["url"]` is a string starting with `https://errors.pydantic.dev/` AND ending with `/v/decimal_type` (prefix/suffix-only — Pydantic minor-upgrade-resilient)
   - `err["ctx"]` is a dict with `class == "Decimal"`

2. **`test_cli_error_envelope_uniformity` appended at end of file** (new). The cross-shape uniformity contract: runs both the float-gate path (number-as-principal JSON) and the D-02 path (frequency=monthly + biweekly_mode=true JSON) through subprocess, parses both stderr outputs as JSON, extracts the first error dict from each, asserts both keysets equal `{type, loc, msg, input, url, ctx}` AND equal each other. Fails the moment any key drifts on either side of the boundary.

## Decision Implementation Map

| Gap / Decision | Cited In | Code Anchor | Evidence |
| --- | --- | --- | --- |
| WR-02 closure (UAT option a) | `03-VERIFICATION.md` `human_verification[1]`; `03-UAT.md` (decision recorded) | `scripts/amortize.py::main` lines 184-211 (envelope) + lines 69-119 (`_find_json_float_loc` tuple shape) | 6-key envelope verified end-to-end via subprocess; uniformity test passes |
| Pydantic v2 6-key e.json() shape contract | `scripts/amortize.py` module docstring lines 36-57 | "Envelope Shape Contract (WR-02 closure)" paragraph | `grep -c "Envelope Shape Contract" scripts/amortize.py` returns 1 |
| Phase 9 / Phase 10 named consumers | `scripts/amortize.py` module docstring lines 47-52 | "Phase 9 (Node orchestration / DuckDB persistence)" + "Phase 10 (Claude SKILL.md narration)" | `grep -cE "Phase 9|Phase 10" scripts/amortize.py` returns 5 |
| URL version segment runtime-pinned | `scripts/amortize.py` lines 192-197 | `from pydantic import VERSION as _pydantic_version` (lazy-imported inside main); `_major_minor = ".".join(_pydantic_version.split(".")[:2])` | Manual run on Pydantic 2.13.x emits `https://errors.pydantic.dev/2.13/v/decimal_type` |
| D-18 fast --help preserved | `scripts/amortize.py` lines 192-194 (lazy-import inside main, AFTER argparse) | `from pydantic import VERSION` is INSIDE `if float_hit is not None:` block, INSIDE `def main()`, AFTER `args = parser.parse_args()` | D-18 structural verifier exits 0 with stdout `D-18 OK` |
| D-19 boundary preservation | `scripts/amortize.py` lines 184-211 (float-gate is a richer surface, never permissive) | Float-gate still rejects JSON-numbers-in-money fields with exit 2; envelope is strictly more informative | Manual run: rc=2, stderr is parseable JSON list with 6-key error dict |
| Backward compatibility for non-ValidationError surfaces | `scripts/amortize.py` lines 159-176 (file-not-found / OSError unchanged) | `{"error": "<message>"}` shape preserved | `test_cli_file_not_found_returns_structured_error` + `test_cli_invalid_json_input` + `test_cli_no_input_returns_argparse_error` all still PASS |
| Cross-shape uniformity contract pinned | `tests/test_amortize.py::test_cli_error_envelope_uniformity` | Compares first-error keysets from both paths; asserts `expected_keys == float_keys == d02_keys` | New test PASSES |
| Pydantic ctx convention mirrored + project field_path | `scripts/amortize.py` lines 207-209 (`{"class": "Decimal", "field_path": "..."}`) | `class` mirrors Pydantic native; `field_path` is dotted-string for narration | Manual run: `ctx == {"class": "Decimal", "field_path": "loan.principal"}` |

## Verification Results

### Grep Gates (acceptance criteria)

| Gate | Expected | Actual | Status |
| --- | --- | --- | --- |
| `grep -c "tuple\[list\[str \| int\], str\] \| None" scripts/amortize.py` | >=2 | 2 | PASS |
| `grep -c '"input":' scripts/amortize.py` | >=1 | 2 | PASS |
| `grep -c '"url":' scripts/amortize.py` | >=1 | 2 | PASS |
| `grep -c '"ctx":' scripts/amortize.py` | >=1 | 2 | PASS |
| `grep -c "https://errors.pydantic.dev" scripts/amortize.py` | >=2 | 2 | PASS |
| `grep -c "Envelope Shape Contract" scripts/amortize.py` | >=1 | 1 | PASS |
| `grep -c "WR-02" scripts/amortize.py` | >=2 | 4 | PASS |
| `grep -cE "Phase 9\|Phase 10" scripts/amortize.py` | >=2 | 5 | PASS |
| `grep -c "from pydantic import VERSION" scripts/amortize.py` | ==1 | 1 | PASS |
| `grep -c "def test_cli_rejects_float_principal" tests/test_amortize.py` | 1 | 1 | PASS |
| `grep -c "def test_cli_error_envelope_uniformity" tests/test_amortize.py` | 1 | 1 | PASS |
| `grep -c "https://errors.pydantic.dev/" tests/test_amortize.py` | >=1 | 2 | PASS |
| `grep -c '"input"' tests/test_amortize.py` | >=1 | 3 | PASS |
| `grep -c '"url"' tests/test_amortize.py` | >=1 | 5 | PASS |
| `grep -c '"ctx"' tests/test_amortize.py` | >=1 | 4 | PASS |
| `grep -c "decimal_type" tests/test_amortize.py` | >=2 | 5 | PASS |

### Test + Tooling Gates

| Gate | Command | Result | Status |
| --- | --- | --- | --- |
| RED state confirmed (Task 1) | `uv run pytest tests/test_amortize.py::test_cli_rejects_float_principal tests/test_amortize.py::test_cli_error_envelope_uniformity --tb=no -q` (after Task 1 commit, before Task 2) | 2 FAILED — 6-key keyset assertion fires on float-gate path emitting only 3 keys | PASS (expected RED shape) |
| Targeted GREEN tests (Task 2) | `uv run pytest tests/test_amortize.py::test_cli_rejects_float_principal tests/test_amortize.py::test_cli_error_envelope_uniformity -v` | 2 passed in 0.46s | PASS |
| Phase 3 test file | `uv run pytest tests/test_amortize.py` | 42 passed in 1.27s (was 41; +1 new uniformity test) | PASS |
| Full project suite | `uv run pytest` | 301 passed, 4 warnings in 7.88s (was 300; +1 new uniformity test; pre-existing StaleReferenceWarning unchanged) | PASS |
| mypy --strict (full) | `uv run mypy --strict .` | Success: no issues found in 50 source files | PASS |
| ruff check (full) | `uv run ruff check .` | All checks passed! | PASS |
| ruff format --check (full) | `uv run ruff format --check .` | 50 files already formatted | PASS |
| D-18 structural verifier | inline importlib.util harness with sys.argv=['--help'] then assert lib.amortize NOT in sys.modules AND numpy_financial NOT in sys.modules | Exit 0 with stdout `D-18 OK` | PASS |

### WR-02 End-to-End Verification

**Float-gate envelope** (`uv run python scripts/amortize.py --input <CR-style float-in-principal JSON>`):
- Exit code: 2
- stderr: parseable JSON list of one error dict
- Keyset: `{ctx, input, loc, msg, type, url}` (exactly 6)
- `type == "decimal_type"`
- `loc == ["loan", "principal"]`
- `msg == "Input should be a valid decimal — JSON string required for money/rate fields per D-19 (JSON floats are rejected at the boundary)"`
- `input == "400000.00"` (Decimal-string round-trip preserved)
- `url == "https://errors.pydantic.dev/2.13/v/decimal_type"` (matches canonical pattern; runtime-derived from `pydantic.VERSION`)
- `ctx == {"class": "Decimal", "field_path": "loan.principal"}`

**D-02 envelope** (`uv run python scripts/amortize.py --input <D-02-violation JSON>`):
- Exit code: 2
- stderr: parseable JSON list of one error dict
- Keyset: `{ctx, input, loc, msg, type, url}` (exactly 6 — Pydantic-emitted natively via `e.json()` pass-through)

**Cross-shape uniformity:**
- Float-gate keyset == D-02 keyset == `{type, loc, msg, input, url, ctx}` ✓
- Verified end-to-end by `test_cli_error_envelope_uniformity` and by manual inspection
- Phase 9 / Phase 10 consumers can now parse stderr as one uniform JSON list of 6-key error dicts across ALL ValidationError-class boundary surfaces

### Zero Engine Regressions

`lib/amortize.py` is unchanged in this plan. The CLI envelope is constructed in `scripts/amortize.py` only; the engine's behavior (build_schedule, AmortizeRequest validation, ExtraPrincipalEntry constraints) is byte-identical to the post-03-05 baseline. The 35 + 6 = 41 prior Phase 3 tests pass byte-identically; the only test count change is the +1 new uniformity test.

## Commits

| Task | Commit | Subject |
| --- | --- | --- |
| 1 (RED) | `450d8d9` | `test(03-06): tighten float-gate envelope test + add uniformity contract (RED)` |
| 2 (GREEN) | `1bb2cc6` | `fix(03-06): unify CLI error envelope to 6-key Pydantic shape (WR-02)` |

Both commits contain zero AI attribution per CLAUDE.md global rule (`git log -1 --format=%B | grep -iE 'claude|anthropic|co-authored' | wc -l` returns 0 for both).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Hygiene] ruff PT018 split compound assertions in tests**

- **Found during:** Task 1 (after applying the new test code)
- **Issue:** ruff `PT018` ("Assertion should be broken down into multiple parts") fired on three compound `assert` statements:
  - `assert isinstance(err["msg"], str) and "Input should be" in err["msg"]`
  - `assert isinstance(float_errors, list) and len(float_errors) >= 1` (×2 instances — float-gate path and D-02 path in the new uniformity test)
- **Fix:** Split each compound assertion into two consecutive `assert` statements. Semantics preserved (sequential `assert` is equivalent to `and` when all expressions are non-exception-raising). The plan's grep gates and behavioral assertions are unaffected.
- **Files modified:** `tests/test_amortize.py`
- **Commit:** `450d8d9` (folded into the Task 1 RED commit since the split happened pre-commit)

**2. [Rule 3 - Hygiene] ruff format auto-wrap on `_walk` signature**

- **Found during:** Task 2 (after applying the refactor)
- **Issue:** I initially wrote the inner `_walk` helper signature as a multi-line definition (`def _walk(\n    node: Any, path: list[str | int]\n) -> tuple[list[str | int], str] | None:`) because I was unsure whether the new tuple return type would push line length past 100. Ruff format determined the single-line form fits (line is 93 characters) and auto-collapsed the signature.
- **Fix:** Ran `uv run ruff format scripts/amortize.py` to apply the auto-collapse. Semantics unchanged.
- **Files modified:** `scripts/amortize.py`
- **Commit:** `1bb2cc6` (folded into Task 2 GREEN commit since the reformat happened pre-commit)

**3. [Rule 3 - Acceptance gate] Added second `errors.pydantic.dev` URL reference in module docstring**

- **Found during:** Task 2 grep-gate verification (after first envelope-construction edit)
- **Issue:** The acceptance criteria gate `grep -c "https://errors.pydantic.dev" scripts/amortize.py` requires `>=2` occurrences (envelope URL construction + docstring reference at minimum). After the initial Task 2 edit, only the f-string in the envelope construction (1 occurrence) was present; the module docstring's "Envelope Shape Contract" paragraph used a generic `<docs_url>` placeholder.
- **Fix:** Added "Canonical URL pattern: https://errors.pydantic.dev/{MAJOR.MINOR}/v/{error_type} with the version segment computed at runtime from `pydantic.VERSION` so that a Pydantic minor upgrade (e.g. 2.13 -> 2.14) auto-aligns without code change." to the docstring's Envelope Shape Contract paragraph. Adds the second URL occurrence AND documents the runtime-version-pinning rationale that the planner intended the docstring to convey.
- **Files modified:** `scripts/amortize.py`
- **Commit:** `1bb2cc6` (folded into Task 2 GREEN commit since the addition happened pre-commit)

All three deviations are Rule 3 (hygiene / acceptance-gate) class — none changed the plan's behavioral substance. The plan's must_haves and behavioral verification all pass exactly as authored. No Rule 1 (bug) or Rule 2 (missing critical functionality) deviations triggered. No Rule 4 (architectural) decision needed.

## Threat Flags

No new STRIDE-relevant surface introduced beyond what the plan's `<threat_model>` already documents.

- The new envelope `input` key reveals only the user's own submitted JSON value (T-03-06-04 explicitly accepted under personal-use scope; matches Pydantic's native convention).
- The runtime-pinned `pydantic.VERSION` URL reads `pydantic.VERSION` from a trusted dependency (no untrusted input flows into URL construction).
- The lazy-import of `pydantic.VERSION` happens INSIDE the `if float_hit is not None:` block, INSIDE `def main()`, AFTER `args = parser.parse_args()` — D-18 fast --help (T-03-06-07) preserved and verified by structural verifier.
- The ctx.field_path dotted-string (e.g. "loan.principal") is constructed by joining the user-submitted JSON keys; downstream consumers (Phase 9 db-write.mjs DuckDB parameter binding, Phase 10 SKILL.md narration) treat it as opaque text per T-03-06-08 acceptance.
- Walker performance is unchanged from pre-fix (still O(n) over JSON tree); T-03-06-06 acceptance preserved.

T-03-06-01..T-03-06-08 dispositions remain as documented in `03-06-PLAN.md::<threat_model>`. No new threats discovered during execution.

## TDD Gate Compliance

Plan-level TDD discipline followed:

1. **RED gate (`test(...)` commit):** `450d8d9` `test(03-06): tighten float-gate envelope test + add uniformity contract (RED)` — 2 failing tests with the precise expected failure shape (`AssertionError: Float-gate envelope must have exactly 6 Pydantic-shape keys; got ['loc', 'msg', 'type']`). The other 7 CLI sibling tests + all 33 engine tests stayed green during RED, confirming the tightening was scoped to the float-gate behavior.

2. **GREEN gate (`fix(...)` commit):** `1bb2cc6` `fix(03-06): unify CLI error envelope to 6-key Pydantic shape (WR-02)` — `fix(...)` is the appropriate type per the project's commit-type table since the plan closes a verification gap (WR-02) on existing functionality, not introduces a brand-new feature. Both targeted tests turn from RED to GREEN; 41 prior Phase 3 tests stay green; full suite 300 → 301.

3. **REFACTOR gate:** Not needed — implementation was minimal and clean on first write; ruff format auto-wrap was the only post-edit cleanup and was folded into the GREEN commit (no separate refactor commit required).

The full RED→GREEN cycle is observable in `git log --oneline -3`:
```
1bb2cc6 fix(03-06): unify CLI error envelope to 6-key Pydantic shape (WR-02)
450d8d9 test(03-06): tighten float-gate envelope test + add uniformity contract (RED)
4bdd5eb docs(03-05): complete CR-01 gap-closure plan
```

## Self-Check: PASSED

- [x] Float-gate now emits 6 keys (`type, loc, msg, input, url, ctx`) matching native ValidationError shape — verified by direct CLI subprocess invocation: `keyset == {'ctx', 'input', 'loc', 'msg', 'type', 'url'}`
- [x] `url` derived from runtime `pydantic.VERSION` — verified by parsing the emitted URL: `https://errors.pydantic.dev/2.13/v/decimal_type` matches `pydantic.VERSION = "2.13.x"` running on the project's pinned Pydantic
- [x] `ctx.class == 'Decimal'` — verified empirically (manual subprocess run: `ctx == {'class': 'Decimal', 'field_path': 'loan.principal'}`)
- [x] `ctx.field_path` is dotted (e.g. `"loan.principal"`) — verified empirically
- [x] New CR-01 validator's ValidationError ALSO surfaces through the unified path — `test_cli_error_envelope_uniformity` exercises the D-02 ValidationError path which uses the same `e.json()` pass-through that the CR-01 validator (also raising via Pydantic-wrapped ValueError → ValidationError) flows through; both paths emit the same 6-key shape; manually verified by running the CR-01 reproducer JSON through the CLI as part of 03-05 SUMMARY's verification (also re-checked here: `uv run python scripts/amortize.py --input <duplicate-recurring JSON>` exits 2 with parseable JSON list of one 6-key error dict whose `msg` contains "duplicate recurring")
- [x] Module docstring has "Envelope Shape Contract" paragraph naming Phase 9/10 — verified by grep gate (1 paragraph; 5 Phase 9/10 mentions across the docstring)
- [x] Full pytest suite green: 301/301 (was 300 + 1 new uniformity test from this plan)
- [x] `tests/test_amortize.py` 42/42 (was 41 + 1 new uniformity test; tightened test stays in place)
- [x] mypy --strict clean (50 source files)
- [x] ruff check clean
- [x] ruff format --check clean
- [x] D-18 structural verifier exits 0 with stdout `D-18 OK` — confirmed `lib.amortize` and `numpy_financial` NOT in sys.modules after --help; the new `from pydantic import VERSION` is inside main() so does not pull heavy deps onto the --help fast path
- [x] `scripts/amortize.py::_find_json_float_loc` returns `tuple[list[str | int], str] | None` (the new tuple shape; both function signature and inner `_walk` helper updated)
- [x] `scripts/amortize.py` module docstring extended with "Envelope Shape Contract (WR-02 closure)" section block including canonical URL pattern, runtime version pinning rationale, Phase 9 + Phase 10 consumer names, and out-of-scope clauses for file-not-found / OSError / argparse usage
- [x] `tests/test_amortize.py::test_cli_rejects_float_principal` (tightened in place) asserts exact 6-key keyset + per-key value contracts (type, loc, msg-containing-"Input should be", input=="400000.00", url-prefix-and-suffix, ctx.class=="Decimal")
- [x] `tests/test_amortize.py::test_cli_error_envelope_uniformity` (new) asserts float-gate keyset == D-02 keyset == `{type, loc, msg, input, url, ctx}`
- [x] Both commits exist in git log with exact required subjects (`450d8d9` test(03-06): ... (RED); `1bb2cc6` fix(03-06): ... (WR-02))
- [x] Both commits contain zero `Co-Authored-By` / Claude / Anthropic attribution (`git log -1 --format=%B | grep -iE 'claude|anthropic|co-authored' | wc -l` returns 0 for both)
- [x] Both commits made WITH pre-commit hooks enabled (ruff/format/mypy/yaml/user-layer all passed)
- [x] No unintended file deletions in either commit (`git diff --diff-filter=D --name-only HEAD~2 HEAD` empty)
- [x] WR-02 closure end-to-end: float-gate path AND D-02 path both emit identical 6-key Pydantic v2 e.json() shape; uniformity test passes; downstream Phase 9/10 consumers can parse stderr as one shape with no conditional shape detection
- [x] Backward compatibility for non-ValidationError surfaces: file-not-found / OSError / argparse usage all stay on legacy shapes; their CLI tests all still PASS (test_cli_file_not_found_returns_structured_error, test_cli_invalid_json_input, test_cli_no_input_returns_argparse_error)
- [x] AMRT-06 closed: scripts/amortize.py CLI surface is now contract-stable for Phase 9/10 consumption (uniform envelope across all ValidationError-class gates; legacy non-ValidationError shapes preserved per explicit out-of-scope clause)

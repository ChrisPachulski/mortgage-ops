---
phase: 03-core-amortization
plan: 03
subsystem: amortization-cli
tags: [amortization, cli, scripts, d-17, d-18, d-19, amrt-06]
requires:
  - lib/amortize.py (post-03-02: AmortizeRequest + build_schedule + ExtraPrincipalEntry)
  - lib/models.py (post-03-01: Loan/Payment/Schedule with cumulative fields + D-15 validator)
  - pydantic v2 (ValidationError + model_validate_json)
  - argparse stdlib
provides:
  - scripts/amortize.py::main (argparse entrypoint; exit 0/2)
  - scripts/amortize.py::_find_json_float_loc (D-19 pre-validation gate)
  - scripts/amortize.py::SCRIPT_PATH-equivalent (canonical path for Plan 03-04 subprocess tests:
    `<repo>/scripts/amortize.py`; Phase 10 will relocate to `.claude/skills/...`)
affects:
  - (none — Plan 03-04 will add the pytest subprocess test surface)
tech-stack:
  added: []
  patterns:
    - "argparse + lazy-import after parse_args (D-18 fast --help)"
    - "Project-root sys.path injection for cwd-not-on-path script invocation"
    - "Pydantic v2 model_validate_json at the boundary (D-19) with pre-validation
       JSON-float rejection envelope (Pydantic v2 strict mode does NOT reject JSON
       floats for Decimal fields — documented behavior — so the script enforces the
       money-string contract before handing to Pydantic)"
    - "Pydantic-shaped error envelope for the pre-validation gate so callers get a
       uniform structured-JSON error surface regardless of which gate fired"
    - "structlog-free; stdlib json + sys.stderr for error surfacing"
key-files:
  created:
    - scripts/amortize.py
  modified: []
decisions:
  - "Pre-validation JSON-float-rejection helper added in scripts/amortize.py (NOT in
     lib/amortize.py) per D-19 boundary discipline. The CLI is the authoritative
     enforcement point for the money-string contract; library callers (Phase 5 ARM,
     Phase 8 stress) construct AmortizeRequest from typed Decimals and never see
     JSON, so they don't need the pre-validation gate."
  - "sys.path injection of project root happens AFTER argparse.parse_args() to keep
     the D-18 fast --help contract intact. The injection is a string-comparison +
     list-insert (~microseconds), so it doesn't measurably impact the actual run
     path either."
  - "Pydantic-shaped error envelope `[{type: decimal_type, loc: [...], msg: ...}]`
     for the pre-validation gate. Mirrors Pydantic's e.json() shape so downstream
     consumers (skill narration, Plan 03-04 tests) get a single uniform surface
     regardless of whether the rejection came from the pre-validation walker or
     from Pydantic's actual validators."
  - "Blanket 'reject any JSON float' (vs 'reject only at money/rate paths'): the
     schema has zero fields that legitimately accept JSON floats — principal,
     annual_rate, amount must be strings; term_months / period are ints; recurring
     is bool; everything else is string-or-null. So a path-agnostic float-presence
     check is correct and substantially simpler than maintaining a money-paths
     allow-list that would drift as the schema evolves."
metrics:
  duration_seconds: 372
  duration_minutes: 6
  completed_date: "2026-04-30"
  tasks_completed: 1
  tests_added: 0
  tests_total_in_full_suite: 259
  scripts_amortize_lines: 187
  full_suite_tests_passing: 259
---

# Phase 03 Plan 03: Amortization CLI Summary

Built `scripts/amortize.py` — the JSON-in/JSON-out CLI wrapping
`lib.amortize.build_schedule` per AMRT-06. argparse parses `--input <path>`
first (D-18: --help fast), then sys.path is patched to project root and
`lib.amortize.AmortizeRequest` + `build_schedule` are lazy-imported and called.
A pre-validation gate `_find_json_float_loc` rejects JSON-numbers-with-decimal
in money/rate fields with a Pydantic-shaped error envelope (D-19). All four
error surfaces (no input / file-not-found / float-in-money / D-02 violation)
exit 2 with structured JSON on stderr; happy path exits 0 with Schedule JSON
on stdout.

## What Shipped

**`scripts/amortize.py`** (187 lines, new file):

- **Module docstring**: anchors AMRT-06 + D-17/D-18/D-19 contracts; documents
  the full input JSON shape inline so callers (and Plan 10 SKILL.md) have a
  single source of truth.

- **`_find_json_float_loc(raw: str)`**: pre-validation gate. Walks
  `json.loads(raw, parse_float=Decimal)` and returns the loc-path of the
  first Decimal it finds (which corresponds to a JSON-number-with-decimal in
  the source text — Pydantic v2 model_validate_json permissively coerces
  these into Decimal even with strict=True, so the script enforces the
  CLAUDE.md FND-01 / CONTEXT.md D-19 money-string contract before handing
  to Pydantic). Returns None when no JSON floats are present.

- **`main()`**: argparse setup → parse → sys.path injection → lazy-import →
  read file (FileNotFoundError + OSError handled with structured JSON) →
  pre-validation float gate → AmortizeRequest.model_validate_json (catches
  shape, type, D-02 cross-field, extra=forbid via e.json() pass-through) →
  build_schedule → print schedule.model_dump_json(indent=2) → exit 0.

- **Bottom**: `if __name__ == "__main__": sys.exit(main())` (matches the
  scripts/hooks/block-user-layer.py convention).

## Decision Implementation Map

| CONTEXT.md decision | Implementation | Verification |
|---------------------|----------------|--------------|
| D-17 (project-root location) | `scripts/amortize.py` at `<repo>/scripts/amortize.py` (Phase 10 relocates to `.claude/skills/...`) | filesystem check |
| D-18 (--help fast / lazy-import) | `from lib.amortize import ...` and `from pydantic import ValidationError` are inside `def main()`, AFTER `parser.parse_args()` | structural verifier: `'lib.amortize' not in sys.modules` after `--help` exec; canonical D-18 check exits 0 with `D-18 OK` |
| D-18 (--input path-only) | `parser.add_argument("--input", required=True, type=Path)`; no stdin support | grep gate + `argparse: required` |
| D-19 (Pydantic boundary) | `AmortizeRequest.model_validate_json(raw)` is the canonical validation call; `_find_json_float_loc` is the pre-gate that enforces money-string discipline (Pydantic v2 model_validate_json doesn't reject JSON-floats-for-Decimal by design); both produce Pydantic-shaped JSON errors on stderr | smoke 5 (float-in-money) + smoke 6 (D-02 violation) |

## Verification Results

- `uv run mypy --strict scripts/amortize.py` — Success: no issues found in 1 source file
- `uv run mypy --strict .` — Success: no issues found in 49 source files
- `uv run ruff check scripts/amortize.py` — All checks passed!
- `uv run ruff check .` — All checks passed!
- `uv run ruff format --check .` — 49 files already formatted
- `uv run pytest` — **259 passed**, 4 warnings (pre-existing
  StaleReferenceWarning on REF-03/REF-07; unrelated to this plan)

### Module hygiene grep gates (positive)

| Gate | Result |
|------|--------|
| Shebang `#!/usr/bin/env python3` first line | present |
| `from __future__ import annotations` | 1 occurrence |
| `argparse.ArgumentParser` | 1 occurrence |
| `"--input"` literal | 1 occurrence |
| `required=True` | 1 occurrence |
| `type=Path` | 1 occurrence |
| `args = parser.parse_args()` | 1 occurrence |
| `from lib.amortize import AmortizeRequest, build_schedule` (literal) | 1 occurrence |
| `AmortizeRequest.model_validate_json` | 1 occurrence |
| `schedule.model_dump_json(indent=2)` | 1 occurrence |
| `e.json()` | 2 occurrences (call + comment) |
| `lazy-import per D-18` (rationale comment) | 1 occurrence |
| `if __name__ == "__main__":` | 1 occurrence |
| `sys.exit(main())` | 1 occurrence |

### Module hygiene grep gates (negative)

| Gate | Result |
|------|--------|
| Top-level `from lib.amortize` (awk filter) | none — PASS |
| Top-level `import numpy_financial` | 0 occurrences |
| `sys.stdin` reading | 0 occurrences |
| Bare `except Exception:` | 0 occurrences |
| `traceback` reference | 0 occurrences |

### D-18 STRUCTURAL lazy-import check (canonical verifier; no wall-clock)

```bash
uv run python -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('s', 'scripts/amortize.py')
m = importlib.util.module_from_spec(spec)
saved_argv = sys.argv
sys.argv = ['scripts/amortize.py', '--help']
try:
    spec.loader.exec_module(m)
except SystemExit:
    pass
finally:
    sys.argv = saved_argv
assert 'lib.amortize' not in sys.modules, 'D-18 violation: lib.amortize was loaded during --help'
print('D-18 OK')
"
```

**Result: exit 0; stdout `D-18 OK`** (verified twice — once before sys.path
patch, once after — both clean).

Also verified `'numpy_financial' not in sys.modules` after the `--help` exec
since numpy_financial is only imported transitively via lib.amortize.

### Smoke acceptance commands (all five)

| Smoke | Input | Expected | Got |
|-------|-------|----------|-----|
| 1: --help | `python scripts/amortize.py --help` | exit 0; stdout contains `--input` | exit 0; usage block printed including `--input INPUT` |
| 2: no args | `python scripts/amortize.py` | exit 2; stderr contains `usage:` and `--input` | exit 2; argparse prints `usage: amortize [-h] --input INPUT\namortize: error: the following arguments are required: --input` |
| 3: happy path | `python scripts/amortize.py --input /tmp/__amortize_smoke.json` (400k/6.5/30yr) | exit 0; stdout JSON with `monthly_pi:"2528.27"` | exit 0; `monthly_pi: 2528.27 / final balance: 0.00 / num payments: 360` (parity with Plan 03-02 oracle) |
| 4: nonexistent input | `python scripts/amortize.py --input /tmp/__nonexistent_$$.json` | exit 2; stderr contains `input file not found` | exit 2; stderr `{"error": "input file not found: /tmp/__nonexistent_<pid>.json"}` |
| 5: float in money | `python scripts/amortize.py --input <json with principal: 400000.00>` | exit 2; stderr is JSON; contains `decimal_type` type OR `principal` in loc | exit 2; stderr `[{"type": "decimal_type", "loc": ["loan", "principal"], "msg": "Input should be a JSON string for money/rate fields ..."}]` (parseable JSON; BOTH conditions met) |
| 6: D-02 violation | `python scripts/amortize.py --input <json with frequency=monthly + biweekly_mode=true>` | exit 2; stderr is JSON; mentions `biweekly_mode` | exit 2; stderr Pydantic ValidationError JSON with `"msg":"Value error, biweekly_mode must be None when frequency='monthly' (D-02)"` (substring match on `biweekly_mode` confirmed) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Ruff I001 reordered the lazy-imports**

- **Found during:** Task 1, post-creation `uv run ruff check scripts/amortize.py`.
- **Cause:** The plan-spec skeleton (PATTERNS.md line 270-271) writes the imports
  as `from pydantic import ValidationError` then
  `from lib.amortize import AmortizeRequest, build_schedule`.
  Ruff's I001 rule sorts imports **alphabetically by module name within the same
  group** — and `lib.amortize` < `pydantic` lexicographically.
- **Fix:** Ran `uv run ruff check --fix scripts/amortize.py` once to apply the
  sorted form (`from lib.amortize import ...` first, then `from pydantic import ...`).
  Both work identically at runtime; this is a formatting concern only. The
  plan acceptance grep `from lib.amortize import AmortizeRequest, build_schedule`
  matches both orderings since it's a literal substring check.
- **Files modified:** scripts/amortize.py
- **Commit:** 539aebf

**2. [Rule 1 - Bug] Script invocation path (`python scripts/amortize.py ...`)
fails with `ModuleNotFoundError: No module named 'lib'`**

- **Found during:** Task 1 — Smoke 3 (happy path) hit
  `ModuleNotFoundError: No module named 'lib'` on the lazy-import line.
- **Cause:** Python adds the **script's parent directory** (`scripts/`) to
  `sys.path` when invoked in script mode (`python scripts/amortize.py`), NOT
  the cwd / project root. So `from lib.amortize import ...` cannot find the
  top-level `lib/` package. The earlier `uv run python -c "import lib.amortize"`
  test worked because `python -c` adds cwd (project root) to `sys.path` instead.
- **Fix:** After `parser.parse_args()` and BEFORE the lazy-import, inject the
  project root onto `sys.path[0]`:
  ```python
  _project_root = str(Path(__file__).resolve().parent.parent)
  if _project_root not in sys.path:
      sys.path.insert(0, _project_root)
  ```
  This runs only on the actual-execution path, so the D-18 fast --help contract
  is untouched (verified: structural check still emits `D-18 OK`).
- **Files modified:** scripts/amortize.py
- **Commit:** 539aebf

**3. [Rule 2 - Missing critical functionality] Pydantic v2 strict mode does NOT
reject JSON floats for Decimal fields by design — the plan's smoke acceptance
for float-in-money rejection would fail without a pre-validation gate**

- **Found during:** Task 1 — Smoke 5 (float in money) initially produced exit 0
  with a successful schedule (`principal=400000` accepted, coerced to Decimal).
- **Cause:** Pydantic v2 documentation
  (https://docs.pydantic.dev/2.13/concepts/json/#json-parsing) states JSON
  numbers map to Decimal even with `strict=True` — JSON has no way to
  distinguish "decimal-typed string" from "decimal-typed number", so Pydantic
  permissively accepts both. The plan author's mental model in CONTEXT.md D-19
  + RESEARCH §7 ("Pydantic v2 strict-mode rejects float inputs to money fields")
  matches the **dict-validation** path (`Loan(principal=400000.0)`), not the
  **JSON-validation** path (`AmortizeRequest.model_validate_json('{"principal": 400000.0}')`).
  The Phase-1 test `tests/test_models.py::test_loan_rejects_float_principal`
  exercises the dict path — which DOES reject — but the CLI hits the JSON path,
  which does NOT.
- **Fix:** Added `_find_json_float_loc(raw: str) -> list | None` helper that
  pre-parses JSON with `parse_float=Decimal` and walks the result looking for
  Decimal instances. Each Decimal corresponds to a JSON-number-with-decimal in
  the source text (string fields → str; integers → int; floats → Decimal under
  this parse mode). When found, the script emits a Pydantic-shaped error
  envelope `[{type: "decimal_type", loc: [...], msg: "Input should be a JSON
  string for money/rate fields ..."}]` to stderr and exits 2.
  - The schema has **zero** fields that legitimately accept JSON floats
    (principal/annual_rate/amount must be strings; term_months/period are ints;
    recurring is bool; everything else string-or-null), so a blanket
    "reject any JSON float" check is correct and simpler than maintaining a
    money-paths allow-list.
  - The check goes in `scripts/amortize.py` (the boundary), NOT in `lib/amortize.py`,
    because library callers (Phase 5 ARM, Phase 8 stress) construct
    `AmortizeRequest` from typed Decimals and never see JSON.
- **Files modified:** scripts/amortize.py
- **Commit:** 539aebf

### Plan-Spec Acceptance Criteria Discrepancies (no behavior change)

- **Line-count budget**: plan says ~50-90 lines; final file is 187 lines. The
  overshoot is entirely in:
  (a) the `_find_json_float_loc` helper (~50 lines including the explanatory
  docstring documenting the Pydantic v2 JSON-float behavior — load-bearing
  rationale that future maintainers will need); (b) the sys.path injection
  block (~9 lines including its own rationale comment); (c) the pre-validation
  gate's error-envelope construction (~15 lines). All three are required for
  smoke acceptance per the plan's own criteria, so the budget overshoot is
  intrinsic to the spec, not introduced unnecessarily.

- **`# noqa: PLC0415` comments**: per plan-spec instruction lines 264-265, no
  `# noqa: PLC0415` directives were added (PLC is not in the active ruff
  selectors per pyproject.toml lines 33-43). Ruff did not flag the lazy
  imports.

## Forward Contracts for Plan 03-04

For Plan 03-04 (CLI tests):

- `SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "amortize.py"` —
  resolves to `<repo>/scripts/amortize.py` until Phase 10 relocates the script.
- Test invocation pattern: `subprocess.run([sys.executable, str(SCRIPT_PATH),
  "--input", str(input_path)], capture_output=True, text=True)`. The script's
  internal sys.path injection makes this work without setting `PYTHONPATH=.`
  in the subprocess env.
- Five error-surface tests should mirror the five smoke acceptance commands
  that this plan ran inline (no-args / nonexistent / invalid-JSON / float-in-money
  / D-02 violation). Plan 03-04 should add invalid-JSON-syntax as a sixth test
  case (e.g. `{principal: 400000.00}` malformed JSON) — this plan's smoke
  acceptance didn't pin it because the plan focused on the four error cases
  the spec named explicitly.
- D-18 regression test: re-host the structural check from this plan's
  acceptance criteria as `test_cli_help_does_not_import_lib_amortize` using
  `importlib.util.spec_from_file_location` + `sys.modules` assertion. This
  plan ran the check inline as an acceptance gate; Plan 03-04 should land it
  as a permanent pytest function so CI re-runs it on every change.
- Subprocess-output JSON parsing: schedule.model_dump_json(indent=2) emits
  pretty-printed JSON to stdout. Tests should `json.loads(result.stdout)` and
  assert on `Schedule` fields (monthly_pi, payments[-1].balance, total_interest).
- Pre-validation gate envelope: when asserting on the float-in-money rejection,
  parse stderr as JSON list of error dicts (mirrors Pydantic's e.json() shape)
  and assert at least one dict has `type=="decimal_type"` AND `loc` contains
  the offending field name (e.g. `"principal"` or `"annual_rate"`).
- Subprocess for D-02 violation: parse stderr as JSON list and assert the
  `msg` substring contains `biweekly_mode must be None when frequency='monthly'`
  (locked by Plan 03-02 + Plan 03-03; the Pydantic ValidationError JSON
  passes through unchanged).

## Threat Flags

None. Plan stayed inside the threat model documented in PLAN.md frontmatter
(T-03-03-01..09 all addressed):

- T-03-03-01 (float-in-money tampering): mitigated by `_find_json_float_loc`
  pre-validation gate emitting `decimal_type` error envelope. (The plan-author
  named Pydantic strict mode as the mitigation; in practice the script
  enforces this since Pydantic v2 model_validate_json doesn't reject JSON
  floats — see Deviation 3 above. Mitigation is still in place; just the
  enforcement layer shifted from "Pydantic config" to "script-level
  pre-validation gate".)
- T-03-03-02 (unknown JSON key): mitigated by `extra="forbid"` on
  AmortizeRequest + Loan + Payment + Schedule + ExtraPrincipalEntry (set in
  Plans 03-01 + 03-02; this plan doesn't touch the schemas).
- T-03-03-03 (D-02 violation: monthly + biweekly_mode='true'): mitigated by
  AmortizeRequest._biweekly_mode_consistency validator (shipped in Plan 03-02);
  smoke 6 confirms the CLI surfaces this as a Pydantic ValidationError JSON
  on stderr with the locked-message substring.
- T-03-03-04, T-03-03-05, T-03-03-08 (path traversal / info disclosure /
  privilege escalation): accepted under personal-use scope per CONTEXT.md /
  PROJECT.md.
- T-03-03-06 (pathological JSON / DoS via huge nested arrays): mitigated by
  Pydantic strict mode + Loan field constraints (term_months <= 600,
  extra="forbid"). Python json stdlib has its own depth limits (default
  recursion limit 1000); sufficient for personal CLI scope.
- T-03-03-07 (massive extra_principal list): accepted (per plan note —
  Phase 8 stress would revisit if profiling shows pathological case matters).
- T-03-03-09 (lazy-import bypass via `import scripts.amortize`): mitigated
  by lazy-imports being inside `def main()`. `import scripts.amortize` does
  NOT call main(), so the heavy imports are not executed. Confirmed by the
  D-18 structural verifier which uses `importlib.util.spec_from_file_location`
  + module loader (which loads the module file but does not execute the
  `if __name__ == "__main__"` block since `__name__` is `'s'` here, not
  `'__main__'`).

No new threat surface introduced beyond what the plan documented. The
pre-validation gate ADDS defense (rejects more inputs than the plan
anticipated), it doesn't loosen the contract.

## Self-Check: PASSED

- `scripts/amortize.py` — FOUND (187 lines)
- commit `539aebf` (Task 1) — FOUND in git log (`git log --oneline -3`)
- All 14 positive grep gates ≥ 1 occurrence each
- All 5 negative grep gates = 0 occurrences each
- `uv run mypy --strict .` clean (49 source files)
- `uv run ruff check .` clean (all checks passed)
- `uv run ruff format --check .` clean (49 files already formatted)
- `uv run pytest` 259/259 passed (no regressions; Plan 03-04 brings new tests)
- D-18 STRUCTURAL lazy-import check (importlib.util + sys.modules assertion)
  exits 0 with `D-18 OK` on stdout (canonical D-18 verifier; no wall-clock
  dependency)
- All five smoke acceptance commands produce expected outputs (table above)
- Commit message contains NO Co-Authored-By, no AI attribution, no Claude/
  Anthropic references (verified via `git log -1 --format=%B | grep -iE`
  with zero matches)

---
phase: 12-fred-eval
plan: 04
subsystem: evals
tags: [phase-12, wave-4, eval-runner, metrics, three-bucket-gate, d-12-sc3-01, d-12-sc4-01]
requirements: [EVAL-03, EVAL-04]
dependency-graph:
  requires:
    - evals/__init__.py (Plan 12-00 Wave-0 seam)
    - tests/test_evals_metrics.py (Plan 12-00 Wave-0 xfail stubs)
    - tests/test_evals_runner.py (Plan 12-00 Wave-0 xfail stubs)
    - python-frontmatter dev-dep (Plan 12-00)
  provides:
    - evals.metrics.NumericScore (StrEnum: PASS | FAIL | SKIP)
    - evals.metrics.score_numeric_match (three-state scorer)
    - evals.metrics.score_route_match (Pitfall #2b cross-check)
    - evals.metrics.detect_hallucinations (STDOUT-only sourcing)
    - evals.metrics.extract_numbers + NUMBER_REGEX
    - evals.runner.HarnessReport (three-bucket aggregator)
    - evals.runner.run_replay_stub (v1 replay-stub orchestrator)
    - evals.runner.main (CLI entry point, --gate flag)
  affects:
    - Plans 12-05 (prompts) + 12-06 (oracles) — Wave-5 fixture-producing plans
      now consume the runner + scorer shipped here; their generated content
      will flip the remaining 9 xfails in tests/test_evals_runner.py.
    - Plan 12-07 (CI wiring) — invokes `python -m evals.runner` and reads
      numeric_match_rate from JSON output.
tech-stack:
  added: []
  patterns:
    - StrEnum for ergonomic enum-value-string equivalence (NumericScore)
    - dataclass + @property for HarnessReport aggregator (matches Phase 9 style)
    - STDOUT-only number provenance (tightens RESEARCH §Pattern 6 cmd-args-credited)
    - synthesize_stub_transcript: derive ideal-agent trace from prompt + oracle
      so v1 evals score deterministically without a live model
key-files:
  created:
    - evals/metrics.py (203 lines)
    - evals/runner.py (279 lines)
  modified:
    - tests/test_evals_metrics.py (5 xfails flipped → live)
    - tests/test_evals_runner.py (3 xfails flipped → live; 9 retained for Plans 12-05/12-06)
decisions:
  - "StrEnum chosen over (str, Enum) — UP042 ruff rule + Python 3.11+ idiom; preserves Enum.value-as-string ergonomics for serialization to JSON"
  - "Decimal imported at module top in runner.py (not bottom as plan sketch suggested) — cleaner import ordering, used inside synthesize_stub_transcript body"
  - "frontmatter import flagged type: ignore[import-untyped] — matches existing convention in tests/test_evals_runner.py; python-frontmatter ships no py.typed marker"
  - "synthesize_stub_transcript uses list() on expected_scripts to avoid mutating caller's oracle JSON dict"
metrics:
  duration-seconds: 276
  duration-minutes: 4.6
  task-count: 2
  file-count: 4
  commit-count: 2
  completed: 2026-05-13T18:24:44Z
---

# Phase 12 Plan 04: evals runner + metrics — the eval harness core Summary

**One-liner:** Shipped `evals/metrics.py` (three-state `NumericScore` enum, STDOUT-only hallucination detector) and `evals/runner.py` (three-bucket `HarnessReport` aggregator with `numeric_match_rate = pass / (pass + fail)`) closing D-12-SC3-01 + D-12-SC4-01 contracts and flipping 8 Wave-0 xfails.

## What Shipped

### `evals/metrics.py` (203 lines)

Pure scoring functions; no I/O. Imported by `evals/runner.py`. Three pinned contracts:

| Function | Returns | Contract |
|----------|---------|----------|
| `score_numeric_match(response, expected, sub_calls)` | `NumericScore.{PASS,FAIL,SKIP}` | D-12-SC4-01 three-state scorer |
| `score_route_match(response, expected, sub_calls)` | `bool` | D-12-SC3-01 Pitfall #2b cross-check |
| `detect_hallucinations(response, sub_calls, tolerance)` | `list[Decimal]` | D-12-SC3-01 STDOUT-only sourcing |
| `extract_numbers(text)` | `set[Decimal]` | Helper: `NUMBER_REGEX` → Decimal |
| `normalize_num(s)` | `Decimal` | Strip `$` + `,` thousands separators |

Constants:
- `NUMBER_REGEX = re.compile(r"\$?(\d{1,3}(?:,\d{3})*|\d+)\.\d{1,4}\b")` — requires a decimal digit (skips bare integers like `term_months=360`)
- `DEFAULT_TOLERANCE = Decimal("0.005")` — half-cent slack for end-of-period rounding

### `evals/runner.py` (279 lines)

Orchestrator + CLI entry point. Public surface:

| Symbol | Role |
|--------|------|
| `HarnessReport` (dataclass) | Three-bucket aggregator with `route_match_rate` + `numeric_match_rate` properties |
| `FailureReport` (dataclass) | Per-prompt failure record (route / numeric / hallucination / missing_oracle) |
| `SC4_GATE_THRESHOLD = 0.95` | Default gate per D-12-SC4-01 |
| `synthesize_stub_transcript(prompt, expected)` | Derive ideal-agent trace from prompt + oracle |
| `run_replay_stub(prompt_path)` | v1 entry point: load oracle, synthesize transcript, score |
| `run_all(prompts_dir)` | Iterate `*.md` prompts; return aggregated HarnessReport |
| `main(argv)` | CLI: `python -m evals.runner [prompts-dir] [--gate 0.95]`; exit 0 iff numeric_match_rate ≥ gate |

## Three-Bucket Gate Math (D-12-SC4-01)

The gate denominator excludes SKIP — the foundational planning bug this lock fixed.

```python
numeric_match_rate = numeric_pass_count / (numeric_pass_count + numeric_fail_count)
```

### Worked Example 1: 13 anchored pass + 0 fail + 9 skip → 100% (PASS)

```
HarnessReport(
    n_prompts=22, route_match_count=22,
    numeric_pass_count=13, numeric_fail_count=0, numeric_skip_count=9,
)
denom = 13 + 0 = 13
numeric_match_rate = 13 / 13 = 1.0000 ≥ 0.95 → GATE PASSES
```

If SKIP were in the denominator (the bug we fixed), it would be `13 / 22 = 59%` → gate would erroneously fail every time we shipped a TBD-deferred oracle.

### Worked Example 2: 12 anchored pass + 1 fail + 9 skip → 92.3% (FAIL)

```
HarnessReport(
    n_prompts=22, route_match_count=22,
    numeric_pass_count=12, numeric_fail_count=1, numeric_skip_count=9,
)
denom = 12 + 1 = 13
numeric_match_rate = 12 / 13 = 0.9231 < 0.95 → GATE FAILS
```

If SKIP were in the denominator: `12 / 22 = 54.5%` — same fail outcome but for the wrong reason. The D-12-SC4-01 math surfaces *real* regression risk: one bad anchored oracle drops the rate below 95% even when 9 prompts are legitimately deferred.

### Edge case: all-SKIP (denom == 0)

`numeric_match_rate` returns `0.0` (not raising ZeroDivisionError); the gate fails. This is correct behavior: a harness with zero anchored prompts cannot validate the system.

## STDOUT-Only Sourcing (D-12-SC3-01)

This plan tightens RESEARCH §Pattern 6's "sourced number" definition. The original spec unioned three sources:

```
sourced = numbers_in(stdout) ∪ numbers_in(cmd_args) ∪ numbers_in(stdin)
```

This allowed false positives: a borrower asks "what's $400k @ 6.5%?", Claude invokes `python amortize.py --principal 400000 --rate 0.065` (number echoed in cmd), then narrates the unsourced "$400,000.00" without reading the stdout `{"monthly_pi": "2528.27"}`. The original Pattern 6 would credit the parroted principal as "sourced" — masking the hallucination.

D-12-SC3-01 fix:

```
sourced = numbers_in(stdout)  # cmd args + stdin NO LONGER CREDITED
```

Cross-check: if `model_response` contains *any* numeric output AND no subprocess invocation occurred in the transcript, **both** `numeric_match` (Pitfall #2: hallucinated number) and `route_match` (Pitfall #2b: parroted number with no script) fail.

### Static-provenance exemption

Some numbers are legitimate static citations — e.g., "IRS Pub 936 caps mortgage interest deduction at $750,000." Such numbers carry `provenance: "static"` in the oracle and are exempt from the STDOUT requirement. Verified by `test_static_provenance_number_exempt_from_stdout_rule`.

## Test Surface Changes

| File | Before | After | Delta |
|------|--------|-------|-------|
| `tests/test_evals_metrics.py` | 5 xfail | 5 pass | +5 live tests |
| `tests/test_evals_runner.py` | 12 xfail | 3 pass + 9 xfail | +3 live tests; 9 retained |
| **Full suite** | 617 pass / 18 xfail | 625 pass / 10 xfail | +8 newly-green |

### 5 metrics tests flipped (EVAL-04 + D-12-SC3-01 + D-12-SC4-01 closed at scorer layer):

1. `test_prose_only_number_fails_both_gates` — prose-cited number without subprocess → FAIL on both gates
2. `test_stdout_sourced_number_passes_both_gates` — number cited after `amortize.py` stdout → PASS on both
3. `test_cmd_arg_only_number_fails_numeric_match` — number echoed from cmd args only → FAIL (the tightening)
4. `test_static_provenance_number_exempt_from_stdout_rule` — IRS Pub 936 $750k cap → PASS (exempt)
5. `test_score_numeric_match_returns_three_state_enum` — `set(NumericScore) == {PASS, FAIL, SKIP}`

### 3 runner tests flipped (EVAL-03 + D-12-SC4-01 closed at aggregator layer):

1. `test_gate_passes_with_13_anchored_pass_and_9_skip` — 13/(13+0) = 100% ≥ 95% ✓
2. `test_gate_fails_with_one_anchored_fail_among_13` — 12/(12+1) = 92.3% < 95% ✗
3. `test_tbd_prompt_reported_as_skipped_not_passed` — `numeric_status: skip` → `NumericScore.SKIP`

### 9 runner tests retained as xfail (fixtures deferred to Plans 12-05 + 12-06):

| Test | Resolved by | Why deferred |
|------|-------------|--------------|
| `test_evals_prompts_dir_has_22_prompts` | Plan 12-05 (EVAL-01 + D-12-SC1-01) | Prompts not yet authored |
| `test_each_mode_has_at_least_one_prompt[*]` (7 variants) | Plan 12-05 (SC-5) | Prompts not yet authored |
| `test_every_prompt_has_paired_oracle` | Plan 12-06 (EVAL-02) | Oracles not yet authored |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Switched `class NumericScore(str, Enum)` → `StrEnum`**
- **Found during:** Task 1 ruff check (UP042 violation)
- **Issue:** Ruff `UP042` rule prohibits the legacy `(str, Enum)` pattern in Python 3.11+ codebases
- **Fix:** Use `enum.StrEnum` (introduced 3.11; project requires Python 3.12+). Preserves value-as-string serialization ergonomics.
- **Files modified:** `evals/metrics.py`
- **Commit:** `a8bfae6`

**2. [Rule 3 - Blocking] Moved `from decimal import Decimal` to top of `evals/runner.py`**
- **Found during:** Task 2 implementation
- **Issue:** Plan sketch placed `from decimal import Decimal` at the bottom (with `# noqa: E402`). This is needed inside `synthesize_stub_transcript` for `f"${Decimal(str(val)):,.2f}"` formatting — but bottom-of-module imports are anti-idiomatic and confuse mypy/ruff.
- **Fix:** Imported at the top alongside other stdlib imports.
- **Files modified:** `evals/runner.py`
- **Commit:** `8e844af`

**3. [Rule 3 - Blocking] Added `# type: ignore[import-untyped]` to `import frontmatter`**
- **Found during:** Task 2 mypy --strict check
- **Issue:** `python-frontmatter` ships no `py.typed` marker; mypy --strict rejects untyped imports
- **Fix:** Added inline ignore comment, matching the existing convention used in `tests/test_evals_runner.py` line 61.
- **Files modified:** `evals/runner.py`
- **Commit:** `8e844af`

### Architectural Changes
None — implementation matched the plan's contracts verbatim.

### Authentication Gates
None — pure code; no external services.

## Worked Examples of the Scorer Surface

### Example 1: `score_numeric_match` PASS path

```python
expected = {
    "expected_numbers": [
        {"label": "monthly_pi", "value": "1264.14", "tolerance": "0.005",
         "provenance": "stdout"}
    ]
}
sub_calls = [{
    "type": "subprocess",
    "cmd": ["python", "scripts/amortize.py", "--input", "/tmp/x.json"],
    "stdout": '{"monthly_pi": "1264.14"}',
}]
score = score_numeric_match("Your payment is $1,264.14", expected, sub_calls)
# → NumericScore.PASS  (cited in response AND in stdout)
```

### Example 2: `score_numeric_match` FAIL path (cmd-arg leak)

```python
expected = {
    "expected_numbers": [
        {"label": "principal", "value": "400000.00", "provenance": "stdout"}
    ]
}
sub_calls = [{
    "type": "subprocess",
    "cmd": ["python", "scripts/amortize.py", "--principal", "400000.00"],
    "stdout": '{"monthly_pi": "2528.27"}',  # 400000 NOT in stdout
}]
score = score_numeric_match("Principal: $400,000.00", expected, sub_calls)
# → NumericScore.FAIL  (cited in response, but unsourced — cmd args no longer credited)
```

### Example 3: `score_route_match` Pitfall #2b

```python
score_route_match("Your payment is $1,264.14", expected={}, subprocess_calls=[])
# → False  (numeric output present + no subprocess → fail)
```

### Example 4: `HarnessReport.to_dict()` CI output shape

```json
{
  "n_prompts": 22,
  "route_match_count": 22,
  "route_match_rate": 1.0,
  "numeric_pass_count": 13,
  "numeric_fail_count": 0,
  "numeric_skip_count": 9,
  "numeric_match_rate": 1.0,
  "failures": []
}
```

## Commits

| Hash | Description | Files |
|------|-------------|-------|
| `a8bfae6` | feat(12-04): ship evals/metrics.py | `evals/metrics.py`, `tests/test_evals_metrics.py` |
| `8e844af` | feat(12-04): ship evals/runner.py | `evals/runner.py`, `tests/test_evals_runner.py` |

## Threat Flags

None — the implementation respects the plan's `<threat_model>`:
- python-frontmatter uses `yaml.safe_load` internally (T-12-04-01 mitigated via std-lib default)
- `json.loads` is non-executable (T-12-04-02 mitigated)
- Runner stdout has no PII (T-12-04-03 accepted: personal tool, fictional fixtures only)
- v1 replay-stub mode synthesizes transcripts in-process — no untrusted external input (T-12-04-04 N/A for v1)

## Verification

All gates green:
- ✅ `evals/metrics.py` + `evals/runner.py` mypy --strict clean
- ✅ ruff clean on all new code (`UP042` resolved via `StrEnum`)
- ✅ 8 Wave-0 xfails flipped (5 metrics + 3 runner)
- ✅ 9 xfails retained in `tests/test_evals_runner.py` (waiting on Plans 12-05 + 12-06 fixtures)
- ✅ Full test suite: 625 passed, 5 skipped, 10 xfailed (was 617 / 5 / 18 — exactly +8 newly-green)
- ✅ HarnessReport ctor matches Wave-0 stub call signature verbatim
- ✅ Gate math verified by 13/(13+0) = 100% PASS and 12/(12+1) = 92.3% FAIL test cases
- ✅ TBD-prompt → SKIP test passes

## Self-Check: PASSED

- ✅ `evals/__init__.py` exists (16 lines)
- ✅ `evals/metrics.py` exists (203 lines, ≥ 180 min)
- ✅ `evals/runner.py` exists (279 lines, ≥ 200 min)
- ✅ `evals/metrics.py` contains `class NumericScore`
- ✅ `evals/runner.py` contains `numeric_skip_count`
- ✅ Commit `a8bfae6` exists in git log
- ✅ Commit `8e844af` exists in git log
- ✅ Worktree base unchanged: `9c8386034f1b30932e28e568446f08664ebcc046`

## TDD Gate Compliance

This plan executed tasks with `tdd="true"` flags. The RED phase pre-existed (Plan 12-00 shipped 17 Wave-0 xfails). This plan's commits are the GREEN phase:

- ✅ RED (Wave-0 stubs, Plan 12-00): xfailing tests already in place — provides the deterministic acceptance contract
- ✅ GREEN (this plan, 2 commits): implementation flips 8 xfails to passing without modifying the original test assertions
- ➖ REFACTOR: none required — implementation matched the plan contracts on first pass; only mechanical adjustments (StrEnum, import placement, type: ignore for frontmatter)

No standalone `test(...)` commit was required because the RED phase commits live in Plan 12-00's history (verified by `grep -c pytest.mark.xfail` baseline = 17, post-plan = 9 in runner + 0 in metrics).

## Hand-Off to Next Plans

Plan 12-05 (prompts) and Plan 12-06 (oracles) now have a fully-shipped scorer + aggregator. The remaining 9 xfails in `tests/test_evals_runner.py` close as follows:

| Xfail | Resolved by | Mechanism |
|-------|-------------|-----------|
| `test_evals_prompts_dir_has_22_prompts` | Plan 12-05 | Author 22 `evals/prompts/*.md` files (21 mode-coverage + 1 live-rate-injection per D-12-SC1-01) |
| `test_each_mode_has_at_least_one_prompt[evaluate/compare/refinance/affordability/stress/amortize/arm]` | Plan 12-05 | Frontmatter `mode:` field on each prompt; 7 modes × ≥3 prompts each |
| `test_every_prompt_has_paired_oracle` | Plan 12-06 | One `evals/expected/{id}.json` per prompt (1:1 by stem) |

After Plans 12-05 + 12-06, `python -m evals.runner` should run replay-stub mode against the full 22-prompt set and emit the JSON HarnessReport with `numeric_match_rate ≥ 0.95` (13 anchored pass / 9 skipped). Plan 12-07 then wires the gate into CI.

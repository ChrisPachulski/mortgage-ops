---
phase: 11-subagents
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - .claude/agents/amortization-agent.md
  - .claude/agents/refi-npv-agent.md
  - .claude/agents/stress-test-agent.md
  - .claude/agents/README.md
  - .claude/skills/mortgage-ops/SKILL.md
  - .claude/skills/mortgage-ops/modes/stress.md
  - .claude/skills/mortgage-ops/references/subagent-routing.md
  - CLAUDE.md
  - pyproject.toml
  - tests/fixtures/subagent_transcripts/.gitkeep
  - tests/fixtures/subagent_transcripts/README.md
  - tests/fixtures/subagent_transcripts/amort_single_loan.transcript.jsonl
  - tests/fixtures/subagent_transcripts/refi_3_offers.transcript.jsonl
  - tests/fixtures/subagent_transcripts/stress_50_scenarios.transcript.jsonl
  - tests/test_subagents.py
findings:
  critical: 3
  warning: 6
  info: 4
  total: 13
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-05-10
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 11 ships three subagent definitions, a routing reference, a SKILL.md update,
test surface, and three synthetic transcript fixtures. The frontmatter parses, the
SUBA-05 routing rule is wired correctly, and PII / AI-attribution discipline is
clean throughout. However the code review surfaces several real defects:

- **BLOCKER (CR-01):** A reference document (`references/stress-tests.md`) is
  cited from five places — including the `stress-test-agent` body, the
  `subagent-routing.md` references list, `modes/stress.md`, and the actual
  `stress_test.py` error envelope — but the file does not exist on disk.
  This is a broken cross-link that the agents and the script will hit.
- **BLOCKER (CR-02):** The `amortization-agent` body specifies the inline
  markdown table columns as `period | date | payment | principal | interest |
  balance`, but the committed transcript fixture and the SUBA-04 amort shape
  test use `month | payment | principal | interest | balance` (no `period`
  column, no `date` column). The fixture and the test contradict the canonical
  agent contract — exactly the drift the synthetic fixture is supposed to
  prevent.
- **BLOCKER (CR-03):** `refi-npv-agent.md` Workflow Step 3b says "Write the
  input to `/tmp/refi-input-{offer-idx}-{timestamp}.json`" with no `bash:`
  prefix, while Step 3c uses `bash:` explicitly. The agent's tools list is
  `[Read, Bash]` — Write is intentionally absent (Hard rule #5 + line 122) —
  so an agent that takes the verb "Write" literally will attempt the
  unavailable Write tool. Internally inconsistent instructions.

The warnings address a tiktoken dependency that the project's RESEARCH explicitly
rejects, future-tense SKILL.md prose for a phase that is now landing, a
permissive SUBA-05 regex, and a fragile NPV-column parser. Info items document
smaller polish issues.

## Critical Issues

### CR-01: Broken cross-link to non-existent `references/stress-tests.md`

**File:** `.claude/agents/stress-test-agent.md:147`
**File:** `.claude/skills/mortgage-ops/references/subagent-routing.md:5,164`
**File:** `.claude/skills/mortgage-ops/modes/stress.md:146`
**File:** `.claude/skills/mortgage-ops/scripts/stress_test.py:101` (cited via grep, outside review scope, but confirms the leak)

**Issue:** `references/stress-tests.md` is referenced by:
1. `stress-test-agent.md` line 147 — the agent body's "Reference:" footer points
   readers there for the Phase 8 → Phase 11 input contract.
2. `subagent-routing.md` line 5 — listed as a sibling doc.
3. `subagent-routing.md` line 164 — listed under "Cross-references" as the
   upstream input-contract document.
4. `modes/stress.md` line 146 — listed under "RELATED REFERENCES" with a
   user-facing trigger phrase ("explain the sweep").
5. `stress_test.py` (out of review scope) prints "See references/stress-tests.md
   for sweep mechanics" in its 6-key Pydantic envelope error path.

A directory listing of `.claude/skills/mortgage-ops/references/` shows only
9 files: `affordability-rules.md, amortization-formulas.md, apr-reg-z.md,
arm-mechanics.md, gse-limits.md, mip-pmi.md, refi-npv.md,
spreadsheet-conventions.md, subagent-routing.md, tax-deductibility.md`.
**`stress-tests.md` is absent.**

When a user asks "explain the sweep" / "what's the ATR/QM heuristic" the
mode-routing in `modes/stress.md` instructs the LLM to load this file
on-demand; the load will fail or silently no-op, breaking the documented
progressive-disclosure contract.

**Fix:** Either (a) ship `references/stress-tests.md` (it appears Phase 8 was
expected to ship it), or (b) remove the dangling references from all four
locations and update `stress_test.py`'s error message in a follow-up. (a) is
the right fix because the references are load-bearing — multiple Phase 11
artifacts treat the file as the upstream contract document.

---

### CR-02: Amortization agent column contract does not match fixture/test

**File:** `.claude/agents/amortization-agent.md:66`
**File:** `tests/fixtures/subagent_transcripts/amort_single_loan.transcript.jsonl:1`
**File:** `tests/test_subagents.py:366`

**Issue:** Agent body says (line 66):

```
return an inline markdown table with columns
`period | date | payment | principal | interest | balance`.
```

The transcript fixture uses columns `month | payment | principal | interest |
balance` — no `period`, no `date`. The SUBA-04 amort shape test
(`test_subagents.py:366`) asserts `"| month " in content` and `"| balance " in
content`. So:

1. The fixture violates the agent's own column contract.
2. The test, which is supposed to anchor that contract against drift, asserts
   the WRONG column header (`month` instead of `period`).
3. A real agent that follows the body verbatim will produce `period` headers
   — and the SUBA-04 test will fail because the fixture's hand-authored
   `month` column is what the test now asserts on.

The synthetic fixture is supposed to mirror the canonical agent output per
README.md "Why synthetic, not live" (D-02). It currently mirrors a
non-canonical shape.

**Fix:** Pick one canonical column set. Two options:

```
# Option A: keep agent body intact, fix fixture + test to use period|date
columns: period | date | payment | principal | interest | balance
fixture header: | period | date | payment | principal | interest | balance |
test asserts: "| period " in content AND "| balance " in content

# Option B: change agent body to match the fixture (drop period+date)
agent body line 66: `month | payment | principal | interest | balance`.
```

Option A preserves audit-traceability (period number AND amortization date are
both useful in a single-loan schedule). Option B is a smaller diff but loses
the date column.

---

### CR-03: refi-npv-agent body instructs "Write the input" with no Write tool available

**File:** `.claude/agents/refi-npv-agent.md:69-70`
**File:** `.claude/agents/refi-npv-agent.md:5-7` (tools list)
**File:** `.claude/agents/refi-npv-agent.md:51,122` (Write-not-in-toolset rules)

**Issue:** Workflow Step 3b reads:

```
   b. Write the input to
      `/tmp/refi-input-{offer-idx}-{timestamp}.json`.
```

with no `bash:` prefix. Step 3c, by contrast, prefixes with `bash:` to make
the dispatch explicit. The agent's frontmatter `tools:` list is `[Read, Bash]`
— Write is intentionally absent per Hard rule #5 ("The Write tool is
intentionally NOT in your toolset") and the Reference footer at line 122.

This produces an internal contradiction: the body's verb "Write" with no `bash:`
prefix can plausibly be read as "use the Write tool", but that tool is denied
by the frontmatter allowlist. An agent trying to follow the instruction
literally will either:

1. Try the Write tool and hit a permission-denied error, OR
2. Ad-lib a Bash heredoc / `printf` invocation to materialize the tmpfile
   (depending on the model's interpretation).

Compare to `amortization-agent.md` Workflow Step 4, which is explicit:

> Write the input JSON to a tmpfile. Use `/tmp/amortize-input-{timestamp}.json`
> (Bash tool). Verify the file exists before invocation.

— note the inline `(Bash tool)` disambiguation. Refi-npv-agent should match.

**Fix:** Update Workflow Step 3b to disambiguate:

```
   b. Write the input to
      `/tmp/refi-input-{offer-idx}-{timestamp}.json` (Bash tool — use
      a heredoc or `printf` to materialize the tmpfile; the Write tool
      is NOT in this agent's toolset per Hard rule #5).
```

Alternatively, prefix with `bash:` like step 3c: "bash: write the input to
`/tmp/refi-input-...`" — but the parenthetical-disambiguation pattern matches
`amortization-agent.md` and is less ambiguous.

## Warnings

### WR-01: tiktoken dev-dep contradicts the project's tokenizer doctrine

**File:** `pyproject.toml:21`
**File:** `tests/test_subagents.py:438`

**Issue:** `pyproject.toml` lists `tiktoken>=0.7,<1.0` under `[dependency-groups] dev`.
Yet `tests/test_subagents.py` line 438 documents:

> tokenizer = anthropic.Anthropic().messages.count_tokens (the official Claude
> tokenizer; tiktoken explicitly REJECTED per RESEARCH Standard Stack because
> it is OpenAI-specific and ~5-20% drift on the <1k boundary).

So tiktoken is pinned in dev deps but is explicitly rejected for use in tests.
No file in the review scope imports it. Either:

1. Some other phase (not in review scope) does use tiktoken — in which case
   the test docstring's "REJECTED" wording is misleading, OR
2. Tiktoken is dead weight and should be removed.

This is a quality / supply-chain concern: every dep widens the audit surface
and the lockfile churn. The project's RESEARCH document (cited in the test)
explicitly rejects it.

**Fix:** Either (a) remove `"tiktoken>=0.7,<1.0"` from dev deps, or
(b) document explicitly somewhere (a comment in pyproject.toml is enough)
which other test or tool needs it. Recommendation: (a) — the test docstring
is the canonical statement and tiktoken should be excluded.

---

### WR-02: SKILL.md "Subagents (Phase 11)" section is in future tense for a now-shipping phase

**File:** `.claude/skills/mortgage-ops/SKILL.md:181-194`

**Issue:** Section reads:

```
## Subagents (Phase 11)

Three subagents will land in Phase 11 to provide context isolation for
calc-heavy operations. Their files will be created at
`.claude/agents/{agent}.md`:
...
Phase 10 ships ONLY the forward-link. The skill does NOT delegate to these
agents at Phase 10. When Phase 11 lands, `modes/stress.md` (D-SUBA-FW-02)
will activate the dispatch automatically via an existence check on
`.claude/agents/stress-test-agent.md` — no SKILL.md edit required.
```

This Phase 11 commit is shipping the agent files. The "will land" / "will be
created" / "When Phase 11 lands" prose is now stale. A user / planner reading
SKILL.md after the commit will be misled into thinking the agents have not
shipped.

This is also internally inconsistent: line 198 ("Routes parameter-grid stress
sweeps. Sweeps with `scenario_count > 5` dispatch to `stress-test-agent`") is
in present tense and assumes the agent file exists, which contradicts the
future-tense block 17 lines above.

**Fix:** Convert lines 183-194 to present tense:

```
## Subagents

Three subagents provide context isolation for calc-heavy operations. Files
live at `.claude/agents/{agent}.md`:

- `amortization-agent` (Haiku) — single-loan ARM amortization requests
- `refi-npv-agent` (Sonnet) — multi-step NPV reasoning, sweeps multiple offers
- `stress-test-agent` (Haiku) — parameter-grid sweeps; returns < 1k token summary

Dispatch is gated by `modes/stress.md` (D-SUBA-FW-02), which performs an
existence check on `.claude/agents/stress-test-agent.md` and falls back
to inline execution if the file is absent.
```

---

### WR-03: SUBA-05 regex is too permissive (false-positive risk)

**File:** `tests/test_subagents.py:402-410`

**Issue:** The pattern is:

```python
pattern = re.compile(
    r"(scenarios?\s*(>|more than|greater than)\s*5|scenario[_ ]count\s*>\s*5).*"
    r"(stress-test-agent|subagent)",
    re.IGNORECASE | re.DOTALL,
)
```

With `re.DOTALL`, the `.*` between the threshold phrase and `stress-test-agent`
spans the entire rest of the file. So a future edit could:

1. Add a sentence "If `scenario_count > 5` we used to dispatch but now we
   route differently" anywhere near the top of `modes/stress.md`,
2. Mention `stress-test-agent` 200 lines later in an unrelated context (e.g.,
   a "Related agents" list),
3. The regex still passes — even though the routing rule was effectively
   broken.

The current `modes/stress.md` has the canonical phrasing in three places
(lines 80, 134, 155), so the regex matches today. But the test's purpose is
guarding the contract against drift; a permissive regex undermines that.

**Fix:** Tighten the regex to a per-line check, or assert against a phrase
that has to appear close to the agent reference:

```python
# Option A: per-line — assert exact threshold phrase appears within 3 lines
# of "stress-test-agent" reference.
lines = stress_md.splitlines()
for i, line in enumerate(lines):
    if "stress-test-agent" in line:
        nearby = "\n".join(lines[max(0, i-3):i+4])
        if re.search(r"(scenario_count\s*>\s*5|sweeps?\s*with\s*>\s*5)", nearby, re.IGNORECASE):
            return
pytest.fail("SUBA-05: routing rule (>5 scenarios -> stress-test-agent) not found within 3 lines of any stress-test-agent reference")

# Option B: assert the canonical literal sentence directly, no regex:
assert "If `scenario_count > 5`, dispatch to `stress-test-agent`" in stress_md
```

Option B is the strongest pin and matches the canonical phrasing in
`modes/stress.md` line 155 verbatim.

---

### WR-04: SUBA-04 refi NPV parser will crash on `n/a` if the contract evolves

**File:** `tests/test_subagents.py:339-346`

**Issue:** The parser does:

```python
npv_str = cells[-1].replace("$", "").replace(",", "")
npv_values.append(float(npv_str))
```

The current `refi-npv-agent` Hard rule #5 specifies NPV is always a numeric
value (with explicit sign, prefix `-$` for negative). But the same rule states
that `breakeven_months` can be `n/a`. If a future agent body change reorders
columns, or if an off-by-one creeps into the table layout, `cells[-1]` could
contain `n/a` and `float("n/a")` raises `ValueError` with no diagnostic
context — the test fails with a Python error, not an interpretable assertion
failure.

This is a fragility, not a bug per se, because the current contract pins NPV
last. But the test's failure mode for column-reorder is opaque.

**Fix:** Wrap the parse with a clearer error:

```python
npv_values: list[float] = []
for row in table_rows[1:]:
    cells = [c.strip() for c in row.split("|") if c.strip()]
    npv_str = cells[-1].replace("$", "").replace(",", "")
    try:
        npv_values.append(float(npv_str))
    except ValueError:
        pytest.fail(
            f"SUBA-04 refi: last column of row {row!r} is not a numeric NPV "
            f"(got {cells[-1]!r}). Verify the agent contract still places NPV "
            f"as the LAST column per Plan 11-02 Hard rule #5."
        )
```

---

### WR-05: Refi `Computed by:` cite uses shell brace-expansion that is documentation, not a runnable command

**File:** `tests/fixtures/subagent_transcripts/refi_3_offers.transcript.jsonl:1`

**Issue:** The fixture's citation line is:

```
Computed by: bash python .claude/skills/mortgage-ops/scripts/refi_npv.py --input /tmp/refi-input-{1,2,3}-1714665600.json (3 invocations)
```

`{1,2,3}` is shell brace expansion that bash will expand to three separate
words — but as a single argument to `--input` it would actually pass the
literal string `{1,2,3}` to the script (since brace expansion happens before
quoting and the `--input` flag takes one path). The cite reads as if it were
a copy-pasteable command but isn't.

The agent body says the agent runs the script ONCE PER OFFER (Step 3c invokes
once per offer; Step 4 ranks the per-offer outputs). So the natural cite
should list three explicit invocations, not collapse them into a brace.

**Fix:** Either list each invocation on its own line:

```
Computed by:
  bash python .claude/skills/mortgage-ops/scripts/refi_npv.py --input /tmp/refi-input-1-1714665600.json
  bash python .claude/skills/mortgage-ops/scripts/refi_npv.py --input /tmp/refi-input-2-1714665600.json
  bash python .claude/skills/mortgage-ops/scripts/refi_npv.py --input /tmp/refi-input-3-1714665600.json
```

or document that this is a glob, not a runnable command:

```
Computed by: bash python .claude/skills/mortgage-ops/scripts/refi_npv.py --input /tmp/refi-input-N-1714665600.json (3 invocations, N=1..3)
```

The latter is more compact for token-budget purposes.

---

### WR-06: README.md cross-link target depth is wrong

**File:** `.claude/agents/README.md:93,94,95,96-97`

**Issue:** README.md lines 93-97 reference relative paths like:

```
- Phase 11 success criteria: `../../.planning/ROADMAP.md` Phase 11 section (SC-1..SC-5).
- Per-requirement traceability: `../../.planning/REQUIREMENTS.md` SUBA-01..SUBA-06.
- Test gates: `../../tests/test_subagents.py` + the synthetic transcripts at
  `../../tests/fixtures/subagent_transcripts/` (live-capture recipe in that directory's
  README).
```

`.claude/agents/` is two levels deep from repo root, so `../../` resolves to
the repo root. That is correct. But the SUBA-05 cross-phase TODO link in
`subagent-routing.md` line 162-163 has:

```
if Phase 10 hasn't shipped at Plan 11-04 time, see
`.planning/phases/11-subagents/11-04-SUBA-05-TODO.md` for the cross-phase contract).
```

This is a bare path (no `../../` prefix), implying repo-root anchoring. From
`.claude/skills/mortgage-ops/references/`, the actual relative path to that
file would be `../../../../.planning/phases/11-subagents/11-04-SUBA-05-TODO.md`
(four levels up). The bare path will not resolve from the file's location;
only as a repo-rooted path in a viewer that auto-roots.

The same issue may affect line 6 (`.planning/phases/11-subagents/11-01..06-*-PLAN.md`)
in `subagent-routing.md`.

**Fix:** Either (a) consistently use repo-rooted paths everywhere with a
note that they are repo-rooted (which the README cross-references already
violate by using `../../`), or (b) prefix with the right number of `../`
components for each file's depth. The Anthropic skill convention (per the
project's other references) is repo-rooted bare paths, so option (a) plus
fixing the README's `../../` prefixes is the cleaner direction.

## Info

### IN-01: Future-tense roadmap prose in test_subagents.py docstring

**File:** `tests/test_subagents.py:11-19`

**Issue:** Module docstring says "Wave 0 (Plan 11-00) creates ALL 6 tests as
xfail stubs. Subsequent waves flip the relevant xfail decorators to real
assertions" then enumerates Waves 1-5. Today (with all flips applied), no
xfail decorators remain in the file. The docstring is a stale plan, not a
description of the current code.

**Fix:** Convert to past tense or remove the wave-by-wave narrative:

```
# All SUBA-01..06 tests are live (no xfail decorators remain).
# Wave provenance: SUBA-01 (Plan 11-01), SUBA-02 (Plan 11-02),
# SUBA-03 (Plan 11-03), SUBA-04 + SUBA-06 (Plan 11-05),
# SUBA-05 (Plan 11-04).
```

---

### IN-02: TRANSCRIPT_DIR docstring references a non-existent file

**File:** `tests/test_subagents.py:65-67`

**Issue:** The `TRANSCRIPT_DIR` constant docstring says:

```
"""Phase 11 Wave 5 ships recorded transcripts here. SUBA-06 reads
stress_50_scenario_summary.md and pipes it through anthropic.count_tokens."""
```

The actual fixture filename is `stress_50_scenarios.transcript.jsonl`, not
`stress_50_scenario_summary.md`. The docstring is from an earlier draft.

**Fix:** Update to:

```
"""Phase 11 Wave 5 ships recorded transcripts here. SUBA-06 reads
stress_50_scenarios.transcript.jsonl and pipes its content through
anthropic.count_tokens."""
```

---

### IN-03: `.gitkeep` is empty AND README.md exists in same dir — `.gitkeep` is now redundant

**File:** `tests/fixtures/subagent_transcripts/.gitkeep`

**Issue:** The file is 0 bytes. Its purpose is to keep an otherwise-empty
directory in git. Once `README.md` and the three `.transcript.jsonl` fixtures
landed in the same directory (Wave 5), the `.gitkeep` is redundant — git
already tracks the directory because of the other files.

This is not a defect; it is residue from Wave 0 that the cleanup path didn't
remove.

**Fix:** Remove the file. Single-line cleanup:

```
git rm tests/fixtures/subagent_transcripts/.gitkeep
```

---

### IN-04: Fixture path date drifts from system date

**File:** `tests/fixtures/subagent_transcripts/amort_single_loan.transcript.jsonl:1`

**Issue:** The fixture references `reports/001-amortization-2026-05-02.csv`,
but today's date (per the project's date conventions and CLAUDE.md context)
is 2026-05-10. The agent body Hard rule #4 says "today's ISO date".

The SUBA-04 amort test asserts only that the path matches the regex
`reports/\d{3}-amortization-\d{4}-\d{2}-\d{2}\.csv`, so the test passes
regardless of date. This is documentation drift, not a test failure.

**Fix:** Update the date to anything in 2026-05 to reduce reader confusion:

```
reports/001-amortization-2026-05-10.csv
```

(Or accept this as a "synthetic fixture, dates don't matter" call.)

---

_Reviewed: 2026-05-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

# Mortgage-Ops Comprehensive Loop Plan

> Self-contained instructions for a single ralph-loop run that exercises and validates
> the mortgage-ops corpus + calc engine across three phases. Loop converges when all
> three phases are verifiably complete.

## How to invoke

```bash
/ralph-loop:ralph-loop --name mortgage-comprehensive "Read and execute every phase in .planning/MORTGAGE-OPS-COMPREHENSIVE-LOOP.md against its 'phase complete when' criteria. Track progress in a working file at .planning/MORTGAGE-OPS-LOOP-PROGRESS.md (create on iter 1, update each iter). Output <promise>CONVERGED</promise> only after the final consolidated report exists at .planning/MORTGAGE-OPS-LOOP-REPORT.md AND all three phases meet their completion criteria. Do not output the promise until you have re-verified completion." --completion-promise CONVERGED --max-iterations 25
```

---

## Phase 1 — Zotero corpus cleanup

**Input:** `.planning/ZOTERO-CLEANUP-TODO.md` (5 items with weak provenance URLs)

**Steps:**
1. For each of the 5 items:
   - WebFetch the proposed better URL to verify it resolves
   - If it resolves: update the URL in Zotero via direct SQLite write. Back up `~/Zotero/zotero.sqlite` first to `~/Zotero/zotero.backup-loop-<timestamp>.sqlite`. Quit Zotero before writing (`osascript -e 'quit app "Zotero"'`); relaunch after.
   - If it doesn't resolve: WebSearch for the actual best-available canonical URL on the same authority's site, retry WebFetch verification, and use that.
2. After all 5 are updated, verify via `cli-anything-zotero --json item find <title-search>` that each updated item's URL field now reflects the upgrade.

**Phase 1 complete when:**
- All 5 items have URLs pointing to a Tier 1 authority (consumerfinance.gov / fhfa.gov / hud.gov / fanniemae.com / freddiemac.com / law.cornell.edu / govinfo.gov / nwmls.com / Federal Register), AND
- A SQLite backup file exists with timestamp from this loop run.

---

## Phase 2 — Calc engine citation audit

**Input:** `.planning/CITATION-COVERAGE.md` + the actual code in `lib/rules/*.py` and `lib/*.py`.

**Steps:**
1. For each entry in the coverage matrix:
   - Read the module's docstring + first ~30 lines for embedded citation references (CFR sections, MLs, statutes, USC citations).
   - Verify each cited authority has a matching item in the Zotero corpus by title/URL search via `cli-anything-zotero`.
   - WebSearch for "[citation] amended OR withdrawn OR superseded" to check whether the cited authority is still current (last 12 months).
   - Flag any module whose cited rule has been materially amended since the docstring was written.
2. Append an audit-results section to `.planning/CITATION-COVERAGE.md` titled `## Audit YYYY-MM-DD` with three subsections:
   - **Verified current** — modules whose citations are confirmed Zotero-traceable AND current
   - **Concerns** — modules where (a) Zotero entry exists but the underlying rule has been amended, OR (b) Zotero entry doesn't actually match the citation in code
   - **Action items** — for each concern, the specific remediation (update Zotero entry, update docstring, file a code change)

**Phase 2 complete when:**
- Every module listed in the matrix has a row in either "Verified current" or "Concerns"
- The audit-results section exists in `CITATION-COVERAGE.md`
- Any high-severity concerns (amended rules) are also surfaced in the final consolidated report.

---

## Phase 3 — Literature-grounded stress tests

**Input:** `.planning/HOUSE-PURCHASE-GOAL-2026.md` (current target: $700K at 6.36% rate) + the Climate and Insurance Risk + Calc Methods Zotero collections.

**Steps:**

Generate and execute three stress-test scenarios via `scripts/stress_test.py`:

1. **Rate-shock**: 30yr fixed jumps 6.36% → 7.50% on the $700K target purchase. Cite Liebersohn-Rothstein / Fonseca-Liu for the lock-in framing.

2. **Climate-insurance escalation**: insurance premium grows 15% per year for 5 years (WA market trajectory). Cite the Dallas Fed Ge/Johnson/Tzur-Ilan 2025 paper ($500/yr premium hike → 27% delinquency rise) for the delinquency-cliff argument.

3. **Dana income disruption**: Dana's $10,000/mo gross goes to $0 for 6 months (modeling unexpected job loss or extended parental leave beyond standard PFML). Test whether Chris's $13,491.67/mo alone carries the PITI + non-housing burn + the $300/mo new-baby costs.

For each scenario:
- Run `python scripts/stress_test.py --help` first to confirm input schema
- Build JSON input matching that schema → `/tmp/stress-comprehensive-<scenario>.json`
- Execute via `uv run python .claude/skills/mortgage-ops/scripts/stress_test.py --input ...`
- Capture results to `/tmp/stress-result-<scenario>.json`

Append a new section to `.planning/HOUSE-PURCHASE-GOAL-2026.md` titled `## Literature-Grounded Stress Tests (YYYY-MM-DD)` with for each scenario:
- One-paragraph narration of the scenario (citing the relevant Zotero entries)
- The resulting PITI / DTI / cash-flow numbers from the script
- Verdict: does the $700K target survive this stress? If not, what tier-down is needed?

**Phase 3 complete when:**
- 3 result JSON files exist in `/tmp/`
- The new stress-test section exists in `HOUSE-PURCHASE-GOAL-2026.md`
- Each scenario has its narration grounded in a specific Zotero entry (title cited inline)

---

## Convergence

Write the final consolidated report to `.planning/MORTGAGE-OPS-LOOP-REPORT.md` covering:
- **Phase 1:** Table of 5 items with before/after URLs + verification status
- **Phase 2:** Counts of verified vs concerns; list of any high-severity concerns with recommended remediation
- **Phase 3:** Table of 3 stress scenarios with PITI deltas + verdict per scenario; consolidated implication for the $700K target

Only after `MORTGAGE-OPS-LOOP-REPORT.md` exists with all three phases populated, output `<promise>CONVERGED</promise>`.

## Anti-shortcut clauses

- Do NOT output CONVERGED to escape a stuck phase. If you cannot complete a step, document the specific blocker in `MORTGAGE-OPS-LOOP-PROGRESS.md` and continue with the next steps.
- Do NOT skip the SQLite backup in Phase 1 — that's the rollback path.
- Do NOT report a Phase 2 concern without proposing a specific remediation.
- Do NOT cite Zotero entries by guess; verify each cited title exists via `cli-anything-zotero --json item find` before referencing.
- Do NOT cite numbers in Phase 3 narration that aren't from the script's stdout JSON.

---

*Last edited 2026-05-16. Reusable: re-run anytime the corpus has been substantially expanded or the calc engine has gained new modules. Edit phase criteria as scope changes.*

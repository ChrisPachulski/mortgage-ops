# Best-in-Class Roadmap

## Positioning

`mortgage-ops` should be best-in-class for one narrow job: helping the
Pachulski household avoid bad housing and mortgage decisions. It should not be
cutting edge in the general software sense. For this domain, "cutting edge"
usually means more model discretion, more live integrations, more scraping
fragility, and more maintenance burden. The target is unusual trustworthiness.

Upstream filter for all future work:

> Would this reduce the chance of making a six-figure housing mistake?

If yes, the work is likely strategic. If it only makes the project feel more
advanced, skip it.

## Operating Model

Codex and Claude are expected to maintain this project. The roadmap is designed
around that reality:

- Codex should own repo edits, tests, refactors, reference-data refreshes, and
  verification.
- Claude skill/runtime should own user interaction, gap-fill questions, script
  dispatch, and narration.
- Neither agent owns arithmetic. Every dollar figure must come from `lib/`,
  `scripts/`, or a cited reference row.
- Neither agent writes User Layer files unless the user explicitly asks.
- Any future maintainer should be able to regenerate a report and explain every
  number without re-reading long historical phase plans.

This means the best investments are boring, explicit, and checkable.

## Moat Layers

| Layer | Bad-decision class reduced | What "best-in-class" means here |
|---|---|---|
| Report traceability | Uncatchable arithmetic or assumption error | Every user-facing number maps to function, args, input field, reference row, effective date, and oracle/fixture coverage. |
| Rules refresh discipline | Wrong eligibility from stale law/table data | Annual refresh produces impact diffs; stale data is visible before decision use. |
| Property verdict quality | Buying the wrong property or dismissing a good one | GO / WATCH / NO-GO reasons are specific, ranked, and tied to household constraints. |
| Oracle mesh | Silent calc drift | Each commodity calc family has independent cross-source coverage where conventions match. |
| Decision ergonomics | Tool not used when it matters | Saved listings, assumptions, and comparisons make the right decision easier than ad hoc spreadsheeting. |
| Low-maintenance agent ops | Future agents degrade trust accidentally | Contributor rules, tests, and docs make the safe path the easy path. |

## Success Metrics

These are the steady-state quality bars.

- 100% of report-visible numbers are traceable or explicitly labeled as source
  input, user-provided value, or heuristic estimate.
- 0 orphan numeric values in generated reports.
- 100% of `lib/rules/` predicates have citation, source URL, effective date,
  fixture coverage, and catalog entry.
- Reference data used for active decisions is less than 12 months stale or has a
  documented waiver.
- Every calc family has either a hand-calc oracle and an independent external
  oracle, or a documented reason external parity is impossible.
- Property reports are reproducible from persisted listing, household/profile
  inputs, reference-data versions, and code revision.
- New features pass the six-figure-mistake filter before planning begins.
- Claude/Codex can run the maintenance playbook without writing User Layer
  files or inventing numbers.

## Roadmap

### Phase 19: Traceability Spine

**Goal:** Make every report number auditable without reading source code.

Build:

- A structured `TraceEntry` / `TraceIndex` model that records:
  `display_path`, `value`, `source_kind`, `function_or_script`, `args_hash`,
  `input_field`, `reference_file`, `reference_row`, `effective`, and
  `oracle_coverage`.
- Report-side citation footers generated from trace data, not manually composed
  strings.
- A report parser/meta-test that fails on orphan numbers in committed report
  fixtures and in reports generated under a temporary test directory. Live
  `reports/*.md` are User/Data Layer (gitignored per DATA_CONTRACT.md) and stay
  out of CI; a separate opt-in `scripts/audit_reports.py` lets the user
  validate their local reports on demand without making tests nondeterministic
  across workstations.
- A deterministic report manifest containing code revision, household/profile
  input hashes, listing hash, and reference-data effective dates.

Success criteria:

- Property reports can answer "where did this dollar amount come from?" for
  every displayed number.
- Any numeric value not traceable must be explicitly tagged as display-only
  formatting, source input, or user-provided text.
- Codex can add a new report field by adding a trace entry and a focused test;
  Claude does not need to infer provenance.

### Phase 20: Reference Refresh Discipline

**Goal:** Turn annual rule/data refresh into a repeatable, agent-safe workflow.

Build:

- `scripts/reference_refresh_audit.py` that scans `data/reference/*.yml`,
  reports stale files, source URLs, effective dates, and impacted predicates.
- Impact-diff reports: before/after snapshots for affected golden fixtures and
  property-analysis scenarios.
- A refresh ledger under `.planning/reference-refresh-{YEAR}.md` with source
  links, checked dates, changed rows, unchanged rows, and risk notes.
- CI/test support for "decision mode": active property analysis warns or fails
  when required reference files are stale without waiver.
- Rules catalog consistency checks so `references/rules-catalog.md` cannot drift
  from `lib/rules/*.py`.

Success criteria:

- Annual refresh is a checklist a future Codex session can execute.
- A changed reference row shows exactly which affordability/property verdicts
  moved.
- No silent refreshes: data changes come with source, effective date, and impact
  summary.

### Phase 21: Verdict Quality and Ambiguity Control

**Goal:** Make GO / WATCH / NO-GO decisions precise, ranked, and useful.

Build:

- A stable verdict-reason taxonomy:
  `hard_blocker`, `cashflow_risk`, `stress_risk`, `data_gap`,
  `heuristic_estimate`, `tax_caveat`, `market_context`, `preference_mismatch`.
- Reason severity and precedence rules so the top three reasons explain the
  verdict without burying the user in raw matrix output.
- Gap-fill prompts that ask only for decision-critical missing fields, with
  defaults clearly labeled as estimates.
- Counterfactual explanations:
  "This becomes GO if down payment rises to X" or
  "This remains NO-GO even at 25% down because Y."
- Golden verdict fixtures for ambiguous cases, not just happy paths.

Success criteria:

- A WATCH verdict tells the household what to verify next.
- A NO-GO verdict identifies whether the blocker is price, cash, DTI, program
  eligibility, stress path, or data uncertainty.
- Claude narrates reasons from structured fields; it does not invent or reorder
  the decision logic.

### Phase 22: Oracle Mesh

**Goal:** Detect silent drift in commodity math and convention changes.

Build:

- Optional oracle adapters for MortgageModeler, pyloan, and public calculator
  captures where conventions match.
- A convention registry documenting units, rounding, compounding, timing, and
  known incompatibilities for each external oracle.
- Cross-source parity grids for:
  fixed amortization, ARM reset examples, refi breakeven, APR tolerance,
  points breakeven, PMI/MIP/funding-fee examples.
- Skip-unless-installed tests for optional packages; never add runtime
  dependency risk just to gain oracle coverage.
- A coverage matrix showing which calc/rule families have hand-calc,
  third-party, and engine-emitted fixtures.

Success criteria:

- External parity failures are actionable because convention mismatches are
  documented up front.
- Optional oracle absence does not break normal development.
- Any calc primitive change has at least one independent check that did not
  come from the same engine output.

### Phase 23: Decision Ergonomics

**Goal:** Make the workbench easier to use at the moment of decision.

Build:

- Saved listing comparison reports:
  "show A vs B vs C by monthly cash, cash-to-close, stress loss, tax caveat,
  and top verdict reason."
- Assumption profiles for conservative/base/aggressive scenarios, stored in
  committed examples and user-private config.
- A "why this over that" comparison mode that explains the dominant decision
  drivers without adding new valuation models.
- Watchlist summaries over persisted listings:
  GO candidates, WATCH requiring gap-fill, NO-GO with blocker reason.
- Report snapshots that preserve assumptions used at decision time, even after
  future reference-data refreshes.

Success criteria:

- The household can compare a shortlist without exporting to a spreadsheet.
- The report preserves enough assumptions that a future agent can explain why a
  past listing was accepted or rejected.
- Ergonomics stay report/CLI/skill based; no complex UI unless repeated real
  use proves it would reduce decision risk.

### Phase 24: Agent Maintenance Hardening

**Goal:** Make safe maintenance the default path for Codex and Claude.

Build:

- A maintainer runbook for common tasks:
  reference refresh, adding a predicate, adding an oracle, updating property
  fixtures, regenerating reports, and investigating verdict drift.
- A "change checklist" template that forces future agents to answer:
  six-figure filter, affected moat layer, User Layer impact, reference-data
  impact, oracle impact, and verification commands.
- Tests that detect stale roadmap/catalog links and accidental User Layer writes.
- A lightweight release checklist for milestone closure:
  full test suite, mypy, ruff, reference staleness audit, oracle coverage audit,
  and report traceability audit.
- Clear split between top-level `references/` for repo maintainers and
  `.claude/skills/mortgage-ops/references/` for skill progressive disclosure.

Success criteria:

- A future Codex session can maintain the project by following local docs and
  tests, without relying on long conversation memory.
- Claude runtime behavior remains constrained to dispatch and narration.
- Maintenance actions leave a visible audit trail in committed docs and tests.

## Non-Goals

These remain out of scope unless the six-figure-mistake test gives a concrete
reason to revisit them:

- Autonomous regulatory interpretation.
- Live scraping sophistication for its own sake.
- New generic mortgage math primitives when an oracle or maintained package can
  cover the need.
- Complex frontend/UI work.
- Zestimate-style valuation models.
- School, commute, walkability, or lifestyle scoring unless a real purchase
  decision depends on it.
- Replacing tested local math with an external dependency solely to reduce
  lines of code.

## Recommended Order

Finish v1.1 first: Phases 16-18 close reference data, pinned fixtures, and
property documentation. Then proceed in this order:

1. Phase 19 Traceability Spine.
2. Phase 20 Reference Refresh Discipline.
3. Phase 21 Verdict Quality and Ambiguity Control.
4. Phase 22 Oracle Mesh.
5. Phase 23 Decision Ergonomics.
6. Phase 24 Agent Maintenance Hardening.

This order intentionally puts auditability before usability improvements. A
slicker report is not valuable until its numbers and rules are easy to defend.

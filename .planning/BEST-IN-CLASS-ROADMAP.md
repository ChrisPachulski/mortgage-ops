# Best-in-Class Roadmap

## Positioning

`mortgage-ops` should be best-in-class for one narrow job: giving a household a
private, personalized underwriting workbench that helps it avoid bad housing
and mortgage decisions. The Pachulski household is the first concrete user, not
the limiting product boundary.

It should not be cutting edge in the general software sense. For this domain,
"cutting edge" usually means more model discretion, more live integrations,
more scraping fragility, and more maintenance burden. The target is unusual
trustworthiness plus repeatable personalization.

Upstream filter for all future work:

> Would this reduce the chance of making a six-figure housing mistake?

If yes, the work is likely strategic. If it only makes the project feel more
advanced, skip it.

## Shareable Thesis

The shareable product is not a generic mortgage calculator and not a public
underwriting oracle. The shareable product is the ability for any household to
stand up its own local, private, auditable underwriting workbench:

- Personal assumptions live in a User Layer, never in committed system code.
- Household-specific preferences become configuration and profile inputs, not
  forks of the engine.
- The rules, calculators, traceability, and report contracts are reusable.
- Codex maintains the repo and reference data; Claude guides the household
  through inputs, gap-fill, and narration.
- The default distribution must make personalization safe without leaking
  private financial data or turning the tool into compliance software.

That means public/shareable work should improve the personalization substrate:
schemas, onboarding, examples, privacy boundaries, traceability, and agent
maintenance. It should not flatten the tool into a one-size-fits-all web
calculator.

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
| Personalization substrate | Other households cannot safely adapt it | Household-specific assumptions are schema-driven, private-by-default, and easy to inspect. |
| Low-maintenance agent ops | Future agents degrade trust accidentally | Contributor rules, tests, and docs make the safe path the easy path. |

## Success Metrics

These are the steady-state quality bars.

- 100% of report-visible numbers emitted by the report formatter are traceable
  or explicitly labeled as source input, user-provided value, or heuristic
  estimate.
- 0 orphan numeric values in generated reports: report generation itself fails
  before emitting markdown when trace coverage is incomplete.
- 100% of `lib/rules/` predicates have citation, source URL, effective date,
  fixture coverage, and catalog entry.
- Reference data used for active decisions is less than 12 months stale or has a
  documented waiver.
- Every calc family has either a hand-calc oracle and an independent external
  oracle, or a documented reason external parity is impossible.
- Property reports are reproducible from persisted listing, household/profile
  inputs, reference-data versions, and code revision.
- A new household can initialize private config by copying templates without
  editing committed code or exposing private data.
- New features pass the six-figure-mistake filter before planning begins.
- Claude/Codex can run the maintenance playbook without writing User Layer
  files or inventing numbers.

## Roadmap

### Phase 18.5: Maintenance Scaffold

**Goal:** Put the agent-maintenance guardrails in place before the high-risk
traceability, oracle, refresh, and personalization work begins.

Build:

- A maintainer runbook skeleton covering reference refresh, adding a predicate,
  adding an oracle, updating property fixtures, regenerating reports, and
  investigating verdict drift.
- A "change checklist" template that every Phase 19+ implementation plan must
  answer before code changes begin: six-figure filter, affected moat layer,
  User Layer impact, reference-data impact, oracle impact, and verification
  commands.

Success criteria:

- Phase 19 and later plans are written against the checklist instead of
  retrofitting the checklist after implementation.
- Phase 26 can focus on end-state release polish, stale-link tests, and
  hardening rather than inventing the maintenance process late.

### Phase 19: Traceability Spine

**Goal:** Make every report number auditable without reading source code.

Build:

- A frozen Pydantic v2 `TraceEntry` / `TraceIndex` schema, shipped before any
  other Phase 19 implementation work and treated as a stability contract for
  Phases 20-24. The schema records:
  `display_path`, `value`, `source_kind`, `function_or_script`, `args_hash`,
  `input_field`, `reference_file`, `reference_row`, `effective`, and
  `oracle_coverage`.
- Schema rules:
  `source_kind` is an enum covering `computed`, `source_input`,
  `user_provided`, `heuristic_estimate`, and `reference_row`; `args_hash` is
  SHA-256 over sorted JSON with `Decimal` values serialized as strings at
  construction precision; `oracle_coverage` is a list of named oracle or
  fixture identifiers, empty only when the source kind documents why coverage is
  not applicable; and trace indexes include a report-scoped identifier so
  `display_path` collisions across reports cannot alias entries.
- Report-side citation footers generated from trace data, not manually composed
  strings.
- A shared reference index utility, for example `lib/reference_index.py`, that
  enumerates loaded `data/reference/*.yml` files, effective dates, source URLs,
  and contributing rows. The report manifest writer and Phase 20 refresh audit
  must both consume this utility instead of scraping reference YAML
  independently.
- A pre-emit trace coverage gate in the report formatter
  (`lib/property_report.py` or its successor) that fails report generation when
  orphan numbers are present. CI tests the gate with committed report fixtures
  and reports generated under a temporary test directory; live `reports/*.md`
  remain User/Data Layer and stay out of CI, while `scripts/audit_reports.py`
  only revalidates local reports after generation.
- A deterministic local report manifest containing code revision, listing hash,
  reference-data effective dates, and private-input fingerprints. Fingerprints
  for household/profile inputs are stored only in local private manifests or are
  computed as keyed HMACs with a local uncommitted secret; shareable reports and
  redacted manifests must omit these fields.

Success criteria:

- A committed formatter fixture test verifies every report-visible numeric token
  maps to a `TraceEntry` or to an explicit display-only/source-input tag.
- Any numeric value not traceable must be explicitly tagged as display-only
  formatting, source input, or user-provided text, and the trace coverage gate
  fails without that tag.
- The Phase 18.5 change checklist for any new report field names the added trace
  entry and test file; Claude does not need to infer provenance.
- Phases 20-24 consume the frozen trace schema rather than redefining
  provenance fields independently.

### Phase 20: Reference Refresh Discipline

**Goal:** Turn annual rule/data refresh into a repeatable, agent-safe workflow.

Build:

- `scripts/reference_refresh_audit.py` that consumes the Phase 19 reference index
  utility and reports stale files, source URLs, effective dates, and impacted
  predicates.
- Impact-diff reports: before/after snapshots for affected golden fixtures and
  property-analysis scenarios.
- A refresh ledger under `.planning/reference-refresh-{YEAR}.md` with source
  links, checked dates, changed rows, unchanged rows, and risk notes.
- CI/test support for "decision mode": active property analysis fails when
  required reference files are stale without a valid waiver, and decision mode
  is the default for the property-analysis CLI.
- A tracked waiver file at `data/reference/waivers.yml` with required fields
  `path`, `reason`, `granted_by`, `granted_on`, and `expires_on`. The staleness
  check refuses missing, malformed, or expired waivers; permissive CLI-only
  bypasses are out of scope.
- Extend the existing rules-catalog floor in
  `references/rules-catalog.md` and
  `tests/test_rules/test_citation_coverage.py` so the catalog cannot drift from
  `lib/rules/*.py`; do not create parallel citation-coverage mechanisms.

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
- Counterfactual explanations limited to the bounded axes already enumerated by
  Phase 14 and existing program matrices: down-payment percentage, 15-year vs
  30-year term, and loan program choice. Rate, income, debt, credit-score, and
  location counterfactuals are deferred until a later phase defines bounded
  search and monotonicity checks.
  Example report language:
  "This becomes GO if down payment rises to X" or
  "This remains NO-GO even at 25% down because Y."
- Golden verdict fixtures for ambiguous cases, not just happy paths.
- A backward-compatibility policy for pre-Phase-21 free-text reasons:
  tag them as `source_kind=legacy_freeform`, exclude them from precedence
  ranking, add `reason_taxonomy_version` to `analyzed_listings`, and require
  Phase 23 snapshot queries to gate on that version before using structured
  reason fields.

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

### Phase 24: Personalization Substrate

**Goal:** Make the workbench shareable by making personalization private,
schema-driven, and easy for another household to adopt.

Build:

- A first-run onboarding flow that renders templates for User Layer files:
  `config/household.yml`, `config/profile.yml`, and optional narrative
  preferences. The flow previews values and writes generated templates to a
  non-User-Layer staging path only; the user copies them into place manually.
  System code must not create, overwrite, or migrate User Layer paths.
- Strict schemas and validation messages for household income, debts, cash,
  applicants, credit assumptions, location, risk preferences, tax assumptions,
  and preferred loan programs.
- Example household profiles that are synthetic but realistic enough for tests,
  demos, and documentation.
- A migration/versioning mechanism that emits migration reports or patch
  templates for User Layer config without mutating existing User Layer files.
- A privacy audit command that extends `DATA_CONTRACT.md`, `.gitignore`,
  `.pre-commit-config.yaml`, and `scripts/hooks/block-user-layer.py`
  protections. It proves no User Layer paths are staged or committed, and its
  shareable-report mode depends on Phase 19 trace data: every `TraceEntry` with
  `source_kind=user_provided` is treated as redactable, and `--share` succeeds
  only when each redactable entry is redacted or explicitly whitelisted by the
  user.
- A "household assumptions" report section that lets users see exactly which
  personal assumptions affected a verdict.

Success criteria:

- A new household can run setup, answer guided questions, copy generated
  templates into private config, and produce a report without editing source
  code.
- All private state stays in gitignored User Layer paths by default.
- Codex can evolve schemas with migration templates; Claude can ask for missing
  values without guessing or writing config.

### Phase 25: Shareable Distribution and Demo Path

**Goal:** Package the project so other households can understand and adopt the
personalized workbench safely.

Build:

- A public-facing README path that explains: personal decision support, not
  lender underwriting, not legal/tax advice, not regulated disclosures.
- A synthetic demo dataset and fixtures that exercise property mode end-to-end
  with no real household data.
- A read-only `doctor` command that checks Python/Node/uv dependencies, missing
  config, stale references, and optional oracle availability, returning
  non-zero only for required setup or decision-mode blockers.
- A "local-first" setup guide for Codex/Claude maintainers: what agents may
  edit, what they may read, and what they must never commit.
- Redaction support for sharing a report externally without household/private
  fields.
- Release artifacts that separate reusable System/Reference layers from
  private User/Data layers.

Success criteria:

- A technically capable household can install and run the workbench locally
  using only synthetic examples before adding private data.
- Public docs make the personalization thesis obvious: users bring their own
  household assumptions; the project gives them a trusted decision structure.
- No public artifact contains Pachulski-private values.

### Phase 26: Agent Maintenance Hardening

**Goal:** Make safe maintenance the default path for Codex and Claude.

Build:

- Finalize and expand the Phase 18.5 maintainer runbook for common tasks:
  reference refresh, adding a predicate, adding an oracle, updating property
  fixtures, regenerating reports, and investigating verdict drift.
- Extend the Phase 18.5 "change checklist" template with any lessons from
  Phases 19-25 while preserving its required answers: six-figure filter,
  affected moat layer, User Layer impact, reference-data impact, oracle impact,
  and verification commands.
- Tests that detect stale roadmap/catalog links and accidental User Layer
  writes, extending the existing `DATA_CONTRACT.md`, `.pre-commit-config.yaml`,
  and `scripts/hooks/block-user-layer.py` enforcement instead of replacing it.
- A lightweight release checklist for milestone closure:
  full test suite, mypy, ruff, reference staleness audit, oracle coverage audit,
  and report traceability audit.
- Extend the existing references split documented in `CLAUDE.md`: top-level
  `references/` for repo maintainers and
  `.claude/skills/mortgage-ops/references/` for skill progressive disclosure.

Success criteria:

- A future Codex session can maintain the project by following local docs and
  tests, without relying on long conversation memory.
- Claude runtime behavior remains constrained to dispatch and narration.
- Maintenance actions leave a visible audit trail by updating the applicable
  Phase 18.5 checklist entry plus the committed doc or test named by that entry.

## Non-Goals

These remain out of scope unless the six-figure-mistake test gives a concrete
reason to revisit them:

- Autonomous regulatory interpretation.
- Live scraping sophistication for its own sake.
- New generic mortgage math primitives when an oracle or maintained package can
  cover the need.
- One-size-fits-all mortgage-calculator UX that removes household
  personalization.
- Cloud-hosted multi-tenant storage of household financial data.
- Complex frontend/UI work unless it materially improves safe household setup,
  comparison, or repeated decision use.
- Zestimate-style valuation models.
- School, commute, walkability, or lifestyle scoring unless a real purchase
  decision depends on it.
- Replacing tested local math with an external dependency solely to reduce
  lines of code.
- Agent-issued verdicts that act on the household's behalf. Verdicts are
  advisory artifacts requiring household review, not triggers for automated
  action.

## Recommended Order

Finish v1.1 first: Phases 16-18 close reference data, pinned fixtures, and
property documentation. Then proceed in this order:

1. Phase 18.5 Maintenance Scaffold.
2. Phase 19 Traceability Spine.
3. Phase 22 Oracle Mesh.
4. Phase 20 Reference Refresh Discipline.
5. Phase 21 Verdict Quality and Ambiguity Control.
6. Phase 23 Decision Ergonomics.
7. Phase 24 Personalization Substrate.
8. Phase 25 Shareable Distribution and Demo Path.
9. Phase 26 Agent Maintenance Hardening.

This order intentionally puts auditability before usability improvements. The
oracle mesh is auditability, so parity checks land before verdict-quality
calibration pins ambiguous fixtures and reason precedence. A slicker report is
not valuable until its numbers and rules are easy to defend.

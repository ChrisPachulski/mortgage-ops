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

- 100% of report-visible numbers emitted by any report or analysis markdown
  producer have a `TraceEntry` when they are computed, source input,
  user-provided, reference-backed, heuristic, or derived from private input;
  non-trace tags are reserved for pure display formatting only.
- 0 orphan numeric values in generated reports: report generation itself fails
  before emitting markdown when trace coverage is incomplete.
- 100% of `lib/rules/` predicates have citation, source URL, effective date,
  fixture coverage, and catalog entry.
- Reference data used for active decisions is applicable to the report decision
  date and is less than 12 months stale or has a documented waiver.
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
  commands. The template is shipped as
  `.planning/templates/CHANGE-CHECKLIST.md`, GSD plan generation copies it into
  each Phase 19+ `PLAN.md`, and CI compares plans against the exact template
  heading strings. Each required heading contains two to four required
  sub-prompts that appear verbatim in every copied plan. For example,
  `Reference-data impact` asks which reference files are read, which
  `effective_from` dates are crossed, and whether a waiver is added. CI
  verifies that each required sub-prompt is present and has a non-blocklisted
  answer line beneath it. The checker normalizes candidate answers by trimming
  whitespace, case-folding, and stripping punctuation before comparing against a
  closed filler blocklist that includes `tbd`, `na`, `notapplicable`,
  `seeabove`, `asabove`, `pending`, `none`, `todo`, `unknown`, and
  dash/period-only answers. After removing whitespace and any repeated
  sub-prompt text, each answer must contain at least 30 characters and at least
  one high-specificity concrete identifier matching a file path, fixture id,
  citation id, issue id, or command token. Empty answers,
  placeholder-only answers, and normalized filler fail the check. The template
  and checker publish the exact identifier grammar as named patterns:
  `FILE_PATH = (?<![\w./-])(?:\.?[A-Za-z0-9_-]+/)*\.?[A-Za-z0-9_-]+\.(py|yml|yaml|md|mjs|js|json|toml|csv|parquet|sql|txt|lock)(?![\w./-])`,
  `FIXTURE_ID = (?<![\w-])(fixture|scenario|case):[A-Za-z0-9_.-]+(?![\w-])`,
  `CITATION = (?<![\w])(?:12|24|26)\s*CFR\s*(?:\xA7|Sec\.)?\s*[0-9.]+[A-Za-z0-9().-]*`,
  `HUD_CITATION = (?<![\w-])(?:HUD\s+)?ML\s*\d{4}-\d{2}(?![\w-])`,
  `IRC_CITATION = (?<![\w])IRC\s*(?:\xA7|Sec\.)?\s*[0-9A-Za-z().-]+(?![\w.-])`,
  `FUNCTION = (?<![\w.])(?:lib|scripts|tests|orchestration)(?:\.[A-Za-z_][A-Za-z0-9_]*)+(?:\()?(?![\w])`,
  `ISSUE_ID = (?<![\w-])(?:#[0-9]+|[A-Z][A-Z0-9]+-[0-9]+)(?![\w-])`, and
  `COMMAND = (?<![\w-])(?:pytest|ruff|mypy|uv|node|npm|python|python3)\s+[-\w./:=]+`.
  `FUNCTION` matches are supporting evidence only and never satisfy the
  required concrete-identifier check by themselves; an answer containing only
  prose plus bare words or function-like names still fails unless it also
  contains one of `FILE_PATH`, `FIXTURE_ID`, `CITATION`, `HUD_CITATION`,
  `IRC_CITATION`, `ISSUE_ID`, or `COMMAND`.
  The canonical checker compiles these patterns with Python `re.compile(...)`
  from ordinary Python string values, so `\xA7` resolves to `§`; CI checklist
  enforcement is Python-only. Node tooling that needs the same grammar consumes
  a JSON fixture of pre-tested accepted/rejected literals exported by
  `scripts/dump_checklist_grammar.py` rather than recompiling the markdown
  regexes. `FILE_PATH` matches identifier text only and is exposed only through
  `scripts/checklist_grammar.py:match_file_path(text, repo_root)`, which returns
  a `ValidatedRelPath` after splitting the matched path, rejecting `.` and `..`
  components, resolving it against the repo root, and verifying realpath
  containment. Callers must use that helper result for filesystem operations and
  must not run existence checks or opens against the raw regex match.
  A sub-prompt that is genuinely out of scope may instead use the literal prefix
  `NOT_APPLICABLE: ` followed by a reason of at least 30 characters; this bypasses
  the filler blocklist and identifier requirement only for that sub-prompt and
  still fails when the reason is empty, placeholder-only, or normalized filler.
- A committed runbook coverage map at `.planning/runbook-coverage-map.yml` and a
  CI script that maps workflow code paths to required runbook files. For
  example, changes under `lib/rules/` require
  `docs/runbook/adding-predicate.md`, changes under `data/reference/*.yml`
  require `docs/runbook/reference-refresh.md`, and report generator changes
  require the report-regeneration runbook. If a PR touches a mapped path without
  touching the corresponding runbook file, CI fails with the missing runbook
  target listed explicitly.

Success criteria:

- Phase 19 and later plans are written against the checklist instead of
  retrofitting the checklist after implementation.
- The maintainer runbook is treated as a living contract: each Phase 19+ change
  that alters a covered workflow updates the runbook in the same PR, so Phase 26
  is a copyedit and audit pass rather than a backfill.
- A checklist-enforcement test fails when a Phase 19+ plan is missing any of
  the six required headings, omits a required sub-prompt, leaves a required
  sub-prompt answer empty, placeholder-only, shorter than the minimum content
  floor, lacking a high-specificity concrete identifier, or blocklisted as
  filler after normalization. Adversarial fixtures include English-only prose
  such as `We update the docs and reference files later`, which must fail even
  though it exceeds the character floor and contains tokens that look like
  function names.
- A runbook-coverage CI check fails when a Phase 19+ code or reference-data
  change omits the runbook file named by `.planning/runbook-coverage-map.yml`.
- Phase 26 can focus on end-state release polish, stale-link tests, and
  hardening rather than inventing the maintenance process late.

### Phase 19: Traceability Spine

**Goal:** Make every report number auditable without reading source code.

Build:

- A frozen Pydantic v2 `TraceEntry` / `TraceIndex` / `TraceDecimalArg` schema,
  shipped before any other Phase 19 implementation work and treated as a
  stability contract for Phases 20-24. Each model sets
  `model_config = ConfigDict(frozen=True)`, nested collections exposed on the
  models use immutable tuple forms, and a regression test proves post-
  construction mutation of any field raises. The schema records:
  `display_path`, `value`, `source_kind`, `function_or_script`, `args_hash`,
  `input_field`, `reference_file`, `reference_row`, `effective`,
  `oracle_coverage`, `sensitivity`, and `derived_from_user_input`.
- Schema rules:
  `source_kind` is an enum covering `computed`, `source_input`,
  `user_provided`, `heuristic_estimate`, and `reference_row`; `args_hash` is
  produced only through `lib/trace_canonical.py` using recursive canonical JSON:
  UTF-8 bytes, codepoint `sort_keys=True`, `separators=(",", ":")`, no trailing
  newline, explicit `None` handling as `["null", null]`, type-tagged
  dates/datetimes, NFC-normalized strings, and `Decimal` values converted
  losslessly in `decimal.Context(prec=50, Emax=999, Emin=-999)` with traps for
  invalid operation, overflow, division by zero, and invalid context. Decimals
  whose normalized coefficient length after zero-collapse and insignificant
  trailing-zero stripping exceeds the canonical context precision, or whose
  adjusted exponent is outside the `Emin`/`Emax` bounds, are rejected instead
  of rounded.
  Decimal provenance is explicit because Python `Decimal` values cannot carry
  metadata. All Decimal arithmetic that can feed trace args must be performed
  through `lib/decimal_context.py:project_decimal_arg`, which executes the
  operation under the project context and returns a `TraceDecimalArg`
  `(value, provenance="project_context_arithmetic", context_fingerprint)`.
  Plain `Decimal` values are accepted only for parsed source/reference literals
  whose provenance is declared as non-arithmetic by the caller. `TraceEntry`
  construction rejects computed trace args containing a plain `Decimal` unless
  the caller explicitly marks that path as a parsed literal, and rejects
  `TraceDecimalArg` instances whose fingerprint does not match the project
  context. Tests cover arithmetic values produced while caller contexts are 9,
  28, and 50 and prove caller precision cannot silently change accepted hashes.
  Zero-like Decimals are values where `d.is_zero()` is true, regardless of sign
  or exponent, and they are serialized as `"0"` so legitimate arithmetic
  residuals such as `Decimal("-0E-2")` do not destabilize trace hashing. All
  other finite Decimals are serialized from their sign, digit tuple, and exponent
  after stripping only insignificant trailing zeros, so equivalent values such as
  `0.065` and `0.0650` hash identically without context-driven rounding.
  A fixture proves `Decimal("0.065" + "0" * 60)` is accepted and hashes
  identically to `Decimal("0.065")`, while a value whose stripped coefficient
  still exceeds 50 digits is rejected. Canonicalization rejects non-finite
  Decimal values. `args_hash` input values
  may only be `str`,
  `int`, `Decimal`, `TraceDecimalArg`, `bool`, `date`, `datetime`, `None`,
  `list`, or recursively nested `dict[str, allowed_value]`; dictionary keys must
  be strings, so boolean,
  integer, float, Decimal, date, and other non-string keys are rejected instead
  of coerced. Unsupported input types, including `float`, `set`, `frozenset`,
  `tuple` unless the caller explicitly converts it to a list, `bytes`,
  Pydantic models, dataclasses, and enums, fail with a structured error naming
  the offending path within the args tree.
  Heterogeneous primitive
  values that would otherwise collapse in JSON must have distinct canonical
  preimages. Type tags are mandatory for every primitive: booleans serialize as
  boolean tags with literal `true`/`false`, integers serialize as integer tags,
  Decimals serialize as Decimal tags, strings serialize as string tags,
  `None` serializes as the null tag `["null", null]`, and dates/datetimes
  serialize as temporal tags. Therefore `True`, `1`,
  `Decimal("1.0")`, `"1"`, a raw string `"2025-01-01"`, and a date for
  2025-01-01 all hash differently. A fixture proves `None`, `"null"`,
  `"None"`, and `""` have distinct hash preimages. `args_hash` is computed only
  over
  function/script args; `oracle_coverage` is trace metadata and is never part of
  the hash preimage. `oracle_coverage` is stored on `TraceEntry` as an immutable
  `tuple[str, ...]` containing canonical sorted unique named oracle or fixture
  identifiers, validated at construction and normalized for storage/reporting so
  order-only differences cannot change coverage reporting. Computed values backed
  by committed golden fixtures start with
  `hand_calc:<fixture>`, Phase 22 appends third-party oracle identifiers, and
  the list may be empty only for
  `source_input`/`user_provided`/`heuristic_estimate`/`reference_row` values
  whose source kind documents why coverage is not applicable. Fixture-emitted
  trace entries must be constructed with `emitter="hand_calc:<fixture>"`; all
  non-fixture emitters pass `emitter=None`. Constructor validation rejects
  duplicates, unknown identifier syntax, and any fixture emitter that appears in
  its own `oracle_coverage` before emission, and a regression fixture covers
  that self-reference path. `sensitivity`
  classifies trace values as public or private. Trace writers must set it
  explicitly for `source_input`, `user_provided`, and `heuristic_estimate`
  entries; reference rows default to public unless their catalog entry marks
  them private, and computed entries derived from user input default to private.
  The trace emission gate uses one shared function,
  `lib/trace_emit.py:check_sensitivity_propagation`, and fails on unset
  sensitivity when `source_kind` is `source_input`, `user_provided`, or
  `heuristic_estimate`; when `derived_from_user_input=true`; or when any parent
  entry in the `TraceEntry.derive` chain has `sensitivity=private`. The gate
  walks the constructor-created parent chain, rejects cycles, and raises if any
  child with private ancestry or `derived_from_user_input=true` is not
  `sensitivity=private`. Downgrading such a value to `public` is allowed only
  through a dedicated audited declassification API that records an explicit
  reason and has regression tests covering the redaction impact. The committed
  audit artifact is `references/declassification-log.md` and may contain only
  trace `display_path`, a non-sensitive justification slug, reviewer, and date;
  full household-specific reasons stay in a gitignored User Layer audit file
  referenced by local manifest fingerprint. A privacy fixture proves private
  values and free-form household context cannot appear in the committed log.
  `derived_from_user_input` is true when a value directly or transitively
  depends on User Layer inputs rather than only when its own `source_kind` is
  `user_provided`; computed trace entries must be created through
  `TraceEntry.derive(parent_entries, ...)` in `lib/trace_canonical.py`, which
  OR-folds the flag across parents, and the gate rejects computed entries
  constructed without that derivation metadata. Trace indexes include a
  report-scoped identifier so `display_path` collisions across reports cannot
  alias entries.
- Report-side citation footers generated from trace data, not manually composed
  strings.
- A shared reference index utility, for example `lib/reference_index.py`, that
  enumerates loaded `data/reference/*.yml` files, effective dates, source URLs,
  and contributing rows. The report manifest writer and Phase 20 refresh audit
  must both consume this utility instead of scraping reference YAML
  independently. CI includes an AST/import-graph lint that scans every `.py`
  file under `lib/`, `scripts/`, and `tests/`, excluding
  `lib/reference_index.py` and exact paths listed in
  `.planning/reference-index-allowlist.yml`. The lint is a decidable
  defense-in-depth check, not a proof of all possible runtime paths: it fails
  when unauthorized code contains a string literal, f-string literal segment, or
  joined `pathlib`/`os.path.join` component sequence that normalizes to the
  substring `data/reference/`; imports or re-exports a reference-data path
  constant for use outside the shared index; imports `yaml` in a module that
  also constructs, reads, or parses `data/reference/*.yml`; calls
  `yaml.safe_load` on bytes/text read from a reference `.yml` path in
  unauthorized code; or performs reference `.yml` globbing/reads without an
  exact allowlist entry. The checker ignores module, class, and function
  docstrings, and ignores triple-quoted explanatory strings inside blocks marked
  with `# noqa: REF-INDEX`; those exclusions are documented next to the lint
  rule so ordinary documentation can name `data/reference/` without becoming a
  data-access bypass. Unrelated YAML usage for user config, fixtures, and
  planning metadata remains allowed through safe loaders and its own tests; only
  reference YAML access must go through `lib/reference_index.py`. Decision-mode
  startup for every report generator and analysis CLI imports
  `lib/reference_index.py` before loading rules or reports; that module installs
  one process-wide narrow runtime trap based on Python `sys.addaudithook` `open`
  events, filtered to resolved `data/reference/*.yml` paths and the exact
  authorized caller paths. Startup asserts the trap is installed and aborts
  decision-mode execution if the assertion fails. It fails unauthorized reference
  YAML opens without
  monkey-patching `open`, `io.open`, `Path.open`, `Path.read_text`, `os.open`,
  or stdlib internals, catching common variable indirection and helper-module
  bypasses that static analysis misses. Test fixtures also install the same trap
  during unit and integration runs, and an end-to-end regression invokes the
  production CLI with `python -m ... --decision-mode` to prove the hook is active
  outside pytest. The trap is defense-in-depth, not
  exhaustive: file descriptors opened before trap installation and native
  extensions that bypass Python audit events remain outside its guarantee and
  are covered by static lint and code review. A negative fixture proves
  `tempfile`, `subprocess`, pytest collection, and unrelated YAML fixture reads
  still work while the trap is active. Node orchestration code is not
  allowed to read reference YAML directly:
  `.mjs`/`.js` files must call the Python reference-index command/API for
  reference metadata, and CI rejects direct `fs` YAML reads, `yaml` package
  imports, or `data/reference` path construction outside an explicit
  Node-side allowlist entry. Allowlist entries are exact file paths, never globs,
  and approved test fixtures must still exercise the shared staleness and
  applicability checks. The reference index utility owns an explicit
  `control_plane_files = {"waivers.yml"}` set. Files in that set never appear
  in `rows()` and are never subject to reference-row sensitivity enforcement;
  they are exposed through a separate `control_metadata()` API used by the
  Phase 20 refresh audit to validate waiver owners, reasons, and expiry dates.
- A shared pre-emit trace coverage gate, for example `lib/trace_emit.py`, used by
  every markdown/report producer including `lib/property_report.py`, refi NPV,
  amortization, ARM simulation, and stress-test output. It fails generation when
  orphan numbers are present. The schema document defines the numeric-token
  grammar the gate enforces: money, percentages, ratios, signed or unsigned raw
  decimals, and thousands-separated quantities in report body/table text require
  trace entries; ISO dates, regulatory citation IDs, heading anchors, fixture
  identifiers, schema versions, street addresses, zip codes, footnote markers,
  and fixed UI strings are exempt only when emitted through renderer-owned
  display-token APIs or wrapped in an explicit `<num-exempt kind="...">...</num-exempt>`
  span whose `kind` is in a closed allowlist and whose kind-specific structured
  attributes validate the exemption. For example, `kind="footnote_marker"`
  requires a `marker` attribute matching a known renderer-owned footnote table,
  and `kind="schema_version"` requires a manifest schema field name and value.
  The gate rejects any `<num-exempt>` token that matches money, percentage, or
  ratio grammar unless that exact token shape is whitelisted for that exemption
  kind and renderer. CI tests the gate with committed fixtures for each
  producing script and reports generated under a temporary test directory; live
  `reports/*.md` remain User/Data Layer and stay out of CI.
- Refactor `scripts/refi_npv.py`, `scripts/amortize.py`,
  `scripts/arm_simulate.py`, and `scripts/stress_test.py` so every
  report-visible number is represented by a `TraceEntry` and emitted through
  `lib/trace_emit.py`. Each script gets a committed fixture test proving the
  pre-emit gate fails on an orphan-number regression.
- Report renderers are pure functions of trace data and code: no wall-clock
  timestamps, current-working-directory-dependent formatting,
  locale-dependent number formatting, hash-seed-sensitive iteration, platform
  line-ending drift, or environment-dependent paths in generated report text.
  A fixture renders the same report twice under different environment settings
  and requires an empty diff.
- `scripts/audit_reports.py` is a local audit tool for reports generated before
  the pre-emit gate existed or for explicitly non-decision/dev-mode output; it
  is not a substitute for the shared gate and cannot bless decision-ready
  reports that failed pre-emit validation. Every Phase 19+ report producer sets
  `manifest_schema_version: 1` in its JSON manifest, and
  `manifest_schema_version` is a JSON integer greater than or equal to 0.
  Non-integer values, including string `"1"`, float `1.0`, and `null`, or
  negative integer values such as `-1`, cause `scripts/audit_reports.py` to exit
  `3` with an error naming the offending manifest file; unit tests cover all
  malformed values plus the `-1`, `0`, and `1` boundaries. A report blessing
  requires a version-1-or-newer manifest with both `pre_emit_gate_passed: true`
  and `decision_mode: true`. When no manifest is present, or when a manifest is
  present with `manifest_schema_version: 0`, `scripts/audit_reports.py` exits
  with code `2` to signal genuine legacy or explicitly non-decision/dev-mode
  inspection without decision-use blessing. When
  `manifest_schema_version >= 1` but `pre_emit_gate_passed` or `decision_mode`
  is missing or false, the tool exits with code `3` to signal a broken Phase
  19+ producer that must be investigated. Ordinary audit failures, such as a
  legacy report containing unblessed orphan numbers, exit with code `1`. The
  complete exit-code contract is `0=ok`, `1=ordinary audit failure`,
  `2=legacy/no-manifest/dev-mode-only inspection without decision blessing`,
  and `3=broken Phase 19+ producer`.
- A deterministic local report manifest containing code revision, listing hash,
  reference-data effective dates, and private-input fingerprints. Fingerprints
  for household/profile inputs are stored only in local private manifests or are
  computed as keyed HMACs with a local uncommitted secret; shareable reports and
  redacted manifests must omit these fields. The HMAC key is generated on first
  run with `secrets.token_bytes(32)`, stored outside the repo, and never
  committed. Key resolution uses exactly one path: if `$XDG_CONFIG_HOME` is set,
  non-empty, and absolute, use
  `$XDG_CONFIG_HOME/mortgage-ops/fingerprint.key`; if it is unset or empty, use
  `~/.config/mortgage-ops/fingerprint.key`; if it is set to a relative path,
  fail with a clear configuration error. The resolved key path and resolved repo
  root must not be equal, and the key path must not resolve under the repo root,
  including through symlinked `$XDG_CONFIG_HOME` components. The loader never
  searches both locations or falls back silently after choosing a path. On POSIX,
  the key-owned `mortgage-ops` parent directory is created and
  then opened once with `O_DIRECTORY | O_NOFOLLOW`; the opened directory file
  descriptor is verified with `fstat` as a non-symlink directory owned by the
  current user with mode `0700` before the key is touched; the implementation
  never requires `$XDG_CONFIG_HOME` or `~/.config` itself to be `0700`. Key
  creation and reads use `os.open(..., dir_fd=parent_fd)` on basenames only.
  Creation writes a same-directory temporary file with a random suffix using
  `O_CREAT | O_EXCL | O_WRONLY | O_NOFOLLOW` and mode `0600`, writes all 32 bytes
  with a checked full-length write, `fsync`s the temporary key file, publishes it
  with `linkat`/`os.link` from the temporary basename to `fingerprint.key` so an
  existing final key is never overwritten, re-`fstat`s the parent directory fd and
  verifies its device/inode still match the originally opened parent before
  treating the key as published, `fsync`s the parent directory, closes the
  descriptor, and unlinks the temporary file on success or failure. If the
  post-publish parent check fails, creation unlinks the temporary name when still
  present, refuses to use the new key, and fails loudly. Platforms
  may use `renameat2(RENAME_NOREPLACE)` only with a tested fallback to the link
  publish path; plain POSIX `rename` is forbidden for publishing the final key
  because it can overwrite a concurrent winner. If first-run creation loses the
  publish race because `fingerprint.key` already exists, the loser follows the
  read path with bounded retry/backoff for up to one second so it cannot consume
  an empty or partial file while the winner is still publishing. Reads use
  `O_RDONLY | O_NOFOLLOW`. After opening and
  reading the key, the
  implementation verifies the key inode is a regular file owned by the current
  user with mode `0600`, verifies the parent directory inode still matches the
  originally opened parent fd, and requires the key contents to be exactly 32
  bytes. Empty, short, or longer files are treated as corrupt partial-write
  artifacts and fail loudly before fingerprints are computed; if the bad file is
  a leftover `fingerprint.key.*.tmp` temporary file older than the bounded retry
  window, the loader unlinks it before retrying creation, but it never deletes or
  overwrites a corrupt final `fingerprint.key` without an explicit user command.
  The error message for a corrupt final key names the path, reports
  `expected 32 bytes, found N`, and includes both recovery choices: run
  `truncate -s 32 <quoted-path>` only when the extra bytes are confirmed
  trailing whitespace, or run `rm <quoted-path>` to delete and regenerate the key
  after confirming no other process is creating it. The rendered commands use
  `shlex.quote(path)` for POSIX shell display, and a unit test covers a resolved
  path containing a single quote, a space, and `$`.
  Any broader permission, parent-swap mismatch, pre-existing symlink,
  non-regular file, or insecure key-owned parent directory fails loudly before
  fingerprints are computed. On
  Windows, the key resolves to
  `%LOCALAPPDATA%\mortgage-ops\fingerprint.key` only if the implementation sets
  an explicit current-user-only ACL, for example via `pywin32`; otherwise the
  fingerprint feature refuses to run with a clear unsupported-platform message.
  Production decision-mode reports are POSIX-only until that ACL-backed Windows
  path exists. On Windows without explicit ACL support, manifest generation
  disables fingerprints and omits `private_input_fingerprints` entirely, rather
  than writing `null` or an empty object, only for non-decision/dev-mode output.
  Snapshot replay treats any snapshot manifest that contains private-input
  fingerprints as requiring fingerprint capability; replay on an unsupported
  Windows host fails with the same unsupported-platform message instead of
  reproducing a fingerprintless manifest.
  Losing the key makes historical private fingerprints incomparable. Rotation is
  an explicit user action: `fingerprint.key` is always the current key, and
  retained historical keys live under the same key-owned parent in
  `keys/<UTC-basic-timestamp>-<old-key-sha256-prefix>.key`, for example
  `keys/20260524T173000Z-1a2b3c4d5e6f.key`. The `keys/` directory uses the same
  owner, mode, symlink, regular-file, `O_NOFOLLOW`, and repo-containment checks
  as the active key parent. Manifest comparison reads the current key and all
  retained keys whose metadata fingerprint can match the manifest key id.
  `prune-old-keys` deletes only retained `keys/*.key` files older than the
  user-specified retention window and never deletes `fingerprint.key` without a
  separate rotate command; multi-machine consistency is out of scope unless the
  user manually installs the same key set on each machine.
- A hash-stability test for `lib/trace_canonical.py` with explicit buckets:
  equivalent cases include nested inputs, `Decimal("0.065")` and
  `Decimal("0.0650")`, Unicode canonical equivalents after NFC normalization,
  unsigned and signed zero variants such as `Decimal("0E+10")`,
  `Decimal("0.00")`, and `Decimal("-0E-2")`, and caller process contexts with
  `getcontext().prec` set to 9, 28, and 50; distinct cases include string-vs-date
  and string-vs-numeric values; rejected cases include non-string dictionary
  keys, bool keys, tuples, high-precision Decimal values longer than the
  canonical context, adjusted exponents outside the canonical bounds, and
  non-finite Decimal boundary cases. Distinct buckets also prove `True`, `1`,
  `Decimal("1.0")`, and `"1"` all produce different hashes, and arithmetic
  Decimal buckets prove caller context precision cannot silently change accepted
  trace hashes. The fingerprint-key tests pre-create the
  POSIX key path and parent path as symlinks and require both creation and read
  attempts to fail loudly without following the link. They also simulate two
  first-run processes racing key creation, an orphaned temporary key file, and a
  corrupt final short-key file and a 33-byte final key with a trailing newline;
  the loser must retry until it reads exactly 32 bytes, orphaned temporary files
  must be cleaned after the retry window, and corrupt final keys must fail with
  the remediation message. Key-path fixtures
  require `XDG_CONFIG_HOME=""` to resolve to the home
  fallback, reject `XDG_CONFIG_HOME="relative/path"`, and reject an absolute or
  symlinked XDG config path that resolves inside the repo.
- `oracle_coverage` tests verify constructor-time sorting and deduplication
  rejection, prove two traces differing only in coverage order produce the same
  normalized coverage list, prove two traces with identical function args but
  different coverage annotations produce the same `args_hash`, and reject a
  hand-calc fixture trace entry that lists itself as covered by its own fixture id.

Success criteria:

- Committed fixture tests for each report-producing script verify every
  report-visible numeric token maps to a `TraceEntry` unless it is pure display
  formatting.
- Any numeric value not traceable must be explicitly tagged as display-only
  formatting only through the closed display-token classes defined by the
  numeric-token grammar. User-provided values, source inputs, reference rows,
  heuristic estimates, and values derived from private input require
  `TraceEntry` records; the trace coverage gate rejects private or source-input
  bypass tags and rejects any display-only tag whose token text or `kind` falls
  outside the allowlist.
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
- `scripts/reference_impact_fixtures.py` produces before/after verdict diffs
  against committed `tests/fixtures/property_listings/*.yml`, runs in CI, and
  writes committable output for review.
- `scripts/reference_impact_local.py` produces before/after verdict diffs
  against local `data/analyzed_listings.duckdb` household data; its output stays
  gitignored User/Data Layer material and never runs in CI.
- A refresh ledger under `.planning/reference-refresh-{YEAR}.md` with source
  links, checked dates, changed rows, unchanged rows, and risk notes.
- CI/test support for "decision mode": active property analysis fails when
  required reference files are stale without a valid waiver or when a referenced
  row is not applicable to the report decision date, and decision mode is the
  default for the property-analysis CLI.
- A tracked waiver file at `data/reference/waivers.yml` with required fields
  `path`, `reason`, `granted_by`, `granted_on`, and `expires_on`. The staleness
  check requires a waiver only when a reference file is stale, defined as more
  than 12 months after its `effective` date. For stale files, absent, malformed,
  or expired waivers cause failure; non-stale files do not require waivers.
  Waiver paths are exact normalized POSIX relative file paths under
  `data/reference/`; globs, absolute paths, backslashes, `..` components,
  leading `./`, symlinks, and realpaths outside `data/reference/` are rejected.
  The loader normalizes paths before duplicate detection by stripping redundant
  separators, rejecting nonexistent waiver targets with the offending waiver line,
  computing the repo-relative realpath, and comparing `os.path.normcase` of that
  realpath where the filesystem is case-insensitive, so variants such as
  `./data/reference/x.yml` or mixed-case aliases cannot create
  duplicate-equivalent waivers. The waiver loader rejects entries where
  `granted_on > expires_on`, where `granted_on` is in the future, or where two
  entries share the same normalized path, and it reports the offending waiver
  line instead of surfacing a generic staleness failure.
  Freshness and decision-date applicability are separate checks: the reference
  index records `effective_from`/`effective_to` or superseded metadata for rows,
  rejects future-effective rows unless an explicit simulation mode is selected,
  and includes boundary fixtures around annual rule-change dates. Permissive
  CLI-only bypasses that still claim decision-ready output are out of scope. A
  documented non-decision development mode, exposed as
  `--no-decision-mode` or `MORTGAGE_OPS_DEV_MODE`, may downgrade
  stale-reference failures to warnings only when generated manifests are tagged
  `decision_mode: false`. The environment variable enables dev mode only when
  set to exactly ASCII `1`, `true`, `yes`, or `on`, case-insensitive and with no
  leading or trailing whitespace; `0`, `false`, `no`, and `off` are explicit
  opt-outs equivalent to unset, and an empty value is treated as unset. Parsing
  first encodes the value as ASCII with strict errors and rejects non-ASCII
  input, embedded NUL bytes, Unicode lookalikes such as fullwidth digits, and
  any value whose stripped form differs from the original; only then does it
  apply locale-independent lowercase comparison against the closed ASCII token
  sets. Strict rejection of every other non-empty value, such as `maybe`, `2`, or
  whitespace-only strings, applies only to commands that consult decision/dev
  mode, such as analysis, report generation, `scripts/audit_reports.py`, and
  snapshot replay. The accepted true/false sets are implemented once in
  `lib/env_flags.py:is_truthy(name)` and reused by every privacy- or
  safety-relevant environment flag, including
  `MORTGAGE_OPS_AUDIT_ACK_REPO_STAGING`.
  Fuzz fixtures cover embedded NUL bytes, non-ASCII fullwidth digits, Unicode
  case lookalikes, and whitespace variants.
  Read-only discovery paths such as `--help` and `--version` parse argv first,
  report an unrecognized `MORTGAGE_OPS_DEV_MODE` as a warning, and continue
  unless the command is explicitly checking decision-mode blockers. The
  `doctor` command is a blocker-checking command, so it uses strict env-flag
  parsing and exits non-zero for an unrecognized decision/dev-mode value.
  Every markdown report generated in that mode must include the visible
  blockquote banner
  `> DEV MODE - REFERENCE DATA IS STALE - NOT FOR DECISION USE` after any UTF-8
  BOM and YAML front matter, within the first five non-blank content lines, and
  before the first non-banner heading or body paragraph. CI parses markdown
  structure rather than byte-matching the file prefix, verifies the banner is
  present in dev-mode fixtures, absent in decision-mode fixtures, and that
  `MORTGAGE_OPS_DEV_MODE` is unset in decision-mode test jobs. Dev-mode parser
  tests cover every accepted true value, every explicit false value, and a
  representative set of rejected unparseable values.
- Extend the existing rules-catalog floor in
  `references/rules-catalog.md` and
  `tests/test_rules/test_citation_coverage.py` so the catalog cannot drift from
  `lib/rules/*.py`; do not create parallel citation-coverage mechanisms.
  The existing rules catalog gains a `sensitivity: public | private` column for
  each predicate row it already indexes. Reference YAML row schemas separately
  require an explicit `sensitivity: public | private` field with no default, and
  CI fails when any decision reference row in `data/reference/*.yml` omits it.
  `data/reference/waivers.yml` is excluded from reference-row sensitivity
  enforcement and reference-row catalog generation because it is control-plane
  metadata, not decision reference data. The reference index's
  `control_plane_files = {"waivers.yml"}` exclusion is the only allowed waiver
  bypass: `waivers.yml` entries are visible through `control_metadata()` for
  expiry auditing, but never through `rows()` or `row.sensitivity` loading. A new
  `references/reference-row-catalog.md` maps each reference row identifier to
  its sensitivity when row-level YAML metadata is not sufficient. The Phase 19
  reference index utility exposes `row.sensitivity` from the reference-row
  YAML/catalog source, not from `references/rules-catalog.md`, so trace defaults
  and share redaction do not infer privacy from free-form notes. Share-mode
  regression tests prove an omitted reference-row sensitivity fails loading
  before report generation rather than being emitted as public, and that
  `data/reference/waivers.yml` does not trip that gate while still being audited
  for waiver expiry through `control_metadata()`.

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
- A `VerdictReason` Pydantic model whose `reason_kind` is one of the taxonomy
  values or `legacy_free_text`, with `reason_text: str`, `severity: int`, and
  `precedence: int`. Structured reasons are stored in the
  `analyzed_listings.verdict_reasons` JSON field. The forward-only migration is
  executed through `orchestration/db-write.mjs` under the existing lockfile.
  Project DuckDB versions are pinned to a build with the JSON extension
  available from the local installation; migration code runs `LOAD json` only
  and never runs `INSTALL json`. If `LOAD json` fails,
  the migration exits with an error naming the pinned DuckDB version and the
  required local extension/cache path. To stay compatible with DuckDB `ALTER
  TABLE` limitations, the migration first adds nullable/default-free
  `verdict_reasons JSON` and `reason_taxonomy_version INTEGER` columns, backfills
  every existing row to `verdict_reasons='[]'` and
  `reason_taxonomy_version=0`, validates that no `NULL`, invalid JSON, or
  non-array JSON value remains, then rebuilds and atomically swaps
  `analyzed_listings` with a table that declares `verdict_reasons JSON NOT NULL
  DEFAULT '[]' CHECK (json_valid(verdict_reasons) AND
  json_type(verdict_reasons) = 'ARRAY')` and
  `reason_taxonomy_version INTEGER NOT NULL DEFAULT 0`. Existing rows remain
  version `0`, and new structured rows write version `1`. Migration tests prove
  the nullable-add/backfill/rebuild path succeeds against existing rows and that
  the post-migration table contains zero `NULL` verdict-reason or taxonomy
  values; they do not accept a branch where `verdict_reasons` remains `NULL`
  after backfill. The migration records step completion in a durable migration
  version table inside the same DuckDB file before releasing the lock, and
  startup resumes from the recorded step rather than assuming a never-migrated
  database. Each step is idempotent: re-running after failure between nullable
  add, backfill, validation, rebuild, and atomic swap either observes the
  completed step or completes it without data loss. Regression tests inject a
  failure between each pair of steps and prove the next invocation finishes with
  the final NOT NULL/CHECK-constrained table.
  `db-write.mjs` asserts before INSERT/UPDATE that `verdict_reasons` is a JSON
  array literal and that
  `reason_taxonomy_version` is never explicitly `NULL`. Unit tests prove direct
  DB-layer inserts of `NULL`, invalid JSON, non-array JSON, and
  `reason_taxonomy_version=NULL` fail, including a non-array valid JSON literal
  that confirms the JSON extension-backed `json_type` check is active.
  `verdict_reasons` is always a JSON array, never `NULL`; absence of structured
  reasons is represented as `[]`.
- Reason severity and precedence rules so the top three reasons explain the
  verdict without burying the user in raw matrix output.
- Gap-fill prompts that ask only for decision-critical missing fields, with
  defaults clearly labeled as estimates.
- Counterfactual explanations limited to the bounded axes already enumerated by
  Phase 14 and existing program matrices: down-payment percentage, 15-year vs
  30-year term, and loan program choice. Rate, income, debt, credit-score, and
  location counterfactuals are deferred until a later phase defines bounded
  search and monotonicity checks. The explanatory "because" clause may reference
  fixed, read-only constraints such as the current DTI cap or program limit, but
  it must not search or vary any deferred axis. When `decision_mode: false`, any
  reference-derived number in that clause must carry an inline stale-reference
  marker naming the source file and effective date, using the machine-parseable
  XML-empty-element form
  `<stale source="atr-qm-thresholds.yml" effective="2024-01-01"/>`; `source` must
  be XML-escaped and match the reference filename grammar
  `[A-Za-z0-9_.-]+\.ya?ml`, the same basename character set accepted by the
  reference-index `FILE_PATH` lexicon. If the cited row cannot be identified precisely,
  counterfactual generation is suppressed with
  `counterfactual analysis suppressed: reference data is stale`.
  Example report language:
  "This becomes GO if down payment rises to X" or
  "This remains NO-GO even at 25% down because the fixed DTI cap is still
  exceeded." In non-decision/dev-mode output, the second sentence must inline
  the stale marker immediately after the reference-derived cap value. A report
  pipeline fixture parses and re-emits the stale marker and proves it round-trips
  without corruption.
- Golden verdict fixtures for ambiguous cases, not just happy paths.
- A backward-compatibility policy for pre-Phase-21 free-text reasons:
  preserve them outside `TraceEntry.source_kind` as `reason_kind=legacy_free_text`
  with `reason_taxonomy_version=0`, exclude them from precedence ranking, add
  `reason_taxonomy_version` to `analyzed_listings`, and require Phase 23 snapshot
  queries to verify the snapshot-pinned `reason_taxonomy_version` before reading
  `verdict_reasons`.

Success criteria:

- A WATCH verdict tells the household what to verify next.
- A NO-GO verdict identifies whether the blocker is price, cash, DTI, program
  eligibility, stress path, or data uncertainty.
- Claude narrates reasons from structured fields; it does not invent or reorder
  the decision logic.
- A freshly migrated database with version-0 rows and empty `verdict_reasons`
  still produces a valid report through the existing reader path without
  iterating over `NULL`.

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
- `tests/test_calc_primitives_have_fixtures.py` enumerates the public
  calculation primitives in `lib/amortize.py`, `lib/apr.py`, `lib/refinance.py`,
  `lib/affordability.py`, `lib/stress.py`, `lib/arm.py`, and `lib/points.py`
  and asserts each appears in at least one `tests/fixtures/hand_calc/*.yml`
  fixture with a citation field.

Success criteria:

- External parity failures are actionable because convention mismatches are
  documented up front.
- Optional oracle absence does not break normal development.
- Every calc primitive has a committed hand-calc golden-value fixture with a
  citation, and CI requires that always-on fixture.
- Where conventions match, each calc primitive also has a skip-unless-installed
  third-party parity test; absence of optional oracle packages is informational
  and never counts as coverage by itself.

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
  future reference-data refreshes. Snapshots include the pinned code revision,
  reference-data versions, `snapshot_schema_version`, a hash of User Layer state,
  the snapshot-pinned `reason_taxonomy_version`, any forward-only DB schema
  version read by the report, and all User Layer inputs needed to reproduce the
  report without reading mutable local private files. Snapshots also embed the
  relevant `analyzed_listings` row or rows used by the report, including
  `verdict_reasons` and listing notes when present, with per-row hashes and a
  schema-versioned serialization so replay never depends on mutable local DuckDB
  listing state.
  Snapshot files are private Data/User Layer artifacts stored only under
  `reports/snapshots/private/` by default; that path is added to
  `DATA_CONTRACT.md`, `.gitignore`, `.pre-commit-config.yaml`,
  `scripts/hooks/block-user-layer.py`, and the Phase 24 privacy audit. Any
  committed snapshot fixture must be synthetic or redacted and must not contain
  real household income, debts, cash, preferences, or listing notes.
  `scripts/replay_snapshot.py <snapshot.json>` is inspect-only by default for
  every snapshot: it validates the snapshot schema, pinned revision, reference
  data, and embedded input hashes but does not check out or run code. Execution
  requires explicit `--trusted --execute` for every snapshot and then refuses to
  run unless the pinned revision is reachable from a signed release tag already
  present locally or the snapshot carries a detached signature from a key
  registered in local user config. Reachability from mutable branches such as
  `origin/main` is inspect-only unless the reachable commit or ref is signed by a
  configured trusted key; no replay command fetches remote revisions
  automatically. Trust means signed provenance from a configured key, not branch
  reachability. The executable replay sequence is fixed: first verify signed-tag
  reachability or the detached snapshot signature using only the current trusted
  checkout and local metadata; second print the exact commit hash, author,
  signature or signed-ref verification result, and diffstat from the signed base
  and require an interactive `y/N` confirmation; third, and only after that trust
  gate succeeds, create the temporary pinned checkout and invoke its compatibility
  probes; fourth materialize embedded state; fifth run the replay. Invoking
  pinned-code probes is code execution, so no `--print-*` probe may run before
  signature verification and user confirmation. Unsigned snapshots from
  unprotected revisions remain inspect-only. Inspect-only replay never requires a
  clean source worktree because validation reads only the snapshot and local
  metadata, not mutable checkout files. Snapshots record
  `replay_protocol_version: 1`; the temporary checkout of the pinned code must
  expose `--print-replay-protocol-version` and return a compatible integer
  greater than or equal to the snapshot version. It must also expose
  `--print-snapshot-schema-compat-version` and return an integer greater than or
  equal to the snapshot's `snapshot_schema_version`; pinned revisions without the
  marker, with junk or non-integer output, with an older replay protocol, or with
  an older snapshot-schema compatibility version are non-replayable by design and
  abort with the incompatible schema/taxonomy non-zero exit before any embedded
  state is materialized. Regression fixtures cover a pinned revision whose
  `--print-replay-protocol-version` exits 0 with junk output, and a pre-Phase-21
  pinned revision without `verdict_reasons`/snapshot-schema compatibility support,
  and both must fail after the trust gate but before state materialization.
  Execution uses a unique temporary `git worktree add` checkout path containing
  the host identifier, PID, monotonic timestamp, and short snapshot hash. Before
  execution, replay refuses to proceed
  when the source worktree has modified, staged, deleted, renamed, copied, or
  unmerged tracked paths; ignores untracked files that are already gitignored;
  fails on untracked non-ignored files by default with the offending paths
  printed; and allows them only when the user passes `--allow-untracked` after
  reviewing that path list. Replay never
  writes embedded inputs to standard User Layer paths. Instead, replay
  materializes the embedded `user_layer_state` block into a repo-external
  temporary state directory created in the same cleanup scope as the replay
  worktree and passes explicit config-path overrides to the
  pinned code. `user_layer_state` keys are a closed enum of allowed User Layer
  relative paths such as `config/household.yml`, `config/profile.yml`, and
  configured narrative preference files; replay rejects any unknown key, `..`
  component, leading slash, `~`, Windows drive letter, absolute path, symlink, or
  resolved realpath outside the temporary state directory before writing any
  file. All YAML deserialization of snapshot-embedded `user_layer_state` uses
  `yaml.safe_load` exclusively on already schema-bounded values; `yaml.load`,
  `yaml.full_load`, and custom-object constructors are forbidden anywhere
  snapshot-derived bytes flow. A regression fixture with a
  `!!python/object` payload must fail before any materialized file write, hash
  check, checkout, or execution. Replay refuses to execute snapshots without
  `user_layer_state`, verifies the hash of each materialized input against the
  snapshot before running code, materializes embedded listing rows into a
  temporary DuckDB database with the snapshot schema version, verifies each row
  hash before report generation, and never reads current User Layer files or
  current `data/analyzed_listings.duckdb` from disk. Before reading
  `verdict_reasons`, replay verifies that the pinned code declares snapshot
  schema compatibility for the snapshot's embedded listing-row serialization and
  `min_supported_reason_taxonomy_version` and
  `max_supported_reason_taxonomy_version`, and that the snapshot-pinned
  `reason_taxonomy_version` falls inside that inclusive range; snapshots below
  the minimum or above the maximum abort non-zero. Fixtures cover supported v0,
  supported v1, below-minimum, and above-maximum taxonomy versions. Replay removes
  the temporary checkout with `git worktree remove --force` and removes the
  temporary state directory in `try/finally` and `SIGTERM`/`SIGINT`/`SIGHUP`
  handlers. Temporary User Layer materialization cleanup best-effort overwrites
  regular files before unlinking where the platform permits, then unlinks files
  and directories even after replay exceptions. Each replay worktree and
  temporary state directory records PID,
  process creation time, host identifier, wall-clock UTC creation timestamp,
  optional monotonic timestamp, and snapshot hash in a sidecar file. Each replay
  invocation uses the wall-clock UTC timestamp for the 24-hour stale-worktree
  decision and uses the monotonic timestamp only for in-process ordering or
  diagnostics. It prunes stale replay worktrees and replay state directories
  older than 24 hours only when
  the recorded PID is absent or the live process creation time/host identifier
  does not match the sidecar, so PID reuse cannot keep a dead checkout or
  materialized private-state directory indefinitely. If the recorded process
  still matches, or if `git worktree add` or state-directory creation fails
  because a stale path still exists, replay reports the path, recorded host and
  PID when available, and a remediation message to rerun after that process exits
  or remove the stale replay directory only after confirming the process is gone,
  then exits non-zero instead of reusing it. If the revision, trusted
  provenance, or inputs are unavailable, replay fails loudly instead of silently
  continuing into execution.

Success criteria:

- The household can compare a shortlist without exporting to a spreadsheet.
- The report preserves enough assumptions that a future agent can explain why a
  past listing was accepted or rejected.
- Snapshots are replayable: `scripts/replay_snapshot.py <snapshot.json>`
  verifies pinned code, embedded listing state, inputs, reference data,
  `snapshot_schema_version`, and `reason_taxonomy_version` reproduce
  bit-identical results or exits non-zero with the missing prerequisite or
  incompatible schema/taxonomy version.
- Snapshot privacy tests prove real snapshot output lands only in ignored
  private paths, synthetic/redacted fixtures are the only committed snapshots,
  and the pre-commit hook plus privacy audit block repo-local private snapshots.
- Ergonomics stay report/CLI/skill based; no complex UI unless repeated real
  use proves it would reduce decision risk.

### Phase 24: Personalization Substrate

**Goal:** Make the workbench shareable by making personalization private,
schema-driven, and easy for another household to adopt.

Build:

- A first-run onboarding flow that renders templates for User Layer files:
  `config/household.yml`, `config/profile.yml`, and optional narrative
  preferences. The flow previews values and writes generated templates to a
  repo-external staging path resolved by the same XDG rule as other private local
  state: if `$XDG_STATE_HOME` is set, non-empty, and absolute, use
  `$XDG_STATE_HOME/mortgage-ops/onboarding-staging/`; if it is unset or empty,
  use `~/.local/state/mortgage-ops/onboarding-staging/`; if it is set to a
  relative path, fail with a clear configuration error. The user copies staged
  files into place manually. System code must not create, overwrite, or migrate
  User Layer paths, and onboarding staging artifacts are classified as private
  anywhere they may contain household values. If tests or local development
  override the staging path into the repo, `.gitignore` and
  `scripts/hooks/block-user-layer.py` provide only a bypassable backstop against
  accidental forced adds, not the privacy boundary.
- Strict schemas and validation messages for household income, debts, cash,
  applicants, credit assumptions, location, risk preferences, tax assumptions,
  and preferred loan programs.
- Example household profiles that are synthetic but realistic enough for tests,
  demos, and documentation.
- A migration/versioning mechanism that emits migration reports or patch
  templates for User Layer config without mutating existing User Layer files.
- A privacy audit command that extends `DATA_CONTRACT.md`, `.gitignore`,
  `.pre-commit-config.yaml`, and `scripts/hooks/block-user-layer.py`
  protections to User Layer paths and any repo-local onboarding staging
  overrides. It proves no private paths are staged or committed and verifies the
  resolved onboarding staging path after environment-variable expansion and
  symlink resolution is outside the resolved repo root from
  `git rev-parse --show-toplevel`, not merely that the default template path is
  external. The audit compares `os.path.realpath`/`Path.resolve()` for both the
  expanded staging path and repo root, rejects equality or any resolved staging
  subpath below the resolved repo root, and includes fixtures where
  `$XDG_STATE_HOME=""` falls back to `~/.local/state`,
  `$XDG_STATE_HOME="relative/dir"` fails before path expansion, and
  `$XDG_STATE_HOME` is a symlink to a directory inside the repo. The audit also
  covers `reports/snapshots/private/` and any configured snapshot output
  override, treating snapshots as private whenever they contain embedded User
  Layer state. Onboarding refuses to write staging artifacts below the resolved
  repo root even when `$XDG_STATE_HOME` points there directly or through a
  symlink unless the caller passes an explicit `--allow-in-repo-staging` flag
  and a per-invocation acknowledgement. The acknowledgement is either an
  interactive `y/N` confirmation on a TTY after the tool prints the resolved
  repo root and staging path, or a `--repo-staging-token <token>` emitted by a
  prior `--explain-risk` invocation for the same resolved repo root, staging
  path, caller uid, and PID family and expiring after five minutes. Sticky
  environment variables are not accepted as acknowledgement. It prints a
  structured warning block that names `$XDG_STATE_HOME` as shell-controlled and
  that pre-commit treats as a hard failure. Without a valid per-invocation
  acknowledgement, the audit exits non-zero. CI refuses
  `--allow-in-repo-staging` and never issues repo-staging tokens. The
  shareable-report mode depends on Phase 19 trace data: every `TraceEntry` with
  `source_kind=user_provided`,
  `derived_from_user_input=true`, or private `sensitivity` is treated as
  redactable, and `--share` succeeds only when each redactable entry is redacted
  or explicitly whitelisted by the user. Whitelists are per share invocation:
  users pass one or more `--whitelist <field_path>` arguments, or
  `--whitelist-file <path>` pointing at a YAML file used only for that run.
  `<field_path>` must be an exact `TraceEntry.display_path` value present in the
  trace index; globs, regexes, wildcards, empty strings, `*`, `?`, `..`, leading
  slash, and trailing slash are rejected before rendering. Whitelisting is
  audited per snapshot/report hash through a repo-external private ledger in the
  same XDG state location as other local private state; no persistent whitelist
  exists in committed files, household config, or user config. Before rendering,
  share mode unions the requested whitelist with prior ledger entries for the
  same snapshot/report hash and enforces a cumulative maximum of 10 whitelisted
  display paths. Interactive runs require a confirmation that lists every display
  path and source kind being newly added plus the cumulative ledger set;
  non-interactive runs require an explicit `--confirm-whitelist-file`. That file
  contains the SHA-256 digest of a deterministic canonical whitelist form:
  UTF-8 without BOM, LF line endings, sorted unique display paths, one path per
  line, and a final trailing newline. The same SHA-256 digest and canonicalized
  whitelisted field paths are recorded in the share manifest so recipients can
  verify which redactions were skipped and detect post-hoc expansion.
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
  config, stale references, optional oracle availability, and strict parsing of
  safety-relevant environment flags such as `MORTGAGE_OPS_DEV_MODE`, returning
  non-zero only for required setup, malformed safety flags, or decision-mode
  blockers.
- A "local-first" setup guide for Codex/Claude maintainers: what agents may
  edit, what they may read, and what they must never commit.
- Redaction support for sharing a report externally without household/private
  fields. Redaction must not remove the `decision_mode: false` dev-mode banner
  from markdown reports.
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
  report traceability audit, and confirmation that no decision-mode report was
  blessed through `scripts/audit_reports.py` instead of the pre-emit gate, and
  that no `scripts/audit_reports.py` exit-code-3 output exists for Phase 19+
  manifests.
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
3. Phase 20 Reference Refresh Discipline.
4. Phase 22 Oracle Mesh.
5. Phase 21 Verdict Quality and Ambiguity Control.
6. Phase 23 Decision Ergonomics.
7. Phase 24 Personalization Substrate.
8. Phase 25 Shareable Distribution and Demo Path.
9. Phase 26 Agent Maintenance Hardening.

This order intentionally puts auditability before usability improvements. The
reference refresh discipline is the first auditability dependency after the
trace spine, so stale or inapplicable reference rows are visible before oracle
parity grids are assembled. The oracle mesh then lands before verdict-quality
calibration pins ambiguous fixtures and reason precedence. A slicker report is
not valuable until its numbers and rules are easy to defend.

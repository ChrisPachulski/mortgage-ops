# Phase 11: Subagents — Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** 5 NEW + 1-2 MODIFIED (depending on Phase 10 surface)
**Analogs found:** 2 / 5 strong codebase analogs; 3 of 5 require external-spec patterns (Anthropic sub-agents docs) because mortgage-ops, career-ops, and card-ops have **NO** existing `.claude/agents/*.md` files anywhere.

---

## CRITICAL ISSUES (surfaced up-front per orchestrator request)

### CRITICAL #1 — Anthropic agent frontmatter spec is the canonical pattern source (no in-tree analog)

**No agent files exist in mortgage-ops, career-ops, or card-ops.** Searches confirmed:
- `/Users/cujo253/Documents/mortgage-ops/` — no `.claude/` directory at all (skill arrives in Phase 10).
- `/Users/cujo253/Documents/career-ops/.claude/` — contains only `skills/career-ops/SKILL.md`. No `agents/` subdirectory.
- `/Users/cujo253/Documents/career-ops/.claude/skills/career-ops/SKILL.md:84-93` instead uses inline `Agent(subagent_type="general-purpose", prompt=...)` dispatch — that is a **different pattern** (transient subagent invocation at SKILL execution time) and is NOT what SUBA-01..03 require. SUBA spec wants persistent `.claude/agents/*.md` files with YAML frontmatter that Claude Code discovers at session start.

**Canonical spec to follow:** `https://code.claude.com/docs/en/sub-agents` (already cited in `.planning/research/ARCHITECTURE.md:458`). The frontmatter contract that ROADMAP SC-1 (`.planning/ROADMAP.md:205`) locks for Phase 11 is:

```yaml
---
name: amortization-agent              # required; kebab-case, must match filename stem
description: <one-sentence routing trigger Claude reads at dispatch>
model: claude-haiku-4-5               # or "haiku" / "sonnet" / "inherit" — see #1a below
skills:
  - mortgage-ops                       # references .claude/skills/mortgage-ops/SKILL.md
tools:                                # OPTIONAL; whitelist of tools the subagent may use
  - Bash
  - Read
  - Write
---

# Subagent body — system-prompt-style instructions Claude follows when dispatched.
```

**#1a — Model field naming.** ROADMAP SC-1 says `model:` is required. Anthropic's published frontmatter accepts:
- A short alias: `haiku` / `sonnet` / `opus` / `inherit` (resolves to caller's model). PROJECT.md key decision row "Subagents (amortization, refi-npv, stress-test) for context isolation" specifies Haiku for amortization+stress, Sonnet for refi-npv (multi-step NPV reasoning); REQUIREMENTS.md SUBA-01..03 confirms (`SUBA-01` Haiku, `SUBA-02` Sonnet, `SUBA-03` Haiku). **Planner decision needed:** alias vs. fully-qualified ID. Recommendation: use the short alias (`model: haiku` / `model: sonnet`) so model upgrades (e.g., haiku-4-5 → haiku-5) don't require touching three agent files. This matches how the Anthropic skill examples pin model class, not version.
- Note: REQUIREMENTS.md SUBA-03 originally said "Haiku" but the orchestrator prompt says "model TBD" for stress-test-agent — surface this discrepancy to the planner; the multi-iteration nature of 50-scenario summarization may warrant Sonnet despite the requirement text.

**#1b — `skills:` field requires the skill be installed first.** Hard dependency confirmed: `skills: [mortgage-ops]` resolves at subagent-spawn time against `.claude/skills/mortgage-ops/SKILL.md`. **That file is created by Phase 10 (SKLL-01).** Planning Phase 11 in parallel with Phase 10 is fine — the YAML frontmatter is static text — but **implementation of Phase 11 must wait for Phase 10 to land the skill folder.** ROADMAP `Phase 11 Depends on: Phase 10` (`.planning/ROADMAP.md:202`) already encodes this; this PATTERNS.md re-affirms the gate so the planner doesn't accidentally schedule Phase 11 plans before Phase 10 plans complete. Smoke test in SC-5 (`subagent has access to bundled scripts`) literally cannot pass until `.claude/skills/mortgage-ops/scripts/*.py` exists.

**#1c — `description:` is load-bearing.** Claude Code reads `description:` to decide WHEN to dispatch the subagent. Phrase it as a routing trigger: e.g., `description: "Run a single-loan amortization schedule and return CSV path or markdown table. Use when the request is ONE loan, no parameter sweeps."` — not as a noun phrase like `description: "Amortization helper"`. This mirrors the `argument-hint` discipline in `career-ops/.claude/skills/career-ops/SKILL.md:6`.

### CRITICAL #2 — Token-counting harness for SC-3 (`< 1k token summary`)

ROADMAP SC-3 (`.planning/ROADMAP.md:207`): "50-scenario rate-shock stress sweep dispatched through the subagent returns a summary < 1,000 tokens to the main context (token-counted via the eval harness)."

**Existing in-tree token-counting infrastructure:** NONE. Searched the entire repo for `tiktoken`, `count_tokens`, `num_tokens`, `token_budget` — zero hits outside narrative `.md` files. PITFALLS Pitfall 9 (`.planning/research/PITFALLS.md:216-235`) names the budget concept ("SKILL.md ≤ 5k tokens", "subagent return ≤ 1k tokens") but does NOT pin a specific tokenizer.

**Cross-phase reuse target:** Phase 10 (`SKLL-01`: SKILL.md ≤ 5k tokens, `SKLL-02`: routing in first 200 lines) MUST land a tokenizer choice for the SKILL.md size check. **The Phase 11 planner should require Phase 10 to expose its tokenizer as a reusable harness** (e.g., `evals/lib/token_count.py` or similar) so SC-3 can call the same function with the same token-counting semantics. If Phase 10 hasn't planned this yet, raise it as a Phase 10 dependency in 11-CONTEXT.md.

**Tokenizer recommendation (for the planner to confirm in 11-DISCUSSION):**
1. `tiktoken` with `cl100k_base` — fast, deterministic, no network. Approximate (Claude uses a different BPE), but close enough for budget-discipline assertions. Used widely as a public proxy.
2. `anthropic.Anthropic().messages.count_tokens(...)` — exact, but requires API key + network call. Heavyweight for a CI test.
3. Naive `len(text) / 4` — too crude; flunks any real budget audit.

Recommendation: tiktoken cl100k_base in CI (no network, deterministic, < 50ms), with a docstring noting "approximation — Claude tokenizer differs by ~5-10%; budget includes 10% safety margin." This matches how `evals/runner.py` (Phase 12 EVAL-03) is designed in `.planning/REQUIREMENTS.md:165` to be a deterministic regression harness. Planner: surface this in 11-DISCUSSION-LOG so user signs off.

### CRITICAL #3 — Career-ops is NOT a subagent analog (different pattern)

User-prompt note: "career-ops is the canonical pattern" turns out to be **incorrect for `.claude/agents/`**. Career-ops has **zero `.claude/agents/*.md` files**. Career-ops uses inline transient `Agent(subagent_type="general-purpose", prompt=...)` calls inside SKILL.md (`/Users/cujo253/Documents/career-ops/.claude/skills/career-ops/SKILL.md:84-93`):

```markdown
### Modes delegated to subagent:
For `scan`, `apply` (with Playwright), and `pipeline` (3+ URLs): launch as Agent
with the content of `_shared.md` + `modes/{mode}.md` injected into the subagent prompt.

Agent(
  subagent_type="general-purpose",
  prompt="[content of modes/_shared.md]\n\n[content of modes/{mode}.md]\n\n[invocation-specific data]",
  description="career-ops {mode}"
)
```

That is **dispatch-time prompt injection of a generic agent**, not the persistent typed-subagent pattern Phase 11 wants. The pattern career-ops *does* validate is **deciding when to delegate** (3+ URLs threshold), which is the structural analog for SUBA-05 (`Stress mode invokes stress-test-agent for sweeps > 5 scenarios`). The planner should:
- Lift the **threshold-routing pattern** from `career-ops/.claude/skills/career-ops/SKILL.md:84-93` for `modes/stress.md` SUBA-05 wiring.
- Do **NOT** lift the inline `Agent(...)` syntax — that's career-ops's workaround for the lack of typed agents. Phase 11 has typed `.claude/agents/*.md` files and should reference them by name (`agent: stress-test-agent` per the dispatch convention `.planning/research/ARCHITECTURE.md:448`).

---

## File Classification

### NEW files (Phase 11 creates)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `.claude/agents/amortization-agent.md` | subagent definition | event-driven (Claude dispatches → agent shells out → returns markdown/CSV path) | external spec (Anthropic sub-agents doc) + `career-ops/.claude/skills/career-ops/SKILL.md:1-7` (frontmatter shape only) | weak (no in-tree analog; spec-driven) |
| `.claude/agents/refi-npv-agent.md` | subagent definition | event-driven (multi-step: parse 3 offers → invoke `scripts/refi_npv.py` per offer → rank → return table) | external spec + same as above | weak (spec-driven) |
| `.claude/agents/stress-test-agent.md` | subagent definition | event-driven (parameter sweep: invoke `scripts/stress_test.py` once with N scenarios → summarize JSON to ≤1k tokens) | external spec + Phase 8 `references/stress-tests.md` "subagent consumption contract" (`.planning/phases/08-stress-points/08-PATTERNS.md:27`) | weak (spec-driven, but Phase 8 designed the JSON shape FOR this consumer) |
| `tests/test_subagents.py` | test (frontmatter parse + skill-resolution + token-budget) | invariant assertion + filesystem introspection + tokenizer call | `tests/test_reference/test_schema.py:1-36` (filesystem-introspection meta-test pattern; YAML parse + required-field assertion) | **exact** (composite — extends the same parametrize-over-`*.yml` idiom to `.claude/agents/*.md` frontmatter blocks) |
| `tests/fixtures/subagents/stress_50_scenario_summary.md` (or `.txt`) | test fixture (oracle for SC-3 token budget) | static data | `tests/fixtures/golden_pmt.json` (Phase 1 oracle anchor) + `tests/fixtures/arm/oracle/` (Phase 5 capture-as-fixture pattern at `.planning/phases/05-arm-modeling/05-PATTERNS.md:19`) | role-match (oracle pattern; content shape new) |

### MODIFIED files (Phase 11 touches existing — depends on Phase 10 surface)

| Modified File | Modification | Closest Analog Pattern |
|---|---|---|
| `.claude/skills/mortgage-ops/modes/stress.md` (Phase 10 owns; Phase 11 EXTENDS) | Add SUBA-05 dispatch rule: "if scenario count > 5, dispatch to `stress-test-agent`; else inline" | `career-ops/.claude/skills/career-ops/SKILL.md:84-93` (threshold-based delegation) |
| `.claude/skills/mortgage-ops/modes/refinance.md` (Phase 10 owns; Phase 11 OPTIONAL extension) | Add note: "if comparing ≥ 3 offers, dispatch to `refi-npv-agent`" — covers SUBA-02 ranked-NPV-table use case | same threshold-routing pattern |
| `.claude/skills/mortgage-ops/modes/amortize.md` (Phase 10 owns; Phase 11 OPTIONAL extension) | Add note: "for single-loan schedule output, may dispatch to `amortization-agent` to keep main context clean" — covers SUBA-01 | same threshold-routing pattern |

### NO ANALOG FOUND (planner must lean on RESEARCH.md / external spec)

| File | Role | Reason |
|---|---|---|
| `.claude/agents/*.md` (all three) | subagent definition | First persistent typed subagents in any of the three `*-ops` repos. Frontmatter spec lives at `https://code.claude.com/docs/en/sub-agents`. |
| Token-budget harness call site | utility | No tokenizer integrated yet; depends on Phase 10's choice. |

---

## Pattern Assignments

### `.claude/agents/amortization-agent.md` (subagent definition, event-driven)

**Primary pattern source:** Anthropic sub-agents spec (`https://code.claude.com/docs/en/sub-agents`).
**Secondary in-tree shape source:** `career-ops/.claude/skills/career-ops/SKILL.md:1-7` (YAML frontmatter parsing convention — same delimiter `---`/`---`, same kebab-case field names).

**Frontmatter pattern** (NEW — must follow Anthropic spec; no in-tree analog):

```yaml
---
name: amortization-agent
description: >
  Run a single-loan amortization schedule and return either a markdown table
  (≤30 rows) or a path to a generated CSV (full schedule). Dispatch when the
  user wants ONE loan's payment-by-payment detail and no parameter sweep.
model: haiku
skills:
  - mortgage-ops
tools:
  - Bash
  - Read
  - Write
---
```

**Body pattern** — copy the discipline from `career-ops/.claude/skills/career-ops/SKILL.md:96` ("Execute the instructions from the loaded mode file"). Subagent body should:
1. State the single-purpose contract ("you handle ONE amortization request per dispatch").
2. Reference the bundled script with full path: `.claude/skills/mortgage-ops/scripts/amortize.py --input <tmpfile.json>` (mirrors the SCRIPT_PATH discipline at `tests/test_amortize.py:51`).
3. Quote PROJECT.md decision #10 ("Run `--help` first; do not read source") — `--help` first, then construct JSON, then invoke. This is the same doctrine that scripts already encode at `scripts/amortize.py:84-89`.
4. Output contract: either inline markdown table OR `csv_path` reference; no raw 360-row JSON. SUBA-01 spec.

**Auth/guard pattern (skill discovery):** `skills: [mortgage-ops]` resolves at spawn-time; nothing for Phase 11 to write. The smoke test (SC-5) is the validation.

### `.claude/agents/refi-npv-agent.md` (subagent definition, event-driven, multi-step)

**Primary pattern source:** Anthropic sub-agents spec (model: sonnet because SUBA-02 specifies multi-step NPV reasoning across N offers).
**Cross-phase contract source:** `.planning/phases/06-refinance-npv/06-PATTERNS.md:158` and `06-RESEARCH.md:288` already document that `lib.refinance.evaluate` MUST be safe to call N times (no module-global mutation, no caching pitfalls) precisely because Phase 11 SUBA-02 will iterate over offer arrays.

**Frontmatter pattern** (NEW):

```yaml
---
name: refi-npv-agent
description: >
  Compare 2-5 competing refinance offers (rate-and-term or cash-out). Invoke
  scripts/refi_npv.py once per offer, rank by NPV, return a markdown table
  ordered best-to-worst with breakeven months and total interest delta.
model: sonnet
skills:
  - mortgage-ops
tools:
  - Bash
  - Read
  - Write
---
```

**Body pattern** — multi-step orchestration:
1. Parse user-supplied offers into N JSON files (one per offer, mirroring `scripts/refi_npv.py`'s contract).
2. Loop: for each offer, `bash` invoke the script, capture stdout JSON.
3. Rank by NPV (Sonnet handles the comparison reasoning — that's why this agent is Sonnet not Haiku per PROJECT.md key decision row).
4. Output: ranked markdown table + one-paragraph narrative explaining the winner.

**`pyxirr` deferred from Phase 6 to Phase 11** (`.planning/phases/06-refinance-npv/06-RESEARCH.md:489`, decision D-07). The planner should evaluate whether refi-npv-agent benefits from `pyxirr` (Rust-backed XNPV/IRR for irregular dates) when ranking 3+ offers. If yes, add `pyxirr` to `pyproject.toml` as a Phase 11 dependency. If no (numpy_financial.npv is fine for the 3-5 offer scale), document the deferral to v2.

### `.claude/agents/stress-test-agent.md` (subagent definition, event-driven, summarization)

**Primary pattern source:** Anthropic sub-agents spec.
**Cross-phase contract source:** `.planning/phases/08-stress-points/08-PATTERNS.md:11, 27, 261, 290`. Phase 8 designed the stress-test JSON output shape **specifically** for this subagent to consume:
- "scenario-summary table at the top of JSON for SC-5 subagent consumption" (`08-PATTERNS.md:11`)
- "top-table-summary contract for SC-5" (`08-PATTERNS.md:261`)
- "Top-of-JSON scenario-summary table + < 100KB total" (`08-PATTERNS.md:290`)

**Phase 8's `references/stress-tests.md` is the canonical contract source for this agent** — the planner must read it as the spec for what JSON shape arrives at the subagent.

**Frontmatter pattern** (NEW):

```yaml
---
name: stress-test-agent
description: >
  Run a parameter-grid stress sweep (rate-shock, income-shock, or ARM-reset
  scenarios) and return a < 1,000-token summary. Dispatch from stress mode
  whenever scenario count > 5. Reads scripts/stress_test.py output and
  produces a top-line table + one-paragraph narrative; never returns the raw
  per-scenario JSON to main context.
model: haiku   # PLANNER OPEN QUESTION: Sonnet may be needed for 50-scenario summarization quality
skills:
  - mortgage-ops
tools:
  - Bash
  - Read
---
```

**Body pattern** — single-shot summarization:
1. One bash invocation: `bash scripts/stress_test.py --input <tmp.json>` (Phase 8 `scripts/stress_test.py` per ROADMAP).
2. Read JSON output (top-of-file scenario-summary table per Phase 8 contract).
3. Summarize: produce a markdown table of the top 5 scenarios + a one-paragraph "what this means" narrative.
4. **Token-budget self-check:** subagent body should include the instruction "Your final response MUST be ≤ 1,000 tokens — count by approximating 4 chars/token and trim if over." This is enforced by SC-3's external token count check, but a self-check in-prompt reduces failure rate.

### `tests/test_subagents.py` (test — frontmatter parse + skill-resolution + token-budget)

**Primary analog:** `tests/test_reference/test_schema.py:1-36` — a parametrized filesystem-introspection meta-test that loops over `data/reference/*.yml` and asserts every file has `source:` + `effective:` keys. Phase 11 lifts this exact pattern, adapted to `.claude/agents/*.md` frontmatter blocks.

**Pattern excerpt to copy** (`tests/test_reference/test_schema.py:19-36`):

```python
# tests/test_reference/test_schema.py:19-35
REF_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data" / "reference"

def _ref_files() -> list[Path]:
    return sorted(p for p in REF_DIR.glob("*.yml"))

@pytest.mark.parametrize("path", _ref_files(), ids=lambda p: p.stem)
def test_reference_yaml_has_source_and_effective(path: Path) -> None:
    raw = yaml.safe_load(path.read_text())
    assert isinstance(raw, dict), f"{path.name} must parse to a dict (REF-09)"
    assert "source" in raw, f"{path.name} missing `source:` (REF-09)"
    assert "effective" in raw, f"{path.name} missing `effective:` (REF-09)"
    ...
```

**Apply to Phase 11** (`tests/test_subagents.py`):

```python
# tests/test_subagents.py — adapted from tests/test_reference/test_schema.py
AGENT_DIR: Path = Path(__file__).resolve().parent.parent / ".claude" / "agents"

REQUIRED_FRONTMATTER_KEYS = {"name", "description", "model", "skills"}
ALLOWED_MODELS = {"haiku", "sonnet", "opus", "inherit"}  # short-alias policy

def _agent_files() -> list[Path]:
    return sorted(p for p in AGENT_DIR.glob("*-agent.md"))

def _parse_frontmatter(text: str) -> dict[str, Any]:
    # Split on first two `---` lines per YAML frontmatter convention
    if not text.startswith("---\n"):
        raise ValueError("missing frontmatter delimiter")
    _, fm, _body = text.split("---\n", 2)
    return yaml.safe_load(fm)

@pytest.mark.parametrize("path", _agent_files(), ids=lambda p: p.stem)
def test_agent_frontmatter_required_keys(path: Path) -> None:
    fm = _parse_frontmatter(path.read_text())
    missing = REQUIRED_FRONTMATTER_KEYS - fm.keys()
    assert not missing, f"{path.name} missing frontmatter keys: {missing} (SUBA-01..04)"
    assert fm["name"] == path.stem, f"{path.name} `name:` must match filename stem"
    assert fm["model"] in ALLOWED_MODELS, f"{path.name} model {fm['model']!r} not in {ALLOWED_MODELS}"
    assert fm["skills"] == ["mortgage-ops"], f"{path.name} must declare skills: [mortgage-ops] (SUBA-04)"
```

**Test scope (covers SC-1, SC-4, SC-5):**
1. `test_agent_frontmatter_required_keys` — YAML parses; required keys present; values within whitelisted set. (SC-1)
2. `test_skill_resolves_to_filesystem` — for each agent's `skills:` entry, assert `.claude/skills/<skill>/SKILL.md` exists. (SC-5; **gated by Phase 10 landing the skill**)
3. `test_amortization_agent_returns_csv_or_markdown_table` — fixture-driven; spawn agent (or simulate dispatch via subprocess; planner decides), assert output is one of two shapes. (SC-4)
4. `test_refi_npv_agent_ranks_three_offers` — three-offer fixture; assert output is markdown table sorted descending by NPV. (SC-4)
5. `test_50_scenario_stress_summary_under_1000_tokens` — load Phase 8 stress JSON oracle (50 scenarios), pipe through stress-test-agent's summarization, run output through tokenizer (Phase 10 harness), assert `count < 1000`. (SC-3)

**Subprocess-vs-import discipline** for tests that need to invoke a script: copy from `tests/test_amortize.py:51` (`SCRIPT_PATH` constant + `subprocess.run([sys.executable, str(SCRIPT_PATH), ...])`). This is the project-canonical idiom for CLI testing and survives the Phase 10 script relocation (`.claude/skills/mortgage-ops/scripts/...`) because tests reference a constant, not a module import. Per Phase 3 D-17 (`scripts/amortize.py:16-18`).

**Filename-with-hyphen import idiom** (if tests need to import-as-module the agent definition or a hook script): copy from `tests/test_block_user_layer.py:23-30` (`importlib.util.spec_from_file_location` for kebab-case filenames). Probably not needed for `.md` files but documented here in case a planner needs it for a yaml-helper.

---

## Shared Patterns (cross-cutting concerns)

### Frontmatter YAML discipline

**Source:** `data/reference/*.yml` schema convention enforced by `tests/test_reference/test_schema.py`.
**Apply to:** All three `.claude/agents/*.md` files.
**Rule:** Every required frontmatter field is asserted by a parametrized meta-test that auto-discovers files via `glob("*-agent.md")`. Adding a new agent file with missing frontmatter automatically produces a failing test case — same auto-coverage discipline as REF-09.

### Bundled script invocation discipline

**Source:** `scripts/amortize.py:84-89` + PROJECT.md key decision #10 ("Run `--help` first; do not read source").
**Apply to:** All three subagent body prompts.
**Rule:** Subagent prompts MUST instruct the agent to run `--help` on the bundled script before constructing JSON. Never `Read` the script source — it is a black-box CLI per the webapp-testing skill convention.

### Output token-budget self-check

**Source:** PITFALLS Pitfall 9 (`.planning/research/PITFALLS.md:216-235`) + ROADMAP SC-3 (`.planning/ROADMAP.md:207`).
**Apply to:** stress-test-agent (mandatory), refi-npv-agent (recommended), amortization-agent (recommended for full-schedule output mode).
**Rule:** Subagent body includes "Your final response MUST be ≤ N tokens" instruction. Enforced externally by `tests/test_subagents.py` token-count assertion. Tokenizer choice deferred to Phase 10 (see CRITICAL #2).

### Threshold-based dispatch

**Source:** `career-ops/.claude/skills/career-ops/SKILL.md:84-93` (3+ URLs threshold for delegating `pipeline` mode to a subagent).
**Apply to:** `.claude/skills/mortgage-ops/modes/stress.md` (>5 scenarios → stress-test-agent per SUBA-05); optionally also `modes/refinance.md` (≥3 offers → refi-npv-agent) and `modes/amortize.md` (full-schedule request → amortization-agent).
**Rule:** Mode files include an explicit dispatch rule with a numeric threshold. Threshold values are user-tunable (planner: surface in 11-DISCUSSION-LOG for sign-off).

---

## No Analog Found

| File / Concept | Role | Reason | Planner Action |
|---|---|---|---|
| `.claude/agents/*.md` frontmatter | subagent definition | First in any `*-ops` repo | Use Anthropic sub-agents doc (`https://code.claude.com/docs/en/sub-agents`) as canonical spec. Cite the URL in the body of each agent file. |
| Token-counting harness | utility | No tokenizer in repo; Phase 10 hasn't pinned one | Surface as Phase 10 dependency; recommend tiktoken `cl100k_base` for CI determinism. |
| Subagent dispatch from inside SKILL.md | orchestration | Career-ops uses inline `Agent(...)` (different pattern); mortgage-ops wants typed `agent: <name>` references | Document the typed-dispatch convention in Phase 10's SKILL.md plan; cross-link from each modes/*.md update. |

---

## Cross-Phase Dependency Map

| Phase 11 file | Hard dependency | Why |
|---|---|---|
| `.claude/agents/*.md` (all three) | **Phase 10 SKLL-01..04** | `skills: [mortgage-ops]` resolves to `.claude/skills/mortgage-ops/SKILL.md`. Smoke test SC-5 fails until Phase 10 lands. |
| `.claude/agents/stress-test-agent.md` body | **Phase 8 STRS-04** + Phase 8's `references/stress-tests.md` | Subagent body references `scripts/stress_test.py` JSON output shape. Phase 8 designed the top-of-JSON scenario-summary table FOR this consumer. |
| `.claude/agents/refi-npv-agent.md` body | **Phase 6 REFI-08** | Subagent body invokes `scripts/refi_npv.py` once per offer. Phase 6 explicitly documented at `.planning/phases/06-refinance-npv/06-RESEARCH.md:288` that `evaluate()` is safe to call N times for this consumer. |
| `.claude/agents/amortization-agent.md` body | **Phase 3 AMRT-06** + **Phase 5 ARM-08** | Subagent invokes `scripts/amortize.py` (fixed) and may also handle ARM via `scripts/arm_simulate.py` per Phase 5 CONTEXT (`.planning/phases/05-arm-modeling/05-CONTEXT.md:405`). Both ship with stable JSON-in / JSON-out CLI contracts. |
| `tests/test_subagents.py` token budget | **Phase 10 tokenizer choice** | Test must call the same tokenizer Phase 10 uses for SKILL.md size check. Don't pick a different one. |
| `modes/stress.md` SUBA-05 update | **Phase 10 SKLL-05** (creates `modes/stress.md`) | Phase 11 EXTENDS the file Phase 10 creates. |

**Planning is safe NOW. Implementation must wait for Phase 10 (SKLL-01..13) to land.**

---

## Metadata

**Analog search scope:**
- `/Users/cujo253/Documents/mortgage-ops/` (entire tree, including `.planning/`, `lib/`, `scripts/`, `tests/`)
- `/Users/cujo253/Documents/career-ops/.claude/` (entire `.claude/` subtree)
- `/Users/cujo253/Documents/career-ops/CLAUDE.md` (skill orchestration patterns)

**Files scanned:** ~80 (full mortgage-ops `.planning/`; full career-ops `.claude/`; mortgage-ops `scripts/*.py`, `tests/test_*.py`, `lib/*.py`).

**Anthropic external spec source:** `https://code.claude.com/docs/en/sub-agents` (cited in `.planning/research/ARCHITECTURE.md:458`; planner should re-verify URL is current at planning time).

**Pattern extraction date:** 2026-05-02

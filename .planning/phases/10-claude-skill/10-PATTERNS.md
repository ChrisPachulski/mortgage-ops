# Phase 10: Claude Skill Frontend — Pattern Map

**Mapped:** 2026-05-02
**Phase:** 10-claude-skill
**Files analyzed:** 22 NEW + 12+ MODIFIED across `tests/` + `pyproject.toml`
**Analogs found:** 18 / 22 strong; 4 of 22 require external Anthropic-skills spec patterns (no in-tree analog).

---

## CRITICAL ISSUES (surfaced up-front per orchestrator request)

### CRITICAL #1 — career-ops `SKILL.md` is a SHALLOW analog (frontmatter + mode-routing only)

The canonical in-house skill at `/Users/cujo253/Documents/career-ops/.claude/skills/career-ops/SKILL.md` is **96 lines / ~700 tokens** — well under the SKLL-01 budget, but it leaves three Phase 10 gaps unaddressed.

**What career-ops SKILL.md gives us (LIFT VERBATIM):**

1. **YAML frontmatter shape** — `/Users/cujo253/Documents/career-ops/.claude/skills/career-ops/SKILL.md:1-7`:
   ```yaml
   ---
   name: career-ops
   description: AI job search command center -- evaluate offers, generate CVs, scan portals, track applications
   user_invocable: true
   args: mode
   argument-hint: "[scan | deep | pdf | evaluate | compare | apply | batch | tracker | pipeline | contact | training | project | interview-prep | update]"
   ---
   ```
   Phase 10 mortgage-ops adapts:
   ```yaml
   ---
   name: mortgage-ops
   description: Personal mortgage analysis -- evaluate, compare, refinance NPV, affordability, stress, amortize, ARM
   license: see LICENSE.txt
   user_invocable: true
   args: mode
   argument-hint: "[evaluate | compare | refinance | affordability | stress | amortize | arm]"
   ---
   ```
   **GAP:** SKLL-03 requires `license` and `compatibility` fields. career-ops does NOT have these — Phase 10 must add them per Anthropic skills spec (no in-tree analog).

2. **Mode-routing dispatch table** — `career-ops/SKILL.md:11-37` (lines 11-37, 27 lines total):
   ```markdown
   ## Mode Routing

   Determine the mode from `{{mode}}`:

   | Input | Mode |
   |-------|------|
   | (empty / no args) | `discovery` -- Show command menu |
   | JD text or URL (no sub-command) | **`auto-pipeline`** |
   | `evaluate` | `evaluate` |
   ...
   ```
   Phase 10 lifts the **table-with-pipe-rows** layout AS-IS for SKLL-05's seven modes. Auto-detection logic at `career-ops/SKILL.md:34` ("If `{{mode}}` is not a known sub-command AND contains JD text...") is the **shape pattern** for "if user pastes a Loan Estimate, route to `evaluate`".

3. **Discovery mode (no-args menu)** — `career-ops/SKILL.md:40-66` (27 lines including code-fenced menu). This is the SKLL-02 "first 200 lines" load-bearing content.

4. **Context loading by mode (progressive disclosure)** — `career-ops/SKILL.md:70-95`:
   ```markdown
   ### Modes that require `_shared.md` + their mode file:
   Read `modes/_shared.md` + `modes/{mode}.md`

   Applies to: `auto-pipeline`, `evaluate`, `compare`, ...

   ### Standalone modes (only their mode file):
   Read `modes/{mode}.md`

   Applies to: `tracker`, `deep`, ...
   ```
   This is the EXACT pattern Phase 10 needs for SKLL-09 (references load on demand). Lift the structure verbatim; modes that need `references/*.md` declare which one in their per-mode file, not in SKILL.md.

**What career-ops SKILL.md does NOT cover (Phase 10 must invent):**

- `compatibility:` frontmatter field (SKLL-03) — no in-tree precedent.
- `LICENSE.txt` bundling (SKLL-04) — career-ops has no license file inside the skill folder; mortgage-ops MUST per anthropics/skills spec.
- "ALWAYS shell out to scripts; never compute inline" doctrine (SKLL-11) — career-ops uses `node`/`bash` shellouts but does not codify the doctrine. Phase 10 must add an explicit instruction in `_shared.md` per webapp-testing convention. RECOMMENDED substring (test_skill_structure SC-5 will assert presence):
  > "ALWAYS shell out to scripts/ for math; NEVER compute numbers inline. Run `--help` first; do not read script source."
- Token-counting harness (SKLL-01 ≤ 5k tokens enforcement) — career-ops never measures itself. Phase 10 must ship `tests/test_skill_structure.py` with a tokenizer call. **See CRITICAL #5 below.**

**Career-ops body length budget reference:** SKILL.md = 96 lines, ~700 tokens. Mortgage-ops can grow to ~5x larger and still stay within SKLL-01. Mortgage-ops has 7 modes vs career-ops's 15, so even with richer per-mode dispatch hints, ≤ 200 lines is achievable.

---

### CRITICAL #2 — Scripts relocation: TRUE RELOCATION (git mv), not symlink, not shim

**Recommendation: physically move the four files** (`amortize.py`, `affordability.py`, `arm_simulate.py`, `_cli_helpers.py`) **from `scripts/` to `.claude/skills/mortgage-ops/scripts/` via `git mv`**, update `pyproject.toml`, and update the four `SCRIPT_PATH` test constants in a single atomic Phase 10 plan. **Do NOT use symlink. Do NOT keep a shim.**

**Rationale (with citations):**

1. **The codebase has been pre-engineered for true relocation.** Every CLI script's docstring and every test's `SCRIPT_PATH` comment explicitly anticipates this:
   - `scripts/amortize.py:16-18`: *"Phase 3 keeps this script at project root. Phase 10 physically relocates it to `.claude/skills/mortgage-ops/scripts/amortize.py` — only the path moves; test SCRIPT_PATH constants and SKILL.md routing absorb the change."*
   - `scripts/affordability.py:55-58`: *"Phase 4 keeps this script at project root. Phase 10 physically relocates it to `.claude/skills/mortgage-ops/scripts/affordability.py` — only the path moves; test SCRIPT_PATH constants and SKILL.md routing absorb the change."*
   - `scripts/arm_simulate.py:6-8`: *"Lives at project root (Phase 5); Phase 10 relocates to `.claude/skills/mortgage-ops/scripts/arm_simulate.py` per PROJECT.md decision #8."*
   - `scripts/_cli_helpers.py:7-9`: *"Phase 10 may relocate to `.claude/skills/mortgage-ops/scripts/_cli_helpers.py` following the script-relocation pattern."*
   - `tests/test_amortize.py:51-53`: *"Phase 3 CLI lives at project root scripts/. Phase 10 will relocate to `.claude/skills/mortgage-ops/scripts/`; only this constant updates."*
   - `tests/test_affordability.py:73-75`, `tests/test_arm.py:34-36`: identical comment.
   - `lib/affordability.py:91-94`: *".claude/skills/mortgage-ops/scripts/ via SCRIPT_PATH single-constant edit."*

2. **CLAUDE.md `## Conventions` skill-portability section** (`/Users/cujo253/Documents/mortgage-ops/CLAUDE.md:62-65`) makes it a hard rule:
   > `scripts/`, `references/`, `assets/`, `LICENSE.txt` all INSIDE `.claude/skills/mortgage-ops/`.

3. **Phase 11 SC-5 hard-depends on the directory existing.** `.planning/phases/11-subagents/11-PATTERNS.md:40` (re-confirmed by orchestrator prompt):
   > Smoke test in SC-5 (`subagent has access to bundled scripts`) literally cannot pass until `.claude/skills/mortgage-ops/scripts/*.py` exists.

   A symlink would satisfy filesystem-check tests but NOT skill-portability — when a user copies `.claude/skills/mortgage-ops/` to another machine, the symlink would dangle. Skill portability is the whole point of SKLL-10.

4. **A shim (leave at root + thin wrapper at skill path) actively hurts.** It would:
   - Fail mypy/ruff (two copies of the same module).
   - Confuse readers about which is canonical.
   - Require maintenance in two places (every Phase 6/7/8 script append).
   - Violate DATA_CONTRACT.md System Layer rule that `scripts/**` is the System Layer — having the same file in two locations bifurcates the layer.

**Concrete relocation steps** (Phase 10 plan should sequence in this order):

```bash
# Step 1: Create skill directory structure
mkdir -p .claude/skills/mortgage-ops/scripts
mkdir -p .claude/skills/mortgage-ops/modes
mkdir -p .claude/skills/mortgage-ops/references
mkdir -p .claude/skills/mortgage-ops/assets

# Step 2: git-mv the four scripts (preserves git history)
git mv scripts/amortize.py        .claude/skills/mortgage-ops/scripts/amortize.py
git mv scripts/affordability.py   .claude/skills/mortgage-ops/scripts/affordability.py
git mv scripts/arm_simulate.py    .claude/skills/mortgage-ops/scripts/arm_simulate.py
git mv scripts/_cli_helpers.py    .claude/skills/mortgage-ops/scripts/_cli_helpers.py

# Step 3 (CRITICAL): scripts/hooks/block-user-layer.py STAYS at scripts/hooks/.
#   It is invoked by .pre-commit-config.yaml:35 and .github/workflows/ci.yml:61
#   via the hardcoded path `scripts/hooks/block-user-layer.py`. It is NOT a
#   skill artifact. Do NOT relocate it.

# Step 4: scripts/_generate_arm_fixtures.py STAYS at scripts/.
#   It's a Phase 5 fixture-generator dev tool, not a skill-bundled script.
#   Do NOT relocate it.

# Step 5: After all of the above succeeds, the empty `scripts/` parent
#   directory still contains hooks/ and _generate_arm_fixtures.py.
#   Do NOT delete `scripts/` itself.
```

**What survives `scripts/` after relocation:**
- `scripts/.gitkeep` — leave (Phase 1 seam).
- `scripts/hooks/block-user-layer.py` — stays (CI / pre-commit hard-coded).
- `scripts/hooks/*` — stays.
- `scripts/_generate_arm_fixtures.py` — stays (Phase 5 dev tool, not skill-bundled).

**What moves to `.claude/skills/mortgage-ops/scripts/`:**
- `amortize.py`, `affordability.py`, `arm_simulate.py`, `_cli_helpers.py` (this phase).
- Phase 6's `refi_npv.py` (lands directly there per `06-PATTERNS.md:160`).
- Phase 7's `apr_reg_z.py` (lands directly there per `07-04-cli-PLAN.md:55`).
- Phase 8's `stress_test.py` + `points_breakeven.py` (land directly there per `08-04-clis-PLAN.md:380`).

---

### CRITICAL #3 — Test imports that BREAK on relocation (exhaustive enumeration)

Three categories of breakage. All trace to four physical files moving from `scripts/` to `.claude/skills/mortgage-ops/scripts/`.

**Category A: `SCRIPT_PATH` constants in test modules (4 files, 4 single-line edits).**

| Test File | Line | Current Constant | New Constant After Relocation |
|---|---|---|---|
| `tests/test_amortize.py` | 51 | `SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "amortize.py"` | `SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops" / "scripts" / "amortize.py"` |
| `tests/test_affordability.py` | 73 | `SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "affordability.py"` | (same skill path with `affordability.py`) |
| `tests/test_arm.py` | 34 | `SCRIPT_PATH: Path = Path(__file__).resolve().parent.parent / "scripts" / "arm_simulate.py"` | (same skill path with `arm_simulate.py`) |
| `tests/test_cli_helpers.py` | 21 | `from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope` | **see Category B below** |

Each `SCRIPT_PATH` is then consumed by `subprocess.run([sys.executable, str(SCRIPT_PATH), ...])` calls — those callers DO NOT change, only the constant updates. Subprocess-uses to verify still wired correctly (auditable greppable surface):
- `tests/test_amortize.py`: lines 743, 833, 846, 861, 902, 952, 983, 1017, 1045 (9 sites + 1 importlib reference at 785).
- `tests/test_affordability.py`: lines 699, 736, 1266, 1299, 1315, 1331, 1354 (7 sites + 1 importlib reference at 1207).
- `tests/test_arm.py`: lines 913, 1006, 1038, 1067, 1095 (5 sites + 1 importlib reference at 954).

**Category B: Direct `from scripts._cli_helpers import …` imports (3 files, harder to fix).**

These are `from scripts.X import Y` style — they break the moment `scripts/_cli_helpers.py` moves because `.claude/skills/mortgage-ops/scripts/` is NOT on `sys.path` and is NOT a Python package.

| File | Line | Current Import | Resolution Strategy |
|---|---|---|---|
| `tests/test_cli_helpers.py` | 21 | `from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope` | Inject skill path into sys.path BEFORE the import (mirroring `tests/test_cli_helpers.py:16-20` precedent that already does the same for `scripts/`). |
| `scripts/amortize.py` (now `.claude/skills/mortgage-ops/scripts/amortize.py`) | 109 | `from scripts._cli_helpers import find_json_float_loc, make_decimal_type_envelope` | After relocation, BOTH files live in the same dir. Either: (a) keep `from scripts._cli_helpers import …` and add `.claude/skills/mortgage-ops/` to sys.path inside main() (parallel to existing `_project_root` insert), OR (b) change to relative-import-style `from _cli_helpers import …` after sys.path injection of the script's own dir. **RECOMMENDATION (a):** preserve the `scripts._cli_helpers` namespace for grep stability, swap the `_project_root` calculation to point at `.claude/skills/mortgage-ops/` instead of project root. |
| `scripts/affordability.py` (relocated) | 164 | same | same |
| `scripts/arm_simulate.py` (relocated) | 71 | same | same |

**Recommended sys.path injection idiom for relocated scripts** (replaces current `_project_root` block at e.g. `scripts/amortize.py:98-100`):

```python
# Phase 10: scripts moved to .claude/skills/mortgage-ops/scripts/.
# Inject the SKILL ROOT (parent of this scripts/ dir) so `from scripts.X import Y`
# resolves; AND inject the project root so `from lib.X import Y` resolves.
_skill_root = str(Path(__file__).resolve().parent.parent)  # .../.claude/skills/mortgage-ops
_project_root = str(Path(__file__).resolve().parents[4])   # repo root (4 levels up)
for _p in (_project_root, _skill_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)
```

This preserves `from lib.amortize import …` AND `from scripts._cli_helpers import …` semantics in BOTH locations (script-as-script and pytest invocations).

**Category C: pyproject.toml configuration (3 single-line edits).**

| Line | Current | New After Relocation |
|---|---|---|
| `pyproject.toml:31` | `src = ["lib", "tests", "scripts"]` | `src = ["lib", "tests", "scripts", ".claude/skills/mortgage-ops/scripts"]` (ruff) |
| `pyproject.toml:52` | `files = ["lib", "tests", "scripts"]` | `files = ["lib", "tests", "scripts", ".claude/skills/mortgage-ops/scripts"]` (mypy) |
| `pyproject.toml:70-73` `[tool.pytest.ini_options]` | (no `pythonpath`) | Add `pythonpath = [".", ".claude/skills/mortgage-ops"]` so pytest sees both `scripts._cli_helpers` (legacy import path lift) AND the relocated module. |

**Category D: lib-side and CI references that survive (no edit needed).**

These mention `scripts/` in comments/docstrings but DO NOT need updating immediately (they describe Phase 3/4/5 history or refer to the surviving `scripts/hooks/` path):
- `lib/amortize.py:61, 176` (docstrings — keep, Phase 3 history)
- `lib/affordability.py:91-114, 1479` (docstring already mentions `.claude/skills/mortgage-ops/scripts/` per line 94)
- `lib/arm.py:88` (docstring, refers to `scripts/arm_simulate.py` — UPDATE to relocated path for accuracy)
- `.github/workflows/ci.yml:42, 61` — still references `scripts/hooks/block-user-layer.py` correctly (hooks STAY)
- `.pre-commit-config.yaml:35` — same, hooks STAY

**Recommended Plan 10-XX ordering to keep the test suite green throughout:**
1. Create `.claude/skills/mortgage-ops/scripts/` directory (empty seam + `.gitkeep`).
2. Update `pyproject.toml` ruff `src`, mypy `files`, pytest `pythonpath` to INCLUDE both `scripts` AND skill-scripts paths simultaneously (additive).
3. `git mv` the four scripts.
4. Update `_project_root` block inside each relocated script to use 4-levels-up instead of 1-level-up.
5. Update the four `SCRIPT_PATH` constants in tests.
6. Run full test suite. Expect green.
7. Optional cleanup (LATER PR): drop `scripts` from `src`/`files` if `scripts/hooks/` doesn't need ruff/mypy.

---

### CRITICAL #4 — `references/arm-mechanics.md` strategy: COPY (do not symlink, do not move)

**Recommendation: COPY `references/arm-mechanics.md` → `.claude/skills/mortgage-ops/references/arm-mechanics.md`**, leave the original at `<repo>/references/arm-mechanics.md`. **NOT a symlink.** **NOT a move.**

**Rationale:**

1. **Phase 5 docstring citations bind the project-root path.** `lib/arm.py` `ARMTerms` docstring cites `references/arm-mechanics.md` (per `.planning/phases/05-arm-modeling/05-CONTEXT.md:13` SC-5 mandate). Moving the file would invalidate the docstring path; symlinking creates the same dangle-on-copy problem as scripts.

2. **CONTEXT.md gives Phase 10 explicit choice between copy and symlink** (`05-CONTEXT.md:32, 207, 441`):
   > Phase 10 either copies or symlinks it into `.claude/skills/mortgage-ops/references/arm-mechanics.md` (Phase 10 picks).

3. **Skill portability requires self-containment** (CLAUDE.md `## Conventions`:62-65) — when a user `cp -r .claude/skills/mortgage-ops` to another machine, references must travel with it. Symlinks break that contract. Hence copy.

4. **Phase 11 docstring cites would NOT break** if Phase 5's `lib/arm.py` keeps citing `references/arm-mechanics.md` (project-root path) AND a duplicate exists at `.claude/skills/mortgage-ops/references/arm-mechanics.md` for skill-context loading. Both paths work for their respective consumers.

5. **Drift-protection mitigation:** add a CI test (Phase 10 plan, alongside `tests/test_skill_structure.py`) that asserts `<repo>/references/arm-mechanics.md` and `.claude/skills/mortgage-ops/references/arm-mechanics.md` are byte-identical (or a hash check). **Pattern:**
   ```python
   def test_arm_mechanics_skill_mirror_in_sync() -> None:
       """ARM mechanics doc must stay byte-identical between project root and skill folder."""
       root = Path(__file__).resolve().parent.parent / "references" / "arm-mechanics.md"
       skill = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops" / "references" / "arm-mechanics.md"
       assert root.read_bytes() == skill.read_bytes(), (
           "drift: update both copies of references/arm-mechanics.md"
       )
   ```

**Same strategy for Phase 6's `references/refi-npv.md`** (which Phase 6 ships at root per `06-RESEARCH.md` SC-5): Phase 10 COPIES it into the skill folder, drops a parallel byte-equality test.

**For Phase 7/8 references that haven't shipped yet:** since the user prompt says Phase 6/7/8 scripts will land directly inside the skill folder, the natural extension is to land Phase 7/8 NEW references directly in `.claude/skills/mortgage-ops/references/` from the start (no project-root copy). But Phase 5/6 references already shipped at root and need Phase 10 to copy them. This asymmetry is fine — earlier phases pre-date the skill folder; later ones don't.

---

### CRITICAL #5 — Tokenizer choice: tiktoken cl100k_base, hard-pinned, with documented 10% safety margin

**Recommendation:** **`tiktoken` with `cl100k_base`** for SKLL-01 enforcement (≤ 5k tokens) and SKLL-02 enforcement (routing in first 200 lines via line count, no tokenizer needed for the latter). Add `tiktoken>=0.7,<1.0` to `[dependency-groups] dev` in `pyproject.toml`.

**Rationale (with citations):**

1. **CI feasibility is the deciding factor.** `tests/test_skill_structure.py::test_skill_md_under_token_budget` runs on every PR. Two competing options:

   | Option | Speed | Determinism | Network | Accuracy vs Claude tokenizer | CI fit |
   |---|---|---|---|---|---|
   | **`tiktoken` cl100k_base** | <50 ms | full | none | ~5-10% off (different BPE family) | excellent |
   | `anthropic.Anthropic().messages.count_tokens` | network round-trip | flaky (rate limits, outages) | YES (API key) | exact | poor |
   | `len(text) / 4` | instant | full | none | ~30% error | unacceptable |

2. **`tiktoken` is already the recommended choice in Phase 11 PATTERNS.md** (`.planning/phases/11-subagents/11-PATTERNS.md:48-57`):
   > Recommendation: tiktoken cl100k_base in CI (no network, deterministic, < 50ms), with a docstring noting "approximation — Claude tokenizer differs by ~5-10%; budget includes 10% safety margin."

   Phase 10 should adopt the SAME choice for cross-phase consistency. Phase 11 SC-3 (`< 1k token summary`) reuses the SAME helper.

3. **Safety-margin policy:** assert `tokens(SKILL.md) ≤ 4500` (10% under the 5000 budget) so a tokenizer-drift on Anthropic's side doesn't break CI. Document the margin in the test docstring.

4. **Reusable harness placement:** put the tokenizer call in `tests/_skill_helpers.py` (new) — Phase 10 ships it; Phase 11 imports from it for SC-3 (`tests/test_subagents.py::test_50_scenario_stress_summary_under_1000_tokens`). This avoids duplicate tokenizer wiring across phases. If the planner prefers, an `evals/lib/token_count.py` location is fine too (Phase 12 EVAL-03 will also consume it).

5. **What the test enforces:**
   ```python
   # tests/test_skill_structure.py — SC-1 sketch
   import tiktoken

   SKILL_MD = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops" / "SKILL.md"
   ENCODER = tiktoken.get_encoding("cl100k_base")
   TOKEN_BUDGET = 4500   # 5000 SKLL-01 budget − 10% safety margin for tokenizer drift

   def test_skill_md_under_token_budget() -> None:
       text = SKILL_MD.read_text()
       n_tokens = len(ENCODER.encode(text))
       assert n_tokens <= TOKEN_BUDGET, (
           f"SKILL.md is {n_tokens} tokens (budget {TOKEN_BUDGET}, hard cap 5000). "
           f"SKLL-01 violation; trim or progressive-disclose."
       )
   ```

**Open planner decision:** if `tiktoken` proves too heavy for the project's slim dev-dep policy, the fallback is `len(text.encode('utf-8')) // 4` with a tighter safety margin (e.g., 4000). Surface this in 10-DISCUSSION-LOG.

---

## File Classification

### NEW files (Phase 10 creates)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `.claude/skills/mortgage-ops/SKILL.md` | skill-router entrypoint | request-response (mode dispatch) | `career-ops/.claude/skills/career-ops/SKILL.md` | exact (lift frontmatter + routing table + dispatch) |
| `.claude/skills/mortgage-ops/LICENSE.txt` | license | static | `pyproject.toml` (no in-tree license file yet — see Critical #6) | weak (external pattern: anthropics/skills) |
| `.claude/skills/mortgage-ops/scripts/amortize.py` | CLI (relocated) | request-response | `scripts/amortize.py` (current path) | exact (file moves; behavior unchanged) |
| `.claude/skills/mortgage-ops/scripts/affordability.py` | CLI (relocated) | request-response | `scripts/affordability.py` | exact |
| `.claude/skills/mortgage-ops/scripts/arm_simulate.py` | CLI (relocated) | request-response | `scripts/arm_simulate.py` | exact |
| `.claude/skills/mortgage-ops/scripts/_cli_helpers.py` | shared utility (relocated) | utility | `scripts/_cli_helpers.py` | exact |
| `.claude/skills/mortgage-ops/modes/_shared.md` | shared scoring + report structure | static doc | (no in-tree analog; career-ops's `modes/_shared.md` not visible in scope, but referenced at `career-ops/SKILL.md:74-77`) | weak (lift the role contract) |
| `.claude/skills/mortgage-ops/modes/_profile.md` | user-customization layer | static doc | `DATA_CONTRACT.md:19` (Phase 10 User Layer) | exact (User Layer convention) |
| `.claude/skills/mortgage-ops/modes/evaluate.md` | mode dispatcher → scripts/ | per-mode routing | `career-ops` modes pattern (referenced) | weak (no in-tree visible analog) |
| `.claude/skills/mortgage-ops/modes/compare.md` | mode dispatcher | same | same | weak |
| `.claude/skills/mortgage-ops/modes/refinance.md` | mode dispatcher → `scripts/refi_npv.py` | same | Phase 6 SC contract in `06-PATTERNS.md` | role-match |
| `.claude/skills/mortgage-ops/modes/affordability.md` | mode dispatcher → `scripts/affordability.py` | same | `scripts/affordability.py:71-132` --help epilog | exact (reuse the JSON-shape doc) |
| `.claude/skills/mortgage-ops/modes/stress.md` | mode dispatcher → `scripts/stress_test.py` (Phase 8) | same | Phase 8 `08-PATTERNS.md:11` top-summary contract | role-match |
| `.claude/skills/mortgage-ops/modes/amortize.md` | mode dispatcher → `scripts/amortize.py` | same | `scripts/amortize.py:71-90` --help epilog | exact |
| `.claude/skills/mortgage-ops/modes/arm.md` | mode dispatcher → `scripts/arm_simulate.py` | same | `scripts/arm_simulate.py:33-59` --help epilog | exact |
| `.claude/skills/mortgage-ops/references/amortization-formulas.md` | reference doc (progressive disclosure) | static | `references/arm-mechanics.md` | exact (doc style only; content NEW) |
| `.claude/skills/mortgage-ops/references/apr-reg-z.md` | reference (Phase 7 ships parallel; Phase 10 mirrors or stubs) | static | same | role-match |
| `.claude/skills/mortgage-ops/references/arm-mechanics.md` | COPY of project-root file | static | `references/arm-mechanics.md` (verbatim copy) | exact (byte-equality) |
| `.claude/skills/mortgage-ops/references/refi-npv.md` | COPY of Phase 6 file | static | `references/refi-npv.md` (Phase 6 ships at root) | exact (byte-equality) |
| `.claude/skills/mortgage-ops/references/affordability-rules.md` | reference (NEW) | static | `references/arm-mechanics.md` style | exact (style); content NEW |
| `.claude/skills/mortgage-ops/references/gse-limits.md` | reference (NEW) | static | same | exact |
| `.claude/skills/mortgage-ops/references/mip-pmi.md` | reference (NEW) | static | same | exact |
| `.claude/skills/mortgage-ops/references/tax-deductibility.md` | reference (NEW) | static | same | exact |
| `.claude/skills/mortgage-ops/references/spreadsheet-conventions.md` | reference (NEW) | static | same | exact |
| `.claude/skills/mortgage-ops/assets/.gitkeep` | seam | static | `tests/fixtures/arm/oracle/.gitkeep` (Phase 5 idiom) | exact |
| `tests/test_skill_structure.py` | test (token + frontmatter + layout + modes + refs + always-shell-out doctrine) | invariant + filesystem | `tests/test_reference/test_schema.py:19-36` (parametrized filesystem-introspection meta-test) | exact (composite) |
| `tests/_skill_helpers.py` | tokenizer harness (shared by Phase 11/12) | utility | `scripts/_cli_helpers.py` (factor-extract pattern; Phase 5) | role-match |

### MODIFIED files (Phase 10 touches existing)

| Modified File | Modification | Reason / Closest Pattern |
|---|---|---|
| `pyproject.toml` | (a) `src = [..., ".claude/skills/mortgage-ops/scripts"]`, (b) mypy `files = [..., same]`, (c) `[tool.pytest.ini_options] pythonpath = [".", ".claude/skills/mortgage-ops"]`, (d) add `tiktoken>=0.7,<1.0` to dev deps | Critical #3 Category C + Critical #5 |
| `tests/test_amortize.py` | Update `SCRIPT_PATH` constant on line 51 to skill path | Critical #3 Category A |
| `tests/test_affordability.py` | Same on line 73 | Same |
| `tests/test_arm.py` | Same on line 34 | Same |
| `tests/test_cli_helpers.py` | Update sys.path injection (line 16-20) + import (line 21) to find relocated `_cli_helpers.py` in skill path | Critical #3 Category B |
| `.claude/skills/mortgage-ops/scripts/amortize.py` (post-mv) | Update `_project_root` block (line 98-100) to point 4 levels up to repo root + 1 level up to skill root | Critical #3 Category B "Recommended sys.path injection idiom" |
| `.claude/skills/mortgage-ops/scripts/affordability.py` (post-mv) | Same on line 140-142 | Same |
| `.claude/skills/mortgage-ops/scripts/arm_simulate.py` (post-mv) | Same on line 64-66 | Same |
| `lib/arm.py` | Update docstring on line 88 to reference relocated `scripts/arm_simulate.py` path (cosmetic but accurate) | Critical #3 Category D (optional but recommended for grep stability) |
| `references/arm-mechanics.md` | NO modification (stays at root); copied to skill folder | Critical #4 |
| `references/refi-npv.md` (when Phase 6 lands) | NO modification; copied | Critical #4 |
| `tests/conftest.py` | (optional) Add `skill_dir` fixture if multiple test files want a shared skill-root path constant | n/a — small enough to inline |

### NO ANALOG FOUND (planner must lean on Anthropic skills spec / external pattern)

| File | Role | Reason |
|---|---|---|
| `.claude/skills/mortgage-ops/LICENSE.txt` | license | Neither career-ops nor card-ops nor mortgage-ops has a `LICENSE.txt` inside a skill folder. Use anthropics/skills convention (typically MIT or project's chosen license; mortgage-ops `pyproject.toml` does not currently declare a license — see CRITICAL #6 below). |
| Modes index (per-mode files) | mode dispatchers | career-ops's `modes/*.md` files are NOT in scope of this analysis (only `SKILL.md` was confirmed visible in the user prompt). Lift the **role contract** from `career-ops/SKILL.md:74-77` (mode files dispatched after routing) but the per-mode body shape is invented for mortgage-ops based on each mode's existing `scripts/X.py --help` epilog. |
| `compatibility:` frontmatter field | metadata | SKLL-03 specifies it; no in-tree precedent. Use anthropics/skills spec (e.g., `compatibility: claude-code, opencode`). |
| Token-counting harness | utility | First in-tree tokenizer adoption. See CRITICAL #5. |

---

### CRITICAL #6 — `LICENSE.txt` content gap

**Issue:** `pyproject.toml` does NOT currently declare a `[project] license` field (verified at `pyproject.toml:1-11`). SKLL-04 requires `LICENSE.txt` bundled inside the skill folder. Phase 10 has no source-of-truth license to copy from.

**Recommendation:** Phase 10 plan must explicitly choose a license. Two options:
1. **Add `license = "MIT"` to `pyproject.toml [project]` block** + ship `LICENSE.txt` (MIT text) at BOTH `<repo>/LICENSE` (project-level) AND `.claude/skills/mortgage-ops/LICENSE.txt` (skill-level mirror).
2. **Mark "All Rights Reserved — personal use" if PROJECT.md's "Personal household use; not commercial" framing prevails.** PROJECT.md `## What This Is` says *"Built for making real household mortgage decisions, not commercial use."* This argues for proprietary, but bundling a skill that a user might fork suggests permissive is friendlier.

**Surface in 10-DISCUSSION-LOG for user signoff.** Recommend option (1) MIT for sibling-repo consistency and to avoid blocking future open-sourcing decisions.

---

## Pattern Assignments

### `.claude/skills/mortgage-ops/SKILL.md` (skill router; ≤ 500 lines, ≤ 5k tokens)

**Closest analog:** `/Users/cujo253/Documents/career-ops/.claude/skills/career-ops/SKILL.md:1-96`.

**Imports / frontmatter pattern** (lines 1-7 of analog):
```yaml
---
name: career-ops
description: AI job search command center -- evaluate offers, generate CVs, scan portals, track applications
user_invocable: true
args: mode
argument-hint: "[scan | deep | pdf | evaluate | compare | apply | batch | tracker | pipeline | contact | training | project | interview-prep | update]"
---
```

Adapt for mortgage-ops (SKLL-03 adds `license` + `compatibility`):
```yaml
---
name: mortgage-ops
description: Personal mortgage analysis command center -- evaluate, compare, refinance NPV, affordability, ARM modeling, stress tests, amortization
license: MIT   # see LICENSE.txt
compatibility: claude-code  # OPEN: confirm with user; opencode/codex compat optional
user_invocable: true
args: mode
argument-hint: "[evaluate | compare | refinance | affordability | stress | amortize | arm]"
---
```

**Mode-routing dispatch pattern** (lift table layout from `career-ops/SKILL.md:11-37`):
```markdown
## Mode Routing

Determine the mode from `{{mode}}`:

| Input | Mode |
|-------|------|
| (empty / no args) | `discovery` -- Show command menu |
| Loan Estimate text or numeric loan params (no sub-command) | **`auto-evaluate`** |
| `evaluate` | `evaluate` |
| `compare` | `compare` |
| `refinance` | `refinance` |
| `affordability` | `affordability` |
| `stress` | `stress` |
| `amortize` | `amortize` |
| `arm` | `arm` |
```

**Auto-detection pattern** (`career-ops/SKILL.md:34`): "If `{{mode}}` is not a known sub-command AND contains [domain-keyword cues], execute `<auto-mode>`." Phase 10 cue list: keywords like "principal", "30-year", "fixed rate", "ARM", "refinance", "monthly P&I", or any LE-shaped form.

**Discovery menu pattern** (`career-ops/SKILL.md:42-66`):
```markdown
## Discovery Mode (no arguments)

Show this menu:

\`\`\`
mortgage-ops -- Personal Mortgage Command Center

Available commands:
  /mortgage-ops {loan params}  -> AUTO-EVALUATE: full report (paste LE or describe loan)
  /mortgage-ops evaluate       -> Evaluate a single loan or scenario
  /mortgage-ops compare        -> Compare 2-5 loan offers side-by-side
  /mortgage-ops refinance      -> Rate-and-term or cash-out refi NPV
  /mortgage-ops affordability  -> What loan can I qualify for? DTI/LTV/PITI
  /mortgage-ops stress         -> Rate-shock / income-shock / ARM-path sweeps
  /mortgage-ops amortize       -> Generate fixed-rate amortization schedule
  /mortgage-ops arm            -> Simulate ARM (5/1, 7/1, 10/1, 5/6) with reset paths

Configuration:
  config/household.yml + config/profile.yml -- your household income / debts / location
  modes/_profile.md            -- your customization overrides
\`\`\`
```

**Context-loading-by-mode pattern** (`career-ops/SKILL.md:70-95` lift verbatim shape):
```markdown
## Context Loading by Mode

After determining the mode, load the necessary files before executing:

### Modes that require `_shared.md` + their mode file:
Read `modes/_shared.md` + `modes/{mode}.md`

Applies to: `auto-evaluate`, `evaluate`, `compare`, `refinance`, `affordability`, `stress`

### Standalone modes (only their mode file):
Read `modes/{mode}.md`

Applies to: `amortize`, `arm`

### References load on demand only (SKLL-09 progressive disclosure):
Modes individually pull `references/{topic}.md` when answering domain questions
that require regulatory or formula citations. Do NOT eagerly read references in SKILL.md.
```

**SKLL-11 always-shell-out doctrine** (NEW — no in-tree analog; mandatory):
```markdown
## Math Discipline -- ALWAYS SHELL OUT

ALWAYS shell out to `scripts/` for math; NEVER compute numbers inline. Run `--help`
first; do not read script source. Every dollar figure that exits this skill must
trace to a `bash scripts/X.py --input <tmp.json>` invocation. Inline arithmetic on
loan amounts / rates / payments is a project-wide policy violation.

Rationale: PROJECT.md `## Core Value` -- "The LLM frontend is a router and
narrator -- it never owns numbers."
```

This sentence ("ALWAYS shell out to scripts/ for math; NEVER compute numbers inline. Run `--help` first; do not read script source.") is the **substring SC-5 of `tests/test_skill_structure.py` will assert presence**.

---

### `.claude/skills/mortgage-ops/scripts/amortize.py` (relocated CLI)

**Closest analog:** itself, at current path `scripts/amortize.py`.

**Behavioral changes:** NONE. Only the file location moves.

**Code change:** sys.path injection in `main()` (current line 98-100) updates from `parent.parent` (= project root) to `parents[4]` (= project root, since the file is now 4 levels deep) AND adds `parents[1]` (= skill root, so `from scripts._cli_helpers import …` resolves):

Current (lines 92-100):
```python
# When invoked as a script (`python scripts/amortize.py ...`), Python puts
# `scripts/` on sys.path, NOT the project root, so `from lib.amortize import ...`
# fails with ModuleNotFoundError. Insert the project root (parent of this file's
# directory) at sys.path[0] so the lazy-import below resolves. Cheap (one Path
# operation + list insert) and runs only AFTER --help has already exited above,
# so D-18 (--help fast) is unaffected.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
```

After (Phase 10 edit):
```python
# Phase 10: relocated to .claude/skills/mortgage-ops/scripts/amortize.py.
# Inject BOTH the repo root (so `from lib.amortize import ...` resolves) AND
# the skill root (so `from scripts._cli_helpers import ...` resolves —
# scripts/ here means the skill-local scripts/, not project-root scripts/).
# parents[4] = repo root (skipping scripts/, mortgage-ops/, skills/, .claude/).
# parents[1] = skill root (.claude/skills/mortgage-ops).
_skill_root = str(Path(__file__).resolve().parents[1])
_project_root = str(Path(__file__).resolve().parents[4])
for _p in (_project_root, _skill_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)
```

The `from scripts._cli_helpers import ...` line at current 109 STAYS — under skill-root sys.path injection, the import resolves to the new colocated `_cli_helpers.py`.

**Same edit on `affordability.py` (line 140-142) and `arm_simulate.py` (line 64-66).** `_cli_helpers.py` itself has no sys.path block to update.

---

### `.claude/skills/mortgage-ops/modes/_shared.md` (shared scoring + report structure)

**Closest analog:** none in mortgage-ops or visible career-ops scope. The role contract is defined by `career-ops/SKILL.md:74-77`:
> ### Modes that require `_shared.md` + their mode file:
> Read `modes/_shared.md` + `modes/{mode}.md`

**Pattern to invent** (Phase 10 plan should design):
1. Standard report-header block (loan name + date + scenario summary).
2. Scoring scaffold (if applicable to comparison modes — likely a green/yellow/red traffic-light per affordability rule, modeled on `lib.affordability.AffordabilityResponse.binding_constraint`).
3. Math-discipline reminder (one-paragraph restatement of "ALWAYS shell out to scripts/" — duplicates SKILL.md doctrine for redundancy at execution time, NOT for SC-5 substring purposes).
4. Report-write convention: `reports/{###}-{slug}-{YYYY-MM-DD}.md` per SKLL-13. Mirror career-ops's `reports/` numbering scheme.

---

### `.claude/skills/mortgage-ops/modes/_profile.md` (User Layer customization)

**Closest analog:** `DATA_CONTRACT.md:19` (already enumerates this file as User Layer) + `.gitignore` rules.

**Pattern:** copy a **template** at `.claude/skills/mortgage-ops/modes/_profile.template.md` (System Layer, committed) that the user copies to `.claude/skills/mortgage-ops/modes/_profile.md` (User Layer, gitignored). Mirrors career-ops's documented onboarding flow at `career-ops/CLAUDE.md` ("If `modes/_profile.md` is missing, copy from `modes/_profile.template.md` silently").

**`.gitignore` update REQUIRED:**
```gitignore
# Phase 10: skill user-layer override
.claude/skills/mortgage-ops/modes/_profile.md
```

**Pre-commit hook update REQUIRED:** `scripts/hooks/block-user-layer.py` must add `.claude/skills/mortgage-ops/modes/_profile.md` to its `USER_LAYER_PATTERNS` (already cited as cross-ref source by `DATA_CONTRACT.md:73-74`).

---

### `.claude/skills/mortgage-ops/modes/{evaluate,compare,refinance,affordability,stress,amortize,arm}.md`

**Pattern source:** each mode's CURRENT `scripts/X.py --help` epilog. Phase 10 lifts these into the per-mode `.md` body so Claude has invocation guidance without re-reading the script.

**Example for `modes/affordability.md`** (lift from `scripts/affordability.py:74-123`):
```markdown
# affordability mode

When invoked, Claude does the following:

1. Read `modes/_shared.md` + this file.
2. Gather inputs from user:
   - household block (joint income, monthly debts, location with state_fips + county_fips)
   - max_dti (e.g. "0.430000")
   - target_loan_type (one of: conventional, fha, va, usda, jumbo)
   - mode discriminator: "forward" (known loan + property) OR "reverse" (known max_dti + LTV target)
3. Construct JSON per the shape documented at `scripts/affordability.py --help`.
4. Invoke: `bash .claude/skills/mortgage-ops/scripts/affordability.py --input <tmp.json>`
5. Parse JSON output; narrate the result citing `binding_constraint` if blocked.
6. Persist report to `reports/{###}-affordability-{YYYY-MM-DD}.md` per SKLL-13.

DOMAIN GUIDANCE:
- All money/rate fields MUST be JSON strings (e.g. "400000.00") -- floats are
  rejected at the boundary with a 6-key envelope on stderr.
- target_loan_type=='va' requires household.va block (region, family_size,
  actual_residual_income).
- target_loan_type=='conventional' with LTV > 0.80 requires monthly_pmi.
- FHA UFMIP is auto-financed into principal.

RELATED REFERENCES (load on demand if user asks):
- `references/affordability-rules.md` -- DTI / LTV / CLTV bounds and citations
- `references/gse-limits.md` -- conforming, FHA, VA, USDA cutoffs
- `references/mip-pmi.md` -- when MIP/PMI applies + how to terminate
```

**Same shape for `modes/amortize.md`** (lift `scripts/amortize.py:71-90` epilog), `modes/arm.md` (lift `scripts/arm_simulate.py:33-59` epilog), and Phase 6/7/8 modes.

---

### `tests/test_skill_structure.py` (NEW — covers SC-1..SC-5 of Phase 10)

**Closest analog:** `tests/test_reference/test_schema.py:19-36` (parametrized filesystem-introspection meta-test) + Phase 11's planned `tests/test_subagents.py` (mirror pattern, see `.planning/phases/11-subagents/11-PATTERNS.md:236-260`).

**Test scope (orchestrator prompt SC-1..SC-5):**

```python
# tests/test_skill_structure.py — SKLL-01..13 enforcement
from __future__ import annotations

from pathlib import Path

import pytest
import tiktoken
import yaml

SKILL_DIR: Path = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "mortgage-ops"
SKILL_MD: Path = SKILL_DIR / "SKILL.md"

REQUIRED_FRONTMATTER_KEYS = {"name", "description", "license", "compatibility"}  # SKLL-03
EXPECTED_MODES = {"evaluate", "compare", "refinance", "affordability", "stress", "amortize", "arm"}  # SKLL-05
EXPECTED_REFERENCES = {  # SKLL-08
    "amortization-formulas", "apr-reg-z", "arm-mechanics", "refi-npv",
    "affordability-rules", "gse-limits", "mip-pmi", "tax-deductibility",
    "spreadsheet-conventions",
}
ALWAYS_SHELL_OUT_SUBSTRING = (
    "ALWAYS shell out to scripts/ for math; NEVER compute numbers inline. "
    "Run `--help` first; do not read script source."
)  # SKLL-11

ENCODER = tiktoken.get_encoding("cl100k_base")
TOKEN_BUDGET = 4500   # SKLL-01: 5000 hard cap with 10% safety margin for tokenizer drift
LINE_BUDGET = 500     # SKLL-01
ROUTING_FIRST_N_LINES = 200  # SKLL-02


# --- SC-1: token + line budget ----------------------------------------------

def test_skill_md_under_token_budget() -> None:
    """SKLL-01: SKILL.md ≤ 5000 tokens (4500 with 10% safety margin)."""
    text = SKILL_MD.read_text()
    n_tokens = len(ENCODER.encode(text))
    assert n_tokens <= TOKEN_BUDGET, (
        f"SKILL.md is {n_tokens} tokens (budget {TOKEN_BUDGET}; SKLL-01 hard cap 5000). "
        f"Trim or move detail into modes/ or references/ (progressive disclosure)."
    )


def test_skill_md_under_line_budget() -> None:
    """SKLL-01: SKILL.md ≤ 500 lines."""
    n_lines = SKILL_MD.read_text().count("\n") + 1
    assert n_lines <= LINE_BUDGET, f"SKILL.md is {n_lines} lines (cap {LINE_BUDGET})."


def test_routing_in_first_200_lines() -> None:
    """SKLL-02: routing logic must be in the first 200 lines (post-compaction re-attach budget)."""
    head = "\n".join(SKILL_MD.read_text().splitlines()[:ROUTING_FIRST_N_LINES])
    assert "## Mode Routing" in head, "SKLL-02: '## Mode Routing' must appear in first 200 lines"


# --- SC-2: frontmatter ------------------------------------------------------

def _parse_frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---\n"):
        raise ValueError("missing frontmatter delimiter")
    _, fm, _body = text.split("---\n", 2)
    return yaml.safe_load(fm)


def test_skill_md_frontmatter_has_required_keys() -> None:
    """SKLL-03: frontmatter has name, description, license, compatibility."""
    fm = _parse_frontmatter(SKILL_MD.read_text())
    missing = REQUIRED_FRONTMATTER_KEYS - set(fm)
    assert not missing, f"SKLL-03 frontmatter missing keys: {missing}"
    assert fm["name"] == "mortgage-ops", f"name must be 'mortgage-ops', got {fm['name']!r}"


# --- SC-3: layout (LICENSE.txt, scripts/, modes/, references/, assets/) ----

@pytest.mark.parametrize("relpath", [
    "LICENSE.txt",                 # SKLL-04
    "scripts/amortize.py",         # SKLL-10 (relocation)
    "scripts/affordability.py",    # SKLL-10
    "scripts/arm_simulate.py",     # SKLL-10
    "scripts/_cli_helpers.py",     # SKLL-10
    "modes/_shared.md",            # SKLL-06
    "assets/.gitkeep",             # placeholder dir (SKLL conv.)
])
def test_skill_layout_includes_required_path(relpath: str) -> None:
    """SKLL-04 + SKLL-06 + SKLL-10: bundled artifacts exist inside the skill folder."""
    p = SKILL_DIR / relpath
    assert p.exists(), f"skill layout missing: {relpath}"


# --- SC-4: every mode file exists -------------------------------------------

@pytest.mark.parametrize("mode", sorted(EXPECTED_MODES))
def test_mode_file_exists(mode: str) -> None:
    """SKLL-05: every mode in {evaluate, compare, refinance, affordability, stress, amortize, arm}
    has a modes/{mode}.md file."""
    p = SKILL_DIR / "modes" / f"{mode}.md"
    assert p.exists(), f"SKLL-05 mode file missing: modes/{mode}.md"


# --- SC-5: every reference exists + always-shell-out doctrine substring ----

@pytest.mark.parametrize("ref", sorted(EXPECTED_REFERENCES))
def test_reference_file_exists(ref: str) -> None:
    """SKLL-08: all 9 reference docs are bundled."""
    p = SKILL_DIR / "references" / f"{ref}.md"
    assert p.exists(), f"SKLL-08 reference missing: references/{ref}.md"


def test_always_shell_out_doctrine_in_skill_md() -> None:
    """SKLL-11: SKILL.md MUST instruct Claude to ALWAYS shell out to scripts for math."""
    text = SKILL_MD.read_text()
    assert ALWAYS_SHELL_OUT_SUBSTRING in text, (
        f"SKLL-11 violation: substring not found in SKILL.md.\n"
        f"Expected: {ALWAYS_SHELL_OUT_SUBSTRING!r}\n"
        f"This substring is the load-bearing math-discipline doctrine; reword in test+SKILL.md together."
    )


# --- bonus: byte-equality of mirrored references ----------------------------

@pytest.mark.parametrize("ref_name", ["arm-mechanics", "refi-npv"])
def test_reference_mirror_in_sync_with_repo_root(ref_name: str) -> None:
    """Repo-root references/{ref}.md and skill-root references/{ref}.md must be byte-identical
    so SKLL-09 progressive disclosure and Phase 5/6 docstring cites do not drift apart."""
    root = Path(__file__).resolve().parent.parent / "references" / f"{ref_name}.md"
    skill = SKILL_DIR / "references" / f"{ref_name}.md"
    if not root.exists():
        pytest.skip(f"<repo>/references/{ref_name}.md not yet shipped")
    assert root.read_bytes() == skill.read_bytes(), (
        f"drift between <repo>/references/{ref_name}.md and "
        f".claude/skills/mortgage-ops/references/{ref_name}.md -- update both."
    )
```

**Pattern lifted from** `tests/test_reference/test_schema.py:19-36` (the parametrize-over-glob meta-test idiom):
```python
# tests/test_reference/test_schema.py — analog
REF_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data" / "reference"

def _ref_files() -> list[Path]:
    return sorted(p for p in REF_DIR.glob("*.yml"))

@pytest.mark.parametrize("path", _ref_files(), ids=lambda p: p.stem)
def test_reference_yaml_has_source_and_effective(path: Path) -> None:
    raw = yaml.safe_load(path.read_text())
    assert isinstance(raw, dict), f"{path.name} must parse to a dict (REF-09)"
    assert "source" in raw, f"{path.name} missing `source:` (REF-09)"
    assert "effective" in raw, f"{path.name} missing `effective:` (REF-09)"
```

---

### `tests/_skill_helpers.py` (NEW — shared tokenizer harness for Phase 10/11/12)

**Closest analog:** `scripts/_cli_helpers.py` (Phase 5 factor-extract pattern — single source of truth for cross-script helpers).

**Pattern:**
```python
"""Shared skill/eval token-counting harness (Phase 10 ships; Phase 11 SUBA-06, Phase 12 EVAL-04 consume).

Per Phase 10 PATTERNS.md CRITICAL #5: tiktoken cl100k_base for CI-friendly,
deterministic, network-free token counting. Approximation note: Claude tokenizer
differs by ~5-10%; budgets include a 10% safety margin (e.g., 4500 tokens for a
nominal 5000 budget; 900 tokens for a nominal 1000 budget).
"""

from __future__ import annotations

import tiktoken

_ENCODER = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Return tiktoken cl100k_base count -- approximate Claude usage within ±10%."""
    return len(_ENCODER.encode(text))


def assert_under_budget(text: str, hard_budget: int, *, safety_margin_pct: int = 10) -> None:
    """Assert text token count is under hard_budget * (1 - safety_margin_pct/100).
    Raises AssertionError with a message including measured count and effective cap."""
    effective = int(hard_budget * (100 - safety_margin_pct) / 100)
    n = count_tokens(text)
    assert n <= effective, (
        f"token budget exceeded: {n} > {effective} "
        f"(hard cap {hard_budget}; {safety_margin_pct}% safety margin)"
    )
```

---

## Shared Patterns (cross-cutting)

### Subprocess-only CLI testing (preserves portability across script relocations)

**Source:** `scripts/amortize.py:16-18` (D-17 portability comment) + `tests/test_amortize.py:51-53` (`SCRIPT_PATH` constant doctrine).

**Apply to:** every test that invokes a relocated script. Phase 10 keeps the discipline; subprocess-vs-direct-import is the canonical test idiom and has been since Phase 3.

**Rule:** Tests use `subprocess.run([sys.executable, str(SCRIPT_PATH), ...])`, NEVER `from scripts.X import Y`. The single `SCRIPT_PATH` constant absorbs the Phase 10 relocation. (One exception: `tests/test_cli_helpers.py:21` directly imports `_cli_helpers` because it tests the helper module's API surface; that one needs sys.path injection, see Critical #3 Category B.)

### Filesystem-introspection meta-tests

**Source:** `tests/test_reference/test_schema.py:19-36` (parametrized over `glob("*.yml")`).
**Apply to:** `tests/test_skill_structure.py` (parametrize over expected modes / references / required paths).
**Rule:** Use `@pytest.mark.parametrize("path", _files(), ids=lambda p: p.stem)` so adding a new mode/reference auto-extends test coverage. Phase 11 `tests/test_subagents.py` will reuse the same pattern.

### Progressive disclosure (load on demand)

**Source:** `career-ops/SKILL.md:70-95` (mode-files loaded only when their mode is invoked).
**Apply to:** `.claude/skills/mortgage-ops/SKILL.md` mode-loading section + per-mode references.
**Rule:** SKILL.md MUST NOT eagerly read references. Each `modes/X.md` lists which `references/Y.md` it might need. Claude reads them only when the user's question demands the citation/formula.

### User Layer / System Layer separation (extends to skill folder)

**Source:** `DATA_CONTRACT.md:11-44` (existing User vs System layers).
**Apply to:** the skill folder. ENTIRE `.claude/skills/mortgage-ops/**` is System Layer EXCEPT `.claude/skills/mortgage-ops/modes/_profile.md` (User Layer; gitignored; pre-commit hook blocks).
**Rule:** Phase 10 must update both `.gitignore` and `scripts/hooks/block-user-layer.py`'s `USER_LAYER_PATTERNS` to include `.claude/skills/mortgage-ops/modes/_profile.md`. `DATA_CONTRACT.md:19` already enumerates this file.

### `--help` first; do not read source (webapp-testing doctrine)

**Source:** `scripts/amortize.py:71-90` (argparse epilog includes the JSON shape) + PROJECT.md decision #10.
**Apply to:** Every mode file + SKILL.md doctrine block.
**Rule:** Modes must instruct Claude to run `--help` on the bundled script before constructing JSON. NEVER `Read` the script source — it is a black-box CLI. This doctrine appears in Phase 11 PATTERNS.md as a shared pattern too (`.planning/phases/11-subagents/11-PATTERNS.md:284-288`); Phase 10 is the upstream that ships it.

### Sign-convention rigor at the Pydantic boundary (carries into mode dispatchers)

**Source:** Phase 6 `RefiCashflow` validator (`.planning/phases/06-PATTERNS.md:46-60`) + Phase 4 `_validate_common` cross-field validators.
**Apply to:** `modes/refinance.md` MUST instruct Claude that money fields are JSON strings; mode dispatcher pre-validates user input shape before calling `scripts/refi_npv.py`. Same for affordability/stress/amortize/arm modes.
**Rule:** Mode files restate the JSON-string-only contract for user-facing input. Boundary errors return the 6-key envelope on stderr; mode dispatcher narrates `loc[0]` (which field) + `msg` (why) + `input` (what was rejected). Substring spec at `scripts/amortize.py:36-60` is the canonical envelope shape.

---

## Cross-Phase Dependencies (sequencing)

| Dependency | Source | Target | Effect on Phase 10 |
|---|---|---|---|
| `scripts/{amortize,affordability,arm_simulate,_cli_helpers}.py` exist + are stable | Phases 3, 4, 5 | Phase 10 | Met — Phases 3/4/5 are Done per REQUIREMENTS.md traceability table. Safe to relocate. |
| `references/arm-mechanics.md` exists at repo root | Phase 5 | Phase 10 | Met — file confirmed at `<repo>/references/arm-mechanics.md` (9.7 KB, 165 lines). Phase 10 copies into skill folder. |
| `references/refi-npv.md` exists at repo root | Phase 6 | Phase 10 | **OPEN** — Phase 6 plans show it WILL ship at `<repo>/references/refi-npv.md` per `06-RESEARCH.md` SC-5. If Phase 6 lands first (sequential execution), Phase 10 copies into skill folder; if Phase 10 lands first, Phase 6 plan must add the copy step to its 06-06 references-doc plan. |
| Phase 7 `references/apr-reg-z.md` location | Phase 7 | Phase 10 | **OPEN** — Phase 7 plans not yet fully read. Recommend Phase 7 lands references DIRECTLY at `.claude/skills/mortgage-ops/references/apr-reg-z.md` (skill-folder-from-the-start) since Phase 10 will already be in flight or done. Surface to Phase 7 planner. |
| Phase 8 `references/{stress-tests,points-breakeven}.md` location | Phase 8 | Phase 10 | Same as Phase 7 — surface to Phase 8 planner. (Phase 8 PATTERNS.md cites them at root per `08-PATTERNS.md:27-28`; Phase 10 may need to copy.) |
| `.claude/skills/mortgage-ops/scripts/` directory exists | Phase 10 | **Phase 11 SC-5** | **HARD DEPENDENCY** — Phase 11 cannot validate `subagent has access to bundled scripts` until this directory exists per `.planning/phases/11-subagents/11-PATTERNS.md:40`. ROADMAP `Phase 11 Depends on: Phase 10` already encodes the gate. |
| Tokenizer harness (`tests/_skill_helpers.py`) | Phase 10 | **Phase 11 SC-3 + Phase 12 EVAL-03** | Phase 11 PATTERNS.md CRITICAL #2 explicitly requests Phase 10 ship a reusable tokenizer (`.planning/phases/11-subagents/11-PATTERNS.md:48-57`). Phase 10 ships it; downstream phases import. |

---

## Metadata

**Analog search scope:**
- `/Users/cujo253/Documents/career-ops/.claude/skills/career-ops/SKILL.md` (canonical in-house pattern)
- `/Users/cujo253/Documents/career-ops/CLAUDE.md` (data-contract + onboarding patterns)
- `/Users/cujo253/Documents/mortgage-ops/scripts/{amortize,affordability,arm_simulate,_cli_helpers}.py`
- `/Users/cujo253/Documents/mortgage-ops/tests/test_{amortize,affordability,arm,cli_helpers,reference/test_schema}.py`
- `/Users/cujo253/Documents/mortgage-ops/references/arm-mechanics.md`
- `/Users/cujo253/Documents/mortgage-ops/CLAUDE.md`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `DATA_CONTRACT.md`, `pyproject.toml`
- `/Users/cujo253/Documents/mortgage-ops/.planning/phases/{05-arm-modeling,06-refinance-npv,08-stress-points,11-subagents}/*PATTERNS.md, *CONTEXT.md, *RESEARCH.md`
- `/Users/cujo253/Documents/mortgage-ops/.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `lib/{amortize,affordability,arm}.py` (only docstring/comment greps for `scripts/`-path references)

**Files scanned:** ~30 (subset reads on large files; full reads for SKILL.md, scripts, conftest, references/arm-mechanics.md, key planning docs).

**Pattern extraction date:** 2026-05-02.

**Confidence:** HIGH for relocation strategy + breakage enumeration + tokenizer choice (all multiply-cited in existing planning artifacts). MEDIUM for per-mode `.md` body shape (no in-tree analog visible; the role contract is clear but the per-mode richness is invented). LOW for `LICENSE.txt` content (project license decision blocker — see CRITICAL #6).

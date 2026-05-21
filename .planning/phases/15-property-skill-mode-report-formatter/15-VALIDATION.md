---
phase: 15
slug: property-skill-mode-report-formatter
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-20
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed; Phase 14 verified — 644+ tests passing project-wide; 84 Phase-14 tests) |
| **Config file** | `pyproject.toml` (project-wide pytest config) |
| **Quick run command** | `uv run pytest tests/test_property_report.py tests/test_property_analyze_cli.py tests/test_skill_routing.py -x` |
| **Full suite command** | `uv run pytest -x` |
| **Estimated runtime** | ~10–20 seconds full suite; ~5–10 seconds quick run |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green AND `python -m evals.runner` exits 0
- **Max feedback latency:** ~20 seconds

---

## Per-Task Verification Map

> Populated by gsd-planner from RESEARCH.md Validation Architecture; refined per-task during planning.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | MODE-01 | — | mode-file present + URL-pin row | unit | `uv run pytest tests/test_skill_routing.py::test_property_mode_row0_present -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | MODE-02 | — | SKILL.md ≤ 4500 cl100k tokens | unit (tiktoken) | `uv run pytest tests/test_skill_routing.py::test_skill_md_token_budget -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | MODE-03 | T-15-V4 / T-15-V5 | orchestrator emits success envelope | subprocess | `uv run pytest tests/test_property_analyze_cli.py::test_success_envelope_shape -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | MODE-03 | — | orchestrator emits error envelope AND exits 0 on bad input | subprocess | `uv run pytest tests/test_property_analyze_cli.py::test_error_envelope_always_exit_0 -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | MODE-03 | T-15-V5 | Pydantic 6-key envelope on stderr | subprocess | `uv run pytest tests/test_property_analyze_cli.py::test_pydantic_validation_envelope_on_stderr -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | MODE-03 | T-15-V4 | household.yml → Phase 14 Household mapping correct | unit | `uv run pytest tests/test_property_analyze_cli.py::test_household_yaml_mapping -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | RPRT-01 | — | render() emits all 6 sections | unit | `uv run pytest tests/test_property_report.py::test_render_emits_six_sections -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | RPRT-01 | — | filename matches `reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md` | unit | `uv run pytest tests/test_property_analyze_cli.py::test_filename_format -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | RPRT-01 | — | same-day same-zpid → `-r2` suffix | unit | `uv run pytest tests/test_property_analyze_cli.py::test_same_day_zpid_suffix -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | RPRT-01 | — | YOUR FIT matrix renders all cells; preferred-DP bolded | unit | `uv run pytest tests/test_property_report.py::test_matrix_renders_all_cells -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | RPRT-01 | — | ineligible cells show blocker code; eligible show ✓ | unit | `uv run pytest tests/test_property_report.py::test_cell_eligibility_marks -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | RPRT-02 | — | 6 italic citation footers (one per section) | unit | `uv run pytest tests/test_property_report.py::test_six_citation_footers -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | RPRT-02 | — | footer is full re-runnable invocation | unit | `uv run pytest tests/test_property_report.py::test_footer_is_full_invocation -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | SC-6 | — | evals.runner exits 0 with new prompt (route + numeric ≥ 0.95) | subprocess | `uv run python -m evals.runner` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_property_report.py` — RPRT-01, RPRT-02 stubs (formatter unit tests; 6-section render; matrix layout; citation footer regex)
- [ ] `tests/test_property_analyze_cli.py` — MODE-03 stubs (envelope shapes; NNN sequencer; same-day-zpid suffix; household.yml mapping; lazy-import smoke)
- [ ] `tests/test_skill_routing.py` — MODE-01, MODE-02 stubs (filesystem-introspection; tiktoken budget assertion; routing-row grep)
- [ ] `evals/fixtures/property/sfh_conforming_001.json` — synthetic PropertyListing JSON (mirror Phase 14 fixture shape; new zpid; new fetched_at)
- [ ] `evals/fixtures/property/sfh_conforming_001.html` — 2KB synthetic HTML stub with `__NEXT_DATA__` block (optional for extractor smoke)
- [ ] `evals/expected/property-analysis-01.json` — oracle pinning verdict level + 3 numerics (Conv30 cell PITI at preferred DP, verdict.reasons count, tax_block.first_year_interest)

*No framework install needed — pytest already shipped.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Zillow URL → WebFetch → JSON extraction round-trip in `modes/property.md` | MODE-01 | WebFetch + tool use is Claude-runtime behavior; cannot exercise from pytest. Synthetic HTML smoke covers the extractor recipe; live URL exercise belongs to manual UAT. | Open Claude Code with the skill loaded; paste a real Zillow URL; verify mode dispatches to property; verify report renders to `reports/`. |
| SKILL.md token budget under live Claude context loading | MODE-02 | tiktoken assertion is a Python-side proxy; actual context loading is Claude-runtime. | Cross-check budget via `python -c "import tiktoken; print(len(tiktoken.encoding_for_model('gpt-4').encode(open('.claude/skills/mortgage-ops/SKILL.md').read())))"` post-edit. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

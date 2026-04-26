# Stack Research

**Domain:** Personal-use mortgage analysis tool (Python calc engine + Claude skill frontend)
**Researched:** 2026-04-26
**Confidence:** HIGH (verified against active GitHub repos, PyPI release dates, and official Anthropic skill conventions)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | ≥3.12 | Calc engine language | Match-typing for Pydantic v2, modern stdlib, decimal performance improvements |
| numpy-financial | ≥1.0.0 (track main for type stubs) | Wraps Excel-style PMT/IPMT/PPMT/NPV/IRR | Active main 2025; Decimal support; vectorizes for parameter sweeps; BSD-3. **Wrap, do not reimplement.** Beware unfixed bug #130 (pmt fv-sign), #131 (irr arch-dependent) — use as oracle for our own tested wrappers |
| Pydantic | ≥2.6 | Loan/Schedule/Payment models with `condecimal(max_digits=14, decimal_places=2)` | First-class Decimal; runtime validation at script boundaries; JSON-string Decimal serialization (correct for finance APIs) |
| python-dateutil | ≥2.9 | `relativedelta` for monthly payment scheduling | Handles month-end edge cases (Jan 31 + 1mo = Feb 28). Already transitive via pandas |
| pandas | ≥2.2 | Schedule output, statistical sanity checks against Freddie SFLLD samples | Standard for tabular finance data |
| pyxirr | ≥0.10.8 | Rust+PyO3 XIRR/XNPV/PMT for batch refi-NPV scenarios | Active Nov 2025; Unlicense; type-hinted overloads; only fast Rust XIRR worth depending on |
| DuckDB | ≥1.0 | Persistence (loans, scenarios, reports tables) | Single-file, ACID, FTS, single-writer simple. Lockfile pattern from career-ops |
| duckdb-async (Node) | ≥1.4.2 | Skill orchestration writes (mirror career-ops `db-write.mjs`) | Career-ops pattern — write subcommands wrapped in `withLock()` |
| pytest | ≥8 | Test framework | Hand-calculated assertions with citation comments (card-ops pattern) |
| mypy | ≥1.10, --strict | Type checker | Money math is unforgiving — strict typing catches Decimal/float mixing |
| ruff | ≥0.4 | Linter + formatter | Single tool replaces black + isort + flake8 |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyyaml | ≥6 | Read regulatory data files (FHFA limits, FHA MIP, IRS Pub 936) | All reference data files |
| js-yaml | ≥4.1 | Read YAML in Node skill scripts | Mirror career-ops |
| playwright | ≥1.59 | Optional: scrape regulatory pages annually | Only for the annual refresh script; not runtime |
| python-frontmatter | ≥1.1 | Parse SKILL.md frontmatter for skill self-tests | Eval harness only |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Fast Python package/venv manager | Pyproject.toml + uv.lock = reproducible installs |
| pre-commit | Git hooks for ruff + mypy | Enforce before commit, not just CI |
| GitHub Actions | CI: pytest + mypy --strict | Career-ops/card-ops both lack CI — adopt this pattern explicitly |
| direnv (.envrc) | Auto-activate venv on cd | Mirror career-ops pattern |

## Installation

```bash
uv init --python 3.12
uv add numpy-financial pydantic python-dateutil pandas pyxirr duckdb pyyaml
uv add --dev pytest mypy ruff pre-commit

# Node side (skill orchestration scripts)
npm init -y
npm install duckdb-async js-yaml
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| numpy-financial (wrap) | Reimplement Decimal `pmt()` from scratch | If numpy-financial bug #130 (pmt fv-sign) blocks balloon-mortgage modeling. Workaround: use IPMT/PPMT path that doesn't trip the bug |
| Pydantic v2 condecimal | dataclasses + manual Decimal validation | Never — Pydantic v2 has first-class Decimal, JSON-string serialization, runtime validation. Plain dataclasses are strictly worse for finance |
| DuckDB | SQLite | If we ever need cross-host sync (we won't for personal use). DuckDB wins on analytics queries (compare 50 scenarios) |
| DuckDB | Parquet + YAML (card-ops style) | If queries are always single-loan. We need cross-scenario SQL — DuckDB |
| pyxirr | numpy-financial.xnpv/xirr | Drop pyxirr if NPV/IRR is rare (< 100 scenarios per session). Add it only when batch stress tests need speed |
| python-dateutil | pendulum 3.x | If we want nicer API. Adds Rust dep. dateutil is already transitive via pandas |
| Newton-Raphson APR (own) | scipy.optimize.brentq | scipy is heavy and brentq doesn't expose tolerance the way Reg Z requires. Newton-Raphson with explicit tolerance per Appendix J |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `mortgage` PyPI (austinmcconnell) | Last release 2019, repo redirects to fork. Mixes float/Decimal in init. APR is just nominal rate (incorrect). | Wrap numpy-financial; vendor `split_payment` closed-form idiom only |
| `mortgage` (jbmohler) | No license declared = legally radioactive | Read for ideas only |
| `amortization` PyPI (roniemartinez) | Float-based, only plain French amortization. No ARM, biweekly, or extra-payment support | Build on numpy-financial — same surface plus extensibility |
| QuantLib | Derivatives-pricing library; float-only; SWIG bindings; no Python type hints; no native MBS/prepayment classes | numpy-financial covers our needs |
| FinancePy | GPL-3.0 (contagious for any commercial future); no mortgage classes | Skip |
| rateslib | Source-Available (commercial license required) | Skip |
| absbox | Wraps a Haskell engine — heavy ops; ABS/MBS structured-products scope | Skip |
| OpenBB | Data platform, not a calc library | Skip |
| `numpy.financial` | Removed from numpy 1.20 | Use numpy-financial spinoff |
| float for money | Compounds rounding error; `0.1 + 0.2 ≠ 0.3` | Decimal (from strings, ROUND_HALF_UP) |
| `Decimal(0.01)` (from float) | Yields `0.01000000000000000020816...` | `Decimal("0.01")` (from string) |
| py-moneyed | Last release > 12 months; Snyk flags discontinued | Raw Decimal for US-only |
| pip + requirements.txt | Slower; lockfile-less in older patterns | uv + pyproject.toml + uv.lock |

## Stack Patterns by Variant

**If we add LE/CD parsing later:**
- Use Camelot (CFPB-maintained for tabular PDF extraction): https://github.com/cfpb/camelot
- Currently OUT OF SCOPE — user enters numbers manually as YAML

**If we add MBS/prepayment modeling:**
- absbox + Hastructure (Haskell engine)
- Currently OUT OF SCOPE — personal use

**If we need cross-currency:**
- py-moneyed
- Currently OUT OF SCOPE — US-only

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| numpy-financial 1.0.0 | numpy ≥1.16 | Last release Oct 2019 — main branch has type stubs but no PyPI release. Pin to git ref if we need stubs |
| pydantic 2.6+ | python ≥3.8 | Decimal serialization defaults to string (correct for finance). `mode="json"` returns strings; `mode="python"` returns Decimal |
| pyxirr 0.10.x | python 3.8-3.13 | Rust+PyO3 — wheel for macOS arm64 available |
| DuckDB 1.0+ | duckdb-async (Node) 1.4.2+ | duckdb-async wraps native bindings; lockfile pattern from career-ops |

## Sources

### Primary (HIGH confidence — verified against live repos)
- https://github.com/numpy/numpy-financial — main branch 2025-05-20 active; bugs #130, #131, #126 noted
- https://github.com/Anexen/pyxirr — last release Nov 2025
- https://docs.pydantic.dev/2.x/api/types/#pydantic.types.condecimal — official condecimal docs
- https://github.com/pydantic/pydantic/issues/7457 — Decimal JSON serialization defaults to string
- https://pbpython.com/amortization-model-revised.html — canonical pandas amortization (port to Decimal)
- https://github.com/jlumbroso/mortgage — Decimal-based reference (read, don't depend)
- https://github.com/austinmcconnell/mortgage — `split_payment` closed-form idiom (vendor)
- https://github.com/anthropics/skills — official skill conventions
- https://code.claude.com/docs/en/skills — frontmatter, progressive disclosure, compaction re-attach
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching — cache TTL, breakeven

### Secondary (MEDIUM confidence)
- https://www.consumerfinance.gov/rules-policy/regulations/1026/j/ — Reg Z Appendix J
- https://www.ffiec.gov/resources/computational-tools/apr — FFIEC APR Tool (oracle, closed source)
- https://github.com/cfpb/hmda-platform — Scala HMDA platform (one-predicate-per-citation pattern)
- https://github.com/cfpb/jumbo-mortgage — JS canonical jumbo classifier (port to Python)

---
*Stack research for: personal mortgage analysis tool*
*Researched: 2026-04-26*

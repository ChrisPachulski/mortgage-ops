# Pitfalls Research

**Domain:** Personal-use mortgage analysis tool
**Researched:** 2026-04-26
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Float-based money math

**What goes wrong:**
Cents drift over 360 amortization periods. Total interest displayed is wrong by dollars-to-tens-of-dollars compared to lender's schedule. User makes a refi decision off bad numbers.

**Why it happens:**
Python's `0.1 + 0.2 == 0.30000000000000004`. Most amortization tutorials (pbpython, austinmcconnell, roniemartinez) use `float`. Default Python rounds `round(x, 2)` produces banker's rounding, not standard rounding.

**How to avoid:**
- `decimal.Decimal` for all dollar amounts and rates
- Construct from strings: `Decimal("0.065")` NOT `Decimal(0.065)` (the latter inherits float error)
- `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` end-of-period only
- Pydantic v2 `condecimal(max_digits=14, decimal_places=2)` for boundary validation
- Set `Context(prec=28)` (default; never overflows for 30yr loans)
- Never mix float and Decimal in the same expression

**Warning signs:**
- Total interest displayed differs from lender's amort by > $1
- Tests pass for `principal=200000` but fail for `principal=200001`
- `assertAlmostEqual(..., places=2)` instead of exact equality
- Final balance ≠ 0.00 (drifts by cents)

**Phase to address:** Phase 1 (foundations — money discipline + Pydantic models). Lock in before any other phase.

---

### Pitfall 2: Math inside the LLM (hallucinated numbers)

**What goes wrong:**
Claude says "Your monthly payment will be $2,531.42" when the actual answer is $2,528.27. User trusts it. Real-money decision made on wrong number.

**Why it happens:**
LLMs are bad at multi-step arithmetic, especially with large numbers and decimals. Even with chain-of-thought, drift is easy. Quote from Anthropic best practices: *"Give Claude a way to verify its work."*

**How to avoid:**
- Every dollar figure that exits the system is computed by a Python script, never by Claude
- SKILL.md instructs Claude to ALWAYS shell out to `scripts/*.py` for math
- Scripts return JSON; Claude reads JSON and narrates
- Bundled scripts run with `--help` first per Anthropic webapp-testing convention
- If Claude is tempted to compute inline, the SKILL.md should re-route

**Warning signs:**
- A user-facing number doesn't appear in any test fixture
- Claude's report has a number that you can't trace to a `scripts/` invocation
- Logs show no Bash calls during a calc-heavy operation

**Phase to address:** Phase X (skill frontend). Hard rule in SKILL.md from day one.

---

### Pitfall 3: Stale regulatory data

**What goes wrong:**
2026 conforming limit is $832,750. Tool says $806,500 (2025 number). User thinks their $820k loan is jumbo (it isn't), gets a worse-rate quote modeled.

**Why it happens:**
FHFA, HUD, IRS publish updates annually (Nov-Dec for following year). If we hardcode in Python, refresh is a code change. If we silently scrape, the source page might restructure and we miss it.

**How to avoid:**
- All regulatory parameters in `data/reference/*.yml`
- Each YAML has `source:` URL and `effective:` date
- Annual refresh is a YAML edit + commit
- Tool warns at startup if `effective:` is more than 12 months old
- Tests assert that `effective:` for current year exists

**Warning signs:**
- Limits don't match a Bankrate / NerdWallet calculator on the same loan
- `effective:` date in YAML is from a previous calendar year
- No commit to `data/reference/` in the past 12 months

**Phase to address:** Phase 2 (regulatory data + rules predicates). Add a startup-time staleness check.

---

### Pitfall 4: Reg Z Appendix J APR drift vs FFIEC tool

**What goes wrong:**
We compute APR = 6.547%, FFIEC tool says 6.551%. Outside the ±0.005% tolerance. User questions the rest of the system's accuracy.

**Why it happens:**
- Appendix J's unit-period model has odd-first-period rules, fractional days, multiple advances
- Our Newton-Raphson tolerance must be tighter than 0.005%
- Day-count conventions matter (actual/365 vs 30/360 etc.)
- Newton-Raphson can converge to a local minimum if seeded badly

**How to avoid:**
- Capture 20+ FFIEC tool outputs as test fixtures (varying loans, terms, advances)
- Newton-Raphson seeded from `npf.rate(...)` (the regular-transaction rate); Appendix J corrections applied iteratively
- Tolerance Decimal("0.00001") (10x tighter than ±0.005% requirement)
- Label our APR "estimated" in user-facing output
- Document the unit-period model in `references/apr-reg-z.md`
- Re-validate annually against fresh FFIEC captures (FFIEC tool may change)

**Warning signs:**
- Test fixtures pass on contrived loans but fail on FFIEC-captured fixtures
- Newton-Raphson takes > 50 iterations to converge
- "Estimated APR" displayed without an actual computation behind it
- Drift is consistent (always +/- 5bps) — sign of a day-count or unit-period error, not random

**Phase to address:** Phase X (estimated APR). Single-issue dedicated phase recommended given complexity.

---

### Pitfall 5: ARM cap/floor/margin/reset off-by-one errors

**What goes wrong:**
5/1 ARM resets at month 60. We reset at month 61 (or 59). User sees a payment jump in the wrong month, distrust the rest of the simulator.

**Why it happens:**
- "5/1 ARM" means 5 years fixed (60 months), then resets ANNUALLY (the "1"). First reset is at month 61 (start of year 6), or month 60 (end of year 5)?
- Cap structure "2/2/5" can mean (initial / periodic / lifetime) or (periodic-after-first / annual / lifetime)
- "Floor = margin" sometimes; "floor = note rate" other times
- Some ARMs reset every 6 months after initial period, not every 12

**How to avoid:**
- Define ARM mechanics rigorously in `references/arm-mechanics.md` (cite Freddie/Fannie Selling Guides)
- Pydantic model with explicit fields: `initial_period_months`, `reset_period_months`, `initial_cap_bps`, `periodic_cap_bps`, `lifetime_cap_bps`, `floor_rate`, `margin_bps`
- Document convention: reset at start of period (month 61 for 5/1)
- Test against published ARM scenarios (e.g., MGIC ARM calculator screenshots)

**Warning signs:**
- ARM tests use only one reset point (60 or 61) — should test both conventions explicitly
- Reset "skips a month" or "doubles up"
- New rate after cap-applied < floor (should be impossible)

**Phase to address:** Phase X (ARM modeling). Dedicate phase; complex enough.

---

### Pitfall 6: PMI / MIP termination rules wrong

**What goes wrong:**
Tool says PMI auto-terminates at 78% LTV per HPA (true for conventional). User has FHA loan; FHA MIP doesn't auto-terminate at 78% — it's life-of-loan if LTV > 90% at origination, else 11 years. User makes a refi decision based on phantom PMI savings.

**Why it happens:**
Conventional PMI (Homeowners Protection Act 1998) and FHA MIP have different termination rules. Easy to conflate. FHA MIP rules also changed (Mortgagee Letter 2023-05) — pre-2013 origination loans have different rules.

**How to avoid:**
- Separate predicate functions: `lib/rules/conventional_pmi.py` (HPA) vs `lib/rules/fha_mip.py` (HUD ML)
- Each function takes loan-type-specific params (origination_date for FHA grandfathering)
- Tests for both auto-termination (78% LTV) and request-termination (80% LTV) for conventional
- Tests for FHA scenarios: LTV > 90% at orig (life of loan) vs LTV ≤ 90% (11 years) vs pre-2013 (different rules)
- `references/mip-pmi.md` documents both regimes

**Warning signs:**
- One PMI function for both conventional and FHA
- No `origination_date` parameter in MIP calc
- Tests don't include both LTV > 90% and LTV ≤ 90% cases for FHA

**Phase to address:** Phase 2 (rules predicates). Critical for refinance decisions.

---

### Pitfall 7: Loan Type confusion (conforming vs jumbo vs FHA vs VA)

**What goes wrong:**
$830k loan in a non-high-cost county. Tool classifies as conforming (because $830k < $832,750 baseline). User actually needs a high-balance / jumbo product because their county limit is the baseline, not the ceiling.

**Why it happens:**
- Conforming loan limit is per-county for high-cost areas (up to ceiling 150% of baseline)
- "Jumbo" means above the applicable county limit, not above the baseline
- FHA limits are different (floor 65% of conforming baseline)
- VA limits same as conforming since 2020 (no county cap for full-entitlement vets)
- USDA has no loan limit but has income limits

**How to avoid:**
- `data/reference/conforming-limits-2026.yml` includes per-county XLSX from FHFA
- `lib/rules/loan_type.py` requires county input; fails loud if missing
- Adopt `cfpb/jumbo-mortgage` JS pattern: explicit "I need county data" error, not silent default
- Tests for: high-cost county at ceiling, low-cost county at baseline, FHA floor county, FHA ceiling county

**Warning signs:**
- Tool answers loan-type without asking for county
- "Default" baseline used when county unknown (silent fallback)
- Same loan amount classified differently in two counties produces no test failure

**Phase to address:** Phase 2 (rules predicates).

---

### Pitfall 8: Refinance NPV sign convention errors

**What goes wrong:**
NPV says "refinancing saves $34,000". Sign is flipped — actually costs $34,000. User refis a perfectly good loan into a worse one.

**Why it happens:**
- `numpy_financial.npv` and Excel's NPV use different sign conventions for cashflows
- "Cashflow IN" vs "Cashflow OUT" depends on perspective (lender vs borrower)
- Closing costs are typically modeled as t=0 cashflow; new payments as outflows; interest savings as inflows
- Easy to flip a sign and have it pass smell tests

**How to avoid:**
- Document sign convention explicitly in `references/refi-npv.md`: "Borrower perspective: outflows negative, savings positive"
- Pydantic model `RefiCashflow` with `direction: Literal["outflow", "inflow"]`
- Test against worked example: a known-good refi with hand-calculated NPV
- Test against the trivially-better case (rate drops 200bps, no closing costs) — must show positive NPV
- Test against the trivially-worse case (same rate, $5k closing costs) — must show negative NPV

**Warning signs:**
- NPV positive for higher-rate refis
- NPV insensitive to closing-cost amount
- Test fixtures all have NPV > 0 (no negative cases)

**Phase to address:** Phase X (refinance NPV). Subagent boundary helps quarantine bugs.

---

### Pitfall 9: Skill content overflow → re-attach truncation after compaction

**What goes wrong:**
Mid-session, conversation hits compaction. Claude Code re-attaches first 5k tokens of each invoked skill. Our SKILL.md is 8k tokens; the routing rules at line 200 are now lost. Claude doesn't know which mode to use.

**Why it happens:**
- Anthropic skill compaction policy: re-attach first 5k tokens, total budget 25k across all re-attached skills
- Career-ops/card-ops both have SKILL.md content but didn't worry about ordering for compaction

**How to avoid:**
- SKILL.md ≤ 500 lines, ≤ 5k tokens
- Load-bearing routing logic in first 200 lines
- Topic depth in `references/*.md` (loaded only when SKILL.md routes there)
- Eval harness asserts SKILL.md token count budget

**Warning signs:**
- SKILL.md > 500 lines
- Routing rules buried after long preambles
- After compaction, Claude doesn't recognize a mode it routed to earlier

**Phase to address:** Phase X (skill frontend). Token-count CI check.

---

### Pitfall 10: User layer auto-update (career-ops Data Contract violation)

**What goes wrong:**
User edits `config/household.yml` to add a new applicant. Next time they run a phase, system "auto-updates" the file (e.g., normalizes formatting), losing the user's comment about why a number changed.

**Why it happens:**
- Tools that "helpfully" reformat YAML lose comments
- Auto-update logic in update scripts may overwrite user files

**How to avoid:**
- DATA_CONTRACT.md explicitly: User Layer is READ-ONLY from system code
- `config/household.yml`, `config/profile.yml`, `modes/_profile.md` never written to by system
- System updates check git diff before overwriting any user-layer file
- All user-layer files in `.gitignore`
- Tests assert no system file references `Write(config/household.yml)` etc.

**Warning signs:**
- Code path writes to a path under `config/` or `modes/_profile.md`
- Update script doesn't have a "skip user files" check
- User reports "my config got changed"

**Phase to address:** Phase 1 (foundations) + DATA_CONTRACT.md commit.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip type hints in `lib/rules/*.py` | Faster initial implementation | Annual regulatory refresh harder; mypy can't catch citation drift | Never — rules are the audit trail |
| Float for "non-money" rates | "Rates aren't really money" | Decimal(rate) * Decimal(principal) — TypeError unless we normalize | Never — keep all numeric fields Decimal |
| Hardcode 2026 limits in Python | Avoids YAML loading | Annual update is a code change, not data change | Never — YAML from day one |
| One big `lib/qualification.py` | Easier to write initial logic | Refactor cost is huge; rules become tangled | Never — predicate-per-citation from day one |
| Skip `lib/rules/atr_qm.py` (43% DTI cap is gone) | Saves a file | Future regulation may reinstate; we lose the citation hook | Skip the predicate but commit the file with a STUB + citation comment |
| Skip subagents, run sweeps in main context | Simpler architecture | Stress sweeps pollute main conversation; compaction kicks in fast | OK for v1 if user only runs single-loan analysis |
| Skip `evals/` directory | Less ceremony | No regression detection on skill quality | OK for v1; add when skill behavior drifts |
| Skip CI | Faster setup | mypy / pytest regressions slip through | Never — career-ops/card-ops both lack CI; we improve on this |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| FRED MCP | Caching latest weekly rate forever | Cache 7 days max; FRED publishes Thursdays |
| numpy-financial | Trusting `pmt(rate, n, pv, fv)` for balloon mortgages | Bug #130 — fv-sign flipped. Avoid `fv≠0` path; compute residual manually |
| numpy-financial | Trusting `irr` across architectures | Bug #131 — non-deterministic across CPU. Use pyxirr for IRR |
| Pydantic Decimal serialization | Expecting float in JSON | Default is string. `model_dump(mode="json")` gives strings; downstream consumers must parse |
| dateutil relativedelta | Forgetting month-end edge cases | Test January 31 + relativedelta(months=1) (= Feb 28/29) |
| DuckDB | Concurrent writes without lockfile | Always wrap writes in `withLock()`; stale recovery at 60s |
| FFIEC APR Tool | Treating as a live API | Closed source; manual capture only. Re-capture annually if Fed updates |

## Performance Traps

For personal use, performance is rarely an issue. But:

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Generating full 360-row schedule for every PMT lookup | Slow iteration in stress sweeps | Cache schedule per (principal, rate, term); use `npf.ipmt`/`ppmt` for arbitrary period without iterating | Not an issue at < 100 scenarios |
| Newton-Raphson for APR without good seed | 50+ iterations | Seed from `npf.rate(...)` (the regular-transaction approximation) | Not an issue |
| Reading reference YAML on every predicate call | Slow rules evaluation | `functools.lru_cache` on YAML loaders | Not an issue at typical use |
| DuckDB on a small DB without indices | Mostly fine | DuckDB is in-process, fast on small data | Not an issue |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing `config/household.yml` (income, SSN, account numbers) | PII leak | Strict `.gitignore`; pre-commit hook checking for `household.yml` in staged files |
| Storing financial data in `data/mortgage-ops.duckdb` and committing | PII leak | `data/*.duckdb` gitignored; only `data/reference/` and `data/known-loans.yml` committed |
| Logging full loan details to stdout (then captured by Claude) | PII leak in conversation logs | Scripts log only computed results, not user-identifying inputs |
| Passing API keys for FRED in commits | Key leak | FRED public series don't need a key; if we ever add a keyed API, use `.env` (gitignored) and `.envrc` |
| Storing partner/spouse PII in shared household.yml | Trust violation | Both applicants must consent to data model; document in DATA_CONTRACT.md |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Reporting numbers without units ($, %, months) | Confusion; misinterpretation | Always include units in reports |
| Showing "estimated APR" without explaining why | User thinks tool is unreliable | Footer: "APR estimated per Reg Z Appendix J methodology, validated against FFIEC tool ±0.005%" |
| Hiding which rules predicate fired | "Why am I disqualified?" | Each affordability output cites the binding rule (e.g., "blocked by VA-RESIDUAL-WEST-FAMILY-4") |
| Burying the headline number under detail | User has to read 3 paragraphs to find their payment | Headline first; details in collapsible sections |
| No way to override a wrong assumption | User can't say "no, my insurance is $X, not your default" | Every default must be overridable in CLI args / household.yml |

## "Looks Done But Isn't" Checklist

- [ ] **Amortization schedule:** Often missing the final-payment cleanup (last payment must clear balance to exactly $0.00). Verify `final_balance == Decimal("0.00")` and `sum(principal_payments) == original_principal`.
- [ ] **APR calc:** Often passes for vanilla loans but fails for odd-first-period or multi-advance. Verify against FFIEC fixtures spanning these cases.
- [ ] **Refi NPV:** Often correct sign on rate-drop cases but wrong on rate-rise cases. Verify with negative-NPV fixture.
- [ ] **DTI rule:** Often computes the ratio but doesn't fail loud when income data missing. Verify "missing required field" raises, doesn't silently default.
- [ ] **ARM reset:** Often works at month 60 but fails at month 61. Verify both reset month conventions.
- [ ] **MIP/PMI termination:** Often works for conventional, wrong for FHA. Verify FHA-specific tests cover origination date variants.
- [ ] **Skill SKILL.md:** Often complete but exceeds 5k tokens. Verify token count under budget; routing rules in first 200 lines.
- [ ] **Reference YAML:** Often has data but missing `source:` URL or `effective:` date. Verify all reference files have both.
- [ ] **Household model:** Often supports one applicant. Verify joint-applicant tests with two-income scenarios.
- [ ] **Subagents:** Often spawn but don't return summary cleanly to main context. Verify "what came back" is < 1k tokens.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Float drift in shipped amortization | HIGH | Find every codepath touching `float`; convert to Decimal; re-run all fixtures; manual audit of any persisted DuckDB rows |
| LLM hallucinated number reached user-facing report | MEDIUM | Add SKILL.md rule + add eval harness regression test |
| Stale regulatory YAML | LOW | Edit YAML, commit with "data: refresh 2027 limits" |
| APR drift outside ±0.005% | MEDIUM | Capture more FFIEC fixtures; tune Newton-Raphson tolerance / day-count |
| ARM off-by-one | MEDIUM | Add explicit reset-month test, fix, re-run all ARM fixtures |
| User layer auto-overwritten | HIGH | git revert; harden DATA_CONTRACT enforcement; add pre-commit hook |
| Skill SKILL.md exceeds 5k tokens | LOW | Move content to `references/`, re-route in SKILL.md |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Float-based money math | Phase 1 (foundations) | Pydantic models reject float in money fields; test fixtures use exact Decimal equality |
| Math inside the LLM | Skill phase | SKILL.md hard rule; eval harness asserts every reported number traces to a script call |
| Stale regulatory data | Phase 2 (rules + reference data) | Startup-time staleness check; tests assert current-year YAML exists |
| Reg Z APR drift | Phase X (APR) | 20+ FFIEC fixtures; tolerance test; Newton-Raphson convergence test |
| ARM reset off-by-one | Phase X (ARM) | Both reset-month conventions tested explicitly; published-scenario fixtures |
| PMI/MIP termination errors | Phase 2 (rules) | Separate predicates per regime; FHA grandfathering test cases |
| Loan-type confusion | Phase 2 (rules) | County data required; tests across high-cost / baseline / FHA floor / FHA ceiling |
| Refi NPV sign errors | Refi phase | Both positive-NPV and negative-NPV fixtures |
| Skill content overflow | Skill phase | Token-count check in CI |
| User layer auto-update | Phase 1 (foundations) + ongoing | Pre-commit hook; DATA_CONTRACT.md committed; tests assert no writes to user-layer paths |

## Sources

- Career-ops repo deep-dive (especially DATA_CONTRACT.md, mode hardcoded-metrics anti-pattern)
- Card-ops repo deep-dive (test_rewards_grocery_cap.py — hand-calculated test pattern; rules drift)
- Python finance survey (numpy-financial bugs #130, #131, #126; Decimal best practices)
- Claude/MCP ecosystem survey (skill compaction re-attach budget; webapp-testing scripts doctrine)
- OSS / regulatory survey (austinmcconnell APR-is-just-nominal-rate bug; cfpb/jumbo-mortgage's "fail loud on missing county" pattern)
- https://github.com/numpy/numpy-financial/issues — bugs to avoid
- https://www.consumerfinance.gov/rules-policy/regulations/1026/22/ — Reg Z APR tolerances
- https://www.ffiec.gov/resources/computational-tools/apr — FFIEC oracle
- HUD Mortgagee Letter 2023-05 — current FHA MIP rules

---
*Pitfalls research for: personal mortgage analysis tool*
*Researched: 2026-04-26*

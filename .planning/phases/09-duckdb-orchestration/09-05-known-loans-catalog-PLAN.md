---
phase: 09
plan: 05
type: execute
wave: 5
depends_on:
  - "09-00"
files_modified:
  - data/known-loans.yml
  - tests/test_orchestration/test_known_loans_smoke.py
must_haves:
  truths:
    - "data/known-loans.yml exists in the Reference Layer (committed; per DATA_CONTRACT.md line 67) with top-level `source:` URL and `effective:` ISO-8601 date keys"
    - "data/known-loans.yml contains a top-level `products:` array with at least 7 entries: conv-30yr-fixed, conv-15yr-fixed, arm-5-1, arm-7-1, fha-30yr, va-30yr, jumbo-30yr-fixed (verbatim from 09-RESEARCH.md sample)"
    - "Every product entry has all 9 required keys: id, label, type, principal, apr, term_months, frequency, origination_date, citation_url"
    - "All money values (`principal`) and rate values (`apr`) are quoted strings (Decimal-string discipline; never bare YAML floats)"
    - "test_known_loans_smoke.py::test_known_loans_catalog_complete xfail flips to passing (PERS-07 closure)"
    - "yaml.safe_load succeeds on data/known-loans.yml (valid YAML; no parse errors)"
    - "Catalog is loadable by both Python (yaml.safe_load) and Node (js-yaml) — verified by Python smoke + sanity manual js-yaml load"
  artifacts:
    - path: "data/known-loans.yml"
      provides: "Reference Layer product catalog (PERS-07); 7 representative mortgage products with rates anchored to 2026-04-24 PMMS"
      contains: "products:"
    - path: "tests/test_orchestration/test_known_loans_smoke.py"
      provides: "PERS-07 + ROADMAP SC-5 closure test; asserts presence + shape of all 7 entries"
      contains: "def test_known_loans_catalog_complete"
  key_links:
    - from: "tests/test_orchestration/test_known_loans_smoke.py"
      to: "data/known-loans.yml"
      via: "yaml.safe_load(Path('data/known-loans.yml').read_text())"
      pattern: "yaml.safe_load"
    - from: "data/known-loans.yml"
      to: "DATA_CONTRACT.md Reference Layer"
      via: "committed-to-git, source+effective convention"
      pattern: "data/known-loans.yml"
autonomous: true
requirements:
  - PERS-07
tags:
  - phase-09
  - duckdb-orchestration
  - known-loans
  - reference-layer
  - pers-07
---

<objective>
**Goal:** Commit `data/known-loans.yml` (Reference Layer artifact, NOT Data Layer) with all 7 representative mortgage products specified in 09-RESEARCH.md §"Sample data/known-loans.yml" (lines 395-479): conv-30yr-fixed, conv-15yr-fixed, arm-5-1, arm-7-1, fha-30yr, va-30yr, jumbo-30yr-fixed. Flip the Wave 0 xfail in `tests/test_orchestration/test_known_loans_smoke.py::test_known_loans_catalog_complete` so PERS-07 + ROADMAP SC-5 are pinned by an executable assertion, not just a hand-eyeball.

**Purpose:** PERS-07 closure: "data/known-loans.yml catalog: 30yr fixed, 15yr fixed, ARM 5/1, ARM 7/1, FHA 30yr, VA 30yr, jumbo." This catalog seeds Phase 10's skill `evaluate` mode and Phase 12's eval-harness regression set; without it, downstream phases have no canonical product list to route against. Reference-Layer placement (NOT `data/mortgage-ops.duckdb` which is Data Layer + gitignored) is the load-bearing rule per DATA_CONTRACT.md line 67.

**Output:** 1 new committed YAML file under `data/` (~70 lines, 7 product entries copy-pasted verbatim from RESEARCH §"Sample data/known-loans.yml"); 1 xfail flipped (PERS-07 stub becomes passing); pass count delta +1, xfail count delta -1.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/09-duckdb-orchestration/09-PATTERNS.md
@.planning/phases/09-duckdb-orchestration/09-RESEARCH.md
@CLAUDE.md
@DATA_CONTRACT.md
@tests/test_orchestration/test_known_loans_smoke.py

<interfaces>
**Catalog file path (load-bearing — Reference Layer per DATA_CONTRACT.md line 67):**
`data/known-loans.yml`

**Top-level YAML schema:**
```yaml
source: <URL>            # required; Reference Layer convention
effective: <YYYY-MM-DD>  # required; Reference Layer convention (staleness check input)
products:                # required; array of product entries
  - <product entry>
  - <product entry>
  ...
```

**Per-product entry schema (D-05-02; all 9 fields REQUIRED — verbatim from RESEARCH §Sample):**
| Key | Type | Notes |
|-----|------|-------|
| `id` | string | unique slug (e.g., `conv-30yr-fixed`) |
| `label` | string | human-readable description |
| `loan_type` | string | one of: fixed, arm, fha, va, usda, jumbo (Literal options at lib/models.py:45) |
| `principal` | string | DECIMAL-string discipline (e.g., `"400000.00"`); MUST be quoted |
| `apr` | string | DECIMAL-string discipline (e.g., `"0.068100"`); MUST be quoted; 6-decimal precision |
| `term_months` | integer | typically 180 or 360 |
| `frequency` | string | typically `monthly` |
| `origination_date` | date | YAML ISO date (e.g., `2026-05-01`); represents the rate-effective date for this sample |
| `citation_url` | string | URL of the rate source (FRED series, HUD page, FHFA page, etc.) |

**Required 7 product IDs (set membership; PERS-07 closure):**
1. `conv-30yr-fixed`
2. `conv-15yr-fixed`
3. `arm-5-1`
4. `arm-7-1`
5. `fha-30yr`
6. `va-30yr`
7. `jumbo-30yr-fixed`

**Wave 0 stub being flipped (NAME IS PINNED — DO NOT RENAME per Wave 0 D-00 Rule-1):**
`tests/test_orchestration/test_known_loans_smoke.py::test_known_loans_catalog_complete`

**Smoke test signature (lifted verbatim from RESEARCH lines 481-503):**
```python
import yaml
from pathlib import Path

REQUIRED_IDS = {
    "conv-30yr-fixed", "conv-15yr-fixed",
    "arm-5-1", "arm-7-1",
    "fha-30yr", "va-30yr", "jumbo-30yr-fixed",
}

def test_known_loans_catalog_complete():
    path = Path("data/known-loans.yml")
    catalog = yaml.safe_load(path.read_text())
    assert "source" in catalog and "effective" in catalog
    ids = {p["id"] for p in catalog["products"]}
    assert REQUIRED_IDS.issubset(ids), f"missing: {REQUIRED_IDS - ids}"
    for p in catalog["products"]:
        assert {"id","label","loan_type","principal","apr","term_months",
                "frequency","origination_date","citation_url"} <= set(p.keys())
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write data/known-loans.yml with all 7 product entries</name>
  <files>data/known-loans.yml</files>
  <read_first>
    - .planning/phases/09-duckdb-orchestration/09-RESEARCH.md lines 395-479 (sample yaml — copy verbatim)
    - DATA_CONTRACT.md lines 56-69 (Reference Layer rules)
    - .gitignore (verify `data/known-loans.yml` is NOT excluded; Reference Layer must be committed)
  </read_first>
  <action>
    Create `data/known-loans.yml` by copying the sample from 09-RESEARCH.md §"Sample data/known-loans.yml" (lines 399-479) verbatim. The file is the Reference Layer source of truth; any deviation from the sample requires a CONTEXT-level decision (it is a published artifact other phases route against).

    **Step 1 — Verify the data/ directory exists** (Phase 1 created it; Phase 2 added .gitkeep under data/reference/). The file lives directly under `data/`, NOT `data/reference/` (the latter is for regulatory tables; known-loans is the product catalog — DATA_CONTRACT.md line 67 places it at `data/known-loans.yml`).

    **Step 2 — Write the file with the following exact content** (copied verbatim from 09-RESEARCH.md lines 399-479, including all comments):

    ```yaml
    # data/known-loans.yml
    # mortgage-ops product catalog. Reference Layer (committed; manually refreshed).
    # Each entry is a representative product, not a live offer; rates from FRED PMMS week
    # of 2026-04-24 (MORTGAGE30US 6.81%, MORTGAGE15US 6.05%) for the conforming products,
    # and from agency rate-sheet samples for FHA/VA/jumbo/ARM.

    source: https://www.freddiemac.com/pmms
    effective: 2026-04-24

    products:
      - id: conv-30yr-fixed
        label: "Conventional 30-year fixed"
        loan_type: fixed
        principal: "400000.00"
        apr: "0.068100"             # FRED MORTGAGE30US 2026-04-24
        term_months: 360
        frequency: monthly
        origination_date: 2026-05-01
        citation_url: https://fred.stlouisfed.org/series/MORTGAGE30US

      - id: conv-15yr-fixed
        label: "Conventional 15-year fixed"
        loan_type: fixed
        principal: "400000.00"
        apr: "0.060500"             # FRED MORTGAGE15US 2026-04-24
        term_months: 180
        frequency: monthly
        origination_date: 2026-05-01
        citation_url: https://fred.stlouisfed.org/series/MORTGAGE15US

      - id: arm-5-1
        label: "5/1 ARM (5-year initial fixed, annual reset thereafter)"
        loan_type: arm
        principal: "400000.00"
        apr: "0.062500"             # initial 5yr fixed rate (representative)
        term_months: 360
        frequency: monthly
        origination_date: 2026-05-01
        citation_url: https://www.consumerfinance.gov/owning-a-home/loan-options/adjustable-rate-mortgages/

      - id: arm-7-1
        label: "7/1 ARM (7-year initial fixed, annual reset thereafter)"
        loan_type: arm
        principal: "400000.00"
        apr: "0.064000"             # initial 7yr fixed rate (representative)
        term_months: 360
        frequency: monthly
        origination_date: 2026-05-01
        citation_url: https://www.consumerfinance.gov/owning-a-home/loan-options/adjustable-rate-mortgages/

      - id: fha-30yr
        label: "FHA 30-year fixed"
        loan_type: fha
        principal: "400000.00"
        apr: "0.066500"             # representative; FHA typically slightly below conv
        term_months: 360
        frequency: monthly
        origination_date: 2026-05-01
        citation_url: https://www.hud.gov/program_offices/housing/sfh/ins/sfh203b

      - id: va-30yr
        label: "VA 30-year fixed"
        loan_type: va
        principal: "400000.00"
        apr: "0.063500"             # representative; VA often lowest
        term_months: 360
        frequency: monthly
        origination_date: 2026-05-01
        citation_url: https://www.benefits.va.gov/HOMELOANS/

      - id: jumbo-30yr-fixed
        label: "Jumbo 30-year fixed (above 2026 conforming limit)"
        loan_type: jumbo
        principal: "1000000.00"     # > 2026 conforming baseline ($806,500)
        apr: "0.069500"             # representative; jumbo varies widely
        term_months: 360
        frequency: monthly
        origination_date: 2026-05-01
        citation_url: https://www.fhfa.gov/news/news-release/conforming-loan-limit-values-2026
    ```

    **Step 3 — Manual sanity check** (run after writing):

    ```bash
    python -c "import yaml; d = yaml.safe_load(open('data/known-loans.yml')); print(len(d['products']), 'products'); print(sorted(p['id'] for p in d['products']))"
    ```

    Expected output: `7 products` then a sorted list including all 7 required IDs.

    **Step 4 — Confirm Reference Layer placement** (data/known-loans.yml MUST be tracked by git — it is the catalog, not user-state):

    ```bash
    git check-ignore data/known-loans.yml
    ```

    Expected: exit code 1 (NOT ignored — it's Reference Layer, must be committed). If exit 0 (ignored), STOP — `.gitignore` has an over-broad `data/*` rule that needs a `!data/known-loans.yml` whitelist (which would be deferred to Plan 09-07).
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && python -c "import yaml; d = yaml.safe_load(open('data/known-loans.yml')); assert len(d['products']) >= 7, f'have {len(d[\"products\"])}'; ids = {p['id'] for p in d['products']}; required = {'conv-30yr-fixed','conv-15yr-fixed','arm-5-1','arm-7-1','fha-30yr','va-30yr','jumbo-30yr-fixed'}; assert required <= ids, f'missing {required - ids}'; print('OK', sorted(ids))"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f data/known-loans.yml` exits 0
    - `python -c "import yaml; yaml.safe_load(open('data/known-loans.yml'))"` exits 0 (valid YAML)
    - `grep -c '^  - id:' data/known-loans.yml` returns at least 7
    - `grep -c 'conv-30yr-fixed' data/known-loans.yml` returns 1
    - `grep -c 'conv-15yr-fixed' data/known-loans.yml` returns 1
    - `grep -c 'arm-5-1' data/known-loans.yml` returns 1
    - `grep -c 'arm-7-1' data/known-loans.yml` returns 1
    - `grep -c 'fha-30yr' data/known-loans.yml` returns 1
    - `grep -c 'va-30yr' data/known-loans.yml` returns 1
    - `grep -c 'jumbo-30yr-fixed' data/known-loans.yml` returns 1
    - `grep -c '^source:' data/known-loans.yml` returns 1
    - `grep -c '^effective:' data/known-loans.yml` returns 1
    - `grep -cE '^\s+principal: "[0-9]+\.[0-9]{2}"' data/known-loans.yml` returns at least 7 (all principals quoted with cent precision)
    - `grep -cE '^\s+apr: "0\.[0-9]{6}"' data/known-loans.yml` returns at least 7 (all APRs quoted with 6-decimal precision)
    - `grep -cE '^\s+loan_type: (fixed|arm|fha|va|usda|jumbo)$' data/known-loans.yml` returns at least 7 (D-05-02 revision: field is `loan_type`, not `type`; values are lib.models.Loan Literal options)
    - `grep -c '^\s\+type: ' data/known-loans.yml` returns 0 (no entry uses the legacy `type:` field name; PATTERNS round-trip with lib/models.py:45 requires `loan_type:`)
    - `git check-ignore data/known-loans.yml` exits 1 (NOT ignored — Reference Layer is committed)
  </acceptance_criteria>
  <done>
    data/known-loans.yml exists with all 7 product entries; YAML valid; quotes preserved on money/rate strings; tracked by git (not gitignored).
  </done>
</task>

<task type="auto">
  <name>Task 2: Flip test_known_loans_catalog_complete xfail</name>
  <files>tests/test_orchestration/test_known_loans_smoke.py</files>
  <read_first>
    - tests/test_orchestration/test_known_loans_smoke.py (Wave 0 stub state)
    - .planning/phases/09-duckdb-orchestration/09-RESEARCH.md lines 481-503 (smoke-test reference shape)
    - .planning/phases/09-duckdb-orchestration/09-00-test-infrastructure-PLAN.md lines 344-377 (Wave-0 stub format precedent)
  </read_first>
  <action>
    Replace the Wave 0 stub `tests/test_orchestration/test_known_loans_smoke.py` with a real implementation. REMOVE the `@pytest.mark.xfail(strict=True, ...)` decorator. The function body is lifted verbatim from RESEARCH §"Smoke test (per SC-5)" (lines 483-503), with two adjustments: (a) use `pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "known-loans.yml"` for repo-root-anchored path resolution (matches conftest's REPO_ROOT idiom from Wave 0 D-00); (b) use a typed Set[str] annotation for REQUIRED_IDS to satisfy `mypy --strict`.

    Replace ENTIRE file content with:

    ```python
    """Phase 9 known-loans.yml catalog smoke test (PERS-07 + ROADMAP SC-5).

    Wave 5 (Plan 09-05) ships data/known-loans.yml as the Reference Layer
    product catalog. This test asserts: (1) the file is valid YAML, (2) the
    top-level Reference Layer keys (source, effective) are present, (3) all
    7 PERS-07-required product IDs exist, and (4) every product entry has
    the full 9-key schema.
    """

    from __future__ import annotations

    from pathlib import Path

    import yaml

    REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    CATALOG_PATH: Path = REPO_ROOT / "data" / "known-loans.yml"

    # PERS-07: catalog must include 30yr fixed, 15yr fixed, ARM 5/1, ARM 7/1,
    # FHA 30yr, VA 30yr, jumbo 30yr (verbatim from REQUIREMENTS.md PERS-07
    # and 09-RESEARCH.md §"Sample data/known-loans.yml" lines 488-492).
    REQUIRED_IDS: frozenset[str] = frozenset(
        {
            "conv-30yr-fixed",
            "conv-15yr-fixed",
            "arm-5-1",
            "arm-7-1",
            "fha-30yr",
            "va-30yr",
            "jumbo-30yr-fixed",
        }
    )

    # Per RESEARCH §Sample lines 481-503: every product entry MUST carry these
    # 9 keys. Missing keys break Phase 10 routing + Phase 12 eval-harness lookup.
    REQUIRED_PER_ENTRY_KEYS: frozenset[str] = frozenset(
        {
            "id",
            "label",
            "loan_type",
            "principal",
            "apr",
            "term_months",
            "frequency",
            "origination_date",
            "citation_url",
        }
    )


    def test_known_loans_catalog_complete() -> None:
        """PERS-07 + ROADMAP SC-5: data/known-loans.yml exists with at least
        the 7 required product entries, each carrying the full 9-key schema,
        and the top-level Reference Layer convention keys (source, effective)
        are present (per DATA_CONTRACT.md line 69).
        """
        assert CATALOG_PATH.exists(), (
            f"data/known-loans.yml missing at {CATALOG_PATH}; "
            f"Plan 09-05 must commit the Reference Layer catalog."
        )

        catalog = yaml.safe_load(CATALOG_PATH.read_text())
        assert isinstance(catalog, dict), (
            f"catalog root must be a YAML mapping; got {type(catalog).__name__}"
        )

        # Reference Layer convention (DATA_CONTRACT.md line 69)
        assert "source" in catalog, "missing top-level 'source:' key (Reference Layer convention)"
        assert "effective" in catalog, "missing top-level 'effective:' key (Reference Layer convention)"

        # PERS-07 required products
        assert "products" in catalog, "missing top-level 'products:' array"
        products = catalog["products"]
        assert isinstance(products, list), (
            f"'products' must be a YAML list; got {type(products).__name__}"
        )

        ids = {p["id"] for p in products}
        missing = REQUIRED_IDS - ids
        assert not missing, (
            f"PERS-07 violation: missing required product IDs: {sorted(missing)}; "
            f"have: {sorted(ids)}"
        )

        # Per-entry schema check
        for p in products:
            entry_keys = set(p.keys())
            entry_missing = REQUIRED_PER_ENTRY_KEYS - entry_keys
            assert not entry_missing, (
                f"product {p.get('id', '<unknown>')} missing keys: "
                f"{sorted(entry_missing)}"
            )

            # Decimal-string discipline (CLAUDE.md non-negotiable):
            # principal + apr must be quoted strings, not bare YAML floats.
            assert isinstance(p["principal"], str), (
                f"product {p['id']}: principal must be a quoted string "
                f"(Decimal discipline), got {type(p['principal']).__name__}"
            )
            assert isinstance(p["apr"], str), (
                f"product {p['id']}: apr must be a quoted string "
                f"(Decimal discipline), got {type(p['apr']).__name__}"
            )

            # PATTERNS Critical Issue (lib/models.py:45 Loan.loan_type Literal):
            # known-loans.yml must round-trip into the Loan Pydantic model in
            # Phase 10 routing; loan_type values MUST be drawn from the same
            # Literal options as lib.models.Loan.loan_type.
            assert p["loan_type"] in {"fixed", "arm", "fha", "va", "usda", "jumbo"}, (
                f"product {p['id']}: loan_type {p['loan_type']!r} is not a "
                f"valid lib.models.Loan.loan_type Literal option "
                f"(must be one of: fixed, arm, fha, va, usda, jumbo)"
            )
    ```

    The `@pytest.mark.xfail(strict=True, ...)` decorator added in Wave 0 MUST be removed. The `pytest.fail("Wave 0 stub")` body MUST be removed. The `import pytest` line MAY remain or be removed (no longer needed); prefer removing it for `ruff` cleanliness.
  </action>
  <verify>
    <automated>cd /Users/cujo253/Documents/mortgage-ops && pytest tests/test_orchestration/test_known_loans_smoke.py -v --tb=short 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_orchestration/test_known_loans_smoke.py -v 2>&1 | grep -c PASSED` returns 1
    - `pytest tests/test_orchestration/test_known_loans_smoke.py -v 2>&1 | grep -c XFAIL` returns 0
    - `grep -c "@pytest.mark.xfail" tests/test_orchestration/test_known_loans_smoke.py` returns 0
    - `grep -c "Wave 0 stub" tests/test_orchestration/test_known_loans_smoke.py` returns 0
    - `grep -c "def test_known_loans_catalog_complete" tests/test_orchestration/test_known_loans_smoke.py` returns 1
    - `grep -c "REQUIRED_IDS" tests/test_orchestration/test_known_loans_smoke.py` returns at least 2
    - `grep -c "import yaml" tests/test_orchestration/test_known_loans_smoke.py` returns 1
    - `mypy --strict tests/test_orchestration/test_known_loans_smoke.py` exits 0
    - `ruff check tests/test_orchestration/test_known_loans_smoke.py` exits 0
    - `ruff format --check tests/test_orchestration/test_known_loans_smoke.py` exits 0
  </acceptance_criteria>
  <done>
    test_known_loans_catalog_complete passes; PERS-07 closed at the test layer; suite pass count +1, xfail count -1.
  </done>
</task>

</tasks>

<locked_decisions>
**LOCKED DECISIONS:**

- **D-05-01: data/known-loans.yml lives in the Reference Layer (`data/known-loans.yml`), NOT `data/reference/known-loans.yml` and NOT inside `data/mortgage-ops.duckdb`** — rationale: DATA_CONTRACT.md line 67 explicitly enumerates `data/known-loans.yml` (no `reference/` subdir prefix); the catalog is product metadata, not regulatory data (which lives in `data/reference/*.yml`); and the duckdb file is gitignored Data Layer per DATA_CONTRACT.md line 50, which would prevent the catalog from being a committed artifact other phases can depend on. Rule-of-three citation: DATA_CONTRACT.md line 67 ("`data/known-loans.yml` (Phase 9) product catalog"); 09-RESEARCH.md line 161 ("`known-loans.yml          # NEW: 7 product entries (Reference Layer)`"); REQUIREMENTS.md PERS-07 ("data/known-loans.yml catalog").

- **D-05-02: Per-entry schema is the 9-key set {id, label, type, principal, apr, term_months, frequency, origination_date, citation_url}** [SUPERSEDED by D-05-02 revision 2026-05-04] — rationale: this is the schema in 09-RESEARCH.md §"Sample data/known-loans.yml" (every entry uses exactly these 9 keys); the smoke test in RESEARCH lines 500-502 asserts the same 9-key set; deviating from the sample would invalidate the rule-of-three precedent and break Phase 10 product-routing assumptions. Rule-of-three citation: RESEARCH lines 410-418 (conv-30yr-fixed entry has all 9); RESEARCH lines 500-502 (smoke-test schema assertion); the sample reuses the 9-key shape across all 7 entries. **Reason superseded:** the schema field name was inconsistent with PATTERNS.md line ~366 + lib/models.py:45 `Loan.loan_type` Literal — using `type` here would silently break Phase 10 product routing because the YAML field would not round-trip into the Pydantic model. Replaced by D-05-02 revision 2026-05-04 below.

- **D-05-02 (revision 2026-05-04): Per-entry schema is the 9-key set {id, label, loan_type, principal, apr, term_months, frequency, origination_date, citation_url}** — same intent as the original D-05-02 except the type-discriminator field is named `loan_type` (NOT `type`). Rationale: PATTERNS.md line ~366 explicitly cites lib/models.py:45 `Loan.loan_type: Literal["fixed" | "arm" | "fha" | "va" | "usda" | "jumbo"]`; for the catalog to round-trip into the Loan model in Phase 10's `evaluate` mode and Phase 12's eval-harness, the YAML field name MUST match the model attribute name. Smoke test now asserts (a) `loan_type` key is present on every entry and (b) the value is a member of the Loan Literal option set (`{fixed, arm, fha, va, usda, jumbo}`). Rule-of-three citation: PATTERNS.md line ~366 ("Field schema must round-trip into `lib/models.py:Loan`"); lib/models.py:45 (the Literal definition itself); REQUIREMENTS.md PERS-07 + ROADMAP SC-5 both treat product-type as the routing discriminator without prescribing a field name, so the model attribute name wins.

- **D-05-03: Money values (`principal`) and rate values (`apr`) MUST be quoted strings in YAML** — rationale: CLAUDE.md "Money discipline (non-negotiable)" mandates Decimal constructed from strings, never floats; YAML auto-coerces unquoted `400000.00` to a Python float (lossy at scale); `"400000.00"` is preserved as a string and round-trips losslessly to Decimal. The RESEARCH sample (lines 413, 414, etc.) already quotes them. Rule-of-three citation: CLAUDE.md "Money discipline" line 1 ("Decimal for all dollar amounts and rates. Construct from strings"); RESEARCH §Sample lines 413-414 (`principal: "400000.00"`, `apr: "0.068100"` — both quoted); Phase 2 reference YAMLs already follow this convention (`data/reference/fha-mip-rates.yml` MIP rate values are quoted).

- **D-05-04: APR precision is 6 decimal places (e.g., "0.068100"), not 4 or 2** — rationale: matches the RESEARCH sample verbatim (lines 414, 424, etc.); 6 decimals preserves basis-point precision (0.0001 = 1bp, so 6 decimals = sub-bp precision); Phase 2 `data/reference/fha-mip-rates.yml` annual MIP rates use 4-6 decimals; lender rate sheets typically quote to 3 decimals (e.g., 6.875%) but our internal storage carries extra precision for round-trip safety. Rule-of-three citation: RESEARCH sample 7 entries all use 6-decimal APR strings; FRED MORTGAGE30US is published to 2 decimals (6.81%) but stored at 6 (`"0.068100"` = 6.8100%); D-03-02 (CAST AS VARCHAR) mandates string-preservation discipline.

- **D-05-05: Smoke test asserts SET MEMBERSHIP (`REQUIRED_IDS <= ids`), not equality (`REQUIRED_IDS == ids`)** — rationale: PERS-07 says "AT LEAST" the 7 listed products; future phases may add more (e.g., USDA, 20yr fixed) without breaking the contract; equality would force every catalog edit to also edit the test. Rule-of-three citation: RESEARCH line 499 (`assert REQUIRED_IDS.issubset(ids)`); REQUIREMENTS.md PERS-07 lists 7 categories without an "exactly" qualifier; Phase 5 ARM fixtures use the same "at-least" pattern (Wave 6 supersets are valid).

- **D-05-06: Reference Layer convention keys (`source:`, `effective:`) are at TOP LEVEL of YAML, not nested under each product** — rationale: matches RESEARCH sample (lines 406-407 are top-level); matches Phase 2 reference YAMLs (`data/reference/conforming-limits-2026.yml` has top-level source+effective); the staleness check (Phase 2 REF-08) reads top-level `effective:`. Putting per-entry citation under `citation_url` (different from the catalog-wide `source:`) is the correct two-level model. Rule-of-three citation: RESEARCH lines 406-407 (top-level); DATA_CONTRACT.md line 69 ("Reference Layer files... each must include `source:` (URL) and `effective:` (date)" — singular, top-level); Phase 2 REF-09 test asserts top-level shape.

- **D-05-07: The smoke test does NOT load known-loans.yml via Node — Python `yaml.safe_load` is the test-side reader** — rationale: Pitfall 4 (Cross-Process DuckDB Access Excluded) does NOT apply here because the file is plain YAML, not DuckDB; both Python and Node can read it concurrently with no lock; the smoke test's job is to verify the file shape, not to verify Node can parse it (Node consumption is exercised when downstream phases actually call `js-yaml`). Rule-of-three citation: RESEARCH §Smoke test lines 483-503 uses `yaml.safe_load`; Phase 2 REF-09 test uses `yaml.safe_load`; Wave 0 D-00-04 ("Python `lib/` never opens DuckDB" — but YAML is fine).
</locked_decisions>

<verify_block>
**Verify Block:**

```bash
# 1. Catalog file exists and parses as valid YAML
test -f data/known-loans.yml
python -c "import yaml; d = yaml.safe_load(open('data/known-loans.yml')); print('products:', len(d['products']))"

# 2. All 7 PERS-07 required IDs present
python -c "
import yaml
d = yaml.safe_load(open('data/known-loans.yml'))
ids = {p['id'] for p in d['products']}
required = {'conv-30yr-fixed','conv-15yr-fixed','arm-5-1','arm-7-1','fha-30yr','va-30yr','jumbo-30yr-fixed'}
missing = required - ids
assert not missing, f'missing: {sorted(missing)}'
print('OK all 7 required IDs present:', sorted(required))
"

# 3. Top-level Reference Layer convention keys
grep -c '^source:' data/known-loans.yml
grep -c '^effective:' data/known-loans.yml

# 4. Decimal-string discipline (principals + APRs quoted)
grep -cE '^\s+principal: "[0-9]+\.[0-9]{2}"' data/known-loans.yml  # >= 7
grep -cE '^\s+apr: "0\.[0-9]{6}"' data/known-loans.yml             # >= 7

# 5. NOT gitignored (Reference Layer must be committed)
git check-ignore data/known-loans.yml; test $? -eq 1 && echo "OK not ignored"

# 6. Sanity: Node can also load it (no Phase 9 dep here, but verifies shape compatibility)
node -e "
const yaml = require('js-yaml');
const fs = require('fs');
const d = yaml.load(fs.readFileSync('data/known-loans.yml', 'utf-8'));
console.log('products via js-yaml:', d.products.length);
" 2>&1 || echo "(js-yaml not yet installed — Plan 09-03 will add it; skip this check for now if missing)"

# 7. Wave-5 test passes; xfail flips
pytest tests/test_orchestration/test_known_loans_smoke.py -v --tb=short

# 8. Full suite green; xfail count drops by 1 from Wave 4 baseline (was 5 after Wave 4; should be 4 now)
pytest -q 2>&1 | tail -3

# 9. Lint + type clean
mypy --strict tests/test_orchestration/test_known_loans_smoke.py
ruff check tests/test_orchestration/test_known_loans_smoke.py
ruff format --check tests/test_orchestration/test_known_loans_smoke.py
```
</verify_block>

<deviation_rules>
**Deviation Rules:**

- **Rule-1 (catalog content is verbatim from RESEARCH):** D-05-01 through D-05-04 lock the 7 entries to the exact strings in 09-RESEARCH.md §"Sample data/known-loans.yml" lines 399-479. If the executor finds an entry where the RESEARCH rate is plausibly stale, STOP and surface as a blocker comment — DO NOT silently update; this is a Reference Layer artifact whose `effective:` date is the freshness contract, and the rates are explicitly representative-not-live (RESEARCH line 994 + 845).

- **Rule-2 (per-entry schema is exactly 9 keys):** D-05-02 locks the schema. If the executor sees an opportunity to add a `notes:` or `loan_to_value:` or `pmi_required:` field, STOP. Any schema extension is a CONTEXT-level decision (it changes the contract Phase 10 + Phase 12 will route against). The minimal 9-key shape is sufficient for v1.

- **Rule-3 (smoke test asserts subset, not equality):** D-05-05 locks subset semantics. If the executor writes `assert REQUIRED_IDS == ids`, STOP — this is wrong; future phases may add products. Use `REQUIRED_IDS <= ids` (subset operator) or `REQUIRED_IDS.issubset(ids)`.

- **Rule-4 (lint hygiene OK as Rule-3 deviation):** ruff format may collapse multi-line literals; apply minimal fix and document. mypy may flag `Path(__file__).resolve().parent.parent.parent` as untyped chain — wrap with explicit `: Path` annotation as shown in the action's reference implementation.

- **Rule-5 (do NOT touch DuckDB in this plan):** Plan 09-05 is YAML + Python only. NO Node code, NO `Database.create`, NO subprocess invocation. If the executor finds themselves writing a `node ...` shell-out, STOP and re-read this plan — Phase 10 wiring is a Plan 10-XX concern, not 09-05.
</deviation_rules>

<dependencies>
**Dependencies:**

- **Depends on:** Plan 09-00 (Wave 0 created the `tests/test_orchestration/test_known_loans_smoke.py` xfail stub that this plan flips). No dependency on Waves 1-4 — known-loans.yml is a static Reference Layer file independent of lockfile / init-db / inserts / render.
- **Blocks:** Plan 09-06 (integration tests may exercise the catalog as part of seeding scenarios but does not require the YAML for its own SC-1/2/3/4 tests). Plan 09-07 (references doc may describe the catalog's role but doesn't require its content).
- **Inheritance:** D-05-03 (Decimal-string discipline) inherits from CLAUDE.md money discipline + Plan 09-03 D-03-02 (CAST AS VARCHAR for round-trip safety).
- **Forward dependencies:** Phase 10 SKILL.md `evaluate` mode will route off product `id` strings; Phase 12 EVAL-XX may seed eval prompts from catalog entries. Both consume `data/known-loans.yml` as a black-box YAML file; a schema change here breaks both.
</dependencies>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| YAML file -> downstream consumers (Phase 10/12) | Schema mismatch silently breaks routing; Decimal-string discipline preserved by quote convention |
| Reference Layer -> git | Committed artifact; staleness convention (`effective:` date) is the only freshness signal |
| Catalog content -> human reader | Rates are representative samples, not live offers (header comment + RESEARCH §Assumption A5) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-22 | Tampering (per-entry key drops silently break Phase 10 routing) | known-loans.yml schema | mitigate | Smoke test asserts the full 9-key set per entry (D-05-02); test_known_loans_catalog_complete fails CI if any entry loses a key |
| T-09-23 | Information Disclosure (Decimal precision lost via unquoted YAML float) | principal / apr fields | mitigate | D-05-03 mandates string quoting; smoke test asserts `isinstance(p["principal"], str)` and `isinstance(p["apr"], str)` |
| T-09-24 | Repudiation (rate quoted from no-source) | citation_url field | mitigate | D-05-02 makes citation_url required; every entry in the RESEARCH sample carries one |
| T-09-25 | Tampering (catalog gitignored by accident, never committed) | data/known-loans.yml gitignore status | mitigate | Verify block step 5 asserts `git check-ignore` exits 1 (not ignored); D-05-01 locks Reference Layer placement |
| T-09-26 | Spoofing (catalog presents stale rates as live offers) | rate values + `effective:` date | accept | A5 (RESEARCH line 845): rates are explicitly representative-not-live; header comment + `effective: 2026-04-24` discloses provenance; v1 risk acceptance |
</threat_model>

<verification>
- data/known-loans.yml exists with all 7 PERS-07-required entries
- File is valid YAML; loadable by both Python (yaml.safe_load) and Node (js-yaml)
- All money/rate values are quoted strings (Decimal-string discipline)
- Top-level `source:` + `effective:` Reference Layer convention keys present
- Per-entry 9-key schema satisfied for every product
- File is tracked by git (NOT gitignored — Reference Layer must be committed)
- test_known_loans_catalog_complete passes; PERS-07 closed
- Full suite green; xfail count drops by 1
- mypy + ruff clean
</verification>

<success_criteria>
- PERS-07 closed (data/known-loans.yml committed with 7 entries; smoke test pinned)
- ROADMAP SC-5 satisfied at the test layer (catalog completeness asserted)
- Reference Layer convention upheld (top-level source/effective; entries with citation_url)
- Wave 6 (integration tests) and Wave 7 (references doc) can build on the committed catalog
- Phase 10 + Phase 12 have a stable product-ID set to route against
</success_criteria>

<output>
After completion, create `.planning/phases/09-duckdb-orchestration/09-05-SUMMARY.md` documenting:
- known-loans.yml entry count (7) + product IDs list (sorted)
- Reference Layer placement confirmation (NOT gitignored)
- Decimal-string discipline confirmation (principal + apr both quoted strings)
- Pass count delta (Wave 4 baseline 443 -> Wave 5 baseline 444; one xfail flipped)
- PERS-07 closure status
- Cumulative phase status: PERS-01, PERS-02, PERS-03, PERS-06, PERS-07 closed; PERS-04 + PERS-05 (concurrency end-to-end) remain for Wave 6
- Note: Phase 10 + Phase 12 now have a stable product catalog to route against
</output>

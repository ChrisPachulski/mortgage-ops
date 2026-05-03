# Deferred Items — Phase 06

## Pre-existing baseline issues (logged Plan 06-05; out of scope per SCOPE BOUNDARY)

- **mypy --strict baseline emits "Source file found twice under different module names: '_cli_helpers' and 'scripts._cli_helpers'"** against tests/test_refinance.py. Pre-existed Plan 06-05 (verified by stashing 06-05 changes and re-running mypy on the prior commit). Caused by mypy's package-base ambiguity when scripts/ is imported both as a directory and a module path. Resolution candidates: (a) add scripts/__init__.py, (b) configure --explicit-package-bases in pyproject.toml, (c) configure mypy_path. Defer to a later hygiene pass — does not affect runtime, ruff is clean, all tests pass. The same import path was introduced in Plan 06-04 (scripts/refi_npv.py imports `from scripts._cli_helpers import ...`); per Plan 06-04 SUMMARY this was an established Phase 5 factor-extract reuse pattern.

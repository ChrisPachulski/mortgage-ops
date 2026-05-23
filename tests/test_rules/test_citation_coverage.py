"""RUL-12 + RUL-13: Every lib/rules/ predicate has citation header + ≥1 fixture.

Filesystem-introspecting meta-test. Adding a new predicate file without docstring
header or fixture creates a failing parametrized case automatically. The fix is
to add the missing artifact, never to skip the test.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RULES_DIR: Path = Path(__file__).resolve().parent.parent.parent / "lib" / "rules"
FIX_DIR: Path = Path(__file__).resolve().parent.parent / "fixtures" / "rules"

# Files in lib/rules/ that are NOT regulatory predicates (loader, type aliases,
# package marker). Everything else is a predicate and must satisfy the contract.
NON_PREDICATE_FILES: frozenset[str] = frozenset({"__init__.py", "_loader.py", "types.py"})


def _predicate_modules() -> list[Path]:
    return sorted(p for p in RULES_DIR.glob("*.py") if p.name not in NON_PREDICATE_FILES)


@pytest.mark.parametrize("path", _predicate_modules(), ids=lambda p: p.stem)
def test_predicate_has_citation_in_docstring(path: Path) -> None:
    src = path.read_text()
    # Module docstring is the first triple-quoted block.
    m = re.search(r'^"""(.*?)"""', src, flags=re.DOTALL)
    assert m is not None, f"{path.name} missing module docstring (RUL-12)"
    docstring = m.group(1)
    assert re.search(r"Citation(\s*\([^)]+\))?:", docstring), (
        f"{path.name} docstring missing a 'Citation:' or 'Citation (...):' line (RUL-12)"
    )
    assert re.search(r"Source URL(\s*\([^)]+\))?:", docstring), (
        f"{path.name} docstring missing a 'Source URL:' or 'Source URL (...):' line (RUL-12)"
    )
    assert "Effective:" in docstring, f"{path.name} docstring missing 'Effective:' (RUL-12)"
    assert re.search(r"https?://", docstring), (
        f"{path.name} docstring 'Source URL:' must contain an http(s) URL (RUL-12)"
    )


@pytest.mark.parametrize("path", _predicate_modules(), ids=lambda p: p.stem)
def test_predicate_has_at_least_one_fixture(path: Path) -> None:
    matches = list(FIX_DIR.glob(f"{path.stem}_*.json"))
    assert len(matches) >= 1, (
        f"{path.name} has no matching fixture under "
        f"{FIX_DIR.relative_to(Path.cwd())}/{path.stem}_*.json (RUL-13)"
    )

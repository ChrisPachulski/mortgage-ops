"""Reference-data loader for lib/rules/ predicates.

Single source of truth for YAML loading + staleness checks (REF-08). Every
lib/rules/*.py imports load_reference from here; no module rolls its own loader.

Annual regulatory refresh = edit data/reference/*.yml + bump `effective:` field.
No code change. Predicates auto-pick up the new values on next process start
because lru_cache lives across tests but resets per pytest session.
"""

from __future__ import annotations

import re
import warnings
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import yaml
from dateutil.relativedelta import relativedelta

REFERENCE_DIR: Final[Path] = Path(__file__).parent.parent.parent / "data" / "reference"
STALENESS_THRESHOLD: Final[relativedelta] = relativedelta(months=12)

# WR-06 (02-REVIEW.md): validate `name` argument so a caller passing
# "../../etc/passwd" (or any other path-traversal payload) does not escape
# REFERENCE_DIR. All shipped reference YAMLs use lowercase-and-hyphens-only
# stems (e.g. "fha-mip-rates", "atr-qm-thresholds"); this regex matches the
# established naming convention.
_NAME_RX: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class StaleReferenceWarning(UserWarning):
    """Emitted at module-load time when a reference YAML's effective date is
    more than 12 months in the past. Loud-by-default; never suppressed by
    library code. Tests use `pytest.warns(StaleReferenceWarning)` to assert.
    """


class MissingReferenceFieldError(KeyError):
    """Raised when a reference YAML is missing `source:` or `effective:` (REF-09)."""


@lru_cache(maxsize=None)  # noqa: UP033  # Phase 2 plan locks lru_cache(maxsize=None) idiom; tests grep for it
def load_reference(name: str) -> dict[str, Any]:
    """Load data/reference/{name}.yml, validate top-level fields, warn if stale.

    Args:
        name: stem of the YAML file (e.g. "conforming-limits-2026"). Must
            match `[a-z0-9][a-z0-9-]*` per WR-06 (02-REVIEW.md) — defends
            against path-traversal payloads like "../../etc/passwd".

    Returns:
        Parsed dict. `source` is str; `effective` is datetime.date.

    Raises:
        ValueError: if `name` does not match the allowed naming pattern.
        FileNotFoundError: if the file does not exist.
        MissingReferenceFieldError: if `source:` or `effective:` is missing,
            or `effective` is not a `datetime.date`.
    """
    if not _NAME_RX.match(name):
        raise ValueError(
            f"reference name must match {_NAME_RX.pattern!r} "
            f"(lowercase alnum + hyphens, no leading hyphen, no path "
            f"separators); got {name!r}"
        )
    path = REFERENCE_DIR / f"{name}.yml"
    raw: dict[str, Any] = yaml.safe_load(path.read_text())
    if "source" not in raw:
        raise MissingReferenceFieldError(f"{name}.yml missing required `source:` field")
    if "effective" not in raw:
        raise MissingReferenceFieldError(f"{name}.yml missing required `effective:` field")
    # WR-05 (02-REVIEW.md): validate `effective` is an unquoted YAML date here
    # — the loader is the documented single source of truth. Without this guard
    # an accidentally quoted "2026-01-01" would slip past `if "effective" in raw`
    # and produce a confusing TypeError deep in _check_staleness's `<` comparison
    # rather than a clear schema-violation message.
    if not isinstance(raw["effective"], date):
        raise MissingReferenceFieldError(
            f"{name}.yml `effective:` must be an unquoted YAML date "
            f"(YYYY-MM-DD); got {type(raw['effective']).__name__} "
            f"with value {raw['effective']!r}. Quoted strings are not accepted."
        )
    _check_staleness(name, raw["effective"])
    return raw


def _check_staleness(name: str, effective: date) -> None:
    """Emit StaleReferenceWarning if effective is > 12 months old (REF-08)."""
    threshold_date = date.today() - STALENESS_THRESHOLD
    if effective < threshold_date:
        warnings.warn(
            f"Reference data {name!r} has effective={effective.isoformat()}, "
            f"which is more than 12 months old "
            f"(threshold: {threshold_date.isoformat()}). "
            f"Annual regulatory refresh may be overdue.",
            category=StaleReferenceWarning,
            stacklevel=2,
        )

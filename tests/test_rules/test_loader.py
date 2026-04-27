"""REF-08: StaleReferenceWarning fires when effective > 12 months old.
REF-09 (loader-side): MissingReferenceFieldError raised on missing source/effective.

Every assertion includes the hand-calculated expected behavior and why.

Coverage:
  - test_staleness_warning_fires_for_old_yaml: 730-day-old YAML → warns
  - test_no_warning_for_fresh_yaml: 30-day-old YAML → no warn
  - test_missing_source_raises: REF-09 enforcement at load time
  - test_missing_effective_raises: REF-09 enforcement at load time
  - test_load_reference_returns_dict: smoke-check happy path
"""

from __future__ import annotations

import warnings
from collections.abc import Iterator  # noqa: TC003  # used as fixture return annotation at runtime
from datetime import date, timedelta
from pathlib import Path  # noqa: TC003  # used as pytest fixture annotation at runtime

import pytest
from lib.rules._loader import (
    MissingReferenceFieldError,
    StaleReferenceWarning,
    load_reference,
)


@pytest.fixture(autouse=True)
def _clear_loader_cache() -> Iterator[None]:
    # WR-07 (02-REVIEW.md): clear the lru_cache BOTH before AND after each
    # test, so synthetic-tmp-path entries from one test never bleed into
    # another. Pre-fix tests cleared explicitly before but not after; this
    # auto-use fixture eliminates the contamination risk and removes the
    # explicit cache_clear() calls scattered through individual tests.
    load_reference.cache_clear()
    yield
    load_reference.cache_clear()


def test_staleness_warning_fires_for_old_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Hand: 730 days = 24 months; well past the 12-month threshold.
    old = (date.today() - timedelta(days=730)).isoformat()
    fake = tmp_path / "synthetic-old.yml"
    fake.write_text(f"source: 'https://example.test/'\neffective: {old}\nbody: stub\n")
    monkeypatch.setattr("lib.rules._loader.REFERENCE_DIR", tmp_path)
    load_reference.cache_clear()
    with pytest.warns(StaleReferenceWarning, match="more than 12 months old"):
        load_reference("synthetic-old")


def test_no_warning_for_fresh_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Hand: 30 days old; well within the 12-month threshold.
    fresh = (date.today() - timedelta(days=30)).isoformat()
    fake = tmp_path / "synthetic-fresh.yml"
    fake.write_text(f"source: 'https://example.test/'\neffective: {fresh}\nbody: stub\n")
    monkeypatch.setattr("lib.rules._loader.REFERENCE_DIR", tmp_path)
    load_reference.cache_clear()
    with warnings.catch_warnings():
        warnings.simplefilter("error", StaleReferenceWarning)
        # Will raise if any StaleReferenceWarning fires.
        load_reference("synthetic-fresh")


def test_missing_source_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "no-source.yml"
    fake.write_text("effective: 2026-01-01\nbody: stub\n")
    monkeypatch.setattr("lib.rules._loader.REFERENCE_DIR", tmp_path)
    load_reference.cache_clear()
    with pytest.raises(MissingReferenceFieldError, match="missing required `source:` field"):
        load_reference("no-source")


def test_missing_effective_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "no-effective.yml"
    fake.write_text("source: 'https://example.test/'\nbody: stub\n")
    monkeypatch.setattr("lib.rules._loader.REFERENCE_DIR", tmp_path)
    load_reference.cache_clear()
    with pytest.raises(MissingReferenceFieldError, match="missing required `effective:` field"):
        load_reference("no-effective")


def test_load_reference_returns_dict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fresh = (date.today() - timedelta(days=30)).isoformat()
    fake = tmp_path / "smoke.yml"
    fake.write_text(f"source: 'https://example.test/'\neffective: {fresh}\nbody:\n  k: v\n")
    monkeypatch.setattr("lib.rules._loader.REFERENCE_DIR", tmp_path)
    load_reference.cache_clear()
    result = load_reference("smoke")
    assert isinstance(result, dict)
    assert result["body"] == {"k": "v"}


@pytest.mark.parametrize(
    "bad_name",
    [
        "../../etc/passwd",  # path traversal
        "../escape",  # path traversal (relative)
        "/absolute/path",  # absolute path
        "with spaces",  # space
        "UPPERCASE",  # uppercase
        "trailing/slash",  # path separator
        "-leading-hyphen",  # leading hyphen (RX requires alnum start)
        "",  # empty
        "name.yml",  # dot
        "name_with_underscore",  # underscore (not in RX)
    ],
)
def test_load_reference_rejects_invalid_names(bad_name: str) -> None:
    # Regression for WR-06 (02-REVIEW.md): loader rejects any name that does
    # not match the allowed naming pattern, defending against path-traversal
    # payloads even though no internal caller currently passes one. The
    # loader is the documented single source of truth and a defensive check
    # costs almost nothing.
    with pytest.raises(ValueError, match="reference name must match"):
        load_reference(bad_name)


def test_quoted_effective_string_raises_missing_reference_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Regression for WR-05 (02-REVIEW.md): if a YAML accidentally quotes the
    # effective date (effective: "2026-01-01") PyYAML returns it as a str, not
    # a date. Pre-fix the loader passed it through to _check_staleness which
    # raised a confusing TypeError on the < comparison. Post-fix, the loader
    # itself raises MissingReferenceFieldError with a clear schema message.
    fake = tmp_path / "quoted-effective.yml"
    fake.write_text("source: 'https://example.test/'\neffective: '2026-01-01'\nbody: stub\n")
    monkeypatch.setattr("lib.rules._loader.REFERENCE_DIR", tmp_path)
    load_reference.cache_clear()
    with pytest.raises(
        MissingReferenceFieldError,
        match="effective:` must be an unquoted YAML date",
    ):
        load_reference("quoted-effective")

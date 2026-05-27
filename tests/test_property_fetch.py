"""Tests for .claude/skills/mortgage-ops/scripts/property_fetch.py — INGEST-01 + INGEST-03 + INGEST-04.

Phase 13 Plan 13-04 (Wave 4). Subprocess-driven envelope tests across all 3 shapes
(D-13-GAPFILL-01) + the always-exit-0 contract (Phase 12 CR-02 + D-12-LIVE02-01).

Test-flow split:
  - Wave 4 (this module): CLI tests use INLINE-generated synthetic HTML
    written to ``tmp_path`` so no fixture files need to exist yet.
  - Wave 6 (Plan 13-06): integration tests use the real pinned Zillow fixtures
    + sha-keyed extracted/ JSON for the live shape-1 happy path.

Each test strips ``ANTHROPIC_API_KEY`` from the subprocess env so accidental
live Sonnet calls can never escape CI (defense-in-depth — the CLI also returns
None on missing key, but stripping is cheap insurance).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "mortgage-ops"
    / "scripts"
    / "property_fetch.py"
)
"""Phase 12 idiom: subprocess-test absolute path to the CLI under test."""

VALID_ZILLOW_URL = "https://www.zillow.com/homedetails/x/12345_zpid/"
"""Canonical ZPID test URL. extract_zpid returns "12345"."""

MIN_HAPPY_BODY = 6000
"""Comfortably above MIN_BODY_BYTES=5000 in lib.property_block_detector."""


def _write_html_with_sonnet_fixture(
    tmp_path: Path,
    sonnet_dict: dict[str, object] | None,
    body_padding: int = MIN_HAPPY_BODY,
) -> Path:
    """Write a synthetic HTML fixture to tmp_path/page.html.

    When ``sonnet_dict`` is non-None, ALSO writes its companion sha-keyed JSON
    to ``tests/fixtures/zillow/extracted/{sha16}.json`` (the same key the
    ``mock_sonnet`` conftest fixture + the CLI's ``MORTGAGE_OPS_MOCK_SONNET=1``
    hook use). Returns the HTML path.

    The HTML body always contains a valid ``__NEXT_DATA__`` shell so block
    detection passes (otherwise the block-detect step short-circuits before
    we reach the Sonnet code path under test).
    """
    html = (
        "<html>"
        + "x" * body_padding
        + '<script id="__NEXT_DATA__">{"props":{}}</script>'
        + "</html>"
    )
    html_path = tmp_path / "page.html"
    html_path.write_text(html, encoding="utf-8")
    if sonnet_dict is not None:
        digest = hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]
        extracted_dir = Path(__file__).parent / "fixtures" / "zillow" / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        (extracted_dir / f"{digest}.json").write_text(json.dumps(sonnet_dict), encoding="utf-8")
    return html_path


def _run_cli(
    *args: str,
    env: dict[str, str] | None = None,
    timeout: float = 15,
) -> subprocess.CompletedProcess[str]:
    """Run property_fetch.py with given args; return CompletedProcess.

    Strips ANTHROPIC_API_KEY so subprocess tests cannot accidentally make live
    Sonnet calls in CI. Caller passes ``env={"MORTGAGE_OPS_MOCK_SONNET": "1"}``
    to enable the sha-keyed fixture path.
    """
    cmd = [sys.executable, str(SCRIPT_PATH), *args]
    merged_env = dict(os.environ)
    merged_env.pop("ANTHROPIC_API_KEY", None)
    tmp_root = Path(tempfile.mkdtemp(prefix="mortgage-ops-property-fetch-"))
    merged_env.setdefault("MORTGAGE_OPS_PROPERTY_CACHE_DIR", str(tmp_root / "cache"))
    merged_env.setdefault("MORTGAGE_OPS_DB_PATH", str(tmp_root / "mortgage-ops.duckdb"))
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=merged_env,
        check=False,
    )


def test_property_fetch_help_fast_lazy_imports() -> None:
    """D-18: --help <300ms; no anthropic/duckdb on the help path."""
    start = time.perf_counter()
    result = _run_cli("--help")
    elapsed = time.perf_counter() - start
    assert result.returncode == 0
    assert elapsed < 0.3, f"--help took {elapsed:.3f}s; D-18 violated"
    lowered = result.stdout.lower()
    assert "shape" in lowered or "envelope" in lowered or "awaiting" in lowered


def test_argparse_error_exit_2() -> None:
    """Phase 12 WR-02 + D-12-LIVE02-01: argparse parse error is the one
    documented exit-2 exception to always-exit-0."""
    result = _run_cli()  # no positional URL -> argparse error
    assert result.returncode == 2


def test_blocked_captcha_envelope_exit_0(tmp_path: Path) -> None:
    """D-13-BLOCK-01: captcha-phrase body -> shape-3 captcha_detected, exit 0."""
    html = "press & hold to continue " + ("x" * MIN_HAPPY_BODY)
    p = tmp_path / "blocked.html"
    p.write_text(html, encoding="utf-8")
    result = _run_cli(VALID_ZILLOW_URL, "--html-from", str(p))
    assert result.returncode == 0
    env = json.loads(result.stdout)
    assert env["listing"] is None
    assert env["error"] == "captcha_detected"
    assert env["awaiting_user_input"] is False
    assert env["source_url"] == VALID_ZILLOW_URL


def test_body_too_short_envelope(tmp_path: Path) -> None:
    """D-13-BLOCK-01 signal 4: <5KB body -> shape-3 body_too_short."""
    p = tmp_path / "short.html"
    p.write_text("x" * 100, encoding="utf-8")
    result = _run_cli(VALID_ZILLOW_URL, "--html-from", str(p))
    assert result.returncode == 0
    env = json.loads(result.stdout)
    assert env["error"] == "body_too_short"
    assert env["listing"] is None
    assert env["awaiting_user_input"] is False


def test_missing_next_data_envelope(tmp_path: Path) -> None:
    """D-13-BLOCK-01 signal 5: large body without __NEXT_DATA__ -> shape-3."""
    p = tmp_path / "no_data.html"
    p.write_text("<html>" + "x" * MIN_HAPPY_BODY + "</html>", encoding="utf-8")
    result = _run_cli(VALID_ZILLOW_URL, "--html-from", str(p))
    assert result.returncode == 0
    env = json.loads(result.stdout)
    assert env["error"] == "missing_next_data"


def test_zpid_extraction_failed_envelope(tmp_path: Path) -> None:
    """INGEST-04 CLI-level: non-Zillow URL -> shape-3 zpid_extraction_failed."""
    # Block-detect must pass first; supply happy-body HTML
    p = _write_html_with_sonnet_fixture(tmp_path, sonnet_dict=None)
    result = _run_cli("https://redfin.com/property/12345", "--html-from", str(p))
    assert result.returncode == 0
    env = json.loads(result.stdout)
    assert env["error"] == "zpid_extraction_failed"
    assert env["listing"] is None


def test_no_api_key_falls_through_to_shape_2(tmp_path: Path) -> None:
    """INGEST-02 + D-13-GAPFILL-01: without ANTHROPIC_API_KEY, the extractor
    returns None and the CLI emits shape-2 awaiting_user_input with all 3
    MUST_HAVE fields listed as missing.

    (Live-Sonnet shape-1 round-trip is covered in Plan 13-06 integration
    tests with real fixtures + the MORTGAGE_OPS_MOCK_SONNET hook.)
    """
    html_path = _write_html_with_sonnet_fixture(tmp_path, sonnet_dict=None)
    result = _run_cli(VALID_ZILLOW_URL, "--html-from", str(html_path))
    assert result.returncode == 0
    env = json.loads(result.stdout)
    assert env["awaiting_user_input"] is True
    assert env["error"] is None
    assert sorted(env["missing"]) == sorted(["price", "zip", "property_type"])


def test_user_provided_strips_dollar_comma(tmp_path: Path) -> None:
    """§Pitfall 16: user types '$625,000' — CLI normalizes to '625000.00'."""
    html_path = _write_html_with_sonnet_fixture(tmp_path, sonnet_dict=None)
    result = _run_cli(
        VALID_ZILLOW_URL,
        "--html-from",
        str(html_path),
        "--user-provided",
        '{"price":"$625,000","zip":"94110","property_type":"SFH"}',
    )
    assert result.returncode == 0
    env = json.loads(result.stdout)
    # Sonnet returned None (no key); merge overlays user-provided; Pydantic
    # validates -> shape-1.
    assert env["awaiting_user_input"] is False
    assert env["error"] is None
    assert env["listing"]["price"] == "625000.00"
    assert env["listing"]["zip"] == "94110"
    assert env["listing"]["property_type"] == "SFH"


def test_user_provided_tags_provenance_on_tax_annual(tmp_path: Path) -> None:
    """INGEST-03: user-provided tax_annual gets ProvenancedMoney wrapper
    with provenance='user_provided'."""
    html_path = _write_html_with_sonnet_fixture(tmp_path, sonnet_dict=None)
    payload = '{"price":"625000","zip":"94110","property_type":"SFH","tax_annual":"8200"}'
    result = _run_cli(
        VALID_ZILLOW_URL,
        "--html-from",
        str(html_path),
        "--user-provided",
        payload,
    )
    assert result.returncode == 0
    env = json.loads(result.stdout)
    assert env["listing"]["tax_annual"] == {
        "value": "8200.00",
        "provenance": "user_provided",
    }


def test_user_provided_tags_sibling_provenance_on_beds(tmp_path: Path) -> None:
    """INGEST-03: non-money user-provided field gets sibling *_provenance field."""
    html_path = _write_html_with_sonnet_fixture(tmp_path, sonnet_dict=None)
    payload = '{"price":"625000","zip":"94110","property_type":"SFH","beds":3}'
    result = _run_cli(
        VALID_ZILLOW_URL,
        "--html-from",
        str(html_path),
        "--user-provided",
        payload,
    )
    assert result.returncode == 0
    env = json.loads(result.stdout)
    assert env["listing"]["beds"] == 3
    assert env["listing"]["beds_provenance"] == "user_provided"


def test_envelope_always_has_fetched_at_z_suffix(tmp_path: Path) -> None:
    """Pitfall 21 inherited: fetched_at uses Z suffix not +00:00."""
    html_path = _write_html_with_sonnet_fixture(tmp_path, sonnet_dict=None)
    result = _run_cli(VALID_ZILLOW_URL, "--html-from", str(html_path))
    env = json.loads(result.stdout)
    assert env["fetched_at"].endswith("Z")
    assert "+00:00" not in env["fetched_at"]


def test_outer_try_catches_unexpected_failure(tmp_path: Path) -> None:
    """Phase 12 CR-02 outer-try contract: malformed --user-provided JSON crashes
    json.loads inside merge; outer try catches -> shape-3, exit 0."""
    html_path = _write_html_with_sonnet_fixture(tmp_path, sonnet_dict=None)
    result = _run_cli(
        VALID_ZILLOW_URL,
        "--html-from",
        str(html_path),
        "--user-provided",
        "not valid json {{{",
    )
    assert result.returncode == 0
    env = json.loads(result.stdout)
    assert env["listing"] is None
    assert env["error"].startswith("unexpected_failure")


def test_cli_writes_html_cache_on_round_1(tmp_path: Path) -> None:
    """Q1 default: successful shape-1 emission writes
    property-{zpid}.json so a later --user-provided round-trip
    can skip Sonnet entirely."""
    cache_dir = tmp_path / "cache"
    db_path = tmp_path / "mortgage-ops.duckdb"
    cache_file = cache_dir / "property-12345.json"

    html_path = _write_html_with_sonnet_fixture(tmp_path, sonnet_dict=None)
    payload = '{"price":"625000","zip":"94110","property_type":"SFH"}'
    result = _run_cli(
        VALID_ZILLOW_URL,
        "--html-from",
        str(html_path),
        "--user-provided",
        payload,
        env={
            "MORTGAGE_OPS_PROPERTY_CACHE_DIR": str(cache_dir),
            "MORTGAGE_OPS_DB_PATH": str(db_path),
        },
    )
    assert result.returncode == 0
    env = json.loads(result.stdout)
    # Sanity: only assert cache write on a true shape-1 outcome.
    assert env["awaiting_user_input"] is False
    assert cache_file.exists(), f"expected Q1 cache file at {cache_file}"
    assert db_path.exists(), f"expected property persistence DB at {db_path}"

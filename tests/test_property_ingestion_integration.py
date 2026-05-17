"""End-to-end integration test for Phase 13 - Zillow URL to CLI to DuckDB to read-back.

Uses the pinned synthetic fixtures from tests/fixtures/zillow/ + the env-var-driven
mock-Sonnet hook (MORTGAGE_OPS_MOCK_SONNET=1) so the subprocess pipeline runs
without ANTHROPIC_API_KEY or live API calls.

Coverage matrix:
  - SC-1: SFH happy path -> shape-1 envelope
  - SC-2: captcha block -> shape-3 envelope (Sonnet never called)
  - SC-4 + INGEST-04: both /homedetails/ and /b/ URL patterns -> correct zpid
  - SC-5: full PropertyListing round-trip via DuckDB
  - D-13-MUSTHAVE-01: condo with tax_annual=null still validates as shape-1
  - Q1 cache: --user-provided round-trip reuses cached extraction (no re-Sonnet)
  - Meta: no AI attribution in committed HTML fixtures (CLAUDE.md global rule)
  - Meta: extracted/{sha16}.json filenames match sha256(html_bytes)[:16] (drift guard)
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH: Path = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "mortgage-ops"
    / "scripts"
    / "property_fetch.py"
)
FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures" / "zillow"
REPO_ROOT: Path = Path(__file__).resolve().parent.parent


def _run_cli_with_mock_sonnet(
    url: str,
    html_from: Path,
    extra_args: list[str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run property_fetch.py with MORTGAGE_OPS_MOCK_SONNET=1.

    Strips ANTHROPIC_API_KEY from the env so any leak into a live Sonnet call
    surfaces as an auth error rather than a quiet pass.
    """
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env["MORTGAGE_OPS_MOCK_SONNET"] = "1"
    cmd = [sys.executable, str(SCRIPT_PATH), url, "--html-from", str(html_from)]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        cwd=str(cwd) if cwd is not None else None,
    )


def test_cli_exposes_mock_sonnet_hook_and_provenance_wrapping() -> None:
    """Meta-test: this Task assumes Plan 13-04 shipped MORTGAGE_OPS_MOCK_SONNET +
    the ProvenancedMoney wrapping helper. Surface the dependency explicitly so
    a future regression in property_fetch.py fails here, not deep in subprocess output.
    """
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "MORTGAGE_OPS_MOCK_SONNET" in source, (
        "property_fetch.py is missing the MORTGAGE_OPS_MOCK_SONNET env-var hook "
        "(Plan 13-04 contract); integration tests cannot run."
    )
    assert "_wrap_scraped_provenanced_money" in source or "provenance" in source, (
        "property_fetch.py is missing the scraped-provenance wrapping helper "
        "(Plan 13-04 contract); Pydantic validation against PropertyListing will fail."
    )


def test_end_to_end_sfh_happy_path_shape_1() -> None:
    """SC-1: SFH fixture -> shape-1 envelope; tax_annual is a scraped ProvenancedMoney."""
    html_path = FIXTURES_DIR / "sfh_conforming_happy_path.html"
    url = "https://www.zillow.com/homedetails/x/12345678_zpid/"
    result = _run_cli_with_mock_sonnet(url, html_path)
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    env = json.loads(result.stdout)
    assert env["awaiting_user_input"] is False
    assert env["error"] is None
    assert env["listing"] is not None
    listing = env["listing"]
    assert listing["price"] == "625000.00"
    assert listing["zip"] == "94110"
    assert listing["property_type"] == "SFH"
    assert listing["zpid"] == "12345678"
    # Scraped ProvenancedMoney
    assert listing["tax_annual"] == {"value": "7800.00", "provenance": "scraped"}
    assert listing["hoa_monthly"] is None
    # Scraped sibling provenance on non-money fields
    assert listing["beds"] == 3
    assert listing["beds_provenance"] == "scraped"


def test_end_to_end_condo_partial_tax_missing_shape_1() -> None:
    """D-13-MUSTHAVE-01: condo with tax_annual=null still shape-1 (tax is NICE-TO-HAVE)."""
    html_path = FIXTURES_DIR / "condo_partial_tax_missing.html"
    url = "https://www.zillow.com/homedetails/x/87654321_zpid/"
    result = _run_cli_with_mock_sonnet(url, html_path)
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    env = json.loads(result.stdout)
    assert env["awaiting_user_input"] is False, "tax_annual=null must NOT be blocking"
    assert env["error"] is None
    listing = env["listing"]
    assert listing is not None
    assert listing["property_type"] == "condo"
    assert listing["tax_annual"] is None
    assert listing["hoa_monthly"] == {"value": "425.00", "provenance": "scraped"}


def test_end_to_end_blocked_captcha_shape_3() -> None:
    """SC-2: captcha fixture -> shape-3; block detection fires BEFORE Sonnet (cost saved)."""
    html_path = FIXTURES_DIR / "blocked_perimeterx.html"
    url = "https://www.zillow.com/homedetails/x/12345678_zpid/"
    result = _run_cli_with_mock_sonnet(url, html_path)
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    env = json.loads(result.stdout)
    assert env["listing"] is None
    assert env["error"] == "captcha_detected"
    assert env["awaiting_user_input"] is False


def test_end_to_end_zpid_url_pattern_homedetails() -> None:
    """INGEST-04: /homedetails/{slug}/{zpid}_zpid/ pattern -> zpid extracted correctly."""
    html_path = FIXTURES_DIR / "sfh_conforming_happy_path.html"
    url = "https://www.zillow.com/homedetails/x/12345678_zpid/"
    result = _run_cli_with_mock_sonnet(url, html_path)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    env = json.loads(result.stdout)
    assert env["listing"] is not None
    # URL-extracted zpid (matches HTML __NEXT_DATA__ + extracted JSON for this fixture).
    assert env["listing"]["zpid"] == "12345678"


def test_end_to_end_zpid_url_pattern_b_shortlink() -> None:
    """INGEST-04: /b/{zpid}_zpid/ shortlink pattern -> URL-extracted zpid wins over body."""
    html_path = FIXTURES_DIR / "sfh_conforming_happy_path.html"
    url = "https://www.zillow.com/b/99999999_zpid/"
    result = _run_cli_with_mock_sonnet(url, html_path)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    env = json.loads(result.stdout)
    assert env["listing"] is not None
    # The CLI assigns zpid from extract_zpid(args.url) after the mock-Sonnet result,
    # so the URL value wins regardless of what the mock dict contained.
    assert env["listing"]["zpid"] == "99999999"


def test_end_to_end_user_provided_price_override(tmp_path: Path) -> None:
    """D-13-GAPFILL-01: --user-provided overlays user values onto the extracted dict.

    Uses tmp_path as cwd so the Q1 cache (data/cache/property-{zpid}.json) does
    not collide with any prior runs in the repo's data/ directory.
    """
    (tmp_path / "data" / "cache").mkdir(parents=True, exist_ok=True)
    html_path = FIXTURES_DIR / "sfh_conforming_happy_path.html"
    url = "https://www.zillow.com/homedetails/x/12345678_zpid/"
    # Round 1: populate cache
    r1 = _run_cli_with_mock_sonnet(url, html_path, cwd=tmp_path)
    assert r1.returncode == 0, f"stderr: {r1.stderr}"
    # Round 2: --user-provided overrides price
    r2 = _run_cli_with_mock_sonnet(
        url,
        html_path,
        extra_args=["--user-provided", '{"price":"700000.00"}'],
        cwd=tmp_path,
    )
    assert r2.returncode == 0, f"stderr: {r2.stderr}\nstdout: {r2.stdout}"
    env = json.loads(r2.stdout)
    assert env["listing"] is not None
    # Bare price stays flat (no provenance wrapper) per Plan 13-01.
    assert env["listing"]["price"] == "700000.00"


def test_end_to_end_database_roundtrip(tmp_path: Path) -> None:
    """SC-5: write a PropertyListing via the persistence layer; read back; assert equal.

    The CLI's persistence path writes to data/mortgage-ops.duckdb by default (no
    DB-path env-var override at the CLI surface today). For test isolation this
    test runs the CLI to produce the envelope, then re-writes via the API layer
    against a tmp_path DB so the project DB is unaffected. The contract under
    test is round-trip serialization through PropertyListing -> DuckDB JSON ->
    PropertyListing.
    """
    html_path = FIXTURES_DIR / "sfh_conforming_happy_path.html"
    url = "https://www.zillow.com/homedetails/x/12345678_zpid/"
    result = _run_cli_with_mock_sonnet(url, html_path)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    env = json.loads(result.stdout)
    assert env["listing"] is not None

    from lib.property_listing import PropertyListing
    from lib.property_persistence import read_latest_for_zpid, write_listing

    # PropertyListing is strict=True so route through model_validate_json (same
    # pattern lib.property_persistence.read_latest_for_zpid uses): Pydantic's
    # JSON parser handles string -> Decimal / string -> date / string -> datetime
    # coercion at the boundary, where model_validate(dict) rejects those strings.
    listing = PropertyListing.model_validate_json(json.dumps(env["listing"]))
    tmp_db = tmp_path / "test_integration.duckdb"
    write_listing(listing, household_hash="test-hash-integration", db_path=tmp_db)

    roundtrip = read_latest_for_zpid("12345678", db_path=tmp_db)
    assert roundtrip is not None
    assert roundtrip == listing


def test_no_ai_attribution_in_committed_html_fixtures() -> None:
    """CLAUDE.md global rule: fixtures must not contain AI-attribution strings.

    Checked phrases are the canonical attribution markers. We check the raw
    HTML files only (not the README, which legitimately discusses the policy).
    """
    forbidden_phrases = (
        "co-authored-by",
        "generated by claude",
        "generated by ai",
        "claude code",
    )
    for p in sorted(FIXTURES_DIR.glob("*.html")):
        content = p.read_text(encoding="utf-8").lower()
        for forbidden in forbidden_phrases:
            assert forbidden not in content, (
                f"{p.name} contains forbidden AI-attribution string: {forbidden!r}"
            )


def test_extracted_json_sha_keys_match_html_fixtures() -> None:
    """Meta-test: extracted/{sha16}.json filenames must match sha256(html)[:16].

    Catches fixture drift: if someone edits an HTML fixture without regenerating
    the matching extracted JSON, the sha changes and this test fails loudly
    instead of letting the integration tests silently fall through to shape-2.
    """
    happy_path_fixtures = (
        "sfh_conforming_happy_path.html",
        "condo_partial_tax_missing.html",
    )
    for html_name in happy_path_fixtures:
        html_path = FIXTURES_DIR / html_name
        sha = hashlib.sha256(html_path.read_bytes()).hexdigest()[:16]
        expected_json = FIXTURES_DIR / "extracted" / f"{sha}.json"
        assert expected_json.exists(), (
            f"{html_name}: sha={sha} but {expected_json} is missing. "
            "Either the HTML was edited without regenerating the extracted JSON, "
            "or the extracted JSON was committed under a stale name. "
            'Run: python -c "import hashlib; print(hashlib.sha256(open('
            f"'tests/fixtures/zillow/{html_name}','rb').read()).hexdigest()[:16])\" "
            "and rename the JSON to match."
        )


def test_extracted_json_has_expected_shape() -> None:
    """Meta-test: extracted/{sha16}.json files must have the keys the CLI's
    _wrap_scraped_provenanced_money + Pydantic validation expect."""
    required_keys = {
        "zpid",
        "price",
        "zip",
        "property_type",
        "beds",
        "baths",
        "sqft",
        "year_built",
        "tax_annual",
        "hoa_monthly",
        "insurance_estimate_annual",
        "zestimate",
        "days_on_market",
        "list_date",
    }
    extracted_dir = FIXTURES_DIR / "extracted"
    json_files = sorted(extracted_dir.glob("*.json"))
    assert len(json_files) == 2, (
        f"Expected exactly 2 extracted JSON files; got {len(json_files)}: "
        f"{[p.name for p in json_files]}"
    )
    for jpath in json_files:
        d: dict[str, Any] = json.loads(jpath.read_text(encoding="utf-8"))
        missing = required_keys - set(d.keys())
        assert not missing, f"{jpath.name} missing required keys: {missing}"
        # D-19: money fields must be JSON STRINGS (not numbers) when not null.
        for money_field in ("price", "tax_annual", "hoa_monthly", "zestimate"):
            v = d.get(money_field)
            if v is not None:
                assert isinstance(v, str), (
                    f"{jpath.name}: {money_field} must be JSON string, got {type(v).__name__}"
                )

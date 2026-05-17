#!/usr/bin/env python3
"""scripts/property_fetch.py — Zillow URL → PropertyListing envelope.

Phase 13 INGEST-01..04 + D-13-GAPFILL-01 + D-13-BLOCK-01 + D-13-MODEL-01.

Envelope contract (single-line JSON on stdout, ALWAYS exit 0):

  shape-1 success:    {listing: {...}, missing: [], error: null,
                       awaiting_user_input: false, source_url, fetched_at}
  shape-2 awaiting:   {listing: {...partial...}, missing: ["price","zip"],
                       error: null, awaiting_user_input: true, source_url, fetched_at}
  shape-3 blocked:    {listing: null, missing: [],
                       error: "http_403"|"captcha_detected"|"missing_next_data"|
                              "body_too_short"|"zpid_extraction_failed"|
                              "unexpected_failure: ...",
                       awaiting_user_input: false, source_url, fetched_at}

Usage:
  property_fetch.py <url>                                  # initial; HTML from stdin
  property_fetch.py <url> --html-from /tmp/page.html       # fixture path
  property_fetch.py <url> --user-provided '{"price":"625000","zip":"94110","property_type":"SFH"}'

Always exits 0; argparse parse errors are the one documented exit-2 exception
(Phase 12 WR-02 + D-12-LIVE02-01).

Q1 default: on Round 1 success, the extracted dict is written to
``data/cache/property-{zpid}.json``. On Round 2 (``--user-provided`` passed
with the same URL), the CLI reads that JSON instead of re-invoking Sonnet —
saves $0.16/round-trip per the cost analysis in 13-CONTEXT.

Block detection (``lib.property_block_detector.detect_block``) runs BEFORE
the Sonnet extraction call so captcha/short-body/missing-__NEXT_DATA__ pages
never burn $0.16 in API spend (D-13-BLOCK-01).

Test-only hook: ``MORTGAGE_OPS_MOCK_SONNET=1`` env var redirects the Sonnet
call to a sha-keyed fixture under ``tests/fixtures/zillow/extracted/{sha16}.json``
(sha16 = first 16 hex chars of SHA256(body)). Used by Plan 13-06 integration
tests to bypass live Sonnet without ``ANTHROPIC_API_KEY``. Production usage
MUST leave this env var unset.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Module-level constants per D-13-MUSTHAVE-01 + INGEST-03.
MUST_HAVE: tuple[str, ...] = ("price", "zip", "property_type")
MONEY_FIELDS: frozenset[str] = frozenset(
    {"price", "tax_annual", "hoa_monthly", "insurance_estimate_annual", "zestimate"}
)
PROVENANCED_MONEY_FIELDS: frozenset[str] = frozenset(
    {"tax_annual", "hoa_monthly", "insurance_estimate_annual", "zestimate"}
)
NON_MONEY_NUMBER_FIELDS: frozenset[str] = frozenset(
    {"beds", "sqft", "year_built", "days_on_market"}
)
NON_MONEY_DECIMAL_FIELDS: frozenset[str] = frozenset({"baths"})
PLAIN_OVERLAY_FIELDS: frozenset[str] = frozenset({"zip", "property_type", "list_date"})


def _now_iso_z() -> str:
    """ISO-8601 UTC with Z suffix (matches lib/property_listing._serialize_dt)."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _strip_money(raw: str) -> str:
    """§Pitfall 16: users type '$625,000' not '625000.00'. Strip $ and , and pad to .00."""
    cleaned = raw.replace("$", "").replace(",", "").strip()
    if "." not in cleaned:
        cleaned += ".00"
    return cleaned


def _coerce_money_to_string(extracted: dict[str, Any]) -> dict[str, Any]:
    """§Pitfall 15: Sonnet occasionally emits floats despite 'JSON STRINGS' instruction.
    Pydantic strict=True rejects JSON numbers for Decimal. Coerce at the boundary.
    Handles both flat-money and ProvenancedMoney-shaped values.
    """
    for k, v in list(extracted.items()):
        if k in MONEY_FIELDS and isinstance(v, (int, float)) and not isinstance(v, bool):
            extracted[k] = f"{v:.2f}"
        elif k in MONEY_FIELDS and isinstance(v, dict) and "value" in v:
            inner = v["value"]
            if isinstance(inner, (int, float)) and not isinstance(inner, bool):
                v["value"] = f"{inner:.2f}"
    return extracted


def _wrap_scraped_provenanced_money(extracted: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat Sonnet output into PropertyListing's ProvenancedMoney + *_provenance shape.

    Sonnet emits e.g. ``{"tax_annual": "7800.00"}``; PropertyListing requires
    ``{"tax_annual": {"value": "7800.00", "provenance": "scraped"}}``. Same idea
    for non-money: ``{"beds": 4}`` -> ``{"beds": 4, "beds_provenance": "scraped"}``.

    Money fields (PROVENANCED_MONEY_FIELDS) -> wrapped dict; non-money fields
    (NON_MONEY_NUMBER_FIELDS U NON_MONEY_DECIMAL_FIELDS) -> sibling
    ``*_provenance="scraped"``. ``price`` stays bare Money (no provenance wrapper
    per Plan 13-01). list_date, zip, property_type -> plain values, no provenance.
    """
    out = dict(extracted)
    for fld in PROVENANCED_MONEY_FIELDS:
        val = out.get(fld)
        if val is not None and not isinstance(val, dict):
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                val = f"{val:.2f}"
            out[fld] = {"value": val, "provenance": "scraped"}
    for fld in NON_MONEY_NUMBER_FIELDS | NON_MONEY_DECIMAL_FIELDS:
        if out.get(fld) is not None and f"{fld}_provenance" not in out:
            out[f"{fld}_provenance"] = "scraped"
    return out


def _merge_user_provided(extracted: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    """Overlay user values onto extracted dict; tag provenance per INGEST-03 + D-13-GAPFILL-01.

    - ``price`` -> bare Money string (no provenance wrapper per Plan 13-01).
    - PROVENANCED_MONEY_FIELDS -> {"value": stripped, "provenance": "user_provided"}.
    - NON_MONEY_NUMBER_FIELDS -> int + sibling ``{fld}_provenance="user_provided"``.
    - ``baths`` -> str + ``baths_provenance="user_provided"``.
    - PLAIN_OVERLAY_FIELDS -> verbatim value.
    """
    for field, value in user.items():
        if field in PROVENANCED_MONEY_FIELDS:
            extracted[field] = {
                "value": _strip_money(str(value)),
                "provenance": "user_provided",
            }
        elif field == "price":
            extracted["price"] = _strip_money(str(value))
        elif field in NON_MONEY_NUMBER_FIELDS:
            extracted[field] = int(value) if value is not None and value != "" else None
            extracted[f"{field}_provenance"] = "user_provided"
        elif field == "baths":
            extracted["baths"] = str(value) if value not in (None, "") else None
            extracted["baths_provenance"] = "user_provided"
        elif field in PLAIN_OVERLAY_FIELDS:
            extracted[field] = value
        else:
            # Unknown / audit-adjacent field — overlay verbatim. Pydantic's
            # extra="forbid" on PropertyListing will reject genuinely invalid
            # keys at validation time (shape-2 path).
            extracted[field] = value
    return extracted


def _mock_sonnet_extract(body: str, project_root: Path) -> dict[str, Any] | None:
    """When ``MORTGAGE_OPS_MOCK_SONNET=1``, read sha-keyed extracted JSON from fixtures.

    Returns the parsed dict, or None if no fixture exists (caller falls back
    to shape-2 awaiting_user_input). sha16 keys mirror the ``mock_sonnet``
    pytest fixture in tests/conftest.py so the same fixture files serve both
    in-process and subprocess test paths.
    """
    import hashlib

    sha16 = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    fixture = project_root / "tests" / "fixtures" / "zillow" / "extracted" / f"{sha16}.json"
    if fixture.is_file():
        try:
            loaded = json.loads(fixture.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        return loaded if isinstance(loaded, dict) else None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="property_fetch",
        description=(
            "Fetch + extract a Zillow property listing into a structured JSON envelope. "
            "Always exits 0 (argparse parse errors return exit 2 per stdlib convention)."
        ),
        epilog=(
            "Envelope shapes (single-line JSON on stdout):\n"
            '  shape-1 success:   {"listing": {...}, "missing": [], "error": null,\n'
            '                      "awaiting_user_input": false, ...}\n'
            '  shape-2 awaiting:  {"listing": {...partial...}, "missing": ["price","zip"],\n'
            '                      "error": null, "awaiting_user_input": true, ...}\n'
            '  shape-3 blocked:   {"listing": null, "error": "captcha_detected"|...,\n'
            '                      "awaiting_user_input": false, ...}\n'
            "\n"
            "Block detection runs BEFORE Sonnet to skip $0.16 cost on blocked pages.\n"
            "--user-provided round-trips honor Q1 default: read cached extraction from\n"
            "data/cache/property-{zpid}.json instead of re-invoking Sonnet.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="Zillow listing URL (homedetails/ or b/ pattern)")
    parser.add_argument(
        "--user-provided",
        type=str,
        default=None,
        help="JSON dict of user-supplied field values (gap-fill round 2)",
    )
    parser.add_argument(
        "--html-from",
        type=Path,
        default=None,
        help="Read HTML from local file (test path; alternative to stdin)",
    )
    args = parser.parse_args()

    # sys.path injection AFTER argparse (parents[4] = project root from 5-deep
    # skill folder: scripts -> mortgage-ops -> skills -> .claude -> repo).
    # Runs after --help has SystemExit'd, so D-18 (--help <300ms) is unaffected.
    project_root = Path(__file__).resolve().parents[4]
    _root_str = str(project_root)
    if _root_str not in sys.path:
        sys.path.insert(0, _root_str)

    # Lazy imports per D-18 inherited: heavy deps (anthropic, duckdb) are NOT
    # loaded on the --help fast path.
    import os

    from lib.property_block_detector import detect_block, extract_zpid
    from lib.property_extractor import extract_listing
    from lib.property_listing import PropertyListing

    fetched_at = _now_iso_z()

    def _emit(env: dict[str, Any]) -> int:
        print(json.dumps(env))
        return 0

    # ZPID extraction first — needed for cache lookup (Q1 default) and shape-3
    # zpid_extraction_failed. Block detection still runs BEFORE Sonnet below.
    zpid = extract_zpid(args.url)

    # Q1 default: on Round 2 (--user-provided given) with cached extraction,
    # skip stdin/--html-from + Sonnet entirely and reuse the cached dict.
    cache_path: Path | None = None
    cached_extracted: dict[str, Any] | None = None
    if zpid is not None:
        cache_path = project_root / "data" / "cache" / f"property-{zpid}.json"
        if args.user_provided is not None and cache_path.is_file():
            try:
                cached_extracted = json.loads(cache_path.read_text(encoding="utf-8"))
                if not isinstance(cached_extracted, dict):
                    cached_extracted = None
            except (OSError, json.JSONDecodeError):
                cached_extracted = None

    # HTML acquisition: --html-from fixture, or stdin from parent agent's WebFetch.
    # CLI itself NEVER fetches via requests/httpx — D-13-MODEL-01.
    if cached_extracted is not None:
        # Cache hit — body is unused downstream; skip stdin read entirely.
        body = ""
        status_code = 200
    elif args.html_from is not None:
        body = args.html_from.read_text(encoding="utf-8", errors="replace")
        status_code = 200
    else:
        body = sys.stdin.read()
        status_code = 200  # parent passes only on success; non-200 routed upstream

    # 1. Block detection (BEFORE Sonnet — saves ~$0.16/blocked page per D-13-BLOCK-01).
    #    Skipped on cache hits (body is empty + we already validated previously).
    if cached_extracted is None:
        block_err = detect_block(status_code, body)
        if block_err is not None:
            return _emit(
                {
                    "listing": None,
                    "missing": [],
                    "error": block_err,
                    "awaiting_user_input": False,
                    "source_url": args.url,
                    "fetched_at": fetched_at,
                }
            )

    # 2. ZPID extraction failure -> shape-3 (after block-detect so blocked pages
    #    surface their specific error rather than masking as zpid_extraction_failed).
    if zpid is None:
        return _emit(
            {
                "listing": None,
                "missing": [],
                "error": "zpid_extraction_failed",
                "awaiting_user_input": False,
                "source_url": args.url,
                "fetched_at": fetched_at,
            }
        )

    # 3. Sonnet extraction (or cache reuse, or mock-Sonnet hook).
    if cached_extracted is not None:
        extracted: dict[str, Any] | None = cached_extracted
        skip_wrap = True  # cache JSON is already wrapped
    elif os.environ.get("MORTGAGE_OPS_MOCK_SONNET") == "1":
        extracted = _mock_sonnet_extract(body, project_root)
        skip_wrap = False
    else:
        extracted = extract_listing(body, args.url)
        skip_wrap = False

    # 4. If extraction returned None AND no --user-provided fill, shape-2.
    #    If --user-provided is given, treat extracted as empty dict so the merge
    #    step can build the full record from user values alone.
    if extracted is None:
        if args.user_provided is None:
            return _emit(
                {
                    "listing": None,
                    "missing": list(MUST_HAVE),
                    "error": None,
                    "awaiting_user_input": True,
                    "source_url": args.url,
                    "fetched_at": fetched_at,
                }
            )
        extracted = {}
        skip_wrap = True  # nothing to wrap; user-provided values overlay directly

    # 5. Defensive money-coercion (§Pitfall 15).
    extracted = _coerce_money_to_string(extracted)

    # 6. Wrap scraped ProvenancedMoney + sibling *_provenance fields BEFORE merge.
    #    Skipped when reading from cache (already wrapped) or when no extraction.
    if not skip_wrap:
        extracted = _wrap_scraped_provenanced_money(extracted)

    # 7. Merge --user-provided overlay (D-13-GAPFILL-01); tags provenance.
    if args.user_provided:
        extracted = _merge_user_provided(extracted, json.loads(args.user_provided))

    # 8. Add audit fields (source_url, zpid, fetched_at). CLI owns these per
    #    extractor docstring (extract_listing does NOT add them).
    extracted["source_url"] = args.url
    extracted["zpid"] = zpid
    extracted["fetched_at"] = fetched_at

    # 9. Pydantic validation. PropertyListing uses strict=True so Decimal-typed
    #     money fields and datetime fields will reject string inputs from
    #     ``model_validate(dict)``. Route through ``model_validate_json`` so
    #     Pydantic's JSON parser handles the string->Decimal / string->datetime
    #     coercion at the boundary (matches lib.property_persistence pattern).
    #     On failure -> shape-2 with computed missing set.
    try:
        listing = PropertyListing.model_validate_json(json.dumps(extracted))
    except Exception:
        present = {f for f in MUST_HAVE if extracted.get(f) not in (None, "")}
        missing = [f for f in MUST_HAVE if f not in present]
        partial = {k: extracted[k] for k in MUST_HAVE if k in extracted}
        return _emit(
            {
                "listing": partial,
                "missing": missing if missing else list(MUST_HAVE),
                "error": None,
                "awaiting_user_input": True,
                "source_url": args.url,
                "fetched_at": fetched_at,
            }
        )

    # 10. Q1 cache write: persist the validated-source dict to
    #     data/cache/property-{zpid}.json so a follow-up --user-provided round
    #     can skip Sonnet entirely. Best-effort; never blocks envelope emission.
    if cache_path is not None and cached_extracted is None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(extracted, default=str), encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"cache write warning: {exc!r}\n")

    # 11. Persistence (best-effort; never blocks envelope emission).
    #     Wrapped in try/except for ImportError safety (Plan 13-05 ships
    #     write_listing; if not available, degrade gracefully with stderr warn).
    try:
        from lib.property_persistence import compute_household_hash, write_listing

        try:
            from lib.fred_cache import get_cached_or_fetch

            mort_cached = get_cached_or_fetch("MORTGAGE30US")
            mort_value = str(mort_cached.get("value")) if mort_cached else "uncomputed"
            if (
                mort_value in ("None", "", "uncomputed")
                or mort_cached is None
                or mort_cached.get("value") is None
            ):
                mort_value = "uncomputed"
        except Exception:
            mort_value = "uncomputed"

        try:
            household_yml = project_root / "config" / "household.yml"
            profile_yml = project_root / "config" / "profile.yml"
            if household_yml.is_file() and profile_yml.is_file() and mort_value != "uncomputed":
                household_hash = compute_household_hash(household_yml, profile_yml, mort_value)
            else:
                household_hash = "uncomputed"
        except Exception:
            household_hash = "uncomputed"

        write_listing(listing, household_hash=household_hash)
    except Exception as exc:
        sys.stderr.write(f"persistence warning: {exc!r}\n")

    return _emit(
        {
            "listing": json.loads(listing.model_dump_json()),
            "missing": [],
            "error": None,
            "awaiting_user_input": False,
            "source_url": args.url,
            "fetched_at": fetched_at,
        }
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise  # argparse parse errors (exit 2) — the one documented non-zero exit
    except Exception as exc:
        print(
            json.dumps(
                {
                    "listing": None,
                    "missing": [],
                    "error": f"unexpected_failure: {exc!r}",
                    "awaiting_user_input": False,
                    "source_url": "<unknown>",
                    "fetched_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                }
            )
        )
        sys.exit(0)

#!/usr/bin/env python3
""".claude/skills/mortgage-ops/scripts/property_analyze.py — PropertyListing
JSON + household.yml + profile.yml -> AnalysisReport -> markdown report.

Phase 15 MODE-03 + D-15-ORCH-01..04. Pure compute (no network); browser-side
fetching + URL handling lives in ``modes/property.md`` (D-15-ORCH-02). Mirrors Phase 12
always-exit-0 contract (D-12-LIVE02-01) and Phase 3 6-key Pydantic envelope on
validation errors (WR-02 closure).

Envelope contract (single-line JSON on stdout, ALWAYS exit 0):

  success:  {"report_path": "reports/{NNN}-property-{zpid}-{YYYY-MM-DD}.md",
             "verdict": "GO" | "WATCH" | "NO_GO", "error": null}
  error:    {"report_path": null, "verdict": null,
             "error": {"code": "<error_code>",
                       "message": "<human-readable>"}}

Error codes (D-15-ORCH-03):
  - household_yaml_invalid       — yaml.safe_load / KeyError / Household ValidationError
  - profile_yaml_invalid         — yaml.safe_load / KeyError / Profile ValidationError
  - listing_validation_failed    — PropertyListing.model_validate_json ValidationError
                                   (6-key Pydantic envelope ALSO emitted on stderr)
  - fred_cache_cold              — lib.property_analysis raised ValueError containing
                                   "FRED cache cold" substring (cache refresh required)
  - missing_county_data          — surface-future-proof; Phase 14 currently degrades
                                   internally to warnings.append("MissingCountyDataError")
  - analyze_internal_error       — any other Exception caught at outer wrapper
  - output_dir_unwritable        — --output-dir outside project root or not a directory
                                   (ASVS V5 path-traversal hardening)

Pydantic ValidationError 6-key envelope contract (WR-02 closure, verbatim from
scripts/amortize.py L36-60):

  All ValidationError-class boundary surfaces emit a uniform 6-key Pydantic v2
  e.json() envelope on stderr:
    [{"type": "<error_type>", "loc": [<JSON-pointer>],
      "msg": "<message>",     "input": "<offending_value>",
      "url": "<docs_url>",    "ctx": {"class": "<...>", ...}}]
  Canonical URL pattern: https://errors.pydantic.dev/{MAJOR.MINOR}/v/{error_type}.
  Downstream consumers (Phase 9 Node orchestration / Phase 10 SKILL.md narration)
  parse stderr as a JSON list of 6-key error dicts.

Usage:
  python .claude/skills/mortgage-ops/scripts/property_analyze.py \\
    --listing data/property-listings/{zpid}-{date}.json \\
    --household config/household.yml \\
    --profile config/profile.yml \\
    --output-dir reports/

Always exits 0. The ONLY documented exit-2 case is argparse parse error (Phase
12 WR-02 + D-12-LIVE02-01). All other failure modes — bad listing JSON, missing
YAML, FRED cache cold, path traversal — emit the error envelope on stdout and
return 0.

DATA_CONTRACT (CLAUDE.md User Layer): reads config/household.yml +
config/profile.yml; NEVER writes them. The orchestrator is read-only against
the User Layer (ASVS V4).

Pure-compute discipline (D-15-ORCH-01 + Pitfall 7): no network libraries are
imported (no requests/urllib/httpx/anthropic-style SDK; no browser-side
fetching tools). Network I/O is a parent-agent concern that ``modes/property.md``
owns; the orchestrator just composes Phase 14 analyze() + Plan 15-02 render()
into a markdown file under reports/.

Sidecar listing JSON write (Pitfall 10 + Assumption A3): the validated
PropertyListing is copied to ``data/property-listings/{zpid}-{YYYY-MM-DD}.json``
BEFORE writing the report; the citation-footer argv is rewritten to cite that
stable path so the report's "Computed by:" footer is a reproducible copy-paste.

NNN sequencer (D-15-ORCH-04 + Pitfall 6): the filename uses the next available
3-digit prefix across all files under ``--output-dir``; same-day-same-zpid
collisions append ``-r2`` / ``-r3`` etc. so re-runs never overwrite prior reports.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lib.household import Household


def _emit_error_envelope(code: str, message: str) -> None:
    """Print error-envelope JSON to stdout (D-15-ORCH-03).

    Module-level for testability + grep-visibility on the plan's verify regex.
    """
    print(
        json.dumps(
            {
                "report_path": None,
                "verdict": None,
                "error": {"code": code, "message": message},
            }
        )
    )


def _resolve_filename(out_dir: Path, zpid: str, today: str) -> Path:
    """NNN sequencer (D-15-ORCH-04 + Pitfall 6): scan ``out_dir`` for the highest
    3-digit prefix; increment by 1; same-day-same-zpid duplicates append
    ``-r2`` / ``-r3`` / etc. so re-runs never overwrite prior reports.

    Module-level for testability + grep-visibility on the plan's verify regex.
    """
    pattern = re.compile(r"^(\d{3})-")
    existing_nnns: list[int] = []
    for f in out_dir.glob("*.md"):
        m = pattern.match(f.name)
        if m is not None:
            existing_nnns.append(int(m.group(1)))
    next_nnn = (max(existing_nnns) + 1) if existing_nnns else 1
    base = f"{next_nnn:03d}-property-{zpid}-{today}"
    dupes = list(out_dir.glob(f"*-property-{zpid}-{today}*.md"))
    if not dupes:
        return out_dir / f"{base}.md"
    return out_dir / f"{base}-r{len(dupes) + 1}.md"


def _load_phase14_household_from_yaml(path: Path) -> Household:
    """Map the Phase-4 multi-applicant household.yml schema to the flat
    Phase-14 Household snapshot (Pitfall 2). Aggregates gross_monthly_income
    across applicants, sums the 4 monthly_debts categories, takes min FICO,
    and defaults the two Phase-15 optional fields when omitted.

    Module-level for testability + grep-visibility on the plan's verify regex.
    Lazy-imports yaml / Decimal / Household so the --help fast path stays clean
    (this function is never called on --help; argparse exits first).
    """
    from decimal import Decimal

    import yaml
    from lib.household import Household
    from lib.money import quantize_cents

    raw = yaml.safe_load(path.read_text())["household"]
    monthly_income = sum(
        (Decimal(a["gross_monthly_income"]) for a in raw["applicants"]),
        Decimal("0"),
    )
    monthly_obligations = sum(
        (
            Decimal(raw["monthly_debts"][k])
            for k in ("auto", "student_loans", "credit_cards", "other")
        ),
        Decimal("0"),
    )
    fico = min(int(a["credit_score"]) for a in raw["applicants"])
    return Household(
        monthly_income=quantize_cents(monthly_income),
        monthly_obligations=quantize_cents(monthly_obligations),
        fico=fico,
        liquid_reserves=Decimal(raw.get("liquid_reserves", "0.00")),
        state_fips=raw["location"]["state_fips"],
        county_fips=raw["location"]["county_fips"],
        county_name=raw["location"]["county_name"],
        preferred_down_payment_pct=Decimal(raw.get("preferred_down_payment_pct", "0.200000")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="property_analyze",
        description=(
            "Compose Phase 14 analyze() into a markdown underwriting report. "
            "Always exits 0 (argparse parse errors return exit 2)."
        ),
        epilog=(
            "Envelope shapes (single-line JSON on stdout):\n"
            '  success: {"report_path": "...", "verdict": "GO|WATCH|NO_GO", "error": null}\n'
            '  error:   {"report_path": null, "verdict": null, '
            '"error": {"code": "...", "message": "..."}}\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--listing", required=True, type=Path)
    parser.add_argument("--household", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    # sys.path injection AFTER argparse so --help is fast (D-18). parents[4]
    # from .claude/skills/mortgage-ops/scripts/property_analyze.py is the
    # project root, mirroring Phase 13 property_fetch.py:213 verbatim:
    #   parents[0] = scripts/
    #   parents[1] = mortgage-ops/ (skill root)
    #   parents[2] = skills/
    #   parents[3] = .claude/
    #   parents[4] = repo root
    project_root = Path(__file__).resolve().parents[4]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Lazy imports per D-18: heavy deps (pydantic, yaml, lib.property_analysis)
    # are NOT loaded on the --help fast path. argparse has already exited above
    # for --help / --version invocations. The module-level helpers
    # _emit_error_envelope / _resolve_filename / _load_phase14_household_from_yaml
    # already have their own lazy-import discipline; no additional setup needed.
    from decimal import Decimal

    import yaml
    from lib.profile import Profile
    from lib.property_analysis import analyze
    from lib.property_listing import PropertyListing
    from lib.property_report import render
    from pydantic import ValidationError

    # Step A — --output-dir hardening (ASVS V5 / Pitfall PATTERNS L920-930).
    #
    # Reject:
    #   1. paths containing ".." segments (defense-in-depth path-traversal),
    #   2. paths that don't resolve to an existing directory,
    #   3. paths whose resolved location is NOT inside the project root.
    #
    # Containment uses Path.is_relative_to(project_root) against the FULLY
    # resolved (symlink-followed) output dir vs. the fully resolved project
    # root, so e.g. /tmp/foo-property-out, ~/Desktop/reports, or a symlink
    # pointing outside the repo all fail closed. This closes the medium-
    # severity gap where the previous "directory exists" gate accepted any
    # writable directory anywhere on disk.
    raw_output_dir = args.output_dir
    if ".." in raw_output_dir.parts:
        _emit_error_envelope(
            "output_dir_unwritable",
            f"output-dir must not contain '..' segments; got {raw_output_dir}",
        )
        return 0
    try:
        output_dir = raw_output_dir.resolve()
    except OSError as exc:
        _emit_error_envelope(
            "output_dir_unwritable",
            f"output-dir could not be resolved: {exc!r}",
        )
        return 0
    if not output_dir.is_dir():
        _emit_error_envelope(
            "output_dir_unwritable",
            f"output-dir does not exist or is not a directory: {output_dir}",
        )
        return 0
    if not output_dir.is_relative_to(project_root):
        _emit_error_envelope(
            "output_dir_unwritable",
            (f"output-dir must be inside the project root ({project_root}); got {output_dir}"),
        )
        return 0

    # Step B — load + validate PropertyListing JSON. Two accepted input shapes:
    #   1. Flat PropertyListing JSON (production path; matches property_fetch.py
    #      shape-1 envelope's ``listing`` block contents).
    #   2. Eval-fixture wrapper {"listing": {...}, "household": ..., "profile": ...,
    #      "expected_response": ..., "_meta": ...} — the orchestrator extracts
    #      the ``listing`` sub-document so the same fixture used by Phase 14
    #      unit tests (and Plan 15-01's evals/fixtures/property/) flows through
    #      the orchestrator without bespoke transformation.
    try:
        listing_raw_text = args.listing.read_text()
    except FileNotFoundError:
        _emit_error_envelope(
            "listing_validation_failed",
            f"--listing file not found: {args.listing}",
        )
        return 0
    except OSError as exc:
        _emit_error_envelope(
            "listing_validation_failed",
            f"--listing file could not be read: {exc!r}",
        )
        return 0

    try:
        listing_root: Any = json.loads(listing_raw_text)
    except json.JSONDecodeError as exc:
        _emit_error_envelope(
            "listing_validation_failed",
            f"--listing is not valid JSON: {exc!r}",
        )
        return 0

    # Optional eval-fixture wrapper: when --listing points at a wrapper that
    # carries a top-level ``fred_rates`` block (Plan 15-01 + Phase 14 unit-test
    # fixture shape), the orchestrator extracts the inner ``listing`` and
    # forwards the wrapped rates to analyze() as fred_mortgage_{30,15}us kwargs.
    # This keeps the synthetic-fixture path FRED-cache-independent and matches
    # the test injection contract documented in lib/property_analysis.py:1437-1440.
    fred_30_override: Decimal | None = None
    fred_15_override: Decimal | None = None
    if (
        isinstance(listing_root, dict)
        and "listing" in listing_root
        and isinstance(listing_root["listing"], dict)
    ):
        listing_payload: Any = listing_root["listing"]
        wrapped_rates = listing_root.get("fred_rates")
        if isinstance(wrapped_rates, dict):
            rate_30_raw = wrapped_rates.get("MORTGAGE30US")
            rate_15_raw = wrapped_rates.get("MORTGAGE15US")
            try:
                if rate_30_raw is not None:
                    fred_30_override = Decimal(str(rate_30_raw))
                if rate_15_raw is not None:
                    fred_15_override = Decimal(str(rate_15_raw))
            except (ValueError, ArithmeticError):
                # Malformed fred_rates block — degrade gracefully (cache-cold
                # path remains; we don't fail the validation step over an
                # auxiliary fixture-only field).
                fred_30_override = None
                fred_15_override = None
    else:
        listing_payload = listing_root

    try:
        listing = PropertyListing.model_validate_json(json.dumps(listing_payload))
    except ValidationError as e:
        # WR-02 closure: dual emission — 6-key Pydantic envelope on stderr,
        # orchestrator error envelope on stdout; return 0 (D-15-ORCH-03
        # supersedes amortize.py's exit-2 on ValidationError).
        print(e.json(), file=sys.stderr)
        _emit_error_envelope(
            "listing_validation_failed",
            "PropertyListing failed Pydantic validation; see stderr 6-key envelope",
        )
        return 0

    # Step C — load household.yml -> Phase-14 flat Household (Pitfall 2).
    try:
        household = _load_phase14_household_from_yaml(args.household)
    except (yaml.YAMLError, KeyError, ValueError, ValidationError, TypeError) as exc:
        _emit_error_envelope(
            "household_yaml_invalid",
            f"household.yml could not be loaded: {exc!r}",
        )
        return 0
    except FileNotFoundError:
        _emit_error_envelope(
            "household_yaml_invalid",
            f"--household file not found: {args.household}",
        )
        return 0

    # Step D — load profile.yml -> Profile. Route through model_validate_json
    # (not direct Profile(**raw)) so Decimal-string fields like marginal_tax_rate
    # coerce correctly under strict mode (mirrors the JSON-validation idiom in
    # property_fetch.py:347 + tests/test_property_analysis.py:1264).
    try:
        profile_raw = yaml.safe_load(args.profile.read_text())["profile"]
        profile = Profile.model_validate_json(json.dumps(profile_raw))
    except FileNotFoundError:
        _emit_error_envelope(
            "profile_yaml_invalid",
            f"--profile file not found: {args.profile}",
        )
        return 0
    except (yaml.YAMLError, KeyError, ValueError, ValidationError, TypeError) as exc:
        _emit_error_envelope(
            "profile_yaml_invalid",
            f"profile.yml could not be loaded: {exc!r}",
        )
        return 0

    # Step E — call analyze() (Phase 14 frozen entrypoint). FRED cache-cold
    # surfaces as ValueError with substring "FRED cache cold" (per
    # lib/property_analysis.py:540-543); all other Exceptions degrade to
    # analyze_internal_error so the always-exit-0 envelope contract holds.
    try:
        report = analyze(
            listing,
            household,
            profile,
            fred_mortgage_30us=fred_30_override,
            fred_mortgage_15us=fred_15_override,
        )
    except ValueError as exc:
        if "FRED cache cold" in str(exc):
            _emit_error_envelope("fred_cache_cold", str(exc))
            return 0
        _emit_error_envelope(
            "analyze_internal_error",
            f"analyze() ValueError: {exc!r}",
        )
        return 0
    except Exception as exc:
        _emit_error_envelope(
            "analyze_internal_error",
            f"analyze() raised {type(exc).__name__}: {exc!r}",
        )
        return 0

    # Step F — sidecar listing JSON write (Pitfall 10 + A3 reproducible footer).
    today = datetime.now(UTC).date().isoformat()
    zpid = listing.zpid
    sidecar_dir = project_root / "data" / "property-listings"
    try:
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        sidecar_path = sidecar_dir / f"{zpid}-{today}.json"
        sidecar_path.write_text(listing.model_dump_json(indent=2))
    except OSError as exc:
        _emit_error_envelope(
            "analyze_internal_error",
            f"sidecar listing write failed: {exc!r}",
        )
        return 0

    # Step G — rewrite footer argv so the citation cites the stable sidecar
    # path, NOT the (possibly ephemeral) input --listing path. Output-dir is
    # written as project-relative for portability across the user's filesystem.
    sidecar_rel = sidecar_path.relative_to(project_root)
    try:
        output_dir_rel = output_dir.relative_to(project_root)
        output_dir_arg = f"{output_dir_rel}/"
    except ValueError:
        # output_dir is exactly project_root (or unrelated — already rejected above).
        output_dir_arg = str(output_dir) + "/"
    footer_argv: list[str] = [
        "--listing",
        str(sidecar_rel),
        "--household",
        str(args.household),
        "--profile",
        str(args.profile),
        "--output-dir",
        output_dir_arg,
    ]

    # Step H — render markdown body via the Plan 15-02 formatter.
    try:
        markdown_body = render(report, footer_argv)
    except Exception as exc:
        _emit_error_envelope(
            "analyze_internal_error",
            f"render() raised {type(exc).__name__}: {exc!r}",
        )
        return 0

    # Step I — resolve filename via NNN sequencer.
    report_path = _resolve_filename(output_dir, zpid, today)

    # Step J — write report.
    try:
        report_path.write_text(markdown_body)
    except OSError as exc:
        _emit_error_envelope(
            "analyze_internal_error",
            f"report write failed: {exc!r}",
        )
        return 0

    # Step K — emit success envelope on stdout. report_path is project-relative
    # when possible (matches the citation-footer convention); falls back to
    # absolute when output_dir lies outside the project (already rejected above,
    # so this is defense-in-depth).
    try:
        report_path_str = str(report_path.relative_to(project_root))
    except ValueError:
        report_path_str = str(report_path)
    print(
        json.dumps(
            {
                "report_path": report_path_str,
                "verdict": report.verdict.level,
                "error": None,
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise  # argparse parse errors (exit 2) — the one documented non-zero exit
    except Exception as exc:
        # Phase 12 D-12-LIVE02-01 + D-15-ORCH-03: ANY uncaught exception that
        # escapes main() converts to an error envelope + exit 0. This is the
        # last line of defense; main() already catches every documented surface.
        print(
            json.dumps(
                {
                    "report_path": None,
                    "verdict": None,
                    "error": {
                        "code": "analyze_internal_error",
                        "message": f"unexpected_failure: {exc!r}",
                    },
                }
            )
        )
        sys.exit(0)

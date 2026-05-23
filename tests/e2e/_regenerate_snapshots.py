"""Snapshot regenerator for tests/e2e.

When the calc engine output legitimately changes (e.g., a regulatory YAML
refresh, a rounding-rule clarification, an APR-band cutoff move),
regenerate the affected snapshot:

    uv run python tests/e2e/_regenerate_snapshots.py <stem>
    uv run python tests/e2e/_regenerate_snapshots.py --all

Then `git diff tests/e2e/fixtures/snapshots/` and review the change. If the
diff aligns with the engine change you intended, commit. If not, the
regeneration surfaced an unintended engine regression — investigate before
overwriting the snapshot.

This module is NOT collected by pytest (the leading underscore + lack of
``test_`` prefix). It is a manual maintenance tool.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUTS_DIR = Path(__file__).resolve().parent / "fixtures" / "inputs"
SNAPSHOTS_DIR = Path(__file__).resolve().parent / "fixtures" / "snapshots"
SKILL_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "mortgage-ops" / "scripts"

CLI_PATHS: dict[str, Path] = {
    "affordability": SKILL_SCRIPTS / "affordability.py",
    "amortize": SKILL_SCRIPTS / "amortize.py",
    "arm_simulate": SKILL_SCRIPTS / "arm_simulate.py",
    "refi_npv": SKILL_SCRIPTS / "refi_npv.py",
}


def regenerate_one(stem: str) -> None:
    """Re-run a single fixture's CLI and overwrite its snapshot file."""
    fixture_path = INPUTS_DIR / f"{stem}.yml"
    if not fixture_path.exists():
        raise FileNotFoundError(f"No input fixture at {fixture_path}")
    spec = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    cli_name = spec["cli"]
    script = CLI_PATHS[cli_name]

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(spec["request"], f)
        req_path = f.name
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--input", req_path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    finally:
        with contextlib.suppress(OSError):
            os.unlink(req_path)

    if proc.returncode != 0:
        print(
            f"!! {stem}: CLI exited {proc.returncode}",
            file=sys.stderr,
        )
        print(proc.stderr[:2048], file=sys.stderr)
        raise SystemExit(1)

    payload = json.loads(proc.stdout)
    snap_path = SNAPSHOTS_DIR / f"{stem}.json"
    snap_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"ok {stem}: rewrote {snap_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate E2E snapshot JSON from current engine output."
    )
    parser.add_argument(
        "stems",
        nargs="*",
        help="Fixture stems to regenerate (e.g. scenario_a_conv30_median).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Regenerate every fixture under tests/e2e/fixtures/inputs/.",
    )
    args = parser.parse_args()

    if args.all:
        stems: list[str] = sorted(p.stem for p in INPUTS_DIR.glob("*.yml"))
    elif args.stems:
        stems = args.stems
    else:
        parser.error("pass one or more stems, or --all")

    for stem in stems:
        regenerate_one(stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

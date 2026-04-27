"""REF-09: Every data/reference/*.yml has `source:` URL and `effective:` date.

Filesystem-introspecting meta-test (parametrized at collection time). Adding a
new YAML without source/effective produces a new failing test case automatically.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest
import yaml

REF_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data" / "reference"


def _ref_files() -> list[Path]:
    return sorted(p for p in REF_DIR.glob("*.yml"))


@pytest.mark.parametrize("path", _ref_files(), ids=lambda p: p.stem)
def test_reference_yaml_has_source_and_effective(path: Path) -> None:
    raw = yaml.safe_load(path.read_text())
    assert isinstance(raw, dict), f"{path.name} must parse to a dict (REF-09)"
    assert "source" in raw, f"{path.name} missing `source:` (REF-09)"
    assert "effective" in raw, f"{path.name} missing `effective:` (REF-09)"
    assert re.match(r"^https?://", raw["source"]), (
        f"{path.name} `source:` must be an http(s) URL (REF-09)"
    )
    assert isinstance(raw["effective"], date), (
        f"{path.name} `effective:` must be a YAML date (zero-padded YYYY-MM-DD); "
        f"got {type(raw['effective']).__name__} (REF-09)"
    )

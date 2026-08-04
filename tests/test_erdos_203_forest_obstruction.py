from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKER = (
    ROOT
    / "execution"
    / "erdos-203-cover"
    / "verify_forest_obstruction_55440.py"
)
ARTIFACT = (
    ROOT / "artifacts" / "analyses" / "erdos203-55440-forest-obstruction.v1.json"
)
SPEC = importlib.util.spec_from_file_location("erdos_203_forest_checker", CHECKER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_exact_forest_obstruction_verifies() -> None:
    result = MODULE.verify(ROOT, ARTIFACT)
    assert result["ok"] is True
    assert result["tree_edges"] == 54
    assert result["forest_mass"] == "353861/1663200"
    assert result["density_slack"] == "3013/18480"
    assert result["contradiction_gap"] == "11813/237600"
    assert result["result"] == "no_cover_selected_family"


def test_checker_rejects_a_duplicated_tree_edge(tmp_path: pathlib.Path) -> None:
    value = json.loads(ARTIFACT.read_text())
    selected = value["certificate"]["selected_pairs"]
    selected[1] = selected[0]
    candidate = tmp_path / "mutated.json"
    candidate.write_bytes(MODULE.canonical_bytes(value))
    with pytest.raises(ValueError, match="duplicated or not in"):
        MODULE.verify(ROOT, candidate)

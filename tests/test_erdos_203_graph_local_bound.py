from __future__ import annotations

import copy
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKER = (
    ROOT / "execution" / "erdos-203-cover" / "verify_graph_local_55440.py"
)
ARTIFACT = (
    ROOT / "artifacts" / "analyses" / "erdos203-55440-graph-local-bound.v1.json"
)
SPEC = importlib.util.spec_from_file_location("erdos_203_graph_local_checker", CHECKER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def artifact() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text())


def test_all_root_excluding_orientations_verify() -> None:
    value = artifact()
    graph = value["graph"]
    certificate = value["certificate"]
    MODULE.verify_orientations(
        graph["vertices"],
        [tuple(edge) for edge in graph["edges"]],
        certificate["root_excluding_orientations"],
    )
    assert certificate["exact_edge_to_excess_ratio"] == "91/6"
    assert value["comparison"]["contradiction_gap"] == (
        "-412596397/204906240"
    )
    assert value["conclusion"]["result"] == "no_conclusion"


def test_orientation_check_fails_closed_on_one_changed_unit() -> None:
    value = artifact()
    graph = value["graph"]
    certificates = copy.deepcopy(
        value["certificate"]["root_excluding_orientations"]
    )
    first = certificates[0]["left_endpoint_units"]
    first[0] = first[0] + 1 if first[0] < 6 else first[0] - 1
    with pytest.raises(ValueError, match="orientation capacity certificate fails"):
        MODULE.verify_orientations(
            graph["vertices"],
            [tuple(edge) for edge in graph["edges"]],
            certificates,
        )

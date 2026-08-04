#!/usr/bin/env python3
"""Independently check the 55440 mandatory-pair forest obstruction."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from fractions import Fraction
from typing import Any

TARGET = "erdos:203:finite-cover"
INPUT_ROOT = "sha256:c4e63f2cec41e39c9c6bcbb08207a76892900d6b88c47d672aee2c63025322bd"
INPUT_CHECK_ROOT = "sha256:5a13a21aa562181dc7b706bf9320cd89e3c5555a5794df8c2b9312ae6a235660"
SCHEMA = "erdos-frontier.erdos-203-55440-forest-obstruction.v1"
PREREGISTRATION = "execution/erdos-203-cover/forest-55440-preregistration.v1.json"
PRODUCER = "execution/erdos-203-cover/forest_obstruction_55440.py"
INPUT_ARTIFACT = "artifacts/analyses/erdos203-55440-overlap-obstruction.v1.json"
INPUT_CHECK = "artifacts/runs/erdos203-55440-overlap-obstruction-check.v1.json"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class DisjointSet:
    def __init__(self, vertices: list[int]) -> None:
        self.parent = {vertex: vertex for vertex in vertices}

    def find(self, vertex: int) -> int:
        while self.parent[vertex] != vertex:
            self.parent[vertex] = self.parent[self.parent[vertex]]
            vertex = self.parent[vertex]
        return vertex

    def join(self, left: int, right: int) -> bool:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return False
        self.parent[right_root] = left_root
        return True


def verify(frontier: pathlib.Path, artifact: pathlib.Path) -> dict[str, Any]:
    preregistration_raw = (frontier / PREREGISTRATION).read_bytes()
    preregistration = json.loads(preregistration_raw)
    if preregistration_raw != canonical_bytes(preregistration):
        raise ValueError("preregistration is not canonical JSON")
    producer_raw = (frontier / PRODUCER).read_bytes()
    registered_producer = preregistration.get("method", {}).get("producer", {})
    if registered_producer != {
        "path": PRODUCER,
        "sha256": root(producer_raw),
        "size": len(producer_raw),
    }:
        raise ValueError("producer bytes drifted from preregistration")

    input_raw = (frontier / INPUT_ARTIFACT).read_bytes()
    if root(input_raw) != INPUT_ROOT:
        raise ValueError("registered mandatory graph root drifted")
    input_value = json.loads(input_raw)
    input_check_raw = (frontier / INPUT_CHECK).read_bytes()
    if root(input_check_raw) != INPUT_CHECK_ROOT:
        raise ValueError("source-first mandatory graph check root drifted")
    input_check = json.loads(input_check_raw)
    if not input_check.get("ok") or input_check.get("artifact_root") != INPUT_ROOT:
        raise ValueError("source-first mandatory graph check is not valid")

    raw = artifact.read_bytes()
    value = json.loads(raw)
    if raw != canonical_bytes(value) or value.get("schema") != SCHEMA:
        raise ValueError("forest artifact is not canonical or has the wrong schema")
    if value.get("target") != TARGET or value.get("claim_credit") is not False:
        raise ValueError("forest artifact crosses its Target or credit boundary")
    if value.get("inputs") != {
        "artifact_path": INPUT_ARTIFACT,
        "artifact_root": INPUT_ROOT,
        "preregistration": PREREGISTRATION,
    }:
        raise ValueError("forest artifact inputs drifted")

    vertices = [member["prime"] for member in input_value["family"]["members"]]
    mandatory = {
        tuple(pair["primes"]): pair
        for pair in input_value["mandatory_overlap"]["pairs"]
    }
    certificate = value.get("certificate", {})
    if certificate.get("vertices") != vertices:
        raise ValueError("forest vertex list differs from the mandatory graph")
    selected = certificate.get("selected_pairs", [])
    if len(selected) != len(vertices) - 1 or certificate.get("edge_count") != 54:
        raise ValueError("forest certificate has the wrong edge count")
    components = DisjointSet(vertices)
    seen = set()
    mass = Fraction()
    for pair in selected:
        key = tuple(pair.get("primes", []))
        if key in seen or key not in mandatory or pair != mandatory[key]:
            raise ValueError("selected pair is duplicated or not in the mandatory graph")
        seen.add(key)
        if not components.join(*key):
            raise ValueError("selected mandatory pairs contain a cycle")
        mass += Fraction(pair["intersection_density"])
    if len({components.find(vertex) for vertex in vertices}) != 1:
        raise ValueError("selected mandatory pairs are not spanning")

    slack = Fraction(input_value["family"]["density_slack"])
    gap = mass - slack
    if mass != Fraction(353861, 1663200):
        raise ValueError("forest mass differs from the frozen exact result")
    if gap != Fraction(11813, 237600) or gap <= 0:
        raise ValueError("forest does not strictly exceed multiplicity slack")
    if certificate.get("forest_mass") != str(mass):
        raise ValueError("reported forest mass differs")
    if value.get("comparison") != {
        "forest_mass": str(mass),
        "density_slack": str(slack),
        "contradiction_gap": str(gap),
    }:
        raise ValueError("reported forest comparison differs")
    if value.get("conclusion", {}).get("result") != "no_cover_selected_family":
        raise ValueError("forest conclusion differs from the exact inequality")
    return {
        "schema": "erdos-frontier.erdos-203-55440-forest-obstruction-check.v1",
        "ok": True,
        "accepted_state_change": "none",
        "artifact_root": root(raw),
        "mandatory_graph_root": INPUT_ROOT,
        "mandatory_graph_check_root": INPUT_CHECK_ROOT,
        "tiles": len(vertices),
        "tree_edges": len(selected),
        "forest_mass": str(mass),
        "density_slack": str(slack),
        "contradiction_gap": str(gap),
        "result": "no_cover_selected_family",
        "implementation_independence": {
            "imports_producer_code": False,
            "certificate_check": "direct mandatory-edge membership, acyclicity, connectivity, and exact Fraction summation",
            "graph_lineage": "pinned independently checked 1,485-pair mandatory graph",
        },
        "shared_dependencies": [
            "Same human operator and machine as the producer workflow.",
            "Same pinned mandatory-graph artifact, Python runtime, and integer-arithmetic assumptions.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier", required=True, type=pathlib.Path)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = verify(args.frontier.resolve(), args.artifact.resolve())
        raw = canonical_bytes(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

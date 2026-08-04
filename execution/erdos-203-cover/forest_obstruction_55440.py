#!/usr/bin/env python3
"""Build one exact mandatory-pair forest obstruction for the 55440 family."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from fractions import Fraction
from typing import Any

TARGET = "erdos:203:finite-cover"
INPUT_ROOT = "sha256:c4e63f2cec41e39c9c6bcbb08207a76892900d6b88c47d672aee2c63025322bd"
INPUT_SCHEMA = "erdos-frontier.erdos-203-overlap-obstruction.v1"
OUTPUT_SCHEMA = "erdos-frontier.erdos-203-55440-forest-obstruction.v1"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class DisjointSet:
    def __init__(self, vertices: list[int]) -> None:
        self.parent = {vertex: vertex for vertex in vertices}
        self.rank = {vertex: 0 for vertex in vertices}

    def find(self, vertex: int) -> int:
        parent = self.parent[vertex]
        if parent != vertex:
            self.parent[vertex] = self.find(parent)
        return self.parent[vertex]

    def join(self, left: int, right: int) -> bool:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return False
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1
        return True


def build(input_path: pathlib.Path, preregistration: str) -> dict[str, Any]:
    raw = input_path.read_bytes()
    value = json.loads(raw)
    if raw != canonical_bytes(value) or root(raw) != INPUT_ROOT:
        raise ValueError("55440 overlap input is not the pinned canonical artifact")
    if value.get("schema") != INPUT_SCHEMA or value.get("target") != TARGET:
        raise ValueError("55440 overlap input crosses the registered boundary")
    if value.get("inputs", {}).get("period") != 55440:
        raise ValueError("55440 overlap input has the wrong family")

    vertices = [member["prime"] for member in value["family"]["members"]]
    pairs = value["mandatory_overlap"]["pairs"]
    ordered = sorted(
        pairs,
        key=lambda row: (
            -Fraction(row["intersection_density"]),
            row["primes"],
            row["orders"],
        ),
    )
    components = DisjointSet(vertices)
    selected = []
    for pair in ordered:
        left, right = pair["primes"]
        if components.join(left, right):
            selected.append(pair)
    if len(selected) != len(vertices) - 1:
        raise ValueError("mandatory graph is not connected")

    forest_mass = sum(
        (Fraction(pair["intersection_density"]) for pair in selected), Fraction()
    )
    density_slack = Fraction(value["family"]["density_slack"])
    gap = forest_mass - density_slack
    result = "no_cover_selected_family" if gap > 0 else "no_conclusion"
    return {
        "schema": OUTPUT_SCHEMA,
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "inputs": {
            "artifact_path": input_path.as_posix(),
            "artifact_root": INPUT_ROOT,
            "preregistration": preregistration,
        },
        "family": {
            "period": 55440,
            "tiles": len(vertices),
            "density": value["family"]["density"],
            "density_slack": str(density_slack),
        },
        "certificate": {
            "kind": "mandatory_pair_spanning_tree",
            "selection": "Deterministic maximum-weight Kruskal tree ordered by exact intersection density, then prime and order pairs.",
            "vertices": vertices,
            "selected_pairs": selected,
            "edge_count": len(selected),
            "forest_mass": str(forest_mass),
            "pointwise_bound": "Every selected covering-set subgraph has at most |S|-1 edges because the certificate graph is a forest.",
        },
        "comparison": {
            "forest_mass": str(forest_mass),
            "density_slack": str(density_slack),
            "contradiction_gap": str(gap),
        },
        "conclusion": {
            "result": result,
            "scope": (
                "No choice of one affine shift for each of the 55 selected n-divides-55440 tiles covers Z^2."
                if result == "no_cover_selected_family"
                else "The selected mandatory-pair forest does not decide this family."
            ),
            "proof": "For a cover, integrate the selected mandatory-pair count. The spanning-tree property bounds it pointwise by multiplicity minus one, but its exact fixed mass exceeds total multiplicity excess.",
        },
        "nonclaims": [
            "This post-exploratory qualification is not an unbiased discovery episode.",
            "The bounded exclusion says nothing about tiles outside the n-divides-55440 family.",
            "The n-divides-55440 family is not a superset of the separately excluded n-divides-10080 family.",
            "This does not resolve Erdos problem 203 globally or establish novelty.",
            "This is not a Vela Verification or human Decision, and it changes no Standing.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=pathlib.Path)
    parser.add_argument("--preregistration", required=True)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        value = build(args.input, args.preregistration)
        raw = canonical_bytes(value)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "artifact_root": root(raw),
                "result": value["conclusion"]["result"],
                "forest_mass": value["comparison"]["forest_mass"],
                "contradiction_gap": value["comparison"]["contradiction_gap"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

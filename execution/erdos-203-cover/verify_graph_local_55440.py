#!/usr/bin/env python3
"""Independently verify the 55440 graph-local orientation certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import subprocess
from fractions import Fraction
from typing import Any

CAMPAIGN_COMMIT = "94fde841ea6ad90437bd66a91953bfeba13dba0f"
CAMPAIGN_TREE = "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a"
POOL_ROOT = "sha256:9a8f179bf6ab509c53144ac679acd8ffe42e66588b1516b0ca3a9f45e18395b3"
INPUT_ROOT = "sha256:c4e63f2cec41e39c9c6bcbb08207a76892900d6b88c47d672aee2c63025322bd"
TARGET = "erdos:203:finite-cover"
SCHEMA = "erdos-frontier.erdos-203-55440-graph-local-bound.v1"
PREREGISTRATION = "execution/erdos-203-cover/graph-local-55440-preregistration.v1.json"
PRODUCER = "execution/erdos-203-cover/graph_local_55440.py"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def git_value(source: pathlib.Path, expression: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", expression], text=True
    ).strip()


def distinct_prime_factors(value: int) -> list[int]:
    factors = []
    candidate = 2
    while candidate * candidate <= value:
        if value % candidate == 0:
            factors.append(candidate)
            while value % candidate == 0:
                value //= candidate
        candidate = 3 if candidate == 2 else candidate + 2
    if value > 1:
        factors.append(value)
    return factors


def primitive_root_prime(prime: int) -> int:
    factors = distinct_prime_factors(prime - 1)
    for candidate in range(2, prime):
        if all(pow(candidate, (prime - 1) // factor, prime) != 1 for factor in factors):
            return candidate
    raise ValueError(f"no primitive root found for p={prime}")


def subgroup_log(prime: int, generator: int, order: int, target: int) -> int:
    value = 1
    for exponent in range(order):
        if value == target % prime:
            return exponent
        value = value * generator % prime
    raise ValueError(f"target {target} is outside the registered subgroup for p={prime}")


def compatibility_index(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    u1, v1, n1 = left
    u2, v2, n2 = right
    columns = ((u1, u2), (v1, v2), (n1, 0), (0, n2))
    determinants = []
    for first in range(len(columns)):
        for second in range(first + 1, len(columns)):
            a = columns[first]
            b = columns[second]
            determinants.append(abs(a[0] * b[1] - a[1] * b[0]))
    return math.gcd(*determinants)


def load_graph(source: pathlib.Path) -> tuple[list[int], list[tuple[int, int]]]:
    if git_value(source, "HEAD") != CAMPAIGN_COMMIT:
        raise ValueError("campaign source commit drifted")
    if git_value(source, "HEAD^{tree}") != CAMPAIGN_TREE:
        raise ValueError("campaign source tree drifted")
    pool_raw = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_raw) != POOL_ROOT:
        raise ValueError("prime pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_raw).items()}
    tiles = []
    for prime, order in sorted(pool.items(), key=lambda item: (item[1], item[0])):
        if 55440 % order:
            continue
        primitive = primitive_root_prime(prime)
        generator = pow(primitive, (prime - 1) // order, prime)
        u = subgroup_log(prime, generator, order, 2)
        v = subgroup_log(prime, generator, order, 3)
        if math.gcd(math.gcd(u, v), order) != 1:
            raise ValueError(f"derived a non-primitive coordinate map for p={prime}")
        tiles.append((prime, order, u, v))
    edges = []
    for first, left in enumerate(tiles):
        for right in tiles[first + 1 :]:
            if compatibility_index(
                (left[2], left[3], left[1]), (right[2], right[3], right[1])
            ) == 1:
                edges.append((left[0], right[0]))
    return [tile[0] for tile in tiles], edges


def verify_orientations(
    vertices: list[int],
    edges: list[tuple[int, int]],
    certificates: list[dict[str, Any]],
) -> None:
    by_root = {row.get("excluded_prime"): row for row in certificates}
    if set(by_root) != set(vertices) or len(certificates) != len(vertices):
        raise ValueError("root-excluding certificate set is incomplete or duplicated")
    for excluded in vertices:
        allocations = by_root[excluded].get("left_endpoint_units")
        if not isinstance(allocations, list) or len(allocations) != len(edges):
            raise ValueError(f"orientation length differs for p={excluded}")
        inflow = {prime: 0 for prime in vertices}
        for (left, right), left_units in zip(edges, allocations, strict=True):
            if type(left_units) is not int or not 0 <= left_units <= 6:
                raise ValueError(f"invalid edge allocation for p={excluded}")
            inflow[left] += left_units
            inflow[right] += 6 - left_units
        expected = {
            prime: 0 if prime == excluded else 91 for prime in vertices
        }
        if inflow != expected:
            raise ValueError(f"orientation capacity certificate fails for p={excluded}")


def verify(
    frontier: pathlib.Path, source: pathlib.Path, artifact: pathlib.Path
) -> dict[str, Any]:
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

    input_path = frontier / "artifacts/analyses/erdos203-55440-overlap-obstruction.v1.json"
    if root(input_path.read_bytes()) != INPUT_ROOT:
        raise ValueError("registered 55440 input root drifted")
    raw = artifact.read_bytes()
    value = json.loads(raw)
    if raw != canonical_bytes(value) or value.get("schema") != SCHEMA:
        raise ValueError("graph-local artifact is not canonical or has the wrong schema")
    if value.get("target") != TARGET or value.get("claim_credit") is not False:
        raise ValueError("graph-local artifact crosses its Target or credit boundary")
    if value.get("inputs") != {
        "artifact_path": "artifacts/analyses/erdos203-55440-overlap-obstruction.v1.json",
        "artifact_root": INPUT_ROOT,
        "preregistration": PREREGISTRATION,
    }:
        raise ValueError("graph-local artifact inputs drifted")

    vertices, edges = load_graph(source)
    graph = value.get("graph", {})
    if graph != {
        "vertices": vertices,
        "edges": [list(edge) for edge in edges],
        "vertex_count": 55,
        "edge_count": 819,
    }:
        raise ValueError("graph-local artifact graph differs from source reconstruction")
    certificate = value.get("certificate", {})
    if certificate.get("edge_units") != 6 or certificate.get("non_root_capacity") != 91:
        raise ValueError("graph-local certificate scale drifted")
    verify_orientations(
        vertices, edges, certificate.get("root_excluding_orientations", [])
    )
    ratio = Fraction(len(edges), len(vertices) - 1)
    if ratio != Fraction(91, 6):
        raise ValueError("full mandatory graph no longer attains 91/6")
    if certificate.get("exact_edge_to_excess_ratio") != str(ratio):
        raise ValueError("reported exact graph-local ratio differs")
    fixed_pair_mass = Fraction(94093787, 204906240)
    slack = Fraction(3013, 18480)
    upper_bound = ratio * slack
    gap = fixed_pair_mass - upper_bound
    expected_comparison = {
        "registered_degree_sequence_ratio": "551/33",
        "exact_graph_local_ratio": "91/6",
        "density_slack": str(slack),
        "fixed_pair_mass": str(fixed_pair_mass),
        "cover_pair_mass_upper_bound": str(upper_bound),
        "contradiction_gap": str(gap),
    }
    if value.get("comparison") != expected_comparison:
        raise ValueError("reported graph-local comparison differs")
    if value.get("conclusion", {}).get("result") != "no_conclusion" or gap >= 0:
        raise ValueError("graph-local conclusion differs")
    return {
        "schema": "erdos-frontier.erdos-203-55440-graph-local-bound-check.v1",
        "ok": True,
        "accepted_state_change": "none",
        "artifact_root": root(raw),
        "vertices": len(vertices),
        "edges": len(edges),
        "root_excluding_orientations": len(vertices),
        "exact_graph_local_ratio": str(ratio),
        "registered_degree_sequence_ratio": "551/33",
        "cover_pair_mass_upper_bound": str(upper_bound),
        "fixed_pair_mass": str(fixed_pair_mass),
        "contradiction_gap": str(gap),
        "result": "no_conclusion",
        "implementation_independence": {
            "imports_producer_code": False,
            "uses_sympy": False,
            "graph_source": "bounded direct subgroup enumeration from the pinned pool",
            "certificate_check": "direct endpoint-capacity accounting",
        },
        "shared_dependencies": [
            "Same human operator and machine as the producer workflow.",
            "Same pinned source, Python runtime, and integer-arithmetic assumptions.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier", required=True, type=pathlib.Path)
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = verify(
            args.frontier.resolve(),
            args.campaign_source.resolve(),
            args.artifact.resolve(),
        )
        raw = canonical_bytes(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

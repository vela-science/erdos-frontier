#!/usr/bin/env python3
"""Independently verify the extended Erdős 203 forest obstruction."""

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
TARGET = "erdos:203:finite-cover"
SCHEMA = "erdos-frontier.erdos-203-extended-forest-obstruction.v1"
PREREGISTRATION = "execution/erdos-203-cover/extended-forest-preregistration.v1.json"
PRODUCER = "execution/erdos-203-cover/extended_forest_obstruction.py"


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
            a, b = columns[first], columns[second]
            determinants.append(abs(a[0] * b[1] - a[1] * b[0]))
    return math.gcd(*determinants)


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
    if git_value(source, "HEAD") != CAMPAIGN_COMMIT:
        raise ValueError("campaign source commit drifted")
    if git_value(source, "HEAD^{tree}") != CAMPAIGN_TREE:
        raise ValueError("campaign source tree drifted")
    pool_raw = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_raw) != POOL_ROOT:
        raise ValueError("prime pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_raw).items()}

    raw = artifact.read_bytes()
    value = json.loads(raw)
    if raw != canonical_bytes(value) or value.get("schema") != SCHEMA:
        raise ValueError("extended forest artifact is not canonical or has the wrong schema")
    if value.get("target") != TARGET or value.get("claim_credit") is not False:
        raise ValueError("extended forest artifact crosses its Target or credit boundary")
    if value.get("inputs") != {"preregistration": PREREGISTRATION}:
        raise ValueError("extended forest artifact inputs drifted")

    certificate = value.get("certificate", {})
    tile_rows = certificate.get("tiles", [])
    if len(tile_rows) != 188 or certificate.get("tile_count") != 188:
        raise ValueError("extended certificate has the wrong tile count")
    primes = [row.get("prime") for row in tile_rows]
    if len(set(primes)) != len(primes):
        raise ValueError("extended certificate repeats a tile")
    coordinates = {}
    for row in tile_rows:
        prime, order = row.get("prime"), row.get("order")
        if type(prime) is not int or type(order) is not int or pool.get(prime) != order:
            raise ValueError("extended certificate tile differs from the pinned pool")
        primitive = primitive_root_prime(prime)
        generator = pow(primitive, (prime - 1) // order, prime)
        u = subgroup_log(prime, generator, order, 2)
        v = subgroup_log(prime, generator, order, 3)
        if math.gcd(math.gcd(u, v), order) != 1:
            raise ValueError(f"derived a non-primitive coordinate map for p={prime}")
        coordinates[prime] = (u, v, order)

    tree_edges = certificate.get("tree_edges", [])
    if len(tree_edges) != 187 or certificate.get("edge_count") != 187:
        raise ValueError("extended certificate has the wrong tree edge count")
    components = DisjointSet(primes)
    seen = set()
    tree_mass = Fraction()
    for edge in tree_edges:
        endpoint_list = edge.get("primes", [])
        if len(endpoint_list) != 2 or any(prime not in coordinates for prime in endpoint_list):
            raise ValueError("extended tree edge has an unknown endpoint")
        left, right = endpoint_list
        key = frozenset((left, right))
        if len(key) != 2 or key in seen:
            raise ValueError("extended tree edge is a loop or duplicate")
        seen.add(key)
        if compatibility_index(coordinates[left], coordinates[right]) != 1:
            raise ValueError("extended tree edge is not mandatory")
        expected_orders = [coordinates[left][2], coordinates[right][2]]
        expected_mass = Fraction(1, expected_orders[0] * expected_orders[1])
        if edge.get("orders") != expected_orders:
            raise ValueError("extended tree edge order pair differs")
        if edge.get("intersection_density") != str(expected_mass):
            raise ValueError("extended tree edge mass differs")
        if not components.join(left, right):
            raise ValueError("extended tree contains a cycle")
        tree_mass += expected_mass
    if len({components.find(prime) for prime in primes}) != 1:
        raise ValueError("extended tree is not spanning")

    density = sum((Fraction(1, pool[prime]) for prime in primes), Fraction())
    slack = density - 1
    gap = tree_mass - slack
    expected = preregistration.get("observed_candidate", {})
    if expected != {
        "tile_count": 188,
        "tree_edges": 187,
        "density": str(density),
        "tree_mass": str(tree_mass),
        "contradiction_gap": str(gap),
    }:
        raise ValueError("extended exact values differ from the frozen candidate")
    if certificate.get("density") != str(density):
        raise ValueError("reported extended density differs")
    if certificate.get("density_slack") != str(slack):
        raise ValueError("reported extended density slack differs")
    if certificate.get("tree_mass") != str(tree_mass):
        raise ValueError("reported extended tree mass differs")
    if certificate.get("contradiction_gap") != str(gap) or gap <= 0:
        raise ValueError("extended tree does not strictly exceed density slack")
    if value.get("conclusion", {}).get("result") != "no_cover_selected_family":
        raise ValueError("extended forest conclusion differs")
    return {
        "schema": "erdos-frontier.erdos-203-extended-forest-obstruction-check.v1",
        "ok": True,
        "accepted_state_change": "none",
        "artifact_root": root(raw),
        "pool_root": POOL_ROOT,
        "pool_tiles": len(pool),
        "certificate_tiles": len(primes),
        "tree_edges": len(tree_edges),
        "density": str(density),
        "density_slack": str(slack),
        "tree_mass": str(tree_mass),
        "contradiction_gap": str(gap),
        "result": "no_cover_selected_family",
        "implementation_independence": {
            "imports_producer_code": False,
            "uses_sympy": False,
            "coordinate_method": "bounded direct subgroup enumeration",
            "certificate_check": "direct pool membership, compatibility index, tree structure, and exact Fraction summation",
        },
        "shared_dependencies": [
            "Same human operator and machine as the producer workflow.",
            "Same pinned source pool, Python runtime, and integer-arithmetic assumptions.",
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

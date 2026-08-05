#!/usr/bin/env python3
"""Independently verify the frozen 307-tile chordal obstruction."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import pathlib
import subprocess
from fractions import Fraction
from types import ModuleType
from typing import Any

CAMPAIGN_COMMIT = "94fde841ea6ad90437bd66a91953bfeba13dba0f"
CAMPAIGN_TREE = "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a"
POOL_ROOT = "sha256:9a8f179bf6ab509c53144ac679acd8ffe42e66588b1516b0ca3a9f45e18395b3"
BASE_PATH = "artifacts/analyses/erdos203-two-complex-obstruction.v1.json"
BASE_ROOT = "sha256:010f860f416f2fad97ae984c78dc263901127b095eb9f1cfc496dd5f2f678f07"
BASE_VERIFIER_PATH = "execution/erdos-203-cover/verify_two_complex_obstruction.py"
BASE_VERIFIER_ROOT = "sha256:6d29fd16d3591d5f465bbbe864e5db82a2fec929f2e8f85fc66b1545a5cd679a"
PREREGISTRATION_PATH = "execution/erdos-203-chordal/preregistration.v1.json"
PRODUCER_PATH = "execution/erdos-203-chordal/produce.py"
TARGET = "erdos:203:chordal-obstruction"
ARTIFACT_SCHEMA = "erdos-frontier.erdos-203-chordal-obstruction.v1"
CHECK_SCHEMA = "erdos-frontier.erdos-203-chordal-obstruction-check.v1"
PARENT_PRIMES = (31, 47, 71)
NEW_PRIME = 19


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


def coordinate(prime: int, order: int) -> tuple[int, int, int]:
    generator = pow(primitive_root_prime(prime), (prime - 1) // order, prime)
    return (
        subgroup_log(prime, generator, order, 2),
        subgroup_log(prime, generator, order, 3),
        order,
    )


def determinant(matrix: list[list[int]]) -> int:
    size = len(matrix)
    total = 0
    for permutation in itertools.permutations(range(size)):
        inversions = sum(
            permutation[left] > permutation[right]
            for left in range(size)
            for right in range(left + 1, size)
        )
        term = math.prod(matrix[row][permutation[row]] for row in range(size))
        total += -term if inversions % 2 else term
    return total


def intersection_index(rows: tuple[tuple[int, int, int], ...]) -> int:
    size = len(rows)
    columns = [
        tuple(row[0] for row in rows),
        tuple(row[1] for row in rows),
    ]
    columns.extend(
        tuple(row[2] if row_index == column_index else 0 for row_index, row in enumerate(rows))
        for column_index in range(size)
    )
    minors = []
    for selected in itertools.combinations(range(size + 2), size):
        matrix = [[columns[column][row] for column in selected] for row in range(size)]
        minors.append(abs(determinant(matrix)))
    return math.gcd(*minors)


def load_base_verifier(path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("erdos203_frozen_base_verifier", path)
    if spec is None or spec.loader is None:
        raise ValueError("could not load the frozen base verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(
    frontier: pathlib.Path,
    source: pathlib.Path,
    artifact_path: pathlib.Path,
) -> dict[str, Any]:
    if git_value(source, "HEAD") != CAMPAIGN_COMMIT:
        raise ValueError("campaign source commit drifted")
    if git_value(source, "HEAD^{tree}") != CAMPAIGN_TREE:
        raise ValueError("campaign source tree drifted")
    pool_raw = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_raw) != POOL_ROOT:
        raise ValueError("prime pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_raw).items()}

    preregistration_raw = (frontier / PREREGISTRATION_PATH).read_bytes()
    preregistration = json.loads(preregistration_raw)
    if preregistration_raw != canonical_bytes(preregistration):
        raise ValueError("preregistration is not canonical JSON")
    if preregistration.get("target") != TARGET or preregistration.get("claim_credit") is not False:
        raise ValueError("preregistration crosses the frozen target boundary")
    producer_raw = (frontier / PRODUCER_PATH).read_bytes()
    if preregistration.get("method", {}).get("producer") != {
        "path": PRODUCER_PATH,
        "sha256": root(producer_raw),
        "size": len(producer_raw),
    }:
        raise ValueError("producer bytes drifted from preregistration")

    base_raw = (frontier / BASE_PATH).read_bytes()
    if root(base_raw) != BASE_ROOT:
        raise ValueError("base 306-tile certificate drifted")
    base_verifier_path = frontier / BASE_VERIFIER_PATH
    base_verifier_raw = base_verifier_path.read_bytes()
    if root(base_verifier_raw) != BASE_VERIFIER_ROOT:
        raise ValueError("base verifier bytes drifted")
    base_check = load_base_verifier(base_verifier_path).verify(
        frontier, source, frontier / BASE_PATH
    )
    if base_check.get("result") != "no_cover_selected_family" or base_check.get("certificate_tiles") != 306:
        raise ValueError("base verifier did not reproduce the frozen bounded exclusion")

    raw = artifact_path.read_bytes()
    value = json.loads(raw)
    if raw != canonical_bytes(value) or value.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError("artifact is not canonical JSON or has the wrong schema")
    if value.get("target") != TARGET or value.get("authority") != "non_authoritative":
        raise ValueError("artifact crosses its target or authority boundary")
    if value.get("claim_credit") is not False:
        raise ValueError("artifact improperly claims discovery credit")
    if value.get("inputs", {}).get("base_certificate", {}).get("sha256") != BASE_ROOT:
        raise ValueError("artifact does not bind the frozen base certificate")
    if value.get("inputs", {}).get("preregistration", {}).get("sha256") != root(preregistration_raw):
        raise ValueError("artifact preregistration root drifted")

    base = json.loads(base_raw)
    base_certificate = base.get("certificate", {})
    base_tiles = {row["prime"]: row["order"] for row in base_certificate.get("tiles", [])}
    if len(base_tiles) != 306 or NEW_PRIME in base_tiles:
        raise ValueError("base certificate exposes the wrong tile boundary")
    base_triangles = {
        frozenset(row["primes"]) for row in base_certificate.get("triangles", [])
    }
    if frozenset(PARENT_PRIMES) not in base_triangles:
        raise ValueError("parent triangle is absent from the verified base complex")

    primes = (*PARENT_PRIMES, NEW_PRIME)
    rows = {prime: coordinate(prime, pool[prime]) for prime in primes}
    expected_coordinates = {
        "prime": NEW_PRIME,
        "order": pool[NEW_PRIME],
        "coordinates": {"u": rows[NEW_PRIME][0], "v": rows[NEW_PRIME][1]},
        "parent_primes": list(PARENT_PRIMES),
        "parent_orders": [pool[prime] for prime in PARENT_PRIMES],
    }
    extension = value.get("extension", {})
    for key, expected in expected_coordinates.items():
        if extension.get(key) != expected:
            raise ValueError(f"extension {key} drifted")

    pair_indices = {
        f"{left},{right}": intersection_index((rows[left], rows[right]))
        for left, right in itertools.combinations(primes, 2)
    }
    triple_indices = {
        ",".join(map(str, triple)): intersection_index(tuple(rows[prime] for prime in triple))
        for triple in itertools.combinations(primes, 3)
    }
    quadruple_index = intersection_index(tuple(rows[prime] for prime in primes))
    if set(pair_indices.values()) != {1} or extension.get("pair_indices") != pair_indices:
        raise ValueError("mandatory pair indices drifted")
    if set(triple_indices.values()) != {1} or extension.get("triple_indices") != triple_indices:
        raise ValueError("mandatory triple indices drifted")
    if quadruple_index != 1 or extension.get("quadruple_index") != 1:
        raise ValueError("mandatory quadruple index drifted")

    parent_orders = tuple(pool[prime] for prime in PARENT_PRIMES)
    new_order = pool[NEW_PRIME]
    density = Fraction(base_certificate["density"]) + Fraction(1, new_order)
    pair_mass = Fraction(base_certificate["pair_mass"]) + sum(
        (Fraction(1, new_order * order) for order in parent_orders), Fraction()
    )
    triple_mass = Fraction(base_certificate["triple_mass"]) + sum(
        (
            Fraction(1, new_order * left * right)
            for left, right in itertools.combinations(parent_orders, 2)
        ),
        Fraction(),
    )
    quadruple_mass = Fraction(1, new_order * math.prod(parent_orders))
    euler_mass = pair_mass - triple_mass + quadruple_mass
    gap = euler_mass - (density - 1)
    extension_cost = Fraction(
        math.prod(order - 1 for order in parent_orders),
        new_order * math.prod(parent_orders),
    )
    observed = {
        "tile_count": 307,
        "edge_count": 612,
        "triangle_count": 307,
        "tetrahedron_count": 1,
        "density": str(density),
        "pair_mass": str(pair_mass),
        "triple_mass": str(triple_mass),
        "quadruple_mass": str(quadruple_mass),
        "euler_mass": str(euler_mass),
        "contradiction_gap": str(gap),
        "extension_cost": str(extension_cost),
    }
    if preregistration.get("observed_candidate") != observed:
        raise ValueError("exact values differ from the frozen candidate")
    certificate = value.get("certificate", {})
    for key, expected in observed.items():
        if certificate.get(key) != expected:
            raise ValueError(f"reported {key} drifted")
    if extension.get("gap_cost") != str(extension_cost):
        raise ValueError("reported extension cost drifted")
    if gap <= 0 or value.get("conclusion", {}).get("result") != "no_cover_selected_family":
        raise ValueError("artifact does not establish its bounded exclusion")
    if value.get("conclusion", {}).get("omitted_primes") != [5, 7, 11, 13, 17, 23]:
        raise ValueError("reported omitted-prime boundary drifted")

    return {
        "schema": CHECK_SCHEMA,
        "ok": True,
        "accepted_state_change": "none",
        "target": TARGET,
        "artifact_root": root(raw),
        "preregistration_root": root(preregistration_raw),
        "base_artifact_root": BASE_ROOT,
        "base_verifier_root": BASE_VERIFIER_ROOT,
        "source_commit": CAMPAIGN_COMMIT,
        "pool_root": POOL_ROOT,
        "pool_tiles": len(pool),
        "certificate_tiles": 307,
        "edges": 612,
        "triangles": 307,
        "tetrahedra": 1,
        "density": str(density),
        "density_slack": str(density - 1),
        "pair_mass": str(pair_mass),
        "triple_mass": str(triple_mass),
        "quadruple_mass": str(quadruple_mass),
        "euler_mass": str(euler_mass),
        "contradiction_gap": str(gap),
        "result": "no_cover_selected_family",
        "implementation_independence": {
            "imports_extension_producer": False,
            "uses_sympy": False,
            "coordinate_method": "bounded direct subgroup enumeration",
            "base_check": "exact rooted dependency-free verifier replay",
            "extension_check": "direct pair, triple, quadruple lattice-index minors and exact Fraction summation",
        },
        "shared_dependencies": [
            "Same human operator and machine as the producer workflow.",
            "Same pinned source pool, Python runtime, base certificate, and integer-arithmetic assumptions.",
        ],
        "nonclaims": value.get("nonclaims"),
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

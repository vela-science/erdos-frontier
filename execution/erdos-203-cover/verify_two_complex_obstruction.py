#!/usr/bin/env python3
"""Independently verify the Erdős 203 mandatory pair/triple 2-tree."""

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
SCHEMA = "erdos-frontier.erdos-203-two-complex-obstruction.v1"
PREREGISTRATION = "execution/erdos-203-cover/two-complex-preregistration.v1.json"
PRODUCER = "execution/erdos-203-cover/two_complex_obstruction.py"
PRIOR_ARTIFACT = "artifacts/analyses/erdos203-extended-forest-obstruction.v1.json"


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


def pair_index(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    u1, v1, n1 = left
    u2, v2, n2 = right
    columns = ((u1, u2), (v1, v2), (n1, 0), (0, n2))
    determinants = []
    for first in range(len(columns)):
        for second in range(first + 1, len(columns)):
            a, b = columns[first], columns[second]
            determinants.append(abs(a[0] * b[1] - a[1] * b[0]))
    return math.gcd(*determinants)


def triple_index(rows: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]) -> int:
    (u1, v1, n1), (u2, v2, n2), (u3, v3, n3) = rows
    minors = (
        n1 * (u2 * v3 - u3 * v2),
        n2 * (u1 * v3 - u3 * v1),
        n3 * (u1 * v2 - u2 * v1),
        n1 * n2 * u3,
        n1 * n3 * u2,
        n2 * n3 * u1,
        n1 * n2 * v3,
        n1 * n3 * v2,
        n2 * n3 * v1,
        n1 * n2 * n3,
    )
    return math.gcd(*(abs(value) for value in minors))


def edge_key(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def verify(frontier: pathlib.Path, source: pathlib.Path, artifact: pathlib.Path) -> dict[str, Any]:
    preregistration_raw = (frontier / PREREGISTRATION).read_bytes()
    preregistration = json.loads(preregistration_raw)
    if preregistration_raw != canonical_bytes(preregistration):
        raise ValueError("preregistration is not canonical JSON")
    producer_raw = (frontier / PRODUCER).read_bytes()
    if preregistration.get("method", {}).get("producer") != {
        "path": PRODUCER,
        "sha256": root(producer_raw),
        "size": len(producer_raw),
    }:
        raise ValueError("producer bytes drifted from preregistration")
    if git_value(source, "HEAD") != CAMPAIGN_COMMIT or git_value(source, "HEAD^{tree}") != CAMPAIGN_TREE:
        raise ValueError("campaign source identity drifted")
    pool_raw = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_raw) != POOL_ROOT:
        raise ValueError("prime pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_raw).items()}

    raw = artifact.read_bytes()
    value = json.loads(raw)
    if raw != canonical_bytes(value) or value.get("schema") != SCHEMA:
        raise ValueError("two-complex artifact is not canonical or has the wrong schema")
    if value.get("target") != TARGET or value.get("authority") != "non_authoritative" or value.get("claim_credit") is not False:
        raise ValueError("two-complex artifact crosses its Target, authority, or credit boundary")
    if value.get("inputs", {}).get("preregistration") != PREREGISTRATION:
        raise ValueError("two-complex preregistration reference drifted")
    prior_raw = (frontier / PRIOR_ARTIFACT).read_bytes()
    if value.get("inputs", {}).get("prior_certificate_root") != root(prior_raw):
        raise ValueError("prior certificate root drifted")

    certificate = value.get("certificate", {})
    tile_rows = certificate.get("tiles", [])
    if len(tile_rows) != 306 or certificate.get("tile_count") != 306:
        raise ValueError("two-complex has the wrong tile count")
    primes = [row.get("prime") for row in tile_rows]
    if len(set(primes)) != len(primes):
        raise ValueError("two-complex repeats a tile")
    coordinates: dict[int, tuple[int, int, int]] = {}
    for row in tile_rows:
        prime, order = row.get("prime"), row.get("order")
        if type(prime) is not int or type(order) is not int or pool.get(prime) != order:
            raise ValueError("two-complex tile differs from the pinned pool")
        primitive = primitive_root_prime(prime)
        generator = pow(primitive, (prime - 1) // order, prime)
        u = subgroup_log(prime, generator, order, 2)
        v = subgroup_log(prime, generator, order, 3)
        if math.gcd(math.gcd(u, v), order) != 1:
            raise ValueError(f"derived a non-primitive coordinate map for p={prime}")
        coordinates[prime] = (u, v, order)

    seed_primes = value.get("selection", {}).get("seed_primes")
    if seed_primes != [47, 211, 6073] or any(prime not in coordinates for prime in seed_primes):
        raise ValueError("two-complex seed drifted")
    if triple_index(tuple(coordinates[prime] for prime in seed_primes)) != 1:
        raise ValueError("seed triple is not mandatory")
    constructed_vertices = set(seed_primes)
    constructed_edges = {
        edge_key(seed_primes[0], seed_primes[1]),
        edge_key(seed_primes[0], seed_primes[2]),
        edge_key(seed_primes[1], seed_primes[2]),
    }
    constructed_triangles = [tuple(seed_primes)]
    for attachment in value.get("selection", {}).get("attachments", []):
        prime = attachment.get("prime")
        parents = attachment.get("parent_primes", [])
        if prime in constructed_vertices or prime not in coordinates or len(parents) != 2:
            raise ValueError("invalid two-complex attachment vertex")
        parent_edge = edge_key(parents[0], parents[1])
        if parent_edge not in constructed_edges:
            raise ValueError("attachment parent edge was not already present")
        if triple_index((coordinates[parents[0]], coordinates[parents[1]], coordinates[prime])) != 1:
            raise ValueError("attachment triangle is not mandatory")
        expected_cost = Fraction(
            (coordinates[parents[0]][2] - 1) * (coordinates[parents[1]][2] - 1),
            coordinates[parents[0]][2] * coordinates[parents[1]][2] * coordinates[prime][2],
        )
        if attachment.get("gap_cost") != str(expected_cost):
            raise ValueError("attachment gap cost drifted")
        constructed_vertices.add(prime)
        constructed_edges.add(edge_key(parents[0], prime))
        constructed_edges.add(edge_key(parents[1], prime))
        constructed_triangles.append((parents[0], parents[1], prime))
    if constructed_vertices != set(primes):
        raise ValueError("attachment order does not construct the reported tiles")

    edge_rows = certificate.get("edges", [])
    reported_edges = {edge_key(*row.get("primes", [])) for row in edge_rows if len(row.get("primes", [])) == 2}
    if len(edge_rows) != 609 or certificate.get("edge_count") != 609 or reported_edges != constructed_edges:
        raise ValueError("reported two-complex edge set drifted")
    pair_mass = Fraction()
    for row in edge_rows:
        left, right = row["primes"]
        if pair_index(coordinates[left], coordinates[right]) != 1:
            raise ValueError("reported edge is not a mandatory pair")
        orders = [coordinates[left][2], coordinates[right][2]]
        if row.get("orders") != orders:
            raise ValueError("reported edge orders drifted")
        pair_mass += Fraction(1, orders[0] * orders[1])

    triangle_rows = certificate.get("triangles", [])
    reported_triangles = {frozenset(row.get("primes", [])) for row in triangle_rows}
    expected_triangles = {frozenset(row) for row in constructed_triangles}
    if len(triangle_rows) != 304 or certificate.get("triangle_count") != 304 or reported_triangles != expected_triangles:
        raise ValueError("reported two-complex triangle set drifted")
    triple_mass = Fraction()
    for row in triangle_rows:
        triangle = row["primes"]
        if len(triangle) != 3 or triple_index(tuple(coordinates[prime] for prime in triangle)) != 1:
            raise ValueError("reported triangle is not mandatory")
        orders = [coordinates[prime][2] for prime in triangle]
        if row.get("orders") != orders:
            raise ValueError("reported triangle orders drifted")
        triple_mass += Fraction(1, math.prod(orders))

    density = sum((Fraction(1, pool[prime]) for prime in primes), Fraction())
    slack = density - 1
    euler_mass = pair_mass - triple_mass
    gap = euler_mass - slack
    expected = preregistration.get("observed_candidate", {})
    if expected != {
        "tile_count": 306,
        "edge_count": 609,
        "triangle_count": 304,
        "density": str(density),
        "pair_mass": str(pair_mass),
        "triple_mass": str(triple_mass),
        "euler_mass": str(euler_mass),
        "contradiction_gap": str(gap),
    }:
        raise ValueError("two-complex exact values differ from the frozen candidate")
    for key, exact in (
        ("density", density),
        ("density_slack", slack),
        ("pair_mass", pair_mass),
        ("triple_mass", triple_mass),
        ("euler_mass", euler_mass),
        ("contradiction_gap", gap),
    ):
        if certificate.get(key) != str(exact):
            raise ValueError(f"reported {key} drifted")
    if gap <= 0 or value.get("conclusion", {}).get("result") != "no_cover_selected_family":
        raise ValueError("two-complex does not establish its bounded exclusion")

    prior = json.loads(prior_raw)
    prior_primes = {row["prime"] for row in prior["certificate"]["tiles"]}
    prior_complement = set(pool) - prior_primes
    if not prior_complement <= set(primes):
        raise ValueError("two-complex does not include all 125 prior-complement tiles")
    if value.get("selection", {}).get("prior_188_tiles_retained") != len(prior_primes & set(primes)):
        raise ValueError("prior-certificate overlap count drifted")
    if value.get("selection", {}).get("prior_125_complement_retained") != 125:
        raise ValueError("prior-complement coverage count drifted")

    return {
        "schema": "erdos-frontier.erdos-203-two-complex-obstruction-check.v1",
        "ok": True,
        "accepted_state_change": "none",
        "artifact_root": root(raw),
        "pool_root": POOL_ROOT,
        "pool_tiles": len(pool),
        "certificate_tiles": len(primes),
        "prior_125_complement_tiles_included": len(prior_complement & set(primes)),
        "edges": len(edge_rows),
        "triangles": len(triangle_rows),
        "density": str(density),
        "density_slack": str(slack),
        "pair_mass": str(pair_mass),
        "triple_mass": str(triple_mass),
        "euler_mass": str(euler_mass),
        "contradiction_gap": str(gap),
        "result": "no_cover_selected_family",
        "implementation_independence": {
            "imports_producer_code": False,
            "uses_sympy": False,
            "coordinate_method": "bounded direct subgroup enumeration",
            "certificate_check": "direct pool membership, pair and triple surjectivity, 2-tree construction, prior-complement coverage, and exact Fraction summation",
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
            args.frontier.resolve(), args.campaign_source.resolve(), args.artifact.resolve()
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

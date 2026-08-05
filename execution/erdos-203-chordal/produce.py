#!/usr/bin/env python3
"""Build the frozen 307-tile chordal-complex obstruction for Erdős 203."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import pathlib
import subprocess
from fractions import Fraction
from typing import Any

from sympy import discrete_log, primitive_root

CAMPAIGN_COMMIT = "94fde841ea6ad90437bd66a91953bfeba13dba0f"
CAMPAIGN_TREE = "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a"
POOL_ROOT = "sha256:9a8f179bf6ab509c53144ac679acd8ffe42e66588b1516b0ca3a9f45e18395b3"
BASE_PATH = "artifacts/analyses/erdos203-two-complex-obstruction.v1.json"
BASE_ROOT = "sha256:010f860f416f2fad97ae984c78dc263901127b095eb9f1cfc496dd5f2f678f07"
TARGET = "erdos:203:chordal-obstruction"
SCHEMA = "erdos-frontier.erdos-203-chordal-obstruction.v1"
PARENT_PRIMES = (31, 47, 71)
NEW_PRIME = 19


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )


def root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def git_value(source: pathlib.Path, expression: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", expression], text=True
    ).strip()


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


def coordinate(prime: int, order: int) -> tuple[int, int, int]:
    generator = pow(int(primitive_root(prime)), (prime - 1) // order, prime)
    return (
        int(discrete_log(prime, 2, generator)) % order,
        int(discrete_log(prime, 3, generator)) % order,
        order,
    )


def build(
    frontier: pathlib.Path,
    source: pathlib.Path,
    preregistration_path: pathlib.Path,
) -> dict[str, Any]:
    if git_value(source, "HEAD") != CAMPAIGN_COMMIT:
        raise ValueError("campaign source commit drifted")
    if git_value(source, "HEAD^{tree}") != CAMPAIGN_TREE:
        raise ValueError("campaign source tree drifted")
    pool_raw = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_raw) != POOL_ROOT:
        raise ValueError("prime pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_raw).items()}

    base_raw = (frontier / BASE_PATH).read_bytes()
    if root(base_raw) != BASE_ROOT:
        raise ValueError("base 306-tile certificate drifted")
    base = json.loads(base_raw)
    base_certificate = base.get("certificate") or {}
    base_tiles = {row["prime"]: row["order"] for row in base_certificate.get("tiles", [])}
    if len(base_tiles) != 306 or NEW_PRIME in base_tiles:
        raise ValueError("base certificate does not expose the frozen 306-tile boundary")
    if any(base_tiles.get(prime) != pool.get(prime) for prime in PARENT_PRIMES):
        raise ValueError("frozen parent triangle is absent from the base certificate")
    base_triangles = {
        frozenset(row["primes"]) for row in base_certificate.get("triangles", [])
    }
    if frozenset(PARENT_PRIMES) not in base_triangles:
        raise ValueError("frozen parent triangle is not a base face")

    preregistration_raw = preregistration_path.read_bytes()
    preregistration = json.loads(preregistration_raw)
    if preregistration.get("target") != TARGET or preregistration.get("claim_credit") is not False:
        raise ValueError("preregistration crosses the frozen target boundary")

    primes = (*PARENT_PRIMES, NEW_PRIME)
    rows = {prime: coordinate(prime, pool[prime]) for prime in primes}
    pair_indices = {
        f"{left},{right}": intersection_index((rows[left], rows[right]))
        for left, right in itertools.combinations(primes, 2)
    }
    triple_indices = {
        ",".join(map(str, triple)): intersection_index(tuple(rows[prime] for prime in triple))
        for triple in itertools.combinations(primes, 3)
    }
    quadruple_index = intersection_index(tuple(rows[prime] for prime in primes))
    if set(pair_indices.values()) != {1} or set(triple_indices.values()) != {1} or quadruple_index != 1:
        raise ValueError("frozen tetrahedron is not a mandatory intersection simplex")

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
    gap_cost = Fraction(math.prod(order - 1 for order in parent_orders), new_order * math.prod(parent_orders))
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
        "extension_cost": str(gap_cost),
    }
    if preregistration.get("observed_candidate") != observed or gap <= 0:
        raise ValueError("candidate differs from the frozen preregistration")

    return {
        "schema": SCHEMA,
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": {
            "commit": CAMPAIGN_COMMIT,
            "tree": CAMPAIGN_TREE,
            "pool_root": POOL_ROOT,
            "pool_tiles": len(pool),
        },
        "inputs": {
            "preregistration": {
                "path": preregistration_path.relative_to(frontier).as_posix(),
                "sha256": root(preregistration_raw),
            },
            "base_certificate": {
                "path": BASE_PATH,
                "sha256": BASE_ROOT,
                "tile_count": 306,
                "edge_count": 609,
                "triangle_count": 304,
            },
        },
        "extension": {
            "prime": NEW_PRIME,
            "order": new_order,
            "coordinates": {"u": rows[NEW_PRIME][0], "v": rows[NEW_PRIME][1]},
            "parent_primes": list(PARENT_PRIMES),
            "parent_orders": list(parent_orders),
            "pair_indices": pair_indices,
            "triple_indices": triple_indices,
            "quadruple_index": quadruple_index,
            "gap_cost": str(gap_cost),
        },
        "certificate": {
            "kind": "mandatory_pair_triple_quadruple_chordal_complex",
            **observed,
            "density_slack": str(density - 1),
            "pointwise_bound": "For every nonempty set S of selected tiles, |E(S)|-|T(S)|+|Q(S)| <= |S|-1; reverse-eliminate tile 19, then the base 2-tree.",
        },
        "conclusion": {
            "result": "no_cover_selected_family",
            "scope": "No choice of one affine shift for each of these 307 pinned certificate tiles covers Z^2.",
            "proof": "Fixed mandatory pair mass minus triple mass plus quadruple mass exceeds density slack, while the chordal-complex pointwise bound makes that impossible under a cover.",
            "omitted_primes": [5, 7, 11, 13, 17, 23],
        },
        "nonclaims": [
            "This post-exploratory qualification has claim_credit false and is not an unbiased discovery episode.",
            "The certificate omits six pinned tiles and does not exclude the full 313-tile pool.",
            "This does not resolve Erdős problem 203 globally or establish mathematical novelty.",
            "A producer artifact or passing checker is not Vela Standing or human acceptance.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier", required=True, type=pathlib.Path)
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--preregistration", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        value = build(
            args.frontier.resolve(),
            args.campaign_source.resolve(),
            args.preregistration.resolve(),
        )
        raw = canonical_bytes(value)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps({
        "ok": True,
        "artifact_root": root(raw),
        "tile_count": value["certificate"]["tile_count"],
        "contradiction_gap": value["certificate"]["contradiction_gap"],
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Independently check the bounded n-divides-10080 overlap obstruction."""

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
PERIOD = 10080
SCHEMA = "erdos-frontier.erdos-203-overlap-obstruction.v1"
PREREGISTRATION = "execution/erdos-203-cover/overlap-10080-preregistration.v1.json"
PRODUCER = "execution/erdos-203-cover/overlap_obstruction.py"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def canonical_utf8_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .encode()
        + b"\n"
    )


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


def load_tiles(source: pathlib.Path) -> list[dict[str, int]]:
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
        if PERIOD % order:
            continue
        primitive = primitive_root_prime(prime)
        generator = pow(primitive, (prime - 1) // order, prime)
        u = subgroup_log(prime, generator, order, 2)
        v = subgroup_log(prime, generator, order, 3)
        if math.gcd(math.gcd(u, v), order) != 1:
            raise ValueError(f"derived a non-primitive coordinate map for p={prime}")
        tiles.append({"p": prime, "n": order, "u": u, "v": v})
    return tiles


def recompute(tiles: list[dict[str, int]]) -> dict[str, Any]:
    density = sum((Fraction(1, tile["n"]) for tile in tiles), Fraction())
    degrees = [0 for _ in tiles]
    pairs = []
    pair_mass = Fraction()
    checked_pairs = 0
    for first, left in enumerate(tiles):
        for second in range(first + 1, len(tiles)):
            right = tiles[second]
            checked_pairs += 1
            index = compatibility_index(
                (left["u"], left["v"], left["n"]),
                (right["u"], right["v"], right["n"]),
            )
            if index != 1:
                continue
            mass = Fraction(1, left["n"] * right["n"])
            degrees[first] += 1
            degrees[second] += 1
            pair_mass += mass
            pairs.append(
                {
                    "primes": [left["p"], right["p"]],
                    "orders": [left["n"], right["n"]],
                    "intersection_density": str(mass),
                }
            )
    ordered_degrees = sorted(degrees, reverse=True)
    bounds = []
    for selected in range(2, len(tiles) + 1):
        complete = selected * (selected - 1) // 2
        degree_bound = sum(ordered_degrees[:selected]) // 2
        edge_bound = min(complete, degree_bound, len(pairs))
        bounds.append(
            {
                "selected_tiles": selected,
                "complete_graph_bound": complete,
                "degree_sequence_bound": degree_bound,
                "mandatory_edges_upper_bound": edge_bound,
                "edge_to_excess_ratio": str(Fraction(edge_bound, selected - 1)),
            }
        )
    ratio = max(Fraction(row["edge_to_excess_ratio"]) for row in bounds)
    slack = density - 1
    upper_bound = ratio * slack
    return {
        "family": {
            "tiles": len(tiles),
            "density": str(density),
            "density_slack": str(slack),
            "members": [
                {"prime": tile["p"], "order": tile["n"]} for tile in tiles
            ],
        },
        "mandatory_overlap": {
            "pairs_checked": checked_pairs,
            "edges": len(pairs),
            "pairs": pairs,
            "degree_sequence": ordered_degrees,
            "fixed_pair_mass": str(pair_mass),
            "pointwise_bounds": bounds,
            "pointwise_ratio": str(ratio),
            "cover_pair_mass_upper_bound": str(upper_bound),
            "contradiction_gap": str(pair_mass - upper_bound),
        },
    }


def verify(
    frontier: pathlib.Path, source: pathlib.Path, artifact: pathlib.Path
) -> dict[str, Any]:
    preregistration_raw = (frontier / PREREGISTRATION).read_bytes()
    preregistration = json.loads(preregistration_raw)
    if preregistration_raw != canonical_utf8_bytes(preregistration):
        raise ValueError("preregistration is not canonical JSON")
    producer_raw = (frontier / PRODUCER).read_bytes()
    registered_script = preregistration.get("method", {}).get("script", {})
    if registered_script.get("sha256") != root(producer_raw):
        raise ValueError("producer script root drifted from preregistration")
    if registered_script.get("size") != len(producer_raw):
        raise ValueError("producer script size drifted from preregistration")

    raw = artifact.read_bytes()
    value = json.loads(raw)
    if raw != canonical_bytes(value) or value.get("schema") != SCHEMA:
        raise ValueError("obstruction artifact is not canonical or has the wrong schema")
    actual = recompute(load_tiles(source))
    if value.get("family") != actual["family"]:
        raise ValueError("artifact family does not match independent reconstruction")
    if value.get("mandatory_overlap") != actual["mandatory_overlap"]:
        raise ValueError("artifact overlap ledger does not match independent reconstruction")
    expected = {
        "tiles": 33,
        "density": "743/720",
        "density_slack": "23/720",
        "pairs_checked": 528,
        "edges": 307,
        "fixed_pair_mass": "11477773/33868800",
        "pointwise_ratio": "209/20",
        "cover_pair_mass_upper_bound": "4807/14400",
        "contradiction_gap": "171709/33868800",
    }
    summary = {
        "tiles": actual["family"]["tiles"],
        "density": actual["family"]["density"],
        "density_slack": actual["family"]["density_slack"],
        **{
            field: actual["mandatory_overlap"][field]
            for field in (
                "pairs_checked",
                "edges",
                "fixed_pair_mass",
                "pointwise_ratio",
                "cover_pair_mass_upper_bound",
                "contradiction_gap",
            )
        },
    }
    if summary != expected:
        raise ValueError(f"registered exact values do not reproduce: {summary}")
    if value.get("conclusion") != {
        "result": "no_cover_selected_family",
        "scope": "No choice of one affine shift for each of these 33 tiles covers Z^2.",
    }:
        raise ValueError("artifact conclusion exceeds or loses the exact bounded result")
    if Fraction(summary["contradiction_gap"]) <= 0:
        raise ValueError("registered contradiction gap is not positive")
    return {
        "schema": "erdos-frontier.erdos-203-10080-overlap-obstruction-check.v1",
        "ok": True,
        "artifact_root": root(raw),
        **summary,
        "implementation_independence": {
            "imports_producer_code": False,
            "uses_sympy": False,
            "discrete_log_method": "bounded direct subgroup enumeration",
        },
        "shared_dependencies": [
            "Same human operator and machine as the producer workflow.",
            "Same pinned source commit, pool bytes, Python runtime, and integer arithmetic assumptions.",
        ],
        "accepted_state_change": "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier", required=True, type=pathlib.Path)
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(
            args.frontier.resolve(),
            args.campaign_source.resolve(),
            args.artifact.resolve(),
        )
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        result = {
            "schema": "erdos-frontier.erdos-203-10080-overlap-obstruction-check.v1",
            "ok": False,
            "error": str(error),
            "accepted_state_change": "none",
        }
    print(json.dumps(result, sort_keys=True) if args.json else result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

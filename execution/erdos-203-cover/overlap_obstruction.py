#!/usr/bin/env python3
"""Test one pinned n-divides-period family by exact mandatory-overlap mass."""

from __future__ import annotations

import argparse
import hashlib
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
TARGET = "erdos:203:finite-cover"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def git_value(source: pathlib.Path, expression: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", expression], text=True
    ).strip()


def compatibility_index(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    u1, v1, n1 = left
    u2, v2, n2 = right
    columns = [(u1, u2), (v1, v2), (n1, 0), (0, n2)]
    determinants = (
        abs(a[0] * b[1] - a[1] * b[0])
        for index, a in enumerate(columns)
        for b in columns[index + 1 :]
    )
    return math.gcd(*determinants)


def load_tiles(source: pathlib.Path, period: int) -> list[dict[str, int]]:
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
        if period % order:
            continue
        generator = pow(int(primitive_root(prime)), (prime - 1) // order, prime)
        u = int(discrete_log(prime, 2, generator)) % order
        v = int(discrete_log(prime, 3, generator)) % order
        if math.gcd(math.gcd(u, v), order) != 1:
            raise ValueError(f"derived a non-primitive coordinate map for p={prime}")
        tiles.append({"p": prime, "n": order, "u": u, "v": v})
    return tiles


def pointwise_bounds(degrees: list[int], edges: int) -> list[dict[str, Any]]:
    ordered_degrees = sorted(degrees, reverse=True)
    rows = []
    for selected in range(2, len(degrees) + 1):
        complete = selected * (selected - 1) // 2
        degree_sequence = sum(ordered_degrees[:selected]) // 2
        edge_bound = min(complete, degree_sequence, edges)
        rows.append(
            {
                "selected_tiles": selected,
                "complete_graph_bound": complete,
                "degree_sequence_bound": degree_sequence,
                "mandatory_edges_upper_bound": edge_bound,
                "edge_to_excess_ratio": str(Fraction(edge_bound, selected - 1)),
            }
        )
    return rows


def build(source: pathlib.Path, period: int, preregistration: str) -> dict[str, Any]:
    tiles = load_tiles(source, period)
    density = sum((Fraction(1, tile["n"]) for tile in tiles), Fraction())
    slack = density - 1
    degrees = [0 for _ in tiles]
    mandatory_pairs = []
    pair_mass = Fraction()
    checked_pairs = 0
    for first, left in enumerate(tiles):
        left_tuple = (left["u"], left["v"], left["n"])
        for second in range(first + 1, len(tiles)):
            right = tiles[second]
            right_tuple = (right["u"], right["v"], right["n"])
            checked_pairs += 1
            if compatibility_index(left_tuple, right_tuple) != 1:
                continue
            mass = Fraction(1, left["n"] * right["n"])
            pair_mass += mass
            degrees[first] += 1
            degrees[second] += 1
            mandatory_pairs.append(
                {
                    "primes": [left["p"], right["p"]],
                    "orders": [left["n"], right["n"]],
                    "intersection_density": str(mass),
                }
            )
    bounds = pointwise_bounds(degrees, len(mandatory_pairs))
    pointwise_ratio = max(
        Fraction(row["edge_to_excess_ratio"]) for row in bounds
    )
    cover_upper_bound = pointwise_ratio * slack
    gap = pair_mass - cover_upper_bound
    excludes_family = density >= 1 and gap > 0
    result = "no_cover_selected_family" if excludes_family else "no_conclusion"
    scope = (
        f"No choice of one affine shift for each of these {len(tiles)} tiles covers Z^2."
        if excludes_family
        else "The registered mandatory-overlap inequality does not decide this family."
    )
    return {
        "schema": "erdos-frontier.erdos-203-overlap-obstruction.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": {
            "commit": CAMPAIGN_COMMIT,
            "tree": CAMPAIGN_TREE,
            "pool_root": POOL_ROOT,
        },
        "inputs": {
            "period": period,
            "selection": "Every retained prime tile whose exact subgroup order n divides the period.",
            "preregistration": preregistration,
        },
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
            "edges": len(mandatory_pairs),
            "pairs": mandatory_pairs,
            "degree_sequence": sorted(degrees, reverse=True),
            "fixed_pair_mass": str(pair_mass),
            "pointwise_bounds": bounds,
            "pointwise_ratio": str(pointwise_ratio),
            "cover_pair_mass_upper_bound": str(cover_upper_bound),
            "contradiction_gap": str(gap),
        },
        "conclusion": {"result": result, "scope": scope},
        "nonclaims": [
            "A no-conclusion result is not evidence that the selected family can cover.",
            "A bounded exclusion says nothing about tiles outside the selected n-divides-period family.",
            "This does not resolve Erdős problem 203 globally.",
            "This producer analysis is not a Vela Verification or human Decision.",
            "No scientific Standing changes from this artifact.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--period", required=True, type=int)
    parser.add_argument("--preregistration", required=True)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        value = build(
            args.campaign_source.resolve(), args.period, args.preregistration
        )
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True))
        return 1
    raw = canonical_bytes(value)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "artifact_root": root(raw),
                "result": value["conclusion"]["result"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

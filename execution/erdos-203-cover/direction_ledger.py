#!/usr/bin/env python3
"""Build the exact prime-power direction and pair-compatibility ledger."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
from collections import defaultdict
from fractions import Fraction
from typing import Any

from search_5040_cegar import POOL_ROOT, TARGET, canonical_bytes, load_tiles


def prime_power_stages(period: int) -> list[tuple[int, int, int]]:
    stages = []
    remaining = period
    prime = 2
    while prime * prime <= remaining:
        exponent = 0
        modulus = 1
        while remaining % prime == 0:
            remaining //= prime
            exponent += 1
            modulus *= prime
            stages.append((prime, exponent, modulus))
        prime = 3 if prime == 2 else prime + 2
    if remaining > 1:
        stages.append((remaining, 1, remaining))
    return stages


def direction(u: int, v: int, modulus: int) -> tuple[int, int]:
    if math.gcd(u, modulus) == 1:
        return 1, (v * pow(u, -1, modulus)) % modulus
    if math.gcd(v, modulus) == 1:
        return (u * pow(v, -1, modulus)) % modulus, 1
    raise ValueError("local direction has no unit coordinate")


def compatibility_index(
    u1: int, v1: int, n1: int, u2: int, v2: int, n2: int
) -> int:
    columns = [(u1, u2), (v1, v2), (n1, 0), (0, n2)]
    determinants = [
        abs(a[0] * b[1] - a[1] * b[0])
        for index, a in enumerate(columns)
        for b in columns[index + 1 :]
    ]
    return math.gcd(*determinants)


def build(source: pathlib.Path, period: int) -> dict[str, Any]:
    tiles = load_tiles(source, period)
    stages = []
    for prime, exponent, modulus in prime_power_stages(period):
        groups: dict[tuple[int, int], list[int]] = defaultdict(list)
        for index, tile in enumerate(tiles):
            if tile.n % modulus == 0:
                groups[direction(tile.u, tile.v, modulus)].append(index)
        entries = []
        for local_direction, indices in sorted(groups.items()):
            entries.append(
                {
                    "direction": list(local_direction),
                    "supply": len(indices),
                    "distinct_primes": [tiles[index].p for index in indices],
                    "density": str(sum((Fraction(1, tiles[index].n) for index in indices), Fraction())),
                    "base_partition_supply": len(indices) >= prime,
                }
            )
        stages.append(
            {
                "prime": prime,
                "exponent": exponent,
                "modulus": modulus,
                "directions": entries,
                "directions_with_base_partition_supply": sum(
                    1 for entry in entries if entry["base_partition_supply"]
                ),
            }
        )

    pairs = []
    mandatory_density = Fraction()
    for first, left in enumerate(tiles):
        for second in range(first + 1, len(tiles)):
            right = tiles[second]
            index = compatibility_index(
                left.u, left.v, left.n, right.u, right.v, right.n
            )
            image_size = left.n * right.n // index
            compatible_intersection = Fraction(1, image_size)
            mandatory = index == 1
            if mandatory:
                mandatory_density += compatible_intersection
            pairs.append(
                {
                    "primes": [left.p, right.p],
                    "orders": [left.n, right.n],
                    "compatibility_index": index,
                    "compatible_shift_fraction": str(Fraction(1, index)),
                    "compatible_intersection_density": str(compatible_intersection),
                    "overlap_for_every_shift_pair": mandatory,
                }
            )

    return {
        "schema": "erdos-frontier.erdos-203-direction-ledger.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "period": period,
        "tiles": len(tiles),
        "density": str(sum((Fraction(1, tile.n) for tile in tiles), Fraction())),
        "density_slack": "3/140",
        "pool_root": POOL_ROOT,
        "source": {
            "commit": "94fde841ea6ad90437bd66a91953bfeba13dba0f",
            "tree": "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a",
        },
        "stages": stages,
        "pair_compatibility": {
            "pairs": pairs,
            "pairs_with_overlap_for_every_shift_pair": sum(
                1 for pair in pairs if pair["overlap_for_every_shift_pair"]
            ),
            "sum_of_mandatory_pair_intersection_densities": str(mandatory_density),
        },
        "nonclaims": [
            "Pair-intersection sums are not an inclusion-exclusion proof without higher-order control.",
            "Direction supply does not imply that compatible shifts form a cover.",
            "This ledger does not exclude the 5040 family or any broader family.",
            "This ledger is producer instrumentation and does not change Standing.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--period", type=int, default=5040)
    args = parser.parse_args()
    result = build(args.campaign_source.resolve(), args.period)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({"output": str(args.output), "tiles": result["tiles"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

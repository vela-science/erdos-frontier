#!/usr/bin/env python3
"""Qualify the root-supply obstruction for the pinned Erdős 203 pool.

This producer checks one deliberately narrow construction class.  A
root-confined parallel construction first splits Z^2 into q parallel slabs
and assigns every subsequently used tile to one slab.  Every assigned tile
must therefore have q in its subgroup order and the same local projective
direction.  Since the union has density one, that direction class must have
total tile density at least one, even when its tiles overlap.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
from collections import defaultdict
from fractions import Fraction
from typing import Any

from search_5040_cegar import (
    CAMPAIGN_COMMIT,
    CAMPAIGN_TREE,
    POOL_ROOT,
    TARGET,
    canonical_bytes,
    load_tiles,
)


def prime_divisors(value: int) -> list[int]:
    divisors: list[int] = []
    candidate = 2
    while candidate * candidate <= value:
        if value % candidate == 0:
            divisors.append(candidate)
            while value % candidate == 0:
                value //= candidate
        candidate = 3 if candidate == 2 else candidate + 2
    if value > 1:
        divisors.append(value)
    return divisors


def local_direction(u: int, v: int, prime: int) -> tuple[int, int]:
    u %= prime
    v %= prime
    if u:
        return 1, (v * pow(u, -1, prime)) % prime
    if v:
        return 0, 1
    raise ValueError("tile has zero local direction")


def build(source: pathlib.Path) -> dict[str, Any]:
    raw_pool = json.loads((source / "compute203" / "pool_merged.json").read_text())
    full_period = math.lcm(*(int(order) for order in raw_pool.values()))
    tiles = load_tiles(source, full_period)

    grouped: dict[int, dict[tuple[int, int], list[Any]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for tile in tiles:
        for prime in prime_divisors(tile.n):
            grouped[prime][local_direction(tile.u, tile.v, prime)].append(tile)

    stages = []
    candidates: list[tuple[Fraction, int, tuple[int, int], int]] = []
    for prime in sorted(grouped):
        directions = []
        for direction, members in sorted(grouped[prime].items()):
            density = sum((Fraction(1, tile.n) for tile in members), Fraction())
            directions.append(
                {
                    "direction": list(direction),
                    "tile_count": len(members),
                    "primes": [tile.p for tile in members],
                    "density": str(density),
                    "deficit_to_one": str(1 - density),
                }
            )
            candidates.append((density, prime, direction, len(members)))
        stages.append({"prime": prime, "directions": directions})

    maximum_density, maximum_prime, maximum_direction, maximum_count = max(
        candidates,
        key=lambda row: (row[0], -row[1], tuple(-part for part in row[2])),
    )
    if maximum_density >= 1:
        conclusion = "root_supply_gate_open"
    else:
        conclusion = "no_root_confined_parallel_cover_from_pinned_pool"

    return {
        "schema": "erdos-frontier.erdos-203-parallel-root-obstruction.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": {
            "commit": CAMPAIGN_COMMIT,
            "tree": CAMPAIGN_TREE,
            "pool_root": POOL_ROOT,
        },
        "pool": {
            "tiles": len(tiles),
            "density": str(
                sum((Fraction(1, tile.n) for tile in tiles), Fraction())
            ),
            "period_bits": full_period.bit_length(),
        },
        "construction_class": {
            "name": "root-confined parallel construction",
            "definition": (
                "The first move partitions Z^2 into q parallel slabs for one "
                "prime q. Every tile used below that move is confined to one "
                "child slab, so q divides its subgroup order and its local "
                "kernel direction equals the root direction."
            ),
            "necessary_condition": (
                "The direction class has total tile density at least one. "
                "This remains necessary when assigned tile cosets overlap."
            ),
        },
        "root_stages": stages,
        "maximum_direction": {
            "prime": maximum_prime,
            "direction": list(maximum_direction),
            "tile_count": maximum_count,
            "density": str(maximum_density),
            "deficit_to_one": str(1 - maximum_density),
        },
        "conclusion": conclusion,
        "next_obligation": (
            "A pure root-confined parallel construction needs new, "
            "direction-targeted source primes. Otherwise use a hybrid "
            "construction whose tiles are not all confined by one root split."
        ),
        "nonclaims": [
            "This does not rule out an overlapping or hybrid finite cover.",
            "This does not prove that no finite cover exists.",
            "This does not establish a globally complete prime pool.",
            "This producer analysis is not a Vela Verification or Decision.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    result = build(args.campaign_source.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(
        json.dumps(
            {
                "conclusion": result["conclusion"],
                "maximum_direction": result["maximum_direction"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

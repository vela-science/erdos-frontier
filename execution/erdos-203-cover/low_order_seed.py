#!/usr/bin/env python3
"""Exhaust the six indispensable low-order shifts for Erdős 203."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import pathlib
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

LOW_PRIMES = (5, 7, 11, 13, 17, 23)
PERIOD = 2640


def sha256_root(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def prime_powers(value: int) -> list[tuple[int, int]]:
    result = []
    prime = 2
    while prime * prime <= value:
        if value % prime == 0:
            power = 1
            while value % prime == 0:
                value //= prime
                power *= prime
            result.append((prime, power))
        prime = 3 if prime == 2 else prime + 2
    if value > 1:
        result.append((value, value))
    return result


def subset_data(tiles: list[Any]) -> list[dict[str, Any]]:
    subsets = []
    for mask in range(1, 1 << len(tiles)):
        indices = [index for index in range(len(tiles)) if mask >> index & 1]
        local_images = []
        image_size = 1
        primes = sorted(
            {prime for index in indices for prime, _ in prime_powers(tiles[index].n)}
        )
        for prime in primes:
            moduli = []
            for index in indices:
                power = 1
                remaining = tiles[index].n
                while remaining % prime == 0:
                    remaining //= prime
                    power *= prime
                moduli.append(power)
            stage = max(moduli)
            reachable = {
                tuple(
                    (tiles[index].u * x + tiles[index].v * y) % moduli[position]
                    for position, index in enumerate(indices)
                )
                for x in range(stage)
                for y in range(stage)
            }
            local_images.append((prime, moduli, reachable))
            image_size *= len(reachable)
        subsets.append(
            {
                "mask": mask,
                "indices": indices,
                "local_images": local_images,
                "image_size": image_size,
                "sign": 1 if len(indices) % 2 else -1,
            }
        )
    return subsets


def compatible(subset: dict[str, Any], shifts: tuple[int, ...]) -> bool:
    indices = subset["indices"]
    for _prime, moduli, reachable in subset["local_images"]:
        key = tuple(
            shifts[index] % moduli[position]
            for position, index in enumerate(indices)
        )
        if key not in reachable:
            return False
    return True


def complement_summary(source: pathlib.Path, tiles: list[Any], shifts: tuple[int, ...]) -> dict[str, Any]:
    lattice_path = source / "compute203" / "lattice.py"
    specification = importlib.util.spec_from_file_location("erdos203_lattice", lattice_path)
    if specification is None or specification.loader is None:
        raise ValueError("could not load the frozen lattice engine")
    lattice = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(lattice)
    cells = [(1, 0, 0, 1, 0, 0)]
    for tile, shift in zip(tiles, shifts, strict=True):
        uncovered = []
        for cell in cells:
            remainder = lattice.split(cell, tile.u, tile.v, tile.n, shift)
            uncovered.extend([cell] if remainder is None else remainder)
        cells = uncovered
    normalized = sorted([list(cell) for cell in cells])
    density = sum((Fraction(1, lattice.idx(tuple(cell))) for cell in normalized), Fraction())
    return {
        "cell_count": len(normalized),
        "density": str(density),
        "cells_root": sha256_root(normalized),
    }


def build(source: pathlib.Path) -> dict[str, Any]:
    tiles = [tile for tile in load_tiles(source, PERIOD) if tile.p in LOW_PRIMES]
    tiles.sort(key=lambda tile: tile.p)
    if tuple(tile.p for tile in tiles) != LOW_PRIMES:
        raise ValueError("indispensable low-order tile set drifted")
    subsets = subset_data(tiles)
    scale = math.lcm(*(subset["image_size"] for subset in subsets))
    for subset in subsets:
        subset["weight"] = subset["sign"] * scale // subset["image_size"]

    best_score = -1
    best_shifts: tuple[int, ...] | None = None
    optimal_assignments = 0
    assignments_examined = 0
    ranges = [range(1) if tile.p == 5 else range(tile.n) for tile in tiles]
    for shifts in itertools.product(*ranges):
        score = sum(
            subset["weight"] for subset in subsets if compatible(subset, shifts)
        )
        assignments_examined += 1
        if score > best_score:
            best_score = score
            best_shifts = shifts
            optimal_assignments = 1
        elif score == best_score:
            optimal_assignments += 1
    if best_shifts is None:
        raise ValueError("no low-order assignments were enumerated")

    union_density = Fraction(best_score, scale)
    intersections = []
    for subset in subsets:
        is_compatible = compatible(subset, best_shifts)
        intersections.append(
            {
                "primes": [tiles[index].p for index in subset["indices"]],
                "compatible": is_compatible,
                "density": str(Fraction(1, subset["image_size"])) if is_compatible else "0",
                "inclusion_sign": subset["sign"],
            }
        )
    return {
        "schema": "erdos-frontier.erdos-203-low-order-seed.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": {
            "commit": CAMPAIGN_COMMIT,
            "tree": CAMPAIGN_TREE,
            "pool_root": POOL_ROOT,
        },
        "symmetry": {
            "fixed_prime": 5,
            "fixed_shift": 0,
            "reason": "Translation makes one shift arbitrary; fixing it removes a factor of four.",
        },
        "tiles": [
            {"p": tile.p, "n": tile.n, "g": tile.g, "u": tile.u, "v": tile.v}
            for tile in tiles
        ],
        "search": {
            "assignments_examined": assignments_examined,
            "optimal_assignments": optimal_assignments,
            "score_method": "prime-power image enumeration plus exact inclusion-exclusion",
        },
        "best": {
            "shifts": {str(tile.p): shift for tile, shift in zip(tiles, best_shifts, strict=True)},
            "union_density": str(union_density),
            "complement_density": str(1 - union_density),
            "intersections": intersections,
            "complement": complement_summary(source, tiles, best_shifts),
        },
        "next_obligation": (
            "Search the exact rooted complement with the remaining 307 pinned tiles; "
            "any candidate must still pass the frozen full affine verifier."
        ),
        "nonclaims": [
            "The optimal six-tile seed is not an exact cover.",
            "Optimality is only over shifts of these six fixed pinned tiles.",
            "This does not establish that every full-pool cover uses this seed.",
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
    print(json.dumps({"best": result["best"], "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

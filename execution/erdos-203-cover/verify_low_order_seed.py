#!/usr/bin/env python3
"""Source-first checker for the exhaustive Erdős 203 low-order seed."""

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

from verify import multiplicative_order, split_complement

COMMIT = "94fde841ea6ad90437bd66a91953bfeba13dba0f"
TREE = "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a"
POOL_ROOT = "sha256:9a8f179bf6ab509c53144ac679acd8ffe42e66588b1516b0ca3a9f45e18395b3"
LOW_PRIMES = (5, 7, 11, 13, 17, 23)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def root(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


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


def primitive_root(prime: int) -> int:
    factors = [factor for factor, _ in prime_powers(prime - 1)]
    for candidate in range(2, prime):
        if all(pow(candidate, (prime - 1) // factor, prime) != 1 for factor in factors):
            return candidate
    raise ValueError(f"no primitive root for {prime}")


def coordinates(prime: int, order: int) -> tuple[int, int, int]:
    generator = pow(primitive_root(prime), (prime - 1) // order, prime)
    values = {pow(generator, exponent, prime): exponent for exponent in range(order)}
    if 2 % prime not in values or 3 % prime not in values:
        raise ValueError(f"wrong subgroup order for {prime}")
    return generator, values[2 % prime], values[3 % prime]


def subset_data(tiles: list[dict[str, int]]) -> list[dict[str, Any]]:
    subsets = []
    for mask in range(1, 1 << len(tiles)):
        indices = [index for index in range(len(tiles)) if mask >> index & 1]
        local_images = []
        image_size = 1
        primes = sorted(
            {prime for index in indices for prime, _ in prime_powers(tiles[index]["n"])}
        )
        for prime in primes:
            moduli = []
            for index in indices:
                power = 1
                remaining = tiles[index]["n"]
                while remaining % prime == 0:
                    remaining //= prime
                    power *= prime
                moduli.append(power)
            stage = max(moduli)
            reachable = {
                tuple(
                    (
                        tiles[index]["u"] * x + tiles[index]["v"] * y
                    ) % moduli[position]
                    for position, index in enumerate(indices)
                )
                for x in range(stage)
                for y in range(stage)
            }
            local_images.append((moduli, reachable))
            image_size *= len(reachable)
        subsets.append(
            {
                "indices": indices,
                "local_images": local_images,
                "image_size": image_size,
                "sign": 1 if len(indices) % 2 else -1,
            }
        )
    return subsets


def compatible(subset: dict[str, Any], shifts: tuple[int, ...]) -> bool:
    indices = subset["indices"]
    return all(
        tuple(
            shifts[index] % moduli[position]
            for position, index in enumerate(indices)
        ) in reachable
        for moduli, reachable in subset["local_images"]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    source = args.campaign_source.resolve()
    commit = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    tree = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    if (commit, tree) != (COMMIT, TREE):
        raise ValueError("campaign source drifted")
    pool_bytes = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_bytes) != POOL_ROOT:
        raise ValueError("pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_bytes).items()}
    tiles = []
    for prime in LOW_PRIMES:
        order = pool[prime]
        if math.lcm(multiplicative_order(2, prime), multiplicative_order(3, prime)) != order:
            raise ValueError(f"subgroup order drifted for {prime}")
        generator, u, v = coordinates(prime, order)
        tiles.append({"p": prime, "n": order, "g": generator, "u": u, "v": v})

    raw = args.artifact.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact):
        raise ValueError("artifact is not canonical JSON")
    if artifact.get("schema") != "erdos-frontier.erdos-203-low-order-seed.v1":
        raise ValueError("wrong artifact schema")
    if artifact.get("tiles") != tiles:
        raise ValueError("low-order tile rows drifted")

    subsets = subset_data(tiles)
    scale = math.lcm(*(subset["image_size"] for subset in subsets))
    for subset in subsets:
        subset["weight"] = subset["sign"] * scale // subset["image_size"]
    best_score = -1
    best: tuple[int, ...] | None = None
    optimal = 0
    examined = 0
    ranges = [range(1) if tile["p"] == 5 else range(tile["n"]) for tile in tiles]
    for shifts in itertools.product(*ranges):
        score = sum(subset["weight"] for subset in subsets if compatible(subset, shifts))
        examined += 1
        if score > best_score:
            best_score, best, optimal = score, shifts, 1
        elif score == best_score:
            optimal += 1
    if best is None:
        raise ValueError("no assignment found")
    expected_shifts = {str(tile["p"]): shift for tile, shift in zip(tiles, best, strict=True)}
    union = Fraction(best_score, scale)
    if artifact["search"]["assignments_examined"] != examined:
        raise ValueError("assignment count drifted")
    if artifact["search"]["optimal_assignments"] != optimal:
        raise ValueError("optimal assignment count drifted")
    if artifact["best"]["shifts"] != expected_shifts:
        raise ValueError("lexicographic optimum drifted")
    if artifact["best"]["union_density"] != str(union):
        raise ValueError("union density drifted")
    if artifact["best"]["complement_density"] != str(1 - union):
        raise ValueError("complement density drifted")

    cells = [(1, 0, 0, 1, 0, 0)]
    for tile, shift in zip(tiles, best, strict=True):
        uncovered = []
        for cell in cells:
            remainder = split_complement(
                cell, tile["u"], tile["v"], tile["n"], shift
            )
            uncovered.extend([cell] if remainder is None else remainder)
        cells = uncovered
    normalized = sorted([list(cell) for cell in cells])
    complement = artifact["best"]["complement"]
    if complement != {
        "cell_count": len(normalized),
        "density": str(1 - union),
        "cells_root": root(canonical_bytes(normalized)),
    }:
        raise ValueError("rooted complement drifted")

    result = {
        "schema": "erdos-frontier.erdos-203-low-order-seed-check.v1",
        "target": "erdos:203:finite-cover",
        "authority": "non_authoritative",
        "artifact_root": root(raw),
        "status": "passed",
        "checks": [
            "frozen source commit, tree, and pool root",
            "six exact subgroup coordinate maps",
            "126720 symmetry-reduced assignments",
            "exact prime-power images and inclusion-exclusion optimum",
            "2290-cell complement reconstructed with a separate lattice implementation",
        ],
        "established": "The retained shifts maximize union density for the six fixed low-order tiles.",
        "not_established": [
            "an exact cover",
            "global optimality over other tile subsets",
            "necessity of this seed in a full-pool cover",
            "scientific acceptance or Standing",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = canonical_bytes(result)
    args.output.write_bytes(output)
    print(json.dumps({"output_root": root(output), "status": "passed"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

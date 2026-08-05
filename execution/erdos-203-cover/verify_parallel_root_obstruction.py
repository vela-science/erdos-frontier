#!/usr/bin/env python3
"""Dependency-free checker for the Erdős 203 parallel-root obstruction."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import subprocess
from collections import defaultdict
from fractions import Fraction
from typing import Any

CAMPAIGN_COMMIT = "94fde841ea6ad90437bd66a91953bfeba13dba0f"
CAMPAIGN_TREE = "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a"
POOL_ROOT = "sha256:9a8f179bf6ab509c53144ac679acd8ffe42e66588b1516b0ca3a9f45e18395b3"
TARGET = "erdos:203:finite-cover"
SCHEMA = "erdos-frontier.erdos-203-parallel-root-obstruction.v1"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def root(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def prime_divisors(value: int) -> list[int]:
    result: list[int] = []
    candidate = 2
    while candidate * candidate <= value:
        if value % candidate == 0:
            result.append(candidate)
            while value % candidate == 0:
                value //= candidate
        candidate = 3 if candidate == 2 else candidate + 2
    if value > 1:
        result.append(value)
    return result


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def multiplicative_order(base: int, prime: int) -> int:
    order = prime - 1
    for divisor in prime_divisors(order):
        while order % divisor == 0 and pow(base, order // divisor, prime) == 1:
            order //= divisor
    return order


def primitive_root(prime: int) -> int:
    factors = prime_divisors(prime - 1)
    for candidate in range(2, prime):
        if all(pow(candidate, (prime - 1) // factor, prime) != 1 for factor in factors):
            return candidate
    raise ValueError(f"no primitive root for {prime}")


def local_log(base: int, generator: int, order: int, factor: int, prime: int) -> int:
    target = pow(base, order // factor, prime)
    step = pow(generator, order // factor, prime)
    value = 1
    for exponent in range(factor):
        if value == target:
            return exponent
        value = value * step % prime
    raise ValueError(f"no local logarithm modulo {factor} for {base} mod {prime}")


def local_direction(u: int, v: int, prime: int) -> tuple[int, int]:
    if u % prime:
        return 1, (v * pow(u, -1, prime)) % prime
    if v % prime:
        return 0, 1
    raise ValueError("zero local direction")


def expected(source: pathlib.Path) -> dict[str, Any]:
    commit = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    tree = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    if commit != CAMPAIGN_COMMIT or tree != CAMPAIGN_TREE:
        raise ValueError("campaign source is not the frozen commit and tree")
    pool_bytes = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_bytes) != POOL_ROOT:
        raise ValueError("campaign pool root drifted")
    pool = {int(key): int(value) for key, value in json.loads(pool_bytes).items()}
    grouped: dict[int, dict[tuple[int, int], list[tuple[int, int]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for prime, order in sorted(pool.items(), key=lambda row: row[1]):
        if not is_prime(prime):
            raise ValueError(f"nonprime pool key {prime}")
        if math.lcm(
            multiplicative_order(2, prime), multiplicative_order(3, prime)
        ) != order:
            raise ValueError(f"wrong subgroup order for {prime}")
        generator = pow(primitive_root(prime), (prime - 1) // order, prime)
        if multiplicative_order(generator, prime) != order:
            raise ValueError(f"wrong subgroup generator for {prime}")
        for factor in prime_divisors(order):
            u = local_log(2, generator, order, factor, prime)
            v = local_log(3, generator, order, factor, prime)
            grouped[factor][local_direction(u, v, factor)].append((prime, order))

    stages = []
    candidates: list[tuple[Fraction, int, tuple[int, int], int]] = []
    for factor in sorted(grouped):
        directions = []
        for direction, members in sorted(grouped[factor].items()):
            density = sum((Fraction(1, order) for _, order in members), Fraction())
            directions.append(
                {
                    "direction": list(direction),
                    "tile_count": len(members),
                    "primes": [prime for prime, _ in members],
                    "density": str(density),
                    "deficit_to_one": str(1 - density),
                }
            )
            candidates.append((density, factor, direction, len(members)))
        stages.append({"prime": factor, "directions": directions})
    maximum_density, maximum_prime, maximum_direction, maximum_count = max(
        candidates,
        key=lambda row: (row[0], -row[1], tuple(-part for part in row[2])),
    )
    full_period = math.lcm(*pool.values())
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": {
            "commit": CAMPAIGN_COMMIT,
            "tree": CAMPAIGN_TREE,
            "pool_root": POOL_ROOT,
        },
        "pool": {
            "tiles": len(pool),
            "density": str(sum((Fraction(1, order) for order in pool.values()), Fraction())),
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
        "conclusion": "no_root_confined_parallel_cover_from_pinned_pool",
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
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    artifact_bytes = args.artifact.read_bytes()
    artifact = json.loads(artifact_bytes)
    computed = expected(args.campaign_source.resolve())
    if artifact_bytes != canonical_bytes(artifact):
        raise ValueError("artifact is not canonical JSON")
    if artifact != computed:
        raise ValueError("artifact does not match source-first recomputation")
    if Fraction(artifact["maximum_direction"]["density"]) >= 1:
        raise ValueError("root direction supply is not obstructed")
    result = {
        "schema": "erdos-frontier.erdos-203-parallel-root-obstruction-check.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "artifact_root": root(artifact_bytes),
        "status": "passed",
        "checks": [
            "frozen source commit, tree, and pool root",
            "313 prime keys and exact subgroup orders",
            "local projective direction at every prime divisor of every order",
            "exact direction-class density sums and global maximum",
            "strict maximum-direction density deficit below one",
        ],
        "established": (
            "The pinned pool cannot support a root-confined parallel cover."
        ),
        "not_established": [
            "nonexistence of an overlapping or hybrid cover",
            "nonexistence of any finite cover",
            "completeness of the pinned prime pool",
            "scientific acceptance or Standing",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output_bytes = canonical_bytes(result)
    args.output.write_bytes(output_bytes)
    print(json.dumps({"output_root": root(output_bytes), "status": "passed"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Source-first exact checker for the retained Erdős 203 5040 stage."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import subprocess
from fractions import Fraction
from typing import Any

import numpy as np

from verify import is_prime, multiplicative_order

COMMIT = "94fde841ea6ad90437bd66a91953bfeba13dba0f"
TREE = "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a"
POOL_ROOT = "sha256:9a8f179bf6ab509c53144ac679acd8ffe42e66588b1516b0ca3a9f45e18395b3"
PERIOD = 5040
FIXED = {"5": 0, "7": 0, "11": 0, "13": 1, "17": 3, "23": 0}
TARGET = "erdos:203:finite-cover"
SOURCE = {
    "repository": "https://github.com/williamjblair/lean-proofs.git",
    "commit": COMMIT,
    "tree": TREE,
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def root(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


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

    raw = args.artifact.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact):
        raise ValueError("artifact is not canonical JSON")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-stage.v1":
        raise ValueError("wrong artifact schema")
    if (
        artifact.get("target") != TARGET
        or artifact.get("authority") != "non_authoritative"
        or artifact.get("claim_credit") is not False
        or artifact.get("source") != SOURCE
        or artifact.get("pool_root") != POOL_ROOT
    ):
        raise ValueError("artifact provenance or authority metadata drifted")
    if artifact.get("period") != PERIOD or artifact.get("fixed_seed") != FIXED:
        raise ValueError("wrong period or fixed seed")
    rows = artifact.get("rows")
    expected_primes = [
        prime
        for prime, order in sorted(pool.items(), key=lambda item: (item[1], item[0]))
        if PERIOD % order == 0
    ]
    if (
        artifact.get("tile_count") != len(expected_primes)
        or not isinstance(rows, list)
        or [row.get("p") for row in rows] != expected_primes
    ):
        raise ValueError("period tile family drifted")

    counts = np.zeros((PERIOD, PERIOD), dtype=np.int8)
    columns = np.arange(PERIOD, dtype=np.int64)
    for position, row in enumerate(rows):
        if set(row) != {"p", "n", "g", "u", "v", "c"}:
            raise ValueError(f"row {position} has wrong fields")
        prime, order, generator, u, v, shift = (
            row["p"], row["n"], row["g"], row["u"], row["v"], row["c"]
        )
        if not is_prime(prime) or order != pool[prime]:
            raise ValueError(f"row {position} has wrong prime or order")
        if math.lcm(multiplicative_order(2, prime), multiplicative_order(3, prime)) != order:
            raise ValueError(f"row {position} subgroup order fails")
        if (
            multiplicative_order(generator, prime) != order
            or pow(generator, u, prime) != 2 % prime
            or pow(generator, v, prime) != 3 % prime
            or not 0 <= shift < order
        ):
            raise ValueError(f"row {position} coordinate map fails")
        for lattice_row in range(PERIOD):
            mask = (u * lattice_row + v * columns) % order == shift
            counts[lattice_row, mask] += 1

    holes_mask = counts == 0
    holes = int(np.count_nonzero(holes_mask))
    packed = np.packbits(holes_mask.reshape(-1), bitorder="little").tobytes()
    residual = Fraction(holes, PERIOD * PERIOD)
    expected_result = {
        "status": "exact_residual",
        "points": PERIOD * PERIOD,
        "holes": holes,
        "assignment_root": root(canonical_bytes(rows)),
        "holes_root": root(packed),
        "packing": "row-major boolean holes, numpy packbits little-bit order",
        "residual_density": str(residual),
        "covered_density": str(1 - residual),
    }
    if artifact.get("result") != expected_result:
        raise ValueError("exact torus result drifted")

    result = {
        "schema": "erdos-frontier.erdos-203-period-stage-check.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "artifact_root": root(raw),
        "status": "passed",
        "checks": [
            "frozen source commit, tree, and pool root",
            "complete 31-tile period family and exact coordinate maps",
            "all 25401600 period-5040 torus points",
            "canonical packed-hole root and exact density fractions",
        ],
        "established": "The retained assignment has exactly the reported period-5040 holes.",
        "not_established": [
            "an exact cover",
            "global optimality of the assignment",
            "nonexistence of a finite cover",
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

#!/usr/bin/env python3
"""Source-first exact checker for the retained Erdős 203 period-55440 lift."""

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
BASE_ARTIFACT_ROOT = "sha256:8c2633e79b305a8940fd2b577664d1d75e4d4c366ba0c375e2d0e76dc11bb84d"
BASE_HOLES_ROOT = "sha256:b9e0d56de8050dbde4bf41708f20447567bc7ea56e8515ab04ada82991a893a9"
INITIAL_ASSIGNMENT_ROOT = "sha256:32d1cef3664b946b5acc8d9b1242e42949f8932c4a9bb5366d8a580d48ccd85e"
TARGET = "erdos:203:finite-cover"
SOURCE = {
    "repository": "https://github.com/williamjblair/lean-proofs.git",
    "commit": COMMIT,
    "tree": TREE,
}
BASE_PERIOD = 5_040
PERIOD = 55_440
FIBER = 11
FIXED_SEED = {"5": 0, "7": 0, "11": 0, "13": 1, "17": 3, "23": 0}
RESIDUAL_DOMAIN = b"erdos203-period-55440-residual-v1\0"
MASK64 = (1 << 64) - 1
MASK57 = (1 << 57) - 1


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def popcount(values: np.ndarray) -> np.ndarray:
    values = values.copy()
    values -= (values >> np.uint64(1)) & np.uint64(0x5555555555555555)
    values = (values & np.uint64(0x3333333333333333)) + (
        (values >> np.uint64(2)) & np.uint64(0x3333333333333333)
    )
    values = (values + (values >> np.uint64(4))) & np.uint64(
        0x0F0F0F0F0F0F0F0F
    )
    return ((values * np.uint64(0x0101010101010101)) >> np.uint64(56)).astype(
        np.uint8
    )


def line_masks(row: dict[str, int]) -> tuple[list[np.uint64], list[np.uint64]]:
    low = []
    high = []
    for offset in range(FIBER):
        value = 0
        for first in range(FIBER):
            for second in range(FIBER):
                if (row["u"] * first + row["v"] * second) % FIBER == offset:
                    value |= 1 << (FIBER * first + second)
        low.append(np.uint64(value & MASK64))
        high.append(np.uint64(value >> 64))
    return low, high


def empty_masks(size: int) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.full(size, np.uint64(MASK64), dtype=np.uint64),
        np.full(size, np.uint64(MASK57), dtype=np.uint64),
    )


def apply_tile(
    low: np.ndarray,
    high: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    row: dict[str, int],
) -> None:
    modulus = row["n"] // FIBER
    if row["n"] != FIBER * modulus or BASE_PERIOD % modulus:
        raise ValueError(f"prime {row['p']} is not an 11-fiber tile")
    base = (row["u"] * first + row["v"] * second) % row["n"]
    delta = (row["c"] - base) % row["n"]
    inverse = pow((BASE_PERIOD // modulus) % FIBER, -1, FIBER)
    line_low, line_high = line_masks(row)
    for quotient in range(FIBER):
        selected = delta == quotient * modulus
        if not np.any(selected):
            continue
        offset = quotient * inverse % FIBER
        low[selected] &= ~line_low[offset]
        high[selected] &= ~line_high[offset]


def residual_masks(
    first: np.ndarray,
    second: np.ndarray,
    rows: list[dict[str, int]],
    omitted: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    low, high = empty_masks(len(first))
    for index, row in enumerate(rows):
        if index != omitted:
            apply_tile(low, high, first, second, row)
    return low, high


def score_shifts(
    low: np.ndarray,
    high: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    row: dict[str, int],
) -> np.ndarray:
    modulus = row["n"] // FIBER
    base = (row["u"] * first + row["v"] * second) % row["n"]
    residue = base % modulus
    quotient = base // modulus
    inverse = pow((BASE_PERIOD // modulus) % FIBER, -1, FIBER)
    line_low, line_high = line_masks(row)
    scores = np.zeros(row["n"], dtype=np.int64)
    for delta in range(FIBER):
        candidate = residue + modulus * ((quotient + delta) % FIBER)
        offset = delta * inverse % FIBER
        weights = popcount(low & line_low[offset]).astype(np.int64)
        weights += popcount(high & line_high[offset]).astype(np.int64)
        scores += np.bincount(candidate, weights=weights, minlength=row["n"]).astype(
            np.int64
        )
    return scores


def hole_count(low: np.ndarray, high: np.ndarray) -> int:
    total = 0
    batch = 250_000
    for start in range(0, len(low), batch):
        end = start + batch
        total += int(np.sum(popcount(low[start:end]), dtype=np.int64))
        total += int(np.sum(popcount(high[start:end]), dtype=np.int64))
    return total


def residual_root(
    first: np.ndarray, second: np.ndarray, low: np.ndarray, high: np.ndarray
) -> str:
    digest = hashlib.sha256()
    digest.update(RESIDUAL_DOMAIN)
    dtype = np.dtype(
        [("first", "<u2"), ("second", "<u2"), ("low", "<u8"), ("high", "<u8")]
    )
    batch = 250_000
    for start in range(0, len(first), batch):
        end = min(start + batch, len(first))
        records = np.empty(end - start, dtype=dtype)
        records["first"] = first[start:end]
        records["second"] = second[start:end]
        records["low"] = low[start:end]
        records["high"] = high[start:end]
        digest.update(records.tobytes())
    return "sha256:" + digest.hexdigest()


def verify_row(row: dict[str, int], prime: int, order: int, position: int) -> None:
    if set(row) != {"p", "n", "g", "u", "v", "c"}:
        raise ValueError(f"row {position} has wrong fields")
    if row["p"] != prime or row["n"] != order or not is_prime(prime):
        raise ValueError(f"row {position} has wrong prime or order")
    generator, first, second, shift = row["g"], row["u"], row["v"], row["c"]
    if math.lcm(multiplicative_order(2, prime), multiplicative_order(3, prime)) != order:
        raise ValueError(f"row {position} has wrong subgroup order")
    if (
        multiplicative_order(generator, prime) != order
        or pow(generator, first, prime) != 2 % prime
        or pow(generator, second, prime) != 3 % prime
        or math.gcd(math.gcd(first, second), order) != 1
        or not 0 <= shift < order
    ):
        raise ValueError(f"row {position} coordinate map fails")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--base-artifact", required=True, type=pathlib.Path)
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
    pool_raw = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_raw) != POOL_ROOT:
        raise ValueError("pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_raw).items()}

    base_raw = args.base_artifact.read_bytes()
    base_artifact = json.loads(base_raw)
    if root(base_raw) != BASE_ARTIFACT_ROOT or base_raw != canonical_bytes(base_artifact):
        raise ValueError("base period artifact drifted")

    raw = args.artifact.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact):
        raise ValueError("artifact is not canonical JSON")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-55440-lift.v1":
        raise ValueError("wrong artifact schema")
    if (
        artifact.get("target") != TARGET
        or artifact.get("authority") != "non_authoritative"
        or artifact.get("claim_credit") is not False
        or artifact.get("source") != SOURCE
        or artifact.get("pool_root") != POOL_ROOT
        or artifact.get("period") != PERIOD
        or artifact.get("fixed_seed") != FIXED_SEED
    ):
        raise ValueError("artifact provenance, authority, or period drifted")

    expected = [
        (prime, order)
        for prime, order in sorted(pool.items(), key=lambda item: item[1])
        if PERIOD % order == 0
    ]
    rows = artifact.get("rows")
    if artifact.get("tile_count") != 55 or not isinstance(rows, list) or len(rows) != 55:
        raise ValueError("wrong period-55440 tile count")
    for position, (row, (prime, order)) in enumerate(zip(rows, expected, strict=True)):
        verify_row(row, prime, order, position)

    shifts = {str(row["p"]): row["c"] for row in rows}
    if {prime: shifts.get(prime) for prime in FIXED_SEED} != FIXED_SEED:
        raise ValueError("qualified seed shifts drifted")
    base_rows = [row for row in rows if BASE_PERIOD % row["n"] == 0]
    lift_rows = [row for row in rows if BASE_PERIOD % row["n"] != 0]
    if base_rows != base_artifact.get("rows") or len(lift_rows) != 24:
        raise ValueError("base assignment or lift family drifted")

    columns = np.arange(BASE_PERIOD, dtype=np.int64)
    counts = np.zeros((BASE_PERIOD, BASE_PERIOD), dtype=np.int8)
    for row in base_rows:
        for lattice_row in range(BASE_PERIOD):
            selected = (
                row["u"] * lattice_row + row["v"] * columns
            ) % row["n"] == row["c"]
            counts[lattice_row, selected] += 1
    packed = np.packbits((counts == 0).reshape(-1), bitorder="little").tobytes()
    first, second = np.nonzero(counts == 0)
    first = first.astype(np.int32)
    second = second.astype(np.int32)
    if len(first) != 7_184_680 or root(packed) != BASE_HOLES_ROOT:
        raise ValueError("base residual drifted")

    low, high = residual_masks(first, second, lift_rows)
    holes = hole_count(low, high)
    residual = Fraction(holes, PERIOD * PERIOD)
    expected_result = {
        "status": "exact_residual",
        "points": PERIOD * PERIOD,
        "holes": holes,
        "assignment_root": root(canonical_bytes(rows)),
        "residual_root": residual_root(first, second, low, high),
        "residual_encoding": (
            "sha256 over domain tag then row-major <u2 first, <u2 second, "
            "<u8 low mask, <u8 high mask for every period-5040 base hole; "
            "fiber bit is 11*i+j for (x+5040*i,y+5040*j)"
        ),
        "residual_density": str(residual),
        "covered_density": str(1 - residual),
    }
    if artifact.get("result") != expected_result:
        raise ValueError("exact lifted residual drifted")

    search = artifact.get("search")
    if (
        not isinstance(search, dict)
        or search.get("algorithm") != "deterministic exact-residual coordinate descent"
        or search.get("initial_assignment_root") != INITIAL_ASSIGNMENT_ROOT
        or search.get("base_holes") != len(first)
        or search.get("fiber_points") != len(first) * FIBER * FIBER
        or search.get("exact_search_holes") != holes
        or search.get("coordinatewise_optimal") is not True
        or search.get("movable_tiles") != 23
        or search.get("fixed_lift_tile") != {"prime": 23, "shift": 0}
        or search.get("tie_break") != "least shift"
    ):
        raise ValueError("search contract drifted")

    for index, row in enumerate(lift_rows):
        if row["p"] == 23:
            continue
        without_low, without_high = residual_masks(
            first, second, lift_rows, omitted=index
        )
        scores = score_shifts(without_low, without_high, first, second, row)
        if row["c"] != int(np.argmax(scores)):
            raise ValueError(f"prime {row['p']} is not least-shift coordinate-optimal")

    result = {
        "schema": "erdos-frontier.erdos-203-period-55440-lift-check.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "artifact_root": root(raw),
        "status": "passed",
        "checks": [
            "frozen source commit, tree, pool, and period-5040 base artifact",
            "complete 55-tile period family and exact coordinate maps",
            "factor-complete count of all 3073593600 period-55440 points",
            "canonical rooted residual and exact density fractions",
            "all shifts for each of the 23 movable lift tiles",
        ],
        "established": (
            "The retained assignment has exactly the reported period-55440 residual "
            "and is coordinate-wise optimal for the 23 movable lift tiles under its fixed base assignment and prime-23 shift."
        ),
        "not_established": [
            "an exact cover",
            "global or joint optimality of the 55-tile assignment",
            "optimality after moving the inherited period-5040 shifts or prime 23",
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

#!/usr/bin/env python3
"""Source-first checker for the Erdős 203 period-110880 factor-two lift."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
from fractions import Fraction
from typing import Any

import numpy as np

from verify_period_55440_lift import (
    COMMIT,
    POOL_ROOT,
    SOURCE,
    TARGET,
    TREE,
    canonical_bytes,
    popcount,
    residual_masks,
    residual_root,
    root,
    verify_row,
)

INNER_PERIOD = 5_040
BASE_PERIOD = 55_440
PERIOD = 110_880
FIBER = 2
BASE_ARTIFACT_ROOT = "sha256:e81480fbc4275ff15d39cd09dc9597c367d12f1cf032ce421ffe8190eeb73e95"
BASE_ASSIGNMENT_ROOT = "sha256:f7bcfc100800467363a39847605975d785474264b2200897bc62d18a71b98eba"
BASE_RESIDUAL_ROOT = "sha256:6c5bb5959a374d7a680fcf8847cf4a8176fb9b516a884e6420eac99d6df38bb4"
BASE_HOLES = 737_345_045
FROZEN_ASSIGNMENT = {193: 44, 353: 123, 2113: 103, 6337: 2696, 20161: 2802}
RESIDUAL_DOMAIN = b"erdos203-period-110880-residual-v1\0"
NIBBLE_POPCOUNT = np.asarray([value.bit_count() for value in range(16)], dtype=np.uint8)


def factor_line_masks(row: dict[str, int]) -> tuple[np.uint8, np.uint8]:
    modulus = row["n"] // FIBER
    if (
        row["n"] != FIBER * modulus
        or BASE_PERIOD % modulus
        or (BASE_PERIOD // modulus) % FIBER != 1
    ):
        raise ValueError(f"prime {row['p']} is not a nonsingular factor-two lift")
    masks = []
    for offset in range(FIBER):
        mask = 0
        for first in range(FIBER):
            for second in range(FIBER):
                if (row["u"] * first + row["v"] * second) % FIBER == offset:
                    mask |= 1 << (FIBER * first + second)
        if mask.bit_count() != FIBER:
            raise ValueError(f"prime {row['p']} does not cut an affine fiber line")
        masks.append(np.uint8(mask))
    return masks[0], masks[1]


def apply_factor_tile(
    nibbles: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    row: dict[str, int],
) -> None:
    modulus = row["n"] // FIBER
    base = (row["u"] * first + row["v"] * second) % row["n"]
    compatible = base % modulus == row["c"] % modulus
    if not np.any(compatible):
        return
    offsets = ((row["c"] // modulus) - (base[compatible] // modulus)) % FIBER
    masks = factor_line_masks(row)
    selected = np.flatnonzero(compatible)
    for offset in range(FIBER):
        positions = selected[offsets == offset]
        nibbles[positions] &= np.uint8(15 ^ int(masks[offset]))


def exact_result(
    first: np.ndarray,
    second: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    rows: list[dict[str, int]],
) -> tuple[int, str]:
    packed = np.zeros((len(first), 61), dtype=np.uint8)
    holes = 0
    for position in range(11 * 11):
        if position < 64:
            open_mask = ((low >> np.uint64(position)) & np.uint64(1)).astype(bool)
        else:
            open_mask = ((high >> np.uint64(position - 64)) & np.uint64(1)).astype(bool)
        if not np.any(open_mask):
            continue
        fiber_first, fiber_second = divmod(position, 11)
        current_first = first[open_mask].astype(np.int64) + INNER_PERIOD * fiber_first
        current_second = second[open_mask].astype(np.int64) + INNER_PERIOD * fiber_second
        nibbles = np.full(len(current_first), np.uint8(15), dtype=np.uint8)
        for row in rows:
            apply_factor_tile(nibbles, current_first, current_second, row)
        holes += int(np.sum(NIBBLE_POPCOUNT[nibbles], dtype=np.int64))
        byte = position // 2
        if position % 2:
            packed[open_mask, byte] |= nibbles << np.uint8(4)
        else:
            packed[open_mask, byte] |= nibbles

    digest = hashlib.sha256()
    digest.update(RESIDUAL_DOMAIN)
    digest.update(BASE_ARTIFACT_ROOT.encode("ascii"))
    dtype = np.dtype([("first", "<u2"), ("second", "<u2"), ("fiber", "u1", (61,))])
    batch = 100_000
    for start in range(0, len(first), batch):
        end = min(start + batch, len(first))
        records = np.empty(end - start, dtype=dtype)
        records["first"] = first[start:end]
        records["second"] = second[start:end]
        records["fiber"] = packed[start:end]
        digest.update(records.tobytes())
    return holes, "sha256:" + digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--base-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    source = args.campaign_source.resolve()
    commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD^{tree}"], text=True).strip()
    if (commit, tree) != (COMMIT, TREE):
        raise ValueError("campaign source drifted")
    pool_raw = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_raw) != POOL_ROOT:
        raise ValueError("pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_raw).items()}

    base_raw = args.base_artifact.read_bytes()
    base_artifact = json.loads(base_raw)
    if base_raw != canonical_bytes(base_artifact) or root(base_raw) != BASE_ARTIFACT_ROOT:
        raise ValueError("retained period-55440 artifact drifted")
    if (
        base_artifact.get("result", {}).get("assignment_root") != BASE_ASSIGNMENT_ROOT
        or base_artifact.get("result", {}).get("residual_root") != BASE_RESIDUAL_ROOT
        or base_artifact.get("result", {}).get("holes") != BASE_HOLES
    ):
        raise ValueError("retained period-55440 result drifted")

    raw = args.artifact.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact):
        raise ValueError("artifact is not canonical JSON")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-110880-lift.v1":
        raise ValueError("wrong artifact schema")
    expected_base = {
        "period": BASE_PERIOD,
        "artifact_root": BASE_ARTIFACT_ROOT,
        "assignment_root": BASE_ASSIGNMENT_ROOT,
        "residual_root": BASE_RESIDUAL_ROOT,
        "holes": BASE_HOLES,
        "lift_factor": FIBER,
    }
    if (
        artifact.get("target") != TARGET
        or artifact.get("authority") != "non_authoritative"
        or artifact.get("claim_credit") is not False
        or artifact.get("source") != SOURCE
        or artifact.get("pool_root") != POOL_ROOT
        or artifact.get("period") != PERIOD
        or artifact.get("base_stage") != expected_base
    ):
        raise ValueError("artifact provenance, authority, or base stage drifted")

    expected = [
        (prime, order)
        for prime, order in sorted(pool.items(), key=lambda item: item[1])
        if PERIOD % order == 0
    ]
    rows = artifact.get("rows")
    if artifact.get("tile_count") != 60 or not isinstance(rows, list) or len(rows) != 60:
        raise ValueError("wrong period-110880 tile count")
    for position, (row, (prime, order)) in enumerate(zip(rows, expected, strict=True)):
        verify_row(row, prime, order, position)
    base_by_prime = {row["p"]: row for row in base_artifact["rows"]}
    inherited_rows = [row for row in rows if row["p"] in base_by_prime]
    added_rows = [row for row in rows if row["p"] not in base_by_prime]
    if inherited_rows != base_artifact["rows"] or len(added_rows) != 5:
        raise ValueError("inherited assignment or factor-two family drifted")
    if {row["p"]: row["c"] for row in added_rows} != FROZEN_ASSIGNMENT:
        raise ValueError("frozen factor-two assignment drifted")
    for row in added_rows:
        factor_line_masks(row)

    base_rows = [row for row in inherited_rows if INNER_PERIOD % row["n"] == 0]
    lift_rows = [row for row in inherited_rows if INNER_PERIOD % row["n"] != 0]
    columns = np.arange(INNER_PERIOD, dtype=np.int64)
    counts = np.zeros((INNER_PERIOD, INNER_PERIOD), dtype=np.int8)
    for row in base_rows:
        for lattice_row in range(INNER_PERIOD):
            selected = (row["u"] * lattice_row + row["v"] * columns) % row["n"] == row["c"]
            counts[lattice_row, selected] += 1
    first, second = np.nonzero(counts == 0)
    first = first.astype(np.int32)
    second = second.astype(np.int32)
    low, high = residual_masks(first, second, lift_rows)
    if residual_root(first, second, low, high) != BASE_RESIDUAL_ROOT:
        raise ValueError("retained period-55440 residual does not reconstruct")
    inherited_holes = 0
    batch = 250_000
    for start in range(0, len(low), batch):
        end = start + batch
        inherited_holes += int(np.sum(popcount(low[start:end]), dtype=np.int64))
        inherited_holes += int(np.sum(popcount(high[start:end]), dtype=np.int64))
    if inherited_holes != BASE_HOLES:
        raise ValueError("retained period-55440 hole count drifted")

    holes, result_root = exact_result(first, second, low, high, added_rows)
    residual = Fraction(holes, PERIOD * PERIOD)
    expected_result = {
        "status": "exact_residual",
        "points": PERIOD * PERIOD,
        "holes": holes,
        "improvement_over_repeated_base": FIBER * FIBER * BASE_HOLES - holes,
        "assignment_root": root(canonical_bytes(rows)),
        "residual_root": result_root,
        "residual_encoding": (
            "sha256 over the domain tag, predecessor artifact root, then row-major "
            "<u2 first, <u2 second and 61 packed bytes for every period-5040 base hole; "
            "each nibble records the four period-110880 lifts of one period-55440 fiber point"
        ),
        "residual_density": str(residual),
        "covered_density": str(1 - residual),
    }
    if artifact.get("result") != expected_result:
        raise ValueError("exact factor-two residual drifted")
    search = artifact.get("search")
    if (
        not isinstance(search, dict)
        or search.get("algorithm") != "deterministic disclosed sample coordinate descent"
        or search.get("seed") != 20_311_088
        or search.get("sample_stride") != 4_093
        or search.get("starts") != 8
        or search.get("maximum_sweeps") != 6
        or search.get("exact_optimization_claim") is not False
        or search.get("tie_break") != "fewest sample holes, then lexicographically least shift vector"
    ):
        raise ValueError("sample-search disclosure drifted")

    result = {
        "schema": "erdos-frontier.erdos-203-period-110880-lift-check.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "artifact_root": root(raw),
        "status": "passed",
        "checks": [
            "frozen source commit, tree, pool, and period-55440 predecessor",
            "complete 60-tile coordinate family and five frozen factor-two shifts",
            "factor-complete count of all 12294374400 period-110880 points",
            "canonical nested residual root and exact density fractions",
            "non-authoritative and no-Claim-credit boundaries",
        ],
        "established": (
            "The retained 60-tile assignment has exactly the reported period-110880 residual "
            "under a complete four-point factor lift of the rooted predecessor."
        ),
        "not_established": [
            "an exact cover",
            "global, joint, or coordinate-wise optimality",
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

#!/usr/bin/env python3
"""Source-first checker for the Erdős 203 period-332640 factor-three lift."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
from fractions import Fraction
from typing import Any

import numpy as np

from verify_period_110880_lift import (
    COMMIT,
    INNER_PERIOD,
    NIBBLE_POPCOUNT,
    POOL_ROOT,
    SOURCE,
    TARGET,
    TREE,
    apply_factor_tile as apply_factor_two_tile,
    canonical_bytes,
    residual_masks as residual_eleven_masks,
    residual_root as residual_eleven_root,
    root,
    verify_row,
)

MIDDLE_PERIOD = 55_440
BASE_PERIOD = 110_880
PERIOD = 332_640
FIBER = 3
BASE_ARTIFACT_ROOT = "sha256:e81480fbc4275ff15d39cd09dc9597c367d12f1cf032ce421ffe8190eeb73e95"
BASE_RESIDUAL_ROOT = "sha256:6c5bb5959a374d7a680fcf8847cf4a8176fb9b516a884e6420eac99d6df38bb4"
PREDECESSOR_ARTIFACT_ROOT = "sha256:fc1fb21ad47f1c464f6870de062a5d797a670b04e3e2998921b15e3d0d16da28"
PREDECESSOR_ASSIGNMENT_ROOT = "sha256:da07f3844ea74097f8059abf2a285886a0571778d1cfdf793368b01beb1a9365"
PREDECESSOR_RESIDUAL_ROOT = "sha256:cbe0bf2de5a89c7944bbc42648a3ecde0ebadceca00ed1bd5117bbcdbe95357f"
PREDECESSOR_HOLES = 2_897_027_136
FROZEN_ASSIGNMENT = {
    109: 32,
    433: 55,
    271: 4,
    379: 38,
    541: 121,
    2377: 9,
    23761: 181,
    16633: 541,
    4159: 188,
}
MASK = (1 << (FIBER * FIBER)) - 1
PACKED_BYTES = 545
EXACT_BATCH = 250_000
RESIDUAL_DOMAIN = b"erdos203-period-332640-residual-v1\0"
MASK_POPCOUNT = np.asarray([value.bit_count() for value in range(MASK + 1)], dtype=np.uint8)


def factor_line_masks(row: dict[str, int]) -> tuple[np.uint16, np.uint16, np.uint16]:
    modulus = row["n"] // FIBER
    if (
        row["n"] != FIBER * modulus
        or BASE_PERIOD % modulus
        or (BASE_PERIOD // modulus) % FIBER == 0
    ):
        raise ValueError(f"prime {row['p']} is not a nonsingular factor-three lift")
    masks = []
    for offset in range(FIBER):
        value = 0
        for first in range(FIBER):
            for second in range(FIBER):
                if (row["u"] * first + row["v"] * second) % FIBER == offset:
                    value |= 1 << (FIBER * first + second)
        if value.bit_count() != FIBER:
            raise ValueError(f"prime {row['p']} does not cut an affine F3 line")
        masks.append(np.uint16(value))
    return masks[0], masks[1], masks[2]


def apply_factor_tile(
    masks: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    row: dict[str, int],
) -> None:
    modulus = row["n"] // FIBER
    base = (row["u"] * first + row["v"] * second) % row["n"]
    compatible = base % modulus == row["c"] % modulus
    if not np.any(compatible):
        return
    inverse = pow((BASE_PERIOD // modulus) % FIBER, -1, FIBER)
    offsets = (
        ((row["c"] // modulus) - (base[compatible] // modulus)) * inverse
    ) % FIBER
    lines = factor_line_masks(row)
    selected = np.flatnonzero(compatible)
    for offset in range(FIBER):
        positions = selected[offsets == offset]
        masks[positions] &= np.uint16(MASK ^ int(lines[offset]))


def pack_masks(packed: np.ndarray, indices: np.ndarray, position: int, masks: np.ndarray) -> None:
    bit_offset = position * FIBER * FIBER
    byte = bit_offset // 8
    shift = bit_offset % 8
    wide = masks.astype(np.uint32) << np.uint32(shift)
    packed[indices, byte] |= (wide & np.uint32(255)).astype(np.uint8)
    packed[indices, byte + 1] |= ((wide >> np.uint32(8)) & np.uint32(255)).astype(np.uint8)


def exact_result(
    first: np.ndarray,
    second: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    factor_two_rows: list[dict[str, int]],
    factor_three_rows: list[dict[str, int]],
) -> tuple[int, int, str]:
    digest = hashlib.sha256()
    digest.update(RESIDUAL_DOMAIN)
    digest.update(PREDECESSOR_ARTIFACT_ROOT.encode("ascii"))
    dtype = np.dtype([("first", "<u2"), ("second", "<u2"), ("fiber", "u1", (PACKED_BYTES,))])
    predecessor_holes = 0
    holes = 0
    for start in range(0, len(first), EXACT_BATCH):
        end = min(start + EXACT_BATCH, len(first))
        batch_first = first[start:end]
        batch_second = second[start:end]
        batch_low = low[start:end]
        batch_high = high[start:end]
        packed = np.zeros((end - start, PACKED_BYTES), dtype=np.uint8)
        for eleven_position in range(11 * 11):
            if eleven_position < 64:
                open_eleven = ((batch_low >> np.uint64(eleven_position)) & np.uint64(1)).astype(bool)
            else:
                open_eleven = ((batch_high >> np.uint64(eleven_position - 64)) & np.uint64(1)).astype(bool)
            if not np.any(open_eleven):
                continue
            record_eleven = np.flatnonzero(open_eleven)
            eleven_first, eleven_second = divmod(eleven_position, 11)
            middle_first = batch_first[open_eleven].astype(np.int64) + INNER_PERIOD * eleven_first
            middle_second = batch_second[open_eleven].astype(np.int64) + INNER_PERIOD * eleven_second
            factor_two = np.full(len(middle_first), np.uint8(15), dtype=np.uint8)
            for row in factor_two_rows:
                apply_factor_two_tile(factor_two, middle_first, middle_second, row)
            for two_position in range(2 * 2):
                open_two = ((factor_two >> np.uint8(two_position)) & np.uint8(1)).astype(bool)
                if not np.any(open_two):
                    continue
                record_indices = record_eleven[open_two]
                two_first, two_second = divmod(two_position, 2)
                current_first = middle_first[open_two] + MIDDLE_PERIOD * two_first
                current_second = middle_second[open_two] + MIDDLE_PERIOD * two_second
                predecessor_holes += len(current_first)
                factor_three = np.full(len(current_first), np.uint16(MASK), dtype=np.uint16)
                for row in factor_three_rows:
                    apply_factor_tile(factor_three, current_first, current_second, row)
                holes += int(np.sum(MASK_POPCOUNT[factor_three], dtype=np.int64))
                pack_masks(packed, record_indices, eleven_position * 4 + two_position, factor_three)
        records = np.empty(end - start, dtype=dtype)
        records["first"] = batch_first
        records["second"] = batch_second
        records["fiber"] = packed
        digest.update(records.tobytes())
    return predecessor_holes, holes, "sha256:" + digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--base-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--predecessor-artifact", required=True, type=pathlib.Path)
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
    base = json.loads(base_raw)
    if base_raw != canonical_bytes(base) or root(base_raw) != BASE_ARTIFACT_ROOT:
        raise ValueError("period-55440 base artifact drifted")
    if base.get("result", {}).get("residual_root") != BASE_RESIDUAL_ROOT:
        raise ValueError("period-55440 base residual drifted")
    predecessor_raw = args.predecessor_artifact.read_bytes()
    predecessor = json.loads(predecessor_raw)
    if predecessor_raw != canonical_bytes(predecessor) or root(predecessor_raw) != PREDECESSOR_ARTIFACT_ROOT:
        raise ValueError("period-110880 predecessor artifact drifted")
    if (
        predecessor.get("result", {}).get("assignment_root") != PREDECESSOR_ASSIGNMENT_ROOT
        or predecessor.get("result", {}).get("residual_root") != PREDECESSOR_RESIDUAL_ROOT
        or predecessor.get("result", {}).get("holes") != PREDECESSOR_HOLES
    ):
        raise ValueError("period-110880 predecessor result drifted")

    raw = args.artifact.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact):
        raise ValueError("artifact is not canonical JSON")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-332640-lift.v1":
        raise ValueError("wrong artifact schema")
    expected_base = {
        "period": BASE_PERIOD,
        "artifact_root": PREDECESSOR_ARTIFACT_ROOT,
        "assignment_root": PREDECESSOR_ASSIGNMENT_ROOT,
        "residual_root": PREDECESSOR_RESIDUAL_ROOT,
        "holes": PREDECESSOR_HOLES,
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
    if artifact.get("tile_count") != 69 or not isinstance(rows, list) or len(rows) != 69:
        raise ValueError("wrong period-332640 tile count")
    for position, (row, (prime, order)) in enumerate(zip(rows, expected, strict=True)):
        verify_row(row, prime, order, position)
    predecessor_by_prime = {row["p"]: row for row in predecessor["rows"]}
    inherited_rows = [row for row in rows if row["p"] in predecessor_by_prime]
    factor_three_rows = [row for row in rows if row["p"] not in predecessor_by_prime]
    if inherited_rows != predecessor["rows"] or len(factor_three_rows) != 9:
        raise ValueError("inherited assignment or factor-three family drifted")
    if {row["p"]: row["c"] for row in factor_three_rows} != FROZEN_ASSIGNMENT:
        raise ValueError("frozen factor-three assignment drifted")
    for row in factor_three_rows:
        factor_line_masks(row)

    base_primes = {row["p"] for row in base["rows"]}
    factor_two_rows = [row for row in predecessor["rows"] if row["p"] not in base_primes]
    if len(factor_two_rows) != 5:
        raise ValueError("factor-two predecessor family drifted")
    inner_rows = [row for row in base["rows"] if INNER_PERIOD % row["n"] == 0]
    eleven_rows = [row for row in base["rows"] if INNER_PERIOD % row["n"] != 0]
    columns = np.arange(INNER_PERIOD, dtype=np.int64)
    counts = np.zeros((INNER_PERIOD, INNER_PERIOD), dtype=np.int8)
    for row in inner_rows:
        for lattice_row in range(INNER_PERIOD):
            selected = (row["u"] * lattice_row + row["v"] * columns) % row["n"] == row["c"]
            counts[lattice_row, selected] += 1
    first, second = np.nonzero(counts == 0)
    first = first.astype(np.int32)
    second = second.astype(np.int32)
    low, high = residual_eleven_masks(first, second, eleven_rows)
    if residual_eleven_root(first, second, low, high) != BASE_RESIDUAL_ROOT:
        raise ValueError("period-55440 residual does not reconstruct")

    predecessor_holes, holes, result_root = exact_result(
        first, second, low, high, factor_two_rows, factor_three_rows
    )
    if predecessor_holes != PREDECESSOR_HOLES:
        raise ValueError("period-110880 predecessor hole count does not reconstruct")
    residual = Fraction(holes, PERIOD * PERIOD)
    expected_result = {
        "status": "exact_residual",
        "points": PERIOD * PERIOD,
        "holes": holes,
        "improvement_over_repeated_base": FIBER * FIBER * PREDECESSOR_HOLES - holes,
        "assignment_root": root(canonical_bytes(rows)),
        "residual_root": result_root,
        "residual_encoding": (
            "sha256 over the domain tag, predecessor artifact root, then row-major <u2 first, "
            f"<u2 second and {PACKED_BYTES} packed bytes for every period-5040 base hole; "
            "each nine-bit mask records the period-332640 lifts of one period-110880 fiber point"
        ),
        "residual_density": str(residual),
        "covered_density": str(1 - residual),
    }
    if artifact.get("result") != expected_result:
        raise ValueError("exact factor-three residual drifted")
    search = artifact.get("search")
    if (
        not isinstance(search, dict)
        or search.get("algorithm") != "deterministic disclosed sample coordinate descent"
        or search.get("seed") != 203_332_640
        or search.get("sample_stride") != 32_771
        or search.get("starts") != 12
        or search.get("maximum_sweeps") != 8
        or search.get("exact_optimization_claim") is not False
        or search.get("tie_break") != "fewest sample holes, then lexicographically least shift vector"
    ):
        raise ValueError("sample-search disclosure drifted")

    result = {
        "schema": "erdos-frontier.erdos-203-period-332640-lift-check.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "artifact_root": root(raw),
        "status": "passed",
        "checks": [
            "frozen source, pool, and both rooted predecessor stages",
            "complete 69-tile family and nine frozen factor-three shifts",
            "factor-complete count of all 110649369600 period-332640 points",
            "canonical 545-byte nested residual records and exact density fractions",
            "non-authoritative and no-Claim-credit boundaries",
        ],
        "established": (
            "The retained 69-tile assignment has exactly the reported period-332640 residual "
            "under a complete nine-point factor lift of the rooted predecessor."
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

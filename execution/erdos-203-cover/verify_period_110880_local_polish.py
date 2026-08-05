#!/usr/bin/env python3
"""Exact checker for the Erdős 203 period-110880 local polish."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
from fractions import Fraction

import numpy as np

from verify_period_110880_lift import (
    COMMIT,
    INNER_PERIOD,
    NIBBLE_POPCOUNT,
    PERIOD,
    POOL_ROOT,
    SOURCE,
    TARGET,
    TREE,
    apply_factor_tile,
    canonical_bytes,
    exact_result,
    factor_line_masks,
    residual_masks,
    residual_root,
    root,
    verify_row,
)

PREDECESSOR_ARTIFACT_ROOT = "sha256:e81480fbc4275ff15d39cd09dc9597c367d12f1cf032ce421ffe8190eeb73e95"
BASE_ARTIFACT_ROOT = "sha256:6496277c7d6a3949d39e668dbf0afc20b93d96fa962860643426e139db7c221b"
BASE_ASSIGNMENT_ROOT = "sha256:b2778a164cc324b9a7d6a544660dbc54da963614c4f97cdec4cf9d734226f15f"
BASE_RESIDUAL_ROOT = "sha256:39dc3b45b2c43bf3e34948e85cb38fde1b3a4e70f9eb9d8b9ca292efff0b1034"
PREDECESSOR_RESIDUAL_ROOT = "sha256:6c5bb5959a374d7a680fcf8847cf4a8176fb9b516a884e6420eac99d6df38bb4"
BASE_HOLES = 2_904_265_474
FROZEN_ASSIGNMENT = {193: 18, 353: 101, 2113: 103, 6337: 1233, 20161: 303}


def coverage_nibbles(
    first: np.ndarray,
    second: np.ndarray,
    row: dict[str, int],
) -> np.ndarray:
    residual = np.full(len(first), np.uint8(15), dtype=np.uint8)
    apply_factor_tile(residual, first, second, row)
    return np.uint8(15) ^ residual


def score_shifts(
    nibbles: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    row: dict[str, int],
) -> np.ndarray:
    modulus = row["n"] // 2
    base = (row["u"] * first + row["v"] * second) % row["n"]
    residue = base % modulus
    quotient = base // modulus
    masks = factor_line_masks(row)
    scores = np.zeros(row["n"], dtype=np.int64)
    for delta in range(2):
        candidates = residue + modulus * ((quotient + delta) % 2)
        weights = NIBBLE_POPCOUNT[nibbles & masks[delta]].astype(np.int64)
        scores += np.bincount(candidates, weights=weights, minlength=row["n"]).astype(np.int64)
    return scores


def exact_best_responses(
    first: np.ndarray,
    second: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    rows: list[dict[str, int]],
) -> tuple[dict[int, int], int]:
    scores = [np.zeros(row["n"], dtype=np.int64) for row in rows]
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
        coverages = [coverage_nibbles(current_first, current_second, row) for row in rows]
        complete = np.zeros(len(current_first), dtype=np.uint8)
        for coverage in coverages:
            complete |= coverage
        holes += int(np.sum(NIBBLE_POPCOUNT[np.uint8(15) ^ complete], dtype=np.int64))
        for index, row in enumerate(rows):
            others = np.zeros(len(current_first), dtype=np.uint8)
            for other_index, coverage in enumerate(coverages):
                if other_index != index:
                    others |= coverage
            scores[index] += score_shifts(
                np.uint8(15) ^ others, current_first, current_second, row
            )
    return {
        row["p"]: int(np.argmax(values))
        for row, values in zip(rows, scores, strict=True)
    }, holes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--predecessor-artifact", required=True, type=pathlib.Path)
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

    predecessor_raw = args.predecessor_artifact.read_bytes()
    predecessor = json.loads(predecessor_raw)
    if predecessor_raw != canonical_bytes(predecessor) or root(predecessor_raw) != PREDECESSOR_ARTIFACT_ROOT:
        raise ValueError("period-55440 predecessor drifted")
    if predecessor.get("result", {}).get("residual_root") != PREDECESSOR_RESIDUAL_ROOT:
        raise ValueError("period-55440 predecessor residual drifted")
    base_raw = args.base_artifact.read_bytes()
    base = json.loads(base_raw)
    if base_raw != canonical_bytes(base) or root(base_raw) != BASE_ARTIFACT_ROOT:
        raise ValueError("period-110880 base artifact drifted")
    if (
        base.get("result", {}).get("assignment_root") != BASE_ASSIGNMENT_ROOT
        or base.get("result", {}).get("residual_root") != BASE_RESIDUAL_ROOT
        or base.get("result", {}).get("holes") != BASE_HOLES
    ):
        raise ValueError("period-110880 base result drifted")

    raw = args.artifact.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact):
        raise ValueError("artifact is not canonical JSON")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-110880-local-polish.v1":
        raise ValueError("wrong artifact schema")
    expected_base = {
        "artifact_root": BASE_ARTIFACT_ROOT,
        "assignment_root": BASE_ASSIGNMENT_ROOT,
        "residual_root": BASE_RESIDUAL_ROOT,
        "holes": BASE_HOLES,
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
    base_by_prime = {row["p"]: row for row in base["rows"]}
    added_primes = set(FROZEN_ASSIGNMENT)
    for row in rows:
        predecessor_row = base_by_prime.get(row["p"])
        if predecessor_row is None:
            raise ValueError(f"unexpected tile prime {row['p']}")
        if row["p"] not in added_primes and row != predecessor_row:
            raise ValueError(f"inherited shift drifted for prime {row['p']}")
        if {key: row[key] for key in ("p", "n", "g", "u", "v")} != {
            key: predecessor_row[key] for key in ("p", "n", "g", "u", "v")
        }:
            raise ValueError(f"coordinate map drifted for prime {row['p']}")
    added_rows = [row for row in rows if row["p"] in added_primes]
    if {row["p"]: row["c"] for row in added_rows} != FROZEN_ASSIGNMENT:
        raise ValueError("frozen local assignment drifted")

    predecessor_rows = predecessor["rows"]
    base_rows = [row for row in predecessor_rows if INNER_PERIOD % row["n"] == 0]
    lift_rows = [row for row in predecessor_rows if INNER_PERIOD % row["n"] != 0]
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
    if residual_root(first, second, low, high) != PREDECESSOR_RESIDUAL_ROOT:
        raise ValueError("period-55440 residual does not reconstruct")

    best, scored_holes = exact_best_responses(first, second, low, high, added_rows)
    if best != FROZEN_ASSIGNMENT:
        raise ValueError(f"factor-two shifts are not coordinate-optimal: {best}")
    holes, result_root = exact_result(first, second, low, high, added_rows)
    if holes != scored_holes:
        raise ValueError("independent residual paths disagree")
    residual = Fraction(holes, PERIOD * PERIOD)
    expected_result = {
        "status": "exact_residual",
        "points": PERIOD * PERIOD,
        "holes": holes,
        "improvement_over_base": BASE_HOLES - holes,
        "assignment_root": root(canonical_bytes(rows)),
        "residual_root": result_root,
        "residual_encoding": (
            "sha256 over the domain tag, period-55440 predecessor artifact root, then row-major "
            "<u2 first, <u2 second and 61 packed bytes for every period-5040 base hole; "
            "each nibble records the four period-110880 lifts of one period-55440 fiber point"
        ),
        "residual_density": str(residual),
        "covered_density": str(1 - residual),
    }
    if artifact.get("result") != expected_result:
        raise ValueError("exact polished residual drifted")
    search = artifact.get("search")
    if (
        not isinstance(search, dict)
        or search.get("algorithm") != "deterministic exact synchronous best-response sweeps"
        or search.get("maximum_sweeps") != 4
        or search.get("fixed_inherited_tiles") != 55
        or search.get("movable_factor-two_tiles") != 5
        or search.get("tie_break") != "least shift"
        or search.get("coordinatewise_optimal") is not True
        or not isinstance(search.get("traces"), list)
        or not search["traces"]
        or search["traces"][-1].get("changed_shifts") != 0
        or search["traces"][-1].get("holes") != holes
    ):
        raise ValueError("exact search contract drifted")

    result = {
        "schema": "erdos-frontier.erdos-203-period-110880-local-polish-check.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "artifact_root": root(raw),
        "status": "passed",
        "checks": [
            "frozen source, pool, period-55440 predecessor, and period-110880 base",
            "complete 60-tile family with all 55 inherited shifts fixed",
            "factor-complete count and canonical residual root for all 12294374400 points",
            "least-shift exact best response for every one of the five movable tiles",
            "non-authoritative and no-Claim-credit boundaries",
        ],
        "established": (
            "The retained assignment has exactly the reported residual and is least-shift "
            "coordinate-wise optimal for the five factor-two tiles while all 55 inherited shifts remain fixed."
        ),
        "not_established": [
            "an exact cover",
            "joint or global optimality",
            "optimality after moving any inherited shift",
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

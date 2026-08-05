#!/usr/bin/env python3
"""Exact local polish of the five Erdős 203 factor-two lift shifts."""

from __future__ import annotations

import argparse
import json
import pathlib
from fractions import Fraction
from typing import Any

import numpy as np

from period_110880_lift import (
    BASE_PERIOD,
    INNER_PERIOD,
    NIBBLE_POPCOUNT,
    PERIOD,
    apply_factor_tile,
    canonical_bytes,
    exact_result,
    factor_line_masks,
    load_base,
    score_shifts,
    sha256_root,
)
from search_5040_cegar import POOL_ROOT, SOURCE, TARGET

BASE_ARTIFACT_ROOT = "sha256:6496277c7d6a3949d39e668dbf0afc20b93d96fa962860643426e139db7c221b"
BASE_ASSIGNMENT_ROOT = "sha256:b2778a164cc324b9a7d6a544660dbc54da963614c4f97cdec4cf9d734226f15f"
BASE_RESIDUAL_ROOT = "sha256:39dc3b45b2c43bf3e34948e85cb38fde1b3a4e70f9eb9d8b9ca292efff0b1034"
BASE_HOLES = 2_904_265_474
MAX_SWEEPS = 4
FROZEN_ASSIGNMENT = {193: 18, 353: 101, 2113: 103, 6337: 1233, 20161: 303}


def coverage_nibbles(
    first: np.ndarray,
    second: np.ndarray,
    row: Any,
    shift: int,
) -> np.ndarray:
    residual = np.full(len(first), np.uint8(15), dtype=np.uint8)
    apply_factor_tile(residual, first, second, row, shift)
    return np.uint8(15) ^ residual


def exact_best_responses(
    first: np.ndarray,
    second: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    rows: list[Any],
    assignment: np.ndarray,
) -> tuple[np.ndarray, int]:
    scores = [np.zeros(row.n, dtype=np.int64) for row in rows]
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
        coverages = [
            coverage_nibbles(current_first, current_second, row, int(shift))
            for row, shift in zip(rows, assignment, strict=True)
        ]
        complete = np.zeros(len(current_first), dtype=np.uint8)
        for coverage in coverages:
            complete |= coverage
        holes += int(np.sum(NIBBLE_POPCOUNT[np.uint8(15) ^ complete], dtype=np.int64))
        for index, row in enumerate(rows):
            others = np.zeros(len(current_first), dtype=np.uint8)
            for other_index, coverage in enumerate(coverages):
                if other_index != index:
                    others |= coverage
            residual = np.uint8(15) ^ others
            scores[index] += score_shifts(residual, current_first, current_second, row)
    return np.asarray([int(np.argmax(values)) for values in scores], dtype=np.int32), holes


def load_current(
    source: pathlib.Path,
    predecessor_path: pathlib.Path,
    artifact_path: pathlib.Path,
) -> tuple[list[Any], np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    all_tiles, added, first, second, low, high, _ = load_base(source, predecessor_path)
    raw = artifact_path.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact) or sha256_root(raw) != BASE_ARTIFACT_ROOT:
        raise ValueError("retained period-110880 lift artifact drifted")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-110880-lift.v1":
        raise ValueError("wrong retained period-110880 artifact schema")
    rows = artifact.get("rows")
    if not isinstance(rows, list) or len(rows) != len(all_tiles):
        raise ValueError("retained period-110880 tile family drifted")
    shifts = {row["p"]: int(row["c"]) for row in rows}
    for tile in added:
        factor_line_masks(tile)
    return (
        added,
        np.asarray([shifts[tile.p] for tile in added], dtype=np.int32),
        first,
        second,
        low,
        high,
    )


def explore(
    rows: list[Any],
    assignment: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
) -> dict[str, Any]:
    traces = []
    for sweep in range(MAX_SWEEPS):
        best, holes = exact_best_responses(first, second, low, high, rows, assignment)
        changed = int(np.count_nonzero(best != assignment))
        traces.append(
            {
                "sweep": sweep,
                "holes": holes,
                "changed_shifts": changed,
                "assignment": {
                    str(row.p): int(shift)
                    for row, shift in zip(rows, assignment, strict=True)
                },
                "best_responses": {
                    str(row.p): int(shift)
                    for row, shift in zip(rows, best, strict=True)
                },
            }
        )
        if changed == 0:
            return {"converged": True, "traces": traces}
        assignment = best
    return {"converged": False, "traces": traces}


def build(
    source: pathlib.Path,
    predecessor_artifact: pathlib.Path,
    base_artifact: pathlib.Path,
) -> dict[str, Any]:
    rows, assignment, first, second, low, high = load_current(
        source, predecessor_artifact, base_artifact
    )
    exploration = explore(rows, assignment, first, second, low, high)
    if not exploration["converged"]:
        raise ValueError("exact best-response sweeps did not converge")
    final_map = exploration["traces"][-1]["assignment"]
    frozen = {str(prime): shift for prime, shift in FROZEN_ASSIGNMENT.items()}
    if final_map != frozen:
        raise ValueError(f"exact local assignment drifted: {final_map}")
    final_assignment = np.asarray(
        [FROZEN_ASSIGNMENT[row.p] for row in rows], dtype=np.int32
    )
    holes, result_root = exact_result(
        first, second, low, high, rows, final_assignment
    )
    if holes != exploration["traces"][-1]["holes"]:
        raise ValueError("exact residual count disagrees with best-response sweep")

    base_raw = base_artifact.read_bytes()
    base = json.loads(base_raw)
    shifts = FROZEN_ASSIGNMENT
    retained_rows = []
    for row in base["rows"]:
        if row["p"] in shifts:
            row = dict(row)
            row["c"] = shifts[row["p"]]
        retained_rows.append(row)
    residual = Fraction(holes, PERIOD * PERIOD)
    return {
        "schema": "erdos-frontier.erdos-203-period-110880-local-polish.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": SOURCE["campaign"],
        "pool_root": POOL_ROOT,
        "period": PERIOD,
        "tile_count": len(retained_rows),
        "base_stage": {
            "artifact_root": sha256_root(base_raw),
            "assignment_root": BASE_ASSIGNMENT_ROOT,
            "residual_root": BASE_RESIDUAL_ROOT,
            "holes": BASE_HOLES,
        },
        "search": {
            "algorithm": "deterministic exact synchronous best-response sweeps",
            "maximum_sweeps": MAX_SWEEPS,
            "fixed_inherited_tiles": 55,
            "movable_factor-two_tiles": len(rows),
            "tie_break": "least shift",
            "traces": exploration["traces"],
            "coordinatewise_optimal": True,
        },
        "rows": retained_rows,
        "result": {
            "status": "exact_residual",
            "points": PERIOD * PERIOD,
            "holes": holes,
            "improvement_over_base": BASE_HOLES - holes,
            "assignment_root": sha256_root(canonical_bytes(retained_rows)),
            "residual_root": result_root,
            "residual_encoding": (
                "sha256 over the domain tag, period-55440 predecessor artifact root, then row-major "
                "<u2 first, <u2 second and 61 packed bytes for every period-5040 base hole; "
                "each nibble records the four period-110880 lifts of one period-55440 fiber point"
            ),
            "residual_density": str(residual),
            "covered_density": str(1 - residual),
        },
        "next_obligation": (
            "Lift this exact five-coordinate local residual through factor three, the best remaining "
            "compatible density-per-fiber candidate; only a zero-hole certificate can enter the verifier."
        ),
        "nonclaims": [
            "This assignment is not an exact cover.",
            "Five-coordinate optimality with 55 inherited shifts fixed is not joint or global optimality.",
            "A bounded period-110880 residual is not evidence that no finite cover exists.",
            "This producer result is not a Vela Verification or Decision.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--predecessor-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--base-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--explore-only", action="store_true")
    args = parser.parse_args()
    source = args.campaign_source.resolve()
    predecessor = args.predecessor_artifact.resolve()
    base = args.base_artifact.resolve()
    if args.explore_only:
        rows, assignment, first, second, low, high = load_current(
            source, predecessor, base
        )
        result = explore(rows, assignment, first, second, low, high)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["converged"] else 1
    if args.output is None:
        parser.error("--output is required unless --explore-only is used")
    result = build(source, predecessor, base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({"output": str(args.output), "result": result["result"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

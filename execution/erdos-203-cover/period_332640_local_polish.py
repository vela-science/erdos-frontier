#!/usr/bin/env python3
"""Exact local polish of the nine Erdős 203 factor-three lift shifts."""

from __future__ import annotations

import argparse
import json
import pathlib
import time
from fractions import Fraction
from typing import Any

import numpy as np

from period_110880_lift import INNER_PERIOD, apply_factor_tile as apply_factor_two_tile
from period_332640_lift import (
    BASE_PERIOD,
    FIBER,
    MASK,
    MASK_POPCOUNT,
    MIDDLE_PERIOD,
    PERIOD,
    apply_factor_tile,
    canonical_bytes,
    exact_result,
    load_predecessor,
    score_shifts,
    sha256_root,
)
from search_5040_cegar import POOL_ROOT, SOURCE, TARGET

BASE_ARTIFACT_ROOT = "sha256:04ab40ff2fa896a2829aa832ec3a27188b14379c9b5dcead63230aae904aaca6"
BASE_ASSIGNMENT_ROOT = "sha256:dee2b131a6044b58b050b40ba40dc9f4d923c5740e7fd00431060d88ae50edfc"
BASE_RESIDUAL_ROOT = "sha256:f110e3f7bd3ecfe50a19c95679acdbbb6c38eebd7119ddc21c930ae1342ba956"
BASE_HOLES = 25_392_268_030
MAX_SWEEPS = 4
EXACT_BATCH = 250_000

# Frozen after the disclosed exact exploratory sweeps and before qualification.
FROZEN_ASSIGNMENT = {
    109: 7,
    433: 5,
    271: 146,
    379: 199,
    541: 503,
    2377: 365,
    23761: 632,
    16633: 1894,
    4159: 716,
}
EXPLORATORY_HOLE_COUNTS = [25_392_268_030, 25_264_276_468, 25_279_077_496, 25_283_047_186]
SELECTED_SWEEP = 1


def coverage_masks(
    first: np.ndarray,
    second: np.ndarray,
    row: Any,
    shift: int,
) -> np.ndarray:
    residual = np.full(len(first), np.uint16(MASK), dtype=np.uint16)
    apply_factor_tile(residual, first, second, row, shift)
    return np.uint16(MASK) ^ residual


def exact_best_responses(
    factor_two_tiles: list[Any],
    factor_two_assignment: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    rows: list[Any],
    assignment: np.ndarray,
    limit_base_holes: int | None = None,
) -> tuple[np.ndarray, int, int]:
    scores = [np.zeros(row.n, dtype=np.int64) for row in rows]
    holes = 0
    complete_base_holes = min(len(first), limit_base_holes or len(first))
    for start in range(0, complete_base_holes, EXACT_BATCH):
        end = min(start + EXACT_BATCH, complete_base_holes)
        batch_first = first[start:end]
        batch_second = second[start:end]
        batch_low = low[start:end]
        batch_high = high[start:end]
        for eleven_position in range(11 * 11):
            if eleven_position < 64:
                open_eleven = ((batch_low >> np.uint64(eleven_position)) & np.uint64(1)).astype(bool)
            else:
                open_eleven = ((batch_high >> np.uint64(eleven_position - 64)) & np.uint64(1)).astype(bool)
            if not np.any(open_eleven):
                continue
            eleven_first, eleven_second = divmod(eleven_position, 11)
            middle_first = batch_first[open_eleven].astype(np.int64) + INNER_PERIOD * eleven_first
            middle_second = batch_second[open_eleven].astype(np.int64) + INNER_PERIOD * eleven_second
            factor_two = np.full(len(middle_first), np.uint8(15), dtype=np.uint8)
            for tile, shift in zip(factor_two_tiles, factor_two_assignment, strict=True):
                apply_factor_two_tile(factor_two, middle_first, middle_second, tile, int(shift))
            for two_position in range(2 * 2):
                open_two = ((factor_two >> np.uint8(two_position)) & np.uint8(1)).astype(bool)
                if not np.any(open_two):
                    continue
                two_first, two_second = divmod(two_position, 2)
                current_first = middle_first[open_two] + MIDDLE_PERIOD * two_first
                current_second = middle_second[open_two] + MIDDLE_PERIOD * two_second
                coverages = [
                    coverage_masks(current_first, current_second, row, int(shift))
                    for row, shift in zip(rows, assignment, strict=True)
                ]
                prefix = [np.zeros(len(current_first), dtype=np.uint16)]
                for coverage in coverages:
                    prefix.append(prefix[-1] | coverage)
                suffix = [np.zeros(len(current_first), dtype=np.uint16) for _ in range(len(rows) + 1)]
                for index in range(len(rows) - 1, -1, -1):
                    suffix[index] = suffix[index + 1] | coverages[index]
                holes += int(np.sum(MASK_POPCOUNT[np.uint16(MASK) ^ prefix[-1]], dtype=np.int64))
                for index, row in enumerate(rows):
                    without = np.uint16(MASK) ^ (prefix[index] | suffix[index + 1])
                    scores[index] += score_shifts(without, current_first, current_second, row)
    return (
        np.asarray([int(np.argmax(values)) for values in scores], dtype=np.int32),
        holes,
        complete_base_holes,
    )


def load_current(
    source: pathlib.Path,
    predecessor_base: pathlib.Path,
    predecessor: pathlib.Path,
    artifact_path: pathlib.Path,
) -> tuple[
    list[Any],
    list[Any],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    (
        _,
        added,
        factor_two_tiles,
        factor_two_assignment,
        first,
        second,
        low,
        high,
        _,
    ) = load_predecessor(source, predecessor_base, predecessor)
    raw = artifact_path.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact) or sha256_root(raw) != BASE_ARTIFACT_ROOT:
        raise ValueError("retained period-332640 lift artifact drifted")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-332640-lift.v1":
        raise ValueError("wrong period-332640 base schema")
    if (
        artifact.get("result", {}).get("assignment_root") != BASE_ASSIGNMENT_ROOT
        or artifact.get("result", {}).get("residual_root") != BASE_RESIDUAL_ROOT
        or artifact.get("result", {}).get("holes") != BASE_HOLES
    ):
        raise ValueError("period-332640 base result drifted")
    shifts = {row["p"]: int(row["c"]) for row in artifact["rows"]}
    return (
        added,
        factor_two_tiles,
        factor_two_assignment,
        np.asarray([shifts[row.p] for row in added], dtype=np.int32),
        first,
        second,
        low,
        high,
    )


def explore(
    factor_two_tiles: list[Any],
    factor_two_assignment: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    rows: list[Any],
    assignment: np.ndarray,
) -> dict[str, Any]:
    traces = []
    for sweep in range(MAX_SWEEPS):
        best, holes, processed = exact_best_responses(
            factor_two_tiles,
            factor_two_assignment,
            first,
            second,
            low,
            high,
            rows,
            assignment,
        )
        if processed != len(first):
            raise ValueError("exact exploratory sweep was incomplete")
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
    predecessor_base: pathlib.Path,
    predecessor: pathlib.Path,
    base_artifact: pathlib.Path,
) -> dict[str, Any]:
    (
        rows,
        factor_two_tiles,
        factor_two_assignment,
        assignment,
        first,
        second,
        low,
        high,
    ) = load_current(source, predecessor_base, predecessor, base_artifact)
    if {row.p: int(shift) for row, shift in zip(rows, assignment, strict=True)} == FROZEN_ASSIGNMENT:
        raise ValueError("selected polish must differ from the retained base assignment")
    final_assignment = np.asarray([FROZEN_ASSIGNMENT[row.p] for row in rows], dtype=np.int32)
    holes, result_root, processed = exact_result(
        factor_two_tiles,
        factor_two_assignment,
        first,
        second,
        low,
        high,
        rows,
        final_assignment,
    )
    if processed != len(first) or holes != EXPLORATORY_HOLE_COUNTS[SELECTED_SWEEP]:
        raise ValueError("exact residual disagrees with the selected exploratory sweep")
    base_raw = base_artifact.read_bytes()
    base = json.loads(base_raw)
    retained_rows = []
    for row in base["rows"]:
        if row["p"] in FROZEN_ASSIGNMENT:
            row = dict(row)
            row["c"] = FROZEN_ASSIGNMENT[row["p"]]
        retained_rows.append(row)
    residual = Fraction(holes, PERIOD * PERIOD)
    return {
        "schema": "erdos-frontier.erdos-203-period-332640-polish.v1",
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
            "algorithm": "post-exploratory fixed-assignment qualification",
            "exploratory_algorithm": "deterministic exact synchronous best-response sweeps",
            "exploratory_converged": False,
            "exploratory_hole_counts": EXPLORATORY_HOLE_COUNTS,
            "exploratory_maximum_sweeps": MAX_SWEEPS,
            "selected_sweep": SELECTED_SWEEP,
            "fixed_inherited_tiles": 60,
            "movable_factor-three_tiles": len(rows),
            "selection_rule": "least exact hole count among the four disclosed assignments",
            "coordinatewise_optimal": False,
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
                "sha256 over the domain tag, period-110880 predecessor artifact root, then row-major "
                "<u2 first, <u2 second and 545 packed bytes for every period-5040 base hole; "
                "each nine-bit mask records the period-332640 lifts of one period-110880 fiber point"
            ),
            "residual_density": str(residual),
            "covered_density": str(1 - residual),
        },
        "next_obligation": (
            "Compare the improved exact residual against factor-five and inherited-shift alternatives; "
            "only a zero-hole full-pool certificate can enter the frozen verifier."
        ),
        "nonclaims": [
            "This assignment is not an exact cover.",
            "The synchronous best-response exploration did not converge and establishes no coordinate-wise optimum.",
            "The selected assignment is not a joint or global optimum.",
            "A bounded period-332640 residual is not evidence that no finite cover exists.",
            "This producer result is not a Vela Verification or Decision.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--predecessor-base-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--predecessor-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--base-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--explore-only", action="store_true")
    parser.add_argument("--benchmark-base-holes", type=int)
    args = parser.parse_args()
    source = args.campaign_source.resolve()
    predecessor_base = args.predecessor_base_artifact.resolve()
    predecessor = args.predecessor_artifact.resolve()
    base = args.base_artifact.resolve()
    (
        rows,
        factor_two_tiles,
        factor_two_assignment,
        assignment,
        first,
        second,
        low,
        high,
    ) = load_current(source, predecessor_base, predecessor, base)
    if args.benchmark_base_holes is not None:
        started = time.monotonic()
        best, holes, processed = exact_best_responses(
            factor_two_tiles,
            factor_two_assignment,
            first,
            second,
            low,
            high,
            rows,
            assignment,
            limit_base_holes=args.benchmark_base_holes,
        )
        elapsed = time.monotonic() - started
        print(json.dumps({
            "authority": "non_authoritative",
            "complete_result": False,
            "processed_base_holes": processed,
            "total_base_holes": len(first),
            "partial_holes": holes,
            "best_responses": {str(row.p): int(shift) for row, shift in zip(rows, best, strict=True)},
            "elapsed_seconds": elapsed,
            "projected_seconds_per_sweep": elapsed * len(first) / processed,
        }, sort_keys=True))
        return 0
    if args.explore_only:
        result = explore(
            factor_two_tiles,
            factor_two_assignment,
            first,
            second,
            low,
            high,
            rows,
            assignment,
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result["converged"] else 1
    if args.output is None:
        parser.error("--output is required for the retained complete run")
    result = build(source, predecessor_base, predecessor, base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({"output": str(args.output), "result": result["result"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

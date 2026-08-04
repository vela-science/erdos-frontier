#!/usr/bin/env python3
"""Versioned local-search CEGAR instrumentation for the L=5040 family."""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import time
from typing import Any

import numpy as np

from search_5040_cegar import (
    POOL_ROOT,
    SOURCE,
    TARGET,
    Tile,
    canonical_bytes,
    certificate,
    holes,
    load_tiles,
    sha256_root,
)


def requirements(tiles: list[Tile], points: list[tuple[int, int]]) -> np.ndarray:
    return np.asarray(
        [
            [(tile.u * k + tile.v * ell) % tile.n for tile in tiles]
            for k, ell in points
        ],
        dtype=np.int32,
    )


def build_buckets(required: np.ndarray) -> list[dict[int, np.ndarray]]:
    buckets: list[dict[int, np.ndarray]] = []
    for tile_index in range(required.shape[1]):
        column = required[:, tile_index]
        buckets.append(
            {
                int(shift): np.flatnonzero(column == shift)
                for shift in np.unique(column)
            }
        )
    return buckets


def counts_for(required: np.ndarray, assignment: np.ndarray) -> np.ndarray:
    return np.sum(required == assignment[np.newaxis, :], axis=1, dtype=np.int16)


def greedy_assignment(
    tiles: list[Tile], buckets: list[dict[int, np.ndarray]], points: int
) -> np.ndarray:
    assignment = np.zeros(len(tiles), dtype=np.int32)
    counts = np.zeros(points, dtype=np.int16)
    for tile_index, tile in enumerate(tiles):
        choices = buckets[tile_index]
        shift = max(
            range(tile.n),
            key=lambda value: (
                int(np.count_nonzero(counts[choices.get(value, ())] == 0))
                if value in choices
                else 0,
                -value,
            ),
        )
        assignment[tile_index] = shift
        indices = choices.get(shift)
        if indices is not None:
            counts[indices] += 1
    return assignment


def solve_points(
    tiles: list[Tile],
    required: np.ndarray,
    seed: int,
    move_budget: int,
    prior: np.ndarray | None,
    deadline: float,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    rng = random.Random(seed)
    buckets = build_buckets(required)
    best_assignment: np.ndarray | None = None
    best_uncovered = required.shape[0] + 1
    moves = 0
    restarts = 0
    stagnant = 0
    assignment = (
        prior.copy()
        if prior is not None
        else greedy_assignment(tiles, buckets, required.shape[0])
    )
    counts = counts_for(required, assignment)

    while moves < move_budget and time.monotonic() < deadline:
        uncovered = np.flatnonzero(counts == 0)
        current = len(uncovered)
        if current == 0:
            return assignment, {
                "moves": moves,
                "restarts": restarts,
                "best_uncovered": 0,
            }
        if current < best_uncovered:
            best_uncovered = current
            best_assignment = assignment.copy()
            stagnant = 0
        else:
            stagnant += 1

        point = int(uncovered[rng.randrange(current)])
        candidates: list[tuple[int, float, int, int]] = []
        for tile_index, tile in enumerate(tiles):
            old_shift = int(assignment[tile_index])
            new_shift = int(required[point, tile_index])
            if old_shift == new_shift:
                continue
            old_indices = buckets[tile_index].get(old_shift)
            new_indices = buckets[tile_index][new_shift]
            loss = (
                int(np.count_nonzero(counts[old_indices] == 1))
                if old_indices is not None
                else 0
            )
            gain = int(np.count_nonzero(counts[new_indices] == 0))
            candidates.append((loss - gain, rng.random(), tile_index, new_shift))
        if not candidates:
            break
        candidates.sort()
        if rng.random() < 0.035:
            _, _, tile_index, new_shift = candidates[rng.randrange(len(candidates))]
        else:
            _, _, tile_index, new_shift = candidates[0]
        old_shift = int(assignment[tile_index])
        old_indices = buckets[tile_index].get(old_shift)
        if old_indices is not None:
            counts[old_indices] -= 1
        counts[buckets[tile_index][new_shift]] += 1
        assignment[tile_index] = new_shift
        moves += 1

        if stagnant >= 10_000:
            restarts += 1
            stagnant = 0
            assignment = np.asarray(
                [
                    rng.choice(tuple(bucket)) if bucket else rng.randrange(tile.n)
                    for tile, bucket in zip(tiles, buckets, strict=True)
                ],
                dtype=np.int32,
            )
            counts = counts_for(required, assignment)

    return None, {
        "moves": moves,
        "restarts": restarts,
        "best_uncovered": best_uncovered,
        "best_assignment": best_assignment.tolist() if best_assignment is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--period", type=int, default=5040)
    parser.add_argument("--wall-seconds", type=int, default=3600)
    parser.add_argument("--max-iterations", type=int, default=200)
    parser.add_argument("--moves-per-iteration", type=int, default=500_000)
    parser.add_argument("--holes-per-iteration", type=int, default=512)
    parser.add_argument("--initial-points", type=int, default=2048)
    parser.add_argument("--candidate", type=pathlib.Path)
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    tiles = load_tiles(args.campaign_source.resolve(), args.period)
    if args.period == 5040 and len(tiles) != 31:
        raise SystemExit(f"expected 31 frozen tiles, found {len(tiles)}")

    rng = random.Random(203_5040)
    point_set = {
        (rng.randrange(args.period), rng.randrange(args.period))
        for _ in range(args.initial_points)
    }
    while len(point_set) < args.initial_points:
        point_set.add((rng.randrange(args.period), rng.randrange(args.period)))
    points = sorted(point_set)
    started = time.monotonic()
    deadline = started + args.wall_seconds
    assignment: np.ndarray | None = None
    result: dict[str, Any] = {
        "schema": "erdos-frontier.erdos-203-search-5040-minconflicts-result.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "period": args.period,
        "tiles": len(tiles),
        "density": sum(1 / tile.n for tile in tiles),
        "source": SOURCE["campaign"],
        "pool_root": POOL_ROOT,
        "algorithm": "deterministic-seed min-conflicts CEGAR over exact torus points",
        "iterations": [],
        "nonclaims": [
            "This engineering iteration is not a fresh context-isolated scientific episode.",
            "Local-search failure is not UNSAT for the selected family.",
            "A bounded null is not evidence that no finite cover exists.",
            "A candidate requires the frozen independent verifier and human Decision boundary.",
        ],
    }
    status = "budget_exhausted"
    for iteration in range(args.max_iterations):
        if time.monotonic() >= deadline:
            break
        required = requirements(tiles, points)
        assignment, metrics = solve_points(
            tiles,
            required,
            203_5040 + iteration,
            args.moves_per_iteration,
            assignment,
            deadline,
        )
        entry: dict[str, Any] = {
            "iteration": iteration,
            "points": len(points),
            **{key: value for key, value in metrics.items() if key != "best_assignment"},
        }
        result["iterations"].append(entry)
        print(json.dumps(entry, sort_keys=True), flush=True)
        if assignment is None:
            status = "local_search_exhausted"
            break
        missing, complete_scan = holes(
            tiles,
            assignment.tolist(),
            args.period,
            args.holes_per_iteration,
            iteration % args.period,
        )
        entry["holes_found"] = len(missing)
        entry["complete_torus_scan"] = complete_scan
        if not missing and complete_scan:
            output = args.candidate or (args.work_dir / "erdos203-cover-certificate.v1.json")
            output.write_bytes(canonical_bytes(certificate(tiles, assignment.tolist())))
            entry["candidate"] = str(output)
            entry["candidate_root"] = sha256_root(output.read_bytes())
            status = "cover_candidate"
            break
        before = len(point_set)
        point_set.update(missing)
        points = sorted(point_set)
        entry["new_points"] = len(point_set) - before

    result["status"] = status
    result["wall_seconds"] = round(time.monotonic() - started, 6)
    result["registered_points"] = len(points)
    result_path = args.work_dir / "result.v2.json"
    result_path.write_bytes(canonical_bytes(result))
    print(json.dumps({"result": str(result_path), "status": status}, sort_keys=True))
    return 0 if status == "cover_candidate" else 2


if __name__ == "__main__":
    raise SystemExit(main())

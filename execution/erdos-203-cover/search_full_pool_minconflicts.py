#!/usr/bin/env python3
"""Bounded full-pool min-conflicts search for an Erdős 203 cover.

The search works on deterministic sampled lattice points and uses independent
probe batches to add counterexamples.  It may produce a candidate, but only
the dependency-free exact affine verifier can establish that the complement
is empty.  A bounded null result has no scientific authority.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import time
from fractions import Fraction
from typing import Any

import numpy as np

from search_5040_cegar import POOL_ROOT, SOURCE, TARGET, canonical_bytes, certificate, load_tiles, sha256_root
from search_5040_minconflicts import requirements, solve_points


def all_tiles(source: pathlib.Path):
    pool = {int(prime): int(order) for prime, order in json.loads((source / "compute203" / "pool_merged.json").read_bytes()).items()}
    period = math.lcm(*pool.values())
    tiles = load_tiles(source, period)
    if len(tiles) != 313:
        raise ValueError(f"expected 313 frozen tiles, found {len(tiles)}")
    return tiles, period


def points(seed: int, count: int, coordinate_bound: int) -> list[tuple[int, int]]:
    rng = random.Random(seed)
    found: set[tuple[int, int]] = set()
    while len(found) < count:
        found.add((rng.randrange(coordinate_bound), rng.randrange(coordinate_bound)))
    return sorted(found)


def uncovered_points(tiles, assignment: np.ndarray, candidates: list[tuple[int, int]]) -> list[tuple[int, int]]:
    missing: list[tuple[int, int]] = []
    batch = 8192
    for start in range(0, len(candidates), batch):
        current = candidates[start : start + batch]
        required = requirements(tiles, current)
        uncovered = np.flatnonzero(np.sum(required == assignment[np.newaxis, :], axis=1) == 0)
        missing.extend(current[int(index)] for index in uncovered)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--initial-points", type=int, default=4096)
    parser.add_argument("--probe-points", type=int, default=200000)
    parser.add_argument("--max-iterations", type=int, default=8)
    parser.add_argument("--moves-per-iteration", type=int, default=250000)
    parser.add_argument("--wall-seconds", type=int, default=900)
    parser.add_argument("--seed", type=int, default=203313)
    args = parser.parse_args()

    source = args.campaign_source.resolve()
    tiles, period = all_tiles(source)
    coordinate_bound = 1 << 31
    registered = points(args.seed, args.initial_points, coordinate_bound)
    started = time.monotonic()
    deadline = started + args.wall_seconds
    assignment = None
    iterations: list[dict[str, Any]] = []
    status = "budget_exhausted"

    for iteration in range(args.max_iterations):
        if time.monotonic() >= deadline:
            break
        required = requirements(tiles, registered)
        assignment, metrics = solve_points(
            tiles,
            required,
            args.seed + iteration,
            args.moves_per_iteration,
            assignment,
            deadline,
        )
        entry = {
            "iteration": iteration,
            "registered_points": len(registered),
            **{key: value for key, value in metrics.items() if key != "best_assignment"},
        }
        iterations.append(entry)
        print(json.dumps(entry, sort_keys=True), flush=True)
        if assignment is None:
            status = "local_search_exhausted"
            break

        probe = points(args.seed + 10000 + iteration, args.probe_points, coordinate_bound)
        missing = uncovered_points(tiles, assignment, probe)
        entry["probe_points"] = len(probe)
        entry["probe_uncovered"] = len(missing)
        entry["probe_coverage"] = str(Fraction(len(probe) - len(missing), len(probe)))
        if not missing:
            args.candidate.parent.mkdir(parents=True, exist_ok=True)
            args.candidate.write_bytes(canonical_bytes(certificate(tiles, assignment.tolist())))
            entry["candidate_root"] = sha256_root(args.candidate.read_bytes())
            status = "sampled_cover_candidate"
            break
        registered = sorted(set(registered).union(missing[:4096]))

    result: dict[str, Any] = {
        "schema": "erdos-frontier.erdos-203-full-pool-minconflicts-result.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "status": status,
        "pool": {
            "tiles": len(tiles),
            "density": str(sum((Fraction(1, tile.n) for tile in tiles), Fraction())),
            "period_bits": period.bit_length(),
            "pool_root": POOL_ROOT,
            "indispensable_low_order_primes": [5, 7, 11, 13, 17, 23],
        },
        "source": SOURCE["campaign"],
        "budget": {
            "seed": args.seed,
            "initial_points": args.initial_points,
            "probe_points_per_iteration": args.probe_points,
            "max_iterations": args.max_iterations,
            "moves_per_iteration": args.moves_per_iteration,
            "wall_seconds": args.wall_seconds,
            "coordinate_domain": [0, coordinate_bound - 1],
        },
        "iterations": iterations,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "accepted_state_change": "none",
        "nonclaims": [
            "A bounded null is not evidence that no finite cover exists.",
            "Passing sampled points is not an exact cover and is not a Verification.",
            "The heuristic search is instrumentation, not an independent scientific episode.",
            "A candidate changes no Standing unless the frozen exact verifier passes and a human Decision accepts it.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({"ok": True, "status": status, "result_root": sha256_root(args.output.read_bytes()), "iterations": len(iterations)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Exact joint coordinate polish of the retained Erdős 203 period-55440 stage."""

from __future__ import annotations

import argparse
import json
import pathlib
from fractions import Fraction
from typing import Any

import numpy as np

from period_5040_stage import add_tile
from period_55440_lift import (
    BASE_PERIOD,
    PERIOD,
    SOURCE,
    TARGET,
    canonical_bytes,
    hole_count,
    popcount,
    residual_masks,
    residual_root,
    score_shifts,
    sha256_root,
)
from search_5040_cegar import POOL_ROOT, load_tiles

BASE_ARTIFACT_ROOT = "sha256:9f7e0f7da84c9d1919c4c0ee5ef7a1902c34ca82b5cce38cdcaea75a2a18fd75"
MAX_SWEEPS = 3


def load_base(
    source: pathlib.Path, artifact_path: pathlib.Path
) -> tuple[list[Any], list[Any], np.ndarray, np.ndarray, str]:
    raw = artifact_path.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact) or sha256_root(raw) != BASE_ARTIFACT_ROOT:
        raise ValueError("retained period-55440 artifact drifted")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-55440-lift.v1":
        raise ValueError("wrong retained period-55440 schema")
    tiles = load_tiles(source, PERIOD)
    rows = artifact.get("rows")
    if not isinstance(rows, list) or len(rows) != len(tiles):
        raise ValueError("retained period-55440 family drifted")
    shifts = {}
    for tile, row in zip(tiles, rows, strict=True):
        expected = {
            "p": tile.p,
            "n": tile.n,
            "g": tile.g,
            "u": tile.u,
            "v": tile.v,
        }
        if {key: row.get(key) for key in expected} != expected:
            raise ValueError(f"retained coordinate map drifted for prime {tile.p}")
        shifts[tile.p] = int(row["c"])
    base_tiles = [tile for tile in tiles if BASE_PERIOD % tile.n == 0]
    lift_tiles = [tile for tile in tiles if BASE_PERIOD % tile.n != 0]
    return (
        base_tiles,
        lift_tiles,
        np.asarray([shifts[tile.p] for tile in base_tiles], dtype=np.int32),
        np.asarray([shifts[tile.p] for tile in lift_tiles], dtype=np.int32),
        sha256_root(raw),
    )


def optimize(
    base_tiles: list[Any],
    lift_tiles: list[Any],
    base_assignment: np.ndarray,
    lift_assignment: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict[str, int]]]:
    columns = np.arange(BASE_PERIOD, dtype=np.int64)
    counts = np.zeros((BASE_PERIOD, BASE_PERIOD), dtype=np.int8)
    for tile, shift in zip(base_tiles, base_assignment, strict=True):
        add_tile(counts, tile, int(shift), 1, columns)
    traces = []
    first = second = low = high = None
    for sweep in range(MAX_SWEEPS):
        changed_base = 0
        changed_lift = 0
        for index, tile in enumerate(base_tiles):
            if tile.p == 5:
                continue
            old_shift = int(base_assignment[index])
            add_tile(counts, tile, old_shift, -1, columns)
            first, second = np.nonzero(counts == 0)
            first = first.astype(np.int32)
            second = second.astype(np.int32)
            low, high = residual_masks(
                first, second, lift_tiles, lift_assignment
            )
            weights = popcount(low).astype(np.int64)
            weights += popcount(high).astype(np.int64)
            required = (tile.u * first + tile.v * second) % tile.n
            scores = np.bincount(required, weights=weights, minlength=tile.n)
            new_shift = int(np.argmax(scores))
            base_assignment[index] = new_shift
            changed_base += new_shift != old_shift
            add_tile(counts, tile, new_shift, 1, columns)

        first, second = np.nonzero(counts == 0)
        first = first.astype(np.int32)
        second = second.astype(np.int32)
        for index, tile in enumerate(lift_tiles):
            low, high = residual_masks(
                first, second, lift_tiles, lift_assignment, omitted=index
            )
            scores = score_shifts(low, high, first, second, tile)
            old_shift = int(lift_assignment[index])
            new_shift = int(np.argmax(scores))
            lift_assignment[index] = new_shift
            changed_lift += new_shift != old_shift
        low, high = residual_masks(first, second, lift_tiles, lift_assignment)
        holes = hole_count(low, high)
        traces.append(
            {
                "sweep": sweep,
                "changed_base_shifts": changed_base,
                "changed_lift_shifts": changed_lift,
                "base_holes": len(first),
                "holes": holes,
            }
        )
        if changed_base + changed_lift == 0:
            break
    if (
        first is None
        or second is None
        or low is None
        or high is None
        or not traces
        or traces[-1]["changed_base_shifts"] + traces[-1]["changed_lift_shifts"]
        != 0
    ):
        raise ValueError("exact joint coordinate descent did not converge")
    return base_assignment, lift_assignment, first, second, traces


def build(source: pathlib.Path, base_artifact: pathlib.Path) -> dict[str, Any]:
    (
        base_tiles,
        lift_tiles,
        base_assignment,
        lift_assignment,
        base_root,
    ) = load_base(source, base_artifact)
    base_assignment, lift_assignment, first, second, traces = optimize(
        base_tiles, lift_tiles, base_assignment, lift_assignment
    )
    low, high = residual_masks(first, second, lift_tiles, lift_assignment)
    holes = hole_count(low, high)
    residual = Fraction(holes, PERIOD * PERIOD)
    shifts = {
        tile.p: int(shift)
        for tile, shift in zip(base_tiles, base_assignment, strict=True)
    }
    shifts.update(
        {
            tile.p: int(shift)
            for tile, shift in zip(lift_tiles, lift_assignment, strict=True)
        }
    )
    all_tiles = load_tiles(source, PERIOD)
    rows = [
        {
            "p": tile.p,
            "n": tile.n,
            "g": tile.g,
            "u": tile.u,
            "v": tile.v,
            "c": shifts[tile.p],
        }
        for tile in all_tiles
    ]
    return {
        "schema": "erdos-frontier.erdos-203-period-55440-joint-polish.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": SOURCE["campaign"],
        "pool_root": POOL_ROOT,
        "period": PERIOD,
        "tile_count": len(rows),
        "base_stage": {
            "artifact_root": base_root,
            "assignment_root": "sha256:139e5d1403fad9df5884deb481f789a4e6dec7aa801f3041ac7c30bb2a75aa4e",
            "holes": 737_348_251,
        },
        "search": {
            "algorithm": "deterministic exact joint coordinate descent",
            "maximum_sweeps": MAX_SWEEPS,
            "fixed_translation_normalization": {"prime": 5, "shift": 0},
            "movable_tiles": len(rows) - 1,
            "tie_break": "least shift",
            "traces": traces,
            "coordinatewise_optimal": True,
        },
        "rows": rows,
        "result": {
            "status": "exact_residual",
            "points": PERIOD * PERIOD,
            "holes": holes,
            "improvement_over_base": 737_348_251 - holes,
            "assignment_root": sha256_root(canonical_bytes(rows)),
            "residual_root": residual_root(first, second, low, high),
            "residual_encoding": (
                "sha256 over domain tag then row-major <u2 first, <u2 second, "
                "<u8 low mask, <u8 high mask for every period-5040 base hole; "
                "fiber bit is 11*i+j for (x+5040*i,y+5040*j)"
            ),
            "residual_density": str(residual),
            "covered_density": str(1 - residual),
        },
        "next_obligation": (
            "Lift the exact joint-local residual through the cheapest useful compatible "
            "prime factor; only a zero-hole full-pool certificate can enter the frozen verifier."
        ),
        "nonclaims": [
            "This assignment is not an exact cover.",
            "Coordinate-wise optimality is not global or multi-coordinate optimality.",
            "Fixing prime 5 removes only global translation symmetry; it does not establish uniqueness.",
            "A bounded period-55440 residual is not evidence that no finite cover exists.",
            "This producer result is not a Vela Verification or Decision.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--base-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    result = build(args.campaign_source.resolve(), args.base_artifact.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({"output": str(args.output), "result": result["result"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

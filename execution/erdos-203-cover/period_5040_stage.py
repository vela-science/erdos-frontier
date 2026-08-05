#!/usr/bin/env python3
"""Exact coordinate-descent stage on the complete Erdős 203 5040 torus."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
from fractions import Fraction
from typing import Any

import numpy as np

from search_5040_cegar import (
    POOL_ROOT,
    SOURCE,
    TARGET,
    canonical_bytes,
    load_tiles,
)

PERIOD = 5040
SEED = 1
MAX_SWEEPS = 5
FIXED = {5: 0, 7: 0, 11: 0, 13: 1, 17: 3, 23: 0}


def add_tile(
    counts: np.ndarray, tile: Any, shift: int, delta: int, columns: np.ndarray
) -> None:
    for row in range(PERIOD):
        mask = (tile.u * row + tile.v * columns) % tile.n == shift
        counts[row, mask] += delta


def holes_root(counts: np.ndarray) -> str:
    packed = np.packbits((counts == 0).reshape(-1), bitorder="little")
    return "sha256:" + hashlib.sha256(packed.tobytes()).hexdigest()


def build(source: pathlib.Path) -> dict[str, Any]:
    tiles = load_tiles(source, PERIOD)
    if len(tiles) != 31:
        raise ValueError(f"expected 31 period-5040 tiles, found {len(tiles)}")
    columns = np.arange(PERIOD, dtype=np.int64)
    randomizer = random.Random(SEED)
    assignment = np.asarray(
        [FIXED.get(tile.p, randomizer.randrange(tile.n)) for tile in tiles],
        dtype=np.int32,
    )
    movable = [index for index, tile in enumerate(tiles) if tile.p not in FIXED]
    counts = np.zeros((PERIOD, PERIOD), dtype=np.int8)
    for tile, shift in zip(tiles, assignment, strict=True):
        add_tile(counts, tile, int(shift), 1, columns)

    sweeps = []
    for sweep in range(MAX_SWEEPS):
        changed = 0
        for index in movable:
            tile = tiles[index]
            old_shift = int(assignment[index])
            add_tile(counts, tile, old_shift, -1, columns)
            histogram = np.zeros(tile.n, dtype=np.int64)
            for row in range(PERIOD):
                residues = (tile.u * row + tile.v * columns) % tile.n
                histogram += np.bincount(
                    residues[counts[row] == 0], minlength=tile.n
                )
            new_shift = int(np.argmax(histogram))
            assignment[index] = new_shift
            add_tile(counts, tile, new_shift, 1, columns)
            changed += new_shift != old_shift
        missing = int(np.count_nonzero(counts == 0))
        sweeps.append({"sweep": sweep, "changed_shifts": changed, "holes": missing})
        if changed == 0:
            break

    holes = int(np.count_nonzero(counts == 0))
    total = PERIOD * PERIOD
    residual = Fraction(holes, total)
    rows = [
        {
            "p": tile.p,
            "n": tile.n,
            "g": tile.g,
            "u": tile.u,
            "v": tile.v,
            "c": int(shift),
        }
        for tile, shift in zip(tiles, assignment, strict=True)
    ]
    return {
        "schema": "erdos-frontier.erdos-203-period-stage.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": SOURCE["campaign"],
        "pool_root": POOL_ROOT,
        "period": PERIOD,
        "tile_count": len(tiles),
        "fixed_seed": {str(prime): shift for prime, shift in FIXED.items()},
        "search": {
            "algorithm": "deterministic exact-torus coordinate descent",
            "seed": SEED,
            "maximum_sweeps": MAX_SWEEPS,
            "sweeps": sweeps,
            "tie_break": "least shift",
        },
        "rows": rows,
        "result": {
            "status": "exact_residual",
            "points": total,
            "holes": holes,
            "assignment_root": "sha256:"
            + hashlib.sha256(canonical_bytes(rows)).hexdigest(),
            "holes_root": holes_root(counts),
            "packing": "row-major boolean holes, numpy packbits little-bit order",
            "residual_density": str(residual),
            "covered_density": str(1 - residual),
        },
        "next_obligation": (
            "Lift the exact rooted holes through a larger compatible period; "
            "only a zero-hole full-pool certificate can enter the frozen affine verifier."
        ),
        "nonclaims": [
            "This assignment is not an exact cover.",
            "Coordinate-descent convergence is not global optimality.",
            "A bounded period-5040 residual is not evidence that no finite cover exists.",
            "This producer result is not a Vela Verification or Decision.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    result = build(args.campaign_source.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({"output": str(args.output), "result": result["result"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Factor the exact Erdős 203 period-5040 residual through period 55440."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from fractions import Fraction
from typing import Any

import numpy as np

from period_5040_stage import PERIOD as BASE_PERIOD
from period_5040_stage import add_tile, holes_root
from search_5040_cegar import POOL_ROOT, SOURCE, TARGET, canonical_bytes, load_tiles

PERIOD = 55_440
FIBER = 11
SEED = 20_355_440
FIXED_SEED = {5: 0, 7: 0, 11: 0, 13: 1, 17: 3, 23: 0}
MAX_SWEEPS = 3
START_ASSIGNMENT = {
    23: 0,
    67: 35,
    89: 61,
    199: 197,
    331: 263,
    397: 197,
    463: 62,
    617: 321,
    661: 288,
    1321: 540,
    881: 269,
    991: 415,
    2971: 221,
    3169: 97,
    3697: 95,
    7393: 1205,
    2311: 1168,
    9241: 1570,
    5281: 2327,
    4621: 502,
    55441: 2661,
    18481: 2665,
    110881: 5826,
    332641: 5875,
}
RESIDUAL_DOMAIN = b"erdos203-period-55440-residual-v1\0"
MASK64 = (1 << 64) - 1
MASK57 = (1 << 57) - 1


def sha256_root(raw: bytes) -> str:
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


def line_masks(tile: Any) -> tuple[list[np.uint64], list[np.uint64]]:
    low = []
    high = []
    for offset in range(FIBER):
        value = 0
        for first in range(FIBER):
            for second in range(FIBER):
                if (tile.u * first + tile.v * second) % FIBER == offset:
                    value |= 1 << (FIBER * first + second)
        low.append(np.uint64(value & MASK64))
        high.append(np.uint64(value >> 64))
    return low, high


def empty_masks(size: int) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.full(size, np.uint64(MASK64), dtype=np.uint64),
        np.full(size, np.uint64(MASK57), dtype=np.uint64),
    )


def apply_lift_tile(
    low: np.ndarray,
    high: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    tile: Any,
    shift: int,
) -> None:
    modulus = tile.n // FIBER
    if tile.n != FIBER * modulus or BASE_PERIOD % modulus:
        raise ValueError(f"tile {tile.p} does not define an 11-fiber lift")
    base = (tile.u * first + tile.v * second) % tile.n
    delta = (shift - base) % tile.n
    inverse = pow((BASE_PERIOD // modulus) % FIBER, -1, FIBER)
    line_low, line_high = line_masks(tile)
    for quotient in range(FIBER):
        selected = delta == quotient * modulus
        if not np.any(selected):
            continue
        offset = quotient * inverse % FIBER
        low[selected] &= ~line_low[offset]
        high[selected] &= ~line_high[offset]


def score_shifts(
    low: np.ndarray,
    high: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    tile: Any,
) -> np.ndarray:
    modulus = tile.n // FIBER
    base = (tile.u * first + tile.v * second) % tile.n
    residue = base % modulus
    quotient = base // modulus
    inverse = pow((BASE_PERIOD // modulus) % FIBER, -1, FIBER)
    line_low, line_high = line_masks(tile)
    scores = np.zeros(tile.n, dtype=np.int64)
    for delta in range(FIBER):
        candidate = residue + modulus * ((quotient + delta) % FIBER)
        offset = delta * inverse % FIBER
        weights = popcount(low & line_low[offset]).astype(np.int64)
        weights += popcount(high & line_high[offset]).astype(np.int64)
        scores += np.bincount(candidate, weights=weights, minlength=tile.n).astype(
            np.int64
        )
    return scores


def residual_masks(
    first: np.ndarray,
    second: np.ndarray,
    tiles: list[Any],
    assignment: np.ndarray,
    omitted: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    low, high = empty_masks(len(first))
    for index, (tile, shift) in enumerate(zip(tiles, assignment, strict=True)):
        if index != omitted:
            apply_lift_tile(low, high, first, second, tile, int(shift))
    return low, high


def hole_count(low: np.ndarray, high: np.ndarray) -> int:
    batch = 250_000
    total = 0
    for start in range(0, len(low), batch):
        end = start + batch
        total += int(np.sum(popcount(low[start:end]), dtype=np.int64))
        total += int(np.sum(popcount(high[start:end]), dtype=np.int64))
    return total


def load_base_holes(
    source: pathlib.Path, base_artifact: pathlib.Path
) -> tuple[np.ndarray, np.ndarray, list[dict[str, int]], str]:
    raw = base_artifact.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact):
        raise ValueError("base period artifact is not canonical JSON")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-stage.v1":
        raise ValueError("wrong base period artifact schema")
    tiles = load_tiles(source, BASE_PERIOD)
    rows = artifact.get("rows")
    if not isinstance(rows, list) or len(rows) != len(tiles):
        raise ValueError("wrong base period tile family")
    columns = np.arange(BASE_PERIOD, dtype=np.int64)
    counts = np.zeros((BASE_PERIOD, BASE_PERIOD), dtype=np.int8)
    for tile, row in zip(tiles, rows, strict=True):
        expected = {"p": tile.p, "n": tile.n, "g": tile.g, "u": tile.u, "v": tile.v}
        if {key: row.get(key) for key in expected} != expected:
            raise ValueError(f"base coordinate map drifted for prime {tile.p}")
        add_tile(counts, tile, int(row["c"]), 1, columns)
    if artifact.get("result", {}).get("holes_root") != holes_root(counts):
        raise ValueError("base hole root drifted")
    first, second = np.nonzero(counts == 0)
    return (
        first.astype(np.int32),
        second.astype(np.int32),
        rows,
        sha256_root(raw),
    )


def optimize(
    first: np.ndarray, second: np.ndarray, tiles: list[Any]
) -> tuple[np.ndarray, list[dict[str, Any]], int]:
    fixed = {index for index, tile in enumerate(tiles) if tile.p == 23}
    if set(START_ASSIGNMENT) != {tile.p for tile in tiles}:
        raise ValueError("frozen exploratory assignment does not match lift family")
    assignment = np.asarray(
        [START_ASSIGNMENT[tile.p] for tile in tiles], dtype=np.int32
    )
    traces: list[dict[str, Any]] = []
    holes = -1
    for sweep in range(MAX_SWEEPS):
        changed = 0
        for index, tile in enumerate(tiles):
            if index in fixed:
                continue
            low, high = residual_masks(first, second, tiles, assignment, omitted=index)
            new_shift = int(np.argmax(score_shifts(low, high, first, second, tile)))
            changed += new_shift != int(assignment[index])
            assignment[index] = new_shift
        low, high = residual_masks(first, second, tiles, assignment)
        holes = hole_count(low, high)
        traces.append({"sweep": sweep, "changed_shifts": changed, "holes": holes})
        if changed == 0:
            break
    if not traces or traces[-1]["changed_shifts"] != 0:
        raise ValueError("exact coordinate descent did not converge")
    return assignment, traces, holes


def residual_root(
    first: np.ndarray, second: np.ndarray, low: np.ndarray, high: np.ndarray
) -> str:
    digest = hashlib.sha256()
    digest.update(RESIDUAL_DOMAIN)
    dtype = np.dtype([("first", "<u2"), ("second", "<u2"), ("low", "<u8"), ("high", "<u8")])
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


def build(
    source: pathlib.Path,
    base_artifact: pathlib.Path,
) -> dict[str, Any]:
    first, second, base_rows, base_root = load_base_holes(source, base_artifact)
    all_tiles = load_tiles(source, PERIOD)
    base_primes = {row["p"] for row in base_rows}
    lift_tiles = [tile for tile in all_tiles if tile.p not in base_primes]
    if len(all_tiles) != 55 or len(lift_tiles) != 24:
        raise ValueError("expected 55 period tiles with 24 new 11-fiber tiles")
    assignment, traces, exact_search_holes = optimize(first, second, lift_tiles)
    low, high = residual_masks(first, second, lift_tiles, assignment)
    holes = hole_count(low, high)
    total = PERIOD * PERIOD
    residual = Fraction(holes, total)
    lift_shifts = {
        tile.p: int(shift) for tile, shift in zip(lift_tiles, assignment, strict=True)
    }
    rows = []
    base_shifts = {row["p"]: row["c"] for row in base_rows}
    for tile in all_tiles:
        rows.append(
            {
                "p": tile.p,
                "n": tile.n,
                "g": tile.g,
                "u": tile.u,
                "v": tile.v,
                "c": int(base_shifts.get(tile.p, lift_shifts.get(tile.p))),
            }
        )
    return {
        "schema": "erdos-frontier.erdos-203-period-55440-lift.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": SOURCE["campaign"],
        "pool_root": POOL_ROOT,
        "period": PERIOD,
        "tile_count": len(all_tiles),
        "base_stage": {
            "period": BASE_PERIOD,
            "artifact_root": base_root,
            "holes": len(first),
            "holes_root": "sha256:b9e0d56de8050dbde4bf41708f20447567bc7ea56e8515ab04ada82991a893a9",
            "lift_factor": FIBER,
        },
        "fixed_seed": {str(prime): shift for prime, shift in FIXED_SEED.items()},
        "search": {
            "algorithm": "deterministic exact-residual coordinate descent",
            "seed": SEED,
            "initial_assignment_root": sha256_root(
                canonical_bytes({str(prime): shift for prime, shift in START_ASSIGNMENT.items()})
            ),
            "base_holes": len(first),
            "fiber_points": len(first) * FIBER * FIBER,
            "maximum_sweeps": MAX_SWEEPS,
            "traces": traces,
            "exact_search_holes": exact_search_holes,
            "coordinatewise_optimal": True,
            "movable_tiles": len(lift_tiles) - 1,
            "fixed_lift_tile": {"prime": 23, "shift": 0},
            "tie_break": "least shift",
        },
        "rows": rows,
        "result": {
            "status": "exact_residual",
            "points": total,
            "holes": holes,
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
            "Use the exact rooted period-55440 residual to choose the next compatible "
            "prime-factor lift; only a zero-hole full-pool certificate can enter the frozen verifier."
        ),
        "nonclaims": [
            "This assignment is not an exact cover unless the exact hole count is zero.",
            "Sampled coordinate-descent convergence is not global optimality.",
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
    result = build(
        args.campaign_source.resolve(),
        args.base_artifact.resolve(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({"output": str(args.output), "result": result["result"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

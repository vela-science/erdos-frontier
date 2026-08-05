#!/usr/bin/env python3
"""Lift the exact Erdős 203 period-55440 residual through factor two."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from fractions import Fraction
from typing import Any

import numpy as np

from period_5040_stage import add_tile
from period_55440_lift import (
    BASE_PERIOD as INNER_PERIOD,
    canonical_bytes,
    residual_masks,
    residual_root,
    sha256_root,
)
from search_5040_cegar import POOL_ROOT, SOURCE, TARGET, load_tiles

BASE_PERIOD = 55_440
PERIOD = 110_880
FIBER = 2
SAMPLE_STRIDE = 4_093
SEARCH_SEED = 20_311_088
SEARCH_STARTS = 8
MAX_SAMPLE_SWEEPS = 6
BASE_ARTIFACT_ROOT = "sha256:e81480fbc4275ff15d39cd09dc9597c367d12f1cf032ce421ffe8190eeb73e95"
BASE_ASSIGNMENT_ROOT = "sha256:f7bcfc100800467363a39847605975d785474264b2200897bc62d18a71b98eba"
BASE_RESIDUAL_ROOT = "sha256:6c5bb5959a374d7a680fcf8847cf4a8176fb9b516a884e6420eac99d6df38bb4"
BASE_HOLES = 737_345_045
RESIDUAL_DOMAIN = b"erdos203-period-110880-residual-v1\0"
NIBBLE_POPCOUNT = np.asarray([value.bit_count() for value in range(16)], dtype=np.uint8)

# Filled only after the disclosed exploratory sample search. The retained producer
# reruns that search and refuses to qualify a different assignment.
FROZEN_ASSIGNMENT = {193: 44, 353: 123, 2113: 103, 6337: 2696, 20161: 2802}


def factor_line_masks(row: Any) -> tuple[np.uint8, np.uint8]:
    modulus = row.n // FIBER
    if row.n != FIBER * modulus or BASE_PERIOD % modulus:
        raise ValueError(f"prime {row.p} does not define a factor-two lift")
    scale = (BASE_PERIOD // modulus) % FIBER
    if scale != 1:
        raise ValueError(f"prime {row.p} has a singular factor-two fiber")
    masks = []
    for offset in range(FIBER):
        mask = 0
        for first in range(FIBER):
            for second in range(FIBER):
                if (row.u * first + row.v * second) % FIBER == offset:
                    mask |= 1 << (FIBER * first + second)
        if mask.bit_count() != FIBER:
            raise ValueError(f"prime {row.p} does not cut an affine fiber line")
        masks.append(np.uint8(mask))
    return masks[0], masks[1]


def apply_factor_tile(
    nibbles: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    row: Any,
    shift: int,
) -> None:
    modulus = row.n // FIBER
    base = (row.u * first + row.v * second) % row.n
    compatible = base % modulus == shift % modulus
    if not np.any(compatible):
        return
    offsets = ((shift // modulus) - (base[compatible] // modulus)) % FIBER
    masks = factor_line_masks(row)
    selected = np.flatnonzero(compatible)
    for offset in range(FIBER):
        positions = selected[offsets == offset]
        nibbles[positions] &= np.uint8(15 ^ int(masks[offset]))


def residual_nibbles(
    first: np.ndarray,
    second: np.ndarray,
    rows: list[Any],
    assignment: np.ndarray,
    omitted: int | None = None,
) -> np.ndarray:
    nibbles = np.full(len(first), np.uint8(15), dtype=np.uint8)
    for index, (row, shift) in enumerate(zip(rows, assignment, strict=True)):
        if index != omitted:
            apply_factor_tile(nibbles, first, second, row, int(shift))
    return nibbles


def score_shifts(
    nibbles: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    row: Any,
) -> np.ndarray:
    modulus = row.n // FIBER
    base = (row.u * first + row.v * second) % row.n
    residue = base % modulus
    quotient = base // modulus
    masks = factor_line_masks(row)
    scores = np.zeros(row.n, dtype=np.int64)
    for delta in range(FIBER):
        candidates = residue + modulus * ((quotient + delta) % FIBER)
        weights = NIBBLE_POPCOUNT[nibbles & masks[delta]].astype(np.int64)
        scores += np.bincount(candidates, weights=weights, minlength=row.n).astype(
            np.int64
        )
    return scores


def load_base(
    source: pathlib.Path, artifact_path: pathlib.Path
) -> tuple[list[Any], list[Any], np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]:
    raw = artifact_path.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact) or sha256_root(raw) != BASE_ARTIFACT_ROOT:
        raise ValueError("retained period-55440 joint artifact drifted")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-55440-joint-polish.v1":
        raise ValueError("wrong retained period-55440 artifact schema")
    if artifact.get("result", {}).get("assignment_root") != BASE_ASSIGNMENT_ROOT:
        raise ValueError("retained period-55440 assignment drifted")
    if artifact.get("result", {}).get("residual_root") != BASE_RESIDUAL_ROOT:
        raise ValueError("retained period-55440 residual declaration drifted")

    period_tiles = load_tiles(source, PERIOD)
    previous = artifact.get("rows")
    if not isinstance(previous, list) or len(previous) != 55:
        raise ValueError("wrong retained period-55440 tile family")
    previous_by_prime = {row["p"]: row for row in previous}
    inherited = [tile for tile in period_tiles if tile.p in previous_by_prime]
    added = [tile for tile in period_tiles if tile.p not in previous_by_prime]
    if len(period_tiles) != 60 or len(inherited) != 55 or len(added) != 5:
        raise ValueError("expected 60 period tiles with five new factor-two tiles")
    for tile in inherited:
        row = previous_by_prime[tile.p]
        expected = {"p": tile.p, "n": tile.n, "g": tile.g, "u": tile.u, "v": tile.v}
        if {key: row.get(key) for key in expected} != expected:
            raise ValueError(f"retained coordinate map drifted for prime {tile.p}")
    for tile in added:
        factor_line_masks(tile)

    base_tiles = [tile for tile in inherited if INNER_PERIOD % tile.n == 0]
    lift_tiles = [tile for tile in inherited if INNER_PERIOD % tile.n != 0]
    shifts = {row["p"]: int(row["c"]) for row in previous}
    columns = np.arange(INNER_PERIOD, dtype=np.int64)
    counts = np.zeros((INNER_PERIOD, INNER_PERIOD), dtype=np.int8)
    for tile in base_tiles:
        add_tile(counts, tile, shifts[tile.p], 1, columns)
    first, second = np.nonzero(counts == 0)
    first = first.astype(np.int32)
    second = second.astype(np.int32)
    lift_assignment = np.asarray([shifts[tile.p] for tile in lift_tiles], dtype=np.int32)
    low, high = residual_masks(first, second, lift_tiles, lift_assignment)
    if residual_root(first, second, low, high) != BASE_RESIDUAL_ROOT:
        raise ValueError("retained period-55440 residual does not reconstruct")
    return period_tiles, added, first, second, low, high, sha256_root(raw)


def expand_sample(
    first: np.ndarray, second: np.ndarray, low: np.ndarray, high: np.ndarray
) -> tuple[np.ndarray, np.ndarray, int]:
    selected = np.arange(0, len(first), SAMPLE_STRIDE, dtype=np.int64)
    sample_first = first[selected]
    sample_second = second[selected]
    sample_low = low[selected]
    sample_high = high[selected]
    expanded_first = []
    expanded_second = []
    for position in range(11 * 11):
        if position < 64:
            open_mask = ((sample_low >> np.uint64(position)) & np.uint64(1)).astype(bool)
        else:
            open_mask = ((sample_high >> np.uint64(position - 64)) & np.uint64(1)).astype(bool)
        if not np.any(open_mask):
            continue
        fiber_first, fiber_second = divmod(position, 11)
        expanded_first.append(sample_first[open_mask].astype(np.int64) + INNER_PERIOD * fiber_first)
        expanded_second.append(sample_second[open_mask].astype(np.int64) + INNER_PERIOD * fiber_second)
    return (
        np.concatenate(expanded_first),
        np.concatenate(expanded_second),
        len(selected),
    )


def sample_search(
    first: np.ndarray, second: np.ndarray, rows: list[Any]
) -> tuple[np.ndarray, list[dict[str, int]], int]:
    rng = np.random.default_rng(SEARCH_SEED)
    starts = [np.zeros(len(rows), dtype=np.int32)]
    for _ in range(SEARCH_STARTS - 1):
        starts.append(np.asarray([rng.integers(row.n) for row in rows], dtype=np.int32))
    candidates = []
    for start_index, initial in enumerate(starts):
        assignment = initial.copy()
        traces = []
        for sweep in range(MAX_SAMPLE_SWEEPS):
            changed = 0
            for index, row in enumerate(rows):
                without = residual_nibbles(first, second, rows, assignment, omitted=index)
                new_shift = int(np.argmax(score_shifts(without, first, second, row)))
                changed += new_shift != int(assignment[index])
                assignment[index] = new_shift
            holes = int(np.sum(NIBBLE_POPCOUNT[residual_nibbles(first, second, rows, assignment)], dtype=np.int64))
            traces.append({"sweep": sweep, "changed_shifts": changed, "sample_holes": holes})
            if changed == 0:
                break
        candidates.append((holes, tuple(int(value) for value in assignment), start_index, traces))
    holes, values, start_index, traces = min(candidates)
    return np.asarray(values, dtype=np.int32), traces, start_index


def exact_result(
    first: np.ndarray,
    second: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    rows: list[Any],
    assignment: np.ndarray,
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
        nibbles = residual_nibbles(current_first, current_second, rows, assignment)
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


def build(source: pathlib.Path, base_artifact: pathlib.Path) -> dict[str, Any]:
    all_tiles, added, first, second, low, high, base_root = load_base(source, base_artifact)
    sample_first, sample_second, sampled_base_holes = expand_sample(first, second, low, high)
    assignment, traces, winning_start = sample_search(sample_first, sample_second, added)
    observed = {tile.p: int(shift) for tile, shift in zip(added, assignment, strict=True)}
    if observed != FROZEN_ASSIGNMENT:
        raise ValueError(f"sample search assignment drifted: {observed}")
    holes, result_root = exact_result(first, second, low, high, added, assignment)
    inherited_rows = {row["p"]: row for row in json.loads(base_artifact.read_bytes())["rows"]}
    added_shifts = {tile.p: int(shift) for tile, shift in zip(added, assignment, strict=True)}
    rows = []
    for tile in all_tiles:
        if tile.p in inherited_rows:
            rows.append(inherited_rows[tile.p])
        else:
            rows.append({"p": tile.p, "n": tile.n, "g": tile.g, "u": tile.u, "v": tile.v, "c": added_shifts[tile.p]})
    residual = Fraction(holes, PERIOD * PERIOD)
    return {
        "schema": "erdos-frontier.erdos-203-period-110880-lift.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": SOURCE["campaign"],
        "pool_root": POOL_ROOT,
        "period": PERIOD,
        "tile_count": len(rows),
        "base_stage": {
            "period": BASE_PERIOD,
            "artifact_root": base_root,
            "assignment_root": BASE_ASSIGNMENT_ROOT,
            "residual_root": BASE_RESIDUAL_ROOT,
            "holes": BASE_HOLES,
            "lift_factor": FIBER,
        },
        "search": {
            "algorithm": "deterministic disclosed sample coordinate descent",
            "seed": SEARCH_SEED,
            "sample_stride": SAMPLE_STRIDE,
            "sampled_base_holes": sampled_base_holes,
            "sampled_period-55440_holes": len(sample_first),
            "starts": SEARCH_STARTS,
            "maximum_sweeps": MAX_SAMPLE_SWEEPS,
            "winning_start": winning_start,
            "traces": traces,
            "tie_break": "fewest sample holes, then lexicographically least shift vector",
            "exact_optimization_claim": False,
        },
        "rows": rows,
        "result": {
            "status": "exact_residual",
            "points": PERIOD * PERIOD,
            "holes": holes,
            "improvement_over_repeated_base": FIBER * FIBER * BASE_HOLES - holes,
            "assignment_root": sha256_root(canonical_bytes(rows)),
            "residual_root": result_root,
            "residual_encoding": (
                "sha256 over the domain tag, predecessor artifact root, then row-major "
                "<u2 first, <u2 second and 61 packed bytes for every period-5040 base hole; "
                "each nibble records the four period-110880 lifts of one period-55440 fiber point"
            ),
            "residual_density": str(residual),
            "covered_density": str(1 - residual),
        },
        "next_obligation": (
            "Compare the exact marginal reduction against the next compatible prime-factor lift; "
            "only a zero-hole full-pool certificate can enter the frozen verifier."
        ),
        "nonclaims": [
            "This assignment is not an exact cover unless the exact hole count is zero.",
            "The sampled search establishes no global, joint, or coordinate-wise optimum.",
            "A bounded period-110880 residual is not evidence that no finite cover exists.",
            "This producer result is not a Vela Verification or Decision.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--base-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--explore-only", action="store_true")
    args = parser.parse_args()
    source = args.campaign_source.resolve()
    base = args.base_artifact.resolve()
    if args.explore_only:
        _, added, first, second, low, high, _ = load_base(source, base)
        sample_first, sample_second, sampled_base = expand_sample(first, second, low, high)
        assignment, traces, winning_start = sample_search(sample_first, sample_second, added)
        print(json.dumps({
            "assignment": {str(tile.p): int(shift) for tile, shift in zip(added, assignment, strict=True)},
            "sampled_base_holes": sampled_base,
            "sampled_period-55440_holes": len(sample_first),
            "winning_start": winning_start,
            "traces": traces,
        }, sort_keys=True))
        return 0
    if args.output is None:
        parser.error("--output is required unless --explore-only is used")
    result = build(source, base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({"output": str(args.output), "result": result["result"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

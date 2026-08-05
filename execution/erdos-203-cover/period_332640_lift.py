#!/usr/bin/env python3
"""Lift the exact Erdős 203 period-110880 residual through factor three."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time
from fractions import Fraction
from typing import Any

import numpy as np

from period_110880_lift import (
    INNER_PERIOD,
    apply_factor_tile as apply_factor_two_tile,
    canonical_bytes,
    load_base,
    sha256_root,
)
from search_5040_cegar import POOL_ROOT, SOURCE, TARGET, load_tiles

BASE_PERIOD = 110_880
MIDDLE_PERIOD = 55_440
PERIOD = 332_640
FIBER = 3
PREDECESSOR_ARTIFACT_ROOT = "sha256:fc1fb21ad47f1c464f6870de062a5d797a670b04e3e2998921b15e3d0d16da28"
PREDECESSOR_ASSIGNMENT_ROOT = "sha256:da07f3844ea74097f8059abf2a285886a0571778d1cfdf793368b01beb1a9365"
PREDECESSOR_RESIDUAL_ROOT = "sha256:cbe0bf2de5a89c7944bbc42648a3ecde0ebadceca00ed1bd5117bbcdbe95357f"
PREDECESSOR_HOLES = 2_897_027_136
SAMPLE_STRIDE = 32_771
SEARCH_SEED = 203_332_640
SEARCH_STARTS = 12
MAX_SAMPLE_SWEEPS = 8
EXACT_BATCH = 250_000
MASK = (1 << (FIBER * FIBER)) - 1
PACKED_BYTES = (11 * 11 * 2 * 2 * FIBER * FIBER + 7) // 8
RESIDUAL_DOMAIN = b"erdos203-period-332640-residual-v1\0"
MASK_POPCOUNT = np.asarray([value.bit_count() for value in range(MASK + 1)], dtype=np.uint8)

# Filled after the disclosed bounded sample search and before the retained run.
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


def factor_line_masks(row: Any) -> tuple[np.uint16, np.uint16, np.uint16]:
    modulus = row.n // FIBER
    if row.n != FIBER * modulus or BASE_PERIOD % modulus:
        raise ValueError(f"prime {row.p} does not define a factor-three lift")
    scale = (BASE_PERIOD // modulus) % FIBER
    if scale == 0:
        raise ValueError(f"prime {row.p} has a singular factor-three fiber")
    masks = []
    for offset in range(FIBER):
        value = 0
        for first in range(FIBER):
            for second in range(FIBER):
                if (row.u * first + row.v * second) % FIBER == offset:
                    value |= 1 << (FIBER * first + second)
        if value.bit_count() != FIBER:
            raise ValueError(f"prime {row.p} does not cut an affine F3 line")
        masks.append(np.uint16(value))
    return masks[0], masks[1], masks[2]


def apply_factor_tile(
    masks: np.ndarray,
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
    inverse = pow((BASE_PERIOD // modulus) % FIBER, -1, FIBER)
    offsets = (
        ((shift // modulus) - (base[compatible] // modulus)) * inverse
    ) % FIBER
    lines = factor_line_masks(row)
    selected = np.flatnonzero(compatible)
    for offset in range(FIBER):
        positions = selected[offsets == offset]
        masks[positions] &= np.uint16(MASK ^ int(lines[offset]))


def residual_masks(
    first: np.ndarray,
    second: np.ndarray,
    rows: list[Any],
    assignment: np.ndarray,
    omitted: int | None = None,
) -> np.ndarray:
    masks = np.full(len(first), np.uint16(MASK), dtype=np.uint16)
    for index, (row, shift) in enumerate(zip(rows, assignment, strict=True)):
        if index != omitted:
            apply_factor_tile(masks, first, second, row, int(shift))
    return masks


def score_shifts(
    masks: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    row: Any,
) -> np.ndarray:
    modulus = row.n // FIBER
    base = (row.u * first + row.v * second) % row.n
    residue = base % modulus
    quotient = base // modulus
    inverse = pow((BASE_PERIOD // modulus) % FIBER, -1, FIBER)
    lines = factor_line_masks(row)
    scores = np.zeros(row.n, dtype=np.int64)
    for delta in range(FIBER):
        candidates = residue + modulus * ((quotient + delta) % FIBER)
        offset = delta * inverse % FIBER
        weights = MASK_POPCOUNT[masks & lines[offset]].astype(np.int64)
        scores += np.bincount(candidates, weights=weights, minlength=row.n).astype(np.int64)
    return scores


def load_predecessor(
    source: pathlib.Path,
    base_artifact_path: pathlib.Path,
    predecessor_path: pathlib.Path,
) -> tuple[
    list[Any],
    list[Any],
    list[Any],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    str,
]:
    all_period_tiles = load_tiles(source, PERIOD)
    previous_tiles, factor_two_tiles, first, second, low, high, _ = load_base(
        source, base_artifact_path
    )
    raw = predecessor_path.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact) or sha256_root(raw) != PREDECESSOR_ARTIFACT_ROOT:
        raise ValueError("retained period-110880 local artifact drifted")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-110880-local-polish.v1":
        raise ValueError("wrong period-110880 predecessor schema")
    if (
        artifact.get("result", {}).get("assignment_root") != PREDECESSOR_ASSIGNMENT_ROOT
        or artifact.get("result", {}).get("residual_root") != PREDECESSOR_RESIDUAL_ROOT
        or artifact.get("result", {}).get("holes") != PREDECESSOR_HOLES
    ):
        raise ValueError("period-110880 predecessor result drifted")
    rows = artifact.get("rows")
    if not isinstance(rows, list) or len(rows) != len(previous_tiles):
        raise ValueError("period-110880 predecessor family drifted")
    rows_by_prime = {row["p"]: row for row in rows}
    for tile in previous_tiles:
        row = rows_by_prime.get(tile.p)
        expected = {"p": tile.p, "n": tile.n, "g": tile.g, "u": tile.u, "v": tile.v}
        if row is None or {key: row.get(key) for key in expected} != expected:
            raise ValueError(f"period-110880 coordinate map drifted for prime {tile.p}")
    previous_primes = set(rows_by_prime)
    added = [tile for tile in all_period_tiles if tile.p not in previous_primes]
    if len(all_period_tiles) != 69 or len(added) != 9:
        raise ValueError("expected 69 period tiles with nine new factor-three tiles")
    for tile in added:
        factor_line_masks(tile)
    factor_two_assignment = np.asarray(
        [rows_by_prime[tile.p]["c"] for tile in factor_two_tiles], dtype=np.int32
    )
    return (
        all_period_tiles,
        added,
        factor_two_tiles,
        factor_two_assignment,
        first,
        second,
        low,
        high,
        sha256_root(raw),
    )


def expand_sample(
    factor_two_tiles: list[Any],
    factor_two_assignment: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int]:
    selected = np.arange(0, len(first), SAMPLE_STRIDE, dtype=np.int64)
    sample_first = first[selected]
    sample_second = second[selected]
    sample_low = low[selected]
    sample_high = high[selected]
    expanded_first = []
    expanded_second = []
    for eleven_position in range(11 * 11):
        if eleven_position < 64:
            open_eleven = ((sample_low >> np.uint64(eleven_position)) & np.uint64(1)).astype(bool)
        else:
            open_eleven = ((sample_high >> np.uint64(eleven_position - 64)) & np.uint64(1)).astype(bool)
        if not np.any(open_eleven):
            continue
        eleven_first, eleven_second = divmod(eleven_position, 11)
        middle_first = sample_first[open_eleven].astype(np.int64) + INNER_PERIOD * eleven_first
        middle_second = sample_second[open_eleven].astype(np.int64) + INNER_PERIOD * eleven_second
        factor_two = np.full(len(middle_first), np.uint8(15), dtype=np.uint8)
        for tile, shift in zip(factor_two_tiles, factor_two_assignment, strict=True):
            apply_factor_two_tile(factor_two, middle_first, middle_second, tile, int(shift))
        for two_position in range(2 * 2):
            open_two = ((factor_two >> np.uint8(two_position)) & np.uint8(1)).astype(bool)
            if not np.any(open_two):
                continue
            two_first, two_second = divmod(two_position, 2)
            expanded_first.append(middle_first[open_two] + MIDDLE_PERIOD * two_first)
            expanded_second.append(middle_second[open_two] + MIDDLE_PERIOD * two_second)
    return np.concatenate(expanded_first), np.concatenate(expanded_second), len(selected)


def sample_search(
    first: np.ndarray,
    second: np.ndarray,
    rows: list[Any],
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
                without = residual_masks(first, second, rows, assignment, omitted=index)
                new_shift = int(np.argmax(score_shifts(without, first, second, row)))
                changed += new_shift != int(assignment[index])
                assignment[index] = new_shift
            holes = int(np.sum(MASK_POPCOUNT[residual_masks(first, second, rows, assignment)], dtype=np.int64))
            traces.append({"sweep": sweep, "changed_shifts": changed, "sample_holes": holes})
            if changed == 0:
                break
        candidates.append((holes, tuple(int(value) for value in assignment), start_index, traces))
    holes, values, start_index, traces = min(candidates)
    return np.asarray(values, dtype=np.int32), traces, start_index


def pack_masks(packed: np.ndarray, indices: np.ndarray, position: int, masks: np.ndarray) -> None:
    bit_offset = position * FIBER * FIBER
    byte = bit_offset // 8
    shift = bit_offset % 8
    wide = masks.astype(np.uint32) << np.uint32(shift)
    packed[indices, byte] |= (wide & np.uint32(255)).astype(np.uint8)
    packed[indices, byte + 1] |= ((wide >> np.uint32(8)) & np.uint32(255)).astype(np.uint8)


def exact_result(
    factor_two_tiles: list[Any],
    factor_two_assignment: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    rows: list[Any],
    assignment: np.ndarray,
    limit_base_holes: int | None = None,
) -> tuple[int, str, int]:
    digest = hashlib.sha256()
    digest.update(RESIDUAL_DOMAIN)
    digest.update(PREDECESSOR_ARTIFACT_ROOT.encode("ascii"))
    dtype = np.dtype([("first", "<u2"), ("second", "<u2"), ("fiber", "u1", (PACKED_BYTES,))])
    holes = 0
    complete_base_holes = min(len(first), limit_base_holes or len(first))
    for start in range(0, complete_base_holes, EXACT_BATCH):
        end = min(start + EXACT_BATCH, complete_base_holes)
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
            for tile, shift in zip(factor_two_tiles, factor_two_assignment, strict=True):
                apply_factor_two_tile(factor_two, middle_first, middle_second, tile, int(shift))
            for two_position in range(2 * 2):
                open_two = ((factor_two >> np.uint8(two_position)) & np.uint8(1)).astype(bool)
                if not np.any(open_two):
                    continue
                record_indices = record_eleven[open_two]
                two_first, two_second = divmod(two_position, 2)
                current_first = middle_first[open_two] + MIDDLE_PERIOD * two_first
                current_second = middle_second[open_two] + MIDDLE_PERIOD * two_second
                factor_three = residual_masks(current_first, current_second, rows, assignment)
                holes += int(np.sum(MASK_POPCOUNT[factor_three], dtype=np.int64))
                position = eleven_position * 4 + two_position
                pack_masks(packed, record_indices, position, factor_three)
        records = np.empty(end - start, dtype=dtype)
        records["first"] = batch_first
        records["second"] = batch_second
        records["fiber"] = packed
        digest.update(records.tobytes())
    return holes, "sha256:" + digest.hexdigest(), complete_base_holes


def build(
    source: pathlib.Path,
    base_artifact: pathlib.Path,
    predecessor_artifact: pathlib.Path,
) -> dict[str, Any]:
    (
        all_tiles,
        added,
        factor_two_tiles,
        factor_two_assignment,
        first,
        second,
        low,
        high,
        predecessor_root,
    ) = load_predecessor(source, base_artifact, predecessor_artifact)
    sample_first, sample_second, sampled_base_holes = expand_sample(
        factor_two_tiles, factor_two_assignment, first, second, low, high
    )
    assignment, traces, winning_start = sample_search(sample_first, sample_second, added)
    observed = {tile.p: int(shift) for tile, shift in zip(added, assignment, strict=True)}
    if observed != FROZEN_ASSIGNMENT:
        raise ValueError(f"sample search assignment drifted: {observed}")
    holes, result_root, processed = exact_result(
        factor_two_tiles,
        factor_two_assignment,
        first,
        second,
        low,
        high,
        added,
        assignment,
    )
    if processed != len(first):
        raise ValueError("complete retained run did not process every base hole")
    predecessor = json.loads(predecessor_artifact.read_bytes())
    inherited = {row["p"]: row for row in predecessor["rows"]}
    added_shifts = {tile.p: int(shift) for tile, shift in zip(added, assignment, strict=True)}
    rows = []
    for tile in all_tiles:
        if tile.p in inherited:
            rows.append(inherited[tile.p])
        else:
            rows.append({"p": tile.p, "n": tile.n, "g": tile.g, "u": tile.u, "v": tile.v, "c": added_shifts[tile.p]})
    residual = Fraction(holes, PERIOD * PERIOD)
    return {
        "schema": "erdos-frontier.erdos-203-period-332640-lift.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": SOURCE["campaign"],
        "pool_root": POOL_ROOT,
        "period": PERIOD,
        "tile_count": len(rows),
        "base_stage": {
            "period": BASE_PERIOD,
            "artifact_root": predecessor_root,
            "assignment_root": PREDECESSOR_ASSIGNMENT_ROOT,
            "residual_root": PREDECESSOR_RESIDUAL_ROOT,
            "holes": PREDECESSOR_HOLES,
            "lift_factor": FIBER,
        },
        "search": {
            "algorithm": "deterministic disclosed sample coordinate descent",
            "seed": SEARCH_SEED,
            "sample_stride": SAMPLE_STRIDE,
            "sampled_base_holes": sampled_base_holes,
            "sampled_period-110880_holes": len(sample_first),
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
            "improvement_over_repeated_base": FIBER * FIBER * PREDECESSOR_HOLES - holes,
            "assignment_root": sha256_root(canonical_bytes(rows)),
            "residual_root": result_root,
            "residual_encoding": (
                "sha256 over the domain tag, predecessor artifact root, then row-major <u2 first, "
                f"<u2 second and {PACKED_BYTES} packed bytes for every period-5040 base hole; "
                "each nine-bit mask records the period-332640 lifts of one period-110880 fiber point"
            ),
            "residual_density": str(residual),
            "covered_density": str(1 - residual),
        },
        "next_obligation": (
            "Measure the exact marginal reduction before choosing any further factor or inherited-shift polish; "
            "only a zero-hole full-pool certificate can enter the frozen verifier."
        ),
        "nonclaims": [
            "This assignment is not an exact cover unless the exact hole count is zero.",
            "The sampled search establishes no global, joint, or coordinate-wise optimum.",
            "A bounded period-332640 residual is not evidence that no finite cover exists.",
            "This producer result is not a Vela Verification or Decision.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--base-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--predecessor-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--explore-only", action="store_true")
    parser.add_argument("--benchmark-base-holes", type=int)
    args = parser.parse_args()
    source = args.campaign_source.resolve()
    base = args.base_artifact.resolve()
    predecessor = args.predecessor_artifact.resolve()
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
    ) = load_predecessor(source, base, predecessor)
    sample_first, sample_second, sampled_base = expand_sample(
        factor_two_tiles, factor_two_assignment, first, second, low, high
    )
    assignment, traces, winning_start = sample_search(sample_first, sample_second, added)
    if args.explore_only:
        print(json.dumps({
            "assignment": {str(tile.p): int(shift) for tile, shift in zip(added, assignment, strict=True)},
            "sampled_base_holes": sampled_base,
            "sampled_period-110880_holes": len(sample_first),
            "winning_start": winning_start,
            "traces": traces,
        }, sort_keys=True))
        return 0
    if args.benchmark_base_holes is not None:
        started = time.monotonic()
        holes, partial_root, processed = exact_result(
            factor_two_tiles,
            factor_two_assignment,
            first,
            second,
            low,
            high,
            added,
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
            "partial_root": partial_root,
            "elapsed_seconds": elapsed,
            "projected_seconds": elapsed * len(first) / processed,
        }, sort_keys=True))
        return 0
    if args.output is None:
        parser.error("--output is required for the retained complete run")
    result = build(source, base, predecessor)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(json.dumps({"output": str(args.output), "result": result["result"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

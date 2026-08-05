#!/usr/bin/env python3
"""Exact checker for the Erdős 203 period-55440 joint coordinate polish."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
from fractions import Fraction

import numpy as np

from verify_period_55440_lift import (
    BASE_PERIOD,
    COMMIT,
    PERIOD,
    POOL_ROOT,
    SOURCE,
    TARGET,
    canonical_bytes,
    hole_count,
    popcount,
    residual_masks,
    residual_root,
    root,
    score_shifts,
    verify_row,
)

TREE = "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a"
BASE_ARTIFACT_ROOT = "sha256:9f7e0f7da84c9d1919c4c0ee5ef7a1902c34ca82b5cce38cdcaea75a2a18fd75"
BASE_ASSIGNMENT_ROOT = "sha256:139e5d1403fad9df5884deb481f789a4e6dec7aa801f3041ac7c30bb2a75aa4e"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--base-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    source = args.campaign_source.resolve()
    commit = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    tree = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    if (commit, tree) != (COMMIT, TREE):
        raise ValueError("campaign source drifted")
    pool_raw = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_raw) != POOL_ROOT:
        raise ValueError("pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_raw).items()}

    base_raw = args.base_artifact.read_bytes()
    base_artifact = json.loads(base_raw)
    if root(base_raw) != BASE_ARTIFACT_ROOT or base_raw != canonical_bytes(base_artifact):
        raise ValueError("retained period-55440 artifact drifted")
    if base_artifact.get("result", {}).get("assignment_root") != BASE_ASSIGNMENT_ROOT:
        raise ValueError("retained period-55440 assignment drifted")

    raw = args.artifact.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact):
        raise ValueError("artifact is not canonical JSON")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-55440-joint-polish.v1":
        raise ValueError("wrong artifact schema")
    if (
        artifact.get("target") != TARGET
        or artifact.get("authority") != "non_authoritative"
        or artifact.get("claim_credit") is not False
        or artifact.get("source") != SOURCE
        or artifact.get("pool_root") != POOL_ROOT
        or artifact.get("period") != PERIOD
        or artifact.get("base_stage", {}).get("artifact_root") != BASE_ARTIFACT_ROOT
        or artifact.get("base_stage", {}).get("assignment_root")
        != BASE_ASSIGNMENT_ROOT
    ):
        raise ValueError("artifact provenance, authority, or base stage drifted")

    expected = [
        (prime, order)
        for prime, order in sorted(pool.items(), key=lambda item: item[1])
        if PERIOD % order == 0
    ]
    rows = artifact.get("rows")
    if artifact.get("tile_count") != 55 or not isinstance(rows, list) or len(rows) != 55:
        raise ValueError("wrong period-55440 tile count")
    for position, (row, (prime, order)) in enumerate(zip(rows, expected, strict=True)):
        verify_row(row, prime, order, position)
    base_rows_by_prime = {row["p"]: row for row in base_artifact["rows"]}
    for row in rows:
        predecessor = base_rows_by_prime.get(row["p"])
        if predecessor is None or {
            key: row[key] for key in ("p", "n", "g", "u", "v")
        } != {key: predecessor[key] for key in ("p", "n", "g", "u", "v")}:
            raise ValueError(f"coordinate family drifted for prime {row['p']}")
    if next(row for row in rows if row["p"] == 5)["c"] != 0:
        raise ValueError("translation normalization drifted")

    base_rows = [row for row in rows if BASE_PERIOD % row["n"] == 0]
    lift_rows = [row for row in rows if BASE_PERIOD % row["n"] != 0]
    columns = np.arange(BASE_PERIOD, dtype=np.int64)
    counts = np.zeros((BASE_PERIOD, BASE_PERIOD), dtype=np.int8)
    for row in base_rows:
        for lattice_row in range(BASE_PERIOD):
            selected = (
                row["u"] * lattice_row + row["v"] * columns
            ) % row["n"] == row["c"]
            counts[lattice_row, selected] += 1
    first, second = np.nonzero(counts == 0)
    first = first.astype(np.int32)
    second = second.astype(np.int32)
    low, high = residual_masks(first, second, lift_rows)
    holes = hole_count(low, high)
    residual = Fraction(holes, PERIOD * PERIOD)
    expected_result = {
        "status": "exact_residual",
        "points": PERIOD * PERIOD,
        "holes": holes,
        "improvement_over_base": 737_348_251 - holes,
        "assignment_root": root(canonical_bytes(rows)),
        "residual_root": residual_root(first, second, low, high),
        "residual_encoding": (
            "sha256 over domain tag then row-major <u2 first, <u2 second, "
            "<u8 low mask, <u8 high mask for every period-5040 base hole; "
            "fiber bit is 11*i+j for (x+5040*i,y+5040*j)"
        ),
        "residual_density": str(residual),
        "covered_density": str(1 - residual),
    }
    if artifact.get("result") != expected_result:
        raise ValueError("exact joint residual drifted")
    search = artifact.get("search")
    if (
        not isinstance(search, dict)
        or search.get("algorithm") != "deterministic exact joint coordinate descent"
        or search.get("fixed_translation_normalization")
        != {"prime": 5, "shift": 0}
        or search.get("movable_tiles") != 54
        or search.get("tie_break") != "least shift"
        or search.get("coordinatewise_optimal") is not True
        or not isinstance(search.get("traces"), list)
        or not search["traces"]
        or search["traces"][-1].get("changed_base_shifts") != 0
        or search["traces"][-1].get("changed_lift_shifts") != 0
        or search["traces"][-1].get("holes") != holes
    ):
        raise ValueError("search contract drifted")

    for row in base_rows:
        if row["p"] == 5:
            continue
        for lattice_row in range(BASE_PERIOD):
            selected = (
                row["u"] * lattice_row + row["v"] * columns
            ) % row["n"] == row["c"]
            counts[lattice_row, selected] -= 1
        candidate_first, candidate_second = np.nonzero(counts == 0)
        candidate_first = candidate_first.astype(np.int32)
        candidate_second = candidate_second.astype(np.int32)
        candidate_low, candidate_high = residual_masks(
            candidate_first, candidate_second, lift_rows
        )
        weights = popcount(candidate_low).astype(np.int64)
        weights += popcount(candidate_high).astype(np.int64)
        required = (
            row["u"] * candidate_first + row["v"] * candidate_second
        ) % row["n"]
        scores = np.bincount(required, weights=weights, minlength=row["n"])
        if row["c"] != int(np.argmax(scores)):
            raise ValueError(f"base prime {row['p']} is not coordinate-optimal")
        for lattice_row in range(BASE_PERIOD):
            selected = (
                row["u"] * lattice_row + row["v"] * columns
            ) % row["n"] == row["c"]
            counts[lattice_row, selected] += 1

    for index, row in enumerate(lift_rows):
        without_low, without_high = residual_masks(
            first, second, lift_rows, omitted=index
        )
        scores = score_shifts(without_low, without_high, first, second, row)
        if row["c"] != int(np.argmax(scores)):
            raise ValueError(f"lift prime {row['p']} is not coordinate-optimal")

    result = {
        "schema": "erdos-frontier.erdos-203-period-55440-joint-polish-check.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "artifact_root": root(raw),
        "status": "passed",
        "checks": [
            "frozen source commit, tree, pool, and retained period-55440 stage",
            "complete 55-tile coordinate family and prime-5 translation normalization",
            "factor-complete count of all 3073593600 period-55440 points",
            "canonical rooted residual and exact density fractions",
            "every shift for all 54 non-normalizing tiles",
        ],
        "established": (
            "The retained assignment has exactly the reported residual and is "
            "least-shift coordinate-wise optimal across all 54 movable tiles after fixing prime 5 by translation symmetry."
        ),
        "not_established": [
            "an exact cover",
            "global or multi-coordinate optimality",
            "uniqueness modulo translation",
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

#!/usr/bin/env python3
"""Source-first checker for the improved Erdős 203 period-332640 assignment."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
from fractions import Fraction

import numpy as np

from verify_period_332640_lift import (
    BASE_RESIDUAL_ROOT,
    COMMIT,
    INNER_PERIOD,
    PERIOD,
    POOL_ROOT,
    PREDECESSOR_ARTIFACT_ROOT,
    PREDECESSOR_HOLES,
    SOURCE,
    TARGET,
    TREE,
    canonical_bytes,
    exact_result,
    factor_line_masks,
    residual_eleven_masks,
    residual_eleven_root,
    root,
    verify_row,
)

PREDECESSOR_BASE_ARTIFACT_ROOT = "sha256:e81480fbc4275ff15d39cd09dc9597c367d12f1cf032ce421ffe8190eeb73e95"
BASE_ARTIFACT_ROOT = "sha256:04ab40ff2fa896a2829aa832ec3a27188b14379c9b5dcead63230aae904aaca6"
BASE_ASSIGNMENT_ROOT = "sha256:dee2b131a6044b58b050b40ba40dc9f4d923c5740e7fd00431060d88ae50edfc"
BASE_RESIDUAL_ROOT_332640 = "sha256:f110e3f7bd3ecfe50a19c95679acdbbb6c38eebd7119ddc21c930ae1342ba956"
BASE_HOLES = 25_392_268_030
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--predecessor-base-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--predecessor-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--base-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    source = args.campaign_source.resolve()
    commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD^{tree}"], text=True).strip()
    if (commit, tree) != (COMMIT, TREE):
        raise ValueError("campaign source drifted")
    pool_raw = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_raw) != POOL_ROOT:
        raise ValueError("pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_raw).items()}

    predecessor_base_raw = args.predecessor_base_artifact.read_bytes()
    predecessor_base = json.loads(predecessor_base_raw)
    if (
        predecessor_base_raw != canonical_bytes(predecessor_base)
        or root(predecessor_base_raw) != PREDECESSOR_BASE_ARTIFACT_ROOT
        or predecessor_base.get("result", {}).get("residual_root") != BASE_RESIDUAL_ROOT
    ):
        raise ValueError("period-55440 predecessor base drifted")
    predecessor_raw = args.predecessor_artifact.read_bytes()
    predecessor = json.loads(predecessor_raw)
    if predecessor_raw != canonical_bytes(predecessor) or root(predecessor_raw) != PREDECESSOR_ARTIFACT_ROOT:
        raise ValueError("period-110880 predecessor drifted")
    if predecessor.get("result", {}).get("holes") != PREDECESSOR_HOLES:
        raise ValueError("period-110880 predecessor holes drifted")
    base_raw = args.base_artifact.read_bytes()
    base = json.loads(base_raw)
    if base_raw != canonical_bytes(base) or root(base_raw) != BASE_ARTIFACT_ROOT:
        raise ValueError("period-332640 base artifact drifted")
    if (
        base.get("result", {}).get("assignment_root") != BASE_ASSIGNMENT_ROOT
        or base.get("result", {}).get("residual_root") != BASE_RESIDUAL_ROOT_332640
        or base.get("result", {}).get("holes") != BASE_HOLES
    ):
        raise ValueError("period-332640 base result drifted")

    raw = args.artifact.read_bytes()
    artifact = json.loads(raw)
    if raw != canonical_bytes(artifact):
        raise ValueError("artifact is not canonical JSON")
    if artifact.get("schema") != "erdos-frontier.erdos-203-period-332640-polish.v1":
        raise ValueError("wrong artifact schema")
    expected_base = {
        "artifact_root": BASE_ARTIFACT_ROOT,
        "assignment_root": BASE_ASSIGNMENT_ROOT,
        "residual_root": BASE_RESIDUAL_ROOT_332640,
        "holes": BASE_HOLES,
    }
    if (
        artifact.get("target") != TARGET
        or artifact.get("authority") != "non_authoritative"
        or artifact.get("claim_credit") is not False
        or artifact.get("source") != SOURCE
        or artifact.get("pool_root") != POOL_ROOT
        or artifact.get("period") != PERIOD
        or artifact.get("base_stage") != expected_base
    ):
        raise ValueError("artifact provenance, authority, or base stage drifted")

    expected = [
        (prime, order)
        for prime, order in sorted(pool.items(), key=lambda item: item[1])
        if PERIOD % order == 0
    ]
    rows = artifact.get("rows")
    if artifact.get("tile_count") != 69 or not isinstance(rows, list) or len(rows) != 69:
        raise ValueError("wrong period-332640 tile count")
    for position, (row, (prime, order)) in enumerate(zip(rows, expected, strict=True)):
        verify_row(row, prime, order, position)
    base_by_prime = {row["p"]: row for row in base["rows"]}
    movable_primes = set(FROZEN_ASSIGNMENT)
    for row in rows:
        predecessor_row = base_by_prime.get(row["p"])
        if predecessor_row is None:
            raise ValueError(f"unexpected tile prime {row['p']}")
        if row["p"] not in movable_primes and row != predecessor_row:
            raise ValueError(f"inherited shift drifted for prime {row['p']}")
        if {key: row[key] for key in ("p", "n", "g", "u", "v")} != {
            key: predecessor_row[key] for key in ("p", "n", "g", "u", "v")
        }:
            raise ValueError(f"coordinate map drifted for prime {row['p']}")
    factor_three_rows = [row for row in rows if row["p"] in movable_primes]
    if {row["p"]: row["c"] for row in factor_three_rows} != FROZEN_ASSIGNMENT:
        raise ValueError("frozen improved assignment drifted")
    for row in factor_three_rows:
        factor_line_masks(row)

    base_primes = {row["p"] for row in predecessor_base["rows"]}
    factor_two_rows = [row for row in predecessor["rows"] if row["p"] not in base_primes]
    if len(factor_two_rows) != 5:
        raise ValueError("factor-two predecessor family drifted")
    inner_rows = [row for row in predecessor_base["rows"] if INNER_PERIOD % row["n"] == 0]
    eleven_rows = [row for row in predecessor_base["rows"] if INNER_PERIOD % row["n"] != 0]
    columns = np.arange(INNER_PERIOD, dtype=np.int64)
    counts = np.zeros((INNER_PERIOD, INNER_PERIOD), dtype=np.int8)
    for row in inner_rows:
        for lattice_row in range(INNER_PERIOD):
            selected = (row["u"] * lattice_row + row["v"] * columns) % row["n"] == row["c"]
            counts[lattice_row, selected] += 1
    first, second = np.nonzero(counts == 0)
    first = first.astype(np.int32)
    second = second.astype(np.int32)
    low, high = residual_eleven_masks(first, second, eleven_rows)
    if residual_eleven_root(first, second, low, high) != BASE_RESIDUAL_ROOT:
        raise ValueError("period-55440 residual does not reconstruct")

    predecessor_holes, holes, result_root = exact_result(
        first, second, low, high, factor_two_rows, factor_three_rows
    )
    if predecessor_holes != PREDECESSOR_HOLES:
        raise ValueError("period-110880 predecessor hole count does not reconstruct")
    residual = Fraction(holes, PERIOD * PERIOD)
    expected_result = {
        "status": "exact_residual",
        "points": PERIOD * PERIOD,
        "holes": holes,
        "improvement_over_base": BASE_HOLES - holes,
        "assignment_root": root(canonical_bytes(rows)),
        "residual_root": result_root,
        "residual_encoding": (
            "sha256 over the domain tag, period-110880 predecessor artifact root, then row-major "
            "<u2 first, <u2 second and 545 packed bytes for every period-5040 base hole; "
            "each nine-bit mask records the period-332640 lifts of one period-110880 fiber point"
        ),
        "residual_density": str(residual),
        "covered_density": str(1 - residual),
    }
    if artifact.get("result") != expected_result:
        raise ValueError("exact improved residual drifted")
    search = artifact.get("search")
    if (
        not isinstance(search, dict)
        or search.get("algorithm") != "post-exploratory fixed-assignment qualification"
        or search.get("exploratory_algorithm") != "deterministic exact synchronous best-response sweeps"
        or search.get("exploratory_converged") is not False
        or search.get("exploratory_hole_counts") != EXPLORATORY_HOLE_COUNTS
        or search.get("exploratory_maximum_sweeps") != 4
        or search.get("selected_sweep") != 1
        or search.get("fixed_inherited_tiles") != 60
        or search.get("movable_factor-three_tiles") != 9
        or search.get("coordinatewise_optimal") is not False
        or search.get("selection_rule") != "least exact hole count among the four disclosed assignments"
    ):
        raise ValueError("exploratory selection disclosure drifted")

    result = {
        "schema": "erdos-frontier.erdos-203-period-332640-polish-check.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "artifact_root": root(raw),
        "status": "passed",
        "checks": [
            "frozen source, pool, period-55440 base, period-110880 predecessor, and period-332640 base",
            "complete 69-tile family with all 60 inherited shifts fixed",
            "factor-complete count and canonical residual root for all 110649369600 points",
            "exact fixed improved assignment and explicit nonconvergence disclosure",
            "non-authoritative and no-Claim-credit boundaries",
        ],
        "established": (
            "The retained fixed assignment has exactly the reported period-332640 residual "
            "and strictly improves the retained factor-three base assignment."
        ),
        "not_established": [
            "an exact cover",
            "coordinate-wise, joint, or global optimality",
            "convergence of the exploratory best-response method",
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

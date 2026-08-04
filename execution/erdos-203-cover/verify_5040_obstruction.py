#!/usr/bin/env python3
"""Independently check the bounded n-divides-5040 obstruction."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import subprocess
from fractions import Fraction
from typing import Any

from sympy import discrete_log, primitive_root

CAMPAIGN_COMMIT = "94fde841ea6ad90437bd66a91953bfeba13dba0f"
CAMPAIGN_TREE = "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a"
POOL_ROOT = "sha256:9a8f179bf6ab509c53144ac679acd8ffe42e66588b1516b0ca3a9f45e18395b3"
SCHEMA = "erdos-frontier.erdos-203-5040-structural-obstruction.v1"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def git_value(source: pathlib.Path, expression: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", expression], text=True
    ).strip()


def compatibility_index(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    u1, v1, n1 = left
    u2, v2, n2 = right
    columns = [(u1, u2), (v1, v2), (n1, 0), (0, n2)]
    return math.gcd(
        *(
            abs(a[0] * b[1] - a[1] * b[0])
            for index, a in enumerate(columns)
            for b in columns[index + 1 :]
        )
    )


def verify(source: pathlib.Path, artifact: pathlib.Path) -> dict[str, Any]:
    raw = artifact.read_bytes()
    value = json.loads(raw)
    if raw != canonical_bytes(value) or value.get("schema") != SCHEMA:
        raise ValueError("obstruction artifact is not canonical or has the wrong schema")
    if git_value(source, "HEAD") != CAMPAIGN_COMMIT:
        raise ValueError("campaign source commit drifted")
    if git_value(source, "HEAD^{tree}") != CAMPAIGN_TREE:
        raise ValueError("campaign source tree drifted")
    pool_raw = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_raw) != POOL_ROOT:
        raise ValueError("prime pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_raw).items()}
    tiles = []
    for prime, order in sorted(pool.items(), key=lambda item: item[1]):
        if 5040 % order:
            continue
        generator = pow(int(primitive_root(prime)), (prime - 1) // order, prime)
        u = int(discrete_log(prime, 2, generator)) % order
        v = int(discrete_log(prime, 3, generator)) % order
        if math.gcd(math.gcd(u, v), order) != 1:
            raise ValueError("derived a non-primitive coordinate map")
        tiles.append((u, v, order))
    density = sum((Fraction(1, tile[2]) for tile in tiles), Fraction())
    mandatory_edges = 0
    pair_mass = Fraction()
    for first, left in enumerate(tiles):
        for right in tiles[first + 1 :]:
            if compatibility_index(left, right) == 1:
                mandatory_edges += 1
                pair_mass += Fraction(1, left[2] * right[2])
    pointwise_ratio = max(
        Fraction(min(r * (r - 1) // 2, mandatory_edges), r - 1)
        for r in range(2, len(tiles) + 1)
    )
    slack = density - 1
    upper_bound = pointwise_ratio * slack
    gap = pair_mass - upper_bound
    expected = {
        "tiles": 31,
        "density": Fraction(143, 140),
        "mandatory_edges": 271,
        "pair_mass": Fraction(420493, 1270080),
        "pointwise_ratio": Fraction(271, 23),
        "upper_bound": Fraction(813, 3220),
        "gap": Fraction(2295803, 29211840),
    }
    actual = {
        "tiles": len(tiles),
        "density": density,
        "mandatory_edges": mandatory_edges,
        "pair_mass": pair_mass,
        "pointwise_ratio": pointwise_ratio,
        "upper_bound": upper_bound,
        "gap": gap,
    }
    if actual != expected or gap <= 0:
        raise ValueError(f"bounded obstruction does not reproduce: {actual}")
    proof = value.get("proof", {})
    required_strings = {
        "density_identity": "3/140",
        "fixed_pair_mass": "420493/1270080",
        "pointwise_bound": "271/23",
        "cover_upper_bound": "813/3220",
        "contradiction": "2295803/29211840",
    }
    for field, required in required_strings.items():
        if required not in str(proof.get(field, "")):
            raise ValueError(f"artifact proof field {field} lost exact value {required}")
    return {
        "schema": "erdos-frontier.erdos-203-5040-structural-obstruction-check.v1",
        "ok": True,
        "artifact_root": root(raw),
        "tiles": len(tiles),
        "density": str(density),
        "mandatory_edges": mandatory_edges,
        "mandatory_pair_mass": str(pair_mass),
        "pointwise_ratio": str(pointwise_ratio),
        "cover_pair_mass_upper_bound": str(upper_bound),
        "contradiction_gap": str(gap),
        "accepted_state_change": "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.campaign_source.resolve(), args.artifact)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        result = {
            "schema": "erdos-frontier.erdos-203-5040-structural-obstruction-check.v1",
            "ok": False,
            "error": str(error),
            "accepted_state_change": "none",
        }
    print(json.dumps(result, sort_keys=True) if args.json else result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

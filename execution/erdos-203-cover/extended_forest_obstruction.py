#!/usr/bin/env python3
"""Extend the 55440 forest obstruction across the pinned Erdős 203 pool."""

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
TARGET = "erdos:203:finite-cover"
SCHEMA = "erdos-frontier.erdos-203-extended-forest-obstruction.v1"


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
    columns = ((u1, u2), (v1, v2), (n1, 0), (0, n2))
    determinants = (
        abs(a[0] * b[1] - a[1] * b[0])
        for index, a in enumerate(columns)
        for b in columns[index + 1 :]
    )
    return math.gcd(*determinants)


def load_tiles(source: pathlib.Path) -> list[dict[str, int]]:
    if git_value(source, "HEAD") != CAMPAIGN_COMMIT:
        raise ValueError("campaign source commit drifted")
    if git_value(source, "HEAD^{tree}") != CAMPAIGN_TREE:
        raise ValueError("campaign source tree drifted")
    pool_raw = (source / "compute203" / "pool_merged.json").read_bytes()
    if root(pool_raw) != POOL_ROOT:
        raise ValueError("prime pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(pool_raw).items()}
    tiles = []
    for prime, order in sorted(pool.items(), key=lambda item: (item[1], item[0])):
        generator = pow(int(primitive_root(prime)), (prime - 1) // order, prime)
        u = int(discrete_log(prime, 2, generator)) % order
        v = int(discrete_log(prime, 3, generator)) % order
        if math.gcd(math.gcd(u, v), order) != 1:
            raise ValueError(f"derived a non-primitive coordinate map for p={prime}")
        tiles.append({"p": prime, "n": order, "u": u, "v": v})
    return tiles


class DisjointSet:
    def __init__(self, vertices: set[int]) -> None:
        self.parent = {vertex: vertex for vertex in vertices}
        self.rank = {vertex: 0 for vertex in vertices}

    def find(self, vertex: int) -> int:
        if self.parent[vertex] != vertex:
            self.parent[vertex] = self.find(self.parent[vertex])
        return self.parent[vertex]

    def join(self, left: int, right: int) -> bool:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return False
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1
        return True


def pair_record(left: dict[str, int], right: dict[str, int]) -> dict[str, Any]:
    return {
        "primes": [left["p"], right["p"]],
        "orders": [left["n"], right["n"]],
        "intersection_density": str(Fraction(1, left["n"] * right["n"])),
    }


def build(source: pathlib.Path, preregistration: str) -> dict[str, Any]:
    tiles = load_tiles(source)
    by_prime = {tile["p"]: tile for tile in tiles}
    weights: dict[tuple[int, int], Fraction] = {}
    mandatory_pairs = 0
    for first, left in enumerate(tiles):
        for right in tiles[first + 1 :]:
            if compatibility_index(
                (left["u"], left["v"], left["n"]),
                (right["u"], right["v"], right["n"]),
            ) != 1:
                continue
            weights[(left["p"], right["p"])] = Fraction(
                1, left["n"] * right["n"]
            )
            mandatory_pairs += 1

    selected = {tile["p"] for tile in tiles if 55440 % tile["n"] == 0}
    components = DisjointSet(selected)
    base_edges = [
        (edge, weight)
        for edge, weight in weights.items()
        if edge[0] in selected and edge[1] in selected
    ]
    tree: list[dict[str, Any]] = []
    for (left, right), _ in sorted(base_edges, key=lambda row: (-row[1], row[0])):
        if components.join(left, right):
            tree.append(pair_record(by_prime[left], by_prime[right]))
    if len(tree) != len(selected) - 1:
        raise ValueError("the 55440 seed graph is not connected")

    density = sum((Fraction(1, by_prime[p]["n"]) for p in selected), Fraction())
    tree_mass = sum(
        (Fraction(edge["intersection_density"]) for edge in tree), Fraction()
    )
    gap = tree_mass - (density - 1)
    additions = []
    while True:
        candidates = []
        for tile in tiles:
            prime = tile["p"]
            if prime in selected:
                continue
            incident = []
            for anchor in selected:
                key = (prime, anchor) if prime < anchor else (anchor, prime)
                weight = weights.get(key)
                if weight:
                    incident.append((weight, anchor))
            if not incident:
                continue
            edge_weight, anchor = max(incident, key=lambda row: (row[0], -row[1]))
            delta = edge_weight - Fraction(1, tile["n"])
            candidates.append(
                (delta, -tile["n"], -prime, prime, anchor, edge_weight)
            )
        if not candidates:
            next_candidate = None
            break
        delta, _, _, prime, anchor, edge_weight = max(candidates)
        next_gap = gap + delta
        if next_gap <= 0:
            next_candidate = {
                "prime": prime,
                "order": by_prime[prime]["n"],
                "anchor_prime": anchor,
                "edge_mass": str(edge_weight),
                "gap_delta": str(delta),
                "gap_after_addition": str(next_gap),
            }
            break
        selected.add(prime)
        gap = next_gap
        density += Fraction(1, by_prime[prime]["n"])
        tree_mass += edge_weight
        edge = pair_record(by_prime[min(prime, anchor)], by_prime[max(prime, anchor)])
        tree.append(edge)
        additions.append(
            {
                "prime": prime,
                "order": by_prime[prime]["n"],
                "anchor_prime": anchor,
                "edge_mass": str(edge_weight),
                "gap_delta": str(delta),
                "gap_after_addition": str(gap),
            }
        )

    if len(selected) != 188 or len(tree) != 187 or gap <= 0:
        raise ValueError("extended forest dimensions differ from the frozen experiment")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "source": {
            "commit": CAMPAIGN_COMMIT,
            "tree": CAMPAIGN_TREE,
            "pool_root": POOL_ROOT,
            "pool_tiles": len(tiles),
            "mandatory_pairs_checked": len(tiles) * (len(tiles) - 1) // 2,
            "mandatory_pairs": mandatory_pairs,
        },
        "inputs": {"preregistration": preregistration},
        "selection": {
            "seed": "All 55 retained tiles whose order divides 55440, with their deterministic maximum-weight mandatory-pair spanning tree.",
            "extension": "Repeatedly add the remaining tile with the largest exact gap delta from its strongest mandatory edge into the current tree; break ties by smaller order, prime, and anchor; stop before the first nonpositive total gap.",
            "seed_tiles": 55,
            "additions": additions,
            "next_rejected_candidate": next_candidate,
        },
        "certificate": {
            "kind": "mandatory_pair_spanning_tree",
            "tiles": [
                {"prime": prime, "order": by_prime[prime]["n"]}
                for prime in sorted(selected, key=lambda p: (by_prime[p]["n"], p))
            ],
            "tile_count": len(selected),
            "tree_edges": tree,
            "edge_count": len(tree),
            "tree_mass": str(tree_mass),
            "density": str(density),
            "density_slack": str(density - 1),
            "contradiction_gap": str(gap),
            "pointwise_bound": "Every selected covering-set subgraph has at most |S|-1 tree edges.",
        },
        "conclusion": {
            "result": "no_cover_selected_family",
            "scope": "No choice of one affine shift for each of the 188 certificate tiles covers Z^2.",
            "proof": "For a cover, the exact fixed mass of selected mandatory tree edges is at most total multiplicity excess; the certificate has strictly larger tree mass.",
        },
        "nonclaims": [
            "This post-exploratory qualification is not an unbiased discovery episode.",
            "The excluded 188-tile family is an algorithmically selected subset of the pinned 313-tile pool, not the entire pool.",
            "The result says nothing about finite covers using tiles outside the certificate family.",
            "This does not resolve Erdos problem 203 globally or establish novelty.",
            "This is not a Vela Verification or human Decision, and it changes no Standing.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--preregistration", required=True)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        value = build(args.campaign_source.resolve(), args.preregistration)
        raw = canonical_bytes(value)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "artifact_root": root(raw),
                "result": value["conclusion"]["result"],
                "tile_count": value["certificate"]["tile_count"],
                "contradiction_gap": value["certificate"]["contradiction_gap"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

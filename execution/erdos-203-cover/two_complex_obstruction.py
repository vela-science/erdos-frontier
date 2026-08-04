#!/usr/bin/env python3
"""Build a mandatory pair/triple 2-tree obstruction for Erdős 203."""

from __future__ import annotations

import argparse
import hashlib
import heapq
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
SCHEMA = "erdos-frontier.erdos-203-two-complex-obstruction.v1"
SEED_PRIMES = (47, 211, 6073)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def git_value(source: pathlib.Path, expression: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", expression], text=True
    ).strip()


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
        tiles.append({"prime": prime, "order": order, "u": u, "v": v})
    return tiles


def triple_index(rows: tuple[dict[str, int], dict[str, int], dict[str, int]]) -> int:
    first, second, third = rows
    u1, v1, n1 = first["u"], first["v"], first["order"]
    u2, v2, n2 = second["u"], second["v"], second["order"]
    u3, v3, n3 = third["u"], third["v"], third["order"]
    minors = (
        n1 * (u2 * v3 - u3 * v2),
        n2 * (u1 * v3 - u3 * v1),
        n3 * (u1 * v2 - u2 * v1),
        n1 * n2 * u3,
        n1 * n3 * u2,
        n2 * n3 * u1,
        n1 * n2 * v3,
        n1 * n3 * v2,
        n2 * n3 * v1,
        n1 * n2 * n3,
    )
    return math.gcd(*(abs(value) for value in minors))


def edge_key(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def attachment_cost(left: dict[str, int], right: dict[str, int], tile: dict[str, int]) -> Fraction:
    """Exact decrease in Euler-mass gap when a vertex is glued along an edge."""
    n1, n2, n3 = left["order"], right["order"], tile["order"]
    return Fraction((n1 - 1) * (n2 - 1), n1 * n2 * n3)


def build(source: pathlib.Path, preregistration: str) -> dict[str, Any]:
    tiles = load_tiles(source)
    by_prime = {tile["prime"]: tile for tile in tiles}
    if any(prime not in by_prime for prime in SEED_PRIMES):
        raise ValueError("frozen seed is absent from the pinned pool")

    triple_extensions: dict[tuple[int, int], list[int]] = {}
    mandatory_triples = 0
    for first in range(len(tiles) - 2):
        for second in range(first + 1, len(tiles) - 1):
            for third in range(second + 1, len(tiles)):
                if triple_index((tiles[first], tiles[second], tiles[third])) != 1:
                    continue
                mandatory_triples += 1
                triple_extensions.setdefault((first, second), []).append(third)
                triple_extensions.setdefault((first, third), []).append(second)
                triple_extensions.setdefault((second, third), []).append(first)

    index_by_prime = {tile["prime"]: index for index, tile in enumerate(tiles)}
    seed = tuple(index_by_prime[prime] for prime in SEED_PRIMES)
    if triple_index(tuple(tiles[index] for index in seed)) != 1:
        raise ValueError("frozen seed triple is not mandatory")
    selected = set(seed)
    edges = {
        edge_key(seed[0], seed[1]),
        edge_key(seed[0], seed[2]),
        edge_key(seed[1], seed[2]),
    }
    triangles = [seed]
    attachments: list[dict[str, Any]] = []
    offered_edges: set[tuple[int, int]] = set()
    candidates: list[tuple[Fraction, int, int, int, int, int]] = []

    gap = math.prod(Fraction(tiles[index]["order"] - 1, tiles[index]["order"]) for index in seed)

    def offer(edge: tuple[int, int]) -> None:
        if edge in offered_edges:
            return
        offered_edges.add(edge)
        left, right = edge
        for vertex in triple_extensions.get(edge, []):
            if vertex in selected:
                continue
            tile = tiles[vertex]
            heapq.heappush(candidates, (
                attachment_cost(tiles[left], tiles[right], tile),
                tile["order"],
                tile["prime"],
                left,
                right,
                vertex,
            ))

    for edge in sorted(edges):
        offer(edge)

    next_rejected = None
    while candidates:
        cost, _, _, left, right, vertex = heapq.heappop(candidates)
        if vertex in selected:
            continue
        next_gap = gap - cost
        if next_gap <= 0:
            next_rejected = {
                "prime": tiles[vertex]["prime"],
                "order": tiles[vertex]["order"],
                "parent_primes": [tiles[left]["prime"], tiles[right]["prime"]],
                "gap_cost": str(cost),
                "gap_after_attachment": str(next_gap),
            }
            break
        selected.add(vertex)
        gap = next_gap
        triangles.append((left, right, vertex))
        attachments.append({
            "prime": tiles[vertex]["prime"],
            "order": tiles[vertex]["order"],
            "parent_primes": [tiles[left]["prime"], tiles[right]["prime"]],
            "gap_cost": str(cost),
            "gap_after_attachment": str(gap),
        })
        for edge in (edge_key(left, vertex), edge_key(right, vertex)):
            edges.add(edge)
            offer(edge)

    selected_rows = [tiles[index] for index in sorted(selected, key=lambda index: (tiles[index]["order"], tiles[index]["prime"]))]
    edge_rows = sorted(edges, key=lambda edge: (
        tiles[edge[0]]["prime"], tiles[edge[1]]["prime"]
    ))
    triangle_rows = triangles
    density = sum((Fraction(1, row["order"]) for row in selected_rows), Fraction())
    pair_mass = sum((Fraction(1, tiles[left]["order"] * tiles[right]["order"]) for left, right in edge_rows), Fraction())
    triple_mass = sum((Fraction(1, math.prod(tiles[index]["order"] for index in triangle)) for triangle in triangle_rows), Fraction())
    euler_mass = pair_mass - triple_mass
    exact_gap = euler_mass - (density - 1)
    if len(selected_rows) != 306 or len(edge_rows) != 609 or len(triangle_rows) != 304 or exact_gap != gap or gap <= 0:
        raise ValueError("two-complex dimensions differ from the frozen experiment")

    prior = json.loads((pathlib.Path(__file__).parents[2] / "artifacts/analyses/erdos203-extended-forest-obstruction.v1.json").read_text())
    prior_primes = {row["prime"] for row in prior["certificate"]["tiles"]}
    pool_primes = {row["prime"] for row in tiles}
    selected_primes = {row["prime"] for row in selected_rows}
    prior_complement = pool_primes - prior_primes
    if not prior_complement <= selected_primes:
        raise ValueError("two-complex omitted a tile outside the prior 188-tile certificate")

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
            "mandatory_triples": mandatory_triples,
        },
        "inputs": {
            "preregistration": preregistration,
            "prior_certificate_root": root((pathlib.Path(__file__).parents[2] / "artifacts/analyses/erdos203-extended-forest-obstruction.v1.json").read_bytes()),
        },
        "selection": {
            "seed_primes": list(SEED_PRIMES),
            "rule": "Start from the frozen mandatory triple. Repeatedly attach the unselected tile with least exact gap cost along an available mandatory parent edge; break ties by order, prime, then parent indices; stop before the first nonpositive gap.",
            "attachments": attachments,
            "next_rejected_candidate": next_rejected,
            "prior_188_tiles_retained": len(prior_primes & selected_primes),
            "prior_125_complement_retained": len(prior_complement & selected_primes),
        },
        "certificate": {
            "kind": "mandatory_pair_triple_two_tree",
            "tiles": [{"prime": row["prime"], "order": row["order"]} for row in selected_rows],
            "tile_count": len(selected_rows),
            "edges": [{
                "primes": [tiles[left]["prime"], tiles[right]["prime"]],
                "orders": [tiles[left]["order"], tiles[right]["order"]],
            } for left, right in edge_rows],
            "edge_count": len(edge_rows),
            "triangles": [{
                "primes": [tiles[index]["prime"] for index in triangle],
                "orders": [tiles[index]["order"] for index in triangle],
            } for triangle in triangle_rows],
            "triangle_count": len(triangle_rows),
            "density": str(density),
            "density_slack": str(density - 1),
            "pair_mass": str(pair_mass),
            "triple_mass": str(triple_mass),
            "euler_mass": str(euler_mass),
            "contradiction_gap": str(exact_gap),
            "pointwise_bound": "For every nonempty set S of tiles covering a point, the induced 2-tree satisfies |E(S)|-|T(S)| <= |S|-1.",
        },
        "conclusion": {
            "result": "no_cover_selected_family",
            "scope": "No choice of one affine shift for each of the 306 certificate tiles covers Z^2.",
            "proof": "Mandatory pair mass minus mandatory triple mass is fixed. The induced 2-tree Euler bound makes it at most total multiplicity excess under a cover, but the exact certificate mass is strictly larger.",
        },
        "nonclaims": [
            "This post-exploratory qualification is not an unbiased discovery episode.",
            "The 306-tile certificate omits seven pinned tiles and does not exclude the full 313-tile pool.",
            "The prior 188-tile certificate is not a subset of this certificate; eight of its low-order tiles are replaced while all 125 previously outside tiles are included.",
            "This does not resolve Erdős problem 203 globally or establish novelty.",
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
    print(json.dumps({
        "ok": True,
        "output": str(args.output),
        "artifact_root": root(raw),
        "result": value["conclusion"]["result"],
        "tile_count": value["certificate"]["tile_count"],
        "contradiction_gap": value["certificate"]["contradiction_gap"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

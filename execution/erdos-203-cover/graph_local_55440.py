#!/usr/bin/env python3
"""Certify the exact unweighted graph-local overlap ratio for the 55440 family."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections import deque
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

TARGET = "erdos:203:finite-cover"
INPUT_ROOT = "sha256:c4e63f2cec41e39c9c6bcbb08207a76892900d6b88c47d672aee2c63025322bd"
INPUT_SCHEMA = "erdos-frontier.erdos-203-overlap-obstruction.v1"
OUTPUT_SCHEMA = "erdos-frontier.erdos-203-55440-graph-local-bound.v1"
EDGE_UNITS = 6
NON_ROOT_CAPACITY = 91


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass
class Arc:
    to: int
    reverse: int
    capacity: int


class Dinic:
    def __init__(self, vertices: int) -> None:
        self.graph: list[list[Arc]] = [[] for _ in range(vertices)]

    def add(self, source: int, target: int, capacity: int) -> int:
        forward = len(self.graph[source])
        reverse = len(self.graph[target])
        self.graph[source].append(Arc(target, reverse, capacity))
        self.graph[target].append(Arc(source, forward, 0))
        return forward

    def max_flow(self, source: int, sink: int) -> int:
        total = 0
        while True:
            level = [-1] * len(self.graph)
            level[source] = 0
            queue = deque([source])
            while queue:
                vertex = queue.popleft()
                for arc in self.graph[vertex]:
                    if arc.capacity and level[arc.to] < 0:
                        level[arc.to] = level[vertex] + 1
                        queue.append(arc.to)
            if level[sink] < 0:
                return total
            cursor = [0] * len(self.graph)

            def send(vertex: int, available: int) -> int:
                if vertex == sink:
                    return available
                while cursor[vertex] < len(self.graph[vertex]):
                    index = cursor[vertex]
                    arc = self.graph[vertex][index]
                    if arc.capacity and level[arc.to] == level[vertex] + 1:
                        pushed = send(arc.to, min(available, arc.capacity))
                        if pushed:
                            arc.capacity -= pushed
                            self.graph[arc.to][arc.reverse].capacity += pushed
                            return pushed
                    cursor[vertex] += 1
                return 0

            while True:
                pushed = send(source, 10**18)
                if not pushed:
                    break
                total += pushed


def orientation(
    vertices: list[int], edges: list[tuple[int, int]], excluded: int
) -> list[int]:
    vertex_index = {prime: index for index, prime in enumerate(vertices)}
    source = 0
    edge_offset = 1
    vertex_offset = edge_offset + len(edges)
    sink = vertex_offset + len(vertices)
    network = Dinic(sink + 1)
    left_arcs: list[tuple[int, int]] = []
    for index, (left, right) in enumerate(edges):
        edge_node = edge_offset + index
        network.add(source, edge_node, EDGE_UNITS)
        left_arc = network.add(
            edge_node, vertex_offset + vertex_index[left], EDGE_UNITS
        )
        network.add(edge_node, vertex_offset + vertex_index[right], EDGE_UNITS)
        left_arcs.append((edge_node, left_arc))
    for prime, index in vertex_index.items():
        capacity = 0 if prime == excluded else NON_ROOT_CAPACITY
        network.add(vertex_offset + index, sink, capacity)
    expected = EDGE_UNITS * len(edges)
    observed = network.max_flow(source, sink)
    if observed != expected:
        raise ValueError(
            f"no root-excluding orientation for p={excluded}: {observed}/{expected}"
        )
    return [
        EDGE_UNITS - network.graph[node][arc].capacity for node, arc in left_arcs
    ]


def build(input_path: pathlib.Path, preregistration: str) -> dict[str, Any]:
    raw = input_path.read_bytes()
    value = json.loads(raw)
    if raw != canonical_bytes(value) or root(raw) != INPUT_ROOT:
        raise ValueError("55440 overlap input is not the pinned canonical artifact")
    if value.get("schema") != INPUT_SCHEMA or value.get("target") != TARGET:
        raise ValueError("55440 overlap input crosses the registered boundary")
    if value.get("inputs", {}).get("period") != 55440:
        raise ValueError("55440 overlap input has the wrong family")

    vertices = [member["prime"] for member in value["family"]["members"]]
    edges = [tuple(pair["primes"]) for pair in value["mandatory_overlap"]["pairs"]]
    if len(vertices) != 55 or len(edges) != 819 or len(set(edges)) != len(edges):
        raise ValueError("55440 mandatory graph dimensions drifted")
    certificates = [
        {
            "excluded_prime": prime,
            "left_endpoint_units": orientation(vertices, edges, prime),
        }
        for prime in vertices
    ]

    exact_ratio = Fraction(len(edges), len(vertices) - 1)
    if exact_ratio != Fraction(NON_ROOT_CAPACITY, EDGE_UNITS):
        raise ValueError("full graph no longer attains the certified ratio")
    density_slack = Fraction(value["family"]["density_slack"])
    fixed_pair_mass = Fraction(value["mandatory_overlap"]["fixed_pair_mass"])
    upper_bound = exact_ratio * density_slack
    gap = fixed_pair_mass - upper_bound
    return {
        "schema": OUTPUT_SCHEMA,
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "inputs": {
            "artifact_path": input_path.as_posix(),
            "artifact_root": INPUT_ROOT,
            "preregistration": preregistration,
        },
        "graph": {
            "vertices": vertices,
            "edges": [list(edge) for edge in edges],
            "vertex_count": len(vertices),
            "edge_count": len(edges),
        },
        "certificate": {
            "edge_units": EDGE_UNITS,
            "non_root_capacity": NON_ROOT_CAPACITY,
            "root_excluding_orientations": certificates,
            "inequality": "6*|E(S)| <= 91*(|S|-1) for every vertex set S with |S| >= 2",
            "attaining_set": "all 55 vertices",
            "exact_edge_to_excess_ratio": str(exact_ratio),
        },
        "comparison": {
            "registered_degree_sequence_ratio": value["mandatory_overlap"]["pointwise_ratio"],
            "exact_graph_local_ratio": str(exact_ratio),
            "density_slack": str(density_slack),
            "fixed_pair_mass": str(fixed_pair_mass),
            "cover_pair_mass_upper_bound": str(upper_bound),
            "contradiction_gap": str(gap),
        },
        "conclusion": {
            "result": "no_conclusion",
            "scope": "The exact strongest unweighted mandatory-graph ratio does not exclude the n-divides-55440 family.",
            "next_obligation": "Use weighted marginals, prime-power structure, or higher-order intersections; another unweighted mandatory-edge count cannot decide this family.",
        },
        "nonclaims": [
            "This post-exploratory method qualification is not an unbiased discovery episode.",
            "No-conclusion is not evidence that the selected family can cover.",
            "The exact graph-local ratio uses only the unweighted mandatory-pair graph.",
            "This does not resolve Erdős problem 203 globally.",
            "This is not a Vela Verification or human Decision, and it changes no Standing.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=pathlib.Path)
    parser.add_argument("--preregistration", required=True)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        value = build(args.input, args.preregistration)
        raw = canonical_bytes(value)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "artifact_root": root(raw),
                "result": value["conclusion"]["result"],
                "exact_ratio": value["comparison"]["exact_graph_local_ratio"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

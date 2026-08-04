from __future__ import annotations

import json
import pathlib
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = (
    ROOT / "artifacts" / "analyses" / "erdos203-extended-forest-obstruction.v1.json"
)


class DisjointSet:
    def __init__(self, vertices: list[int]) -> None:
        self.parent = {vertex: vertex for vertex in vertices}

    def find(self, vertex: int) -> int:
        while self.parent[vertex] != vertex:
            self.parent[vertex] = self.parent[self.parent[vertex]]
            vertex = self.parent[vertex]
        return vertex

    def join(self, left: int, right: int) -> bool:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return False
        self.parent[right_root] = left_root
        return True


def test_extended_certificate_is_an_exact_positive_gap_tree() -> None:
    value = json.loads(ARTIFACT.read_text())
    certificate = value["certificate"]
    tiles = certificate["tiles"]
    primes = [tile["prime"] for tile in tiles]
    assert len(primes) == len(set(primes)) == certificate["tile_count"] == 188

    tree = DisjointSet(primes)
    mass = Fraction()
    seen = set()
    for edge in certificate["tree_edges"]:
        left, right = edge["primes"]
        key = frozenset((left, right))
        assert len(key) == 2 and key not in seen
        seen.add(key)
        assert tree.join(left, right)
        mass += Fraction(edge["intersection_density"])
    assert len(seen) == certificate["edge_count"] == 187
    assert len({tree.find(prime) for prime in primes}) == 1

    density = sum((Fraction(1, tile["order"]) for tile in tiles), Fraction())
    gap = mass - (density - 1)
    assert str(density) == certificate["density"]
    assert str(mass) == certificate["tree_mass"]
    assert str(gap) == certificate["contradiction_gap"]
    assert gap > 0
    assert value["conclusion"]["result"] == "no_cover_selected_family"

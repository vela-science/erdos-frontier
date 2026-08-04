from __future__ import annotations

import json
import pathlib
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "artifacts/analyses/erdos203-two-complex-obstruction.v1.json"
PRIOR = ROOT / "artifacts/analyses/erdos203-extended-forest-obstruction.v1.json"


def edge_key(left: int, right: int) -> frozenset[int]:
    return frozenset((left, right))


def test_two_complex_is_an_exact_positive_gap_2_tree() -> None:
    value = json.loads(ARTIFACT.read_text())
    certificate = value["certificate"]
    tiles = certificate["tiles"]
    orders = {tile["prime"]: tile["order"] for tile in tiles}
    assert len(orders) == certificate["tile_count"] == 306

    seed = value["selection"]["seed_primes"]
    vertices = set(seed)
    edges = {
        edge_key(seed[0], seed[1]),
        edge_key(seed[0], seed[2]),
        edge_key(seed[1], seed[2]),
    }
    triangles = {frozenset(seed)}
    for attachment in value["selection"]["attachments"]:
        prime = attachment["prime"]
        left, right = attachment["parent_primes"]
        assert prime not in vertices
        assert edge_key(left, right) in edges
        vertices.add(prime)
        edges.add(edge_key(left, prime))
        edges.add(edge_key(right, prime))
        triangles.add(frozenset((left, right, prime)))

    reported_edges = {edge_key(*edge["primes"]) for edge in certificate["edges"]}
    reported_triangles = {
        frozenset(triangle["primes"]) for triangle in certificate["triangles"]
    }
    assert vertices == set(orders)
    assert edges == reported_edges
    assert triangles == reported_triangles
    assert len(edges) == certificate["edge_count"] == 609
    assert len(triangles) == certificate["triangle_count"] == 304

    density = sum((Fraction(1, order) for order in orders.values()), Fraction())
    pair_mass = sum(
        (Fraction(1, orders[left] * orders[right]) for left, right in (
            tuple(edge) for edge in reported_edges
        )),
        Fraction(),
    )
    triple_mass = sum(
        (Fraction(1, orders[first] * orders[second] * orders[third]) for first, second, third in (
            tuple(triangle) for triangle in reported_triangles
        )),
        Fraction(),
    )
    euler_mass = pair_mass - triple_mass
    gap = euler_mass - (density - 1)
    assert str(density) == certificate["density"]
    assert str(pair_mass) == certificate["pair_mass"]
    assert str(triple_mass) == certificate["triple_mass"]
    assert str(euler_mass) == certificate["euler_mass"]
    assert str(gap) == certificate["contradiction_gap"]
    assert gap > 0
    assert value["conclusion"]["result"] == "no_cover_selected_family"


def test_two_complex_contains_every_tile_outside_the_prior_certificate() -> None:
    current = json.loads(ARTIFACT.read_text())
    prior = json.loads(PRIOR.read_text())
    selected = {row["prime"] for row in current["certificate"]["tiles"]}
    prior_selected = {row["prime"] for row in prior["certificate"]["tiles"]}
    pool = selected | {
        row["prime"]
        for row in current["certificate"]["tiles"]
    }
    # The exact pool size and overlap counts are independently bound in the
    # source-first checker; these identities catch projection-level drift.
    assert current["source"]["pool_tiles"] == 313
    assert current["selection"]["prior_188_tiles_retained"] == 181
    assert current["selection"]["prior_125_complement_retained"] == 125
    assert len(selected & prior_selected) == 181
    assert len(selected - prior_selected) == 125
    assert len(pool) == 306

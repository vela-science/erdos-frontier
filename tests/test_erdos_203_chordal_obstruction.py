from __future__ import annotations

import hashlib
import json
import pathlib
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = ROOT / "artifacts/analyses/erdos203-two-complex-obstruction.v1.json"
ARTIFACT = ROOT / "artifacts/analyses/erdos203-chordal-obstruction.v1.json"
CHECK = ROOT / "artifacts/runs/erdos203-chordal-obstruction-check.v1.json"
PREREGISTRATION = ROOT / "execution/erdos-203-chordal/preregistration.v2.json"


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )


def root(path: pathlib.Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_chordal_extension_has_the_frozen_exact_positive_gap() -> None:
    base = json.loads(BASE.read_text())
    artifact = json.loads(ARTIFACT.read_text())
    preregistration = json.loads(PREREGISTRATION.read_text())
    assert ARTIFACT.read_bytes() == canonical_bytes(artifact)
    assert PREREGISTRATION.read_bytes() == canonical_bytes(preregistration)
    assert artifact["authority"] == "non_authoritative"
    assert artifact["claim_credit"] is False
    assert artifact["target"] == "erdos:203:chordal-obstruction"
    assert artifact["inputs"]["base_certificate"]["sha256"] == root(BASE)
    assert artifact["inputs"]["preregistration"]["sha256"] == root(
        PREREGISTRATION
    )

    extension = artifact["extension"]
    assert extension["prime"] == 19
    assert extension["order"] == 18
    assert extension["coordinates"] == {"u": 1, "v": 13}
    assert extension["parent_primes"] == [31, 47, 71]
    assert extension["parent_orders"] == [30, 23, 35]
    assert set(extension["pair_indices"].values()) == {1}
    assert len(extension["pair_indices"]) == 6
    assert set(extension["triple_indices"].values()) == {1}
    assert len(extension["triple_indices"]) == 4
    assert extension["quadruple_index"] == 1

    base_certificate = base["certificate"]
    parent_orders = extension["parent_orders"]
    new_order = extension["order"]
    density = Fraction(base_certificate["density"]) + Fraction(1, new_order)
    pair_mass = Fraction(base_certificate["pair_mass"]) + sum(
        (Fraction(1, new_order * order) for order in parent_orders), Fraction()
    )
    triple_mass = Fraction(base_certificate["triple_mass"]) + sum(
        (
            Fraction(1, new_order * parent_orders[left] * parent_orders[right])
            for left, right in ((0, 1), (0, 2), (1, 2))
        ),
        Fraction(),
    )
    quadruple_mass = Fraction(1, new_order * 30 * 23 * 35)
    euler_mass = pair_mass - triple_mass + quadruple_mass
    gap = euler_mass - (density - 1)
    expected = {
        "tile_count": 307,
        "edge_count": 612,
        "triangle_count": 307,
        "tetrahedron_count": 1,
        "density": str(density),
        "pair_mass": str(pair_mass),
        "triple_mass": str(triple_mass),
        "quadruple_mass": str(quadruple_mass),
        "euler_mass": str(euler_mass),
        "contradiction_gap": str(gap),
        "extension_cost": "5423/108675",
    }
    assert preregistration["observed_candidate"] == expected
    assert all(artifact["certificate"][key] == value for key, value in expected.items())
    assert gap > 0
    assert artifact["conclusion"]["result"] == "no_cover_selected_family"
    assert artifact["conclusion"]["omitted_primes"] == [5, 7, 11, 13, 17, 23]


def test_independent_check_binds_the_full_base_and_extension() -> None:
    check = json.loads(CHECK.read_text())
    artifact = json.loads(ARTIFACT.read_text())
    assert CHECK.read_bytes() == canonical_bytes(check)
    assert check["ok"] is True
    assert check["accepted_state_change"] == "none"
    assert check["artifact_root"] == root(ARTIFACT)
    assert check["base_artifact_root"] == root(BASE)
    assert check["preregistration_root"] == root(PREREGISTRATION)
    assert check["certificate_tiles"] == 307
    assert check["edges"] == 612
    assert check["triangles"] == 307
    assert check["tetrahedra"] == 1
    assert check["contradiction_gap"] == artifact["certificate"][
        "contradiction_gap"
    ]
    assert check["implementation_independence"] == {
        "base_check": "exact rooted dependency-free verifier replay",
        "coordinate_method": "bounded direct subgroup enumeration",
        "extension_check": (
            "direct pair, triple, quadruple lattice-index minors and exact "
            "Fraction summation"
        ),
        "imports_extension_producer": False,
        "uses_sympy": False,
    }
    assert any("Same human operator" in row for row in check["shared_dependencies"])
    assert any("does not resolve" in row for row in check["nonclaims"])


def test_v2_retains_the_failed_serialization_iteration_without_scientific_change() -> None:
    preregistration = json.loads(PREREGISTRATION.read_text())
    prior = preregistration["prior_iteration"]
    assert preregistration["iteration"]["number"] == 2
    assert preregistration["claim_credit"] is False
    assert prior["artifact_root"] == (
        "sha256:da81039027c1b2224193c7876b3cbc01562ea1fb8652db8aab8821a8587eb67b"
    )
    assert prior["scientific_change"] == "none"
    assert "canonical JSON" in prior["failure"]

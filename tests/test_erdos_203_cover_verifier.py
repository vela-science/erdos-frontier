from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERIFIER = ROOT / "execution" / "erdos-203-cover" / "verify.py"
SPEC = importlib.util.spec_from_file_location("erdos_203_cover_verifier", VERIFIER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def members(cell: tuple[int, int, int, int, int, int], bound: int) -> set[tuple[int, int]]:
    a11, a12, a21, a22, b1, b2 = cell
    determinant = a11 * a22 - a12 * a21
    result = set()
    for x in range(bound):
        for y in range(bound):
            rx, ry = x - b1, y - b2
            if (
                (a22 * rx - a12 * ry) % determinant == 0
                and (-a21 * rx + a11 * ry) % determinant == 0
            ):
                result.add((x, y))
    return result


@pytest.mark.parametrize(
    ("prime", "order_2", "order_3"),
    [(5, 4, 4), (7, 3, 6), (11, 10, 5), (23, 11, 11)],
)
def test_native_number_theory_checks(prime: int, order_2: int, order_3: int) -> None:
    assert MODULE.is_prime(prime)
    assert MODULE.multiplicative_order(2, prime) == order_2
    assert MODULE.multiplicative_order(3, prime) == order_3


def test_exact_split_matches_bounded_point_complement() -> None:
    cell = (1, 0, 0, 1, 0, 0)
    children = MODULE.split_complement(cell, 1, 3, 4, 0)
    assert children is not None
    observed = set().union(*(members(child, 16) for child in children))
    expected = {
        (x, y)
        for x in range(16)
        for y in range(16)
        if (x + 3 * y) % 4 != 0
    }
    assert observed == expected


def test_crt_recomputes_unique_residue() -> None:
    value, modulus = MODULE.crt([(5, 4), (7, 6), (11, 10)])
    assert modulus == 385
    assert value % 5 == 4
    assert value % 7 == 6
    assert value % 11 == 10


def test_source_binding_separates_statement_from_campaign_lineage() -> None:
    assert MODULE.SOURCE["formal_statement"]["status"] == "merged_upstream"
    assert MODULE.SOURCE["formal_statement"]["declaration"] == "Erdos203.erdos_203"
    assert MODULE.SOURCE["campaign"]["commit"] == (
        "94fde841ea6ad90437bd66a91953bfeba13dba0f"
    )


def test_partial_cover_fails_closed(tmp_path: pathlib.Path) -> None:
    candidate = {
        "m": "9",
        "problem": 203,
        "problem_claim": MODULE.PROBLEM_CLAIM,
        "rows": [{"c": 0, "g": 2, "n": 4, "p": 5, "u": 1, "v": 3}],
        "schema": MODULE.SCHEMA,
        "source": MODULE.SOURCE,
        "target": "erdos:203:finite-cover",
    }
    path = tmp_path / "candidate.json"
    path.write_bytes(MODULE.canonical_bytes(candidate) + b"\n")
    with pytest.raises(MODULE.VerificationError, match="do not cover"):
        MODULE.verify(path)

#!/usr/bin/env python3
"""Verify an exact finite covering certificate for Erdős problem 203.

The verifier is deliberately independent of the producer search. It checks
each prime/tile from modular arithmetic, proves that the tile complements have
empty intersection as exact affine lattices, and recomputes the CRT witness.
It does not make or authorize a scientific Decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import sys
from functools import reduce
from typing import Any

SCHEMA = "erdos-frontier.erdos-203-cover-certificate.v1"
PROBLEM_CLAIM = {
    "claim_id": "vcl_8131cdf07c70fe688bf18bc6ca274d6bff43eaeed116430351685e925bf4a796",
    "claim_root": "sha256:998616dbbf3a0f704bbab20504a15fe1e4ab92fe60524ab6ad8798eab3435e06",
}
SOURCE = {
    "campaign": {
        "repository": "https://github.com/williamjblair/lean-proofs.git",
        "commit": "94fde841ea6ad90437bd66a91953bfeba13dba0f",
        "tree": "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a",
    },
    "formal_statement": {
        "repository": "https://github.com/google-deepmind/formal-conjectures.git",
        "commit": "50ee83fa7dc31c99c03c83f04be90b7fea37d314",
        "tree": "af55637ba163e4381b00cd0fca0f59158c6998f3",
        "path": "FormalConjectures/ErdosProblems/203.lean",
        "blob_sha1": "2bc9f5fb212533aeb94c2328dbb5b53987a9f9ec",
        "sha256": "sha256:dfd0eb1bf073a27ad74a398acb7c2986b73be9cf72e6dc6ed9fc4618c6538cfb",
        "declaration": "Erdos203.erdos_203",
        "status": "merged_upstream",
    },
}


class VerificationError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256_root(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def factor(value: int) -> dict[int, int]:
    factors: dict[int, int] = {}
    divisor = 2
    while divisor * divisor <= value:
        while value % divisor == 0:
            factors[divisor] = factors.get(divisor, 0) + 1
            value //= divisor
        divisor = 3 if divisor == 2 else divisor + 2
    if value > 1:
        factors[value] = factors.get(value, 0) + 1
    return factors


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    for prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if value == prime:
            return True
        if value % prime == 0:
            return False
    exponent = value - 1
    power = 0
    while exponent % 2 == 0:
        power += 1
        exponent //= 2
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        witness = pow(base, exponent, value)
        if witness in (1, value - 1):
            continue
        for _ in range(power - 1):
            witness = pow(witness, 2, value)
            if witness == value - 1:
                break
        else:
            return False
    return True


def multiplicative_order(base: int, prime: int) -> int:
    order = prime - 1
    for divisor in factor(order):
        while order % divisor == 0 and pow(base, order // divisor, prime) == 1:
            order //= divisor
    return order


def _lattice_basis(generators: list[tuple[int, int]]) -> tuple[tuple[int, int], tuple[int, int]]:
    vectors = [tuple(row) for row in generators if row != (0, 0)]
    while True:
        nonzero = sorted(
            (row for row in vectors if row[0] != 0), key=lambda row: abs(row[0])
        )
        if len(nonzero) <= 1:
            break
        pivot = nonzero[0]
        reduced = []
        for row in vectors:
            if row == pivot or row[0] == 0:
                reduced.append(row)
                continue
            quotient = row[0] // pivot[0]
            reduced.append(
                (row[0] - quotient * pivot[0], row[1] - quotient * pivot[1])
            )
        vectors = [row for row in reduced if row != (0, 0)]
    first = next((row for row in vectors if row[0] != 0), None)
    seconds = [abs(row[1]) for row in vectors if row[0] == 0 and row[1] != 0]
    second_gcd = reduce(math.gcd, seconds) if seconds else 0
    if first is None or not second_gcd:
        raise VerificationError("tile complement did not produce a rank-two lattice")
    first = (first[0], first[1] % second_gcd)
    return first, (0, second_gcd)


def split_complement(
    cell: tuple[int, int, int, int, int, int],
    u: int,
    v: int,
    modulus: int,
    shift: int,
) -> list[tuple[int, int, int, int, int, int]] | None:
    """Return exact subcells not covered by one linear-congruence tile."""

    a11, a12, a21, a22, b1, b2 = cell
    g1 = (u * a11 + v * a21) % modulus
    g2 = (u * a12 + v * a22) % modulus
    image_step = math.gcd(math.gcd(g1, g2), modulus)
    image_at_base = (u * b1 + v * b2) % modulus
    if (shift - image_at_base) % image_step != 0:
        return None
    quotient = modulus // image_step
    if quotient == 1:
        return []
    h1 = (g1 // image_step) % quotient
    h2 = (g2 // image_step) % quotient
    first, second = _lattice_basis(
        [(quotient, 0), (0, quotient), (h2 % quotient, (-h1) % quotient)]
    )
    determinant = abs(first[0] * second[1] - first[1] * second[0])
    if determinant != quotient:
        raise VerificationError("tile-complement lattice has the wrong index")
    representative = None
    gcd_h1 = math.gcd(h1, quotient)
    for y in range(quotient):
        remainder = (1 - h2 * y) % quotient
        if gcd_h1 and remainder % gcd_h1 == 0:
            reduced_modulus = quotient // gcd_h1
            x = (
                (remainder // gcd_h1)
                * pow(h1 // gcd_h1, -1, reduced_modulus)
            ) % reduced_modulus if reduced_modulus > 1 else 0
            if (h1 * x + h2 * y) % quotient == 1 % quotient:
                representative = (x, y)
                break
        elif gcd_h1 == 0 and remainder == 0:
            representative = (0, y)
            break
    if representative is None:
        raise VerificationError("could not construct an exact quotient representative")
    covered_class = ((shift - image_at_base) // image_step) % quotient
    children = []
    for index in range(quotient):
        if index == covered_class:
            continue
        tx = index * representative[0]
        ty = index * representative[1]
        children.append(
            (
                a11 * first[0] + a12 * first[1],
                a11 * second[0] + a12 * second[1],
                a21 * first[0] + a22 * first[1],
                a21 * second[0] + a22 * second[1],
                b1 + a11 * tx + a12 * ty,
                b2 + a21 * tx + a22 * ty,
            )
        )
    return children


def crt(congruences: list[tuple[int, int]]) -> tuple[int, int]:
    value = 0
    modulus = 1
    for prime, residue in congruences:
        step = ((residue - value) * pow(modulus, -1, prime)) % prime
        value += modulus * step
        modulus *= prime
        value %= modulus
    return value, modulus


def verify(candidate_path: pathlib.Path) -> dict[str, Any]:
    raw = candidate_path.read_bytes()
    try:
        candidate = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"candidate is not JSON: {error}") from error
    if raw != canonical_bytes(candidate) + b"\n":
        raise VerificationError("candidate must be canonical JSON with one trailing newline")
    if candidate.get("schema") != SCHEMA:
        raise VerificationError("candidate has the wrong schema")
    if candidate.get("problem") != 203 or candidate.get("target") != "erdos:203:finite-cover":
        raise VerificationError("candidate names another Target")
    if candidate.get("problem_claim") != PROBLEM_CLAIM:
        raise VerificationError("candidate does not bind the accepted problem Claim")
    if candidate.get("source") != SOURCE:
        raise VerificationError(
            "candidate does not bind the merged formal statement and retained campaign source"
        )
    rows = candidate.get("rows")
    if not isinstance(rows, list) or not rows or len(rows) > 512:
        raise VerificationError("candidate rows must contain 1..512 tiles")

    seen: set[int] = set()
    congruences: list[tuple[int, int]] = []
    cells = [(1, 0, 0, 1, 0, 0)]
    for position, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"p", "n", "g", "u", "v", "c"}:
            raise VerificationError(f"row {position} has the wrong fields")
        prime, order, generator, u, v, shift = (
            row["p"], row["n"], row["g"], row["u"], row["v"], row["c"]
        )
        if not all(isinstance(value, int) for value in (prime, order, generator, u, v, shift)):
            raise VerificationError(f"row {position} contains a non-integer")
        if prime in seen or prime <= 3 or not is_prime(prime):
            raise VerificationError(f"row {position} does not name a distinct prime greater than 3")
        seen.add(prime)
        expected_order = math.lcm(
            multiplicative_order(2, prime), multiplicative_order(3, prime)
        )
        if order != expected_order or not 0 <= shift < order:
            raise VerificationError(f"row {position} has the wrong subgroup order or shift")
        if (
            multiplicative_order(generator, prime) != order
            or pow(generator, u, prime) != 2 % prime
            or pow(generator, v, prime) != 3 % prime
            or math.gcd(math.gcd(u, v), order) != 1
        ):
            raise VerificationError(f"row {position} has an invalid subgroup coordinate map")
        target_residue = pow(generator, shift, prime)
        congruences.append((prime, (-pow(target_residue, -1, prime)) % prime))
        uncovered = []
        for cell in cells:
            remainder = split_complement(cell, u, v, order, shift)
            if remainder is None:
                uncovered.append(cell)
            else:
                uncovered.extend(remainder)
        cells = uncovered

    if cells:
        raise VerificationError(
            f"tiles do not cover Z^2; {len(cells)} exact uncovered cells remain"
        )
    witness, product = crt(congruences)
    while witness <= max(seen) or math.gcd(witness, 6) != 1:
        witness += product
    if str(witness) != candidate.get("m"):
        raise VerificationError("candidate m differs from the canonical CRT witness")
    for prime, residue in congruences:
        if witness % prime != residue:
            raise VerificationError("CRT witness does not satisfy a retained congruence")
    return {
        "schema": "erdos-frontier.erdos-203-cover-verification.v1",
        "ok": True,
        "candidate_root": sha256_root(raw),
        "rows": len(rows),
        "crt_modulus_bits": product.bit_length(),
        "uncovered_cells": 0,
        "accepted_state_change": "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.candidate)
    except (OSError, VerificationError) as error:
        result = {
            "schema": "erdos-frontier.erdos-203-cover-verification.v1",
            "ok": False,
            "error": str(error),
            "accepted_state_change": "none",
        }
    print(json.dumps(result, sort_keys=True) if args.json else result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

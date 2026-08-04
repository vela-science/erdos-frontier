#!/usr/bin/env python3
"""Search the exact L=5040 Erdős 203 tile family with SAT/CEGAR.

This is producer-side search code, not the independent verifier.  It chooses
exactly one shift for each retained prime tile, asks CaDiCaL to cover a growing
set of points, and then searches the complete 5040 by 5040 torus for holes.
Any positive candidate is emitted in the canonical Frontier certificate
schema and must still pass ``verify.py``.  UNSAT applies only to this frozen
31-tile family.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
from sympy import discrete_log, primitive_root

CAMPAIGN_COMMIT = "94fde841ea6ad90437bd66a91953bfeba13dba0f"
CAMPAIGN_TREE = "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a"
POOL_ROOT = "sha256:9a8f179bf6ab509c53144ac679acd8ffe42e66588b1516b0ca3a9f45e18395b3"
TARGET = "erdos:203:finite-cover"
PROBLEM_CLAIM = {
    "claim_id": "vcl_8131cdf07c70fe688bf18bc6ca274d6bff43eaeed116430351685e925bf4a796",
    "claim_root": "sha256:998616dbbf3a0f704bbab20504a15fe1e4ab92fe60524ab6ad8798eab3435e06",
}
SOURCE = {
    "campaign": {
        "repository": "https://github.com/williamjblair/lean-proofs.git",
        "commit": CAMPAIGN_COMMIT,
        "tree": CAMPAIGN_TREE,
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


@dataclass(frozen=True)
class Tile:
    p: int
    n: int
    g: int
    u: int
    v: int


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def sha256_root(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def git_value(source: pathlib.Path, expression: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", expression], text=True
    ).strip()


def load_tiles(source: pathlib.Path, period: int) -> list[Tile]:
    if git_value(source, "HEAD") != CAMPAIGN_COMMIT:
        raise ValueError("campaign checkout is not at the frozen commit")
    if git_value(source, "HEAD^{tree}") != CAMPAIGN_TREE:
        raise ValueError("campaign checkout has the wrong frozen tree")
    pool_path = source / "compute203" / "pool_merged.json"
    raw = pool_path.read_bytes()
    if sha256_root(raw) != POOL_ROOT:
        raise ValueError("campaign prime pool root drifted")
    pool = {int(prime): int(order) for prime, order in json.loads(raw).items()}
    tiles: list[Tile] = []
    for prime, order in sorted(pool.items(), key=lambda item: item[1]):
        if period % order:
            continue
        primitive = int(primitive_root(prime))
        generator = pow(primitive, (prime - 1) // order, prime)
        u = int(discrete_log(prime, 2, generator)) % order
        v = int(discrete_log(prime, 3, generator)) % order
        if math.gcd(math.gcd(u, v), order) != 1:
            raise ValueError(f"non-primitive tile coordinates for prime {prime}")
        tiles.append(Tile(prime, order, generator, u, v))
    return tiles


class Cnf:
    def __init__(self) -> None:
        self.variables = 0
        self.clauses: list[list[int]] = []

    def new_var(self) -> int:
        self.variables += 1
        return self.variables

    def add(self, *literals: int) -> None:
        self.clauses.append(list(literals))

    def exactly_one(self, variables: list[int]) -> None:
        self.clauses.append(variables[:])
        if len(variables) <= 1:
            return
        ladder = [self.new_var() for _ in range(len(variables) - 1)]
        self.add(-variables[0], ladder[0])
        for index in range(1, len(variables) - 1):
            self.add(-variables[index], ladder[index])
            self.add(-ladder[index - 1], ladder[index])
            self.add(-variables[index], -ladder[index - 1])
        self.add(-variables[-1], -ladder[-1])

    def write(self, path: pathlib.Path) -> str:
        with path.open("w", encoding="ascii", newline="\n") as stream:
            stream.write(f"p cnf {self.variables} {len(self.clauses)}\n")
            for clause in self.clauses:
                stream.write(" ".join(map(str, clause)) + " 0\n")
        return sha256_root(path.read_bytes())


def parse_model(path: pathlib.Path) -> set[int]:
    selected: set[int] = set()
    for line in path.read_text(encoding="ascii").splitlines():
        if not line.startswith("v "):
            continue
        selected.update(int(value) for value in line.split()[1:] if int(value) > 0)
    return selected


def run_solver(
    cadical: str,
    cnf_path: pathlib.Path,
    model_path: pathlib.Path,
    seconds: int,
) -> tuple[str, float]:
    model_path.unlink(missing_ok=True)
    started = time.monotonic()
    completed = subprocess.run(
        [cadical, "-q", "-t", str(seconds), "-w", str(model_path), str(cnf_path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    elapsed = time.monotonic() - started
    if completed.returncode == 10:
        return "sat", elapsed
    if completed.returncode == 20:
        return "unsat", elapsed
    if completed.returncode == 0:
        return "timeout", elapsed
    raise RuntimeError(
        f"CaDiCaL failed with {completed.returncode}: {completed.stderr.strip()}"
    )


def holes(
    tiles: list[Tile],
    shifts: list[int],
    period: int,
    limit: int,
    offset: int,
) -> tuple[list[tuple[int, int]], bool]:
    """Return deterministic holes and whether the complete torus was scanned."""

    columns = np.arange(period, dtype=np.int64)
    stride = 1429
    if math.gcd(stride, period) != 1:
        raise ValueError("row stride must permute the complete torus")
    found: list[tuple[int, int]] = []
    for step in range(period):
        k = (offset + stride * step) % period
        covered = np.zeros(period, dtype=np.bool_)
        for tile, shift in zip(tiles, shifts, strict=True):
            covered |= (tile.u * k + tile.v * columns) % tile.n == shift
        missing = np.flatnonzero(~covered)
        for value in missing:
            found.append((int(k), int(value)))
            if len(found) >= limit:
                return found, False
    return found, True


def crt(congruences: list[tuple[int, int]]) -> tuple[int, int]:
    value = 0
    modulus = 1
    for prime, residue in congruences:
        step = ((residue - value) * pow(modulus, -1, prime)) % prime
        value = (value + modulus * step) % (modulus * prime)
        modulus *= prime
    return value, modulus


def certificate(tiles: list[Tile], shifts: list[int]) -> dict[str, Any]:
    rows = []
    congruences = []
    for tile, shift in zip(tiles, shifts, strict=True):
        rows.append(
            {"p": tile.p, "n": tile.n, "g": tile.g, "u": tile.u, "v": tile.v, "c": shift}
        )
        target_residue = pow(tile.g, shift, tile.p)
        congruences.append((tile.p, (-pow(target_residue, -1, tile.p)) % tile.p))
    witness, modulus = crt(congruences)
    while witness <= max(tile.p for tile in tiles) or math.gcd(witness, 6) != 1:
        witness += modulus
    return {
        "schema": "erdos-frontier.erdos-203-cover-certificate.v1",
        "problem": 203,
        "target": TARGET,
        "problem_claim": PROBLEM_CLAIM,
        "source": SOURCE,
        "rows": rows,
        "m": str(witness),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-source", required=True, type=pathlib.Path)
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--period", type=int, default=5040)
    parser.add_argument("--wall-seconds", type=int, default=3600)
    parser.add_argument("--solver-seconds", type=int, default=120)
    parser.add_argument("--max-iterations", type=int, default=200)
    parser.add_argument("--holes-per-iteration", type=int, default=512)
    parser.add_argument("--candidate", type=pathlib.Path)
    args = parser.parse_args()

    cadical = shutil.which("cadical")
    if cadical is None:
        raise SystemExit("cadical is required")
    args.work_dir.mkdir(parents=True, exist_ok=True)
    tiles = load_tiles(args.campaign_source.resolve(), args.period)
    if args.period == 5040 and len(tiles) != 31:
        raise SystemExit(f"expected 31 frozen tiles, found {len(tiles)}")
    density = sum(1 / tile.n for tile in tiles)

    cnf = Cnf()
    shift_vars: list[list[int]] = []
    reverse: dict[int, tuple[int, int]] = {}
    for tile_index, tile in enumerate(tiles):
        variables = []
        for shift in range(tile.n):
            variable = cnf.new_var()
            variables.append(variable)
            reverse[variable] = (tile_index, shift)
        shift_vars.append(variables)
        cnf.exactly_one(variables)
    # Translating the lattice origin can send any one primitive tile shift to
    # zero, so this removes only equivalent global-translation solutions.
    cnf.add(shift_vars[0][0])

    registered_points: set[tuple[int, int]] = set()

    def add_point(k: int, ell: int) -> None:
        point = (k % args.period, ell % args.period)
        if point in registered_points:
            return
        cnf.clauses.append(
            [shift_vars[index][(tile.u * point[0] + tile.v * point[1]) % tile.n]
             for index, tile in enumerate(tiles)]
        )
        registered_points.add(point)

    for k in range(32):
        for ell in range(32):
            add_point(k, ell)

    started = time.monotonic()
    result: dict[str, Any] = {
        "schema": "erdos-frontier.erdos-203-search-5040-result.v1",
        "target": TARGET,
        "authority": "non_authoritative",
        "claim_credit": False,
        "period": args.period,
        "tiles": len(tiles),
        "density": density,
        "source": SOURCE["campaign"],
        "pool_root": POOL_ROOT,
        "solver": subprocess.check_output([cadical, "--version"], text=True).strip(),
        "iterations": [],
        "nonclaims": [
            "UNSAT for this selected family is not global nonexistence.",
            "A timed-out or bounded search is not evidence that no cover exists.",
            "A producer candidate is not valid until the frozen independent verifier passes.",
            "A verifier pass is not an attributed human Decision or scientific Standing.",
        ],
    }
    status = "budget_exhausted"
    cnf_path = args.work_dir / "search.cnf"
    model_path = args.work_dir / "model.sol"
    for iteration in range(args.max_iterations):
        remaining = args.wall_seconds - (time.monotonic() - started)
        if remaining <= 0:
            break
        cnf_root = cnf.write(cnf_path)
        solver_status, solver_elapsed = run_solver(
            cadical,
            cnf_path,
            model_path,
            max(1, min(args.solver_seconds, int(remaining))),
        )
        entry: dict[str, Any] = {
            "iteration": iteration,
            "points": len(registered_points),
            "variables": cnf.variables,
            "clauses": len(cnf.clauses),
            "cnf_root": cnf_root,
            "solver_status": solver_status,
            "solver_seconds": round(solver_elapsed, 6),
        }
        result["iterations"].append(entry)
        print(json.dumps(entry, sort_keys=True), flush=True)
        if solver_status == "unsat":
            status = "unsat_selected_family"
            break
        if solver_status == "timeout":
            status = "solver_timeout"
            break
        selected = parse_model(model_path)
        shifts = [-1] * len(tiles)
        for variable in selected:
            location = reverse.get(variable)
            if location is None:
                continue
            tile_index, shift = location
            shifts[tile_index] = shift
        if any(shift < 0 for shift in shifts):
            raise RuntimeError("SAT model omitted an exactly-one tile shift")
        missing, complete_scan = holes(
            tiles,
            shifts,
            args.period,
            args.holes_per_iteration,
            iteration % args.period,
        )
        entry["holes_found"] = len(missing)
        entry["complete_torus_scan"] = complete_scan
        if not missing and complete_scan:
            output = args.candidate or (args.work_dir / "erdos203-cover-certificate.v1.json")
            output.write_bytes(canonical_bytes(certificate(tiles, shifts)))
            entry["candidate"] = str(output)
            entry["candidate_root"] = sha256_root(output.read_bytes())
            status = "cover_candidate"
            break
        before = len(registered_points)
        for point in missing:
            add_point(*point)
        entry["new_points"] = len(registered_points) - before

    result["status"] = status
    result["wall_seconds"] = round(time.monotonic() - started, 6)
    result["registered_points"] = len(registered_points)
    result["final_cnf_root"] = cnf.write(cnf_path)
    result_path = args.work_dir / "result.v1.json"
    result_path.write_bytes(canonical_bytes(result))
    print(json.dumps({"result": str(result_path), "status": status}, sort_keys=True))
    return 0 if status in {"cover_candidate", "unsat_selected_family"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

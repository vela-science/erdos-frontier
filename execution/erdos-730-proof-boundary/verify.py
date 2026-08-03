#!/usr/bin/env python3
"""Verify the exact source boundary for the retained Erdős 730 proof.

This verifier checks Git object identities, source bytes, toolchains, the
terminal proof lineage, and a compact source-equivalence report.  Mechanical
passage is evidence only: it neither decides statement equivalence nor changes
Vela Standing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
from typing import Any

TARGET = "erdos:730:external-proof-boundary"
REPORT_SCHEMA = "erdos-frontier.erdos-730-boundary-report.v1"
LEAN_PROOFS = {
    "repository": "https://github.com/williamjblair/lean-proofs.git",
    "snapshot_commit": "4f915a323443bfb1709a6805a013812016dca88a",
    "snapshot_tree": "a0aaa84d22ed8fab7c2788bced29472953cc1752",
    "terminal_solve_commit": "8c85623069b3923afe418876d06459dbc4d24a51",
    "terminal_path": "ErdosProblems/Erdos730FullDensityTheorem.lean",
    "terminal_sha256": "sha256:7f341400b34cd3241007dce7365aa84c367546ffda0acf164d7a32e003f98ba0",
    "terminal_declaration": "Erdos730.FullDensityTheorem.pairSet_infinite",
    "lean_toolchain": "leanprover/lean4:v4.29.1",
    "mathlib_commit": "5e932f97dd25535344f80f9dd8da3aab83df0fe6",
    "erdos_730_module_count": 74,
}
FORMAL_CONJECTURES = {
    "repository": "https://github.com/google-deepmind/formal-conjectures.git",
    "commit": "50ee83fa7dc31c99c03c83f04be90b7fea37d314",
    "tree": "af55637ba163e4381b00cd0fca0f59158c6998f3",
    "path": "FormalConjectures/ErdosProblems/730.lean",
    "blob_sha1": "d37ca5fc59eb615e7406dff2c7881e1600d15d58",
    "sha256": "sha256:c8e532aa2916312501375df4e30ca4770fdeb3968d39622dda5cdfc5f9fa26e7",
    "declaration": "Erdos730.erdos_730",
    "lean_toolchain": "leanprover/lean4:v4.27.0",
    "mathlib_commit": "a3a10db0e9d66acbebf76c5e6a135066525ac900",
}
REQUIRED_DIMENSIONS = {
    "domain_and_pair_order",
    "central_binomial_definition",
    "prime_support_equality",
    "conclusion_strength",
    "proof_assumptions_and_axioms",
    "toolchain_and_import_boundary",
}
ALLOWED_CONCLUSIONS = {"equivalent", "not_equivalent", "indeterminate"}
ALLOWED_NEXT_ROUTES = {
    "authorized_external_proof_boundary_decision",
    "ported_or_affirmative_bridge_in_formal_conjectures",
    "resolve_source_equivalence_gap",
}
FORBIDDEN_SOURCE_TOKENS = re.compile(
    r"(?<![A-Za-z0-9_])(sorry|admit|axiom|opaque|unsafe)(?![A-Za-z0-9_])"
)


class VerificationError(ValueError):
    """The supplied source or report violates the frozen boundary."""


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def git_bytes(repository: pathlib.Path, *args: str) -> bytes:
    process = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
    )
    return process.stdout


def git_text(repository: pathlib.Path, *args: str) -> str:
    return git_bytes(repository, *args).decode().strip()


def mathlib_revision(manifest: bytes) -> str:
    try:
        value = json.loads(manifest)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError("lake manifest is not valid JSON") from error
    row = next(
        (
            package
            for package in value.get("packages", [])
            if package.get("name") == "mathlib"
        ),
        None,
    )
    if not isinstance(row, dict) or not isinstance(row.get("rev"), str):
        raise VerificationError("lake manifest does not pin mathlib")
    return row["rev"]


def code_without_comments(source: str) -> str:
    """Remove nested Lean comments while preserving code and strings."""

    output: list[str] = []
    index = 0
    depth = 0
    in_string = False
    while index < len(source):
        pair = source[index : index + 2]
        if depth:
            if pair == "/-":
                depth += 1
                index += 2
            elif pair == "-/":
                depth -= 1
                index += 2
            else:
                index += 1
            continue
        if not in_string and pair == "/-":
            depth = 1
            index += 2
            continue
        if not in_string and pair == "--":
            newline = source.find("\n", index)
            index = len(source) if newline < 0 else newline
            continue
        character = source[index]
        output.append(character)
        if character == '"' and (index == 0 or source[index - 1] != "\\"):
            in_string = not in_string
        index += 1
    if depth:
        raise VerificationError("Lean source contains an unterminated comment")
    return "".join(output)


def validate_lean_proofs(repository: pathlib.Path) -> dict[str, Any]:
    snapshot = LEAN_PROOFS["snapshot_commit"]
    terminal = LEAN_PROOFS["terminal_solve_commit"]
    if git_text(repository, "rev-parse", f"{snapshot}^{{tree}}") != LEAN_PROOFS[
        "snapshot_tree"
    ]:
        raise VerificationError("lean-proofs snapshot tree differs")
    ancestry = subprocess.run(
        ["git", "-C", str(repository), "merge-base", "--is-ancestor", terminal, snapshot]
    )
    if ancestry.returncode != 0:
        raise VerificationError("terminal solve is not an ancestor of the snapshot")
    path = LEAN_PROOFS["terminal_path"]
    terminal_bytes = git_bytes(repository, "show", f"{terminal}:{path}")
    snapshot_bytes = git_bytes(repository, "show", f"{snapshot}:{path}")
    if terminal_bytes != snapshot_bytes or sha256(snapshot_bytes) != LEAN_PROOFS[
        "terminal_sha256"
    ]:
        raise VerificationError("terminal Erdős 730 theorem bytes differ")
    toolchain = git_text(repository, "show", f"{snapshot}:lean-toolchain")
    manifest = git_bytes(repository, "show", f"{snapshot}:lake-manifest.json")
    if toolchain != LEAN_PROOFS["lean_toolchain"]:
        raise VerificationError("lean-proofs toolchain differs")
    if mathlib_revision(manifest) != LEAN_PROOFS["mathlib_commit"]:
        raise VerificationError("lean-proofs mathlib revision differs")
    paths = [
        path
        for path in git_text(repository, "ls-tree", "-r", "--name-only", snapshot).splitlines()
        if path.startswith("ErdosProblems/Erdos730") and path.endswith(".lean")
    ]
    if len(paths) != LEAN_PROOFS["erdos_730_module_count"]:
        raise VerificationError("Erdős 730 module count differs")
    for module_path in paths:
        source = git_bytes(repository, "show", f"{snapshot}:{module_path}").decode()
        match = FORBIDDEN_SOURCE_TOKENS.search(
            code_without_comments(source)
        )
        if match:
            raise VerificationError(
                f"Erdős 730 source contains forbidden token {match.group(1)}"
            )
    declaration = "theorem pairSet_infinite : FullDensityCore.PairSet.Infinite := by"
    if declaration not in snapshot_bytes.decode():
        raise VerificationError("terminal theorem declaration differs")
    return {
        "snapshot_commit": snapshot,
        "snapshot_tree": LEAN_PROOFS["snapshot_tree"],
        "terminal_solve_commit": terminal,
        "terminal_root": LEAN_PROOFS["terminal_sha256"],
        "module_count": len(paths),
        "toolchain": toolchain,
        "mathlib_commit": LEAN_PROOFS["mathlib_commit"],
        "proof_escape_tokens": [],
    }


def validate_formal_conjectures(repository: pathlib.Path) -> dict[str, Any]:
    commit = FORMAL_CONJECTURES["commit"]
    if git_text(repository, "rev-parse", f"{commit}^{{tree}}") != FORMAL_CONJECTURES[
        "tree"
    ]:
        raise VerificationError("Formal Conjectures tree differs")
    path = FORMAL_CONJECTURES["path"]
    source = git_bytes(repository, "show", f"{commit}:{path}")
    if sha256(source) != FORMAL_CONJECTURES["sha256"]:
        raise VerificationError("Formal Conjectures Erdős 730 bytes differ")
    blob = git_text(repository, "ls-tree", commit, "--", path).split()[2]
    if blob != FORMAL_CONJECTURES["blob_sha1"]:
        raise VerificationError("Formal Conjectures Erdős 730 blob differs")
    toolchain = git_text(repository, "show", f"{commit}:lean-toolchain")
    manifest = git_bytes(repository, "show", f"{commit}:lake-manifest.json")
    if toolchain != FORMAL_CONJECTURES["lean_toolchain"]:
        raise VerificationError("Formal Conjectures toolchain differs")
    if mathlib_revision(manifest) != FORMAL_CONJECTURES["mathlib_commit"]:
        raise VerificationError("Formal Conjectures mathlib revision differs")
    if "theorem erdos_730 : answer(sorry) ↔ S.Infinite := by" not in source.decode():
        raise VerificationError("Formal Conjectures theorem declaration differs")
    return {
        "commit": commit,
        "tree": FORMAL_CONJECTURES["tree"],
        "source_root": FORMAL_CONJECTURES["sha256"],
        "toolchain": toolchain,
        "mathlib_commit": FORMAL_CONJECTURES["mathlib_commit"],
    }


def validate_report(report_path: pathlib.Path) -> dict[str, Any]:
    raw = report_path.read_bytes()
    try:
        report = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError("boundary report is not valid JSON") from error
    canonical = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if raw != canonical.encode() + b"\n":
        raise VerificationError("boundary report must be canonical JSON")
    matrix = report.get("matrix")
    if (
        report.get("schema") != REPORT_SCHEMA
        or report.get("target") != TARGET
        or report.get("authority") != "non_authoritative"
        or report.get("accepted_state_change") != "none"
        or report.get("conclusion") not in ALLOWED_CONCLUSIONS
        or not isinstance(matrix, dict)
        or set(matrix) != REQUIRED_DIMENSIONS
        or report.get("next_route") not in ALLOWED_NEXT_ROUTES
        or report.get("sources")
        != {"formal_conjectures": FORMAL_CONJECTURES, "lean_proofs": LEAN_PROOFS}
    ):
        raise VerificationError("boundary report crosses its frozen source contract")
    if not all(isinstance(value, str) and value.strip() for value in matrix.values()):
        raise VerificationError("every source-equivalence dimension needs a finding")
    discrepancies = report.get("discrepancies")
    nonclaims = report.get("nonclaims")
    if not isinstance(discrepancies, list) or not isinstance(nonclaims, list):
        raise VerificationError("report must retain discrepancies and nonclaims")
    if not all(isinstance(item, str) and item.strip() for item in nonclaims):
        raise VerificationError("report nonclaims are malformed")
    required_nonclaims = (
        "external acceptance",
        "Vela causality",
        "Standing",
        "Lean 4.29.1",
        "Lean 4.27.0",
    )
    joined = " ".join(nonclaims)
    if any(value not in joined for value in required_nonclaims):
        raise VerificationError("report omits a required boundary nonclaim")
    if (
        report["conclusion"] == "equivalent"
        and report["next_route"] == "resolve_source_equivalence_gap"
    ):
        raise VerificationError("equivalent report retains the wrong next route")
    if (
        report["conclusion"] != "equivalent"
        and report["next_route"] != "resolve_source_equivalence_gap"
    ):
        raise VerificationError("unresolved equivalence cannot cross the proof boundary")
    return report


def compile_external(repository: pathlib.Path) -> None:
    if git_text(repository, "rev-parse", "HEAD") != LEAN_PROOFS["snapshot_commit"]:
        raise VerificationError("compilation checkout is not the pinned snapshot")
    if git_text(repository, "status", "--porcelain=v1", "--untracked-files=all"):
        raise VerificationError("compilation checkout is dirty")
    for module in (
        "ErdosProblems/Erdos730FullDensityTheorem.lean",
        "ErdosProblems/Erdos730FullDensityTheoremAudit.lean",
    ):
        process = subprocess.run(
            ["lake", "env", "lean", module],
            cwd=repository,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        if process.returncode != 0:
            raise VerificationError(
                f"native Lean failed for {module}; "
                f"stdout_root={sha256(process.stdout.encode())}; "
                f"stderr_root={sha256(process.stderr.encode())}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lean-proofs", type=pathlib.Path, required=True)
    parser.add_argument("--formal-conjectures", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path)
    parser.add_argument("--compile-external", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        sources = {
            "lean_proofs": validate_lean_proofs(args.lean_proofs.resolve()),
            "formal_conjectures": validate_formal_conjectures(
                args.formal_conjectures.resolve()
            ),
        }
        if args.compile_external:
            compile_external(args.lean_proofs.resolve())
        report = validate_report(args.report.resolve()) if args.report else None
        result = {
            "schema": "erdos-frontier.erdos-730-boundary-verification.v1",
            "outcome": "pass",
            "authority": "non_authoritative",
            "target": TARGET,
            "sources": sources,
            "external_native_lean_passed": args.compile_external,
            "report_root": sha256(args.report.read_bytes()) if args.report else None,
            "report_conclusion": report.get("conclusion") if report else None,
            "semantic_review_required": True,
            "accepted_state_change": "none",
        }
    except (OSError, subprocess.SubprocessError, VerificationError) as error:
        result = {
            "schema": "erdos-frontier.erdos-730-boundary-verification.v1",
            "outcome": "fail",
            "authority": "non_authoritative",
            "target": TARGET,
            "error": str(error),
            "accepted_state_change": "none",
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

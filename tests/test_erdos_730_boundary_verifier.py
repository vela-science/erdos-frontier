from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERIFIER_PATH = ROOT / "execution/erdos-730-proof-boundary/verify.py"
SPEC = importlib.util.spec_from_file_location("erdos_730_boundary_verifier", VERIFIER_PATH)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def report(conclusion: str = "equivalent") -> dict[str, object]:
    next_route = (
        "authorized_external_proof_boundary_decision"
        if conclusion == "equivalent"
        else "resolve_source_equivalence_gap"
    )
    return {
        "schema": VERIFIER.REPORT_SCHEMA,
        "target": VERIFIER.TARGET,
        "authority": "non_authoritative",
        "sources": {
            "formal_conjectures": VERIFIER.FORMAL_CONJECTURES,
            "lean_proofs": VERIFIER.LEAN_PROOFS,
        },
        "conclusion": conclusion,
        "matrix": {name: f"finding for {name}" for name in VERIFIER.REQUIRED_DIMENSIONS},
        "discrepancies": ["Lean and mathlib versions differ."],
        "next_route": next_route,
        "nonclaims": [
            "This does not establish external acceptance.",
            "This does not establish Vela causality.",
            "This does not change Standing.",
            "Lean 4.29.1 evidence is not silently a Lean 4.27.0 artifact.",
        ],
        "accepted_state_change": "none",
    }


def write_report(path: pathlib.Path, value: dict[str, object]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )


def test_equivalent_report_retains_external_boundary(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "report.json"
    value = report()
    write_report(path, value)
    assert VERIFIER.validate_report(path) == value


def test_unresolved_report_cannot_select_acceptance_route(
    tmp_path: pathlib.Path,
) -> None:
    path = tmp_path / "report.json"
    value = report("indeterminate")
    value["next_route"] = "authorized_external_proof_boundary_decision"
    write_report(path, value)
    with pytest.raises(VERIFIER.VerificationError, match="cannot cross"):
        VERIFIER.validate_report(path)


def test_report_must_retain_version_and_authority_nonclaims(
    tmp_path: pathlib.Path,
) -> None:
    path = tmp_path / "report.json"
    value = report()
    value["nonclaims"] = ["Standing remains unchanged."]
    write_report(path, value)
    with pytest.raises(VERIFIER.VerificationError, match="required boundary nonclaim"):
        VERIFIER.validate_report(path)


def test_mathlib_revision_is_exact() -> None:
    manifest = {"packages": [{"name": "mathlib", "rev": "exact-revision"}]}
    assert VERIFIER.mathlib_revision(json.dumps(manifest).encode()) == "exact-revision"


def test_comment_mentions_do_not_create_false_proof_escape() -> None:
    source = "/- nested /- axiom -/ comment -/\n-- sorry\ntheorem t : True := by trivial\n"
    assert VERIFIER.FORBIDDEN_SOURCE_TOKENS.search(
        VERIFIER.code_without_comments(source)
    ) is None


def test_actual_proof_escape_remains_visible() -> None:
    source = "/- harmless -/\ntheorem t : True := by sorry\n"
    match = VERIFIER.FORBIDDEN_SOURCE_TOKENS.search(
        VERIFIER.code_without_comments(source)
    )
    assert match is not None and match.group(1) == "sorry"

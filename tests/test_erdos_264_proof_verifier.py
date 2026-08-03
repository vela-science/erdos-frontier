from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERIFIER_PATH = ROOT / "execution/erdos-264-proof-repair/verify.py"
SPEC = importlib.util.spec_from_file_location("erdos_264_proof_verifier", VERIFIER_PATH)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def source(body: str) -> bytes:
    return (
        "prefix\n"
        + VERIFIER.THEOREM_MARKER
        + body
        + VERIFIER.NEXT_DECLARATION_MARKER
        + "\nsuffix\n"
    ).encode()


def test_candidate_may_change_only_the_target_proof() -> None:
    original = source("\n  sorry")
    candidate = source("\n  exact fun h ↦ False.elim (by contradiction)")
    proof = VERIFIER.validate_candidate(original, candidate)
    assert "exact fun h" in proof


@pytest.mark.parametrize("token", ["sorry", "admit", "axiom", "opaque", "unsafe"])
def test_candidate_rejects_proof_escape_tokens(token: str) -> None:
    with pytest.raises(VERIFIER.VerificationError, match="forbidden token"):
        VERIFIER.validate_candidate(source("\n  sorry"), source(f"\n  {token}"))


def test_candidate_rejects_unrelated_source_change() -> None:
    candidate = source("\n  exact fun h ↦ False.elim (by contradiction)").replace(
        b"prefix", b"changed"
    )
    with pytest.raises(VERIFIER.VerificationError, match="before"):
        VERIFIER.validate_candidate(source("\n  sorry"), candidate)


def test_axiom_report_rejects_sorry() -> None:
    with pytest.raises(VERIFIER.VerificationError, match="forbidden axioms"):
        VERIFIER.parse_axioms(
            "Erdos264.erdos_264.parts.i depends on axioms: [propext, sorryAx]"
        )


def test_axiom_report_accepts_only_permitted_axioms() -> None:
    assert VERIFIER.parse_axioms(
        "Erdos264.erdos_264.parts.i depends on axioms: "
        "[propext, Classical.choice, Quot.sound]"
    ) == ["Classical.choice", "Quot.sound", "propext"]


def test_native_checker_makes_its_unlimited_heartbeat_contract_explicit() -> None:
    assert VERIFIER.LEAN_HEARTBEAT_MODE == "unlimited"
    assert VERIFIER.LEAN_COMMAND == (
        "lake",
        "env",
        "lean",
        "-DmaxHeartbeats=0",
    )

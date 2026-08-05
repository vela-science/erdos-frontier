from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate_target_closure import TargetClosureError, validate  # noqa: E402
from build_target_index import (  # noqa: E402
    ERDOS_203_CHORDAL_PACKET_PATH,
    ERDOS_203_PACKET_PATH,
    ERDOS_264_CORRECTION_CLAIM,
    ERDOS_264_PACKET_PATH,
    ERDOS_730_PACKET_PATH,
    erdos_203_chordal_execution_input_paths,
    erdos_203_execution_input_paths,
    erdos_264_correction_accepted,
    erdos_264_execution_input_paths,
    erdos_264_proof_repair_complete,
    erdos_264_target_available,
    erdos_730_execution_input_paths,
    execution_input_paths,
    fidelity_work_complete,
    fidelity_execution_input_paths,
    git_source_commit,
    target_from_validation,
    validate_erdos_203_chordal_packet,
    validate_erdos_203_packet,
    validate_erdos_264_packet,
    validate_erdos_730_packet,
)


def _copy(root: pathlib.Path, relative: str) -> None:
    source = ROOT / relative
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


@pytest.fixture
def frontier(tmp_path: pathlib.Path) -> pathlib.Path:
    closure_paths = [
        "targets/closures/erdos-1056-10429601-10429800.json",
        "targets/closures/erdos-1056-10429801-10430000.json",
        "targets/closures/erdos-1056-10430001-10430200.json",
        "targets/closures/erdos-1056-10430201-10430400.json",
        "targets/closures/erdos-1056-10430401-10430600.json",
    ]
    closures = [json.loads((ROOT / path).read_text()) for path in closure_paths]
    successor_packet = (ROOT / "targets/erdos-1056.json").read_bytes()
    paths = {
        *(row["path"] for closure in closures for row in closure["evidence"]),
    }
    for closure in closures:
        completed_packet = json.loads(
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(ROOT),
                    "show",
                    f"{closure['completed_packet']['git_commit']}:"
                    f"{closure['completed_packet']['path']}",
                ],
                check=True,
                capture_output=True,
            ).stdout
        )
        paths.update(
            locator["path"]
            for locator in (completed_packet.get("execution_contracts") or {}).values()
        )
        submission_row = next(
            row for row in closure["evidence"] if row["kind"] == "submission"
        )
        submission = json.loads((ROOT / submission_row["path"]).read_text())
        # Historical Canopus records retain sidecar manifests at their authored
        # paths. Current direct Submissions need only the content-addressed
        # retained Artifact referenced by the closure; the producer's mutable
        # output path is deliberately disposable after registration.
        paths.update(
            row["path"]
            for row in submission["artifacts"]
            if (ROOT / row["path"]).is_file()
        )
    for relative in sorted(paths):
        _copy(tmp_path, relative)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "config",
            "user.email",
            "target-test@vela.invalid",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Vela Target Test"],
        check=True,
    )

    retained_commits: list[str] = []
    for index, closure in enumerate(closures, start=1):
        for relative, commit in (
            (
                closure["completed_packet"]["path"],
                closure["completed_packet"]["git_commit"],
            ),
            (".vela/repository.json", closure["repository_commit"]),
        ):
            retained = subprocess.run(
                ["git", "-C", str(ROOT), "show", f"{commit}:{relative}"],
                check=True,
                capture_output=True,
            ).stdout
            destination = tmp_path / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(retained)
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(tmp_path),
                "commit",
                "-qm",
                f"retain completed packet {index}",
            ],
            check=True,
        )
        retained_commits.append(
            subprocess.run(
                ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )

    # The retained commits above prove historical closure. The live successor
    # packet binds its source commit/tree and accepted Claims; targets.json
    # separately binds the current repository root.
    (tmp_path / ".vela/repository.json").write_bytes(
        (ROOT / ".vela/repository.json").read_bytes()
    )
    successor = json.loads(successor_packet)
    _write(tmp_path / "targets/erdos-1056.json", successor)
    for path, closure, retained_commit in zip(
        closure_paths, closures, retained_commits, strict=True
    ):
        closure["completed_packet"]["git_commit"] = retained_commit
        closure["repository_commit"] = retained_commit
        _write(tmp_path / path, closure)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-qm", "expose successor packet"],
        check=True,
    )
    return tmp_path


def _read(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


def _write(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def test_exact_closure_derives_first_uncovered_interval(
    frontier: pathlib.Path,
) -> None:
    result = validate(frontier)
    assert result["closed_range"] == {"first": 10430401, "last": 10430600}
    assert result["closure_basis"] == "verified_submission"
    assert result["accepted_coverage"] == {"first": 10430601, "last": 10430800}
    assert result["successor_range"] == {"first": 10430801, "last": 10431000}
    assert (
        result["completion_claim_root"]
        == "sha256:f0bc52506e71391e8f7e9737dc48f29bf7a6227b67cfe431723a25415fc7698a"
    )


def test_completed_successor_is_rejected(frontier: pathlib.Path) -> None:
    path = frontier / "targets/erdos-1056.json"
    packet = _read(path)
    packet["target"]["next_bounded_range"] = {
        "first": 10429601,
        "last": 10429800,
        "inclusive": True,
    }
    _write(path, packet)
    with pytest.raises(TargetClosureError, match="successor range differs|overlaps"):
        validate(frontier)


def test_overlapping_closure_is_rejected(frontier: pathlib.Path) -> None:
    original = frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    duplicate = frontier / "targets/closures/overlap.json"
    duplicate.write_bytes(original.read_bytes())
    subprocess.run(["git", "-C", str(frontier), "add", str(duplicate)], check=True)
    with pytest.raises(TargetClosureError, match="ranges overlap"):
        validate(frontier)


def test_malformed_range_is_rejected(frontier: pathlib.Path) -> None:
    path = frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    closure = _read(path)
    closure["completed_scope"]["first"] = "10429601"
    _write(path, closure)
    with pytest.raises(TargetClosureError, match="malformed"):
        validate(frontier)


def test_untracked_input_is_rejected(frontier: pathlib.Path) -> None:
    relative = "targets/closures/erdos-1056-10429601-10429800.json"
    subprocess.run(
        ["git", "-C", str(frontier), "rm", "--cached", "-q", "--", relative],
        check=True,
    )
    with pytest.raises(TargetClosureError, match="untracked"):
        validate(frontier)


def test_evidence_root_drift_is_rejected(frontier: pathlib.Path) -> None:
    claim = (
        frontier
        / "records/claims/sha256/226cdf85adf6edcaf67a3680ffd52a3c3e3cab5ad9dea9e12b8577d69e02f5fc.json"
    )
    claim.write_bytes(claim.read_bytes() + b" ")
    with pytest.raises(TargetClosureError, match="root drift"):
        validate(frontier)


def test_completed_packet_git_bytes_are_bound(frontier: pathlib.Path) -> None:
    path = frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    closure = _read(path)
    closure["completed_packet"]["git_commit"] = subprocess.run(
        ["git", "-C", str(frontier), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _write(path, closure)
    with pytest.raises(TargetClosureError, match="Git bytes drifted"):
        validate(frontier)


def test_verified_submission_needs_no_decision_or_accepted_claim(
    frontier: pathlib.Path,
) -> None:
    result = validate(frontier)
    assert result["closure_basis"] == "verified_submission"
    assert result["verification_root"].startswith("sha256:")


def test_verified_submission_requires_verification(
    frontier: pathlib.Path,
) -> None:
    closure_path = frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    closure = _read(closure_path)
    closure["evidence"] = [
        row for row in closure["evidence"] if row["kind"] != "verification"
    ]
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="evidence kinds differ"):
        validate(frontier)


def test_tampered_rerooted_completion_artifact_is_rejected(
    frontier: pathlib.Path,
) -> None:
    closure_path = frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    closure = _read(closure_path)
    artifact_row = next(row for row in closure["evidence"] if row["kind"] == "artifact")
    artifact_path = frontier / artifact_row["path"]
    artifact_path.write_text(
        artifact_path.read_text().replace("primes_tested=13", "primes_tested=12")
    )
    artifact_row["root"] = (
        "sha256:" + hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    )
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="prime count is incorrect"):
        validate(frontier)


def test_submission_without_exact_replay_is_rejected(
    frontier: pathlib.Path,
) -> None:
    closure_path = frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    closure = _read(closure_path)
    submission_row = next(
        row for row in closure["evidence"] if row["kind"] == "submission"
    )
    submission_path = frontier / submission_row["path"]
    submission = _read(submission_path)
    submission["replayability"] = "none"
    _write(submission_path, submission)
    submission_row["root"] = (
        "sha256:" + hashlib.sha256(submission_path.read_bytes()).hexdigest()
    )
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="not exactly replayable"):
        validate(frontier)


def test_verification_must_bind_every_replay_artifact(
    frontier: pathlib.Path,
) -> None:
    closure_path = frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    closure = _read(closure_path)
    verification_row = next(
        row for row in closure["evidence"] if row["kind"] == "verification"
    )
    verification_path = frontier / verification_row["path"]
    verification = _read(verification_path)
    verification["subject"]["artifact_ids"].pop()
    _write(verification_path, verification)
    verification_row["root"] = (
        "sha256:" + hashlib.sha256(verification_path.read_bytes()).hexdigest()
    )
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="every required artifact"):
        validate(frontier)


def test_verification_environment_must_bind_verifier_manifest(
    frontier: pathlib.Path,
) -> None:
    closure_path = frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    closure = _read(closure_path)
    verification_row = next(
        row for row in closure["evidence"] if row["kind"] == "verification"
    )
    verification_path = frontier / verification_row["path"]
    verification = _read(verification_path)
    verification["method"]["environment_root"] = "sha256:" + "0" * 64
    _write(verification_path, verification)
    verification_row["root"] = (
        "sha256:" + hashlib.sha256(verification_path.read_bytes()).hexdigest()
    )
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="environment"):
        validate(frontier)


def test_current_submission_must_bind_exact_execution_contracts(
    frontier: pathlib.Path,
) -> None:
    closure_path = frontier / "targets/closures/erdos-1056-10430401-10430600.json"
    closure = _read(closure_path)
    submission_row = next(
        row for row in closure["evidence"] if row["kind"] == "submission"
    )
    submission_path = frontier / submission_row["path"]
    submission = _read(submission_path)
    submission["execution_binding"]["result_contract_root"] = "sha256:" + "0" * 64
    _write(submission_path, submission)
    submission_row["root"] = (
        "sha256:" + hashlib.sha256(submission_path.read_bytes()).hexdigest()
    )
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="execution binding differs"):
        validate(frontier)


def test_current_result_contract_root_drift_is_rejected(
    frontier: pathlib.Path,
) -> None:
    contract_path = (
        frontier / "execution/erdos-1056/10430401-10430600/result-contract.v1.json"
    )
    contract = _read(contract_path)
    contract["range"]["last"] = 10430601
    _write(contract_path, contract)

    with pytest.raises(TargetClosureError, match="result contract root drifted"):
        validate(frontier)


def test_current_verification_must_satisfy_exact_independent_requirement(
    frontier: pathlib.Path,
) -> None:
    closure_path = frontier / "targets/closures/erdos-1056-10430401-10430600.json"
    closure = _read(closure_path)
    verification_row = next(
        row for row in closure["evidence"] if row["kind"] == "verification"
    )
    verification_path = frontier / verification_row["path"]
    verification = _read(verification_path)
    verification["scope"]["property"] = "A different property."
    _write(verification_path, verification)
    verification_row["root"] = (
        "sha256:" + hashlib.sha256(verification_path.read_bytes()).hexdigest()
    )
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="exact independent requirement"):
        validate(frontier)


def test_proposal_cannot_bind_another_submission(
    frontier: pathlib.Path,
) -> None:
    closure_path = frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    closure = _read(closure_path)
    proposal_row = next(row for row in closure["evidence"] if row["kind"] == "proposal")
    proposal_path = frontier / proposal_row["path"]
    proposal = _read(proposal_path)
    proposal["producer_package"]["root"] = "sha256:" + "0" * 64
    _write(proposal_path, proposal)
    proposal_row["root"] = (
        "sha256:" + hashlib.sha256(proposal_path.read_bytes()).hexdigest()
    )
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="does not bind the Submission"):
        validate(frontier)


def test_pending_submission_cannot_replace_accepted_coverage(
    frontier: pathlib.Path,
) -> None:
    packet_path = frontier / "targets/erdos-1056.json"
    packet = _read(packet_path)
    latest = packet["accepted_state"]["latest_bounded_negative"]
    repository = _read(frontier / ".vela/repository.json")
    pending = {
        "claim_id": "vcl_" + "f" * 64,
        "claim_root": "sha256:" + "e" * 64,
    }
    repository["pending_claims"].append(pending)
    _write(frontier / ".vela/repository.json", repository)
    latest["claim_id"] = pending["claim_id"]
    latest["claim_root"] = pending["claim_root"]
    _write(packet_path, packet)

    with pytest.raises(TargetClosureError, match="not accepted"):
        validate(frontier)


def test_prior_verified_submission_stays_closed_after_later_acceptance(
    frontier: pathlib.Path,
) -> None:
    result = validate(frontier)
    assert result["closed_range"]["last"] == 10430600
    assert result["accepted_coverage"]["last"] == 10430800
    assert result["successor_range"]["first"] == 10430801


def test_later_acceptance_reconciles_without_rewriting_closure(
    frontier: pathlib.Path,
) -> None:
    result = validate(frontier)
    assert result["accepted_coverage"]["last"] == 10430800
    assert result["successor_range"]["first"] == 10430801
    assert "pending review" not in target_from_validation(result)["why"]


def test_target_copy_uses_derived_successor_range() -> None:
    target = target_from_validation(
        {
            "accepted_coverage": {"first": 10430601, "last": 10430800},
            "closed_range": {"first": 10430401, "last": 10430600},
            "closure_basis": "verified_submission",
            "successor_range": {"first": 10430801, "last": 10431000},
        }
    )
    assert "10430801..10431000" in target["objective"]
    assert "ending at 10430800" in target["why"]


def test_execution_inputs_bind_only_the_exact_agent_bundle_files() -> None:
    assert execution_input_paths(ROOT) == [
        "execution/erdos-1056/10430801-10431000/producer-profile.v1.json",
        "execution/erdos-1056/10430801-10431000/result-contract.v1.json",
        "execution/erdos-1056/verifier/v1/linux-arm64/verifier",
        "execution/erdos-1056/verifier/v1/verifier.cpp",
    ]


def _copy_erdos_1056_execution_inputs(destination: pathlib.Path) -> None:
    for relative in [
        "targets/erdos-1056.json",
        "execution/erdos-1056/10430801-10431000/producer-profile.v1.json",
        "execution/erdos-1056/10430801-10431000/result-contract.v1.json",
        "execution/erdos-1056/verifier/v1/linux-arm64/verifier",
        "execution/erdos-1056/verifier/v1/verifier.cpp",
    ]:
        _copy(destination, relative)


def test_execution_inputs_reject_missing_result_contract(
    tmp_path: pathlib.Path,
) -> None:
    _copy_erdos_1056_execution_inputs(tmp_path)
    packet_path = tmp_path / "targets/erdos-1056.json"
    packet = _read(packet_path)
    packet["execution_contracts"].pop("result_contract")
    _write(packet_path, packet)

    with pytest.raises(ValueError, match="execution contract set differs"):
        execution_input_paths(tmp_path)


def test_execution_inputs_reject_changed_result_contract(
    tmp_path: pathlib.Path,
) -> None:
    _copy_erdos_1056_execution_inputs(tmp_path)
    contract_path = (
        tmp_path / "execution/erdos-1056/10430801-10431000/result-contract.v1.json"
    )
    contract = _read(contract_path)
    contract["verifier"]["witness_minimum_multiplicity"] = 15
    _write(contract_path, contract)

    with pytest.raises(ValueError, match="bytes differ from the locator"):
        execution_input_paths(tmp_path)


def test_astra_fidelity_packet_preserves_exact_source_and_authority_boundary() -> None:
    # This one-shot Target is already complete. Its packet remains bound to the
    # repository state it reviewed rather than being rewritten after unrelated
    # later Decisions.
    assert fidelity_work_complete(ROOT)
    packet = _read(ROOT / "targets/erdos-183-astra-fidelity.json")
    assert packet["authority"] == "non_authoritative"
    assert packet["review_contract"]["accepted_state_change"] == (
        "none until a separate authorized human Decision"
    )
    assert (
        packet["source_problem"]["status_observation"]["source_last_update"]
        < "2026-08-01"
    )
    assert packet["nonclaims"][0].startswith("Lean or Comparator passage")


def test_astra_fidelity_packet_binds_exact_execution_contracts() -> None:
    assert fidelity_execution_input_paths(ROOT) == [
        "execution/erdos-183-astra-fidelity/producer-profile.v1.json",
        "execution/erdos-183-astra-fidelity/result-contract.v1.json",
        "execution/erdos-183-astra-fidelity/reviewer-capsule.v1.json",
    ]
    packet = _read(ROOT / "targets/erdos-183-astra-fidelity.json")
    assert packet["execution_contracts"]["producer_profile"]["sha256"] == (
        "sha256:3fe54bd5fdffc8bb639155b4d408709082eee5aaf255b7d582ad17a4434f5f37"
    )
    assert packet["execution_contracts"]["verifier_capsule"]["sha256"] == (
        "sha256:aec9b1c3b91b1a2cdfaf6d3da8f051884b0017b31e7450d3148ba0565235d8ec"
    )
    assert packet["execution_contracts"]["result_contract"]["sha256"] == (
        "sha256:7618f6bbd2c5aa13653a771735c586e6cb24056b092854e20c19112471aff6b2"
    )


def test_erdos_264_repair_packet_is_exact_and_non_authoritative() -> None:
    validate_erdos_264_packet(ROOT)
    packet = _read(ERDOS_264_PACKET_PATH)
    assert packet["authority"] == "non_authoritative"
    assert packet["prerequisite"]["accepted_claim"] == ERDOS_264_CORRECTION_CLAIM
    assert packet["source"]["commit"] == ("e6d6b867dc85eec2f88bc47496b4314c623f9f92")
    assert packet["source"]["sha256"] == (
        "sha256:c59caaa2524e3edd52944e63f5d9bb0614f1bc36d7fb8a0fec7029c14c266b46"
    )


def test_erdos_203_target_binds_corrected_campaign_and_exact_verifier() -> None:
    validate_erdos_203_packet(ROOT)
    packet = _read(ERDOS_203_PACKET_PATH)
    assert packet["authority"] == "non_authoritative"
    assert packet["problem_claim"] == {
        "claim_id": "vcl_8131cdf07c70fe688bf18bc6ca274d6bff43eaeed116430351685e925bf4a796",
        "claim_root": "sha256:998616dbbf3a0f704bbab20504a15fe1e4ab92fe60524ab6ad8798eab3435e06",
    }
    assert packet["prior_work"]["source"]["commit"] == (
        "94fde841ea6ad90437bd66a91953bfeba13dba0f"
    )
    assert packet["prior_work"]["correction"]["commit"] == (
        "ccb4105e6b89837c226512ba87a79084cd01cfe5"
    )
    assert packet["formal_statement"] == {
        "blob_sha1": "2bc9f5fb212533aeb94c2328dbb5b53987a9f9ec",
        "commit": "50ee83fa7dc31c99c03c83f04be90b7fea37d314",
        "declaration": "Erdos203.erdos_203",
        "path": "FormalConjectures/ErdosProblems/203.lean",
        "repository": "https://github.com/google-deepmind/formal-conjectures.git",
        "sha256": "sha256:dfd0eb1bf073a27ad74a398acb7c2986b73be9cf72e6dc6ed9fc4618c6538cfb",
        "status": "merged_upstream",
        "tree": "af55637ba163e4381b00cd0fca0f59158c6998f3",
    }
    assert "99.98 percent" in packet["prior_work"]["correction"]["reason"]
    assert "repository" not in packet


def test_erdos_203_execution_inputs_bind_dependency_free_verifier() -> None:
    assert erdos_203_execution_input_paths(ROOT) == [
        "execution/erdos-203-cover/producer-profile.v1.json",
        "execution/erdos-203-cover/result-contract.v1.json",
        "execution/erdos-203-cover/verifier-capsule.v1.json",
        "execution/erdos-203-cover/verify.py",
    ]
    packet = _read(ERDOS_203_PACKET_PATH)
    assert all(
        forbidden not in json.dumps(packet["execution_contracts"])
        for forbidden in ("model", "worker", "budgets")
    )


def test_erdos_203_chordal_target_binds_bounded_no_credit_qualification() -> None:
    validate_erdos_203_chordal_packet(ROOT)
    packet = _read(ERDOS_203_CHORDAL_PACKET_PATH)
    assert packet["authority"] == "non_authoritative"
    preregistration = _read(ROOT / packet["preregistration"]["path"])
    assert preregistration["claim_credit"] is False
    assert packet["base_evidence"]["accepted_state_change"] == "none"
    assert packet["target"] == {
        "id": "erdos:203:chordal-obstruction",
        "objective": (
            "Independently qualify the exact 307-tile chordal-complex "
            "obstruction obtained by adjoining tile 19 over the mandatory "
            "triangle 31, 47, 71."
        ),
        "problem": 203,
        "state": "open",
    }
    assert "full solution" in packet["nonclaims"][0]


def test_erdos_203_chordal_inputs_bind_both_independent_checkers() -> None:
    assert erdos_203_chordal_execution_input_paths(ROOT) == [
        "artifacts/analyses/erdos203-two-complex-obstruction.v1.json",
        "execution/erdos-203-chordal/preregistration.v1.json",
        "execution/erdos-203-chordal/produce.py",
        "execution/erdos-203-chordal/producer-profile.v1.json",
        "execution/erdos-203-chordal/result-contract.v1.json",
        "execution/erdos-203-chordal/verifier-capsule.v1.json",
        "execution/erdos-203-chordal/verify.py",
        "execution/erdos-203-cover/verify_two_complex_obstruction.py",
    ]


def test_erdos_264_execution_inputs_bind_native_verifier() -> None:
    packet = _read(ERDOS_264_PACKET_PATH)
    assert packet["target"]["state"] == "available_after_accepted_correction"
    assert erdos_264_execution_input_paths(ROOT) == [
        "execution/erdos-264-proof-repair/producer-profile.v1.json",
        "execution/erdos-264-proof-repair/result-contract.v1.json",
        "execution/erdos-264-proof-repair/verifier-capsule.v1.json",
        "execution/erdos-264-proof-repair/verify.py",
    ]


def test_erdos_730_target_binds_complete_external_solution_and_transfer_gap() -> None:
    validate_erdos_730_packet(ROOT)
    packet = _read(ERDOS_730_PACKET_PATH)
    assert packet["authority"] == "non_authoritative"
    assert packet["external_proof"]["status"] == (
        "complete_kernel_checked_solution_in_source_repository"
    )
    assert packet["external_proof"]["snapshot_commit"] == (
        "4f915a323443bfb1709a6805a013812016dca88a"
    )
    assert packet["external_proof"]["terminal_solve_commit"] == (
        "8c85623069b3923afe418876d06459dbc4d24a51"
    )
    assert packet["external_proof"]["terminal_sha256"] == (
        "sha256:7f341400b34cd3241007dce7365aa84c367546ffda0acf164d7a32e003f98ba0"
    )
    assert packet["external_proof"]["erdos_730_module_count"] == 74
    assert packet["external_proof"]["lean_toolchain"] == "leanprover/lean4:v4.29.1"
    assert packet["formal_statement"]["lean_toolchain"] == (
        "leanprover/lean4:v4.27.0"
    )
    assert packet["current_frontier_standing"]["standing"].startswith("open")


def test_erdos_730_execution_inputs_bind_source_local_verifier() -> None:
    assert erdos_730_execution_input_paths(ROOT) == [
        "execution/erdos-730-proof-boundary/producer-profile.v1.json",
        "execution/erdos-730-proof-boundary/result-contract.v1.json",
        "execution/erdos-730-proof-boundary/verifier-capsule.v1.json",
        "execution/erdos-730-proof-boundary/verify.py",
    ]


def _copy_erdos_264_target(destination: pathlib.Path) -> None:
    for relative in [
        ".vela/repository.json",
        "targets/erdos-264-parts-i-proof-repair.json",
        *erdos_264_execution_input_paths(ROOT),
    ]:
        _copy(destination, relative)


def test_erdos_264_repair_remains_hidden_before_correction_decision(
    tmp_path: pathlib.Path,
) -> None:
    _copy_erdos_264_target(tmp_path)
    repository = _read(tmp_path / ".vela/repository.json")
    correction = next(
        row
        for row in repository["accepted_claims"]
        if row["claim_id"] == ERDOS_264_CORRECTION_CLAIM["claim_id"]
    )
    repository["accepted_claims"].remove(correction)
    repository["pending_claims"].append({**correction, "standing": "pending_review"})
    _write(tmp_path / ".vela/repository.json", repository)
    assert not erdos_264_correction_accepted(tmp_path)
    assert not erdos_264_target_available(tmp_path)
    correction = next(
        row
        for row in repository["pending_claims"]
        if row["claim_id"] == ERDOS_264_CORRECTION_CLAIM["claim_id"]
    )
    repository["pending_claims"].remove(correction)
    repository["accepted_claims"].append({**correction, "standing": "accepted"})
    _write(tmp_path / ".vela/repository.json", repository)
    assert erdos_264_correction_accepted(tmp_path)
    assert erdos_264_target_available(tmp_path)


def test_erdos_264_repair_closes_only_after_exact_passing_verification(
    tmp_path: pathlib.Path,
) -> None:
    _copy_erdos_264_target(tmp_path)
    packet_path = tmp_path / "targets/erdos-264-parts-i-proof-repair.json"
    packet = _read(packet_path)
    artifact_path = tmp_path / "artifacts/erdos264-parts-i-proof-repair/264.lean"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("exact candidate bytes\n")
    artifact_root = "sha256:" + hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    execution_binding = {
        "schema": "vela.execution-binding.v1",
        "packet_root": "sha256:" + hashlib.sha256(packet_path.read_bytes()).hexdigest(),
        "profile_root": packet["execution_contracts"]["producer_profile"]["sha256"],
        "verifier_capsule_root": packet["execution_contracts"]["verifier_capsule"][
            "sha256"
        ],
        "result_contract_root": packet["execution_contracts"]["result_contract"][
            "sha256"
        ],
    }
    submission = {
        "schema": "vela.submission.v1",
        "submission_id": "vsb_test",
        "execution_binding": execution_binding,
        "artifacts": [
            {
                "kind": "lean-source-repair",
                "path": "artifacts/erdos264-parts-i-proof-repair/264.lean",
                "digest": artifact_root,
            }
        ],
        "verification_requirements": [
            packet["verification_requirement"]
            + " Bind the exact artifact root and reported axiom set."
        ],
    }
    proposal = {
        "schema": "vela.proposal.v1",
        "proposal_id": "vpr_test",
        "producer_package": {},
        "subject": {"kind": "claim", "id": "vcl_test", "root": "sha256:" + "1" * 64},
    }
    verification = {
        "schema": "vela.verification-record.v1",
        "verification_record_id": "vvr_test",
        "outcome": "pass",
        "subject": {
            "claim_id": "vcl_test",
            "proposal_id": "vpr_test",
            "submission_id": "vsb_test",
            "submission_root": "",
            "artifact_ids": [artifact_root.removeprefix("sha256:")],
        },
        "method": {
            "profile": "erdos-264-parts-i-native-lean-v1",
            "implementation": "execution/erdos-264-proof-repair/verifier-capsule.v1.json",
            "environment_root": packet["execution_contracts"]["verifier_capsule"][
                "sha256"
            ],
        },
        "scope": {
            "property": packet["verification_requirement"]
            + " Bind the exact artifact root and reported axiom set."
        },
    }
    records = tmp_path / "records"
    submission_path = records / "submissions/submission.json"
    _write(submission_path, submission)
    submission_root = (
        "sha256:" + hashlib.sha256(submission_path.read_bytes()).hexdigest()
    )
    proposal["producer_package"] = {
        "kind": "submission_v1",
        "id": "vsb_test",
        "root": submission_root,
        "path": "records/submissions/submission.json",
    }
    verification["subject"]["submission_root"] = submission_root
    proposal_path = records / "proposals/proposal.json"
    verification_path = records / "verifications/verification.json"
    _write(proposal_path, proposal)
    _write(verification_path, verification)
    repository = _read(tmp_path / ".vela/repository.json")
    repository["pending_claims"].append(
        {
            "claim_id": "vcl_test",
            "claim_root": "sha256:" + "1" * 64,
            "path": "records/claims/test.json",
            "standing": "pending_review",
        }
    )
    repository["submissions"].append(
        {
            "id": "vsb_test",
            "path": "records/submissions/submission.json",
            "root": submission_root,
        }
    )
    repository["proposals"].append(
        {
            "id": "vpr_test",
            "path": "records/proposals/proposal.json",
            "root": "sha256:" + hashlib.sha256(proposal_path.read_bytes()).hexdigest(),
        }
    )
    repository["verifications"].append(
        {
            "id": "vvr_test",
            "path": "records/verifications/verification.json",
            "root": "sha256:"
            + hashlib.sha256(verification_path.read_bytes()).hexdigest(),
        }
    )
    _write(tmp_path / ".vela/repository.json", repository)
    assert erdos_264_proof_repair_complete(tmp_path)
    assert not erdos_264_target_available(tmp_path)
    verification["scope"]["property"] = ""
    _write(verification_path, verification)
    assert not erdos_264_proof_repair_complete(tmp_path)
    verification["scope"]["property"] = submission["verification_requirements"][0]
    verification["outcome"] = "fail"
    _write(verification_path, verification)
    assert not erdos_264_proof_repair_complete(tmp_path)


def test_astra_fidelity_work_is_complete_while_awaiting_decision() -> None:
    assert fidelity_work_complete(ROOT)


def test_generated_target_index_uses_vela_canonical_order() -> None:
    targets = _read(ROOT / "targets.json")["targets"]
    assert [
        (target["rank"], target["id"]) for target in targets
    ] == sorted((target["rank"], target["id"]) for target in targets)


@pytest.mark.parametrize(
    ("relative", "mutation"),
    [
        (
            "artifacts/fidelity/erdos-183-astra-fidelity.v1.json",
            lambda value: value["matrix"].pop("quantifiers"),
        ),
        (
            "records/proposals/sha256/5abe5d1742a2fa2bd71159c0debaf9f3b0d5c786d5dc84242d3a48af7a56cfc1.json",
            lambda value: value["producer_package"].update(
                {"root": "sha256:" + "0" * 64}
            ),
        ),
        (
            "records/verifications/sha256/6da941b2e6946f59b85b31df1f2d4bdc2472d8357f654b79952c1b8c21e53428.json",
            lambda value: value.update({"outcome": "fail"}),
        ),
    ],
)
def test_astra_fidelity_offer_closes_only_for_exact_verified_chain(
    tmp_path: pathlib.Path,
    relative: str,
    mutation,
) -> None:
    for retained in [
        ".vela/repository.json",
        "targets/erdos-183-astra-fidelity.json",
        "artifacts/fidelity/erdos-183-astra-fidelity.v1.json",
        "records/submissions/sha256/8d5bb0e86d8cd50f5d12bc32ed62fa7db0ba7ce951f4eee09b76f7b29884652d.json",
        "records/proposals/sha256/5abe5d1742a2fa2bd71159c0debaf9f3b0d5c786d5dc84242d3a48af7a56cfc1.json",
        "records/verifications/sha256/6da941b2e6946f59b85b31df1f2d4bdc2472d8357f654b79952c1b8c21e53428.json",
    ]:
        _copy(tmp_path, retained)
    value = _read(tmp_path / relative)
    mutation(value)
    _write(tmp_path / relative, value)

    assert not fidelity_work_complete(tmp_path)


def test_astra_fidelity_offer_remains_closed_after_acceptance(
    tmp_path: pathlib.Path,
) -> None:
    for retained in [
        ".vela/repository.json",
        "targets/erdos-183-astra-fidelity.json",
        "artifacts/fidelity/erdos-183-astra-fidelity.v1.json",
        "records/submissions/sha256/8d5bb0e86d8cd50f5d12bc32ed62fa7db0ba7ce951f4eee09b76f7b29884652d.json",
        "records/proposals/sha256/5abe5d1742a2fa2bd71159c0debaf9f3b0d5c786d5dc84242d3a48af7a56cfc1.json",
        "records/verifications/sha256/6da941b2e6946f59b85b31df1f2d4bdc2472d8357f654b79952c1b8c21e53428.json",
    ]:
        _copy(tmp_path, retained)
    assert fidelity_work_complete(tmp_path)


def test_astra_fidelity_offer_reopens_after_nonaccepted_terminal_standing(
    tmp_path: pathlib.Path,
) -> None:
    for retained in [
        ".vela/repository.json",
        "targets/erdos-183-astra-fidelity.json",
        "artifacts/fidelity/erdos-183-astra-fidelity.v1.json",
        "records/submissions/sha256/8d5bb0e86d8cd50f5d12bc32ed62fa7db0ba7ce951f4eee09b76f7b29884652d.json",
        "records/proposals/sha256/5abe5d1742a2fa2bd71159c0debaf9f3b0d5c786d5dc84242d3a48af7a56cfc1.json",
        "records/verifications/sha256/6da941b2e6946f59b85b31df1f2d4bdc2472d8357f654b79952c1b8c21e53428.json",
    ]:
        _copy(tmp_path, retained)
    repository_path = tmp_path / ".vela/repository.json"
    repository = _read(repository_path)
    repository["pending_claims"] = [
        row
        for row in repository["pending_claims"]
        if row["claim_id"]
        != "vcl_47d920289e237e9eedbba44ff247d676b8e739d7a07bf743d213d151162d7881"
    ]
    repository["accepted_claims"] = [
        row
        for row in repository["accepted_claims"]
        if row["claim_id"]
        != "vcl_47d920289e237e9eedbba44ff247d676b8e739d7a07bf743d213d151162d7881"
    ]
    _write(repository_path, repository)

    assert not fidelity_work_complete(tmp_path)


def test_generated_index_commit_does_not_rebind_source(tmp_path: pathlib.Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "config",
            "user.email",
            "target-test@vela.invalid",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Vela Target Test"],
        check=True,
    )
    for relative in [
        "scripts/build_target_index.py",
        "scripts/validate_target_closure.py",
        "targets/closures/erdos-1056-10429401-10429600.json",
        "targets/closures/erdos-1056-10429601-10429800.json",
        "targets/closures/erdos-1056-10429801-10430000.json",
        "targets/closures/erdos-1056-10430001-10430200.json",
        "targets/closures/erdos-1056-10430201-10430400.json",
        "targets/closures/erdos-1056-10430401-10430600.json",
    ]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{relative}\n")
    for relative in [
        "targets/erdos-1056.json",
        "targets/erdos-183-astra-fidelity.json",
        "targets/erdos-203-finite-cover.json",
        "targets/erdos-203-chordal-obstruction.json",
        "targets/erdos-264-parts-i-proof-repair.json",
        "targets/erdos-730-external-proof-boundary.json",
        "execution/erdos-730-proof-boundary/post-decision-handoff.v1.json",
        *execution_input_paths(ROOT),
        *erdos_203_chordal_execution_input_paths(ROOT),
        *erdos_203_execution_input_paths(ROOT),
        *erdos_264_execution_input_paths(ROOT),
        *erdos_730_execution_input_paths(ROOT),
        *fidelity_execution_input_paths(ROOT),
    ]:
        _copy(tmp_path, relative)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-qm", "source inputs"],
        check=True,
    )
    source_commit = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (tmp_path / "targets.json").write_text("{}\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "targets.json"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-qm", "generated index"],
        check=True,
    )

    assert git_source_commit(tmp_path) == source_commit
    builder = tmp_path / "scripts/build_target_index.py"
    builder.write_bytes(builder.read_bytes() + b" ")
    with pytest.raises(ValueError, match="committed exactly"):
        git_source_commit(tmp_path)

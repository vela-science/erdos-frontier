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
    execution_input_paths,
    fidelity_work_awaits_decision,
    fidelity_execution_input_paths,
    git_source_commit,
    target_from_validation,
    validate_fidelity_packet,
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
    ]
    closures = [json.loads((ROOT / path).read_text()) for path in closure_paths]
    successor_packet = (ROOT / "targets/erdos-1056.json").read_bytes()
    paths = {
        *(
            row["path"]
            for closure in closures
            for row in closure["evidence"]
        ),
    }
    for closure in closures:
        submission_row = next(
            row for row in closure["evidence"] if row["kind"] == "submission"
        )
        submission = json.loads((ROOT / submission_row["path"]).read_text())
        paths.update(row["path"] for row in submission["artifacts"])
    for relative in sorted(paths):
        _copy(tmp_path, relative)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "target-test@vela.invalid"],
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

    successor = json.loads(successor_packet)
    repository_bytes = (tmp_path / ".vela/repository.json").read_bytes()
    successor["repository"]["root"] = (
        "sha256:" + hashlib.sha256(repository_bytes).hexdigest()
    )
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
    assert result["closed_range"] == {"first": 10430201, "last": 10430400}
    assert result["closure_basis"] == "verified_submission"
    assert result["accepted_coverage"] == {"first": 10429401, "last": 10429600}
    assert result["successor_range"] == {"first": 10430401, "last": 10430600}
    assert (
        result["completion_claim_root"]
        == "sha256:a1ad4ea66bdac316bfccfbff4a7c18f7917b70b7f7cebd949601c41dcf58299b"
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
    closure_path = (
        frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    )
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
    closure_path = (
        frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    )
    closure = _read(closure_path)
    artifact_row = next(
        row for row in closure["evidence"] if row["kind"] == "artifact"
    )
    artifact_path = frontier / artifact_row["path"]
    artifact_path.write_text(
        artifact_path.read_text().replace("primes_tested=13", "primes_tested=12")
    )
    artifact_row["root"] = "sha256:" + hashlib.sha256(
        artifact_path.read_bytes()
    ).hexdigest()
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="prime count is incorrect"):
        validate(frontier)


def test_submission_without_exact_replay_is_rejected(
    frontier: pathlib.Path,
) -> None:
    closure_path = (
        frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    )
    closure = _read(closure_path)
    submission_row = next(
        row for row in closure["evidence"] if row["kind"] == "submission"
    )
    submission_path = frontier / submission_row["path"]
    submission = _read(submission_path)
    submission["replayability"] = "none"
    _write(submission_path, submission)
    submission_row["root"] = "sha256:" + hashlib.sha256(
        submission_path.read_bytes()
    ).hexdigest()
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="not exactly replayable"):
        validate(frontier)


def test_verification_must_bind_every_replay_artifact(
    frontier: pathlib.Path,
) -> None:
    closure_path = (
        frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    )
    closure = _read(closure_path)
    verification_row = next(
        row for row in closure["evidence"] if row["kind"] == "verification"
    )
    verification_path = frontier / verification_row["path"]
    verification = _read(verification_path)
    verification["subject"]["artifact_ids"].pop()
    _write(verification_path, verification)
    verification_row["root"] = "sha256:" + hashlib.sha256(
        verification_path.read_bytes()
    ).hexdigest()
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="every required artifact"):
        validate(frontier)


def test_verification_environment_must_bind_verifier_manifest(
    frontier: pathlib.Path,
) -> None:
    closure_path = (
        frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    )
    closure = _read(closure_path)
    verification_row = next(
        row for row in closure["evidence"] if row["kind"] == "verification"
    )
    verification_path = frontier / verification_row["path"]
    verification = _read(verification_path)
    verification["method"]["environment_root"] = "sha256:" + "0" * 64
    _write(verification_path, verification)
    verification_row["root"] = "sha256:" + hashlib.sha256(
        verification_path.read_bytes()
    ).hexdigest()
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="environment"):
        validate(frontier)


def test_proposal_cannot_bind_another_submission(
    frontier: pathlib.Path,
) -> None:
    closure_path = (
        frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    )
    closure = _read(closure_path)
    proposal_row = next(
        row for row in closure["evidence"] if row["kind"] == "proposal"
    )
    proposal_path = frontier / proposal_row["path"]
    proposal = _read(proposal_path)
    proposal["producer_package"]["root"] = "sha256:" + "0" * 64
    _write(proposal_path, proposal)
    proposal_row["root"] = "sha256:" + hashlib.sha256(
        proposal_path.read_bytes()
    ).hexdigest()
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="does not bind the Submission"):
        validate(frontier)


def test_pending_submission_cannot_replace_accepted_coverage(
    frontier: pathlib.Path,
) -> None:
    packet_path = frontier / "targets/erdos-1056.json"
    packet = _read(packet_path)
    latest = packet["accepted_state"]["latest_bounded_negative"]
    progress = packet["producer_completion"]["latest_verified_submission"]
    latest["claim_id"] = progress["claim_id"]
    latest["claim_root"] = progress["claim_root"]
    latest["range"] = progress["range"]
    latest["artifact_root"] = progress["artifact_root"]
    _write(packet_path, packet)

    with pytest.raises(TargetClosureError, match="not accepted"):
        validate(frontier)


def test_rejected_submission_still_closes_producer_work(
    frontier: pathlib.Path,
) -> None:
    repository_path = frontier / ".vela/repository.json"
    repository = _read(repository_path)
    claim_id = (
        _read(frontier / "targets/erdos-1056.json")["producer_completion"][
            "latest_verified_submission"
        ]["claim_id"]
    )
    repository["pending_claims"] = [
        row for row in repository["pending_claims"] if row["claim_id"] != claim_id
    ]
    _write(repository_path, repository)

    packet_path = frontier / "targets/erdos-1056.json"
    packet = _read(packet_path)
    packet["repository"]["root"] = "sha256:" + hashlib.sha256(
        repository_path.read_bytes()
    ).hexdigest()
    _write(packet_path, packet)

    result = validate(frontier)
    assert result["accepted_coverage"]["last"] == 10429600
    assert result["successor_range"]["first"] == 10430401


def test_later_acceptance_reconciles_without_rewriting_closure(
    frontier: pathlib.Path,
) -> None:
    packet_path = frontier / "targets/erdos-1056.json"
    packet = _read(packet_path)
    progress = packet.pop("producer_completion")["latest_verified_submission"]
    previous = packet["accepted_state"]["latest_bounded_negative"]
    packet["accepted_state"]["previous_bounded_negative"] = previous
    packet["accepted_state"]["latest_bounded_negative"] = {
        "claim_id": progress["claim_id"],
        "claim_root": progress["claim_root"],
        "range": progress["range"],
        "artifact_root": progress["artifact_root"],
        "result": progress["result"],
    }

    repository_path = frontier / ".vela/repository.json"
    repository = _read(repository_path)
    accepted_row = next(
        row
        for row in repository["pending_claims"]
        if row["claim_id"] == progress["claim_id"]
    )
    repository["pending_claims"] = [
        row
        for row in repository["pending_claims"]
        if row["claim_id"] != progress["claim_id"]
    ]
    repository["accepted_claims"].append(
        {**accepted_row, "standing": "accepted"}
    )
    _write(repository_path, repository)
    packet["repository"]["root"] = "sha256:" + hashlib.sha256(
        repository_path.read_bytes()
    ).hexdigest()
    _write(packet_path, packet)

    result = validate(frontier)
    assert result["accepted_coverage"]["last"] == 10430400
    assert result["successor_range"]["first"] == 10430401
    assert "pending review" not in target_from_validation(result)["why"]


def test_target_copy_uses_derived_successor_range() -> None:
    target = target_from_validation(
        {
            "accepted_coverage": {"first": 1, "last": 10429600},
            "closed_range": {"first": 10430201, "last": 10430400},
            "closure_basis": "verified_submission",
            "successor_range": {"first": 10430401, "last": 10430600},
        }
    )
    assert "10430401..10430600" in target["objective"]
    assert "through 10430400" in target["why"]


def test_execution_inputs_bind_only_the_exact_agent_bundle_files() -> None:
    assert execution_input_paths(ROOT) == [
        "execution/erdos-1056/10430401-10430600/bundle.json",
        "execution/erdos-1056/mission-10430401-10430600.draft.json",
        "execution/erdos-1056/verifier/v1/linux-arm64/verifier",
        "execution/erdos-1056/verifier/v1/verifier.cpp",
    ]


def test_astra_fidelity_packet_preserves_exact_source_and_authority_boundary() -> None:
    validate_fidelity_packet(ROOT)
    packet = _read(ROOT / "targets/erdos-183-astra-fidelity.json")
    assert packet["authority"] == "non_authoritative"
    assert packet["review_contract"]["accepted_state_change"] == (
        "none until a separate authorized human Decision"
    )
    assert packet["source_problem"]["status_observation"]["source_last_update"] < "2026-08-01"
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


def test_astra_fidelity_work_awaits_only_human_decision() -> None:
    assert fidelity_work_awaits_decision(ROOT)


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

    assert not fidelity_work_awaits_decision(tmp_path)


def test_astra_fidelity_offer_requires_zero_accepted_state_delta(
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
    claim = next(
        row
        for row in repository["pending_claims"]
        if row["claim_id"]
        == "vcl_47d920289e237e9eedbba44ff247d676b8e739d7a07bf743d213d151162d7881"
    )
    repository["pending_claims"].remove(claim)
    repository["accepted_claims"].append({**claim, "standing": "accepted"})
    _write(repository_path, repository)

    assert not fidelity_work_awaits_decision(tmp_path)


def test_generated_index_commit_does_not_rebind_source(tmp_path: pathlib.Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "target-test@vela.invalid"],
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
    ]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{relative}\n")
    for relative in [
        "targets/erdos-1056.json",
        "targets/erdos-183-astra-fidelity.json",
        *execution_input_paths(ROOT),
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

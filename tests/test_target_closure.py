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
from build_target_index import git_source_commit, target_from_validation  # noqa: E402


def _copy(root: pathlib.Path, relative: str) -> None:
    source = ROOT / relative
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


@pytest.fixture
def frontier(tmp_path: pathlib.Path) -> pathlib.Path:
    closure = json.loads(
        (
            ROOT
            / "targets/closures/erdos-1056-10429601-10429800.json"
        ).read_text()
    )
    successor_packet = (ROOT / "targets/erdos-1056.json").read_bytes()
    submission_row = next(
        row for row in closure["evidence"] if row["kind"] == "submission"
    )
    submission = json.loads((ROOT / submission_row["path"]).read_text())
    paths = {
        ".vela/repository.json",
        "targets/erdos-1056.json",
        "targets/closures/erdos-1056-10429601-10429800.json",
        *(row["path"] for row in closure["evidence"]),
        *(row["path"] for row in submission["artifacts"]),
    }
    for relative in sorted(paths):
        _copy(tmp_path, relative)
    retained_packet = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "show",
            (
                f"{closure['completed_packet']['git_commit']}:"
                f"{closure['completed_packet']['path']}"
            ),
        ],
        check=True,
        capture_output=True,
    ).stdout
    (tmp_path / "targets/erdos-1056.json").write_bytes(retained_packet)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "target-test@vela.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Vela Target Test"],
        check=True,
    )
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-qm", "retain completed packet"],
        check=True,
    )
    retained_commit = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (tmp_path / "targets/erdos-1056.json").write_bytes(successor_packet)
    closure["completed_packet"]["git_commit"] = retained_commit
    closure["repository_commit"] = retained_commit
    _write(
        tmp_path / "targets/closures/erdos-1056-10429601-10429800.json",
        closure,
    )
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-qm", "expose successor packet"],
        check=True,
    )
    return tmp_path


def _read(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


def _write(path: pathlib.Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def test_exact_closure_derives_first_uncovered_interval(
    frontier: pathlib.Path,
) -> None:
    result = validate(frontier)
    assert result["closed_range"] == {"first": 10429601, "last": 10429800}
    assert result["closure_basis"] == "registered_submission"
    assert result["accepted_coverage"] == {"first": 10429401, "last": 10429600}
    assert result["successor_range"] == {"first": 10429801, "last": 10430000}
    assert (
        result["completion_claim_root"]
        == "sha256:226cdf85adf6edcaf67a3680ffd52a3c3e3cab5ad9dea9e12b8577d69e02f5fc"
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


def test_registered_submission_needs_no_decision_or_accepted_claim(
    frontier: pathlib.Path,
) -> None:
    result = validate(frontier)
    assert result["closure_basis"] == "registered_submission"
    assert result["verification_root"].startswith("sha256:")


def test_registered_submission_requires_verification(
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


def test_registration_cannot_change_accepted_state(
    frontier: pathlib.Path,
) -> None:
    closure_path = (
        frontier / "targets/closures/erdos-1056-10429601-10429800.json"
    )
    closure = _read(closure_path)
    registration_row = next(
        row for row in closure["evidence"] if row["kind"] == "registration"
    )
    registration_path = frontier / registration_row["path"]
    registration = _read(registration_path)
    registration["accepted_state_changed"] = True
    _write(registration_path, registration)
    registration_row["root"] = "sha256:" + hashlib.sha256(
        registration_path.read_bytes()
    ).hexdigest()
    _write(closure_path, closure)

    with pytest.raises(TargetClosureError, match="changed accepted state"):
        validate(frontier)


def test_pending_submission_cannot_replace_accepted_coverage(
    frontier: pathlib.Path,
) -> None:
    packet_path = frontier / "targets/erdos-1056.json"
    packet = _read(packet_path)
    latest = packet["accepted_state"]["latest_bounded_negative"]
    progress = packet["producer_completion"]["latest_registered_submission"]
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
            "latest_registered_submission"
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
    assert result["successor_range"]["first"] == 10429801


def test_later_acceptance_reconciles_without_rewriting_closure(
    frontier: pathlib.Path,
) -> None:
    packet_path = frontier / "targets/erdos-1056.json"
    packet = _read(packet_path)
    progress = packet.pop("producer_completion")["latest_registered_submission"]
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
    assert result["accepted_coverage"]["last"] == 10429800
    assert result["successor_range"]["first"] == 10429801
    assert "pending review" not in target_from_validation(result)["why"]


def test_target_copy_uses_derived_successor_range() -> None:
    target = target_from_validation(
        {
            "accepted_coverage": {"first": 1, "last": 10429600},
            "closed_range": {"first": 10429601, "last": 10429800},
            "closure_basis": "registered_submission",
            "successor_range": {"first": 10429801, "last": 10430000},
        }
    )
    assert "10429801..10430000" in target["objective"]
    assert "through 10429800" in target["why"]


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
        "targets/erdos-1056.json",
    ]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{relative}\n")
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

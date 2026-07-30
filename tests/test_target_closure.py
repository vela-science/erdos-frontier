from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate_target_closure import TargetClosureError, validate  # noqa: E402


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
            / "targets/closures/erdos-1056-10429401-10429600.json"
        ).read_text()
    )
    successor_packet = (ROOT / "targets/erdos-1056.json").read_bytes()
    paths = {
        ".vela/repository.json",
        "targets/erdos-1056.json",
        "targets/closures/erdos-1056-10429401-10429600.json",
        *(row["path"] for row in closure["evidence"]),
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
    _write(
        tmp_path / "targets/closures/erdos-1056-10429401-10429600.json",
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
    assert result["closed_range"] == {"first": 10429401, "last": 10429600}
    assert result["successor_range"] == {"first": 10429601, "last": 10429800}
    assert (
        result["accepted_claim_root"]
        == "sha256:e5dda77fea872d0de9da96934d8c483d851fcfb8615e10fec9386e88d486452c"
    )


def test_completed_successor_is_rejected(frontier: pathlib.Path) -> None:
    path = frontier / "targets/erdos-1056.json"
    packet = _read(path)
    packet["target"]["next_bounded_range"] = {
        "first": 10429401,
        "last": 10429600,
        "inclusive": True,
    }
    _write(path, packet)
    with pytest.raises(TargetClosureError, match="successor range differs|overlaps"):
        validate(frontier)


def test_overlapping_closure_is_rejected(frontier: pathlib.Path) -> None:
    original = frontier / "targets/closures/erdos-1056-10429401-10429600.json"
    duplicate = frontier / "targets/closures/overlap.json"
    duplicate.write_bytes(original.read_bytes())
    subprocess.run(["git", "-C", str(frontier), "add", str(duplicate)], check=True)
    with pytest.raises(TargetClosureError, match="ranges overlap"):
        validate(frontier)


def test_malformed_range_is_rejected(frontier: pathlib.Path) -> None:
    path = frontier / "targets/closures/erdos-1056-10429401-10429600.json"
    closure = _read(path)
    closure["completed_scope"]["first"] = "10429401"
    _write(path, closure)
    with pytest.raises(TargetClosureError, match="malformed"):
        validate(frontier)


def test_untracked_input_is_rejected(frontier: pathlib.Path) -> None:
    relative = "targets/closures/erdos-1056-10429401-10429600.json"
    subprocess.run(
        ["git", "-C", str(frontier), "rm", "--cached", "-q", "--", relative],
        check=True,
    )
    with pytest.raises(TargetClosureError, match="untracked"):
        validate(frontier)


def test_evidence_root_drift_is_rejected(frontier: pathlib.Path) -> None:
    claim = (
        frontier
        / "records/claims/sha256/e5dda77fea872d0de9da96934d8c483d851fcfb8615e10fec9386e88d486452c.json"
    )
    claim.write_bytes(claim.read_bytes() + b" ")
    with pytest.raises(TargetClosureError, match="root drift"):
        validate(frontier)


def test_completed_packet_git_bytes_are_bound(frontier: pathlib.Path) -> None:
    path = frontier / "targets/closures/erdos-1056-10429401-10429600.json"
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

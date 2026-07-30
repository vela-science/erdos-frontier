#!/usr/bin/env python3
"""Validate domain-owned Erdős Target closure and successor coverage.

This is a read-only, non-authoritative validator. It binds a closed numerical
range to retained accepted evidence, then proves that the exposed successor is
tracked, fresh, contiguous, and non-overlapping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLOSURE_PATH = ROOT / "targets" / "closures" / "erdos-1056-10429401-10429600.json"
PACKET_PATH = ROOT / "targets" / "erdos-1056.json"
REPOSITORY_PATH = ROOT / ".vela" / "repository.json"
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class TargetClosureError(ValueError):
    """The derived Target closure cannot be trusted."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def canonical_root(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_root(path: pathlib.Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(root: pathlib.Path, raw: str) -> pathlib.Path:
    path = pathlib.PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise TargetClosureError(f"unsafe Target closure path: {raw}")
    resolved = root.joinpath(*path.parts).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise TargetClosureError(f"Target closure path escapes the Frontier: {raw}")
    return resolved


def require_tracked(root: pathlib.Path, path: pathlib.Path) -> None:
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise TargetClosureError(f"path escapes the Frontier: {path}") from error
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", relative],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise TargetClosureError(f"Target closure input is untracked: {relative}")


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise TargetClosureError(f"cannot read canonical JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise TargetClosureError(f"expected a JSON object at {path}")
    return value


def retained_git_json(
    root: pathlib.Path, commit: str, path_raw: str, expected_root: str
) -> dict[str, Any]:
    if not GIT_COMMIT_RE.fullmatch(commit):
        raise TargetClosureError("completed packet Git commit is malformed")
    if path_raw != PACKET_PATH.relative_to(ROOT).as_posix():
        raise TargetClosureError("completed packet Git path differs")
    if not SHA256_RE.fullmatch(expected_root):
        raise TargetClosureError("completed packet SHA-256 root is malformed")

    commit_check = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "-C",
            str(root),
            "cat-file",
            "-e",
            f"{commit}^{{commit}}",
        ],
        capture_output=True,
    )
    if commit_check.returncode != 0:
        raise TargetClosureError("completed packet Git commit is unavailable")
    ancestor_check = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "-C",
            str(root),
            "merge-base",
            "--is-ancestor",
            commit,
            "HEAD",
        ],
        capture_output=True,
    )
    if ancestor_check.returncode != 0:
        raise TargetClosureError(
            "completed packet Git commit is not retained in current history"
        )

    packet_result = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "-C",
            str(root),
            "show",
            f"{commit}:{path_raw}",
        ],
        capture_output=True,
    )
    if packet_result.returncode != 0:
        raise TargetClosureError("completed packet is absent at its Git commit")
    observed_root = "sha256:" + hashlib.sha256(packet_result.stdout).hexdigest()
    if observed_root != expected_root:
        raise TargetClosureError(
            "completed packet Git bytes drifted: "
            f"expected {expected_root}, observed {observed_root}"
        )
    try:
        value = json.loads(packet_result.stdout)
    except json.JSONDecodeError as error:
        raise TargetClosureError(
            "completed packet Git bytes are not canonical JSON"
        ) from error
    if not isinstance(value, dict):
        raise TargetClosureError("completed packet Git bytes are not a JSON object")
    return value


def bound_json(
    root: pathlib.Path, path_raw: str, expected_root: str
) -> dict[str, Any]:
    if not SHA256_RE.fullmatch(expected_root):
        raise TargetClosureError(f"malformed SHA-256 root for {path_raw}")
    path = relative_path(root, path_raw)
    require_tracked(root, path)
    if not path.is_file():
        raise TargetClosureError(f"missing Target closure input: {path_raw}")
    observed = file_root(path)
    if observed != expected_root:
        raise TargetClosureError(
            f"Target closure root drift for {path_raw}: "
            f"expected {expected_root}, observed {observed}"
        )
    return read_json(path)


def validate_range(value: Any, label: str) -> tuple[int, int]:
    if not isinstance(value, dict):
        raise TargetClosureError(f"{label} is not an object")
    first = value.get("first")
    last = value.get("last")
    if not isinstance(first, int) or not isinstance(last, int) or first > last:
        raise TargetClosureError(f"{label} is malformed")
    return first, last


def evidence_by_kind(closure: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = closure.get("evidence")
    if not isinstance(rows, list):
        raise TargetClosureError("Target closure evidence is not a list")
    by_kind: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("kind"), str):
            raise TargetClosureError("Target closure contains malformed evidence")
        kind = row["kind"]
        if kind in by_kind:
            raise TargetClosureError(f"duplicate Target closure evidence kind: {kind}")
        by_kind[kind] = row
    required = {
        "accepted_claim",
        "submission",
        "verification",
        "artifact",
        "decision_event",
    }
    if set(by_kind) != required:
        raise TargetClosureError(
            "Target closure evidence kinds differ: "
            f"expected {sorted(required)}, observed {sorted(by_kind)}"
        )
    return by_kind


def load_evidence(
    root: pathlib.Path, row: dict[str, Any], expected_id_field: str
) -> dict[str, Any]:
    value = bound_json(root, row.get("path", ""), row.get("root", ""))
    if value.get(expected_id_field) != row.get("id"):
        raise TargetClosureError(
            f"{row.get('kind')} evidence ID does not match {expected_id_field}"
        )
    return value


def validate_all_closed_ranges(root: pathlib.Path) -> None:
    ranges: list[tuple[int, int, str]] = []
    directory = root / "targets" / "closures"
    for path in sorted(directory.glob("*.json")):
        require_tracked(root, path)
        closure = read_json(path)
        if closure.get("schema") != "vela.target-closure.v1":
            raise TargetClosureError(f"unsupported Target closure schema at {path}")
        if closure.get("target_id") != "erdos:1056":
            continue
        if closure.get("status") != "closed":
            raise TargetClosureError(f"non-closed envelope exposed at {path}")
        first, last = validate_range(
            closure.get("completed_scope"), f"{path.name} completed scope"
        )
        ranges.append((first, last, path.name))
    ranges.sort()
    for previous, current in zip(ranges, ranges[1:], strict=False):
        if current[0] <= previous[1]:
            raise TargetClosureError(
                "completed Erdős ranges overlap: "
                f"{previous[2]} and {current[2]}"
            )


def validate(
    root: pathlib.Path = ROOT,
    closure_path: pathlib.Path | None = None,
    packet_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    closure_path = (closure_path or root / CLOSURE_PATH.relative_to(ROOT)).resolve()
    packet_path = (packet_path or root / PACKET_PATH.relative_to(ROOT)).resolve()
    repository_path = root / REPOSITORY_PATH.relative_to(ROOT)
    for path in (closure_path, packet_path, repository_path):
        require_tracked(root, path)

    closure = read_json(closure_path)
    packet = read_json(packet_path)
    repository = read_json(repository_path)

    if closure.get("schema") != "vela.target-closure.v1":
        raise TargetClosureError("unsupported Target closure schema")
    if closure.get("frontier_id") != repository.get("frontier_id"):
        raise TargetClosureError("Target closure names another Frontier")
    if closure.get("target_id") != "erdos:1056":
        raise TargetClosureError("Target closure names another Target")
    if closure.get("status") != "closed":
        raise TargetClosureError("completed Target is not marked closed")
    observed_repository_root = file_root(repository_path)
    if closure.get("repository_root") != observed_repository_root:
        raise TargetClosureError("Target closure repository root drifted")

    contract = closure.get("completion_contract")
    if canonical_root(contract) != closure.get("completion_contract_root"):
        raise TargetClosureError("Target completion-contract root drifted")

    closed_first, closed_last = validate_range(
        closure.get("completed_scope"), "completed scope"
    )
    completed_packet = closure.get("completed_packet") or {}
    retained_packet = retained_git_json(
        root,
        completed_packet.get("git_commit", ""),
        completed_packet.get("path", ""),
        completed_packet.get("sha256", ""),
    )
    if retained_packet.get("schema") != completed_packet.get("schema"):
        raise TargetClosureError("completed packet schema drifted")
    if retained_packet.get("target", {}).get("id") != closure.get("target_id"):
        raise TargetClosureError("completed packet names another Target")
    completed_first, completed_last = validate_range(
        retained_packet.get("target", {}).get("next_bounded_range"),
        "completed packet range",
    )
    if (completed_first, completed_last) != (closed_first, closed_last):
        raise TargetClosureError("completed packet range differs from closure scope")
    if canonical_root(retained_packet.get("completion_contract")) != closure.get(
        "completion_contract_root"
    ):
        raise TargetClosureError("completed packet completion contract drifted")

    evidence = evidence_by_kind(closure)
    claim = load_evidence(root, evidence["accepted_claim"], "claim_id")
    submission = load_evidence(root, evidence["submission"], "submission_id")
    verification = load_evidence(
        root, evidence["verification"], "verification_record_id"
    )
    artifact_row = evidence["artifact"]
    artifact_path = relative_path(root, artifact_row.get("path", ""))
    require_tracked(root, artifact_path)
    if file_root(artifact_path) != artifact_row.get("root"):
        raise TargetClosureError("Target closure artifact root drifted")
    decision = load_evidence(root, evidence["decision_event"], "id")

    accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
        if isinstance(row, dict)
    }
    claim_id = evidence["accepted_claim"]["id"]
    claim_root = evidence["accepted_claim"]["root"]
    if accepted.get(claim_id) != claim_root:
        raise TargetClosureError("bounded-range Claim is not accepted at this root")

    assertion = ((claim.get("assertion") or {}).get("text")) or ""
    expected_range = f"{closed_first}..{closed_last}"
    if (
        expected_range not in assertion
        or "exhaustive bounded search" not in assertion.lower()
    ):
        raise TargetClosureError("accepted Claim does not state the exact bounded range")
    if submission.get("claim", {}).get("assertion") != assertion:
        raise TargetClosureError("Submission and accepted Claim assertions differ")
    if artifact_row["root"] not in {
        row.get("digest") for row in submission.get("artifacts", [])
    }:
        raise TargetClosureError("Submission does not bind the closure artifact")

    subject = verification.get("subject") or {}
    if verification.get("outcome") != "pass":
        raise TargetClosureError("Target closure Verification did not pass")
    if subject.get("claim_id") != claim_id:
        raise TargetClosureError("Verification does not bind the accepted Claim")
    if subject.get("submission_id") != evidence["submission"]["id"]:
        raise TargetClosureError("Verification does not bind the Submission")

    content = decision.get("content") or {}
    payload = content.get("payload") or {}
    if content.get("kind") != "review.accepted":
        raise TargetClosureError("Target closure Decision is not an acceptance")
    if payload.get("proposal_id") != subject.get("proposal_id"):
        raise TargetClosureError("Decision and Verification bind different Proposals")

    if packet.get("schema") != "erdos-frontier.problem-work.v2":
        raise TargetClosureError("successor packet has the wrong schema")
    if packet.get("frontier_id") != repository.get("frontier_id"):
        raise TargetClosureError("successor packet names another Frontier")
    if packet.get("target", {}).get("id") != closure.get("target_id"):
        raise TargetClosureError("successor packet names another Target")
    if packet.get("repository", {}).get("root") != observed_repository_root:
        raise TargetClosureError("successor packet repository root drifted")
    successor_first, successor_last = validate_range(
        packet.get("target", {}).get("next_bounded_range"), "successor range"
    )
    expected_successor = closure.get("successor_packet") or {}
    expected_first, expected_last = validate_range(
        expected_successor.get("expected_scope"), "expected successor scope"
    )
    if (successor_first, successor_last) != (expected_first, expected_last):
        raise TargetClosureError("successor range differs from the closure envelope")
    if successor_first != closed_last + 1:
        raise TargetClosureError(
            "successor repeats, overlaps, or skips completed exact coverage"
        )
    if expected_successor.get("path") != packet_path.relative_to(root).as_posix():
        raise TargetClosureError("successor packet path differs")
    if expected_successor.get("schema") != packet.get("schema"):
        raise TargetClosureError("successor packet schema differs")
    if expected_successor.get("sha256") != file_root(packet_path):
        raise TargetClosureError("successor packet root drifted")
    if expected_successor.get("size") != packet_path.stat().st_size:
        raise TargetClosureError("successor packet size drifted")

    latest = packet.get("accepted_state", {}).get("latest_bounded_negative") or {}
    latest_first, latest_last = validate_range(
        latest.get("range"), "latest accepted bounded range"
    )
    if (latest_first, latest_last) != (closed_first, closed_last):
        raise TargetClosureError("successor packet omits the completed range")
    if latest.get("claim_id") != claim_id or latest.get("claim_root") != claim_root:
        raise TargetClosureError("successor packet binds the wrong accepted Claim")
    if latest.get("artifact_root") != artifact_row["root"]:
        raise TargetClosureError("successor packet binds the wrong accepted artifact")

    previous = packet.get("accepted_state", {}).get("previous_bounded_negative") or {}
    _, previous_last = validate_range(previous.get("range"), "previous bounded range")
    if previous_last + 1 != closed_first:
        raise TargetClosureError("accepted bounded coverage is not contiguous")

    validate_all_closed_ranges(root)
    return {
        "schema": "erdos-frontier.target-closure-check.v1",
        "ok": True,
        "closed_target": closure["target_id"],
        "closed_range": {"first": closed_first, "last": closed_last},
        "accepted_claim_root": claim_root,
        "verification_root": evidence["verification"]["root"],
        "decision_event_root": evidence["decision_event"]["root"],
        "successor_range": {"first": successor_first, "last": successor_last},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = validate()
    except TargetClosureError as error:
        if args.json:
            print(
                json.dumps(
                    {
                        "schema": "erdos-frontier.target-closure-check.v1",
                        "ok": False,
                        "error": str(error),
                    },
                    sort_keys=True,
                )
            )
        else:
            print(f"Target closure invalid: {error}")
        return 1
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            "Target closure valid: "
            f"{result['closed_range']['first']}..{result['closed_range']['last']} "
            f"-> {result['successor_range']['first']}.."
            f"{result['successor_range']['last']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

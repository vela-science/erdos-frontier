#!/usr/bin/env python3
"""Build the current domain-owned Erdős Target Index candidate.

Vela owns sealing and validation of the derived index. This script owns only
the domain target and emits the closed candidate consumed by
`vela target-index seal`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

from validate_target_closure import validate as validate_target_closure

ROOT = pathlib.Path(__file__).resolve().parent.parent
CANDIDATE_PATH = ROOT / ".vela" / "tmp" / "target-index-candidate.json"
REPOSITORY_PATH = ROOT / ".vela" / "repository.json"
PACKET_PATH = ROOT / "targets" / "erdos-1056.json"
BUNDLE_SCHEMA = "vela.agent-execution-bundle.v1"
TARGET_ID = "erdos:1056"
ARTIFACT_PATH = "artifacts/erdos1056-k15-range-10430401-10430600.txt"
ALLOWED_OUTPUTS = [
    {"type": "text/plain", "path": ARTIFACT_PATH},
    {"type": "engine-manifest"},
    {"type": "verifier-manifest"},
]
TARGET_BASE = {
    "id": TARGET_ID,
    "title": "Erdős 1056",
    "state": "open",
    "rank": 1,
    "labels": [
        "bounded-artifact",
        "erdos",
        "machine-checkable",
        "residual-obligations",
        "upstream-open",
    ],
    "packet": {
        "path": "targets/erdos-1056.json",
        "schema": "erdos-frontier.problem-work.v2",
    },
}


def sha256_root(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def rooted_file(
    root: pathlib.Path,
    locator: Any,
    label: str,
    *,
    schema: bool = False,
) -> str:
    required = {"path", "size", "sha256"}
    if schema:
        required.add("schema")
    if not isinstance(locator, dict) or set(locator) != required:
        raise ValueError(f"{label} must be one closed rooted-file locator")
    if schema and locator["schema"] != BUNDLE_SCHEMA:
        raise ValueError(f"{label} schema differs")
    raw = locator.get("path")
    size = locator.get("size")
    expected = locator.get("sha256")
    if (
        not isinstance(raw, str)
        or not isinstance(size, int)
        or size <= 0
        or not isinstance(expected, str)
    ):
        raise ValueError(f"{label} locator is malformed")
    path = pathlib.PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} path escapes the Frontier")
    resolved = root.joinpath(*path.parts)
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"{label} must name one regular file")
    data = resolved.read_bytes()
    if len(data) != size or sha256_root(data) != expected:
        raise ValueError(f"{label} bytes differ from the locator")
    return raw


def execution_input_paths(root: pathlib.Path = ROOT) -> list[str]:
    packet_path = root / PACKET_PATH.relative_to(ROOT)
    packet = json.loads(packet_path.read_text())
    if packet.get("allowed_outputs") != ALLOWED_OUTPUTS:
        raise ValueError("Erdős 1056 allowed outputs differ from the Agent contract")
    bundle_path = rooted_file(
        root,
        packet.get("execution_bundle"),
        "execution bundle",
        schema=True,
    )
    bundle_file = root / bundle_path
    bundle = json.loads(bundle_file.read_text())
    if bundle_file.read_bytes() != canonical_bytes(bundle):
        raise ValueError("execution bundle must be canonical JSON")
    if (
        bundle.get("schema") != BUNDLE_SCHEMA
        or bundle.get("authority") != "non_authoritative"
        or bundle.get("effect") != "none"
        or bundle.get("target") != {"id": TARGET_ID}
        or "target_packet" in bundle
    ):
        raise ValueError("execution bundle crosses its exact Target or authority boundary")
    artifact = bundle.get("artifact_contract")
    if (
        not isinstance(artifact, dict)
        or artifact.get("kind") != ALLOWED_OUTPUTS[0]["type"]
        or artifact.get("path") != ALLOWED_OUTPUTS[0]["path"]
    ):
        raise ValueError("execution bundle Artifact contract differs from allowed outputs")
    if bundle.get("safeguards") != {
        "duplicate_work": "target_revalidation",
        "prior_answer_inputs": [],
        "worker_inputs": ["mission", "target_packet"],
    }:
        raise ValueError("execution bundle input boundary differs")
    verifier = bundle.get("verifier")
    if (
        not isinstance(verifier, dict)
        or verifier.get("isolation") != {"network": "deny", "writes": "deny"}
        or (verifier.get("runtime") or {}).get("verifier_platform") != "linux/arm64"
    ):
        raise ValueError("execution bundle verifier boundary differs")
    mission_path = rooted_file(root, bundle.get("mission"), "mission")
    mission_file = root / mission_path
    mission = json.loads(mission_file.read_text())
    if mission_file.read_bytes() != canonical_bytes(mission):
        raise ValueError("Agent mission must be canonical JSON")
    if (
        mission.get("target") != TARGET_ID
        or mission.get("actor") != "agent:codex"
        or mission.get("frontier") != "."
        or mission.get("role") != "producer"
        or mission.get("allowed_paths") != [ARTIFACT_PATH]
    ):
        raise ValueError("Agent mission differs from the exact Target and output contract")
    nested = [
        mission_path,
        rooted_file(root, verifier.get("source"), "verifier source"),
        rooted_file(root, verifier.get("capsule"), "verifier capsule"),
    ]
    return sorted([bundle_path, *nested])


def input_paths(root: pathlib.Path = ROOT) -> list[str]:
    return sorted(
        [
            "scripts/build_target_index.py",
            "scripts/validate_target_closure.py",
            *(
                path.relative_to(root).as_posix()
                for path in (root / "targets" / "closures").glob("*.json")
            ),
            *execution_input_paths(root),
        ]
    )


def git_source_commit(
    root: pathlib.Path = ROOT,
    paths: list[str] | None = None,
) -> str:
    paths = paths or input_paths(root)
    packet = PACKET_PATH.relative_to(ROOT).as_posix()
    retained = [*paths, packet]
    commit = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "log",
            "-1",
            "--format=%H",
            "--",
            *retained,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not commit:
        raise ValueError("Target Index inputs have no retained Git source commit")
    for relative in retained:
        tracked = subprocess.run(
            ["git", "-C", str(root), "show", f"{commit}:{relative}"],
            capture_output=True,
        )
        path = root / relative
        if (
            tracked.returncode != 0
            or not path.is_file()
            or tracked.stdout != path.read_bytes()
        ):
            raise ValueError(
                f"Target Index source input must be committed exactly: {relative}"
            )
    return commit


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def target_from_validation(validation: dict[str, Any]) -> dict[str, Any]:
    successor = validation["successor_range"]
    accepted = validation["accepted_coverage"]
    completed = validation["closed_range"]
    pending = ""
    if (
        validation["closure_basis"] == "verified_submission"
        and completed["last"] > accepted["last"]
    ):
        pending = (
            f", and producer-complete work pending review through "
            f"{completed['last']}"
        )
    return {
        **TARGET_BASE,
        "why": (
            "The exact current packet binds the open problem, banked k=2..14 "
            f"evidence, accepted bounded k=15 coverage through {accepted['last']}"
            f"{pending}; the next non-overlapping range is ready."
        ),
        "objective": (
            "Search the exact next k=15 range "
            f"{successor['first']}..{successor['last']} without repeating "
            "banked coverage; produce one bounded, verifier-replayable artifact "
            "whose Claim states its actual scope and does not imply acceptance."
        ),
    }


def validate_packet(validation: dict[str, Any]) -> None:
    repository = json.loads(REPOSITORY_PATH.read_text())
    packet = json.loads(PACKET_PATH.read_text())
    repository_root = "sha256:" + hashlib.sha256(REPOSITORY_PATH.read_bytes()).hexdigest()
    if packet.get("schema") != TARGET_BASE["packet"]["schema"]:
        raise ValueError("Erdős 1056 packet schema differs from the Target")
    if packet.get("frontier_id") != repository.get("frontier_id"):
        raise ValueError("Erdős 1056 packet targets another Frontier")
    if (packet.get("target") or {}).get("id") != TARGET_BASE["id"]:
        raise ValueError("Erdős 1056 packet targets another work item")
    if (packet.get("repository") or {}).get("root") != repository_root:
        raise ValueError("Erdős 1056 packet is stale for the current repository root")

    accepted = {
        row["claim_id"]: row["claim_root"]
        for row in repository.get("accepted_claims", [])
    }
    roles = (packet.get("accepted_state") or {}).values()
    for role in roles:
        claim_id = role.get("claim_id")
        claim_root = role.get("claim_root")
        if accepted.get(claim_id) != claim_root:
            raise ValueError(
                f"Erdős 1056 packet does not bind current accepted Claim {claim_id}"
            )

    next_range = packet["target"]["next_bounded_range"]
    if next_range != {
        **validation["successor_range"],
        "inclusive": True,
    }:
        raise ValueError("Erdős 1056 packet differs from the derived successor range")


def candidate() -> dict[str, Any]:
    validation = validate_target_closure(ROOT)
    validate_packet(validation)
    paths = input_paths(ROOT)
    return {
        "schema": "vela.target-index-candidate.v1",
        "frontier_id": "vfr_0a25edabc16db143",
        "source": {
            "git_commit": git_source_commit(ROOT, paths),
            "input_paths": paths,
        },
        "targets": [target_from_validation(validation)],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=CANDIDATE_PATH,
    )
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        value = candidate()
    except ValueError as error:
        print(f"Target Index candidate unavailable: {error}", file=sys.stderr)
        return 1
    output.write_bytes(canonical_bytes(value))
    try:
        display = output.relative_to(ROOT)
    except ValueError:
        display = output
    print(f"Wrote {display}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

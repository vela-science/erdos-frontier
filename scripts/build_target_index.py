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
from typing import Any

from validate_target_closure import validate as validate_target_closure

ROOT = pathlib.Path(__file__).resolve().parent.parent
CANDIDATE_PATH = ROOT / ".vela" / "tmp" / "target-index-candidate.json"
REPOSITORY_PATH = ROOT / ".vela" / "repository.json"
PACKET_PATH = ROOT / "targets" / "erdos-1056.json"
INPUT_PATHS = [
    "scripts/build_target_index.py",
    "scripts/validate_target_closure.py",
    *sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "targets" / "closures").glob("*.json")
    ),
]
TARGET_BASE = {
    "id": "erdos:1056",
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


def git_source_commit(root: pathlib.Path = ROOT) -> str:
    return subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "log",
            "-1",
            "--format=%H",
            "--",
            *INPUT_PATHS,
            PACKET_PATH.relative_to(ROOT).as_posix(),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


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
        validation["closure_basis"] == "registered_submission"
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
    return {
        "schema": "vela.target-index-candidate.v1",
        "frontier_id": "vfr_0a25edabc16db143",
        "source": {
            "git_commit": git_source_commit(),
            "input_paths": INPUT_PATHS,
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
    output.write_bytes(canonical_bytes(candidate()))
    try:
        display = output.relative_to(ROOT)
    except ValueError:
        display = output
    print(f"Wrote {display}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

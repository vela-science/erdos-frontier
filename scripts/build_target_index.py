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

ROOT = pathlib.Path(__file__).resolve().parent.parent
CANDIDATE_PATH = ROOT / ".vela" / "tmp" / "target-index-candidate.json"
REPOSITORY_PATH = ROOT / ".vela" / "repository.json"
PACKET_PATH = ROOT / "targets" / "erdos-1056.json"
INPUT_PATHS = [
    "scripts/build_target_index.py",
]
TARGET = {
    "id": "erdos:1056",
    "title": "Erdős 1056",
    "why": (
        "The exact current packet binds the open problem, banked k=2..14 "
        "evidence, and the accepted bounded k=15 range 10429201..10429400; "
        "the next non-overlapping range is ready."
    ),
    "state": "open",
    "rank": 1,
    "objective": (
        "Search the exact next k=15 range 10429401..10429600 without repeating "
        "banked coverage; produce one bounded, verifier-replayable artifact "
        "whose Claim states its actual scope and does not imply acceptance."
    ),
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


def git_head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD^{commit}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def validate_packet() -> None:
    repository = json.loads(REPOSITORY_PATH.read_text())
    packet = json.loads(PACKET_PATH.read_text())
    repository_root = "sha256:" + hashlib.sha256(REPOSITORY_PATH.read_bytes()).hexdigest()
    if packet.get("schema") != TARGET["packet"]["schema"]:
        raise ValueError("Erdős 1056 packet schema differs from the Target")
    if packet.get("frontier_id") != repository.get("frontier_id"):
        raise ValueError("Erdős 1056 packet targets another Frontier")
    if (packet.get("target") or {}).get("id") != TARGET["id"]:
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

    previous = packet["accepted_state"]["latest_bounded_negative"]["range"]
    next_range = packet["target"]["next_bounded_range"]
    if previous["last"] + 1 != next_range["first"]:
        raise ValueError("Erdős 1056 next range is not contiguous and non-overlapping")


def candidate() -> dict[str, Any]:
    validate_packet()
    return {
        "schema": "vela.target-index-candidate.v1",
        "frontier_id": "vfr_0a25edabc16db143",
        "source": {
            "git_commit": git_head(),
            "input_paths": INPUT_PATHS,
        },
        "targets": [TARGET],
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

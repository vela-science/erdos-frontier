#!/usr/bin/env python3
"""Build and check the current domain-owned Erdős Target Index candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
CANDIDATE_PATH = ROOT / ".vela" / "tmp" / "target-index-candidate.json"
INDEX_PATH = ROOT / "targets.json"
PACKET_PATH = ROOT / "site" / "problems" / "1056.json"
INPUT_PATHS = [
    "scripts/build_target_index.py",
]
TARGET = {
    "id": "erdos:1056",
    "title": "Erdős 1056",
    "why": (
        "The exact problem packet retains unresolved obligations and nine banked "
        "attempts; the latest bounded search is verified but its stale Claim was "
        "rejected, leaving the problem open and the evidence reusable."
    ),
    "state": "open",
    "rank": 1,
    "objective": (
        "Advance Erdős problem 1056 from its exact packet without repeating "
        "banked routes; produce one bounded, verifier-replayable artifact whose "
        "Claim states its actual scope and does not imply acceptance."
    ),
    "labels": [
        "bounded-artifact",
        "erdos",
        "machine-checkable",
        "residual-obligations",
        "upstream-open",
    ],
    "packet": {
        "path": "site/problems/1056.json",
        "schema": "erdos-frontier.problem-work.v1",
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


def candidate() -> dict[str, Any]:
    return {
        "schema": "vela.target-index-candidate.v1",
        "frontier_id": "vfr_0a25edabc16db143",
        "source": {
            "git_commit": git_head(),
            "input_paths": INPUT_PATHS,
        },
        "targets": [TARGET],
    }


def packet_root() -> str:
    return "sha256:" + hashlib.sha256(PACKET_PATH.read_bytes()).hexdigest()


def check() -> list[str]:
    if not INDEX_PATH.is_file():
        return ["targets.json is absent"]
    sealed = json.loads(INDEX_PATH.read_text())
    if sealed.get("schema") != "vela.target-index.v3":
        return ["targets.json is not a sealed vela.target-index.v3"]
    actual = sealed.get("targets", [])
    if len(actual) != 1:
        return [f"targets.json has {len(actual)} targets; expected 1"]
    failures: list[str] = []
    row = actual[0]
    for key, value in TARGET.items():
        if key != "packet" and row.get(key) != value:
            failures.append(f"targets.json differs at {key}")
    packet = row.get("packet", {})
    if packet.get("path") != TARGET["packet"]["path"]:
        failures.append("targets.json packet path differs")
    if packet.get("schema") != TARGET["packet"]["schema"]:
        failures.append("targets.json packet schema differs")
    if packet.get("size") != PACKET_PATH.stat().st_size:
        failures.append("targets.json packet size differs")
    if packet.get("sha256") != packet_root():
        failures.append("targets.json packet digest differs")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=CANDIDATE_PATH,
    )
    args = parser.parse_args()
    if args.check:
        failures = check()
        if failures:
            print("\n".join(failures), file=sys.stderr)
            return 1
        print("Target Index v3 is current.")
        return 0
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

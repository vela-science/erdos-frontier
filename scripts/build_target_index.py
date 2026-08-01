#!/usr/bin/env python3
"""Generate the final tracked Erdős Target Index directly.

This domain adapter owns target semantics and ranking. Vela validates the
tracked v5 bytes at runtime; there is no candidate, seal, or apply lifecycle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

from validate_target_closure import validate as validate_target_closure

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "targets.json"
REPOSITORY_PATH = ROOT / ".vela" / "repository.json"
PACKET_PATH = ROOT / "targets" / "erdos-1056.json"
FIDELITY_PACKET_PATH = ROOT / "targets" / "erdos-183-astra-fidelity.json"
BUNDLE_SCHEMA = "vela.agent-execution-bundle.v1"
TARGET_ID = "erdos:1056"
FIDELITY_TARGET_ID = "erdos:183:astra-fidelity"
VERIFIER_PROFILE = "erdos-1056-k15-bounded-replay-v1"
FIDELITY_VERIFIER_PROFILE = "erdos-183-astra-fidelity-review-v1"
ARTIFACT_PATH = "artifacts/erdos1056-k15-range-10430401-10430600.txt"
ALLOWED_OUTPUTS = [
    {"type": "text/plain", "path": ARTIFACT_PATH},
    {"type": "engine-manifest"},
    {"type": "verifier-manifest"},
]
TARGET_BASE = {
    "id": TARGET_ID,
    "title": "Erdős 1056",
    "presence": "open",
    "rank": 2,
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
FIDELITY_TARGET_BASE = {
    "id": FIDELITY_TARGET_ID,
    "title": "Erdős 183 statement fidelity",
    "presence": "open",
    "rank": 1,
    "labels": [
        "erdos",
        "external-release",
        "formalization",
        "statement-fidelity",
    ],
    "why": (
        "The exact source snapshot still records Erdős 183 as open while a "
        "later pinned OpenAI release reports a resolution and supplies a "
        "checker-passing Lean declaration; their statement mapping remains "
        "unreviewed."
    ),
    "objective": (
        "Compare the exact source problem, manuscript theorem, and Lean "
        "declaration across definitions, quantifiers, hypotheses, and "
        "conclusion; retain mismatches and uncertainty without treating "
        "checker passage as acceptance."
    ),
    "packet": {
        "path": "targets/erdos-183-astra-fidelity.json",
        "schema": "erdos-frontier.statement-fidelity-work.v1",
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
    if packet.get("verifier_profile") != VERIFIER_PROFILE:
        raise ValueError("Erdős 1056 verifier profile differs from the Target contract")
    bundle_path = rooted_file(
        root,
        packet.get("execution_bundle"),
        "execution bundle",
        schema=True,
    )
    bundle_file = root / bundle_path
    bundle = json.loads(bundle_file.read_text())
    if bundle_file.read_bytes() != canonical_bytes(bundle) + b"\n":
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
    if mission_file.read_bytes() != canonical_bytes(mission) + b"\n":
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
    packets = [
        PACKET_PATH.relative_to(ROOT).as_posix(),
        FIDELITY_PACKET_PATH.relative_to(ROOT).as_posix(),
    ]
    retained = [*paths, *packets]
    commit = subprocess.run(
        ["git", "-C", str(root), "log", "-1", "--format=%H", "--", *retained],
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


def git_source(root: pathlib.Path, paths: list[str]) -> tuple[str, str, str]:
    commit = git_source_commit(root, paths)
    tree = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{commit}^{{tree}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    object_format = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-object-format"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return object_format, commit, tree


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def tracked_entry(relative: str) -> dict[str, Any]:
    row = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--stage", "--", relative],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not row:
        raise ValueError(f"Target Index input is not tracked: {relative}")
    mode = row.split(maxsplit=1)[0]
    data = (ROOT / relative).read_bytes()
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"HEAD:{relative}"],
        check=True,
        capture_output=True,
    ).stdout
    if tracked != data:
        raise ValueError(f"Target Index input differs from HEAD: {relative}")
    return {
        "path": relative,
        "git_mode": mode,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


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


def validate_fidelity_packet(root: pathlib.Path = ROOT) -> None:
    repository_path = root / REPOSITORY_PATH.relative_to(ROOT)
    packet_path = root / FIDELITY_PACKET_PATH.relative_to(ROOT)
    repository = json.loads(repository_path.read_text())
    packet = json.loads(packet_path.read_text())
    repository_root = sha256_root(repository_path.read_bytes())
    release = packet.get("openai_release") or {}
    source = packet.get("source_problem") or {}
    status = source.get("status_observation") or {}
    review = packet.get("review_contract") or {}
    reproduction = packet.get("reproduction_evidence") or {}
    if (
        packet.get("schema") != FIDELITY_TARGET_BASE["packet"]["schema"]
        or packet.get("frontier_id") != repository.get("frontier_id")
        or packet.get("authority") != "non_authoritative"
        or packet.get("repository") != {"root": repository_root}
        or (packet.get("target") or {}).get("id") != FIDELITY_TARGET_ID
        or (packet.get("target") or {}).get("problem") != 183
        or packet.get("verifier_profile") != FIDELITY_VERIFIER_PROFILE
    ):
        raise ValueError("Erdős 183 fidelity packet crosses its Target or authority boundary")
    if (
        release.get("repository") != "https://github.com/openai/ten-proofs"
        or release.get("commit") != "29362184c2b698c1b279bc85b3957ee813646c63"
        or release.get("tree") != "730bf2c6a13dbb96606024c5fd681a48633fb393"
        or (release.get("manuscript") or {}).get("sha256")
        != "sha256:64b900d5fae6fe22f2ae1b8e3b712d20055194a6c81cf343a2455e5898ac7dd6"
        or (release.get("comparator_profile") or {}).get("sha256")
        != "sha256:03c4a87dfda6588dc685afbd4c6da4338f652166b24df0c4ff2f819ca22f5fd7"
        or (release.get("challenge") or {}).get("sha256")
        != "sha256:12f969e50e5b09579849e25692c8cfc1d9351d09278ec9c5e4ea7c36756a6273"
        or (release.get("solution") or {}).get("sha256")
        != "sha256:a87bd60efe16dab00ba07ea4069f22b8dbc991b3f3ba34ae5088b1f8b1987cd3"
    ):
        raise ValueError("Erdős 183 fidelity packet does not bind the exact OpenAI release")
    if (
        status.get("repository") != "https://github.com/teorth/erdosproblems"
        or status.get("commit") != "8138974387d9030542daabe67faaa33eff9356f8"
        or status.get("tree") != "7ed44c260d7eb63a067cf5a16afdb645d494ef06"
        or status.get("sha256")
        != "sha256:a4358d57b591fc92c75981c160a11f43a561de6b5e8478d8f9629511759a9213"
    ):
        raise ValueError("Erdős 183 fidelity packet does not bind the exact source observation")
    if (
        review.get("required_dimensions")
        != [
            "definition_mapping",
            "quantifiers",
            "hypotheses",
            "conclusion",
            "source_timing_and_disagreement",
            "unresolved_questions",
        ]
        or review.get("allowed_conclusions")
        != ["faithful", "not_faithful", "indeterminate"]
        or review.get("accepted_state_change")
        != "none until a separate authorized human Decision"
        or (review.get("output") or {}).get("schema")
        != "vela.statement-fidelity-report.v1"
        or reproduction.get("sha256")
        != "sha256:cd38ac37a3abd04c045e2905886fa418155a1838cb755bc351f96341a84179cd"
    ):
        raise ValueError("Erdős 183 fidelity packet weakens its review contract")


def index() -> dict[str, Any]:
    validation = validate_target_closure(ROOT)
    validate_packet(validation)
    validate_fidelity_packet()
    paths = input_paths(ROOT)
    object_format, commit, tree = git_source(ROOT, paths)
    entries = [tracked_entry(path) for path in paths]
    inputs = {
        "schema": "vela.target-index-input-manifest.v1",
        "entries": entries,
    }
    inputs["input_root"] = sha256_root(canonical_bytes(inputs))
    repository = json.loads(REPOSITORY_PATH.read_text())
    target = target_from_validation(validation)
    targets = [FIDELITY_TARGET_BASE.copy(), target]
    for current, packet_path in zip(
        targets,
        (FIDELITY_PACKET_PATH, PACKET_PATH),
        strict=True,
    ):
        packet = packet_path.read_bytes()
        current["packet"] = {
            **current["packet"],
            "size": len(packet),
            "sha256": sha256_root(packet),
        }
    value = {
        "schema": "vela.target-index.v5",
        "frontier_id": "vfr_0a25edabc16db143",
        "source": {
            "git_object_format": object_format,
            "git_commit": commit,
            "git_tree": tree,
        },
        "inputs": inputs,
        "repository": {
            "origin_id": repository["origin_id"],
            "repository_root": sha256_root(REPOSITORY_PATH.read_bytes()),
        },
        "claim_boundary": {
            "derived": True,
            "authoritative": False,
            "deletable": True,
        },
        "targets": targets,
    }
    value["index_root"] = sha256_root(canonical_bytes(value))
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        expected = canonical_bytes(index())
    except ValueError as error:
        print(f"Target Index unavailable: {error}", file=sys.stderr)
        return 1
    if args.check:
        if not INDEX_PATH.is_file() or INDEX_PATH.read_bytes() != expected:
            print("targets.json is stale; run scripts/build_target_index.py", file=sys.stderr)
            return 1
        print("targets.json is current")
        return 0
    with tempfile.NamedTemporaryFile(dir=ROOT, delete=False) as temporary:
        temporary.write(expected)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = pathlib.Path(temporary.name)
    os.replace(temporary_path, INDEX_PATH)
    print("Wrote targets.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

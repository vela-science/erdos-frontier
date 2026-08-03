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
TARGET_ID = "erdos:1056"
FIDELITY_TARGET_ID = "erdos:183:astra-fidelity"
VERIFIER_PROFILE = "erdos-1056-k15-bounded-replay-v1"
FIDELITY_VERIFIER_PROFILE = "erdos-183-astra-fidelity-review-v1"
FIDELITY_EXECUTION_CONTRACT_PATHS = {
    "producer_profile": "execution/erdos-183-astra-fidelity/producer-profile.v1.json",
    "verifier_capsule": "execution/erdos-183-astra-fidelity/reviewer-capsule.v1.json",
    "result_contract": "execution/erdos-183-astra-fidelity/result-contract.v1.json",
}
ERDOS_1056_EXECUTION_CONTRACT_PATHS = {
    "producer_profile": "execution/erdos-1056/10430601-10430800/producer-profile.v1.json",
    "verifier_capsule": "execution/erdos-1056/verifier/v1/linux-arm64/verifier",
    "result_contract": "execution/erdos-1056/10430601-10430800/result-contract.v1.json",
}
ERDOS_1056_VERIFIER_SOURCE_PATH = "execution/erdos-1056/verifier/v1/verifier.cpp"
ARTIFACT_PATH = "artifacts/erdos1056-k15-range-10430601-10430800.txt"
ALLOWED_OUTPUTS = [
    {"type": "text/plain", "path": ARTIFACT_PATH},
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
) -> str:
    required = {"path", "size", "sha256"}
    if not isinstance(locator, dict) or set(locator) != required:
        raise ValueError(f"{label} must be one closed rooted-file locator")
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
    contracts = packet.get("execution_contracts")
    if not isinstance(contracts, dict) or set(contracts) != set(
        ERDOS_1056_EXECUTION_CONTRACT_PATHS
    ):
        raise ValueError("Erdős 1056 execution contract set differs")
    contract_paths = {}
    for name, expected_path in ERDOS_1056_EXECUTION_CONTRACT_PATHS.items():
        path = rooted_file(root, contracts.get(name), f"Erdős 1056 {name}")
        if path != expected_path:
            raise ValueError(f"Erdős 1056 {name} path differs")
        contract_paths[name] = path
    producer_profile_file = root / contract_paths["producer_profile"]
    producer_profile = json.loads(producer_profile_file.read_text())
    if producer_profile_file.read_bytes() != canonical_bytes(producer_profile) + b"\n":
        raise ValueError("Erdős 1056 producer profile must be canonical JSON")
    if (
        producer_profile.get("schema")
        != "erdos-frontier.bounded-search-producer-profile.v1"
        or producer_profile.get("authority") != "non_authoritative"
        or producer_profile.get("effect") != "none"
        or producer_profile.get("target") != TARGET_ID
        or producer_profile.get("range")
        != {"first": 10430601, "inclusive": True, "last": 10430800}
        or (producer_profile.get("artifact") or {}).get("path") != ARTIFACT_PATH
        or "worker" in producer_profile
        or "budgets" in producer_profile
    ):
        raise ValueError("Erdős 1056 producer profile crosses its scientific boundary")

    result_contract_file = root / contract_paths["result_contract"]
    result_contract = json.loads(result_contract_file.read_text())
    if result_contract_file.read_bytes() != canonical_bytes(result_contract) + b"\n":
        raise ValueError("Erdős 1056 result contract must be canonical JSON")
    if (
        result_contract.get("schema")
        != "erdos-frontier.bounded-search-result-contract.v1"
        or result_contract.get("authority") != "non_authoritative"
        or result_contract.get("effect") != "none"
        or result_contract.get("target") != TARGET_ID
        or result_contract.get("range")
        != {"first": 10430601, "inclusive": True, "last": 10430800}
        or (result_contract.get("artifact") or {}).get("path") != ARTIFACT_PATH
        or (result_contract.get("verifier") or {}).get(
            "witness_minimum_multiplicity"
        )
        != 16
    ):
        raise ValueError("Erdős 1056 result contract weakens its exact boundary")
    return sorted(
        {
            ERDOS_1056_VERIFIER_SOURCE_PATH,
            *contract_paths.values(),
        }
    )


def fidelity_execution_input_paths(root: pathlib.Path = ROOT) -> list[str]:
    packet = json.loads(
        (root / FIDELITY_PACKET_PATH.relative_to(ROOT)).read_text()
    )
    contracts = packet.get("execution_contracts")
    if not isinstance(contracts, dict) or set(contracts) != set(
        FIDELITY_EXECUTION_CONTRACT_PATHS
    ):
        raise ValueError("Erdős 183 execution contract set differs")
    paths = []
    for name, expected_path in FIDELITY_EXECUTION_CONTRACT_PATHS.items():
        path = rooted_file(root, contracts.get(name), f"Erdős 183 {name}")
        if path != expected_path:
            raise ValueError(f"Erdős 183 {name} path differs")
        value = json.loads((root / path).read_text())
        if value.get("authority") != "non_authoritative" or value.get(
            "target"
        ) != FIDELITY_TARGET_ID:
            raise ValueError(f"Erdős 183 {name} crosses its Target or authority boundary")
        paths.append(path)
    return sorted(paths)


def input_paths(
    root: pathlib.Path = ROOT, *, include_fidelity: bool = False
) -> list[str]:
    paths = [
        "scripts/build_target_index.py",
        "scripts/validate_target_closure.py",
        *(
            path.relative_to(root).as_posix()
            for path in (root / "targets" / "closures").glob("*.json")
        ),
        *execution_input_paths(root),
    ]
    if include_fidelity:
        paths.extend(fidelity_execution_input_paths(root))
    return sorted(paths)


def git_source_commit(
    root: pathlib.Path = ROOT,
    paths: list[str] | None = None,
    *,
    include_fidelity: bool = False,
) -> str:
    paths = paths or input_paths(root, include_fidelity=include_fidelity)
    packets = [PACKET_PATH.relative_to(ROOT).as_posix()]
    if include_fidelity:
        packets.append(FIDELITY_PACKET_PATH.relative_to(ROOT).as_posix())
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


def git_source(
    root: pathlib.Path, paths: list[str], *, include_fidelity: bool = False
) -> tuple[str, str, str]:
    commit = git_source_commit(root, paths, include_fidelity=include_fidelity)
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
    contracts = packet.get("execution_contracts") or {}
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
    if {
        name: (contracts.get(name) or {}).get("sha256")
        for name in FIDELITY_EXECUTION_CONTRACT_PATHS
    } != {
        "producer_profile": "sha256:3fe54bd5fdffc8bb639155b4d408709082eee5aaf255b7d582ad17a4434f5f37",
        "verifier_capsule": "sha256:aec9b1c3b91b1a2cdfaf6d3da8f051884b0017b31e7450d3148ba0565235d8ec",
        "result_contract": "sha256:7618f6bbd2c5aa13653a771735c586e6cb24056b092854e20c19112471aff6b2",
    }:
        raise ValueError("Erdős 183 fidelity packet execution roots differ")


def fidelity_work_complete(root: pathlib.Path = ROOT) -> bool:
    """Return whether the exact one-shot fidelity work is pending or accepted.

    The tracked Target packet remains available as history, but producer work is
    no longer offered after its exact report is bound through a Submission and
    Proposal to a passing scoped Verification. Pending and accepted Claims both
    close this one-shot Target. Rejected or withdrawn work may be offered again.
    This derived lifecycle never implies that Verification caused acceptance.
    """

    repository_path = root / REPOSITORY_PATH.relative_to(ROOT)
    packet_path = root / FIDELITY_PACKET_PATH.relative_to(ROOT)
    repository = json.loads(repository_path.read_text())
    packet = json.loads(packet_path.read_text())
    review = packet.get("review_contract") or {}
    output = review.get("output") or {}
    report_path_raw = output.get("path")
    if not isinstance(report_path_raw, str):
        return False
    report_relative = pathlib.PurePosixPath(report_path_raw)
    if report_relative.is_absolute() or ".." in report_relative.parts:
        return False
    report_path = root.joinpath(*report_relative.parts)
    if not report_path.is_file() or report_path.is_symlink():
        return False
    report_bytes = report_path.read_bytes()
    report_root = sha256_root(report_bytes)
    try:
        report = json.loads(report_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    required_dimensions = review.get("required_dimensions")
    if (
        report.get("schema") != output.get("schema")
        or (report.get("target") or {}).get("frontier_id")
        != repository.get("frontier_id")
        or (report.get("target") or {}).get("target_id") != FIDELITY_TARGET_ID
        or report.get("conclusion") not in review.get("allowed_conclusions", [])
        or not isinstance(required_dimensions, list)
        or set((report.get("matrix") or {})) != set(required_dimensions)
        or not isinstance(report.get("nonclaims"), list)
        or not report["nonclaims"]
        or not all(isinstance(item, str) and item for item in report["nonclaims"])
    ):
        return False

    def records(kind: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        values = []
        for row in repository.get(kind, []):
            relative_raw = row.get("path")
            expected_root = row.get("root")
            if not isinstance(relative_raw, str) or not isinstance(expected_root, str):
                continue
            relative = pathlib.PurePosixPath(relative_raw)
            if relative.is_absolute() or ".." in relative.parts:
                continue
            path = root.joinpath(*relative.parts)
            if not path.is_file() or path.is_symlink():
                continue
            data = path.read_bytes()
            if sha256_root(data) != expected_root:
                continue
            try:
                value = json.loads(data)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            values.append((row, value))
        return values

    contracts = packet.get("execution_contracts") or {}
    expected_binding = {
        "profile_root": (contracts.get("producer_profile") or {}).get("sha256"),
        "verifier_capsule_root": (contracts.get("verifier_capsule") or {}).get(
            "sha256"
        ),
        "result_contract_root": (contracts.get("result_contract") or {}).get(
            "sha256"
        ),
    }
    review_requirement = review.get("verification")
    submissions = []
    for row, submission in records("submissions"):
        binding = submission.get("execution_binding") or {}
        submission_requirements = submission.get("verification_requirements")
        artifact = {
            "kind": "statement-fidelity-report",
            "path": report_path_raw,
            "digest": report_root,
        }
        if (
            submission.get("schema") == "vela.submission.v1"
            and submission.get("submission_id") == row.get("id")
            and artifact in submission.get("artifacts", [])
            and isinstance(review_requirement, str)
            and isinstance(submission_requirements, list)
            and len(submission_requirements) == 1
            and isinstance(submission_requirements[0], str)
            and submission_requirements[0]
            and binding.get("schema") == "vela.execution-binding.v1"
            and all(binding.get(key) == value for key, value in expected_binding.items())
            and isinstance(binding.get("packet_root"), str)
            and binding["packet_root"].startswith("sha256:")
        ):
            submissions.append((row, submission, submission_requirements[0]))

    pending = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("pending_claims", [])
    }
    accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
    }
    for submission_row, submission, submission_requirement in submissions:
        for proposal_row, proposal in records("proposals"):
            package = proposal.get("producer_package") or {}
            subject = proposal.get("subject") or {}
            claim_id = subject.get("id")
            claim_root = subject.get("root")
            if (
                proposal.get("schema") != "vela.proposal.v1"
                or proposal.get("proposal_id") != proposal_row.get("id")
                or proposal.get("action") != "claim.add"
                or package
                != {
                    "kind": "submission_v1",
                    "id": submission.get("submission_id"),
                    "root": submission_row.get("root"),
                    "path": submission_row.get("path"),
                }
                or subject.get("kind") != "claim"
                or (
                    pending.get(claim_id) != claim_root
                    and accepted.get(claim_id) != claim_root
                )
            ):
                continue
            for verification_row, verification in records("verifications"):
                verification_subject = verification.get("subject") or {}
                method = verification.get("method") or {}
                scope = verification.get("scope") or {}
                if (
                    verification.get("schema") == "vela.verification-record.v1"
                    and verification.get("verification_record_id")
                    == verification_row.get("id")
                    and verification.get("outcome") == "pass"
                    and verification_subject.get("claim_id") == claim_id
                    and verification_subject.get("proposal_id")
                    == proposal.get("proposal_id")
                    and verification_subject.get("submission_id")
                    == submission.get("submission_id")
                    and verification_subject.get("submission_root")
                    == submission_row.get("root")
                    and set(verification_subject.get("artifact_ids", []))
                    == {report_root.removeprefix("sha256:")}
                    and method
                    == {
                        "profile": packet.get("verifier_profile"),
                        "implementation": FIDELITY_EXECUTION_CONTRACT_PATHS[
                            "verifier_capsule"
                        ],
                        "environment_root": expected_binding[
                            "verifier_capsule_root"
                        ],
                    }
                    and scope.get("property") == submission_requirement
                ):
                    return True
    return False


def index() -> dict[str, Any]:
    validation = validate_target_closure(ROOT)
    validate_packet(validation)
    fidelity_complete = fidelity_work_complete()
    if not fidelity_complete:
        validate_fidelity_packet()
    paths = input_paths(ROOT, include_fidelity=not fidelity_complete)
    object_format, commit, tree = git_source(
        ROOT, paths, include_fidelity=not fidelity_complete
    )
    entries = [tracked_entry(path) for path in paths]
    inputs = {
        "schema": "vela.target-index-input-manifest.v1",
        "entries": entries,
    }
    inputs["input_root"] = sha256_root(canonical_bytes(inputs))
    repository = json.loads(REPOSITORY_PATH.read_text())
    target = target_from_validation(validation)
    targets_with_packets = [(target, PACKET_PATH)]
    if not fidelity_complete:
        targets_with_packets.insert(0, (FIDELITY_TARGET_BASE.copy(), FIDELITY_PACKET_PATH))
    targets = [current for current, _ in targets_with_packets]
    for current, packet_path in targets_with_packets:
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

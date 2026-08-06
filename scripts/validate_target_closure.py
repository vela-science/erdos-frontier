#!/usr/bin/env python3
"""Validate domain-owned Erdős producer closure and successor coverage.

This is a read-only, non-authoritative validator. A producer-complete Target is
closed by an exact Submission that satisfies its frozen completion contract.
Verification and scientific Standing remain separate: a passing Verification
may be retained with the closure, but only a repository-authority Decision can
change accepted state.
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
CLOSURE_DIRECTORY = ROOT / "targets" / "closures"
PACKET_PATH = ROOT / "targets" / "erdos-1056.json"
REPOSITORY_PATH = ROOT / ".vela" / "repository.json"
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
BOUNDED_NEGATIVE_CLAIM_RE = re.compile(
    r"^An exhaustive bounded search of the (?P<primes_tested>[0-9]+) primes "
    r"in the inclusive range (?P<range_start>[0-9]+)\.\.(?P<range_end>[0-9]+) "
    r"found no k=(?P<k>[0-9]+) witness; the maximum multiplicity observed was "
    r"(?P<max_multiplicity>[0-9]+) at p=(?P<best_p>[0-9]+), "
    r"residue (?P<best_residue>[0-9]+)\.$"
)
SEARCH_ARTIFACT_KEYS = {
    "schema",
    "status",
    "problem",
    "k",
    "range_start",
    "range_end",
    "primes_tested",
    "max_multiplicity",
    "best_p",
    "best_residue",
    "cuts",
}


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
    root: pathlib.Path,
    commit: str,
    path_raw: str,
    expected_root: str,
    required_path: str,
    label: str,
) -> dict[str, Any]:
    if not GIT_COMMIT_RE.fullmatch(commit):
        raise TargetClosureError(f"{label} Git commit is malformed")
    if path_raw != required_path:
        raise TargetClosureError(f"{label} Git path differs")
    if not SHA256_RE.fullmatch(expected_root):
        raise TargetClosureError(f"{label} SHA-256 root is malformed")

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
        raise TargetClosureError(f"{label} Git commit is unavailable")
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
            f"{label} Git commit is not retained in current history"
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
        raise TargetClosureError(f"{label} is absent at its Git commit")
    observed_root = "sha256:" + hashlib.sha256(packet_result.stdout).hexdigest()
    if observed_root != expected_root:
        raise TargetClosureError(
            f"{label} Git bytes drifted: "
            f"expected {expected_root}, observed {observed_root}"
        )
    try:
        value = json.loads(packet_result.stdout)
    except json.JSONDecodeError as error:
        raise TargetClosureError(
            f"{label} Git bytes are not canonical JSON"
        ) from error
    if not isinstance(value, dict):
        raise TargetClosureError(f"{label} Git bytes are not a JSON object")
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


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def parse_search_artifact(path: pathlib.Path) -> dict[str, Any]:
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise TargetClosureError(f"cannot read completion artifact: {error}") from error
    values: dict[str, str] = {}
    for line in lines:
        if not line or "=" not in line:
            raise TargetClosureError("completion artifact is not canonical key=value text")
        key, value = line.split("=", 1)
        if key in values:
            raise TargetClosureError(f"completion artifact repeats {key}")
        values[key] = value
    if set(values) != SEARCH_ARTIFACT_KEYS:
        raise TargetClosureError(
            "completion artifact keys differ: "
            f"expected {sorted(SEARCH_ARTIFACT_KEYS)}, observed {sorted(values)}"
        )

    integer_fields = (
        "problem",
        "k",
        "range_start",
        "range_end",
        "primes_tested",
        "max_multiplicity",
        "best_p",
        "best_residue",
    )
    parsed: dict[str, Any] = {
        "schema": values["schema"],
        "status": values["status"],
    }
    for field in integer_fields:
        if not values[field].isdigit():
            raise TargetClosureError(
                f"completion artifact {field} is not an unsigned integer"
            )
        parsed[field] = int(values[field])
    cuts_raw = values["cuts"].split(",") if values["cuts"] else []
    if not cuts_raw or any(not value.isdigit() for value in cuts_raw):
        raise TargetClosureError("completion artifact cuts are malformed")
    parsed["cuts"] = [int(value) for value in cuts_raw]
    return parsed


def validate_search_artifact(
    path: pathlib.Path,
    assertion: str,
    closed_first: int,
    closed_last: int,
) -> dict[str, Any]:
    artifact = parse_search_artifact(path)
    if artifact["schema"] != "canopus.erdos1056-k15-search.v1":
        raise TargetClosureError("completion artifact schema differs")
    if artifact["status"] != "negative":
        raise TargetClosureError("completion artifact is not a bounded negative")
    if artifact["problem"] != 1056 or artifact["k"] != 15:
        raise TargetClosureError("completion artifact names another problem or k")
    if (artifact["range_start"], artifact["range_end"]) != (
        closed_first,
        closed_last,
    ):
        raise TargetClosureError("completion artifact range differs from the closure")

    observed_primes = sum(
        1 for value in range(closed_first, closed_last + 1) if is_prime(value)
    )
    if artifact["primes_tested"] != observed_primes:
        raise TargetClosureError("completion artifact prime count is incorrect")
    if (
        not is_prime(artifact["best_p"])
        or not closed_first <= artifact["best_p"] <= closed_last
    ):
        raise TargetClosureError("completion artifact best_p is outside the prime range")
    cuts = artifact["cuts"]
    if (
        len(cuts) != artifact["max_multiplicity"]
        or cuts != sorted(set(cuts))
        or any(value < 0 or value >= artifact["best_p"] for value in cuts)
    ):
        raise TargetClosureError("completion artifact cuts are inconsistent")
    if not 0 <= artifact["best_residue"] < artifact["best_p"]:
        raise TargetClosureError("completion artifact best_residue is inconsistent")

    match = BOUNDED_NEGATIVE_CLAIM_RE.fullmatch(assertion)
    if match is None:
        raise TargetClosureError("bounded Claim does not use the exact result contract")
    claim_facts = {key: int(value) for key, value in match.groupdict().items()}
    comparable = {
        key: artifact[key]
        for key in (
            "primes_tested",
            "range_start",
            "range_end",
            "k",
            "max_multiplicity",
            "best_p",
            "best_residue",
        )
    }
    if claim_facts != comparable:
        raise TargetClosureError("completion artifact and Claim facts differ")
    return artifact


def submission_artifact_by_kind(
    submission: dict[str, Any], kind: str
) -> dict[str, Any]:
    rows = [
        row
        for row in submission.get("artifacts", [])
        if isinstance(row, dict) and row.get("kind") == kind
    ]
    if len(rows) != 1:
        raise TargetClosureError(
            f"Submission must bind exactly one {kind} artifact"
        )
    return rows[0]


def validate_manifest_artifact(
    root: pathlib.Path,
    row: dict[str, Any],
    expected_schema: str,
) -> dict[str, Any]:
    path = relative_path(root, row.get("path", ""))
    require_tracked(root, path)
    digest = row.get("digest", "")
    if file_root(path) != digest:
        raise TargetClosureError(f"{row.get('kind')} artifact root drifted")
    manifest = read_json(path)
    if manifest.get("schema") != expected_schema:
        raise TargetClosureError(f"{row.get('kind')} artifact schema differs")
    return manifest


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
    basis = closure.get("closure_basis")
    if basis == "accepted_standing":
        # Accepted Standing is the live boundary. Its complete historical
        # evidence remains in the predecessor archive named by the compaction
        # origin; daily validation must not keep terminal workflow records live.
        required = {"accepted_claim"}
        allowed = required
    elif basis == "verified_submission":
        required = {
            "claim",
            "submission",
            "proposal",
            "artifact",
            "verification",
        }
        allowed = required
    else:
        raise TargetClosureError("Target closure basis is unsupported")
    if not required.issubset(by_kind) or not set(by_kind).issubset(allowed):
        raise TargetClosureError(
            "Target closure evidence kinds differ: "
            f"required {sorted(required)}, allowed {sorted(allowed)}, "
            f"observed {sorted(by_kind)}"
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


def validate_closure(
    root: pathlib.Path,
    path: pathlib.Path,
    repository: dict[str, Any],
) -> dict[str, Any]:
    require_tracked(root, path)
    closure = read_json(path)
    if closure.get("schema") != "vela.target-closure.v1":
        raise TargetClosureError(f"unsupported Target closure schema at {path}")
    if closure.get("frontier_id") != repository.get("frontier_id"):
        raise TargetClosureError(f"Target closure names another Frontier at {path}")
    if closure.get("target_id") != "erdos:1056":
        raise TargetClosureError(f"Target closure names another Target at {path}")
    if closure.get("status") != "closed":
        raise TargetClosureError(f"non-closed envelope exposed at {path}")

    contract = closure.get("completion_contract")
    if canonical_root(contract) != closure.get("completion_contract_root"):
        raise TargetClosureError(f"Target completion-contract root drifted at {path}")

    closed_first, closed_last = validate_range(
        closure.get("completed_scope"), f"{path.name} completed scope"
    )
    completed_packet = closure.get("completed_packet") or {}
    retained_packet = retained_git_json(
        root,
        completed_packet.get("git_commit", ""),
        completed_packet.get("path", ""),
        completed_packet.get("sha256", ""),
        PACKET_PATH.relative_to(ROOT).as_posix(),
        "completed packet",
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
    retained_git_json(
        root,
        closure.get("repository_commit", ""),
        REPOSITORY_PATH.relative_to(ROOT).as_posix(),
        closure.get("repository_root", ""),
        REPOSITORY_PATH.relative_to(ROOT).as_posix(),
        "closure repository state",
    )

    evidence = evidence_by_kind(closure)
    basis = closure["closure_basis"]
    claim_kind = "accepted_claim" if basis == "accepted_standing" else "claim"
    claim = load_evidence(root, evidence[claim_kind], "claim_id")
    claim_id = evidence[claim_kind]["id"]
    claim_root = evidence[claim_kind]["root"]
    assertion = ((claim.get("assertion") or {}).get("text")) or ""
    if basis == "accepted_standing":
        accepted = {
            row.get("claim_id"): row.get("claim_root")
            for row in repository.get("accepted_claims", [])
            if isinstance(row, dict)
        }
        if accepted.get(claim_id) != claim_root:
            raise TargetClosureError("bounded-range Claim is not accepted")
        exact_range = f"inclusive range {closed_first}..{closed_last}"
        if exact_range not in assertion:
            raise TargetClosureError(
                "accepted bounded-range Claim does not state its exact range"
            )
        return {
            "path": path.relative_to(root).as_posix(),
            "basis": basis,
            "first": closed_first,
            "last": closed_last,
            "claim_id": claim_id,
            "claim_root": claim_root,
            "submission_id": None,
            "submission_root": None,
            "proposal_id": None,
            "proposal_root": None,
            "artifact_root": None,
            "verification_id": None,
            "verification_root": None,
            "decision_event_root": None,
        }

    submission = load_evidence(root, evidence["submission"], "submission_id")
    artifact_row = evidence["artifact"]
    artifact_path = relative_path(root, artifact_row.get("path", ""))
    require_tracked(root, artifact_path)
    if file_root(artifact_path) != artifact_row.get("root"):
        raise TargetClosureError("Target closure artifact root drifted")
    # An Artifact has no record to carry an ID field, so the other four kinds'
    # check does not reach this row. Its ID is the content address itself —
    # the same form the Verification Record binds below, and the only form the
    # protocol accepts for an Artifact reference. Unchecked, it silently
    # truncated.
    if artifact_row.get("id") != artifact_row["root"].removeprefix("sha256:"):
        raise TargetClosureError(
            "artifact evidence ID is not the Artifact's content address"
        )

    if submission.get("claim", {}).get("assertion") != assertion:
        raise TargetClosureError("Submission and Claim assertions differ")
    validate_search_artifact(artifact_path, assertion, closed_first, closed_last)

    if submission.get("replayability") != "exact":
        raise TargetClosureError("Submission is not exactly replayable")
    verification_requirements = submission.get("verification_requirements")
    if (
        not isinstance(verification_requirements, list)
        or not verification_requirements
        or any(not isinstance(value, str) or not value for value in verification_requirements)
    ):
        raise TargetClosureError("Submission omits its exact replay requirement")

    execution_binding = submission.get("execution_binding")
    current_execution = isinstance(execution_binding, dict)
    if current_execution:
        contracts = retained_packet.get("execution_contracts") or {}
        if set(contracts) != {
            "producer_profile",
            "verifier_capsule",
            "result_contract",
        }:
            raise TargetClosureError(
                "completed packet omits the current execution contracts"
            )
        expected_binding = {
            "schema": "vela.execution-binding.v1",
            "packet_root": completed_packet.get("sha256"),
            "profile_root": (contracts.get("producer_profile") or {}).get(
                "sha256"
            ),
            "verifier_capsule_root": (
                contracts.get("verifier_capsule") or {}
            ).get("sha256"),
            "result_contract_root": (contracts.get("result_contract") or {}).get(
                "sha256"
            ),
        }
        if execution_binding != expected_binding:
            raise TargetClosureError(
                "Submission execution binding differs from the completed packet"
            )

        result_artifact = submission_artifact_by_kind(
            submission, "bounded-search"
        )
        result_contract_row = contracts["result_contract"]
        result_contract_path = relative_path(
            root, result_contract_row.get("path", "")
        )
        require_tracked(root, result_contract_path)
        if file_root(result_contract_path) != result_contract_row.get("sha256"):
            raise TargetClosureError("result contract root drifted")
        result_contract = read_json(result_contract_path)
        contract_artifact = result_contract.get("artifact") or {}
        contract_first, contract_last = validate_range(
            result_contract.get("range"), "result contract range"
        )
        if (
            result_contract.get("schema")
            != "erdos-frontier.bounded-search-result-contract.v1"
            or result_contract.get("authority") != "non_authoritative"
            or result_contract.get("effect") != "none"
            or result_contract.get("target") != "erdos:1056"
            or (contract_first, contract_last) != (closed_first, closed_last)
            or contract_artifact.get("path") != result_artifact.get("path")
            or result_artifact.get("digest") != artifact_row.get("root")
        ):
            raise TargetClosureError(
                "Submission, result contract, and completion artifact differ"
            )
        required_artifact_ids = {
            result_artifact["digest"].removeprefix("sha256:")
        }
    else:
        # Historical retained Canopus submissions predate the current direct
        # packet/profile/capsule/result execution binding. They remain exact
        # evidence for already-completed ranges, not an active producer path.
        result_artifact = submission_artifact_by_kind(submission, "text/plain")
        if (
            result_artifact.get("path") != artifact_row.get("path")
            or result_artifact.get("digest") != artifact_row.get("root")
        ):
            raise TargetClosureError(
                "Submission does not bind the completion artifact"
            )
        engine_artifact = submission_artifact_by_kind(
            submission, "engine-manifest"
        )
        verifier_artifact = submission_artifact_by_kind(
            submission, "verifier-manifest"
        )
        validate_manifest_artifact(
            root, engine_artifact, "canopus.engine-manifest.v0"
        )
        verifier_manifest = validate_manifest_artifact(
            root, verifier_artifact, "canopus.verifier-manifest.v1"
        )
        executable_root = verifier_manifest.get("executable_sha256")
        if (
            not isinstance(executable_root, str)
            or not SHA256_RE.fullmatch(executable_root)
            or executable_root not in "\n".join(verification_requirements)
        ):
            raise TargetClosureError(
                "Submission replay requirement does not bind the verifier capsule"
            )
        required_artifact_ids = {
            row["digest"].removeprefix("sha256:")
            for row in (result_artifact, engine_artifact, verifier_artifact)
        }

    proposal_id: str | None = None
    verification_root: str | None = None
    decision_event_root: str | None = None
    proposal = load_evidence(root, evidence["proposal"], "proposal_id")
    subject = proposal.get("subject") or {}
    producer_package = proposal.get("producer_package") or {}
    if subject.get("id") != claim_id or subject.get("root") != claim_root:
        raise TargetClosureError("Proposal does not bind the Claim")
    if (
        producer_package.get("id") != evidence["submission"]["id"]
        or producer_package.get("root") != evidence["submission"]["root"]
        or producer_package.get("path") != evidence["submission"]["path"]
    ):
        raise TargetClosureError("Proposal does not bind the Submission")
    proposal_id = proposal.get("proposal_id")

    verification_row = evidence.get("verification")
    if verification_row is not None:
        verification = load_evidence(
            root, verification_row, "verification_record_id"
        )
        subject = verification.get("subject") or {}
        if verification.get("outcome") != "pass":
            raise TargetClosureError("retained Target Verification did not pass")
        if subject.get("claim_id") != claim_id:
            raise TargetClosureError("Verification does not bind the Claim")
        if subject.get("submission_id") != evidence["submission"]["id"]:
            raise TargetClosureError("Verification does not bind the Submission")
        if set(subject.get("artifact_ids") or []) != required_artifact_ids:
            raise TargetClosureError(
                "Verification does not bind every required artifact"
            )
        if current_execution:
            if (
                verification.get("scope", {}).get("property")
                not in verification_requirements
                or verification.get("verifier")
                == submission.get("provenance", {}).get("producer")
                or submission.get("provenance", {}).get("producer")
                not in verification.get("independence", {}).get(
                    "declared_independent_of", []
                )
            ):
                raise TargetClosureError(
                    "Verification does not satisfy the exact independent requirement"
                )
        elif (
            verification.get("method", {}).get("environment_root")
            != verifier_artifact.get("digest")
        ):
            raise TargetClosureError(
                "Verification environment does not bind the verifier manifest"
            )
        if proposal_id is not None and subject.get("proposal_id") != proposal_id:
            raise TargetClosureError("Verification does not bind the Proposal")
        proposal_id = subject.get("proposal_id")
        verification_root = verification_row["root"]

    return {
        "path": path.relative_to(root).as_posix(),
        "basis": basis,
        "first": closed_first,
        "last": closed_last,
        "claim_id": claim_id,
        "claim_root": claim_root,
        "submission_id": evidence["submission"]["id"],
        "submission_root": evidence["submission"]["root"],
        "proposal_id": proposal_id,
        "proposal_root": (evidence.get("proposal") or {}).get("root"),
        "artifact_root": artifact_row["root"],
        "verification_id": (verification_row or {}).get("id"),
        "verification_root": verification_root,
        "decision_event_root": decision_event_root,
    }


def validate_all_closed_ranges(
    root: pathlib.Path, repository: dict[str, Any]
) -> list[dict[str, Any]]:
    closures: list[dict[str, Any]] = []
    directory = root / CLOSURE_DIRECTORY.relative_to(ROOT)
    for path in sorted(directory.glob("*.json")):
        require_tracked(root, path)
        raw = read_json(path)
        if raw.get("target_id") != "erdos:1056":
            continue
        closures.append(validate_closure(root, path, repository))
    closures.sort(key=lambda row: (row["first"], row["last"], row["path"]))
    for previous, current in zip(closures, closures[1:], strict=False):
        if current["first"] <= previous["last"]:
            raise TargetClosureError(
                "completed Erdős ranges overlap: "
                f"{previous['path']} and {current['path']}"
            )
    return closures


def validate(
    root: pathlib.Path = ROOT,
    closure_path: pathlib.Path | None = None,
    packet_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    packet_path = (packet_path or root / PACKET_PATH.relative_to(ROOT)).resolve()
    repository_path = root / REPOSITORY_PATH.relative_to(ROOT)
    for path in (packet_path, repository_path):
        require_tracked(root, path)

    packet = read_json(packet_path)
    repository = read_json(repository_path)
    closures = validate_all_closed_ranges(root, repository)
    if not closures:
        raise TargetClosureError("no completed Erdős Target closure is retained")
    if closure_path is not None:
        requested = closure_path.resolve().relative_to(root).as_posix()
        if requested not in {row["path"] for row in closures}:
            raise TargetClosureError("requested Target closure is not retained")

    if packet.get("schema") != "erdos-frontier.problem-work.v2":
        raise TargetClosureError("successor packet has the wrong schema")
    if packet.get("frontier_id") != repository.get("frontier_id"):
        raise TargetClosureError("successor packet names another Frontier")
    if packet.get("target", {}).get("id") != "erdos:1056":
        raise TargetClosureError("successor packet names another Target")
    repository_locator = packet.get("repository") or {}
    if set(repository_locator) != {"commit", "tree"}:
        raise TargetClosureError(
            "successor packet must bind its source commit and tree, not a mutable "
            "repository root"
        )
    successor_first, successor_last = validate_range(
        packet.get("target", {}).get("next_bounded_range"), "successor range"
    )
    latest = packet.get("accepted_state", {}).get("latest_bounded_negative") or {}
    latest_first, latest_last = validate_range(
        latest.get("range"), "latest accepted bounded range"
    )
    accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
        if isinstance(row, dict)
    }
    if accepted.get(latest.get("claim_id")) != latest.get("claim_root"):
        raise TargetClosureError("packet latest bounded Claim is not accepted")

    producer_closures = [
        row
        for row in closures
        if row["basis"] == "verified_submission" and row["last"] > latest_last
    ]
    expected_first = latest_last + 1
    for row in producer_closures:
        if row["first"] != expected_first:
            raise TargetClosureError(
                "producer-complete coverage repeats, overlaps, or skips accepted coverage"
            )
        expected_first = row["last"] + 1
    if successor_first != expected_first:
        raise TargetClosureError(
            "successor repeats, overlaps, or skips completed producer coverage"
        )

    newest = producer_closures[-1] if producer_closures else None
    progress = packet.get("producer_completion", {}).get(
        "latest_verified_submission"
    )
    if newest is None:
        if progress is not None:
            raise TargetClosureError("packet invents producer-complete work")
    else:
        if not isinstance(progress, dict):
            raise TargetClosureError("packet omits producer-complete work")
        progress_first, progress_last = validate_range(
            progress.get("range"), "latest producer-complete range"
        )
        if (progress_first, progress_last) != (newest["first"], newest["last"]):
            raise TargetClosureError("packet binds the wrong producer-complete range")
        exact_fields = {
            "claim_id": newest["claim_id"],
            "claim_root": newest["claim_root"],
            "submission_id": newest["submission_id"],
            "submission_root": newest["submission_root"],
            "proposal_id": newest["proposal_id"],
            "proposal_root": newest["proposal_root"],
            "artifact_root": newest["artifact_root"],
            "verification_id": newest["verification_id"],
            "verification_root": newest["verification_root"],
        }
        for field, expected in exact_fields.items():
            if progress.get(field) != expected:
                raise TargetClosureError(
                    f"packet producer completion binds the wrong {field}"
                )

    newest_closure = closures[-1]
    return {
        "schema": "erdos-frontier.target-closure-check.v1",
        "ok": True,
        "closed_target": "erdos:1056",
        "closed_range": {
            "first": newest_closure["first"],
            "last": newest_closure["last"],
        },
        "closure_basis": newest_closure["basis"],
        "completion_claim_root": newest_closure["claim_root"],
        "verification_root": newest_closure["verification_root"],
        "accepted_coverage": {"first": latest_first, "last": latest_last},
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

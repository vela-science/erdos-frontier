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

from validate_target_closure import (
    TargetClosureError,
    validate_search_artifact,
    validate as validate_target_closure,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "targets.json"
REPOSITORY_PATH = ROOT / ".vela" / "repository.json"
PACKET_PATH = ROOT / "targets" / "erdos-1056.json"
FIDELITY_PACKET_PATH = ROOT / "targets" / "erdos-183-astra-fidelity.json"
ERDOS_264_PACKET_PATH = ROOT / "targets" / "erdos-264-parts-i-proof-repair.json"
ERDOS_203_PACKET_PATH = ROOT / "targets" / "erdos-203-finite-cover.json"
ERDOS_203_CHORDAL_PACKET_PATH = (
    ROOT / "targets" / "erdos-203-chordal-obstruction.json"
)
ERDOS_730_PACKET_PATH = ROOT / "targets" / "erdos-730-external-proof-boundary.json"
ERDOS_730_HANDOFF_PATH = (
    ROOT
    / "execution"
    / "erdos-730-proof-boundary"
    / "post-decision-handoff.v1.json"
)
TARGET_ID = "erdos:1056"
FIDELITY_TARGET_ID = "erdos:183:astra-fidelity"
ERDOS_264_TARGET_ID = "erdos:264:parts-i-proof-repair"
ERDOS_203_TARGET_ID = "erdos:203:finite-cover"
ERDOS_203_CHORDAL_TARGET_ID = "erdos:203:chordal-obstruction"
ERDOS_730_TARGET_ID = "erdos:730:external-proof-boundary"
VERIFIER_PROFILE = "erdos-1056-k15-bounded-replay-v1"
FIDELITY_VERIFIER_PROFILE = "erdos-183-astra-fidelity-review-v1"
ERDOS_264_VERIFIER_PROFILE = "erdos-264-parts-i-native-lean-v1"
ERDOS_203_VERIFIER_PROFILE = "erdos-203-exact-affine-cover-v1"
ERDOS_203_CHORDAL_VERIFIER_PROFILE = "erdos-203-chordal-obstruction-v1"
ERDOS_730_VERIFIER_PROFILE = "erdos-730-external-proof-boundary-v1"
FIDELITY_EXECUTION_CONTRACT_PATHS = {
    "producer_profile": "execution/erdos-183-astra-fidelity/producer-profile.v1.json",
    "verifier_capsule": "execution/erdos-183-astra-fidelity/reviewer-capsule.v1.json",
    "result_contract": "execution/erdos-183-astra-fidelity/result-contract.v1.json",
}
ERDOS_1056_EXECUTION_CONTRACT_PATHS = {
    "producer_profile": "execution/erdos-1056/10430801-10431000/producer-profile.v1.json",
    "verifier_capsule": "execution/erdos-1056/verifier/v1/linux-arm64/verifier",
    "result_contract": "execution/erdos-1056/10430801-10431000/result-contract.v1.json",
}
ERDOS_1056_VERIFIER_SOURCE_PATH = "execution/erdos-1056/verifier/v1/verifier.cpp"
ERDOS_264_EXECUTION_CONTRACT_PATHS = {
    "producer_profile": "execution/erdos-264-proof-repair/producer-profile.v1.json",
    "verifier_capsule": "execution/erdos-264-proof-repair/verifier-capsule.v1.json",
    "result_contract": "execution/erdos-264-proof-repair/result-contract.v1.json",
}
ERDOS_203_EXECUTION_CONTRACT_PATHS = {
    "producer_profile": "execution/erdos-203-cover/producer-profile.v1.json",
    "verifier_capsule": "execution/erdos-203-cover/verifier-capsule.v1.json",
    "result_contract": "execution/erdos-203-cover/result-contract.v1.json",
}
ERDOS_203_CHORDAL_EXECUTION_CONTRACT_PATHS = {
    "producer_profile": "execution/erdos-203-chordal/producer-profile.v1.json",
    "verifier_capsule": "execution/erdos-203-chordal/verifier-capsule.v1.json",
    "result_contract": "execution/erdos-203-chordal/result-contract.v1.json",
}
ERDOS_730_EXECUTION_CONTRACT_PATHS = {
    "producer_profile": "execution/erdos-730-proof-boundary/producer-profile.v1.json",
    "verifier_capsule": "execution/erdos-730-proof-boundary/verifier-capsule.v1.json",
    "result_contract": "execution/erdos-730-proof-boundary/result-contract.v1.json",
}
ERDOS_264_VERIFIER_SOURCE_PATH = "execution/erdos-264-proof-repair/verify.py"
ERDOS_264_ARTIFACT_PATH = "artifacts/erdos264-parts-i-proof-repair/264.lean"
ERDOS_203_VERIFIER_SOURCE_PATH = "execution/erdos-203-cover/verify.py"
ERDOS_203_ARTIFACT_PATH = "artifacts/erdos203-cover-certificate.v1.json"
ERDOS_203_CHORDAL_PRODUCER_PATH = "execution/erdos-203-chordal/produce.py"
ERDOS_203_CHORDAL_VERIFIER_SOURCE_PATH = "execution/erdos-203-chordal/verify.py"
ERDOS_203_CHORDAL_PREREGISTRATION_PATH = (
    "execution/erdos-203-chordal/preregistration.v1.json"
)
ERDOS_203_CHORDAL_BASE_VERIFIER_PATH = (
    "execution/erdos-203-cover/verify_two_complex_obstruction.py"
)
ERDOS_203_CHORDAL_BASE_ARTIFACT_PATH = (
    "artifacts/analyses/erdos203-two-complex-obstruction.v1.json"
)
ERDOS_203_CHORDAL_ARTIFACT_PATH = (
    "artifacts/analyses/erdos203-chordal-obstruction.v1.json"
)
ERDOS_730_VERIFIER_SOURCE_PATH = "execution/erdos-730-proof-boundary/verify.py"
ERDOS_730_ARTIFACT_PATH = "artifacts/fidelity/erdos-730-proof-boundary.v1.json"
ERDOS_730_ACCEPTED_CLAIM = {
    "claim_id": "vcl_8ef85fca44b8d9105e8c28b9ba702accd9365c4ff23d87466bf2b64853921345",
    "claim_root": "sha256:5c95f42b35f52f5bb018a846555b99ae94dd02d768f76250aa40d4a299959f41",
}
ERDOS_264_CORRECTION_CLAIM = {
    "claim_id": "vcl_5a7df5408c6b11aa52745af2ce1203db3b39cb9a9404c27309f4ee490ffb1386",
    "claim_root": "sha256:4d3f546331886ba10891c1ceb46267993d41b99ed746a19b74d91ccb9448b16e",
}
ARTIFACT_PATH = "artifacts/erdos1056-k15-range-10430801-10431000.txt"
ALLOWED_OUTPUTS = [
    {"type": "text/plain", "path": ARTIFACT_PATH},
]
TARGET_BASE = {
    "id": TARGET_ID,
    "title": "Erdős 1056",
    "presence": "open",
    "rank": 3,
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
ERDOS_264_TARGET_BASE = {
    "id": ERDOS_264_TARGET_ID,
    "title": "Repair the published Erdős 264 part i proof",
    "presence": "open",
    "rank": 1,
    "labels": [
        "correction-inheritance",
        "erdos",
        "formal-proof",
        "lean",
        "machine-checkable",
    ],
    "why": (
        "The accepted source correction changes bounded perturbations from "
        "natural-valued to integer-valued. The retained public Lean proof is "
        "therefore evidence for the predecessor definition, not the corrected one."
    ),
    "objective": (
        "Repair Erdos264.erdos_264.parts.i in the exact pinned Formal "
        "Conjectures source and pass the native Lean verifier without changing "
        "the theorem signature or any unrelated source bytes."
    ),
    "packet": {
        "path": "targets/erdos-264-parts-i-proof-repair.json",
        "schema": "erdos-frontier.correction-inheritance-work.v1",
    },
}
ERDOS_203_TARGET_BASE = {
    "id": ERDOS_203_TARGET_ID,
    "title": "Solve Erdős 203 with a finite two-dimensional cover",
    "presence": "open",
    "rank": 2,
    "labels": [
        "covering-systems",
        "erdos",
        "finite-witness",
        "machine-checkable",
        "open-problem",
    ],
    "why": (
        "A finite exact cover would resolve the retained existential problem "
        "affirmatively. The prior campaign produced a corrected exact lattice "
        "kernel, a viable prime pool, and an explicit structural next route."
    ),
    "objective": (
        "Find one exact finite two-dimensional covering system, pass the "
        "independent affine-lattice verifier, and derive the canonical CRT witness."
    ),
    "packet": {
        "path": "targets/erdos-203-finite-cover.json",
        "schema": "erdos-frontier.finite-cover-work.v1",
    },
}
ERDOS_203_CHORDAL_TARGET_BASE = {
    "id": ERDOS_203_CHORDAL_TARGET_ID,
    "title": "Qualify the Erdős 203 chordal obstruction",
    "presence": "open",
    "rank": 1,
    "labels": [
        "bounded-obstruction",
        "covering-systems",
        "erdos",
        "machine-checkable",
        "post-exploratory",
    ],
    "why": (
        "The exact rooted 306-tile obstruction admits a one-tile chordal "
        "extension: tile 19 attaches over the mandatory triangle 31, 47, 71 "
        "and leaves a positive exact alternating-mass gap."
    ),
    "objective": (
        "Freeze and independently verify the exact 307-tile bounded exclusion, "
        "including the full base replay, tetrahedral intersection indices, "
        "omitted-prime boundary, and explicit nonclaims."
    ),
    "packet": {
        "path": "targets/erdos-203-chordal-obstruction.json",
        "schema": "erdos-frontier.chordal-obstruction-work.v1",
    },
}
ERDOS_730_TARGET_BASE = {
    "id": ERDOS_730_TARGET_ID,
    "title": "Transfer the complete Erdős 730 solution",
    "presence": "open",
    "rank": 2,
    "labels": [
        "erdos",
        "external-proof",
        "formal-proof",
        "lean",
        "source-equivalence",
    ],
    "why": (
        "The pinned external source contains a complete kernel-checked proof of "
        "the stronger positive-density consecutive-pair theorem. Its exact "
        "equivalence and Lean 4.29.1 to 4.27.0 transfer boundary have not yet "
        "been reviewed by this Frontier."
    ),
    "objective": (
        "Verify source equivalence against Erdos730.erdos_730, then prepare "
        "either an explicit external-proof boundary or a native Formal "
        "Conjectures bridge for a separate human Decision."
    ),
    "packet": {
        "path": "targets/erdos-730-external-proof-boundary.json",
        "schema": "erdos-frontier.external-proof-boundary-work.v1",
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
        != {"first": 10430801, "inclusive": True, "last": 10431000}
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
        != {"first": 10430801, "inclusive": True, "last": 10431000}
        or (result_contract.get("artifact") or {}).get("path") != ARTIFACT_PATH
        or (result_contract.get("verifier") or {}).get("witness_minimum_multiplicity")
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
    packet = json.loads((root / FIDELITY_PACKET_PATH.relative_to(ROOT)).read_text())
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
        if (
            value.get("authority") != "non_authoritative"
            or value.get("target") != FIDELITY_TARGET_ID
        ):
            raise ValueError(
                f"Erdős 183 {name} crosses its Target or authority boundary"
            )
        paths.append(path)
    return sorted(paths)


def erdos_264_execution_input_paths(root: pathlib.Path = ROOT) -> list[str]:
    packet_path = root / ERDOS_264_PACKET_PATH.relative_to(ROOT)
    packet = json.loads(packet_path.read_text())
    if packet_path.read_bytes() != canonical_bytes(packet) + b"\n":
        raise ValueError("Erdős 264 packet must be canonical JSON")
    contracts = packet.get("execution_contracts")
    if not isinstance(contracts, dict) or set(contracts) != set(
        ERDOS_264_EXECUTION_CONTRACT_PATHS
    ):
        raise ValueError("Erdős 264 execution contract set differs")
    paths = []
    values = {}
    for name, expected_path in ERDOS_264_EXECUTION_CONTRACT_PATHS.items():
        path = rooted_file(root, contracts.get(name), f"Erdős 264 {name}")
        if path != expected_path:
            raise ValueError(f"Erdős 264 {name} path differs")
        contract_path = root / path
        value = json.loads(contract_path.read_text())
        if contract_path.read_bytes() != canonical_bytes(value) + b"\n":
            raise ValueError(f"Erdős 264 {name} must be canonical JSON")
        if (
            value.get("authority") != "non_authoritative"
            or value.get("target") != ERDOS_264_TARGET_ID
            or "worker" in value
            or "model" in value
            or "budgets" in value
        ):
            raise ValueError(f"Erdős 264 {name} crosses its Target boundary")
        paths.append(path)
        values[name] = value
    verifier = values["verifier_capsule"]
    implementation = verifier.get("implementation") or {}
    verifier_source = root / ERDOS_264_VERIFIER_SOURCE_PATH
    verifier_bytes = verifier_source.read_bytes()
    if implementation != {
        "path": ERDOS_264_VERIFIER_SOURCE_PATH,
        "sha256": sha256_root(verifier_bytes),
        "size": len(verifier_bytes),
    }:
        raise ValueError("Erdős 264 verifier implementation root differs")
    return sorted({*paths, ERDOS_264_VERIFIER_SOURCE_PATH})


def erdos_203_execution_input_paths(root: pathlib.Path = ROOT) -> list[str]:
    packet_path = root / ERDOS_203_PACKET_PATH.relative_to(ROOT)
    packet = json.loads(packet_path.read_text())
    if packet_path.read_bytes() != canonical_bytes(packet) + b"\n":
        raise ValueError("Erdős 203 packet must be canonical JSON")
    contracts = packet.get("execution_contracts")
    if not isinstance(contracts, dict) or set(contracts) != set(
        ERDOS_203_EXECUTION_CONTRACT_PATHS
    ):
        raise ValueError("Erdős 203 execution contract set differs")
    paths = []
    values = {}
    for name, expected_path in ERDOS_203_EXECUTION_CONTRACT_PATHS.items():
        path = rooted_file(root, contracts.get(name), f"Erdős 203 {name}")
        if path != expected_path:
            raise ValueError(f"Erdős 203 {name} path differs")
        contract_path = root / path
        value = json.loads(contract_path.read_text())
        if contract_path.read_bytes() != canonical_bytes(value) + b"\n":
            raise ValueError(f"Erdős 203 {name} must be canonical JSON")
        if (
            value.get("authority") != "non_authoritative"
            or value.get("target") != ERDOS_203_TARGET_ID
        ):
            raise ValueError(f"Erdős 203 {name} crosses its Target boundary")
        paths.append(path)
        values[name] = value
    verifier = values["verifier_capsule"]
    implementation = verifier.get("implementation") or {}
    verifier_source = root / ERDOS_203_VERIFIER_SOURCE_PATH
    verifier_bytes = verifier_source.read_bytes()
    if implementation != {
        "path": ERDOS_203_VERIFIER_SOURCE_PATH,
        "sha256": sha256_root(verifier_bytes),
        "size": len(verifier_bytes),
    }:
        raise ValueError("Erdős 203 verifier implementation root differs")
    return sorted({*paths, ERDOS_203_VERIFIER_SOURCE_PATH})


def erdos_203_chordal_execution_input_paths(
    root: pathlib.Path = ROOT,
) -> list[str]:
    packet_path = root / ERDOS_203_CHORDAL_PACKET_PATH.relative_to(ROOT)
    packet = json.loads(packet_path.read_text())
    if packet_path.read_bytes() != canonical_bytes(packet) + b"\n":
        raise ValueError("Erdős 203 chordal packet must be canonical JSON")
    contracts = packet.get("execution_contracts")
    if not isinstance(contracts, dict) or set(contracts) != set(
        ERDOS_203_CHORDAL_EXECUTION_CONTRACT_PATHS
    ):
        raise ValueError("Erdős 203 chordal execution contract set differs")
    paths = []
    values = {}
    for name, expected_path in ERDOS_203_CHORDAL_EXECUTION_CONTRACT_PATHS.items():
        path = rooted_file(root, contracts.get(name), f"Erdős 203 chordal {name}")
        if path != expected_path:
            raise ValueError(f"Erdős 203 chordal {name} path differs")
        contract_path = root / path
        value = json.loads(contract_path.read_text())
        if contract_path.read_bytes() != canonical_bytes(value) + b"\n":
            raise ValueError(f"Erdős 203 chordal {name} must be canonical JSON")
        if (
            value.get("authority") != "non_authoritative"
            or value.get("target") != ERDOS_203_CHORDAL_TARGET_ID
        ):
            raise ValueError(
                f"Erdős 203 chordal {name} crosses its Target boundary"
            )
        paths.append(path)
        values[name] = value

    verifier_source = root / ERDOS_203_CHORDAL_VERIFIER_SOURCE_PATH
    verifier_bytes = verifier_source.read_bytes()
    verifier = values["verifier_capsule"]
    if verifier.get("implementation") != {
        "path": ERDOS_203_CHORDAL_VERIFIER_SOURCE_PATH,
        "sha256": sha256_root(verifier_bytes),
        "size": len(verifier_bytes),
    }:
        raise ValueError("Erdős 203 chordal verifier implementation root differs")

    preregistration = rooted_file(
        root,
        packet.get("preregistration"),
        "Erdős 203 chordal preregistration",
    )
    if preregistration != ERDOS_203_CHORDAL_PREREGISTRATION_PATH:
        raise ValueError("Erdős 203 chordal preregistration path differs")
    preregistration_value = json.loads((root / preregistration).read_text())
    if (
        preregistration_value.get("target") != ERDOS_203_CHORDAL_TARGET_ID
        or preregistration_value.get("claim_credit") is not False
    ):
        raise ValueError("Erdős 203 chordal preregistration boundary differs")

    producer_bytes = (root / ERDOS_203_CHORDAL_PRODUCER_PATH).read_bytes()
    if (preregistration_value.get("method") or {}).get("producer") != {
        "path": ERDOS_203_CHORDAL_PRODUCER_PATH,
        "sha256": sha256_root(producer_bytes),
        "size": len(producer_bytes),
    }:
        raise ValueError("Erdős 203 chordal producer root differs")
    if (preregistration_value.get("method") or {}).get("checker") != {
        "path": ERDOS_203_CHORDAL_VERIFIER_SOURCE_PATH,
        "sha256": sha256_root(verifier_bytes),
        "size": len(verifier_bytes),
    }:
        raise ValueError("Erdős 203 chordal checker root differs")

    base_evidence = packet.get("base_evidence") or {}
    base_verifier = rooted_file(
        root,
        base_evidence.get("checker"),
        "Erdős 203 chordal base verifier",
    )
    base_artifact = rooted_file(
        root,
        base_evidence.get("artifact"),
        "Erdős 203 chordal base artifact",
    )
    if base_verifier != ERDOS_203_CHORDAL_BASE_VERIFIER_PATH:
        raise ValueError("Erdős 203 chordal base verifier path differs")
    if base_artifact != ERDOS_203_CHORDAL_BASE_ARTIFACT_PATH:
        raise ValueError("Erdős 203 chordal base artifact path differs")
    return sorted(
        {
            *paths,
            preregistration,
            ERDOS_203_CHORDAL_PRODUCER_PATH,
            ERDOS_203_CHORDAL_VERIFIER_SOURCE_PATH,
            base_verifier,
            base_artifact,
        }
    )


def erdos_730_execution_input_paths(root: pathlib.Path = ROOT) -> list[str]:
    packet_path = root / ERDOS_730_PACKET_PATH.relative_to(ROOT)
    packet = json.loads(packet_path.read_text())
    if packet_path.read_bytes() != canonical_bytes(packet) + b"\n":
        raise ValueError("Erdős 730 packet must be canonical JSON")
    contracts = packet.get("execution_contracts")
    if not isinstance(contracts, dict) or set(contracts) != set(
        ERDOS_730_EXECUTION_CONTRACT_PATHS
    ):
        raise ValueError("Erdős 730 execution contract set differs")
    paths = []
    values = {}
    for name, expected_path in ERDOS_730_EXECUTION_CONTRACT_PATHS.items():
        path = rooted_file(root, contracts.get(name), f"Erdős 730 {name}")
        if path != expected_path:
            raise ValueError(f"Erdős 730 {name} path differs")
        contract_path = root / path
        value = json.loads(contract_path.read_text())
        if contract_path.read_bytes() != canonical_bytes(value) + b"\n":
            raise ValueError(f"Erdős 730 {name} must be canonical JSON")
        if (
            value.get("authority") != "non_authoritative"
            or value.get("target") != ERDOS_730_TARGET_ID
            or "worker" in value
            or "model" in value
            or "budgets" in value
        ):
            raise ValueError(f"Erdős 730 {name} crosses its Target boundary")
        paths.append(path)
        values[name] = value
    verifier = values["verifier_capsule"]
    implementation = verifier.get("implementation") or {}
    verifier_source = root / ERDOS_730_VERIFIER_SOURCE_PATH
    verifier_bytes = verifier_source.read_bytes()
    if implementation != {
        "path": ERDOS_730_VERIFIER_SOURCE_PATH,
        "sha256": sha256_root(verifier_bytes),
        "size": len(verifier_bytes),
    }:
        raise ValueError("Erdős 730 verifier implementation root differs")
    return sorted({*paths, ERDOS_730_VERIFIER_SOURCE_PATH})


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
        *erdos_203_execution_input_paths(root),
        *erdos_203_chordal_execution_input_paths(root),
        *erdos_264_execution_input_paths(root),
        *erdos_730_execution_input_paths(root),
        ERDOS_730_HANDOFF_PATH.relative_to(ROOT).as_posix(),
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
    packets.append(ERDOS_203_PACKET_PATH.relative_to(ROOT).as_posix())
    packets.append(ERDOS_203_CHORDAL_PACKET_PATH.relative_to(ROOT).as_posix())
    packets.append(ERDOS_264_PACKET_PATH.relative_to(ROOT).as_posix())
    packets.append(ERDOS_730_PACKET_PATH.relative_to(ROOT).as_posix())
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
            f"evidence, the latest accepted bounded k=15 range ending at "
            f"{accepted['last']}"
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
    if packet.get("schema") != TARGET_BASE["packet"]["schema"]:
        raise ValueError("Erdős 1056 packet schema differs from the Target")
    if packet.get("frontier_id") != repository.get("frontier_id"):
        raise ValueError("Erdős 1056 packet targets another Frontier")
    if (packet.get("target") or {}).get("id") != TARGET_BASE["id"]:
        raise ValueError("Erdős 1056 packet targets another work item")
    repository_locator = packet.get("repository") or {}
    if set(repository_locator) != {"commit", "tree"}:
        raise ValueError(
            "Erdős 1056 packet must bind its source commit and tree, not a mutable "
            "repository root"
        )

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
        or "repository" in packet
        or (packet.get("target") or {}).get("id") != FIDELITY_TARGET_ID
        or (packet.get("target") or {}).get("problem") != 183
        or packet.get("verifier_profile") != FIDELITY_VERIFIER_PROFILE
    ):
        raise ValueError(
            "Erdős 183 fidelity packet crosses its Target or authority boundary"
        )
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
        raise ValueError(
            "Erdős 183 fidelity packet does not bind the exact OpenAI release"
        )
    if (
        status.get("repository") != "https://github.com/teorth/erdosproblems"
        or status.get("commit") != "8138974387d9030542daabe67faaa33eff9356f8"
        or status.get("tree") != "7ed44c260d7eb63a067cf5a16afdb645d494ef06"
        or status.get("sha256")
        != "sha256:a4358d57b591fc92c75981c160a11f43a561de6b5e8478d8f9629511759a9213"
    ):
        raise ValueError(
            "Erdős 183 fidelity packet does not bind the exact source observation"
        )
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


def validate_erdos_264_packet(root: pathlib.Path = ROOT) -> None:
    repository = json.loads((root / REPOSITORY_PATH.relative_to(ROOT)).read_text())
    packet = json.loads((root / ERDOS_264_PACKET_PATH.relative_to(ROOT)).read_text())
    source = packet.get("source") or {}
    prerequisite = packet.get("prerequisite") or {}
    target = packet.get("target") or {}
    outputs = packet.get("allowed_outputs")
    if (
        packet.get("schema") != ERDOS_264_TARGET_BASE["packet"]["schema"]
        or packet.get("frontier_id") != repository.get("frontier_id")
        or packet.get("authority") != "non_authoritative"
        or target.get("id") != ERDOS_264_TARGET_ID
        or target.get("problem") != 264
        or target.get("state") != "available_after_accepted_correction"
        or packet.get("verifier_profile") != ERDOS_264_VERIFIER_PROFILE
        or prerequisite.get("accepted_claim") != ERDOS_264_CORRECTION_CLAIM
        or outputs
        != [
            {
                "kind": "lean-source-repair",
                "media_type": "text/x-lean",
                "path": ERDOS_264_ARTIFACT_PATH,
            }
        ]
    ):
        raise ValueError("Erdős 264 packet crosses its Target or authority boundary")
    if source != {
        "repository": "https://github.com/google-deepmind/formal-conjectures.git",
        "commit": "e6d6b867dc85eec2f88bc47496b4314c623f9f92",
        "tree": "1e24e996a9fee330dc885ec2b314f60bfd508985",
        "path": "FormalConjectures/ErdosProblems/264.lean",
        "sha256": "sha256:c59caaa2524e3edd52944e63f5d9bb0614f1bc36d7fb8a0fec7029c14c266b46",
        "lean_toolchain": "leanprover/lean4:v4.27.0",
        "mathlib_commit": "a3a10db0e9d66acbebf76c5e6a135066525ac900",
        "declaration": "Erdos264.erdos_264.parts.i",
    }:
        raise ValueError("Erdős 264 packet does not bind the exact source")
    requirement = packet.get("verification_requirement")
    if not isinstance(requirement, str) or not requirement:
        raise ValueError("Erdős 264 packet lacks an exact verification requirement")
    erdos_264_execution_input_paths(root)


def validate_erdos_203_packet(root: pathlib.Path = ROOT) -> None:
    repository = json.loads((root / REPOSITORY_PATH.relative_to(ROOT)).read_text())
    packet = json.loads((root / ERDOS_203_PACKET_PATH.relative_to(ROOT)).read_text())
    target = packet.get("target") or {}
    formal_statement = packet.get("formal_statement") or {}
    source = ((packet.get("prior_work") or {}).get("source")) or {}
    correction = ((packet.get("prior_work") or {}).get("correction")) or {}
    problem_claim = packet.get("problem_claim") or {}
    accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
        if row.get("standing") == "accepted"
    }
    if (
        packet.get("schema") != ERDOS_203_TARGET_BASE["packet"]["schema"]
        or packet.get("frontier_id") != repository.get("frontier_id")
        or packet.get("authority") != "non_authoritative"
        or "repository" in packet
        or target.get("id") != ERDOS_203_TARGET_ID
        or target.get("problem") != 203
        or target.get("state") != "open"
        or packet.get("verifier_profile") != ERDOS_203_VERIFIER_PROFILE
        or packet.get("allowed_outputs")
        != [
            {
                "kind": "finite-cover-certificate",
                "media_type": "application/json",
                "path": ERDOS_203_ARTIFACT_PATH,
                "schema": "erdos-frontier.erdos-203-cover-certificate.v1",
            }
        ]
    ):
        raise ValueError("Erdős 203 packet crosses its Target or authority boundary")
    if formal_statement != {
        "repository": "https://github.com/google-deepmind/formal-conjectures.git",
        "commit": "50ee83fa7dc31c99c03c83f04be90b7fea37d314",
        "tree": "af55637ba163e4381b00cd0fca0f59158c6998f3",
        "path": "FormalConjectures/ErdosProblems/203.lean",
        "blob_sha1": "2bc9f5fb212533aeb94c2328dbb5b53987a9f9ec",
        "sha256": "sha256:dfd0eb1bf073a27ad74a398acb7c2986b73be9cf72e6dc6ed9fc4618c6538cfb",
        "declaration": "Erdos203.erdos_203",
        "status": "merged_upstream",
    }:
        raise ValueError("Erdős 203 packet does not bind the merged formal statement")
    if (
        problem_claim
        != {
            "claim_id": "vcl_8131cdf07c70fe688bf18bc6ca274d6bff43eaeed116430351685e925bf4a796",
            "claim_root": "sha256:998616dbbf3a0f704bbab20504a15fe1e4ab92fe60524ab6ad8798eab3435e06",
        }
        or accepted.get(problem_claim.get("claim_id"))
        != problem_claim.get("claim_root")
    ):
        raise ValueError("Erdős 203 packet does not bind its accepted problem Claim")
    if (
        source.get("repository")
        != "https://github.com/williamjblair/lean-proofs.git"
        or source.get("commit") != "94fde841ea6ad90437bd66a91953bfeba13dba0f"
        or source.get("tree") != "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a"
        or correction.get("commit")
        != "ccb4105e6b89837c226512ba87a79084cd01cfe5"
        or not isinstance(correction.get("reason"), str)
        or not correction["reason"]
        or len(correction.get("retracted", [])) != 2
    ):
        raise ValueError("Erdős 203 packet does not bind the corrected campaign source")
    expected_files = {
        "docs/plans/erdos203-campaign.md": (7567, "sha256:3f8b9e037a71ef8fea97d534aa5c3e62bfd8138c3511cc46e51ed5125ffb95af"),
        "compute203/lattice.py": (4104, "sha256:2579bfb9f9b1213abeb5e8e33e8c25e2434dc4822f5b2ce247bbbc38a2705b2f"),
        "compute203/tree_builder.py": (8335, "sha256:8bcf760578104a8a1b318174e6b084cc7909b02ed5c8290f64f73db79e1099e9"),
        "compute203/fleet5040.py": (2170, "sha256:df26cbd844ebb42146535b9c06614c0a7e1ef77dbcee9ac76050d7d2f48df13e"),
        "compute203/fleetfull.py": (119, "sha256:ddbeb895b8c828b46645f2e5980940eabf8923ad844d137862f1b09a5ee0c38f"),
        "compute203/point_solver.py": (2935, "sha256:59511ea34bbd719778c37b5295aa95db7b84a49d2eca385eee30c598b391f4ec"),
        "compute203/pool_merged.json": (4104, "sha256:9a8f179bf6ab509c53144ac679acd8ffe42e66588b1516b0ca3a9f45e18395b3"),
    }
    observed_files = {
        row.get("path"): (row.get("size"), row.get("sha256"))
        for row in source.get("files", [])
        if isinstance(row, dict)
    }
    if observed_files != expected_files:
        raise ValueError("Erdős 203 packet source-file roots differ")
    expected_retracted = {
        "compute203/best_full2.json": (547, "sha256:b937be3510ae1f7839e9fd316360c9bf41a9f456bd9f350ea2b85268622b712d"),
        "compute203/stall_cells.json": (2326472, "sha256:72dbc754aecf79c6698b20394f00868c52133013dfa06b9c12f69aaeb708d7ad"),
    }
    observed_retracted = {
        row.get("path"): (row.get("size"), row.get("sha256"))
        for row in correction.get("retracted", [])
        if isinstance(row, dict)
    }
    if observed_retracted != expected_retracted:
        raise ValueError("Erdős 203 retracted evidence roots differ")
    requirement = packet.get("verification_requirement")
    if not isinstance(requirement, str) or not requirement:
        raise ValueError("Erdős 203 packet lacks an exact verification requirement")
    erdos_203_execution_input_paths(root)


def validate_erdos_203_chordal_packet(root: pathlib.Path = ROOT) -> None:
    repository = json.loads((root / REPOSITORY_PATH.relative_to(ROOT)).read_text())
    packet = json.loads(
        (root / ERDOS_203_CHORDAL_PACKET_PATH.relative_to(ROOT)).read_text()
    )
    target = packet.get("target") or {}
    formal_statement = packet.get("formal_statement") or {}
    source = packet.get("source") or {}
    problem_claim = packet.get("problem_claim") or {}
    accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
        if row.get("standing") == "accepted"
    }
    if (
        packet.get("schema") != ERDOS_203_CHORDAL_TARGET_BASE["packet"]["schema"]
        or packet.get("frontier_id") != repository.get("frontier_id")
        or packet.get("authority") != "non_authoritative"
        or "repository" in packet
        or target.get("id") != ERDOS_203_CHORDAL_TARGET_ID
        or target.get("problem") != 203
        or target.get("state") != "open"
        or packet.get("verifier_profile") != ERDOS_203_CHORDAL_VERIFIER_PROFILE
        or packet.get("allowed_outputs")
        != [
            {
                "kind": "chordal-complex-obstruction",
                "media_type": "application/json",
                "path": ERDOS_203_CHORDAL_ARTIFACT_PATH,
                "schema": "erdos-frontier.erdos-203-chordal-obstruction.v1",
            }
        ]
    ):
        raise ValueError(
            "Erdős 203 chordal packet crosses its Target or authority boundary"
        )
    if formal_statement != {
        "repository": "https://github.com/google-deepmind/formal-conjectures.git",
        "commit": "50ee83fa7dc31c99c03c83f04be90b7fea37d314",
        "tree": "af55637ba163e4381b00cd0fca0f59158c6998f3",
        "path": "FormalConjectures/ErdosProblems/203.lean",
        "blob_sha1": "2bc9f5fb212533aeb94c2328dbb5b53987a9f9ec",
        "sha256": "sha256:dfd0eb1bf073a27ad74a398acb7c2986b73be9cf72e6dc6ed9fc4618c6538cfb",
        "declaration": "Erdos203.erdos_203",
        "status": "merged_upstream",
    }:
        raise ValueError(
            "Erdős 203 chordal packet does not bind the merged formal statement"
        )
    if (
        problem_claim
        != {
            "claim_id": "vcl_8131cdf07c70fe688bf18bc6ca274d6bff43eaeed116430351685e925bf4a796",
            "claim_root": "sha256:998616dbbf3a0f704bbab20504a15fe1e4ab92fe60524ab6ad8798eab3435e06",
        }
        or accepted.get(problem_claim.get("claim_id"))
        != problem_claim.get("claim_root")
    ):
        raise ValueError(
            "Erdős 203 chordal packet does not bind its accepted problem Claim"
        )
    if source != {
        "repository": "https://github.com/williamjblair/lean-proofs.git",
        "commit": "94fde841ea6ad90437bd66a91953bfeba13dba0f",
        "tree": "5b8a3013fbc08edb9e04086aeb4aa9f5c9a09a9a",
        "pool_root": "sha256:9a8f179bf6ab509c53144ac679acd8ffe42e66588b1516b0ca3a9f45e18395b3",
    }:
        raise ValueError("Erdős 203 chordal packet source identity differs")
    base = packet.get("base_evidence") or {}
    if (
        base.get("accepted_state_change") != "none"
        or base.get("result")
        != "The exact rooted 306-tile mandatory pair/triple 2-tree has a positive contradiction gap and excludes that bounded family."
    ):
        raise ValueError("Erdős 203 chordal base-evidence boundary differs")
    requirement = packet.get("verification_requirement")
    if not isinstance(requirement, str) or not requirement:
        raise ValueError(
            "Erdős 203 chordal packet lacks an exact verification requirement"
        )
    erdos_203_chordal_execution_input_paths(root)


def validate_erdos_730_packet(root: pathlib.Path = ROOT) -> None:
    repository = json.loads((root / REPOSITORY_PATH.relative_to(ROOT)).read_text())
    packet = json.loads((root / ERDOS_730_PACKET_PATH.relative_to(ROOT)).read_text())
    target = packet.get("target") or {}
    external = packet.get("external_proof") or {}
    formal = packet.get("formal_statement") or {}
    standing = packet.get("current_frontier_standing") or {}
    next_obligation = packet.get("next_obligation") or {}
    accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
        if row.get("standing") == "accepted"
    }
    if (
        packet.get("schema") != ERDOS_730_TARGET_BASE["packet"]["schema"]
        or packet.get("frontier_id") != repository.get("frontier_id")
        or packet.get("authority") != "non_authoritative"
        or target.get("id") != ERDOS_730_TARGET_ID
        or target.get("problem") != 730
        or target.get("state")
        != "complete_external_solution_pending_frontier_transfer"
        or packet.get("verifier_profile") != ERDOS_730_VERIFIER_PROFILE
        or packet.get("allowed_outputs")
        != [
            {
                "kind": "source-equivalence-report",
                "media_type": "application/json",
                "path": ERDOS_730_ARTIFACT_PATH,
                "schema": "erdos-frontier.erdos-730-boundary-report.v1",
            }
        ]
    ):
        raise ValueError("Erdős 730 packet crosses its Target or authority boundary")
    if external != {
        "repository": "https://github.com/williamjblair/lean-proofs.git",
        "snapshot_commit": "4f915a323443bfb1709a6805a013812016dca88a",
        "snapshot_tree": "a0aaa84d22ed8fab7c2788bced29472953cc1752",
        "terminal_solve_commit": "8c85623069b3923afe418876d06459dbc4d24a51",
        "terminal_path": "ErdosProblems/Erdos730FullDensityTheorem.lean",
        "terminal_sha256": "sha256:7f341400b34cd3241007dce7365aa84c367546ffda0acf164d7a32e003f98ba0",
        "terminal_declaration": "Erdos730.FullDensityTheorem.pairSet_infinite",
        "lean_toolchain": "leanprover/lean4:v4.29.1",
        "mathlib_commit": "5e932f97dd25535344f80f9dd8da3aab83df0fe6",
        "erdos_730_module_count": 74,
        "status": "complete_kernel_checked_solution_in_source_repository",
        "strength": (
            "The terminal theorem proves a stronger positive-density "
            "consecutive-pair result, not merely one witness or a partial reduction."
        ),
        "conclusion": (
            "The explicit family has lower density strictly greater than "
            "107/2500, hence there are infinitely many consecutive pairs whose "
            "central binomial coefficients have identical prime support."
        ),
    }:
        raise ValueError("Erdős 730 packet does not bind the complete external proof")
    if formal != {
        "repository": "https://github.com/google-deepmind/formal-conjectures.git",
        "commit": "50ee83fa7dc31c99c03c83f04be90b7fea37d314",
        "tree": "af55637ba163e4381b00cd0fca0f59158c6998f3",
        "path": "FormalConjectures/ErdosProblems/730.lean",
        "blob_sha1": "d37ca5fc59eb615e7406dff2c7881e1600d15d58",
        "sha256": "sha256:c8e532aa2916312501375df4e30ca4770fdeb3968d39622dda5cdfc5f9fa26e7",
        "declaration": "Erdos730.erdos_730",
        "lean_toolchain": "leanprover/lean4:v4.27.0",
        "mathlib_commit": "a3a10db0e9d66acbebf76c5e6a135066525ac900",
        "status": "merged_upstream_open_statement",
    }:
        raise ValueError("Erdős 730 packet does not bind Formal Conjectures")
    claims = [standing.get("problem_claim"), standing.get("formal_source_claim")]
    if any(
        not isinstance(claim, dict)
        or accepted.get(claim.get("claim_id")) != claim.get("claim_root")
        for claim in claims
    ):
        raise ValueError("Erdős 730 packet does not bind current accepted source Claims")
    if (
        standing.get("standing")
        != "open until a separate authorized human Decision"
        or "Lean 4.29.1" not in next_obligation.get("first", "")
        or "Lean 4.27.0" not in next_obligation.get("after_equivalence", "")
        or "authorized human Decision" not in next_obligation.get(
            "prohibited_shortcut", ""
        )
    ):
        raise ValueError("Erdős 730 packet weakens its transfer boundary")
    nonclaims = " ".join(packet.get("nonclaims", []))
    if any(
        required not in nonclaims
        for required in ("accepted", "Vela caused", "Lean 4.29.1", "Standing")
    ):
        raise ValueError("Erdős 730 packet omits a required nonclaim")
    erdos_730_execution_input_paths(root)


def erdos_730_work_complete(root: pathlib.Path = ROOT) -> bool:
    repository = json.loads((root / REPOSITORY_PATH.relative_to(ROOT)).read_text())
    accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
        if row.get("standing") == "accepted"
    }
    return (
        accepted.get(ERDOS_730_ACCEPTED_CLAIM["claim_id"])
        == ERDOS_730_ACCEPTED_CLAIM["claim_root"]
    )


def validate_erdos_730_handoff(root: pathlib.Path = ROOT) -> None:
    handoff_path = root / ERDOS_730_HANDOFF_PATH.relative_to(ROOT)
    handoff = json.loads(handoff_path.read_text())
    repository = json.loads((root / REPOSITORY_PATH.relative_to(ROOT)).read_text())
    completed = handoff.get("completed_target") or {}
    accepted = handoff.get("accepted_boundary") or {}
    decision = handoff.get("decision") or {}
    obligations = handoff.get("next_obligations") or {}
    if (
        handoff.get("schema") != "erdos-frontier.next-obligation-handoff.v1"
        or handoff.get("frontier_id") != repository.get("frontier_id")
        or handoff.get("authority") != "non_authoritative"
        or completed.get("id") != ERDOS_730_TARGET_ID
        or completed.get("state") != "accepted_local_external_proof_boundary"
        or accepted != ERDOS_730_ACCEPTED_CLAIM
        or decision.get("proposal_id") != "vpr_c9554694d438c594"
        or decision.get("decision_event_id") != "vev_0ab843df6ad373ec"
        or decision.get("repository_before")
        != "sha256:db438141c7780f1122ee11daf7a57390a275dfc03744131ad991e9a65bbd39b9"
        or decision.get("repository_after")
        != "sha256:821cf0d94778f647305107943572f4916a6cf63fe5ea12506a471fabc07b7474"
        or obligations.get("primary")
        != "Build Erdős 730 as the second non-authoritative Result Dossier case."
        or obligations.get("scientific_followup")
        != "Obtain external mathematical review or build an explicit Lean 4.27.0 bridge as a separate future campaign."
    ):
        raise ValueError("Erdős 730 handoff weakens or misstates the accepted boundary")
    current_accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
        if row.get("standing") == "accepted"
    }
    if current_accepted.get(accepted.get("claim_id")) != accepted.get("claim_root"):
        raise ValueError("Erdős 730 handoff does not bind current accepted Standing")
    evidence = handoff.get("evidence") or {}
    expected_paths = {
        "producer_report": ERDOS_730_ARTIFACT_PATH,
        "semantic_review": "execution/erdos-730-proof-boundary/independent-semantic-review.v1.json",
        "verification": "records/verifications/sha256/fb28b83d8a03cbd75e28ed9ce6c0e8a5169fea9acce6bfe6e7f03142f85b64ac.json",
        "decision_event": ".vela/authority/events/vev_0ab843df6ad373ec.json",
        "standing_event": ".vela/authority/events/vev_50a750b12f5dbc53.json",
        "authority_record": ".vela/authority/records/var_6fc6421006cbab2e.dsse.json",
    }
    if set(evidence) != set(expected_paths):
        raise ValueError("Erdős 730 handoff evidence set differs")
    for name, expected_path in expected_paths.items():
        observed_path = rooted_file(
            root, evidence.get(name), f"Erdős 730 handoff {name}"
        )
        if observed_path != expected_path:
            raise ValueError(f"Erdős 730 handoff {name} path differs")
    nonclaims = " ".join(handoff.get("nonclaims", []))
    if any(
        required not in nonclaims
        for required in (
            "global solution",
            "external mathematical review",
            "novelty",
            "Lean 4.27.0 port",
            "Vela caused",
        )
    ):
        raise ValueError("Erdős 730 handoff omits a required nonclaim")


def current_records(
    repository: dict[str, Any], kind: str, root: pathlib.Path = ROOT
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
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


def erdos_264_correction_accepted(root: pathlib.Path = ROOT) -> bool:
    repository = json.loads((root / REPOSITORY_PATH.relative_to(ROOT)).read_text())
    accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
        if row.get("standing") == "accepted"
    }
    return (
        accepted.get(ERDOS_264_CORRECTION_CLAIM["claim_id"])
        == ERDOS_264_CORRECTION_CLAIM["claim_root"]
    )


def erdos_264_proof_repair_complete(root: pathlib.Path = ROOT) -> bool:
    """Close the repair offer only after an exact passing Verification.

    Producer completion prevents duplicate proof work while the resulting
    Proposal remains a separate human Decision. Verification never changes or
    implies Standing here.
    """

    repository = json.loads((root / REPOSITORY_PATH.relative_to(ROOT)).read_text())
    packet = json.loads((root / ERDOS_264_PACKET_PATH.relative_to(ROOT)).read_text())
    artifact_path = root / ERDOS_264_ARTIFACT_PATH
    if not artifact_path.is_file() or artifact_path.is_symlink():
        return False
    artifact_root = sha256_root(artifact_path.read_bytes())
    artifact_id = artifact_root.removeprefix("sha256:")
    contracts = packet.get("execution_contracts") or {}
    expected_binding = {
        "schema": "vela.execution-binding.v1",
        "packet_root": sha256_root(
            (root / ERDOS_264_PACKET_PATH.relative_to(ROOT)).read_bytes()
        ),
        "profile_root": (contracts.get("producer_profile") or {}).get("sha256"),
        "verifier_capsule_root": (contracts.get("verifier_capsule") or {}).get(
            "sha256"
        ),
        "result_contract_root": (contracts.get("result_contract") or {}).get("sha256"),
    }
    pending = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("pending_claims", [])
    }
    accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
    }
    for submission_row, submission in current_records(repository, "submissions", root):
        submission_requirements = submission.get("verification_requirements")
        if (
            submission.get("schema") != "vela.submission.v1"
            or submission.get("execution_binding") != expected_binding
            or submission.get("artifacts")
            != [
                {
                    "kind": "lean-source-repair",
                    "path": ERDOS_264_ARTIFACT_PATH,
                    "digest": artifact_root,
                }
            ]
            or not isinstance(submission_requirements, list)
            or len(submission_requirements) != 1
            or not isinstance(submission_requirements[0], str)
            or not submission_requirements[0]
        ):
            continue
        for proposal_row, proposal in current_records(repository, "proposals", root):
            package = proposal.get("producer_package") or {}
            subject = proposal.get("subject") or {}
            claim_id = subject.get("id")
            claim_root = subject.get("root")
            if (
                proposal.get("schema") != "vela.proposal.v1"
                or package.get("id") != submission.get("submission_id")
                or package.get("root") != submission_row.get("root")
                or package.get("path") != submission_row.get("path")
                or (
                    pending.get(claim_id) != claim_root
                    and accepted.get(claim_id) != claim_root
                )
            ):
                continue
            for _, verification in current_records(repository, "verifications", root):
                verification_subject = verification.get("subject") or {}
                method = verification.get("method") or {}
                scope = verification.get("scope") or {}
                if (
                    verification.get("schema") == "vela.verification-record.v1"
                    and verification.get("outcome") == "pass"
                    and verification_subject.get("claim_id") == claim_id
                    and verification_subject.get("proposal_id")
                    == proposal_row.get("id")
                    and verification_subject.get("submission_id")
                    == submission.get("submission_id")
                    and verification_subject.get("submission_root")
                    == submission_row.get("root")
                    and set(verification_subject.get("artifact_ids", []))
                    == {artifact_id}
                    and method.get("profile") == ERDOS_264_VERIFIER_PROFILE
                    and method.get("implementation")
                    == ERDOS_264_EXECUTION_CONTRACT_PATHS["verifier_capsule"]
                    and method.get("environment_root")
                    == expected_binding["verifier_capsule_root"]
                    and isinstance(scope.get("property"), str)
                    and bool(scope["property"])
                ):
                    return True
    return False


def erdos_264_target_available(root: pathlib.Path = ROOT) -> bool:
    return erdos_264_correction_accepted(root) and not erdos_264_proof_repair_complete(
        root
    )


def erdos_203_chordal_work_complete(root: pathlib.Path = ROOT) -> bool:
    """Close the bounded qualification offer only after exact Verification."""

    repository = json.loads((root / REPOSITORY_PATH.relative_to(ROOT)).read_text())
    packet_path = root / ERDOS_203_CHORDAL_PACKET_PATH.relative_to(ROOT)
    packet = json.loads(packet_path.read_text())
    artifact_path = root / ERDOS_203_CHORDAL_ARTIFACT_PATH
    if not artifact_path.is_file() or artifact_path.is_symlink():
        return False
    artifact_root = sha256_root(artifact_path.read_bytes())
    artifact_id = artifact_root.removeprefix("sha256:")
    contracts = packet.get("execution_contracts") or {}
    expected_binding = {
        "schema": "vela.execution-binding.v1",
        "packet_root": sha256_root(packet_path.read_bytes()),
        "profile_root": (contracts.get("producer_profile") or {}).get("sha256"),
        "verifier_capsule_root": (contracts.get("verifier_capsule") or {}).get(
            "sha256"
        ),
        "result_contract_root": (contracts.get("result_contract") or {}).get(
            "sha256"
        ),
    }
    pending = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("pending_claims", [])
    }
    accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
    }
    for submission_row, submission in current_records(repository, "submissions", root):
        requirements = submission.get("verification_requirements")
        if (
            submission.get("schema") != "vela.submission.v1"
            or submission.get("execution_binding") != expected_binding
            or submission.get("artifacts")
            != [
                {
                    "kind": "chordal-complex-obstruction",
                    "path": ERDOS_203_CHORDAL_ARTIFACT_PATH,
                    "digest": artifact_root,
                }
            ]
            or not isinstance(requirements, list)
            or len(requirements) != 1
            or not isinstance(requirements[0], str)
            or not requirements[0]
        ):
            continue
        for proposal_row, proposal in current_records(repository, "proposals", root):
            package = proposal.get("producer_package") or {}
            subject = proposal.get("subject") or {}
            claim_id = subject.get("id")
            claim_root = subject.get("root")
            if (
                proposal.get("schema") != "vela.proposal.v1"
                or package.get("id") != submission.get("submission_id")
                or package.get("root") != submission_row.get("root")
                or package.get("path") != submission_row.get("path")
                or (
                    pending.get(claim_id) != claim_root
                    and accepted.get(claim_id) != claim_root
                )
            ):
                continue
            for _, verification in current_records(repository, "verifications", root):
                subject = verification.get("subject") or {}
                method = verification.get("method") or {}
                scope = verification.get("scope") or {}
                if (
                    verification.get("schema") == "vela.verification-record.v1"
                    and verification.get("outcome") == "pass"
                    and subject.get("claim_id") == claim_id
                    and subject.get("proposal_id") == proposal_row.get("id")
                    and subject.get("submission_id")
                    == submission.get("submission_id")
                    and subject.get("submission_root") == submission_row.get("root")
                    and set(subject.get("artifact_ids", [])) == {artifact_id}
                    and method.get("profile")
                    == ERDOS_203_CHORDAL_VERIFIER_PROFILE
                    and method.get("implementation")
                    == ERDOS_203_CHORDAL_EXECUTION_CONTRACT_PATHS[
                        "verifier_capsule"
                    ]
                    and method.get("environment_root")
                    == expected_binding["verifier_capsule_root"]
                    and isinstance(scope.get("property"), str)
                    and bool(scope["property"])
                ):
                    return True
    return False


def erdos_1056_work_complete(root: pathlib.Path = ROOT) -> bool:
    """Return whether the exact live range already has passing evidence.

    Producer work closes at scoped Verification, not at human acceptance. This
    prevents `vela next` from offering duplicate computation while the
    consequence-bearing Proposal remains in the Decision Inbox.
    """

    repository = json.loads((root / REPOSITORY_PATH.relative_to(ROOT)).read_text())
    packet_path = root / PACKET_PATH.relative_to(ROOT)
    packet_bytes = packet_path.read_bytes()
    packet = json.loads(packet_bytes)
    packet_root = sha256_root(packet_bytes)
    contracts = packet.get("execution_contracts") or {}
    expected_binding = {
        "schema": "vela.execution-binding.v1",
        "packet_root": packet_root,
        "profile_root": (contracts.get("producer_profile") or {}).get("sha256"),
        "verifier_capsule_root": (contracts.get("verifier_capsule") or {}).get(
            "sha256"
        ),
        "result_contract_root": (contracts.get("result_contract") or {}).get("sha256"),
    }
    target_range = (packet.get("target") or {}).get("next_bounded_range") or {}
    artifact_path = ((packet.get("allowed_outputs") or [{}])[0]).get("path")
    if (
        set(contracts) != {"producer_profile", "verifier_capsule", "result_contract"}
        or not isinstance(artifact_path, str)
        or not isinstance(target_range.get("first"), int)
        or not isinstance(target_range.get("last"), int)
        or target_range.get("inclusive") is not True
    ):
        return False

    artifact_file = root / artifact_path
    if not artifact_file.is_file() or artifact_file.is_symlink():
        return False
    artifact_root = sha256_root(artifact_file.read_bytes())
    artifact_id = artifact_root.removeprefix("sha256:")
    pending = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("pending_claims", [])
    }
    accepted = {
        row.get("claim_id"): row.get("claim_root")
        for row in repository.get("accepted_claims", [])
    }

    for submission_row, submission in current_records(repository, "submissions", root):
        artifacts = submission.get("artifacts")
        requirements = submission.get("verification_requirements")
        if (
            submission.get("schema") != "vela.submission.v1"
            or submission.get("execution_binding") != expected_binding
            or not isinstance(artifacts, list)
            or len(artifacts) != 1
            or artifacts[0]
            != {
                "kind": "bounded-search",
                "path": artifact_path,
                "digest": artifact_root,
            }
            or not isinstance(requirements, list)
            or len(requirements) != 1
            or not isinstance(requirements[0], str)
            or not requirements[0]
        ):
            continue
        assertion = ((submission.get("claim") or {}).get("assertion")) or ""
        try:
            validate_search_artifact(
                artifact_file,
                assertion,
                target_range["first"],
                target_range["last"],
            )
        except TargetClosureError:
            continue

        for proposal_row, proposal in current_records(repository, "proposals", root):
            package = proposal.get("producer_package") or {}
            subject = proposal.get("subject") or {}
            claim_id = subject.get("id")
            claim_root = subject.get("root")
            if (
                proposal.get("schema") != "vela.proposal.v1"
                or package.get("id") != submission.get("submission_id")
                or package.get("root") != submission_row.get("root")
                or package.get("path") != submission_row.get("path")
                or (
                    pending.get(claim_id) != claim_root
                    and accepted.get(claim_id) != claim_root
                )
            ):
                continue
            for _, verification in current_records(repository, "verifications", root):
                verification_subject = verification.get("subject") or {}
                method = verification.get("method") or {}
                scope = verification.get("scope") or {}
                if (
                    verification.get("schema") == "vela.verification-record.v1"
                    and verification.get("outcome") == "pass"
                    and verification_subject.get("claim_id") == claim_id
                    and verification_subject.get("proposal_id")
                    == proposal_row.get("id")
                    and verification_subject.get("submission_id")
                    == submission.get("submission_id")
                    and verification_subject.get("submission_root")
                    == submission_row.get("root")
                    and set(verification_subject.get("artifact_ids", []))
                    == {artifact_id}
                    and method.get("profile") == packet.get("verifier_profile")
                    and scope.get("property") == requirements[0]
                ):
                    return True
    return False


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

    contracts = packet.get("execution_contracts") or {}
    expected_binding = {
        "profile_root": (contracts.get("producer_profile") or {}).get("sha256"),
        "verifier_capsule_root": (contracts.get("verifier_capsule") or {}).get(
            "sha256"
        ),
        "result_contract_root": (contracts.get("result_contract") or {}).get("sha256"),
    }
    review_requirement = review.get("verification")
    submissions = []
    for row, submission in current_records(repository, "submissions", root):
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
            and all(
                binding.get(key) == value for key, value in expected_binding.items()
            )
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
        for proposal_row, proposal in current_records(repository, "proposals", root):
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
            for verification_row, verification in current_records(
                repository, "verifications", root
            ):
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
                        "environment_root": expected_binding["verifier_capsule_root"],
                    }
                    and scope.get("property") == submission_requirement
                ):
                    return True
    return False


def index() -> dict[str, Any]:
    validate_erdos_203_packet()
    validate_erdos_203_chordal_packet()
    validate_erdos_264_packet()
    validate_erdos_730_packet()
    validate_erdos_730_handoff()
    erdos_1056_complete = erdos_1056_work_complete()
    validation = None
    if not erdos_1056_complete:
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
    targets_with_packets = []
    if not erdos_203_chordal_work_complete():
        targets_with_packets.append(
            (ERDOS_203_CHORDAL_TARGET_BASE.copy(), ERDOS_203_CHORDAL_PACKET_PATH)
        )
    if erdos_264_target_available():
        targets_with_packets.append(
            (ERDOS_264_TARGET_BASE.copy(), ERDOS_264_PACKET_PATH)
        )
    if not erdos_730_work_complete():
        targets_with_packets.append(
            (ERDOS_730_TARGET_BASE.copy(), ERDOS_730_PACKET_PATH)
        )
    targets_with_packets.append((ERDOS_203_TARGET_BASE.copy(), ERDOS_203_PACKET_PATH))
    if not erdos_1056_complete:
        assert validation is not None
        targets_with_packets.append((target_from_validation(validation), PACKET_PATH))
    if not fidelity_complete:
        targets_with_packets.insert(
            0, (FIDELITY_TARGET_BASE.copy(), FIDELITY_PACKET_PATH)
        )
    targets_with_packets.sort(
        key=lambda item: (item[0]["rank"], item[0]["id"])
    )
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
            print(
                "targets.json is stale; run scripts/build_target_index.py",
                file=sys.stderr,
            )
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

#!/usr/bin/env python3
"""Build the root-pinned Erdős work inventory and its two graph planes.

This reducer never scans a live sibling checkout. Its public inputs are the
versioned registry, source locks, the committed legacy ledger, and the
materialized Erdős frontier. Producer repositories remain evidence stores;
their Git pins and selected-path digests are carried into every projection.

Usage:
    python scripts/build_work_inventory.py          # write generated outputs
    python scripts/build_work_inventory.py --check  # CI: validate + byte-compare
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter, defaultdict
from typing import Any, Iterable

import yaml

HERE = pathlib.Path(__file__).resolve().parent.parent
REGISTRY_PATH = HERE / "sources" / "work-registry.yaml"
MIGRATION_PATH = HERE / "sources" / "attempt-migration.yaml"
IMPORT_MAP_PATH = HERE / "sources" / "attempt-import-map.yaml"
LOCK_PATH = HERE / "sources.lock.json"
LEDGER_PATH = HERE / "attack" / "attempt-ledger.v2.json"
STATUS_PATH = HERE / "site" / "status.json"
VERDICTS_PATH = HERE / "site" / "verdicts.json"
FRONTIER_PATH = HERE / "frontier.json"
VELA_LOCK_PATH = HERE / "vela.lock"
DEVELOPED_PROPOSALS_PATH = HERE / "review" / "developed-campaign-proposals.v1.yaml"
RECOVERED_ATTEMPTS_PATH = HERE / "sources" / "recovered-attempts.yaml"
RECOVERED_LEDGER_PATH = HERE / "sources" / "recovered-attempt-ledger.v2.json"
RECOVERED_IMPORT_MAP_PATH = HERE / "sources" / "recovered-attempt-import-map.yaml"
FORMAL_CONJECTURES_ACTIVITY_PATH = (
    HERE / "sources" / "formal-conjectures-activity.yaml"
)
WORK_INDEX_PATH = HERE / "site" / "work-index.json"
TARGET_INDEX_PATH = HERE / "targets.json"
TARGET_INDEX_CANDIDATE_PATH = HERE / ".vela" / "tmp" / "target-index-candidate.json"
PROBLEM_DIR = HERE / "site" / "problems"
WORK_INVENTORY_PATH = HERE / "graph" / "work-inventory.json"
CLAIM_GRAPH_PATH = HERE / "graph" / "claim-graph.json"
SITE_CLAIM_GRAPH_PATH = HERE / "site" / "claim-graph.json"
FRONTIER_MAP_PATH = HERE / "graph" / "frontier-map.json"
MIGRATION_REPORT_PATH = HERE / "graph" / "attempt-migration-report.json"
RECONCILIATION_PATH = HERE / "graph" / "frontier-reconciliation.json"

VALID_ROLES = {
    "authority",
    "federated_theorem_authority",
    "artifact_producer",
    "integration_producer",
    "external_reference",
    "deprecated_duplicate",
    "consumer",
}
VAT_RE = re.compile(r"^vat_[0-9a-f]{16}$")
ABSOLUTE_PATH_RE = re.compile(r"(?:/Users/[^/]+|/home/[^/]+)(?:/[^\s\"']*)?")
# The candidate context separately binds the exact event, scientific-state,
# proposal, and repository roots. Migration-derived frontier.json and vela.lock
# are therefore deliberately excluded so a byte-compatible materialization
# cannot make every sealed target stale.
TARGET_INDEX_INPUT_PATHS = sorted([
    "attack/attempt-ledger.v2.json",
    "review/developed-campaign-proposals.v1.yaml",
    "scripts/build_work_inventory.py",
    "site/status.json",
    "site/verdicts.json",
    "sources.lock.json",
    "sources/attempt-import-map.yaml",
    "sources/attempt-migration.yaml",
    "sources/formal-conjectures-activity.yaml",
    "sources/recovered-attempt-import-map.yaml",
    "sources/recovered-attempt-ledger.v2.json",
    "sources/recovered-attempts.yaml",
    "sources/work-registry.yaml",
])

ATTEMPT_ACTIVITY = {
    "verified_witness": "computation",
    "prefix_scip_decision_bound": "computation",
    "published_theorem_lean_bridge": "theorem",
    "known_result": "theorem",
    "research_audit": "audit",
}
TRUST_RANK = {
    "declared": 0,
    "recorded": 1,
    "signed": 2,
    "machine_reproduced": 3,
    "lean_attested": 4,
}


class InventoryError(ValueError):
    """A pinned input violates the inventory contract."""


def _load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text())


def _load_yaml(path: pathlib.Path) -> Any:
    return yaml.safe_load(path.read_text())


def _json_bytes(value: Any, *, compact: bool = False) -> bytes:
    if compact:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"))
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    return (text + "\n").encode()


def _yaml_bytes(value: Any) -> bytes:
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True).encode()


def _sha256(path: pathlib.Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()

def _git_head() -> str:
    result = subprocess.run(
        ["git", "-C", str(HERE), "rev-parse", "HEAD^{commit}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _short(text: str, limit: int = 180) -> str:
    clean = " ".join(sanitize_public_text(text).split())
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def sanitize_public_text(value: Any) -> Any:
    """Remove workstation-specific locators from otherwise public evidence."""
    if not isinstance(value, str):
        return value

    def replacement(match: re.Match[str]) -> str:
        raw = match.group(0)
        personal = re.search(r"/personal/([^/]+)(?:/(.*))?", raw)
        if personal:
            repo, rest = personal.group(1), personal.group(2)
            return f"repo:{repo}/{rest}" if rest else f"repo:{repo}"
        return "[local-path-redacted]"

    return ABSOLUTE_PATH_RE.sub(replacement, value)


def validate_problem_id(problem: Any, *, allow_zero: bool = False) -> int:
    if isinstance(problem, bool) or not isinstance(problem, int):
        raise InventoryError(f"problem identity must be an integer, got {problem!r}")
    low = 0 if allow_zero else 1
    if not low <= problem <= 1217:
        raise InventoryError(f"invalid Erdős problem identity: {problem}")
    return problem


def validate_repository_roles(repositories: dict[str, dict], locks: dict | None = None) -> None:
    authorities = [key for key, spec in repositories.items()
                   if spec.get("role") == "authority"]
    if authorities != ["erdos_frontier"]:
        raise InventoryError(f"exactly erdos_frontier must be authority, got {authorities}")

    remotes: dict[str, list[str]] = defaultdict(list)
    frontier_ids: dict[str, list[str]] = defaultdict(list)
    for key, spec in repositories.items():
        role = spec.get("role")
        if role not in VALID_ROLES:
            raise InventoryError(f"{key}: unknown repository role {role!r}")
        remote = spec.get("remote")
        if not isinstance(remote, str) or not remote.startswith("https://github.com/"):
            raise InventoryError(f"{key}: repository remote must be a public GitHub URL")
        remotes[remote].append(key)
        if spec.get("frontier_id"):
            frontier_ids[spec["frontier_id"]].append(key)
        if role == "deprecated_duplicate":
            duplicate_of = spec.get("duplicate_of")
            if duplicate_of not in repositories:
                raise InventoryError(f"{key}: deprecated duplicate needs a known duplicate_of")
        if spec.get("public_output") and spec.get("lock_key") and locks is not None:
            lock_key = spec["lock_key"]
            source = (locks.get("work_sources") or {}).get(lock_key)
            source = source or (locks.get("sources") or {}).get(lock_key)
            if not source:
                raise InventoryError(f"{key}: public source lock {lock_key!r} is missing")
            digest = source.get("sha256", "")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                raise InventoryError(f"{key}: public source has no valid sha256 digest")
            commit = source.get("commit")
            if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
                raise InventoryError(f"{key}: public source needs an exact 40-hex commit")
            if spec.get("commit") and commit != spec["commit"]:
                raise InventoryError(f"{key}: registry and source-lock commits differ")
            remote_repo = remote.removeprefix("https://github.com/").removesuffix(".git")
            if source.get("repo") != remote_repo:
                raise InventoryError(
                    f"{key}: source-lock repo {source.get('repo')!r} differs from {remote_repo!r}"
                )
            selected = spec.get("selected_paths") or []
            locked_paths = source.get("paths") or ([source["path"]] if source.get("path") else [])
            if not selected or selected != locked_paths:
                raise InventoryError(
                    f"{key}: selected paths {selected!r} differ from lock paths {locked_paths!r}"
                )

    for remote, keys in remotes.items():
        if len(keys) < 2:
            continue
        roots = [key for key in keys if not (
            repositories[key].get("duplicate_of") or repositories[key].get("component_of")
        )]
        if len(roots) != 1:
            raise InventoryError(
                f"remote {remote} needs one canonical role entry; unqualified entries: {roots}"
            )
    for frontier_id, keys in frontier_ids.items():
        canonical = [k for k in keys if repositories[k]["role"] != "deprecated_duplicate"]
        if len(canonical) != 1:
            raise InventoryError(
                f"frontier id {frontier_id} needs exactly one non-deprecated authority: {keys}"
            )


def _selector_matches(record: dict, selector: dict) -> bool:
    if "attempt_ids" in selector:
        return record.get("attempt_id") in set(selector["attempt_ids"])
    problem = record.get("problem")
    return (isinstance(problem, int)
            and selector.get("problem_min", problem) <= problem
            and problem <= selector.get("problem_max", problem))


def classify_attempt_routes(records: list[dict], migration: dict) -> dict[str, dict]:
    routes = migration.get("routes") or []
    by_id: dict[str, dict] = {}
    counts: Counter[str] = Counter()
    for record in records:
        attempt_id = record.get("attempt_id")
        if not isinstance(attempt_id, str) or not VAT_RE.fullmatch(attempt_id):
            raise InventoryError(f"invalid attempt id {attempt_id!r}")
        matches = [route for route in routes if _selector_matches(record, route["selector"])]
        if len(matches) != 1:
            raise InventoryError(
                f"attempt {attempt_id} must match exactly one migration route, got "
                f"{[route['id'] for route in matches]}"
            )
        route = matches[0]
        by_id[attempt_id] = route
        counts[route["id"]] += 1

    if len(by_id) != migration["expected"]["records"]:
        raise InventoryError(f"migration accounts for {len(by_id)} records, expected 219")
    for route in routes:
        if counts[route["id"]] != route["expected_records"]:
            raise InventoryError(
                f"route {route['id']} has {counts[route['id']]} records, "
                f"expected {route['expected_records']}"
            )
    return by_id


def _build_cli_import_map(records: list[dict], routes: dict[str, dict]) -> dict:
    mappings = []
    for record in records:
        attempt_id = record["attempt_id"]
        route = routes[attempt_id]
        route_id = route["id"]
        if route_id == "numbered_erdos":
            mappings.append({
                "attempt_id": attempt_id,
                "action": "import",
                "expected_attempt_id": attempt_id,
            })
        elif route_id == "erdos_campaign_audit":
            mappings.append({
                "attempt_id": attempt_id,
                "action": "import",
                "problem": 0,
                "frontier": "vfr_0a25edabc16db143",
                "expected_attempt_id": "vat_0364e7ec199e4b9b",
                "source_id_rule": "legacy_explicit_problem_zero",
                "reason": "Normalize the corpus-level audit to the canonical Erdős frontier.",
            })
        elif route_id == "oeis_sidon":
            target = f"oeis:A{record['problem']}"
            mappings.append({
                "attempt_id": attempt_id,
                "action": "exclude",
                "reason": "OEIS/Sidon work belongs to its non-Erdős frontier.",
                "target": target,
            })
        elif route_id == "vela_platform":
            mappings.append({
                "attempt_id": attempt_id,
                "action": "exclude",
                "reason": "Vela substrate research is platform activity, not Erdős state.",
                "target": "vela-platform-activity",
            })
        else:  # pragma: no cover - guarded by the checked registry
            raise InventoryError(f"unsupported migration route {route_id}")
    return {
        "schema": "vela.attempt-import-map.v1",
        "exhaustive": True,
        "mappings": mappings,
    }


def _migration_report(records: list[dict], routes: dict[str, dict]) -> dict:
    rows = []
    for record in records:
        route = routes[record["attempt_id"]]
        route_id = route["id"]
        if route_id == "numbered_erdos":
            identity = f"erdos:{record['problem']}"
            target_id = record["attempt_id"]
            preserved = True
        elif route_id == "erdos_campaign_audit":
            identity = "erdos:0"
            target_id = "vat_0364e7ec199e4b9b"
            preserved = False
        elif route_id == "oeis_sidon":
            identity = f"oeis:A{record['problem']}"
            target_id = None
            preserved = False
        else:
            identity = "vela-platform:activity"
            target_id = None
            preserved = False
        rows.append({
            "source_attempt_id": record["attempt_id"],
            "source_claim_digest": record["claim_digest"],
            "source_problem": record["problem"],
            "route": route_id,
            "action": route["action"],
            "target_identity": identity,
            "target_attempt_id": target_id,
            "id_preserved": preserved,
        })
    route_counts = Counter(row["route"] for row in rows)
    return {
        "schema": "erdos-frontier.attempt-migration-report.v1",
        "source": {
            "path": "attack/attempt-ledger.v2.json",
            "sha256": _sha256(LEDGER_PATH),
        },
        "identity_semantics": {
            "erdos:0": (
                "Campaign-level Erdős activity. Attempt.problem uses protocol default zero, "
                "so canonical JSON may omit the field; an omitted problem decodes as 0 and must "
                "not be interpreted as an unknown problem."
            ),
        },
        "summary": {
            "records": len(rows),
            "imported": sum(row["target_attempt_id"] is not None for row in rows),
            "excluded": sum(row["target_attempt_id"] is None for row in rows),
            "ids_preserved": sum(row["id_preserved"] for row in rows),
            "ids_changed": sum(row["target_attempt_id"] is not None and not row["id_preserved"]
                               for row in rows),
            "by_route": dict(sorted(route_counts.items())),
        },
        "records": rows,
    }


def _developed_draft_records(pack: dict, frontier: dict) -> list[dict]:
    """Join the review pack to its materialized, still-pending Vela proposals.

    These records belong to the proposal/activity plane. Exact assertion text is
    the join key because it is part of the proposal payload and the review pack
    intentionally preserves the source claim verbatim.
    """
    if pack.get("schema") != "erdos-frontier.developed-campaign-proposals.v1":
        raise InventoryError("developed-campaign proposal pack has an unknown schema")
    if (pack.get("frontier") or {}).get("frontier_id") != frontier.get("frontier_id"):
        raise InventoryError("developed-campaign proposal pack targets another frontier")

    pending_by_assertion: dict[str, list[dict]] = defaultdict(list)
    for proposal in frontier.get("proposals") or []:
        if proposal.get("status") != "pending_review":
            continue
        finding = (proposal.get("payload") or {}).get("finding") or {}
        assertion = str((finding.get("assertion") or {}).get("text") or "")
        if assertion:
            pending_by_assertion[assertion].append(proposal)

    source = pack["source_repository"]
    remote = source["remote"].removesuffix(".git")
    records = []
    for campaign in pack.get("campaigns") or []:
        problem = validate_problem_id(campaign.get("problem"))
        candidates = [(False, campaign["claim"])] + [
            (True, residual) for residual in campaign.get("residuals") or []
        ]
        for is_residual, spec in candidates:
            if spec.get("disposition") != "propose":
                continue
            assertion = spec.get("assertion")
            matches = pending_by_assertion.get(assertion, [])
            if len(matches) != 1:
                raise InventoryError(
                    f"draft {spec.get('proposal_key')} must match one pending proposal; "
                    f"found {len(matches)}"
                )
            proposal = matches[0]
            finding = proposal["payload"]["finding"]
            artifact = spec.get("artifact")
            if artifact:
                artifact = {
                    **artifact,
                    "repository": source["remote"].removeprefix(
                        "https://github.com/"
                    ).removesuffix(".git"),
                    "repository_key": "lean_proofs",
                    "commit": source["commit"],
                    "locator": (
                        f"{remote}/blob/{source['commit']}/{artifact['path']}"
                        f"#{artifact['declaration']}"
                    ),
                }
            records.append({
                "id": proposal["id"],
                "target_finding_id": (proposal.get("target") or {}).get("id"),
                "problem": problem,
                "proposal_key": spec["proposal_key"],
                "assertion": assertion,
                "assertion_type": (finding.get("assertion") or {}).get("type") or "unknown",
                "conditions": (finding.get("conditions") or {}).get("text") or "",
                "actor": (proposal.get("actor") or {}).get("id") or "unknown",
                "status": proposal["status"],
                "activity": spec["activity"],
                "mathematical_scope": spec["mathematical_scope"],
                "trust": spec["trust"],
                "lifecycle": spec["lifecycle"],
                "machine_status": (spec.get("machine_status") or {}).get("status"),
                "machine_evidence": spec.get("machine_status") or {},
                "statement_fidelity": (
                    spec.get("statement_fidelity") or {}
                ).get("status"),
                "is_residual": is_residual,
                "artifact": artifact,
                "review_obligations": campaign.get("review_obligations") or [],
            })
    if len(records) != 12:
        raise InventoryError(f"expected 12 developed-campaign drafts, found {len(records)}")
    if len({record["id"] for record in records}) != len(records):
        raise InventoryError("a pending proposal was matched by more than one review record")
    return sorted(records, key=lambda record: (record["problem"], record["id"]))


def _repository_key(repository: str, registry: dict) -> str:
    normalized = repository.removeprefix("https://github.com/").removesuffix(".git")
    slug = normalized.rsplit("/", 1)[-1]
    aliases = {repository, normalized, slug, slug.replace("-", "_")}
    for key, spec in registry["repositories"].items():
        remote = spec["remote"].removeprefix("https://github.com/").removesuffix(".git")
        remote_slug = remote.rsplit("/", 1)[-1]
        if key in aliases or remote in aliases or remote_slug in aliases:
            if key == "vela_nested_formal_conjectures":
                continue
            return key
    if slug == "vela":
        return "vela_history"
    raise InventoryError(f"recovered record names unknown repository {repository!r}")


def _normalize_recovered_records(pack: dict, registry: dict, frontier: dict) -> list[dict]:
    """Turn pinned Git-history evidence into one operational record per problem.

    A signed attempt deposited from the recovery ledger wins over the recorded
    placeholder. The semantic dedup key is `(problem, sha256(claim)[:16])`, the
    same claim digest carried by the Attempt wire format.
    """
    if pack.get("schema") != "erdos-frontier.recovered-attempts.v1":
        raise InventoryError("recovered-attempt pack has an unknown schema")
    raw_records = pack.get("records") or []
    if len(raw_records) != 31:
        raise InventoryError(f"expected 31 recovered records, found {len(raw_records)}")
    if len({record.get("problem") for record in raw_records}) != len(raw_records):
        raise InventoryError("recovered records must have unique problem identities")

    signed_by_key: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for attempt in frontier.get("attempts") or []:
        problem = attempt.get("problem", 0)
        digest = attempt.get("claim_digest")
        if isinstance(problem, int) and isinstance(digest, str):
            signed_by_key[(problem, digest)].append(attempt)

    normalized = []
    classifications = Counter()
    for raw in raw_records:
        problem = validate_problem_id(raw.get("problem"))
        classification = raw.get("classification")
        if classification not in {"duplicate", "importable_attempt", "deferred_with_reason"}:
            raise InventoryError(
                f"recovered Erdős {problem} has invalid classification {classification!r}"
            )
        classifications[classification] += 1
        claim = raw.get("claim")
        if not isinstance(claim, str) or not claim.strip():
            raise InventoryError(f"recovered Erdős {problem} has no source claim")
        digest = hashlib.sha256(claim.strip().encode()).hexdigest()[:16]
        signed_matches = signed_by_key.get((problem, digest), [])
        if len(signed_matches) > 1:
            raise InventoryError(
                f"recovered Erdős {problem} matches multiple signed attempts by claim digest"
            )
        if classification == "deferred_with_reason" and signed_matches:
            raise InventoryError(f"deferred Erdős {problem} was unexpectedly deposited")

        source = raw.get("source") or {}
        repository_key = _repository_key(str(source.get("repository") or ""), registry)
        if not re.fullmatch(r"[0-9a-f]{40}", str(source.get("commit") or "")):
            raise InventoryError(f"recovered Erdős {problem} has no exact source commit")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(source.get("sha256") or "")):
            raise InventoryError(f"recovered Erdős {problem} has no exact source digest")
        path = str(source.get("path") or "")
        if not path or path.startswith("/") or "/Users/" in path or "/home/" in path:
            raise InventoryError(f"recovered Erdős {problem} has an unsafe source path")

        signed = signed_matches[0] if signed_matches else None
        expected_attempt_id = raw.get("attempt_id")
        duplicate_id = raw.get("duplicate_of_attempt_id")
        if classification == "duplicate":
            if not isinstance(duplicate_id, str) or not VAT_RE.fullmatch(duplicate_id):
                raise InventoryError(f"recovered Erdős {problem} duplicate has no target id")
            record_id = duplicate_id
        elif classification == "importable_attempt":
            if not isinstance(expected_attempt_id, str) or not VAT_RE.fullmatch(
                expected_attempt_id
            ):
                raise InventoryError(
                    f"recovered Erdős {problem} has no stable target attempt id"
                )
            if signed and signed["attempt_id"] != expected_attempt_id:
                raise InventoryError(
                    f"recovered Erdős {problem} signed attempt differs from expected id"
                )
            record_id = expected_attempt_id
        else:
            record_id = f"recovered:{problem}:{digest}"
        evidence_key = raw.get("evidence_key")
        declaration = f"#{source['declaration']}" if source.get("declaration") else ""
        expected_evidence_key = (
            f"source:{source['repository']}@{source['commit']}:{path}"
            f"{declaration}@{source['sha256']}"
        )
        if evidence_key != expected_evidence_key:
            raise InventoryError(f"recovered Erdős {problem} has no evidence key")
        normalized.append({
            **raw,
            "attempt_id": record_id,
            "claim_digest": digest,
            "kind": raw["activity_type"],
            "repository_key": repository_key,
            "source_ref": f"{source['repository']}@{source['commit']}:{path}",
            "source_url": (
                f"{registry['repositories'][repository_key]['remote'].removesuffix('.git')}"
                f"/blob/{source['commit']}/{path}"
                f"{('#' + source['declaration']) if source.get('declaration') else ''}"
            ),
            "signed_attempt": bool(signed),
            "is_attempt": classification == "importable_attempt",
            "provenance": {
                "proposer": (
                    (signed.get("provenance") or {}).get("proposer") if signed else None
                ) or "git-history recovery",
            },
        })
    if classifications != {"importable_attempt": 30, "deferred_with_reason": 1}:
        raise InventoryError(f"unexpected recovered classifications: {dict(classifications)}")
    expected = (
        set(registry["inventory"]["current_artifact_additions"])
        | set(registry["inventory"]["history_only_campaigns"])
    )
    if {record["problem"] for record in normalized} != expected:
        raise InventoryError("recovered records do not exactly cover current plus history additions")
    return sorted(normalized, key=lambda record: record["problem"])


def _validate_recovered_import_bundle(
    recovered_records: list[dict], ledger: dict, import_map: dict, frontier_id: str
) -> None:
    importable = [record for record in recovered_records if record["is_attempt"]]
    expected_ids = {record["attempt_id"] for record in importable}
    if (
        ledger.get("object") != "CanopusAttemptLedger"
        or ledger.get("version") != 2
        or ledger.get("signed") is not False
    ):
        raise InventoryError("recovered attempt ledger has an invalid envelope")
    ledger_records = ledger.get("records") or []
    if len(ledger_records) != 30 or {row.get("attempt_id") for row in ledger_records} != expected_ids:
        raise InventoryError("recovered attempt ledger does not exactly cover 30 imports")
    if (
        import_map.get("schema") != "vela.attempt-import-map.v1"
        or import_map.get("exhaustive") is not True
    ):
        raise InventoryError("recovered import map has an invalid envelope")
    mappings = import_map.get("mappings") or []
    if len(mappings) != 30 or {row.get("attempt_id") for row in mappings} != expected_ids:
        raise InventoryError("recovered import map does not exactly cover 30 imports")
    if any(
        row.get("action") != "import" or row.get("expected_attempt_id") != row.get("attempt_id")
        for row in mappings
    ):
        raise InventoryError("recovered import map must preserve every generated attempt id")

    source_by_id = {record["attempt_id"]: record for record in importable}
    for attempt in ledger_records:
        source = source_by_id[attempt["attempt_id"]]
        if attempt.get("problem") != source["problem"]:
            raise InventoryError(f"{attempt['attempt_id']}: recovered problem identity drift")
        if attempt.get("frontier") != frontier_id:
            raise InventoryError(f"{attempt['attempt_id']}: recovered frontier identity drift")
        if attempt.get("claim") != source["claim"]:
            raise InventoryError(f"{attempt['attempt_id']}: recovered source claim drift")
        if attempt.get("claim_digest") != source["claim_digest"]:
            raise InventoryError(f"{attempt['attempt_id']}: recovered claim digest drift")
        if (attempt.get("method_families") or []) != source.get("method_families"):
            raise InventoryError(f"{attempt['attempt_id']}: recovered method-family drift")
        if (attempt.get("remaining_obligations") or []) != source.get("remaining_obligations"):
            raise InventoryError(f"{attempt['attempt_id']}: recovered obligation drift")
        if (attempt.get("named_obstructions") or []) != source.get("named_obstructions"):
            raise InventoryError(f"{attempt['attempt_id']}: recovered obstruction drift")


def _public_source_locks(registry: dict, locks: dict) -> dict:
    output = {}
    for key, spec in sorted(registry["repositories"].items()):
        if not spec.get("public_output") or not spec.get("lock_key"):
            continue
        lock_key = spec["lock_key"]
        source = (locks.get("work_sources") or {}).get(lock_key)
        source = source or (locks.get("sources") or {}).get(lock_key)
        if not source:
            continue
        output[key] = {
            field: source[field]
            for field in ("repo", "commit", "sha256", "paths", "path", "url")
            if source.get(field) not in (None, "", [])
        }
    return output


def _normalize_formal_conjectures_activity(
    manifest: dict, registry: dict, source_locks: dict
) -> list[dict]:
    """Validate the authored-touch partition against its immutable source pin.

    Formal Conjectures is an integration producer, not a second truth store.
    These records therefore enter only the operational plane.  Keeping the
    manifest as an explicit reducer input prevents a statement or proof-link
    edit from silently becoming mathematical work.
    """
    if manifest.get("schema") != "erdos-frontier.formal-conjectures-activity.v1":
        raise InventoryError("Formal Conjectures activity manifest has an unknown schema")

    repository = registry["repositories"]["formal_conjectures"]
    source = manifest.get("source") or {}
    if source.get("repository") != repository["remote"]:
        raise InventoryError("Formal Conjectures activity remote differs from the registry")
    if source.get("pinned_commit") != repository["commit"]:
        raise InventoryError("Formal Conjectures activity commit differs from the registry")
    if source.get("selected_paths") != repository["selected_paths"]:
        raise InventoryError("Formal Conjectures activity paths differ from the registry")
    if source.get("registry") != "sources/work-registry.yaml":
        raise InventoryError("Formal Conjectures activity has no stable registry locator")
    if source.get("authored_inventory_key") != "inventory.formal_conjectures_authored":
        raise InventoryError("Formal Conjectures activity names the wrong authored inventory")
    if source.get("classification_key") != "inventory.formal_conjectures_classification":
        raise InventoryError("Formal Conjectures activity names the wrong classification")

    source_lock = source_locks.get("formal_conjectures") or {}
    expected_repo = repository["remote"].removeprefix(
        "https://github.com/"
    ).removesuffix(".git")
    if source_lock.get("repo") != expected_repo:
        raise InventoryError("Formal Conjectures activity has no matching repository lock")
    if source_lock.get("commit") != source["pinned_commit"]:
        raise InventoryError("Formal Conjectures activity has no matching commit lock")
    if source_lock.get("paths") != source["selected_paths"]:
        raise InventoryError("Formal Conjectures activity has no matching path lock")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", source_lock.get("sha256", "")):
        raise InventoryError("Formal Conjectures activity has no content digest lock")

    inventory = registry["inventory"]
    expected_partition: dict[int, str] = {}
    for category, problems in inventory["formal_conjectures_classification"].items():
        for problem in problems:
            validate_problem_id(problem)
            if problem in expected_partition:
                raise InventoryError(
                    f"Formal Conjectures problem {problem} has duplicate classifications"
                )
            expected_partition[problem] = category
    if set(expected_partition) != set(inventory["formal_conjectures_authored"]):
        raise InventoryError("Formal Conjectures registry partition is not exhaustive")

    rows = manifest.get("problems") or []
    if len(rows) != 136:
        raise InventoryError(
            f"Formal Conjectures activity has {len(rows)} rows, expected 136"
        )
    normalized = []
    seen: set[int] = set()
    for row in rows:
        problem = validate_problem_id(row.get("problem"))
        if problem in seen:
            raise InventoryError(f"Formal Conjectures activity repeats problem {problem}")
        seen.add(problem)
        category = row.get("category")
        if expected_partition.get(problem) != category:
            raise InventoryError(
                f"Formal Conjectures problem {problem} has category {category!r}, "
                f"expected {expected_partition.get(problem)!r}"
            )
        affects_math = category == "mathematical_proof_work"
        if row.get("affects_mathematical_work_lens") is not affects_math:
            raise InventoryError(
                f"Formal Conjectures problem {problem} has inconsistent lens semantics"
            )
        normalized.append({
            "id": f"activity:fc-{category}:{problem}",
            "problem": problem,
            "category": category,
            "affects_mathematical_work_lens": affects_math,
            "source_commit": source_lock["commit"],
            "source_root": source_lock["sha256"],
            "source_ref": f"sources/formal-conjectures-activity.yaml#problem-{problem}",
        })

    normalized.sort(key=lambda row: row["problem"])
    if [row["problem"] for row in normalized] != sorted(expected_partition):
        raise InventoryError("Formal Conjectures activity does not match the authored baseline")
    counts = dict(sorted(Counter(row["category"] for row in normalized).items()))
    summary = manifest.get("summary") or {}
    if summary.get("authored_problem_count") != len(normalized):
        raise InventoryError("Formal Conjectures activity summary count has drifted")
    if summary.get("category_counts") != counts:
        raise InventoryError("Formal Conjectures activity category counts have drifted")
    policy = manifest.get("policy") or {}
    if policy.get("mathematical_lens_category") != "mathematical_proof_work":
        raise InventoryError("Formal Conjectures activity has an unsafe lens policy")
    return normalized


def _frontier_dependencies(vela_lock: dict, registry: dict) -> list[dict]:
    dependencies = []
    reconciliation = registry["frontier_reconciliation"]
    canonical_key = reconciliation["canonical"]
    canonical_repository = registry["repositories"][canonical_key]
    for dependency in vela_lock.get("dependencies") or []:
        vfr_id = dependency.get("frontier_id")
        snapshot = dependency.get("scientific_state_root")
        commit = dependency.get("git_commit")
        remote = canonical_repository.get("remote")
        locator = (
            f"{remote.removesuffix('.git')}/tree/{commit}"
            if isinstance(remote, str) and isinstance(commit, str)
            else None
        )
        if not re.fullmatch(r"vfr_[0-9a-f]{16}", str(vfr_id or "")):
            raise InventoryError("frontier dependency has no valid frontier id")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(snapshot or "")):
            raise InventoryError(
                f"{vfr_id}: frontier dependency has no scientific-state pin"
            )
        if not isinstance(locator, str) or not locator.startswith("https://"):
            raise InventoryError(f"{vfr_id}: frontier dependency has no stable locator")
        dependencies.append({
            "name": canonical_key.replace("_", "-"),
            "source": "git",
            "frontier_id": vfr_id,
            "snapshot_hash": snapshot,
            "locator": locator,
        })
    expected = reconciliation["frontier_id"]
    if [dependency["frontier_id"] for dependency in dependencies] != [expected]:
        raise InventoryError(
            "vela.lock must pin the standalone formal-conjectures frontier dependency"
        )
    return dependencies


def _normalize_upstream_state(raw: Any) -> str:
    state = str(raw or "open").lower()
    if state.startswith("disproved"):
        return "disproved"
    if state.startswith("proved") or state.startswith("solved"):
        return "proved"
    if state in {"independent", "not provable", "not disprovable"}:
        return "independent"
    return "open"


def _problem_from_finding(finding: dict) -> int | None:
    title = str((finding.get("provenance") or {}).get("title") or "")
    match = re.search(r"(?:^|:)(\d+)$", title)
    if not match:
        text = str((finding.get("assertion") or {}).get("text") or "")
        match = re.search(r"Erd(?:ő|o)s(?: Problem)?\s*#?(\d+)", text, re.I)
    if not match:
        return None
    problem = int(match.group(1))
    return problem if 1 <= problem <= 1217 else None


def _strongest_trust(values: Iterable[str]) -> str:
    return max(values, key=lambda value: TRUST_RANK.get(value, -1), default="declared")


def _attempt_activity(kind: str) -> str:
    if kind in {"attempt", "computation", "theorem", "scout", "audit"}:
        return kind
    return ATTEMPT_ACTIVITY.get(kind, "attempt")


def _source_repositories(problem: int, registry: dict, has_attempt: bool) -> list[str]:
    sources = {"erdos_frontier"} if has_attempt else set()
    inventory = registry["inventory"]
    for source, problems in inventory.get("source_problem_sets", {}).items():
        if problem in set(problems):
            sources.add(source)
    if problem in set(inventory["formal_conjectures_authored"]):
        sources.add("formal_conjectures")
    if problem in set(inventory["scouting_only"]):
        sources.add("vela_history")
    return sorted(sources)


def _build_problem_profiles(
    registry: dict,
    records: list[dict],
    recovered_records: list[dict],
    formal_conjectures_activity: list[dict],
    status_rows: list[dict],
    verdict_rows: list[dict],
    deposited_attempt_ids: set[str],
) -> tuple[list[dict], dict[int, list[dict]], dict[str, set[int]]]:
    inv = registry["inventory"]
    attempts_by_problem: dict[int, list[dict]] = defaultdict(list)
    for record in records:
        if isinstance(record.get("problem"), int) and 1 <= record["problem"] <= 1217:
            attempts_by_problem[record["problem"]].append(record)
    ledger_problems = set(attempts_by_problem)
    if len(ledger_problems) != 82:
        raise InventoryError(f"legacy ledger covers {len(ledger_problems)} problems, expected 82")
    for record in recovered_records:
        attempts_by_problem[record["problem"]].append(record)

    current = ledger_problems | set(inv["current_artifact_additions"])
    mathematical = current | set(inv["history_only_campaigns"])
    research = mathematical | set(inv["scouting_only"])
    all_authored = research | set(inv["formal_conjectures_authored"])
    lenses = {
        "current_record": current,
        "mathematical_work": mathematical,
        "research_plus_scouting": research,
        "all_authored": all_authored,
    }
    for name, values in lenses.items():
        for problem in values:
            validate_problem_id(problem)
        expected = inv["expected_counts"][name]
        if len(values) != expected:
            raise InventoryError(f"{name} has {len(values)} problems, expected {expected}")
    if sorted(all_authored) != inv["expected_all_authored"]:
        raise InventoryError("all_authored differs from the audited 248-problem baseline")
    if not current <= mathematical <= research <= all_authored:
        raise InventoryError("inventory lenses must be monotonically inclusive")

    status_by_problem = {int(row["problem"]): row for row in status_rows}
    verdict_by_problem = {int(row["problem"]): row for row in verdict_rows}
    if set(status_by_problem) != set(range(1, 1218)):
        raise InventoryError("status feed must cover every problem 1..1217 exactly once")

    additions = set(inv["current_artifact_additions"])
    history = set(inv["history_only_campaigns"])
    scouting = set(inv["scouting_only"])
    fc_authored = set(inv["formal_conjectures_authored"])
    fc_class_by_problem = {
        row["problem"]: row["category"] for row in formal_conjectures_activity
    }
    if set(fc_class_by_problem) != fc_authored:
        raise InventoryError("Formal Conjectures classifications must partition all 136 touches")
    if not {
        row["problem"] for row in formal_conjectures_activity
        if row["affects_mathematical_work_lens"]
    } <= mathematical:
        raise InventoryError("FC mathematical_proof_work must already have independent math evidence")
    overrides = {int(key): value for key, value in inv.get("problem_overrides", {}).items()}
    special = {int(key): value for key, value in inv.get("excluded_special_activity", {}).items()}
    source_sets = {key: set(value) for key, value in inv.get("source_problem_sets", {}).items()}

    profiles = []
    for problem in range(1, 1218):
        status = status_by_problem[problem]
        verdict = verdict_by_problem.get(problem, {})
        attempts = attempts_by_problem.get(problem, [])
        banked_attempt_ids = {
            attempt["attempt_id"] for attempt in attempts
            if attempt.get("is_attempt", True)
        } & deposited_attempt_ids
        activity_types = {_attempt_activity(record.get("kind", "")) for record in attempts}
        if problem in additions:
            if problem in source_sets.get("lean_proofs", set()) or problem in source_sets.get(
                    "formal_conjectures_frontier", set()):
                activity_types.add("theorem")
            else:
                activity_types.add("computation")
        if problem in history:
            activity_types.add("attempt")
        if problem in scouting:
            activity_types.add("scout")
        fc_category = fc_class_by_problem.get(problem)
        if fc_category == "mathematical_proof_work":
            activity_types.add("theorem")
        elif fc_category:
            activity_types.add(fc_category)
        if problem in special:
            activity_types.add(special[problem]["activity_type"])

        in_math = problem in mathematical
        if in_math:
            mathematical_scope = "partial"
            lifecycle = "historical" if problem in history else "banked"
            location = "git_history_only" if problem in history else "current_commit"
            trust_values = {"recorded"}
        elif problem in scouting:
            mathematical_scope = "not_applicable"
            lifecycle = "paused"
            location = "current_commit"
            trust_values = {"recorded"}
        elif problem in fc_authored or problem in special:
            mathematical_scope = "not_applicable"
            lifecycle = "banked"
            location = "current_commit"
            trust_values = {"declared"}
        else:
            mathematical_scope = "not_applicable"
            lifecycle = "unstarted"
            location = "reference_only"
            trust_values = {"declared"}

        machine_status = verdict.get("machine_verdict") or "not_checked"
        if machine_status in {"unconditional", "conditional"} and in_math:
            trust_values.add("machine_reproduced")
        signed_fidelity = verdict.get("signed_fidelity_verdict")
        if signed_fidelity:
            statement_fidelity = "attested"
            trust_values.add("signed")
        elif verdict.get("held_for_review") or status.get("claims"):
            statement_fidelity = "pending"
        else:
            statement_fidelity = "not_assessed"

        override = overrides.get(problem, {})
        activity_types.update(override.get("activity_types", []))
        mathematical_scope = override.get("mathematical_scope", mathematical_scope)
        machine_status = override.get("machine_status", machine_status)
        lifecycle = override.get("lifecycle", lifecycle)
        location = override.get("location", location)
        if override.get("trust"):
            trust_values.add(override["trust"])
        recovered = [attempt for attempt in attempts if "classification" in attempt]
        if recovered:
            if len(recovered) != 1:
                raise InventoryError(f"Erdős {problem} has duplicate recovered records")
            recovered_record = recovered[0]
            mathematical_scope = recovered_record["mathematical_scope"]
            lifecycle = recovered_record["lifecycle"]
            location = recovered_record["location"]
            trust_values.add(recovered_record["trust"])
        if banked_attempt_ids:
            trust_values.add("signed")

        channels = sorted({
            sanitize_public_text(channel)
            for record in attempts
            for channel in (
                ([record["frontier"]] if record.get("frontier") else [])
                + list(record.get("method_families") or [])
            )
        })
        related = {related for record in attempts for related in record.get("related_problems", [])
                   if isinstance(related, int) and 1 <= related <= 1217}
        reusable = any(record.get("reusable_for") for record in attempts)
        if len(related) >= 3 or reusable:
            dependency_impact = "cross_problem_reusable"
        elif related:
            dependency_impact = "cross_problem"
        elif activity_types:
            dependency_impact = "problem_local"
        else:
            dependency_impact = "none"

        repositories = _source_repositories(problem, registry, bool(attempts))
        repositories = sorted(set(repositories) | {
            record["repository_key"] for record in recovered
        })
        attempt_count = sum(record.get("is_attempt", True) for record in attempts)
        if attempt_count:
            summary = (
                f"{attempt_count} recorded research attempt"
                f"{'s' if attempt_count != 1 else ''}."
            )
        elif recovered:
            summary = "Pinned historical activity; attempt promotion is explicitly deferred."
        elif problem in history:
            summary = "Substantive campaign recovered from pinned Git history."
        elif problem in additions:
            summary = "Durable theorem or computation artifact at a pinned source commit."
        elif problem in scouting:
            summary = "Dossier-only research target; no mathematical attempt is claimed."
        elif problem in fc_authored:
            summary = "Authored Formal Conjectures integration activity; not a proof attempt."
        elif problem in special:
            summary = special[problem]["reason"]
        else:
            summary = "Reference corpus entry; no authored work recorded."

        profiles.append({
            "problem": problem,
            "label": f"Erdős {problem}",
            "url": status.get("erdos_url") or f"https://www.erdosproblems.com/{problem}",
            "upstream_state": _normalize_upstream_state(status.get("erdos_state")),
            "lenses": {name: problem in values for name, values in lenses.items()},
            "activity_types": sorted(activity_types),
            "formal_conjectures_activity": fc_category,
            "mathematical_scope": mathematical_scope,
            "machine_status": machine_status,
            "statement_fidelity": statement_fidelity,
            "trust": _strongest_trust(trust_values),
            "lifecycle": lifecycle,
            "location": location,
            "accepted_activity": False,
            "banked_attempt_count": len(banked_attempt_ids),
            "attempt_count": attempt_count,
            "recovered_record_count": len(recovered),
            "repositories": repositories,
            "method_channels": channels,
            "dependency_impact": dependency_impact,
            "summary": summary,
            "detail_url": f"problems/{problem}.json",
            **({"lens_exclusion": "special_activity_outside_audited_authorship_baseline"}
               if problem in special else {}),
        })
    return profiles, attempts_by_problem, lenses


def _build_claim_graph(frontier: dict, frontier_root: str) -> tuple[dict, dict[int, list[dict]]]:
    accepted = [finding for finding in frontier.get("findings", [])
                if not (finding.get("flags") or {}).get("retracted")]
    accepted_ids = {finding["id"] for finding in accepted}
    by_problem: dict[int, list[dict]] = defaultdict(list)
    nodes = []
    edges = []
    for finding in sorted(accepted, key=lambda item: item["id"]):
        assertion = str((finding.get("assertion") or {}).get("text") or finding["id"])
        node = {
            "id": finding["id"],
            "kind": "finding",
            "label": _short(assertion),
            "state": "accepted",
            "trust": "signed",
            "source_root": frontier_root,
            "inferred": False,
        }
        nodes.append(node)
        problem = _problem_from_finding(finding)
        if problem:
            by_problem[problem].append({
                "id": finding["id"],
                "assertion": sanitize_public_text(assertion),
                "type": (finding.get("assertion") or {}).get("type") or "unknown",
                "trust": "signed",
            })
        for link in finding.get("links") or []:
            target = link.get("target")
            if target not in accepted_ids:
                continue
            edges.append({
                "from": finding["id"],
                "to": target,
                "kind": link.get("type") or "related",
                "trust": "signed",
                "source_root": frontier_root,
                "inferred": bool(link.get("inferred_by")),
            })
    edges.sort(key=lambda edge: (edge["from"], edge["to"], edge["kind"]))
    return ({
        "schema": "vela.frontier_graph.claims.v0.1",
        "frontier_id": frontier["frontier_id"],
        "frontier_root": frontier_root,
        "summary": {
            "nodes": len(nodes),
            "edges": len(edges),
            "accepted_findings": len(nodes),
        },
        "nodes": nodes,
        "edges": edges,
        "claim_boundary": {
            "graph_is_derived": True,
            "nodes_are_accepted_findings": True,
            "relations_are_materialized_typed_links": True,
            "activity_is_excluded": True,
        },
    }, by_problem)


def _stable_component(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode()).hexdigest()[:16]
    return f"{prefix}:{digest}"


def _build_operational_graph(
    registry: dict,
    source_locks: dict,
    frontier_dependencies: list[dict],
    profiles: list[dict],
    records: list[dict],
    routes: dict[str, dict],
    recovered_records: list[dict],
    formal_conjectures_activity: list[dict],
    developed_drafts: list[dict],
    proposal_state_hash: str,
    frontier: dict,
    claim_graph: dict,
    finding_problems: dict[int, list[dict]],
) -> dict:
    frontier_root = (frontier.get("_meta") or {}).get("scientific_state_root")
    if not isinstance(frontier_root, str):
        raise InventoryError("materialized frontier has no scientific state root")
    deposited = {attempt.get("attempt_id"): attempt for attempt in frontier.get("attempts") or []}
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(node_id: str, kind: str, label: str, path: str, **attrs: Any) -> None:
        candidate = {
            "id": node_id,
            "kind": kind,
            "label": sanitize_public_text(label),
            "path": sanitize_public_text(path),
            **{key: sanitize_public_text(value) for key, value in attrs.items()
               if value not in (None, "", [])},
        }
        nodes.setdefault(node_id, candidate)

    def add_edge(source: str, target: str, relation: str, evidence: str,
                 trust: str, source_root: str, inferred: bool) -> None:
        edges.append({
            "source": source,
            "target": target,
            "relation": relation,
            "evidence": sanitize_public_text(evidence),
            "trust": trust,
            "source_root": source_root,
            "inferred": inferred,
        })

    for profile in profiles:
        problem = profile["problem"]
        add_node(
            f"erdos:{problem}", "problem", profile["label"],
            f"site/problems/{problem}.json", trust="declared",
            source_root=frontier_root, inferred=False, plane="reference",
            upstream_state=profile["upstream_state"],
        )

    for repo_id, lock in sorted(source_locks.items()):
        repo = lock.get("repo") or registry["repositories"][repo_id]["remote"].removeprefix(
            "https://github.com/").removesuffix(".git")
        remote = registry["repositories"][repo_id]["remote"]
        add_node(f"repo:{repo_id}", "repository", repo, remote,
                 trust="recorded", source_root=lock["sha256"], inferred=False,
                 role=registry["repositories"][repo_id]["role"])
        if lock.get("commit"):
            commit_id = f"commit:{repo_id}:{lock['commit']}"
            commit_url = remote.removesuffix(".git") + f"/commit/{lock['commit']}"
            add_node(commit_id, "commit", lock["commit"][:12], commit_url,
                     trust="recorded", source_root=lock["sha256"], inferred=False)
            add_edge(f"repo:{repo_id}", commit_id, "pins",
                     "Selected paths are content-locked at this Git commit.",
                     "recorded", lock["sha256"], False)

    for dependency in frontier_dependencies:
        dependency_id = f"frontier:{dependency['frontier_id']}"
        add_node(
            dependency_id,
            "frontier_dependency",
            dependency["name"],
            dependency["locator"],
            trust="recorded",
            source_root=dependency["snapshot_hash"],
            inferred=False,
            plane="federated_state",
            frontier_id=dependency["frontier_id"],
        )
        repository_key = next(
            key for key, spec in registry["repositories"].items()
            if spec.get("frontier_id") == dependency["frontier_id"]
            and spec.get("role") != "deprecated_duplicate"
        )
        add_edge(
            f"repo:{repository_key}",
            dependency_id,
            "publishes_frontier",
            "Pinned dependency references accepted findings without copying them locally.",
            "recorded",
            dependency["snapshot_hash"],
            False,
        )

    for finding in claim_graph["nodes"]:
        add_node(finding["id"], "finding", finding["label"],
                 f"frontier.json#{finding['id']}", trust="signed",
                 source_root=frontier_root, inferred=False, plane="state")
    for edge in claim_graph["edges"]:
        add_edge(edge["from"], edge["to"], edge["kind"],
                 "Materialized typed link between accepted findings.",
                 edge["trust"], edge["source_root"], edge["inferred"])
    for problem, findings in finding_problems.items():
        for finding in findings:
            add_edge(finding["id"], f"erdos:{problem}", "describes",
                     "Problem identity derived from the accepted finding's pinned source anchor.",
                     "signed", frontier_root, True)

    ledger_root = _sha256(LEDGER_PATH)
    activity_by_problem: dict[int, list[str]] = defaultdict(list)
    for record in records:
        source_attempt_id = record["attempt_id"]
        route = routes[source_attempt_id]
        target_attempt_id = ("vat_0364e7ec199e4b9b"
                             if route["id"] == "erdos_campaign_audit"
                             else source_attempt_id)
        is_deposited = target_attempt_id in deposited
        attempt_id = target_attempt_id if is_deposited else source_attempt_id
        problem = record.get("problem")
        if route["id"] == "numbered_erdos":
            target = f"erdos:{problem}"
            relation = "investigates"
            activity_by_problem[problem].append(attempt_id)
        elif route["id"] == "erdos_campaign_audit":
            target = "campaign:erdos"
            relation = "audits"
            add_node(target, "campaign", "Erdős corpus campaign", "site/work-index.json",
                     trust="recorded", source_root=ledger_root, inferred=False, plane="activity")
        elif route["id"] == "oeis_sidon":
            target = f"oeis:A{problem}"
            relation = "investigates"
            add_node(target, "external_problem", f"OEIS A{problem}",
                     f"https://oeis.org/A{problem}", trust="recorded",
                     source_root=ledger_root, inferred=False, plane="external")
        else:
            target = "platform:vela"
            relation = "evaluates"
            add_node(target, "platform", "Vela platform activity", "sources/attempt-migration.yaml",
                     trust="recorded", source_root=ledger_root, inferred=False, plane="activity")
        add_node(
            attempt_id, "attempt", f"{record.get('kind', 'attempt')} — {target}",
            (f"frontier.json#{attempt_id}" if is_deposited else
             f"attack/attempt-ledger.v2.json#{source_attempt_id}"),
            trust="signed" if is_deposited else "recorded",
            source_root=frontier_root if is_deposited else ledger_root,
            inferred=False, plane="activity",
            claimed_status=record.get("claimed_status"), migration_route=route["id"],
        )
        add_edge(attempt_id, target, relation,
                 ("Signed banked attempt; claimed_status remains display-only."
                  if is_deposited else
                  "Unsigned legacy activity record; claimed_status is display-only."),
                 "signed" if is_deposited else "recorded",
                 frontier_root if is_deposited else ledger_root, False)
        proposer = str((record.get("provenance") or {}).get("proposer") or "unknown producer")
        producer_id = _stable_component("producer", proposer)
        add_node(producer_id, "producer", proposer, "attack/attempt-ledger.v2.json",
                 trust="recorded", source_root=ledger_root, inferred=False, plane="activity")
        add_edge(producer_id, attempt_id, "produced",
                 "Producer declared by the legacy attempt provenance.",
                 "recorded", ledger_root, False)
        channel = record.get("frontier")
        if channel:
            channel_id = _stable_component("channel", str(channel))
            add_node(channel_id, "channel", str(channel), "attack/attempt-ledger.v2.json",
                     trust="recorded", source_root=ledger_root, inferred=False, plane="activity")
            add_edge(attempt_id, channel_id, "uses_channel",
                     "Method channel declared by the legacy attempt.",
                     "recorded", ledger_root, False)

    for record in recovered_records:
        problem = record["problem"]
        record_id = record["attempt_id"]
        source = record["source"]
        signed = record["signed_attempt"]
        deferred = record["classification"] == "deferred_with_reason"
        trust = "signed" if signed else record["trust"]
        source_root = frontier_root if signed else source["sha256"]
        node_kind = "historical_record" if deferred else "attempt"
        add_node(
            record_id,
            node_kind,
            f"{record['activity_type']} — Erdős {problem}",
            f"frontier.json#{record_id}" if signed else record["source_ref"],
            trust=trust,
            source_root=source_root,
            inferred=False,
            plane="activity",
            accepted=False,
            classification=record["classification"],
            lifecycle=record["lifecycle"],
            location=record["location"],
            mathematical_scope=record["mathematical_scope"],
            claim_digest=record["claim_digest"],
            deposit_deferred=deferred,
        )
        add_edge(
            record_id,
            f"erdos:{problem}",
            "documents" if deferred else "investigates",
            (
                record.get("reason")
                if deferred
                else "Recovered research attempt; claimed content remains activity-plane evidence."
            ),
            trust,
            source_root,
            False,
        )
        producer = str((record.get("provenance") or {}).get("proposer") or "git-history recovery")
        producer_id = _stable_component("producer", producer)
        add_node(
            producer_id,
            "producer",
            producer,
            record["source_ref"],
            trust="recorded",
            source_root=source["sha256"],
            inferred=False,
            plane="activity",
        )
        add_edge(
            producer_id,
            record_id,
            "produced",
            "Producer attribution recovered from the pinned research artifact.",
            "recorded",
            source["sha256"],
            False,
        )
        for family in record.get("method_families") or []:
            channel_id = _stable_component("channel", family)
            add_node(
                channel_id,
                "channel",
                family,
                record["source_ref"],
                trust="recorded",
                source_root=source["sha256"],
                inferred=False,
                plane="activity",
            )
            add_edge(
                record_id,
                channel_id,
                "uses_channel",
                "Method family is declared by the pinned recovered record.",
                "recorded",
                source["sha256"],
                False,
            )

        repository_key = record["repository_key"]
        repo_id = f"repo:{repository_key}"
        commit_id = f"commit:{repository_key}:{source['commit']}"
        remote = registry["repositories"][repository_key]["remote"].removesuffix(".git")
        add_node(
            commit_id,
            "commit",
            source["commit"][:12],
            f"{remote}/commit/{source['commit']}",
            trust="recorded",
            source_root=source["sha256"],
            inferred=False,
        )
        if repo_id in nodes:
            add_edge(
                repo_id,
                commit_id,
                "contains_history",
                "Recovered artifact is pinned to this exact historical or non-main commit.",
                "recorded",
                source["sha256"],
                False,
            )
        artifact_id = _stable_component(
            "artifact", f"{repository_key}:{source['commit']}:{source['path']}:{source['sha256']}"
        )
        artifact_locator = f"{remote}/blob/{source['commit']}/{source['path']}"
        if source.get("declaration"):
            artifact_locator += f"#{source['declaration']}"
        add_node(
            artifact_id,
            "artifact",
            source.get("declaration") or source["path"],
            artifact_locator,
            trust=record["trust"],
            source_root=source["sha256"],
            inferred=False,
            plane="evidence",
            repository=repository_key,
            commit=source["commit"],
            content_hash=source["sha256"],
            declaration=source.get("declaration"),
        )
        add_edge(
            commit_id,
            artifact_id,
            "contains",
            "Artifact path and digest are pinned at this producer commit.",
            "recorded",
            source["sha256"],
            False,
        )
        add_edge(
            artifact_id,
            record_id,
            "evidences_activity",
            "Pinned source artifact evidences this activity record, not accepted truth.",
            record["trust"],
            source["sha256"],
            False,
        )

    inventory = registry["inventory"]
    pseudo_sets = [
        ("current", set(inventory["current_artifact_additions"]), "artifact_record", "recorded"),
        ("history", set(inventory["history_only_campaigns"]), "historical_campaign", "recorded"),
        ("scout", set(inventory["scouting_only"]), "scout", "recorded"),
    ]
    for prefix, problems, kind, trust in pseudo_sets:
        for problem in sorted(problems):
            if prefix in {"current", "history"} and any(
                record["problem"] == problem for record in recovered_records
            ):
                continue
            node_id = f"activity:{prefix}:{problem}"
            source_repo = (
                "vela_history" if prefix in {"history", "scout"} else
                (_source_repositories(problem, registry, False) or ["erdos_frontier"])[0]
            )
            root = source_locks.get(source_repo, {}).get("sha256", frontier_root)
            add_node(node_id, kind, f"{kind.replace('_', ' ')} — Erdős {problem}",
                     f"site/problems/{problem}.json", trust=trust, source_root=root,
                     inferred=False, plane="activity", accepted=False)
            add_edge(node_id, f"erdos:{problem}",
                     "investigates",
                     "Pinned authored activity; it does not establish mathematical truth.",
                     trust, root, False)
            activity_by_problem[problem].append(node_id)

    for record in formal_conjectures_activity:
        problem = record["problem"]
        category = record["category"]
        node_id = record["id"]
        add_node(
            node_id,
            category,
            f"{category.replace('_', ' ')} — Erdős {problem}",
            record["source_ref"],
            trust="declared",
            source_root=record["source_root"],
            inferred=False,
            plane="activity",
            accepted=False,
            repository="formal_conjectures",
            commit=record["source_commit"],
            activity_manifest="sources/formal-conjectures-activity.yaml",
            affects_mathematical_work_lens=record["affects_mathematical_work_lens"],
        )
        add_edge(
            node_id,
            f"erdos:{problem}",
            "documents",
            (
                "Pinned Formal Conjectures activity classification; integration activity "
                "does not establish mathematical truth."
            ),
            "declared",
            record["source_root"],
            False,
        )
        activity_by_problem[problem].append(node_id)

    for problem_raw, spec in inventory.get("excluded_special_activity", {}).items():
        problem = int(problem_raw)
        node_id = f"activity:special:{problem}"
        add_node(node_id, spec["activity_type"], spec["activity_type"].replace("_", " "),
                 f"site/problems/{problem}.json", trust="declared", source_root=frontier_root,
                 inferred=False, plane="activity", accepted=False)
        add_edge(node_id, f"erdos:{problem}", "documents", spec["reason"],
                 "declared", frontier_root, False)
        activity_by_problem[problem].append(node_id)

    for draft in developed_drafts:
        proposal_id = draft["id"]
        problem = draft["problem"]
        add_node(
            proposal_id,
            "proposal",
            _short(draft["assertion"]),
            f"frontier.json#{proposal_id}",
            trust="recorded",
            source_root=proposal_state_hash,
            inferred=False,
            plane="proposal",
            status=draft["status"],
            accepted=False,
            proposal_key=draft["proposal_key"],
            assertion_type=draft["assertion_type"],
            mathematical_scope=draft["mathematical_scope"],
            machine_status=draft["machine_status"],
            statement_fidelity=draft["statement_fidelity"],
            lifecycle=draft["lifecycle"],
            is_residual=draft["is_residual"],
        )
        add_edge(
            proposal_id,
            f"erdos:{problem}",
            "proposes",
            draft["assertion"],
            "recorded",
            proposal_state_hash,
            False,
        )
        producer_id = _stable_component("producer", draft["actor"])
        add_node(
            producer_id,
            "producer",
            draft["actor"],
            "review/developed-campaign-proposals.v1.yaml",
            trust="recorded",
            source_root=proposal_state_hash,
            inferred=False,
            plane="proposal",
        )
        add_edge(
            producer_id,
            proposal_id,
            "drafted",
            "The agent drafted a proposal; human review and acceptance remain required.",
            "recorded",
            proposal_state_hash,
            False,
        )
        artifact = draft.get("artifact")
        if artifact:
            artifact_id = _stable_component(
                "artifact",
                (
                    f"{artifact['repository_key']}:{artifact['commit']}:"
                    f"{artifact['path']}:{artifact['sha256']}"
                ),
            )
            add_node(
                artifact_id,
                "artifact",
                artifact["declaration"],
                artifact["locator"],
                trust=draft["trust"],
                source_root=artifact["sha256"],
                inferred=False,
                plane="evidence",
                repository=artifact["repository"],
                repository_key=artifact["repository_key"],
                commit=artifact["commit"],
                content_hash=artifact["sha256"],
                declaration=artifact["declaration"],
                mathematical_scope=draft["mathematical_scope"],
                machine_status=draft["machine_status"],
                machine_evidence=draft["machine_evidence"],
                statement_fidelity=draft["statement_fidelity"],
            )
            add_edge(
                artifact_id,
                proposal_id,
                "supports_draft",
                "Pinned proof artifact supports a draft claim; it does not accept the claim.",
                draft["trust"],
                artifact["sha256"],
                False,
            )
            commit_id = f"commit:{artifact['repository_key']}:{artifact['commit']}"
            if commit_id in nodes:
                add_edge(
                    commit_id,
                    artifact_id,
                    "contains",
                    "The artifact path and declaration are pinned at this producer commit.",
                    "recorded",
                    artifact["sha256"],
                    False,
                )

    for artifact in sorted(frontier.get("artifacts") or [], key=lambda item: item["id"]):
        locator = sanitize_public_text(artifact.get("locator") or f"frontier.json#{artifact['id']}")
        add_node(artifact["id"], "artifact", artifact.get("name") or artifact["id"], locator,
                 trust="signed", source_root=frontier_root, inferred=False, plane="evidence",
                 content_hash=artifact.get("content_hash"))
        for target in sorted(artifact.get("target_findings") or []):
            if target in nodes:
                add_edge(artifact["id"], target, "evidences",
                         "Accepted frontier artifact targets this finding.",
                         "signed", frontier_root, False)

    for attachment in sorted(frontier.get("verifier_attachments") or [],
                             key=lambda item: item["id"]):
        add_node(attachment["id"], "verifier_attachment",
                 attachment.get("verifier_method") or attachment["id"],
                 f"frontier.json#{attachment['id']}", trust="machine_reproduced",
                 source_root=frontier_root, inferred=False, plane="evidence",
                 outcome=attachment.get("outcome"))
        target = attachment.get("target")
        if target in nodes:
            add_edge(attachment["id"], target, "verifies",
                     "Materialized verifier attachment matches the target claim digest.",
                     "machine_reproduced", frontier_root, False)

    # Leases are evaluated against the pinned July 13 baseline, never wall clock.
    for index, lease in enumerate(sorted(frontier.get("attempt_claims") or [],
                                         key=lambda item: (item.get("obligation_id", ""),
                                                           item.get("claimant_actor", "")))):
        obligation = lease.get("obligation_id") or "unknown"
        lease_id = f"lease:{index:03d}:{obligation}"
        add_node(lease_id, "lease", f"expired lease — {obligation}",
                 f"frontier.json#attempt_claims-{index}", trust="signed",
                 source_root=frontier_root, inferred=False, plane="activity",
                 lifecycle="expired", claimant=lease.get("claimant_actor"))
        if obligation in nodes:
            add_edge(lease_id, obligation, "claimed",
                     "Lease expired before the pinned inventory baseline.",
                     "signed", frontier_root, False)

    node_list = [nodes[key] for key in sorted(nodes)]
    edges.sort(key=lambda edge: (edge["source"], edge["target"], edge["relation"], edge["evidence"]))
    return {
        "schema": "vela.frontier_graph.v0.1",
        "frontier": "Erdős formalization fidelity",
        "frontier_id": registry["frontier_id"],
        "frontier_root": frontier_root,
        "proposal_state_hash": proposal_state_hash,
        "review_pack_sha256": _sha256(DEVELOPED_PROPOSALS_PATH),
        "recovered_records_sha256": _sha256(RECOVERED_ATTEMPTS_PATH),
        "formal_conjectures_activity": {
            "path": "sources/formal-conjectures-activity.yaml",
            "sha256": _sha256(FORMAL_CONJECTURES_ACTIVITY_PATH),
            "source_root": source_locks["formal_conjectures"]["sha256"],
            "source_commit": source_locks["formal_conjectures"]["commit"],
            "records": len(formal_conjectures_activity),
            "category_counts": dict(sorted(Counter(
                row["category"] for row in formal_conjectures_activity
            ).items())),
        },
        "source_locks": source_locks,
        "frontier_dependencies": frontier_dependencies,
        "summary": {
            "nodes": len(node_list),
            "edges": len(edges),
            "by_node_kind": dict(sorted(Counter(node["kind"] for node in node_list).items())),
            "by_relation": dict(sorted(Counter(edge["relation"] for edge in edges).items())),
            "problems": 1217,
            "legacy_records": len(records),
            "attempts": sum(node["kind"] == "attempt" for node in node_list),
            "recovered_records": len(recovered_records),
            "formal_conjectures_activity_records": len(formal_conjectures_activity),
            "pending_proposals": len(developed_drafts),
            "receipts": 0,
            "active_leases": 0,
        },
        "nodes": node_list,
        "edges": edges,
        "claim_boundary": {
            "graph_is_derived": True,
            "claims_external_validation": False,
            "claims_target_validation": False,
            "tracked_frontier_mutated": False,
            "activity_does_not_establish_truth": True,
            "accepted_state_plane": "graph/claim-graph.json",
        },
    }


def _build_reconciliation(registry: dict) -> dict:
    rec = registry["frontier_reconciliation"]
    canonical = set(rec["canonical_event_ids"])
    duplicate = set(rec["duplicate_event_ids"])
    common = sorted(canonical & duplicate)
    canonical_only = sorted(canonical - duplicate)
    duplicate_only = sorted(duplicate - canonical)
    canonical_audit = rec.get("canonical_event_audit") or {}
    if set(canonical_audit) != canonical:
        raise InventoryError(
            "duplicate-frontier audit must inventory every canonical event exactly once"
        )
    for event_id, metadata in canonical_audit.items():
        if not isinstance(metadata.get("kind"), str):
            raise InventoryError(f"{event_id}: canonical event has no kind")
        finding_id = metadata.get("target_finding_id")
        proposal_id = metadata.get("target_proposal_id")
        if finding_id and not re.fullmatch(r"vf_[0-9a-f]{16}", finding_id):
            raise InventoryError(f"{event_id}: invalid canonical target finding id")
        if proposal_id and not re.fullmatch(r"vpr_[0-9a-f]{16}", proposal_id):
            raise InventoryError(f"{event_id}: invalid canonical target proposal id")
    audited = {
        row["event_id"]: row for row in rec.get("duplicate_only_event_audit") or []
    }
    if set(audited) != set(duplicate_only):
        raise InventoryError(
            "duplicate-frontier audit must classify every duplicate-only event exactly once"
        )
    if len(audited) != len(rec.get("duplicate_only_event_audit") or []):
        raise InventoryError("duplicate-frontier audit repeats an event id")

    event_dispositions = []
    for event_id in sorted(canonical | duplicate):
        if event_id in canonical and event_id in duplicate:
            event_dispositions.append({
                **canonical_audit[event_id],
                "event_id": event_id,
                "canonical_presence": True,
                "duplicate_presence": True,
                "classification": "mapped_duplicate",
                "disposition": "mapped",
                "mapped_to_event_id": event_id,
                "reason": (
                    "Byte-identical event is already present in the canonical frontier; "
                    "the retired copy adds no state."
                ),
            })
        elif event_id in canonical:
            event_dispositions.append({
                **canonical_audit[event_id],
                "event_id": event_id,
                "canonical_presence": True,
                "duplicate_presence": False,
                "classification": "mapped_canonical",
                "disposition": "mapped",
                "mapped_to_event_id": event_id,
                "reason": "Canonical-only event remains authoritative in the standalone frontier.",
            })
        else:
            audit = audited[event_id]
            kind = audit.get("kind")
            disposition = audit.get("disposition")
            if kind == "review.rejected":
                if disposition != "ignored_with_reason" or audit.get("proposal_required"):
                    raise InventoryError(f"{event_id}: rejected history must be explicitly ignored")
                classification = "ignored_with_reason"
            elif kind == "finding.asserted":
                if disposition != "deferred" or audit.get("proposal_required") is not True:
                    raise InventoryError(f"{event_id}: duplicate-only finding must require proposal")
                if not re.fullmatch(r"vf_[0-9a-f]{16}", audit.get("target_finding_id", "")):
                    raise InventoryError(f"{event_id}: deferred finding has no target finding id")
                classification = "deferred_proposal_required"
            else:
                raise InventoryError(f"{event_id}: unsupported duplicate-only event kind {kind!r}")
            if not re.fullmatch(r"vpr_[0-9a-f]{16}", audit.get("target_proposal_id", "")):
                raise InventoryError(f"{event_id}: duplicate-only event has no target proposal id")
            event_dispositions.append({
                **audit,
                "canonical_presence": False,
                "duplicate_presence": True,
                "classification": classification,
            })

    disposition_counts = dict(sorted(Counter(
        row["classification"] for row in event_dispositions
    ).items()))
    expected_counts = {
        "deferred_proposal_required": 4,
        "ignored_with_reason": 4,
        "mapped_canonical": 15,
        "mapped_duplicate": 18,
    }
    if disposition_counts != expected_counts:
        raise InventoryError(
            f"duplicate-frontier dispositions drifted: {disposition_counts}"
        )
    proposal_required = [
        row["event_id"] for row in event_dispositions if row.get("proposal_required")
    ]
    ignored_rejections = [
        row["event_id"] for row in event_dispositions
        if row["classification"] == "ignored_with_reason"
    ]
    return {
        "schema": "erdos-frontier.frontier-reconciliation.v1",
        "frontier_id": rec["frontier_id"],
        "canonical": {
            "repository": rec["canonical"],
            "snapshot_hash": rec["canonical_snapshot_hash"],
            "event_log_hash": rec["canonical_event_log_hash"],
            "event_count": len(canonical),
            "public_source": True,
        },
        "duplicate": {
            "repository": rec["duplicate"],
            "snapshot_hash": rec["duplicate_snapshot_hash"],
            "event_log_hash": rec["duplicate_event_log_hash"],
            "event_count": len(duplicate),
            "public_source": False,
            "status": "retired_materialization",
        },
        "comparison": {
            "common_event_ids": common,
            "canonical_only_event_ids": canonical_only,
            "duplicate_only_event_ids": duplicate_only,
            "common": len(common),
            "canonical_only": len(canonical_only),
            "duplicate_only": len(duplicate_only),
            "unique_events": len(canonical | duplicate),
            "common_events_byte_identical": True,
            "disposition_counts": disposition_counts,
        },
        "event_dispositions": event_dispositions,
        "disposition": {
            "policy": rec["policy"],
            "json_merge_performed": False,
            "findings_copied_into_erdos_state": False,
            "duplicate_only_events_require_proposal": proposal_required,
            "duplicate_only_rejections_ignored": ignored_rejections,
        },
    }


def _validate_registered_proof_artifact(artifact: dict) -> None:
    """Reject mutable or incomplete records from the proof-artifact feed."""
    required = ("repository", "commit", "path", "content_digest", "url", "artifact_kind")
    missing = [field for field in required if not artifact.get(field)]
    if missing:
        raise InventoryError(
            f"proof artifact is missing immutable identity fields: {', '.join(missing)}"
        )
    repository = str(artifact["repository"])
    commit = str(artifact["commit"])
    path = str(artifact["path"])
    digest = str(artifact["content_digest"])
    url = str(artifact["url"])
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise InventoryError(f"proof artifact has invalid repository identity {repository!r}")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise InventoryError(f"proof artifact has invalid commit {commit!r}")
    if not path or path.startswith("/") or "/Users/" in path or "/home/" in path:
        raise InventoryError(f"proof artifact has unsafe path {path!r}")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise InventoryError(f"proof artifact has invalid content digest {digest!r}")
    expected_prefix = f"https://github.com/{repository}/blob/{commit}/{path}"
    if not url.startswith(expected_prefix) or "/blob/main/" in url:
        raise InventoryError(f"proof artifact has mutable or mismatched locator {url!r}")
    if str(artifact["artifact_kind"]).startswith("lean_") and not artifact.get("declaration"):
        raise InventoryError("Lean proof artifact has no declaration name")
    if artifact.get("git_blob") and not re.fullmatch(r"[0-9a-f]{40}", artifact["git_blob"]):
        raise InventoryError("proof artifact has an invalid Git blob identity")


def _problem_detail(
    profile: dict,
    status: dict,
    accepted: list[dict],
    attempts: list[dict],
    developed_drafts: list[dict],
    operational: dict,
    source_locks: dict,
) -> dict:
    problem = profile["problem"]
    activity = []
    operational_nodes = {node["id"]: node for node in operational["nodes"]}
    for attempt in attempts:
        banked_node = operational_nodes.get(attempt["attempt_id"])
        banked = bool(banked_node and banked_node.get("trust") == "signed")
        activity.append({
            "id": attempt["attempt_id"],
            "kind": attempt.get("kind") or "attempt",
            "claim": sanitize_public_text(attempt.get("claim") or ""),
            "claimed_status": attempt.get("claimed_status") or "",
            "trust": "signed" if banked else attempt.get("trust", "recorded"),
            "lifecycle": attempt.get("lifecycle") or "banked",
            "location": attempt.get("location") or "current_commit",
            "mathematical_scope": attempt.get("mathematical_scope") or "partial",
            "classification": attempt.get("classification") or "legacy_attempt",
            "accepted": False,
            "banked": banked,
            "source_ref": (banked_node["path"] if banked_node else
                           attempt.get("source_ref") or
                           f"attack/attempt-ledger.v2.json#{attempt['attempt_id']}"),
            "method_channel": sanitize_public_text(attempt.get("frontier") or ""),
            "method_families": [sanitize_public_text(item) for item in
                                attempt.get("method_families", [])],
            "named_obstructions": [sanitize_public_text(item) for item in
                                   attempt.get("named_obstructions", [])],
            "related_problems": sorted({p for p in attempt.get("related_problems", [])
                                        if isinstance(p, int) and 1 <= p <= 1217}),
            "remaining_obligations": [sanitize_public_text(item) for item in
                                      (attempt.get("remaining_obligations") or
                                       attempt.get("depends_on") or [])],
        })
    seen_activity = {item["id"] for item in activity}
    for edge in operational["edges"]:
        if edge["target"] != f"erdos:{problem}" or edge["source"] in seen_activity:
            continue
        node = operational_nodes.get(edge["source"])
        if not node or node.get("plane") != "activity":
            continue
        activity.append({
            "id": node["id"],
            "kind": node["kind"],
            "claim": edge["evidence"],
            "trust": node.get("trust", "recorded"),
            "lifecycle": node.get("lifecycle", profile["lifecycle"]),
            "accepted": False,
            "source_ref": node["path"],
        })
        seen_activity.add(node["id"])

    draft_proposals = [{
        "id": draft["id"],
        "proposal_key": draft["proposal_key"],
        "assertion": draft["assertion"],
        "assertion_type": draft["assertion_type"],
        "conditions": draft["conditions"],
        "status": draft["status"],
        "activity": draft["activity"],
        "mathematical_scope": draft["mathematical_scope"],
        "trust": draft["trust"],
        "lifecycle": draft["lifecycle"],
        "machine_status": draft["machine_status"],
        "statement_fidelity": draft["statement_fidelity"],
        "is_residual": draft["is_residual"],
        "accepted": False,
    } for draft in developed_drafts]

    node_ids = {f"erdos:{problem}"}
    node_ids.update(item["id"] for item in accepted)
    node_ids.update(item["id"] for item in activity)
    node_ids.update(item["id"] for item in draft_proposals)
    changed = True
    while changed:
        changed = False
        for edge in operational["edges"]:
            if edge["target"] in node_ids and edge["source"] not in node_ids:
                source_node = next((node for node in operational["nodes"]
                                    if node["id"] == edge["source"]), None)
                if source_node and source_node["kind"] in {
                    "artifact", "proof_artifact", "verifier_attachment"
                }:
                    node_ids.add(edge["source"])
                    changed = True
    nodes = [node for node in operational["nodes"] if node["id"] in node_ids]
    edges = [edge for edge in operational["edges"]
             if edge["source"] in node_ids and edge["target"] in node_ids]
    sources = [{"repository": repo, **source_locks[repo]}
               for repo in profile["repositories"] if repo in source_locks]
    residual_obligations = sorted({
        sanitize_public_text(item)
        for attempt in attempts
        for item in ((attempt.get("remaining_obligations") or []) +
                     (attempt.get("depends_on") or []))
        if isinstance(item, str) and item.strip()
    } | {
        sanitize_public_text(draft["assertion"])
        for draft in developed_drafts
        if draft["is_residual"] or draft["assertion_type"] == "open_question"
    })
    # Hosted links are references, not registered artifacts. A proof artifact
    # must identify immutable producer content down to repo, commit, path and
    # digest; Lean artifacts additionally carry the declaration name.
    external_references = [{
        "source": link.get("source") or "unknown",
        "url": sanitize_public_text(link.get("url") or ""),
        "declared_state": link.get("state") or "unknown",
        "reference_kind": "hosted_proof_link",
        "registered_artifact": False,
    } for link in status.get("proof_links") or []]
    proof_artifact_candidates = []
    witnesses = []
    for draft in developed_drafts:
        artifact = draft.get("artifact")
        if not artifact:
            continue
        machine = draft["machine_evidence"]
        proof_artifact_candidates.append({
            "repository": artifact["repository"],
            "repository_key": artifact["repository_key"],
            "commit": artifact["commit"],
            "path": artifact["path"],
            "declaration": artifact["declaration"],
            "content_digest": artifact["sha256"],
            "git_blob": artifact["git_blob"],
            "url": artifact["locator"],
            "artifact_kind": "lean_source",
            "registered_artifact": True,
            "trust": draft["trust"],
            "machine_status": draft["machine_status"],
            "mathematical_scope": draft["mathematical_scope"],
            "statement_fidelity": draft["statement_fidelity"],
            "axioms_clean": machine.get("axioms_clean"),
            "axiom_footprint": machine.get("axiom_footprint") or [],
            "attestation_proof_hash": machine.get("attestation_proof_hash"),
            "review_reproduction": machine.get("review_reproduction"),
            "machine_evidence": machine,
            "supports": [{"kind": "proposal", "id": draft["id"]}],
            "accepted": False,
        })
    for attempt in attempts:
        if "classification" not in attempt:
            continue
        source = attempt["source"]
        artifact = {
            "repository": source["repository"],
            "repository_key": attempt["repository_key"],
            "commit": source["commit"],
            "path": source["path"],
            **({"declaration": source["declaration"]} if source.get("declaration") else {}),
            "content_digest": source["sha256"],
            "url": attempt["source_url"],
            "mathematical_scope": attempt["mathematical_scope"],
            "trust": attempt["trust"],
            "supports": [{"kind": "attempt", "id": attempt["attempt_id"]}],
            "accepted": False,
            "registered_artifact": True,
        }
        if attempt["activity_type"] == "theorem" or (
            attempt["activity_type"] == "audit" and source.get("declaration")
        ):
            proof_artifact_candidates.append({
                **artifact,
                "artifact_kind": (
                    "lean_source" if source["path"].endswith(".lean")
                    else "lean_evidence_record" if source.get("declaration")
                    else "research_theorem"
                ),
                "machine_status": (
                    "lean_attested" if attempt["trust"] == "lean_attested"
                    else "machine_reproduced" if attempt["trust"] == "machine_reproduced"
                    else "not_reproduced"
                ),
                "statement_fidelity": profile["statement_fidelity"],
            })
        elif attempt["activity_type"] == "computation":
            witnesses.append({**artifact, "evidence_kind": "exact_compute"})

    proof_artifacts_by_key: dict[tuple[str, str, str, str], dict] = {}
    for artifact in proof_artifact_candidates:
        key = (
            artifact["repository"], artifact["commit"], artifact["path"],
            artifact["content_digest"],
        )
        existing = proof_artifacts_by_key.get(key)
        if existing is None:
            proof_artifacts_by_key[key] = artifact
            continue
        existing["supports"] = sorted(
            existing.get("supports", []) + artifact.get("supports", []),
            key=lambda item: (item["kind"], item["id"]),
        )
        for field, value in artifact.items():
            if field == "supports":
                continue
            if existing.get(field) in (None, "", [], "not_reproduced") and value not in (
                None, "", []
            ):
                existing[field] = value
    proof_artifacts = sorted(
        proof_artifacts_by_key.values(),
        key=lambda artifact: (
            artifact["repository"], artifact["commit"], artifact["path"],
            artifact["content_digest"],
        ),
    )
    for artifact in proof_artifacts:
        _validate_registered_proof_artifact(artifact)
    witnesses.extend([
        {key: node[key] for key in ("id", "label", "path", "content_hash") if key in node}
        for node in nodes
        if node["kind"] == "artifact" and (
            "witness" in node["label"].lower() or "dataset" in node["label"].lower()
        )
    ])
    producers = sorted({
        sanitize_public_text(str((attempt.get("provenance") or {}).get("proposer")))
        for attempt in attempts
        if (attempt.get("provenance") or {}).get("proposer")
    } | {draft["actor"] for draft in developed_drafts})
    commits = [
        {"repository": source["repository"], "commit": source["commit"],
         "source_root": source["sha256"]}
        for source in sources if source.get("commit")
    ]
    commits.extend({
        "repository": attempt["repository_key"],
        "commit": attempt["source"]["commit"],
        "source_root": attempt["source"]["sha256"],
    } for attempt in attempts if "classification" in attempt)
    commits = sorted(
        {json.dumps(item, sort_keys=True): item for item in commits}.values(),
        key=lambda item: (item["repository"], item["commit"]),
    )
    fc = status.get("fc") or {}
    statement = {
        "upstream_url": status.get("erdos_url") or profile["url"],
        "upstream_state": profile["upstream_state"],
        "formal_statement": ({
            "theorem": fc.get("theorem"),
            "url": fc.get("fc_url"),
            "linked_proof": bool(fc.get("linked")),
        } if (fc.get("has_file") or fc.get("path") or fc.get("theorem")) else None),
        "statement_fidelity": profile["statement_fidelity"],
    }
    return {
        "schema": "erdos-frontier.problem-work.v1",
        "frontier_id": operational["frontier_id"],
        "frontier_root": operational["frontier_root"],
        "proposal_state_hash": operational["proposal_state_hash"],
        **profile,
        "statement": statement,
        "accepted": accepted,
        "residual_obligations": residual_obligations,
        "activity": activity,
        "draft_proposals": draft_proposals,
        "review_obligations": sorted({
            sanitize_public_text(obligation)
            for draft in developed_drafts
            for obligation in draft.get("review_obligations") or []
        }),
        "proof_artifacts": proof_artifacts,
        "external_references": external_references,
        "witnesses": witnesses,
        "receipts": [],
        "producers": producers,
        "commits": commits,
        "nodes": nodes,
        "edges": edges,
        "sources": sources,
    }


def _native_target_entry(profile: dict, detail: dict, packet_bytes: bytes) -> dict:
    problem = profile["problem"]
    upstream = profile["upstream_state"]
    lifecycle = profile["lifecycle"]
    residual_count = len(detail["residual_obligations"])
    proof_count = len(detail["proof_artifacts"])
    attempt_count = profile["attempt_count"]
    formal = detail["statement"].get("formal_statement")

    if upstream == "open" and lifecycle == "paused":
        state = "paused"
    elif upstream == "open":
        state = "open"
    else:
        state = "done"

    if state == "open" and (residual_count or attempt_count):
        rank_group = 0
    elif state == "open" and (formal or proof_count):
        rank_group = 1
    elif state == "open":
        rank_group = 2
    elif state == "paused":
        rank_group = 3
    else:
        rank_group = 4
    priority_signal = min(
        10_000,
        residual_count * 100
        + attempt_count * 10
        + proof_count * 5
        + (1 if formal else 0),
    )

    if residual_count:
        why = (
            f"{residual_count} pinned residual obligation"
            f"{'s' if residual_count != 1 else ''}; "
            f"{attempt_count} recorded attempt"
            f"{'s' if attempt_count != 1 else ''}; upstream {upstream}."
        )
    elif attempt_count:
        why = (
            f"{attempt_count} recorded attempt"
            f"{'s' if attempt_count != 1 else ''}; upstream {upstream}; "
            f"machine status {profile['machine_status']}."
        )
    elif formal or proof_count:
        why = (
            f"Pinned formal/proof context is available; upstream {upstream}; "
            f"statement fidelity {profile['statement_fidelity']}."
        )
    else:
        why = (
            f"Complete pinned corpus entry; upstream {upstream}; "
            "no authored attempt is currently recorded."
        )

    labels = [
        "erdos",
        f"upstream-{upstream}",
        f"lifecycle-{lifecycle}",
        f"machine-{profile['machine_status']}",
    ]
    labels.extend(f"activity-{kind}" for kind in profile["activity_types"])
    if formal:
        labels.append("formal-statement")
    if proof_count:
        labels.append("proof-artifact")
    if residual_count:
        labels.append("residual-obligations")

    if state == "open":
        objective = (
            f"Advance Erdős problem {problem} from its pinned statement, theorem and proof "
            "records, attempts, residual obligations, dependency context, and source locks; "
            "produce one decision-relevant artifact or an informative negative result without "
            "repeating banked routes."
        )
    elif state == "paused":
        objective = (
            f"Inspect the pinned record for Erdős problem {problem} and resume it only after "
            "checking the recorded in-flight coordination; preserve prior attempts, proof "
            "records, dependencies, and source locks."
        )
    else:
        objective = (
            f"Inspect, reproduce, or extend the pinned completed record for Erdős problem "
            f"{problem}; do not reopen its upstream status without new decision-relevant "
            "evidence."
        )

    return {
        "id": f"erdos:{problem}",
        "title": profile["label"],
        "why": why,
        "state": state,
        "rank": rank_group * 100_000_000 + (10_000 - priority_signal) * 2_000 + problem,
        "objective": objective,
        "labels": sorted(set(labels)),
        "packet": {
            "path": f"site/problems/{problem}.json",
            "sha256": _sha256_bytes(packet_bytes),
            "schema": detail["schema"],
        },
    }


def build_outputs() -> tuple[dict[pathlib.Path, bytes], dict]:
    registry = _load_yaml(REGISTRY_PATH)
    migration = _load_yaml(MIGRATION_PATH)
    locks = _load_json(LOCK_PATH)
    ledger = _load_json(LEDGER_PATH)
    status = _load_json(STATUS_PATH)
    verdicts = _load_json(VERDICTS_PATH)
    frontier = _load_json(FRONTIER_PATH)
    vela_lock = _load_yaml(VELA_LOCK_PATH)
    developed_pack = _load_yaml(DEVELOPED_PROPOSALS_PATH)
    recovered_pack = _load_yaml(RECOVERED_ATTEMPTS_PATH)
    recovered_ledger = _load_json(RECOVERED_LEDGER_PATH)
    recovered_import_map = _load_yaml(RECOVERED_IMPORT_MAP_PATH)
    formal_conjectures_manifest = _load_yaml(FORMAL_CONJECTURES_ACTIVITY_PATH)

    validate_repository_roles(registry["repositories"], locks)
    if registry["frontier_id"] != frontier.get("frontier_id"):
        raise InventoryError("registry frontier id differs from materialized state")
    materialized_meta = frontier.get("_meta") or {}
    frontier_root = materialized_meta.get("scientific_state_root")
    if not isinstance(frontier_root, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", frontier_root):
        raise InventoryError("materialized frontier has no valid scientific state root")
    # The public work-inventory projection retains its v1 field names until a
    # separately versioned projection migration. Their values come only from
    # the current Vela 0.914 materialization and lock vocabulary.
    state_pins = {
        "snapshot_hash": frontier_root,
        "event_log_hash": materialized_meta.get("event_log_root"),
        "proposal_state_hash": vela_lock.get("proposal_root"),
    }
    lock_fields = {
        "snapshot_hash": "scientific_state_root",
        "event_log_hash": "event_log_root",
        "proposal_state_hash": "proposal_root",
    }
    for name, digest in state_pins.items():
        if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise InventoryError(f"materialized frontier has no valid {name}")
        lock_field = lock_fields[name]
        if vela_lock.get(lock_field) != digest:
            raise InventoryError(
                f"vela.lock {lock_field} differs from materialized state"
            )
    if _sha256(LEDGER_PATH) != migration["source"]["sha256"]:
        raise InventoryError("legacy attempt ledger differs from its migration pin")
    records = ledger.get("records") or []
    if ledger.get("object") != "CanopusAttemptLedger" or len(records) != 219:
        raise InventoryError("legacy ledger envelope is not the pinned 219-record v2 ledger")

    routes = classify_attempt_routes(records, migration)
    import_map = _build_cli_import_map(records, routes)
    migration_report = _migration_report(records, routes)
    developed_drafts = _developed_draft_records(developed_pack, frontier)
    recovered_records = _normalize_recovered_records(recovered_pack, registry, frontier)
    _validate_recovered_import_bundle(
        recovered_records, recovered_ledger, recovered_import_map, registry["frontier_id"]
    )
    source_locks = _public_source_locks(registry, locks)
    formal_conjectures_activity = _normalize_formal_conjectures_activity(
        formal_conjectures_manifest, registry, source_locks
    )
    frontier_dependencies = _frontier_dependencies(vela_lock, registry)
    deposited_attempt_ids = {attempt.get("attempt_id") for attempt in frontier.get("attempts") or []}
    profiles, attempts_by_problem, lenses = _build_problem_profiles(
        registry, records, recovered_records, formal_conjectures_activity,
        status["rows"], verdicts["rows"],
        deposited_attempt_ids,
    )
    claim_graph, findings_by_problem = _build_claim_graph(frontier, frontier_root)
    claim_graph["frontier_dependencies"] = frontier_dependencies
    claim_graph["claim_boundary"]["federated_findings_are_referenced_not_copied"] = True
    operational = _build_operational_graph(
        registry, source_locks, frontier_dependencies, profiles, records, routes, recovered_records,
        formal_conjectures_activity, developed_drafts,
        state_pins["proposal_state_hash"], frontier, claim_graph,
        findings_by_problem,
    )
    reconciliation = _build_reconciliation(registry)

    work_index = {
        "schema": "erdos-frontier.work-index.v1",
        "frontier_id": registry["frontier_id"],
        "frontier_root": frontier_root,
        "state_pins": state_pins,
        "source_locks": source_locks,
        "activity_manifests": {
            "formal_conjectures": {
                "path": "sources/formal-conjectures-activity.yaml",
                "sha256": _sha256(FORMAL_CONJECTURES_ACTIVITY_PATH),
                "source_root": source_locks["formal_conjectures"]["sha256"],
                "records": len(formal_conjectures_activity),
            },
        },
        "counts": {
            "current_record": len(lenses["current_record"]),
            "mathematical_work": len(lenses["mathematical_work"]),
            "research_plus_scouting": len(lenses["research_plus_scouting"]),
            "all_authored": len(lenses["all_authored"]),
            "corpus": len(profiles),
        },
        "problems": profiles,
    }
    work_inventory = {
        "schema": "erdos-frontier.work-inventory.v1",
        "frontier_id": registry["frontier_id"],
        "frontier_root": frontier_root,
        "state_pins": state_pins,
        "baseline_frontier_root": registry["baseline_frontier_root"],
        "counts": work_index["counts"],
        "lenses": {name: sorted(values) for name, values in lenses.items()},
        "history_only_campaigns": registry["inventory"]["history_only_campaigns"],
        "scouting_only": registry["inventory"]["scouting_only"],
        "excluded_special_activity": registry["inventory"]["excluded_special_activity"],
        "developed_proposals": {
            "path": "review/developed-campaign-proposals.v1.yaml",
            "sha256": _sha256(DEVELOPED_PROPOSALS_PATH),
            "pending": len(developed_drafts),
            "proposal_state_hash": state_pins["proposal_state_hash"],
        },
        "recovered_records": {
            "path": "sources/recovered-attempts.yaml",
            "sha256": _sha256(RECOVERED_ATTEMPTS_PATH),
            "ledger_sha256": _sha256(RECOVERED_LEDGER_PATH),
            "import_map_sha256": _sha256(RECOVERED_IMPORT_MAP_PATH),
            "records": len(recovered_records),
            "importable_attempts": sum(record["is_attempt"] for record in recovered_records),
            "signed_attempts": sum(record["signed_attempt"] for record in recovered_records),
            "deferred": sum(not record["is_attempt"] for record in recovered_records),
        },
        "formal_conjectures_activity": {
            "path": "sources/formal-conjectures-activity.yaml",
            "sha256": _sha256(FORMAL_CONJECTURES_ACTIVITY_PATH),
            "source": {
                "repository": source_locks["formal_conjectures"]["repo"],
                "commit": source_locks["formal_conjectures"]["commit"],
                "paths": source_locks["formal_conjectures"]["paths"],
                "sha256": source_locks["formal_conjectures"]["sha256"],
            },
            "records": len(formal_conjectures_activity),
            "authored_problem_count": len({
                row["problem"] for row in formal_conjectures_activity
            }),
            "category_counts": dict(sorted(Counter(
                row["category"] for row in formal_conjectures_activity
            ).items())),
            "mathematical_lens_category": "mathematical_proof_work",
        },
        "lens_policy": {
            "all_authored": (
                "The audited 248 baseline covers research, scouting, and authored Formal "
                "Conjectures file activity. Problems 872 and 1082 are retained as special "
                "prompt/prior-art process records but excluded because neither is an authored "
                "mathematical or integration artifact in that audit."
            ),
        },
        "claim_boundary": {
            "inventory_is_derived": True,
            "activity_does_not_establish_truth": True,
            "statement_edits_do_not_imply_mathematical_work": True,
            "dirty_worktrees_are_excluded": True,
            "omitted_attempt_problem_decodes_as_zero": True,
        },
    }

    claim_graph_bytes = _json_bytes(claim_graph)
    outputs: dict[pathlib.Path, bytes] = {
        IMPORT_MAP_PATH: _yaml_bytes(import_map),
        MIGRATION_REPORT_PATH: _json_bytes(migration_report),
        WORK_INVENTORY_PATH: _json_bytes(work_inventory),
        CLAIM_GRAPH_PATH: claim_graph_bytes,
        # Public canonical projection.  site/graph.json remains the legacy
        # compatibility corpus graph and is deliberately not overwritten.
        SITE_CLAIM_GRAPH_PATH: claim_graph_bytes,
        FRONTIER_MAP_PATH: _json_bytes(operational),
        RECONCILIATION_PATH: _json_bytes(reconciliation),
        WORK_INDEX_PATH: _json_bytes(work_index, compact=True),
    }
    profile_by_problem = {profile["problem"]: profile for profile in profiles}
    status_by_problem = {int(row["problem"]): row for row in status["rows"]}
    drafts_by_problem: dict[int, list[dict]] = defaultdict(list)
    for draft in developed_drafts:
        drafts_by_problem[draft["problem"]].append(draft)
    native_targets = []
    for problem in range(1, 1218):
        detail = _problem_detail(
            profile_by_problem[problem], status_by_problem[problem],
            findings_by_problem.get(problem, []),
            attempts_by_problem.get(problem, []), drafts_by_problem.get(problem, []),
            operational, source_locks,
        )
        packet_bytes = _json_bytes(detail, compact=True)
        outputs[PROBLEM_DIR / f"{problem}.json"] = packet_bytes
        native_targets.append(
            _native_target_entry(profile_by_problem[problem], detail, packet_bytes)
        )
    native_targets.sort(key=lambda target: (target["rank"], target["id"]))

    outputs[TARGET_INDEX_CANDIDATE_PATH] = _json_bytes({
        "schema": "vela.target-index-candidate.v1",
        "frontier_id": registry["frontier_id"],
        "source": {
            "git_commit": _git_head(),
            "input_paths": TARGET_INDEX_INPUT_PATHS,
        },
        "targets": [
            {
                **{key: value for key, value in target.items() if key != "packet"},
                "packet": {
                    "schema": target["packet"]["schema"],
                    "path": target["packet"]["path"],
                },
            }
            for target in native_targets
        ],
    }, compact=True)

    # A hard public-data guard: generated feeds never leak workstation paths.
    for path, data in outputs.items():
        text = data.decode()
        if "/Users/" in text or "/home/" in text:
            raise InventoryError(f"absolute path leaked into public output {path.relative_to(HERE)}")
    return outputs, {
        "counts": work_index["counts"],
        "migration": migration_report["summary"],
        "operational": operational["summary"],
    }


def write_outputs(target_candidate_output: pathlib.Path | None = None) -> dict:
    outputs, summary = build_outputs()
    selected_outputs = outputs
    if target_candidate_output is not None:
        candidate = json.loads(outputs[TARGET_INDEX_CANDIDATE_PATH])
        packet_paths = {
            HERE / target["packet"]["path"]
            for target in candidate["targets"]
        }
        selected_outputs = {
            path: data
            for path, data in outputs.items()
            if path == TARGET_INDEX_CANDIDATE_PATH or path in packet_paths
        }

    for path, data in selected_outputs.items():
        destination = (
            target_candidate_output
            if path == TARGET_INDEX_CANDIDATE_PATH and target_candidate_output is not None
            else path
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    if target_candidate_output is None:
        expected_shards = {path.name for path in outputs if path.parent == PROBLEM_DIR}
        for stale in PROBLEM_DIR.glob("*.json"):
            if stale.name not in expected_shards:
                stale.unlink()
    return summary


def check_outputs() -> dict:
    outputs, summary = build_outputs()
    failures = []
    for path, expected in outputs.items():
        if path == TARGET_INDEX_CANDIDATE_PATH:
            continue
        if not path.exists():
            failures.append(f"missing {path.relative_to(HERE)}")
        elif path.read_bytes() != expected:
            failures.append(f"stale {path.relative_to(HERE)}")
    expected_shards = {path.name for path in outputs if path.parent == PROBLEM_DIR}
    extra_shards = sorted(path.name for path in PROBLEM_DIR.glob("*.json")
                          if path.name not in expected_shards)
    failures.extend(f"unexpected site/problems/{name}" for name in extra_shards)
    try:
        candidate = json.loads(outputs[TARGET_INDEX_CANDIDATE_PATH])
        sealed = _load_json(TARGET_INDEX_PATH)
        if sealed.get("schema") != "vela.target-index.v2":
            failures.append("targets.json is not a sealed vela.target-index.v2")
        elif sealed.get("frontier_id") != candidate["frontier_id"]:
            failures.append("targets.json frontier_id differs from the generated candidate")
        else:
            expected_targets = candidate["targets"]
            actual_targets = sealed.get("targets", [])
            if len(actual_targets) != len(expected_targets):
                failures.append(
                    f"targets.json has {len(actual_targets)} targets; expected {len(expected_targets)}"
                )
            for expected, actual in zip(expected_targets, actual_targets):
                expected_common = {
                    key: value for key, value in expected.items() if key != "packet"
                }
                actual_common = {
                    key: actual.get(key) for key in expected_common
                }
                if actual_common != expected_common:
                    failures.append(
                        f"targets.json semantics differ for {expected['id']}"
                    )
                    break
                packet_path = HERE / expected["packet"]["path"]
                packet = actual.get("packet", {})
                if (
                    packet.get("schema") != expected["packet"]["schema"]
                    or packet.get("path") != expected["packet"]["path"]
                    or packet.get("size") != packet_path.stat().st_size
                    or packet.get("sha256") != _sha256(packet_path)
                ):
                    failures.append(
                        f"targets.json packet binding differs for {expected['id']}"
                    )
                    break
    except (KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
        failures.append(f"cannot validate sealed targets.json: {exc}")
    if failures:
        raise InventoryError("generated inventory check failed:\n  " + "\n  ".join(failures))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="validate and byte-compare without writing")
    parser.add_argument(
        "--target-candidate-output",
        type=pathlib.Path,
        help=(
            "write the Target Index candidate to this path; repository "
            "migration requires a path outside the Frontier checkout"
        ),
    )
    args = parser.parse_args()
    try:
        if args.check and args.target_candidate_output is not None:
            raise InventoryError("--check and --target-candidate-output are mutually exclusive")
        summary = (
            check_outputs()
            if args.check
            else write_outputs(
                args.target_candidate_output.expanduser().resolve()
                if args.target_candidate_output is not None
                else None
            )
        )
    except (InventoryError, KeyError, TypeError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"work inventory: ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        "work inventory: "
        f"{summary['counts']['current_record']}/"
        f"{summary['counts']['mathematical_work']}/"
        f"{summary['counts']['research_plus_scouting']}/"
        f"{summary['counts']['all_authored']} lenses; "
        f"{summary['counts']['corpus']} corpus problems"
    )
    print(
        "attempt migration: "
        f"{summary['migration']['records']} accounted, "
        f"{summary['migration']['ids_preserved']} ids preserved, "
        f"{summary['migration']['ids_changed']} changed, "
        f"{summary['migration']['excluded']} excluded"
    )
    print(
        "operational map: "
        f"{summary['operational']['nodes']} nodes, "
        f"{summary['operational']['edges']} edges"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

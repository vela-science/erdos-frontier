"""Truth and determinism gates for the unified Erdős work inventory."""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

import pytest
import yaml

from scripts import build_work_inventory as work

HERE = pathlib.Path(__file__).resolve().parent.parent


def _work_index() -> dict:
    return json.loads((HERE / "site" / "work-index.json").read_text())


def _row(problem: int) -> dict:
    return _work_index()["problems"][problem - 1]


def _row_detail(problem: int) -> dict:
    return json.loads((HERE / "site" / "problems" / f"{problem}.json").read_text())


def _target_index() -> dict:
    return json.loads((HERE / "targets.json").read_text())


def test_generated_inventory_is_current_and_deterministic():
    first, _ = work.build_outputs()
    second, _ = work.build_outputs()
    assert first == second
    subprocess.run(
        [sys.executable, "scripts/build_work_inventory.py", "--check"],
        cwd=HERE,
        check=True,
        capture_output=True,
        text=True,
    )


def test_external_target_candidate_writes_only_seal_inputs(tmp_path, monkeypatch):
    packet = tmp_path / "site" / "problems" / "1056.json"
    candidate = tmp_path / ".vela" / "tmp" / "target-index-candidate.json"
    unrelated = tmp_path / "graph" / "frontier-map.json"
    external = tmp_path / "external-candidate.json"
    candidate_bytes = json.dumps(
        {
            "targets": [
                {
                    "packet": {
                        "path": "site/problems/1056.json",
                    },
                },
            ],
        },
        separators=(",", ":"),
    ).encode()
    monkeypatch.setattr(work, "HERE", tmp_path)
    monkeypatch.setattr(work, "TARGET_INDEX_CANDIDATE_PATH", candidate)
    monkeypatch.setattr(
        work,
        "build_outputs",
        lambda: (
            {
                packet: b'{"schema":"erdos-frontier.problem-work.v1"}',
                candidate: candidate_bytes,
                unrelated: b'{"derived":true}',
            },
            {"counts": {}, "migration": {}, "operational": {}},
        ),
    )

    work.write_outputs(external)

    assert packet.is_file()
    assert external.read_bytes() == candidate_bytes
    assert not candidate.exists()
    assert not unrelated.exists()


def test_exact_inventory_lenses_and_corpus_coverage():
    index = _work_index()
    assert index["schema"] == "erdos-frontier.work-index.v1"
    assert index["counts"] == {
        "current_record": 102,
        "mathematical_work": 113,
        "research_plus_scouting": 120,
        "all_authored": 248,
        "corpus": 1217,
    }
    assert [row["problem"] for row in index["problems"]] == list(range(1, 1218))
    expected = yaml.safe_load((HERE / "sources" / "work-registry.yaml").read_text())[
        "inventory"
    ]["expected_all_authored"]
    actual = [row["problem"] for row in index["problems"]
              if row["lenses"]["all_authored"]]
    assert actual == expected


def test_all_corpus_problems_are_native_hash_pinned_vela_targets():
    index = _target_index()
    assert index["schema"] == "vela.target-index.v2"
    assert index["frontier_id"] == json.loads((HERE / "frontier.json").read_text())["frontier_id"]
    target_states = Counter(target["state"] for target in index["targets"])
    assert len(index["targets"]) == 1217
    assert target_states == {
        "open": 646,
        "paused": 7,
        "done": 564,
    }
    assert index["claim_boundary"] == {
        "derived": True,
        "authoritative": False,
        "deletable": True,
    }
    targets_by_id = {target["id"]: target for target in index["targets"]}
    assert set(targets_by_id) == {
        f"erdos:{problem}" for problem in range(1, 1218)
    }

    for target in index["targets"]:
        packet_path = HERE / target["packet"]["path"]
        assert packet_path.is_file()
        assert target["packet"]["sha256"] == (
            "sha256:" + hashlib.sha256(packet_path.read_bytes()).hexdigest()
        )
        packet = json.loads(packet_path.read_text())
        assert packet["problem"] == int(target["id"].split(":")[1])
        assert packet["schema"] == target["packet"]["schema"]

    target_1056 = targets_by_id["erdos:1056"]
    assert target_1056["state"] == "open"
    assert "residual-obligations" in target_1056["labels"]
    assert "without repeating banked routes" in target_1056["objective"]
    assert targets_by_id["erdos:2"]["state"] == "done"

    # These four corpus records changed from open to terminal upstream states
    # in the pinned source refresh. Keep the exact transitions explicit so a
    # stale aggregate count cannot hide which target states moved.
    for problem in (119, 123, 320, 321):
        target = targets_by_id[f"erdos:{problem}"]
        assert target["id"] == f"erdos:{problem}"
        assert target["state"] == "done"
        assert "upstream-proved" in target["labels"]


def test_migration_accounts_for_every_record_and_preserves_numbered_ids():
    report = json.loads((HERE / "graph" / "attempt-migration-report.json").read_text())
    assert report["summary"] == {
        "records": 219,
        "imported": 213,
        "excluded": 6,
        "ids_preserved": 212,
        "ids_changed": 1,
        "by_route": {
            "erdos_campaign_audit": 1,
            "numbered_erdos": 212,
            "oeis_sidon": 3,
            "vela_platform": 3,
        },
    }
    numbered = [row for row in report["records"] if row["route"] == "numbered_erdos"]
    assert len(numbered) == 212
    assert all(row["source_attempt_id"] == row["target_attempt_id"] for row in numbered)
    audit = next(row for row in report["records"] if row["route"] == "erdos_campaign_audit")
    assert audit["source_attempt_id"] == "vat_3042c1ec533c9a0f"
    assert audit["target_attempt_id"] == "vat_0364e7ec199e4b9b"
    assert audit["source_problem"] == 0
    assert audit["target_identity"] == "erdos:0"
    assert "omitted problem decodes as 0" in report["identity_semantics"]["erdos:0"]


def test_cli_import_map_is_explicit_and_exhaustive():
    mapping = yaml.safe_load((HERE / "sources" / "attempt-import-map.yaml").read_text())
    ledger = json.loads((HERE / "attack" / "attempt-ledger.v2.json").read_text())
    assert mapping["schema"] == "vela.attempt-import-map.v1"
    assert mapping["exhaustive"] is True
    assert len(mapping["mappings"]) == len(ledger["records"]) == 219
    assert {item["attempt_id"] for item in mapping["mappings"]} == {
        item["attempt_id"] for item in ledger["records"]
    }
    assert sum(item["action"] == "exclude" for item in mapping["mappings"]) == 6


def test_signed_import_is_reflected_without_confusing_activity_with_truth():
    frontier = json.loads((HERE / "frontier.json").read_text())
    index = _work_index()
    attempts = frontier.get("attempts") or []
    assert len(attempts) == 243
    campaign_audit = next(
        attempt for attempt in attempts
        if attempt["attempt_id"] == "vat_0364e7ec199e4b9b"
    )
    # Attempt.problem has a protocol default of zero. Canonical serialization
    # elides the default, but the campaign identity remains explicitly erdos:0
    # in the reconciliation report rather than becoming "unknown".
    assert "problem" not in campaign_audit
    assert campaign_audit.get("problem", 0) == 0
    report = json.loads((HERE / "graph" / "attempt-migration-report.json").read_text())
    audit_row = next(
        row for row in report["records"]
        if row["target_attempt_id"] == campaign_audit["attempt_id"]
    )
    assert audit_row["target_identity"] == "erdos:0"
    assert index["frontier_root"] == frontier["_meta"]["scientific_state_root"]
    assert sum(row["banked_attempt_count"] for row in index["problems"]) == 242
    assert all(row["accepted_activity"] is False for row in index["problems"])
    operational = json.loads((HERE / "graph" / "frontier-map.json").read_text())
    signed_attempts = [node for node in operational["nodes"]
                       if node["kind"] == "attempt" and node["trust"] == "signed"]
    assert len(signed_attempts) == 243


def test_recovered_attempts_prefer_signed_ids_and_deferred_773_stays_a_record():
    recovered = yaml.safe_load((HERE / "sources" / "recovered-attempts.yaml").read_text())
    importable = [record for record in recovered["records"]
                  if record["classification"] == "importable_attempt"]
    expected_ids = {record["attempt_id"] for record in importable}
    operational = json.loads((HERE / "graph" / "frontier-map.json").read_text())
    nodes = operational["nodes"]
    by_id = {node["id"]: node for node in nodes}
    assert len(expected_ids) == 30
    assert all(by_id[attempt_id]["kind"] == "attempt" for attempt_id in expected_ids)
    assert all(by_id[attempt_id]["trust"] == "signed" for attempt_id in expected_ids)
    assert all(sum(node["id"] == attempt_id for node in nodes) == 1
               for attempt_id in expected_ids)

    row_773 = _row(773)
    assert row_773["attempt_count"] == 0
    assert row_773["recovered_record_count"] == 1
    detail = _row_detail(773)
    deferred = [item for item in detail["activity"]
                if item["classification"] == "deferred_with_reason"]
    assert len(deferred) == 1
    assert deferred[0]["banked"] is False

    inventory = json.loads((HERE / "graph" / "work-inventory.json").read_text())
    assert inventory["recovered_records"]["records"] == 31
    assert inventory["recovered_records"]["signed_attempts"] == 30
    assert inventory["recovered_records"]["deferred"] == 1


def test_invalid_erdos_id_and_duplicate_authority_are_rejected():
    for invalid in (0, 1218, 396704, "23", True):
        with pytest.raises(work.InventoryError):
            work.validate_problem_id(invalid)
    registry = yaml.safe_load((HERE / "sources" / "work-registry.yaml").read_text())
    broken = copy.deepcopy(registry["repositories"])
    broken["lean_proofs"]["role"] = "authority"
    with pytest.raises(work.InventoryError):
        work.validate_repository_roles(broken)


def test_every_public_repository_has_a_complete_exact_lock():
    registry = yaml.safe_load((HERE / "sources" / "work-registry.yaml").read_text())
    locks = json.loads((HERE / "sources.lock.json").read_text())
    work.validate_repository_roles(registry["repositories"], locks)
    for key, spec in registry["repositories"].items():
        if not spec.get("public_output"):
            continue
        source = (locks.get("work_sources") or {}).get(spec["lock_key"])
        source = source or locks["sources"][spec["lock_key"]]
        assert len(source["commit"]) == 40, key
        assert source["sha256"].startswith("sha256:"), key
        assert source.get("paths") or source.get("path"), key
        assert source["repo"] == spec["remote"].removeprefix(
            "https://github.com/").removesuffix(".git")


def test_history_and_scope_semantics_remain_honest():
    assert _row(23)["upstream_state"] == "open"
    assert _row(686)["upstream_state"] == "open"
    assert _row(686)["machine_status"] == "lean_kernel_passed"
    assert _row(686)["mathematical_scope"] == "partial"

    history_42 = _row(42)
    assert history_42["lenses"]["current_record"] is False
    assert history_42["lifecycle"] == "historical"
    assert history_42["location"] == "git_history_only"

    pending_92 = _row(92)
    assert pending_92["mathematical_scope"] == "partial"
    assert pending_92["accepted_activity"] is False
    assert pending_92["lifecycle"] == "paused"
    assert pending_92["location"] == "non_main_ref"


def test_theorem_scope_machine_status_and_fidelity_are_independent():
    row = _row(154)
    assert row["mathematical_scope"] == "full"
    assert row["machine_status"] == "unconditional"
    assert row["statement_fidelity"] == "not_assessed"
    assert row["trust"] == "lean_attested"


def test_formal_conjectures_classification_does_not_inflate_math():
    registry = yaml.safe_load((HERE / "sources" / "work-registry.yaml").read_text())
    categories = registry["inventory"]["formal_conjectures_classification"]
    classified = [problem for problems in categories.values() for problem in problems]
    assert len(classified) == len(set(classified)) == 136
    assert set(classified) == set(registry["inventory"]["formal_conjectures_authored"])
    integration_only = _row(24)
    assert integration_only["formal_conjectures_activity"] == "proof_link_edit"
    assert integration_only["lenses"]["all_authored"] is True
    assert integration_only["lenses"]["mathematical_work"] is False
    assert integration_only["mathematical_scope"] == "not_applicable"


def test_formal_conjectures_manifest_is_a_pinned_operational_source():
    manifest = yaml.safe_load(
        (HERE / "sources" / "formal-conjectures-activity.yaml").read_text()
    )
    inventory = json.loads((HERE / "graph" / "work-inventory.json").read_text())
    operational = json.loads((HERE / "graph" / "frontier-map.json").read_text())
    source_record = inventory["formal_conjectures_activity"]

    assert source_record["records"] == source_record["authored_problem_count"] == 136
    assert source_record["category_counts"] == manifest["summary"]["category_counts"]
    assert source_record["source"]["commit"] == manifest["source"]["pinned_commit"]
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", source_record["sha256"])
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", source_record["source"]["sha256"])

    nodes = [
        node for node in operational["nodes"]
        if node.get("activity_manifest") == "sources/formal-conjectures-activity.yaml"
    ]
    assert len(nodes) == 136
    assert {node["id"] for node in nodes} == {
        f"activity:fc-{row['category']}:{row['problem']}"
        for row in manifest["problems"]
    }
    assert {
        category: sum(node["kind"] == category for node in nodes)
        for category in manifest["summary"]["category_counts"]
    } == manifest["summary"]["category_counts"]
    assert all(node["plane"] == "activity" and node["accepted"] is False for node in nodes)
    assert all(node["commit"] == manifest["source"]["pinned_commit"] for node in nodes)
    assert operational["summary"]["formal_conjectures_activity_records"] == 136


def test_special_process_records_are_visible_but_outside_the_248_lens():
    for problem, kind in ((872, "prompt_authored"), (1082, "prior_art_adjudicated")):
        row = _row(problem)
        assert kind in row["activity_types"]
        assert not any(row["lenses"].values())
        assert row["lens_exclusion"] == "special_activity_outside_audited_authorship_baseline"


def test_graph_planes_are_separate_and_operational_edges_are_attributed():
    claims = json.loads((HERE / "graph" / "claim-graph.json").read_text())
    operational = json.loads((HERE / "graph" / "frontier-map.json").read_text())
    assert claims["schema"] == "vela.frontier_graph.claims.v0.1"
    assert claims["frontier_dependencies"] == [{
        "name": "formal-conjectures-frontier",
        "source": "git",
        "frontier_id": "vfr_97d7d25957384f80",
        "snapshot_hash": "sha256:4924adbbea6dfe288d14af03cf3d544f73c511df6b6ef8b938c8291685101444",
        "locator": (
            "https://github.com/constellate-science/formal-conjectures-frontier/"
            "tree/a143c351f8488e0c621598307e248373d9dc3374"
        ),
    }]
    assert claims["claim_boundary"]["federated_findings_are_referenced_not_copied"] is True
    assert all(node["kind"] == "finding" and node["state"] == "accepted"
               for node in claims["nodes"])
    assert not any(node["id"].startswith("vat_") for node in claims["nodes"])
    assert operational["schema"] == "vela.frontier_graph.v0.1"
    assert operational["summary"]["problems"] == 1217
    assert operational["summary"]["attempts"] == 249
    assert operational["summary"]["recovered_records"] == 31
    assert operational["summary"]["active_leases"] == 0
    assert operational["summary"]["pending_proposals"] == 12
    dependency_nodes = [node for node in operational["nodes"]
                        if node["kind"] == "frontier_dependency"]
    assert [node["frontier_id"] for node in dependency_nodes] == [
        "vfr_97d7d25957384f80"
    ]
    assert sum(node["kind"] == "proposal" for node in operational["nodes"]) == 12
    assert not any(node["kind"] == "proposal" for node in claims["nodes"])
    assert all({"trust", "source_root", "inferred"} <= set(edge)
               for edge in operational["edges"])
    problem_ids = {node["id"] for node in operational["nodes"] if node["kind"] == "problem"}
    assert problem_ids == {f"erdos:{problem}" for problem in range(1, 1218)}
    assert "erdos:396704" not in problem_ids
    assert "erdos:396705" not in problem_ids
    recovered_problems = {
        record["problem"]
        for record in yaml.safe_load(
            (HERE / "sources" / "recovered-attempts.yaml").read_text()
        )["records"]
    }
    assert not any(
        node["id"] in {
            f"activity:current:{problem}", f"activity:history:{problem}"
        }
        for problem in recovered_problems
        for node in operational["nodes"]
    )


def test_public_claim_graph_is_canonical_and_legacy_graph_stays_compatibility_only():
    canonical = HERE / "graph" / "claim-graph.json"
    public = HERE / "site" / "claim-graph.json"
    compatibility = HERE / "site" / "graph.json"

    assert public.read_bytes() == canonical.read_bytes()
    public_graph = json.loads(public.read_text())
    compatibility_graph = json.loads(compatibility.read_text())
    assert public_graph["schema"] == "vela.frontier_graph.claims.v0.1"
    assert all(node["kind"] == "finding" for node in public_graph["nodes"])
    assert compatibility_graph != public_graph
    assert any(node["kind"] == "problem" for node in compatibility_graph["nodes"])

    map_html = (HERE / "site" / "map.html").read_text()
    assert 'href="claim-graph.json">claim graph</a>' in map_html
    assert 'href="graph.json">compatibility graph</a>' in map_html
    assert 'href="graph.json">Claim graph JSON</a>' not in map_html


def test_public_map_renders_typed_records_without_silent_truncation():
    map_html = (HERE / "site" / "map.html").read_text()
    assert 'typeof item.assertion === "string"' in map_html
    assert "item.formal_statement.theorem" in map_html
    assert "item.mathematical_scope" in map_html
    assert "rows.slice(0, 10)" not in map_html
    assert '${rows.map(item =>' in map_html


def test_problem_shards_expose_all_drilldown_sections():
    expected = {
        "statement", "accepted", "residual_obligations", "activity",
        "proof_artifacts", "external_references", "witnesses", "receipts",
        "producers", "commits",
        "draft_proposals", "review_obligations", "nodes", "edges", "sources",
    }
    for problem in (23, 42, 92, 154, 617, 686, 730):
        detail = json.loads((HERE / "site" / "problems" / f"{problem}.json").read_text())
        assert expected <= set(detail)
        assert detail["problem"] == problem
        assert detail["frontier_root"] == _work_index()["frontier_root"]


def test_registered_proof_artifacts_are_complete_and_immutable():
    artifacts = []
    references = []
    for path in sorted((HERE / "site" / "problems").glob("*.json")):
        detail = json.loads(path.read_text())
        artifacts.extend((detail["problem"], artifact)
                         for artifact in detail["proof_artifacts"])
        references.extend((detail["problem"], reference)
                          for reference in detail["external_references"])

    assert len(artifacts) == 23
    assert len({
        (artifact["repository"], artifact["commit"], artifact["path"],
         artifact["content_digest"])
        for _, artifact in artifacts
    }) == len(artifacts)
    for problem, artifact in artifacts:
        assert artifact["registered_artifact"] is True, problem
        assert re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", artifact["repository"])
        assert re.fullmatch(r"[0-9a-f]{40}", artifact["commit"])
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", artifact["content_digest"])
        assert artifact["path"] and not artifact["path"].startswith("/")
        assert (
            f"/blob/{artifact['commit']}/{artifact['path']}" in artifact["url"]
        )
        assert "/blob/main/" not in artifact["url"]
        assert "/Users/" not in artifact["url"] and "/home/" not in artifact["url"]
        if artifact["artifact_kind"].startswith("lean_"):
            assert artifact["declaration"], problem

    developed = [artifact for _, artifact in artifacts if artifact.get("git_blob")]
    assert len(developed) == 7
    assert {problem for problem, artifact in artifacts if artifact.get("git_blob")} == {
        23, 154, 617, 686, 699, 727, 730,
    }
    assert all(
        artifact["repository"] == "williamjblair/lean-proofs"
        and artifact["commit"] == "eab646ceae7f270c024d5d08a8917305b07fd35d"
        and re.fullmatch(r"[0-9a-f]{40}", artifact["git_blob"])
        and artifact["machine_evidence"]["status"] == artifact["machine_status"]
        for artifact in developed
    )
    assert all(reference["registered_artifact"] is False for _, reference in references)
    assert all(reference["reference_kind"] == "hosted_proof_link"
               for _, reference in references)


def test_developed_campaign_drafts_are_visible_but_never_accepted_state():
    expected = {23: 2, 154: 1, 617: 1, 686: 2, 699: 2, 727: 2, 730: 2}
    for problem, count in expected.items():
        detail = json.loads((HERE / "site" / "problems" / f"{problem}.json").read_text())
        assert len(detail["draft_proposals"]) == count
        assert all(draft["status"] == "pending_review" for draft in detail["draft_proposals"])
        assert all(draft["accepted"] is False for draft in detail["draft_proposals"])
    assert any("multi-stub" in item for item in _row_detail(23)["residual_obligations"])


def test_frontier_duplicate_is_reconciled_without_a_json_merge():
    report = json.loads((HERE / "graph" / "frontier-reconciliation.json").read_text())
    assert report["canonical"]["repository"] == "formal_conjectures_frontier"
    assert report["canonical"]["public_source"] is True
    assert report["duplicate"]["public_source"] is False
    assert report["comparison"]["common"] == 18
    assert report["comparison"]["canonical_only"] == 15
    assert report["comparison"]["duplicate_only"] == 8
    assert report["comparison"]["unique_events"] == 41
    assert report["comparison"]["common_events_byte_identical"] is True
    assert report["comparison"]["disposition_counts"] == {
        "deferred_proposal_required": 4,
        "ignored_with_reason": 4,
        "mapped_canonical": 15,
        "mapped_duplicate": 18,
    }
    assert report["disposition"]["json_merge_performed"] is False
    assert report["disposition"]["findings_copied_into_erdos_state"] is False
    assert len(report["disposition"]["duplicate_only_events_require_proposal"]) == 4
    assert len(report["disposition"]["duplicate_only_rejections_ignored"]) == 4

    rows = report["event_dispositions"]
    assert len(rows) == 41
    assert len({row["event_id"] for row in rows}) == 41
    assert all(row.get("kind") for row in rows)
    assert all(row.get("target_finding_id") or row.get("target_proposal_id") for row in rows)
    deferred = [row for row in rows
                if row["classification"] == "deferred_proposal_required"]
    ignored = [row for row in rows if row["classification"] == "ignored_with_reason"]
    assert all(row["kind"] == "finding.asserted" for row in deferred)
    assert all(row["proposal_required"] is True for row in deferred)
    assert all(row["target_finding_id"].startswith("vf_") for row in deferred)
    assert all(row["target_proposal_id"].startswith("vpr_") for row in deferred)
    assert all(row["kind"] == "review.rejected" for row in ignored)
    assert all("truth state" in row["reason"] for row in ignored)


def test_public_outputs_have_no_local_absolute_paths_or_wall_clock_field():
    public_paths = [
        HERE / "targets.json",
        HERE / "site" / "work-index.json",
        HERE / "graph" / "claim-graph.json",
        HERE / "graph" / "frontier-map.json",
        HERE / "graph" / "work-inventory.json",
        *sorted((HERE / "site" / "problems").glob("*.json")),
    ]
    for path in public_paths:
        text = path.read_text()
        assert "/Users/" not in text, path
        assert "/home/" not in text, path
        assert '"generated_at"' not in text, path

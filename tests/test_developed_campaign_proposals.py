from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
PACK = ROOT / "review" / "developed-campaign-proposals.v1.yaml"


def load_pack():
    return yaml.safe_load(PACK.read_text())


def iter_records(pack):
    for campaign in pack["campaigns"]:
        yield campaign["problem"], campaign["claim"]
        for residual in campaign["residuals"]:
            yield campaign["problem"], residual


def test_developed_campaign_pack_has_one_claim_for_each_target():
    pack = load_pack()
    assert pack["schema"] == "erdos-frontier.developed-campaign-proposals.v1"
    assert pack["source_repository"]["commit"] == (
        "eab646ceae7f270c024d5d08a8917305b07fd35d"
    )
    assert [campaign["problem"] for campaign in pack["campaigns"]] == [
        23,
        154,
        617,
        686,
        699,
        727,
        730,
    ]


def test_proposals_keep_status_dimensions_orthogonal():
    pack = load_pack()
    allowed_upstream = {"open", "proved", "disproved"}
    allowed_scope = {"full", "partial", "conditional", "bounded", "variant"}
    allowed_trust = {"declared", "recorded", "signed", "machine_reproduced", "lean_attested"}
    allowed_lifecycle = {"active", "banked", "paused", "superseded", "historical"}

    for campaign in pack["campaigns"]:
        assert campaign["upstream_state"] in allowed_upstream
        for _problem, record in iter_records({"campaigns": [campaign]}):
            assert record["mathematical_scope"] in allowed_scope
            assert record["trust"] in allowed_trust
            assert record["lifecycle"] in allowed_lifecycle
            assert record["statement_fidelity"]["status"] == "pending_human_review"
            assert "machine_status" in record


def test_proposals_use_direct_submission_and_pending_review():
    pack = load_pack()
    policy = pack["draft_policy"]
    assert policy["submission_schema"] == "vela.submission.v1"
    assert policy["workflow"] == {
        "select": "next",
        "brief": "start",
        "submit": "submit",
        "verify": "verification import",
        "decision": "human review",
    }
    assert policy["session_required"] is False
    assert policy["expected_route"] == "pending_review"
    assert policy["agent_finalization_forbidden"] is True
    assert policy["human_acceptance_required"] is True

    proposed = []
    duplicates = []
    for problem, record in iter_records(pack):
        if record["disposition"] == "propose":
            proposed.append((problem, record["proposal_key"]))
            assert "draft_command" not in record
            assert record["assertion"]
            assert record["activity"] in policy["submission_mapping"]["type"]
            assert record["statement_fidelity"]["status"] == "pending_human_review"
        else:
            assert record["disposition"] == "skip_duplicate"
            duplicates.append((problem, record["duplicate_finding_id"]))
            assert "draft_command" not in record

    assert len(proposed) == 12
    assert duplicates == [(617, "vf_da8d51a6cae5ec11")]


def test_artifact_locators_are_pinned_and_public_safe():
    pack = load_pack()
    for campaign in pack["campaigns"]:
        artifact = campaign["claim"]["artifact"]
        assert artifact["path"]
        assert artifact["declaration"]
        assert len(artifact["git_blob"]) == 40
        assert artifact["sha256"].startswith("sha256:")
        assert "/Users/" not in artifact["path"]


def test_617_residual_is_an_exact_duplicate_not_a_second_proposal():
    pack = load_pack()
    campaign = next(c for c in pack["campaigns"] if c["problem"] == 617)
    residual = campaign["residuals"][0]
    existing = yaml.safe_load("""\
id: vf_da8d51a6cae5ec11
""")
    assert residual["disposition"] == "skip_duplicate"
    assert residual["duplicate_finding_id"] == existing["id"]

"""The corpus graph is a derived index — these pin its honesty properties:
deterministic from the same inputs, referentially intact, and in exact parity
with the audit's own discrepancy list (no phantom contradictions)."""
import json
import pathlib
import sys

import pytest
import yaml

HERE = pathlib.Path(__file__).parent.parent
GRAPH = HERE / "graph" / "corpus-graph.json"
sys.path.insert(0, str(HERE / "scripts"))

from build_graph import GraphBuildError, build  # noqa: E402


@pytest.fixture
def signed_frontier(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "frontier.json"
    path.write_text(json.dumps({
        "statement_attestations": [
            {
                "id": "vsa_test_faithful",
                "informal_ref": "erdosproblems.com/246",
                "attested_by": "reviewer:test",
                "verdict": "faithful",
            },
            {
                "id": "vsa_test_variant",
                "informal_ref": "erdosproblems.com/205",
                "attested_by": "reviewer:test",
                "verdict": "variant",
            },
        ]
    }))
    return path


def _build(frontier_path: pathlib.Path) -> bytes:
    return (json.dumps(build(frontier_path), indent=1) + "\n").encode()


def test_graph_is_deterministic(signed_frontier: pathlib.Path):
    a = _build(signed_frontier)
    b = _build(signed_frontier)
    assert a == b, "same inputs must produce byte-identical graphs"


def test_missing_signed_frontier_fails_closed(tmp_path: pathlib.Path):
    missing = tmp_path / "frontier.json"
    with pytest.raises(GraphBuildError, match="signed frontier projection is missing"):
        build(missing)


def test_frontier_without_signed_source_fails_closed(tmp_path: pathlib.Path):
    incomplete = tmp_path / "frontier.json"
    incomplete.write_text("{}")
    with pytest.raises(GraphBuildError, match="no statement_attestations list"):
        build(incomplete)


def test_every_edge_endpoint_exists():
    doc = json.loads(GRAPH.read_text())
    ids = {n["id"] for n in doc["nodes"]}
    dangling = [(e["from"], e["to"]) for e in doc["edges"]
                if e["from"] not in ids or e["to"] not in ids]
    assert not dangling, f"dangling edge endpoints: {dangling[:5]}"


def test_contradictions_match_the_audit():
    doc = json.loads(GRAPH.read_text())
    verdicts = json.loads((HERE / "site" / "verdicts.json").read_text())
    graph_disc = sorted(int(e["from"].split(":")[1]) for e in doc["edges"]
                        if e["kind"] == "contradicts" and e["trust"] == "recorded")
    assert graph_disc == sorted(verdicts["summary"]["discrepancies"]), (
        "the graph's recorded contradictions must equal the audit's "
        "discrepancy list — no phantom edges, none missing")


def test_signed_tier_matches_the_frontier(signed_frontier: pathlib.Path):
    doc = build(signed_frontier)
    frontier = json.loads(signed_frontier.read_text())
    signed_edges = [e for e in doc["edges"] if e["trust"] == "signed"]
    atts = frontier.get("statement_attestations") or []
    assert len(signed_edges) == len(atts), (
        "every signed edge must come from a real vsa_ in the spine, 1:1")


def test_campaign_statements_are_in_the_graph():
    """Every problem in a campaign batch that is past drafting (staged draft or
    open PR) must have a statement node — the graph indexes the campaign's own
    statements, not only what conjectures.json already lists."""
    doc = json.loads(GRAPH.read_text())
    ids = {n["id"] for n in doc["nodes"]}
    camp = yaml.safe_load((HERE / "campaign.yaml").read_text())
    missing = [p for b in camp["batches"] if b["state"] != "merged"
               for p in b["problems"] if f"fc:{p}" not in ids]
    assert not missing, f"campaign statements absent from the graph: {missing}"


def test_attestations_land_on_the_statement_when_it_exists():
    """A vsa edge may fall back to the erdos: problem only when no statement
    node exists at all (e.g. fidelity verdicts on hosted proofs with no FC
    file); it must never bypass an fc: node that is in the graph."""
    doc = json.loads(GRAPH.read_text())
    ids = {n["id"] for n in doc["nodes"]}
    bypassed = [(e["from"], e["to"]) for e in doc["edges"]
                if e["from"].startswith("vsa:") and e["to"].startswith("erdos:")
                and e["to"].replace("erdos:", "fc:") in ids]
    assert not bypassed, f"vsa edges bypass an existing statement: {bypassed}"

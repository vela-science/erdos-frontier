"""The corpus graph is a derived index — these pin its honesty properties:
deterministic from the same inputs, referentially intact, and in exact parity
with the audit's own discrepancy list (no phantom contradictions)."""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent.parent
GRAPH = HERE / "graph" / "corpus-graph.json"


def _build() -> bytes:
    subprocess.run([sys.executable, "scripts/build_graph.py"],
                   cwd=HERE, check=True, capture_output=True)
    return GRAPH.read_bytes()


def test_graph_is_deterministic():
    a = _build()
    b = _build()
    assert a == b, "same inputs must produce byte-identical graphs"


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


def test_signed_tier_matches_the_frontier():
    doc = json.loads(GRAPH.read_text())
    frontier = json.loads((HERE / "frontier.json").read_text())
    signed_edges = [e for e in doc["edges"] if e["trust"] == "signed"]
    atts = frontier.get("statement_attestations") or []
    assert len(signed_edges) == len(atts), (
        "every signed edge must come from a real vsa_ in the spine, 1:1")

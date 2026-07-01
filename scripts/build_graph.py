#!/usr/bin/env python3
"""Materialize the Erdős corpus as a typed frontier graph — the Vela object
model over every ingested source, derived and deterministic.

Two tiers, deliberately distinct (the substrate enforces this: an agent may not
author truth-bearing findings):

  the signed spine   .vela/ + frontier.json — human-signed verdicts only
  the corpus graph   THIS — an index of what the sources declare, typed in the
                     substrate's EdgeKind vocabulary, with a trust tier on
                     every edge, rebuilt from source locks by the reducer

Nodes  erdos:<n>        the boxed problem (1,217)
       fc:<n>           the Formal Conjectures statement
       proof:<src>:<n>  a hosted Lean proof artifact
       cond:<key>       a load-bearing condition (assumed theorem / hypothesis)
       wiki:<n>         the frozen AI-contributions wiki claim
       vsa:<id>         a SIGNED statement-fidelity attestation (from the spine)

Edges  fc:<n>          derived_from  erdos:<n>       (formalization)     declared
       proof:s:<n>     supports      erdos:<n>       (unconditional)     machine
       proof:s:<n>     depends_on    cond:<k>        (conditional on)    machine
       proof:a:<n>     replicates    proof:b:<n>     (verdicts agree)    machine
       wiki:<n>        contradicts   proof:s:<n>     (the discrepancy)   recorded
       vsa:<id>        supports      fc:<n>          (faithful)          signed
       vsa:<id>        contradicts   fc:<n>          (unfaithful)        signed
       vsa:<id>        specializes   fc:<n>          (variant)           signed

Outputs
  graph/corpus-graph.json    the full typed model (nodes + edges + provenance)
  graph/corpus-edges.jsonl   {"from","to","kind"} lines — the shape
                             `vela atlas decl-blast --edges` loads
  site/graph.json            compact feed for the site's map view

Usage:  python scripts/build_graph.py
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
STATUS = HERE / "site" / "status.json"
VERDICTS = HERE / "site" / "verdicts.json"
FRONTIER = HERE / "frontier.json"
LOCK = HERE / "sources.lock.json"
OUT_DIR = HERE / "graph"
SITE_GRAPH = HERE / "site" / "graph.json"

VERDICT_EDGE = {"faithful": "supports", "unfaithful": "contradicts",
                "variant": "specializes"}


def build() -> dict:
    status = json.loads(STATUS.read_text())
    verdicts = json.loads(VERDICTS.read_text())
    conditions = verdicts["summary"].get("conditions") or []
    frontier = json.loads(FRONTIER.read_text()) if FRONTIER.exists() else {}

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def node(nid: str, kind: str, label: str, **attrs) -> str:
        if nid not in nodes:
            nodes[nid] = {"id": nid, "kind": kind, "label": label,
                          **{k: v for k, v in attrs.items() if v not in (None, "", [])}}
        return nid

    def edge(frm: str, to: str, kind: str, trust: str, **attrs) -> None:
        edges.append({"from": frm, "to": to, "kind": kind, "trust": trust,
                      **{k: v for k, v in attrs.items() if v not in (None, "", [])}})

    # condition nodes first (their keys canonicalize hypothesis/axiom families)
    cond_by_problem: dict[int, list[str]] = {}
    for c in conditions:
        cid = node(f"cond:{c['key']}", "condition", c["name"],
                   tier=c["tier"], description=c.get("description"),
                   leverage=c["leverage"])
        for p in c["problems"]:
            cond_by_problem.setdefault(p, []).append(cid)

    for row in status["rows"]:
        n = row["problem"]
        pid = node(f"erdos:{n}", "problem", f"Erdős {n}",
                   state=row.get("erdos_state"), bucket=row.get("bucket"),
                   url=row.get("erdos_url"))

        fc = row.get("fc") or {}
        if fc.get("has_file") or fc.get("path"):
            fid = node(f"fc:{n}", "statement", fc.get("theorem") or f"FC {n}",
                       url=fc.get("fc_url"), linked=bool(fc.get("linked")))
            edge(fid, pid, "derived_from", "declared",
                 evidence="FormalConjectures file exists")

        machine = row.get("machine") or {}
        proof_ids = []
        for link in row.get("proof_links") or []:
            src = link.get("source") or "unknown"
            prid = node(f"proof:{src}:{n}", "proof", f"{src} proof of {n}",
                        url=link.get("url"), state=link.get("state"))
            proof_ids.append((prid, src))
            audited_here = machine.get("source") == src
            verdict = machine.get("verdict") if audited_here else None
            if verdict == "unconditional":
                edge(prid, pid, "supports", "machine",
                     evidence="kernel-clean, no undischarged hypothesis")
            elif verdict == "conditional":
                # still a proof OF this problem — the conditionality is expressed
                # by the depends_on edges, not by severing the linkage
                edge(prid, pid, "supports", "machine", conditional=True,
                     evidence="holds only under the conditions it depends on")
                for cid in cond_by_problem.get(n, []):
                    edge(prid, cid, "depends_on", "machine",
                         evidence="declared by the proof's own axioms/signature")
            elif link.get("complete") and not link.get("conditional"):
                # indexed complete but not machine-audited: producer's declaration
                edge(prid, pid, "supports", "declared",
                     evidence="producer-declared complete; not yet machine-audited")

        # dual-source replication: audited verdict + another complete proof
        if machine.get("verdict") and len(proof_ids) > 1:
            primary = next((p for p, s in proof_ids if s == machine.get("source")), None)
            for prid, src in proof_ids:
                if primary and prid != primary:
                    edge(prid, primary, "replicates", "machine",
                         evidence="independent hosted proof of the same problem")

        wiki = row.get("wiki") or {}
        if wiki.get("outcome_label"):
            wid = node(f"wiki:{n}", "claim", f"wiki: {wiki['outcome_label']}",
                       ai_systems=wiki.get("ai_systems"))
            if row.get("discrepancy") and machine.get("source"):
                edge(wid, f"proof:{machine['source']}:{n}", "contradicts",
                     "recorded",
                     evidence="wiki records a full solution; the machine audit "
                              "finds the proof conditional")

    # the signed spine: statement-fidelity attestations
    for att in frontier.get("statement_attestations") or []:
        ref = str(att.get("informal_ref") or "")
        num = "".join(ch for ch in ref.split("/")[-1] if ch.isdigit())
        if not num:
            continue
        n = int(num)
        vid = node(f"vsa:{att.get('id', 'unknown')}", "attestation",
                   f"signed {att.get('verdict')} — Erdős {n}",
                   reviewer=att.get("attested_by"), verdict=att.get("verdict"))
        target = f"fc:{n}" if f"fc:{n}" in nodes else f"erdos:{n}"
        kind = VERDICT_EDGE.get(att.get("verdict"), "supports")
        edge(vid, target, kind, "signed",
             evidence=f"vsa signed by {att.get('attested_by')}")

    # deterministic ordering
    node_list = [nodes[k] for k in sorted(nodes)]
    edges.sort(key=lambda e: (e["from"], e["to"], e["kind"]))

    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    return {
        "schema": "erdos-frontier.corpus-graph.v1",
        "note": ("Derived index of what the ingested sources declare — typed in "
                 "the Vela EdgeKind vocabulary with a trust tier per edge. Not "
                 "signed state: the signed spine is .vela/ + frontier.json."),
        "source_locks": {k: (v.get("sha256") or "")[:16]
                         for k, v in (lock.get("sources") or {}).items()},
        "counts": {
            "nodes": len(node_list),
            "edges": len(edges),
            "by_node_kind": _count(node_list, "kind"),
            "by_edge_kind": _count(edges, "kind"),
            "by_trust": _count(edges, "trust"),
        },
        "nodes": node_list,
        "edges": edges,
    }


def _count(items, key):
    out: dict[str, int] = {}
    for it in items:
        out[it[key]] = out.get(it[key], 0) + 1
    return dict(sorted(out.items()))


def main() -> int:
    doc = build()
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "corpus-graph.json").write_text(json.dumps(doc, indent=1) + "\n")
    # The JSONL projection is DEPENDENCY-directed for `vela atlas decl-blast`
    # (every line reads "from depends on to"; retraction flows to dependents).
    # A `supports` edge (proof -> problem) therefore flips: the problem's solved
    # status DEPENDS ON the proof. All other kinds already point at what they
    # rest on (proof->condition, statement->problem, claim->proof, vsa->statement).
    with (OUT_DIR / "corpus-edges.jsonl").open("w") as f:
        for e in doc["edges"]:
            frm, to = e["from"], e["to"]
            if e["kind"] == "supports":
                frm, to = to, frm
            f.write(json.dumps({"from": frm, "to": to, "kind": e["kind"]}) + "\n")
    # compact site feed: drop verbose evidence, keep the map's needs
    site = {
        "generated_from": doc["source_locks"],
        "counts": doc["counts"],
        "nodes": [{k: v for k, v in n.items() if k != "description"}
                  for n in doc["nodes"]],
        "edges": [{k: e[k] for k in ("from", "to", "kind", "trust")}
                  for e in doc["edges"]],
    }
    SITE_GRAPH.write_text(json.dumps(site, separators=(",", ":")) + "\n")
    c = doc["counts"]
    print(f"corpus graph: {c['nodes']} nodes, {c['edges']} edges")
    print(f"  node kinds: {c['by_node_kind']}")
    print(f"  edge kinds: {c['by_edge_kind']}")
    print(f"  trust:      {c['by_trust']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

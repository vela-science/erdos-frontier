import hashlib
import json
import subprocess
from pathlib import Path

import yaml

import erdos_frontier

from erdos_frontier import (
    Claim,
    _wiki_summary,
    apply_machine_audit,
    build_proofs,
    build_status,
    classify,
    load_candidate_claims,
    load_fidelity,
    load_machine_audit,
    load_wiki_registry,
    parse_fidelity,
)


def test_witnesses_are_ordinary_git_blobs_without_checkout_filters():
    witnesses = sorted(Path("witnesses").glob("*.witness.json"))
    assert len(witnesses) == 38

    checked = subprocess.run(
        ["git", "check-attr", "filter", "--", *(str(path) for path in witnesses)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert {line.rsplit(": ", 1)[-1] for line in checked.stdout.splitlines()} == {"unset"}

    for witness in witnesses:
        payload = witness.read_bytes()
        assert not payload.startswith(b"version https://git-lfs.github.com/spec/v1")
        json.loads(payload)


def test_machine_audit_overrides_flags_and_buckets_hypothesis_conditional():
    # The Lean extractor found a problem-defined named Prop assumed as a hypothesis
    # (kernel-clean, #print-axioms-invisible). It must override a producer's
    # (wrong) "complete" flag and route to the precise bucket.
    proofs = {1148: {"complete": True, "conditional": False, "partial": False, "sources": {}}}
    audit = {1148: {"problem": 1148, "machine_verdict": "conditional",
                    "named_assumptions": ["h_duke : Erdos1148.DukeTheoremStatement"],
                    "non_kernel_axioms": []}}
    apply_machine_audit(proofs, audit)
    assert proofs[1148]["conditional"] is True
    assert proofs[1148]["complete"] is False
    bucket = classify(1148, {"has_file": True, "linked": False}, proofs[1148], [], None, None)
    assert bucket == "hypothesis-conditional"


def test_machine_audit_axiom_conditional_is_docstring_not_hypothesis():
    # A proof conditional via a non-kernel AXIOM (caught by #print axioms, no named
    # hypothesis) is the generic "docstring" bucket, not "hypothesis-conditional".
    proofs = {694: {"complete": True, "conditional": False, "partial": False, "sources": {}}}
    audit = {694: {"problem": 694, "machine_verdict": "conditional",
                   "named_assumptions": [], "non_kernel_axioms": ["mertens_product", "linnik_dvd"]}}
    apply_machine_audit(proofs, audit)
    assert classify(694, {"has_file": True, "linked": False}, proofs[694], [], None, None) == "docstring"


def erdos_records(*problems):
    return {
        problem: {
            "number": problem,
            "status": {"state": "solved"},
            "formalized": {"state": "yes"},
        }
        for problem in problems
    }


def complete_plby_proofs(*problems):
    return build_proofs([{"key": f"Erdos{problem}"} for problem in problems], [], {})


def status_for(problem, *, proof=None, fc=None, claims=None, override=None,
               fidelity=None, wiki=None):
    payload = build_status(
        erdos=erdos_records(problem),
        fc={problem: fc} if fc else {},
        proofs={problem: proof} if proof else {},
        claims_by_problem={problem: claims} if claims else {},
        claims_available=True,
        overrides={problem: override} if override else {},
        fidelity={problem: fidelity} if fidelity else {},
        wiki={problem: wiki} if wiki else {},
        generated_at="2026-06-29",
    )
    return payload, payload["rows"][0]


def test_plby_conditional_key_presence_counts_even_when_value_is_null():
    proofs = build_proofs([{"key": "Erdos1148", "conditional": None}], [], {})

    proof = proofs[1148]
    assert proof["complete"] is False
    assert proof["conditional"] is True
    assert proof["sources"]["plby"]["state"] == "conditional"


def test_jayyhk_complete_axiomatic_and_trust_extended_states():
    proofs = build_proofs(
        [],
        [
            {"number": 1, "proof": {"state": "complete"}},
            {"number": 2, "proof": {"state": "axiomatic"}},
            {"number": 3, "proof": {"state": "trust_extended"}},
        ],
        {},
    )

    assert proofs[1]["complete"] is True
    assert proofs[1]["conditional"] is False
    assert proofs[2]["complete"] is False
    assert proofs[2]["conditional"] is True
    assert proofs[3]["complete"] is False
    assert proofs[3]["conditional"] is True


def test_complete_proof_plus_open_pr_becomes_in_pr_with_claim_details():
    proof = complete_plby_proofs(199)[199]
    claim = Claim(number=4343, title="Erdos batch", url="https://example.test/pr/4343", head_ref="batch")

    _, row = status_for(199, proof=proof, claims=[claim])

    assert row["bucket"] == "in-pr"
    assert row["claims"] == [
        {
            "number": 4343,
            "title": "Erdos batch",
            "url": "https://example.test/pr/4343",
            "head_ref": "batch",
        }
    ]


def test_mismatch_override_beats_actionable_statement():
    proof = complete_plby_proofs(214)[214]

    _, row = status_for(
        214,
        proof=proof,
        override={"bucket": "mismatch", "reason": "quantifier mismatch"},
    )

    assert row["bucket"] == "mismatch"
    assert row["override"]["reason"] == "quantifier mismatch"


def test_hypothesis_conditional_override_prevents_statement_bucket():
    proof = complete_plby_proofs(1148)[1148]

    _, row = status_for(
        1148,
        proof=proof,
        override={"bucket": "hypothesis-conditional", "reason": "extra theorem hypothesis"},
    )

    assert row["bucket"] == "hypothesis-conditional"


def test_330_override_prevents_unsafe_link_bucket():
    proof = complete_plby_proofs(330)[330]
    fc = {
        "has_file": True,
        "linked": False,
        "path": "FormalConjectures/ErdosProblems/330.lean",
        "formal_proof_link": None,
    }

    _, row = status_for(
        330,
        proof=proof,
        fc=fc,
        override={"bucket": "needs-statement-update", "reason": "answer still open"},
    )

    assert row["bucket"] == "needs-statement-update"


def test_status_payload_shape_preserves_actionable_classification():
    proofs = complete_plby_proofs(24, 214)
    payload = build_status(
        erdos=erdos_records(24, 214),
        fc={},
        proofs=proofs,
        claims_by_problem={},
        claims_available=True,
        overrides={214: {"bucket": "mismatch", "reason": "not the boxed statement"}},
        generated_at="2026-06-29",
    )

    encoded = json.dumps(payload)
    decoded = json.loads(encoded)
    assert decoded["counts"]["statement"] == 1
    assert decoded["counts"]["mismatch"] == 1
    assert {row["problem"]: row["bucket"] for row in decoded["rows"]} == {
        24: "statement",
        214: "mismatch",
    }

    assert decoded["rows"][0]["recommended_action"]
    assert decoded["rows"][1]["override"]["reason"] == "not the boxed statement"


FIDELITY_DOC_214 = {
    "statement_attestations": [
        {
            "id": "vsa_test214",
            "target": "vf_erdos_214",
            "verdict": "unfaithful",
            "informal_ref": "erdosproblems.com/214",
            "formal_ref": "google-deepmind/formal-conjectures@HEAD:ErdosProblems/214.lean",
            "formal_statement_hash": "sha256:deadbeef",
            "attested_by": "reviewer:will-blair",
            "note": "proves an existential coloring result, not the universal boxed problem",
            "signed_at": "2026-06-29T00:00:00Z",
        }
    ]
}


def test_parse_fidelity_keys_on_problem_and_marks_provenance():
    parsed = parse_fidelity(FIDELITY_DOC_214, source="hub")

    assert set(parsed) == {214}
    record = parsed[214]
    assert record["verdict"] == "unfaithful"
    assert record["reviewer"] == "reviewer:will-blair"
    assert record["signed"] is True
    assert record["source"] == "hub"


def test_fidelity_verdict_flows_to_mismatch_bucket_and_row_field():
    fidelity = parse_fidelity(FIDELITY_DOC_214, source="hub")[214]

    _, row = status_for(214, fidelity=fidelity)

    assert row["bucket"] == "mismatch"
    assert row["fidelity"] == {
        "verdict": "unfaithful",
        "reviewer": "reviewer:will-blair",
        "signed": True,
        "note": "proves an existential coloring result, not the universal boxed problem",
        "formal_ref": "google-deepmind/formal-conjectures@HEAD:ErdosProblems/214.lean",
        "source": "hub",
        "stale": None,
    }


def test_signed_verdict_supersedes_a_matching_override():
    fidelity = parse_fidelity(FIDELITY_DOC_214, source="cache")[214]

    # An override would say defer; the signed unfaithful verdict wins -> mismatch.
    _, row = status_for(
        214,
        fidelity=fidelity,
        override={"bucket": "defer", "reason": "stale human note"},
    )

    assert row["bucket"] == "mismatch"
    assert row["fidelity"]["source"] == "cache"


def test_faithful_verdict_routes_to_link_when_fc_has_file_else_statement():
    faithful = {
        "verdict": "faithful",
        "reviewer": "reviewer:will-blair",
        "signed": True,
        "note": "",
        "source": "hub",
    }

    _, with_file = status_for(
        24,
        fc={"has_file": True, "linked": False, "path": "p", "formal_proof_link": None},
        fidelity=faithful,
    )
    _, without_file = status_for(24, fidelity=dict(faithful))

    assert with_file["bucket"] == "link"
    assert without_file["bucket"] == "statement"


def test_load_fidelity_missing_source_degrades_to_empty(tmp_path):
    # A path that does not exist (the 404 analogue) yields an empty column.
    missing = tmp_path / "no-such-fidelity.json"

    assert load_fidelity(str(missing)) == {}


def test_missing_fidelity_leaves_row_field_empty_without_crashing():
    proof = complete_plby_proofs(24)[24]

    _, row = status_for(24, proof=proof, fidelity=None)

    assert row["fidelity"] is None
    assert row["bucket"] == "statement"


def test_load_fidelity_reads_committed_cache_file():
    # The committed sources/fidelity_cache.json is the offline fallback / seed.
    cached = load_fidelity("sources/fidelity_cache.json")

    assert 214 in cached
    assert cached[214]["source"] == "cache"
    assert cached[214]["signed"] is True


# --- frozen AI-contributions wiki: registry + the discrepancy view ----------

WIKI_FULL_LEAN = [
    {"section": "1(a)", "section_name": "AI standalone",
     "ai_systems": ["DeepMind prover agent"], "date": "21 Feb, 2026",
     "outcome": {"color": "yellow", "label": "Solution to variant problem (Lean)", "lean": True}},
    {"section": "1(a)", "section_name": "AI standalone",
     "ai_systems": ["DeepMind prover agent"], "date": "30 Mar, 2026",
     "outcome": {"color": "green", "label": "Full solution (Lean)", "lean": True}},
]


def machine_conditional_proof(problem, *, named=(), axioms=()):
    proofs = complete_plby_proofs(problem)
    apply_machine_audit(proofs, {problem: {
        "problem": problem, "machine_verdict": "conditional",
        "named_assumptions": list(named), "non_kernel_axioms": list(axioms)}})
    return proofs[problem]


def machine_unconditional_proof(problem):
    proofs = complete_plby_proofs(problem)
    apply_machine_audit(proofs, {problem: {
        "problem": problem, "machine_verdict": "unconditional",
        "named_assumptions": [], "non_kernel_axioms": []}})
    return proofs[problem]


def test_wiki_summary_collapses_entries_to_strongest_claim():
    s = _wiki_summary(WIKI_FULL_LEAN)
    assert s["claims_full_solution"] is True   # a green "Full solution" entry exists
    assert s["claims_lean"] is True            # at least one (Lean) entry
    assert s["claimed_color"] == "green"       # strongest non-red colour
    assert s["ai_systems"] == ["DeepMind prover agent"]
    assert s["has_incorrect"] is False


def test_wiki_claim_plus_conditional_proof_flags_discrepancy():
    # The frozen wiki records 1148 as a full solution; the hosted Lean proof we
    # load assumes DukeTheoremStatement as a parameter -> the wedge made visible.
    proof = machine_conditional_proof(1148, named=["h : Erdos1148.DukeTheoremStatement"])
    payload, row = status_for(1148, proof=proof, wiki=_wiki_summary(WIKI_FULL_LEAN))

    assert row["wiki"]["claims_full_solution"] is True
    assert row["discrepancy"] is True
    assert 1148 in payload["discrepancies"]


def test_no_discrepancy_when_audited_proof_is_unconditional():
    # The celebrated proofs (#728 etc.) come out unconditional: no false flag.
    proof = machine_unconditional_proof(728)
    _, row = status_for(728, proof=proof, wiki=_wiki_summary(WIKI_FULL_LEAN))

    assert row["wiki"]["claims_full_solution"] is True
    assert row["discrepancy"] is False


def test_row_without_wiki_entry_has_no_claim_or_discrepancy():
    proof = machine_conditional_proof(999, named=["h : Erdos999.Hyp"])
    _, row = status_for(999, proof=proof)

    assert row["wiki"] is None
    assert row["discrepancy"] is False


def test_load_wiki_registry_reads_committed_snapshot():
    # The committed sources/wiki/registry.json is the frozen-wiki seed.
    reg = load_wiki_registry()
    assert 728 in reg
    assert reg[728]["claims_full_solution"] is True
    assert reg[728]["claims_lean"] is True


def test_machine_audit_merges_repo_feeds_keeping_strongest_verdict(tmp_path):
    # Two proof repos audit #12; an unconditional proof in one settles it over a
    # conditional proof in the other. The legacy audit_feed.json is tagged plby.
    (tmp_path / "audit_feed.json").write_text(json.dumps([
        {"problem": 12, "machine_verdict": "conditional",
         "named_assumptions": ["h : Erdos12.Hyp"], "non_kernel_axioms": []},
        {"problem": 99, "machine_verdict": "incomplete",
         "named_assumptions": [], "non_kernel_axioms": []},
    ]))
    (tmp_path / "audit_feed_alphaproof.json").write_text(json.dumps([
        {"problem": 12, "machine_verdict": "unconditional",
         "named_assumptions": [], "non_kernel_axioms": []},
    ]))

    merged = load_machine_audit(tmp_path)

    assert merged[12]["machine_verdict"] == "unconditional"  # strongest wins
    assert merged[12]["source"] == "alphaproof"
    assert merged[99]["source"] == "plby"                    # legacy file -> plby


def test_staging_gate_holds_a_celebrated_proof_flag_until_cleared():
    # A conditional flag on a celebrated proof (#728) must NOT auto-publish: a false
    # positive on a Tao-accepted proof is costly. It is held for human review.
    proof = machine_conditional_proof(728, named=["h : Erdos728.Hyp"])
    payload, row = status_for(728, proof=proof, wiki=_wiki_summary(WIKI_FULL_LEAN))

    assert row["held_for_review"] is True
    assert row["discrepancy"] is False                       # suppressed while held
    assert 728 in payload["held_for_review"]

    assert 728 in payload["held_for_review"]
    assert 728 not in payload["discrepancies"]


def test_staging_gate_releases_a_cleared_celebrated_flag():
    proof = machine_conditional_proof(728, named=["h : Erdos728.Hyp"])
    payload = build_status(
        erdos=erdos_records(728), fc={}, proofs={728: proof},
        claims_by_problem={}, claims_available=True, overrides={},
        wiki={728: _wiki_summary(WIKI_FULL_LEAN)}, cleared={728},
        generated_at="2026-06-30")
    row = payload["rows"][0]

    assert row["held_for_review"] is False
    assert row["discrepancy"] is True                        # cleared -> publishes


def test_non_celebrated_conditional_flag_is_not_held():
    # The gate only applies to the celebrated set; ordinary flags publish as usual.
    proof = machine_conditional_proof(1148, named=["h : Erdos1148.DukeTheoremStatement"])
    _, row = status_for(1148, proof=proof, wiki=_wiki_summary(WIKI_FULL_LEAN))

    assert row["held_for_review"] is False
    assert row["discrepancy"] is True


# --- gpt-erdos: independent human classification, cross-referenced -----------

def test_load_candidate_claims_reads_gpt_erdos_registry():
    claims = load_candidate_claims()
    assert claims[281]["category"] == "new_proof"   # Neel credits a new GPT proof
    assert claims[281]["source"] == "gpt-erdos"


def test_candidate_claim_rides_the_reconciled_row():
    # #281: gpt-erdos says "new proof"; our extractor flags the Lean proof conditional.
    # The overlap (different artifacts, different verdicts) is the point.
    proof = machine_conditional_proof(281, named=["h : Erdos281.Hyp"])
    cand = {"category": "new_proof", "category_label": "New proofs", "source": "gpt-erdos"}
    payload = build_status(
        erdos=erdos_records(281), fc={}, proofs={281: proof},
        claims_by_problem={}, claims_available=True, overrides={},
        candidate_claims={281: cand}, generated_at="2026-06-30")
    row = payload["rows"][0]

    assert row["candidate_claims"]["category"] == "new_proof"
    assert row["machine"]["verdict"] == "conditional"


def test_source_lock_refresh_records_only_live_sources_and_selected_paths(
    tmp_path, monkeypatch
):
    frozen_payload = b"frozen registry"
    frozen_path = tmp_path / "sources" / "frozen.json"
    frozen_path.parent.mkdir()
    frozen_path.write_bytes(frozen_payload)
    (tmp_path / "sources.yaml").write_text(
        yaml.safe_dump(
            {
                "sources": {
                    "live": {
                        "kind": "proof_manifest",
                        "repo": "example/live",
                        "ref": "main",
                        "path": "data/proofs.yaml",
                        "url": "https://example.invalid/proofs.yaml",
                    },
                    "frozen": {
                        "kind": "frozen_snapshot",
                        "repo": "example/frozen",
                        "commit": "c" * 40,
                        "path": "sources/frozen.json",
                        "paths": ["README.md"],
                    },
                }
            }
        )
    )
    (tmp_path / "sources.lock.json").write_text(
        json.dumps(
            {
                "generated_at": "old",
                "sources": {"stale": {"sha256": "sha256:stale"}},
            }
        )
        + "\n"
    )

    live_payload = b"live registry"

    def fake_fetch(url, _headers=None):
        if "api.github.com" in url:
            return json.dumps({"sha": "d" * 40}).encode()
        return live_payload

    monkeypatch.setattr(erdos_frontier, "claims_headers", lambda: {})
    monkeypatch.setattr(erdos_frontier, "fetch", fake_fetch)

    refreshed = erdos_frontier.write_sources_lock(tmp_path)

    assert set(refreshed) == {"generated_at", "sources"}
    assert "stale" not in refreshed["sources"]
    assert refreshed["sources"]["live"]["path"] == "data/proofs.yaml"
    assert refreshed["sources"]["live"]["commit"] == "d" * 40
    assert refreshed["sources"]["live"]["sha256"] == (
        "sha256:" + hashlib.sha256(live_payload).hexdigest()
    )
    assert refreshed["sources"]["frozen"]["path"] == "sources/frozen.json"
    assert refreshed["sources"]["frozen"]["paths"] == ["README.md"]
    assert refreshed["sources"]["frozen"]["commit"] == "c" * 40
    assert refreshed["sources"]["frozen"]["sha256"] == (
        "sha256:" + hashlib.sha256(frozen_payload).hexdigest()
    )

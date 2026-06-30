import json

from fc_sync_status import (
    Claim,
    apply_machine_audit,
    build_proofs,
    build_status,
    classify,
    load_fidelity,
    parse_fidelity,
    render_next_batch_md,
    render_status_md,
)


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


def status_for(problem, *, proof=None, fc=None, claims=None, override=None, fidelity=None):
    payload = build_status(
        erdos=erdos_records(problem),
        fc={problem: fc} if fc else {},
        proofs={problem: proof} if proof else {},
        claims_by_problem={problem: claims} if claims else {},
        claims_available=True,
        overrides={problem: override} if override else {},
        fidelity={problem: fidelity} if fidelity else {},
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


def test_status_json_shape_and_rendered_artifacts_are_useful():
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

    status_md = render_status_md(payload)
    next_batch_md = render_next_batch_md(payload, top_count=20, batch_size=8)
    assert "## `mismatch`" in status_md
    assert "Problem 24" in next_batch_md
    assert "ErdosProblems/24" in next_batch_md
    assert "Problem 214" not in next_batch_md


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


def test_fidelity_section_renders_in_status_md():
    fidelity = parse_fidelity(FIDELITY_DOC_214, source="cache")[214]
    payload, _ = status_for(214, fidelity=fidelity)

    status_md = render_status_md(payload)

    assert "## statement fidelity" in status_md
    assert "`unfaithful`" in status_md
    assert "cache" in status_md


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
    # The committed fidelity_cache.json is the offline fallback / seed.
    cached = load_fidelity("fidelity_cache.json")

    assert 214 in cached
    assert cached[214]["source"] == "cache"
    assert cached[214]["signed"] is True

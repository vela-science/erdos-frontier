# Lean assumption extractor (L1 machine evidence)

For each Erdős problem with a hosted Lean proof, this reports — mechanically, no
human or model judgment — whether the proof establishes the statement
**unconditionally**, or only under undischarged assumptions:

- the axiom set (`#print axioms`) and whether it is kernel-clean,
- `sorry`-free status,
- **the non-instance Prop hypotheses the theorem takes as parameters**, split into
  *named assumptions* (a problem-defined Prop standing for a deep result — e.g.
  `DensityHypothesis`, `DukeTheoremStatement`) and routine *preconditions*
  (`0 < ε`, `x ∈ S`).

The last is the case `#print axioms` cannot see: a proof can be `sorry`-free and
kernel-clean yet conditional on a famous theorem passed as a hypothesis. That is
the gap this layer closes.

## Run

    python3 extract_assumptions.py --repo plby         # default; the v4.29.1 fork
    python3 extract_assumptions.py --repo alphaproof   # alphaproof-nexus, Lean 4.27.0

Each repo is loaded in its own built `.lake` at its own pinned Lean toolchain (override
the root with the per-repo `VELA_PROOF_REPO[_<TAG>]` env var). For each, the harness
discovers headline theorems per problem, generates a transient `extract_<tag>.lean`
(imports the built modules, robust to missing decls; git-ignored), runs it under
`lake env lean`, and writes:

- `assumptions[_<tag>].jsonl` — one L1 record per theorem.
- `audit_feed[_<tag>].json` — one retained machine-evidence row per problem.

`erdos_frontier` merges every `audit_feed*.json` into its source-audit payload,
keeping the strongest verdict per problem with provenance. It does not publish
a parallel site or graph snapshot. To rebuild every feed at once, use
`reaudit.sh`.

Neutral: no Vela dependency. The signed/replayable tier lives in the Vela frontier;
this is the public machine-evidence generator.

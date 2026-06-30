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

    VELA_PROOF_REPO=/path/to/lean-proofs/src/v4.29.1 python3 extract_assumptions.py

Discovers headline theorems per problem, generates `extract_all.lean` (imports the
built modules, robust to missing decls), runs it under `lake env lean`, and writes:

- `assumptions.jsonl` — one L1 record per theorem.
- `audit_feed.json` — one row per problem (joined with `../status.json`).

Neutral: no Vela dependency. The signed/replayable tier lives in the Vela frontier;
this is the public machine-evidence generator.

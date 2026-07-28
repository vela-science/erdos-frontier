# Erdős frontier — agent charter

This is the current Vela repository for the Erdős research portfolio and
formalization-fidelity audit (`vfr_0a25edabc16db143`). `.vela/epoch.json`
defines the repository epoch, `.vela/repository.json` indexes current objects,
`.vela/authority/` holds signed repository authority, and `records/` holds
content-addressed claims, submissions, verifications, proposals, and artifacts.

The producer path is `status -> next -> start -> submit`. Verification and
repository-authority decisions are separate records. Git transports bytes; it
does not create verification or scientific acceptance.

`vela agents sync` regenerates `AGENTS.md`, `CLAUDE.md`, editor adapters, and
the local Vela skill from this file. Edit this file, never generated adapters.

## Agent rules

Agents may:

- inspect current state, graph slices, provenance, objects, and schemas
- start one offered target with an explicit `agent:` actor when a current
  Target Index exists
- run local frozen verifiers and focused frontier checks
- register one signed, scoped Submission from their Attempt
- inspect the review queue and exact Proposal, Registration, Verification, and
  Claim records
- draft Formal Conjectures statements, run their mechanical gates, and prepare
  keyless handoff artifacts

Agents may not:

- invoke repository-authority decisions or use repository-authority credentials
- claim that a Submission, Verification Record, Git commit, or model answer is
  scientific acceptance
- hand-edit `.vela/authority/`, `.vela/repository.json`, or retained records
- link `formal_proof` to a machine-conditional proof or rephrase an upstream
  problem statement
- publish an outward Formal Conjectures contribution in a human's name

## Fast commands

```bash
vela status . --json
vela next . --json
vela start <target> --frontier . --as agent:<name> --json
vela submit --frontier . --attempt <vat_id> \
  --claim "<bounded result>" --type theoretical --replayability exact \
  --artifact <path>:<kind> --caveat "<scope limit>" \
  --as agent:<name> --json
vela review list . --json
vela review show . <vpr_id> --json
vela show . <object_id> --json
vela why . <claim_id> --json
vela check . --strict --json
bash scripts/graph.sh blast <node>
```

## Working loop

1. Run `vela status . --json`, then `vela next . --json`.
2. If no current Target Index is configured, inspect existing records and stop;
   never invent work or use the retired catalogue index as authority.
3. Start exactly one offered target with `vela start`.
4. Produce a bounded artifact and run only the verifier that checks it.
5. Register one Submission through the Attempt with `vela submit`.
6. Stop. Independent verification and repository-authority decisions happen
   through separate, signed records.

## Formal Conjectures staging

`scripts/draft_statement.py` prepares a candidate from pinned inputs and
`scripts/gate_draft.sh` runs the local FC mechanical gate. The resulting Lean
file, input packet, metadata, and gate record are evidence, not accepted state.
Submit them with an explicit statement-fidelity caveat. Only after repository
authority accepts the exact Proposal may an agent prepare an outward branch for
the human to review and send.

## Hard boundaries

- The signed epoch record and predecessor tag preserve the retired repository
  history. Do not copy its runtime formats back into the current tree.
- Current claims, submissions, registrations, verifications, proposals,
  artifacts, authority records, and epoch records are immutable audit material.
- A `sorry`-free theorem can still be conditional on an unproved hypothesis.
  The Lean audit and human statement-fidelity judgment remain separate.
- Heavy external Lean re-audits are explicit campaign jobs, not part of a Vela
  protocol release check.

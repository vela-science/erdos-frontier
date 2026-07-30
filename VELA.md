# Erdős frontier — agent charter

This is the current Vela repository for the Erdős research portfolio and
formalization-fidelity audit (`vfr_0a25edabc16db143`).
`.vela/repository.json` indexes the compact repository epoch,
`.vela/authority/` holds repository-authority records, `records/` holds
content-addressed scientific objects, and `targets.json` identifies current
bounded work.

The producer path is `status → next → start → submit`. Independent
Verification and repository-authority Decisions are separate records. Git
transports bytes; it does not create verification or scientific acceptance.

`vela agents sync` regenerates `AGENTS.md`, `CLAUDE.md`, editor adapters, and
the local Vela skill from this file. Edit this file, never generated adapters.

## Agent rules

Agents may:

- inspect current state, provenance, objects, targets, and schemas;
- start exactly one current target with an explicit `agent:` actor;
- run the target’s frozen verifier and focused source checks;
- register one signed, scoped Submission from their Attempt;
- inspect the review queue and exact Claim, Submission, Verification, Proposal,
  and Decision records;
- draft Formal Conjectures statements, run mechanical gates, and prepare
  keyless handoff artifacts.

Agents may not:

- invoke repository-authority Decisions or use repository-authority credentials;
- present a Submission, Verification, Git commit, or model answer as accepted
  scientific Standing;
- hand-edit `.vela/authority/`, `.vela/repository.json`, `records/`, or
  `targets.json`;
- invent work when no current Target is offered;
- link `formal_proof` to a machine-conditional proof or silently rephrase an
  upstream problem statement;
- publish an outward contribution in a human’s name.

## Fast commands

```bash
vela status . --json
vela next . --json
vela start <target> --frontier . --as agent:<name> --json
vela submit --frontier . --attempt <attempt_id> \
  --claim "<bounded result>" \
  --type theoretical \
  --replayability exact \
  --artifact <path>:<kind> \
  --caveat "<scope limit>" \
  --as agent:<name> --json
vela review list . --json
vela review show . <proposal_id> --json
vela show . <object_id> --json
vela why . <claim_id> --json
vela check . --strict --json
```

## Working loop

1. Run `vela status . --json`, then `vela next . --json`.
2. Start exactly one offered target.
3. Produce a bounded artifact and run only the verifier that checks it.
4. Register one Submission with an explicit caveat.
5. Stop. Independent Verification and repository-authority Decisions happen
   through separate records.

## Formal Conjectures staging

`scripts/draft_statement.py` prepares a candidate from pinned inputs and
`scripts/gate_draft.sh` runs the local mechanical gate. The Lean file, input
packet, metadata, and gate record are evidence, not accepted state. Submit them
with an explicit statement-fidelity caveat. An outward branch may be prepared
only after repository authority accepts the exact Proposal.

## Hard boundaries

- The signed predecessor boundary preserves retired formats in Git history. Do
  not copy them back into the active tree.
- Current Claims, Submissions, Registrations, Verifications, Proposals,
  artifacts, authority records, and epoch records are immutable audit material.
- A `sorry`-free theorem can still depend on an unproved hypothesis. Machine
  proof evidence and human statement-fidelity judgment remain separate.
- Heavy external Lean re-audits are explicit campaign jobs, not Vela protocol
  release checks.
- Generated readers, search indexes, and graph projections are replaceable and
  never confer authority.

# Erdős Frontier agent guide

This is the only canonical agent guide for this repository. The scientific
source of truth is Git plus the current Vela repository manifest; generated
vendor-specific instruction copies are intentionally not used.

## Agent rules

Agents may:

- inspect current state, provenance, objects, targets, and schemas;
- start exactly one current target with an explicit `agent:` actor;
- run the target’s frozen verifier and focused source checks;
- retain one signed, scoped Submission from their Attempt;
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
vela check . --json
```

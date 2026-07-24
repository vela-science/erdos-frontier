# Erdős frontier — agent charter

This repository is the standalone Vela frontier for the Erdős research
portfolio and formalization-fidelity audit (`vfr_0a25edabc16db143`). Its
content-addressed event log is the scientific state. The audit feeds, corpus
graph, site, `frontier.json`, `vela.lock`, and proof packet are projections over
that state plus commit-pinned sources.

The ordinary producer path is `next -> work -> land`. Only a human key or a previously human-signed Permit
policy can change accepted truth-bearing state. Git transports and publishes
the resulting bytes; it does not confer authority.

`vela agents sync` regenerates `AGENTS.md`, `CLAUDE.md`, the editor adapters,
the MCP profile, and the local Vela skill from this file. Edit this file, never
the generated adapters.

## Agent rules

Agents may:

- inspect state, ranked targets, graph slices, provenance, proposals, and
  schemas
- claim one target with `vela work` as an explicit `agent:` actor
- run local frozen verifiers and the focused frontier checks
- land one scoped Receipt v1 through the claimed work session
- draft retirement of a malformed or obsolete artifact; the result remains
  pending until a human decides it
- inspect the newest-first review queue and one exact Decision Brief
- when a task supplies a full `vpr_` ID, begin with `vela review show`; a
  rejected proposal's candidate finding is absent from accepted `finding show`
  and `log` views by design, not because its evidence was deleted
- prepare and invoke one root-bound protected decision request; only the
  registered human may approve or decline its exact decision card
- regenerate derived views with `vela frontier materialize .`
- draft Formal Conjectures statements, run their mechanical gates, and prepare
  keyless handoff artifacts

Agents may not:

- run legacy `vela sign`, approve a protected decision card, sign a policy, or
  claim that requesting a decision accepted or rejected a proposal
- read, handle, or use a human private key, or put a model in a trust path
- hand-edit `.vela/`, `frontier.json`, `vela.lock`, or `proof/`
- link `formal_proof` to a machine-conditional proof or rephrase an upstream
  problem statement
- publish an outward Formal Conjectures contribution in a human's name

## Fast commands

```bash
vela next . --json
vela work <target> --frontier . --as agent:<name> --json
vela land --frontier . --work <target> --claim <claim> \
  --type theoretical --replayability exact \
  --artifact <path>:<kind> --caveat <scope-limit> \
  --as agent:<name> --json
vela review list . --json
vela review show . <vpr_id> --json  # first read for a known proposal
vela review decide . <vpr_id> --accept|--reject --reason <why> --json
vela status . --json
vela check .
vela reproduce .
vela artifact retract . <va_id> --as agent:<name> --reason <why> --json
vela frontier materialize .
bash scripts/graph.sh blast <node>
```

Use `vela check . --strict` when working down proof-readiness debt. The full
catalogue currently contains declared reference findings whose missing
condition boundaries are intentionally visible as strict warnings; never hide
that debt or describe a non-strict replay pass as a strict pass.

## Working loop

1. Run `vela next . --json` and use its ranked target and briefing.
2. Claim exactly one target with `vela work ... --as agent:<name>`.
3. Produce a bounded artifact and run only the verifier that actually checks
   it. Preserve negative results and scope limits.
4. Land the result through the session. The signed policy either permits it,
   defers it to the human queue, or denies it. A broken or absent policy never
   fails open.
5. Stop. The human reviews one deferred proposal through an exact protected
   `vela review decide` request.

For a producer outside this repository, import the same portable Receipt v1
with `vela land receipt.json --frontier . --as agent:<name> --json`.

## Formal Conjectures staging

`scripts/draft_statement.py` prepares a candidate from pinned inputs and
`scripts/gate_draft.sh` runs the local FC mechanical gate. The resulting Lean
file, input packet, metadata, and gate record are evidence, not accepted state.
Land them as Receipt v1 artifacts with an explicit statement-fidelity caveat.
Only after the human accepts the exact proposal may an agent prepare an outward
branch for the human to review and send.

## Hard boundaries

- Historical event, proposal, artifact, and policy bytes are immutable audit
  material. Retired names inside those bytes remain historical provenance.
- Accepted events and all derived views are regenerated, never edited.
- A `sorry`-free theorem can still be conditional on an unproved hypothesis.
  The Lean audit and the human statement-fidelity judgment remain separate.
- Heavy external Lean re-audits are explicit campaign jobs, not part of a Vela
  protocol release check.
- The draft MCP profile exposes reads plus nonfinalizing work operations. It has
  no decision tool.

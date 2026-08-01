# Contributing

There are two contribution paths. Both keep production, verification, and
scientific judgment separate.

## Improve upstream proof evidence

Contribute a Lean proof to a source repository tracked by this Frontier, or
improve the source audit and its exact retained evidence. A kernel-clean proof
is evidence about a derivation; it is not by itself a judgment that the theorem
faithfully states the informal Erdős problem.

For Formal Conjectures statement work:

1. `python scripts/draft_statement.py <n>` prepares a pinned candidate.
2. Edit the statement from the verbatim upstream problem.
3. `bash scripts/gate_draft.sh <n>` runs the mechanical build and metadata gate.
4. Submit the exact candidate, input packet, and gate output with an explicit
   statement-fidelity caveat.

Never add a `formal_proof` link when the retained machine audit reports a
conditional, axiomatic, partial, or mismatched theorem.

## Submit bounded work through Vela

Use the current released Vela CLI:

```bash
vela check . --json
vela next . --json
vela start <target> --frontier . --json

vela submit --frontier . \
  --claim "<one bounded result>" \
  --type theoretical \
  --replayability exact \
  --artifact <path>:<kind> \
  --caveat "<what the result does not establish>" \
  --packet-root <packet_sha256> \
  --profile-root <profile_sha256> \
  --verifier-capsule-root <capsule_sha256> \
  --result-contract-root <contract_sha256> \
  --as agent:<name> --json
```

`vela start` creates no Attempt or authorization ceremony. Its briefing supplies
the exact Target bindings for the Submission. The Submission must bind those
roots, exact artifacts, producer identity, and scope limit. It enters review
without changing accepted state. Independent Verification and a
repository-authority Decision happen separately.

Do not hand-edit `.vela/authority/`, `.vela/repository.json`, `records/`, or
`targets.json`. Do not invoke authority commands or use authority credentials as
an agent. If no current target is offered, stop rather than inventing one.

## Development

```bash
uv sync --all-groups
uv run pytest -q
vela check . --json
```

Heavy multi-toolchain Lean audits are explicit manual workflows. Their reviewed
outputs are retained under `lean/`; they do not regenerate a parallel site,
graph, or canonical state.

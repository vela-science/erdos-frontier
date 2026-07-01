# erdos-frontier is the git-native Vela frontier for Erdős formalization

This repository does two things, in two layers.

## The audit (the public site)

It reads each hosted Lean proof of an Erdős problem and reports, mechanically,
whether the proof establishes the problem outright or only under an unproven
assumption — an axiom it never discharges, or a hypothesis it carries. It
cross-references the frozen AI-contributions wiki and the gpt-erdos review, and
it separates two questions that a single "solved" mark runs together:

- **Is the proof unconditional?** A fact, read from the proof. Deterministic.
- **Is the formal statement the right problem?** A judgment, signed by a named
  reviewer.

The site (`site/`) — the overview, the per-problem finding pages, the load-bearing
condition map — is a **materialized view** of that state. So are `STATUS.md`,
`status.json`, and `NEXT_BATCH.md`. They are generated, not authored.

## The frontier (the signed state)

Underneath the dashboard, the answers that carry a human judgment live as signed,
content-addressed, replayable state in `.vela/`. A statement-fidelity verdict is a
`vsa_` attestation signed with a reviewer's key and recorded as an event; the
frontier's materialized `frontier.json` and `vela.lock` are replayed from that
event log by the Vela reducer. Nothing here asks you to trust the dashboard:

```bash
git clone https://github.com/williamjblair/erdos-frontier
cd erdos-frontier
vela check . --strict     # replays the event log, verifies every signature
```

That command reproduces the materialized state from the events and re-verifies
each signature from the bytes alone. The frontier id is `vfr_0a25edabc16db143`;
the hub indexes it read-only.

## What this is not

- Not a claim that a green Lean file is a solved problem — statement fidelity is a
  separate, signed edge.
- Not a place where a model accepts its own results — an agent may draft a finding
  or a packet; only a human key signs a truth-bearing verdict.
- Not branding over mechanism — the replay claim above is exactly what
  `vela check` verifies, and no more.

The rule underneath: **Git stores and transports. The proof checker checks
derivations. A human key accepts the judgments. The reducer derives the view.**

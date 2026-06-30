# erdos-fc-sync

A **computed** source of truth for syncing solved-problem proofs into
[Formal Conjectures](https://github.com/google-deepmind/formal-conjectures).

## The problem: drift

An Erdős problem's "status" lives in several places that update independently:

- **erdosproblems.com** — the upstream status (open / solved / formally solved).
- **Formal Conjectures** — each file's `@[category ...]` annotation and `formal_proof` link.
- **[plby/lean-proofs](https://github.com/plby/lean-proofs)** — hosted Lean proofs and
  `conditional` / `partial` flags.
- **[Jayyhk/erdos-lean](https://github.com/Jayyhk/erdos-lean)** — hosted Lean proofs and
  `complete` / `axiomatic` / `trust_extended` states.
- **[williamjblair/lean-proofs](https://github.com/williamjblair/lean-proofs)** — a small
  CI-audited proof host whose manifest is checked by `#print axioms`.
- **Statement-fidelity verdicts** — signed reviewer attestations of whether a formal theorem
  faithfully states the boxed problem (`faithful` / `variant` / `unfaithful`). Read from a
  snapshot URL when available, otherwise from a committed [`fidelity_cache.json`](fidelity_cache.json).
- **Human review notes** — mismatch and claim judgments that live in issue comments or PR review,
  not in any upstream data feed.

Reconciling these by hand is what drifts. The cost is double-work (two people formalising the
same problem) and mislabelling (a conditional or mismatched proof linked as if it proved the
boxed statement).

## What this does

[`fc-sync-status.py`](fc-sync-status.py) computes the status instead of tracking it. It fetches
the sources fresh, joins them on the problem number, folds in live open FC pull requests, applies
explicit human overrides from [`overrides.yaml`](overrides.yaml), and writes generated artifacts.
A GitHub Action runs tests and regenerates the artifacts daily.

Generated files:

- **[STATUS.md](STATUS.md)** — human-readable dashboard and bucket counts.
- **[status.json](status.json)** — machine-readable rows for agents and scripts.
- **[NEXT_BATCH.md](NEXT_BATCH.md)** — ranked safe `statement` candidates with proof links and
  anti-collision commands.

## The status categories

| status | meaning |
|---|---|
| `statement` | a complete hosted proof exists, FC has no file — write the statement and link it |
| `link` | FC has the statement, the proof just isn't linked |
| `needs-statement-update` | FC has a file, but this is not a trivial link-only update |
| `needs-human-match-check` | a hosted proof exists, but theorem/boxed-statement match has not been audited |
| `mismatch` | hosted proof is complete but does not prove the boxed FC statement |
| `hypothesis-conditional` | `#print axioms` can be clean, but the theorem takes a non-problem hypothesis |
| `docstring` | the hosted proof is conditional, axiomatic, or trust-extended — do not add `formal_proof` |
| `partial` | the hosted proof proves a variant, not the full statement |
| `blocked-claim` | a human issue-comment claim exists outside an open PR |
| `in-pr` | an open FC pull request already touches this file |
| `wont-fix` | maintainers marked the hosted proof/problem as not linkable |
| `defer` | explicit human deferral |
| `done` | already linked in FC |
| `no-proof` | no hosted Lean proof to link yet |

See **[STATUS.md](STATUS.md)** for the live lists, each linked to erdosproblems.com.

## Overrides

[`overrides.yaml`](overrides.yaml) is the only hand-maintained input. Use it for facts that the
machine-readable sources cannot know, such as:

- a proof theorem is complete but proves a different quantified statement (`mismatch`);
- a proof theorem has a non-problem hypothesis (`hypothesis-conditional`);
- a problem is claimed in an issue comment rather than an open PR (`blocked-claim`);
- a maintainer explicitly says not to link it (`wont-fix`).

Do not hand-edit generated artifacts. Change `overrides.yaml` or the script, then regenerate.

## Statement fidelity

A signed statement-fidelity feed records, per problem, whether a formal theorem faithfully states
the boxed problem. The script reads it from a snapshot URL when reachable and otherwise from the
committed [`fidelity_cache.json`](fidelity_cache.json); if neither is present the column is simply
empty and the run still succeeds. A signed verdict supersedes the computed bucket and any matching
`overrides.yaml` row.

Verdicts are signed with `vela attest faithfulness` against the `erdos-formalization` Vela frontier
(only a human reviewer can sign one); they are not stored in this repo. Review the match-check
packet before signing:

- [`match_packet.py`](match_packet.py) — writes a three-panel review packet (upstream statement,
  formal theorem, hosted theorem signature) to `packets/match-check/erdos_<n>.md` for a problem
  or for every row still needing a match-check.

## Regenerate locally

```sh
uv sync --all-groups
uv run pytest
GH_TOKEN=$(gh auth token) uv run python fc-sync-status.py
uv run python -m json.tool status.json >/dev/null
```

The token is only used to read open FC pull requests (the `in-pr` layer). Without it everything
else still computes.

## Development

The CLI wrapper is [`fc-sync-status.py`](fc-sync-status.py). The importable implementation is
[`fc_sync_status.py`](fc_sync_status.py), so tests can exercise classification and rendering
without network access.

Before pushing:

```sh
uv sync --all-groups
uv run pytest
GH_TOKEN=$(gh auth token) uv run python fc-sync-status.py
uv run python -m json.tool status.json >/dev/null
git diff --check
```

## Context

This supports [formal-conjectures#3998](https://github.com/google-deepmind/formal-conjectures/issues/3998)
(syncing hosted Lean proofs into FC) and #4184 (the Jayyhk set). It is offered as a coordination
aid. If the maintainers want it in-repo or wired into FC CI, the core is intentionally small and
plain Python.

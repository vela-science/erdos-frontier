# Erdős Problems Frontier

The canonical Git frontier for the Erdős-problem audit and its bounded
research state. Inspect its read-only projection in
[Vela Observatory](https://app.vela.space/frontiers/erdos), or clone this
repository to verify the exact state yourself.

The audit asks which formally solved Erdős problems rest on an unconditional
Lean proof and which silently assume an unproven result.

The gap it closes: a proof can be `sorry`-free and `#print axioms`-clean and still
prove the goal only conditionally, by taking a deep theorem as a hypothesis
parameter the axiom check never sees. The audit reads each hosted proof
mechanically and reports its axiom set, its `sorry` state, and the Prop
hypotheses it takes as parameters. Nine problems recorded as solved currently
hold only under an unproven result
([published frontier](https://app.vela.space/frontiers/erdos)).

Two axes, one trust rule:

- **Axis 1, the proof.** Is it unconditional? Machine-checked, reproducible, no
  human or model in the path.
- **Axis 2, the statement.** Does the formal theorem state the boxed problem?
  A human judgment, signed by a named reviewer. Never inferred, never
  auto-filled: a problem with no signed verdict shows blank.

## How the pieces fit

The current repository loop is deliberately small:

1. **Inspect.** `status`, `show`, and `why` expose exact repository objects.
2. **Attempt.** `next` and `start` bind one bounded target when a current Target
   Index is configured.
3. **Submit.** A producer registers one signed Submission. It cannot create a
   Verification Record, Decision, Event, or accepted claim.
4. **Verify.** Independent, signed Verification Records report scoped checks.
5. **Decide.** Repository authority accepts or refuses one exact Proposal.
6. **Reuse.** Git and read-only consumers transport and project the result
   without acquiring authority.

## Verify it yourself

The Observatory is a read-only projection. The current repository epoch is
declared by [`.vela/epoch.json`](.vela/epoch.json); its accepted and pending
objects are indexed by [`.vela/repository.json`](.vela/repository.json), with
signed repository authority under [`.vela/authority/`](.vela/authority/) and
content-addressed scientific records under [`records/`](records/). External
catalogue and proof inputs remain commit-pinned:

```bash
git clone https://github.com/vela-science/erdos-frontier
cd erdos-frontier
vela check . --strict --json
vela status . --json
vela review show . vpr_533385002e7c3ac9 --json
```

Strict verification passes for the migrated current epoch. The signed epoch
record binds predecessor tag `pre-current-epoch/c236b4fdedb2`; historical event
and policy details remain available there without remaining in the active
runtime.

Everything under [`site/`](site/) is a generated catalogue projection. It is
useful for reading and interoperability but confers no authority.

## Native Vela work surface

The repository contains the complete 1,217-problem Erdős catalogue and its
derived problem packets. The migrated current epoch does not yet declare a
current Target Index, so `vela next` correctly returns no offers. The catalogue
must not be mistaken for an authority-bearing work queue.

```bash
vela next . --json
```

The next engineering step is to derive and review a current-format Target Index
from the exact catalogue. Until then, inspect claims with `vela show` and
`vela why`, and use the domain-specific audit commands below.

## Sources

The audit joins records that update independently and drift apart:

| source | what it contributes |
|---|---|
| [erdosproblems.com](https://www.erdosproblems.com) (Thomas Bloom) | problem numbering, statements, upstream status |
| [formal-conjectures](https://github.com/google-deepmind/formal-conjectures) (Google DeepMind) | formal statements, `@[category]` annotations, `formal_proof` links |
| [plby/lean-proofs](https://github.com/plby/lean-proofs), [Jayyhk/erdos-lean](https://github.com/Jayyhk/erdos-lean), [williamjblair/lean-proofs](https://github.com/williamjblair/lean-proofs) | hosted Lean proofs and their own condition flags |
| [AI-contributions wiki](https://github.com/teorth/erdosproblems/wiki/AI-contributions-to-Erd%C5%91s-problems) (Nat Sothanaphan, frozen 2026-06-30) | recorded solution claims, carried over intact |
| [gpt-erdos](https://github.com/neelsomani/gpt-erdos) (Neel Somani) | independent human classification of GPT-5.2 candidates |
| signed fidelity verdicts | reviewer attestations on Axis 2, read from the frontier |

Reconciling these by hand is what drifts: two people formalise the same problem,
or a conditional proof gets linked as if it proved the boxed statement.

## How it works

[`erdos_frontier.py`](erdos_frontier.py) fetches the sources, joins them, folds
in the machine verdicts from the Lean extractor ([`lean/`](lean/), multiple
toolchains, strongest verdict per problem), applies
[`overrides.yaml`](overrides.yaml) and any signed verdicts, and regenerates the
compatibility feeds under [`site/`](site/). A scheduled GitHub Action refreshes
those derived feeds; the heavier Lean re-audit
([`lean/reaudit.sh`](lean/reaudit.sh)) runs on demand.

Derived work and compatibility outputs:

- [`targets.json`](targets.json): native Vela target index for all 1,217 problems
- [`site/problems/`](site/problems/): hash-pinned complete per-problem work packets
- [`site/verdicts.json`](site/verdicts.json): the audit feed, one row per problem
- [`site/status.json`](site/status.json) / [`site/STATUS.md`](site/STATUS.md): the proof-status join and bucket counts
- [`site/NEXT_BATCH.md`](site/NEXT_BATCH.md): ranked safe `statement` candidates for FC
- [`site/graph.json`](site/graph.json): the typed corpus graph

The corpus graph holds the whole reconciled state (problems, statements, proofs,
conditions, claims, verdicts) as typed edges with a trust tier on every edge
(`signed` / `machine` / `recorded` / `declared`). It is a derived index, never
signed state:

```bash
bash scripts/graph.sh build                   # rebuild from the sources
bash scripts/graph.sh blast cond:maynard-tao  # what does retracting an input unsettle?
bash scripts/graph.sh serve                   # inspect the local derived graph
```

## Contributing

Two paths, detailed in [CONTRIBUTING.md](CONTRIBUTING.md): host a proof the
audit reads, or land a portable Receipt v1 through Vela's task-first loop.
[VISION.md](VISION.md) explains the two layers and the trust rule.
[STANDARD_CHECK.md](STANDARD_CHECK.md) is the proposal for a layered
statement-review check upstream in formal-conjectures.

Agents use `status -> next -> start -> submit` and stop after registering a
Submission. Verification and repository-authority decisions are separate
records. Historical statement-fidelity attestations remain immutable audit
material through the signed predecessor boundary.

[`overrides.yaml`](overrides.yaml) is the only hand-maintained classification
input. Use it for facts the sources cannot know: a mismatched quantifier, a
non-problem hypothesis, a claim living in an issue comment, a maintainer
wont-fix. Never hand-edit generated artifacts; change the input and regenerate.

## Develop locally

```sh
uv sync --all-groups
uv run pytest
GH_TOKEN=$(gh auth token) uv run python erdos_frontier.py
uv run python -m json.tool site/status.json >/dev/null
```

The token only reads open FC pull requests (the `in-pr` layer); everything else
computes without it. `erdos_frontier.py` is importable, so the tests exercise
classification and rendering offline.

```
erdos_frontier.py     fetch, join, classify, render
match_packet.py       human-review packets for the discrepancies
site/                 generated compatibility feeds; not the authority surface
sources/              ingested claim snapshots (wiki, gpt-erdos, fidelity cache)
lean/                 the Lean assumption-extractor + committed machine verdicts
overrides.yaml        the only hand-maintained classification input
staging_cleared.yaml  human clearances for held celebrated-proof flags
```

## Status categories

| status | meaning |
|---|---|
| `statement` | a complete hosted proof exists, FC has no file: write the statement and link it |
| `link` | FC has the statement, the proof just isn't linked |
| `needs-statement-update` | FC has a file, but this is not a trivial link-only update |
| `needs-human-match-check` | a hosted proof exists, but the theorem/boxed-statement match is unaudited |
| `mismatch` | hosted proof is complete but does not prove the boxed FC statement |
| `hypothesis-conditional` | `#print axioms` is clean, but the theorem takes a non-problem hypothesis |
| `docstring` | the hosted proof is conditional, axiomatic, or trust-extended; do not add `formal_proof` |
| `partial` | the hosted proof proves a variant, not the full statement |
| `blocked-claim` | a human issue-comment claim exists outside an open PR |
| `in-pr` | an open FC pull request already touches this file |
| `wont-fix` | maintainers marked it not linkable |
| `defer` | explicit human deferral |
| `done` | already linked in FC |
| `no-proof` | no hosted Lean proof to link yet |

Live lists, each linked to erdosproblems.com: [site/STATUS.md](site/STATUS.md).

## Context

Built to support
[formal-conjectures#3998](https://github.com/google-deepmind/formal-conjectures/issues/3998)
(syncing hosted Lean proofs into FC) and #4184 (the Jayyhk set). The core is
small, plain Python; if the FC maintainers want it in-repo or wired into CI, it
moves cleanly.

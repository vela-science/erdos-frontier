# Erdős Problems Frontier

A standalone Vela custody source for the Erdős-problem audit and bounded
research state. The read-only published projection is available in
[Vela Observatory](https://app.vela.space/frontiers/erdos).

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

## Verify it yourself

The dashboard is a materialized view. Accepted scientific state is the
replayable event log under [`.vela/`](.vela/) (Vela frontier
`vfr_0a25edabc16db143`); external catalogue and proof inputs are commit-pinned
in the source registry:

```bash
git clone https://github.com/vela-science/erdos-frontier
cd erdos-frontier
vela check . --json       # replay and the applied retirement event pass
vela status . --json
```

`vela check . --strict` also promotes the catalogue's declared-data condition
debt and historical unsigned writes to a failing proof-readiness gate. The
current 1,217-problem import keeps that debt visible rather than pretending
every reference row is proof-ready. On 2026-07-16 a key-custody human applied
proposal `vpr_12b236db3fc0b409`, retiring the unsupported prelaunch active-policy
byte pair without changing scientific state. The frontier now has no active
policy and is intentionally human-only for future truth-bearing decisions.

Everything under [`site/`](site/), plus `frontier.json` and `vela.lock`, is
generated from the event log and locked sources. Nothing there confers
authority by itself.

## Native Vela work surface

The repository is the complete 1,217-problem Erdős work atlas, not only a
dashboard. [`targets.json`](targets.json) gives every problem a stable
`erdos:<n>` handle and an exact digest for its full packet under
[`site/problems/`](site/problems/). Each packet joins the upstream statement
and status, formal theorem and proof records, attempts, residual obligations,
dependencies, witnesses, source locks, and trust labels.

```bash
vela next . --json
vela work erdos:1056 --frontier . --as agent:<you> --json
vela reproduce .
```

`next` ranks current open, unpaused problems and loads only the selected
packet. Solved, disproved, independent, or in-flight entries stay out of the
suggestion queue but remain directly addressable for inspection and
reproduction. The index and packets are derived, deletable briefing
projections; only signed Vela events carry accepted truth.

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
[`overrides.yaml`](overrides.yaml) and any signed verdicts, and regenerates
[`site/`](site/). A GitHub Action reruns it daily; the heavier Lean re-audit
([`lean/reaudit.sh`](lean/reaudit.sh)) runs on demand.

Machine-readable outputs, one URL each:

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
bash scripts/graph.sh serve                   # the frontier over HTTP
```

The repo also ships [`.mcp.json`](.mcp.json): an MCP client opened here gets
the read surface plus nonfinalizing `work` and `land` operations. The draft
profile has no decision tool.

## Contributing

Two paths, detailed in [CONTRIBUTING.md](CONTRIBUTING.md): host a proof the
audit reads, or land a portable Receipt v1 through Vela's task-first loop.
[VISION.md](VISION.md) explains the two layers and the trust rule.
[STANDARD_CHECK.md](STANDARD_CHECK.md) is the proposal for a layered
statement-review check upstream in formal-conjectures.

Agents use `vela next -> work -> land` and stop. A human handles deferred
truth-bearing proposals through the single `vela sign` ceremony. Historical
statement-fidelity attestations remain immutable audit material.

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
site/                 the published surface (generated; GitHub Pages serves it)
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

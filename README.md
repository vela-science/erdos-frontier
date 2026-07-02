# erdos-frontier

An audit of the formally solved Erdős problems: which rest on an unconditional
Lean proof, and which silently assume an unproven result. Live at
[erdos.constellate.science](https://erdos.constellate.science/).

The gap it closes: a proof can be `sorry`-free and `#print axioms`-clean and still
prove the goal only conditionally, by taking a deep theorem as a hypothesis
parameter the axiom check never sees. The audit reads each hosted proof
mechanically and reports its axiom set, its `sorry` state, and the Prop
hypotheses it takes as parameters. Nine problems recorded as solved currently
hold only under an unproven result
([the discrepancy view](https://erdos.constellate.science/)).

Two axes, one trust rule:

- **Axis 1, the proof.** Is it unconditional? Machine-checked, reproducible, no
  human or model in the path.
- **Axis 2, the statement.** Does the formal theorem state the boxed problem?
  A human judgment, signed by a named reviewer. Never inferred, never
  auto-filled: a problem with no signed verdict shows blank.

## Verify it yourself

The dashboard is a materialized view. The authority is a signed, replayable
event log under [`.vela/`](.vela/) (Vela frontier `vfr_0a25edabc16db143`):

```bash
git clone https://github.com/williamjblair/erdos-frontier
cd erdos-frontier
vela check . --strict     # replay the log, verify every signature
```

Everything under [`site/`](site/), plus `frontier.json` and `vela.lock`, is
generated from that log and the locked sources. Nothing there is hand-authored.

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

The repo also ships [`.mcp.json`](.mcp.json): any MCP client opened here gets
the read-only Vela tool set over the signed frontier.

## Contributing

Two paths, detailed in [CONTRIBUTING.md](CONTRIBUTING.md): host a proof the
audit reads, or fork and propose a finding a maintainer accepts.
[VISION.md](VISION.md) explains the two layers and the trust rule.
[STANDARD_CHECK.md](STANDARD_CHECK.md) is the proposal for a layered
statement-review check upstream in formal-conjectures.

To review and sign a statement-fidelity verdict (reviewer key only, no AI
signs):

```bash
python match_packet.py <n>    # three-panel review packet: upstream statement,
                              # formal theorem, hosted theorem signature
bash scripts/sign-fidelity.sh <problem> <faithful|variant|unfaithful> "<note>" --sign
```

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

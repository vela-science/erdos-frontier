# erdos-frontier

A formal-proof fidelity audit over the Erdős frontier: **which "formally solved"
problems rest on an unconditional Lean proof, and which silently assume an unproven
result.** Live at [williamjblair.github.io/erdos-frontier](https://williamjblair.github.io/erdos-frontier/).

A proof can be `sorry`-free and `#print axioms`-clean and still prove the goal only
*conditionally*, by taking a deep theorem as a hypothesis parameter the axiom check
cannot see. This reads each hosted Lean proof mechanically and reports it, then:

- **cross-references the frozen [AI-contributions wiki](https://github.com/teorth/erdosproblems/wiki/AI-contributions-to-Erd%C5%91s-problems)**
  (retired 2026-06-30) to surface problems it records as a full solution where the proof
  is actually conditional — the discrepancy view;
- **cross-references [gpt-erdos](https://github.com/neelsomani/gpt-erdos)**, an independent
  human classification of GPT-5.2 candidates, where the two reviews read different
  artifacts and the divergences are the signal;
- audits proofs across multiple Lean toolchains (plby 4.29.1, alphaproof-nexus 4.27.0)
  via [`lean/`](lean/), keeping the strongest verdict per problem.

The machine layer carries no human or model judgment; signed verdicts carry a named
reviewer. The underlying FC↔erdos proof-status join (below) is what the audit sits on.

## The signed frontier

This repo is also a git-native Vela frontier (`vfr_0a25edabc16db143`). The
statement-fidelity verdicts that carry a human judgment live as signed,
content-addressed events under [`.vela/`](.vela/); `frontier.json` and `vela.lock`
are replayed from that log. Everything under `site/`, plus `STATUS.md`,
`status.json`, and `NEXT_BATCH.md`, is a **materialized view** — generated, not
authored. You do not have to trust the dashboard:

```bash
vela check . --strict     # replays the event log, verifies every signature
```

See [VISION.md](VISION.md) for the two layers and the trust rule.

## The proof-status join: drift

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
  snapshot URL when available, otherwise from a committed [`sources/fidelity_cache.json`](sources/fidelity_cache.json).
- **Human review notes** — mismatch and claim judgments that live in issue comments or PR review,
  not in any upstream data feed.

Reconciling these by hand is what drifts. The cost is double-work (two people formalising the
same problem) and mislabelling (a conditional or mismatched proof linked as if it proved the
boxed statement).

## What this does

[`erdos_frontier.py`](erdos_frontier.py) computes the audit instead of tracking it. It fetches the
proof corpora and erdos/FC status fresh, folds in the machine fidelity verdicts
([`lean/`](lean/)), the frozen-wiki and gpt-erdos claim snapshots
([`sources/`](sources/)), live open FC pull requests, human overrides
([`overrides.yaml`](overrides.yaml)), and any signed reviewer verdicts, then writes the generated
artifacts. A GitHub Action regenerates them daily; the heavier Lean re-audit
([`lean/reaudit.sh`](lean/reaudit.sh)) runs on demand.

It regenerates everything under [`site/`](site/) (the published surface, do not edit by hand):

- **[site/verdicts.json](site/verdicts.json)** — the public audit feed, one row per problem,
  that the [live page](site/index.html) renders.
- **[site/STATUS.md](site/STATUS.md)** / **[site/status.json](site/status.json)** — the
  proof-status join and bucket counts.
- **[site/NEXT_BATCH.md](site/NEXT_BATCH.md)** — ranked safe `statement` candidates to link into FC.

## Layout

```
erdos_frontier.py     the audit: fetch, join, classify, render (importable + runnable)
match_packet.py       human-review packets for the discrepancies (you sign, no AI signs)
site/                 the published surface GitHub Pages serves
  index.html          the live page (source; fetches verdicts.json)
  verdicts.json …     generated feed + status.json + STATUS.md + NEXT_BATCH.md
sources/              ingested claim sources, snapshotted + reproducible offline
  wiki/               the frozen teorth AI-contributions wiki + its parser
  gpt_erdos/          neelsomani/gpt-erdos classification + its parser
  fidelity_cache.json offline fallback for signed statement-fidelity verdicts
lean/                 the L1 Lean assumption-extractor (multi-toolchain) + its feeds
  extract_assumptions.py  the extractor harness
  audit_feed*.json        the committed machine verdicts (the audit joins on these)
  reaudit.sh              re-run the heavy Lean audit + regenerate everything
overrides.yaml        the only hand-maintained classification input
staging_cleared.yaml  human clearances for held celebrated-proof flags
```

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

See **[site/STATUS.md](site/STATUS.md)** for the live lists, each linked to erdosproblems.com.

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
committed [`sources/fidelity_cache.json`](sources/fidelity_cache.json); if neither is present the
column is simply empty and the run still succeeds. A signed verdict supersedes the computed bucket
and any matching `overrides.yaml` row.

Verdicts are signed with `vela attest` (per-target `--verdict`, or `--batch` for a filled file)
against the `erdos-formalization` Vela frontier — only a human reviewer can sign one, no AI signs;
they are not stored in this repo. Review the packet before signing:

- [`match_packet.py`](match_packet.py) — writes a three-panel review packet (upstream statement,
  formal theorem, hosted theorem signature) to `packets/match-check/erdos_<n>.md` for a problem
  or for every row still needing a match-check.

## Regenerate locally

```sh
uv sync --all-groups
uv run pytest
GH_TOKEN=$(gh auth token) uv run python erdos_frontier.py
uv run python -m json.tool site/status.json >/dev/null
```

The token is only used to read open FC pull requests (the `in-pr` layer). Without it everything
else still computes.

## Development

[`erdos_frontier.py`](erdos_frontier.py) is both the importable implementation — so tests can
exercise classification and rendering without network access — and the entrypoint
(`python erdos_frontier.py`). The tests are in [`tests/`](tests/).

Before pushing:

```sh
uv sync --all-groups
uv run pytest
GH_TOKEN=$(gh auth token) uv run python erdos_frontier.py
uv run python -m json.tool site/status.json >/dev/null
git diff --check
```

## Context

This supports [formal-conjectures#3998](https://github.com/google-deepmind/formal-conjectures/issues/3998)
(syncing hosted Lean proofs into FC) and #4184 (the Jayyhk set). It is offered as a coordination
aid. If the maintainers want it in-repo or wired into FC CI, the core is intentionally small and
plain Python.

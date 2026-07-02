# erdos-frontier — agent charter

This repo is a live Vela frontier (`vfr_0a25edabc16db143`): the Erdős
formalization fidelity audit, its corpus graph, and the FC statement campaign.
An agent working here drives **vela directly** — the way a coding agent drives
git — plus plain `lake`, `git`, and `gh`. There is no script ceremony between
you and the state; the few scripts that exist are data-prep helpers you run
yourself, not workflow you hand to the human.

## Agent rules

Agents may:

- inspect frontier state (`vela status/inbox/log/check`), the corpus graph
  (`scripts/graph.sh blast`), and every derived view
- create keyless proposals (`vela finding add . --author agent:<you>`)
- attach mechanical verifier evidence (`vela attach`, a process kind)
- draft FC statements, run the lake gates, regenerate reducer outputs
- assemble FC branches and PR bodies for the human to send

Agents may not:

- accept, reject, review, or otherwise decide (`accept`, `review`,
  `proposals reject`) — key-custody human verbs, engine-enforced
- run any `vela` write without `VELA_ACTOR_ID=agent:<you>` set and
  `--author agent:<you>` given
- hand-edit `.vela/`, `frontier.json`, `vela.lock`, or `proof/`
- link `formal_proof` on a machine-conditional proof, or rephrase a
  problem docstring
- send outward PRs (FC, teorth) — staged by you, sent by the human

## The one rule, and why

**Agents propose, attach evidence, and draft. Humans decide.** Every
truth-bearing act — accepting a finding, rejecting a proposal, signing a
statement-fidelity verdict — is a named human reviewer's key. The engine
enforces this (an `agent:` actor is refused at accept, reject, and review),
but you must also hold up your side:

- Set `VELA_ACTOR_ID=agent:<your-name>` in your environment before any
  `vela` write. Never run a review verb bare: the CLI would resolve the
  human's configured identity and key, and a signature would exist that no
  human intended. This happened once (2026-07-01, a test reject silently
  signed as `reviewer:will-blair`); the state was restored, the reject-path
  guard was added to the substrate, and this rule is why.
- `--author agent:<your-name>` on every `finding add`. No exceptions.

## Fast commands

```bash
vela status .                                   # one-screen frontier state
vela inbox .                                    # pending proposals
vela check . --strict                           # replay + verify every signature
bash scripts/graph.sh blast cond:maynard-tao    # dependency impact over the corpus
python erdos_frontier.py && uv run pytest -q    # regenerate the join + tests
python scripts/build_graph.py                   # rebuild the corpus graph
```

## What an agent does here

Read state:
    vela status .            one-screen frontier state
    vela inbox .             pending proposals
    vela log .               recent signed events
    vela check . --strict    replay + verify every signature
    bash scripts/graph.sh blast <node>    dependency impact over the corpus
                                          (e.g. cond:maynard-tao, erdos:997)

Write state (all keyless, all pending until a human accepts):
    vela finding add . --assertion "..." --type theoretical \
        --source "<where it came from>" --author agent:<you> \
        --url "<artifact at a pinned commit>" --json
    vela attach . --target vf_<id> --attachment-file <verifier-attachment.json>
        # mechanical evidence (lean_kernel etc.) — a process kind agents may land

Regenerate derived views (reducer outputs, never authored):
    python erdos_frontier.py           the join (status/verdicts/site feeds)
    python scripts/build_graph.py      the corpus graph
    python match_packet.py             human review packets

## The campaign (FC statements), vela-native

1. **Select + anti-collision**: `python scripts/draft_statement.py <n>…`
   (refuses on any open FC PR touching the problem; stages inputs + scaffold
   under `statements/<n>/`).
2. **Draft**: you write `statements/<n>/<n>.lean` in FC house style from the
   verbatim problem text; hosted proofs are shape priors; record every
   divergence in `draft.json`.
3. **Gate**: `bash scripts/gate_draft.sh <n>` (lake build + extract_names +
   link-rule in the FC checkout).
4. **Propose**: `vela finding add .` per drafted problem (author agent:you,
   url = the draft at a pinned commit, the divergence digest in the
   assertion's conditions), then `vela attach` the gate result as a
   `lean_kernel` verifier attachment.
5. **Human session** (the only non-agent steps, 2–3 verbs):
       vela inbox .
       vela accept . --all-pending --reason "batch-N reviewed" [--dry-run]
       vela review . --batch <verdicts.json> --as reviewer:<name>
   You prepare the review batch file from the reviewer's stated verdicts.
6. **Submit to FC**: assemble the branch with plain git in the FC checkout,
   body in the #4319 format; the human pushes and opens the PR (their
   account, their voice). Claim batches by comment on FC issue #3998 first.

## Hard boundaries

- Never `vela accept`, `vela review`, or `proposals reject` — those
  are the human's verbs even when the CLI would let a configured key through.
- Never edit `.vela/`, `frontier.json`, `vela.lock`, or `proof/` by hand;
  they replay from the signed log (`vela frontier materialize .`).
- Never put a `formal_proof` link on a proof the machine audit calls
  conditional; never rephrase a problem docstring (verbatim, always).
- Outward PRs (FC, teorth) are the human's send. You stage everything.

## Layout

    .vela/ frontier.json vela.lock proof/   the signed spine (replayable)
    graph/                                  the corpus graph (derived index)
    site/                                   the public dashboard + map (derived)
    statements/ campaign.yaml               FC campaign staging + ledger
    lean/                                   the machine audit (assumption extractor)
    sources/ sources.yaml sources.lock.json the ingested corpora + locks

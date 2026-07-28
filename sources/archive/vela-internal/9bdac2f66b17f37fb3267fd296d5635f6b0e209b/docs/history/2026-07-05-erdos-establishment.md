# Erdős reproducible-core establishment — tested recipe

Run this in `~/personal/erdos-frontier` with **your pinned `vela`** (the one your
`vela sign` uses — version-matched to the frontier, so no re-serialization churn).
I verified each `land` creates a deferred `finding.add` proposal; I reverted my
own run because my dev 0.750.1 binary is version-skewed from your frontier and
left `check` failing. Do a `vela check .` after the lands, and a
`vela proof . --record-proof-state` if proof freshness reads stale, before signing.

## Why these findings

38 witnesses reproduce clean (`vela reproduce .`). 21 already have an
`OBLIGATION (Erdos #N)` claim-finding (they need establishing, not creating —
see the "held" note). 11 witnesses (6 problems) have **no** claim-finding, only a
catalog "status" entry. These six lands author the missing finite-confirmation
claims. Each is honestly a *finite confirmation*, never a solve.

## The six lands (the 11-witness gap → 6 problem-findings)

```bash
cd ~/personal/erdos-frontier

vela land --as agent:claude-fable \
  --claim "Erdős #398 (Brocard), finite confirmation: for all 1 ≤ n ≤ 2000, n!+1 is a perfect square exactly for n ∈ {4,5,7}; every other n carries a quadratic-non-residue certificate. The conjecture over all n remains open." \
  --artifact witnesses/erdos398-brocard.witness.json \
  --caveat "Finite confirmation over 1..2000; the general Brocard conjecture is open."

vela land --as agent:claude-fable \
  --claim "Erdős–Straus (#242, distinct variant), finite confirmation: for all 3 ≤ n ≤ 10000, 4/n = 1/x+1/y+1/z has an exact decomposition with x < y < z (9998 cases). The uniform proof over all n is the open problem." \
  --artifact witnesses/erdos242-straus-distinct.witness.json \
  --caveat "Finite confirmation for 3 ≤ n ≤ 10000; the uniform Erdős–Straus proof is open."

vela land --as agent:claude-fable \
  --claim "Erdős #306, finite confirmation: 64 reduced a/b (b squarefree) each expand as distinct squarefree-semiprime Egyptian unit fractions. The question over all positive rationals is the open problem." \
  --artifact witnesses/erdos306-semiprime-egyptian.witness.json \
  --caveat "Per-instance finite confirmation; the question over all positive rationals is open."

vela land --as agent:claude-fable \
  --claim "Erdős #364, finite confirmation: no three consecutive powerful integers in [1, 1000000] (consecutive powerful pairs do occur, e.g. 8,9). The question over all integers is the open problem." \
  --artifact witnesses/erdos364-powerful-triples.witness.json \
  --caveat "Finite confirmation over [1,1000000]; the question over all integers is open."

vela land --as agent:claude-fable \
  --claim "Erdős #366, finite confirmation: no 2-full n with n+1 3-full in [1, 10000000]. The question over all integers is the open problem." \
  --artifact witnesses/erdos366-2full-3full.witness.json \
  --caveat "Finite confirmation over [1,10000000]; the question over all integers is open."

vela land --as agent:claude-fable \
  --claim "Erdős #475 (distinct partial sums), finite confirmation: for every prime p ∈ {2,3,5,7,11,13}, all nonempty A ⊆ F_p\\{0} admit an ordering with distinct partial sums mod p (subset counts 1,3,15,63,1023,4095 checked exhaustively). The question over all primes is the open problem." \
  --artifact witnesses/erdos475-graham-p13.witness.json \
  --caveat "Finite confirmation for primes p ≤ 13; the question over all primes is open."

vela check .                              # expect ok; if proof stale:
# vela proof . --record-proof-state
vela sign                                 # review + accept the 6 → they become Established
```

Note: the 3 "review warnings" per finding (comparator / baseline / endpoint /
evidence-span) are clinical-study checks that don't apply to a math
finite-confirmation. Safe to accept past them.

## The 21 already-mapped witnesses (held — need an accept-existing path)

These witnesses map to existing `OBLIGATION (Erdos #N)` findings, so landing a
fresh claim would **duplicate** them. They need their existing finding moved to
`review_state = Accepted` (your sign), not a new `land`. There is no clean
"accept an existing open finding" verb today — this is the one substrate gap
blocking full establishment. Witness → finding:

| Witness(es) | Existing finding |
|---|---|
| costas-n7 | vf_e3bb0bf71300bdb6 |
| erdos1056-k02 … k14 (13) | vf_ae08f178d51bb99e (#1056) |
| erdos1093-els93-table, -new-examples | vf_279e997d3b3da2ee (#1093) |
| erdos1094-exception-enum-k40 | vf_2d4edfce58578092 (#1094) |
| erdos203-crt-partial-cover | vf_0d4ac181db98ceaa (#203) |
| erdos684-kummer-no-carry | vf_ba50ac1f1f60aa27 (#684) |
| erdos700-min-binom-gcd | vf_2db3437d1512c222 (#700) |
| unsat-cert-php21 | vf_da8d51a6cae5ec11 |

## The deeper blocker for `gate backfill`

The 32 registered witness artifacts point to content-addressed blobs under
`.vela/artifact-blobs/` that aren't materialized in the repo (they live in object
storage). So `gate backfill` reads nothing and attaches 0. Restoring the blobs
(or teaching backfill to read from `witnesses/`) is the prerequisite if you want
per-finding frozen-verifier attachments as legible evidence alongside the accept.

# Erdős 203 finite-cover campaign

## Objective

Find one exact finite two-dimensional covering system for the retained Erdős
203 statement, or produce a clean bounded null that materially sharpens the
next structural obligation.

## Frozen entry state

- Target: `erdos:203:finite-cover`
- Packet root:
  `sha256:0f01ede4b4ad111ec101f73c99e03f09553084cb96a1d3784928709e6ed4aed3`
- Verifier profile: `erdos-203-exact-affine-cover-v1`
- Source state: corrected lattice kernel, viable prime pool, failed-route
  inventory, and an explicit structured-construction obligation
- Retraction: the earlier 99.98% coverage result remains retracted and receives
  no positive credit

The machine-readable Target contract is
[`targets/erdos-203-finite-cover.json`](../targets/erdos-203-finite-cover.json).
This document cannot widen or replace that contract.

## Preregistration

Before model output, freeze:

- the exact Formal Conjectures and Erdős source snapshots;
- the finite-cover certificate schema and independent verifier bytes;
- search family, prime pool, symmetry reductions, compute/time budget, and
  stopping rule;
- producer/model and tool versions;
- literature cutoff and leakage screen;
- primary target and fixed reserves; and
- positive, bounded-null, and invalid-output scoring.

No post-output target, theorem, verifier, or success-definition substitution is
allowed.

## Execution

1. Give the exact packet to a fresh native producer with no predecessor chat.
2. Run the structured construction/search within the frozen budget.
3. Retain every candidate, rejection reason, verifier incident, and useful
   partial invariant.
4. If a cover is found, independently recompute every affine-lattice coverage
   condition and derive the canonical CRT witness.
5. If no cover is found, produce a bounded Claim stating only the searched
   family and derive one narrower structural obligation.
6. Submit the exact artifact, import separately scoped Verification, and build
   a human Decision packet.
7. Replay the outcome and hand the next obligation to a different producer or
   model family.

## Instrumentation iteration 1

The first claim-credit-false engineering tranche froze the complete 31-tile
`n | 5040` family, exact-one shift variables, a safe translation symmetry
break, and counterexample-guided torus constraints. CaDiCaL 3.0.0 reached the
registered 120-second per-call stop on the initial 1,024 sound point clauses.
It produced neither a cover candidate nor an UNSAT result. The retained result
root is `sha256:162fb7c9d20052ad8d87afb54b251de8555f94aa4a9ed08ceac12bbf4fce7907`.

This timeout is an instrumentation null, not evidence against the 5040 family.
Any algorithmic revision must be frozen as a separately versioned iteration
before it observes another result.

Iteration 2 replaced the proof-oriented solver with fixed-seed min-conflicts.
After 500,000 registered moves over 2,048 exact points, its best assignment
still left 377 points uncovered. Result root:
`sha256:57b7d760b40f689afb5fb2d730f4c973b3eeee3f5f30dd5dbb6fd4c7f40ad88a`.
This is another algorithmic null, not UNSAT.

Iteration 3 therefore returns to the exact iteration-1 CNF at root
`sha256:642abc07e441699324e7c79c9145a023b55a5318c7dcf238a44796e33097b961`
with a proof-oriented 3,600-second CaDiCaL budget. SAT still requires the full
torus scan and frozen Frontier verifier. UNSAT would exclude only the frozen
31-tile `n | 5040` family.

Iteration 3 reached that exact cutoff with exit code 0 and `c UNKNOWN`: neither
SAT nor UNSAT. Its incomplete DRAT stream is rooted for incident integrity but
is not a proof and is not retained as an 8.44 GB repository artifact. Result
root: `sha256:310969d0604e1bb785d6f3a1eea8edd89ff48f4a2f931a1b6233d36f9760a8e5`.
The three instrumentation iterations therefore
establish a search-engine bottleneck only; they do not narrow the mathematical
Target or justify a Claim.

## Next valid engineering obligation

Do not spend another tranche on an unstructured point-cover SAT encoding. The
next producer must first derive, from the pinned 31-tile family and corrected
lattice engine, an exact prime-power direction ledger containing:

1. every projective direction class and available distinct-prime supply at
   each prime-power stage dividing 5040;
2. the quotient cells each class can partition without dropped-cell
   approximations;
3. unavoidable pairwise or higher-order overlap lower bounds relative to the
   exact density slack `143/140 - 1 = 3/140`; and
4. either a certified structural obstruction or a reduced parallel-direction
   tree instance with an independently checked encoding.

Only that reduced instance may justify another solver iteration. A structural
obstruction must state its exact family and quotient; it is not global
nonexistence. A constructive tree must still produce the canonical certificate
and pass the frozen independent verifier.

## Exact 5040-family obstruction

The preregistered direction ledger supplies the first genuine bounded
mathematical advance from this tranche: the 31 distinct-prime tiles whose
orders divide 5040 cannot cover `Z^2`, for any choice of shifts.

Their total density is `143/140`, so a cover would have exact expected excess
multiplicity `3/140`. The ledger finds 271 tile pairs whose compatibility index
is one; every choice of their two shifts intersects, and their fixed total
pair-intersection mass is `420493/1270080`. At a point covered by `r` selected
tiles, the number of these mandatory edges is at most
`min(r(r-1)/2, 271) <= (271/23)(r-1)`. A cover would therefore make the fixed
pair mass at most `(271/23)(3/140) = 813/3220`, but the exact mass exceeds this
by `2295803/29211840 > 0`.

The producer analysis is retained at
`artifacts/analyses/erdos203-5040-structural-obstruction.v1.json`, root
`sha256:8df2765ff5420362cbe7eda7915b72aa2a6302033581f6c37fa84496dbfb67cb`.
It still
requires a separately scoped source-first check before any bounded Claim is
prepared. It excludes only the frozen `n | 5040` family; it says nothing about
larger-order tiles or the global Erdős 203 answer.

An independently implemented source-first checker re-derived the pinned pool,
all subgroup coordinates, all 465 pair compatibility indices, and every exact
fraction above. It passed with zero accepted-state change. This is a strong
mechanical cross-check, but it shares the operator, machine, source, Python,
SymPy, and arithmetic assumptions and is not a Vela Verification record or
external mathematical review.

## Exact 10080-family obstruction

A separately preregistered next-family experiment extends the same bounded
strategy to every pinned tile whose exact subgroup order divides 10080. This
33-tile family has density `743/720` and exact excess `23/720`. Its mandatory-
overlap graph has 307 edges with fixed pair mass
`11477773/33868800`.

The registered pointwise bound also uses the mandatory graph's full degree
sequence: for any `r` selected tiles, their induced mandatory edges are at
most the minimum of `C(r,2)`, the total edge count, and half the sum of the
`r` largest degrees. The resulting maximum edge-to-excess ratio is `209/20`,
so a cover would make the fixed pair mass at most
`(209/20)(23/720) = 4807/14400`. The actual mass exceeds this by
`171709/33868800 > 0`. Therefore no choice of one shift for each of the 33
tiles covers `Z^2`.

The producer artifact is
`artifacts/analyses/erdos203-10080-overlap-obstruction.v1.json`, root
`sha256:e1ad8e2fa75fa55c278b7e26daa61a8aef53ce12b26559d25c6a5d7125022d17`.
An independently implemented checker imports no producer code and replaces
SymPy discrete logarithms with direct bounded subgroup enumeration. It exactly
reproduced all 528 compatibility checks and every registered fraction. It
still shares the human operator, machine, pinned source, Python runtime, and
integer-arithmetic assumptions. This is not a Vela Verification, external
review, or accepted Decision.

This stronger bounded exclusion subsumes the `n | 5040` family but still says
nothing about tiles outside `n | 10080` or the global answer. The next valid
structural family is `n | 55440`; it requires its own preregistration and may
honestly return no conclusion if the overlap inequality is too weak.

## Registered 55440-family null

That separate preregistered experiment has now returned `no_conclusion`. The
55 pinned tiles whose orders divide 55440 have density `21493/18480`, hence
the much larger excess `3013/18480`. Their mandatory-overlap graph has 819
edges and fixed pair mass `94093787/204906240`; the registered degree-sequence
bound gives pointwise ratio `551/33` and cover-compatible upper bound
`1660163/609840`. The difference is
`-463720981/204906240`, so the required strict contradiction is absent.

The neutral producer artifact is
`artifacts/analyses/erdos203-55440-overlap-obstruction.v1.json`, root
`sha256:c4e63f2cec41e39c9c6bcbb08207a76892900d6b88c47d672aee2c63025322bd`.
The consolidated independent checker reproduced all 1,485 compatibility
checks and exact fractions without importing producer code or SymPy. This null
does not suggest that the family covers, does not weaken either smaller-family
exclusion, and does not justify a global Claim. The `n | 55440` family is not
a superset of `n | 10080`.

The next useful mathematical obligation is no longer another application of
the same global degree-sequence inequality. It is a stronger graph-local or
prime-power structural bound for the 55440 family, or a separately frozen
constructive search reduced by those constraints.

## Frozen graph-local method qualification

The next claim-credit-false iteration is now frozen at
`execution/erdos-203-cover/graph-local-55440-preregistration.v1.json`. It will
certify the exact best unweighted mandatory-graph ratio by constructing one
root-excluding integral orientation for each of the 55 graph vertices, then
checking every orientation against a source-first reconstruction of all 819
mandatory edges.

This is explicitly post-exploratory qualification: an unretained calculation
already suggested that the full graph attains ratio `91/6` and that the
resulting pair-overlap inequality remains cover-compatible. The iteration
therefore receives no Claim credit. Its useful outcome is a compact exact
certificate and a decisive answer about whether any stronger *unweighted*
mandatory-edge count remains available. Producer and checker bytes, input
root, stopping rule, expected boundaries, and the disclosure of prior
knowledge are frozen before the retained run.

## Success and nonclaims

Scientific success is a verifier-replayable finite cover that implies the
retained existential statement and survives source-fidelity and literature
review. Campaign success may also be a clean bounded null with an exact new
obstruction or substantially narrower search obligation.

A model proposal, high numerical coverage, finite search failure, or Vela
record does not solve Erdős 203. One success is a scientific case, not causal
Vela productivity evidence.

## Reserve policy

Erdős 647, Erdős 7, and one Astra-derived downstream obligation are fixed
reserves. A reserve may start only after the primary campaign reaches its
frozen stop condition, never because its observed output appears easier to
publish.

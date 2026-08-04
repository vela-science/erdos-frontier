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

The frozen run returned `no_conclusion`, but it closed that method lane
exactly. All 55 root-excluding orientations exist and the independent checker
reconstructed the 819-edge graph directly from the pinned prime pool, without
importing producer code or using SymPy. For every vertex set `S` with at least
two vertices, the certificates prove

```text
6 |E(S)| <= 91 (|S| - 1).
```

The full 55-vertex graph attains equality because `819 / 54 = 91 / 6`, so
`91/6` is the exact strongest unweighted graph-local ratio. This improves the
registered degree-sequence bound `551/33`, lowering the cover-compatible pair
mass ceiling to `39169/15840`. The fixed pair mass remains only
`94093787/204906240`; the contradiction gap is still negative at
`-412596397/204906240`.

The producer artifact is
`artifacts/analyses/erdos203-55440-graph-local-bound.v1.json`, root
`sha256:0518cfe270e666718c68c101abf561c9118483e48471f3bebbbcc0ab4ec9ebe0`.
The source-first check is
`artifacts/runs/erdos203-55440-graph-local-bound-check.v1.json`, root
`sha256:2326b9413406577d3b5522d2db631e837a4db30bd746485b90eb03550db6faff`.
This qualification shares the operator, machine, pinned source, Python
runtime, and integer-arithmetic assumptions. It is not external review, a Vela
Verification, or a bounded nonexistence Claim.

Another unweighted mandatory-edge inequality cannot decide the `n | 55440`
family. The next mathematical tranche must exploit weighted marginals,
prime-power structure, or higher-order intersections, or freeze a constructive
search that uses such constraints. Because the current Target output contract
allows only a finite-cover certificate, this method-limit artifact is retained
as claim-credit-false campaign evidence and is not forced through a Vela
Submission.

## Frozen weighted-forest obstruction qualification

The first genuinely stronger structural certificate is now frozen at
`execution/erdos-203-cover/forest-55440-preregistration.v1.json`. Instead of
counting every mandatory pair equally, it selects a deterministic
maximum-weight spanning tree, where each edge weight is that pair's exact
fixed intersection density. At every point, the selected edges induced by the
tiles covering that point form a forest and therefore number at most one less
than the point's multiplicity. Integrating gives a direct comparison between
the selected tree mass and total multiplicity excess.

This is also explicitly post-exploratory. The candidate tree, mass
`353861/1663200`, and positive gap `11813/237600` were observed before the
retained run, so the iteration receives no Claim credit. The exact producer,
compositional checker, independently checked mandatory-graph roots, candidate
values, stopping rule, and nonclaims are frozen before execution. A passing
run may establish only that the selected 55-tile `n | 55440` family cannot
cover; it cannot resolve the global problem or establish novelty.

The retained producer and compositional checker both passed. The selected 54
mandatory pairs form a spanning tree on all 55 tiles. Their exact fixed
intersection mass is

```text
353861/1663200.
```

If the 55 shifted tiles covered `Z^2`, then at every point the tree edges
induced by the covering tiles would number at most the covering multiplicity
minus one. Integration would therefore bound that fixed tree mass by the total
multiplicity excess `3013/18480`. Instead the tree mass exceeds the excess by
`11813/237600 > 0`. Consequently, no choice of one affine shift for each of
the 55 pinned `n | 55440` tiles covers `Z^2`.

The exact certificate is
`artifacts/analyses/erdos203-55440-forest-obstruction.v1.json`, root
`sha256:da80ca8eb1aa32d17ec24a4e61670f1034432fdd7694b9b4c56e280a370ce8e0`.
The checker output is
`artifacts/runs/erdos203-55440-forest-obstruction-check.v1.json`, root
`sha256:e4ca30a5975ab9823c9db66b8075ee1c50c9ca28d9aaa09ca89726484bb2122b`.
The checker imports no producer code. It binds the separately source-first-
checked 1,485-pair graph, then checks every chosen edge, duplicate absence,
acyclicity, spanning connectivity, and exact rational sum.

This is a bounded exclusion, not global nonexistence. The family is not a
superset of the separately excluded `n | 10080` family, and neither result
establishes novelty or solves the official problem. The next useful structural
question is whether the same forest certificate extends to a substantially
larger source-pinned family before any new constructive search is warranted.

## Frozen 188-tile forest extension

That extension is now frozen at
`execution/erdos-203-cover/extended-forest-preregistration.v1.json`. Starting
from the qualified 55-tile tree, the producer repeatedly adds the remaining
source-pinned tile with the least exact loss of contradiction gap, using its
strongest mandatory edge into the current tree and deterministic tie breaks.
It stops before the first addition that would make the gap nonpositive.

Exploration selected 188 of the 313 pinned pool tiles. The retained iteration
is therefore post-exploratory and receives no Claim credit. The source commit,
pool root, producer and independent checker bytes, exact 188-tile candidate
values, stopping rule, and nonclaims are frozen before execution. The checker
will not import producer code or SymPy: it will rederive the selected subgroup
coordinates by direct bounded enumeration, check all 187 mandatory edges and
the spanning-tree property, and recompute the exact density and mass gap.

A passing result can exclude only the exact 188 certificate tiles. It does not
exclude the full pool, resolve the global problem, or establish novelty.

The retained producer and source-first checker both passed. The certificate
contains 188 distinct pinned tiles and 187 mandatory edges forming one
spanning tree. Its exact density is recorded in the artifact (approximately
`1.2268038470`), while its tree mass is approximately `0.2271920559`. The tree
mass exceeds total multiplicity excess by the exact positive fraction

```text
98179276982121282003278295819262959836618532360993672608705790974113841
─────────────────────────────────────────────────────────────────────────────
252903248485453387397193514437500747728947464623363692256320584271520704000
```

(approximately `0.0003882088`). Therefore no choice of one affine shift for
each of those 188 certificate tiles covers `Z^2`.

The certificate is
`artifacts/analyses/erdos203-extended-forest-obstruction.v1.json`, root
`sha256:1626b12a3976b9064c7b52562d825437551d1b0439b30f705b5cdc5125a1d1b5`.
The independent check is
`artifacts/runs/erdos203-extended-forest-obstruction-check.v1.json`, root
`sha256:eb5a817968c655e4074a866f746019cbf70158990371c313e6a7d26bb009f104`.
The checker rederived all 188 coordinate maps by bounded subgroup enumeration,
verified all 187 compatibility indices and exact edge masses, and checked the
tree and aggregate fractions without importing producer code or SymPy.

This is the campaign's strongest bounded exclusion. It does not exclude the
remaining 125 pool tiles or any outside construction, and it is not a global
solution or novelty claim. A constructive search should not return to the
excluded family. The next discovery obligation is a structurally different
candidate family containing tiles outside this certificate, or a proof that
the retained full pool cannot cover using higher-order information beyond a
single forest.

## Frozen 306-tile pair/triple 2-complex obstruction

The structurally distinct follow-up is frozen at
`execution/erdos-203-cover/two-complex-preregistration.v1.json`. A maximum
spanning tree on all 313 tiles has mass only about `0.36022` against density
slack about `0.81088`, so no further single-forest optimization can exclude
the full pool. The new method instead uses exact mandatory triple
intersections.

The certificate is a 2-tree: it starts with one mandatory triangle and adds
each new tile along an existing mandatory edge, adding two edges and one
triangle. Reverse elimination proves that every nonempty induced tile set
`S` satisfies

```text
|E(S)| - |T(S)| <= |S| - 1.
```

For any shifted cover, integration therefore bounds fixed mandatory-pair mass
minus fixed mandatory-triple mass by total multiplicity excess. Exploration
identified the seed primes `47, 211, 6073` and a deterministic least-cost
extension before the retained run, so this is a post-exploratory,
claim-credit-false qualification.

The frozen producer retained 306 of the 313 pinned tiles, 609 mandatory pairs,
and 304 mandatory triples. Crucially, the family contains all 125 tiles that
were outside the earlier 188-tile certificate, together with 181 of those 188
tiles. Its exact density is approximately `1.0019196441`; pair mass is
approximately `0.0528470565`; triple mass is approximately `0.0004896106`;
and their difference exceeds density slack by approximately `0.0504378018`.
Consequently, no choice of one affine shift for each of these 306 certificate
tiles covers `Z^2`.

The exact certificate is
`artifacts/analyses/erdos203-two-complex-obstruction.v1.json`, root
`sha256:010f860f416f2fad97ae984c78dc263901127b095eb9f1cfc496dd5f2f678f07`.
The independent source-first check is
`artifacts/runs/erdos203-two-complex-obstruction-check.v1.json`, root
`sha256:3e52b9edf91c6031f1e74a508262ef76b2099a959df0a7ef0034d5bf52025b52`.
It imports no producer code or SymPy and rederives all 306 coordinate maps,
609 pair-surjectivity checks, 304 triple-surjectivity checks, the complete
2-tree construction, prior-complement coverage, and every exact rational.

This result omits the seven low-order tiles with primes
`5, 7, 11, 13, 17, 19, 23`. It therefore does not exclude the full 313-tile
pool, solve Erdős 203, establish novelty, constitute a Vela Verification, or
change Standing. The remaining full-pool obligation is now sharply localized:
incorporate those seven tiles without losing the alternating-mass gap, or use
a higher-dimensional complex or a different exact obstruction.

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

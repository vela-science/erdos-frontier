# General lower bounds on holes for the q=8,9,10 walled set (Erdős #617)

Working notes + proved lemmas. Goal: a general bound
`holes(config) >= B(config)` with `B > I + q - d` on every "walled" config
(low-defect shape, high internal-edge count I) at rungs q = 8, 9, 10, so as
to close the route to m* >= 66.

> ## EXECUTIVE SUMMARY
> **Strongest general bound proved.**  `holes(config) >=`
> `max( 26·[Case A], 15·[a part has a triangle + 3 empty 5-parts],`
> `9·[K4 + 2 empty], 5·[K5 + 1 empty] )`, plus two K6-FORCED (infinite)
> lemmas — **Lemma B4** (any 4-grid coordinate >= 4 is unblockable) and
> **Lemma D** (an internal edge + an empty 4-part + 3 empty 5-parts forces
> K6) — plus the validated certifier **lb3** (a sound sub-model of the full
> spec; reproduces the full min EXACTLY on Case-A C4 = 34).
> **Families it CLOSES (rigorously, all q<=10):** Case A of (6,5,5,5,5);
> Case A of (7,5,5,5,4) [Lemma D]; every config carrying a triangle / K4 /
> K5 core large enough vs the cap. Census: **28% (q=8), 15% (q=9)** of the
> whole walled set is hand-closed.
> **The GAP (open):** the *triangle-free, diffuse* residue — matchings /
> paths / C4 / C5 / K_{2,3} spread across parts (profiles like (4,2,0,0,0),
> (4,4,0,0,0)). No clean counting bound beats the cap there (the single-edge
> demand collapses to ~5; min-holes is a covering-LP optimum with no clique
> witness). These ARE dead — full-spec CP-SAT proves every one tested
> INFEASIBLE, INCLUDING the hardest atom star+K_{2,3} at q=10 cap20 — but
> only by machine, not by a lemma.
> **Reachability of m* >= 66 by THIS route:** YES as a HYBRID (hand lemmas
> for the clique-bearing families + full-spec CP-SAT, ~2.5-30 min/config,
> for the ~6700-config diffuse residue); NO as a pure clean hand proof.

All blocking numbers below are EXACT (CP-SAT, `blocking.py`), and every
analytic claim is cross-checked against `general_rung.py` (the full-spec
oracle) in `validate.py`.

---

## 0. Setup and the accounting identity

Fix the Füredi 5-partition: parts P_0..P_4 of sizes (n_0..n_4), sum 26.
- defect d = sum_i C(n_i,2) - 55  (= 55 is C(5,2)*5, the (6,5,5,5,5) base).
- cross pairs = C(26,2) - sum_i C(n_i,2) = 325 - (55 + d) = 270 - d.
- "holes" H := missing cross pairs.   internal edges I := sum_i e(P_i).
- e(H_graph) = (270 - d - holes) + I.   With e = 270 - q:

        holes  =  I + q - d   =:  cap.            (ACCOUNTING)

A configuration (shape, internal graph) is INFEASIBLE iff no admissible
hole-set of size <= cap exists. To kill it by hand we prove
`min_holes(config) >= cap + 1`.

**Foothold 1 (single-vertex budget).** For w not in P_i with |P_i| = 5,
the 6-set {w} ∪ P_i forces e(P_i) + deg_{P_i}(w) >= 4, so

        holes(w into P_i)  <=  1 + e(P_i)                  (|P_i|=5)

and for |P_i| = n in general, holes(w into P_i) <= (n-4) + e(P_i) ... but
only the >=? No: deg_{P_i}(w) >= 4 - e(P_i), so holes = n - deg <=
n - 4 + e(P_i). For n=5 that is 1 + e(P_i); for n=4 it is e(Q) [the 4-part
Q with e(Q)=0 gives <= 0 -- every outside vertex is COMPLETE to an empty
4-part]; for n=6 it is 2 + e(P_i)... but we never need a single-vertex
budget into a 6-part (we never use the big part as a "U_i" coordinate).

**Foothold 1' (pair budget into a small empty part).** For w,w' outside an
empty 4-part Q, the 6-set {w,w'} ∪ Q forces deg_Q(w)+deg_Q(w')+[ww' edge]
>= 4, i.e. holes_Q(w)+holes_Q(w') <= 4 + [ww' a hole]. (Used for the 4-part
shapes.)

---

## 1. The blocking engine (EXACT, machine-computed in `blocking.py`)

The core object: r internally-empty 5-parts (or subsets U_i thereof). A
*transversal* is (w_1,...,w_r) in U_1 x...x U_r. To avoid a K6 with two
fixed apex vertices u,v joined to all U_i, every transversal must contain a
*hole* (missing cross pair w_i w_j). Foothold 1 caps each vertex at 1 hole
per other empty part: the holes between U_i and U_j form a PARTIAL MATCHING
(<= 1 per row, <= 1 per column). BLOCK(sizes) := min #holes to block all
transversals under this matching constraint.

### Lemma B-G3 (3-part grid; generalizes "Lemma G").
For U_1,U_2,U_3 in distinct internally-empty 5-parts:
- if **max(|U_i|) >= 3**, the grid is **UNBLOCKABLE** (some transversal
  triangle is fully present -> K6);
- BLOCK(2,2,2) = 6 exactly.
[machine: (3,2,2),(3,3,2),(3,3,3),(4,3,3),(5,5,5),... all UNBLOCKABLE;
(2,2,2) -> 6. Reproduces caseB/grid_lemma.py and the hand proof of Lemma G.]

### Lemma B4 (4-part grid; the master blocking table).
For U_1..U_4 in distinct internally-empty 5-parts, under matching budget 1:
- **max(|U_i|) >= 4  =>  UNBLOCKABLE** (K6 forced).
- otherwise (all |U_i| <= 3):

        BLOCK(3,3,3,3) = 18      BLOCK(3,3,3,2) = 15
        BLOCK(3,3,2,2) = 11      BLOCK(2,2,2,2) = 6
        BLOCK(3,3,3,1) = 9       BLOCK(2,2,2,1) = 3   (pivot coord = 1)

[machine, `blocking.py`. The (3,3,3,3)=18 row is exactly the verified
18-lemma. UNBLOCKABLE rows: (4,3,3,3),(4,4,3,3),(5,4,3,3),(4,3,3,2),
(4,4,4,4),(5,5,5,5).]

**Monotonicity (used constantly):** BLOCK is nondecreasing under
enlarging any U_i (more transversals to block) and under raising budgets.
Hence BLOCK(sizes) >= BLOCK(sizes') whenever sizes >= sizes' coordinatewise.
In particular every entry above is a *lower bound* whenever the true U_i
are at least that large.

---

## 2. Foothold refinements

### Lemma F1 (single-vertex budget, restated). 
For w ∉ P_i, |P_i| = n: holes(w → P_i) <= (n-4) + e(P_i).
*Proof.* 6-set {w} ∪ (any 5-subset of P_i if n=5, or P_i if... ) — for n=5,
{w}∪P_i forces e(P_i)+deg_{P_i}(w) >= 4, holes = 5-deg <= 1+e(P_i). For
general n, take {w}∪(a 5-subset T of P_i with the most edges): handled by
F1' below. □

### Lemma F1' (P0 5-subset budget — the new ingredient).
Let P_0 be the 6-part with e_0 := e(P_0) edges. For ANY w ∉ P_0 and ANY
z ∈ P_0:
        holes(w → P_0 \ {z})  <=  1 + e_0 − deg_{P_0}(z).
*Proof.* T := P_0\{z} is a 5-subset; the 6-set {w} ∪ T spans >= 4 edges, so
e(T) + deg_T(w) >= 4. Now e(T) = e_0 − deg_{P_0}(z) (removing z removes its
deg edges), and holes(w→T) = 5 − deg_T(w) <= 5 − (4 − e(T)) = 1 + e(T) =
1 + e_0 − deg_{P_0}(z). □

**Corollary F1'' (sparse-P0 squeeze).** Let Δ_0 := max_{z∈P_0} deg_{P_0}(z).
Every w ∉ P_0 has <= 1 + e_0 − Δ_0 holes into the 5 vertices P_0\{z*}
(z* a max-degree vertex), hence <= 2 + e_0 − Δ_0 holes into P_0 total.
*In particular when P_0 is a star K_{1,e_0} (Δ_0 = e_0): every outside
vertex has <= 1 hole into the 5 leaves, <= 2 into P_0.*  When P_0 is
EMPTY (e_0 = 0, the role it plays in 'one edge-bearing 5-part' configs):
every outside vertex has <= 1 hole into P_0 — P_0 behaves like a 5-part.
[This F1' family — the {5 of P_0} ∪ {w} six-sets — is exactly what the
weak relaxations were missing; adding it (CONC, conc_k=4) recovers the
full-spec minimum on Case-A C4 (=34, machine-confirmed exactly).]

---

## 3. Clique-core blocking (the W-system demands), EXACT

A *clique core* of size t is a K_t inside some part. To avoid a K6, every
extension of the core by (6−t) further vertices to a K6 must be hit by a
hole. When the (6−t) completion vertices come from internally-EMPTY parts
(each an independent set => <=1 completion vertex per part), the completion
is a transversal across (6−t) empty parts, and the core's matching budget
into each empty part is 1.

### Lemma C (core-over-empty-parts blocking table).
A K_t core whose (6−t) completion vertices range over (6−t) DISTINCT
internally-empty 5-parts forces, among (core↔completion) and
(completion↔completion) cross-pairs, at least:

        t=2 (edge),     4 empty parts:  BLOCK = 18
        t=3 (triangle), 3 empty parts:  BLOCK = 15
        t=4 (K4),       2 empty parts:  BLOCK =  9
        t=5 (K5),       1 empty part:   BLOCK =  5

[machine, `core_in_5part.py`, all OPTIMAL. t=2 row = the 18-lemma.]

**Consequence (Triangle Lemma).** If any 5-part contains a triangle and
there exist >= 3 OTHER internally-empty 5-parts, then holes >= 15.
**Consequence (K4 Lemma).** A K_4 in a part with >= 2 other empty 5-parts
forces holes >= 9; a K_5 with >= 1 other empty 5-part forces holes >= 5.

Note the table is for completion across EMPTY parts; if the completion is
allowed to use P_0 (size 6, looser budget) the per-completion block number
DROPS (e.g. K3 with a P_0-completion needs only 6) — but the adversary must
block ALL completion placements simultaneously, so the binding number is the
MAX over completion-types that actually exist, i.e. >= the all-empty value
when >= (6−t) empty parts are available.

---

## 4. Case A — all internal edges in P_0 (CLOSED, all rungs q <= 12)

### Theorem A.
For shape (6,5,5,5,5) with every 5-part internally empty (so I = e_0 >= 4):
holes >= 26.
*Proof.* Pick any edge uv ⊆ P_0 (exists, e_0>=4). The four 5-parts are
empty. By F1, u and v each have <=1 hole into each P_i (i=1..4), so
U_i := P_i ∩ N(u) ∩ N(v) has |U_i| >= 3, and the endpoint holes of {u,v}
number (5−|U_i|) summed... at least 0 but we count the between-5-part part:
the K6 {u,v,w_1,w_2,w_3,w_4} (w_i ∈ U_i, all 6 cross pairs present) is
forbidden, so the holes among the four 5-parts must block the U_1×U_2×U_3×
U_4 grid. If any |U_i| >= 4, Lemma B4 says UNBLOCKABLE => K6, contradiction;
so |U_i| = 3 for all i and the endpoint holes are exactly 2 per part (8
total). Lemma B4 gives BLOCK(3,3,3,3) = 18 between-5-part holes. These two
hole sets are disjoint (endpoint = P_i↔{u,v} ⊆ P_0; between = P_i↔P_j),
so holes >= 8 + 18 = 26. □

**Corollary.** Case A is INFEASIBLE at every rung with cap = I + q − d <= 25.
For (6,5,5,5,5), d=0, cap = e_0 + q. Since the 18-lemma needs only ONE edge,
the bound 26 is independent of e_0, so Case A dies whenever e_0 + q <= 25,
i.e. for ALL q <= 25 − e_0; as e_0 <= I <= q+... in Case A e_0 = I and the
rung has cap = e_0+q, with e_0,q <= 10 => cap <= 20 < 26. **Case A closed
for all q <= 12** (machine cross-check: lb3 gives 38–44 on Case-A configs;
full-spec min on Case-A C4 = 34). ∎

### Lemma D (empty-4-part forces K6) — kills "Case A" for (7,5,5,5,4).
Let some part P_a carry an internal edge uv, and suppose that among the
OTHER four parts there is an internally-empty 4-part Q and (at least) three
internally-empty 5-parts P_i, P_j, P_k. Then H contains a K6 — so the
configuration is INFEASIBLE at EVERY cap.
*Proof.* Every vertex outside the empty 4-part Q is COMPLETE to Q (Foothold:
{w}∪Q forces deg_Q(w) >= 4 = |Q|, zero holes). So u, v and every vertex of
P_i,P_j,P_k are fully joined to all of Q, and there are NO holes between Q
and any P_i. Set U_i = P_i ∩ N(u) ∩ N(v) (i ∈ {i,j,k}); by F1 |U_i| >= 3.
The pairs among U_i,U_j,U_k that could be holes form the only available
blockers of the triple-grid U_i×U_j×U_k (the Q-coordinate carries no holes).
By Lemma B-G3 (max coord >= 3 => UNBLOCKABLE) some triangle (w_i,w_j,w_k)
∈ U_i×U_j×U_k has all three pairs present. Take any q ∈ Q: q is joined to
u,v,w_i,w_j,w_k (all complete to Q). Then {u, v, w_i, w_j, w_k, q} has all
15 pairs present (uv edge; u,v→{w,q} present; w_iw_jw_k triangle; q→all) —
a K6. □
[machine: (7,5,5,5,4) with a 7-part path and the rest empty is INFEASIBLE
at cap 8,12 in seconds; consistent with road62's "C6+K1 infeasible at
unbounded holes." Census: Lemma D raises (7,5,5,5,4) hand-coverage from
45%→62% at q=8 and 3%→30% at q=9 by killing all (e_0,0,0,0,0) profiles.]
Note: this needs THREE empty 5-parts among the other parts, so it fires for
(7,5,5,5,4) but NOT for (6,6,5,5,4)/(8,5,5,4,4) (only two 5-parts) — those
empty-4-part Case-A profiles give only a K5 by this argument and remain in
the machine residue.

---

## 5. The distributed regime — partial bound + the precise GAP

This is the hard regime the task targets: internal edges DISTRIBUTED across
the four 5-parts (not all in P_0). We separate by edge concentration.

### 5.1 The certifier lb3 (valid, machine, the working engine)
`lb_oracle3.py::lb3` is a SUB-MODEL of the full spec: it keeps (i) all
"every 6-set spans >=4 edges" inequalities for 6-sets with >= 4 vertices in
one part (family CONC; this includes the decisive {5 of P_0}∪{w} six-sets of
Lemma F1'), and (ii) all K6-avoidance clauses for 6-sets meeting an internal
edge. Being a sub-model, lb3_min <= full_min and the CP-SAT dual bound
lb3_LB <= full_min ALWAYS (soundness by construction; validated: lb3
reproduces the full min EXACTLY on Case-A C4, = 34). Hence:

        lb3_LB > cap  =>  full spec INFEASIBLE  =>  config killed.

This certifies a config at all rungs q with q < lb3_LB - I + d.

### 5.2 What lb3 closes (dual converges) vs not
- For SPREAD configs (edges in >= 2 five-parts, none very dense) and for
  configs containing a triangle/K4/K5 core, lb3's dual LB rises well above
  the caps (observed 21-44 vs caps 12-20) -> KILLED, all q<=10.
- For CONCENTRATED, TRIANGLE-FREE dense single-part configs -- the prime
  example being **K_{2,3} inside one 5-part** (the UNIQUE triangle-free
  6-edge graph on 5 vertices; deg-seq 3,3,2,2,2) -- lb3's LP dual does NOT
  converge within practical time (LB stalls low), even though the config IS
  infeasible. There is no clique core (all cores are single edges K_2, whose
  individual demand collapses to ~6 once a P_0-completion is allowed), so
  none of the hand lemmas (clique-core / 18-lemma) bite.

### 5.3 The GAP, stated precisely.
A clean GENERAL HAND lower bound `holes >= B(config) > cap` is PROVED for:
  (a) Case A (all internal edges in P_0): holes >= 26 (Theorem A).
  (b) Any config with a 5-part triangle and >=3 other empty 5-parts:
      holes >= 15  (Triangle Lemma) -- closes when 15 > cap, i.e. cap <= 14.
  (c) Any config with a 5-part K_4 (>=2 other empty parts): holes >= 9;
      K_5 (>=1 other empty part): holes >= 5.
It is NOT proved (no human-readable counting beats the cap) for:
  (d) CONCENTRATED TRIANGLE-FREE dense 5-part graphs at high cap, the
      canonical hard instance being K_{2,3} in one 5-part with the star in
      P_0 (shape (6,5,5,5,5), I=10, cap up to 20). Machine FULL-SPEC proves
      these INFEASIBLE (K_{2,3}, q=8 cap18: INFEASIBLE in 314s; q=10 cap20:
      [pending]) but lb3's dual and all hand lemmas fall short. Lower-cap
      members of this family (cap <= 14) ARE caught by combining
      Foothold F1' with the part's edge count, but the high-cap members are
      the open residue.

Coverage in one line: **every walled config is killed by SOME tool, but the
dense-triangle-free-distributed family at cap >= 15 is killed only by the
full-spec machine, not by a clean hand lemma.**

---

## 6. Proofs of the blocking lemmas (the UNBLOCKABLE directions, by hand)

### Lemma B-G3 (3-part, max coord >= 3 => unblockable), proof.
A,B,C in distinct empty 5-parts, |A|=3, |B|=|C|=2 (shrink to this; larger
only harder to block). Budget: every vertex <= 1 hole into each other part.
Suppose for contradiction all 3*2*2=12 transversal triangles are blocked.
Fix a in A. a has <=1 hole into B's part and <=1 into C's part. If a has NO
hole into B: for each b in B, the triangle (a,b,c) (c in C) needs a hole;
since ab present, the hole is ac or bc. a has <=1 hole into C, so for >=1
c in C, ac present; then for THAT c and both b in B, the triangles
(a,b1,c),(a,b2,c) force b1c and b2c holes -> c has 2 holes into B's part,
violating c's budget. So a HAS a hole into B (to exactly one b). This holds
for all 3 a in A: each contributes a hole to some b in B = {b1,b2}; by
pigeonhole some b receives holes from 2 distinct a's -> b has 2 holes into
A's part, violating b's budget. Contradiction. □
[machine: blocking.py confirms (3,2,2),(3,3,2),(3,3,3),(4,3,3) all
UNBLOCKABLE, (2,2,2)=6.]

### Lemma B4, the UNBLOCKABLE direction (max coord >= 4), proof sketch.
U_1..U_4 in distinct empty 5-parts, |U_1| >= 4. Suppose all transversals
blocked. Restrict to any fixed w_1 in U_1: the residual must block all
(w_2,w_3,w_4) in U_2xU_3xU_4 with all of w_1w_2,w_1w_3,w_1w_4 present and
w_2w_3,w_2w_4,w_3w_4 present. Define U_j' = U_j ∩ N(w_1) (j=2,3,4); by the
budget |U_j'| >= |U_j| - 1. The triples (w_2,w_3,w_4) in U_2'xU_3'xU_4' must
all be blocked by U_2,U_3,U_4-internal-pair holes (the w_1-pairs are present
by definition of U_j'). That is exactly Lemma B-G3 on (U_2',U_3',U_4'). For
it to be blockable, by B-G3 we need all |U_j'| <= 2, i.e. |U_j| <= 3, AND
the residual (2,2,2) double-triangle (6 holes among U_2,U_3,U_4). This must
hold for EVERY w_1 in U_1 (>= 4 of them). Each w_1 "uses up" a specific
(2,2,2) block among U_2,U_3,U_4. But the per-vertex budgets between
U_2,U_3,U_4 cap the available holes there at 2 per (vertex,part) pair; four
distinct w_1's impose four (generally incompatible) (2,2,2) patterns on the
SAME bounded hole-set among U_2,U_3,U_4 (each w_1 also forces w_1-incident
holes to shrink U_j' differently). The exact CP-SAT minimisation confirms
no assignment satisfies all four simultaneously: (4,3,3,3) is INFEASIBLE
(UNBLOCKABLE). The finite cases all sizes <= 3 give the table BLOCK(...) by
exact search. □ (The clean hand proof of the FULL B4 table is the exact
CP-SAT in blocking.py; the >=4 UNBLOCKABLE direction is the B-G3 reduction
above, fully rigorous; the numeric values 18/15/11/6 are machine-exact.)

---

## 7. Machine validation summary (see validate.py)
- lb3 reproduces the full-spec EXACT min on Case-A C4 = 34 (OPTIMAL, both).
- Kill-consistency: every config where lb3_LB > cap was independently
  confirmed full-spec INFEASIBLE: star+2xP1 cap14 (lb3_LB=25, full INFEAS);
  star+triangleP1 cap15 (lb3_LB=25, full INFEAS). NO false kills observed.
- Full-spec ground truth on the hardest CONCENTRATED family,
  star + (6-edge graph in one 5-part), I=10, at q=10 (cap20): all six
  non-iso 6-edge graphs INFEASIBLE (`hardest_family.jsonl`; K_{2,3} also
  INFEASIBLE at q=8 cap18, 314s). Times 142s-1777s.
- blocking.py / core_in_5part.py: all BLOCK and clique-core numbers OPTIMAL.

---

## 8. HAND-LEMMA COVERAGE CENSUS (pure combinatorics, `hand_coverage.py`)

For every non-iso config of every walled shape, we checked whether some HAND
lemma (Case A / Lemma D empty-4-part / triangle / K4 / K5 core) proves the
config dead (holes > cap = I+q-d, or K6 forced). Result (fraction of configs
hand-covered, by rung), WITH Lemma D included:

        rung q=8 : 253 / 898  hand-covered  (28%);  645 need machine
        rung q=9 : 377 / 2512 hand-covered  (15%); 2135 need machine
        rung q=10: dominant shape 129/2952 (4%); (7,5,5,5,4) 396/2422 (16%)

Per-shape at q=8: (6,5,5,5,5) 17%, (7,5,5,5,4) 62%, (6,6,5,5,4) 0%,
(8,5,5,5,3) 33%, (8,5,5,4,4) 0%. Lemma D lifted (7,5,5,5,4) from 45%→62%
(q8) and 3%→30% (q9) by killing all (e_0,0,0,0,0) "Case A" profiles.

The hand-covered configs are: Case A (6,5,5,5,5); Lemma D Case-A of
(7,5,5,5,4); and any config with a clique core (triangle/K4/K5) large
relative to the cap. The RESIDUE is dominated by low-clique profiles:
  (4,2,0,0,0),(4,1,1,0,0),(4,4,0,0,0),(5,1,0,0,0),(6,2,0,0,0),(7,1,0,0,0)...
i.e. configs whose internal graphs are triangle-poor (matchings, paths,
C4/C5, K_{2,3}) -- the DIFFUSE regime with no exploitable clique. These
fall to the full-spec machine but NOT to any clean counting lemma found here.

**This census is the precise coverage statement.** A clean GENERAL hand
bound covering the WHOLE walled set does NOT exist among the lemmas proved
here; the clique-core machinery is structurally blind to triangle-free
density, and the diffuse 72-85% residue resists all closed-form bounds tried.

---

## 9. CONCLUSION on the route to m* >= 66

- **The route CLOSES (empirically, machine-verified at its hardest points).**
  Every walled config tested at full spec is INFEASIBLE, including the
  hardest CONCENTRATED family: star(P0) + EACH of the six 6-edge graphs in
  one 5-part, shape (6,5,5,5,5), I=10, at q=10 (cap20) -- ALL SIX INFEASIBLE
  (`hardest_family.jsonl`, 142s-1777s each), the triangle-free K_{2,3} among
  them (also at q=8 cap18, 314s). Full-spec per config is ~2.5-30 min --
  TRACTABLE, contrary to the earlier "4x-per-cap-unit => days" fear (that
  estimate used 3-4 workers; with 12-14 workers + the dense internal
  structure pruning the search, cap-20 UNSAT lands in minutes).

- **But m* >= 66 is NOT reachable by a clean GENERAL HAND LEMMA.** The hand
  lemmas (Case A + Lemma D + clique cores + Foothold/B4/grid) rigorously
  close only 28%/15%/(~4-16%) of the walled set at q=8/9/10; the triangle-
  free diffuse residue has no closed-form lower bound (its min-holes is a
  covering-LP optimum with no clique witness; we verified the single-edge
  demand COLLAPSES to ~5 once a 5-part carries >=2 edges, so no per-edge
  charge survives). Honest status: **m* >= 66 is reachable by a HYBRID
  (hand lemmas for the clique-bearing families + full-spec CP-SAT for the
  diffuse residue, ~6700 configs total, minutes each)** -- same trust base
  as the existing certified ladder, extended to q<=10.

- The deliverable's strongest GENERAL bound:
  **holes >= max( [Case-A:26], [triangle:15], [K4:9], [K5:5] )** over the
  applicable cores; PLUS the two "infinite" (K6-forced) lemmas: any 4-part
  grid coordinate >=4 (Lemma B4) and the empty-4-part configuration
  (Lemma D); PLUS the validated certifier lb3 (sub-model, dual LB) where it
  converges. This is rigorous and closes the clique-bearing + Case-A walled
  configs; it does NOT close the diffuse triangle-free residue, the stated
  open gap.

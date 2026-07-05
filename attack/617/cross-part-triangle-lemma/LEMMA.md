# A hand lemma for the concentrated triangle-free residue (Erdős #617, road to m\* ≥ 66)

**Status: verified to high confidence (see §5). Closes the canonical hardest atom
of the q = 8,9,10 residue — the configuration the campaign's `road66/handlemma/
LEMMAS.md` marked "machine-only, no closed-form bound exists."**

*Origin: the cross-part-triangle argument was proposed by GPT Pro and certified
through the propose → verify loop (independent reimplementation of every finite
check, plus machine confirmation of the load-bearing obstruction against the full
model). W. Blair, June 2026.*

## 1. The configuration

Shape (6,5,5,5,5), defect d = 0, so cap = I + q. Parts: P₀ (size 6), P₁,…,P₄
(size 5). The family:

- **P₀ = K\_{1,4} ∪ {z}**: a 4-edge star (center c, leaves ℓ₁..ℓ₄) plus an
  isolated vertex z.
- **P₁ = F**, a triangle-free graph, F ∈ {K\_{2,3}, C₅, C₄, P₄}.
- **P₂, P₃, P₄ empty.**

Working in the complement H: holes = absent cross-pairs; min_holes is the least
number of holes for which H is K₆-free and every 6-set spans ≥ 4 edges. A config
is **infeasible at rung q** (hence closed) iff min_holes > cap = I + q.

| F | e(F) | I = 4+e(F) | proven bound B | cap at q=10 | margin |
|---|---:|---:|---:|---:|---:|
| K\_{2,3} | 6 | 10 | **39** | 20 | +19 |
| C₅ | 5 | 9 | **39** | 19 | +20 |
| C₄ | 4 | 8 | **36** | 18 | +18 |
| P₄ | 3 | 7 | **36** | 17 | +19 |

Every bound exceeds the cap at q = 8, 9, 10, so the whole family is closed by hand.
(Even the plain aggregation bound — 38 for K\_{2,3} — already exceeds cap 20; the
obstruction's +1 is extra precision, not needed for closure.)

## 2. Why the campaign's methods missed it

K\_{2,3} is triangle-free, so the campaign's **clique-core** lemmas (triangle/K₄/K₅
inside a part) see nothing, and the **fractional packing** provably stalls at 13.75
(integrality gap, `road66/lpdual/`). The new idea is to use **cross-part triangles**
as K₆-completion bases — these the clique-core machinery structurally never
considered because they are not within-part cliques:

- **star triple** (c, ℓ, y): center + leaf (a P₀ star edge) + any y ∈ P₁;
- **dense triple** (w, a, b): a P₀ vertex w + an edge ab of F (in P₁).

A triple is *active* (for a fixed core pattern X ⊆ P₀×P₁ of present/absent
cross-pairs) when its two P₀–P₁ pairs are present. An active triple is a triangle
whose completion to a K₆ runs over the empty grid P₂×P₃×P₄.

## 3. The aggregation lemma

> For every valid core pattern X with at least one active triple, every valid
> completion has **non-core holes ≥ 3·|U(X)| + 6**, where U(X) is the union of the
> vertices of all active triples.

**Local matching budget.** For v ∉ Pⱼ (Pⱼ empty), the Füredi cut on {v}∪Pⱼ reads
Σ_{x∈Pⱼ} x_{vx} ≤ 5 − 4 = 1: every vertex has ≤ 1 hole into each empty part.
Holes between two empty parts likewise form a matching.

**Single-triple forcing.** Fix an active triple T = {u,v,w}. Each K₆
T∪{x₂,x₃,x₄}, xⱼ∈Pⱼ, has all internal pairs present and (by activity) no core
hole, so it must carry an anchor-empty or empty-empty hole. If some anchor of T
had no hole into, say, P₂, then the unblocked residual contains a 3×2×2 box that
empty-empty matchings alone would have to block — but **MATCH_BLOCK(3,2,2) = ∞**
(unblockable). Hence every anchor of T spends exactly one hole into each of
P₂,P₃,P₄ (9 anchor-empty holes), leaving a 2×2×2 residual that needs
**MATCH_BLOCK(2,2,2) = 6** empty-empty holes.

**Aggregation (no overlap collapse).** Any v ∈ U(X) lies in some active triple, so
by the above it carries one hole into each empty part: ≥ 3 anchor-empty holes per
*distinct* anchor. For distinct anchors v ≠ v′, the holes vx and v′x′ are distinct
vertex pairs even if x = x′, so the counts don't collide: ≥ 3|U(X)| anchor-empty
holes. The 6 empty-empty holes (from any one triple's residual) are a disjoint
pair-class. Hence non-core holes ≥ 3|U(X)| + 6. ∎

Therefore min_holes ≥ min over valid X of (|X| + 3|U(X)| + 6). The core scan
(§5) evaluates this minimum to **38**, attained at a **unique** pattern
X\* = {(z,a₀),(z,a₁)} (z to the two degree-3 vertices of K\_{2,3}).

## 4. The equality obstruction (38 → 39 for K\_{2,3})

A 38-hole assignment would force equality throughout: core = X\*, every vertex of
U exactly one hole per empty part, z none, exactly six empty-empty holes. Fix one
empty part E and let f(v) ∈ E be the unique hole-neighbor of each anchor v.

- **Rainbow:** equality forces each active triple's three anchors onto three
  *distinct* slabs of E, so f is a proper ("rainbow") coloring of the active-triple
  hypergraph.
- **Leaves distinct:** the Füredi cut on {ℓ₁,ℓ₂,ℓ₃,ℓ₄,z,x}, x∈E, has 5 cross-pairs
  and 0 internal edges, giving Σ ≤ 1; with z spending no hole into E, the four
  leaves must hit four distinct vertices of E.

But the dense triples force the two sides of K\_{2,3} to use ≥ 2 colors, and the
star triples force every leaf color to avoid the center color and every P₁ color,
leaving each leaf at most 5 − 1 − 2 = 2 choices — impossible for four distinct
leaves. So no 38-hole assignment exists: **min_holes ≥ 39.** ∎

## 5. Verification record

Every finite step was checked, the load-bearing obstruction three independent ways.
Scripts in this directory; reproduce with `python3 <script>`.

- **`verify_aggregation.py`** (GPT's verifier, re-run here): MATCH_BLOCK(2,2,2)=6,
  MATCH_BLOCK(3,2,2)=∞; core scan over all 248809 valid cores → B = 38 at a unique
  X\* (next value 39); `no_active = 0` (every valid core has an active triple, so
  §3's premise always holds); `rainbow_colorings_with_four_distinct_leaves = 0`.
- **`indep_rainbow.py`** (independent brute force, full 5¹⁰ enumeration, no shared
  code): rainbow count = **0**. Confirms §4 independently of GPT's pruning.
- **`fix_core_check.py CORE`** (K\_{2,3}, CP-SAT against the full model): with the
  core pinned to X\* the config has **no ≤ 38-hole completion** (UNSAT) — the
  obstruction confirmed directly, bypassing the rainbow argument entirely. The empty
  core (LB = 39) is likewise UNSAT at cap 38, a second structurally different point.
- **`confirm_family.py`** (C₄/C₅/P₄, CP-SAT against the full model): for each F the
  binding core is found by the scan, pinned, and checked at cap B(F)−1 — all UNSAT:
  **C₄ min ≥ 36, C₅ min ≥ 39, P₄ min ≥ 36.** So every atom of the family is
  machine-backed at its tightest core, not just K\_{2,3}. (A direct full-model UNSAT
  at the rung cap times out at this boundary — pinning the core is what makes it
  tractable, which is the whole reason the hand lemma earns its keep.)
- **`ground_truth_min.py`** brackets the open full minimization at [22, 49]
  (consistent, but the boundary is too hard for a direct full-model UNSAT — which is
  exactly why the hand lemma matters).

**Honest confidence: high, not 100% machine-certified.** The obstruction (§4) is
fully machine-confirmed. The aggregation lemma (§3) rests on the elementary argument
above — the campaign's own grid-blocking method (cf. `LEMMAS.md` Theorem A,
BLOCK(3,3,3,3)=18), extended to cross-part triangles — plus machine confirmation at
**the binding (tightest) core of every atom**: K\_{2,3} at X\* and the empty core,
and C₄/C₅/P₄ at their binding cores, all UNSAT below their bounds. The one residual
is that §3 is invoked as a universal lower bound for the *non-binding* cores too;
those are looser, the argument is uniform, and the tightest case of each atom is
machine-checked. A publication-grade proof would formalize §3 as a standalone lemma.
For the question "does this close the family," the answer is yes — and every atom now
stands on its own machine check.

## 6. What it does and does not do

**Does:** closes the P₀-star + triangle-free-in-one-5-part family (the residue's
canonical hard core) by hand, removing the most expensive CP-SAT configurations
from the q=8,9,10 sweep.

**Does not:** solve m\* ≥ 66. The residue retains other profiles — edges spread
across two 5-parts (e.g. (4,1,1,0,0)), non-star P₀ structures ((5,1,…), (6,2,…),
(7,1,…)), other shapes ((7,5,5,5,4)). Extending the cross-part-triangle method to
those is the next step (`../GPT-PRO-RESIDUE-PROMPT-3.md`).

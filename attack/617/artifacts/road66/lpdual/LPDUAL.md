# Explicit fractional packing for the triangle-free residue (Erdős #617, road→66)

**Mandate.** The triangle-free / diffuse residue of the walled set (matchings,
paths, C4, C5, K_{2,3} spread across the four 5-parts of (6,5,5,5,5) /
(6,6,5,5,4) / (7,5,5,5,4) at q = 8,9,10) is the last lock. The plan: build an
EXPLICIT fractional packing of K6-obligations whose value exceeds the cap, as a
hand certificate replacing the per-config CP-SAT machine.

**Headline result (honest, and it overturns the briefing's premise).**
The natural fractional-packing LP — the LP whose dual the CP-SAT MINIMIZE was
believed to expose — does **NOT** reach the cap on the hard concentrated
configs. Its optimum is governed by a large (≈ factor 2) **integrality gap**;
the value `27` the briefing attributed to "an LP/fractional dual" is a CP-SAT
*branch-and-bound* bound (post-cuts/clauses), **not** the LP relaxation, which
is only `13.75`. So an explicit fractional packing **cannot** close the
concentrated triangle-free residue — provably, not for lack of cleverness.

**But the construction is not empty.** The explicit packing **does** close the
*diffuse-matching* end of the residue (edges spread one-per-part across ≥3 of
the empty 5-parts), at the rungs where its fixed value beats the shrinking cap.
This is exactly the family the hand-lemma census (LEMMAS.md §8) left open
(clique cores need a triangle; matchings have none). So the packing and the
clique lemmas are **complementary**, and together they shrink the machine
residue. The precise coverage is tabulated below.

All numbers reproduced by the scripts in this directory (`verify_packing.py`,
`full_lp.py`, `covering_lp.py`, `symmetrize.py`), each an independent, elementary
check (capacity load ≤ 1 per cross-pair; value vs cap) — no trust in CP-SAT.

---

## 1. The packing LP and its weak-duality certificate

Fix shape (6,5,5,5,5), parts P0 (size 6), P1..P4 (size 5), defect d=0.
`holes` = missing cross-pairs; `cap = I + q − d`. A **potential K6** is a 6-set
K whose every same-part pair is an internal edge (so K is a clique once all its
cross-pairs are present); to be K6-free, K must contain a hole.

Let x_p ∈ {0,1} mark cross-pair p as a hole. Every K6-free hole-set satisfies
the **covering** system

>   (COVER_K)   Σ_{p ∈ cross(K)} x_p ≥ 1     for every potential K6 K.

Hence `min_holes ≥ LP-min { Σ_p x_p : (COVER), x ≥ 0 }`, and by LP duality this
equals the **max fractional packing**

>   max Σ_K y_K   s.t.   (CAP_p)  Σ_{K ∋ p} y_K ≤ 1  for every cross-pair p;  y ≥ 0.

**Certificate (weak duality, elementary).** *Any* y ≥ 0 satisfying every (CAP_p)
gives `min_holes ≥ Σ_K y_K`. If additionally `Σ_K y_K > cap`, the config is
**INFEASIBLE** at that rung. The check is purely arithmetic: load every
cross-pair by the K6s through it, confirm each load ≤ 1, sum the weights.
`verify_packing.py` does exactly this (column `max cross-pair load` ≤ 1.000000
on every atom below; no Füredi cut, no CP-SAT).

This bound is **rung-uniform in the right way**: the packing y is fixed; only
`cap = I + q − d` moves. A config is closed by the packing at rung q **iff**
`V := Σ_K y_K > I + q − d`, i.e. **iff `q < V − I + d`**.

---

## 2. The explicit packing on the diffuse atom (star + 4 spread matching edges)

Canonical *diffuse* hardest atom `star_m_m_m_m`: star K_{1,4} in P0
(center c, leaves ℓ1..ℓ4, isolated z) **plus one matching edge in each** of
P1,P2,P3,P4. I = 4 + 4 = 8. (This is the (4,1,1,1,1) edge-profile — the maximal
spread of a 4-edge internal graph; "4 disjoint edges in one part" is impossible
on 5 vertices, so this is the genuine diffuse extreme.)

The optimal packing has value **V = 18.8667 = 283/15**, with max cross-pair load
exactly 1. Symmetrizing over the config automorphisms (permute P1..P4; permute
star leaves; swap each matching edge's endpoints) collapses the 125-vertex LP
optimum to **7 orbit-classes** — a hand-presentable certificate. Put weight
`w_t` *uniformly* on every K6 of orbit-type t:

| orbit type (what the 6 vertices are) | #K6 | total wt | wt each |
|---|---:|---:|---:|
| 1 leaf of P0 + 3 single transversal vtxs + 1 **matching-edge pair** | 2000 | 8.327 | 0.00416 |
| isolated z of P0 + 3 single vtxs + 1 matching-edge pair | 500 | 3.673 | 0.00735 |
| **star-edge** {c, ℓ} in P0 + 1 vtx from each of the 4 matching parts | 2500 | 3.000 | 0.00120 |
| star-edge {c, ℓ} in P0 + **two** matching-edge pairs | 24 | 2.000 | 0.08333 |
| 1 leaf of P0 + 1 single vtx + two matching-edge pairs | 240 | 1.469 | 0.00612 |
| (P0 empty) + three matching-edge pairs | 4 | 0.267 | 0.06667 |
| isolated z + 1 single vtx + two matching-edge pairs | 60 | 0.131 | 0.00218 |
| **TOTAL** | | **18.867** | |

(4 further orbit-classes carry weight < 1e-4 and are dropped.) Every K6 is one of
two structural kinds — **star-edge-anchored** (the doubled part is P0, via a
star edge {c,ℓ}) or **matching-edge-anchored** (the doubled part is some Pi, via
its matching edge) — completed by a transversal across the remaining parts. The
capacity load is ≤ 1 on every cross-pair (machine-checked exactly).

Since **V = 18.867**, and for this atom I = 8, d = 0:

>   closes rung q  ⟺  q < V − I = 10.867  ⟺  **q ∈ {8, 9, 10} all close**
>   (caps 16, 17, 18; 18.867 > 18). ∎ (`verify_packing.py star_m_m_m_m 18`.)

So **star_m_m_m_m is killed FREE (no machine) at q = 8, 9, 10** by this packing.

---

## 3. Coverage of the residue — exact boundary

Per-config max fractional packing V (pure covering, `verify_packing.py`), and
which rungs `q ∈ {8,9,10}` it closes (closes iff V > I+q on (6,5,5,5,5), d=0):

| atom (internal graph) | profile | I | **V** | q8 (cap) | q9 (cap) | q10 (cap) |
|---|---|---:|---:|---|---|---|
| star + m in each of P1..P4 | (4,1,1,1,1) | 8 | **18.87** | ✅ 16 | ✅ 17 | ✅ 18 |
| star + m in P1,P2,P3        | (4,1,1,1,0) | 7 | **15.67** | ✅ 15 | ✗ 16 | ✗ 17 |
| star + 2-match in P1,P2     | (4,2,2,0,0) | 8 | **17.00** | ✅ 16 | ✗ 17 | ✗ 18 |
| star + m in P1,P2           | (4,1,1,0,0) | 6 | **12.40** | ✗ 14 | ✗ 15 | ✗ 16 |
| star + C5 in P1             | (4,5,0,0,0) | 9 | **15.00** | ✗ 17 | ✗ 18 | ✗ 19 |
| star + C4 in P1             | (4,4,0,0,0) | 8 | **13.00** | ✗ 16 | ✗ 17 | ✗ 18 |
| star + P4-path in P1        | (4,4,0,0,0) | 8 | **13.00** | ✗ 16 | ✗ 17 | ✗ 18 |
| star + K_{2,3} in P1        | (4,6,0,0,0) | 10 | **13.00** | ✗ 18 | ✗ 19 | ✗ 20 |

**What the packing CLOSES (free, hand-auditable):** the *spread* end —
- any config whose 4 P0-star edges sit on a part-disjoint matching across **≥3**
  of the empty 5-parts closes at **q = 8** (the 3-part spread already gives
  V ≈ 15.7 > cap 15); the **4-part** spread closes at **q = 8, 9, 10**.
- the 2-deep-in-2-parts spread (2m+2m) closes at **q = 8** only.

**What the packing CANNOT close (provably — §4):** the *concentrated* end —
every config with its triangle-free edges piled into ONE 5-part (C4, C5, P4,
K_{2,3}, …). There V tops out at 13–15, far under the caps 16–20, at **every**
rung. These are precisely the configs the briefing hoped to kill (the K_{2,3}
atom: V = 13 vs cap 20). The packing misses by 5–7.

The boundary is monotone and clean: **packing-value rises with edge spread and
falls with concentration**; the residue splits at "edges touch ≥3 empty parts."

---

## 4. Why the packing CANNOT reach the cap on the concentrated configs
(the integrality gap — this is the load-bearing negative result)

Two independent, elementary proofs that no fractional packing of K6-obligations
beats the cap for the concentrated triangle-free configs:

**(a) The global LP relaxation is far below the integer min.**
`full_lp.py` solves the *exact* LP relaxation of the full general_rung spec
(covering ≥1 constraints AND the Füredi "every 6-set ≥4 edges" ≤-cuts), via
HiGHS. For `star_K23` it returns **13.75** (`min_holes ≥ 14`). The *integer*
min, by contrast, is **≥ 21** (CP-SAT BestObjectiveBound, `dualLB_K23_cap40.log`;
the full spec is INFEASIBLE at cap 20, `handlemma/crux_K23_q8.log`). Thus the
LP→IP gap is `21 / 13.75 ≈ 1.5`, and **any** fractional dual (which is bounded
by the LP optimum 13.75) is stuck at 14 ≪ cap 20. The briefing's "27" is the
*branch-and-bound* integer bound, **not** the LP/packing dual.

The mechanism is visible in the LP: the Füredi cut for the 6-set {one outside
vertex w} ∪ P1 reads `e(P1) + deg_{P1}(w) ≥ 4`; with K_{2,3} already at
`e(P1) = 6` this is **vacuous**, so a dense 5-part **absorbs its own
constraints** and offers the packing nothing. (Exactly LEMMAS.md's "the
single-edge demand collapses to ~5.")

**(b) The clean hand bound itself is integer-only.**
Theorem A's bound 26 = 8 (endpoint holes) + 18 (grid holes) rests on
`BLOCK(3,3,3,3) = 18` — an *integer* blocking number. Its LP relaxation is **9**,
and there is an explicit half-fractional blocker of cost **13.5** (put x = 1/4 on
every grid hole: each transversal is covered 6·¼ = 1.5 ≥ 1; each vertex-into-part
load is 3·¼ = 0.75 ≤ 1). So the *fractional* dual of the grid certifies at most
13.5, vs the integer 18 — a factor-2 gap baked into the geometry. A fractional
packing route to Theorem A could reach at most 8 + 13.5 = 21.5, and on K_{2,3}
(no clean grid, dense part) only 14.

**Conclusion of §4.** The concentrated triangle-free residue is INFEASIBLE, but
its witness is the **integer** min-holes (CP-SAT, or an integer combinatorial
lemma), which fractional LP duality cannot reproduce. This is a theorem about
the LP, not a failure of construction.

---

## 5. Honest coverage statement (the deliverable's bottom line)

- **Does the explicit fractional packing close the triangle-free residue, giving
  m\* ≥ 66 FREE?**  **No** — not the whole residue. It is mathematically
  impossible for the *concentrated* sub-family (integrality gap, §4).

- **Which families does it close (free, hand-checkable certificate)?** The
  *diffuse-matching* sub-family — internal edges forming a part-disjoint matching
  spread across ≥3 of the empty 5-parts:
  - **4-part spread** (profile (4,1,1,1,1)): closed at **q = 8, 9, 10** (V=18.87).
  - **3-part spread** (4,1,1,1,0): closed at **q = 8** (V=15.67).
  - **2×2 spread** (4,2,2,0,0): closed at **q = 8** (V=17.0).
  These are exactly the configs invisible to the clique-core lemmas, so the
  packing is genuine *new* coverage, complementary to LEMMAS.md §8.

- **Residual (still machine-only):**
  - all **concentrated** triangle-free configs (C4 / C5 / P4 / K_{2,3} in one
    5-part) at every rung — V tops out at 13–15 < caps 16–20;
  - the **2-part / 1-deep spreads** (4,1,1,0,0), and the 3-part spread at q≥9 and
    2×2 spread at q≥9 — V exceeds the q=8 cap but not the q=9,10 caps.
  These fall to the full-spec CP-SAT (tractable, minutes/config; the hardest,
  K_{2,3} at q=10 cap20, is INFEASIBLE in 478s — `handlemma/crux_K23_q10.log`).

- **Net effect on m\* ≥ 66.** The route still **CLOSES as a HYBRID** (hand lemmas
  + this packing + CP-SAT for the concentrated residue). The packing removes the
  diffuse-spread configs from the machine list (the cheapest part was already the
  machine's easiest, but the *spread* cases are now lemma-closed with an
  elementary certificate). It does **not** upgrade the route to a pure clean hand
  proof: the concentrated triangle-free residue is the irreducible machine core,
  and §4 proves no fractional packing can change that.

---

## 6. Files (all in this directory)

- `verify_packing.py NAME CAP` — solves the max fractional packing (covering
  dual), checks capacity load ≤ 1 exactly, reports value vs cap. **The
  certificate verifier.**
- `full_lp.py NAME` — exact LP relaxation of the full spec (covering + Füredi
  cuts) via HiGHS; prints fractional min and dual support. Shows LP ≪ IP.
- `covering_lp.py NAME [--budgets]` — pure covering LP (primal); confirms 13 for
  K_{2,3} and that Foothold budgets (upper bounds) do not lift a minimization.
- `symmetrize.py NAME` — collapses the optimal packing into automorphism orbit
  classes (the §2 table).
- `dualLB.py NAME CAP TL WK` — CP-SAT MINIMIZE at a LARGE cap, reads
  BestObjectiveBound (the *integer* bound; gave 21 for K_{2,3}, vs LP 13.75).
- Logs: `dualLB_K23_cap40.log` (integer bound 21), `dualLB_K23_cap20.log`
  (shows why minimizing at the binding cap gives a meaningless 0).

### Reproduce the headline lines
```
python3 verify_packing.py star_m_m_m_m 18   # value 18.867 > 18  -> CLOSES q8-10
python3 verify_packing.py star_K23     20   # value 13.000 < 20  -> short by 7
python3 full_lp.py        star_K23          # LP relax 13.75 (≫ below integer 21)
```

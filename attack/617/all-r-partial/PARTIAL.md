# Erdős #617 — an all-*r* blocking theorem and the s≤2 obstruction

*W. Blair, 2026-06-16. A partial result toward the general (all-*r*) conjecture.
The **r = 5** case is settled separately (see `../RESULT.md` and the q=10 sweep);
this note is about what generalizes to all *r* and what does not.*

**Trust labels used below:** **[VERIFIED]** machine-checked *and* hand-checked
here; **[ESTABLISHED]** standard/elementary, checked; **[ASSUMED]** load-bearing
input not proved here; **[CONDITIONAL]** follows from a step that is itself
ASSUMED or only PLAUSIBLE; **[OPEN]** not proved by anyone (the barrier).

---

## 0. The conjecture (erdosproblems.com #617, status *falsifiable*)

> For every *r* ≥ 3: if the edges of K_{r²+1} are *r*-coloured, then some *r*+1
> vertices induce a K_{r+1} missing at least one colour.

Equivalently, **no balanced colouring exists**: there is no *r*-colouring of
K_{r²+1} in which every (*r*+1)-set sees all *r* colours. Known: true for
*r*=3,4 (Erdős–Gyárfás), false for *r*=2, and K_{r²} *does* admit balanced
colourings for infinitely many *r* (affine planes), so the threshold r²+1 is
sharp. Open for all *r* ≥ 5.

## 1. Reduction to a single-colour extremal bound  **[ESTABLISHED]**

Balanced ⟺ every colour class G_c has α(G_c) ≤ r. Pass to H_c = complement of
G_c on the same r²+1 vertices. Then:

- H_c is **K_{r+1}-free** (a K_{r+1} in H_c is an independent (r+1)-set in G_c);
- **every (r+1)-set spans ≥ r−1 edges of H_c** (the other r−1 colours each
  appear at least once on its C(r+1,2) pairs).

The average colour-class size is A_r = (1/r)·C(r²+1,2) = r(r²+1)/2. So #617
reduces to the

> **Universal single-colour theorem (target).** For every r ≥ 3, any H on r²+1
> vertices that is K_{r+1}-free with every (r+1)-set spanning ≥ r−1 edges has
> e(H) ≤ (r−1)·r(r²+1)/2 − 1, i.e. e(G) ≥ A_r + 1.

Summing A_r+1 over r colours exceeds C(r²+1,2): contradiction. For r=5 this is
exactly the certified `e(G) ≥ 66 = A_5 + 1`.

### 1.1 The local cap is load-bearing  **[VERIFIED]**

One must use the *upper* local cap `e_G(S) ≤ M_r` with `M_r = C(r+1,2)−(r−1)`,
not merely `α(G), ω(G) ≤ r`. The weaker statement "α,ω ≤ r ⟹ e(G) > A_r" is
already **false at r=3**: the 10-vertex graph
`{01,03,09,12,14,24,25,35,39,45,59,67,68,78}` has α=ω=3 yet only **14 < A_3=15**
edges — it fails *only* the local cap (the 4-set {0,3,5,9} carries 5 > M_3=4
edges). And `SC(3)` (every 4-set in [1, M_3]) has minimum **18 ≥ A_3+1=16**, so
the single-colour theorem holds for r=3 with room. Both checked in
`local_cap_loadbearing.py`. Consequence: any proof of #617 must invoke the upper
cap, not just independence/clique numbers.

## 2. Turán-rung window  **[ESTABLISHED]**

Turán number for K_{r+1}-free graphs on r²+1 vertices:
`T_r = r(r−1)(r²+2)/2` (one Turán part of size r+1, the other r−1 of size r —
verified by direct count). The target is `e(H) ≤ T_r − (r(r−1)/2 + 1)`, so the
dangerous rungs are `e(H) = T_r − q` for `0 ≤ q ≤ r(r−1)/2`. For r=5 this is
q ≤ 10, matching the campaign's binding rung. A Füredi-style stability partition
then gives an r-partition with internal edges I, defect
`d = Σ C(n_i,2) − [C(r+1,2) + (r−1)C(r,2)]`, and cross-holes `h = I + q − d`;
a configuration is killed when `min h > I + q − d`.

> **[ASSUMED]** An *exact* Füredi-style partition theorem for general r (the
> stability step that produces the r-partition with I ≤ q). Used implicitly for
> r=5; not proved here for general r. This is a genuine load-bearing gap.

## 3. The all-*r* DP / matching blocking theorem  **[VERIFIED]**

Take s ≥ 2 parts E_1,…,E_s. Blocker edges between each pair form a matching
(each vertex ≤ 1 blocker into each other part). `MBLOCK(sizes)` = minimum
blocker edges hitting every transversal (leaving no independent transversal).

> **Theorem.**  `MBLOCK(s−1,…,s−1) = (s−1)·C(s,2)`  and
> `MBLOCK(s, s−1,…,s−1) = ∞`.

**Status: VERIFIED.** Machine-checked by exact CP-SAT minimisation
(`mblock_verify.py`), and hand-proved (below). It recovers the three constants
certified for r=5 — `MBLOCK(2,2,2)=6`, `MBLOCK(3,2,2)=∞`, `BLOCK(3,3,3,3)=18`
— and predicts new values that the machine confirms:

| sizes | machine `min` | `(s−1)C(s,2)` / ∞ |
|---|---|---|
| (2,2,2) | 6 | 6 |
| (3,2,2) | ∞ (infeasible) | ∞ |
| (3,3,3,3) | 18 | 18 |
| (4,3,3,3) | ∞ | ∞ |
| (4,4,4,4,4) | 40 | 40 |
| (5,4,4,4,4) | ∞ | ∞ |

**Proof.** Independent-transversal lemma: if parts V_1,…,V_p have a matching
between each pair and, sorted, |V_i| ≥ i for all i, then an independent
transversal exists (induct: take a vertex in the smallest part, it deletes ≤ 1
per other part, the sorted residual still satisfies |V'_i| ≥ i).
- *(∞ case)* sizes (s, s−1,…,s−1) sorted are (s−1,…,s−1,s), which satisfy
  |V_i| ≥ i, so an unblocked transversal always exists ⇒ no finite blocker.
- *(lower bound)* if all s parts have size s−1 and some vertex had blocker-degree
  ≤ s−2, deleting it leaves s−1 parts with sorted sizes ≥ (s−2,…,s−2,s−1)
  satisfying |V_i| ≥ i ⇒ unblocked transversal, contradiction. So every vertex
  has degree exactly s−1, giving ≥ s(s−1)(s−1)/2 = (s−1)C(s,2) edges.
- *(upper bound)* label each part 1..s−1, join equal labels across every pair;
  any transversal repeats a label (pigeonhole: s parts, s−1 labels) ⇒ blocked;
  edge count is (s−1)·C(s,2).  ∎

## 4. Aggregation lemma  **[PLAUSIBLE — not independently certified]**

For a core configuration with **s empty parts** and at least one *active tuple*
(an internal edge in one loaded part + one vertex per other loaded part, all
core cross-pairs present), with anchor set U(X):

> non-core holes ≥ **s·|U(X)| + (s−1)·C(s,2)**.

Reasoning: by the local (r+1)-cut each anchor has ≤ 1 hole into each empty part;
if an anchor *misses* an empty part the K_{r+1}-completion residual is
(s, s−1,…,s−1) = ∞-unblockable, so each anchor must spend one hole into every
empty part (s·|U| holes); the empty–empty residual (s−1,…,s−1) then needs
ρ_s = (s−1)C(s,2) more.

**Status:** both pillars (the ∞ case and the ρ_s value) are the VERIFIED
constants of §3. The *assembly* (forced anchor-holes + no-overlap residual) is
the exact analogue of the **machine-certified** r=5 cross-part-triangle lemma
(`../cross-part-triangle-lemma/`), but it is **not independently certified for
general r here**. This is precisely the step where the earlier "PROMPT-4"
extension to size-4/3 empty parts was *refuted* — so it must be re-certified,
not trusted. See §7, item 1.

## 5. What the aggregation closes: s ≥ 3  **[CONDITIONAL on §2 + §4]**

For s ≥ 3 the bound is strong. A single active tuple already forces
`s·(r+1−s) + (s−1)C(s,2)` holes; for one loaded part (s = r−1) this is
`2(r−1) + (r−2)·C(r−1,2) = Θ(r³)`, while the cap window is only `q ≤ r(r−1)/2 =
Θ(r²)`. So **every configuration with ≥ 3 empty Turán parts is annihilated far
above the cap** — the clean all-r analogue of why the r=5 star-plus-dense-5-part
residue collapsed. (Conditional because it inherits the §2 ASSUMED Füredi step
and the §4 PLAUSIBLE aggregation.)

## 6. The genuine barrier: s ≤ 2  **[OPEN]**

The blocker does **not** close one- or two-empty-part configurations:

- **s = 2:** ρ_2 = 1, so the bound is only `2|U| + 1`. One active tuple gives
  ~2r holes against a cap ~r(r−1)/2. Needs many active tuples with large union,
  or a separate core-hole / rainbow obstruction.
- **s = 1:** ρ_1 = 0, bound is only `|U|` — too weak against a quadratic cap.
  These high-loaded configurations are the **true all-r bottleneck**.
- **s = 0:** no empty parts; the cross-part machinery does not apply at all. A
  different (purely core) integer lemma is required.

This is the same concentrated-configuration wall that, **at r=5, was only closed
by the brute-force q=10 CP-SAT sweep** — for which there is no general-r analogue
(infinitely many r). No proof exists for s ≤ 2. **This is where #617 lives.**

## 7. Concrete next steps

1. **Re-certify §4 for r = 6** by the same fix-core protocol that certified
   r=5: build the full-spec K_{37} model on an s=3 core configuration, pin the
   core, and check `min holes ≥ s|U|+(s−1)C(s,2)` (expect the aggregation to be
   tight/valid). This upgrades §4–§5 from PLAUSIBLE/CONDITIONAL to VERIFIED for
   r=6 and is the decisive guard against a PROMPT-4-style error. (Cost: one
   moderate CP-SAT model, not a full sweep.)
2. **Discharge §2** — state and cite/prove the exact Füredi partition theorem
   for general r, or identify the precise stability constant needed.
3. **Attack s ≤ 2.** Candidate routes (each currently with a gap):
   - *minority-colour + Brooks* (**cleanest route — avoids the partition
     census**): the minority colour graph G has e(G) ≤ A_r; if Δ(G) ≤ r, Brooks
     gives an (r+1)-independent set or a K_{r+1} (colour missing), so a
     counterexample has Δ(G) ≥ r+1 and (since avg degree ≤ r) some x with
     d(x) ≤ r−1. Deleting x and N(x) leaves R with |R| ≥ r²−r+1. The single
     missing lemma is
     > **LD(r):** under `e(G) ≤ A_r`, `e_G(S) ≤ M_r`, `α(G) ≤ r`, the residual R
     > cannot have `α(G[R]) ≤ r−1`.

     This is exact and finite per r (pin a low-degree vertex; expect UNSAT), and
     for r=3,4 it is what the Erdős–Gyárfás hand proof effectively verifies. A
     *symbolic* proof of LD(r) for all r would finish #617 without the near-Turán
     machinery. Not proved.
   - *(r+1)-critical surplus*: G_c has χ ≥ r+1, so contains an (r+1)-critical
     K_{r+1}-free subgraph with average degree > r; need to combine the critical
     surplus with α ≤ r to force e(G) > A_r. Gap: the critical subgraph may be
     small.
   - *affine-plane rigidity*: classify balanced K_{r²} colourings as
     affine-plane-like and show none extends to K_{r²+1}. **The second half is
     now done [VERIFIED]:** the standard affine K_{q²} colouring provably does
     *not* extend to a balanced K_{q²+1} by one vertex (two singleton-colour
     lines of different directions would meet in a doubly-coloured point;
     brute-forced for q=3 in `affine_nonextension.py`). This kills the obvious
     *counterexample* route. The open half is the classification (are all
     balanced K_{q²} colourings affine?) — likely as hard as #617 itself.
   - *spectral / Motzkin–Straus*: Lagrangian bound per H_c summed over colours;
     the slack is only the Turán deficit — it does not see the integer blocking
     obstruction, so it reproduces stability pressure but not the final `+1`.

## 7b. The rooted surplus route (alternative framing)  **[partly VERIFIED]**

Root a counterexample at a maximum independent set I (|I|=r, since α(G)=r). With
O=V∖I, F=G[O], L=#root links, the target e(G)≥A_r+1 becomes the **surplus
inequality** `(e(F)−y0) + (L−m) ≥ C_r`, where y0 = C(r,2)+(r−1)C(r−1,2) is the
Turán minimum of e(F), m=r²−r+1, and C_r=C(r,2)+1 (arithmetic VERIFIED, r=3..6).

- **[VERIFIED]** *Exact Turán base is impossible:* `e(F)=y0` admits no valid
  root-linking (`turan_base.py`, INFEASIBLE for r=3,4; clean all-r hand proof via
  the perfect-matching-on-Q0 + small-part-transversal argument). So `e(F)≥y0+1`
  — **one unit** of the required C_r surplus, for every r.
- **[OPEN]** the full surplus `≥ C_r = Θ(r²)`: only 1 unit is proved. Reduces to
  the weighted blocker `|D|+τ ≥ C(r,2)+1` over the near-Turán range
  `1 ≤ surplus ≤ C(r,2)`. This is the same barrier as s≤2, in rooted clothing.

## 8. Bottom line

The **only fully VERIFIED new result** here is the all-r DP/matching blocking
theorem (§3): `MBLOCK(s−1,…,s−1) = (s−1)C(s,2)`, `MBLOCK(s,s−1,…,s−1) = ∞`,
machine-confirmed through s=5 and recovering all three r=5 constants. Built on
it (conditionally, modulo §2 and a re-certification of §4) is the closure of all
**s ≥ 3** configurations. The conjecture itself remains **open**: the obstruction
is now sharply isolated to **s ≤ 2 loaded-core configurations**, for which no
proof exists and the r=5 brute-force fallback does not generalize.

*Reproduce §3: `python3 mblock_verify.py`.*

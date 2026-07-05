# Hand analysis of Case I (independent of the SAT run)

Setup: V(B) = P ⊔ Q ⊔ R, |P|=4, |Q|=5, |R|=10.  Write a=e(P), b=e(Q),
r=e(R), x=e(P,R), y=e(Q,R), z=e(P,Q).  Spec facts used: e(B)=40, α(B)≤4,
Δ(B)≤6, every 6-set ≤ 11 edges, b ≤ 6, and the hitting conditions, which
are equivalent to:

* α(B−P) = α(Q∪R) ≤ 3   (P hits all independent 4-sets)
* α(B−Q) = α(P∪R) ≤ 3   (Q hits all independent 4-sets)
* α(R) ≤ 2              (P∪Q hits all independent 3-sets)

Turán complements give the basic bounds (min edges of an m-vertex graph
with α ≤ k is C(m,2) − T(m,k), equality iff the graph is a disjoint union
of k balanced cliques):

* r ≥ 20, equality iff R = 2K₅;
* e(Q∪R) = b+y+r ≥ 30, equality iff Q∪R = 3K₅;
* e(P∪R) = a+x+r ≥ 26, equality iff P∪R = K₅⊔K₅⊔K₄.

**Lemma 1: e(Q∪R) ≥ 31.**  If e(Q∪R)=30 then Q∪R = 3K₅ with parts C₁,C₂,C₃
and qᵢ=|Q∩Cᵢ| (Σqᵢ=5).  Then r = ΣC(5−qᵢ,2), and r ≥ 20 forces
(q₁,q₂,q₃)=(5,0,0) (all other splits give r ≤ 16); but then Q = C₁ = K₅ and
b = 10 > 6.  ∎

**Lemma 2: e(P∪R) ≥ 27.**  If e(P∪R)=26 then P∪R = K₅⊔K₅⊔K₄; r ≥ 20 forces
P = the K₄ part (all other splits give r ≤ 16), so a=6, x=0, R = 2K₅
(call the parts R₁,R₂), r=20.  The 6-set bound applied to R₁∪{w} for w ∈ Q
gives 10 + deg_{R₁}(w) ≤ 11, i.e. every Q-vertex has at most one edge into
each Rᵢ.  Total: 40 = 20+6+b+0+y+z, and e(B) accounting with
e(Q∪R) ≥ 31 (Lemma 1) gives b+y ≥ 11, while a+x+z ≤ 40−r−b−y ⇒ z ≤ 3.
Since b ≤ 6 < 10, Q has two non-adjacent vertices q₁,q₂.  As z ≤ 3, some
p* ∈ P is adjacent to neither; as each qᵢ has ≤ 1 edge into each Rⱼ, there
are rⱼ ∈ Rⱼ adjacent to neither.  Then {q₁,q₂,p*,r₁,r₂} is independent
(no P–R edges, R₁–R₂ empty), contradicting α(B) ≤ 4.  ∎

**Corollary (budget squeeze).**  Adding e(Q∪R) ≥ 31 and e(P∪R) ≥ 27 to
e(B)=40 yields  r ≥ 18 + z,  a+x+z ≤ 9,  b+y+z ≤ 13.

These were checked numerically and are consistent with everything the SAT
solver explores; they are not by themselves a refutation — the full spec
(saturation, non-4-partiteness, τ₄ ≥ 4) is decided by the SAT run.

## Saturation–hitting interaction (both cases)

K₅-saturation of the complement says: for every B-edge uv there is a 3-set
T, independent and with no edges to u or v.  Then T∪{u} and T∪{v} are
*independent 4-sets*, so P and Q must hit both.  For an edge uv with
u,v ∉ P∪Q (in Case I at least r ≥ 20 of the 40 edges lie inside R), T
itself must meet **both** P and Q.  So every R-edge uv admits p ∈ P,
q ∈ Q with: pq a non-edge, and p,q both non-adjacent to both u,v.
With e(P,R) ≤ 9 and e(Q,R) ≤ 13 (budget corollary) this is a strong
simultaneous non-adjacency demand against α(B) ≤ 4 density pressure —
this is exactly the regime the SAT solver decides.

Note z ≤ r − 18 (from Lemmas 1–2 plus the budget), so e(P,Q) ≤ 12−...
in the typical r=20..22 range, e(P,Q) ≤ 2..4.

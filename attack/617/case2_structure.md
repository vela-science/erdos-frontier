# Hand analysis of Case II (independent of the SAT run)

Setup: |P| = |Q| = 4, k = |P∩Q|, e_B(P)+k ≤ 6, e_B(Q)+k ≤ 6, P and Q each
hit every independent 4-set of B, i.e. α(B−P) ≤ 3 and α(B−Q) ≤ 3 (both on
15 vertices).  Turán: e(B−P), e(B−Q) ≥ 30, equality iff the graph is 3K₅.

**Lemma 3: e(B−P) ≥ 31 (and symmetrically e(B−Q) ≥ 31).**

Suppose e(B−P) = 30, so B−P = C₁⊔C₂⊔C₃ with Cᵢ ≅ K₅.

1. *Every p ∈ P has at most one neighbour in each Cᵢ*: the 6-set Cᵢ∪{p}
   carries 10 + deg_{Cᵢ}(p) ≤ 11 edges (L4).
2. *P is a clique, hence e_B(P) = 6 and k = 0*: if p₁,p₂ ∈ P were
   non-adjacent, pick cᵢ ∈ Cᵢ∖(N(p₁)∪N(p₂)) — possible since each pⱼ has
   ≤ 1 neighbour in Cᵢ, leaving ≥ 3 choices.  Then {p₁,p₂,c₁,c₂,c₃} is an
   independent 5-set (cross-clique pairs are non-edges of B−P = 3K₅),
   contradicting α(B) ≤ 4.  Then e_B(P)+k ≤ 6 forces k = 0, so Q ⊆ B−P.
3. *Fix p ∈ P and let Fᵢ = Cᵢ∖N(p) (|Fᵢ| ≥ 4).*  Every transversal
   {f₁,f₂,f₃} with fᵢ ∈ Fᵢ makes {p,f₁,f₂,f₃} an independent 4-set, which
   Q must hit; since p ∉ Q, Q must hit every such transversal, which for a
   4-set Q is possible only if Fᵢ ⊆ Q for some i.  As |Fᵢ| ≥ 4 = |Q| this
   forces Q = Fᵢ, |N(p)∩Cᵢ| = 1, i.e. **Q = Cᵢ minus the single
   p-neighbour cᵢ\* ∈ Cᵢ**.
4. This holds for *every* p ∈ P with the *same* clique Cᵢ (Q determines i)
   and the same excluded vertex cᵢ\* = Cᵢ∖Q.  Hence all four vertices of P
   are adjacent to cᵢ\*, giving deg(cᵢ\*) ≥ 4 + 4 (inside Cᵢ) = 8 > 6,
   contradicting Δ(B) ≤ 6.  ∎

Uses only spec facts: L2 (Δ≤6), L3 (α≤4), L4 (6-set bound), the hitting
conditions and the e_B(P)+k ≤ 6 caps.  Encoded as the sound cardinality
cuts  e(B−P) ≥ 31, e(B−Q) ≥ 31  in Case II.

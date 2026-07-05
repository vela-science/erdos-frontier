# Gap 1 (uniform even k): the D-congruence formulation

Date: 2026-06-10. Status: attack notes — one new structural constraint,
its exact limits, and the residual case. This is the Phase-2 opening
document (see SESSION-REPORT.md roadmap).

## Setup

Even k = 2κ, N = 4. Write F(y) = ∏_{i=1}^k (y+i) = Q(y)² − r(y) with
Q ∈ (1/2^κ)ℤ[y] monic-ish of degree κ, deg r ≤ 2κ−2 (the polynomial
square-root truncation of the dichotomy proof, T1). A solution
F(m) = 4F(n) gives

  (Q(m) − 2Q(n)) · (Q(m) + 2Q(n)) = r(m) − 4r(n),

so D := Q(m) − 2Q(n) is a rational with denominator | 2^{κ+s} and
|D| ≤ C(k)·m^{κ−2}/m^{κ−1}-scale after the matched expansion — the
Thue-type smallness of T1. The T1 box comes from: D ≠ 0 ⇒ |D| ≥ 2^{−κ−s}.
Gap 1 = improve the lower bound on |D| using the capture structure, for
k³ ≤ n ≤ 2^κ·poly.

## CORRECTION (added same night, after attempting the proof)

Two discoveries from actually attacking the disjoint-split statement:

1. **Sharing is forced, not optional** (good news): the equation gives
   matched valuations `v_p(F(m)) = v_p(F(n))` for every odd prime
   (`eq_four_matched_valuation`, already Lean-verified), so EVERY
   captured prime of either block divides both blocks with equal
   multiplicity. The "disjoint-split residual" below is vacuous for the
   equation-relevant obstruction; the matched-valuation hypothesis is now
   threaded into the Lean closure
   (`no_eq_four_ge_five_..._pinned_matched`).
2. **The D-congruence counting is vacuous** (bad news): D = Q(m) − 2Q(n)
   lies in the ≤4 square-root residue classes mod p *automatically* —
   the congruence is a consequence of F(m) ≡ F(n) ≡ 0 (mod p), not a
   constraint. The "counting kill" claimed below does not exist. Gap 1
   reverts to: bound |2^(κ+s)·D| from below (or handle D = 0
   structurally), now WITH the knowledge that all captured primes are
   shared. The original section is kept for the record.

## The new constraint (this session — see CORRECTION above)

Let p > 2k be a prime dividing an element of **both** blocks:
p | n+j and p | m+j' (equivalently p | d+(j'−j), so p lives in the
Δ-window). Then F(n) ≡ F(m) ≡ 0 (mod p), hence

  Q(n)² ≡ r(n),  Q(m)² ≡ r(m)  (mod p),

so mod p the quantity 2^{κ+s}·D lies in the ≤ 4 element set
2^{κ+s}·(±√r(m) ∓ 2√r(n)) — and r(m), r(n) mod p are determined by
(j, j', d mod p). **Each shared prime cuts the residue freedom of the
integer 2^{κ+s}D to ≤ 4 classes out of p.** With t shared primes
p_1 < … < p_t and ∏ p_i > 4^t · 2^{κ+s+1} · max|D|, the integer
2^{κ+s}D is confined to a set of size < 1 unless it hits an allowed
class exactly — a counting kill of the generic shared-prime case.

(For a prime dividing only one block, only Q(n) mod p is constrained and
D remains free: single-block primes give nothing on D.)

## The exact limit

Capture does **not** force primes to be shared between the blocks. The
two-capture structure allows configurations where block-1 and block-2
rough primes occupy disjoint slot sets (h vs h' = h+j'−j bookkeeping
aside), t = 0, and the D-congruence is vacuous. So:

- **Closed by this + counting (in principle):** configurations with
  enough shared prime mass (∏ shared p_i ≳ 4^t 2^κ m^{κ−2}).
- **Residual:** few-or-no shared primes — i.e. the two blocks are
  captured by essentially disjoint parts of the Δ-window. Note this
  residual is *more* structured than before: disjointness means the
  window's rough mass splits into two halves each ≳ m/(2^{k-1}k!),
  which is a strong constraint on the factorization of the 2k−1 window
  elements (each window slot serves one block only — combine with
  `slot_capacity` to make this precise).

## Next concrete steps (Phase 2 proper)

1. Quantify the disjoint-split residual: window slots partition into
   B₁-serving and B₂-serving; per-slot capacity (Lean: `slot_capacity`)
   plus the unique-fraction theorem (`big_cells_cross_eq`) bound the
   number of slots needed by each side; derive a 2-adic constraint on
   the split via the κ-parity valuation laws (T2/T3 machinery from
   passes 3–4: v₂(c_j) = s₂(j) − 4j etc.).
2. Numerically map the allowed splits for k = 18, 22, 26, 30, 32 in the
   unswept boxes — if the splits are empty there, T1+split closes those
   cells without sweeping, a template for uniformity.
3. The uniform statement to aim at: "for even k and n ≥ k³, every
   two-capture configuration has shared prime mass ≥ X(k)" with X(k)
   beating 4^t·2^κ·m^{κ−2} — this is now a *combinatorial* statement
   about window factorizations, no longer about approximation quality.

## Honest assessment

This reformulation moves Gap 1 from "combine Thue with 2-adic" (vague)
to "show two captured blocks must share primes" (precise, combinatorial,
testable). It does not close Gap 1 tonight. The residual disjoint-split
case is exactly where the next effort goes, and it is the first version
of Gap 1 that looks like finite combinatorics rather than transcendence
theory.

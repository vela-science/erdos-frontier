# Erdős #686 — session report, 2026-06-09 (pass 7)

Continues the pass 1–6 program. Focus: the Lean lane's frontier statement
for the `N = 4, k ≥ 5` branch, which (with the closed `k = 2, 3, 4` cells)
would answer #686 in the negative.

## What was proven (all Lean-verified, kernel axioms only)

New module `vela/lean/Vela/Erdos686Tail.lean` (~400 lines, builds green,
every theorem depends only on `propext`, `Classical.choice`, `Quot.sound`):

1. **Tail bound** (`lowerCapturedAboveTwo_bound`): capture of a single
   block forces `d + x < 2^(k-1) · k! · Δ_k(d)`. The frontier theorem
   `no_two_lowerCapturedAboveTwo_of_lt` — previously quantified over all
   `x > d` — is now reduced to a **finite window per (k, d)** via the new
   wrapper `no_eq_four_ge_five_of_forall_no_two_lowerCapturedAboveTwo_of_lt_bounded`.
   Proof: `P_k(A) = k!·C(A+k,k)`, Kummer's carry bound, `π(2k) ≤ k−1` for
   `k ≥ 5`. The `x → ∞` regime that looked Størmer/S-unit-hard is closed by
   elementary counting; `k = 5` is exactly where the argument activates.

2. **Rough-mass lower bound + gcd-mass theorem**
   (`lt_two_pow_mul_factorial_mul_roughPart`,
   `lowerCapturedAboveTwo_gcd_mass`): a captured row forces
   `d + x < 2^(k-1)·k!·gcd(Δ_k(d), P_{3k-2}(x−k+1))` — the windows around
   `d` and around `x` must share ~`log x` of divisor mass. This is the
   formal launching point for the middle-range attack (Dirichlet descent:
   generic ratio `x/d` ⇒ all captured primes `O(√(kd))`; exceptional ratio
   ⇒ overlap-family structure). See `MIDDLE-RANGE.md`.

3. **Pinning theorems** (`eq_four_pinning_lower/upper`, `eq_four_window`):
   any solution of `P_k(n+d) = 4·P_k(n)` satisfies
   `4(n+1)^k ≤ (n+d+1)^k ≤ … ≤ 4(n+k)^k`-squeeze, and two solutions for the
   same `(k,d)` differ by `< k` (borderline case killed 2-adically:
   `a^k = 4·b^k ⇒ k | 2`). This is the soundness theorem for window sweeps.

## Computation (engines validated, all artifacts in this directory)

- **Capture-pair sweeps** (`sweep_capture.c`, validated element-wise vs
  sympy): zero two-capture pairs for k=5–12 / d ≤ 2000 / x ≤ 10^6,
  d ≤ 200 / x ≤ 10^7, d ≤ 50 / x ≤ 10^8 (k ≤ 7), d ≤ 20000 / x ≤ 10^5
  (k ≤ 8) — including the weaker `k < x ≤ d` region.
- **Equation sweeps along the pinned ray** (`search_eq.c`, ~100 ns/d at
  k=5, Mersenne-61 filter, validated against the known overlap families):
  **first-ever finite swept regions for odd k**. Completed as of writing:
  N=25, k=5–11, d ≤ 10^9: zero admissible hits. In flight (check
  `logs/eq_*.err` for DONE lines): N=4 k=5–13 to d ≤ 10^10; N=49/64/81
  odd k to d ≤ 10^9; queued overnight (`run_even_cells.sh`): the
  outstanding even cells k=18 (d ≤ 5·10^10), k=32 (d ≤ 1.1·10^10), k=36
  (d ≤ 1.3·10^10), N=4 — covering their pass-5 dichotomy boxes.
  Only hit so far: the known inadmissible telescope `k=9, d=1, n=2`
  (`(n+k+1)/(n+1) = 4`), re-verified exactly (`verify_hits.py`).

## State of the problem after this pass

The `N = 4` branch of #686 now rests on the **pinned frontier statement**
(`no_eq_four_ge_five_of_forall_no_two_lowerCapturedAboveTwo_pinned`,
kernel-clean):

> For `5 ≤ k ≤ d < x` with `x` squeeze-admissible
> (`4(d+x+1)^k ≤ (2d+x+1)^k` and `(2d+x+k)^k ≤ 4(d+x+k)^k`) — fewer than
> `k` such `x` per `(k,d)`, by `pinned_squeeze_window` — not both
> `rough_{>2k}(P_k(d+x)) | Δ_k(d)` and `rough_{>2k}(P_k(2d+x)) | Δ_k(d)`.

The pinning is not just convenience. In the unpinned `d^(2k-1)`-sized
window, an adversary can CRT-align `x` against arbitrary slot prime powers
(`d+h = p^e` with smooth cofactors), so no slot-capacity counting argument
alone can close it — the wide form of the frontier is near-sharp as a
counting target. The pinned form removes the adversary's freedom in `x`
entirely: for each `k` there is one forced ratio `x/d → k/ln 4 − 1`, and
the exceptional-relation branch of the descent becomes a question about
rational approximations to the single algebraic number `1/(4^(1/k)−1)`.

Remaining mathematical targets, in order (details in `MIDDLE-RANGE.md`):
1. Generic-ratio theorem (Dirichlet descent + slot capacity) — would leave
   only `x/d` near small-denominator rationals.
2. Overlap-ratio theorem (congruence obstructions per denominator) — the
   regime where every observed near-solution lives.

Both sub-targets are now quantitative thanks to the gcd-mass theorem; the
Thue/Roth-quality wall of the pass-6 report reappears precisely as the
trade-off `β ≥ d^(1/k)` (Liouville, effective) vs `β ≥ d^(1/2-ε)` (Roth,
ineffective) for exact relations `β(x+c) = α(d+h)`.

## Provenance / caveats

- The even-k box values (k=18: n ≤ 6·10^11, k=32: 2.3·10^11, k=36:
  3·10^11) are taken from the pass-6 consolidated report (T1 thresholds);
  the box derivations are not independently replayed here, so those sweeps
  close cells *conditionally on the pass-5 dichotomy computation*.
- The odd-k sweeps need no box: they are unconditional "no solution with
  d ≤ D" statements, justified by the Lean pinning theorems.
- Nothing has been committed to git in either repo yet; new/modified
  files: `vela/lean/Vela/Erdos686Tail.lean`,
  `vela/docs/erdos-attack/686/NOTE.md`, and this directory.

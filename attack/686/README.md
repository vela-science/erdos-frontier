# Erdős #686 — session artifacts (2026-06-09)

Target: the remaining `N = 4, k ≥ 5` branch (all five stuck squares reduce
to per-(N,k) cells; the Lean lane in `vela/lean/Vela/Erdos686.lean` closes
every `k ≥ 5` for `N = 4` from one frontier statement). This directory holds
the session's new mathematics, engines, and sweep results.

## Results

### 1. Tail bound — frontier now finite per (k,d)  [Lean-verified]

`TAIL-BOUND.md` + `vela/lean/Vela/Erdos686Tail.lean` (green,
axioms = Mathlib core three):

> If `5 ≤ k ≤ d` and the `p>2k` rough part of `P_k(d+x)` divides `Δ_k(d)`,
> then `d + x < 2^(k-1) · k! · Δ_k(d)`.

So the frontier theorem `no_two_lowerCapturedAboveTwo_of_lt` is reduced to
the finite window `d < x < 2^(k-1)·k!·Δ_k(d)` (wrapper
`no_eq_four_ge_five_of_forall_no_two_lowerCapturedAboveTwo_of_lt_bounded`).
Pure counting: Kummer bound on `v_p(choose(A+k,k))` + `π(2k) ≤ k−1` for
`k ≥ 5`. Validation: `validate_tail_bound.py`.

### 2. Capture-pair sweeps — frontier window evidence  [zero hits]

`sweep_capture.c` (sieve over the fineness predicate
`rough_{>2k}(m) | Δ_k(d)`, validated element-by-element against sympy):

| pass | k | d | x | hits |
|------|---|---|---|------|
| broad | 5–12 | ≤ 2000 | ≤ 10^6 | 0 |
| deep | 5–12 | ≤ 200 | ≤ 10^7 | 0 |
| very deep | 5–7 | ≤ 50 | ≤ 10^8 | 0 |
| wide | 5–8 | 2001–20000 | ≤ 10^5 | 0 |

Zero two-capture pairs anywhere, including the weaker region `k < x ≤ d`.

### 3. Equation sweeps along the pinned ray  [first odd-k sweeps]

Any solution of `P_k(n+d) = N·P_k(n)` has `n+1 ≤ d/θ ≤ n+k`
(`θ = N^(1/k)−1`): at most `k−1` candidate `n` per `(k,d)`. `search_eq.c`
sweeps all `d` with a Mersenne-61 modular filter (validated: finds exactly
the known inadmissible overlap families, e.g. `d=1, n=(k−3)/3` for `N=4`,
`3 | k−3`, and `d=1, n=0` for `N=25, k=24`).

Sweep log (only hits are the known `d < k` overlap families; "clean" =
no admissible hit, i.e. none with `d ≥ k`):

| N | k | d range | result |
|---|---|---------|--------|
| 4 | 5,7,9,11,13 | ≤ 10^10 | **clean** (unconditional; only the known d=1 telescope at k=9) |
| 25 | 5,7,9,11,13 | ≤ 10^9 | **clean** (unconditional) |
| 49 | 5,7,9,11,13 | ≤ 10^9 | **clean** (unconditional) |
| 64 | 5,7,9,11,13 | ≤ 10^9 | **clean** (unconditional) |
| 81 | 5,7,9,11,13 | ≤ 10^9 | **clean** (unconditional) |

These are the first finite nontrivial regions ever swept for odd `k`
(previous program state: odd `k ≥ 5` entirely open, no boxes).

### 3b. k=5, N=4 → one genus-2 curve  [reduction proven]

`CHABAUTY-K5.md` + `verify_chabauty_reduction.py`: the oddness of P₅ about
its center collapses the genus-6 curve `P₅(m) = 4·P₅(n)` to the genus-2
quotient `w² = 9t⁶ + 64t⁵ − 200t³ + 64t + 144` (conductor 3²·5⁵·139·349).
Determining its rational points closes the cell. 34 points found to height
10⁶; the only nontrivial lift is the rational identity
`P₅(5/3) = 4·P₅(2/3)`. Next step: Magma `RankBounds` + (quadratic)
Chabauty / Mordell–Weil sieve.

### 4. Middle range analysis

`MIDDLE-RANGE.md`: gcd-mass lower bound, Euclidean/Dirichlet descent
dichotomy (generic ratio ⇒ all captured primes `O(√(kd))`; exceptional
ratio ⇒ overlap-family structure), and the two named sub-targets that
would close the window.

## Files

- `TAIL-BOUND.md`, `MIDDLE-RANGE.md` — mathematics
- `sweep_capture.c` — capture-pair sieve engine (validated)
- `search_eq.c` — pinned-ray equation sweep engine (validated)
- `search_no_two_capture.py` — original Python reference implementation
- `validate_tail_bound.py` — numeric validation of the inequality chain
- `logs/` — all sweep outputs (`*.err` has the DONE/hits summary lines)

Lean artifacts live in the vela repo: `lean/Vela/Erdos686Tail.lean`,
documented in `docs/erdos-attack/686/NOTE.md`.

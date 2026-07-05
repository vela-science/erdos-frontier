# The tail bound: block capture forces x ≤ explicit(k, d)

Date: 2026-06-09. Status: elementary proof, numerically validated; Lean
formalization in progress (`Vela/Erdos686.lean`).

## Statement

Notation as in `Vela/Erdos686.lean`:
`P_k(y) = ∏_{i=1}^k (y+i)`, `Δ_k(d) = ∏_{h=-(k-1)}^{k-1} (d+h)`,
`rough_{>B}(N)` = the part of `N` made of primes `> B`, and

```
lowerCapturedAboveTwo k d t  :=  rough_{>2k}(P_k(d+t)) | Δ_k(d).
```

**Theorem (tail bound).** Let `k ≥ 5` and `A ≥ k`. If
`rough_{>2k}(P_k(A)) | Δ_k(d)` then

```
A < 2^(k-1) · k! · Δ_k(d).
```

In particular `lowerCapturedAboveTwo k d x` implies
`d + x < 2^(k-1) · k! · Δ_k(d) ≤ 2^(k-1) · k! · (d+k-1)^(2k-1)`,
so the frontier theorem `no_two_lowerCapturedAboveTwo_of_lt` (and hence the
remaining `N = 4, k ≥ 5` branch of Erdős #686 through
`no_eq_four_ge_five_of_forall_no_two_lowerCapturedAboveTwo_of_lt`) is reduced
to the **finite** range

```
d < x < 2^(k-1) · k! · Δ_k(d)        (per fixed k, d).
```

A sharper form of the same argument (kept out of Lean for now) gives
`A ≤ (2^π k!)^{1/(k-π)} (d+k)^{(2k-1)/(k-π)}` with `π = π(2k)`, i.e. exponent
`(2k-1)/(k-π(2k))` → ~2 for large `k`; at `k = 5, 6` the exponent is `9` and
`11`.

## Proof

Write `P := P_k(A) = ∏_{j=1}^k (A+j)`, and split `P = S·T` with
`T := rough_{>2k}(P)` and `S := P/T` its `2k`-smooth part.

1. **T is small.** By hypothesis `T | Δ_k(d)`, and `Δ_k(d) ≥ 1`, so
   `T ≤ Δ_k(d)`.

2. **S is small (Kummer/Legendre).** `P = (A+k)!/A! = k! · C(A+k, k)`.
   For every prime `p`,
   `v_p(C(A+k,k)) ≤ log_p(A+k)` (the number of base-`p` carries in
   `A + k`, Kummer; equivalently each Legendre summand
   `⌊(A+k)/p^i⌋ − ⌊A/p^i⌋ − ⌊k/p^i⌋ ∈ {0,1}` and vanishes for `p^i > A+k`).
   Hence

   ```
   S = ∏_{p ≤ 2k} p^{v_p(P)} ≤ ∏_{p ≤ 2k} p^{v_p(k!)} · ∏_{p ≤ 2k} p^{log_p(A+k)}
     ≤ k! · (A+k)^{π(2k)} .
   ```

   (The first product is exactly `k!` since all prime factors of `k!` are
   `≤ k ≤ 2k`; the second uses `p^{log_p m} ≤ m`.)

3. **π(2k) ≤ k−1 for k ≥ 5.** The primes in `[2, 2k]` are `2` together with
   odd numbers in `[3, 2k−1]`; there are `k−1` odd numbers there and at least
   one (namely `9`, since `2k ≥ 10`) is composite, so
   `π(2k) ≤ 1 + (k−1) − 1 = k−1`.

4. **Assemble.** `A^k < (A+1)⋯(A+k) = S·T ≤ k! (A+k)^{k-1} Δ_k(d)`.
   Since `A ≥ k`, `A+k ≤ 2A`, so
   `A^k < k! · 2^{k-1} A^{k-1} · Δ_k(d)`, and dividing by `A^{k-1}`:

   ```
   A < 2^(k-1) · k! · Δ_k(d).            ∎
   ```

## Why this matters

The frontier statement quantifies over all `x > d`. The regime `x → ∞` looked
like it needed Størmer/S-unit machinery (block elements must be
`2k`-smooth × divisor-of-`Δ`, and runs of such numbers thin out only
ineffectively by standard tools). The observation here is that **one block
capture alone** already caps `x` elementarily: the rough mass of a captured
block is at most `Δ`, while the smooth mass of `k` consecutive integers can
only carry `π(2k) < k` "free" digit-counts — the same smooth-density wall
that makes `k = 5` the threshold (`π(8) = 4 = k` at `k = 4`, where the
argument exactly saturates).

What remains of the frontier theorem after this reduction is the structured
middle range `d < x < 2^{k-1} k! Δ_k(d)`, where the difference-window descent
(`lowerCapturedAboveTwo_roughPart_dvd_difference_window`) is available.

## Validation

`validate_tail_bound.py`: 4000 random `(k, A)`, `k ≤ 16`, `A ≤ 10^12`:
`S ≤ k!·(A+k)^{π(2k)}` holds always — worst observed ratio `S/bound`
= 0.0051; `π(2k) ≤ k−1` checked for `k = 5..10^4`.

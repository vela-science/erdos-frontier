# The middle range: what remains of the #686 frontier after the tail bound

Date: 2026-06-09. Companion to `TAIL-BOUND.md` and
`vela/lean/Vela/Erdos686Tail.lean`.

After the tail bound, the remaining N=4, k≥5 target is:

**(M)** For all k ≥ 5, k ≤ d, d < x < 2^(k-1)·k!·Δ_k(d): not both
rough_{>2k}(P_k(d+x)) | Δ_k(d) and rough_{>2k}(P_k(2d+x)) | Δ_k(d).

## Structure available inside the window

Write A = d+x. Capture forces, per prime power q = p^e ∥ (block element),
p > 2k:

1. **Window localization (both sides).** q divides a Δ-slot d+h (|h| ≤ k−1)
   *and* (subtracting) an element of the difference window near x
   (lower block: x+j−h, width 3k−2 — this is
   `lowerCapturedAboveTwo_roughPart_dvd_difference_window` in Lean; upper
   block: x+j−2h after subtracting twice, width ~5k). So every captured
   prime power divides a gcd `gcd(d+h, x+c)` with |h| < k, |c| ≤ 3k.

2. **Mass lower bound (from the tail-bound smooth estimate).** The rough
   parts satisfy T₁ ≥ A/(2^(k-1)·k!) and T₂ ≥ (A+d)/(2^(k-1)·k!).
   Combined with (1): **two captures force the gcd mass**

   ∏_{|h|<k, |c|≤3k} gcd(d+h, x+c) ≥ A/(2^(k-1)·k!),

   i.e. the integer windows around d and around x must share ~log x of
   common divisor mass. For generic (d,x) this mass is O(k² log)-ish; the
   exceptional x form a very sparse, structured set.

3. **Euclidean descent / Dirichlet dichotomy.** If p > 2k divides d+h and
   x+c, then for any rational approximation α/β to x/d with β ≤ B
   (Dirichlet: |βx − αd| ≤ d/B), p divides β(x+c) − α(d+h), an integer of
   size ≤ d/B + Bk-ish. Hence either
   - p ≤ d/B + O(Bk)  (taking B ~ √(d/k): p = O(√(kd)) — "small primes"), or
   - the relation is *exact*: β(x+c) = α(d+h), i.e. x+c is a small-denominator
     rational multiple of a window element — the **overlap-family structure**
     (x/d near a small-denominator rational), which is exactly the only
     family of solutions ever observed in ~6·10^12 swept values.

   So the middle range splits: (a) x/d "generic" — all captured primes are
   O(√(kd)) and the Δ-window must carry rough mass ~x out of √(kd)-bounded
   primes, each prime power confined to one of 2k−1 slots; (b) x/d near a
   small-denominator rational — the overlap regime, where the candidate
   block elements are explicit rational multiples of window elements and
   per-slot elementary arguments (parity/3-adic, as in the closed even-k
   cells) should apply.

## For the equation, the window is really k−1 points

Any solution of P_k(n+d) = 4·P_k(n) satisfies the squeeze
(1+d/(n+k))^k ≤ 4 ≤ (1+d/(n+1))^k, i.e.

  n+1 ≤ d/θ_k ≤ n+k,  θ_k = 4^(1/k)−1,

so per (k,d) there are at most k−1 candidate n — the equation only ever
meets the capture predicate on the ray x = n−d ≈ (1/θ_k − 1)d. The ratio
x/d → k/ln4 − 1 + O(1/k) is *fixed* per k; the relational/overlap branch of
the descent then concerns rational approximations to the single number
1/θ_k — this is where the program's known Thue/Roth-quality wall (Gap 1)
reappears, now in elementary clothing: Liouville gives β ≥ c·d^(1/k) for an
exact relation, Roth-quality would give β ≥ d^(1/2−ε) but ineffectively.

This pinning also makes direct cell sweeps cheap (`search_eq.c`): all d up
to 10^9–10^10 per (k,N) in minutes-to-hours, for the first time covering
odd k.

## Status

- (M) restricted to the swept boxes: verified empty (see README table).
- (M) in general: open. The two named sub-targets, in decreasing value:
  1. **Generic-ratio theorem**: if x/d has no rational approximation α/β
     with β ≤ d^(1/3) and |βx−αd| ≤ k·β-ish, then no two-capture pair.
     (All captured primes ≤ O(d^(2/3)k); needs a slot-capacity count that
     beats the 2k−1 slots × multiplicity budget.)
  2. **Overlap-ratio theorem**: x ≈ (α/β)d with small β ⇒ block elements
     are near-multiples of window slots; close by congruence obstructions
     per β (finitely many β per k after 1.; the even-k closed cells did
     exactly this for the β occurring there).

# k = 5, N = 4 reduces to one genus-2 curve

Date: 2026-06-09. Status: reduction proven (symbolically verified,
`verify_chabauty_reduction.py`); rank computation scoped; this is the
concrete path to closing the most valuable open cell of Erdős #686.

## The reduction

The equation `P₅(m) = 4·P₅(n)`, `P₅(y) = (y+1)⋯(y+5)`, centered at
`u = m+3, v = n+3`, becomes `g(u) = 4·g(v)` with the **odd** quintic
`g(u) = u⁵ − 5u³ + 4u = u(u²−1)(u²−4)`.

The plane curve `C : g(u) = 4g(v)` is a smooth quintic (verified: no shared
critical values, 5 distinct points at infinity), genus 6 — hopeless
directly. But oddness gives the involution `σ(u,v) = (−u,−v)`, with 6 fixed
points ((0,0) and the 5 points at infinity); Riemann–Hurwitz:
`10 = 2(2g′−2) + 6`, so the quotient `C/σ` has **genus 2**.

Explicitly, with `p = u²`, `q = v²`, `h(s) = (s−1)(s−4)`:

- `t := 4h(q)/h(p)` satisfies `p = q·t²`, and
- `q²(t⁵−4) − 5q(t³−4) + 4(t−4) = 0` — *quadratic in q*, so
- `w := 2q(t⁵−4) − 5(t³−4)` gives the hyperelliptic model

```
C₂ :  w² = D(t) = 9t⁶ + 64t⁵ − 200t³ + 64t + 144        (genus 2)
```

(`D` squarefree; leading coefficient `9 = 3²` ⇒ two rational points at
infinity.) All identities verified symbolically modulo the curve ideal.

**Lifting.** A point `(t,w) ∈ C₂(ℚ)` with `t⁵ ≠ 4` lifts to a point of
`C(ℚ)` iff `q = (w + 5(t³−4)) / (2(t⁵−4))` is a rational square (then
`p = qt²` is automatically one). Every integer solution of the original
equation with `u ∉ {0,±1,±2}` maps to such a point. Hence:

> **`C₂(ℚ)` finite and known ⇒ the cell (k=5, N=4) of #686 is closed.**

## Data

- Conductor (PARI `genus2red`): `1 364 371 875 = 3²·5⁵·139·349`.
  (Above the LMFDB genus-2 range, so the curve is not in LMFDB.)
- Point search to height 10⁶ (PARI `hyperellratpoints`): 34 affine points,
  x-coordinates `t ∈ {0, ±1, ±2, 4, −20, ±1/2, −38/5, −34/5, 2/7, −19/9,
  14/11, −20/17, −34/43, −53/55}` (each with ±w), plus `∞±`.
- Pullback analysis (all 34 checked): the lifting condition `q = □` holds
  only for the degenerate points (they map to `u², v² ∈ {0,1,4}`, i.e.
  product = 0) **and one nontrivial orbit**: `t = 14/11` lifts to
  `(u,v) = (±14/3, ±11/3)`, i.e. the rational identity
  `P₅(5/3) = 4·P₅(2/3)` — a non-integral rational point. No integral
  solutions appear, consistent with #686.
- The abundance of non-lifting rational points suggests
  `rank J(ℚ) ≥ 2`; analytic rank computation via PARI `lfungenus2` was
  started (slow at conductor ~1.4·10⁹; see logs).

## Magma results (2026-06-09, run by Will via the online calculator)

- `RankBounds(J) = 3 5`; torsion trivial.
- **`MordellWeilGroupGenus2(J)`: J(ℚ) ≅ ℤ⁵, free, both certification
  flags true — rank exactly 5, proven.** Remarkably rich for conductor
  ~1.4·10⁹ (consistent with 34 small points). With `End(J) = ℤ` (RM test
  negative) this rules out every Chabauty variant at the quotient level.
- Surviving geometric route: Chabauty on the genus-6 cover `C` needs
  `rank Jac(C) = 5 + rank(Prym) ≤ 5`, i.e. **Prym (dim 4) rank exactly 0**.
- **Prym probe result (Magma, 2026-06-09): the Prym is simple.** For
  `p ∈ {7, 11, 13, 17, 19}` the deg-12 zeta numerator of `C/𝔽_p` factors
  as (the `C₂` quartic — traces −8, −5, −8, −14, −4, matching the PARI
  Euler data exactly) × an octic **irreducible over ℚ** in every case.
  Prym Frobenius traces: −10, −8, −8, −6, −10 at p = 7, 11, 13, 17, 19.
  No decomposition ⇒ no `RankBounds` shortcut; the Prym rank is only
  reachable via (i) its L-value at the center (dim-4 motive, conductor
  `cond(Jac C)/1364371875`, likely far beyond current analytic software),
  or (ii) descent machinery for simple 4-dim abelian varieties, which
  does not currently exist in usable form.

### Geometric-lane verdict

The cell is fully specified but genuinely hard by current technology:
`C₂` has `J(ℚ) = ℤ⁵` (proven), `End = ℤ`, no Chabauty at the quotient;
the cover route hinges on the rank of a simple 4-dim Prym, out of reach
of available software; and any eventual method must "see" the nontrivial
rational point `P₅(5/3) = 4·P₅(2/3)`. This is a strong invitation for the
Balakrishnan–Bruin–Stoll school (genus-6 plane-quintic Chabauty with one
differential *if* Prym rank 0, else MW-sieve with the ℤ⁵ generators), and
a clean problem statement to circulate. Meanwhile the **pinned gcd-mass
lane** (`MIDDLE-RANGE.md`, `Erdos686Tail.lean`) is unaffected and remains
the primary route to the uniform theorem.
- The nontrivial lift confirmed in Magma's weighted coordinates:
  `(14 : −10740 : 11)` ↔ affine `(t, w) = (14/11, −10740/11³)`,
  `q = 121/9`, i.e. `P₅(5/3) = 4·P₅(2/3)`.

Consequences: rank ≥ 3 > g = 2 kills classical Chabauty, and generic
quadratic Chabauty needs `r ≤ g + ρ(Jac) − 1 = 2` unless the Néron–Severi
rank ρ ≥ 2 (e.g. real multiplication — see RM test below). The
`[3,5]` gap is likely 2-Selmer noise (Sha[2]); worth running
`MordellWeilGroupGenus2(J)` / `RankBound(J : ...)` refinements to settle
the exact rank.

**RM test: negative** (PARI `hyperellcharpoly`, all good `p ≤ 200`): the
squarefree kernels of `a_p² − 4(b_p − 2p)` vary (1, 53, 6, 30, 19, 5, …),
so `End(J) = ℤ`, `ρ = 1`, and quadratic Chabauty is capped at rank 2 —
**both Chabauty variants are unavailable on `C₂` at rank ≥ 3**.

Remaining routes, in order of promise:
1. **Settle the exact rank and get generators**: run in the Magma
   calculator `MordellWeilGroupGenus2(J);` (Stoll's algorithm; use
   `SetClassGroupBounds("GRH")` if it stalls). The `[3,5]` gap is likely
   Sha[2]; exact generators are the prerequisite for everything below.
2. **Attack the square-lift double cover directly**: the lifting locus is
   `z² = q` on `C₂`, which IS the original genus-6 curve `C`; note the
   identity `(w + 5(t³−4))(w − 5(t³−4)) = −16(t⁵−4)(t−4)` on `C₂`, so the
   lift condition is equivalently `−2(t−4)(w − 5(t³−4)) = □`. Covering
   collection: twists `δz² = −2(t−4)(w−5(t³−4))`, `δ` supported on
   `{±1, 2, 3, 5, 139, 349}`; combine with a Mordell–Weil sieve once
   generators are known. Note the only twist relevant to #686 is `δ = 1`,
   whose cover is the original genus-6 curve `C` itself: Chabauty on `C`
   needs `rank Jac(C) = rank Jac(C₂) + rank Prym ≤ 5`, i.e. Prym (dim 4)
   rank ≤ 2 if the quotient rank is exactly 3 — testable numerically via
   the L-function factorization `L(Jac C) = L(Jac C₂)·L(Prym)`.
3. **Return to the pinned gcd-mass theorem** (uniform-k lane, see
   `MIDDLE-RANGE.md`) — unaffected by this rank obstruction.

Bottom line: the cell is now *specified* for specialists — explicit curve,
conductor `3²·5⁵·139·349`, rank window `[3,5]`, trivial torsion, no RM,
known points incl. the nontrivial `P₅(5/3) = 4·P₅(2/3)`, and the exact
cover whose rational points decide #686's k=5 cell. This matches the
pass-6 estimate ("months-scale with specialists") but replaces an
amorphous task with a concrete one.

## What a specialist (or a Magma session) should run

```magma
P<x> := PolynomialRing(Rationals());
C := HyperellipticCurve(9*x^6 + 64*x^5 - 200*x^3 + 64*x + 144);
J := Jacobian(C);
RankBounds(J);                      // expect 2 (maybe 3)
// if rank <= 1: Chabauty(J ! [pt - infty]) finishes immediately.
// if rank = 2:  quadratic Chabauty (Balakrishnan–Dogra–Müller toolkit),
//               or Two-cover descent + Mordell–Weil sieve:
TwoCoverDescent(C);
```

The Mordell–Weil sieve is particularly promising here because we do not
need all of `C₂(ℚ)`: we only need the points where `q` is a square, i.e.
rational points on the *double cover* `z² = q(t,w)`, which is a curve of
higher genus — an Elliptic-Chabauty-style finish over `ℚ` may apply to it
directly.

## Literature check (done 2026-06-09)

Web search found no prior treatment of the specific equation
`P₅(m) = 4·P₅(n)`: the classical results (Erdős–Selfridge;
Bennett–Bruin–Győry–Hajdu and successors) concern *perfect powers* of
products of consecutive terms, not fixed rational ratios between two
shifted blocks. The #686 forum thread is at
erdosproblems.com/forum/thread/686. A deeper check against the
`f(x) = c·f(y)` literature (Beukers-style, Hajdu–Pintér) is still advised
before publication.

## Caveats / further checks before claiming novelty

Equations `f(x) = c·f(y)` for products of consecutive integers have a
literature (Bennett–Bruin–Győry–Hajdu and successors on
`x(x+1)⋯(x+k−1) = c·y(y+1)⋯(y+k−1)`); the case `c = 4, k = 5` may already
be resolved or resolvable by their methods. Check before publishing:
- Bennett–Bruin–Győry–Hajdu, *Powers from products of consecutive terms in
  arithmetic progression* and related;
- Hajdu–Pintér and Beukers-style results on `f(x) = cf(y)`;
- Stoll's work on `y(y+1)⋯(y+k−1) = x(x+1)⋯(x+k−1)·c`.

## Outlook for other cells

The same oddness trick works for every odd `k` (P_k is odd around its
center) and every `N`: `g_k(u) = N·g_k(v)` has the `(−u,−v)` involution and
the quotient has genus `(k−1)/2 − 1 + (k − #{...})`-type drop; for `k = 5`
genus 6 → 2. For `k = 7`: genus 15 → quotient genus 6 (still hard). So
`k = 5` is the unique cell where this collapse lands in Chabauty range —
exactly the cell the pass-6 report identified as the most valuable target.

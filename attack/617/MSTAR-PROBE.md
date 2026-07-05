# The m* probe (2026-06-12)

Define **m\*** = minimum number of edges of a graph G on 26 vertices with

* (A) α(G) ≤ 5 — every 6-set of vertices spans ≥ 1 edge;
* (B) every 6-set of vertices spans ≤ 11 edges.

Both hold for every colour class of a balanced 5-colouring of K₂₆
(NOTES.md §1, unconditional).  m\* is the single number that decides the
shape of the whole campaign:

* **m\* ≥ 66** ⟹ the five colour classes carry ≥ 330 > 325 = e(K₂₆)
  edges — **no balanced colouring exists and #617 r = 5 is proved**, with
  no dependence on the imported pass-1..20 ladder (it is bypassed
  entirely).
* **m\* ≤ 65** ⟹ single-colour-class constraints alone can never close
  r = 5; the 62..65 rungs must use interaction between classes.

Known bounds: m\* ≥ 55 (Turán: (A) alone), and m\* > 55 strictly since the
Turán extremal K₆ ⊔ 4K₅ violates (B) on its K₆.  The conditional ladder
(≥ 62, NOTES.md §5) is *consistent with* but does not bound m\*: its
provenance may use multi-class arguments.

## Method

`probe_mstar.py`: CP-SAT over 325 edge variables, both 6-set families
eager (230 230 × 2 constraints), valid Turán cut e ≥ 55, sorted-degree
symmetry breaking.  Two modes: minimise e(G), or decision "∃ G with
e(G) ≤ target".  Every incumbent is dumped as an edge list and re-verified
by `check_mstar_witness.py` (independent, bitset recheck of all 230 230
six-sets, no shared code).

CP-SAT INFEASIBLE here is solver-trust only; if the decision run at 65
returns INFEASIBLE the follow-up is a certified UNSAT (CNF + cube-and-
conquer + DRAT, as in `certify_unsat.py`) — that artifact would *be* the
proof of #617 r = 5.

## Status

* Minimise run (13 workers, stopped at ~7 min in favour of the decision
  form): incumbents 122 → **98**, still descending at kill time
  (`artifacts/mstar_witness_E98.txt`, independently VERIFIED: m\* ≤ 98);
  internal lower bound parked at the Turán cut 55.  Minimise relaunched at
  cloud scale alongside the decision runs; current verified record
  **m\* ≤ 96** (`artifacts/mstar_witness_E96.txt`, cloud, ~48 min).
* Decision run at target 65 (6 h, 10 workers): **in flight**
  (`artifacts/mstar_decision65.log`).
* Useful secondary targets once it resolves: 61 (consistency check against
  the imported P1 if its proof was single-class), and bisection toward the
  true m\*.

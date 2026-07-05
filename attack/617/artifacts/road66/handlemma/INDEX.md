# road66/handlemma — deliverables index

Attack on the "walled set" (low-defect, high-I configs) for Erdős #617,
rungs q = 8, 9, 10 (the route to m* >= 66). All claims are machine-checked;
hand lemmas are proved in LEMMAS.md.

## Read this first
- **LEMMAS.md** — every lemma stated + proved (or marked PARTIAL with the
  exact gap). Sections: accounting identity; blocking engine (B-G3, B4);
  Foothold refinements (F1, F1'); clique-core table (Lemma C); Case A
  (Theorem A); the distributed-regime certifier + the precise GAP; proofs;
  validation; **the hand-coverage census (§8)**; conclusion (§9).

## Scripts (each runnable; all use ortools CP-SAT)
- `blocking.py`        — EXACT transversal-grid blocking numbers under the
                         Foothold matching budget. Lemma B4 / B-G3 tables.
                         (18-lemma = BLOCK(3,3,3,3)=18.)
- `core_in_5part.py`   — EXACT clique-core blocking (Lemma C): K2->18,
                         K3->15, K4->9, K5->5 over empty completion parts.
- `clique_core.py`     — core-in-P0 variant (corrected completion size).
- `lb_oracle3.py`      — the CERTIFIER lb3: a valid SUB-MODEL of the full
                         spec (CONC concentration cuts incl. Lemma F1' +
                         all K6 clauses). lb3_LB <= full_min always; reproduces
                         the full min EXACTLY on Case-A C4 (=34). Kills a
                         config at rung q when lb3_LB > I+q-d.
- `hand_coverage.py`   — pure-combinatorial census: what fraction of the
                         walled set the HAND lemmas close (4-24%).
- `hardest_family.py`  — full-spec confirmation of the hardest CONCENTRATED
                         family (star + each 6-edge graph in one 5-part,
                         I=10) at a chosen rung.
- `crux_dense.py`      — full-spec decision on the single hardest atom
                         (star + K_{2,3}). q8 cap18 + q10 cap20: INFEASIBLE.
- `validate.py`        — (A) lb3 tightness vs exact full min; (B) kill-
                         consistency: lb3 kills ⊆ full-spec INFEASIBLE.
- `lb_oracle.py`,`lb_oracle2.py` — weaker earlier relaxations (kept to show
                         WHICH constraints matter; superseded by lb3).
- `single_edge.py`     — single-P0-edge demand vs 5-part edge-profile
                         (shows the per-edge bound COLLAPSES once parts carry
                         edges — why no clean per-edge bound exists).
- `one_part_demand.py` — MOOT: its premise (P0 empty) is unrealizable
                         (P0 must have >=4 edges); returns INTRA_INFEAS.
                         Kept as a documented dead end.

## Result logs / data
- `crux_K23_q8.log`, `crux_K23_q10.log` — K_{2,3} atom: INFEASIBLE both.
- `hardest_family_q10.log`, `hardest_family.jsonl` — 6 dense graphs @ cap20.
- `hand_coverage.log` — the census numbers.
- `validate.log` — tightness + kill-consistency.

## One-line status
The route to m* >= 66 CLOSES (machine-verified at its hardest points), but
NOT via a clean general hand lemma: the hand lemmas close only the
clique-bearing 4-24% of the walled set; the triangle-free diffuse residue
is killed only by the full-spec CP-SAT (tractable, minutes/config). See
LEMMAS.md §9.

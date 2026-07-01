Adds Formal Conjectures statements for Erdős problems 24, 93, 164, 314, 315, 333, 369, 401, 429, 435.

Each statement was drafted from the boxed problem text on erdosproblems.com (docstrings verbatim), cross-checked against two independently hosted Lean proofs, and reviewed for statement fidelity before submission. `formal_proof` links (pinned to a commit) are included only where the hosted proof is unconditional under an axiom and hypothesis audit; divergences from the hosted formalizations are noted below.

| problem | upstream state | proof linked | divergence notes |
|---|---|---|---|
| 24 | proved (Lean) | yes | Count vocabulary: draft uses Mathlib's SimpleGraph.copyCount G (cycleGraph 5) (number of subgraphs of G isomorphic to C5); both hosted proofs define numC5 G = #{labelled C5 maps Fin 5 -> V} / 10 (labelled embeddings divi |
| 93 | proved (Lean) | yes | Space: draft uses FC's concrete R^2 (EuclideanSpace R (Fin 2), the scoped notation from FormalConjecturesForMathlib/Geometry/2d.lean), house style of the sibling problems FC 982 and FC 1082; both hosted quantify over an  |
| 164 | proved (Lean) | yes | Members > 1: both hosted bake (forall a in A, 2 <= a) into their PrimitiveSet predicate; draft keeps the problem text's definition verbatim (IsPrimitive A = no member of A divides another) and adds the floor as a separat |
| 314 | proved (Lean) | yes | FC house wrapper: stated as answer(True) ↔ (liminf n²·ε(n) = 0); jayyhk's hosted erdos_314 is the bare equality Filter.liminf (fun n => (n:ℝ)^2 * eps n) atTop = 0 with no answer() wrapper.; vs plby: plby has NO erdos_314 |
| 315 | proved (Lean) | yes | FC house wrapper: stated as answer(True) ↔ ∀ a, … ; both hosted erdos_315 theorems are bare implications with the sequence a as a theorem parameter.; Monotonicity: the text says a₁<a₂<⋯, so we use StrictMono a — this mat |
| 333 | disproved (Lean) | yes | Polarity/wrapper: stated as answer(False) ↔ P where P = (∀ A density-zero, ∃ B, A ⊆ B+B ∧ count = o(√N)) — FC house style for a disproved yes/no question (cf. FC 263.parts.ii). jayyhk's hosted erdos_333 is the direct neg |
| 369 | proved (Lean) | yes | INTERPRETATION (statement vs problem text): the text as written is trivially true (the site commentary itself says so: take {1,...,k} and n > k^{1/eps}). The drafted statement formalizes the commentary's SECOND non-trivi |
| 401 | proved (Lean) | yes | HOSTED-vs-HOSTED structural disagreement: jayyhk's erdos_401 states the text's question directly (`exists f : N -> R, Tendsto f atTop atTop && forall r >= 1, ...`); plby has no single final statement matching the text -- |
| 429 | disproved (Lean) | yes | STATEMENT DIRECTION: the drafted theorem states the QUESTION positively as `answer(False) <-> P` (upstream state 'disproved (Lean)' maps to FC category 'research solved' with answer False). Both hosted theorems instead s |
| 435 | proved (Lean) | yes | 'What is the largest integer not of the form ...' rendered as `IsGreatest {m : Z | not exists c, m = sum ...} target`; both hosted theorems state `target n not-in Representable n && forall x : Z, x > target n -> x in Rep |

Part of #3998.

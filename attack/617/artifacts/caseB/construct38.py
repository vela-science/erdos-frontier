"""Explicit hand construction of a (conjecturally) valid Case-B H with 38
holes (e(H)=237), C4 config -- used to validate the independent checker
and the CP-SAT encoding end-to-end (a model must accept it).

Structure:
  P0: C4 on 0-1-2-3 (edges 01,12,23,03), isolated 4,5
  P1: x=6,y=7 edge; P2={11..15}, P3={16..20}, P4={21..25}
  - cycle class {0,2} holed to (11,16,21); class {1,3} to (12,17,22)
  - P1 vertices aligned to triples: 6,9 -> (13,18,23); 7,10 -> (14,19,24);
    8 -> (15,20,25)
  - aligned hole-triangles: (13,18,23),(14,19,24),(15,20,25) all 3 pairs each
  - x=6 cut from isolated P0 vertices 4,5  (blocks the xy-system there)
"""
import json

holes = []
# P0 -> parts (12)
for z, (a, b, c) in [(0, (11, 16, 21)), (2, (11, 16, 21)),
                     (1, (12, 17, 22)), (3, (12, 17, 22))]:
    holes += [(z, a), (z, b), (z, c)]
# P1 -> parts (15)
for w, (a, b, c) in [(6, (13, 18, 23)), (9, (13, 18, 23)),
                     (7, (14, 19, 24)), (10, (14, 19, 24)),
                     (8, (15, 20, 25))]:
    holes += [(w, a), (w, b), (w, c)]
# aligned hole-triangles (9)
for (a, b, c) in [(13, 18, 23), (14, 19, 24), (15, 20, 25)]:
    holes += [(a, b), (a, c), (b, c)]
# x cut from isolated P0 vertices (2)
holes += [(4, 6), (5, 6)]

assert len(holes) == len(set(map(lambda e: tuple(sorted(e)), holes))) == 38
with open("/tmp/caseB/witness_construct38.json", "w") as f:
    json.dump({"config": [(0,1),(1,2),(2,3),(0,3)],
               "holes": [tuple(sorted(e)) for e in holes]}, f)
print("wrote witness_construct38.json with", len(holes), "holes")

"""Corrected explicit Case-B H, C4 config, 46 holes (e(H)=229).

  - P0: C4 on 0-1-2-3, isolated 4,5; P1 edge (6,7)
  - cycle class {0,2} -> holes at (11,16,21); class {1,3} -> (12,17,22)
  - every cycle vertex also holed to 9,10  (so U1 = {6,7,8} for all 4 edges)
  - 6 -> (13,18,23), 7 -> (14,19,24), 8 -> (15,20,25)  (aligned, unique)
  - aligned hole-triangles (13,18,23),(14,19,24),(15,20,25)
  - W-triangles (11,16,21),(12,17,22)  (block the xy-system for cycle z)
  - x=6 cut from isolated 4,5          (blocks the xy-system there)
"""
import json

holes = []
for z, (a, b, c) in [(0,(11,16,21)),(2,(11,16,21)),(1,(12,17,22)),(3,(12,17,22))]:
    holes += [(z,a),(z,b),(z,c)]
for z in (0,1,2,3):
    holes += [(z,9),(z,10)]
for w, (a,b,c) in [(6,(13,18,23)),(7,(14,19,24)),(8,(15,20,25))]:
    holes += [(w,a),(w,b),(w,c)]
for (a,b,c) in [(13,18,23),(14,19,24),(15,20,25),(11,16,21),(12,17,22)]:
    holes += [(a,b),(a,c),(b,c)]
holes += [(4,6),(5,6)]

uniq = {tuple(sorted(e)) for e in holes}
assert len(holes) == len(uniq) == 46, (len(holes), len(uniq))
with open("/tmp/caseB/witness_construct46.json","w") as f:
    json.dump({"config": [(0,1),(1,2),(2,3),(0,3)],
               "holes": sorted(uniq)}, f)
print("wrote witness_construct46.json with", len(uniq), "holes")

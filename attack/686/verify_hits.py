#!/usr/bin/env python3
"""Exactly re-verify every HIT line in logs/eq_*.out with exact bignum
arithmetic, and classify admissibility (d >= k)."""
import glob, re
from math import prod

ok = bad = 0
for f in sorted(glob.glob("logs/eq_*.out")):
    for line in open(f):
        m = re.match(r"HIT k=(\d+) N=(\d+) d=(\d+) n=(\d+)", line)
        if not m:
            continue
        k, N, d, n = map(int, m.groups())
        lhs = prod(n + d + i for i in range(1, k + 1))
        rhs = N * prod(n + i for i in range(1, k + 1))
        exact = lhs == rhs
        adm = d >= k
        status = "EXACT" if exact else "FALSE-POSITIVE"
        print(f"{status} k={k} N={N} d={d} n={n} admissible={adm}")
        if exact and adm:
            print("*** ADMISSIBLE SOLUTION — N IS REPRESENTABLE ***")
        ok += exact
        bad += not exact
print(f"verified: {ok} exact, {bad} false positives")

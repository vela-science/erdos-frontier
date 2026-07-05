#!/usr/bin/env python3
"""Counterexample search for the Lean frontier theorem
no_two_lowerCapturedAboveTwo_of_lt:

  forall k>=5, d>=k, x>d:
    NOT ( rough_{>2k}(P_k(d+x)) | Delta_k(d)  AND  rough_{>2k}(P_k(2d+x)) | Delta_k(d) )

where P_k(y) = (y+1)...(y+k), Delta_k(d) = prod_{h=-(k-1)}^{k-1} (d+h).

Since p > 2k exceeds both window lengths (k and 2k-1), at most one factor of
each product is divisible by p.  So
  rough(P_k(y)) | Delta  <=>  for every j in 1..k, every prime power p^e || (y+j)
  with p > 2k divides some d+h, |h| <= k-1.

Per (k,d) we compute a boolean "fine" array over m and then slide windows.

Usage: search_no_two_capture.py KMIN KMAX DMAX XFACTOR
scans k in [KMIN,KMAX], d in [k, DMAX], x in (d, XFACTOR*d + 200].
Prints every (k,d,x) violating the theorem.
"""
import sys
from array import array

def build_spf(limit):
    spf = array('i', range(limit + 1))
    i = 2
    while i * i <= limit:
        if spf[i] == i:
            for j in range(i * i, limit + 1, i):
                if spf[j] == j:
                    spf[j] = i
        i += 1
    return spf

def rough_factor(m, bound, spf):
    """prime powers p^e || m with p > bound, as list of (p, p^e)."""
    out = []
    while m > 1:
        p = spf[m]
        pe = 1
        while m % p == 0:
            m //= p
            pe *= p
        if p > bound:
            out.append((p, pe))
    return out

def main():
    kmin, kmax, dmax, xfac = (int(a) for a in sys.argv[1:5])
    maxm = 2 * dmax + (xfac * dmax + 200) + kmax + 2
    spf = build_spf(maxm)
    # cache rough factorizations per bound value 2k
    found = 0
    for k in range(kmin, kmax + 1):
        bound = 2 * k
        rf = [None] * (maxm + 1)
        for d in range(k, dmax + 1):
            xmax = xfac * d + 200
            window = [d + h for h in range(-(k - 1), k)]
            lo = 2 * d + 2          # smallest m we test: d+x+1 with x=d+1
            hi = 2 * d + xmax + k   # largest: 2d+x+k
            # fine[m] for m in [lo, hi]
            fine = bytearray(hi - lo + 1)
            for m in range(lo, hi + 1):
                r = rf[m]
                if r is None:
                    r = rough_factor(m, bound, spf)
                    rf[m] = r
                ok = True
                for p, pe in r:
                    # unique h in window with p | d+h, if any
                    rem = d % p
                    cand = None
                    if rem <= k - 1:
                        cand = d - rem
                    if p - rem <= k - 1:
                        # both can't happen since p > 2k-1... but be safe
                        c2 = d + (p - rem)
                        if cand is None:
                            cand = c2
                    if cand is None or cand % pe != 0:
                        ok = False
                        break
                fine[m - lo] = 1 if ok else 0
            # run-length of consecutive fine values ending at m
            run = bytearray(hi - lo + 1)
            r = 0
            for i in range(hi - lo + 1):
                r = r + 1 if fine[i] else 0
                run[i] = min(r, 255)
            for x in range(d + 1, xmax + 1):
                if run[d + x + k - lo] >= k and run[2 * d + x + k - lo] >= k:
                    print(f"COUNTEREXAMPLE k={k} d={d} x={x}")
                    found += 1
        print(f"k={k} done (d<={dmax})", file=sys.stderr)
    print(f"total counterexamples: {found}")

if __name__ == "__main__":
    main()

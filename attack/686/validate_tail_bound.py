"""Validate the tail-bound inequality chain: S <= k!*(A+k)^pi(2k), pi(2k)<=k-1."""
import random, math
from sympy import factorint, primepi
random.seed(7)
worst = 0.0
for trial in range(800):
    k = random.randint(5, 16)
    A = random.randint(k, 10**random.randint(2, 9))
    P = 1
    for j in range(1, k+1): P *= A + j
    S = 1
    for p, e in factorint(P).items():
        if p <= 2*k: S *= p**e
    bound = math.factorial(k) * (A + k)**int(primepi(2*k))
    assert S <= bound, (k, A, S, bound)
    worst = max(worst, S/bound)
    assert int(primepi(2*k)) <= k - 1
for k in range(5, 10001):
    assert int(primepi(2*k)) <= k-1
print("800 random (k,A) OK; worst S/bound ratio:", worst)
print("pi(2k) <= k-1 verified for k=5..10000")

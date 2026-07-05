/* sweep_capture.c — counterexample search for the Erdős #686 frontier theorem
 *
 *   no_two_lowerCapturedAboveTwo_of_lt:
 *     forall k>=5, d>=k, x>d:
 *       NOT ( rough_{>2k}(P_k(d+x)) | Delta_k(d)
 *             AND rough_{>2k}(P_k(2d+x)) | Delta_k(d) )
 *
 *   P_k(y) = (y+1)...(y+k),  Delta_k(d) = prod_{h=-(k-1)}^{k-1} (d+h).
 *
 * Since any prime p > 2k exceeds both window lengths, capture of a block is
 * equivalent to: every block element m is "fine", i.e. for each prime power
 * p^e || m with p > 2k there is |h| <= k-1 with p^e | d+h.
 *
 * Per (k,d) we sieve fineness over m in [d+k+2, 3d+XMAX+k]:
 *   residual[m] = m with all p<=2k divided out and, for each window prime
 *   power q = p^e || (d+h) with p > 2k, p divided out at most e times.
 *   fine(m) <=> residual == 1.
 * Then x is a hit iff blocks at d+x and 2d+x are both all-fine.
 *
 * We scan x > k (not just x > d) and label the region, since the broad
 * variant no_two_lowerCapturedAboveTwo (hx : k < x) is also of interest.
 *
 * Usage: sweep_capture k dmin dmax xmax
 * Prints "HIT k=.. d=.. x=.. region=.." for every violation found.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

static int primes_upto(int n, int **out) {
    char *comp = calloc(n + 1, 1);
    int *ps = malloc(sizeof(int) * (n + 1));
    int cnt = 0;
    for (int i = 2; i <= n; i++) {
        if (!comp[i]) {
            ps[cnt++] = i;
            for (long j = (long)i * i; j <= n; j += i) comp[j] = 1;
        }
    }
    free(comp);
    *out = ps;
    return cnt;
}

int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: %s k dmin dmax xmax\n", argv[0]); return 1; }
    int k = atoi(argv[1]);
    long dmin = atol(argv[2]), dmax = atol(argv[3]), xmax = atol(argv[4]);
    int bound = 2 * k;
    int *small_primes; int n_small = primes_upto(bound, &small_primes);

    long hits = 0;
    for (long d = dmin; d <= dmax; d++) {
        long lo = d + k + 2;              /* smallest block element: d+x+1, x=k+1 */
        long hi = 2 * d + xmax + k;       /* largest: 2d+x+k */
        long M = hi - lo + 1;
        uint64_t *res = malloc(sizeof(uint64_t) * M);
        if (!res) { fprintf(stderr, "alloc fail d=%ld\n", d); return 2; }
        for (long i = 0; i < M; i++) res[i] = (uint64_t)(lo + i);

        /* divide out small primes completely */
        for (int t = 0; t < n_small; t++) {
            long p = small_primes[t];
            long start = ((lo + p - 1) / p) * p;
            for (long m = start; m <= hi; m += p) {
                uint64_t *r = &res[m - lo];
                while (*r % p == 0) *r /= p;
            }
        }
        /* window prime powers: factor d+h for |h|<=k-1, primes > 2k */
        for (long h = -(k - 1); h <= k - 1; h++) {
            long w = d + h;
            if (w <= 1) continue;
            /* factor w: strip small primes first */
            long v = w;
            for (int t = 0; t < n_small && (long)small_primes[t] * small_primes[t] <= v; t++) {
                long p = small_primes[t];
                while (v % p == 0) v /= p;
            }
            /* remaining v has all prime factors > 2k (or v == 1);
               trial-divide v by odd numbers > 2k */
            for (long p = bound + 1; p * p <= v; p++) {
                if (v % p) continue;
                int e = 0; while (v % p == 0) { v /= p; e++; }
                /* divide res at multiples of p by p, at most e times each */
                long start = ((lo + p - 1) / p) * p;
                for (long m = start; m <= hi; m += p) {
                    uint64_t *r = &res[m - lo];
                    int c = 0;
                    while (c < e && *r % p == 0) { *r /= p; c++; }
                }
            }
            if (v > bound) { /* v itself is prime > 2k (e = full valuation of w at v) */
                long p = v;
                /* exponent of p in w */
                int e = 0; long ww = w; while (ww % p == 0) { ww /= p; e++; }
                long start = ((lo + p - 1) / p) * p;
                for (long m = start; m <= hi; m += p) {
                    uint64_t *r = &res[m - lo];
                    int c = 0;
                    while (c < e && *r % p == 0) { *r /= p; c++; }
                }
            }
        }
        /* run lengths of consecutive fine */
        /* reuse res as fine flags via second pass with run counter */
        int run = 0;
        /* store run length capped at 255 in a byte array */
        unsigned char *rl = malloc(M);
        for (long i = 0; i < M; i++) {
            run = (res[i] == 1) ? run + 1 : 0;
            rl[i] = (unsigned char)(run > 255 ? 255 : run);
        }
        for (long x = k + 1; x <= xmax; x++) {
            long b1 = d + x + k, b2 = 2 * d + x + k;
            if (rl[b1 - lo] >= k && rl[b2 - lo] >= k) {
                printf("HIT k=%d d=%ld x=%ld region=%s\n", k, d, x,
                       x > d ? "d<x" : "k<x<=d");
                fflush(stdout);
                hits++;
            }
        }
        free(rl);
        free(res);
        if (d % 500 == 0) fprintf(stderr, "k=%d d=%ld done\n", k, d);
    }
    fprintf(stderr, "k=%d dmin=%ld dmax=%ld xmax=%ld hits=%ld\n", k, dmin, dmax, xmax, hits);
    return 0;
}

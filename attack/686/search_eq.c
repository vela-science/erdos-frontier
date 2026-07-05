/* search_eq.c — direct equation sweep for Erdős #686 cells.
 *
 * Searches P_k(n+d) = N * P_k(n), P_k(y) = (y+1)...(y+k), over all d in
 * [dmin, dmax] and ALL admissible n, using the squeeze
 *
 *   (1 + d/(n+k))^k <= N <= (1 + d/(n+1))^k
 *     ==>  n+1 <= d/theta <= n+k,   theta = N^(1/k) - 1,
 *
 * which pins n to a window of k integers around d/theta. We scan the
 * window [d/theta - k - 2, d/theta + 2] (slop covers all float error).
 *
 * Equality is tested modulo the Mersenne prime 2^61 - 1 (fast folding
 * reduction); hits are printed and must be re-verified exactly (they are
 * expected only for the inadmissible overlap families d < k, e.g.
 * d=1, n=(k-3)/3 for N=4 when 3 | k-3).
 *
 * Usage: search_eq k N dmin dmax
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>

#define M61 2305843009213693951ULL  /* 2^61 - 1, prime */

static inline uint64_t mod61(unsigned __int128 x) {
    uint64_t r = (uint64_t)(x & M61) + (uint64_t)(x >> 61);
    if (r >= M61) r -= M61;
    return r;
}
static inline uint64_t mulmod61(uint64_t a, uint64_t b) {
    return mod61((unsigned __int128)a * b);
}

int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: %s k N dmin dmax\n", argv[0]); return 1; }
    int k = atoi(argv[1]);
    uint64_t N = strtoull(argv[2], 0, 10);
    uint64_t dmin = strtoull(argv[3], 0, 10), dmax = strtoull(argv[4], 0, 10);
    long double theta = powl((long double)N, 1.0L / k) - 1.0L;
    long double inv = 1.0L / theta;
    uint64_t hits = 0;
    for (uint64_t d = dmin; d <= dmax; d++) {
        long double bf = (long double)d * inv;
        int64_t base = (int64_t)bf;
        int64_t nlo = base - k - 2; if (nlo < 0) nlo = 0;
        int64_t nhi = base + 2;
        for (int64_t n = nlo; n <= nhi; n++) {
            uint64_t lhs = 1, rhs = N % M61;
            for (int i = 1; i <= k; i++) {
                lhs = mulmod61(lhs, (uint64_t)(n + d + i) % M61);
                rhs = mulmod61(rhs, (uint64_t)(n + i) % M61);
            }
            if (lhs == rhs) {
                printf("HIT k=%d N=%llu d=%llu n=%lld %s\n", k,
                       (unsigned long long)N, (unsigned long long)d,
                       (long long)n, d < (uint64_t)k ? "(overlap-region)" : "(ADMISSIBLE!)");
                fflush(stdout);
                hits++;
            }
        }
        if ((d & 0xFFFFFFF) == 0 && d > dmin)
            fprintf(stderr, "k=%d N=%llu progress d=%llu\n", k,
                    (unsigned long long)N, (unsigned long long)d);
    }
    fprintf(stderr, "DONE k=%d N=%llu dmin=%llu dmax=%llu hits=%llu\n",
            k, (unsigned long long)N, (unsigned long long)dmin,
            (unsigned long long)dmax, (unsigned long long)hits);
    return 0;
}

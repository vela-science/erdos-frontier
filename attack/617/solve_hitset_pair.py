#!/usr/bin/env python3
"""Erdos #617, r=5 route: decide the pass-20 'hitset-pair' finite problem.

Spec (section 6 of the pass-20 notes). Find or rule out a graph B on 19
vertices with:
  (L1) e(B) = 40
  (L2) Delta(B) <= 6
  (L3) alpha(B) <= 4                      (== complement K5-free)
  (L4) e_B(S) <= 11 for every 6-set S
  (L5) complement(B) is K5-saturated      (adding any edge to ~B makes a K5)
  (L6) complement(B) is NOT 4-partite     (V(B) has no partition into 4 B-cliques)
  (L7) tau_4(B) = 4                       (min vertex set hitting all independent
                                           4-sets has size exactly 4)
and at least one of:
  Case I : exist disjoint P,Q in V(B), |P|=4, |Q|=5, each of P,Q hits every
           independent 4-set of B, P u Q hits every independent 3-set of B,
           and e_B(Q) <= 6.
  Case II: exist P,Q in V(B), |P|=|Q|=4, each hits every independent 4-set,
           e_B(P)+|P n Q| <= 6 and e_B(Q)+|P n Q| <= 6.

WLOG (all of L1-L7 are invariant under vertex relabelling) P and Q are placed
canonically; Case II is split into sub-cases by k=|P n Q|.

Method: core constraints are encoded eagerly in CNF; (L4), (L5), the lower
half of (L7) (tau_4 >= 4) and (L6) are enforced lazily (CEGAR): each witness
is checked, and violated instances are added as new hard constraints, all of
which are *sound* (they are implied by the spec for every B).  The loop ends
with either UNSAT (no B exists for that case) or a witness satisfying the
entire spec, which is then re-verified by the independent checker
check_witness.py.

Note tau_4 <= 4 is implied by the Case conditions (P itself is a hitting
4-set), so (L7) reduces to tau_4 >= 4.
"""
import itertools, json, sys, time
from pysat.card import CardEnc, EncType, ITotalizer
from pysat.formula import IDPool
from pysat.solvers import Cadical195

N = 19
VS = list(range(N))
PAIRS = list(itertools.combinations(VS, 2))


def pairs_in(S):
    return itertools.combinations(sorted(S), 2)


class Instance:
    def __init__(self, name, P, Q, hit3=False, ePmax=None, eQmax=None,
                 use_cuts=True, restrict_T=True):
        self.name, self.P, self.Q = name, set(P), set(Q)
        self.use_cuts, self.restrict_T = use_cuts, restrict_T
        self.pool = IDPool()
        self.evars = {}
        for (i, j) in PAIRS:
            self.evars[(i, j)] = self.pool.id(('e', i, j))
        self.solver = Cadical195()
        self.nclauses = 0
        self.all_clauses = []
        # --- core constraints ---
        # (L1) e(B) = 40
        self._card(list(self.evars.values()), 40, equals=True)
        # (L2) degrees <= 6
        for v in VS:
            self._card([self.ev(v, u) for u in VS if u != v], 6)
        # (L3) alpha <= 4: every 5-set contains an edge
        for S in itertools.combinations(VS, 5):
            self._clause([self.ev(i, j) for (i, j) in pairs_in(S)])
        # P hits all independent 4-sets: 4-sets disjoint from P have an edge
        for S in itertools.combinations([v for v in VS if v not in self.P], 4):
            self._clause([self.ev(i, j) for (i, j) in pairs_in(S)])
        # Q likewise
        for S in itertools.combinations([v for v in VS if v not in self.Q], 4):
            self._clause([self.ev(i, j) for (i, j) in pairs_in(S)])
        if hit3:  # P u Q hits all independent 3-sets (Case I only)
            R = [v for v in VS if v not in self.P and v not in self.Q]
            for S in itertools.combinations(R, 3):
                self._clause([self.ev(i, j) for (i, j) in pairs_in(S)])
        if ePmax is not None:
            self._card([self.ev(i, j) for (i, j) in pairs_in(self.P)], ePmax)
        if eQmax is not None:
            self._card([self.ev(i, j) for (i, j) in pairs_in(self.Q)], eQmax)
        # Structural cuts, each implied by the spec (proofs in
        # case1_structure.md / NOTES.md):
        #  - hitting conditions mean alpha(B-P) <= 3, alpha(B-Q) <= 3 and
        #    (Case I) alpha(R) <= 2; Turan complements give edge lower
        #    bounds on those vertex sets, sharpened by Lemmas 1-2 in Case I.
        notP = [v for v in VS if v not in self.P]
        notQ = [v for v in VS if v not in self.Q]
        litsP = [self.ev(i, j) for (i, j) in pairs_in(notP)]   # edges of B-P
        litsQ = [self.ev(i, j) for (i, j) in pairs_in(notQ)]   # edges of B-Q
        if not use_cuts:
            pass
        elif hit3:  # Case I: |B-P|=15, |B-Q|=14, |R|=10
            self._card(litsP, 31, atleast=True)   # Lemma 1
            self._card(litsQ, 27, atleast=True)   # Lemma 2
            R = [v for v in VS if v not in self.P and v not in self.Q]
            self._card([self.ev(i, j) for (i, j) in pairs_in(R)], 20,
                       atleast=True)              # Turan, alpha(R)<=2
        else:     # Case II: |B-P|=|B-Q|=15
            self._card(litsP, 31, atleast=True)   # Lemma 3
            self._card(litsQ, 31, atleast=True)   # Lemma 3
        # (L5) eager K5-saturation of ~B: for every pair u<v, if uv is a
        # B-edge there is a 3-set T with all 9 pairs of (T u {u,v}) \ {uv}
        # non-edges of B.  Sound T-range restriction: any valid T makes
        # T u {u} and T u {v} independent 4-sets, which P and Q must hit;
        # hence T meets P unless u,v are both in P, and likewise for Q.
        for (u, v) in PAIRS:
            others = [w for w in VS if w != u and w != v]
            needP = restrict_T and not (u in self.P and v in self.P)
            needQ = restrict_T and not (u in self.Q and v in self.Q)
            disj = [-self.ev(u, v)]
            for T in itertools.combinations(others, 3):
                ts = set(T)
                if (needP and not ts & self.P) or (needQ and not ts & self.Q):
                    continue
                t = self.pool.id(('sat', u, v, T))
                disj.append(t)
                for (a, b) in pairs_in(T):
                    self._clause([-t, -self.ev(a, b)])
                for w in T:
                    self._clause([-t, -self.ev(u, w)])
                    self._clause([-t, -self.ev(v, w)])
            self._clause(disj)
        # (L7 lower half) eager tau_4 >= 4: for every 3-set H there is an
        # independent 4-set avoiding H.  Aux i_S -> S independent.
        for S4 in itertools.combinations(VS, 4):
            i_s = self.pool.id(('i4', S4))
            for (a, b) in pairs_in(S4):
                self._clause([-i_s, -self.ev(a, b)])
        for H in itertools.combinations(VS, 3):
            hs = set(H)
            self._clause([self.pool.id(('i4', S4))
                          for S4 in itertools.combinations(
                              [v for v in VS if v not in hs], 4)])
        # Symmetry breaking (sound): every constraint family here — and
        # every lazy clause added later — is implied by the spec for all
        # graphs, and the spec itself is invariant under permutations
        # fixing P and Q setwise.  The interchangeable classes are P&Q,
        # P-Q, Q-P and the rest.  For each adjacent pair u<w inside a
        # class we require A[u] <=_lex A[w] over the common columns
        # (lex-leader w.r.t. adjacent transpositions): every orbit of
        # spec-models keeps at least one representative.
        classes = [sorted(self.P & self.Q), sorted(self.P - self.Q),
                   sorted(self.Q - self.P),
                   sorted(set(VS) - self.P - self.Q)]
        for cls in classes:
            for (u, w) in zip(cls, cls[1:]):
                cols = [t for t in VS if t != u and t != w]
                # e_i: rows equal on the first i+1 columns
                prev = None
                for i, t in enumerate(cols):
                    xu, xw = self.ev(u, t), self.ev(w, t)
                    if prev is None:
                        self._clause([-xu, xw])  # first col: u<=w
                        e = self.pool.id(('lex', u, w, i))
                        # e0 <- (xu = xw)
                        self._clause([xu, xw, e])
                        self._clause([-xu, -xw, e])
                        # e0 -> (xu = xw)
                        self._clause([-e, xu, -xw])
                        self._clause([-e, -xu, xw])
                    else:
                        self._clause([-prev, -xu, xw])  # equal so far: u<=w
                        if i == len(cols) - 1:
                            break  # no need for the last equality var
                        e = self.pool.id(('lex', u, w, i))
                        # e <- prev & (xu = xw)
                        self._clause([-prev, xu, xw, e])
                        self._clause([-prev, -xu, -xw, e])
                        # e -> prev & (xu = xw)
                        self._clause([-e, prev])
                        self._clause([-e, xu, -xw])
                        self._clause([-e, -xu, xw])
                    prev = e
        # lazy-constraint bookkeeping
        self.sixsets_added = set()
        self.sat_edges_added = set()
        self.tau4_hitsets_added = set()
        self.cover_blocks = 0

    def ev(self, i, j):
        return self.evars[(min(i, j), max(i, j))]

    def _clause(self, cl):
        self.solver.add_clause(cl)
        self.all_clauses.append(cl)
        self.nclauses += 1

    def dump_dimacs(self, path):
        with open(path, 'w') as f:
            f.write(f"p cnf {self.pool.top} {len(self.all_clauses)}\n")
            for cl in self.all_clauses:
                f.write(' '.join(map(str, cl)) + ' 0\n')

    def _card(self, lits, bound, equals=False, atleast=False):
        if equals:
            f, enc = CardEnc.equals, EncType.totalizer
        elif atleast:
            f, enc = CardEnc.atleast, EncType.seqcounter
        else:
            f, enc = CardEnc.atmost, EncType.seqcounter
        cnf = f(lits=lits, bound=bound, vpool=self.pool, encoding=enc)
        for cl in cnf.clauses:
            self._clause(cl)

    # ---------- witness extraction ----------
    def model_graph(self):
        model = self.solver.get_model()
        pos = set(l for l in model if l > 0)
        adj = [[False] * N for _ in range(N)]
        E = set()
        for (i, j) in PAIRS:
            if self.evars[(i, j)] in pos:
                adj[i][j] = adj[j][i] = True
                E.add((i, j))
        return adj, E

    # ---------- lazy checks; each returns #constraints added ----------
    def lazy_sixsets(self, adj):
        added = 0
        for S in itertools.combinations(VS, 6):
            if S in self.sixsets_added:
                continue
            m = sum(adj[i][j] for (i, j) in pairs_in(S))
            if m > 11:
                # (L4): at most 11 of the 15 pair-variables of S are true
                self._card([self.ev(i, j) for (i, j) in pairs_in(S)], 11)
                self.sixsets_added.add(S)
                added += 1
                if added >= 400:
                    break
        return added

    def lazy_saturation(self, adj, E):
        """(L5) ~B is K5-saturated: for every B-edge uv there must exist a
        3-set T with all 9 pairs inside (T u {u,v}) except uv being non-edges
        of B.  For each violated (u,v), add the (sound, global) constraint
        x_uv -> OR_T t_uvT,  t_uvT -> the 9 pairs are non-edges."""
        added = 0
        for (u, v) in E:
            if (u, v) in self.sat_edges_added:
                continue
            ok = False
            others = [w for w in VS if w != u and w != v]
            for T in itertools.combinations(others, 3):
                if (not any(adj[a][b] for (a, b) in pairs_in(T))
                        and not any(adj[u][w] or adj[v][w] for w in T)):
                    ok = True
                    break
            if ok:
                continue
            # violated: encode the existential for this pair
            disj = [-self.ev(u, v)]
            for T in itertools.combinations(others, 3):
                t = self.pool.id(('sat', u, v, T))
                disj.append(t)
                for (a, b) in pairs_in(T):
                    self._clause([-t, -self.ev(a, b)])
                for w in T:
                    self._clause([-t, -self.ev(u, w)])
                    self._clause([-t, -self.ev(v, w)])
            self._clause(disj)
            self.sat_edges_added.add((u, v))
            added += 1
            if added >= 30:
                break
        return added

    def lazy_tau4(self, adj):
        """(L7 lower half) tau_4(B) >= 4: no 3-set hits every independent
        4-set.  If the witness has a hitting 3-set H, add: there exists an
        independent 4-set inside V \ H."""
        ind4 = [S for S in itertools.combinations(VS, 4)
                if not any(adj[i][j] for (i, j) in pairs_in(S))]
        for H in itertools.combinations(VS, 3):
            if H in self.tau4_hitsets_added:
                continue
            hs = set(H)
            if all(hs & set(S) for S in ind4):
                disj = []
                for S in itertools.combinations([v for v in VS if v not in hs], 4):
                    s = self.pool.id(('t4', H, S))
                    disj.append(s)
                    for (a, b) in pairs_in(S):
                        self._clause([-s, -self.ev(a, b)])
                self._clause(disj)
                self.tau4_hitsets_added.add(H)
                return 1
        return 0

    def lazy_nonfourpartite(self, adj):
        """(L6) ~B not 4-partite, i.e. V(B) has no partition into <=4
        B-cliques.  If the witness complement is 4-colourable, block that
        specific partition: it must contain at least one B-non-edge."""
        part = four_clique_cover(adj)
        if part is None:
            return 0
        cl = []
        for cls in part:
            for (a, b) in pairs_in(cls):
                cl.append(-self.ev(a, b))
        self._clause(cl)
        self.cover_blocks += 1
        return 1


def four_clique_cover(adj):
    """Partition of VS into <=4 cliques of B (== 4-colouring of ~B), or None.
    Simple backtracking, vertices in decreasing ~B-degree order."""
    order = sorted(VS, key=lambda v: sum(not adj[v][u] for u in VS if u != v),
                   reverse=True)
    parts = [[] for _ in range(4)]

    def bt(idx):
        if idx == N:
            return True
        v = order[idx]
        used = 0
        for p in parts:
            if not p:
                if used:
                    return False  # symmetry: only one empty part tried
                used = 1
            if all(adj[v][u] for u in p):
                p.append(v)
                if bt(idx + 1):
                    return True
                p.pop()
        return False

    return [list(p) for p in parts] if bt(0) else None


def run_case(name, P, Q, hit3, ePmax, eQmax, log, use_cuts=True,
             restrict_T=True):
    t0 = time.time()
    inst = Instance(name, P, Q, hit3=hit3, ePmax=ePmax, eQmax=eQmax,
                    use_cuts=use_cuts, restrict_T=restrict_T)
    log(f"[{name}] P={sorted(P)} Q={sorted(Q)} hit3={hit3} "
        f"ePmax={ePmax} eQmax={eQmax} cuts={use_cuts} rT={restrict_T} "
        f"core_clauses={inst.nclauses}")
    it = 0
    while True:
        it += 1
        if not inst.solver.solve():
            log(f"[{name}] UNSAT after {it} solver calls, "
                f"{inst.nclauses} clauses, {time.time()-t0:.1f}s "
                f"(lazy: six={len(inst.sixsets_added)} "
                f"sat={len(inst.sat_edges_added)} "
                f"tau4={len(inst.tau4_hitsets_added)} cover={inst.cover_blocks})")
            tag = ('' if use_cuts else '_nocuts') + \
                  ('' if restrict_T else '_fullT')
            inst.dump_dimacs(f'artifacts/final_{name}{tag}.cnf')
            log(f"[{name}] final CNF dumped to artifacts/final_{name}{tag}.cnf")
            return ('UNSAT', None, inst)
        adj, E = inst.model_graph()
        a = inst.lazy_sixsets(adj)
        b = inst.lazy_saturation(adj, E)
        c = inst.lazy_tau4(adj)
        d = inst.lazy_nonfourpartite(adj)
        if a + b + c + d == 0:
            log(f"[{name}] WITNESS found after {it} solver calls, "
                f"{time.time()-t0:.1f}s — full spec satisfied")
            return ('SAT', sorted(E), inst)
        if it % 10 == 0:
            log(f"[{name}] iter {it}: +six {a} +sat {b} +tau4 {c} +cover {d} "
                f"clauses={inst.nclauses} t={time.time()-t0:.1f}s")


def main():
    logf = open('artifacts/solve_log.txt', 'a')

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        print(line, file=logf, flush=True)

    results = {}
    only = sys.argv[1] if len(sys.argv) > 1 else None
    use_cuts = 'nocuts' not in sys.argv
    restrict_T = 'fullT' not in sys.argv
    suffix = ('' if use_cuts else '_nocuts') + ('' if restrict_T else '_fullT')

    cases = []
    # Case I: P,Q disjoint, |P|=4,|Q|=5, hit3 over the remaining 10, e(Q)<=6
    cases.append(('I', list(range(4)), list(range(4, 9)), True, None, 6))
    # Case II, k = |P n Q| in 0..4: P={0..3}, Q = {0..k-1} u {4..7-k}
    for k in range(5):
        Q = list(range(k)) + list(range(4, 8 - k))
        cases.append((f'II.k{k}', list(range(4)), Q, False, 6 - k, 6 - k))

    for (name, P, Q, hit3, ePmax, eQmax) in cases:
        if only and name != only:
            continue
        verdict, witness, inst = run_case(name, P, Q, hit3, ePmax, eQmax, log,
                                          use_cuts=use_cuts,
                                          restrict_T=restrict_T)
        results[name] = {'verdict': verdict, 'witness': witness,
                         'P': sorted(P), 'Q': sorted(Q),
                         'use_cuts': use_cuts, 'restrict_T': restrict_T}
        with open(f'artifacts/result_{name}{suffix}.json', 'w') as f:
            json.dump(results[name], f, indent=1)
    log(f"SUMMARY {json.dumps({k: v['verdict'] for k, v in results.items()})}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Assemble the final results table for the hitset-pair problem from
artifacts/ (result JSONs + solve log timings + certification logs)."""
import glob, json, os, re

os.chdir(os.path.dirname(os.path.abspath(__file__)))
rows = {}
for p in sorted(glob.glob('artifacts/result_*.json')):
    base = os.path.basename(p)[len('result_'):-len('.json')]
    if base.startswith('cpsat_'):
        continue
    d = json.load(open(p))
    case = base.split('_')[0]
    variant = base[len(case):].strip('_') or 'main'
    rows.setdefault(case, {})[variant] = d['verdict']

# timings from log: map (case, cuts, rT) -> seconds
times = {}
log = open('artifacts/solve_log.txt').read()
cur = {}
for m in re.finditer(r'\[([A-Za-z.0-9]+)\] (?:P=.*?cuts=(\w+) rT=(\w+) '
                     r'core_clauses|P=.*?core_clauses|'
                     r'UNSAT after 1 solver calls, \d+ clauses, ([0-9.]+)s)',
                     log):
    case = m.group(1)
    if m.group(4) is None:
        if m.group(2) is None:
            cur[case] = 'main'  # pre-flag log format: cuts+restricted-T
        else:
            cur[case] = ('main' if m.group(2) == 'True' and
                         m.group(3) == 'True'
                         else 'nocuts' if m.group(3) == 'True'
                         else 'fullT' if m.group(2) == 'True'
                         else 'nocuts_fullT')
    elif case in cur and (case, cur[case]) not in times:
        times[(case, cur[case])] = float(m.group(4))

cpsat = {}
for p in sorted(glob.glob('artifacts/result_cpsat_*.json')):
    d = json.load(open(p))
    case = os.path.basename(p)[len('result_cpsat_'):-len('.json')]
    cpsat[case] = d['verdict']

certs = {}
if os.path.exists('artifacts/certs_summary.txt'):
    for line in open('artifacts/certs_summary.txt'):
        parts = line.split()
        if len(parts) >= 2:
            certs[parts[0]] = parts[1]

print(f"{'case':8} {'main':>14} {'nocuts':>10} {'fullT':>10} "
      f"{'pure':>10} {'cp-sat':>8} {'drat':>9}")
for case in ['I', 'II.k0', 'II.k1', 'II.k2', 'II.k3', 'II.k4']:
    r = rows.get(case, {})
    def cell(v):
        verdict = r.get(v, '-')
        t = times.get((case, v))
        return f"{verdict}{f'({t:.0f}s)' if t and verdict != '-' else ''}"
    print(f"{case:8} {cell('main'):>14} {cell('nocuts'):>10} "
          f"{cell('fullT'):>10} {cell('nocuts_fullT'):>10} "
          f"{cpsat.get(case, '-'):>8} {certs.get(case, '-'):>9}")

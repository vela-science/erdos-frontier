#!/bin/zsh
# Queue: after the running odd-k sweeps finish, sweep the outstanding even-k
# N=4 cells over their dichotomy boxes (n-box converted to d-box via
# d = theta_k * n_box, theta_k = 4^(1/k)-1, rounded up generously):
#   k=18: n <= 6e11  -> d <= 5.0e10
#   k=32: n <= 2.3e11 -> d <= 1.1e10
#   k=36: n <= 3e11  -> d <= 1.3e10
# Box values are from the pass-6 consolidated report (T1 thresholds); the
# sweep is labeled as conditional on those box derivations.
cd "$(dirname "$0")"
while pgrep -f search_eq > /dev/null; do sleep 120; done

run_chunks() {
  local k=$1 N=$2 dmax=$3 P=$4
  local step=$((dmax / P))
  local i lo hi
  for i in $(seq 0 $((P-1))); do
    lo=$((i*step+1)); if [ $i -eq $((P-1)) ]; then hi=$dmax; else hi=$(((i+1)*step)); fi
    ( ./search_eq $k $N $lo $hi >> logs/eq_k${k}_N${N}.out 2>> logs/eq_k${k}_N${N}.err ) &
  done
  wait
}

run_chunks 18 4 50000000000 6
run_chunks 32 4 11000000000 6
run_chunks 36 4 13000000000 6
date > logs/even_cells.done

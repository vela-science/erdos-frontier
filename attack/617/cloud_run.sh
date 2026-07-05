#!/usr/bin/env bash
# Erdős #617 — offload the solver-bound runs to a GCP VM (project epst-platform-dev).
#
# Usage:  ./cloud_run.sh up      create VM, push scripts, launch all runs
#         ./cloud_run.sh poll    tail the run logs
#         ./cloud_run.sh fetch   pull artifacts back into ./artifacts/cloud/
#         ./cloud_run.sh down    delete the VM (also auto-deletes after 24h)
#
# Runs launched on the VM (52 workers total, sized for c2-standard-60):
#   mstar_decision65  probe_mstar.py 86400 40 65    the fork question, 24h budget
#   z2-12             search_group_invariant.py z2-12 86400
#   z2-13             search_group_invariant.py z2-13 86400
#   z3-5              search_group_invariant.py z3-5 43200
# Local Mac keeps: 1094 enumeration, 993 sweeps, interactive work.
set -euo pipefail
cd "$(dirname "$0")"

NAME=erdos-solver-1
ZONE=us-east4-a
PROJECT=epst-platform-dev
GC="gcloud --project=$PROJECT compute"

up() {
  for MT in c2-standard-60 n2-highcpu-48 n2-highcpu-32 e2-highcpu-16; do
    echo ">> trying machine type $MT"
    if $GC instances create $NAME --zone=$ZONE --machine-type=$MT \
        --image-family=debian-12 --image-project=debian-cloud \
        --boot-disk-size=40GB \
        --max-run-duration=24h --instance-termination-action=DELETE \
        --labels=purpose=erdos,owner=wblair 2>/dev/null; then
      echo ">> created $NAME ($MT)"; break
    fi
  done
  $GC instances describe $NAME --zone=$ZONE --format='value(status)' >/dev/null
  echo ">> waiting for ssh"; sleep 25
  $GC ssh $NAME --zone=$ZONE --command='sudo apt-get -qq update && sudo apt-get -qq install -y python3-pip >/dev/null && pip3 install -q --break-system-packages ortools python-sat 2>&1 | tail -1 && mkdir -p ~/erdos/artifacts'
  $GC scp probe_mstar.py check_mstar_witness.py search_group_invariant.py \
      $NAME:~/erdos/ --zone=$ZONE
  # NB: plain "cd X && job &" backgrounds the whole group as a subshell and
  # later jobs run from $HOME — keep the cd separated by ";" and one line.
  $GC ssh $NAME --zone=$ZONE --command='cd ~/erdos; nohup python3 probe_mstar.py 86400 22 65 > artifacts/mstar_decision65.log 2>&1 < /dev/null & nohup python3 search_group_invariant.py z2-12 86400 > artifacts/z2-12.log 2>&1 < /dev/null & nohup python3 search_group_invariant.py z2-13 86400 > artifacts/z2-13.log 2>&1 < /dev/null & nohup python3 search_group_invariant.py z3-5 43200 > artifacts/z3-5.log 2>&1 < /dev/null & sleep 3; pgrep -af "probe_mstar|search_group"'
  echo ">> all runs launched.  ./cloud_run.sh poll  to watch."
}

poll()  { $GC ssh $NAME --zone=$ZONE --command='tail -n 4 ~/erdos/artifacts/*.log'; }
fetch() { mkdir -p artifacts/cloud && $GC scp --recurse $NAME:~/erdos/artifacts/ artifacts/cloud/ --zone=$ZONE && ls -la artifacts/cloud/artifacts/; }
down()  { $GC instances delete $NAME --zone=$ZONE --quiet; }

"${1:-up}"

S=/mnt/c/Users/jjzzw/AppData/Local/Temp/claude/c--Users-jjzzw-Desktop-AGI/67483bff-ccd7-4a64-87c0-e3cc020f3969/scratchpad
LOG=$S/t2_fresh.log
C=~/t2-successor
export PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/mpl CUDA_VISIBLE_DEVICES=
export EVIDENCE_MEMORY_TOKENIZER=/mnt/c/Users/jjzzw/Desktop/AGI/.cache/phase4-tokenizer
rm -rf $C && git clone -q --no-local --branch track2-successor-runtime-v1 /mnt/c/Users/jjzzw/Desktop/AGI $C || { echo "clone failed" > $LOG; exit 1; }
cd $C
git fetch -q /mnt/c/Users/jjzzw/Desktop/AGI refs/remotes/origin/wheelhouse-replacement-audit 2>/dev/null
echo "clone at $(git rev-parse HEAD); basis object: $(git cat-file -t 5a21dd339d22ec6e13307722b42dcef0882f6829 2>&1); baseline: $(git cat-file -t 107d8b4 2>&1); load $(cat /proc/loadavg)" > $LOG
echo "== builder check" >> $LOG
/usr/bin/python3 scripts/build_evidence_memory_v1_sessions.py --check >> $LOG 2>&1; echo "builder exit $?" >> $LOG
echo "== token cross-check (transformers) reproduces the committed audits" >> $LOG
/home/jingjing/.local/share/agi/tok-env-4576/bin/python scripts/audit_evidence_memory_v1_tokens.py > /tmp/t2-audit.out 2>&1; echo "audit exit $?" >> $LOG
git status --short >> $LOG; git diff --stat >> $LOG
echo "== review checks" >> $LOG
for s in a b; do /usr/bin/python3 scripts/evidence_memory_v1_session_${s}_package.py review-check --revision 1 >> $LOG 2>&1; echo "review-check $s exit $?" >> $LOG; /usr/bin/python3 scripts/evidence_memory_v1_session_${s}_package.py launch-build >> $LOG 2>&1; echo "launch-build $s exit $? (must be 1)" >> $LOG; done
git checkout -q -- reports
echo "== successor group" >> $LOG
/usr/bin/python3 scripts/run_evidence_memory_v1_successor_checks.py --group successor --out /tmp/t2-cpu/cpu_checks_successor.json >> $LOG 2>&1; echo "successor exit $?" >> $LOG
echo "== track2 group" >> $LOG
/home/jingjing/.local/share/agi/dev-env/bin/python scripts/run_evidence_memory_v1_successor_checks.py --group track2 --out /tmp/t2-cpu/cpu_checks_track2.json >> $LOG 2>&1; echo "track2 exit $?" >> $LOG
mkdir -p $S/t2-cpu && cp /tmp/t2-cpu/* $S/t2-cpu/
echo "DONE $(date) load $(cat /proc/loadavg)" >> $LOG

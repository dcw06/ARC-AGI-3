S=/mnt/c/Users/jjzzw/Desktop/AGI/.cache/t2r5/fresh
LOG=$S/fresh_clone_run_r5.log
C=~/v-t2r5
DEV=/home/jingjing/.local/share/agi/dev-env/bin/python
TOK=/home/jingjing/.local/share/agi/tok-env-4576/bin/python
VLLM=/home/jingjing/t1-run/install-check/model/venv/bin/python
ISOLATE="unshare --user --map-root-user --net sh -c 'ip link set lo up && exec \"\$@\"' sh"
iso() { unshare --user --map-root-user --net sh -c 'ip link set lo up && exec "$@"' sh "$@"; }
export PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/mpl CUDA_VISIBLE_DEVICES= HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
export EVIDENCE_MEMORY_TOKENIZER=/mnt/c/Users/jjzzw/Desktop/AGI/.cache/phase4-tokenizer
mkdir -p $S /tmp/t2r5-cpu && rm -rf $S/out && mkdir -p $S/out
rm -rf $C && git clone -q --no-local --branch track2-successor-runtime-v1 /mnt/c/Users/jjzzw/Desktop/AGI $C || { echo "clone failed" > $LOG; exit 1; }
cd $C
git fetch -q /mnt/c/Users/jjzzw/Desktop/AGI refs/remotes/origin/wheelhouse-replacement-audit 2>/dev/null
echo "clone at $(git rev-parse HEAD); basis object: $(git cat-file -t 5a21dd339d22ec6e13307722b42dcef0882f6829 2>&1); baseline: $(git cat-file -t 107d8b4 2>&1); r1 audits: $(git cat-file -t fb8cf77 2>&1); load $(cat /proc/loadavg)" > $LOG
echo "network isolation: every check below runs under: $ISOLATE (loopback only)" >> $LOG
echo "== builder check" >> $LOG
iso /usr/bin/python3 scripts/build_evidence_memory_v1_sessions.py --check >> $LOG 2>&1; echo "builder exit $?" >> $LOG
echo "== structured-output check r3 (dump: dev env; check: vLLM 0.19.0 interpreter, CPU) reproduces the committed receipt" >> $LOG
iso $DEV scripts/check_evidence_memory_v1_structured_outputs.py dump --out /tmp/t2r5-schemas.json >> $LOG 2>&1; echo "dump exit $?" >> $LOG
iso $VLLM scripts/check_evidence_memory_v1_structured_outputs.py check --schemas /tmp/t2r5-schemas.json \
    --tokenizer $EVIDENCE_MEMORY_TOKENIZER --out reports/evidence_memory_v1_successor/structured_outputs_check_r3.json \
    >> $LOG 2>/tmp/t2r5-so.stderr; echo "check exit $?" >> $LOG
echo "== token cross-check (transformers 4.57.6) reproduces the committed audits and the r3 report" >> $LOG
iso $TOK scripts/audit_evidence_memory_v1_tokens.py > /tmp/t2r5-audit.out 2>&1; echo "audit exit $?" >> $LOG
echo "== prompt token counts against the r4 audits (2d0aa6b)" >> $LOG
iso $DEV scripts/compare_evidence_memory_v1_token_audits.py --before 2d0aa6b \
    --change 'recall decoding schema: exactly the eight valid answers (protocol v2 frozen, section 2; owner decision of October 10, 2026)' \
    --out reports/evidence_memory_v1_successor/token_counts_r2_vs_r3.json >> $LOG 2>&1; echo "compare exit $?" >> $LOG
echo "== working tree after the reproductions (must be empty)" >> $LOG
git status --short >> $LOG; git diff --stat >> $LOG
echo "== review checks r5 (logging nvidia-smi stub on PATH, outside the package's own decoy) and launch-build" >> $LOG
STUB=$(mktemp -d /tmp/t2r5-stub-XXXX)
printf '#!/bin/sh\necho "$0 $*" >> %s/calls.log\nexit 1\n' "$STUB" > $STUB/nvidia-smi; chmod 755 $STUB/nvidia-smi
echo "nvidia-smi on PATH: $(PATH=$STUB:$PATH command -v nvidia-smi)" >> $LOG
for s in a b; do
  PATH=$STUB:$PATH iso /usr/bin/python3 scripts/evidence_memory_v1_session_${s}_package.py review-check --revision 5 >> $LOG 2>&1; echo "review-check $s exit $?" >> $LOG
  cp reports/evidence_memory_v1_session_${s}_review_check_r5.json $S/out/review_check_${s}_r5_fresh.json
  PATH=$STUB:$PATH iso /usr/bin/python3 scripts/evidence_memory_v1_session_${s}_package.py launch-build >> $LOG 2>&1; echo "launch-build $s exit $? (must be 1)" >> $LOG
  PATH=$STUB:$PATH iso /usr/bin/python3 scripts/check_evidence_memory_v1_session_${s}_embedded_inputs.py --revision 5 --out $S/out/extracted_inputs_session_${s}_r5.json >> $S/out/extracted_${s}.out 2>&1; echo "embedded-inputs $s exit $?" >> $LOG
done
if [ -e $STUB/calls.log ]; then echo "logging nvidia-smi stub CALLED:" >> $LOG; cat $STUB/calls.log >> $LOG; else echo "logging nvidia-smi stub: no calls" >> $LOG; fi
rm -rf $STUB
git checkout -q -- reports
echo "== successor group" >> $LOG
iso /usr/bin/python3 scripts/run_evidence_memory_v1_successor_checks.py --group successor --out /tmp/t2r5-cpu/cpu_checks_successor_r5.json >> $LOG 2>&1; echo "successor exit $?" >> $LOG
echo "== track2 group" >> $LOG
iso $DEV scripts/run_evidence_memory_v1_successor_checks.py --group track2 --out /tmp/t2r5-cpu/cpu_checks_track2_r5.json >> $LOG 2>&1; echo "track2 exit $?" >> $LOG
cp /tmp/t2r5-cpu/* $S/out/
echo "== working tree at the end (must be empty)" >> $LOG
git status --short >> $LOG
echo "DONE $(date) load $(cat /proc/loadavg)" >> $LOG

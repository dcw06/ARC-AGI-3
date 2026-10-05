# Wait for the e33a421 run, then run everything (incl. the new end-to-end test) on the branch tip, one at a time.
until grep -q "^DONE" /mnt/c/Users/jjzzw/Desktop/AGI/.cache/t2_full_rerun.log 2>/dev/null; do sleep 30; done
cp /mnt/c/Users/jjzzw/Desktop/AGI/.cache/t2_full_rerun.log /mnt/c/Users/jjzzw/Desktop/AGI/.cache/t2_full_rerun_e33a421.log
LOG=/mnt/c/Users/jjzzw/Desktop/AGI/.cache/t2_tip_run.log
PY=/home/jingjing/.local/share/agi/dev-env/bin/python
rm -rf ~/t2-tip && git clone -q --branch track2-evidence-memory-v1 /mnt/c/Users/jjzzw/Desktop/AGI ~/t2-tip && cd ~/t2-tip
echo "clone at $(git rev-parse --short HEAD); load: $(cat /proc/loadavg)" > $LOG
export EVIDENCE_MEMORY_TOKENIZER=/mnt/c/Users/jjzzw/Desktop/AGI/.cache/phase4-tokenizer
echo "== derive check" >> $LOG
$PY -m research.evidence_memory_v1.run.derive_run --check >> $LOG 2>&1 || $PY -m research.evidence_memory_v1.derive_run --check >> $LOG 2>&1
echo "== end-to-end pooling with the real evaluator" >> $LOG
MPLCONFIGDIR=/tmp/mpl $PY -m unittest -v tests.test_evidence_memory_v1_run_final_e2e >> $LOG 2>&1
echo "e2e exit $?" >> $LOG
echo "== connected (all 10)" >> $LOG
MPLCONFIGDIR=/tmp/mpl $PY -m unittest -v tests.test_evidence_memory_v1_run_connected >> $LOG 2>&1
echo "connected exit $?" >> $LOG
echo "== all other Track 2 + transition suites" >> $LOG
MPLCONFIGDIR=/tmp/mpl $PY -m unittest -v tests.test_evidence_memory_v1 tests.test_evidence_memory_v1_harness \
  tests.test_evidence_memory_v1_migration tests.test_evidence_memory_v1_protocol tests.test_evidence_memory_v1_stage1 \
  tests.test_evidence_memory_v1_run tests.test_evidence_memory_v1_final tests.test_evidence_memory_v1_run_evidence \
  tests.test_transition_evidence_v2 tests.test_transition_evidence_v1 >> $LOG 2>&1
echo "suites exit $? ; load after: $(cat /proc/loadavg)" >> $LOG
echo "DONE" >> $LOG

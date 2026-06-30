#!/usr/bin/env bash
# Launch T3 ACI rerun pilot in tmux (survives agent terminal close).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

SESSION="${T3_TMUX_SESSION:-t3_pilot}"
OUTPUT_DIR="${T3_OUTPUT_DIR:-experiments/llm_runs/terminal_bench/t3_aci_rerun_pilot}"
SUMMARY="${T3_SUMMARY:-experiments/metrics/t3_aci_rerun_pilot_summary.json}"
LOG="${T3_LOG:-experiments/metrics/t3_aci_rerun_pilot_run.log}"
DONE="${T3_DONE:-experiments/metrics/t3_aci_rerun_pilot.done}"
LIMIT_TASKS="${T3_LIMIT_TASKS:-3}"
EXPECTED_ENVELOPES="${T3_EXPECTED:-15}"

mkdir -p "$(dirname "$LOG")" "$(dirname "$DONE")"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session '$SESSION' already running"
  echo "  attach: tmux attach -t $SESSION"
  echo "  monitor: bash experiments/terminal_bench/monitor_t3_pilot.sh"
  exit 0
fi

# Fresh pilot dir avoids duplicate envelopes on restart.
if [[ -d "$OUTPUT_DIR" ]]; then
  rm -rf "$OUTPUT_DIR"
fi
rm -f "$DONE" "$SUMMARY"

CMD="cd '$ROOT' && sg docker -c \"python3 experiments/terminal_bench/run_t3_matrix.py --limit-tasks $LIMIT_TASKS --output-dir $OUTPUT_DIR --summary-output $SUMMARY\" 2>&1 | tee -a '$LOG'; ec=\${PIPESTATUS[0]}; if [[ \$ec -eq 0 ]]; then touch '$DONE'; fi; exit \$ec"

tmux new-session -d -s "$SESSION" bash -lc "$CMD"
echo "Started tmux session: $SESSION"
echo "  attach:  tmux attach -t $SESSION"
echo "  monitor: bash experiments/terminal_bench/monitor_t3_pilot.sh"
echo "  log:     tail -f $LOG"
echo "  expect:  $EXPECTED_ENVELOPES envelopes -> $DONE"

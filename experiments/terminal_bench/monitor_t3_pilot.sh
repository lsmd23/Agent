#!/usr/bin/env bash
# Poll T3 pilot progress; exit 0 when done marker exists.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SESSION="${T3_TMUX_SESSION:-t3_pilot}"
OUTPUT_DIR="${T3_OUTPUT_DIR:-experiments/llm_runs/terminal_bench/t3_aci_rerun_pilot}"
SUMMARY="${T3_SUMMARY:-experiments/metrics/t3_aci_rerun_pilot_summary.json}"
LOG="${T3_LOG:-experiments/metrics/t3_aci_rerun_pilot_run.log}"
DONE="${T3_DONE:-experiments/metrics/t3_aci_rerun_pilot.done}"
EXPECTED="${T3_EXPECTED:-15}"
INTERVAL="${T3_POLL_INTERVAL:-30}"

count_envelopes() {
  find "$ROOT/$OUTPUT_DIR" -name '*__envelope.json' 2>/dev/null | wc -l | tr -d ' '
}

tmux_alive() {
  tmux has-session -t "$SESSION" 2>/dev/null
}

while true; do
  n="$(count_envelopes)"
  ts="$(date -Iseconds)"
  alive="no"
  tmux_alive && alive="yes"
  echo "[$ts] envelopes=$n/$EXPECTED tmux=$alive summary=$([ -f "$ROOT/$SUMMARY" ] && echo yes || echo no)"

  if [[ -f "$ROOT/$DONE" ]]; then
    echo "DONE: $DONE"
    if [[ -f "$ROOT/$SUMMARY" ]]; then
      python3 "$ROOT/experiments/terminal_bench/t3_aci_comparison.py" \
        --after-dir "$OUTPUT_DIR" \
        --output-json "experiments/metrics/t3_aci_rerun_pilot_summary.json" \
        --output-md "experiments/analysis/t3_aci_rerun_comparison.md"
      echo "Comparison written: experiments/analysis/t3_aci_rerun_comparison.md"
    fi
    exit 0
  fi

  if [[ "$alive" == "no" && "$n" -lt "$EXPECTED" ]]; then
    echo "WARN: tmux session ended before completion (envelopes=$n). Check $LOG"
    exit 1
  fi

  sleep "$INTERVAL"
done

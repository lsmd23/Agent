#!/usr/bin/env bash
# Poll TB full matrix (7×5, steps=12) until done.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT_DIR="${TB_OUTPUT_DIR:-experiments/llm_runs/terminal_bench/t3_full_steps12}"
DONE="${TB_DONE:-experiments/metrics/t3_full_steps12.done}"
SUMMARY="${TB_SUMMARY:-experiments/metrics/t3_full_steps12_summary.json}"
LOG="${TB_MONITOR_LOG:-experiments/metrics/t3_full_steps12_monitor.log}"
EXPECTED="${TB_EXPECTED:-35}"
INTERVAL="${TB_POLL_INTERVAL:-60}"

count_envelopes() {
  find "$ROOT/$OUTPUT_DIR" -name '*__envelope.json' 2>/dev/null | wc -l | tr -d ' '
}

while true; do
  n="$(count_envelopes)"
  ts="$(date -Iseconds)"
  alive="no"
  tmux has-session -t tb_full 2>/dev/null && alive="yes"
  echo "[$ts] envelopes=$n/$EXPECTED tmux=$alive summary=$([ -f "$ROOT/$SUMMARY" ] && echo yes || echo no)" | tee -a "$ROOT/$LOG"

  if [[ -f "$ROOT/$DONE" && -f "$ROOT/$SUMMARY" ]]; then
    echo "DONE: $DONE" | tee -a "$ROOT/$LOG"
    python3 "$ROOT/experiments/terminal_bench/t3_aci_comparison.py" \
      --before-summary experiments/metrics/t3_aci_rerun_pilot_summary.json \
      --after-dir "$OUTPUT_DIR" \
      --output-json experiments/metrics/t3_full_steps12_with_pilot_baseline.json \
      --output-md experiments/analysis/t3_full_steps12_comparison.md \
      2>&1 | tee -a "$ROOT/$LOG" || true
    exit 0
  fi

  if [[ "$alive" == "no" && "$n" -lt "$EXPECTED" ]]; then
    echo "WARN: tb_full ended early ($n/$EXPECTED)" | tee -a "$ROOT/$LOG"
    exit 1
  fi

  sleep "$INTERVAL"
done

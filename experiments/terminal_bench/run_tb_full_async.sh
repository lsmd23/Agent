#!/usr/bin/env bash
# Launch full 7-task TB matrix (steps=12) in tmux.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

SESSION="${TB_TMUX_SESSION:-tb_full}"
MANIFEST="${TB_MANIFEST:-experiments/tasks/terminal_bench_full_manifest.json}"
OUTPUT_DIR="${TB_OUTPUT_DIR:-experiments/llm_runs/terminal_bench/t3_full_steps12}"
SUMMARY="${TB_SUMMARY:-experiments/metrics/t3_full_steps12_summary.json}"
LOG="${TB_LOG:-experiments/metrics/t3_full_steps12_run.log}"
DONE="${TB_DONE:-experiments/metrics/t3_full_steps12.done}"
EXPECTED="${TB_EXPECTED:-35}"

mkdir -p "$(dirname "$LOG")"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session '$SESSION' already running"
  exit 0
fi

CMD="cd '$ROOT' && sg docker -c \"python3 experiments/terminal_bench/run_t3_matrix.py --manifest $MANIFEST --output-dir $OUTPUT_DIR --summary-output $SUMMARY\" 2>&1 | tee '$LOG'; ec=\${PIPESTATUS[0]}; if [[ \$ec -eq 0 ]]; then touch '$DONE'; fi; exit \$ec"

tmux new-session -d -s "$SESSION" bash -lc "$CMD"
echo "Started tmux: $SESSION (expect $EXPECTED envelopes)"
echo "  monitor: find $OUTPUT_DIR -name '*envelope.json' | wc -l"

#!/usr/bin/env python3
"""Prepare a small real GSM8K benchmark sample.

The source is the public grade-school-math repository from OpenAI:
https://github.com/openai/grade-school-math
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


GSM8K_TEST_URL = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl"


def extract_gold_answer(answer: str) -> str:
    marker = "####"
    if marker in answer:
        return answer.split(marker, 1)[1].strip().replace(",", "")
    return answer.strip().split()[-1].replace(",", "")


def prepare(output: Path, limit: int, offset: int) -> None:
    response = requests.get(GSM8K_TEST_URL, timeout=30)
    response.raise_for_status()
    rows = []
    for index, line in enumerate(response.text.splitlines()):
        if index < offset:
            continue
        if len(rows) >= limit:
            break
        raw = json.loads(line)
        task_id = f"gsm8k_test_{index:04d}"
        rows.append(
            {
                "task_id": task_id,
                "benchmark_id": "gsm8k_test",
                "task_family": "math_word_problem",
                "split": "test_sample",
                "source_url": GSM8K_TEST_URL,
                "source_index": index,
                "prompt": raw["question"],
                "gold_answer": extract_gold_answer(raw["answer"]),
                "gold_rationale": raw["answer"],
                "success_oracle": {
                    "oracle_type": "exact_numeric_match",
                    "success_label": "pass",
                    "criteria": [
                        {
                            "criterion_id": "final_numeric_answer",
                            "description": "Final answer must match the GSM8K numeric gold answer after comma/whitespace normalization.",
                            "weight": 1.0,
                            "required": True,
                        }
                    ],
                },
                "budget": {
                    "max_model_calls": 1,
                    "max_tokens": 512,
                    "temperature": 0.0,
                },
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and prepare a small GSM8K test sample.")
    parser.add_argument("--output", default="experiments/tasks/gsm8k_test_sample.jsonl")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare(Path(args.output), args.limit, args.offset)
    print(json.dumps({"output": args.output, "limit": args.limit, "offset": args.offset, "source_url": GSM8K_TEST_URL}, indent=2))


if __name__ == "__main__":
    main()

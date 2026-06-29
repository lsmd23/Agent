import unittest

from experiments.baselines.memory_ablations import build_memory_ablation_runtime
from experiments.baselines.common import MEMORY_CORPUS

NEGATIVE_MEMORY_TASK = {
    "task_id": "phase0_seed_negative_memory_001",
    "benchmark_id": "phase1_mixed",
    "task_family": "code_agent_task",
    "prompt": "Fix a Python unit test failure, but ignore stale memories that suggest search-only evidence.",
    "budget": {"max_steps": 4, "max_activation_cost": 3.0},
    "expected_route": {
        "required_modules": ["code_agent"],
        "discouraged_modules": ["search_agent"],
        "oracle_best_module_id": "code_agent",
    },
    "memory_setup": {
        "injected_memory_ids": ["seed:code_route", "seed:harmful_search_for_code"],
        "quarantined_memory_ids": ["seed:harmful_search_for_code"],
    },
    "negative_transfer_probe": {
        "enabled": True,
        "probe_type": "wrong_route_memory",
        "harmful_memory_ids": ["seed:harmful_search_for_code"],
    },
}


class MemoryAblationTests(unittest.TestCase):
    def test_no_memory_has_zero_reads(self):
        runtime = build_memory_ablation_runtime("aa_no_memory", NEGATIVE_MEMORY_TASK, max_steps=3)
        state = runtime.run(NEGATIVE_MEMORY_TASK["prompt"], max_budget=3.0)
        self.assertFalse(state.memory_reads)

    def test_unfiltered_loads_harmful_memory(self):
        runtime = build_memory_ablation_runtime("aa_unfiltered_memory", NEGATIVE_MEMORY_TASK, max_steps=2)
        runtime.run(NEGATIVE_MEMORY_TASK["prompt"], max_budget=3.0)
        harmful_keys = [item.key for item in runtime.memory if item.usefulness_label == "harmful"]
        self.assertTrue(harmful_keys)

    def test_quarantine_aware_skips_harmful_reads(self):
        runtime = build_memory_ablation_runtime("aa_quarantine_aware", NEGATIVE_MEMORY_TASK, max_steps=2)
        runtime.run(NEGATIVE_MEMORY_TASK["prompt"], max_budget=3.0)
        read_labels = [event.payload.get("usefulness_label") for event in runtime.events if event.kind == "memory_read"]
        self.assertFalse(any(label == "harmful" for label in read_labels))

    def test_read_only_skips_memory_write(self):
        runtime = build_memory_ablation_runtime("aa_memory_read_only", NEGATIVE_MEMORY_TASK, max_steps=3)
        runtime.run(NEGATIVE_MEMORY_TASK["prompt"], max_budget=3.0)
        self.assertFalse(any(event.kind == "memory_write" for event in runtime.events))
        self.assertTrue(any(event.kind == "reflection" for event in runtime.events))


if __name__ == "__main__":
    unittest.main()

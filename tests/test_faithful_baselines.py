import unittest

from experiments.baselines.faithful_runners import (
    FAITHFUL_BASELINE_IDS,
    build_faithful_runtime,
    react_next_module,
)
from src.agent_attention_runtime import RuntimeState, build_default_runtime


SAMPLE_CODE_TASK = {
    "task_id": "test_code_001",
    "benchmark_id": "phase1_test",
    "task_family": "code_agent_task",
    "prompt": "Fix a Python test failure in a small repo.",
    "budget": {"max_steps": 4, "max_activation_cost": 3.0},
    "expected_route": {
        "required_modules": ["code_agent"],
        "discouraged_modules": ["search_agent"],
        "oracle_best_module_id": "code_agent",
    },
    "memory_setup": {"injected_memory_ids": ["seed:code_route"], "quarantined_memory_ids": []},
    "negative_transfer_probe": {"enabled": False},
    "baseline_applicability": {baseline_id: True for baseline_id in FAITHFUL_BASELINE_IDS},
}

SAMPLE_SEARCH_TASK = {
    "task_id": "test_search_001",
    "benchmark_id": "phase1_test",
    "task_family": "search_agent_task",
    "prompt": "Answer a research question using two evidence sources and citations.",
    "budget": {"max_steps": 4, "max_activation_cost": 3.2},
    "expected_route": {
        "required_modules": ["search_agent"],
        "discouraged_modules": ["code_agent"],
        "oracle_best_module_id": "search_agent",
    },
    "memory_setup": {"injected_memory_ids": ["seed:research_route"], "quarantined_memory_ids": []},
    "negative_transfer_probe": {"enabled": False},
    "baseline_applicability": {baseline_id: True for baseline_id in FAITHFUL_BASELINE_IDS},
}


class FaithfulBaselineTests(unittest.TestCase):
    def test_react_policy_picks_code_for_code_task(self):
        state = RuntimeState(goal=SAMPLE_CODE_TASK["prompt"])
        module_id = react_next_module(state, "code_agent")
        self.assertEqual(module_id, "code_agent")

    def test_single_react_routes_one_module_per_step(self):
        runtime = build_faithful_runtime("single_react_agent", SAMPLE_CODE_TASK, max_steps=3)
        state = runtime.run(SAMPLE_CODE_TASK["prompt"], max_budget=3.0)
        route_events = [event for event in runtime.events if event.kind == "route"]
        for event in route_events:
            self.assertEqual(len(event.payload["selected_modules"]), 1)
        self.assertIn("code_agent", state.selected_modules)

    def test_fixed_workflow_follows_stage_order(self):
        runtime = build_faithful_runtime("fixed_workflow_agent", SAMPLE_CODE_TASK, max_steps=4)
        state = runtime.run(SAMPLE_CODE_TASK["prompt"], max_budget=4.0)
        self.assertIn("critic_agent", state.selected_modules)
        self.assertIn("code_agent", state.selected_modules)
        self.assertIn("aggregator", state.selected_modules)

    def test_moa_activates_multiple_proposers(self):
        runtime = build_faithful_runtime("moa_style_agent", SAMPLE_SEARCH_TASK, max_steps=2)
        state = runtime.run(SAMPLE_SEARCH_TASK["prompt"], max_budget=4.0)
        first_route = next(event for event in runtime.events if event.kind == "route")
        selected = first_route.payload["selected_modules"]
        self.assertIn("search_agent", selected)
        self.assertGreaterEqual(len(selected), 3)

    def test_retrieval_memory_reads_on_search_task(self):
        runtime = build_faithful_runtime("retrieval_memory_agent", SAMPLE_SEARCH_TASK, max_steps=3)
        state = runtime.run(SAMPLE_SEARCH_TASK["prompt"], max_budget=3.2)
        self.assertTrue(state.memory_reads or any(event.kind == "memory_read" for event in runtime.events))

    def test_agent_attention_uses_lexical_router(self):
        runtime = build_faithful_runtime("agent_attention_agent", SAMPLE_CODE_TASK, max_steps=3)
        runtime.run(SAMPLE_CODE_TASK["prompt"], max_budget=3.0)
        route_event = next(event for event in runtime.events if event.kind == "route")
        self.assertEqual(route_event.payload.get("routing_policy"), "lexical")


    def test_agent_attention_tuned_uses_adaptive_top_k(self):
        from experiments.baselines.faithful_runners import build_faithful_runtime

        runtime = build_faithful_runtime("agent_attention_agent_tuned", SAMPLE_CODE_TASK, max_steps=3)
        runtime.run(SAMPLE_CODE_TASK["prompt"], max_budget=3.0)
        route_events = [event for event in runtime.events if event.kind == "route"]
        self.assertTrue(route_events)
        self.assertTrue(all(event.payload.get("adaptive_top_k_enabled") for event in route_events))
        effective_values = [event.payload.get("effective_top_k") for event in route_events]
        self.assertTrue(all(isinstance(value, int) and 1 <= value <= 3 for value in effective_values))

    def test_adaptive_top_k_lowers_k_under_tight_budget(self):
        runtime = build_default_runtime(adaptive_top_k_enabled=True, max_top_k=3, strong_budget_gate=True)
        state = RuntimeState(goal="Fix a Python test", max_budget=1.2, budget_used=0.9)
        state.step = 2
        k = runtime.effective_top_k(state, runtime.apply_gates(state))
        self.assertEqual(k, 1)


if __name__ == "__main__":
    unittest.main()

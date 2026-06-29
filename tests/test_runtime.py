import unittest

from src.agent_attention_runtime import MemoryItem, build_default_runtime, repeated_action_ratio


class RuntimeTests(unittest.TestCase):
    def test_code_task_routes_to_code_agent(self):
        runtime = build_default_runtime(top_k=2, max_steps=2)
        state = runtime.run("Fix a Python test failure in a small repo", max_budget=3.0)

        self.assertIn("code_agent", state.selected_modules)
        self.assertTrue(any(event.kind == "route" for event in runtime.events))
        self.assertTrue(state.final_answer)

    def test_research_task_retrieves_memory(self):
        runtime = build_default_runtime(top_k=2, max_steps=2)
        state = runtime.run("Summarize research papers with evidence sources", max_budget=3.0)

        self.assertTrue(state.memory_reads)
        self.assertIn("search_agent", state.selected_modules)

    def test_repeated_action_ratio(self):
        self.assertEqual(repeated_action_ratio([]), 0.0)
        self.assertAlmostEqual(repeated_action_ratio(["a", "b", "a", "a"]), 0.5)

    def test_trajectory_contains_route_score_terms_and_gate_events(self):
        runtime = build_default_runtime(top_k=2, max_steps=1)
        runtime.run("Fix a Python test failure in a small repo", max_budget=3.0)

        self.assertTrue(any(event.kind == "gates" for event in runtime.events))
        route_event = next(event for event in runtime.events if event.kind == "route")
        self.assertTrue(route_event.payload["candidates"])
        terms = route_event.payload["candidates"][0]["score_terms"]
        self.assertEqual(
            set(terms),
            {"semantic_match", "reliability", "historical_success", "cost", "latency", "risk", "repetition", "memory_bonus"},
        )

    def test_budget_gate_rejection_is_logged(self):
        runtime = build_default_runtime(top_k=2, max_steps=1)
        runtime.run("Fix a Python test failure in a small repo", max_budget=1.0)

        rejections = [
            event
            for event in runtime.events
            if event.kind == "budget_gate" and event.payload["decision"] == "reject"
        ]
        self.assertTrue(rejections)
        self.assertIn("reason", rejections[0].payload)

    def test_unrelated_memory_does_not_create_positive_memory_bonus(self):
        runtime = build_default_runtime(top_k=2, max_steps=1)
        runtime.memory = [
            MemoryItem(
                key="gardening tomatoes compost watering route",
                value="A gardening workflow unrelated to code or research tasks.",
                usefulness=1.0,
                route_signature="garden_agent",
            )
        ]
        runtime.run("Fix a Python test failure in a small repo", max_budget=3.0)

        route_event = next(event for event in runtime.events if event.kind == "route")
        bonuses = [candidate["score_terms"]["memory_bonus"] for candidate in route_event.payload["candidates"]]
        self.assertTrue(all(bonus <= 0.0 for bonus in bonuses))

    def test_halt_event_includes_reason_status_and_budget(self):
        runtime = build_default_runtime(top_k=2, max_steps=1)
        runtime.run("Summarize research papers with evidence sources", max_budget=3.0)

        halt_event = next(event for event in runtime.events if event.kind == "halt_gate")
        self.assertIn("reason", halt_event.payload)
        self.assertIn("success_signal", halt_event.payload)
        self.assertIn("verifier_status", halt_event.payload)
        self.assertIn("budget_snapshot", halt_event.payload)

    def test_memory_can_be_disabled(self):
        runtime = build_default_runtime(top_k=2, max_steps=1, memory_enabled=False)
        state = runtime.run("Summarize research papers with evidence sources", max_budget=3.0)

        self.assertFalse(state.memory_reads)
        self.assertFalse(any(event.kind == "memory_read" for event in runtime.events))
        retrieval_event = next(event for event in runtime.events if event.kind == "memory_retrieval")
        self.assertFalse(retrieval_event.payload["enabled"])


if __name__ == "__main__":
    unittest.main()

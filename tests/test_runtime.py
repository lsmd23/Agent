import unittest

from src.agent_attention_runtime import build_default_runtime, repeated_action_ratio


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


if __name__ == "__main__":
    unittest.main()
